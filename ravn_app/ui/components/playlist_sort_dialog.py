"""Sortable playlist preview dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Dict, List

import customtkinter as ctk


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
        self.title("Playlist Siralama")
        self.geometry("980x560")
        self.minsize(840, 460)

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
            text=f"Siralama kalitesi: {self._quality_label}",
            anchor="w",
        )
        info.pack(fill="x", padx=12, pady=(12, 6))

        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        columns = ("selected", "title", "size", "duration", "album", "channel")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings", height=18)
        self.tree.heading("selected", text="Sec", command=self._toggle_all)
        self.tree.heading("title", text="Isim", command=lambda: self._sort_by("title"))
        self.tree.heading("size", text="Boyut", command=lambda: self._sort_by("size"))
        self.tree.heading("duration", text="Sure", command=lambda: self._sort_by("duration"))
        self.tree.heading("album", text="Album", command=lambda: self._sort_by("album"))
        self.tree.heading("channel", text="Kanal", command=lambda: self._sort_by("channel"))

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

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkButton(btn_frame, text="Tumunu Sec", command=self._select_all).pack(side="left")
        ctk.CTkButton(btn_frame, text="Secimi Temizle", command=self._clear_selection).pack(
            side="left", padx=(8, 0)
        )
        ctk.CTkButton(btn_frame, text="Varsayilan Siraya Don", command=self._reset_order).pack(
            side="left"
        )
        ctk.CTkButton(btn_frame, text="Indir", command=self._download).pack(
            side="right", padx=(8, 0)
        )
        ctk.CTkButton(btn_frame, text="Kapat", command=self.destroy).pack(side="right")

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
