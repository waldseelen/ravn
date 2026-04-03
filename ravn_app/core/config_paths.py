"""
RAVN - Config and Data Path Management
OS-aware configuration and data directory resolution with migration support.
"""

import os
import sys
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from ravn_app.core.theme_catalog import get_theme_ids, normalize_theme_id

logger = logging.getLogger(__name__)


def get_config_directory() -> Path:
    """
    Get the configuration directory based on OS.

    Returns:
        Path to config directory:
        - Windows: %APPDATA%/ravn/
        - macOS: ~/Library/Application Support/ravn/
        - Linux: ~/.config/ravn/
    """
    if sys.platform == 'win32':
        base_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        config_dir = base_dir / 'ravn'
    elif sys.platform == 'darwin':
        config_dir = Path.home() / 'Library' / 'Application Support' / 'ravn'
    else:  # Linux and others
        xdg_config = os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))
        config_dir = Path(xdg_config) / 'ravn'

    return config_dir


def get_data_directory() -> Path:
    """
    Get the data directory based on OS.

    Returns:
        Path to data directory:
        - Windows: %APPDATA%/ravn/data/
        - macOS: ~/Library/Application Support/ravn/data/
        - Linux: ~/.local/share/ravn/
    """
    if sys.platform == 'win32':
        base_dir = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        data_dir = base_dir / 'ravn' / 'data'
    elif sys.platform == 'darwin':
        data_dir = Path.home() / 'Library' / 'Application Support' / 'ravn' / 'data'
    else:  # Linux and others
        xdg_data = os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
        data_dir = Path(xdg_data) / 'ravn'

    return data_dir


def get_cache_directory() -> Path:
    """
    Get the cache directory based on OS.

    Returns:
        Path to cache directory:
        - Windows: %LOCALAPPDATA%/ravn/cache/
        - macOS: ~/Library/Caches/ravn/
        - Linux: ~/.cache/ravn/
    """
    if sys.platform == 'win32':
        base_dir = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        cache_dir = base_dir / 'ravn' / 'cache'
    elif sys.platform == 'darwin':
        cache_dir = Path.home() / 'Library' / 'Caches' / 'ravn'
    else:  # Linux and others
        xdg_cache = os.environ.get('XDG_CACHE_HOME', str(Path.home() / '.cache'))
        cache_dir = Path(xdg_cache) / 'ravn'

    return cache_dir


def get_config_file_path() -> Path:
    """Get the full path to the config file."""
    return get_config_directory() / 'ravn_config.json'


def get_database_file_path() -> Path:
    """Get the full path to the history database file."""
    return get_data_directory() / 'ravn_history.db'


def get_media_library_file_path() -> Path:
    """Get the full path to the Phase 7 media library database file."""
    return get_data_directory() / 'media_library.db'


def get_download_archive_file_path() -> Path:
    """Get the full path to the shared yt-dlp download archive file."""
    return get_data_directory() / 'download_archive.txt'


def ensure_directories_exist() -> Dict[str, Path]:
    """
    Create all required directories if they don't exist.

    Returns:
        Dict with paths to created directories
    """
    directories = {
        'config': get_config_directory(),
        'data': get_data_directory(),
        'cache': get_cache_directory(),
    }

    for name, path in directories.items():
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {path}")
        except Exception as e:
            logger.error(f"Failed to create {name} directory {path}: {e}")
            raise

    return directories


def find_legacy_config_file() -> Optional[Path]:
    """
    Find legacy config file in project root or current directory.

    Returns:
        Path to legacy config if found, None otherwise
    """
    # Check common legacy locations
    legacy_locations = [
        Path.cwd() / 'ravn_config.json',
        Path(__file__).parent.parent.parent / 'ravn_config.json',  # Project root
    ]

    for path in legacy_locations:
        if path.exists():
            return path

    return None


def find_legacy_database_file() -> Optional[Path]:
    """
    Find legacy database file in project root or current directory.

    Returns:
        Path to legacy database if found, None otherwise
    """
    legacy_locations = [
        Path.cwd() / 'ravn_history.db',
        Path(__file__).parent.parent.parent / 'ravn_history.db',  # Project root
    ]

    for path in legacy_locations:
        if path.exists():
            return path

    return None


def migrate_legacy_config() -> bool:
    """
    Migrate legacy config file from project root to config directory.

    Returns:
        True if migration was performed, False otherwise
    """
    legacy_path = find_legacy_config_file()
    new_path = get_config_file_path()

    if legacy_path is None:
        logger.debug("No legacy config file found")
        return False

    if new_path.exists():
        logger.debug(f"Config file already exists at {new_path}, skipping migration")
        return False

    try:
        ensure_directories_exist()
        shutil.copy2(legacy_path, new_path)
        logger.info(f"Migrated config from {legacy_path} to {new_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate config: {e}")
        return False


def migrate_legacy_database() -> bool:
    """
    Migrate legacy database file from project root to data directory.

    Returns:
        True if migration was performed, False otherwise
    """
    legacy_path = find_legacy_database_file()
    new_path = get_database_file_path()

    if legacy_path is None:
        logger.debug("No legacy database file found")
        return False

    if new_path.exists():
        logger.debug(f"Database file already exists at {new_path}, skipping migration")
        return False

    try:
        ensure_directories_exist()
        shutil.copy2(legacy_path, new_path)
        logger.info(f"Migrated database from {legacy_path} to {new_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to migrate database: {e}")
        return False


def migrate_all_legacy_files() -> Dict[str, bool]:
    """
    Migrate all legacy files on first run.

    Returns:
        Dict with migration status for each file type
    """
    return {
        'config': migrate_legacy_config(),
        'database': migrate_legacy_database(),
    }


# Config schema validation
CONFIG_SCHEMA = {
    'default_download_path': {'type': str, 'default': None},  # Will use ~/Downloads/RAVN
    'default_format': {'type': str, 'default': 'MP4', 'allowed': ['MP4', 'MKV', 'WEBM', 'AVI', 'MOV']},
    'default_quality': {'type': str, 'default': '1080p', 'allowed': ['360p', '480p', '720p', '1080p', '1440p', '2160p', 'best']},
    'theme': {'type': str, 'default': 'dark', 'allowed': get_theme_ids()},
    'concurrent_downloads': {'type': int, 'default': 1, 'min': 1, 'max': 5},
    'auto_cleanup': {'type': bool, 'default': False},
    'auto_update_check': {'type': bool, 'default': True},
    'ffmpeg_path': {'type': str, 'default': 'ffmpeg'},
    'language': {'type': str, 'default': 'tr', 'allowed': ['tr', 'en']},
    'notifications_enabled': {'type': bool, 'default': True},
    'history_limit': {'type': int, 'default': 1000, 'min': 100, 'max': 10000},
    'auto_subtitle_download': {'type': bool, 'default': False},
    'preferred_subtitle_language': {'type': str, 'default': 'tr'},
    'subtitle_fallback_language': {'type': str, 'default': 'en'},
    'subtitle_include_auto_generated': {'type': bool, 'default': True},
    'auto_embed_subtitles': {'type': bool, 'default': False},
    'auto_id3_tagging': {'type': bool, 'default': True},
    'auto_embed_lyrics': {'type': bool, 'default': True},
    'auto_sort_downloads': {'type': bool, 'default': False},
    'auto_sort_mode': {'type': str, 'default': 'artist', 'allowed': ['artist', 'channel']},
    'download_naming_preset': {'type': str, 'default': 'standard', 'allowed': ['standard', 'clean', 'playlist']},
    'download_filename_template': {'type': str, 'default': ''},
    'download_postprocess': {
        'type': dict,
        'default': {
            'extract_audio': False,
            'audio_format': 'mp3',
            'audio_bitrate': '192k',
            'convert_enabled': False,
            'convert_format': 'mkv',
            'embed_subtitles': False,
        },
    },
    'download_robustness': {
        'type': dict,
        'default': {
            'enable_archive': True,
            'detect_duplicates': True,
            'continue_partial': True,
            'format_fallback': True,
            'rate_limit_kbps': 0,
        },
    },
    'download_advanced': {
        'type': dict,
        'default': {
            'cookies_mode': 'none',
            'cookies_browser': 'chrome',
            'cookies_profile': '',
            'cookies_file': '',
            'concurrent_fragments': 1,
            'fragment_retries': 0,
            'socket_timeout_seconds': 0,
        },
    },
    'mixer': {
        'type': dict,
        'default': {
            'default_format': 'mp3',
            'default_bitrate': '320k',
            'crossfade_duration': 1.0,
            'normalize_audio': True,
            'video_codec': 'libx264',
            'video_preset': 'medium',
            'video_crf': 23,
            'temp_dir': 'temp_mixer',
        },
    },
    'library': {
        'type': dict,
        'default': {
            'library_db': 'media_library.db',
            'auto_thumbnail': True,
            'thumbnail_size': [160, 90],
            'max_search_results': 100,
            'auto_add_downloads': True,
            'auto_add_mixer_output': True,
            'auto_add_filter_output': True,
            'auto_add_converted_files': True,
        },
    },
    'filters': {
        'type': dict,
        'default': {
            'default_quality': 'high',
            'preview_enabled': True,
            'preview_scale': 0.5,
        },
    },
}


def get_default_config() -> Dict[str, Any]:
    """
    Get default configuration values.

    Returns:
        Dict with default config values
    """
    config = {}
    for key, schema in CONFIG_SCHEMA.items():
        if key == 'default_download_path' and schema['default'] is None:
            config[key] = str(Path.home() / 'Downloads' / 'RAVN')
        else:
            config[key] = deepcopy(schema['default'])
    return config


def validate_config_value(key: str, value: Any) -> tuple[bool, Any, str]:
    """
    Validate a single config value against the schema.

    Args:
        key: Config key
        value: Value to validate

    Returns:
        Tuple of (is_valid, corrected_value, error_message)
    """
    if key not in CONFIG_SCHEMA:
        return True, value, ""  # Unknown keys are allowed

    schema = CONFIG_SCHEMA[key]
    expected_type = schema['type']

    if key == 'theme' and isinstance(value, str):
        normalized = normalize_theme_id(value)
        if normalized != value:
            return False, normalized, f"Normalized legacy theme for {key}: {value} -> {normalized}"
        return True, normalized, ""

    # Type check
    if not isinstance(value, expected_type):
        default = deepcopy(schema['default'])
        if key == 'default_download_path' and default is None:
            default = str(Path.home() / 'Downloads' / 'RAVN')
        return False, default, f"Invalid type for {key}: expected {expected_type.__name__}"

    # Range check for integers
    if expected_type == int:
        if 'min' in schema and value < schema['min']:
            return False, schema['min'], f"{key} must be at least {schema['min']}"
        if 'max' in schema and value > schema['max']:
            return False, schema['max'], f"{key} must be at most {schema['max']}"

    # Allowed values check
    if 'allowed' in schema and value not in schema['allowed']:
        return False, deepcopy(schema['default']), f"Invalid value for {key}: must be one of {schema['allowed']}"

    return True, value, ""


def validate_config(config: Dict[str, Any]) -> tuple[Dict[str, Any], list[str]]:
    """
    Validate entire config against schema and apply defaults for missing keys.

    Args:
        config: Config dict to validate

    Returns:
        Tuple of (validated_config, list_of_errors)
    """
    errors = []
    validated = {}

    # Get defaults first
    defaults = get_default_config()

    # Validate provided values
    for key, value in config.items():
        is_valid, corrected, error = validate_config_value(key, value)
        if not is_valid:
            errors.append(error)
        validated[key] = corrected

    # Fill in missing keys with defaults
    for key, default_value in defaults.items():
        if key not in validated:
            validated[key] = default_value

    return validated, errors
