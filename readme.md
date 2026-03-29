# Kree

Kree is a Windows-first voice assistant for local automation, app launching, screen awareness, and task workflows.

## Overview

The project is intended to be source-first and easy to ship. You can run it from Python for development, or package it into a Windows executable for release builds.

## Features

* Real-time voice interaction
* System control and app launching
* Autonomous task execution
* Visual awareness through screen and webcam analysis
* Persistent memory for preferences and context
* Integrated tools for search, reminders, messaging, and code help

## Quick Start

```bash
git clone <your-fork-or-repo-url>
cd Mark-XXX-main
python setup.py
python main.py
```

On first launch, enter your Gemini API key when prompted.

## Build a Windows Executable

Use the checked-in PyInstaller spec:

```bash
pyinstaller "Kree AI.spec"
```

The packaged app will be created under `dist/Kree AI/`.

For a one-click Windows build, run `build_kree.bat`.

## Repository Layout

* `main.py` - assistant runtime and tool routing
* `ui.py` - desktop UI and widget behavior
* `actions/` - app launch, automation, and system actions
* `core/` - telemetry and runtime helpers
* `memory/` - configuration and persistent state
* `stitch_core_system_dashboard/` - bundled UI assets

## Requirements

* Windows 10 or 11
* Python 3.10 or newer
* Microphone
* Gemini API key

## Open Source Notes

* Source code lives in the repository.
* Release builds should be published separately in GitHub Releases.
* Generated artifacts such as `build/` and `dist/` are ignored from version control.

## License

This project is released under the MIT License. See [LICENSE](LICENSE).