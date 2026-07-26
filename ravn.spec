# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the RAVN build. Produces two executables in one onedir
folder: the CustomTkinter desktop app (`RAVN`) and the headless Click CLI
(`ravn-cli`). Windows-only literals are guarded by sys.platform so the Linux
packaging workflow (.github/workflows/linux-package.yml) can reuse this spec."""

from __future__ import annotations

import os
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

# NOTE: no aria2p entry here. aria2 support shells out to the `aria2c` binary via
# subprocess (ravn_app/core/runners/aria2.py); the aria2p Python library is
# intentionally NOT a dependency (see requirements.in), so collecting its submodules
# would import a package that isn't installed.
hiddenimports = sorted(
    {
        *collect_submodules("PIL"),
        *collect_submodules("yt_dlp"),
        *collect_submodules("tkinterdnd2"),
        "customtkinter",
    }
)


# Ship the VC++ runtime DLLs so the build also starts on a machine without the
# redistributable installed. They are collected opportunistically: these absolute
# System32 paths do not exist on every Windows install (they arrive with the
# redistributable), and a missing file there used to hard-fail the whole build.
# Skipping them is safe -- CPython itself links against this runtime, so any machine
# that can run the packaged app has it.
binaries = []
if sys.platform == "win32":
    for _dll in ("vcruntime140.dll", "msvcp140.dll"):
        _dll_path = Path(os.environ.get("SystemRoot", "C:\\Windows")) / "System32" / _dll
        if _dll_path.is_file():
            binaries.append((str(_dll_path), "."))
        else:
            print(f"ravn.spec: skipping absent VC runtime DLL {_dll_path}")

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

# Second entry point: the Click CLI (ravn_app/cli.py). It imports no Tk/customtkinter,
# so the resulting console executable runs headless -- which is what makes it usable
# over SSH/in scripts, and lets CI smoke-test a real packaged binary without a display.
# Both executables land in the same COLLECT folder and share the collected libraries.
cli = Analysis(
    [str(project_root / "ravn_cli_entry.py")],
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
cli_pyz = PYZ(cli.pure)

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

# Console executable for the CLI. No Splash (a splash screen on a command-line tool
# would be nonsense) and console=True so stdout/stderr actually reach the terminal.
cli_exe = EXE(
    cli_pyz,
    cli.scripts,
    [],
    exclude_binaries=True,
    name="ravn-cli",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    icon=str(assets_dir / "ravn.ico") if (assets_dir / "ravn.ico").exists() else None,
    version='version_info.txt' if sys.platform == "win32" else None,
)

# Both executables are collected into one folder so they share a single copy of the
# bundled libraries; PyInstaller de-duplicates the overlapping binaries/datas entries.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    cli_exe,
    cli.binaries,
    cli.zipfiles,
    cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="RAVN",
)
