"""
ravn_app/api/deps.py — Shared FastAPI dependency providers.

All routers import from here to get singleton service instances.
No business logic lives here; this file only manages object lifetimes so that
routers stay free of global state.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from ravn_app.core.database import ConfigManager, DatabaseManager
from ravn_app.core.downloader import YouTubeDownloader
from ravn_app.core.persistence.media_library import MediaLibrary
from ravn_app.core.task_manager import TaskQueue, get_task_queue
from ravn_app.utils.bundled_tools import find_tool
from ravn_app.utils.metadata_handler import MetadataHandler

# ---------------------------------------------------------------------------
# Tool-path resolution (reuses the same lookup chain as the desktop runtime)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _ytdlp_path() -> str:
    return find_tool("yt-dlp") or "yt-dlp"


@lru_cache(maxsize=1)
def _ffmpeg_path() -> str:
    return find_tool("ffmpeg") or "ffmpeg"


@lru_cache(maxsize=1)
def _ffprobe_path() -> str:
    return find_tool("ffprobe") or "ffprobe"


# ---------------------------------------------------------------------------
# Singleton service factories
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _downloader() -> YouTubeDownloader:
    return YouTubeDownloader(
        ytdlp_path=_ytdlp_path(),
        ffmpeg_path=_ffmpeg_path(),
        ffprobe_path=_ffprobe_path(),
    )


@lru_cache(maxsize=1)
def _db_manager() -> DatabaseManager:
    return DatabaseManager()


@lru_cache(maxsize=1)
def _config_manager() -> ConfigManager:
    return ConfigManager()


@lru_cache(maxsize=1)
def _task_queue() -> TaskQueue:
    return get_task_queue(max_concurrent=2)


# ---------------------------------------------------------------------------
# FastAPI dependency callables (used with Depends())
# ---------------------------------------------------------------------------

def get_downloader() -> YouTubeDownloader:
    return _downloader()


def get_db() -> DatabaseManager:
    return DatabaseManager()


def get_config() -> ConfigManager:
    return _config_manager()


def get_queue() -> TaskQueue:
    return _task_queue()


def get_library() -> MediaLibrary:
    metadata_handler = MetadataHandler(ffmpeg_path=_ffmpeg_path())
    return MediaLibrary(metadata_handler=metadata_handler)


# Typed shortcuts for cleaner router signatures
DownloaderDep = Annotated[YouTubeDownloader, Depends(get_downloader)]
DbDep = Annotated[DatabaseManager, Depends(get_db)]
ConfigDep = Annotated[ConfigManager, Depends(get_config)]
QueueDep = Annotated[TaskQueue, Depends(get_queue)]
LibraryDep = Annotated[MediaLibrary, Depends(get_library)]

