"""Quick script to copy logo + banner to DOWNLOAD_ME folder."""
import os, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "DOWNLOAD_ME")
os.makedirs(OUT, exist_ok=True)

logo_src = r"C:\Users\HP\.gemini\antigravity\brain\8f230f69-d216-4612-894f-7f054b5eef17\kree_unified_icon_1775146383052.png"
banner_src = r"C:\Users\HP\.gemini\antigravity\brain\8f230f69-d216-4612-894f-7f054b5eef17\kree_banner_1775146604564.png"

shutil.copy2(logo_src, os.path.join(OUT, "kree-logo.png"))
shutil.copy2(banner_src, os.path.join(OUT, "kree-banner.png"))

print("Done! Files ready in DOWNLOAD_ME/")
for f in os.listdir(OUT):
    size = os.path.getsize(os.path.join(OUT, f))
    print(f"  {f} ({size:,} bytes)")
