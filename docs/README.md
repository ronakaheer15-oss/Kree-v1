# Kree AI — Local-First Voice Assistant

Kree is a local-first, privacy-focused AI voice assistant for Windows, designed to give you full control over your digital life without compromising your data. It leverages advanced multimodal models like Google Gemini Live for high-performance reasoning and local LLMs (via Ollama) for offline privacy. Kree can control your desktop, manage your files, browse the web, and even interact with you via a mobile companion app, all while keeping your sensitive information encrypted and on your device.

## Tech Stack

| Component | Technology |
|---|---|
| **Language** | Python 3.10+ |
| **Intelligence** | Google Gemini 2.0/2.5 Live, Ollama (Local LLMs) |
| **Interface** | pywebview (Desktop Dashboard), HTML/JS (Mobile PWA) |
| **Voice (STT)** | Vosk (Offline), Google Multimodal Live (Cloud) |
| **Voice (TTS)** | Edge TTS (Neural Neural Voices), fallback Local Speech |
| **Wake Word** | OpenWakeWord (ONNX), Resemblyzer (Voice Fingerprinting) |
| **Automation** | Playwright (Web), PyAutoGUI (Desktop), Custom OS Hooks |
| **Connectivity** | WebSockets (Mobile Bridge), PWA Server |

## Project Folder Structure

```text
Mark-XXX-main/
├── main.py              # Entry point — The Orchestrator (kree_master.py)
├── ui.py                # Desktop dashboard (pywebview)
├── serve_pwa.py         # Mobile companion server
├── mobile_bridge.py     # Desktop ↔ Phone WebSocket bridge
├── core/                # Security, auth, updates, telemetry, LLM gateway
├── actions/             # Tool modules (browser, files, code, etc.)
├── agent/               # Task planner and execution engine
├── memory/              # User memory and long-term context
├── pwa/                 # Mobile companion web app files
├── config/              # API keys, user settings (encrypted)
├── assets/              # App icons, sounds, and local models
└── docs/                # Project documentation
```

## How to Install and Run

### Prerequisites
- **Windows 10/11**
- **Python 3.10+**
- **Google Gemini API Key** (Get one at [aistudio.google.com](https://aistudio.google.com/apikey))

### Step-by-Step Setup
1. **Clone the Repository**:
   ```bash
   git clone <repo-url>
   cd Mark-XXX-main
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Install Browser for Web Actions**:
   ```bash
   python -m playwright install
   ```
4. **Launch Kree**:
   ```bash
   python main.py
   ```
5. **Initial Configuration**:
   - On the first launch, enter your Gemini API key in the dashboard.
   - (Optional) Record your voice to enable "Voice Lock" (Owner-only wake).
6. **Mobile Connection**:
   - Open the **Connect** tab in the Kree dashboard.
   - Scan the QR code with your phone to launch the mobile companion.

## Current Capabilities

- **Voice Interaction**: Wake Kree with "Hey Kree" or "Hey Jarvis". Supports whisper mode and voice fingerprinting.
- **Multimodal Vision**: Kree can "see" your screen or camera to answer questions about what you're doing.
- **Web Automation**: Navigate sites, search the web, and fill forms using the `kree_web` (browser_control) module.
- **File Management**: Organize your desktop, search for files, and manage directories via `kree_files` (file_controller).
- **System Control**: Adjust settings, open apps, and monitor system performance (CPU/RAM).
- **Long-Term Memory**: Kree remembers your name, preferences, and past interactions across sessions.
- **Mobile Bridge**: Control your PC from your phone using voice or text commands.

## Documentation Links

- [ARCHITECTURE.md](ARCHITECTURE.md) — Deep dive into how Kree works.
- [ROADMAP.md](ROADMAP.md) — Future versions and planned features.
- [CONTRIBUTING.md](CONTRIBUTING.md) — Guidelines for developers.
