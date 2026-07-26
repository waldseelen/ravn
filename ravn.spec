# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the RAVN desktop build. Packaged releases are Windows-only
today (see build.ps1), but the Windows-only literals below are guarded by
sys.platform so a future Linux/macOS PyInstaller invocation doesn't hard-fail."""

from __future__ import annotations

import sys
from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ, Splash
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path.cwd().resolve()
assets_dir = project_root / "assets"
translations_dir = project_root / "ravn_app" / "translations"


datas = []
if assets_dir.exists():
    datas.extend(
        (
            str(path),
            str(Path("assets") / path.relative_to(assets_dir).parent).replace("\\", "/"),
        )
        for path in assets_dir.rglob("*")
        if path.is_file()
    )
if translations_dir.exists():
    datas.extend(
        (
            str(path),
            str(Path("ravn_app") / "translations" / path.relative_to(translations_dir).parent).replace("\\", "/"),
        )
        for path in translations_dir.rglob("*")
        if path.is_file()
    )

datas += collect_data_files("customtkinter")
datas += collect_data_files("tkinterdnd2", include_py_files=False)

hiddenimports = sorted(
    {
        *collect_submodules("PIL"),
        *collect_submodules("yt_dlp"),
        *collect_submodules("tkinterdnd2"),
        *collect_submodules("aria2p"),
        "customtkinter",
    }
)


binaries = []
if sys.platform == "win32":
    binaries = [
        ('C:\\Windows\\System32\\vcruntime140.dll', '.'),
        ('C:\\Windows\\System32\\msvcp140.dll', '.')
    ]

a = Analysis(
    [str(project_root / "ravn.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'unittest', 'pdb'],
    noarchive=False,
)

pyz = PYZ(a.pure)

splash = Splash(
    str(assets_dir / "ravnapp.jpeg"),
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    minify_script=True,
    always_on_top=True,
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    [],
    exclude_binaries=True,
    name="RAVN",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=str(assets_dir / "ravn.ico") if (assets_dir / "ravn.ico").exists() else None,
    version='version_info.txt' if sys.platform == "win32" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="RAVN",
)
