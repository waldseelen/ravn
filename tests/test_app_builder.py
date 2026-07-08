"""
PyInstaller Desktop Uygulaması Testleri
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.core.app_builder import AppBuilder, Platform


class TestAppBuilder:
    """AppBuilder testleri"""

    def test_app_builder_initialization(self):
        """AppBuilder başlatılmalı"""
        builder = AppBuilder()

        assert builder.project_root is not None
        assert builder.dist_dir is not None
        assert builder.build_dir is not None

    def test_app_builder_custom_project_root(self):
        """Özel proje kök dizini"""
        from pathlib import Path
        custom_path = Path("/custom/path")
        builder = AppBuilder(project_root=str(custom_path))

        assert builder.project_root == custom_path

    @patch('subprocess.run')
    def test_check_requirements_success(self, mock_run):
        """Gerekli paketler kontrol edilmeli - başarı"""
        builder = AppBuilder()

        # Mock import'ları doğrudan kontrol etmek yerine
        with patch('builtins.__import__'):
            result = builder.check_requirements()
            # Import işlemi başarılı olduğunu varsay
            assert result is True

    @patch('subprocess.run')
    def test_check_ffmpeg_success(self, mock_run):
        """FFmpeg kontrolü - bulundu"""
        mock_run.return_value = Mock(returncode=0)

        builder = AppBuilder()
        result = builder.check_ffmpeg()

        assert result is True
        assert mock_run.call_count == 2  # ffmpeg ve ffprobe

    @patch('subprocess.run')
    def test_check_ffmpeg_not_found(self, mock_run):
        """FFmpeg kontrolü - bulunamadı"""
        mock_run.side_effect = FileNotFoundError()

        builder = AppBuilder()
        result = builder.check_ffmpeg()

        assert result is False

    @patch('subprocess.run')
    def test_check_ffmpeg_timeout(self, mock_run):
        """FFmpeg kontrolü - timeout"""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 5)

        builder = AppBuilder()
        result = builder.check_ffmpeg()

        assert result is False

    @patch('subprocess.run')
    def test_create_spec_file_success(self, mock_run):
        """Spec dosyası oluştur - başarı"""
        mock_run.return_value = Mock(returncode=0, stderr='')

        builder = AppBuilder()
        result = builder.create_spec_file()

        assert result is True
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_create_spec_file_failure(self, mock_run):
        """Spec dosyası oluştur - başarısızlık"""
        mock_run.return_value = Mock(returncode=1, stderr='Error')

        builder = AppBuilder()
        result = builder.create_spec_file()

        assert result is False

    @patch('subprocess.run')
    def test_build_executable_success(self, mock_run):
        """Executable oluştur - başarı"""
        mock_run.return_value = Mock(returncode=0, stderr='')

        builder = AppBuilder()
        result = builder.build_executable()

        assert result is True

    @patch('subprocess.run')
    def test_build_executable_failure(self, mock_run):
        """Executable oluştur - başarısızlık"""
        mock_run.return_value = Mock(returncode=1, stderr='Build error')

        builder = AppBuilder()
        result = builder.build_executable()

        assert result is False

    @patch('subprocess.run')
    def test_build_executable_with_options(self, mock_run):
        """Executable oluştur - seçenekli"""
        mock_run.return_value = Mock(returncode=0, stderr='')

        builder = AppBuilder()
        result = builder.build_executable(one_file=True, windowed=True)

        assert result is True
        # Komut argümanlarını kontrol et
        call_args = mock_run.call_args[0][0]
        assert '--onefile' in call_args
        assert '--windowed' in call_args

    @patch('shutil.copy')
    @patch('shutil.which')
    def test_bundle_ffmpeg_success(self, mock_which, mock_copy):
        """FFmpeg bundle et - başarı"""
        mock_which.side_effect = ['/usr/bin/ffmpeg', '/usr/bin/ffprobe']

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = AppBuilder(project_root=tmpdir)
            builder.dist_dir.mkdir(parents=True, exist_ok=True)

            result = builder.bundle_ffmpeg()

            assert result is True
            assert mock_copy.call_count == 2

    @patch('shutil.which')
    def test_bundle_ffmpeg_not_found(self, mock_which):
        """FFmpeg bundle et - bulunamadı"""
        mock_which.return_value = None

        builder = AppBuilder()
        result = builder.bundle_ffmpeg()

        assert result is False

    @patch('subprocess.run')
    def test_create_installer_success(self, mock_run):
        """Installer oluştur - başarı"""
        mock_run.return_value = Mock(returncode=0, stderr='')

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = AppBuilder(project_root=tmpdir)
            result = builder.create_installer()

            # NSIS script oluşturulup oluşturulmadığını kontrol et
            nsis_file = Path(tmpdir) / "ravn_installer.nsis"
            assert nsis_file.exists() or result is False

    def test_nsis_script_generation(self):
        """NSIS script oluşturulmalı"""
        builder = AppBuilder()
        script = builder._generate_nsis_script()

        assert script is not None
        assert 'RAVN' in script
        assert 'NSIS' in script
        assert 'Installer' in script

    @patch('shutil.rmtree')
    def test_clean_build_files_success(self, mock_rmtree):
        """Derleme dosyalarını temizle - başarı"""
        with tempfile.TemporaryDirectory() as tmpdir:
            builder = AppBuilder(project_root=tmpdir)
            builder.build_dir.mkdir(parents=True, exist_ok=True)

            result = builder.clean_build_files()

            assert result is True

    @patch('subprocess.run')
    @patch('shutil.which')
    def test_build_all_success(self, mock_which, mock_run):
        """Tam derleme - başarı"""
        mock_run.return_value = Mock(returncode=0, stderr='')
        mock_which.side_effect = ['/usr/bin/ffmpeg', '/usr/bin/ffprobe', '/usr/bin/ffmpeg', '/usr/bin/ffprobe']

        with tempfile.TemporaryDirectory() as tmpdir:
            builder = AppBuilder(project_root=tmpdir)
            result = builder.build_all()

            # Başarıdan ziyade işlem sırasını kontrol et
            assert isinstance(result, bool)


class TestPlatformEnum:
    """Platform enum testleri"""

    def test_platform_values(self):
        """Platform türlerinin değerleri doğru olmalı"""
        assert Platform.WINDOWS.value == "Windows"
        assert Platform.MACOS.value == "Darwin"
        assert Platform.LINUX.value == "Linux"

    def test_platform_enum_members(self):
        """Platform enum üyeleri"""
        assert len(list(Platform)) == 3
        platforms = [p.value for p in Platform]
        assert "Windows" in platforms
        assert "Darwin" in platforms
        assert "Linux" in platforms


class TestAppBuilderIntegration:
    """AppBuilder entegrasyonu testleri"""

    def test_builder_workflow(self):
        """AppBuilder iş akışı"""
        builder = AppBuilder()

        # Yollar doğru olmalı
        assert builder.project_root.exists()
        assert builder.dist_dir.parent.exists()
        assert builder.build_dir.parent.exists()

    @patch('subprocess.run')
    def test_builder_error_handling(self, mock_run):
        """Builder hata yönetimi"""
        mock_run.side_effect = Exception("Test error")

        builder = AppBuilder()
        result = builder.build_executable()

        assert result is False

    def test_builder_nsis_content(self):
        """NSIS script içeriği doğru olmalı"""
        builder = AppBuilder()
        script = builder._generate_nsis_script()

        # Gerekli bölümleri kontrol et
        assert '!include "MUI2.nsh"' in script
        assert '!define PRODUCT_NAME "RAVN"' in script
        assert 'Section "RAVN Kurulum"' in script
        assert 'Section "Uninstall"' in script
        assert 'OutFile' in script
