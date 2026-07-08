"""
Sistem işlemleri - Executables, platform algılama
"""

import os
import sys
from shutil import which

from ravn_app.core.runners.ffmpeg import FFmpegRunner


def find_executable(name):
    """
    Executable'ı bul - yerel veya sistem PATH'inde

    Args:
        name (str): Program adı (ör: "ffmpeg")

    Returns:
        str: Executable yolu veya None
    """
    executable_name = f"{name}.exe" if sys.platform == "win32" else name

    # Script dizininde ara
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    local_path = os.path.join(script_dir, executable_name)
    if os.path.exists(local_path):
        return local_path

    # Sistem PATH'inde ara
    return which(name)


def is_ffmpeg_available():
    """
    FFmpeg kurulu mu kontrol et

    Returns:
        bool: FFmpeg mevcut mu
    """
    return find_executable("ffmpeg") is not None


def get_ffmpeg_version():
    """
    FFmpeg versiyonunu al

    Returns:
        str: FFmpeg versiyonu veya None
    """
    return FFmpegRunner().get_version()


def get_platform():
    """
    İşletim sistemi bilgisi

    Returns:
        str: Platform adı ("windows", "darwin", "linux")
    """
    if sys.platform == "win32":
        return "windows"
    elif sys.platform == "darwin":
        return "darwin"
    else:
        return "linux"
