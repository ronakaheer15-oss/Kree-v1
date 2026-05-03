# -*- mode: python ; coding: utf-8 -*-
# Kree AI — PyInstaller Build Spec (Production v0.2.0 — Optimized)
#
# Target size: ~180–250 MB (down from ~1 GB)
# Key changes:
#   - Exclude PySide6/Qt (628 MB) — pywebview uses EdgeChromium on Windows
#   - Exclude torch (448 MB) — only used in optional export, not runtime
#   - Exclude llvmlite/numba (128 MB) — not imported anywhere
#   - Exclude vosk (52 MB) — not directly imported
#   - Fix actions.desktop_control → actions.desktop
#   - Bundle only .onnx models (not .tflite duplicates)
#   - Strip node.exe, opencv FFmpeg, MFC DLLs

import os
from pathlib import Path


ROOT = Path(os.environ.get('KREE_ROOT') or Path.cwd()).resolve()

# ── Only bundle .onnx models from openwakeword (skip .tflite duplicates) ─────
OWW_RESOURCES = ROOT.parent / '.venv' / 'Lib' / 'site-packages' / 'openwakeword' / 'resources'

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'config'), 'config'),
        (str(ROOT / 'pwa'), 'pwa'),
        (str(ROOT / 'assets'), 'assets'),
        # openwakeword models (ONNX only)
        (str(OWW_RESOURCES), 'openwakeword/resources'),
    ],
    hiddenimports=[
        # ── Kree Action Modules ───────────────────────────────────────────
        'kree.actions.flight_finder',
        'kree.actions.open_app',
        'kree.actions.downloader_updater',
        'kree.actions.turboquant_helper',
        'kree.actions.openapps_automation',
        'kree.actions.weather_report',
        'kree.actions.send_message',
        'kree.actions.reminder',
        'kree.actions.computer_settings',
        'kree.actions.screen_processor',
        'kree.actions.youtube_video',
        'kree.actions.cmd_control',
        'kree.actions.desktop',
        'kree.actions.browser_control',
        'kree.actions.file_controller',
        'kree.actions.code_helper',
        'kree.actions.dev_agent',
        'kree.actions.web_search',
        'kree.actions.computer_control',
        'kree.actions.email_calendar',

        # ── Core modules ──────────────────────────────────────────────────
        'kree.core.runtime',
        'kree.core.wakeword',
        'kree.core.telemetry',
        'kree.core.version',
        'kree.core.auth_manager',
        'kree.core.auth_ui',
        'kree.core.security_ui',
        'kree.core.update_service',
        'kree.core.api_setup_ui',
        'kree.core.tool_registry',
        'kree._paths',

        # ── Google AI SDKs ───────────────────────────────────────────────
        'google.genai',
        'google.genai.types',
        'google.genai.tools',
        'google.generativeai',
        'google.generativeai.types',
        'google.api_core',
        'google.auth',
        'google.auth.transport.requests',

        # ── Wake Word + Voice ────────────────────────────────────────────
        'openwakeword',
        'openwakeword.model',
        'onnxruntime',
        'resemblyzer',
        'resemblyzer.voice_encoder',

        # ── Audio / TTS ──────────────────────────────────────────────────
        'edge_tts',
        'pygame',
        'pyaudio',
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',
        'speech_recognition',

        # ── Desktop UI ───────────────────────────────────────────────────
        'webview',
        'clr_loader',
        'pythonnet',

        # ── System Control ───────────────────────────────────────────────
        'psutil',
        'pystray',
        'ctypes',
        'winreg',
        'comtypes',
        'comtypes.stream',
        'comtypes.client',
        'pycaw',
        'pycaw.pycaw',

        # ── Notifications ────────────────────────────────────────────────
        'win10toast',
        'pyperclip',

        # ── Web / Network ────────────────────────────────────────────────
        'requests',
        'websockets',
        'websockets.server',
        'websockets.legacy',
        'websockets.legacy.server',
        'duckduckgo_search',
        'bs4',
        'lxml',
        'lxml.etree',
        'certifi',
        'charset_normalizer',
        'urllib3',
        'engineio',

        # ── Image / QR ───────────────────────────────────────────────────
        'PIL',
        'qrcode',
        'qrcode.image',
        'qrcode.image.svg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ══════════════════════════════════════════════════════════════════
        # SIZE KILLERS — These are the packages that bloat the EXE to ~1GB
        # ══════════════════════════════════════════════════════════════════

        # ── PySide6 / Qt (~628 MB) ───────────────────────────────────────
        # pywebview uses EdgeChromium on Windows, NOT Qt.
        # PyInstaller's hook-qtpy.py auto-detects PySide6 and bundles it.
        'PySide6', 'PySide2', 'PyQt5', 'PyQt6',
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        'PySide6.QtNetwork', 'PySide6.QtWebEngine', 'PySide6.QtQml',
        'PySide6.QtQuick', 'PySide6.QtSvg',
        'shiboken6', 'shiboken2',
        'qtpy',

        # ── PyTorch (~448 MB) ────────────────────────────────────────────
        # Only used in optional turboquant export + onnx_runner export.
        # resemblyzer CAN use torch but works fine with numpy-only path.
        'torch', 'torchvision', 'torchaudio',
        'torch.cuda', 'torch.nn', 'torch.utils',

        # ── llvmlite + numba (~128 MB) ───────────────────────────────────
        # Transitive dep of scipy/sklearn. NOT imported by Kree code.
        'llvmlite', 'numba',

        # ── vosk (~52 MB) ────────────────────────────────────────────────
        # NOT directly imported. speech_recognition uses Google STT.
        'vosk',

        # ── Heavy science libs NOT used ──────────────────────────────────
        'tensorflow', 'tensorflow_probability',
        'pandas', 'matplotlib', 'sympy',
        'jax', 'jaxlib',
        'IPython', 'ipykernel', 'ipywidgets',
        'pyarrow', 'dask', 'seaborn', 'skimage',
        'xarray', 'statsmodels', 'plotly',
        'networkx',

        # ── Tkinter (~20 MB) ────────────────────────────────────────────
        'tkinter', '_tkinter', 'tk',

        # ── Unused wake word engines ─────────────────────────────────────
        'pvporcupine', 'pvrecorder',
        'sounddevice',

        # ── Test / Build tools ───────────────────────────────────────────
        'pytest', 'unittest', 'doctest',
        'pip', 'setuptools', 'wheel',
        'Pythonwin', 'win32ui',
    ],
    noarchive=False,
    optimize=1,        # bytecode optimization (strips asserts + docstrings)
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Kree AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,       # Keep console for debug visibility; set False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'kree.ico'),
    version=str(ROOT / 'version_info.txt'),
)

# ── Trim bloated binaries before COLLECT ──────────────────────────────────────
_EXCLUDE_BINARIES = {
    'node.exe',                          # Playwright node runtime (~90 MB)
    'opencv_videoio_ffmpeg',             # OpenCV FFmpeg DLL (~29 MB)
    'mfc140u.dll',                       # MFC for Pythonwin (~6 MB)
    'qt6',                               # Any leaked Qt6 DLLs
    'qt5',                               # Any leaked Qt5 DLLs
    'pyside6',                           # Any leaked PySide6 binaries
    'shiboken6',                         # PySide6 binding generator
    'libcrypto-3-x64.dll',              # Duplicate OpenSSL (keep one copy)
}

# Also strip .tflite model duplicates (we only use ONNX inference)
_EXCLUDE_EXTENSIONS = {'.tflite'}

def _should_keep(name_tuple):
    if not name_tuple:
        return True
    name = name_tuple[0].lower()
    # Check binary name exclusions
    if any(exc in name for exc in _EXCLUDE_BINARIES):
        return False
    # Check extension exclusions in data files
    if any(name.endswith(ext) for ext in _EXCLUDE_EXTENSIONS):
        return False
    return True

trimmed_binaries = [b for b in a.binaries if _should_keep(b)]
trimmed_datas = [d for d in a.datas if _should_keep(d)]

coll = COLLECT(
    exe,
    trimmed_binaries,
    trimmed_datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Kree AI',
)
