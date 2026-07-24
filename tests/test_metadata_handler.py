"""Tests for metadata handling helpers."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.utils.metadata_handler import MetadataHandler


class TestMetadataHandler:
    def test_extract_metadata_returns_empty_for_missing_file(self, tmp_path):
        handler = MetadataHandler()
        missing = tmp_path / "does-not-exist.mp4"

        assert handler.extract_metadata(str(missing)) == {}

    def test_extract_metadata_returns_empty_when_probe_fails(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        with patch.object(handler._runner, "probe", return_value=None):
            assert handler.extract_metadata(str(media_file)) == {}

    def test_extract_metadata_normalizes_probe_data(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        probe_payload = {
            "format": {
                "duration": "12.5",
                "size": "2048",
                "bit_rate": "1500000",
                "tags": {"title": "Demo Title"},
            },
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2},
            ],
        }
        with patch.object(handler._runner, "probe", return_value=probe_payload):
            metadata = handler.extract_metadata(str(media_file))

        assert metadata["title"] == "Demo Title"
        assert metadata["duration"] == 12.5
        assert metadata["width"] == 1920
        assert metadata["height"] == 1080
        assert metadata["fps"] == 30.0
        assert metadata["sample_rate"] == 48000

    def test_read_tags_returns_empty_when_mutagen_unavailable(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        handler = MetadataHandler()
        with patch("ravn_app.utils.metadata_handler.MutagenFile", None):
            assert handler.read_tags(str(media_file)) == {}

    def test_read_tags_returns_empty_when_mutagen_raises(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        handler = MetadataHandler()
        with patch(
            "ravn_app.utils.metadata_handler.MutagenFile",
            side_effect=OSError("corrupt file"),
        ):
            assert handler.read_tags(str(media_file)) == {}

    def test_read_tags_returns_empty_when_media_has_no_tags(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        handler = MetadataHandler()
        with patch("ravn_app.utils.metadata_handler.MutagenFile", return_value=None):
            assert handler.read_tags(str(media_file)) == {}

    def test_read_tags_flattens_single_item_lists(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        fake_media = Mock()
        fake_media.tags = {"title": ["Demo"], "genre": ["Rock", "Pop"]}

        handler = MetadataHandler()
        with patch("ravn_app.utils.metadata_handler.MutagenFile", return_value=fake_media):
            tags = handler.read_tags(str(media_file))

        assert tags["title"] == "Demo"
        assert tags["genre"] == ["Rock", "Pop"]

    def test_write_tags_returns_true_for_empty_tags(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        handler = MetadataHandler()
        assert handler.write_tags(str(media_file), {}) is True

    def test_write_tags_returns_false_for_missing_file(self, tmp_path):
        handler = MetadataHandler()
        missing = tmp_path / "does-not-exist.mp3"

        assert handler.write_tags(str(missing), {"title": "Demo"}) is False

    def test_write_tags_uses_mutagen_when_supported_extension(self, tmp_path):
        media_file = tmp_path / "sample.mp3"
        media_file.write_bytes(b"audio")

        fake_media = {}
        fake_media_obj = Mock()
        fake_media_obj.__setitem__ = Mock(side_effect=fake_media.__setitem__)
        fake_media_obj.save = Mock()

        handler = MetadataHandler()
        with patch("ravn_app.utils.metadata_handler.MutagenFile", return_value=fake_media_obj):
            success = handler.write_tags(str(media_file), {"title": "Demo", "artist": None})

        assert success is True
        fake_media_obj.save.assert_called_once()
        assert fake_media["title"] == ["Demo"]
        assert "artist" not in fake_media

    def test_write_tags_skips_none_values_in_ffmpeg_fallback(self, tmp_path):
        media_file = tmp_path / "sample.mkv"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()

        def _run_raw_side_effect(args):
            Path(args[-1]).write_bytes(b"updated")
            return Mock(success=True)

        with patch("ravn_app.utils.metadata_handler.MutagenFile", None), patch.object(
            handler._runner,
            "run_raw",
            side_effect=_run_raw_side_effect,
        ) as mock_run_raw:
            handler.write_tags(str(media_file), {"title": "Updated", "artist": None})

        args = mock_run_raw.call_args[0][0]
        assert "artist=" not in " ".join(str(a) for a in args)

    def test_write_tags_removes_temp_file_when_ffmpeg_fails(self, tmp_path):
        media_file = tmp_path / "sample.mkv"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        with patch("ravn_app.utils.metadata_handler.MutagenFile", None), patch.object(
            handler._runner, "run_raw", return_value=Mock(success=False)
        ):
            success = handler.write_tags(str(media_file), {"title": "Updated"})

        assert success is False
        assert media_file.exists()  # original file untouched
        assert not (tmp_path / "sample.ravn_meta.mkv").exists()

    def test_write_tags_falls_back_to_ffmpeg_metadata(self, tmp_path):
        media_file = tmp_path / "sample.mkv"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()

        def _run_raw_side_effect(args):
            Path(args[-1]).write_bytes(b"updated")
            return Mock(success=True)

        with patch("ravn_app.utils.metadata_handler.MutagenFile", None), patch.object(
            handler._runner,
            "run_raw",
            side_effect=_run_raw_side_effect,
        ) as mock_run_raw:
            success = handler.write_tags(str(media_file), {"title": "Updated"})

        assert success is True
        args = mock_run_raw.call_args[0][0]
        assert "-metadata" in args
        assert any(str(arg).startswith("title=Updated") for arg in args)

    def test_generate_thumbnail_invokes_ffmpeg(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        thumb_file = tmp_path / "thumb.jpg"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        with patch.object(handler._runner, "run_raw", return_value=Mock(success=True)) as mock_run_raw:
            success = handler.generate_thumbnail(str(media_file), str(thumb_file), timestamp=1.5, width=160, height=90)

        assert success is True
        args = mock_run_raw.call_args[0][0]
        assert "-ss" in args
        assert "1.5" in args
        assert "scale=160:90" in args

    def test_generate_thumbnail_returns_false_for_missing_input(self, tmp_path):
        handler = MetadataHandler()
        missing = tmp_path / "does-not-exist.mp4"

        assert handler.generate_thumbnail(str(missing), str(tmp_path / "thumb.jpg")) is False

    def test_generate_thumbnail_derives_timestamp_from_duration(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        thumb_file = tmp_path / "thumb.jpg"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        with patch.object(handler._runner, "get_duration", return_value=20.0), patch.object(
            handler._runner, "run_raw", return_value=Mock(success=True)
        ) as mock_run_raw:
            success = handler.generate_thumbnail(str(media_file), str(thumb_file))

        assert success is True
        args = mock_run_raw.call_args[0][0]
        assert "-ss" in args
        assert "2.0" in args  # 10% of a 20s duration

    def test_extract_cover_art_returns_false_for_missing_input(self, tmp_path):
        handler = MetadataHandler()
        missing = tmp_path / "does-not-exist.mp4"

        assert handler.extract_cover_art(str(missing), str(tmp_path / "cover.jpg")) is False

    def test_extract_cover_art_invokes_ffmpeg(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        cover_file = tmp_path / "cover.jpg"
        media_file.write_bytes(b"video")

        handler = MetadataHandler()
        with patch.object(handler._runner, "run_raw", return_value=Mock(success=True)) as mock_run_raw:
            success = handler.extract_cover_art(str(media_file), str(cover_file))

        assert success is True
        assert cover_file.parent.exists()
        args = mock_run_raw.call_args[0][0]
        assert "-map" in args
        assert "0:v:0" in args

    def test_export_metadata_returns_false_when_extraction_empty(self, tmp_path):
        handler = MetadataHandler()
        missing = tmp_path / "does-not-exist.mp4"

        assert handler.export_metadata(str(missing), str(tmp_path / "out.json")) is False

    def test_export_metadata_writes_json_file(self, tmp_path):
        media_file = tmp_path / "sample.mp4"
        media_file.write_bytes(b"video")
        output_file = tmp_path / "meta" / "out.json"

        handler = MetadataHandler()
        probe_payload = {"format": {"tags": {"title": "Demo"}}, "streams": []}
        with patch.object(handler._runner, "probe", return_value=probe_payload):
            success = handler.export_metadata(str(media_file), str(output_file))

        assert success is True
        written = json.loads(output_file.read_text(encoding="utf-8"))
        assert written["title"] == "Demo"


class TestMetadataHandlerStaticHelpers:
    def test_parse_fps_returns_zero_for_empty_value(self):
        assert MetadataHandler._parse_fps("") == 0.0

    def test_parse_fps_handles_fraction(self):
        assert MetadataHandler._parse_fps("30/1") == 30.0

    def test_parse_fps_returns_zero_for_malformed_fraction(self):
        assert MetadataHandler._parse_fps("abc/def") == 0.0

    def test_parse_fps_returns_zero_when_denominator_is_zero(self):
        assert MetadataHandler._parse_fps("30/0") == 0.0

    def test_parse_fps_handles_plain_number(self):
        assert MetadataHandler._parse_fps("25") == 25.0

    def test_to_float_returns_default_for_invalid_value(self):
        assert MetadataHandler._to_float("not-a-number") == 0.0
        assert MetadataHandler._to_float(None, default=1.5) == 1.5

    def test_to_int_returns_default_for_invalid_value(self):
        assert MetadataHandler._to_int("not-a-number") == 0
        assert MetadataHandler._to_int(None, default=7) == 7
