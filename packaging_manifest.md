# Kree AI Packaging Readiness Audit Report

This report catalogs all resources, dynamic dependencies, and operating system linkages that must be verified for PyInstaller compatibility.

---

## 1. Packaging Manifest
These are the non-Python files that must be copied into the packaged bundle:

- **Wake Word Models (ONNX only):**
  - All `.onnx` models under the `openwakeword` package resource directories (e.g. `openwakeword/resources/models/*.onnx`).
- **Configuration Templates:**
  - `config/*.json` (e.g., `api_keys.json`, `audio_settings.json`, `automations_config.json`, `service_keys.json`, `user_auth.json`, `user_profile.json`).
  - `config/prompt.txt` (System prompt).
- **Desktop UI Dashboards:**
  - HTML, CSS, JS, and image files in `stitch_core_system_dashboard/` (Light/Dark themes, minimized control widget).
- **Progressive Web App (PWA) Mobile Assets:**
  - HTML, CSS, JS, manifest, and logos in the `pwa/` folder (used by the mobile bridge).
- **Icons, Fonts, and Audio Cues:**
  - `assets/kree.ico` (Executable and notification tray icon).
  - `assets/fonts/fonts.css` (Web font sheets).
  - `assets/sounds/*.mp3` and `assets/sounds/*.wav` (Wake/sleep and greeting cues).
  - `assets/ui/boot.html` and `assets/ui/auto_update_popup.js`.
- **System Version Specs:**
  - `version_info.txt` (Executable headers).

---

## 2. Dynamic & Conditional Imports
The following third-party dependencies are loaded dynamically at runtime (e.g., inside functions or via `importlib`) and have been explicitly declared in `hiddenimports` in `pyinstaller.spec` to prevent dynamic loading failure inside the compiled EXE:

- **Dynamic Kree Actions:**
  - `pyautogui` (for virtual inputs, mouse/keyboard automation).
  - `cv2` / `opencv-python` (for webcam/video capture).
  - `mss` (for high-speed screenshot capture).
  - `pyperclip` (for clipboard operations).
  - `playwright` (for headless browser operations).
  - `youtube_transcript_api` (for scraping YouTube transcripts).
  - `send2trash` (for sending files to the recycle bin).
- **Scientific/Voice Processing Modules:**
  - `scipy` and `scipy.signal` (for voice frequency conversion).
  - `sklearn` and `sklearn.metrics` (for speech enrollment distance thresholds).

---

## 3. Windows API & COM Dependencies
These modules link directly to Windows native functions and must not be stripped or blocked:

- **`ctypes` DLL Mappings:**
  - `user32.dll` (for `GetForegroundWindow`, `MessageBoxW`, `SystemParametersInfoW` wallpaper setup, and virtual key commands).
  - `credui.dll` (for Windows Hello authentication: `CredUIPromptForWindowsCredentialsW` and `CredUnPackAuthenticationBufferW`).
  - `advapi32.dll` (for `LogonUserW`).
  - `kernel32.dll` (for `GetLastError` and handle controls).
- **Registry Access (`winreg`):**
  - Used by `actions.open_app` and `actions.desktop` to discover application paths and install states.
- **COM Interfaces (`comtypes` & `pycaw`):**
  - Used by `actions.computer_settings` to manipulate system volume, capture audio sessions, and query speaker states.

---

## 4. User Data Storage Locations
Kree AI uses isolated writable paths to ensure user-state files do not live next to the read-only executable folder:
- **Default Path:** `%LOCALAPPDATA%\Kree AI\` (e.g. `C:\Users\<User>\AppData\Local\Kree AI\`)
- **Resolved Subfolders:**
  - `config/` (User API keys, audio presets, and automations).
  - `memory/` (Logs of long-term memory facts and access scores).
  - `logs/` (Rotating debug log files, crash records).
  - `vault/` (Encrypted credential vault payloads).
  - `triggers/` (Saved conditional trigger engine rules).
