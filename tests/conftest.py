"""
Test konfigürasyonu ve fixtures
"""

import os
import sys

import pytest

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def sample_filenames():
    """Test için örnek dosya adları"""
    return [
        'normal_file.mp4',
        'file with spaces.mkv',
        'file-with-dashes.webm',
        'file_with_underscores.avi',
        'UPPERCASE.MKV',
        'mixed_Case.Mp4',
    ]


@pytest.fixture
def invalid_filenames():
    """Test için geçersiz dosya adları"""
    return [
        'file*name.txt',
        'file?test.mp4',
        'file:name.doc',
        'file"name".docx',
        'file|pipe.avi',
        'file<angle>.mkv',
        'file>bracket.webm',
    ]


@pytest.fixture
def byte_sizes():
    """Test için byte boyutları"""
    return {
        1: "1.00 Bytes",
        1024: "KB",
        1024 * 1024: "MB",
        1024 * 1024 * 1024: "GB",
    }
