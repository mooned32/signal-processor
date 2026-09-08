# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT_DIR = Path.cwd()

a = Analysis(
    ['run.py'],
    pathex=[str(ROOT_DIR / 'src')],
    binaries=[],
    datas=[],
    hiddenimports=[
        'app',
        'app.main',
        'app.core',
        'app.core.calculator',
        'app.core.parser',
        'app.gui',
        'app.gui.main_window',
        'app.gui.table_model',
        'pandas',
        'numpy',
        'PyQt6',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SignalProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)