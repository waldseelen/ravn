"""Phase 7 mixer tab for audio and video composition workflows."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.database import OperationRecord
from ravn_app.core.i18n import t
from ravn_app.core.runners import AudioMixerRunner, AudioTrack, VideoMixerRunner
from ravn_app.core.task_manager import Task, TaskQueue, TaskResult, TaskType
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import bind_focus_ring, set_button_loading_state, style_combo, style_entry


class MixerTab(ctk.CTkFrame):
    """Audio/video mixing tab powered by Phase 7 runner helpers."""

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
        self.mixer_config = self.config_manager.get_section("mixer") if self.config_manager else {}

        ffmpeg_path = self.config_manager.get("ffmpeg_path", "ffmpeg") if self.config_manager else "ffmpeg"
        self._audio_runner = AudioMixerRunner(ffmpeg_path=ffmpeg_path)
        self._video_runner = VideoMixerRunner(ffmpeg_path=ffmpeg_path)
        self._is_running = False
        self._active_task_id: Optional[str] = None
        self._active_task_context: dict[str, Any] = {}
        self._input_files: list[str] = []

        self._audio_operations: dict[str, str] = {}
        self._video_operations: dict[str, str] = {}

        self._setup_ui()
        self._refresh_operation_choices()
        self._update_operation_fields()
        self._update_input_summary()

    # ------------------------------------------------------------------
    # Static helpers (logic-friendly / testable)
    # ------------------------------------------------------------------

    @staticmethod
    def _input_requirement(mode: str, operation: str) -> tuple[str, int]:
        """Return the expected input cardinality for an operation."""
        normalized_mode = str(mode or "audio").strip().lower()
        normalized_operation = str(operation or "concat").strip().lower()

        if normalized_mode == "audio":
            if normalized_operation in {"normalize", "trim", "fade"}:
                return ("exact", 1)
            return ("min", 2)

        if normalized_operation == "concat":
            return ("min", 2)
        return ("exact", 2)

    @staticmethod
    def _default_output_extension(mode: str, operation: str) -> str:
        if str(mode or "").strip().lower() == "audio":
            return ".mp3"
        if str(operation or "").strip().lower() == "extract-frame":
            return ".png"
        return ".mp4"

    @staticmethod
    def _parse_optional_float(value: str, default: Optional[float] = None) -> Optional[float]:
        candidate = str(value or "").strip()
        if not candidate:
            return default
        return float(candidate)

    @staticmethod
    def _parse_optional_int(value: str, default: Optional[int] = None) -> Optional[int]:
        candidate = str(value or "").strip()
        if not candidate:
            return default
        return int(float(candidate))

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)
        self.content = content

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header,
            text=f"{Icons.MIXER} {t('mixer.title')}",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=t("mixer.subtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        mode_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        mode_frame.pack(fill="x", pady=Spacing.XS)

        mode_inner = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        left_col = ctk.CTkFrame(mode_inner, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True, padx=(0, Spacing.MD))

        ctk.CTkLabel(left_col, text=t("mixer.modeLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.mode_selector = ctk.CTkSegmentedButton(
            left_col,
            values=[t("mixer.modeAudio"), t("mixer.modeVideo")],
            command=lambda _value: self._refresh_operation_choices(),
            font=Fonts.LABEL,
            fg_color=Colors.BG_CARD,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
            unselected_color=Colors.BG_INPUT,
            unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
        )
        self.mode_selector.pack(anchor="w", pady=(Spacing.XS, 0))
        self.mode_selector.set(t("mixer.modeAudio"))

        right_col = ctk.CTkFrame(mode_inner, fg_color="transparent")
        right_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(right_col, text=t("mixer.operationLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.operation_combo = ctk.CTkComboBox(
            right_col,
            values=[""],
            command=lambda _value: self._update_operation_fields(),
            width=280,
            font=Fonts.LABEL,
        )
        style_combo(self.operation_combo)
        self.operation_combo.pack(anchor="w", pady=(Spacing.XS, 0))

        inputs_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        inputs_frame.pack(fill="x", pady=Spacing.XS)

        inputs_header = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        inputs_header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        ctk.CTkLabel(inputs_header, text=t("mixer.inputsLabel"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(side="left")
        self.input_summary_label = ctk.CTkLabel(inputs_header, text="", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
        self.input_summary_label.pack(side="right")

        self.inputs_textbox = ctk.CTkTextbox(
            inputs_frame,
            height=110,
            font=Fonts.MONO,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            wrap="none",
        )
        self.inputs_textbox.pack(fill="x", padx=Spacing.MD)
        self.inputs_textbox.insert("1.0", t("mixer.inputsPlaceholder"))
        self.inputs_textbox.configure(state="disabled")

        inputs_actions = ctk.CTkFrame(inputs_frame, fg_color="transparent")
        inputs_actions.pack(fill="x", padx=Spacing.MD, pady=(Spacing.XS, Spacing.MD))

        self.add_inputs_btn = ctk.CTkButton(
            inputs_actions,
            text=f"{Icons.BROWSE} {t('mixer.addInputs')}",
            command=self._browse_inputs,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.add_inputs_btn.pack(side="left")

        self.clear_inputs_btn = ctk.CTkButton(
            inputs_actions,
            text=f"{Icons.CLEAR_BTN} {t('mixer.clearInputs')}",
            command=self._clear_inputs,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.clear_inputs_btn.pack(side="left", padx=(Spacing.XS, 0))

        output_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        output_frame.pack(fill="x", pady=Spacing.XS)

        output_inner = ctk.CTkFrame(output_frame, fg_color="transparent")
        output_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        ctk.CTkLabel(output_inner, text=t("mixer.outputLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        output_row = ctk.CTkFrame(output_inner, fg_color="transparent")
        output_row.pack(fill="x", pady=(Spacing.XS, Spacing.SM))

        self.output_entry = ctk.CTkEntry(output_row, placeholder_text=t("mixer.outputPlaceholder"), font=Fonts.LABEL)
        style_entry(self.output_entry)
        bind_focus_ring(self.output_entry)
        self.output_entry.configure(cursor=Cursors.TEXT)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        self.output_btn = ctk.CTkButton(
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
        )
        self.output_btn.pack(side="left")

        self.common_options_frame = ctk.CTkFrame(output_inner, fg_color="transparent")
        self.common_options_frame.pack(fill="x")

        common_left = ctk.CTkFrame(self.common_options_frame, fg_color="transparent")
        common_left.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))
        ctk.CTkLabel(common_left, text=t("mixer.bitrateLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.bitrate_combo = ctk.CTkComboBox(common_left, values=["128k", "192k", "256k", "320k"], font=Fonts.LABEL, width=120)
        style_combo(self.bitrate_combo)
        self.bitrate_combo.pack(anchor="w", pady=(Spacing.XS, 0))
        self.bitrate_combo.set(str(self.mixer_config.get("default_bitrate", "320k")))

        common_mid = ctk.CTkFrame(self.common_options_frame, fg_color="transparent")
        common_mid.pack(side="left", fill="x", expand=True, padx=(0, Spacing.SM))
        ctk.CTkLabel(common_mid, text=t("mixer.sampleRateLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.sample_rate_entry = ctk.CTkEntry(common_mid, placeholder_text="44100", font=Fonts.LABEL, width=140)
        style_entry(self.sample_rate_entry)
        bind_focus_ring(self.sample_rate_entry)
        self.sample_rate_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.normalize_var = ctk.BooleanVar(value=bool(self.mixer_config.get("normalize_audio", True)))
        self.normalize_checkbox = ctk.CTkCheckBox(
            self.common_options_frame,
            text=t("mixer.normalizeAudio"),
            variable=self.normalize_var,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
        )
        self.normalize_checkbox.pack(side="left", padx=(0, Spacing.SM), pady=(Spacing.LG, 0))

        self.reencode_var = ctk.BooleanVar(value=False)
        self.reencode_checkbox = ctk.CTkCheckBox(
            self.common_options_frame,
            text=t("mixer.reencodeLabel"),
            variable=self.reencode_var,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
        )
        self.reencode_checkbox.pack(side="left", pady=(Spacing.LG, 0))

        self.audio_fields_frame = ctk.CTkFrame(output_inner, fg_color="transparent")
        self.audio_fields_frame.pack(fill="x", pady=(Spacing.SM, 0))

        self.crossfade_frame = ctk.CTkFrame(self.audio_fields_frame, fg_color="transparent")
        self.crossfade_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.crossfade_frame, text=t("mixer.crossfadeDuration"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.crossfade_entry = ctk.CTkEntry(self.crossfade_frame, width=110, font=Fonts.LABEL)
        style_entry(self.crossfade_entry)
        bind_focus_ring(self.crossfade_entry)
        self.crossfade_entry.insert(0, str(self.mixer_config.get("crossfade_duration", 1.0)))
        self.crossfade_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.trim_start_frame = ctk.CTkFrame(self.audio_fields_frame, fg_color="transparent")
        self.trim_start_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.trim_start_frame, text=t("mixer.startTimeLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.trim_start_entry = ctk.CTkEntry(self.trim_start_frame, width=110, font=Fonts.LABEL)
        style_entry(self.trim_start_entry)
        bind_focus_ring(self.trim_start_entry)
        self.trim_start_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.trim_duration_frame = ctk.CTkFrame(self.audio_fields_frame, fg_color="transparent")
        self.trim_duration_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.trim_duration_frame, text=t("mixer.trimDurationLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.trim_duration_entry = ctk.CTkEntry(self.trim_duration_frame, width=110, font=Fonts.LABEL)
        style_entry(self.trim_duration_entry)
        bind_focus_ring(self.trim_duration_entry)
        self.trim_duration_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.fade_in_frame = ctk.CTkFrame(self.audio_fields_frame, fg_color="transparent")
        self.fade_in_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.fade_in_frame, text=t("mixer.fadeInLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.fade_in_entry = ctk.CTkEntry(self.fade_in_frame, width=110, font=Fonts.LABEL)
        style_entry(self.fade_in_entry)
        bind_focus_ring(self.fade_in_entry)
        self.fade_in_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.fade_out_frame = ctk.CTkFrame(self.audio_fields_frame, fg_color="transparent")
        self.fade_out_frame.pack(side="left")
        ctk.CTkLabel(self.fade_out_frame, text=t("mixer.fadeOutLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.fade_out_entry = ctk.CTkEntry(self.fade_out_frame, width=110, font=Fonts.LABEL)
        style_entry(self.fade_out_entry)
        bind_focus_ring(self.fade_out_entry)
        self.fade_out_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.video_fields_frame = ctk.CTkFrame(output_inner, fg_color="transparent")
        self.video_fields_frame.pack(fill="x", pady=(Spacing.SM, 0))

        self.position_frame = ctk.CTkFrame(self.video_fields_frame, fg_color="transparent")
        self.position_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.position_frame, text=t("mixer.positionLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.position_combo = ctk.CTkComboBox(
            self.position_frame,
            values=list(self._position_display_map().keys()),
            width=150,
            font=Fonts.LABEL,
        )
        style_combo(self.position_combo)
        self.position_combo.set(t("mixer.positionBottomRight"))
        self.position_combo.pack(anchor="w", pady=(Spacing.XS, 0))

        self.scale_frame = ctk.CTkFrame(self.video_fields_frame, fg_color="transparent")
        self.scale_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.scale_frame, text=t("mixer.scaleLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.scale_entry = ctk.CTkEntry(self.scale_frame, width=110, font=Fonts.LABEL)
        style_entry(self.scale_entry)
        bind_focus_ring(self.scale_entry)
        self.scale_entry.insert(0, "0.25")
        self.scale_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.opacity_frame = ctk.CTkFrame(self.video_fields_frame, fg_color="transparent")
        self.opacity_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.opacity_frame, text=t("mixer.opacityLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.opacity_entry = ctk.CTkEntry(self.opacity_frame, width=110, font=Fonts.LABEL)
        style_entry(self.opacity_entry)
        bind_focus_ring(self.opacity_entry)
        self.opacity_entry.insert(0, "1.0")
        self.opacity_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        self.orientation_frame = ctk.CTkFrame(self.video_fields_frame, fg_color="transparent")
        self.orientation_frame.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(self.orientation_frame, text=t("mixer.orientationLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.orientation_combo = ctk.CTkComboBox(
            self.orientation_frame,
            values=list(self._orientation_display_map().keys()),
            width=130,
            font=Fonts.LABEL,
        )
        style_combo(self.orientation_combo)
        self.orientation_combo.set(t("mixer.orientationHorizontal"))
        self.orientation_combo.pack(anchor="w", pady=(Spacing.XS, 0))

        self.transition_frame = ctk.CTkFrame(self.video_fields_frame, fg_color="transparent")
        self.transition_frame.pack(side="left")
        ctk.CTkLabel(self.transition_frame, text=t("mixer.transitionDurationLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.transition_duration_entry = ctk.CTkEntry(self.transition_frame, width=110, font=Fonts.LABEL)
        style_entry(self.transition_duration_entry)
        bind_focus_ring(self.transition_duration_entry)
        self.transition_duration_entry.insert(0, "1.0")
        self.transition_duration_entry.pack(anchor="w", pady=(Spacing.XS, 0))

        action_row = ctk.CTkFrame(content, fg_color="transparent")
        action_row.pack(fill="x", pady=Spacing.XS)

        self.run_btn = ctk.CTkButton(
            action_row,
            text=f"{Icons.MIXER} {t('mixer.runButton')}",
            command=self._start_operation,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.run_btn.pack(side="right")

        self.cancel_btn = ctk.CTkButton(
            action_row,
            text=f"{Icons.STOP} {t('mixer.cancelButton')}",
            command=self._cancel_operation,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BTN_DISABLED,
            hover_color=Colors.BTN_DISABLED,
            state="disabled",
            text_color=Colors.TEXT_MUTED,
            cursor=Cursors.POINTER,
        )
        self.cancel_btn.pack(side="right", padx=(0, Spacing.XS))

        progress_frame = ctk.CTkFrame(content, fg_color="transparent")
        progress_frame.pack(fill="x", pady=(Spacing.XS, 0))

        self.progress_bar = ctk.CTkProgressBar(progress_frame)
        self.progress_bar.configure(progress_color=Colors.ACCENT, fg_color=Colors.PROGRESS_BG)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x")

        self.status_label = ctk.CTkLabel(
            progress_frame,
            text=t("mixer.ready"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.status_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.error_panel = ErrorPanel(self, animation_manager=self.animation_manager, on_retry=self._start_operation)

        log_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        log_frame.pack(fill="both", expand=True, pady=Spacing.SM)

        ctk.CTkLabel(log_frame, text=t("mixer.logTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        self.log_text = ctk.CTkTextbox(log_frame, height=200, font=Fonts.MONO, fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_SECONDARY)
        self.log_text.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _refresh_operation_choices(self) -> None:
        self._audio_operations = {
            "concat": t("mixer.audioConcat"),
            "mix": t("mixer.audioMix"),
            "crossfade": t("mixer.audioCrossfade"),
            "normalize": t("mixer.audioNormalize"),
            "trim": t("mixer.audioTrim"),
            "fade": t("mixer.audioFade"),
        }
        self._video_operations = {
            "concat": t("mixer.videoConcat"),
            "overlay": t("mixer.videoOverlay"),
            "pip": t("mixer.videoPiP"),
            "side-by-side": t("mixer.videoSideBySide"),
            "watermark": t("mixer.videoWatermark"),
            "transition": t("mixer.videoTransition"),
            "replace-audio": t("mixer.videoReplaceAudio"),
        }

        operations = self._audio_operations if self._current_mode() == "audio" else self._video_operations
        values = list(operations.values())
        current_key = self._current_operation_key(default=None)
        fallback_value = operations.get(current_key, values[0]) if values else ""
        self.operation_combo.configure(values=values or [""])
        self.operation_combo.set(fallback_value)
        self._update_operation_fields()
        self._suggest_output_path()

    def _current_mode(self) -> str:
        return "video" if self.mode_selector.get() == t("mixer.modeVideo") else "audio"

    def _current_operation_key(self, default: Optional[str] = "concat") -> Optional[str]:
        label = self.operation_combo.get()
        operations = self._audio_operations if self._current_mode() == "audio" else self._video_operations
        for key, value in operations.items():
            if value == label:
                return key
        return default

    @staticmethod
    def _position_display_map() -> dict[str, str]:
        return {
            t("mixer.positionTopLeft"): "top-left",
            t("mixer.positionTopRight"): "top-right",
            t("mixer.positionBottomLeft"): "bottom-left",
            t("mixer.positionBottomRight"): "bottom-right",
            t("mixer.positionCenter"): "center",
        }

    @staticmethod
    def _orientation_display_map() -> dict[str, str]:
        return {
            t("mixer.orientationHorizontal"): "horizontal",
            t("mixer.orientationVertical"): "vertical",
        }

    def _update_input_summary(self) -> None:
        self.input_summary_label.configure(text=t("mixer.inputCount", count=len(self._input_files)))
        self.inputs_textbox.configure(state="normal")
        self.inputs_textbox.delete("1.0", "end")
        if self._input_files:
            self.inputs_textbox.insert("1.0", "\n".join(self._input_files))
        else:
            self.inputs_textbox.insert("1.0", t("mixer.inputsPlaceholder"))
        self.inputs_textbox.configure(state="disabled")

    def _update_operation_fields(self) -> None:
        mode = self._current_mode()
        operation = self._current_operation_key()

        self.common_options_frame.pack(fill="x")
        self.audio_fields_frame.pack_forget()
        self.video_fields_frame.pack_forget()

        self.normalize_checkbox.pack_forget()
        self.reencode_checkbox.pack_forget()
        self.crossfade_frame.pack_forget()
        self.trim_start_frame.pack_forget()
        self.trim_duration_frame.pack_forget()
        self.fade_in_frame.pack_forget()
        self.fade_out_frame.pack_forget()
        self.position_frame.pack_forget()
        self.scale_frame.pack_forget()
        self.opacity_frame.pack_forget()
        self.orientation_frame.pack_forget()
        self.transition_frame.pack_forget()

        if mode == "audio":
            self.audio_fields_frame.pack(fill="x", pady=(Spacing.SM, 0))
            if operation == "mix":
                self.normalize_checkbox.pack(side="left", padx=(0, Spacing.SM), pady=(Spacing.LG, 0))
            if operation == "crossfade":
                self.crossfade_frame.pack(side="left", padx=(0, Spacing.MD))
            elif operation == "trim":
                self.trim_start_frame.pack(side="left", padx=(0, Spacing.MD))
                self.trim_duration_frame.pack(side="left", padx=(0, Spacing.MD))
            elif operation == "fade":
                self.fade_in_frame.pack(side="left", padx=(0, Spacing.MD))
                self.fade_out_frame.pack(side="left")
        else:
            self.video_fields_frame.pack(fill="x", pady=(Spacing.SM, 0))
            if operation == "concat":
                self.reencode_checkbox.pack(side="left", pady=(Spacing.LG, 0))
            elif operation in {"overlay", "watermark"}:
                self.position_frame.pack(side="left", padx=(0, Spacing.MD))
                self.scale_frame.pack(side="left", padx=(0, Spacing.MD))
                self.opacity_frame.pack(side="left")
            elif operation == "pip":
                self.position_frame.pack(side="left", padx=(0, Spacing.MD))
                self.scale_frame.pack(side="left")
            elif operation == "side-by-side":
                self.orientation_frame.pack(side="left")
            elif operation == "transition":
                self.transition_frame.pack(side="left")
        self._suggest_output_path()

    def _browse_inputs(self) -> None:
        mode = self._current_mode()
        title = t("mixer.selectAudioInputsTitle") if mode == "audio" else t("mixer.selectVideoInputsTitle")
        filetypes = [(t("mixer.audioFiles"), "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.opus"), (t("mixer.allFiles"), "*.*")]
        if mode == "video":
            filetypes = [(t("mixer.videoFiles"), "*.mp4 *.mkv *.mov *.webm *.avi *.png *.jpg *.jpeg *.webp"), (t("mixer.allFiles"), "*.*")]
        selected = filedialog.askopenfilenames(title=title, filetypes=filetypes)
        if not selected:
            return
        for path in selected:
            if path not in self._input_files:
                self._input_files.append(path)
        self._update_input_summary()
        self._suggest_output_path()

    def _clear_inputs(self) -> None:
        self._input_files = []
        self._update_input_summary()

    def _browse_output(self) -> None:
        mode = self._current_mode()
        initial_ext = self._default_output_extension(mode, self._current_operation_key())
        filetypes = [(t("mixer.audioOutput"), "*.mp3 *.wav *.m4a *.flac *.aac *.ogg *.opus"), (t("mixer.allFiles"), "*.*")]
        if mode == "video":
            filetypes = [(t("mixer.videoOutput"), "*.mp4 *.mkv *.mov *.webm *.avi"), (t("mixer.allFiles"), "*.*")]
        path = filedialog.asksaveasfilename(
            title=t("mixer.selectOutputTitle"),
            defaultextension=initial_ext,
            filetypes=filetypes,
        )
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _suggest_output_path(self) -> None:
        if not self._input_files or self.output_entry.get().strip():
            return
        first = Path(self._input_files[0])
        extension = self._default_output_extension(self._current_mode(), self._current_operation_key())
        candidate = first.with_name(f"{first.stem}_{self._current_operation_key()}{extension}")
        self.output_entry.delete(0, "end")
        self.output_entry.insert(0, str(candidate))

    def _append_log(self, message: str) -> None:
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def _set_running(self, is_running: bool) -> None:
        self._is_running = is_running
        if is_running:
            set_button_loading_state(self.run_btn, True, loading_text=t("mixer.runningButton"))
            self.cancel_btn.configure(state="normal", fg_color=Colors.BTN_SECONDARY, hover_color=Colors.BTN_SECONDARY_HOVER, text_color=Colors.TEXT_PRIMARY)
        else:
            set_button_loading_state(self.run_btn, False, original_text=f"{Icons.MIXER} {t('mixer.runButton')}")
            self.cancel_btn.configure(state="disabled", fg_color=Colors.BTN_DISABLED, hover_color=Colors.BTN_DISABLED, text_color=Colors.TEXT_MUTED)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _task_type_for(self, mode: str) -> TaskType:
        return TaskType.MIXER_AUDIO if mode == "audio" else TaskType.MIXER_VIDEO

    def _reset_active_task(self) -> None:
        self._active_task_id = None
        self._active_task_context = {}

    def _persist_task_record(self, task: Task, status_override: Optional[str] = None) -> None:
        if not self.db_manager or not self._active_task_context:
            return

        output_path = (task.result.output_path if task.result else "") or self._active_task_context.get("output_path", "")
        metadata = dict(task.result.metadata) if task.result and isinstance(task.result.metadata, dict) else {}
        metadata.update({"task_name": task.name})

        record = OperationRecord(
            task_type=task.task_type.value,
            operation=self._active_task_context.get("operation", ""),
            title=Path(output_path).name if output_path else task.name,
            input_paths=list(self._active_task_context.get("inputs", [])),
            output_path=output_path,
            format=Path(output_path).suffix.lstrip(".").lower() if output_path else "",
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

    def _start_operation(self) -> None:
        if self._is_running:
            return

        mode = self._current_mode()
        operation = self._current_operation_key()
        requirement_type, requirement_count = self._input_requirement(mode, operation)
        output_path = self.output_entry.get().strip()

        if not self._input_files:
            self._show_error(t("mixer.noInputs"))
            return
        if not output_path:
            self._show_error(t("mixer.outputRequired"))
            return
        if requirement_type == "exact" and len(self._input_files) != requirement_count:
            self._show_error(t("mixer.exactInputRequired", count=requirement_count))
            return
        if requirement_type == "min" and len(self._input_files) < requirement_count:
            self._show_error(t("mixer.minimumInputRequired", count=requirement_count))
            return

        try:
            call, kwargs = self._build_runner_call_spec(mode, operation, output_path)
        except ValueError as exc:
            self._show_error(str(exc))
            return

        self.error_panel.hide_error()
        self.progress_bar.set(0)
        self.status_label.configure(text=t("mixer.started", operation=self.operation_combo.get()))
        self.log_text.delete("1.0", "end")
        self._append_log(f"[{mode}] {operation} -> {output_path}")
        self._set_running(True)

        self._active_task_context = {
            "mode": mode,
            "operation": operation,
            "inputs": list(self._input_files),
            "output_path": output_path,
        }
        self._active_task_id = self.task_queue.add_task(
            task_type=self._task_type_for(mode),
            name=f"{self.mode_selector.get()} • {self.operation_combo.get()}",
            execute_fn=call,
            kwargs=kwargs,
            on_progress=self._on_task_progress,
            on_complete=self._on_task_complete,
            on_error=self._on_task_error,
            on_cancel=self._on_task_cancel,
            cancel_fn=self._audio_runner.cancel if mode == "audio" else self._video_runner.cancel,
        )
        if self.show_queue_tab_callback:
            self.show_queue_tab_callback()

    def _build_runner_call_spec(self, mode: str, operation: str, output_path: str) -> tuple[Callable[..., Any], dict[str, Any]]:
        bitrate = self.bitrate_combo.get().strip() or None
        sample_rate = self._parse_optional_int(self.sample_rate_entry.get(), default=None)
        if sample_rate is not None and sample_rate <= 0:
            raise ValueError(t("mixer.sampleRatePositive"))

        if mode == "audio":
            if operation == "concat":
                return self._audio_runner.concat, {
                    "input_files": list(self._input_files),
                    "output_file": output_path,
                    "bitrate": bitrate,
                    "sample_rate": sample_rate,
                }
            if operation == "mix":
                tracks = [AudioTrack(file_path=path, volume=1.0) for path in self._input_files]
                return self._audio_runner.mix, {
                    "tracks": tracks,
                    "output_file": output_path,
                    "bitrate": bitrate,
                    "sample_rate": sample_rate,
                    "normalize": bool(self.normalize_var.get()),
                }
            if operation == "crossfade":
                duration = self._parse_optional_float(self.crossfade_entry.get(), default=1.0)
                if duration is None or duration <= 0:
                    raise ValueError(t("mixer.durationPositive"))
                return self._audio_runner.crossfade, {
                    "input_files": list(self._input_files),
                    "output_file": output_path,
                    "duration": duration,
                    "bitrate": bitrate,
                }
            if operation == "normalize":
                return self._audio_runner.normalize, {
                    "input_file": self._input_files[0],
                    "output_file": output_path,
                    "bitrate": bitrate,
                }
            if operation == "trim":
                start_time = self._parse_optional_float(self.trim_start_entry.get(), default=None)
                duration = self._parse_optional_float(self.trim_duration_entry.get(), default=None)
                if start_time is None or duration is None or start_time < 0 or duration <= 0:
                    raise ValueError(t("mixer.trimValuesRequired"))
                return self._audio_runner.trim, {
                    "input_file": self._input_files[0],
                    "output_file": output_path,
                    "start_time": start_time,
                    "duration": duration,
                    "bitrate": bitrate,
                }
            if operation == "fade":
                fade_in = self._parse_optional_float(self.fade_in_entry.get(), default=0.0) or 0.0
                fade_out = self._parse_optional_float(self.fade_out_entry.get(), default=0.0) or 0.0
                if fade_in <= 0 and fade_out <= 0:
                    raise ValueError(t("mixer.fadeValuesRequired"))
                return self._audio_runner.apply_fade, {
                    "input_file": self._input_files[0],
                    "output_file": output_path,
                    "fade_in_duration": fade_in,
                    "fade_out_duration": fade_out,
                    "bitrate": bitrate,
                }
            raise ValueError(t("mixer.unsupportedOperation"))

        video_codec = str(self.mixer_config.get("video_codec", "libx264"))
        position = self._position_display_map().get(self.position_combo.get().strip(), "bottom-right")
        scale = self._parse_optional_float(self.scale_entry.get(), default=None)
        opacity = self._parse_optional_float(self.opacity_entry.get(), default=1.0) or 1.0
        transition_duration = self._parse_optional_float(self.transition_duration_entry.get(), default=1.0) or 1.0

        if operation == "concat":
            return self._video_runner.concat, {
                "input_files": list(self._input_files),
                "output_file": output_path,
                "reencode": bool(self.reencode_var.get()),
                "video_codec": video_codec,
            }
        if operation == "overlay":
            return self._video_runner.overlay, {
                "base_file": self._input_files[0],
                "overlay_file": self._input_files[1],
                "output_file": output_path,
                "position": position,
                "scale": scale,
                "opacity": opacity,
                "video_codec": video_codec,
            }
        if operation == "pip":
            return self._video_runner.picture_in_picture, {
                "main_file": self._input_files[0],
                "pip_file": self._input_files[1],
                "output_file": output_path,
                "position": position,
                "scale": scale or 0.25,
                "video_codec": video_codec,
            }
        if operation == "side-by-side":
            return self._video_runner.side_by_side, {
                "left_file": self._input_files[0],
                "right_file": self._input_files[1],
                "output_file": output_path,
                "orientation": self._orientation_display_map().get(self.orientation_combo.get().strip(), "horizontal"),
                "video_codec": video_codec,
            }
        if operation == "watermark":
            return self._video_runner.watermark, {
                "video_file": self._input_files[0],
                "watermark_file": self._input_files[1],
                "output_file": output_path,
                "position": position,
                "scale": scale,
                "opacity": opacity,
                "video_codec": video_codec,
            }
        if operation == "transition":
            if transition_duration <= 0:
                raise ValueError(t("mixer.durationPositive"))
            return self._video_runner.transition, {
                "first_file": self._input_files[0],
                "second_file": self._input_files[1],
                "output_file": output_path,
                "duration": transition_duration,
                "video_codec": video_codec,
            }
        if operation == "replace-audio":
            return self._video_runner.replace_audio, {
                "video_file": self._input_files[0],
                "audio_file": self._input_files[1],
                "output_file": output_path,
            }
        raise ValueError(t("mixer.unsupportedOperation"))

    def _on_task_progress(self, progress: int, message: str = "") -> None:
        if not self._active_task_id:
            return
        normalized = max(0.0, min(float(progress) / 100.0, 1.0))
        self.progress_bar.set(normalized)
        if message:
            self.status_label.configure(text=message)
            self._append_log(message)

    def _on_task_complete(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self.progress_bar.set(1.0)
        self.status_label.configure(text=t("mixer.completed", operation=self.operation_combo.get()))
        output_path = (task.result.output_path if task.result else "") or self._active_task_context.get("output_path", "")
        self._append_log(f"{self._active_task_context.get('operation', '')} -> {output_path}")
        self._persist_task_record(task)
        auto_add_callback = getattr(self, "auto_add_to_library_callback", None)
        if callable(auto_add_callback) and output_path:
            metadata = dict(task.result.metadata) if task.result and isinstance(task.result.metadata, dict) else {}
            metadata.update(
                {
                    "operation": self._active_task_context.get("operation", ""),
                    "mode": self._active_task_context.get("mode", ""),
                    "input_paths": list(self._active_task_context.get("inputs", [])),
                }
            )
            auto_add_callback(output_path, source_type="mixer", metadata=metadata)
        toast = self.toast_manager_getter()
        if toast and output_path:
            toast.show_success(t("mixer.successToast", output=Path(output_path).name))
        self._reset_active_task()

    def _on_task_error(self, task: Task, error_message: str) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self.progress_bar.set(0)
        self.status_label.configure(text=t("mixer.failed", operation=self.operation_combo.get()))
        self._append_log(error_message)
        self._show_error(t("mixer.failedWithReason", reason=error_message), raw_error=error_message)
        self._persist_task_record(task)
        toast = self.toast_manager_getter()
        if toast:
            toast.show_error(error_message)
        self._reset_active_task()

    def _on_task_cancel(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self.progress_bar.set(0)
        self.status_label.configure(text=t("mixer.cancelled"))
        self._append_log(t("mixer.cancelled"))
        self._persist_task_record(task, status_override="cancelled")
        self._reset_active_task()

    def _cancel_operation(self) -> None:
        if not self._active_task_id:
            return
        if self.task_queue.cancel_task(self._active_task_id):
            self.status_label.configure(text=t("mixer.cancelled"))

    def _show_error(self, message: str, raw_error: Optional[str] = None) -> None:
        self.error_panel.show_error(message, raw_error or message)

    # ------------------------------------------------------------------
    # Shortcuts / lifecycle
    # ------------------------------------------------------------------

    def _on_ctrl_enter(self, event=None):
        if not self.winfo_viewable():
            return
        if not self._is_running:
            self._start_operation()

    def _on_escape(self, event=None):
        if not self.winfo_viewable():
            return
        if self._is_running:
            self._cancel_operation()
        else:
            self.error_panel.hide_error()

    def _on_ctrl_l(self, event=None):
        if not self.winfo_viewable():
            return
        self._clear_inputs()
        self.output_entry.delete(0, "end")
        self.log_text.delete("1.0", "end")
        self.error_panel.hide_error()
        self.progress_bar.set(0)
        self.status_label.configure(text=t("mixer.ready"))
        self._reset_active_task()
        return "break"

    def destroy(self):
        try:
            self._audio_runner.cancel()
        except Exception:
            pass
        try:
            self._video_runner.cancel()
        except Exception:
            pass
        super().destroy()
