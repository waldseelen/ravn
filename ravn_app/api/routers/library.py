"""
ravn_app/api/routers/library.py — Local media library and collection endpoints.
"""

from __future__ import annotations

import logging
import os
import platform
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ravn_app.api.deps import LibraryDep
from ravn_app.core.persistence.media_library import MediaSearchFilters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["library"])


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AddMediaRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path to the media file")
    title: Optional[str] = Field(None, description="Optional custom title")
    tags: List[str] = Field(default_factory=list, description="Tags list")


class CreateCollectionRequest(BaseModel):
    name: str = Field(..., description="Collection name")
    description: Optional[str] = Field("", description="Collection description")


class AddToCollectionRequest(BaseModel):
    media_id: int = Field(..., description="Media item ID")
    position: Optional[int] = Field(None, description="Position order")


class ExportLibraryRequest(BaseModel):
    format: str = Field("json", description="Export format: 'json' or 'csv'")
    output_file: Optional[str] = Field(None, description="Output file path")


class PathActionRequest(BaseModel):
    path: str = Field(..., description="File or directory path")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", summary="List or search media items")
def search_media(
    library: LibraryDep,
    q: Optional[str] = Query(None, description="Search keyword"),
    tags: Optional[str] = Query(None, description="Comma-separated tag filter"),
    format: Optional[str] = Query(None, description="Media format filter"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> List[Dict[str, Any]]:
    """List or search media items."""
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()] if tags else []
    filters = MediaSearchFilters(
        format=format if format and format.lower() != "all" else None,
        tags=tag_list,
        limit=limit,
    )
    if q or tag_list or (format and format.lower() != "all"):
        records = library.search_media(query=q or "", filters=filters)
    else:
        records = library.list_media(limit=limit, offset=offset)

    return [asdict(r) for r in records]


@router.post("/", summary="Import a media file into the library", status_code=201)
@router.post("/add", summary="Import a media file into the library", status_code=201)
def add_media(
    body: AddMediaRequest,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Import media file and extract metadata."""
    p = Path(body.file_path)
    if not p.exists():
        raise HTTPException(status_code=400, detail=f"File not found: {body.file_path}")

    try:
        media_id = library.add_media(
            file_path=str(p.resolve()),
            title=body.title,
            tags=body.tags,
        )
        record = library.get_media(media_id)
        return {"success": True, "media_id": media_id, "item": asdict(record) if record else None}
    except Exception as e:
        logger.error("Failed to add media to library: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{media_id}", summary="Delete a media item from the library")
def delete_media(
    media_id: int,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Delete a media item."""
    success = library.delete_media(media_id)
    if not success:
        raise HTTPException(status_code=404, detail="Media item not found")
    return {"success": True, "id": media_id}


@router.get("/stats", summary="Get media library statistics")
def get_library_stats(library: LibraryDep) -> Dict[str, Any]:
    """Get aggregate media statistics."""
    return library.get_statistics()


@router.post("/export", summary="Export library catalog to JSON or CSV")
def export_library(
    body: ExportLibraryRequest,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Export library items."""
    export_fmt = body.format.lower()
    if export_fmt not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="Format must be json or csv")

    out_file = body.output_file
    if not out_file:
        out_dir = Path.home() / "Downloads" / "RAVN"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = str(out_dir / f"ravn_library_export.{export_fmt}")

    success = library.export_library(export_fmt, out_file)
    if not success:
        raise HTTPException(status_code=500, detail="Library export failed")

    return {"success": True, "format": export_fmt, "output_file": out_file}


@router.get("/collections", summary="List collections")
def list_collections(library: LibraryDep) -> List[Dict[str, Any]]:
    """List all collections."""
    collections = library.list_collections()
    return [asdict(c) for c in collections]


@router.post("/collections", summary="Create a new collection", status_code=201)
def create_collection(
    body: CreateCollectionRequest,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Create a new collection."""
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Collection name cannot be empty")
    col_id = library.create_collection(name=body.name.strip(), description=body.description or "")
    return {"success": True, "id": col_id, "name": body.name.strip()}


@router.delete("/collections/{collection_id}", summary="Delete a collection")
def delete_collection(
    collection_id: int,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Delete a collection."""
    success = library.delete_collection(collection_id)
    if not success:
        raise HTTPException(status_code=404, detail="Collection not found")
    return {"success": True, "id": collection_id}


@router.get("/collections/{collection_id}/items", summary="Get media items in a collection")
def get_collection_items(
    collection_id: int,
    library: LibraryDep,
) -> List[Dict[str, Any]]:
    """Return all media items inside a collection."""
    items = library.get_collection_items(collection_id)
    return [asdict(i) for i in items]


@router.post("/collections/{collection_id}/items", summary="Add media to a collection")
def add_item_to_collection(
    collection_id: int,
    body: AddToCollectionRequest,
    library: LibraryDep,
) -> Dict[str, Any]:
    """Add a media item to a collection."""
    success = library.add_to_collection(media_id=body.media_id, collection_id=collection_id, position=body.position)
    return {"success": success, "collection_id": collection_id, "media_id": body.media_id}


@router.get("/recent-searches", summary="Get recent searches")
def get_recent_searches(
    library: LibraryDep,
    limit: int = Query(10, ge=1, le=50),
) -> List[Dict[str, Any]]:
    """Return recent library queries."""
    return library.get_recent_searches(limit=limit)


@router.post("/open-file", summary="Open media file with default application")
def open_file_endpoint(body: PathActionRequest) -> Dict[str, Any]:
    """Open a file with OS default handler."""
    p = Path(body.path)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {body.path}")

    try:
        if platform.system() == "Windows":
            os.startfile(str(p))
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(p)], check=False)
        else:
            subprocess.run(["xdg-open", str(p)], check=False)
        return {"success": True, "path": str(p)}
    except Exception as e:
        logger.error("Failed to open file: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/open-folder", summary="Open directory containing file")
def open_folder_endpoint(body: PathActionRequest) -> Dict[str, Any]:
    """Open folder and select/reveal file."""
    p = Path(body.path)
    folder = p.parent if p.is_file() else p
    if not folder.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {folder}")

    try:
        if platform.system() == "Windows":
            if p.is_file():
                subprocess.run(["explorer", f"/select,{str(p)}"], check=False)
            else:
                os.startfile(str(folder))
        elif platform.system() == "Darwin":
            subprocess.run(["open", "-R" if p.is_file() else "", str(p if p.is_file() else folder)], check=False)
        else:
            subprocess.run(["xdg-open", str(folder)], check=False)
        return {"success": True, "folder": str(folder)}
    except Exception as e:
        logger.error("Failed to open folder: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

