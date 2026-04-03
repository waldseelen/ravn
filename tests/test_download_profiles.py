"""Tests for reusable download profile helpers."""

from ravn_app.core.download_profiles import (
    apply_profile_overrides,
    get_download_profile,
    resolve_profile_output_dir,
)


def test_music_profile_overrides_download_settings() -> None:
    profile = get_download_profile("music")
    merged = apply_profile_overrides(
        {
            "embed_metadata": False,
            "auto_sort_enabled": False,
            "auto_sort_mode": "channel",
            "auto_subtitle_download": True,
            "naming_preset": "standard",
            "postprocess_profile": {"convert_enabled": True, "convert_format": "mkv"},
        },
        profile,
    )

    assert merged["embed_metadata"] is True
    assert merged["auto_sort_enabled"] is True
    assert merged["auto_sort_mode"] == "artist"
    assert merged["auto_subtitle_download"] is False
    assert merged["naming_preset"] == "clean"
    assert merged["audio_bitrate"] == "320K"


def test_archive_profile_resolves_output_dir_and_postprocess() -> None:
    profile = get_download_profile("archive")
    merged = apply_profile_overrides(
        {
            "postprocess_profile": {"extract_audio": False},
        },
        profile,
    )

    assert resolve_profile_output_dir("C:/Downloads/RAVN", profile).endswith("Archive")
    assert merged["postprocess_profile"]["embed_subtitles"] is True
    assert merged["auto_subtitle_download"] is True


def test_unknown_profile_falls_back_to_custom() -> None:
    profile = get_download_profile("does-not-exist")
    assert profile.key == "custom"
