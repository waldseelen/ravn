"""
ravn_app/api/main.py — FastAPI application factory and entry point.

Run standalone (development):
    uvicorn ravn_app.api.main:app --reload --port 7842

Run as Tauri sidecar (production):
    The Tauri build bundles the PyInstaller-compiled executable.
    The executable calls serve() which blocks until SIGINT/SIGTERM.

Architecture:
    This file wires together the router modules and the WebSocket event bus.
    It does NOT contain business logic.  All media, library, and queue
    behaviour lives in ravn_app.core.

Port selection:
    Default: 7842  (chosen to avoid common dev-tool collisions)
    Override: set the RAVN_API_PORT environment variable.
"""

from __future__ import annotations

import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ravn_app.api.routers import downloads, history, library, queue, settings, studio
from ravn_app.api.ws import event_bus
from ravn_app.api.ws import router as ws_router
from ravn_app.core.logging_config import setup_logging

logger = logging.getLogger(__name__)

DEFAULT_PORT = 7842


# ---------------------------------------------------------------------------
# Application lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background services on startup; tear them down on shutdown."""
    from ravn_app.core.config_paths import ensure_directories_exist, migrate_all_legacy_files
    from ravn_app.utils.bundled_tools import configure_bundled_tools_path

    ensure_directories_exist()
    migrate_all_legacy_files()
    configure_bundled_tools_path()

    # Import here to avoid circular imports at module level
    import asyncio
    from ravn_app.api.deps import _task_queue  # type: ignore[import]
    from ravn_app.api.ws import make_task_callbacks

    tq = _task_queue()
    loop = asyncio.get_running_loop()
    callbacks = make_task_callbacks(loop)
    tq.set_default_callbacks(
        on_progress=callbacks["on_progress"],
        on_complete=callbacks["on_complete"],
        on_error=callbacks["on_error"],
        on_cancel=callbacks["on_cancel"],
    )

    port = getattr(app.state, "port", DEFAULT_PORT)
    logger.info("RAVN API server starting up (port=%s)", port)

    yield  # Application runs here


    logger.info("RAVN API server shutting down")
    tq.stop(wait=False)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(
        title="RAVN API",
        description=(
            "Local HTTP/WebSocket transport layer for the RAVN desktop application.\n\n"
            "This API is consumed by the Tauri frontend and exposes the same core "
            "functionality available via the `ravn` CLI.  The backend remains "
            "completely UI-agnostic."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — the Tauri WebView origin is null/localhost; allow it in development.
    # In production the sidecar and the WebView run on the same machine so this
    # is a low-risk setting.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- HTTP routers ---
    app.include_router(downloads.router, prefix="/api/v1")
    app.include_router(queue.router,     prefix="/api/v1")
    app.include_router(history.router,   prefix="/api/v1")
    app.include_router(library.router,   prefix="/api/v1")
    app.include_router(settings.router,  prefix="/api/v1")
    app.include_router(studio.router,    prefix="/api/v1")


    # --- WebSocket ---
    app.include_router(ws_router)

    # --- Health / meta ---
    @app.get("/health", tags=["meta"], summary="Server and tool health check")
    @app.get("/api/v1/health", tags=["meta"], summary="Server and tool health check")
    async def health() -> Dict[str, Any]:
        from ravn_app.core.tool_health import get_tool_health_checker

        checker = get_tool_health_checker()
        tool_summary = checker.get_health_summary()
        return {
            "status": "ok",
            "ws_clients": event_bus.client_count,
            "tools": tool_summary,
        }

    # Mount compiled SPA frontend if dist/ exists
    from starlette.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            # If requesting an existing static file in dist root (e.g. favicon.ico)
            target_file = dist_dir / full_path
            if full_path and target_file.is_file():
                return FileResponse(target_file)
            index_file = dist_dir / "index.html"
            if index_file.exists():
                return FileResponse(index_file)
            return {"service": "RAVN API", "docs": "/docs"}
    else:
        @app.get("/", tags=["meta"], include_in_schema=False)
        async def root() -> Dict[str, str]:
            return {"service": "RAVN API", "docs": "/docs"}

    return app



# Module-level app instance (uvicorn uses this)
app = create_app()


# ---------------------------------------------------------------------------
# CLI entry point (used by PyInstaller sidecar executable)
# ---------------------------------------------------------------------------

def serve(port: int | None = None, host: str = "127.0.0.1") -> None:
    """
    Start the uvicorn server synchronously.

    Called by the PyInstaller entry point when RAVN runs as a Tauri sidecar.
    The Tauri process captures stdout to discover which port the server bound
    on (useful when port=0 / OS-assigned).
    """
    setup_logging()

    resolved_port = port or int(os.environ.get("RAVN_API_PORT", DEFAULT_PORT))

    print(f"RAVN_API_PORT={resolved_port}", flush=True)  # Tauri sidecar reads this
    logger.info("Starting RAVN API on %s:%s", host, resolved_port)

    uvicorn.run(
        "ravn_app.api.main:app",
        host=host,
        port=resolved_port,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    serve(port=port_arg)
