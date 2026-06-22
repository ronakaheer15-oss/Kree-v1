import os
import sys
import io
import json
import shutil
import subprocess
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows console
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kree.core.runtime import APP_DATA_DIR, CONFIG_DIR, LOG_DIR, run_health_check

# Explicitly set PLAYWRIGHT_BROWSERS_PATH for the environment
PLAYWRIGHT_BROWSERS_PATH = APP_DATA_DIR / "playwright_browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_PATH)

def run_acceptance_test():
    print("=" * 60)
    print(" KREE AI - CLEAN MACHINE ACCEPTANCE TEST")
    print("=" * 60)
    
    # 1. Print telemetry paths
    print(f"Detected APP_DATA_DIR : {APP_DATA_DIR}")
    print(f"Detected CONFIG_DIR   : {CONFIG_DIR}")
    print(f"Detected LOG_DIR      : {LOG_DIR}")
    print(f"PLAYWRIGHT_BROWSERS_PATH explicitly set to: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
    
    # 2. Check if running in a clean state
    health_file = APP_DATA_DIR / "health.json"
    if health_file.exists():
        print(f"[Acceptance] Found existing health.json at {health_file}")
    else:
        print("[Acceptance] Running first-boot simulation (no previous health.json)")

    # 3. Trigger health check
    print("\nRunning startup health check...")
    health = run_health_check()
    
    print("\n[Health Check Results]")
    print(json.dumps(health, indent=4))
    
    # 4. Verify output files
    assert health_file.exists(), "health.json was not generated!"
    print(f"\n[Verification] Verified health.json exists at: {health_file}")
    
    # 5. Playwright Install and Launch Check
    if not health["chromium"]:
        print("\nChromium is missing. Performing background installation test...")
        env = dict(os.environ)
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(PLAYWRIGHT_BROWSERS_PATH)
        try:
            subprocess.check_call(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                env=env,
                timeout=600
            )
            print("Chromium installation completed. Re-running health check...")
            health = run_health_check()
            print(f"Updated Chromium presence: {health['chromium']}")
            assert health["chromium"], "Chromium presence check failed even after installation!"
        except Exception as e:
            print(f"❌ Chromium installation failed: {e}")
            sys.exit(1)
            
    # 6. Verify actual Playwright launch
    print("\nVerifying real Chromium launch capability...")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Launch in headless mode for the automated script
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://www.google.com")
            print(f"✅ Playwright launch SUCCESS! Loaded URL: {page.url}")
            browser.close()
    except Exception as e:
        print(f"❌ Playwright launch test failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" ACCEPTANCE CHECKS COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == "__main__":
    run_acceptance_test()
