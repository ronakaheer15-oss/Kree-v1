# Kree AI — Setup & Run Guide

## What is Kree

Kree is a voice-controlled AI assistant for Windows. It uses Google Gemini to understand your commands and can control your computer, browse the web, manage files, send messages, and more. It comes with a mobile companion app that runs on your phone through any browser.

## What you need before running

- **Python 3.10+** installed and in PATH
- **Windows 10 or higher**
- **A phone** on the same WiFi network (for mobile companion)
- **Google Gemini API key** — free at https://aistudio.google.com/apikey

## First time setup

1. Open a terminal in the `Mark-XXX-main` folder
2. Run `pip install -r requirements.txt`
3. Run `python -m playwright install` (one-time browser download)
4. Run `python main.py`
5. Enter your Gemini API key when prompted
6. Scan the QR code from the Connect tab on your phone

## How to run Kree (every time)

```
python main.py
```

Or double-click `Kree AI.exe` if using the packaged build.

## How to connect your phone

1. Launch Kree on your desktop
2. Open the **Connect** tab in the dashboard
3. Scan the QR code with your phone camera
4. The mobile companion opens in your browser — tap "Add to Home Screen"
5. Both devices must be on the **same WiFi network**

## What runs automatically (you do NOT need to start these)

- **PWA server** — starts with Kree, serves the mobile companion
- **WebSocket bridge** — starts with Kree, connects desktop ↔ mobile
- **Screen capture engine** — starts with Kree, used for vision commands
- **System monitor** — starts with Kree, tracks CPU/RAM for dashboard
- **Memory system** — starts with Kree, remembers your preferences

## What you DO need to do manually

- Enter your **API key** on first launch (one time only)
- **Scan QR code** on your phone to connect (one time only)
- Click **microphone button** or type to give commands

## How to build the .exe for distribution

```
build_kree.bat
```

This creates `dist\Kree AI\Kree AI.exe` and a release ZIP in `dist\release\`.
Optional: run `installer\build_installer.bat` to create a Windows installer (requires Inno Setup 6).

## Common problems and fixes

| Problem | Fix |
|---|---|
| `ModuleNotFoundError` on launch | Run `pip install -r requirements.txt` again |
| Microphone not working | Windows Settings → Privacy → Microphone → Allow apps |
| Phone can't connect | Both devices must be on same WiFi. Disable VPN. |
| SmartScreen blocks the exe | Click "More info" → "Run anyway" (normal for unsigned apps) |
| PWA server port conflict | Edit `config/settings.json` → change `pwa_port` to another number |

## File structure explained

```
Mark-XXX-main/
├── main.py              # Entry point — the brain
├── ui.py                # Desktop dashboard (pywebview)
├── serve_pwa.py         # Mobile companion server
├── mobile_bridge.py     # Desktop ↔ Phone WebSocket bridge
├── core/                # Security, auth, updates, telemetry
├── actions/             # All tool modules (browser, files, code, etc.)
├── agent/               # Task planner and executor
├── memory/              # User memory and config management
├── pwa/                 # Mobile companion web app files
├── config/              # API keys, settings (user data — preserved on update)
├── assets/              # App icon
├── build_kree.bat       # One-click exe builder
├── installer/           # Windows installer scripts (Inno Setup)
└── requirements.txt     # Python dependencies
```