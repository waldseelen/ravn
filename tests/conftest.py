"""
Test konfigürasyonu ve fixtures
"""

import os
import sys
from unittest.mock import patch

import pytest

# Proje root'unu path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real_bundled_lookup: let the test see the real assets/ tree instead of the "
        "isolated default (for tests that exercise the lookup's own internals)",
    )


@pytest.fixture(autouse=True)
def isolate_bundled_tools(request):
    """
    Hide the repository's real ``assets/<tool>/<platform>/`` tree from tests.

    Without this, whether a test passes depends on whether someone has run
    ``build.ps1 -Action bundle-tools`` in this checkout: that downloads real
    ffmpeg/aria2c/yt-dlp binaries into ``assets/``, and since ``tool_health`` and the
    runners now prefer bundled copies, ~13 tests would flip to seeing an absolute
    packaged path where they assert a bare tool name.

    That is not hypothetical — ``build.ps1 -Action ci-package`` downloads the tools
    *before* it runs pytest, so the Windows release build would have failed on a tag
    push. Tests must not depend on build side effects, so the default here is
    "nothing is bundled"; tests that need otherwise set up their own roots (see
    tests/test_bundled_tools.py) or opt out with @pytest.mark.real_bundled_lookup.
    """
    if "real_bundled_lookup" in request.keywords:
        yield
        return

    with patch("ravn_app.utils.bundled_tools.candidate_runtime_roots", return_value=[]):
        yield


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
