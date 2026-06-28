"""
Kree PWA Server — Auto-discovers your WiFi IP and serves the mobile companion.
Starts automatically as a background thread when Kree launches.
Now uses FastAPI and Uvicorn for unified HTTP/WebSocket serving.
"""
import socket
import json
import threading
import secrets
import uvicorn
from kree.core.runtime import BUNDLE_DIR, CONFIG_DIR as RUNTIME_CONFIG_DIR

BASE_DIR = BUNDLE_DIR
CONFIG_DIR = RUNTIME_CONFIG_DIR
PWA_DIR = BASE_DIR / "pwa"
TOKEN_FILE = CONFIG_DIR / "pwa_token.json"

DEFAULT_PORT = 8765
TOKEN_TTL_SECONDS = 30 * 24 * 3600

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

    return reset_token()

def reset_token():
    """Generate a new token, invalidating all existing connected devices."""
    import time
    token = secrets.token_urlsafe(32)
    expires = time.time() + TOKEN_TTL_SECONDS
    
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(
        json.dumps({"token": token, "expires": expires}, indent=2),
        encoding="utf-8"
    )
    return token

def get_pwa_url():
    """Get the full PWA URL with authentication token."""
    ip = get_local_ip()
    port = get_pwa_port()
    token = load_or_create_token()
    return f"http://{ip}:{port}?token={token}"

_server_thread = None
_server_error = None
_uvicorn_server = None

def start_pwa_server_background():
    """Start the unified FastAPI server as a background daemon thread. Returns (url, error)."""
    global _server_thread, _server_error, _uvicorn_server
    _server_error = None

    if not PWA_DIR.exists():
        _server_error = f"PWA folder not found: {PWA_DIR}"
        print(f"[KREE PWA] ERROR: {_server_error}")
        return None, _server_error

    port = get_pwa_port()
    url = get_pwa_url()

    def _serve():
        global _server_error, _uvicorn_server
        try:
            print(f"[KREE PWA] Serving on {url}")
            config = uvicorn.Config("kree.fastapi_server:app", host="0.0.0.0", port=port, log_level="warning")
            _uvicorn_server = uvicorn.Server(config)
            _uvicorn_server.run()
        except OSError as e:
            _server_error = f"PWA server failed to start on port {port} — {e}"
            print(f"[KREE PWA] ERROR: {_server_error}")
        except Exception as e:
            _server_error = f"PWA server error: {e}"
            print(f"[KREE PWA] ERROR: {_server_error}")

    _server_thread = threading.Thread(target=_serve, daemon=True, name="kree-fastapi-server")
    _server_thread.start()

    import time
    time.sleep(0.5)

    if _server_error:
        return None, _server_error

    print(f"[KREE PWA] Mobile companion ready: {url}")
    return url, None

def stop_pwa_server():
    """Stop the background FastAPI server."""
    global _uvicorn_server
    if _uvicorn_server:
        _uvicorn_server.should_exit = True

def get_server_status():
    """Return current server status dict for the UI."""
    return {
        "running": _uvicorn_server is not None and _server_error is None,
        "url": get_pwa_url(),
        "port": get_pwa_port(),
        "error": _server_error,
        "local_ip": get_local_ip(),
    }
