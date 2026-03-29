# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


ROOT = Path(__file__).resolve().parent

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
        (str(ROOT / 'stitch_core_system_dashboard'), 'stitch_core_system_dashboard'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Kree AI',
)
