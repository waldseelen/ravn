"""
Queue Panel - Real-time task queue visualization
Displays queued, active, and completed download/conversion jobs
"""

import customtkinter as ctk
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

from ravn_app.core.task_manager import Task, TaskStatus, TaskType, get_task_queue
from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes, Icons


class QueueItemWidget(ctk.CTkFrame):
    """Widget representing a single queue item"""
    
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
        
        # Left: Status icon and info
        left_frame = ctk.CTkFrame(self, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)
        
        # Status icon
        status_icon = self._get_status_icon(task.status)
        self.status_label = ctk.CTkLabel(
            left_frame,
            text=status_icon,
            font=Fonts.H2,
            width=30
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
            anchor="w"
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
                text=f"{Icons.STOP} İptal",
                command=lambda: on_cancel(task.id),
                width=80,
                height=28,
                fg_color=Colors.ERROR,
                hover_color=Colors.ERROR_HOVER,
                font=Fonts.SMALL
            )
            self.cancel_btn.pack()
        elif task.status == TaskStatus.COMPLETED and on_open_folder and task.result and task.result.output_path:
            self.open_btn = ctk.CTkButton(
                button_frame,
                text=f"{Icons.FOLDER} Klasör",
                command=lambda: on_open_folder(task.result.output_path),
                width=80,
                height=28,
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                font=Fonts.SMALL
            )
            self.open_btn.pack()
    
    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get icon for task status"""
        icons = {
            TaskStatus.PENDING: Icons.PENDING,
            TaskStatus.QUEUED: Icons.QUEUED,
            TaskStatus.RUNNING: Icons.RUNNING,
            TaskStatus.COMPLETED: Icons.COMPLETED,
            TaskStatus.FAILED: Icons.FAILED,
            TaskStatus.CANCELLED: Icons.CANCELLED,
            TaskStatus.PAUSED: Icons.PAUSED,
        }
        return icons.get(status, Icons.INFO)
    
    def _get_status_text(self, task: Task) -> str:
        """Get human-readable status text"""
        if task.status == TaskStatus.RUNNING:
            return f"{task.progress}% - {task.progress_message}" if task.progress_message else f"{task.progress}%"
        elif task.status == TaskStatus.COMPLETED:
            duration = ""
            if task.started_at and task.completed_at:
                delta = (task.completed_at - task.started_at).total_seconds()
                duration = f" • {delta:.1f}s"
            return f"Tamamlandı{duration}"
        elif task.status == TaskStatus.FAILED:
            error_msg = task.result.error_message[:50] if task.result and task.result.error_message else "Hata"
            return f"Başarısız: {error_msg}"
        elif task.status == TaskStatus.CANCELLED:
            return "İptal edildi"
        elif task.status == TaskStatus.PAUSED:
            return "Duraklatıldı"
        elif task.status == TaskStatus.QUEUED:
            return "Kuyrukta bekliyor"
        else:
            return "Beklemede"
    
    def update_task(self, task: Task):
        """Update widget with new task state"""
        self.task = task
        
        # Update status icon
        self.status_label.configure(text=self._get_status_icon(task.status))
        
        # Update status text
        self.status_text_label.configure(text=self._get_status_text(task))
        
        # Update progress bar
        if task.status == TaskStatus.RUNNING:
            if not self.progress_bar:
                # Create progress bar if it doesn't exist
                info_frame = self.status_text_label.master
                self.progress_bar = ctk.CTkProgressBar(info_frame, height=4)
                self.progress_bar.pack(fill="x", pady=(4, 0))
            self.progress_bar.set(task.progress / 100.0)
        elif self.progress_bar:
            self.progress_bar.pack_forget()
            self.progress_bar = None


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
            text=f"{Icons.QUEUE}  Görev Kuyruğu",
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
        
        # Placeholder when empty
        self.empty_label = ctk.CTkLabel(
            self.task_list,
            text="Henüz görev yok.\nİndirme veya dönüştürme başlattığınızda burada görünecek.",
            font=Fonts.LABEL,
            text_color=Colors.TEXT_MUTED,
            justify="center"
        )
        self.empty_label.pack(pady=40)
        
        # Start auto-refresh
        self._refresh_tasks()
    
    def _refresh_tasks(self):
        """Refresh task list from queue manager"""
        tasks = self.task_queue.get_all_tasks()
        
        # Update stats
        active = sum(1 for t in tasks if t.status == TaskStatus.RUNNING)
        queued = sum(1 for t in tasks if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED))
        completed = sum(1 for t in tasks if t.status == TaskStatus.COMPLETED)
        
        if tasks:
            self.stats_label.configure(
                text=f"Aktif: {active} • Kuyruk: {queued} • Tamamlanan: {completed}"
            )
            self.empty_label.pack_forget()
        else:
            self.stats_label.configure(text="")
            self.empty_label.pack(pady=40)
        
        # Update existing widgets or create new ones
        current_task_ids = {t.id for t in tasks}
        
        # Remove widgets for tasks no longer in queue
        for task_id in list(self.task_widgets.keys()):
            if task_id not in current_task_ids:
                self.task_widgets[task_id].destroy()
                del self.task_widgets[task_id]
        
        # Update or create widgets
        for task in tasks:
            if task.id in self.task_widgets:
                self.task_widgets[task.id].update_task(task)
            else:
                widget = QueueItemWidget(
                    self.task_list,
                    task,
                    on_cancel=self.on_cancel_task,
                    on_open_folder=self.on_open_folder
                )
                widget.pack(fill="x", pady=4)
                self.task_widgets[task.id] = widget
        
        # Schedule next refresh
        self.after(1000, self._refresh_tasks)
    
    def clear_completed(self):
        """Remove completed tasks from queue"""
        tasks = self.task_queue.get_all_tasks()
        for task in tasks:
            if task.status == TaskStatus.COMPLETED:
                # Remove from queue (implementation depends on TaskQueue API)
                pass
