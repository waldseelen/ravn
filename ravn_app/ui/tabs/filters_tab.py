"""Phase 7 filters tab for FFmpeg-based video adjustments."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.database import OperationRecord
from ravn_app.core.i18n import t
from ravn_app.core.runners import VideoMixerRunner
from ravn_app.core.task_manager import Task, TaskQueue, TaskType
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import bind_focus_ring, set_button_loading_state, style_combo, style_entry


class FiltersTab(ctk.CTkFrame):
    """Advanced local-file filter application tab."""

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
        self.filters_config = self.config_manager.get_section("filters") if self.config_manager else {}

        ffmpeg_path = self.config_manager.get("ffmpeg_path", "ffmpeg") if self.config_manager else "ffmpeg"
        self._runner = VideoMixerRunner(ffmpeg_path=ffmpeg_path)
        self._is_running = False
        self._active_task_id: Optional[str] = None
        self._active_task_context: dict[str, Any] = {}

        self._setup_ui()
        self._update_summary()

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_optional_float(value: str, default: Optional[float] = None) -> Optional[float]:
        candidate = str(value or "").strip()
        if not candidate:
            return default
        return float(candidate)

    @staticmethod
    def _parse_optional_bool(value: Any) -> bool:
        return bool(value)

    @staticmethod
    def _summarize_active_filters(filters: dict[str, Any]) -> list[str]:
        summary: list[str] = []
        for key, value in filters.items():
            if key in {"contrast", "saturation"} and value in (1, 1.0):
                continue
            if value in (None, False, "", 0, 0.0):
                continue
            if isinstance(value, bool):
                summary.append(key)
            else:
                summary.append(f"{key}={value}")
        return summary

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header,
            text=f"{Icons.FILTERS} {t('filters.title')}",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=t("filters.subtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        source_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        source_frame.pack(fill="x", pady=Spacing.XS)

        source_inner = ctk.CTkFrame(source_frame, fg_color="transparent")
        source_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        ctk.CTkLabel(source_inner, text=t("filters.inputLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        input_row = ctk.CTkFrame(source_inner, fg_color="transparent")
        input_row.pack(fill="x", pady=(Spacing.XS, Spacing.SM))

        self.input_entry = ctk.CTkEntry(input_row, placeholder_text=t("filters.inputPlaceholder"), font=Fonts.LABEL)
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

        ctk.CTkLabel(source_inner, text=t("filters.outputLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        output_row = ctk.CTkFrame(source_inner, fg_color="transparent")
        output_row.pack(fill="x", pady=(Spacing.XS, 0))

        self.output_entry = ctk.CTkEntry(output_row, placeholder_text=t("filters.outputPlaceholder"), font=Fonts.LABEL)
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

        controls_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        controls_frame.pack(fill="x", pady=Spacing.XS)

        controls_inner = ctk.CTkFrame(controls_frame, fg_color="transparent")
        controls_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        self._build_numeric_group(controls_inner)
        self._build_effect_group(controls_inner)
        self._build_advanced_group(controls_inner)

        summary_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        summary_frame.pack(fill="x", pady=Spacing.XS)

        ctk.CTkLabel(summary_frame, text=t("filters.summaryLabel"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        self.summary_label = ctk.CTkLabel(summary_frame, text="", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, justify="left", wraplength=980)
        self.summary_label.pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.MD))

        action_row = ctk.CTkFrame(content, fg_color="transparent")
        action_row.pack(fill="x", pady=Spacing.XS)

        self.apply_btn = ctk.CTkButton(
            action_row,
            text=f"{Icons.FILTERS} {t('filters.applyButton')}",
            command=self._apply_filters,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.apply_btn.pack(side="right")

        self.cancel_btn = ctk.CTkButton(
            action_row,
            text=f"{Icons.STOP} {t('filters.cancelButton')}",
            command=self._cancel_filters,
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

        self.status_label = ctk.CTkLabel(progress_frame, text=t("filters.ready"), font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, anchor="w")
        self.status_label.pack(anchor="w", pady=(Spacing.XS, 0))

        self.error_panel = ErrorPanel(self, animation_manager=self.animation_manager, on_retry=self._apply_filters)

        log_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        log_frame.pack(fill="both", expand=True, pady=Spacing.SM)

        ctk.CTkLabel(log_frame, text=t("filters.logTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        self.log_text = ctk.CTkTextbox(log_frame, height=200, font=Fonts.MONO, fg_color=Colors.BG_INPUT, text_color=Colors.TEXT_SECONDARY)
        self.log_text.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))

    def _build_numeric_group(self, parent) -> None:
        numeric = ctk.CTkFrame(parent, fg_color="transparent")
        numeric.pack(fill="x")

        fields = [
            ("brightness", t("filters.brightnessLabel"), "0"),
            ("contrast", t("filters.contrastLabel"), "1.0"),
            ("saturation", t("filters.saturationLabel"), "1.0"),
            ("blur", t("filters.blurLabel"), ""),
            ("sharpen", t("filters.sharpenLabel"), ""),
            ("rotate", t("filters.rotateLabel"), ""),
        ]
        self.numeric_entries: dict[str, ctk.CTkEntry] = {}
        for index, (key, label, default_value) in enumerate(fields):
            field = ctk.CTkFrame(numeric, fg_color="transparent")
            field.grid(row=0, column=index, padx=(0, Spacing.SM), sticky="w")
            ctk.CTkLabel(field, text=label, font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
            entry = ctk.CTkEntry(field, width=120, font=Fonts.LABEL)
            style_entry(entry)
            bind_focus_ring(entry)
            if default_value:
                entry.insert(0, default_value)
            entry.pack(anchor="w", pady=(Spacing.XS, 0))
            entry.bind("<KeyRelease>", lambda _event: self._update_summary(), add="+")
            self.numeric_entries[key] = entry

    def _build_effect_group(self, parent) -> None:
        effects = ctk.CTkFrame(parent, fg_color="transparent")
        effects.pack(fill="x", pady=(Spacing.MD, 0))

        self.effect_vars = {
            "flip_horizontal": ctk.BooleanVar(value=False),
            "flip_vertical": ctk.BooleanVar(value=False),
            "grayscale": ctk.BooleanVar(value=False),
            "sepia": ctk.BooleanVar(value=False),
            "invert": ctk.BooleanVar(value=False),
            "deinterlace": ctk.BooleanVar(value=False),
        }

        labels = {
            "flip_horizontal": t("filters.flipHorizontal"),
            "flip_vertical": t("filters.flipVertical"),
            "grayscale": t("filters.grayscale"),
            "sepia": t("filters.sepia"),
            "invert": t("filters.invert"),
            "deinterlace": t("filters.deinterlace"),
        }

        for index, (key, var) in enumerate(self.effect_vars.items()):
            checkbox = ctk.CTkCheckBox(
                effects,
                text=labels[key],
                variable=var,
                font=Fonts.LABEL,
                text_color=Colors.TEXT_PRIMARY,
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_HOVER,
                command=self._update_summary,
            )
            checkbox.grid(row=index // 3, column=index % 3, padx=(0, Spacing.MD), pady=(0, Spacing.XS), sticky="w")

    def _build_advanced_group(self, parent) -> None:
        advanced = ctk.CTkFrame(parent, fg_color="transparent")
        advanced.pack(fill="x", pady=(Spacing.MD, 0))

        denoise_col = ctk.CTkFrame(advanced, fg_color="transparent")
        denoise_col.pack(side="left", padx=(0, Spacing.MD))
        ctk.CTkLabel(denoise_col, text=t("filters.denoiseLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        self.denoise_combo = ctk.CTkComboBox(
            denoise_col,
            values=list(self._denoise_display_map().keys()),
            width=140,
            font=Fonts.LABEL,
            command=lambda _value: self._update_summary(),
        )
        style_combo(self.denoise_combo)
        self.denoise_combo.set(t("filters.denoiseOff"))
        self.denoise_combo.pack(anchor="w", pady=(Spacing.XS, 0))

        lut_col = ctk.CTkFrame(advanced, fg_color="transparent")
        lut_col.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(lut_col, text=t("filters.lutFileLabel"), font=Fonts.LABEL, text_color=Colors.TEXT_PRIMARY).pack(anchor="w")
        lut_row = ctk.CTkFrame(lut_col, fg_color="transparent")
        lut_row.pack(fill="x", pady=(Spacing.XS, 0))

        self.lut_entry = ctk.CTkEntry(lut_row, placeholder_text=t("filters.lutPlaceholder"), font=Fonts.LABEL)
        style_entry(self.lut_entry)
        bind_focus_ring(self.lut_entry)
        self.lut_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))
        self.lut_entry.bind("<KeyRelease>", lambda _event: self._update_summary(), add="+")

        ctk.CTkButton(
            lut_row,
            text=Icons.BROWSE,
            width=40,
            command=self._browse_lut,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------

    def _browse_input(self) -> None:
        path = filedialog.askopenfilename(
            title=t("filters.selectInputTitle"),
            filetypes=[(t("filters.videoFiles"), "*.mp4 *.mkv *.mov *.webm *.avi"), (t("filters.allFiles"), "*.*")],
        )
        if not path:
            return
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, path)
        if not self.output_entry.get().strip():
            source = Path(path)
            self.output_entry.insert(0, str(source.with_name(f"{source.stem}_filtered{source.suffix or '.mp4'}")))

    def _browse_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title=t("filters.selectOutputTitle"),
            defaultextension=".mp4",
            filetypes=[(t("filters.videoOutput"), "*.mp4 *.mkv *.mov *.webm *.avi"), (t("filters.allFiles"), "*.*")],
        )
        if path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, path)

    def _browse_lut(self) -> None:
        path = filedialog.askopenfilename(
            title=t("filters.selectLutTitle"),
            filetypes=[(t("filters.lutFiles"), "*.cube *.3dl"), (t("filters.allFiles"), "*.*")],
        )
        if path:
            self.lut_entry.delete(0, "end")
            self.lut_entry.insert(0, path)
            self._update_summary()

    def _collect_filter_options(self) -> dict[str, Any]:
        brightness = self._parse_optional_float(self.numeric_entries["brightness"].get(), default=0.0)
        contrast = self._parse_optional_float(self.numeric_entries["contrast"].get(), default=1.0)
        saturation = self._parse_optional_float(self.numeric_entries["saturation"].get(), default=1.0)
        blur = self._parse_optional_float(self.numeric_entries["blur"].get(), default=None)
        sharpen = self._parse_optional_float(self.numeric_entries["sharpen"].get(), default=None)
        rotate = self._parse_optional_float(self.numeric_entries["rotate"].get(), default=None)
        denoise = self._denoise_display_map().get(self.denoise_combo.get().strip()) or None
        lut_file = self.lut_entry.get().strip() or None

        options = {
            "brightness": brightness,
            "contrast": contrast,
            "saturation": saturation,
            "blur": blur,
            "sharpen": sharpen,
            "rotate": rotate,
            "denoise": denoise,
            "lut_file": lut_file,
        }
        for key, var in self.effect_vars.items():
            options[key] = bool(var.get())
        return options

    def _has_meaningful_filters(self, options: dict[str, Any]) -> bool:
        return any(
            [
                options.get("brightness") not in (None, 0, 0.0),
                options.get("contrast") not in (None, 1, 1.0),
                options.get("saturation") not in (None, 1, 1.0),
                options.get("blur") not in (None, 0, 0.0),
                options.get("sharpen") not in (None, 0, 0.0),
                options.get("rotate") not in (None, 0, 0.0),
                options.get("denoise"),
                options.get("lut_file"),
                options.get("flip_horizontal"),
                options.get("flip_vertical"),
                options.get("grayscale"),
                options.get("sepia"),
                options.get("invert"),
                options.get("deinterlace"),
            ]
        )

    @staticmethod
    def _denoise_display_map() -> dict[str, str]:
        return {
            t("filters.denoiseOff"): "",
            t("filters.denoiseLight"): "light",
            t("filters.denoiseModerate"): "moderate",
            t("filters.denoiseStrong"): "strong",
            t("filters.denoiseUltra"): "ultra",
        }

    def _update_summary(self) -> None:
        try:
            options = self._collect_filter_options()
        except ValueError:
            self.summary_label.configure(text=t("filters.summaryPending"))
            return
        if not self._has_meaningful_filters(options):
            self.summary_label.configure(text=t("filters.summaryEmpty"))
            return

        label_map = {
            "brightness": t("filters.brightnessLabel"),
            "contrast": t("filters.contrastLabel"),
            "saturation": t("filters.saturationLabel"),
            "blur": t("filters.blurLabel"),
            "sharpen": t("filters.sharpenLabel"),
            "rotate": t("filters.rotateLabel"),
            "denoise": t("filters.denoiseLabel"),
            "lut_file": t("filters.lutFileLabel"),
            "flip_horizontal": t("filters.flipHorizontal"),
            "flip_vertical": t("filters.flipVertical"),
            "grayscale": t("filters.grayscale"),
            "sepia": t("filters.sepia"),
            "invert": t("filters.invert"),
            "deinterlace": t("filters.deinterlace"),
        }
        summary_parts = []
        for key, value in options.items():
            if key in {"contrast", "saturation"} and value in (1, 1.0):
                continue
            if value in (None, False, "", 0, 0.0):
                continue
            if isinstance(value, bool):
                summary_parts.append(label_map.get(key, key))
            else:
                summary_parts.append(f"{label_map.get(key, key)}: {value}")
        self.summary_label.configure(text=" • ".join(summary_parts) if summary_parts else t("filters.summaryEmpty"))

    def _append_log(self, message: str) -> None:
        self.log_text.insert("end", f"{message}\n")
        self.log_text.see("end")

    def _set_running(self, is_running: bool) -> None:
        self._is_running = is_running
        if is_running:
            set_button_loading_state(self.apply_btn, True, loading_text=t("filters.runningButton"))
            self.cancel_btn.configure(state="normal", fg_color=Colors.BTN_SECONDARY, hover_color=Colors.BTN_SECONDARY_HOVER, text_color=Colors.TEXT_PRIMARY)
        else:
            set_button_loading_state(self.apply_btn, False, original_text=f"{Icons.FILTERS} {t('filters.applyButton')}")
            self.cancel_btn.configure(state="disabled", fg_color=Colors.BTN_DISABLED, hover_color=Colors.BTN_DISABLED, text_color=Colors.TEXT_MUTED)

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

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
            operation="apply_filters",
            title=Path(output_path).name if output_path else task.name,
            input_paths=[self._active_task_context.get("input_file", "")],
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

    def _apply_filters(self) -> None:
        if self._is_running:
            return

        input_file = self.input_entry.get().strip()
        output_file = self.output_entry.get().strip()
        if not input_file:
            self._show_error(t("filters.inputRequired"))
            return
        if not output_file:
            self._show_error(t("filters.outputRequired"))
            return

        try:
            options = self._collect_filter_options()
        except ValueError as exc:
            self._show_error(str(exc))
            return

        if not self._has_meaningful_filters(options):
            self._show_error(t("filters.noFilters"))
            return

        self.error_panel.hide_error()
        self.progress_bar.set(0)
        self.status_label.configure(text=t("filters.started"))
        self.log_text.delete("1.0", "end")
        self._append_log(f"{input_file} -> {output_file}")
        self._set_running(True)

        self._active_task_context = {
            "input_file": input_file,
            "output_path": output_file,
        }
        self._active_task_id = self.task_queue.add_task(
            task_type=TaskType.APPLY_FILTERS,
            name=t("filters.applyButton"),
            execute_fn=self._runner.apply_filters,
            kwargs={
                "input_file": input_file,
                "output_file": output_file,
                **options,
            },
            on_progress=self._on_task_progress,
            on_complete=self._on_task_complete,
            on_error=self._on_task_error,
            on_cancel=self._on_task_cancel,
            cancel_fn=self._runner.cancel,
        )
        if self.show_queue_tab_callback:
            self.show_queue_tab_callback()

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
        self.status_label.configure(text=t("filters.completed"))
        output_path = (task.result.output_path if task.result else "") or self._active_task_context.get("output_path", "")
        self._append_log(output_path)
        self._persist_task_record(task)
        auto_add_callback = getattr(self, "auto_add_to_library_callback", None)
        if callable(auto_add_callback) and output_path:
            metadata = dict(task.result.metadata) if task.result and isinstance(task.result.metadata, dict) else {}
            metadata.update({"input_file": self._active_task_context.get("input_file", "")})
            auto_add_callback(output_path, source_type="filters", metadata=metadata)
        toast = self.toast_manager_getter()
        if toast and output_path:
            toast.show_success(t("filters.successToast", output=Path(output_path).name))
        self._reset_active_task()

    def _on_task_error(self, task: Task, error_message: str) -> None:
        if task.id != self._active_task_id:
            return
        self._set_running(False)
        self.progress_bar.set(0)
        self.status_label.configure(text=t("filters.failed"))
        self._append_log(error_message)
        self._show_error(error_message, raw_error=error_message)
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
        self.status_label.configure(text=t("filters.cancelled"))
        self._append_log(t("filters.cancelled"))
        self._persist_task_record(task, status_override="cancelled")
        self._reset_active_task()

    def _cancel_filters(self) -> None:
        if not self._active_task_id:
            return
        if self.task_queue.cancel_task(self._active_task_id):
            self.status_label.configure(text=t("filters.cancelled"))

    def _show_error(self, message: str, raw_error: Optional[str] = None) -> None:
        self.error_panel.show_error(message, raw_error or message)

    # ------------------------------------------------------------------
    # Shortcuts / lifecycle
    # ------------------------------------------------------------------

    def _on_ctrl_enter(self, event=None):
        if not self.winfo_viewable():
            return
        if not self._is_running:
            self._apply_filters()

    def _on_escape(self, event=None):
        if not self.winfo_viewable():
            return
        if self._is_running:
            self._cancel_filters()
        else:
            self.error_panel.hide_error()

    def _on_ctrl_l(self, event=None):
        if not self.winfo_viewable():
            return
        self.input_entry.delete(0, "end")
        self.output_entry.delete(0, "end")
        self.lut_entry.delete(0, "end")
        for entry in self.numeric_entries.values():
            entry.delete(0, "end")
        self.numeric_entries["brightness"].insert(0, "0")
        self.numeric_entries["contrast"].insert(0, "1.0")
        self.numeric_entries["saturation"].insert(0, "1.0")
        self.denoise_combo.set(t("filters.denoiseOff"))
        for var in self.effect_vars.values():
            var.set(False)
        self.progress_bar.set(0)
        self.status_label.configure(text=t("filters.ready"))
        self.log_text.delete("1.0", "end")
        self.error_panel.hide_error()
        self._reset_active_task()
        self._update_summary()
        return "break"

    def destroy(self):
        try:
            self._runner.cancel()
        except Exception:
            pass
        super().destroy()
