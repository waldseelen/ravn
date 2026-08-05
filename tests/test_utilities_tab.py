from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from ravn_app.core.task_manager import TaskResult, TaskStatus, TaskType
from ravn_app.ui.tabs.utilities_tab import UtilitiesTab


class _FakeEntry:
    def __init__(self, value: str = ""):
        self.value = value

    def get(self) -> str:
        return self.value

    def delete(self, _start, _end) -> None:
        self.value = ""

    def insert(self, _index, value: str) -> None:
        self.value = value


class _FakeCombo:
    def __init__(self, value: str):
        self._value = value

    def get(self) -> str:
        return self._value


class _FakeButton:
    def __init__(self, text: str = "Process"):
        self._text = text
        self.calls: list[dict] = []

    def cget(self, key: str):
        if key == "text":
            return self._text
        return None

    def configure(self, **kwargs) -> None:
        self.calls.append(kwargs)
        if "text" in kwargs:
            self._text = kwargs["text"]


class _FakeToast:
    def __init__(self):
        self.success: list[str] = []
        self.warning: list[str] = []
        self.error: list[str] = []

    def show_success(self, message: str) -> None:
        self.success.append(message)

    def show_warning(self, message: str) -> None:
        self.warning.append(message)

    def show_error(self, message: str) -> None:
        self.error.append(message)


def _make_tab(tmp_path: Path) -> UtilitiesTab:
    tab = UtilitiesTab.__new__(UtilitiesTab)
    tab.helpers = Mock()
    tab.db_manager = Mock()
    tab.task_queue = Mock()
    tab.animation_manager = None
    tab.show_queue_tab_callback = Mock()
    tab.auto_add_to_library_callback = Mock()
    tab._is_running = False
    tab._active_task_id = None
    tab._active_category = "quick"
    tab._active_task_context = {}
    tab._quick_operations = {
        "remux": "Remux",
        "extract_audio": "Extract Audio",
        "mute": "Mute",
        "trim": "Trim",
        "preview_clip": "Preview Clip",
        "thumbnail": "Thumbnail",
    }
    tab._audio_operations = {
        "adjust_volume": "Volume",
        "fade_audio": "Fade",
        "convert_audio_bitrate": "Bitrate",
        "convert_channels": "Stereo / Mono",
        "detect_silence": "Silence Detect",
        "loudness_normalize": "Loudnorm",
    }
    tab._video_operations = {
        "scale_video": "Scale",
        "crop_video": "Crop",
        "pad_video": "Pad",
        "rotate_video": "Rotate",
        "change_fps": "FPS",
        "adjust_color": "Brightness",
        "blur_sharpen": "Blur",
        "deinterlace": "Deinterlace",
    }
    tab._smart_operations = {
        "detect_black_frames": "Blackdetect",
        "generate_scene_previews": "Scene Preview",
        "generate_scene_thumbnails": "Scene Thumbnail",
    }
    tab.quick_operation = _FakeCombo("Remux")
    tab.audio_operation = _FakeCombo("Volume")
    tab.video_operation = _FakeCombo("Scale")
    tab.smart_operation = _FakeCombo("Blackdetect")
    tab.input_entry = _FakeEntry(str(tmp_path / "input.mp4"))
    tab.output_entry = _FakeEntry("")
    tab.process_btn = _FakeButton()
    toast = _FakeToast()
    tab.toast_manager_getter = lambda: toast
    tab._toast_ref = toast
    return tab


def test_resolve_output_target_uses_operation_specific_defaults(tmp_path: Path) -> None:
    tab = _make_tab(tmp_path)
    input_file = str(tmp_path / "clip.mp4")

    thumb = tab._resolve_output_target(input_file, "thumbnail", "")
    audio = tab._resolve_output_target(input_file, "extract_audio", "")
    scene_dir = tab._resolve_output_target(input_file, "generate_scene_previews", "")
    blackdetect = tab._resolve_output_target(input_file, "detect_black_frames", "")

    assert thumb.endswith("_thumbnail.jpg")
    assert audio.endswith("_extract-audio.mp3")
    assert scene_dir.endswith("_scene_previews")
    assert blackdetect is None


def test_build_operation_call_spec_for_crop_uses_safe_probe_dimensions(tmp_path: Path) -> None:
    tab = _make_tab(tmp_path)
    tab.helpers.runner = Mock()
    tab.helpers.runner.probe.return_value = {
        "streams": [{"codec_type": "video", "width": 1920, "height": 1080}]
    }

    fn, kwargs = tab._build_operation_call_spec("in.mp4", "crop_video", "out.mp4")

    assert fn == tab.helpers.crop_video
    assert kwargs["width"] == 1728
    assert kwargs["height"] == 972
    assert kwargs["x"] == 96
    assert kwargs["y"] == 54


def test_process_operation_queues_task_and_persists_operation(tmp_path: Path) -> None:
    input_file = tmp_path / "input.mp4"
    input_file.write_bytes(b"video")

    tab = _make_tab(tmp_path)
    tab.input_entry = _FakeEntry(str(input_file))
    tab.task_queue.add_task.return_value = "task-123"
    tab.helpers.remux = Mock()
    tab.helpers.runner = Mock()
    tab.helpers.runner.probe.return_value = {"streams": []}

    tab._process_operation()

    assert tab._active_task_id == "task-123"
    tab.task_queue.add_task.assert_called_once()
    call = tab.task_queue.add_task.call_args
    assert call.kwargs["task_type"] == TaskType.GENERIC
    assert call.kwargs["execute_fn"] == tab.helpers.remux
    assert call.kwargs["kwargs"]["input_file"] == str(input_file)
    assert call.kwargs["kwargs"]["output_file"].endswith("_remux.mp4")
    tab.db_manager.add_operation.assert_called_once()
    tab.show_queue_tab_callback.assert_called_once()
    assert tab._toast_ref.success


def test_on_task_complete_persists_and_auto_adds_scene_outputs(tmp_path: Path) -> None:
    tab = _make_tab(tmp_path)
    tab._active_task_id = "task-123"
    tab._active_task_context = {
        "operation": "generate_scene_thumbnails",
        "operation_label": "Scene Thumbnail",
        "input_file": str(tmp_path / "input.mp4"),
        "output_target": str(tmp_path / "thumbs"),
    }
    files = [str(tmp_path / "thumbs" / "a.jpg"), str(tmp_path / "thumbs" / "b.jpg")]
    task = SimpleNamespace(
        id="task-123",
        name="Scene Thumbnail: input.mp4",
        status=TaskStatus.COMPLETED,
        started_at=None,
        completed_at=None,
        result=TaskResult(success=True, output_path=None, metadata={"thumbnail_files": files}),
    )

    tab._on_task_complete(task)

    tab.db_manager.add_operation.assert_called_once()
    tab.auto_add_to_library_callback.assert_called_once()
    payload = tab.auto_add_to_library_callback.call_args.args[0]
    assert payload == files
    assert tab._active_task_id is None
    assert tab._toast_ref.success
