"""
Queue Panel - Real-time task queue visualization
Displays queued, active, and completed download/conversion jobs
"""

from typing import Callable, Dict, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.core.task_manager import Task, TaskStatus, get_task_queue
from ravn_app.ui.animation_manager import get_animation_manager
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes
from ravn_app.ui.ui_components import EmptyStateWidget


class QueueItemWidget(ctk.CTkFrame):
    """Widget representing a single queue item"""
    _SPINNER_FRAMES = ("◐", "◓", "◑", "◒")

    def __init__(
        self,
        parent,
        task: Task,
        on_cancel: Optional[Callable[[str], None]] = None,
        on_open_folder: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.task = task
        self.on_cancel = on_cancel
        self.on_open_folder = on_open_folder

        self.configure(
            fg_color=Colors.BG_SURFACE,
            corner_radius=Sizes.CORNER_MD
        )
        self.animation_manager = get_animation_manager()
        self._spinner_index = 0
        self._spinner_after_id = None
        self._pulse_after_id = None
        self._pulse_state = False
        self._last_status = task.status
        self._success_after_id = None

        self.accent_bar = ctk.CTkFrame(
            self,
            width=4,
            fg_color=self._get_status_color(task.status),
            corner_radius=Sizes.CORNER_SM,
        )
        self.accent_bar.pack(side="left", fill="y", padx=(6, 0), pady=8)

        # Left: Status icon and info
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        # Status icon
        status_icon = self._get_status_icon(task.status)
        self.status_label = ctk.CTkLabel(
            left_frame,
            text=status_icon,
            font=Fonts.H2,
            width=30,
            text_color=self._get_status_color(task.status),
        )
        self.status_label.pack(side="left", padx=(0, 8))

        # Info column
        info_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True)

        # Task name
        self.name_label = ctk.CTkLabel(
            info_frame,
            text=task.name,
            font=Fonts.LABEL_BOLD,
            anchor="w",
            wraplength=300,
        )
        self.name_label.pack(anchor="w", fill="x")

        # Status text
        self.status_text_label = ctk.CTkLabel(
            info_frame,
            text=self._get_status_text(task),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w"
        )
        self.status_text_label.pack(anchor="w", fill="x")

        # Progress bar (shown only when running)
        if task.status == TaskStatus.RUNNING:
            self.progress_bar = ctk.CTkProgressBar(info_frame, height=4)
            self.progress_bar.configure(
                progress_color=Colors.ACCENT,
                fg_color=Colors.PROGRESS_BG,
            )
            self.progress_bar.set(task.progress / 100.0)
            self.progress_bar.pack(fill="x", pady=(4, 0))
        else:
            self.progress_bar = None

        # Right: Action buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(side="right", padx=10, pady=8)

        if task.status == TaskStatus.RUNNING and on_cancel:
            self.cancel_btn = ctk.CTkButton(
                button_frame,
                text=f"{Icons.STOP} {t('queue.cancel')}",
                command=lambda: on_cancel(task.id),
                width=80,
                height=Sizes.BTN_HEIGHT_SM,
                fg_color=Colors.ERROR,
                hover_color=Colors.ERROR_HOVER,
                font=Fonts.SMALL,
                corner_radius=Sizes.CORNER_SM,  # POL-22
            )
            self.cancel_btn.pack()
            self.cancel_btn.configure(cursor=Cursors.POINTER)  # POL-27
        elif task.status == TaskStatus.COMPLETED and on_open_folder and task.result and task.result.output_path:
            self.open_btn = ctk.CTkButton(
                button_frame,
                text=f"{Icons.FOLDER} {t('queue.folder')}",
                command=lambda: on_open_folder(task.result.output_path),
                width=80,
                height=Sizes.BTN_HEIGHT_SM,
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                font=Fonts.SMALL,
                corner_radius=Sizes.CORNER_SM,  # POL-22
            )
            self.open_btn.pack()
            self.open_btn.configure(cursor=Cursors.POINTER)  # POL-27

        self._sync_running_animation(task.status)
        self._sync_error_pulse(task.status)

    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get icon for task status"""
        icons = {
            TaskStatus.PENDING: Icons.QUEUED_STATUS,
            TaskStatus.QUEUED: Icons.QUEUED_STATUS,
            TaskStatus.RUNNING: Icons.RUNNING_STATUS,
            TaskStatus.COMPLETED: Icons.SUCCESS_STATUS,
            TaskStatus.FAILED: Icons.ERROR_STATUS,
            TaskStatus.CANCELLED: Icons.CANCEL_BTN,
            TaskStatus.PAUSED: Icons.PAUSED_STATUS,
        }
        return icons.get(status, Icons.INFO)

    def _get_status_color(self, status: TaskStatus) -> str:
        """Get semantic text color for task status icon."""
        colors = {
            TaskStatus.PENDING: Colors.STATUS_QUEUED,
            TaskStatus.QUEUED: Colors.STATUS_QUEUED,
            TaskStatus.RUNNING: Colors.STATUS_RUNNING,
            TaskStatus.COMPLETED: Colors.STATUS_DONE,
            TaskStatus.FAILED: Colors.STATUS_ERROR,
            TaskStatus.CANCELLED: Colors.STATUS_CANCELLED,
            TaskStatus.PAUSED: Colors.STATUS_PAUSED,
        }
        return colors.get(status, Colors.TEXT_MUTED)

    def _sync_running_animation(self, status: TaskStatus):
        """Start/stop spinner animation based on task status."""
        if status == TaskStatus.RUNNING:
            self.status_label.configure(text_color=Colors.STATUS_RUNNING)
            if self._spinner_after_id is None:
                self._animate_running_spinner()
            return

        if self._spinner_after_id is not None:
            self.after_cancel(self._spinner_after_id)
            self._spinner_after_id = None

    def _sync_error_pulse(self, status: TaskStatus):
        """Start/stop pulsing effect for failed status icons."""
        if status == TaskStatus.FAILED:
            if self._pulse_after_id is None:
                self._animate_error_pulse()
            return

        if self._pulse_after_id is not None:
            self.after_cancel(self._pulse_after_id)
            self._pulse_after_id = None
            self._pulse_state = False

    def _animate_running_spinner(self):
        """Animate running icon at roughly 3 rotations per second."""
        if self.task.status != TaskStatus.RUNNING:
            self._spinner_after_id = None
            return

        icon = self._SPINNER_FRAMES[self._spinner_index % len(self._SPINNER_FRAMES)]
        self.status_label.configure(text=icon, text_color=Colors.STATUS_RUNNING)
        self._spinner_index += 1
        self._spinner_after_id = self.after(90, self._animate_running_spinner)

    def _animate_error_pulse(self):
        """Pulse failed-status icon between strong and soft red."""
        if self.task.status != TaskStatus.FAILED:
            self._pulse_after_id = None
            return

        color = Colors.ERROR if self._pulse_state else Colors.ERROR_HOVER
        self.status_label.configure(text=Icons.ERROR_STATUS, text_color=color)
        self._pulse_state = not self._pulse_state
        self._pulse_after_id = self.after(280, self._animate_error_pulse)

    def _animate_success_reveal(self):
        """Reveal success checkmark after 150ms for subtle completion feedback."""
        self.status_label.configure(text="")

        def reveal():
            self._success_after_id = None
            if self.task.status == TaskStatus.COMPLETED:
                self.status_label.configure(text=Icons.SUCCESS_STATUS, text_color=Colors.STATUS_DONE)
                self.animation_manager.animate_success_flash(
                    self.status_label,
                    duration=300,
                    base_color=Colors.STATUS_DONE,
                    flash_color=Colors.SUCCESS_FLASH,
                )

        self._success_after_id = self.after(150, reveal)

    def animate_entrance(self):
        """Animate queue item entrance with subtle slide-in feel."""
        self.animation_manager.animate_queue_entrance(
            self,
            duration=150,
            start_pad=12,
            end_pad=4,
        )

    def _get_status_text(self, task: Task) -> str:
        """Get human-readable status text"""
        if task.status == TaskStatus.RUNNING:
            return f"{task.progress}% - {task.progress_message}" if task.progress_message else f"{task.progress}%"
        elif task.status == TaskStatus.COMPLETED:
            duration = ""
            if task.started_at and task.completed_at:
                delta = (task.completed_at - task.started_at).total_seconds()
                duration = f" • {delta:.1f}s"
            return t("queue.statusCompleted", duration=duration)
        elif task.status == TaskStatus.FAILED:
            error_msg = task.result.error_message[:50] if task.result and task.result.error_message else t("common.unknown")
            return t("queue.statusFailed", error=error_msg)
        elif task.status == TaskStatus.CANCELLED:
            return t("queue.statusCancelled")
        elif task.status == TaskStatus.PAUSED:
            return t("queue.statusPaused")
        elif task.status == TaskStatus.QUEUED:
            return t("queue.statusQueued")
        else:
            return t("queue.statusPending")

    def update_task(self, task: Task):
        """Update widget with new task state"""
        previous_status = self.task.status
        self.task = task

        # Update status icon
        self.status_label.configure(
            text=self._get_status_icon(task.status),
            text_color=self._get_status_color(task.status),
        )
        self.accent_bar.configure(fg_color=self._get_status_color(task.status))

        # Update status text
        self.status_text_label.configure(text=self._get_status_text(task))
        self._sync_running_animation(task.status)
        self._sync_error_pulse(task.status)

        if task.status == TaskStatus.COMPLETED and previous_status != TaskStatus.COMPLETED:
            self._animate_success_reveal()

        self._last_status = task.status

        # Update progress bar
        if task.status == TaskStatus.RUNNING:
            if not self.progress_bar:
                # Create progress bar if it doesn't exist
                info_frame = self.status_text_label.master
                self.progress_bar = ctk.CTkProgressBar(info_frame, height=4)
                self.progress_bar.configure(
                    progress_color=Colors.ACCENT,
                    fg_color=Colors.PROGRESS_BG,
                )
                self.progress_bar.pack(fill="x", pady=(4, 0))
            self.progress_bar.set(task.progress / 100.0)
        elif self.progress_bar:
            self.progress_bar.pack_forget()
            self.progress_bar = None

    def destroy(self):
        """Cancel pending animation callbacks before widget destruction."""
        for after_id in (self._spinner_after_id, self._pulse_after_id, self._success_after_id):
            if after_id is None:
                continue
            try:
                self.after_cancel(after_id)
            except Exception:
                pass

        self._spinner_after_id = None
        self._pulse_after_id = None
        self._success_after_id = None
        super().destroy()


class QueuePanel(ctk.CTkFrame):
    """Main queue panel showing all tasks"""

    def __init__(
        self,
        parent,
        on_cancel_task: Optional[Callable[[str], None]] = None,
        on_open_folder: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        super().__init__(parent, **kwargs)
        self.on_cancel_task = on_cancel_task
        self.on_open_folder = on_open_folder
        self.task_widgets: Dict[str, QueueItemWidget] = {}
        self.task_queue = get_task_queue()

        self.configure(fg_color=Colors.BG_PRIMARY)

        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)

        title = ctk.CTkLabel(
            header,
            text=f"{Icons.QUEUE}  {t('queue.title')}",
            font=Fonts.H1
        )
        title.pack(side="left")

        # Stats
        self.stats_label = ctk.CTkLabel(
            header,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED
        )
        self.stats_label.pack(side="right")

        # Scrollable task list
        self.task_list = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.task_list.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        # MIC-05: Empty state widget
        self.empty_state = EmptyStateWidget(
            self.task_list,
            icon=Icons.EMPTY_LIST,
            message=t("queue.empty"),
        )
        self.empty_state.pack(fill="both", expand=True, pady=40)

        self._refresh_after_id = None
        self._last_task_snapshot = None
        self.refresh_tasks(force=True)
        self._schedule_refresh_fallback()

    def _schedule_refresh_fallback(self):
        """Keep a low-frequency fallback refresh for non-shell hosts."""
        self._refresh_after_id = self.after(2500, self._run_fallback_refresh)

    def _run_fallback_refresh(self):
        self._refresh_after_id = None
        self.refresh_tasks()
        self._schedule_refresh_fallback()

    def refresh_tasks(self, force: bool = False):
        """Refresh task list from queue manager when the task snapshot changes."""
        snapshot = self.task_queue.get_ui_snapshot()
        if not force and snapshot == self._last_task_snapshot:
            return

        self._last_task_snapshot = snapshot
        tasks = self.task_queue.get_all_tasks()

        # Update stats
        active = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        queued = sum(1 for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED))
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)

        if tasks:
            self.stats_label.configure(
                text=t("queue.stats", active=active, queued=queued, completed=completed)
            )
            self.empty_state.pack_forget()
        else:
            self.stats_label.configure(text="")
            self.empty_state.pack(fill="both", expand=True, pady=40)

        current_task_ids = {t.id for t in tasks}

        for task_id in list(self.task_widgets.keys()):
            if task_id not in current_task_ids:
                self.task_widgets[task_id].destroy()
                del self.task_widgets[task_id]

        for task in tasks:
            if task.id in self.task_widgets:
                self.task_widgets[task.id].update_task(task)
            else:
                widget = QueueItemWidget(
                    self.task_list,
                    task,
                    on_cancel=self.on_cancel_task,
                    on_open_folder=self.on_open_folder,
                )
                widget.pack(fill="x", pady=12)
                widget.animate_entrance()
                self.task_widgets[task.id] = widget

    def clear_completed(self):
        """Remove completed/cancelled tasks from the queue UI and backing store."""
        self.task_queue.clear_completed()
        self.refresh_tasks(force=True)

    def destroy(self):
        if self._refresh_after_id is not None:
            try:
                self.after_cancel(self._refresh_after_id)
            except Exception:
                pass
            self._refresh_after_id = None
        for widget in list(self.task_widgets.values()):
            try:
                widget.destroy()
            except Exception:
                pass
        self.task_widgets.clear()
        super().destroy()
