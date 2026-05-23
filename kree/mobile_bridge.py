import asyncio
import hashlib
import base64
import json
import logging
import time
from collections import defaultdict

class RateLimiter:
    def __init__(self, max_calls=10, period=60):
        self.calls = defaultdict(list)
        self.max_calls = max_calls
        self.period = period
    
    def is_allowed(self, client_ip):
        now = time.time()
        self.calls[client_ip] = [
            t for t in self.calls[client_ip] 
            if now - t < self.period
        ]
        if len(self.calls[client_ip]) >= self.max_calls:
            return False
        self.calls[client_ip].append(now)
        return True

_ws_limiter = RateLimiter(max_calls=250, period=60) # Allow 15 websocket commands per minute
AUTH_TIMEOUT_SECONDS = 5.0
MAX_WS_PAYLOAD_BYTES = 16 * 1024 * 1024


def _validate_pwa_token(client_token: str, token_file) -> bool:
    """Return True only when client_token matches a stored, non-expired token.

    A missing or unreadable token file always denies access — never grants it.
    """
    from pathlib import Path
    token_file = Path(token_file)

    if not token_file.exists():
        return False

    try:
        data = json.loads(token_file.read_text(encoding="utf-8"))
        valid_token = data.get("token", "")
        token_expires = data.get("expires", 0)
    except Exception:
        return False

    if not valid_token or not client_token:
        return False

    if client_token != valid_token:
        return False

    if token_expires > 0 and time.time() > token_expires:
        logging.warning("[MOBILE BRIDGE] Token Expired")
        return False

    return True


def _extract_authorization_token(header_value: str) -> str:
    header_value = (header_value or "").strip()
    if header_value.lower().startswith("bearer "):
        return header_value[7:].strip()
    return header_value


def _get_pwa_token_file():
    from kree.core.runtime import CONFIG_DIR
    return CONFIG_DIR / "pwa_token.json"


def _validate_pin_token(client_token: str) -> bool:
    if ":" not in client_token:
        return False

    try:
        handle, pin = client_token.split(":", 1)
        from kree.core.auth_manager import AuthManager
        result = AuthManager.sign_in_user(handle, pin)
        if result.get("ok"):
            return True

        result2 = (
            AuthManager.verify_user_pin(result.get("user", {}).get("user_id", ""), pin)
            if result.get("user") else {"ok": False}
        )
        return bool(result2.get("ok", False))
    except Exception:
        return False


def _authenticate_mobile_token(client_token: str, token_file=None) -> bool:
    client_token = (client_token or "").strip()
    if not client_token:
        return False

    if _validate_pin_token(client_token):
        return True

    return _validate_pwa_token(client_token, token_file or _get_pwa_token_file())


def _server_ws_frame(opcode: int, payload: bytes = b"") -> bytes:
    frame = bytearray([0x80 | (opcode & 0x0f)])
    length = len(payload)
    if length < 126:
        frame.append(length)
    elif length < 65536:
        frame.append(126)
        frame.extend(length.to_bytes(2, byteorder="big"))
    else:
        frame.append(127)
        frame.extend(length.to_bytes(8, byteorder="big"))
    frame.extend(payload)
    return bytes(frame)


def _close_frame(code: int = 1008, reason: str = "Authentication failed") -> bytes:
    reason_bytes = reason.encode("utf-8")[:123]
    return _server_ws_frame(0x8, code.to_bytes(2, "big") + reason_bytes)


async def _read_client_ws_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    header = await reader.readexactly(2)
    b1, b2 = header

    opcode = b1 & 0x0f
    is_masked = b2 & 0x80
    payload_len = b2 & 0x7f

    if not is_masked:
        raise ValueError("Client WebSocket frames must be masked.")

    if payload_len == 126:
        ext = await reader.readexactly(2)
        payload_len = int.from_bytes(ext, "big")
    elif payload_len == 127:
        ext = await reader.readexactly(8)
        payload_len = int.from_bytes(ext, "big")

    if payload_len > MAX_WS_PAYLOAD_BYTES:
        raise ValueError("WebSocket payload too large.")

    masking_key = await reader.readexactly(4)
    masked_data = await reader.readexactly(payload_len)

    unmasked_data = bytearray(payload_len)
    for i in range(payload_len):
        unmasked_data[i] = masked_data[i] ^ masking_key[i % 4]

    return opcode, bytes(unmasked_data)

class KreeMobileBridge:
    def __init__(self, port=8443, on_command_callback=None, on_connect_callback=None):
        self.port = port
        self.clients = set()
        self.server = None
        self.on_command_callback = on_command_callback
        self.on_connect_callback = on_connect_callback
        self.on_notes_sync_callback = None
        self.on_contacts_sync_callback = None
        self.on_quick_action_callback = None
        self.on_clipboard_callback = None
        self.on_file_transfer_callback = None
        self.on_audio_callback = None  # mobile mic → kree audio pipeline

    async def broadcast_state(self, state):
        """Push Kree's current state (listening/speaking/executing) to mobile."""
        await self.broadcast({"type": "kree_state", "state": state})

    async def start(self):
        self.server = await asyncio.start_server(
            self.handle_client, '0.0.0.0', self.port)
        logging.info(f"[MOBILE BRIDGE] Listening on ws://0.0.0.0:{self.port}")
        
    async def stop(self):
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    async def broadcast(self, message: dict):
        if not self.clients:
            return
        payload = json.dumps(message)
        frame = _server_ws_frame(0x1, payload.encode('utf-8'))
        
        dead_clients = set()
        for writer in list(self.clients):
            try:
                writer.write(frame)
                await writer.drain()
            except (ConnectionResetError, ConnectionAbortedError, OSError, BrokenPipeError):
                dead_clients.add(writer)
            except Exception:
                dead_clients.add(writer)
                
        for writer in dead_clients:
            self.clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass

    async def _authenticate_first_frame(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, token_file) -> bool:
        deadline = time.monotonic() + AUTH_TIMEOUT_SECONDS
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False

            opcode, payload = await asyncio.wait_for(_read_client_ws_frame(reader), timeout=remaining)
            if opcode == 0x8: # CLOSE
                return False
            if opcode == 0x9: # PING
                writer.write(_server_ws_frame(0xA, payload))
                await writer.drain()
                continue
            if opcode == 0xA: # PONG
                continue
            if opcode != 0x1: # first meaningful frame must be text auth
                return False

            try:
                data = json.loads(payload.decode("utf-8"))
            except Exception:
                return False

            if data.get("type") != "auth":
                return False

            return _authenticate_mobile_token(str(data.get("token", "")), token_file)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            peer = writer.get_extra_info('peername')
            peer_ip = peer[0] if peer else "unknown"
            
            # Rate limit incoming connection handshakes
            if not _ws_limiter.is_allowed(peer_ip):
                logging.warning(f"[MOBILE BRIDGE] Rate limit exceeded for {peer_ip}")
                writer.write(b"HTTP/1.1 429 Too Many Requests\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            # 1. Read HTTP request
            request_line = await reader.readline()
            if not request_line: return
            
            headers = {}
            while True:
                line = await reader.readline()
                line = line.decode('utf-8').strip()
                if not line:
                    break
                if ':' in line:
                    k, v = line.split(':', 1)
                    headers[k.strip().lower()] = v.strip()
            
            # 2. Check WebSocket Upgrade
            if headers.get('upgrade', '').lower() != 'websocket':
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            # Header auth is used by native clients. Browser clients authenticate
            # with the first WebSocket message after the upgrade.
            token_file = _get_pwa_token_file()
            client_token = _extract_authorization_token(headers.get('authorization', ''))
            auth_passed = _authenticate_mobile_token(client_token, token_file) if client_token else False

            if client_token and not auth_passed:
                logging.warning(f"[MOBILE BRIDGE] Auth failed for {writer.get_extra_info('peername')}")
                writer.write(b"HTTP/1.1 403 Forbidden\r\n\r\n")
                await writer.drain()
                writer.close()
                return

            # 3. Complete Handshake
            key = headers.get('sec-websocket-key')
            if not key:
                writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                await writer.drain()
                writer.close()
                return
                
            magic = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            resp_key = base64.b64encode(hashlib.sha1((key + magic).encode('utf-8')).digest()).decode()
            
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                f"Sec-WebSocket-Accept: {resp_key}\r\n\r\n"
            )
            writer.write(response.encode('utf-8'))
            await writer.drain()

            if not auth_passed:
                auth_passed = await self._authenticate_first_frame(reader, writer, token_file)

            if not auth_passed:
                logging.warning(f"[MOBILE BRIDGE] Auth failed for {writer.get_extra_info('peername')}")
                writer.write(_close_frame())
                await writer.drain()
                writer.close()
                return
            
            self.clients.add(writer)
            if self.on_connect_callback:
                self.on_connect_callback(writer.get_extra_info('peername'))
            logging.info(f"[MOBILE BRIDGE] New device connected: {writer.get_extra_info('peername')}")

            # 4. Message Loop (read incoming masked frames)
            while True:
                opcode, unmasked_data = await _read_client_ws_frame(reader)
                
                if opcode == 0x8: # CLOSE
                    break
                
                if opcode == 0x9: # PING
                    writer.write(_server_ws_frame(0xA, unmasked_data))
                    await writer.drain()
                    continue
                elif opcode == 0xA: # PONG
                    continue
                    
                if opcode == 0x2: # binary frame — mobile mic audio
                    if hasattr(self, 'on_audio_callback') and self.on_audio_callback:
                        try:
                            self.on_audio_callback(unmasked_data)
                        except Exception as e:
                            logging.error(f"[MOBILE BRIDGE] Audio callback error: {e}")
                    continue

                if opcode == 0x1: # text frame
                    msg = unmasked_data.decode('utf-8')
                    try:
                        data = json.loads(msg)
                        msg_type = data.get('type', '')
                        if msg_type == 'device_info':
                            os_name = data.get('os', 'unknown')
                            logging.info(f"[MOBILE BRIDGE] Device: {os_name} ({data.get('agent', '')[:50]})")
                            print(f"[JARVIS] 📱 Mobile OS Detected: {os_name.upper()}")
                        elif msg_type == 'command':
                            if self.on_command_callback:
                                self.on_command_callback(data.get('text', ''))
                        elif msg_type == 'sync_notes':
                            notes = data.get('notes', [])
                            print(f"[JARVIS] 📝 Notes synced from mobile ({len(notes)} notes)")
                            if self.on_notes_sync_callback:
                                self.on_notes_sync_callback(notes)
                        elif msg_type == 'sync_contacts':
                            contacts = data.get('contacts', [])
                            print(f"[JARVIS] 👥 Contacts synced from mobile ({len(contacts)} entries)")
                            if self.on_contacts_sync_callback:
                                self.on_contacts_sync_callback(contacts)
                        elif msg_type == 'quick_action':
                            action = data.get('action', '')
                            print(f"[JARVIS] ⚡ Quick action from mobile: {action}")
                            if self.on_quick_action_callback:
                                self.on_quick_action_callback(action)
                        elif msg_type == 'clipboard_sync':
                            content = data.get('content', '')
                            print(f"[JARVIS] 📋 Clipboard from mobile ({len(content)} chars)")
                            if self.on_clipboard_callback:
                                self.on_clipboard_callback(content)
                        elif msg_type == 'file_transfer':
                            action = data.get('action', '')
                            if action == 'start':
                                print(f"[JARVIS] 📁 Receiving file: {data.get('name', '?')} ({data.get('size', 0)} bytes)")
                            elif action == 'complete':
                                print(f"[JARVIS] ✅ File transfer complete: {data.get('fileId', '')}")
                            if self.on_file_transfer_callback:
                                self.on_file_transfer_callback(data)
                    except json.JSONDecodeError:
                        pass
                    except Exception as e:
                        logging.error(f"[MOBILE BRIDGE] Callback processing error: {e}")
                        print(f"[JARVIS] ⚠️ Error executing mobile command: {e}")
                        
        except asyncio.IncompleteReadError:
            pass # Client disconnected abruptly
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass # WinError 64, 10054, etc — client dropped
        except Exception as e:
            if '10054' not in str(e) and '64' not in str(e):
                logging.error(f"[MOBILE BRIDGE] Error: {e}")
        finally:
            self.clients.discard(writer)
            try:
                writer.close()
            except Exception:
                pass
