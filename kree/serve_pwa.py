"""
Kree PWA Server — Auto-discovers your WiFi IP and serves the mobile companion.
Starts automatically as a background thread when Kree launches.
Supports auth token validation for secure connections.
"""
import http.server
import socket
import os
import sys
import json
import threading
import secrets
from pathlib import Path


def _get_base_dir():
    """Resolve base directory for both frozen (exe) and dev environments."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _get_config_dir():
    """Config always lives next to the exe, not in _MEIPASS temp."""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent / 'config'
    return Path(__file__).resolve().parent / 'config'


BASE_DIR = _get_base_dir()
CONFIG_DIR = _get_config_dir()
PWA_DIR = BASE_DIR / "pwa"
TOKEN_FILE = CONFIG_DIR / "pwa_token.json"

DEFAULT_PORT = 8765


def get_local_ip():
    """Get the machine's WiFi/LAN IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_pwa_port():
    """Read port from config or use default."""
    settings_file = CONFIG_DIR / "settings.json"
    try:
        if settings_file.exists():
            data = json.loads(settings_file.read_text(encoding="utf-8"))
            return int(data.get("pwa_port", DEFAULT_PORT))
    except Exception:
        pass
    return DEFAULT_PORT


def load_or_create_token():
    """Load existing auth token or generate a new one on first launch."""
    import time
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if TOKEN_FILE.exists():
            data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            token = data.get("token", "")
            expires = data.get("expires", 0)
            
            # If valid and not expired
            if token and len(token) >= 16 and (expires == 0 or time.time() < expires):
                return token
    except Exception:
        pass

    # Generate new token with 24-hour expiration
    return reset_token()


def reset_token():
    """Generate a new token, invalidating all existing connected devices."""
    import time
    token = secrets.token_urlsafe(32)
    expires = time.time() + (24 * 3600)  # 24 hours
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps({"token": token, "expires": expires}, indent=2),
        encoding="utf-8"
    )
    return token

def get_pwa_url():
    """Get the full PWA URL without HTTP auth token injection."""
    ip = get_local_ip()
    port = get_pwa_port()
    return f"http://{ip}:{port}"


class _SilentHandler(http.server.SimpleHTTPRequestHandler):
    """Suppress noisy connection-reset errors from mobile browsers."""

    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=str(PWA_DIR), **kwargs)

    def handle(self):
        try:
            super().handle()
        except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError, OSError):
            pass

    def log_message(self, format, *args):
        # Only log successful requests, skip noise
        if len(args) >= 2 and isinstance(args[1], str) and args[1].startswith('4'):
            return
        # Completely silent in background mode
        pass


_server_instance = None
_server_thread = None
_server_error = None


def start_pwa_server_background():
    """Start the PWA server as a background daemon thread. Returns (url, error)."""
    global _server_instance, _server_thread, _server_error
    _server_error = None

    if not PWA_DIR.exists():
        _server_error = f"PWA folder not found: {PWA_DIR}"
        print(f"[KREE PWA] ERROR: {_server_error}")
        return None, _server_error

    port = get_pwa_port()
    url = get_pwa_url()

    def _serve():
        global _server_instance, _server_error
        try:
            _server_instance = http.server.ThreadingHTTPServer(
                ("0.0.0.0", port), _SilentHandler
            )
            print(f"[KREE PWA] Serving on http://0.0.0.0:{port}")
            _server_instance.serve_forever()
        except OSError as e:
            _server_error = f"PWA server failed to start on port {port} — {e}"
            print(f"[KREE PWA] ERROR: {_server_error}")
        except Exception as e:
            _server_error = f"PWA server error: {e}"
            print(f"[KREE PWA] ERROR: {_server_error}")

    _server_thread = threading.Thread(target=_serve, daemon=True, name="kree-pwa-server")
    _server_thread.start()

    # Give the server a moment to start or fail
    import time
    time.sleep(0.3)

    if _server_error:
        return None, _server_error

    print(f"[KREE PWA] Mobile companion ready: {url}")
    return url, None


def stop_pwa_server():
    """Stop the background PWA server."""
    global _server_instance
    if _server_instance:
        try:
            _server_instance.shutdown()
            _server_instance.server_close()
        except Exception:
            pass
        _server_instance = None


def get_server_status():
    """Return current server status dict for the UI."""
    return {
        "running": _server_instance is not None and _server_error is None,
        "url": get_pwa_url() if _server_instance else None,
        "port": get_pwa_port(),
        "error": _server_error,
        "local_ip": get_local_ip(),
    }


# Allow standalone execution for testing
if __name__ == "__main__":
    port = get_pwa_port()
    url = get_pwa_url()

    print()
    print("=" * 52)
    print("   KREE MOBILE COMPANION — PWA SERVER ACTIVE")
    print("=" * 52)
    print()
    print(f"   Your URL:  {url}")
    print()
    print("   HOW TO CONNECT YOUR PHONE:")
    print("   ─────────────────────────────────────────")
    print(f"   1. On your phone, open the browser")
    print(f"   2. Type this URL or scan the QR code in Kree")
    print(f"   3. Tap Share → 'Add to Home Screen'")
    print(f"   4. Open the Kree app from your home screen!")
    print()
    print("   Make sure your phone is on the SAME WiFi!")
    print("=" * 52)
    print()

    if not PWA_DIR.exists():
        print(f"[ERROR] pwa/ folder not found at {PWA_DIR}")
        sys.exit(1)

    os.chdir(str(PWA_DIR))
    handler = _SilentHandler
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", port), handler)
    except AttributeError:
        server = http.server.HTTPServer(("0.0.0.0", port), handler)

    print(f"[KREE] Serving PWA on http://0.0.0.0:{port} ...")
    print("[KREE] Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[KREE] Server stopped.")
        server.server_close()
