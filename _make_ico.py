"""
Convert the Kree brand icon to all required formats:
  - assets/kree.ico (multi-size ICO for the exe)
  - pwa/icon-192.png (PWA icon 192x192)
  - pwa/icon-512.png (PWA icon 512x512)
  - DOWNLOAD_ME/kree-logo.png (downloadable logo)
  - DOWNLOAD_ME/kree-banner.png (downloadable banner)
"""
from PIL import Image
import os
import shutil

ICON_SRC = r'C:\Users\HP\.gemini\antigravity\brain\8f230f69-d216-4612-894f-7f054b5eef17\kree_brand_icon_1775147411722.png'
BANNER_SRC = r'C:\Users\HP\.gemini\antigravity\brain\8f230f69-d216-4612-894f-7f054b5eef17\kree_brand_banner_1775147442610.png'
ROOT = os.path.dirname(os.path.abspath(__file__))

img = Image.open(ICON_SRC).convert('RGBA')

# 1. Create ICO with all required sizes
ico_path = os.path.join(ROOT, 'assets', 'kree.ico')
os.makedirs(os.path.join(ROOT, 'assets'), exist_ok=True)
img.save(ico_path, format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print(f"[1/5] ICO created: {os.path.getsize(ico_path):,} bytes")

# 2. Create PWA 192x192
pwa_192 = os.path.join(ROOT, 'pwa', 'icon-192.png')
img.resize((192, 192), Image.LANCZOS).save(pwa_192, format='PNG')
print(f"[2/5] PWA 192 created: {os.path.getsize(pwa_192):,} bytes")

# 3. Create PWA 512x512
pwa_512 = os.path.join(ROOT, 'pwa', 'icon-512.png')
img.resize((512, 512), Image.LANCZOS).save(pwa_512, format='PNG')
print(f"[3/5] PWA 512 created: {os.path.getsize(pwa_512):,} bytes")

# 4. DOWNLOAD_ME folder
dl = os.path.join(ROOT, "DOWNLOAD_ME")
os.makedirs(dl, exist_ok=True)
img.resize((1024, 1024), Image.LANCZOS).save(os.path.join(dl, "kree-logo.png"), format='PNG')
print(f"[4/5] Logo saved to DOWNLOAD_ME/kree-logo.png")

shutil.copy2(BANNER_SRC, os.path.join(dl, "kree-banner.png"))
print(f"[5/5] Banner saved to DOWNLOAD_ME/kree-banner.png")

print()
print("ALL DONE! Both PWA and EXE now use the same icon.")
print()
print("Files ready:")
for f in os.listdir(dl):
    size = os.path.getsize(os.path.join(dl, f))
    print(f"  DOWNLOAD_ME/{f} ({size:,} bytes)")
print()
print("Next: run .\\build_kree.bat to rebuild the exe with the new icon.")
