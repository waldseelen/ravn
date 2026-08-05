"""
ravn_app/api/routers/downloads.py — Download acquisition endpoints.

Provides request/response HTTP endpoints for starting, inspecting, and
managing download operations.  Real-time progress is streamed via the
WebSocket at /ws/events, not through these endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ravn_app.api.deps import ConfigDep, DbDep, DownloaderDep, QueueDep
from ravn_app.core.downloader import (
    DownloadAdvancedProfile,
    DownloadFormat,
    DownloadPostProcessProfile,
    DownloadQuality,
    DownloadRequest,
    DownloadRobustnessProfile,
    YouTubeDownloader,
)
from ravn_app.core.task_manager import TaskType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/downloads", tags=["downloads"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class DownloadStartRequest(BaseModel):
    url: str = Field(..., description="Media URL to download")
    output_dir: str = Field(..., description="Absolute path to the output directory")
    format: str = Field("mp4", description="Output container format, e.g. mp4, mp3, mkv")
    quality: str = Field("best", description="Quality preset: best, 1080p, 720p, 480p, audio")
    embed_metadata: bool = True
    embed_lyrics: bool = True
    audio_bitrate: Optional[str] = None
    naming_preset: str = "standard"
    filename_template: Optional[str] = None
    auto_subtitle_download: bool = False
    preferred_subtitle_language: str = "tr"


class VideoInfoRequest(BaseModel):
    url: str = Field(..., description="Media URL to inspect")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FORMAT_MAP: Dict[str, DownloadFormat] = {
    f.name.lower(): f for f in DownloadFormat
}
_FORMAT_MAP.update({f.extension: f for f in DownloadFormat})

_QUALITY_MAP: Dict[str, DownloadQuality] = {
    "best": DownloadQuality.BEST,
    "1080p": DownloadQuality.HIGH_1080P,
    "720p": DownloadQuality.MEDIUM_720P,
    "480p": DownloadQuality.LOW_480P,
    "audio": DownloadQuality.AUDIO_ONLY,
}


def _resolve_format(fmt: str) -> DownloadFormat:
    resolved = _FORMAT_MAP.get(fmt.lower())
    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown format '{fmt}'. Valid values: {list(_FORMAT_MAP.keys())}",
        )
    return resolved


def _resolve_quality(quality: str) -> DownloadQuality:
    resolved = _QUALITY_MAP.get(quality.lower())
    if resolved is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown quality '{quality}'. Valid values: {list(_QUALITY_MAP.keys())}",
        )
    return resolved


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/info", summary="Extract video metadata without downloading")
def get_video_info(body: VideoInfoRequest, downloader: DownloaderDep) -> Dict[str, Any]:
    """
    Return title, duration, thumbnail, formats, and quality estimates for a URL.
    Runs synchronously; may take a few seconds for the yt-dlp call.
    """
    info = downloader.extract_video_info(body.url)
    if info is None:
        raise HTTPException(status_code=422, detail="Could not extract video info for the given URL")
    return info


@router.post("/start", summary="Enqueue a new download", status_code=202)
def start_download(
    body: DownloadStartRequest,
    downloader: DownloaderDep,
    queue: QueueDep,
) -> Dict[str, Any]:
    """
    Enqueue a download task.  Returns immediately with a task_id; use
    GET /queue/{task_id} to poll status or subscribe to /ws/events for
    real-time progress.
    """
    dl_format = _resolve_format(body.format)
    dl_quality = _resolve_quality(body.quality)

    request = DownloadRequest(
        url=body.url,
        output_dir=body.output_dir,
        format=dl_format,
        quality=dl_quality,
        embed_metadata=body.embed_metadata,
        embed_lyrics=body.embed_lyrics,
        audio_bitrate=body.audio_bitrate,
        naming_preset=body.naming_preset,
        filename_template=body.filename_template,
        auto_subtitle_download=body.auto_subtitle_download,
        preferred_subtitle_language=body.preferred_subtitle_language,
    )

    task_id = queue.add_task(
        task_type=TaskType.DOWNLOAD,
        name=body.url,
        execute_fn=downloader.download,
        args=(request,),
    )

    logger.info("Download enqueued: task=%s url=%s", task_id, body.url)
    return {"task_id": task_id, "status": "queued"}
