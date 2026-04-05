"""Regression tests for MediaHelpers shared-runner convergence."""

from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.core.media_helpers import MediaHelpers
from ravn_app.core.runners.base import RunnerResult


def _write_input_file(path: Path) -> str:
    path.write_bytes(b"demo")
    return str(path)


def test_detect_silence_uses_runner_raw_and_parses_periods(tmp_path):
    input_file = _write_input_file(tmp_path / "audio.mp3")
    helpers = MediaHelpers()

    stderr = "\n".join(
        [
            "[silencedetect @ 000] silence_start: 1.0",
            "[silencedetect @ 000] silence_end: 2.5 | silence_duration: 1.5",
        ]
    )

    with patch.object(
        helpers.runner,
        "run_raw",
        return_value=RunnerResult(success=True, return_code=0, stderr=stderr),
    ) as mock_run_raw:
        result = helpers.detect_silence(input_file)

    assert result.success is True
    assert result.metadata["operation"] == "detect_silence"
    assert result.metadata["silence_periods"] == [(1.0, 2.5, 1.5)]
    mock_run_raw.assert_called_once()


def test_detect_black_frames_uses_runner_raw_and_parses_periods(tmp_path):
    input_file = _write_input_file(tmp_path / "video.mp4")
    helpers = MediaHelpers()

    stderr = "\n".join(
        [
            "[blackdetect @ 000] black_start:1.25 black_end:2.75 black_duration:1.50",
        ]
    )

    with patch.object(
        helpers.runner,
        "run_raw",
        return_value=RunnerResult(success=True, return_code=0, stderr=stderr),
    ) as mock_run_raw:
        result = helpers.detect_black_frames(input_file)

    assert result.success is True
    assert result.metadata["operation"] == "detect_black_frames"
    assert result.metadata["black_periods"] == [(1.25, 2.75, 1.5)]
    mock_run_raw.assert_called_once()


def test_generate_scene_previews_uses_runner_raw_for_detection(tmp_path):
    input_file = _write_input_file(tmp_path / "movie.mp4")
    output_dir = tmp_path / "previews"
    helpers = MediaHelpers()

    stderr = "\n".join(
        [
            "[Parsed_showinfo_0 @ 000] n:1 pts:100 pts_time:1.0 pos:0 fmt:yuv420p showinfo",
            "[Parsed_showinfo_0 @ 000] n:2 pts:500 pts_time:5.0 pos:0 fmt:yuv420p showinfo",
        ]
    )

    with patch.object(
        helpers.runner,
        "run_raw",
        return_value=RunnerResult(success=True, return_code=0, stderr=stderr),
    ) as mock_run_raw, patch.object(
        helpers.runner,
        "run",
        return_value=RunnerResult(success=True, return_code=0),
    ) as mock_run:
        result = helpers.generate_scene_previews(input_file, str(output_dir), scene_count=2)

    assert result.success is True
    assert result.metadata["operation"] == "generate_scene_previews"
    assert len(result.metadata["preview_files"]) == 2
    assert mock_run_raw.call_count == 1
    assert mock_run.call_count == 2


def test_generate_scene_thumbnails_uses_runner_raw_for_detection(tmp_path):
    input_file = _write_input_file(tmp_path / "movie.mp4")
    output_dir = tmp_path / "thumbs"
    helpers = MediaHelpers()

    stderr = "\n".join(
        [
            "[Parsed_showinfo_0 @ 000] n:1 pts:100 pts_time:1.0 pos:0 fmt:yuv420p showinfo",
            "[Parsed_showinfo_0 @ 000] n:2 pts:500 pts_time:5.0 pos:0 fmt:yuv420p showinfo",
        ]
    )

    with patch.object(
        helpers.runner,
        "run_raw",
        return_value=RunnerResult(success=True, return_code=0, stderr=stderr),
    ) as mock_run_raw, patch.object(
        helpers,
        "thumbnail",
        return_value=RunnerResult(success=True, return_code=0),
    ) as mock_thumbnail:
        result = helpers.generate_scene_thumbnails(input_file, str(output_dir), scene_count=2)

    assert result.success is True
    assert result.metadata["operation"] == "generate_scene_thumbnails"
    assert len(result.metadata["thumbnail_files"]) == 2
    assert mock_run_raw.call_count == 1
    assert mock_thumbnail.call_count == 2
