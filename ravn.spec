# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the Windows RAVN desktop build."""

from __future__ import annotations

from pathlib import Path

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.building.datastruct import Tree
from PyInstaller.utils.hooks import collect_data_files, collect_submodules


project_root = Path(__file__).resolve().parent
assets_dir = project_root / "assets"
translations_dir = project_root / "ravn_app" / "translations"


datas = []
if assets_dir.exists():
    datas.append(Tree(str(assets_dir), prefix="assets"))
if translations_dir.exists():
    datas.append(Tree(str(translations_dir), prefix="ravn_app/translations"))

datas += collect_data_files("customtkinter")
datas += collect_data_files("tkinterdnd2", include_py_files=False)

hiddenimports = sorted(
    {
        *collect_submodules("PIL"),
        *collect_submodules("yt_dlp"),
        *collect_submodules("tkinterdnd2"),
        "customtkinter",
    }
)


a = Analysis(
    [str(project_root / "ravn.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
