"""Utilities tab for quick media helpers and smart operations."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.database import OperationRecord
from ravn_app.core.i18n import t
from ravn_app.core.media_helpers import MediaHelpers
from ravn_app.core.task_manager import Task, TaskQueue, TaskType
from ravn_app.ui.components.collapsible_panel import CollapsiblePanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import bind_focus_ring, set_button_loading_state, style_combo, style_entry


class UtilitiesTab(ctk.CTkFrame):
    """Media utility helpers with progressive disclosure UI."""

    def __init__(
        self,
        parent,
        config_manager: Any,
        db_manager: Any,
        task_queue: TaskQueue,
        animation_manager: Any,
        toast_manager_getter: Callable[[], Any],
        show_queue_tab_callback: Optional[Callable[[], None]] = None,
        auto_add_to_library_callback: Optional[Callable[..., None]] = None,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.config_manager = config_manager
        self.db_manager = db_manager
        self.task_queue = task_queue
        self.animation_manager = animation_manager
        self.toast_manager_getter = toast_manager_getter
        self.show_queue_tab_callback = show_queue_tab_callback
        self.auto_add_to_library_callback = auto_add_to_library_callback

        ffmpeg_path = self.config_manager.get("ffmpeg_path", "ffmpeg") if self.config_manager else "ffmpeg"
        self.helpers = MediaHelpers(ffmpeg_path=ffmpeg_path)

        self._is_running = False
        self._active_task_id: Optional[str] = None
        self._active_category = "quick"
        self._active_task_context: dict[str, Any] = {}
        self._quick_operations: dict[str, str] = {}
        self._audio_operations: dict[str, str] = {}
        self._video_operations: dict[str, str] = {}
        self._smart_operations: dict[str, str] = {}

        self._setup_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the utilities UI with progressive disclosure."""
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header,
            text=f"{Icons.FILTERS} {t('utilities.title')}",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=t("utilities.subtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        io_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        io_frame.pack(fill="x", pady=Spacing.SM)

        io_inner = ctk.CTkFrame(io_frame, fg_color="transparent")
        io_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        ctk.CTkLabel(
            io_inner,
            text=t("utilities.inputFileLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        input_row = ctk.CTkFrame(io_inner, fg_color="transparent")
        input_row.pack(fill="x", pady=(Spacing.XS, Spacing.SM))

        self.input_entry = ctk.CTkEntry(
            input_row,
            placeholder_text=t("utilities.dropHint"),
            font=Fonts.LABEL,
        )
        style_entry(self.input_entry)
        bind_focus_ring(self.input_entry)
        self.input_entry.configure(cursor=Cursors.TEXT)
        self.input_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        ctk.CTkButton(
            input_row,
            text=Icons.BROWSE,
            width=40,
            command=self._browse_input,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        ctk.CTkLabel(
            io_inner,
            text=t("utilities.outputFileLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        output_row = ctk.CTkFrame(io_inner, fg_color="transparent")
        output_row.pack(fill="x", pady=(Spacing.XS, 0))

        self.output_entry = ctk.CTkEntry(
            output_row,
            placeholder_text=t("converter.outputPlaceholder"),
            font=Fonts.LABEL,
        )
        style_entry(self.output_entry)
        bind_focus_ring(self.output_entry)
        self.output_entry.configure(cursor=Cursors.TEXT)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        ctk.CTkButton(
            output_row,
            text=Icons.BROWSE,
            width=40,
            command=self._browse_output,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        self.quick_panel = CollapsiblePanel(
            content,
            title=t("utilities.quickHelpersTitle"),
            subtitle="remux • extract-audio • mute • trim • preview • thumbnail",
            expanded=True,
        )
        self.quick_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_quick_helpers(self.quick_panel.content_frame())

        self.audio_panel = CollapsiblePanel(
            content,
            title=t("utilities.audioUtilityTitle"),
            subtitle="volume • fade • bitrate • channels • silence • loudnorm",
            expanded=False,
        )
        self.audio_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_audio_utilities(self.audio_panel.content_frame())

        self.video_panel = CollapsiblePanel(
            content,
            title=t("utilities.videoUtilityTitle"),
            subtitle="scale • crop • pad • rotate • fps • color • blur/sharpen • deinterlace",
            expanded=False,
        )
        self.video_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_video_utilities(self.video_panel.content_frame())

        self.smart_panel = CollapsiblePanel(
            content,
            title=t("utilities.smartHelpersTitle"),
            subtitle="blackdetect • scene-preview • scene-thumbnail",
            expanded=False,
        )
        self.smart_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_smart_helpers(self.smart_panel.content_frame())

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(Spacing.MD, 0))

        self.process_btn = ctk.CTkButton(
            btn_frame,
            text=t("utilities.process"),
            command=self._process_operation,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.process_btn.pack(side="left", fill="x", expand=True)

    def _build_quick_helpers(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self._quick_operations = {
            "remux": t("utilities.remux"),
            "extract_audio": t("utilities.extractAudio"),
            "mute": t("utilities.mute"),
            "trim": t("utilities.trim"),
            "preview_clip": t("utilities.previewClip"),
            "thumbnail": t("utilities.thumbnail"),
        }
        self.quick_operation = ctk.CTkComboBox(
            parent,
            values=list(self._quick_operations.values()),
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=lambda value: self._on_operation_change("quick", value),
        )
        style_combo(self.quick_operation)
        self.quick_operation.set(self._quick_operations["remux"])
        self.quick_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.quick_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.quick_params_frame.pack(fill="x")

    def _build_audio_utilities(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self._audio_operations = {
            "adjust_volume": t("utilities.volume"),
            "fade_audio": t("utilities.fade"),
            "convert_audio_bitrate": t("utilities.bitrate"),
            "convert_channels": t("utilities.stereoMono"),
            "detect_silence": t("utilities.silenceDetect"),
            "loudness_normalize": t("utilities.loudnorm"),
        }
        self.audio_operation = ctk.CTkComboBox(
            parent,
            values=list(self._audio_operations.values()),
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=lambda value: self._on_operation_change("audio", value),
        )
        style_combo(self.audio_operation)
        self.audio_operation.set(self._audio_operations["adjust_volume"])
        self.audio_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.audio_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.audio_params_frame.pack(fill="x")

    def _build_video_utilities(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self._video_operations = {
            "scale_video": t("utilities.scale"),
            "crop_video": t("utilities.crop"),
            "pad_video": t("utilities.pad"),
            "rotate_video": t("utilities.rotate"),
            "change_fps": t("utilities.fps"),
            "adjust_color": t("utilities.brightness"),
            "blur_sharpen": t("utilities.blur"),
            "deinterlace": t("utilities.deinterlace"),
        }
        self.video_operation = ctk.CTkComboBox(
            parent,
            values=list(self._video_operations.values()),
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=lambda value: self._on_operation_change("video", value),
        )
        style_combo(self.video_operation)
        self.video_operation.set(self._video_operations["scale_video"])
        self.video_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.video_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.video_params_frame.pack(fill="x")

    def _build_smart_helpers(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self._smart_operations = {
            "detect_black_frames": t("utilities.blackdetect"),
            "generate_scene_previews": t("utilities.scenePreview"),
            "generate_scene_thumbnails": t("utilities.sceneThumbnail"),
        }
        self.smart_operation = ctk.CTkComboBox(
            parent,
            values=list(self._smart_operations.values()),
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=lambda value: self._on_operation_change("smart", value),
        )
        style_combo(self.smart_operation)
        self.smart_operation.set(self._smart_operations["detect_black_frames"])
        self.smart_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.smart_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.smart_params_frame.pack(fill="x")

    # ------------------------------------------------------------------
    # Helpers / selection
    # ------------------------------------------------------------------

    def _on_operation_change(self, category: str, _value: str) -> None:
        self._active_category = category

    @staticmethod
    def _operation_key_from_label(label: str, mapping: dict[str, str], default_key: str) -> str:
        for key, value in mapping.items():
            if value == label:
                return key
        return default_key

    def _selected_operation_key(self) -> str:
        if self._active_category == "audio":
            return self._operation_key_from_label(
                self.audio_operation.get(),
                self._audio_operations,
                "adjust_volume",
            )
        if self._active_category == "video":
            return self._operation_key_from_label(
                self.video_operation.get(),
                self._video_operations,
                "scale_video",
            )
        if self._active_category == "smart":
            return self._operation_key_from_label(
                self.smart_operation.get(),
                self._smart_operations,
                "detect_black_frames",
            )
        return self._operation_key_from_label(
            self.quick_operation.get(),
            self._quick_operations,
            "remux",
        )

    def _selected_operation_label(self) -> str:
        key = self._selected_operation_key()
        catalogs = {
            **self._quick_operations,
            **self._audio_operations,
            **self._video_operations,
            **self._smart_operations,
        }
        return catalogs.get(key, key.replace("_", " ").title())

    @staticmethod
    def _operation_slug(operation_key: str) -> str:
        return operation_key.replace("_", "-")

    def _is_detection_operation(self, operation_key: str) -> bool:
        return operation_key in {"detect_silence", "detect_black_frames"}

    def _is_directory_output_operation(self, operation_key: str) -> bool:
        return operation_key in {"generate_scene_previews", "generate_scene_thumbnails"}

    def _suggested_output_target(self, input_path: Path, operation_key: str) -> str:
        slug = self._operation_slug(operation_key)
        if operation_key == "extract_audio":
            return str(input_path.with_name(f"{input_path.stem}_{slug}.mp3"))
        if operation_key == "preview_clip":
            return str(input_path.with_name(f"{input_path.stem}_{slug}.mp4"))
        if operation_key == "thumbnail":
            return str(input_path.with_name(f"{input_path.stem}_{slug}.jpg"))
        if self._is_directory_output_operation(operation_key):
            suffix = "scene_previews" if operation_key == "generate_scene_previews" else "scene_thumbnails"
            return str(input_path.parent / f"{input_path.stem}_{suffix}")
        return str(input_path.with_name(f"{input_path.stem}_{slug}{input_path.suffix}"))

    def _resolve_output_target(self, input_file: str, operation_key: str, raw_output: str) -> Optional[str]:
        input_path = Path(input_file)
        if self._is_detection_operation(operation_key):
            return None
        if raw_output:
            return raw_output
        suggested = self._suggested_output_target(input_path, operation_key)
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, suggested)
        return suggested

    def _probe_dimensions(self, input_file: str) -> tuple[Optional[int], Optional[int]]:
        try:
            data = self.helpers.runner.probe(input_file)
        except Exception:
            return None, None
        if not isinstance(data, dict):
            return None, None
        for stream in data.get("streams", []):
            if stream.get("codec_type") == "video":
                width = stream.get("width")
                height = stream.get("height")
                if isinstance(width, int) and isinstance(height, int):
                    return width, height
        return None, None

    @staticmethod
    def _even(value: int) -> int:
        return value if value % 2 == 0 else value - 1

    def _build_operation_call_spec(
        self,
        input_file: str,
        operation_key: str,
        output_target: Optional[str],
    ) -> tuple[Callable[..., Any], dict[str, Any]]:
        width, height = self._probe_dimensions(input_file)

        if operation_key == "remux":
            return self.helpers.remux, {"input_file": input_file, "output_file": output_target}
        if operation_key == "extract_audio":
            return self.helpers.extract_audio, {
                "input_file": input_file,
                "output_file": output_target,
                "audio_codec": "mp3",
                "audio_bitrate": "192k",
            }
        if operation_key == "mute":
            return self.helpers.mute, {"input_file": input_file, "output_file": output_target}
        if operation_key == "trim":
            return self.helpers.trim, {
                "input_file": input_file,
                "output_file": output_target,
                "start_time": 0.0,
                "duration": 30.0,
            }
        if operation_key == "preview_clip":
            return self.helpers.preview_clip, {
                "input_file": input_file,
                "output_file": output_target,
                "duration": 10.0,
                "start_time": 0.0,
            }
        if operation_key == "thumbnail":
            return self.helpers.thumbnail, {
                "input_file": input_file,
                "output_file": output_target,
                "timestamp": 1.0,
                "width": 640,
            }
        if operation_key == "adjust_volume":
            return self.helpers.adjust_volume, {
                "input_file": input_file,
                "output_file": output_target,
                "volume_db": 3.0,
            }
        if operation_key == "fade_audio":
            return self.helpers.fade_audio, {
                "input_file": input_file,
                "output_file": output_target,
                "fade_in_duration": 2.0,
                "fade_out_duration": 2.0,
            }
        if operation_key == "convert_audio_bitrate":
            return self.helpers.convert_audio_bitrate, {
                "input_file": input_file,
                "output_file": output_target,
                "audio_bitrate": "192k",
                "sample_rate": 44100,
            }
        if operation_key == "convert_channels":
            return self.helpers.convert_channels, {
                "input_file": input_file,
                "output_file": output_target,
                "channels": 2,
            }
        if operation_key == "detect_silence":
            return self.helpers.detect_silence, {
                "input_file": input_file,
                "noise_threshold_db": -50.0,
                "min_duration": 0.5,
            }
        if operation_key == "loudness_normalize":
            return self.helpers.loudness_normalize, {
                "input_file": input_file,
                "output_file": output_target,
            }
        if operation_key == "scale_video":
            return self.helpers.scale_video, {
                "input_file": input_file,
                "output_file": output_target,
                "width": 1280,
                "height": None,
            }
        if operation_key == "crop_video":
            crop_width = self._even(max(2, int((width or 1280) * 0.9)))
            crop_height = self._even(max(2, int((height or 720) * 0.9)))
            crop_x = max(((width or crop_width) - crop_width) // 2, 0)
            crop_y = max(((height or crop_height) - crop_height) // 2, 0)
            return self.helpers.crop_video, {
                "input_file": input_file,
                "output_file": output_target,
                "width": crop_width,
                "height": crop_height,
                "x": crop_x,
                "y": crop_y,
            }
        if operation_key == "pad_video":
            target_width = self._even(max(width or 0, 1280)) or 1280
            target_height = self._even(max(height or 0, 720)) or 720
            return self.helpers.pad_video, {
                "input_file": input_file,
                "output_file": output_target,
                "width": target_width,
                "height": target_height,
            }
        if operation_key == "rotate_video":
            return self.helpers.rotate_video, {
                "input_file": input_file,
                "output_file": output_target,
                "rotation": 90,
            }
        if operation_key == "change_fps":
            return self.helpers.change_fps, {
                "input_file": input_file,
                "output_file": output_target,
                "fps": 30,
            }
        if operation_key == "adjust_color":
            return self.helpers.adjust_color, {
                "input_file": input_file,
                "output_file": output_target,
                "brightness": 0.05,
                "contrast": 1.05,
                "saturation": 1.1,
            }
        if operation_key == "blur_sharpen":
            return self.helpers.blur_sharpen, {
                "input_file": input_file,
                "output_file": output_target,
                "blur_amount": 1.5,
                "sharpen_amount": 0.0,
            }
        if operation_key == "deinterlace":
            return self.helpers.deinterlace, {
                "input_file": input_file,
                "output_file": output_target,
            }
        if operation_key == "detect_black_frames":
            return self.helpers.detect_black_frames, {"input_file": input_file}
        if operation_key == "generate_scene_previews":
            return self.helpers.generate_scene_previews, {
                "input_file": input_file,
                "output_dir": output_target,
                "scene_count": 10,
            }
        if operation_key == "generate_scene_thumbnails":
            return self.helpers.generate_scene_thumbnails, {
                "input_file": input_file,
                "output_dir": output_target,
                "scene_count": 10,
                "thumbnail_width": 640,
            }
        raise ValueError(f"Unsupported operation: {operation_key}")

    def _display_output_path(self, task: Task) -> str:
        result = task.result
        if result is None:
            return self._active_task_context.get("output_target") or ""
        metadata = result.metadata if isinstance(result.metadata, dict) else {}
        for key in ("output_file", "output_path"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
        for key in ("preview_files", "thumbnail_files"):
            files = metadata.get(key)
            if isinstance(files, list) and files:
                return str(Path(files[0]).parent)
        if result.output_path:
            return result.output_path
        return self._active_task_context.get("output_target") or ""

    def _library_payload(self, task: Task) -> Any:
        result = task.result
        if result is None or not isinstance(result.metadata, dict):
            return self._display_output_path(task)
        for key in ("preview_files", "thumbnail_files"):
            files = result.metadata.get(key)
            if isinstance(files, list) and files:
                return files
        return self._display_output_path(task)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _browse_input(self) -> None:
        file_path = filedialog.askopenfilename(
            title=t("utilities.selectFile"),
            filetypes=[("All files", "*.*"), ("Video files", "*.mp4 *.mkv *.avi *.mov"), ("Audio files", "*.mp3 *.m4a *.flac *.wav")],
        )
        if file_path:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, file_path)

    def _browse_output(self) -> None:
        operation_key = self._selected_operation_key()
        if self._is_directory_output_operation(operation_key):
            file_path = filedialog.askdirectory(title=t("utilities.selectFile"))
        else:
            file_path = filedialog.asksaveasfilename(
                title=t("utilities.selectFile"),
                defaultextension=".mp4",
                filetypes=[("All files", "*.*"), ("Video files", "*.mp4 *.mkv *.avi *.mov"), ("Audio files", "*.mp3 *.m4a *.flac *.wav")],
            )
        if file_path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, file_path)

    def _set_running(self, is_running: bool, operation_label: Optional[str] = None) -> None:
        self._is_running = is_running
        if is_running:
            loading_text = f"{t('utilities.processing')} {operation_label or ''}".strip()
            set_button_loading_state(self.process_btn, True, loading_text=loading_text)
        else:
            set_button_loading_state(self.process_btn, False, original_text=t("utilities.process"))

    def _process_operation(self) -> None:
        if self._is_running:
            return

        input_file = self.input_entry.get().strip()
        raw_output = self.output_entry.get().strip()
        operation_key = self._selected_operation_key()
        operation_label = self._selected_operation_label()

        if not input_file:
            self._show_warning(t("utilities.selectInputFirst"))
            return
        if not Path(input_file).exists():
            self._show_error(t("converter.inputMissing"))
            return

        output_target = self._resolve_output_target(input_file, operation_key, raw_output)
        try:
            execute_fn, kwargs = self._build_operation_call_spec(input_file, operation_key, output_target)
        except Exception as exc:
            self._show_error(str(exc))
            return

        self._active_task_context = {
            "operation": operation_key,
            "operation_label": operation_label,
            "input_file": input_file,
            "output_target": output_target or "",
        }
        self._set_running(True, operation_label=operation_label)

        self._active_task_id = self.task_queue.add_task(
            task_type=TaskType.GENERIC,
            name=f"{operation_label}: {Path(input_file).name}",
            execute_fn=execute_fn,
            kwargs=kwargs,
            on_complete=self._on_task_complete,
            on_error=self._on_task_error,
            on_cancel=self._on_task_cancel,
        )

        self._persist_queued_operation(task_name=f"{operation_label}: {Path(input_file).name}")

        if self.show_queue_tab_callback:
            self.show_queue_tab_callback()
        self._show_success(f"{operation_label} queued")

    # ------------------------------------------------------------------
    # Task callbacks / persistence
    # ------------------------------------------------------------------

    def _persist_queued_operation(self, task_name: str) -> None:
        if not self.db_manager:
            return
        record = OperationRecord(
            task_type="utility",
            operation=self._operation_slug(self._active_task_context.get("operation", "utility")),
            title=task_name,
            input_paths=[self._active_task_context.get("input_file", "")],
            output_path=self._active_task_context.get("output_target", ""),
            format=Path(self._active_task_context.get("output_target", "")).suffix.lstrip(".").lower(),
            started_at=datetime.now().isoformat(),
            status="queued",
            metadata={
                "category": self._active_category,
                "operation_label": self._active_task_context.get("operation_label", ""),
            },
        )
        try:
            self.db_manager.add_operation(record)
        except Exception:
            pass

    def _persist_task_record(self, task: Task, status_override: Optional[str] = None) -> None:
        if not self.db_manager or not self._active_task_context:
            return
        output_path = self._display_output_path(task)
        metadata = dict(task.result.metadata) if task.result and isinstance(task.result.metadata, dict) else {}
        metadata.update({"task_name": task.name, "category": self._active_category})
        record = OperationRecord(
            task_type="utility",
            operation=self._operation_slug(self._active_task_context.get("operation", "utility")),
            title=task.name,
            input_paths=[self._active_task_context.get("input_file", "")],
            output_path=output_path,
            format=Path(output_path).suffix.lstrip(".").lower() if output_path and Path(output_path).suffix else "",
            started_at=task.started_at.isoformat() if task.started_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else "",
            duration=(task.result.duration_seconds if task.result else 0.0),
            status=status_override or task.status.value,
            error_message=(task.result.error_message if task.result else "") or "",
            metadata=metadata,
        )
        try:
            self.db_manager.add_operation(record)
        except Exception:
            pass

    def _on_task_complete(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self._persist_task_record(task)

        output_payload = self._library_payload(task)
        auto_add_callback = getattr(self, "auto_add_to_library_callback", None)
        if callable(auto_add_callback) and output_payload:
            try:
                auto_add_callback(
                    output_payload,
                    source_type="utilities",
                    metadata={
                        "operation": self._active_task_context.get("operation", ""),
                        "input_file": self._active_task_context.get("input_file", ""),
                    },
                )
            except Exception:
                pass

        output_path = self._display_output_path(task)
        suffix = Path(output_path).name if output_path else self._active_task_context.get("operation_label", t("utilities.success"))
        self._show_success(f"{t('utilities.success')}: {suffix}")
        self._reset_active_task()

    def _on_task_error(self, task: Task, error_message: str) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self._persist_task_record(task)
        self._show_error(error_message or t("utilities.failed"))
        self._reset_active_task()

    def _on_task_cancel(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self._persist_task_record(task, status_override="cancelled")
        self._show_warning(t("queue.statusCancelled"))
        self._reset_active_task()

    def _reset_active_task(self) -> None:
        self._active_task_id = None
        self._active_task_context = {}

    # ------------------------------------------------------------------
    # Toast helpers
    # ------------------------------------------------------------------

    def _toast(self):
        return self.toast_manager_getter() if callable(self.toast_manager_getter) else None

    def _show_success(self, message: str) -> None:
        toast = self._toast()
        if toast is None:
            return
        if hasattr(toast, "show_success"):
            toast.show_success(message)
        elif hasattr(toast, "show_toast"):
            toast.show_toast(message, "success")

    def _show_warning(self, message: str) -> None:
        toast = self._toast()
        if toast is None:
            return
        if hasattr(toast, "show_warning"):
            toast.show_warning(message)
        elif hasattr(toast, "show_toast"):
            toast.show_toast(message, "warning")

    def _show_error(self, message: str) -> None:
        toast = self._toast()
        if toast is None:
            return
        if hasattr(toast, "show_error"):
            toast.show_error(message)
        elif hasattr(toast, "show_toast"):
            toast.show_toast(message, "error")
