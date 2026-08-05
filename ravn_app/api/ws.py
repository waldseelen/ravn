"""
ravn_app/api/ws.py — WebSocket event streaming endpoint.

Responsibility:
  - Maintain a set of connected WebSocket clients.
  - Broadcast structured JSON events to all connected clients.
  - Accept subscription filters from clients (optional, future).

Architecture rule:
  WebSockets carry EVENTS only:
    • download/task progress
    • queue state changes
    • log lines
    • backend notifications

  All command/query operations use the REST routers in api/routers/.
  This keeps the WebSocket responsibility narrow and the protocol predictable.

Usage:
  Frontend connects to  ws://localhost:{PORT}/ws/events
  Events are JSON objects with the shape:
    { "event": "<event_type>", "data": { ... }, "ts": "<iso8601>" }
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class EventBus:
    """
    Thread-safe WebSocket connection manager and event broadcaster.

    The FastAPI app creates a single EventBus instance at startup.
    Core services (or the task-queue callback bridge) call broadcast()
    to push events to all connected frontend clients.
    """

    def __init__(self) -> None:
        self._connections: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.add(ws)
        logger.info("WS client connected  (total=%d)", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections.discard(ws)
        logger.info("WS client disconnected (total=%d)", len(self._connections))

    async def broadcast(self, event: str, data: Dict[str, Any]) -> None:
        """
        Send a JSON event to every connected client.

        Stale / closed sockets are silently removed.
        """
        if not self._connections:
            return

        message = json.dumps({
            "event": event,
            "data": data,
            "ts": datetime.now(timezone.utc).isoformat(),
        })

        dead: Set[WebSocket] = set()
        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)

        self._connections -= dead

    @property
    def client_count(self) -> int:
        return len(self._connections)


# Module-level singleton — imported by main.py and injected into routers
event_bus = EventBus()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws/events")
async def websocket_events(ws: WebSocket) -> None:
    """
    Real-time event stream for the Tauri frontend.

    The frontend connects here to receive:
      • task.progress  — { task_id, progress, message, status }
      • task.complete  — { task_id, output_path, duration_seconds }
      • task.error     — { task_id, error_message }
      • task.cancel    — { task_id }
      • queue.paused   — { paused: bool }
      • log.line       — { level, message, logger }

    The frontend may send a JSON ping to keep the connection alive:
      { "ping": true }
    """
    await event_bus.connect(ws)
    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                msg = json.loads(raw)
                if msg.get("ping"):
                    await ws.send_text(json.dumps({"pong": True}))
            except asyncio.TimeoutError:
                # Keep-alive: send a server-side ping so the client knows we're alive
                await ws.send_text(json.dumps({"event": "ping", "data": {}}))
            except (json.JSONDecodeError, KeyError):
                pass  # Ignore malformed messages from the client
    except WebSocketDisconnect:
        pass
    finally:
        event_bus.disconnect(ws)


# ---------------------------------------------------------------------------
# Helper: bridge synchronous TaskQueue callbacks → async broadcasts
# ---------------------------------------------------------------------------

def make_task_callbacks(loop: asyncio.AbstractEventLoop):
    """
    Return a dict of TaskQueue callback functions that push events via the
    EventBus into the given asyncio event loop.

    Usage in main.py startup:
        callbacks = make_task_callbacks(asyncio.get_event_loop())
        queue.add_task(..., on_progress=callbacks["on_progress"], ...)
    """

    def _fire(coro):
        """Schedule a coroutine on the FastAPI event loop from a sync thread."""
        asyncio.run_coroutine_threadsafe(coro, loop)

    def on_progress(progress: int, message: str = "", *, task_id: str = "") -> None:
        _fire(event_bus.broadcast("task.progress", {
            "task_id": task_id,
            "progress": progress,
            "message": message,
        }))

    def on_complete(task: Any) -> None:
        _fire(event_bus.broadcast("task.complete", {
            "task_id": task.id,
            "output_path": task.result.output_path if task.result else None,
            "duration_seconds": task.result.duration_seconds if task.result else 0,
        }))

    def on_error(task: Any, error_message: str) -> None:
        _fire(event_bus.broadcast("task.error", {
            "task_id": task.id,
            "error_message": error_message,
        }))

    def on_cancel(task: Any) -> None:
        _fire(event_bus.broadcast("task.cancel", {"task_id": task.id}))

    return {
        "on_progress": on_progress,
        "on_complete": on_complete,
        "on_error": on_error,
        "on_cancel": on_cancel,
    }
