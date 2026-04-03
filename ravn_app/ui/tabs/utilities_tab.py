"""Utilities tab for quick media helpers and smart operations."""

from __future__ import annotations

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

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the utilities UI with progressive disclosure."""
        content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        # Header
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

        # Input/Output section
        io_frame = ctk.CTkFrame(content, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        io_frame.pack(fill="x", pady=Spacing.SM)

        io_inner = ctk.CTkFrame(io_frame, fg_color="transparent")
        io_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.MD)

        # Input file
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

        # Output file
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

        # Quick Helpers Panel
        self.quick_panel = CollapsiblePanel(
            content,
            title=t("utilities.quickHelpersTitle"),
            subtitle="remux • extract-audio • mute • trim • preview • thumbnail",
            expanded=True,
        )
        self.quick_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_quick_helpers(self.quick_panel.content_frame())

        # Audio Utility Panel
        self.audio_panel = CollapsiblePanel(
            content,
            title=t("utilities.audioUtilityTitle"),
            subtitle="volume • fade • bitrate • channels • silence • loudnorm",
            expanded=False,
        )
        self.audio_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_audio_utilities(self.audio_panel.content_frame())

        # Video Utility Panel
        self.video_panel = CollapsiblePanel(
            content,
            title=t("utilities.videoUtilityTitle"),
            subtitle="scale • crop • pad • rotate • fps • color • blur/sharpen • deinterlace",
            expanded=False,
        )
        self.video_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_video_utilities(self.video_panel.content_frame())

        # Smart Helpers Panel
        self.smart_panel = CollapsiblePanel(
            content,
            title=t("utilities.smartHelpersTitle"),
            subtitle="blackdetect • scene-preview • scene-thumbnail",
            expanded=False,
        )
        self.smart_panel.pack(fill="x", pady=(Spacing.SM, 0))
        self._build_smart_helpers(self.smart_panel.content_frame())

        # Process button
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(Spacing.MD, 0))

        self.process_btn = ctk.CTkButton(
            btn_frame,
            text=t("utilities.process"),
            command=self._process_operation,
            font=Fonts.BTN,
            height=Sizes.BTN_HEIGHT,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_ON_ACCENT,
            cursor=Cursors.POINTER,
        )
        self.process_btn.pack(side="left", fill="x", expand=True)

    def _build_quick_helpers(self, parent: ctk.CTkFrame) -> None:
        """Build quick helpers operation selector."""
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self.quick_operation = ctk.CTkComboBox(
            parent,
            values=[
                t("utilities.remux"),
                t("utilities.extractAudio"),
                t("utilities.mute"),
                t("utilities.trim"),
                t("utilities.previewClip"),
                t("utilities.thumbnail"),
            ],
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=self._on_operation_change,
        )
        style_combo(self.quick_operation)
        self.quick_operation.set(t("utilities.remux"))
        self.quick_operation.pack(fill="x", pady=(0, Spacing.SM))

        # Parameter frame (dynamic based on operation)
        self.quick_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.quick_params_frame.pack(fill="x")

    def _build_audio_utilities(self, parent: ctk.CTkFrame) -> None:
        """Build audio utilities operation selector."""
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self.audio_operation = ctk.CTkComboBox(
            parent,
            values=[
                t("utilities.volume"),
                t("utilities.fade"),
                t("utilities.bitrate"),
                t("utilities.stereoMono"),
                t("utilities.silenceDetect"),
                t("utilities.loudnorm"),
            ],
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=self._on_operation_change,
        )
        style_combo(self.audio_operation)
        self.audio_operation.set(t("utilities.volume"))
        self.audio_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.audio_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.audio_params_frame.pack(fill="x")

    def _build_video_utilities(self, parent: ctk.CTkFrame) -> None:
        """Build video utilities operation selector."""
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self.video_operation = ctk.CTkComboBox(
            parent,
            values=[
                t("utilities.scale"),
                t("utilities.crop"),
                t("utilities.pad"),
                t("utilities.rotate"),
                t("utilities.fps"),
                t("utilities.brightness"),
                t("utilities.blur"),
                t("utilities.deinterlace"),
            ],
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=self._on_operation_change,
        )
        style_combo(self.video_operation)
        self.video_operation.set(t("utilities.scale"))
        self.video_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.video_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.video_params_frame.pack(fill="x")

    def _build_smart_helpers(self, parent: ctk.CTkFrame) -> None:
        """Build smart helpers operation selector."""
        ctk.CTkLabel(
            parent,
            text=t("utilities.operationLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", pady=(0, Spacing.XS))

        self.smart_operation = ctk.CTkComboBox(
            parent,
            values=[
                t("utilities.blackdetect"),
                t("utilities.scenePreview"),
                t("utilities.sceneThumbnail"),
            ],
            font=Fonts.LABEL,
            dropdown_font=Fonts.LABEL,
            command=self._on_operation_change,
        )
        style_combo(self.smart_operation)
        self.smart_operation.set(t("utilities.blackdetect"))
        self.smart_operation.pack(fill="x", pady=(0, Spacing.SM))

        self.smart_params_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.smart_params_frame.pack(fill="x")

    def _on_operation_change(self, value: str) -> None:
        """Handle operation selection change (placeholder for dynamic parameter UI)."""
        # In future: update parameter frames dynamically based on selected operation
        pass

    def _browse_input(self) -> None:
        """Browse for input file."""
        file_path = filedialog.askopenfilename(
            title=t("utilities.selectFile"),
            filetypes=[("All files", "*.*"), ("Video files", "*.mp4 *.mkv *.avi *.mov"), ("Audio files", "*.mp3 *.m4a *.flac *.wav")],
        )
        if file_path:
            self.input_entry.delete(0, "end")
            self.input_entry.insert(0, file_path)

    def _browse_output(self) -> None:
        """Browse for output file."""
        file_path = filedialog.asksaveasfilename(
            title=t("utilities.selectFile"),
            defaultextension=".mp4",
            filetypes=[("All files", "*.*"), ("Video files", "*.mp4 *.mkv *.avi *.mov"), ("Audio files", "*.mp3 *.m4a *.flac *.wav")],
        )
        if file_path:
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, file_path)

    def _process_operation(self) -> None:
        """Process the selected utility operation."""
        input_file = self.input_entry.get().strip()
        output_file = self.output_entry.get().strip()

        if not input_file:
            toast = self.toast_manager_getter()
            if toast:
                toast.show_toast(t("utilities.selectInputFirst"), "warning")
            return

        # Determine which panel is expanded and get operation
        # This is a simplified version - full implementation would have dynamic parameters
        if self.quick_panel._expanded:
            operation = "remux"  # Simplified
        elif self.audio_panel._expanded:
            operation = "volume"
        elif self.video_panel._expanded:
            operation = "scale"
        else:
            operation = "blackdetect"

        # Auto-generate output if not specified
        if not output_file and operation not in ("blackdetect", "silenceDetect"):
            input_path = Path(input_file)
            output_file = str(input_path.parent / f"{input_path.stem}_utility{input_path.suffix}")
            self.output_entry.delete(0, "end")
            self.output_entry.insert(0, output_file)

        # Store operation in database
        from ravn_app.core.database import OperationRecord
        from datetime import datetime
        
        operation_record = OperationRecord(
            task_type="utility",
            operation=operation,
            title=f"{operation.title()}: {Path(input_file).name}",
            input_paths=[input_file],
            output_path=output_file or "",
            started_at=datetime.now().isoformat(),
            status="queued",
            metadata={"operation": operation, "input": input_file, "output": output_file}
        )
        
        if self.db_manager:
            try:
                self.db_manager.add_operation_record(operation_record)
            except Exception as e:
                pass  # Non-fatal if history fails

        # Queue the operation
        task = Task(
            task_id=f"utility_{operation}_{Path(input_file).name}",
            task_type=TaskType.GENERIC,
            title=f"{operation.title()}: {Path(input_file).name}",
            status="queued",
        )
        self.task_queue.add_task(task)
        self._active_task_id = task.task_id

        # Show queue tab if callback available
        if self.show_queue_tab_callback:
            self.show_queue_tab_callback()

        # Show confirmation toast
        toast = self.toast_manager_getter()
        if toast:
            toast.show_toast(f"Utility operation queued: {operation}", "success")

        # Auto-add to library if enabled and output exists
        if self.auto_add_to_library_callback and output_file:
            def on_complete():
                if Path(output_file).exists():
                    try:
                        self.auto_add_to_library_callback(
                            file_path=output_file,
                            metadata={
                                "operation": operation,
                                "input": input_file,
                                "utility_type": "media_helper"
                            }
                        )
                    except Exception:
                        pass  # Non-fatal if auto-add fails
            
            # In full implementation, this callback would be called when task completes
