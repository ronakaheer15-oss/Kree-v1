import shutil
import os

src = r"e:\stitch_core_system_dashboard\stitch_core_system_dashboard"
dst = r"e:\Mark-XXX-main\Mark-XXX-main\stitch_core_system_dashboard"

if os.path.exists(src):
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print("Files copied successfully!")
else:
    print(f"Source {src} does not exist.")
