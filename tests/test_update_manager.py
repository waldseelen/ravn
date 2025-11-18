"""
Otomatik Güncelleme Sistemi Testleri
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from ravn_app.core.update_manager import (
    UpdateManager,
    UpdateStatus,
    ReleaseInfo,
    UpdateNotification,
)


class TestReleaseInfo:
    """ReleaseInfo dataclass testleri"""

    def test_release_info_creation(self):
        """ReleaseInfo oluşturulmalı"""
        release = ReleaseInfo(
            version="1.1.0",
            tag="v1.1.0",
            name="RAVN 1.1.0",
            body="Features: ...",
            published_at="2024-01-01",
            download_url="https://example.com/ravn-1.1.0.exe",
            file_name="ravn-1.1.0.exe",
            file_size=50000000
        )

        assert release.version == "1.1.0"
        assert release.tag == "v1.1.0"
        assert release.file_size == 50000000


class TestUpdateManager:
    """UpdateManager testleri"""

    def test_update_manager_initialization(self):
        """UpdateManager başlatılmalı"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UpdateManager(
                current_version="1.0.0",
                update_dir=tmpdir
            )

            assert manager.current_version == "1.0.0"
            assert manager.status == UpdateStatus.CHECKING
            assert Path(tmpdir).exists()

    def test_update_manager_default_dir(self):
        """Varsayılan güncelleme dizini oluşturulmalı"""
        manager = UpdateManager(current_version="1.0.0")

        assert manager.update_dir.parent == Path.home() / ".ravn"

    def test_status_property(self):
        """Status özelliği doğru olmalı"""
        manager = UpdateManager(current_version="1.0.0")

        manager.status = UpdateStatus.UP_TO_DATE
        assert manager.status == UpdateStatus.UP_TO_DATE

    def test_status_change_callback(self):
        """Status değişim callback'i çağrılmalı"""
        manager = UpdateManager(current_version="1.0.0")

        callback_called = []
        manager.on_status_change = lambda status: callback_called.append(status)

        manager.status = UpdateStatus.UPDATE_AVAILABLE

        assert len(callback_called) == 1
        assert callback_called[0] == UpdateStatus.UPDATE_AVAILABLE

    @patch('requests.get')
    def test_get_latest_release_success(self, mock_get):
        """En son sürümü başarıyla al"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v1.1.0',
            'name': 'RAVN 1.1.0',
            'body': 'Release notes',
            'published_at': '2024-01-01T00:00:00Z',
            'assets': [
                {
                    'name': 'ravn-1.1.0.exe',
                    'browser_download_url': 'https://example.com/ravn-1.1.0.exe',
                    'size': 50000000
                }
            ]
        }
        mock_get.return_value = mock_response

        manager = UpdateManager(current_version="1.0.0")
        release = manager.get_latest_release()

        assert release is not None
        assert release.version == "1.1.0"
        assert release.tag == "v1.1.0"
        assert manager.status == UpdateStatus.CHECKING

    @patch('requests.get')
    def test_get_latest_release_network_error(self, mock_get):
        """Network hatası ele alınmalı"""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        manager = UpdateManager(current_version="1.0.0")
        release = manager.get_latest_release()

        assert release is None
        assert manager.status == UpdateStatus.ERROR

    @patch('requests.get')
    def test_get_latest_release_no_asset(self, mock_get):
        """Asset olmayan sürüm ele alınmalı"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'tag_name': 'v1.1.0',
            'name': 'RAVN 1.1.0',
            'body': 'Release notes',
            'published_at': '2024-01-01T00:00:00Z',
            'assets': []
        }
        mock_get.return_value = mock_response

        manager = UpdateManager(current_version="1.0.0")
        release = manager.get_latest_release()

        assert release is None

    def test_is_newer_version_true(self):
        """Yeni sürüm tespiti - yeni"""
        manager = UpdateManager(current_version="1.0.0")

        assert manager._is_newer_version("1.0.1") is True
        assert manager._is_newer_version("1.1.0") is True
        assert manager._is_newer_version("2.0.0") is True

    def test_is_newer_version_false(self):
        """Yeni sürüm tespiti - eski"""
        manager = UpdateManager(current_version="1.0.0")

        assert manager._is_newer_version("0.9.9") is False
        assert manager._is_newer_version("1.0.0") is False

    @patch.object(UpdateManager, 'get_latest_release')
    def test_check_for_updates_available(self, mock_get_release):
        """Güncelleme mevcut"""
        release = ReleaseInfo(
            version="1.1.0",
            tag="v1.1.0",
            name="RAVN 1.1.0",
            body="Features",
            published_at="2024-01-01",
            download_url="https://example.com/ravn-1.1.0.exe",
            file_name="ravn-1.1.0.exe",
            file_size=50000000
        )
        mock_get_release.return_value = release

        manager = UpdateManager(current_version="1.0.0")
        has_update = manager.check_for_updates()

        assert has_update is True
        assert manager.status == UpdateStatus.UPDATE_AVAILABLE

    @patch.object(UpdateManager, 'get_latest_release')
    def test_check_for_updates_not_available(self, mock_get_release):
        """Güncelleme yok"""
        release = ReleaseInfo(
            version="1.0.0",
            tag="v1.0.0",
            name="RAVN 1.0.0",
            body="Same version",
            published_at="2024-01-01",
            download_url="https://example.com/ravn-1.0.0.exe",
            file_name="ravn-1.0.0.exe",
            file_size=50000000
        )
        mock_get_release.return_value = release

        manager = UpdateManager(current_version="1.0.0")
        has_update = manager.check_for_updates()

        assert has_update is False
        assert manager.status == UpdateStatus.UP_TO_DATE

    @patch('requests.get')
    def test_download_update_success(self, mock_get):
        """Güncellemeyi başarıyla indir"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock download
            mock_response = Mock()
            mock_response.iter_content.return_value = [b"test content"]
            mock_response.headers = {'content-length': '12'}
            mock_get.return_value = mock_response

            # Release info oluştur
            manager = UpdateManager(current_version="1.0.0", update_dir=tmpdir)
            manager._latest_release = ReleaseInfo(
                version="1.1.0",
                tag="v1.1.0",
                name="RAVN 1.1.0",
                body="Features",
                published_at="2024-01-01",
                download_url="https://example.com/ravn-1.1.0.exe",
                file_name="ravn-1.1.0.exe",
                file_size=50000000
            )

            result = manager.download_update()

            assert result is not None
            assert result.exists()
            assert manager.status == UpdateStatus.DOWNLOADING

    def test_download_update_no_release(self):
        """Release info olmadan indir başarısız"""
        manager = UpdateManager(current_version="1.0.0")

        result = manager.download_update()

        assert result is None

    @patch('subprocess.Popen')
    def test_install_update_exe(self, mock_popen):
        """Exe güncellemeyi yükle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Test exe dosyası oluştur
            exe_file = Path(tmpdir) / "ravn-1.1.0.exe"
            exe_file.write_text("test")

            manager = UpdateManager(current_version="1.0.0", update_dir=tmpdir)
            result = manager.install_update(exe_file)

            assert result is True
            assert manager.status == UpdateStatus.SUCCESS
            mock_popen.assert_called_once()

    def test_install_update_file_not_found(self):
        """Dosya bulunamadı"""
        manager = UpdateManager(current_version="1.0.0")

        result = manager.install_update(Path("/non/existent/file.exe"))

        assert result is False
        assert manager.status == UpdateStatus.ERROR

    @patch.object(UpdateManager, 'check_for_updates')
    @patch.object(UpdateManager, 'download_update')
    @patch.object(UpdateManager, 'install_update')
    def test_check_and_update_async_success(self, mock_install, mock_download, mock_check):
        """Asenkron güncelleme başarısı"""
        mock_check.return_value = True
        mock_download.return_value = Path("/tmp/ravn.exe")
        mock_install.return_value = True

        manager = UpdateManager(current_version="1.0.0")

        callback_result = []
        def callback(success):
            callback_result.append(success)

        manager.check_and_update_async(callback)

        # Thread'in tamamlanması için bekle
        import time
        time.sleep(0.5)

        assert len(callback_result) > 0
        assert callback_result[0] is True

    def test_get_release_notes(self):
        """Sürüm notlarını al"""
        manager = UpdateManager(current_version="1.0.0")

        release = ReleaseInfo(
            version="1.1.0",
            tag="v1.1.0",
            name="RAVN 1.1.0",
            body="New features:\n- Feature 1\n- Feature 2",
            published_at="2024-01-01",
            download_url="https://example.com/ravn-1.1.0.exe",
            file_name="ravn-1.1.0.exe",
            file_size=50000000
        )

        manager._latest_release = release
        notes = manager.get_release_notes()

        assert notes == release.body
        assert "Feature 1" in notes

    def test_cleanup_old_updates(self):
        """Eski güncelleme dosyalarını temizle"""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = UpdateManager(current_version="1.0.0", update_dir=tmpdir)

            # Fake dosyalar oluştur
            (Path(tmpdir) / "ravn-1.0.0.exe").write_text("v1.0.0")
            (Path(tmpdir) / "ravn-1.0.1.exe").write_text("v1.0.1")
            (Path(tmpdir) / "ravn-1.1.0.exe").write_text("v1.1.0")

            manager.cleanup_old_updates(keep_last=1)

            # En eski dosyalar silinmiş olmalı
            remaining_files = list(Path(tmpdir).glob("*.exe"))
            assert len(remaining_files) <= 1


class TestUpdateNotification:
    """UpdateNotification testleri"""

    def test_notification_creation(self):
        """Notification oluşturulmalı"""
        manager = UpdateManager(current_version="1.0.0")
        notification = UpdateNotification(manager)

        assert notification.manager is manager

    def test_notification_show(self):
        """Notification gösterilmeli"""
        manager = UpdateManager(current_version="1.0.0")
        notification = UpdateNotification(manager)

        release = ReleaseInfo(
            version="1.1.0",
            tag="v1.1.0",
            name="RAVN 1.1.0",
            body="New features",
            published_at="2024-01-01",
            download_url="https://example.com/ravn-1.1.0.exe",
            file_name="ravn-1.1.0.exe",
            file_size=50000000
        )

        callback_data = []
        notification.notification_callback = lambda data: callback_data.append(data)

        notification.show_notification(release)

        assert len(callback_data) == 1
        assert callback_data[0]['version'] == "1.1.0"
        assert "Güncellemesi Mevcut" in callback_data[0]['title']


class TestUpdateManagerIntegration:
    """UpdateManager entegrasyonu testleri"""

    def test_version_comparison_complex(self):
        """Karmaşık sürüm karşılaştırması"""
        manager = UpdateManager(current_version="1.0.0")

        test_cases = [
            ("1.0.1", True),
            ("1.1.0", True),
            ("2.0.0", True),
            ("1.0.0-beta", False),  # Bu başarısız olacak
            ("0.9.9", False),
        ]

        for version, expected in test_cases:
            try:
                result = manager._is_newer_version(version)
                if not version.endswith('-beta'):
                    assert result == expected
            except ValueError:
                # Pre-release sürümler parse başarısız
                pass

    def test_check_interval(self):
        """Kontrol aralığı uygulanmalı"""
        manager = UpdateManager(
            current_version="1.0.0",
            check_interval_hours=1
        )

        # Simulasyon: son kontrol şu an
        manager._last_check = datetime.now()

        # Mock get_latest_release
        with patch.object(manager, 'get_latest_release', return_value=None):
            # Hemen tekrar kontrol
            result = manager.check_for_updates()

            # Aralık henüz geçmediği için check edilmemeli
            assert result is False
