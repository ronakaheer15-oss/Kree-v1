import pystray
from PIL import Image, ImageDraw
import threading
from pathlib import Path

def _create_fallback_icon(color):
    """Generate a simple colored circle icon if actual assets are missing."""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    dc.ellipse((8, 8, 56, 56), fill=color)
    return image

class SystemTrayApp:
    def __init__(self, on_wake_click, on_quit_click):
        self.on_wake_click = on_wake_click
        self.on_quit_click = on_quit_click
        self.icon = None
        
        # Load or generate states
        base_dir = Path("assets")
        base_dir.mkdir(exist_ok=True)
        
        try:
            self.img_sleeping = Image.open(base_dir / "kree_sleeping.png")
        except:
            self.img_sleeping = _create_fallback_icon('gray')
            
        try:
            self.img_active = Image.open(base_dir / "kree_active.png")
        except:
            self.img_active = _create_fallback_icon('#00DC82') # Green

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
