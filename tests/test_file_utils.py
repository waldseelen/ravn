"""Tests for filename/size helper utilities."""

from ravn_app.utils.file_utils import ensure_directory, get_file_size, sanitize_filename


def test_sanitize_filename_strips_invalid_characters():
    assert sanitize_filename('a/b*c?d:e"f<g>h|i') == "abcdefghi"


def test_ensure_directory_creates_missing_path(tmp_path):
    target = tmp_path / "nested" / "dir"

    ensure_directory(str(target))

    assert target.is_dir()


def test_ensure_directory_is_idempotent(tmp_path):
    target = tmp_path / "already-there"
    target.mkdir()

    ensure_directory(str(target))  # should not raise

    assert target.is_dir()


def test_get_file_size_returns_size_for_existing_file(tmp_path):
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"0123456789")

    assert get_file_size(str(sample)) == 10


def test_get_file_size_returns_zero_for_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.bin"

    assert get_file_size(str(missing)) == 0
