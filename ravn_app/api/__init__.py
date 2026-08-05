"""
ravn_app/api — FastAPI transport layer for the Tauri frontend.

This package is the ONLY part of the Python codebase that knows about HTTP/
WebSocket transport.  Its sole responsibility is:

  1. Accept and validate incoming requests.
  2. Translate them into calls on existing ravn_app.core services.
  3. Serialize responses back to JSON.

No business logic lives here.  All media, library, and queue behaviour remains
in ravn_app.core.  The FastAPI app can be run standalone (e.g. for development
with a browser or curl) or launched as a Tauri sidecar.
"""
