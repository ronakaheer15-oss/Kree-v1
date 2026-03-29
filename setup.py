import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REQ_FILE   = str(SCRIPT_DIR / "requirements.txt")
SPEC_FILE  = str(SCRIPT_DIR / "Kree AI.spec")

print("Installing requirements...")
subprocess.run([sys.executable, "-m", "pip", "install", "-r", REQ_FILE], check=True)

print("Installing Playwright browsers...")
subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)

print("\n✅ Setup complete! Run 'python main.py' to start Kree.")
print(f"If you want a packaged build, run: pyinstaller \"{SPEC_FILE}\"")

