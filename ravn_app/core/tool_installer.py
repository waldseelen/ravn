"""
RAVN - Installer helper for missing external tools.

Complements ``ravn_app.core.tool_health``: that module answers "what is
missing?", this module answers "how does the user get it?".

Note this is the *fallback* path. A packaged RAVN release ships ffmpeg/ffprobe,
yt-dlp and aria2c inside ``assets/`` (see ``ravn_app.utils.bundled_tools``), so a
freshly unzipped build should already report every tool as available. This module
matters when running from source, or if the bundled binaries are unavailable.

Platform behaviour differs by necessity:

* **Windows** — winget installs silently and non-interactively, so RAVN performs the
  install itself and then refreshes the process PATH so the new binary is visible
  without a restart.
* **Linux** — apt/dnf/pacman all need root. Shelling out to ``sudo`` from a GUI app
  has nowhere to prompt for a password (no TTY) and would simply hang, and silently
  acquiring root on the user's behalf is not something a media tool should do. So RAVN
  detects the package manager and hands back the exact command for the user to run.
* **macOS** — not implemented yet; see the TODO below.
"""

import logging
import os
import shutil
import subprocess
import sys
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

# Same tools, named as each Linux distro family packages them. aria2's binary is
# aria2c but the package is called "aria2" everywhere, which is why these maps are
# keyed by RAVN's tool name rather than reused from WINGET_PACKAGE_IDS.
APT_PACKAGE_IDS: Dict[str, str] = {
    "ffmpeg": "ffmpeg",
    "yt-dlp": "yt-dlp",
    "aria2c": "aria2",
}

DNF_PACKAGE_IDS: Dict[str, str] = {
    "ffmpeg": "ffmpeg",
    "yt-dlp": "yt-dlp",
    "aria2c": "aria2",
}

PACMAN_PACKAGE_IDS: Dict[str, str] = {
    "ffmpeg": "ffmpeg",
    "yt-dlp": "yt-dlp",
    "aria2c": "aria2",
}

# TODO(macos-followup): add BREW_PACKAGE_IDS + a brew backend. Deferred deliberately —
# Linux packaging is the current priority and a half-built brew path would be worse
# than a clearly-unsupported one.

# Package manager -> (detection binary, argv template for installing packages).
_LINUX_PACKAGE_MANAGERS = (
    ("apt", "apt-get", APT_PACKAGE_IDS, ["sudo", "apt-get", "install", "-y"]),
    ("dnf", "dnf", DNF_PACKAGE_IDS, ["sudo", "dnf", "install", "-y"]),
    ("pacman", "pacman", PACMAN_PACKAGE_IDS, ["sudo", "pacman", "-S", "--noconfirm"]),
)

_INSTALL_TIMEOUT_SECONDS = 300


@dataclass
class ToolInstallResult:
    """
    Outcome of attempting to make a single tool available.

    ``success`` means RAVN actually installed the tool. On Linux that is always False
    and ``manual_command`` carries the command the user should run instead — a
    "here is how" result rather than an error.
    """

    tool: str
    package_id: Optional[str]
    success: bool
    message: str
    manual_command: Optional[str] = None


def is_winget_available() -> bool:
    """Return True if the winget CLI is reachable on PATH."""
    return shutil.which("winget") is not None


def detect_linux_package_manager() -> Optional[str]:
    """Return the name of this system's package manager ('apt'/'dnf'/'pacman')."""
    if not sys.platform.startswith("linux"):
        return None
    for name, binary, _packages, _command in _LINUX_PACKAGE_MANAGERS:
        if shutil.which(binary):
            return name
    return None


def _linux_manager_entry(manager: str):
    for entry in _LINUX_PACKAGE_MANAGERS:
        if entry[0] == manager:
            return entry
    return None


def get_manual_install_command(tool_names: List[str]) -> Optional[str]:
    """
    Build the single command a Linux user should run to install the missing tools.

    Returns None when this is not a Linux system with a recognised package manager,
    or when the requested tools have no packages to install.
    """
    manager = detect_linux_package_manager()
    if manager is None:
        return None

    entry = _linux_manager_entry(manager)
    if entry is None:
        return None

    _name, _binary, packages, command = entry

    # Deduplicate while preserving order: ffmpeg and ffprobe map to one package.
    resolved: List[str] = []
    for tool_name in tool_names:
        package = packages.get("ffmpeg" if tool_name == "ffprobe" else tool_name)
        if package and package not in resolved:
            resolved.append(package)

    if not resolved:
        return None

    return " ".join([*command, *resolved])


def is_install_supported() -> bool:
    """
    Whether RAVN can help with installing missing tools on this system.

    True on Windows when winget is present (RAVN installs directly), and on Linux when
    a known package manager is present (RAVN shows the command to run). The Settings
    UI uses this to decide whether offering the action makes sense at all.
    """
    if os.name == "nt":
        return is_winget_available()
    return detect_linux_package_manager() is not None


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
    if os.name != "nt":
        manual_command = get_manual_install_command([tool_name])
        return ToolInstallResult(
            tool=tool_name,
            package_id=None,
            success=False,
            message=(
                f"Run this command to install: {manual_command}"
                if manual_command
                else f"No supported package manager found to install {tool_name}"
            ),
            manual_command=manual_command,
        )

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

    # Non-Windows: report the command to run rather than attempting a privileged
    # install. See this module's docstring for why RAVN does not shell out to sudo.
    if os.name != "nt":
        manual_command = get_manual_install_command(tool_names)
        for tool_name in tool_names:
            if progress_callback:
                progress_callback(tool_name, "installing")
            results[tool_name] = ToolInstallResult(
                tool=tool_name,
                package_id=None,
                success=False,
                message=(
                    f"Run this command to install: {manual_command}"
                    if manual_command
                    else f"No supported package manager found to install {tool_name}"
                ),
                manual_command=manual_command,
            )
            if progress_callback:
                progress_callback(tool_name, "manual" if manual_command else "error")
        return results

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
