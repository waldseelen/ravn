"""
Async thumbnail loader for RAVN's media surfaces.

Playlist/library entries carry a remote ``thumbnail_url``. Downloading those on the UI
thread would freeze the app, and re-fetching the same image on every render is wasteful,
so this loader:

  1. serves an already-decoded image handle instantly from an in-memory cache,
  2. otherwise reads a previously-downloaded file from the on-disk cache,
  3. otherwise downloads it on a worker thread and reports back via callback.

``request(url, size, on_ready, schedule_on_ui)`` returns a cached handle immediately when
possible; otherwise it returns ``None`` and later calls ``on_ready(image)`` — bridged onto
the Tk main thread through the caller-supplied ``schedule_on_ui`` (e.g. ``widget.after``).

The network fetch and image decode are deliberately split into small overridable methods so
the loader can be unit-tested without a network, Pillow, or a Tk root.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from ravn_app.core.config_paths import get_cache_directory

logger = logging.getLogger(__name__)

_THUMBNAIL_SUBDIR = "thumbnails"
_DOWNLOAD_TIMEOUT = 10


def _thumbnail_cache_dir() -> Path:
    path = get_cache_directory() / _THUMBNAIL_SUBDIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


class ThumbnailLoader:
    """In-memory + on-disk cached async thumbnail loader producing image handles."""

    def __init__(self) -> None:
        # keyed by (url, width, height) so different display sizes stay distinct
        self._image_cache: Dict[Tuple[str, int, int], object] = {}
        self._inflight: set[str] = set()
        self._lock = threading.Lock()

    def get_cached_image(
        self, url: str, size: Tuple[int, int], image_kind: str = "ctk"
    ) -> Optional[object]:
        """Return an already-decoded image handle for this url+size+kind, or None."""
        with self._lock:
            return self._image_cache.get((f"{image_kind}:{url}", size[0], size[1]))

    def request(
        self,
        url: str,
        size: Tuple[int, int],
        on_ready: Callable[[object], None],
        schedule_on_ui: Callable[[Callable[[], None]], None],
        image_kind: str = "ctk",
    ) -> Optional[object]:
        """
        Request a thumbnail. If it's already decoded in memory, return the handle
        immediately (``on_ready`` is NOT called). Otherwise return ``None`` and later
        invoke ``on_ready(image)`` via ``schedule_on_ui`` once the image is ready.

        ``image_kind`` selects the widget-image type: "ctk" (CTkImage, for CTk widgets)
        or "tk" (a tkinter PhotoImage, required by ttk.Treeview rows). The cache key
        includes the kind so the two never collide.
        """
        if not url:
            return None

        cache_url = f"{image_kind}:{url}"
        cached = self.get_cached_image(url, size, image_kind)
        if cached is not None:
            return cached

        with self._lock:
            if cache_url in self._inflight:
                return None
            self._inflight.add(cache_url)

        def worker() -> None:
            try:
                image = self._load_image(url, size, image_kind)
            except Exception as exc:  # pragma: no cover - defensive worker guard
                logger.debug("Thumbnail worker failed for %s: %s", url, exc)
                image = None
            finally:
                with self._lock:
                    self._inflight.discard(url)

            if image is None:
                return
            with self._lock:
                self._image_cache[(cache_url, size[0], size[1])] = image
            try:
                schedule_on_ui(lambda: on_ready(image))
            except Exception:  # pragma: no cover - UI teardown races
                pass

        threading.Thread(target=worker, daemon=True).start()
        return None

    def _load_image(self, url: str, size: Tuple[int, int], image_kind: str = "ctk") -> Optional[object]:
        """Fetch raw bytes then decode into a display image handle. Worker thread only."""
        raw = self._read_or_download(url)
        if raw is None:
            return None
        return self._decode_image(raw, size, image_kind)

    def _decode_image(self, raw: bytes, size: Tuple[int, int], image_kind: str = "ctk") -> Optional[object]:
        """Decode raw bytes into a cover-fitted CTkImage ("ctk") or tk PhotoImage ("tk")."""
        try:
            import io

            from PIL import Image, ImageTk
        except Exception as exc:  # pragma: no cover - deps always present at runtime
            logger.debug("Thumbnail deps unavailable: %s", exc)
            return None

        try:
            pil_image = Image.open(io.BytesIO(raw)).convert("RGB")
            pil_image = self._fit_cover(pil_image, size)
            if image_kind == "tk":
                # ttk.Treeview requires a tkinter PhotoImage; caller must keep a reference.
                return ImageTk.PhotoImage(pil_image)
            import customtkinter as ctk
            return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=size)
        except Exception as exc:
            logger.debug("Thumbnail decode failed: %s", exc)
            return None

    @staticmethod
    def _fit_cover(pil_image, size: Tuple[int, int]):
        """Center-crop to fill the target box (object-fit: cover) so tiles stay uniform."""
        from PIL import Image

        target_w, target_h = size
        src_w, src_h = pil_image.size
        if src_w <= 0 or src_h <= 0:
            return pil_image.resize(size)

        scale = max(target_w / src_w, target_h / src_h)
        new_w, new_h = max(1, int(src_w * scale)), max(1, int(src_h * scale))
        resized = pil_image.resize((new_w, new_h), Image.LANCZOS)

        left = (new_w - target_w) // 2
        top = (new_h - target_h) // 2
        return resized.crop((left, top, left + target_w, top + target_h))

    def _read_or_download(self, url: str) -> Optional[bytes]:
        """Return cached file bytes, or download and cache them. Worker thread only."""
        cache_path = _thumbnail_cache_dir() / f"{_cache_key(url)}.img"
        if cache_path.exists():
            try:
                return cache_path.read_bytes()
            except Exception:  # pragma: no cover - fall through to re-download
                pass

        try:
            import requests

            response = requests.get(url, timeout=_DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            data = response.content
        except Exception as exc:
            logger.debug("Thumbnail download failed for %s: %s", url, exc)
            return None

        try:
            cache_path.write_bytes(data)
        except Exception:  # pragma: no cover - cache write is best-effort
            pass
        return data


_loader: Optional[ThumbnailLoader] = None


def get_thumbnail_loader() -> ThumbnailLoader:
    """Return the process-wide thumbnail loader singleton."""
    global _loader
    if _loader is None:
        _loader = ThumbnailLoader()
    return _loader
