# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT_DIR = Path(__name__).resolve().parent
SRC_DIR = ROOT_DIR / "src"


a = Analysis(
    [str(SRC_DIR / "main.py")],
    pathex=[str(SRC_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "calculation",
        "config_loader",
        "database",
        "error",
        "models",
        "spectrum_reader",
        "ui",
        "ui.file_drop_line_edit",
        "ui.line_template_widget",
        "ui.main_window",
        "ui.startup_dialog",
        "ui.table_model",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "PyQt6.QtNetwork", "PyQt6.QtQml", "PyQt6.QtQuick", "PyQt6.QtPdf"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SignalProcessor",
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
