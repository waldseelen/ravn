"""Tests for automatic MediaLibrary registration flows."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

from ravn_app.core.persistence import MediaLibrary, MediaLibraryAutoAdder
from ravn_app.core.task_manager import TaskQueue, TaskResult, TaskType


class _ConfigStub:
    def __init__(self, library_section=None):
        self._library_section = dict(library_section or {})

    def get_section(self, key: str):
        if key == "library":
            return dict(self._library_section)
        return {}


class TestMediaLibraryAutoAdder:
    def _build_auto_adder(self, tmp_path, library_section=None, metadata=None, metadata_handler_factory=None):
        metadata_handler = Mock()
        metadata_handler.extract_metadata.return_value = metadata or {
            "title": "Generated Output",
            "format": "mp4",
            "duration": 12.0,
            "size": 4,
            "codec": "h264",
        }
        auto_adder = MediaLibraryAutoAdder(
            config_manager=_ConfigStub(library_section),
            db_path=str(tmp_path / "library.db"),
            metadata_handler_factory=metadata_handler_factory or (lambda: metadata_handler),
        )
        return auto_adder, metadata_handler

    def test_register_output_adds_media_and_metadata(self, tmp_path):
        output_file = tmp_path / "mix.mp3"
        output_file.write_bytes(b"audio")
        auto_adder, metadata_handler = self._build_auto_adder(
            tmp_path,
            {"auto_add_mixer_output": True},
            metadata={
                "title": "Merged Track",
                "format": "mp3",
                "duration": 8.0,
                "size": output_file.stat().st_size,
                "codec": "mp3",
            },
        )

        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            result = auto_adder.register_output(
                output_file,
                source_type="mixer",
                metadata={"operation": "mix"},
            )
            library = MediaLibrary(db_path=str(tmp_path / "library.db"), metadata_handler=metadata_handler)
            try:
                item = library.get_media(int(result.media_id or 0))
                assert result.added is True
                assert item is not None
                assert "mixed" in item.tags
                assert item.metadata["operation"] == "mix"
                assert item.metadata["source_type"] == "mixer"
            finally:
                library.close()

    def test_register_output_skips_when_disabled(self, tmp_path):
        output_file = tmp_path / "video.mp4"
        output_file.write_bytes(b"video")
        auto_adder, _ = self._build_auto_adder(
            tmp_path,
            {"auto_add_downloads": False},
        )

        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            result = auto_adder.register_output(output_file, source_type="download")

        assert result.added is False
        assert result.skipped_reason == "disabled"

    def test_register_output_is_idempotent_for_existing_file(self, tmp_path):
        output_file = tmp_path / "converted.mp4"
        output_file.write_bytes(b"video")
        auto_adder, metadata_handler = self._build_auto_adder(
            tmp_path,
            {"auto_add_converted_files": True},
        )

        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            first = auto_adder.register_output(output_file, source_type="conversion")
            second = auto_adder.register_output(
                output_file,
                source_type="conversion",
                metadata={"input_file": "source.mov"},
            )
            library = MediaLibrary(db_path=str(tmp_path / "library.db"), metadata_handler=metadata_handler)
            try:
                items = library.list_media(limit=10)
                assert first.added is True
                assert second.added is False
                assert second.skipped_reason == "exists"
                assert len(items) == 1
                assert items[0].metadata["input_file"] == "source.mov"
            finally:
                library.close()

    def test_register_outputs_reuses_one_library_session_per_batch(self, tmp_path):
        output_files = [tmp_path / "one.mp4", tmp_path / "two.mp4"]
        for file_path in output_files:
            file_path.write_bytes(b"video")

        created_handlers = []

        def handler_factory():
            handler = Mock()
            handler.extract_metadata.side_effect = [
                {
                    "title": "One",
                    "format": "mp4",
                    "duration": 3.0,
                    "size": output_files[0].stat().st_size,
                    "codec": "h264",
                },
                {
                    "title": "Two",
                    "format": "mp4",
                    "duration": 4.0,
                    "size": output_files[1].stat().st_size,
                    "codec": "h264",
                },
            ] if not created_handlers else []
            created_handlers.append(handler)
            return handler

        auto_adder, _ = self._build_auto_adder(
            tmp_path,
            {"auto_add_downloads": True},
            metadata_handler_factory=handler_factory,
        )

        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            results = auto_adder.register_outputs(output_files, source_type="download")

        assert len(results) == 2
        assert all(result.added for result in results)
        assert len(created_handlers) == 1
        assert created_handlers[0].extract_metadata.call_count == 2


class TestQueueToLibraryIntegration:
    def test_completed_queue_task_can_register_output_in_library(self, tmp_path):
        output_file = tmp_path / "filtered.mp4"
        output_file.write_bytes(b"video")
        metadata_handler = Mock()
        metadata_handler.extract_metadata.return_value = {
            "title": "Filtered Clip",
            "format": "mp4",
            "duration": 3.0,
            "size": output_file.stat().st_size,
            "codec": "h264",
        }
        auto_adder = MediaLibraryAutoAdder(
            config_manager=_ConfigStub({"auto_add_filter_output": True}),
            db_path=str(tmp_path / "library.db"),
            metadata_handler_factory=lambda: metadata_handler,
        )
        queue = TaskQueue(max_concurrent=1)
        registered = []

        def execute_fn(*args, **kwargs):
            return TaskResult(
                success=True,
                output_path=str(output_file),
                metadata={"filters": ["eq=brightness=0.1"]},
            )

        def on_complete(task):
            registered.extend(
                auto_adder.register_outputs(
                    task.result.output_path,
                    source_type="filters",
                    metadata=task.result.metadata,
                )
            )

        with patch("ravn_app.core.persistence.media_library.ensure_directories_exist"):
            queue.start()
            try:
                queue.add_task(
                    task_type=TaskType.APPLY_FILTERS,
                    name="Filter Task",
                    execute_fn=execute_fn,
                    on_complete=on_complete,
                )
                time.sleep(0.3)
                queue.process_callbacks()

                library = MediaLibrary(db_path=str(tmp_path / "library.db"), metadata_handler=metadata_handler)
                try:
                    items = library.list_media(limit=10)
                    assert len(items) == 1
                    assert items[0].metadata["filters"] == ["eq=brightness=0.1"]
                    assert registered
                    assert registered[0].added is True
                finally:
                    library.close()
            finally:
                queue.stop(wait=True)
