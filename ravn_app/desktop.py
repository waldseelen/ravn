"""
RAVN Native Desktop Application Launcher.

Runs the embedded FastAPI backend in a background thread and opens a
dedicated native desktop GUI window powered by pywebview (Edge WebView2 on Windows).
When the desktop window is closed, all backend threads and subprocesses are cleanly terminated.
"""

import os
import sys
import time
import socket
import logging
import threading
import uvicorn
import webview

from ravn_app.api.main import app
from ravn_app.utils.bundled_tools import refresh_system_environment_path

logger = logging.getLogger("ravn.desktop")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the target port is currently bound."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def wait_for_server(port: int, host: str = "127.0.0.1", timeout: float = 10.0) -> bool:
    """Wait until the backend server is ready to accept HTTP connections."""
    start = time.time()
    while time.time() - start < timeout:
        if is_port_in_use(port, host):
            return True
        time.sleep(0.1)
    return False


def start_server_thread(port: int, host: str = "127.0.0.1"):
    """Start uvicorn server in a daemon thread."""
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server, thread


def launch_desktop(port: int = 7842, host: str = "127.0.0.1"):
    """
    Launch the native desktop window.
    """
    refresh_system_environment_path()

    # Start FastAPI server if not already running
    if not is_port_in_use(port, host):
        start_server_thread(port, host)
        wait_for_server(port, host, timeout=8.0)

    url = f"http://{host}:{port}/"

    # Create native GUI desktop window
    window = webview.create_window(
        title="RAVN — Media Acquisition & Studio",
        url=url,
        width=1280,
        height=820,
        min_size=(960, 640),
        background_color="#0D0D11",
        text_select=True,
        zoomable=True
    )

    # Start desktop event loop (blocking until window is closed)
    webview.start(gui="edgechromium", debug=False)
    sys.exit(0)


if __name__ == "__main__":
    launch_desktop()
