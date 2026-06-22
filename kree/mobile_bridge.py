import asyncio
import hashlib
import base64
import json
import logging
import time
from collections import defaultdict
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

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

class AuthLockout:
    def __init__(self, max_attempts=5, lockout_time=900):
        self.attempts = defaultdict(list)
        self.max_attempts = max_attempts
        self.lockout_time = lockout_time
        
    def register_failure(self, client_ip):
        now = time.time()
        self.attempts[client_ip].append(now)
        
    def is_locked_out(self, client_ip) -> bool:
        now = time.time()
        # Clean up old attempts
        self.attempts[client_ip] = [
            t for t in self.attempts[client_ip] 
            if now - t < self.lockout_time
        ]
        return len(self.attempts[client_ip]) >= self.max_attempts

_ws_limiter = RateLimiter(max_calls=250, period=60)
_auth_lockout = AuthLockout(max_attempts=5, lockout_time=900) # 15 minutes lockout
AUTH_TIMEOUT_SECONDS = 5.0

def _get_pwa_token_file():
    from kree.core.runtime import CONFIG_DIR
    return CONFIG_DIR / "pwa_token.json"

def _validate_pwa_token(client_token: str, token_file) -> bool:
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

    tf = token_file or _get_pwa_token_file()
    if not tf or not tf.exists():
        logging.warning("[MOBILE BRIDGE] Authentication Token file is missing or unreadable. Secure access denied.")
        return False

    return _validate_pwa_token(client_token, tf)

class KreeMobileBridge:
    def __init__(self, port=8765, on_command_callback=None, on_connect_callback=None):
        self.port = port
        self.clients = set()
        self.on_command_callback = on_command_callback
        self.on_connect_callback = on_connect_callback
        self.on_notes_sync_callback = None
        self.on_contacts_sync_callback = None
        self.on_quick_action_callback = None
        self.on_clipboard_callback = None
        self.on_file_transfer_callback = None
        self.on_audio_callback = None

    async def broadcast_state(self, state):
        await self.broadcast({"type": "kree_state", "state": state})

    async def start(self):
        # The FastAPI server now handles the listening socket, 
        # so we don't need to start a raw asyncio server here.
        logging.info(f"[MOBILE BRIDGE] Bridge initialized, ready for FastAPI to serve WebSockets.")
        
    async def stop(self):
        # Close all connected WebSocket clients
        for client in list(self.clients):
            try:
                await client.close()
            except Exception:
                pass
        self.clients.clear()

    async def broadcast(self, message: dict):
        if not self.clients:
            return
            
        dead_clients = set()
        for client in list(self.clients):
            try:
                # Send JSON data directly
                await client.send_json(message)
            except Exception:
                dead_clients.add(client)
                
        for client in dead_clients:
            self.clients.discard(client)

    async def send_audio_chunk(self, pcm_bytes: bytes):
        if not self.clients:
            return
            
        dead_clients = set()
        for client in list(self.clients):
            try:
                # Send raw binary bytes frame
                await client.send_bytes(pcm_bytes)
            except Exception:
                dead_clients.add(client)
                
        for client in dead_clients:
            self.clients.discard(client)

    async def _authenticate_first_frame(self, websocket: WebSocket, token_file) -> bool:
        try:
            # Wait for the first message (should be JSON auth)
            msg = await asyncio.wait_for(websocket.receive_text(), timeout=AUTH_TIMEOUT_SECONDS)
            data = json.loads(msg)
            if data.get("type") != "auth":
                return False
            return _authenticate_mobile_token(str(data.get("token", "")), token_file)
        except Exception:
            return False

    async def handle_websocket(self, websocket: WebSocket):
        client_ip = websocket.client.host if websocket.client else "unknown"
        
        if not _ws_limiter.is_allowed(client_ip):
            logging.warning(f"[MOBILE BRIDGE] Rate limit exceeded for {client_ip}")
            await websocket.close(code=1008, reason="Rate limit exceeded")
            return
            
        auth_header = websocket.headers.get("authorization", "")
        token_file = _get_pwa_token_file()
        
        if auth_header.startswith("Bearer "):
            client_token = auth_header[len("Bearer "):].strip()
            
            if _auth_lockout.is_locked_out(client_ip):
                logging.warning(f"[MOBILE BRIDGE] Auth locked out for {client_ip} due to too many failed attempts")
                await websocket.close(code=1008, reason="Too many failed attempts. Locked out.")
                return

            if not _authenticate_mobile_token(client_token, token_file):
                _auth_lockout.register_failure(client_ip)
                logging.warning(f"[MOBILE BRIDGE] Header auth failed for {client_ip}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
            await websocket.accept()
        else:
            await websocket.accept()
            
            if _auth_lockout.is_locked_out(client_ip):
                logging.warning(f"[MOBILE BRIDGE] Auth locked out for {client_ip} due to too many failed attempts")
                await websocket.close(code=1008, reason="Too many failed attempts. Locked out.")
                return

            auth_passed = await self._authenticate_first_frame(websocket, token_file)

            if not auth_passed:
                _auth_lockout.register_failure(client_ip)
                logging.warning(f"[MOBILE BRIDGE] Auth failed for {client_ip}")
                await websocket.close(code=1008, reason="Authentication failed")
                return
            
        self.clients.add(websocket)
        peer_name = f"{client_ip}:{websocket.client.port}" if websocket.client else client_ip
        if self.on_connect_callback:
            self.on_connect_callback(peer_name)
        logging.info(f"[MOBILE BRIDGE] New device connected: {peer_name}")
        
        try:
            await websocket.send_json({"type": "auth_ok"})
        except Exception:
            pass

        try:
            while True:
                # Wait for any type of message
                message = await websocket.receive()
                
                if "bytes" in message and message["bytes"]:
                    # Binary frame — mobile mic audio
                    if self.on_audio_callback:
                        try:
                            self.on_audio_callback(message["bytes"])
                        except Exception as e:
                            logging.error(f"[MOBILE BRIDGE] Audio callback error: {e}")
                    continue
                    
                if "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        msg_type = data.get('type', '')
                        if msg_type == 'device_info':
                            os_name = data.get('os', 'unknown')
                            logging.info(f"[MOBILE BRIDGE] Device: {os_name} ({data.get('agent', '')[:50]})")
                            print(f"[JARVIS] 📱 Mobile OS Detected: {os_name.upper()}")
                        elif msg_type == 'command':
                            if self.on_command_callback:
                                asyncio.create_task(asyncio.to_thread(self.on_command_callback, data.get('text', '')))
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
                        
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logging.error(f"[MOBILE BRIDGE] Error: {e}")
        finally:
            self.clients.discard(websocket)
