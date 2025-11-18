"""
Dosya işlemleri - Adlandırma, boyut gibi
"""

import re
import os


def sanitize_filename(name):
    """
    Dosya adını temizle - geçersiz karakterleri kaldır
    
    Args:
        name (str): Temizlenecek dosya adı
    
    Returns:
        str: Temizlenmiş dosya adı
    """
    return re.sub(r'[\/*?:"<>|]', "", name)


def format_bytes(size):
    """
    Byte boyutunu insan okunur formata dönüştür
    
    Args:
        size (int/float): Byte cinsinden boyut
    
    Returns:
        str: Biçimlendirilmiş boyut (KB, MB, GB vb.)
    """
    if not isinstance(size, (int, float)):
        return ""
    
    power = 1024
    n = 0
    power_labels = {0: 'Bytes', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    
    while size >= power and n < len(power_labels) - 1:
        size /= power
        n += 1
    
    return f"({size:.2f} {power_labels[n]})"


def ensure_directory(path):
    """
    Dizinin var olduğundan emin ol
    
    Args:
        path (str): Dizin yolu
    """
    os.makedirs(path, exist_ok=True)


def get_file_size(path):
    """
    Dosya boyutunu al
    
    Args:
        path (str): Dosya yolu
    
    Returns:
        int: Dosya boyutu (byte)
    """
    if os.path.exists(path):
        return os.path.getsize(path)
    return 0
