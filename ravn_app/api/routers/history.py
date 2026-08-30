"""
ravn_app/api/routers/history.py — Download and conversion history endpoints.

Thin wrappers over DatabaseManager.  No business logic here.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

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
    records = db.get_downloads(limit=limit)
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
    records = db.get_conversions(limit=limit)
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


@router.get("/stats", summary="Get overall database and task statistics")
def get_database_statistics(db: DbDep) -> Dict[str, Any]:
    """Return total downloads, conversions, operations, and file size metrics."""
    return db.get_statistics()


@router.get("/recent", summary="Get combined recent activity records")
def get_recent_activity(
    db: DbDep,
    limit: int = Query(6, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Return unified recent operations and downloads for dashboard display."""
    activities: List[Dict[str, Any]] = []

    # Get recent operations
    ops = db.get_operations(limit=limit)
    for op in ops:
        activities.append({
            "id": f"op-{op.id}",
            "type": "operation",
            "category": op.task_type or "operation",
            "title": op.title or f"{op.task_type}: {op.operation}",
            "detail": op.output_path or ", ".join(op.input_paths),
            "status": op.status,
            "timestamp": op.completed_at or op.started_at,
            "duration": op.duration,
        })

    # Get recent downloads
    downloads = db.get_downloads(limit=limit)
    for d in downloads:
        activities.append({
            "id": f"dl-{d.id}",
            "type": "download",
            "category": "download",
            "title": d.title or d.url,
            "detail": d.file_path or d.format,
            "status": d.status,
            "timestamp": str(d.download_date),
            "duration": d.duration or 0.0,
        })

    # Sort descending by timestamp/id and return top N
    activities.sort(key=lambda x: str(x.get("timestamp") or ""), reverse=True)
    return activities[:limit]


@router.get("/operations", summary="List Phase 7/8 operation history")
def list_operations_history(
    db: DbDep,
    limit: int = Query(100, ge=1, le=1000),
    task_type: str | None = Query(None),
) -> List[Dict[str, Any]]:
    """Return recent operation records."""
    records = db.get_operations(limit=limit, task_type=task_type)
    return [
        {
            "id": r.id,
            "task_type": r.task_type,
            "operation": r.operation,
            "title": r.title,
            "input_paths": r.input_paths,
            "output_path": r.output_path,
            "format": r.format,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "duration": r.duration,
            "status": r.status,
            "error_message": r.error_message,
        }
        for r in records
    ]


@router.delete("/downloads/{record_id}", summary="Delete a download history record")
def delete_download_record(record_id: int, db: DbDep) -> Dict[str, Any]:
    conn = db._require_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM downloads WHERE id = ?", (record_id,))
    conn.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    return {"deleted": True, "id": record_id}


@router.delete("/downloads", summary="Clear all download history")
def clear_download_history(db: DbDep) -> Dict[str, Any]:
    db.clear_history("downloads")
    return {"cleared": True}

