"""Unit tests for the pure subtitle logic (language resolution, format detection)."""

import pytest

from ravn_app.core.subtitle_manager import (
    SubtitleDownloader,
    SubtitleFormat,
    _match_language_code,
    _normalize_language_code,
    _unique_language_order,
    count_subtitle_lines,
    detect_subtitle_format,
)


class TestNormalizeLanguageCode:
    @pytest.mark.parametrize("value,expected", [
        ("TR", "tr"),
        ("  en  ", "en"),
        ("pt_BR", "pt-br"),
        ("en_US", "en-us"),
        ("", ""),
        (None, ""),
        ("none", ""),
        ("off", ""),
        ("disabled", ""),
    ])
    def test_normalizes(self, value, expected):
        assert _normalize_language_code(value) == expected


class TestUniqueLanguageOrder:
    def test_dedupes_preserving_order(self):
        assert _unique_language_order("tr", "en", "TR", "", "en", "de") == ["tr", "en", "de"]

    def test_drops_empty_and_disabled(self):
        assert _unique_language_order("", "off", None, "en") == ["en"]


class TestMatchLanguageCode:
    def test_exact_match_returns_original_casing(self):
        available = {"en": "en", "tr": "TR"}
        assert _match_language_code("tr", available) == "TR"

    def test_region_variant_matches_base(self):
        available = {"pt-br": "pt-BR"}
        assert _match_language_code("pt", available) == "pt-BR"

    def test_base_matches_region_variant_request(self):
        available = {"en": "en"}
        assert _match_language_code("en-us", available) == "en"

    def test_no_match_returns_none(self):
        assert _match_language_code("de", {"en": "en"}) is None

    def test_empty_preferred_returns_none(self):
        assert _match_language_code("", {"en": "en"}) is None


class TestResolveDownloadPlan:
    def test_none_info_uses_requested_defaults(self):
        plan = SubtitleDownloader.resolve_download_plan(None, preferred_language="tr", fallback_language="en")
        assert plan.requested_languages == ["tr", "en"]
        assert plan.preferred_language == "tr"
        assert plan.fallback_language == "en"
        assert plan.use_auto_generated is True

    def test_prefers_manual_subtitle_when_available(self):
        info = {"subtitles": {"tr": [{}], "en": [{}]}, "automatic_captions": {"tr": [{}]}}
        plan = SubtitleDownloader.resolve_download_plan(info, preferred_language="tr", fallback_language="en")
        assert plan.requested_languages == ["tr"]
        assert plan.use_auto_generated is False

    def test_falls_back_to_second_language_manual(self):
        info = {"subtitles": {"en": [{}]}, "automatic_captions": {}}
        plan = SubtitleDownloader.resolve_download_plan(info, preferred_language="tr", fallback_language="en")
        assert plan.requested_languages == ["en"]
        assert plan.use_auto_generated is False

    def test_region_variant_manual_match(self):
        info = {"subtitles": {"pt-BR": [{}]}, "automatic_captions": {}}
        plan = SubtitleDownloader.resolve_download_plan(info, preferred_language="pt", fallback_language="en")
        assert plan.requested_languages == ["pt-BR"]


class TestDetectSubtitleFormat:
    @pytest.mark.parametrize("path,expected", [
        ("movie.srt", SubtitleFormat.SRT),
        ("movie.VTT", SubtitleFormat.VTT),
        ("movie.ass", SubtitleFormat.ASS),
        ("movie.ssa", SubtitleFormat.SSA),
        ("movie.sub", SubtitleFormat.SUB),
        ("movie.txt", None),
        ("noext", None),
    ])
    def test_detects_by_extension(self, path, expected):
        assert detect_subtitle_format(path) == expected


class TestCountSubtitleLines:
    def test_counts_non_index_content_lines(self, tmp_path):
        srt = tmp_path / "s.srt"
        srt.write_text(
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n\n"
            "2\n00:00:03,000 --> 00:00:04,000\nWorld\n",
            encoding="utf-8",
        )
        # counts non-empty, non-pure-digit lines: 2 timestamps + 2 text = 4
        assert count_subtitle_lines(str(srt)) == 4

    def test_missing_file_returns_zero(self, tmp_path):
        assert count_subtitle_lines(str(tmp_path / "nope.srt")) == 0
