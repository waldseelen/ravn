"""
RAVN - One-click winget installer for missing external tools.

Complements ``ravn_app.core.tool_health``: that module answers "what is
missing?", this module answers "install it, and make the running process see
it immediately without a restart".
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from ravn_app.core.runners.base import get_hidden_subprocess_kwargs

logger = logging.getLogger(__name__)

# Tool name (as used by tool_health.ToolHealthChecker) -> winget package id.
# ffprobe ships inside the ffmpeg package, so it has no separate entry —
# installing 'ffmpeg' satisfies both.
WINGET_PACKAGE_IDS: Dict[str, str] = {
    "ffmpeg": "Gyan.FFmpeg",
    "yt-dlp": "yt-dlp.yt-dlp",
    "aria2c": "aria2.aria2",
}

_INSTALL_TIMEOUT_SECONDS = 300


@dataclass
class ToolInstallResult:
    """Outcome of attempting to install a single tool via winget."""

    tool: str
    package_id: Optional[str]
    success: bool
    message: str


def is_winget_available() -> bool:
    """Return True if the winget CLI is reachable on PATH."""
    return shutil.which("winget") is not None


def _package_id_for_tool(tool_name: str) -> Optional[str]:
    if tool_name == "ffprobe":
        # ffprobe has no standalone winget package — it is bundled with ffmpeg.
        return WINGET_PACKAGE_IDS.get("ffmpeg")
    return WINGET_PACKAGE_IDS.get(tool_name)


def _refresh_process_environment_path() -> int:
    """
    Merge the persisted user + machine PATH (as winget/installers update it in
    the registry) into this already-running process's ``os.environ['PATH']``.

    Windows only updates the registry on install; a running process keeps its
    original PATH snapshot until something explicitly refreshes it. Without
    this, a freshly installed tool would be invisible to ``shutil.which()``
    until RAVN is restarted. Returns the number of new directories added.
    """
    if os.name != "nt":
        return 0

    try:
        import winreg
    except ImportError:
        return 0

    collected: List[str] = []
    registry_targets = (
        (winreg.HKEY_CURRENT_USER, r"Environment"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
    )
    for hive, subkey in registry_targets:
        try:
            with winreg.OpenKey(hive, subkey) as key:
                value, _type = winreg.QueryValueEx(key, "Path")
                collected.extend(part for part in value.split(os.pathsep) if part)
        except OSError:
            continue

    if not collected:
        return 0

    current_parts = [part for part in os.environ.get("PATH", "").split(os.pathsep) if part]
    seen = {part.strip().lower() for part in current_parts}

    added = 0
    for part in collected:
        norm = part.strip().lower()
        if norm and norm not in seen:
            current_parts.append(part)
            seen.add(norm)
            added += 1

    if added:
        os.environ["PATH"] = os.pathsep.join(current_parts)
    return added


def install_tool(tool_name: str, timeout: int = _INSTALL_TIMEOUT_SECONDS) -> ToolInstallResult:
    """Install a single missing tool via winget. Does not refresh PATH — see install_missing_tools."""
    package_id = _package_id_for_tool(tool_name)
    if package_id is None:
        return ToolInstallResult(
            tool=tool_name,
            package_id=None,
            success=False,
            message=f"{tool_name} has no known winget package mapping",
        )

    if not is_winget_available():
        return ToolInstallResult(
            tool=tool_name,
            package_id=package_id,
            success=False,
            message="winget is not available on PATH",
        )

    command = [
        "winget", "install",
        "--id", package_id,
        "-e",
        "--source", "winget",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--silent",
        "--disable-interactivity",
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            timeout=timeout,
            **get_hidden_subprocess_kwargs(),
        )
    except subprocess.TimeoutExpired:
        return ToolInstallResult(
            tool=tool_name,
            package_id=package_id,
            success=False,
            message=f"Installation timed out after {timeout}s",
        )
    except Exception as exc:  # pragma: no cover - defensive, unexpected OS errors
        logger.error("winget install failed for %s: %s", tool_name, exc)
        return ToolInstallResult(
            tool=tool_name,
            package_id=package_id,
            success=False,
            message=str(exc),
        )

    if result.returncode == 0:
        return ToolInstallResult(tool=tool_name, package_id=package_id, success=True, message="Installed")

    tail = (result.stdout or "").strip().splitlines()[-1:] or [""]
    return ToolInstallResult(
        tool=tool_name,
        package_id=package_id,
        success=False,
        message=f"winget exited with code {result.returncode}: {tail[0]}",
    )


def install_missing_tools(
    tool_names: List[str],
    progress_callback: Optional[Callable[[str, str], None]] = None,
) -> Dict[str, ToolInstallResult]:
    """
    Install every tool in ``tool_names`` (deduplicating shared winget packages,
    e.g. ffmpeg/ffprobe), then refresh this process's PATH so the newly
    installed binaries are immediately visible to ``tool_health`` checks.

    ``progress_callback(tool_name, stage)`` fires with stage in
    {"installing", "done", "error"} — safe to bridge into a UI thread.
    """
    results: Dict[str, ToolInstallResult] = {}

    # Group requested tools by the winget package that actually installs them,
    # so ffmpeg+ffprobe (same package) only trigger one winget invocation.
    package_to_tools: Dict[str, List[str]] = {}
    for tool_name in tool_names:
        package_id = _package_id_for_tool(tool_name)
        if package_id is None:
            results[tool_name] = ToolInstallResult(
                tool=tool_name, package_id=None, success=False,
                message=f"{tool_name} has no known winget package mapping",
            )
            continue
        package_to_tools.setdefault(package_id, []).append(tool_name)

    for package_id, tools_for_package in package_to_tools.items():
        for tool_name in tools_for_package:
            if progress_callback:
                progress_callback(tool_name, "installing")

        outcome = install_tool(tools_for_package[0])
        for tool_name in tools_for_package:
            shared_outcome = ToolInstallResult(
                tool=tool_name,
                package_id=package_id,
                success=outcome.success,
                message=outcome.message,
            )
            results[tool_name] = shared_outcome
            if progress_callback:
                progress_callback(tool_name, "done" if outcome.success else "error")

    _refresh_process_environment_path()

    try:
        from ravn_app.core.tool_health import get_tool_health_checker
        get_tool_health_checker().clear_cache()
    except Exception:
        pass

    return results
