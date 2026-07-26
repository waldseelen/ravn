"""
RAVN - Media Downloader
YouTube indirici ve medya yönetim aracı
"""

__version__ = "1.4.0"
__author__ = "RAVN Project"

# These re-exports are resolved lazily (PEP 562). Importing them eagerly here made
# *any* `from ravn_app import __version__` -- which core modules like
# core/crash_reporter.py do -- pull in the whole customtkinter/Tk GUI stack, which
# the CLI and headless entry points have no use for. Attribute access still works
# (`from ravn_app import YouTubeDownloaderApp`), it just no longer costs a GUI import.
__all__ = ["YouTubeDownloader", "YouTubeDownloaderApp"]

_LAZY_EXPORTS = {
    "YouTubeDownloader": ("ravn_app.core.downloader", "YouTubeDownloader"),
    "YouTubeDownloaderApp": ("ravn_app.ui.main_window", "YouTubeDownloaderApp"),
}


def __getattr__(name: str):
    """Resolve the public re-exports on first access instead of at import time."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    value = getattr(import_module(target[0]), target[1])
    globals()[name] = value  # cache so subsequent lookups skip __getattr__
    return value


def __dir__():
    return sorted([*globals().keys(), *_LAZY_EXPORTS])
