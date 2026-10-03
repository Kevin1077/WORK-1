# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


# ---------------------------------------------------------
# Hidden imports
# ---------------------------------------------------------

ui_hiddenimports = collect_submodules("ui")
utils_hiddenimports = collect_submodules("utils")
playwright_hiddenimports = collect_submodules("playwright")


# ---------------------------------------------------------
# Files to include
# ---------------------------------------------------------

datas = [
    # Application assets and fonts
    (r"assets", r"assets"),

    # Playwright Chromium browser
    (
        r"C:\Users\Kevin Biju Kulangara\AppData\Local\ms-playwright\chromium-1234\chrome-win64",
        r"chromium\chrome-win64",
    ),
]


# ---------------------------------------------------------
# Analysis
# ---------------------------------------------------------

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=[
        *ui_hiddenimports,
        *utils_hiddenimports,
        *playwright_hiddenimports,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)


# ---------------------------------------------------------
# PYZ
# ---------------------------------------------------------

pyz = PYZ(a.pure)


# ---------------------------------------------------------
# EXE
# ---------------------------------------------------------

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Étoffe Laundry",
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


# ---------------------------------------------------------
# COLLECT
# ---------------------------------------------------------

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Étoffe Laundry",
)