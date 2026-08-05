"""
ravn_app/api/routers/history.py — Download and conversion history endpoints.

Thin wrappers over DatabaseManager.  No business logic here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ravn_app.api.deps import DbDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/downloads", summary="List download history")
def list_download_history(
    db: DbDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """Return recent download records, newest first."""
    records = db.get_download_history(limit=limit, offset=offset)
    return [
        {
            "id": r.id,
            "url": r.url,
            "title": r.title,
            "format": r.format,
            "quality": r.quality,
            "file_path": r.file_path,
            "file_size": r.file_size,
            "download_date": r.download_date,
            "status": r.status,
            "duration": r.duration,
            "thumbnail_url": r.thumbnail_url,
        }
        for r in records
    ]


@router.get("/conversions", summary="List conversion history")
def list_conversion_history(
    db: DbDep,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """Return recent conversion records, newest first."""
    records = db.get_conversion_history(limit=limit, offset=offset)
    return [
        {
            "id": r.id,
            "input_file": r.input_file,
            "output_file": r.output_file,
            "input_codec": r.input_codec,
            "output_codec": r.output_codec,
            "conversion_date": r.conversion_date,
            "duration": r.duration,
            "status": r.status,
        }
        for r in records
    ]


@router.delete("/downloads/{record_id}", summary="Delete a download history record")
def delete_download_record(record_id: int, db: DbDep) -> Dict[str, Any]:
    ok = db.delete_download_record(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return {"deleted": True, "id": record_id}


@router.delete("/downloads", summary="Clear all download history")
def clear_download_history(db: DbDep) -> Dict[str, Any]:
    db.clear_download_history()
    return {"cleared": True}
