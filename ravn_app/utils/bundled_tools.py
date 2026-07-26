"""Shared lookup for external tool binaries shipped inside a packaged RAVN build.

RAVN drives four external binaries (ffmpeg, ffprobe, yt-dlp, aria2c). A packaged
release bundles them under ``assets/<tool>/<platform>/`` so a freshly unzipped build
works with no install step and no first-run network fetch -- that is the primary path.
Falling back to a system copy on ``PATH`` (and, failing that, the Settings
"install missing tools" action) is the backup, not the design.

This module holds the tool-agnostic half of that lookup. ``ffmpeg_checker`` layers the
FFmpeg-specific parts (codec probing, the ffmpeg/ffprobe pair) on top of it, and the
aria2c/yt-dlp runners call in here directly.

Layout searched, in order, for every candidate root::

    assets/<subdir>/<platform>/   <- what build.ps1 populates
    <subdir>/<platform>/
    assets/<subdir>/
    <subdir>/

where ``<platform>`` is win64/macos/linux.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Iterator, List, Optional

# Directory name used for this OS inside the bundled-asset layout. Kept module-level
# (rather than computed per call) so tests can patch it to exercise a foreign layout.
PLATFORM_DIR = {
    "win32": "win64",
    "cygwin": "win64",
    "darwin": "macos",
}.get(sys.platform, "linux")


def project_root() -> Path:
    """Repository/source root, used when running unpackaged from a checkout."""
    return Path(__file__).resolve().parents[2]


def candidate_runtime_roots() -> List[Path]:
    """
    Directories that may contain a bundled-tool tree, most specific first.

    ``sys._MEIPASS`` is PyInstaller's extraction dir (onefile); the executable's own
    directory covers onedir builds; the project root covers running from source.
    """
    roots: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))

    executable = getattr(sys, "executable", None)
    if executable:
        try:
            roots.append(Path(executable).resolve().parent)
        except Exception:
            # A missing/unresolvable sys.executable must not break tool lookup.
            pass

    roots.append(project_root())

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        unique_roots.append(root)
    return unique_roots


def binary_name(tool_name: str) -> str:
    """Executable filename for this OS (appends .exe on Windows when absent)."""
    normalized = str(tool_name or "").strip()
    if os.name == "nt" and normalized and not normalized.lower().endswith(".exe"):
        return f"{normalized}.exe"
    return normalized


def iter_bundled_dirs(asset_subdir: str) -> Iterator[Path]:
    """Yield candidate bundled-runtime directories for a tool, in lookup order."""
    seen: set[str] = set()
    relative_dirs = (
        Path("assets") / asset_subdir / PLATFORM_DIR,
        Path(asset_subdir) / PLATFORM_DIR,
        Path("assets") / asset_subdir,
        Path(asset_subdir),
    )
    for root in candidate_runtime_roots():
        for relative_dir in relative_dirs:
            candidate = root / relative_dir
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            yield candidate


def find_bundled_binary(tool_name: str, asset_subdir: str) -> Optional[str]:
    """Return the bundled executable path for a tool, or None if not shipped."""
    filename = binary_name(tool_name)
    for directory in iter_bundled_dirs(asset_subdir):
        candidate = directory / filename
        if candidate.exists() and candidate.is_file():
            return str(candidate)
    return None


def resolve_binary_path(requested_path: str, tool_name: str, asset_subdir: str) -> str:
    """
    Resolve a configured tool path.

    Precedence: an explicit path the user configured, then a custom executable name
    looked up on PATH, then the bundled copy, then PATH. Bundled beats PATH for the
    default name so a packaged build uses the version it shipped with rather than
    whatever happens to be installed on the machine.
    """
    normalized = str(requested_path or tool_name).strip() or tool_name

    if any(sep in normalized for sep in (os.sep, "/", "\\")):
        expanded = Path(normalized).expanduser()
        if expanded.exists():
            return str(expanded)
        return normalized

    if normalized not in {tool_name, binary_name(tool_name)}:
        discovered = shutil.which(normalized)
        return discovered or normalized

    bundled = find_bundled_binary(tool_name, asset_subdir)
    if bundled:
        return bundled

    discovered = shutil.which(normalized)
    return discovered or normalized


# Which asset subdirectory ships each tool. ffprobe has no directory of its own --
# it is distributed inside the same FFmpeg archive, so both resolve to "ffmpeg".
TOOL_ASSET_SUBDIRS = {
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffmpeg",
    "yt-dlp": "ytdlp",
    "aria2c": "aria2",
}


def find_tool(tool_name: str) -> Optional[str]:
    """Locate a known RAVN tool in the bundled tree; None if it is not shipped."""
    asset_subdir = TOOL_ASSET_SUBDIRS.get(tool_name)
    if asset_subdir is None:
        return None
    return find_bundled_binary(tool_name, asset_subdir)


def resolve_tool(requested_path: str, tool_name: str) -> str:
    """Resolve a known RAVN tool, preferring the bundled copy over PATH."""
    asset_subdir = TOOL_ASSET_SUBDIRS.get(tool_name, tool_name)
    return resolve_binary_path(requested_path, tool_name, asset_subdir)


def prefer_bundled(requested_path: str, tool_name: str) -> str:
    """
    Swap in the bundled copy only when the caller asked for the plain default name.

    Deliberately does *not* fall back to ``shutil.which`` the way ``resolve_tool``
    does. Runners resolve PATH lazily when they actually execute, so baking an
    absolute machine-specific path in at construction time would both pin the object
    to one machine and freeze a lookup that must stay live -- PATH changes after the
    Settings "install missing tools" action, and a runner built earlier has to see it.
    An explicitly configured path is passed through untouched.
    """
    normalized = str(requested_path or tool_name).strip() or tool_name
    if normalized not in {tool_name, binary_name(tool_name)}:
        return normalized
    return find_tool(tool_name) or normalized


def configure_bundled_tools_path() -> List[str]:
    """
    Put every bundled tool directory on PATH, and report which ones were added.

    Call once at startup. RAVN resolves most tool paths explicitly, but the tools also
    invoke *each other* -- yt-dlp shells out to ffmpeg to mux separate audio/video
    streams -- and those child processes only see PATH. Without this a packaged build
    would download a video and then fail to merge it.
    """
    configured: List[str] = []
    for tool_name, asset_subdir in TOOL_ASSET_SUBDIRS.items():
        bundled_dir = prepend_bundled_dir_to_path(tool_name, asset_subdir)
        if bundled_dir and bundled_dir not in configured:
            configured.append(bundled_dir)
    return configured


def prepend_bundled_dir_to_path(tool_name: str, asset_subdir: str) -> Optional[str]:
    """
    Put a tool's bundled directory on PATH so child processes resolve it too.

    Needed because the tools invoke each other: yt-dlp shells out to ffmpeg for
    muxing, so it is not enough for RAVN alone to know the bundled path. Idempotent.
    """
    bundled = find_bundled_binary(tool_name, asset_subdir)
    if not bundled:
        return None

    bundled_dir = str(Path(bundled).parent)
    current_path = os.environ.get("PATH", "")
    path_parts = current_path.split(os.pathsep) if current_path else []
    if bundled_dir not in path_parts:
        os.environ["PATH"] = bundled_dir if not current_path else bundled_dir + os.pathsep + current_path
    return bundled_dir
