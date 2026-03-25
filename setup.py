import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REQ_FILE   = str(SCRIPT_DIR / "requirements.txt")

print("Installing requirements...")
subprocess.run([sys.executable, "-m", "pip", "install", "-r", REQ_FILE], check=True)

print("Installing Playwright browsers...")
subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)

print("\n✅ Setup complete! Run 'python main.py' to start MARK XXV.")

