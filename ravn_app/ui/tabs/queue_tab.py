"""Queue tab wrapper that hosts the queue panel."""

from typing import Callable

import customtkinter as ctk

from ravn_app.ui.queue_panel import QueuePanel


class QueueTab(ctk.CTkFrame):
    """Dedicated queue tab container."""

    def __init__(
        self,
        parent,
        on_cancel_task: Callable[[str], None],
        on_open_folder: Callable[[str], None],
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)

        queue_panel = QueuePanel(
            self,
            on_cancel_task=on_cancel_task,
            on_open_folder=on_open_folder,
            fg_color="transparent",
        )
        queue_panel.pack(fill="both", expand=True)
