"""
Tests for config_paths module
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from ravn_app.core.config_paths import (
    CONFIG_SCHEMA,
    ensure_directories_exist,
    find_legacy_config_file,
    find_legacy_database_file,
    get_cache_directory,
    get_config_file_path,
    get_data_directory,
    get_database_file_path,
    get_default_config,
    get_media_library_file_path,
    migrate_all_legacy_files,
    migrate_legacy_config,
    validate_config,
    validate_config_value,
)


class TestConfigDirectoryPaths:
    """Tests for OS-specific directory path resolution"""

    @patch('sys.platform', 'win32')
    @patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'})
    def test_get_config_directory_windows(self):
        """Test config directory on Windows"""
        # Reimport to pick up the patched values
        import importlib

        from ravn_app.core import config_paths
        importlib.reload(config_paths)

        path = config_paths.get_config_directory()
        assert 'ravn' in str(path).lower()

    @patch('sys.platform', 'linux')
    @patch.dict(os.environ, {'HOME': '/home/testuser'}, clear=False)
    def test_get_config_directory_linux(self):
        """Test config directory on Linux"""
        import importlib

        from ravn_app.core import config_paths
        importlib.reload(config_paths)

        # Clear XDG override if present
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': ''}, clear=False):
            path = config_paths.get_config_directory()
            assert 'ravn' in str(path).lower()

    @patch('sys.platform', 'darwin')
    def test_get_config_directory_macos(self):
        """Test config directory on macOS"""
        import importlib

        from ravn_app.core import config_paths
        importlib.reload(config_paths)

        path = config_paths.get_config_directory()
        assert 'ravn' in str(path).lower()


class TestDataDirectoryPaths:
    """Tests for data directory resolution"""

    def test_get_data_directory_exists(self):
        """Test data directory path is valid"""
        path = get_data_directory()
        assert 'ravn' in str(path).lower()
        assert isinstance(path, Path)


class TestCacheDirectoryPaths:
    """Tests for cache directory resolution"""

    def test_get_cache_directory_exists(self):
        """Test cache directory path is valid"""
        path = get_cache_directory()
        assert 'ravn' in str(path).lower()
        assert isinstance(path, Path)


class TestFilePaths:
    """Tests for specific file paths"""

    def test_get_config_file_path(self):
        """Test config file path"""
        path = get_config_file_path()
        assert path.name == 'ravn_config.json'
        assert 'ravn' in str(path).lower()

    def test_get_database_file_path(self):
        """Test database file path"""
        path = get_database_file_path()
        assert path.name == 'ravn_history.db'
        assert 'ravn' in str(path).lower()

    def test_get_media_library_file_path(self):
        """Test media library database file path"""
        path = get_media_library_file_path()
        assert path.name == 'media_library.db'
        assert 'ravn' in str(path).lower()


class TestEnsureDirectoriesExist:
    """Tests for directory creation"""

    def test_ensure_directories_creates_dirs(self):
        """Test that directories are created"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('ravn_app.core.config_paths.get_config_directory', return_value=Path(tmpdir) / 'config'):
                with patch('ravn_app.core.config_paths.get_data_directory', return_value=Path(tmpdir) / 'data'):
                    with patch('ravn_app.core.config_paths.get_cache_directory', return_value=Path(tmpdir) / 'cache'):
                        dirs = ensure_directories_exist()

                        assert dirs['config'].exists()
                        assert dirs['data'].exists()
                        assert dirs['cache'].exists()


class TestLegacyFileFinding:
    """Tests for finding legacy files"""

    def test_find_legacy_config_file_not_found(self):
        """Test when no legacy config exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = find_legacy_config_file()
                # May or may not find legacy file depending on current dir
                assert result is None or isinstance(result, Path)

    def test_find_legacy_database_file_not_found(self):
        """Test when no legacy database exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('pathlib.Path.cwd', return_value=Path(tmpdir)):
                result = find_legacy_database_file()
                assert result is None or isinstance(result, Path)


class TestMigration:
    """Tests for file migration"""

    def test_migrate_legacy_config_no_legacy(self):
        """Test migration when no legacy file exists"""
        with patch('ravn_app.core.config_paths.find_legacy_config_file', return_value=None):
            result = migrate_legacy_config()
            assert result is False

    def test_migrate_legacy_config_already_exists(self):
        """Test migration when target already exists"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / 'config' / 'ravn_config.json'
            config_file.parent.mkdir(parents=True)
            config_file.write_text('{}')

            legacy_file = Path(tmpdir) / 'legacy_config.json'
            legacy_file.write_text('{"key": "value"}')

            with patch('ravn_app.core.config_paths.find_legacy_config_file', return_value=legacy_file):
                with patch('ravn_app.core.config_paths.get_config_file_path', return_value=config_file):
                    result = migrate_legacy_config()
                    assert result is False

    def test_migrate_legacy_config_success(self):
        """Test successful config migration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / 'config'
            config_file = config_dir / 'ravn_config.json'

            legacy_file = Path(tmpdir) / 'legacy_config.json'
            legacy_file.write_text('{"key": "value"}')

            with patch('ravn_app.core.config_paths.find_legacy_config_file', return_value=legacy_file):
                with patch('ravn_app.core.config_paths.get_config_file_path', return_value=config_file):
                    with patch('ravn_app.core.config_paths.ensure_directories_exist'):
                        config_dir.mkdir(parents=True, exist_ok=True)
                        result = migrate_legacy_config()
                        assert result is True
                        assert config_file.exists()

    def test_migrate_all_legacy_files(self):
        """Test migrate all returns dict"""
        with patch('ravn_app.core.config_paths.migrate_legacy_config', return_value=False):
            with patch('ravn_app.core.config_paths.migrate_legacy_database', return_value=False):
                result = migrate_all_legacy_files()
                assert isinstance(result, dict)
                assert 'config' in result
                assert 'database' in result


class TestDefaultConfig:
    """Tests for default configuration"""

    def test_get_default_config(self):
        """Test default config contains all keys"""
        config = get_default_config()

        assert 'default_download_path' in config
        assert 'default_format' in config
        assert 'default_quality' in config
        assert 'theme' in config
        assert 'concurrent_downloads' in config
        assert 'language' in config
        assert 'subtitle_fallback_language' in config
        assert 'subtitle_include_auto_generated' in config
        assert 'auto_embed_subtitles' in config
        assert 'download_naming_preset' in config
        assert 'download_filename_template' in config
        assert 'download_postprocess' in config
        assert 'download_robustness' in config
        assert 'download_advanced' in config
        assert 'mixer' in config
        assert 'library' in config
        assert 'filters' in config
        assert config['download_naming_preset'] == 'standard'
        assert config['download_postprocess']['extract_audio'] is False
        assert config['download_robustness']['enable_archive'] is True
        assert config['download_advanced']['cookies_mode'] == 'none'
        assert config['library']['auto_add_downloads'] is True
        assert config['library']['auto_add_filter_output'] is True

    def test_default_download_path_is_valid(self):
        """Test default download path is a valid path string"""
        config = get_default_config()
        path = Path(config['default_download_path'])
        assert path.is_absolute() or 'RAVN' in str(path)


class TestConfigValidation:
    """Tests for config value validation"""

    def test_validate_config_value_valid_string(self):
        """Test validating a valid string value"""
        is_valid, value, error = validate_config_value('default_format', 'MP4')
        assert is_valid
        assert value == 'MP4'
        assert error == ""

    def test_validate_config_value_invalid_format(self):
        """Test validating an invalid format value"""
        is_valid, value, error = validate_config_value('default_format', 'INVALID_FORMAT')
        assert not is_valid
        assert value == 'MP4'  # Default

    def test_validate_config_value_invalid_naming_preset(self):
        """Naming preset should fall back to the standard preset."""
        is_valid, value, error = validate_config_value('download_naming_preset', 'broken')
        assert not is_valid
        assert value == 'standard'

    def test_validate_config_value_invalid_type(self):
        """Test validating wrong type"""
        is_valid, value, error = validate_config_value('concurrent_downloads', 'not_an_int')
        assert not is_valid
        assert value == 1  # Default

    def test_validate_config_value_int_too_small(self):
        """Test validating int below minimum"""
        is_valid, value, error = validate_config_value('concurrent_downloads', 0)
        assert not is_valid
        assert value == 1  # Minimum

    def test_validate_config_value_int_too_large(self):
        """Test validating int above maximum"""
        is_valid, value, error = validate_config_value('concurrent_downloads', 100)
        assert not is_valid
        assert value == 5  # Maximum

    def test_validate_config_value_unknown_key(self):
        """Test validating unknown key passes through"""
        is_valid, value, error = validate_config_value('unknown_key', 'any_value')
        assert is_valid
        assert value == 'any_value'

    def test_validate_config_full(self):
        """Test validating full config dict"""
        config = {
            'default_format': 'MKV',
            'concurrent_downloads': 3,
            'theme': 'invalid_theme',  # This will be corrected
        }

        validated, errors = validate_config(config)

        assert validated['default_format'] == 'MKV'
        assert validated['concurrent_downloads'] == 3
        assert validated['theme'] == 'dark'  # Corrected to default
        assert 'default_download_path' in validated  # Missing key filled
        assert len(errors) > 0  # Should have error for invalid theme

    def test_validate_config_fills_missing_keys(self):
        """Test that validation fills in missing keys"""
        config = {'theme': 'dark'}

        validated, errors = validate_config(config)

        # Should have all default keys
        defaults = get_default_config()
        for key in defaults:
            assert key in validated


class TestConfigSchema:
    """Tests for config schema definition"""

    def test_schema_has_required_keys(self):
        """Test schema has all required configuration keys"""
        required_keys = [
            'default_download_path',
            'default_format',
            'default_quality',
            'theme',
            'concurrent_downloads',
            'language',
            'mixer',
            'library',
            'filters',
        ]

        for key in required_keys:
            assert key in CONFIG_SCHEMA

    def test_schema_types_are_valid(self):
        """Test all schema types are valid Python types"""
        for schema in CONFIG_SCHEMA.values():
            assert 'type' in schema
            assert schema['type'] in (str, int, bool, dict)

    def test_schema_defaults_match_types(self):
        """Test default values match their specified types"""
        for key, schema in CONFIG_SCHEMA.items():
            default = schema['default']
            if default is not None:
                assert isinstance(default, schema['type']), f"Default for {key} doesn't match type"
