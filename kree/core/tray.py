import pystray
from PIL import Image, ImageDraw
import threading
from kree.core.runtime import ASSETS_DIR
import os
import sys
import winreg
_FALLBACK_COLORS = {
    "listening": "#00FF00", # Green
    "processing": "#FFFF00", # Yellow
    "speaking": "#0000FF", # Blue
    "error": "#FF0000", # Red
    "offline": "#444444" # Dark Gray
}

def _ensure_ico_files():
    """Generate actual .ico files on disk for Windows tray reliability."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for name, color in _FALLBACK_COLORS.items():
        ico_path = ASSETS_DIR / f"{name}.ico"
        if not ico_path.exists():
            image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            dc = ImageDraw.Draw(image)
            dc.ellipse((8, 8, 56, 56), fill=color)
            image.save(ico_path, format="ICO")

def _load_icon(name):
    return Image.open(ASSETS_DIR / f"{name}.ico")

def _is_run_on_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, "Kree")
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False

def _set_run_on_startup(enable):
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
    else:
        exe_path = os.path.abspath(sys.argv[0])
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
        
    if enable:
        winreg.SetValueEx(key, "Kree", 0, winreg.REG_SZ, f'"{exe_path}" --background')
    else:
        try:
            winreg.DeleteValue(key, "Kree")
        except FileNotFoundError:
            pass
    winreg.CloseKey(key)


class SystemTrayApp:
    def __init__(self, callbacks: dict):
        self.callbacks = callbacks
        self.icon = None
        
        _ensure_ico_files()
        
        self.img_listening = _load_icon("listening")
        self.img_processing = _load_icon("processing")
        self.img_speaking = _load_icon("speaking")
        self.img_error = _load_icon("error")
        self.img_offline = _load_icon("offline")

    def run_daemon(self):
        """Run pystray loop in a dedicated background thread."""
        thread = threading.Thread(target=self._run_internal, daemon=True)
        thread.start()
        
    def _run_internal(self):
        menu = pystray.Menu(
            pystray.MenuItem("Open Kree", self._on_open, default=True),
            pystray.MenuItem("Hide Kree", self._on_hide),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Restart Audio", self._on_restart_audio),
            pystray.MenuItem("Reload Wake Word", self._on_reload_wake),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Run on Startup", self._on_toggle_startup, checked=lambda item: _is_run_on_startup()),
            pystray.MenuItem("Diagnostics", self._on_diagnostics),
            pystray.MenuItem("View Logs", self._on_view_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._on_quit)
        )
        
        self.icon = pystray.Icon("Kree", self.img_offline, "Kree - Offline", menu)
        self.icon.run()

    # --- Status Setters ---
    def set_listening(self):
        if self.icon:
            self.icon.icon = self.img_listening
            self.icon.title = "Kree - Listening"

    def set_processing(self):
        if self.icon:
            self.icon.icon = self.img_processing
            self.icon.title = "Kree - Processing"

    def set_speaking(self):
        if self.icon:
            self.icon.icon = self.img_speaking
            self.icon.title = "Kree - Speaking"

    def set_error(self):
        if self.icon:
            self.icon.icon = self.img_error
            self.icon.title = "Kree - Error"

    def set_offline(self):
        if self.icon:
            self.icon.icon = self.img_offline
            self.icon.title = "Kree - Offline"

    # --- Callbacks ---
    def _on_open(self, icon, item):
        cb = self.callbacks.get("open")
        if cb: cb()

    def _on_hide(self, icon, item):
        cb = self.callbacks.get("hide")
        if cb: cb()

    def _on_restart_audio(self, icon, item):
        cb = self.callbacks.get("restart_audio")
        if cb: cb()

    def _on_reload_wake(self, icon, item):
        cb = self.callbacks.get("reload_wake")
        if cb: cb()

    def _on_diagnostics(self, icon, item):
        cb = self.callbacks.get("diagnostics")
        if cb: cb()

    def _on_view_logs(self, icon, item):
        cb = self.callbacks.get("view_logs")
        if cb: cb()
        
    def _on_toggle_startup(self, icon, item):
        current = _is_run_on_startup()
        _set_run_on_startup(not current)
        
    def _on_quit(self, icon, item):
        if self.icon:
            self.icon.stop()
        cb = self.callbacks.get("quit")
        if cb: cb()

    def notify(self, message, title="Kree"):
        if self.icon:
            try:
                self.icon.notify(message, title)
            except Exception:
                pass
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            import threading
            threading.Thread(target=toaster.show_toast, args=(title, message), kwargs={"duration": 5, "threaded": True}, daemon=True).start()
        except Exception:
            pass  # win10toast may fail in frozen builds due to missing pkg_resources metadata
