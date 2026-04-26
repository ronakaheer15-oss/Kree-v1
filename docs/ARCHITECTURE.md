# Kree AI — System Architecture

This document outlines the internal flow and module structure of Kree.

## System Flow: Voice to Response

Kree follows a continuous loop for voice interaction:

```text
[ User Voice ]
      │
      ▼
[ Wake Word Engine (OpenWakeWord + Resemblyzer) ]
      │ (If "Hey Kree" + Owner Voice Verified)
      ▼
[ Audio Capture (PyAudio) ] ───▶ [ Visual Context (Screen/Cam Capture) ]
      │                                 │
      ▼                                 ▼
[ Kree Brain (Gemini 2.5 Live / Local LLM) ]
      │
      ▼
[ Action Engine (Lazy Loader) ]
      │ (Identifies & Executes Tool)
      ▼
[ Tool Execution (Browser, Files, OS) ]
      │
      ▼
[ Response Generation (Neural TTS) ]
      │
      ▼
[ Feedback to UI & Audio Output ]
```

## Module Explanation

Kree is built as a modular system where specific functions are delegated to specialized "Controllers".

### 1. `kree_master.py` (main.py)
The central orchestrator of the system. It handles the lifecycle of the application, initializes the UI, manages the WebSocket bridge for mobile, and maintains the primary loop for the Gemini Live session.

### 2. `kree_web.py` (actions/browser_control.py)
Powered by Playwright, this module allows Kree to interact with the web like a human. It can search, click, type, and scrape content. It automatically detects the system's default browser (Chrome, Edge, Brave, etc.) to maintain a familiar environment.

### 3. `kree_files.py` (actions/file_controller.py)
The file system librarian. It handles all I/O operations, including listing files, searching via regex/extension, organizing messy directories (like the Desktop), and reading/writing documents.

### 4. `kree_memory.py` (memory/memory_manager.py)
Manages long-term persistence. It stores user facts, preferences, and session history in an encrypted JSON format. It ensures that Kree "grows" with the user by injecting relevant context into every prompt.

### 5. `kree_brain.py` (core/llm_gateway.py)
The intelligence router. It decides whether a request should be handled by high-performance cloud models (Gemini) or processed locally on the user's GPU (Ollama) to ensure maximum privacy and offline capability.

## Plugin Architecture

New capabilities should be added as independent scripts in the `actions/` directory. 

**Steps to plug in a new module:**
1. Create a new `.py` file in `actions/` (e.g., `actions/spotify_control.py`).
2. Define a main function that accepts a `parameters` dict.
3. Register the tool in `core/tool_registry.py` with its JSON schema.
4. Add the module to the `LazyToolLoader` in `main.py`.

## Privacy Model

Kree is built on a "Local-First" philosophy:

- **Local Storage**: All configuration, API keys, and long-term memory are stored locally.
- **Encryption**: Sensitive data (memory, keys) is encrypted using AES-256 via `core/vault.py`.
- **Minimal Cloud**: External calls are limited to the Gemini API (for brain reasoning) and optional Edge TTS. No user data is "phoned home" to Kree servers.
- **Offline Mode**: When toggled, Kree switches to `LOCAL_NEXUS` mode, using only local models (Ollama) and Vosk STT, ensuring zero data leaves the machine.
