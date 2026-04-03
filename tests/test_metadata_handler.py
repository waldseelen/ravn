"""Tests for metadata handling helpers."""

from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.utils.metadata_handler import MetadataHandler


class TestMetadataHandler:
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
