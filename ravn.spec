"""
RAVN - Desktop Uygulama Kurulumu (PyInstaller ile)
Bu dosya PyInstaller tarafından kullanılacak spec dosyasını oluşturmak için gereklidir
"""

import sys
from pathlib import Path
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.building.datastruct import Tree

# Proje kök dizini
project_root = Path(__file__).parent
app_dir = project_root / "ravn_app"

# Veri dosyaları
datas = [
    # İkonlar ve görseller
    (str(app_dir / "assets"), "assets") if (app_dir / "assets").exists() else None,
    # Konfigürasyon dosyaları
    (str(project_root / "ravn_config.json"), "."),
]

# None değerleri kaldır
datas = [d for d in datas if d is not None]

# Gizli içe aktarmalar (PyInstaller tarafından otomatik olarak bulunamayan)
hiddenimports = [
    'customtkinter',
    'PIL',
    'yt_dlp',
    'sqlite3',
    'logging',
    'json',
    'pathlib',
    'subprocess',
    'threading',
    'queue',
    'importlib',
]

a = Analysis(
    [str(project_root / "ravn.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludedimports=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RAVN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Windows'ta console penceresi açma
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # İkon dosyası varsa buraya ekle
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RAVN'
)
