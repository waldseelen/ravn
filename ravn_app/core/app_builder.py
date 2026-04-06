"""
PyInstaller Desktop Uygulaması Oluşturucu
Windows, macOS ve Linux için tek kaynak koddan executable oluşturur
"""

import importlib.util
import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, List
import platform as platform_module
from enum import Enum


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Platform(Enum):
    """Desteklenen işletim sistemleri"""
    WINDOWS = "Windows"
    MACOS = "Darwin"
    LINUX = "Linux"


class AppBuilder:
    """PyInstaller ile desktop uygulaması oluşturucu"""

    def __init__(self, project_root: Optional[str] = None):
        """
        Başlatma

        Args:
            project_root: Proje kök dizini (otomatik olarak tespit edilebilir)
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = Path(__file__).parent

        self.dist_dir = self.project_root / "dist"
        self.build_dir = self.project_root / "build"
        self.spec_file = self.project_root / "ravn.spec"

        logger.info(f"Proje kök: {self.project_root}")

    def check_requirements(self) -> bool:
        """PyInstaller ve gerekli bağımlılıkları kontrol et"""
        required_packages = {
            'PyInstaller': 'PyInstaller',
            'customtkinter': 'customtkinter',
            'yt-dlp': 'yt_dlp',
            'pillow': 'PIL',
        }

        missing_packages = [
            package_name
            for package_name, import_name in required_packages.items()
            if importlib.util.find_spec(import_name) is None
        ]

        if missing_packages:
            logger.error("❌ Eksik paketler: %s", ", ".join(missing_packages))
            return False

        logger.info("✅ Tüm gerekli paketler yüklü")
        return True

    def check_ffmpeg(self) -> bool:
        """FFmpeg ve FFprobe'un yüklü olup olmadığını kontrol et"""
        try:
            # FFmpeg kontrol
            result_ffmpeg = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                timeout=5
            )

            # FFprobe kontrol
            result_ffprobe = subprocess.run(
                ['ffprobe', '-version'],
                capture_output=True,
                timeout=5
            )

            if result_ffmpeg.returncode == 0 and result_ffprobe.returncode == 0:
                logger.info("✅ FFmpeg ve FFprobe yüklü")
                return True
            else:
                logger.warning("⚠️ FFmpeg veya FFprobe bulunamadı")
                return False

        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠️ FFmpeg veya FFprobe sistem yolunda bulunamadı")
            return False

    def create_spec_file(self) -> bool:
        """PyInstaller spec dosyası oluştur"""
        try:
            cmd = [
                sys.executable,
                '-m', 'PyInstaller',
                '--onefile',
                '--windowed',
                '--name=RAVN',
                '--icon=ravn_icon.ico' if Path(self.project_root / "ravn_icon.ico").exists() else '',
                str(self.project_root / "ravn.py")
            ]

            # Boş argümanları kaldır
            cmd = [arg for arg in cmd if arg]

            logger.info("Spec dosyası oluşturuluyor...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Spec dosyası başarıyla oluşturuldu")
                return True
            else:
                logger.error(f"Spec dosyası oluşturma hatası: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Spec dosyası oluşturma hatası: {e}")
            return False

    def build_executable(self, one_file: bool = True, windowed: bool = True) -> bool:
        """
        Executable dosyası oluştur

        Args:
            one_file: Tek dosya olarak oluştur
            windowed: Pencere modunda oluştur (konsol çıktısı olmadan)
        """
        try:
            cmd = [
                sys.executable,
                '-m', 'PyInstaller',
                '--clean',
                '--name=RAVN',
                '--distpath=' + str(self.dist_dir),
                '--buildpath=' + str(self.build_dir),
            ]

            if one_file:
                cmd.append('--onefile')

            if windowed:
                cmd.append('--windowed')

            # İkon dosyası varsa ekle
            icon_path = self.project_root / "ravn_icon.ico"
            if icon_path.exists():
                cmd.append(f'--icon={icon_path}')

            # Gizli içe aktarmalar
            hidden_imports = [
                'customtkinter',
                'PIL',
                'yt_dlp',
            ]

            for imp in hidden_imports:
                cmd.append(f'--hidden-import={imp}')

            cmd.append(str(self.project_root / "ravn.py"))

            logger.info("Executable oluşturuluyor...")
            logger.info(f"Komut: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                logger.info("✅ Executable başarıyla oluşturuldu")
                logger.info(f"Konum: {self.dist_dir / 'RAVN.exe' if platform_module.system() == 'Windows' else self.dist_dir / 'RAVN'}")
                return True
            else:
                logger.error(f"Executable oluşturma hatası: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Executable oluşturma hatası: {e}")
            return False

    def bundle_ffmpeg(self) -> bool:
        """FFmpeg ve FFprobe'u uygulamaya bundle et"""
        try:
            import shutil

            # FFmpeg ve FFprobe'u bul
            if platform_module.system() == "Windows":
                ffmpeg_name = "ffmpeg.exe"
                ffprobe_name = "ffprobe.exe"
            else:
                ffmpeg_name = "ffmpeg"
                ffprobe_name = "ffprobe"

            ffmpeg_path = shutil.which(ffmpeg_name)
            ffprobe_path = shutil.which(ffprobe_name)

            if not ffmpeg_path or not ffprobe_path:
                logger.warning("⚠️ FFmpeg/FFprobe sistem yolunda bulunamadı")
                logger.info("Ipucu: https://ffmpeg.org/download.html adresinden indirin")
                return False

            # Dist dizinine kopyala
            app_dir = self.dist_dir / "RAVN" if not (self.dist_dir / "RAVN.exe").exists() else self.dist_dir
            app_dir.mkdir(parents=True, exist_ok=True)

            shutil.copy(ffmpeg_path, app_dir / ffmpeg_name)
            shutil.copy(ffprobe_path, app_dir / ffprobe_name)

            logger.info("✅ FFmpeg ve FFprobe bundle edildi")
            return True

        except Exception as e:
            logger.error(f"FFmpeg bundling hatası: {e}")
            return False

    def create_installer(self) -> bool:
        """NSIS ile Windows installer oluştur"""
        try:
            nsis_script = self.project_root / "ravn_installer.nsis"

            # NSIS script oluştur
            nsis_content = self._generate_nsis_script()

            with open(nsis_script, 'w') as f:
                f.write(nsis_content)

            logger.info("NSIS script oluşturuldu")

            # NSIS çalıştır
            result = subprocess.run(
                ['makensis', str(nsis_script)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.info("✅ Installer başarıyla oluşturuldu")
                return True
            else:
                logger.warning("⚠️ NSIS bulunamadı. Manuel installer oluştur")
                return False

        except Exception as e:
            logger.error(f"Installer oluşturma hatası: {e}")
            return False

    def _generate_nsis_script(self) -> str:
        """NSIS installer scripti oluştur"""
        return '''
; RAVN Media Manager Installer Script
; NSIS 3.0+

!include "MUI2.nsh"

; Tanımlamalar
!define PRODUCT_NAME "RAVN"
!define PRODUCT_VERSION "1.0.0"
!define PRODUCT_PUBLISHER "RAVN Project"
!define PRODUCT_DIR_REGKEY "Software\\RAVN"

; Installer Ayarları
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "RAVN-Setup-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES\\${PRODUCT_NAME}"
ShowInstDetails show
ShowUnInstDetails show

; MUI Ayarları
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Dil
!insertmacro MUI_LANGUAGE "Turkish"

; Installer Bölümleri
Section "RAVN Kurulum"
    SetOutPath "$INSTDIR"

    ; Dosyaları kopyala
    File /r "dist\\RAVN\\*.*"

    ; Başlat Menüsü kısayolları
    CreateDirectory "$SMPROGRAMS\\${PRODUCT_NAME}"
    CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\${PRODUCT_NAME}.lnk" "$INSTDIR\\RAVN.exe"
    CreateShortCut "$SMPROGRAMS\\${PRODUCT_NAME}\\Kaldır.lnk" "$INSTDIR\\uninstall.exe"

    ; Masaüstü kısayolu
    CreateShortCut "$DESKTOP\\${PRODUCT_NAME}.lnk" "$INSTDIR\\RAVN.exe"

    ; Registry'ye kayıt
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${PRODUCT_NAME}" "DisplayName" "${PRODUCT_NAME} ${PRODUCT_VERSION}"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${PRODUCT_NAME}" "UninstallString" "$INSTDIR\\uninstall.exe"
    WriteRegStr HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${PRODUCT_NAME}" "DisplayVersion" "${PRODUCT_VERSION}"

    ; Kaldırma dosyası oluştur
    WriteUninstaller "$INSTDIR\\uninstall.exe"
SectionEnd

; Kaldırma Bölümü
Section "Uninstall"
    RMDir /r "$INSTDIR"
    RMDir /r "$SMPROGRAMS\\${PRODUCT_NAME}"
    Delete "$DESKTOP\\${PRODUCT_NAME}.lnk"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    DeleteRegKey HKLM "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\${PRODUCT_NAME}"
SectionEnd
'''

    def clean_build_files(self) -> bool:
        """Derleme dosyalarını temizle"""
        try:
            import shutil

            if self.build_dir.exists():
                shutil.rmtree(self.build_dir)
                logger.info("✅ Build dizini temizlendi")

            return True

        except Exception as e:
            logger.error(f"Temizleme hatası: {e}")
            return False

    def build_all(self) -> bool:
        """Tam derleme işlemi"""
        logger.info("=" * 50)
        logger.info("RAVN Desktop Uygulaması Derlemesi Başlanıyor")
        logger.info("=" * 50)

        # Gereklilik kontrolleri
        if not self.check_requirements():
            logger.error("Gerekli paketler yüklü değil")
            return False

        ffmpeg_available = self.check_ffmpeg()

        # Executable oluştur
        if not self.build_executable():
            logger.error("Executable oluşturma başarısız")
            return False

        # FFmpeg bundle et (isteğe bağlı)
        if ffmpeg_available:
            self.bundle_ffmpeg()

        # Installer oluştur (Windows)
        if platform_module.system() == "Windows":
            self.create_installer()

        logger.info("=" * 50)
        logger.info("✅ Derleme Başarıyla Tamamlandı!")
        logger.info(f"Çıktı: {self.dist_dir}")
        logger.info("=" * 50)

        return True


def main():
    """Ana giriş noktası"""
    import argparse

    parser = argparse.ArgumentParser(description="RAVN Desktop Uygulaması Derleyicisi")
    parser.add_argument('--project-root', help='Proje kök dizini')
    parser.add_argument('--build', action='store_true', help='Executable oluştur')
    parser.add_argument('--installer', action='store_true', help='Installer oluştur')
    parser.add_argument('--clean', action='store_true', help='Derleme dosyalarını temizle')
    parser.add_argument('--all', action='store_true', help='Tamamını derle')

    args = parser.parse_args()

    builder = AppBuilder(args.project_root)

    if args.clean:
        builder.clean_build_files()
    elif args.build:
        builder.build_executable()
    elif args.installer:
        builder.create_installer()
    elif args.all:
        builder.build_all()
    else:
        # Varsayılan olarak tamamını derle
        builder.build_all()


if __name__ == "__main__":
    main()
