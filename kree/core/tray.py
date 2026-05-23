import pystray
from PIL import Image, ImageDraw
import threading
from kree.core.runtime import ASSETS_DIR

_FALLBACK_ICONS = {}


def _create_fallback_icon(color):
    """Generate a simple colored circle icon if actual assets are missing."""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((8, 8, 56, 56), fill=color)
    return image


def _get_fallback_icon(color):
    if color not in _FALLBACK_ICONS:
        _FALLBACK_ICONS[color] = _create_fallback_icon(color)
    return _FALLBACK_ICONS[color]


def _load_icon(path, fallback_color):
    try:
        return Image.open(path)
    except (FileNotFoundError, OSError):
        return _get_fallback_icon(fallback_color)


class SystemTrayApp:
    def __init__(self, on_wake_click, on_quit_click):
        self.on_wake_click = on_wake_click
        self.on_quit_click = on_quit_click
        self.icon = None
        
        base_dir = ASSETS_DIR
        self.img_sleeping = _load_icon(base_dir / "kree_sleeping.png", 'gray')
        self.img_active = _load_icon(base_dir / "kree_active.png", '#00DC82')

    def run_daemon(self):
        """Run pystray loop in a dedicated background thread."""
        thread = threading.Thread(target=self._run_internal, daemon=True)
        thread.start()
        
    def _run_internal(self):
        menu = pystray.Menu(
            pystray.MenuItem("Wake Kree", self._on_wake),
            pystray.MenuItem("Quit", self._on_quit)
        )
        
        self.icon = pystray.Icon("Kree", self.img_sleeping, "Kree - sleeping", menu)
        # Blocks the current thread, but runs inside our daemon thread
        self.icon.run()

    def set_sleeping(self):
        if self.icon:
            self.icon.icon = self.img_sleeping
            self.icon.title = "Kree - sleeping"

    def set_active(self):
        if self.icon:
            self.icon.icon = self.img_active
            self.icon.title = "Kree - active"

    def _on_wake(self, icon, item):
        self.on_wake_click()
        
    def _on_quit(self, icon, item):
        if self.icon:
            self.icon.stop()
        self.on_quit_click()
