# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PeachAlgo Coach desktop build.
# Prefer running scripts/build-exe.ps1 which prepares static assets first.

from pathlib import Path

block_cipher = None
backend_dir = Path(SPECPATH).resolve()
static_dir = backend_dir / "static"
problems_json = backend_dir / "data" / "problems.json"

datas = []
if problems_json.exists():
    datas.append((str(problems_json), "data"))
if static_dir.exists():
    datas.append((str(static_dir), "static"))

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "app.main",
    "app.api.routes",
    "app.services.adapter",
    "app.services.planner",
    "app.services.review",
    "app.services.stats",
    "app.services.checkin",
    "pydantic.deprecated.decorator",
    "pystray._win32",
    "PIL._tkinter_finder",
]

a = Analysis(
    [str(backend_dir / "desktop_app.py")],
    pathex=[str(backend_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PeachAlgoCoach",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # tray app — no black console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PeachAlgoCoach",
)
