"""
Thumbnail loader testleri — bellek/disk cache, asenkron indirme köprüsü ve
cover-fit davranışı (ağ, Pillow ve Tk root olmadan, mock'lu).
"""

import threading
from unittest.mock import Mock, patch

from ravn_app.ui.components import thumbnail_loader
from ravn_app.ui.components.thumbnail_loader import ThumbnailLoader, get_thumbnail_loader


class TestCaching:
    def test_get_cached_image_returns_none_when_empty(self):
        loader = ThumbnailLoader()
        assert loader.get_cached_image("http://x/a.jpg", (112, 63)) is None

    def test_request_returns_cached_handle_without_calling_on_ready(self):
        loader = ThumbnailLoader()
        sentinel = object()
        loader._image_cache[("ctk:http://x/a.jpg", 112, 63)] = sentinel

        on_ready = Mock()
        result = loader.request("http://x/a.jpg", (112, 63), on_ready, schedule_on_ui=Mock())

        assert result is sentinel
        on_ready.assert_not_called()

    def test_empty_url_returns_none(self):
        loader = ThumbnailLoader()
        assert loader.request("", (112, 63), Mock(), Mock()) is None


class TestAsyncRequest:
    def _run_synchronously(self, loader):
        """Force the worker thread to run inline so the test is deterministic."""
        started = []

        class _InlineThread:
            def __init__(self, target, daemon=None):
                self._target = target

            def start(self):
                started.append(True)
                self._target()

        return patch.object(threading, "Thread", _InlineThread), started

    def test_downloads_and_delivers_via_schedule_on_ui(self):
        loader = ThumbnailLoader()
        decoded = object()
        delivered = []

        thread_patch, _started = self._run_synchronously(loader)
        with thread_patch, patch.object(loader, "_load_image", return_value=decoded):
            result = loader.request(
                "http://x/a.jpg",
                (112, 63),
                on_ready=lambda img: delivered.append(img),
                schedule_on_ui=lambda fn: fn(),  # run immediately, like after(0, fn)
            )

        assert result is None  # not cached yet -> async path
        assert delivered == [decoded]
        # subsequent request is served from cache synchronously
        assert loader.get_cached_image("http://x/a.jpg", (112, 63)) is decoded

    def test_failed_decode_does_not_cache_or_deliver(self):
        loader = ThumbnailLoader()
        delivered = []

        thread_patch, _ = self._run_synchronously(loader)
        with thread_patch, patch.object(loader, "_load_image", return_value=None):
            loader.request(
                "http://x/bad.jpg",
                (112, 63),
                on_ready=lambda img: delivered.append(img),
                schedule_on_ui=lambda fn: fn(),
            )

        assert delivered == []
        assert loader.get_cached_image("http://x/bad.jpg", (112, 63)) is None

    def test_inflight_dedupes_concurrent_requests(self):
        loader = ThumbnailLoader()
        loader._inflight.add("ctk:http://x/a.jpg")  # pretend a download is already running

        result = loader.request("http://x/a.jpg", (112, 63), Mock(), Mock())
        assert result is None  # deduped, no second worker

    def test_ctk_and_tk_image_kinds_do_not_collide_in_cache(self):
        loader = ThumbnailLoader()
        ctk_img, tk_img = object(), object()
        loader._image_cache[("ctk:http://x/a.jpg", 60, 34)] = ctk_img
        loader._image_cache[("tk:http://x/a.jpg", 60, 34)] = tk_img

        assert loader.get_cached_image("http://x/a.jpg", (60, 34), "ctk") is ctk_img
        assert loader.get_cached_image("http://x/a.jpg", (60, 34), "tk") is tk_img

    def test_tk_kind_requests_a_separate_download_from_ctk(self):
        loader = ThumbnailLoader()
        # A ctk download already in flight must NOT dedupe a tk request for the same url.
        loader._inflight.add("ctk:http://x/a.jpg")

        thread_patch, _ = self._run_synchronously(loader)
        with thread_patch, patch.object(loader, "_load_image", return_value=object()) as load_mock:
            loader.request(
                "http://x/a.jpg", (60, 34),
                on_ready=lambda img: None, schedule_on_ui=lambda fn: fn(),
                image_kind="tk",
            )
        load_mock.assert_called_once()
        assert load_mock.call_args[0][2] == "tk"  # image_kind threaded through


class TestReadOrDownload:
    def test_returns_cached_file_without_network(self, tmp_path):
        loader = ThumbnailLoader()
        cache_file = tmp_path / "abc.img"
        cache_file.write_bytes(b"cached-bytes")

        with patch.object(thumbnail_loader, "_thumbnail_cache_dir", return_value=tmp_path), \
             patch.object(thumbnail_loader, "_cache_key", return_value="abc"):
            data = loader._read_or_download("http://x/a.jpg")

        assert data == b"cached-bytes"

    def test_downloads_and_writes_cache_on_miss(self, tmp_path):
        loader = ThumbnailLoader()
        fake_resp = Mock(content=b"downloaded")
        fake_resp.raise_for_status = Mock()
        fake_requests = Mock(get=Mock(return_value=fake_resp))

        with patch.object(thumbnail_loader, "_thumbnail_cache_dir", return_value=tmp_path), \
             patch.object(thumbnail_loader, "_cache_key", return_value="def"), \
             patch.dict("sys.modules", {"requests": fake_requests}):
            data = loader._read_or_download("http://x/new.jpg")

        assert data == b"downloaded"
        assert (tmp_path / "def.img").read_bytes() == b"downloaded"

    def test_network_failure_returns_none(self, tmp_path):
        loader = ThumbnailLoader()
        fake_requests = Mock(get=Mock(side_effect=OSError("no net")))

        with patch.object(thumbnail_loader, "_thumbnail_cache_dir", return_value=tmp_path), \
             patch.object(thumbnail_loader, "_cache_key", return_value="ghi"), \
             patch.dict("sys.modules", {"requests": fake_requests}):
            data = loader._read_or_download("http://x/fail.jpg")

        assert data is None


class TestSingleton:
    def test_get_thumbnail_loader_returns_same_instance(self):
        assert get_thumbnail_loader() is get_thumbnail_loader()
