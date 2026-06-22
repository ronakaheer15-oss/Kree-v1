import sys
import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import io
import time
import platform
import traceback
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

class SafeStream:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        try:
            if self.stream is not None:
                self.stream.write(data)
        except Exception:
            pass
    def flush(self):
        try:
            if self.stream is not None:
                self.stream.flush()
        except Exception:
            pass
    def __getattr__(self, attr):
        if self.stream is None:
            raise AttributeError(attr)
        return getattr(self.stream, attr)

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emoji/symbols
if sys.platform.startswith("win") and 'pytest' not in sys.modules:
    if hasattr(sys.stdout, 'buffer') and sys.stdout is not None:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        except Exception:
            pass
    sys.stdout = SafeStream(sys.stdout)
    if hasattr(sys.stderr, 'buffer') and sys.stderr is not None:
        try:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        except Exception:
            pass
    sys.stderr = SafeStream(sys.stderr)



def check_chromium():
    """Detect the installed Edge WebView2 runtime.
    The previous implementation looked for a single hard‑coded GUID, which may not match the
    GUID present on every system. This version enumerates all sub‑keys under the EdgeUpdate
    "Clients" registry node (both 32‑ and 64‑bit views) and returns the first value it finds
    for the "pv" (product version) entry.
    If no version is discovered, it falls back to a lightweight import check of the
    `pywebview` package, which confirms the library is bundled but does not guarantee the
    runtime presence.
    """
    try:
        import winreg
        # Registry locations to probe – both 32‑bit (WOW6432Node) and native 64‑bit views
        base_paths = [
            r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients",
            r"SOFTWARE\Microsoft\EdgeUpdate\Clients",
        ]
        for base in base_paths:
            for hive in [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]:
                try:
                    root = winreg.OpenKey(hive, base, 0, winreg.KEY_READ)
                except OSError:
                    # Path may not exist in this hive – continue
                    continue
                try:
                    num_subkeys = winreg.QueryInfoKey(root)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(root, i)
                            subkey = winreg.OpenKey(hive, f"{base}\\{subkey_name}", 0, winreg.KEY_READ)
                            val, _ = winreg.QueryValueEx(subkey, "pv")
                            winreg.CloseKey(subkey)
                            if val:
                                winreg.CloseKey(root)
                                return True, f"Edge WebView2 Runtime v{val} detected (registry GUID {subkey_name})"
                        except OSError:
                            # No "pv" value under this GUID – ignore
                            pass
                except OSError:
                    pass
                finally:
                    winreg.CloseKey(root)
        # Registry scan yielded nothing – try a lightweight import check
        try:
            import webview
            return True, "pywebview importable (WebView2 runtime could not be verified via registry)"
        except Exception as e_import:
            return False, f"WebView2 runtime not detected (registry scan failed and pywebview import error: {e_import})"
    except Exception as e:
        return False, f"WebView2 check failed: {e}"

def run_diagnostics():
    print("=========================================")
    print("      KREE SYSTEM DIAGNOSTICS            ")
    print("=========================================")
    start_time = time.perf_counter()

    results = {}
    
    # 1. Vault decryption check
    def check_vault():
        try:
            from kree.core import vault
            test_val = "diagnostics_test_string"
            enc = vault.encrypt_data(test_val)
            dec = vault.decrypt_data(enc)
            if dec == test_val:
                return True, "Vault operational (encryption/decryption successful)"
            return False, "Vault decryption test failed (mismatch)"
        except Exception as e:
            return False, f"Vault error: {e}"

    # 2. ONNX Runtime check
    def check_onnx():
        try:
            import onnxruntime
            return True, f"ONNX Runtime v{onnxruntime.__version__} importable"
        except Exception as e:
            return False, f"ONNX Runtime error: {e}"

    # 3. Wake Word check
    def check_wakeword():
        try:
            import openwakeword
            from openwakeword.model import Model
            return True, "OpenWakeWord engine and models available"
        except Exception as e:
            return False, f"Wake Word engine error: {e}"

    # 4. Camera check
    def check_camera():
        try:
            import cv2
            return True, f"OpenCV v{cv2.__version__} camera controls available"
        except Exception as e:
            return False, f"OpenCV import error: {e}"

    # 5. Audio Input check
    def check_audio_input():
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            cnt = p.get_device_count()
            p.terminate()
            if cnt > 0:
                return True, f"Found {cnt} audio input device(s)"
            return False, "No audio input devices found (microphone missing)"
        except Exception as e:
            return False, f"PyAudio error: {e}"

    # 6. Audio Output check
    def check_audio_output():
        try:
            # pyrefly: ignore [missing-import]
            import pygame
            pygame.mixer.init()
            pygame.mixer.quit()
            return True, "Pygame Mixer operational"
        except Exception as e:
            return False, f"Pygame Mixer init error: {e}"


    # 8. Playwright check
    def check_playwright():
        try:
            import playwright
            return True, "Playwright library importable"
        except Exception as e:
            return False, f"Playwright import error: {e}"

    # 9. Internet connectivity check
    def check_internet():
        try:
            import urllib.request
            # Run quick ping to Google
            with urllib.request.urlopen("https://www.google.com", timeout=2.0) as response:
                if response.status == 200:
                    return True, "Internet connection successful"
            return False, "Failed to connect to Google (Status not 200)"
        except Exception as e:
            return False, f"Internet connection failed: {e}"

    checks = {
        "Vault": check_vault,
        "ONNX": check_onnx,
        "Wake Word": check_wakeword,
        "Camera": check_camera,
        "Audio Input": check_audio_input,
        "Audio Output": check_audio_output,
        "WebView2/Chromium": check_chromium,
        "Playwright": check_playwright,
        "Internet": check_internet
    }

    with ThreadPoolExecutor(max_workers=len(checks)) as executor:
        futures = {name: executor.submit(check_fn) for name, check_fn in checks.items()}
        for name, future in futures.items():
            results[name] = future.result()

    total_time = time.perf_counter() - start_time
    
    critical_checks = {"Vault", "Internet"}
    any_failed_critical = False
    any_failed_optional = False

    for name, (ok, desc) in results.items():
        if ok:
            symbol = "[OK]  "
        else:
            if name in critical_checks:
                symbol = "[FAIL]"
                any_failed_critical = True
            else:
                symbol = "[WARN]"
                any_failed_optional = True
        print(f"{name.ljust(18)}: {desc}")
            
    print("=========================================")
    print(f"Total diagnostic check time: {total_time:.2f} seconds")
    
    if any_failed_critical:
        status_str = "FAILED"
    elif any_failed_optional:
        status_str = "DEGRADED"
    else:
        status_str = "PASSED"
        
    print(f"Overall status: {status_str}")
    print("=========================================")
    return not any_failed_critical


def log_crash(e: Exception):
    try:
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data) / "Kree"
        else:
            base_dir = Path.home() / "AppData" / "Local" / "Kree"
        log_dir = base_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_log_file = log_dir / "crash.log"
        
        import logging
        from logging.handlers import RotatingFileHandler
        
        logger = logging.getLogger("KreeCrash")
        logger.setLevel(logging.CRITICAL)
        if not logger.handlers:
            handler = RotatingFileHandler(str(crash_log_file), maxBytes=5 * 1024 * 1024, backupCount=1, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        error_details = traceback.format_exc()
        logger.critical(
            f"\nPLATFORM: {platform.platform()}\n"
            f"PYTHON: {sys.version}\n"
            f"EXCEPTION: {type(e).__name__}: {e}\n"
            f"TRACEBACK:\n{error_details}"
        )
    except Exception as ie:
        print(f"Failed to log crash to file: {ie}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


if __name__ == "__main__":
    if "--version" in sys.argv:
        try:
            from kree.core.version import APP_NAME, APP_VERSION, BUILD_ID
            py_ver = platform.python_version()
            print(f"{APP_NAME} {APP_VERSION}")
            print(f"Build: {BUILD_ID}")
            print(f"Python: {py_ver}")
        except Exception as e:
            print(f"Kree AI 1.0.0 (version info load error: {e})")
        sys.exit(0)

    if "--diagnostics" in sys.argv:
        success = run_diagnostics()
        sys.exit(0 if success else 1)
        
    try:
        from kree.main_entry import main
        main()
    except Exception as e:
        log_crash(e)
        sys.exit(1)
