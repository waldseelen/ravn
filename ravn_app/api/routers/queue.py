"""
ravn_app/api/routers/queue.py — Queue inspection and control endpoints.

All mutation is forwarded to the shared TaskQueue service; this router only
translates between HTTP requests and service calls.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from ravn_app.api.deps import QueueDep
from ravn_app.core.task_manager import Task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/queue", tags=["queue"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_to_dict(task: Task) -> Dict[str, Any]:
    """Serialize a Task dataclass to a plain dict for JSON responses."""
    return {
        "id": task.id,
        "type": task.task_type.value,
        "name": task.name,
        "status": task.status.value,
        "progress": task.progress,
        "progress_message": task.progress_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "result": {
            "success": task.result.success,
            "output_path": task.result.output_path,
            "error_message": task.result.error_message,
            "duration_seconds": task.result.duration_seconds,
        } if task.result else None,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", summary="List all tasks in the queue")
def list_tasks(queue: QueueDep) -> List[Dict[str, Any]]:
    """Return all tasks (active, pending, and recently completed)."""
    return [_task_to_dict(t) for t in queue.get_all_tasks()]


@router.get("/active", summary="List currently running tasks")
def list_active(queue: QueueDep) -> List[Dict[str, Any]]:
    return [_task_to_dict(t) for t in queue.get_active_tasks()]


@router.get("/pending", summary="List queued tasks not yet started")
def list_pending(queue: QueueDep) -> List[Dict[str, Any]]:
    return [_task_to_dict(t) for t in queue.get_pending_tasks()]


@router.get("/completed", summary="List completed and failed tasks")
def list_completed(queue: QueueDep) -> List[Dict[str, Any]]:
    return [_task_to_dict(t) for t in queue.get_completed_tasks()]


@router.get("/{task_id}", summary="Get a single task by ID")
def get_task(task_id: str, queue: QueueDep) -> Dict[str, Any]:
    task = queue.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return _task_to_dict(task)


@router.post("/{task_id}/cancel", summary="Request cancellation of a running task")
def cancel_task(task_id: str, queue: QueueDep) -> Dict[str, Any]:
    ok = queue.cancel_task(task_id)
    if not ok:
        raise HTTPException(
            status_code=409,
            detail=f"Task '{task_id}' could not be cancelled (not found or already terminal)",
        )
    return {"cancelled": True, "task_id": task_id}


@router.post("/pause", summary="Pause queue intake (no new tasks will start)")
def pause_queue(queue: QueueDep) -> Dict[str, Any]:
    queue.pause()
    return {"paused": True}


@router.post("/resume", summary="Resume queue intake")
def resume_queue(queue: QueueDep) -> Dict[str, Any]:
    queue.resume()
    return {"paused": False}


@router.delete("/completed", summary="Clear all completed/failed tasks from memory")
def clear_completed(queue: QueueDep) -> Dict[str, Any]:
    queue.clear_completed()
    return {"cleared": True}
