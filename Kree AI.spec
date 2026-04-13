# -*- mode: python ; coding: utf-8 -*-
# Kree AI — PyInstaller Build Spec (Production v0.1.0)

import os
from pathlib import Path


ROOT = Path(os.environ.get('KREE_ROOT') or Path.cwd()).resolve()


def _first_existing(*candidates: Path) -> Path:
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


# After reorganization, stitch dashboard lives in _Related_Projects
STITCH_ROOT = _first_existing(
    ROOT / 'stitch_core_system_dashboard',
    ROOT.parent / 'stitch_core_system_dashboard',
    ROOT.parent / '_Related_Projects' / 'stitch_core_system_dashboard_KREE_DESKTOP',
)

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / 'config'), 'config'),
        (str(ROOT / 'core'), 'core'),
        (str(ROOT / 'actions'), 'actions'),
        (str(ROOT / 'memory'), 'memory'),
        (str(ROOT / 'agent'), 'agent'),
        (str(ROOT / 'pwa'), 'pwa'),
        (str(ROOT / 'assets'), 'assets'),
        (str(ROOT / 'README-INSTALL.txt'), '.'),
        (str(STITCH_ROOT), 'stitch_core_system_dashboard'),
        (str(ROOT.parent / '.venv/Lib/site-packages/openwakeword/resources'), 'openwakeword/resources'),
    ],
    hiddenimports=[
        # ── Google AI SDKs (lazy imported) ────────────────────────────────
        'google.genai',
        'google.genai.types',
        'google.generativeai',
        'google.generativeai.types',
        'google.api_core',
        'google.auth',
        'google.auth.transport.requests',
        
        # ── Added via User Spec ───────────────────────────────────────────
        'openwakeword',
        'onnxruntime',
        'edge_tts',
        'pygame',
        'winreg',
        'resemblyzer',
        'pyaudio',
        'psutil',
        'pystray',
        'ctypes',
        'PIL',

        # ── Audio / TTS ──────────────────────────────────────────────────
        'pyttsx3',
        'pyttsx3.drivers',
        'pyttsx3.drivers.sapi5',

        # ── Windows COM / Audio Control ──────────────────────────────────
        'comtypes',
        'comtypes.stream',
        'comtypes.client',
        'pycaw',
        'pycaw.pycaw',

        # ── Notifications & OS ──────────────────────────────────────────
        'win10toast',
        'pyperclip',

        # ── WebSocket (mobile bridge) ────────────────────────────────────
        'websockets',
        'websockets.server',
        'websockets.legacy',
        'websockets.legacy.server',

        # ── Web scraping ─────────────────────────────────────────────────
        'bs4',
        'lxml',
        'lxml.etree',

        # ── QR Code (PWA connect tab) ────────────────────────────────────
        'qrcode',
        'qrcode.image',
        'qrcode.image.svg',

        # ── pywebview internals ──────────────────────────────────────────
        'webview',
        'clr_loader',
        'pythonnet',

        # ── Misc runtime imports ─────────────────────────────────────────
        'engineio',
        'certifi',
        'charset_normalizer',
        'urllib3',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── Heavy ML / Science libs not used ─────────────────────────────
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'tensorflow_probability',
        'pandas', 'matplotlib', 'sympy',
        'jax', 'jaxlib', 'numba',
        'IPython', 'ipykernel', 'ipywidgets',
        'pyarrow', 'dask', 'seaborn', 'skimage',
        'xarray', 'statsmodels', 'plotly',
        # ── Tkinter (not used, saves ~20MB) ──────────────────────────────
        'tkinter', '_tkinter', 'tk',
        # ── Test frameworks ──────────────────────────────────────────────
        'pytest', 'unittest', 'doctest',
        # ── Build tools (not needed at runtime) ──────────────────────────
        'pip',
        # ── Pythonwin / win32ui (MFC, ~7MB) ──────────────────────────────
        'Pythonwin', 'win32ui',
    ],
    noarchive=False,
    optimize=0,
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
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / 'assets' / 'kree.ico'),
    version=str(ROOT / 'version_info.txt'),
)
# ── Trim bloated binaries before COLLECT ──────────────────────────────
# Playwright ships a full node.exe (~90MB) — not needed, Playwright uses
# its own browser install at runtime. OpenCV FFmpeg DLL (~29MB) — not
# needed, we only use camera capture not video file I/O.
_EXCLUDE_BINARIES = {
    'node.exe',                      # Playwright node runtime (~90MB)
    'opencv_videoio_ffmpeg',          # OpenCV FFmpeg (~29MB)
    'mfc140u.dll',                    # MFC for Pythonwin (~6MB)
}

def _should_keep(name_tuple):
    name = name_tuple[0].lower() if name_tuple else ''
    return not any(exc in name for exc in _EXCLUDE_BINARIES)

trimmed_binaries = [b for b in a.binaries if _should_keep(b)]

coll = COLLECT(
    exe,
    trimmed_binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='Kree AI',
)
