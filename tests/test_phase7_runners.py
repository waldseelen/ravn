"""Tests for Phase 7 runner helpers."""

from unittest.mock import patch

from ravn_app.core.runners import AudioMixerRunner, AudioTrack, RunnerResult, VideoMixerRunner


class TestAudioMixerRunner:
    def _mock_result(self, success: bool = True) -> RunnerResult:
        return RunnerResult(success=success, return_code=0 if success else 1, error_message="" if success else "failed")

    def test_concat_builds_concat_command(self, tmp_path):
        file_a = tmp_path / "a.mp3"
        file_b = tmp_path / "b.mp3"
        file_a.write_bytes(b"a")
        file_b.write_bytes(b"b")

        runner = AudioMixerRunner()
        with patch.object(runner._runner, "run_raw", return_value=self._mock_result()) as mock_run_raw:
            result = runner.concat([str(file_a), str(file_b)], str(tmp_path / "out.mp3"))

        assert result.success is True
        args = mock_run_raw.call_args[0][0]
        assert "-f" in args
        assert "concat" in args
        assert "-c:a" in args
        assert result.metadata["operation"] == "concat"

    def test_mix_builds_filter_complex(self, tmp_path):
        file_a = tmp_path / "a.mp3"
        file_b = tmp_path / "b.mp3"
        file_a.write_bytes(b"a")
        file_b.write_bytes(b"b")

        runner = AudioMixerRunner()
        tracks = [
            AudioTrack(file_path=str(file_a), volume=1.0),
            AudioTrack(file_path=str(file_b), volume=0.5),
        ]
        with patch.object(runner._runner, "run_raw", return_value=self._mock_result()) as mock_run_raw:
            result = runner.mix(tracks, str(tmp_path / "mix.mp3"), normalize=True)

        assert result.success is True
        args = mock_run_raw.call_args[0][0]
        filter_complex = args[args.index("-filter_complex") + 1]
        assert "amix=inputs=2" in filter_complex
        assert "volume=0.5" in filter_complex
        assert "loudnorm" in filter_complex
        assert result.metadata["operation"] == "mix"

    def test_trim_rejects_invalid_params(self, tmp_path):
        file_a = tmp_path / "a.mp3"
        file_a.write_bytes(b"a")
        runner = AudioMixerRunner()

        result = runner.trim(str(file_a), str(tmp_path / "trim.mp3"), start_time=-1, duration=5)

        assert result.success is False
        assert "valid positive values" in result.error_message


class TestVideoMixerRunner:
    def _mock_result(self, success: bool = True) -> RunnerResult:
        return RunnerResult(success=success, return_code=0 if success else 1, error_message="" if success else "failed")

    def test_overlay_builds_overlay_filter(self, tmp_path):
        base = tmp_path / "base.mp4"
        overlay = tmp_path / "overlay.mp4"
        base.write_bytes(b"base")
        overlay.write_bytes(b"overlay")

        runner = VideoMixerRunner()
        with patch.object(runner._runner, "run_raw", return_value=self._mock_result()) as mock_run_raw:
            result = runner.overlay(
                base_file=str(base),
                overlay_file=str(overlay),
                output_file=str(tmp_path / "out.mp4"),
                position="bottom-right",
                scale=0.25,
            )

        assert result.success is True
        args = mock_run_raw.call_args[0][0]
        filter_complex = args[args.index("-filter_complex") + 1]
        assert "overlay=x=" in filter_complex
        assert "scale=iw*0.25" in filter_complex
        assert result.metadata["operation"] == "overlay"

    def test_apply_filters_uses_ffmpeg_run(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_bytes(b"video")

        runner = VideoMixerRunner()
        with patch.object(runner._runner, "run", return_value=self._mock_result()) as mock_run:
            result = runner.apply_filters(
                input_file=str(video),
                output_file=str(tmp_path / "filtered.mp4"),
                brightness=20,
                contrast=1.2,
                blur=2,
                grayscale=True,
            )

        assert result.success is True
        extra_args = mock_run.call_args.kwargs["extra_args"]
        vf_string = extra_args[extra_args.index("-vf") + 1]
        assert "brightness=0.2" in vf_string
        assert "contrast=1.2" in vf_string
        assert "gblur=sigma=2" in vf_string
        assert "format=gray" in vf_string
        assert result.metadata["operation"] == "apply_filters"

    def test_transition_rejects_invalid_duration(self, tmp_path):
        first = tmp_path / "one.mp4"
        second = tmp_path / "two.mp4"
        first.write_bytes(b"1")
        second.write_bytes(b"2")

        runner = VideoMixerRunner()
        result = runner.transition(str(first), str(second), str(tmp_path / "out.mp4"), duration=0)

        assert result.success is False
        assert "greater than zero" in result.error_message
