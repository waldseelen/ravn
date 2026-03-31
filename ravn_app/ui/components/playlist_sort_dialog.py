"""Sortable playlist preview dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Fonts


class PlaylistSortDialog(ctk.CTkToplevel):
    """Show playlist entries in a sortable table and apply selected ordering."""

    def __init__(
        self,
        parent,
        entries: List[Dict[str, Any]],
        quality_label: str,
        metrics_getter: Callable[[Dict[str, Any], str], Dict[str, Any]],
        duration_formatter: Callable[[Any], str],
        size_formatter: Callable[[float], str],
        on_download: Callable[[List[Dict[str, Any]]], None],
    ):
        super().__init__(parent)
        self.title(t("download.playlistSortTitle"))
        self.geometry("980x560")
        self.minsize(840, 460)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self._quality_label = quality_label
        self._metrics_getter = metrics_getter
        self._duration_formatter = duration_formatter
        self._size_formatter = size_formatter
        self._on_download = on_download
        self._sort_key = "title"
        self._descending = False

        self._rows = self._build_rows(entries)

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._refresh_tree()

    @staticmethod
    def _resolve_color(token: str | tuple[str, str]) -> str:
        if not isinstance(token, tuple):
            return token
        return token[0] if ctk.get_appearance_mode().lower() == "light" else token[1]

    def _build_rows(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, entry in enumerate(entries):
            metrics = self._metrics_getter(entry, self._quality_label)
            title = str(entry.get("title") or "Unknown")
            album = str(entry.get("album") or "")
            channel = str(entry.get("channel") or entry.get("uploader") or "")
            size_mb = float(metrics.get("size_mb") or 0.0)
            duration_sec = float(entry.get("duration") or 0.0)

            rows.append(
                {
                    "index": index,
                    "entry": entry,
                    "selected": True,
                    "title": title,
                    "title_sort": title.casefold(),
                    "album": album,
                    "album_sort": album.casefold(),
                    "channel": channel,
                    "channel_sort": channel.casefold(),
                    "size_mb": size_mb,
                    "duration": duration_sec,
                }
            )

        return rows

    def _build_ui(self) -> None:
        info = ctk.CTkLabel(
            self,
            text=t("download.playlistSortQuality", quality=self._quality_label),
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL,
            anchor="w",
        )
        info.pack(fill="x", padx=12, pady=(12, 6))

        self.selection_summary_label = ctk.CTkLabel(
            self,
            text="",
            text_color=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            anchor="w",
        )
        self.selection_summary_label.pack(fill="x", padx=12, pady=(0, 8))

        content_wrap = ctk.CTkFrame(self, fg_color="transparent")
        content_wrap.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        frame = ctk.CTkFrame(content_wrap, fg_color=Colors.BG_SURFACE)
        frame.pack(fill="both", expand=True, pady=(0, 8))

        style = ttk.Style(self)
        try:
            # Native Windows themes ignore several custom heading colors.
            # Clam honors explicit foreground/background so headers remain readable.
            style.theme_use("clam")
        except tk.TclError:
            pass

        header_bg = self._resolve_color(Colors.BG_SURFACE)
        header_fg = self._resolve_color(Colors.ACCENT)
        body_bg = self._resolve_color(Colors.BG_CARD)
        body_fg = self._resolve_color(Colors.TEXT_PRIMARY)
        selected_bg = self._resolve_color(Colors.BTN_SECONDARY)

        style.configure(
            "Ravn.Treeview",
            background=body_bg,
            fieldbackground=body_bg,
            foreground=body_fg,
            bordercolor=self._resolve_color(Colors.BORDER),
            borderwidth=0,
            rowheight=26,
        )
        style.configure(
            "Ravn.Treeview.Heading",
            background=header_bg,
            foreground=header_fg,
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        hover_bg = self._resolve_color(Colors.BG_HOVER)

        style.map(
            "Ravn.Treeview",
            background=[("selected", selected_bg), ("hover", hover_bg)],
            foreground=[("selected", body_fg)],
        )
        style.map(
            "Ravn.Treeview.Heading",
            background=[("active", selected_bg)],
            foreground=[("active", header_fg)],
        )

        columns = ("selected", "title", "size", "duration", "album", "channel")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=16, style="Ravn.Treeview")
        self.tree.heading("selected", text=t("download.playlistSortSelect"), command=self._toggle_all)
        self.tree.heading("title", text=t("download.playlistSortName"), command=lambda: self._sort_by("title"))
        self.tree.heading("size", text=t("download.playlistSortSize"), command=lambda: self._sort_by("size"))
        self.tree.heading("duration", text=t("download.playlistSortDuration"), command=lambda: self._sort_by("duration"))
        self.tree.heading("album", text=t("download.playlistSortAlbum"), command=lambda: self._sort_by("album"))
        self.tree.heading("channel", text=t("download.playlistSortChannel"), command=lambda: self._sort_by("channel"))

        self.tree.column("selected", width=56, anchor=tk.CENTER)
        self.tree.column("title", width=320, anchor=tk.W)
        self.tree.column("size", width=120, anchor=tk.E)
        self.tree.column("duration", width=110, anchor=tk.CENTER)
        self.tree.column("album", width=180, anchor=tk.W)
        self.tree.column("channel", width=180, anchor=tk.W)

        yscroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Motion>", self._on_tree_motion)
        self._last_hovered_item = None

        btn_frame = ctk.CTkFrame(content_wrap, fg_color=Colors.BG_SURFACE)
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text=t("download.playlistSortSelectAll"),
            command=self._select_all,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=34,
        ).pack(side="left")
        ctk.CTkButton(
            btn_frame,
            text=t("download.playlistSortClear"),
            command=self._clear_selection,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=34,
        ).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkButton(
            btn_frame,
            text=t("download.playlistSortResetOrder"),
            command=self._reset_order,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=34,
        ).pack(
            side="left"
        )
        ctk.CTkButton(
            btn_frame,
            text=t("download.downloadButton"),
            command=self._download,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
            height=34,
        ).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(
            btn_frame,
            text=t("common.close"),
            command=self.destroy,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=34,
        ).pack(side="right")

    def _sort_value(self, row: Dict[str, Any], sort_key: str) -> Any:
        if sort_key == "title":
            return row["title_sort"]
        if sort_key == "size":
            return row["size_mb"]
        if sort_key == "duration":
            return row["duration"]
        if sort_key == "album":
            return row["album_sort"]
        if sort_key == "channel":
            return row["channel_sort"]
        return row["index"]

    def _sort_by(self, sort_key: str) -> None:
        if self._sort_key == sort_key:
            self._descending = not self._descending
        else:
            self._sort_key = sort_key
            self._descending = False

        self._rows.sort(
            key=lambda row: self._sort_value(row, self._sort_key),
            reverse=self._descending,
        )
        self._refresh_tree()

    def _reset_order(self) -> None:
        self._sort_key = "title"
        self._descending = False
        self._rows.sort(key=lambda row: row["index"])
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)

        for row in self._rows:
            size_text = self._size_formatter(row["size_mb"]) if row["size_mb"] > 0 else "-"
            duration_text = self._duration_formatter(row["duration"]) if row["duration"] > 0 else "-"
            album_text = row["album"] or "-"
            channel_text = row["channel"] or "-"
            marker = "☑" if row.get("selected", True) else "☐"
            self.tree.insert(
                "",
                "end",
                iid=str(row["index"]),
                values=(
                    marker,
                    row["title"],
                    size_text,
                    duration_text,
                    album_text,
                    channel_text,
                ),
            )
        self._update_selection_summary()

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        value = float(max(0, size_bytes))
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
            value /= 1024
        return "0 B"

    def _update_selection_summary(self) -> None:
        selected_rows = [row for row in self._rows if row.get("selected", True)]
        selected_count = len(selected_rows)
        selected_size_mb = sum(float(row.get("size_mb") or 0.0) for row in selected_rows)
        selected_size_bytes = int(selected_size_mb * 1024 * 1024)
        summary = t(
            "download.playlistSortSelectedTotal",
            count=selected_count,
            size=self._format_bytes(selected_size_bytes),
        )
        self.selection_summary_label.configure(text=summary)

    def _on_double_click(self, event) -> None:
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        column_id = self.tree.identify_column(event.x)
        if column_id != "#1":
            return

        row_index = int(item_id)
        for row in self._rows:
            if row["index"] == row_index:
                row["selected"] = not row.get("selected", True)
                break

    def _on_tree_motion(self, event) -> None:
        """Handle mouse motion to highlight hovered rows."""
        item_id = self.tree.identify_row(event.y)

        # Clear hover from previously hovered item
        if self._last_hovered_item and self._last_hovered_item != item_id:
            self.tree.item(self._last_hovered_item, tags=())

        # Apply hover to current item
        if item_id:
            self.tree.item(item_id, tags=("hover",))
            self._last_hovered_item = item_id
        else:
            self._last_hovered_item = None

        self._refresh_tree()

    def _select_all(self) -> None:
        for row in self._rows:
            row["selected"] = True
        self._refresh_tree()

    def _clear_selection(self) -> None:
        for row in self._rows:
            row["selected"] = False
        self._refresh_tree()

    def _toggle_all(self) -> None:
        all_selected = all(row.get("selected", True) for row in self._rows)
        for row in self._rows:
            row["selected"] = not all_selected
        self._refresh_tree()

    def _download(self) -> None:
        selected_entries = [row["entry"] for row in self._rows if row.get("selected", True)]
        if not selected_entries:
            return
        self._on_download(selected_entries)
        self.destroy()
