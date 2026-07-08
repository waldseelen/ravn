"""Sortable playlist preview dialog."""

from __future__ import annotations

import math
import tkinter as tk
from time import perf_counter
from tkinter import ttk
from typing import Any, Callable, Dict, List, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.ui.design_tokens import Colors, Fonts
from ravn_app.ui.ui_components import style_combo, style_entry


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
        self.geometry("980x660")
        self.minsize(900, 560)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self._quality_label = quality_label
        self._metrics_getter = metrics_getter
        self._duration_formatter = duration_formatter
        self._size_formatter = size_formatter
        self._on_download = on_download
        self._perf_metrics: Dict[str, Dict[str, Any]] = {}
        self._sort_key = "index"
        self._descending = False
        # Rows open with flat-pass data only (title/duration, no real size yet); a slower
        # background pass enriches per-video size/resolution afterward via refresh_entries().
        # Without a visible "still loading" cue, the table just shows blank/zero sizes for
        # however long that enrichment takes, which reads as broken rather than in-progress.
        self._details_enriched = False
        # Treeview drops any PhotoImage it can't reach, so hold references here keyed by iid.
        self._thumb_refs: Dict[str, Any] = {}

        self._all_rows = self._build_rows(entries)
        self._rows = list(self._all_rows)

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self._apply_filters()

    def _info_label_text(self) -> str:
        base = t("download.playlistSortQuality", quality=self._quality_label)
        if self._details_enriched:
            return base
        return f"{base} • {t('download.playlistSortEnrichingDetails')}"

    @staticmethod
    def _resolve_color(token: str | tuple[str, str]) -> str:
        if not isinstance(token, tuple):
            return token
        return token[0] if ctk.get_appearance_mode().lower() == "light" else token[1]

    @staticmethod
    def _popularity_options() -> Dict[str, str]:
        return {
            "all": t("download.playlistFilterPopularityAll"),
            "top25": t("download.playlistFilterPopularityTop25"),
            "top50": t("download.playlistFilterPopularityTop50"),
            "top75": t("download.playlistFilterPopularityTop75"),
        }

    @classmethod
    def _normalize_popularity_value(cls, value: Any) -> str:
        options = cls._popularity_options()
        reverse_options = {label.lower(): key for key, label in options.items()}
        normalized_value = str(value or "").strip().lower()
        return reverse_options.get(normalized_value, normalized_value if normalized_value in options else "all")

    def _build_rows(self, entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for index, entry in enumerate(entries):
            metrics = self._metrics_getter(entry, self._quality_label)
            title = str(entry.get("title") or "Unknown")
            album = str(entry.get("album") or "")
            channel = str(entry.get("channel") or entry.get("uploader") or "")
            size_mb = float(metrics.get("size_mb") or 0.0)
            duration_sec = float(entry.get("duration") or 0.0)
            view_count = int(entry.get("view_count") or 0)

            rows.append(
                {
                    "index": index,
                    "position": index + 1,
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
                    "view_count": view_count,
                }
            )

        return rows

    def _build_ui(self) -> None:
        self.info_label = ctk.CTkLabel(
            self,
            text=self._info_label_text(),
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.LABEL,
            anchor="w",
        )
        self.info_label.pack(fill="x", padx=12, pady=(12, 6))

        filters_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE)
        filters_frame.pack(fill="x", padx=12, pady=(0, 8))

        filter_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        filter_row.pack(fill="x", padx=10, pady=(10, 6))

        self.title_filter_entry = ctk.CTkEntry(
            filter_row,
            placeholder_text=t("download.playlistFilterTitlePlaceholder"),
        )
        style_entry(self.title_filter_entry)
        self.title_filter_entry.pack(side="left", fill="x", expand=True)

        self.duration_min_entry = ctk.CTkEntry(
            filter_row,
            width=110,
            placeholder_text=t("download.playlistFilterDurationMinPlaceholder"),
        )
        style_entry(self.duration_min_entry)
        self.duration_min_entry.pack(side="left", padx=(8, 0))

        self.duration_max_entry = ctk.CTkEntry(
            filter_row,
            width=110,
            placeholder_text=t("download.playlistFilterDurationMaxPlaceholder"),
        )
        style_entry(self.duration_max_entry)
        self.duration_max_entry.pack(side="left", padx=(8, 0))

        self.popularity_combo = ctk.CTkComboBox(
            filter_row,
            width=190,
            values=list(self._popularity_options().values()),
        )
        style_combo(self.popularity_combo)
        self.popularity_combo.set(self._popularity_options()["all"])
        self.popularity_combo.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            filter_row,
            text=t("download.playlistFilterApply"),
            command=self._apply_filters,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=32,
            width=110,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            filter_row,
            text=t("download.playlistFilterReset"),
            command=self._reset_filters,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=32,
            width=110,
        ).pack(side="left", padx=(8, 0))

        range_row = ctk.CTkFrame(filters_frame, fg_color="transparent")
        range_row.pack(fill="x", padx=10, pady=(0, 8))

        self.range_start_entry = ctk.CTkEntry(
            range_row,
            width=90,
            placeholder_text=t("download.playlistRangeStartPlaceholder"),
        )
        style_entry(self.range_start_entry)
        self.range_start_entry.pack(side="left")

        self.range_end_entry = ctk.CTkEntry(
            range_row,
            width=90,
            placeholder_text=t("download.playlistRangeEndPlaceholder"),
        )
        style_entry(self.range_end_entry)
        self.range_end_entry.pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            range_row,
            text=t("download.playlistRangeSelect"),
            command=self._apply_range_selection,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=32,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            range_row,
            text=t("download.playlistSelectVisible"),
            command=self._select_visible,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=32,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkButton(
            range_row,
            text=t("download.playlistClearVisible"),
            command=self._clear_visible,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=32,
        ).pack(side="left", padx=(8, 0))

        self.filter_summary_label = ctk.CTkLabel(
            filters_frame,
            text="",
            text_color=Colors.TEXT_MUTED,
            font=Fonts.SMALL,
            anchor="w",
        )
        self.filter_summary_label.pack(fill="x", padx=10, pady=(0, 8))

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
            rowheight=44,  # tall enough to seat a 16:9 cover thumbnail in the #0 column
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
        # "tree headings" keeps the #0 column visible so each row can show a cover thumbnail.
        self.tree = ttk.Treeview(frame, columns=columns, show="tree headings", height=16, style="Ravn.Treeview")
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=76, minwidth=76, anchor=tk.CENTER, stretch=False)
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
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btn_frame,
            text=t("download.playlistSortResetOrder"),
            command=self._reset_order,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=34,
        ).pack(side="left", padx=(8, 0))
        ctk.CTkButton(
            btn_frame,
            text=t("download.downloadButton"),
            command=self._download,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            font=Fonts.LABEL_BOLD,
            height=34,
        ).pack(side="right", padx=(8, 0))
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

    def _sort_rows(self) -> None:
        self._rows.sort(
            key=lambda row: self._sort_value(row, self._sort_key),
            reverse=self._descending,
        )

    def _sort_by(self, sort_key: str) -> None:
        if self._sort_key == sort_key:
            self._descending = not self._descending
        else:
            self._sort_key = sort_key
            self._descending = False

        self._sort_rows()
        self._refresh_tree()

    def _reset_order(self) -> None:
        self._sort_key = "index"
        self._descending = False
        self._sort_rows()
        self._refresh_tree()

    @staticmethod
    def _parse_duration_filter(value: Any) -> Optional[float]:
        text = str(value or "").strip()
        if not text:
            return None

        if ":" in text:
            parts = text.split(":")
            if not all(part.isdigit() for part in parts):
                return None
            values = [int(part) for part in parts]
            if len(values) == 2:
                minutes, seconds = values
                return float(minutes * 60 + seconds)
            if len(values) == 3:
                hours, minutes, seconds = values
                return float(hours * 3600 + minutes * 60 + seconds)
            return None

        try:
            return max(0.0, float(text))
        except ValueError:
            return None

    @staticmethod
    def _parse_range_index(value: Any) -> Optional[int]:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            return max(1, int(text))
        except ValueError:
            return None

    @classmethod
    def _visible_popularity_indexes(cls, rows: List[Dict[str, Any]], popularity_mode: str) -> Optional[set[int]]:
        normalized_mode = cls._normalize_popularity_value(popularity_mode)
        if normalized_mode == "all":
            return None

        available_rows = [row for row in rows if int(row.get("view_count") or 0) > 0]
        if not available_rows:
            return None

        ratio_map = {
            "top25": 0.25,
            "top50": 0.50,
            "top75": 0.75,
        }
        ratio = ratio_map.get(normalized_mode, 1.0)
        top_count = max(1, math.ceil(len(available_rows) * ratio))
        ranked_rows = sorted(
            available_rows,
            key=lambda row: (int(row.get("view_count") or 0), -int(row.get("index") or 0)),
            reverse=True,
        )
        return {int(row["index"]) for row in ranked_rows[:top_count]}

    def _record_perf_metric(self, name: str, *, item_count: int, duration_seconds: float, **extra: Any) -> None:
        metrics = getattr(self, "_perf_metrics", None)
        if metrics is None:
            metrics = {}
            self._perf_metrics = metrics
        metrics[name] = {
            "item_count": int(item_count),
            "duration_ms": round(float(duration_seconds) * 1000.0, 3),
            **extra,
        }

    def _filter_rows(
        self,
        *,
        title_query: str = "",
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        popularity_mode: str = "all",
    ) -> List[Dict[str, Any]]:
        started = perf_counter()
        query = str(title_query or "").strip().casefold()
        if min_duration is not None and max_duration is not None and min_duration > max_duration:
            min_duration, max_duration = max_duration, min_duration

        popularity_indexes = self._visible_popularity_indexes(self._all_rows, popularity_mode)
        filtered_rows: List[Dict[str, Any]] = []

        for row in self._all_rows:
            if query and query not in row["title_sort"]:
                continue

            duration_value = float(row.get("duration") or 0.0)
            if min_duration is not None and duration_value < min_duration:
                continue
            if max_duration is not None and duration_value > max_duration:
                continue
            if popularity_indexes is not None and row["index"] not in popularity_indexes:
                continue

            filtered_rows.append(row)

        self._record_perf_metric(
            "playlist_filter_rows",
            item_count=len(filtered_rows),
            duration_seconds=perf_counter() - started,
            source_count=len(self._all_rows),
            popularity_mode=self._normalize_popularity_value(popularity_mode),
        )
        return filtered_rows

    def update_entry_at_index(self, index: int, entry: Dict[str, Any], quality_label: Optional[str] = None) -> None:
        """Apply a single progressively-resolved entry's detail fields without rebuilding
        the whole table -- used by the yt-dlp library progressive extraction path, which
        resolves one video at a time instead of delivering every entry's details at once."""
        if quality_label is not None:
            self._quality_label = quality_label

        target_row = None
        for row in self._all_rows:
            if int(row.get("index") or -1) == index:
                target_row = row
                break
        if target_row is None:
            return

        metrics = self._metrics_getter(entry, self._quality_label)
        target_row["size_mb"] = float(metrics.get("size_mb") or 0.0)
        target_row["entry"] = entry

        item_id = str(index)
        if self.tree.exists(item_id):
            size_text = self._size_formatter(target_row["size_mb"]) if target_row["size_mb"] > 0 else "-"
            self.tree.set(item_id, "size", size_text)

        self._update_playlist_progress_label()

    def mark_details_complete(self) -> None:
        """Signal that no further per-entry updates will arrive; clears the loading cue."""
        self._details_enriched = True
        if hasattr(self, "info_label"):
            self.info_label.configure(text=self._info_label_text())

    def _update_playlist_progress_label(self) -> None:
        if self._details_enriched or not hasattr(self, "info_label"):
            return
        resolved = sum(1 for row in self._all_rows if row.get("size_mb", 0) > 0)
        total = len(self._all_rows)
        base = t("download.playlistSortQuality", quality=self._quality_label)
        progress = t("download.playlistSortEnrichingProgress", resolved=resolved, total=total)
        self.info_label.configure(text=f"{base} • {progress}")

    def refresh_entries(self, entries: List[Dict[str, Any]], quality_label: Optional[str] = None) -> None:
        """Refresh row metrics after deferred playlist detail enrichment completes."""
        selection_by_index = {
            int(row.get("index") or 0): bool(row.get("selected", True))
            for row in self._all_rows
        }
        self._details_enriched = True
        if quality_label is not None:
            self._quality_label = quality_label
        if hasattr(self, "info_label"):
            self.info_label.configure(text=self._info_label_text())

        refreshed_rows = self._build_rows(entries)
        for row in refreshed_rows:
            row["selected"] = selection_by_index.get(int(row.get("index") or 0), True)
        self._all_rows = refreshed_rows
        self._apply_filters()

    def _apply_filters(self) -> None:
        title_query = self.title_filter_entry.get() if hasattr(self, "title_filter_entry") else ""
        min_duration = self._parse_duration_filter(self.duration_min_entry.get() if hasattr(self, "duration_min_entry") else "")
        max_duration = self._parse_duration_filter(self.duration_max_entry.get() if hasattr(self, "duration_max_entry") else "")
        popularity_mode = self.popularity_combo.get() if hasattr(self, "popularity_combo") else "all"

        self._rows = self._filter_rows(
            title_query=title_query,
            min_duration=min_duration,
            max_duration=max_duration,
            popularity_mode=popularity_mode,
        )
        self._sort_rows()
        self._refresh_tree()

    def _reset_filters(self) -> None:
        for widget_name in ("title_filter_entry", "duration_min_entry", "duration_max_entry", "range_start_entry", "range_end_entry"):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.delete(0, "end")

        if hasattr(self, "popularity_combo"):
            self.popularity_combo.set(self._popularity_options()["all"])

        self._apply_filters()

    def _request_row_thumbnail(self, iid: str, url: str) -> None:
        """Ask the shared loader for this row's cover as a tk PhotoImage (Treeview needs tk, not CTkImage)."""
        if not url:
            return
        from ravn_app.ui.components.thumbnail_loader import get_thumbnail_loader

        image = get_thumbnail_loader().request(
            url,
            (60, 34),
            on_ready=lambda img, _iid=iid: self._apply_row_thumbnail(_iid, img),
            schedule_on_ui=self._schedule_on_ui,
            image_kind="tk",
        )
        if image is not None:
            self._apply_row_thumbnail(iid, image)

    def _schedule_on_ui(self, fn) -> None:
        try:
            self.after(0, fn)
        except Exception:
            pass

    def _apply_row_thumbnail(self, iid: str, image) -> None:
        try:
            if not self.winfo_exists() or not self.tree.exists(iid):
                return
            self._thumb_refs[iid] = image  # keep a reference or Treeview drops it
            self.tree.item(iid, image=image)
        except Exception:
            pass

    def _refresh_tree(self) -> None:
        started = perf_counter()
        for item_id in self.tree.get_children():
            self.tree.delete(item_id)
        self._thumb_refs.clear()

        for row in self._rows:
            size_text = self._size_formatter(row["size_mb"]) if row["size_mb"] > 0 else "-"
            duration_text = self._duration_formatter(row["duration"]) if row["duration"] > 0 else "-"
            album_text = row["album"] or "-"
            channel_text = row["channel"] or "-"
            marker = "☑" if row.get("selected", True) else "☐"
            iid = str(row["index"])
            self.tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    marker,
                    row["title"],
                    size_text,
                    duration_text,
                    album_text,
                    channel_text,
                ),
            )
            self._request_row_thumbnail(iid, (row.get("entry") or {}).get("thumbnail_url", ""))
        self._update_filter_summary()
        self._update_selection_summary()
        self._record_perf_metric(
            "playlist_refresh_tree",
            item_count=len(self._rows),
            duration_seconds=perf_counter() - started,
        )

    @staticmethod
    def _format_bytes(size_bytes: int) -> str:
        value = float(max(0, size_bytes))
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024 or unit == "TB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
            value /= 1024
        return "0 B"

    def _update_filter_summary(self) -> None:
        if not hasattr(self, "filter_summary_label"):
            return
        self.filter_summary_label.configure(
            text=t("download.playlistFilterVisibleSummary", visible=len(self._rows), total=len(self._all_rows))
        )

    def _update_selection_summary(self) -> None:
        selected_rows = [row for row in self._all_rows if row.get("selected", True)]
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
        for row in self._all_rows:
            if row["index"] == row_index:
                row["selected"] = not row.get("selected", True)
                break

        self._refresh_tree()

    def _select_all(self) -> None:
        for row in self._all_rows:
            row["selected"] = True
        self._refresh_tree()

    def _clear_selection(self) -> None:
        for row in self._all_rows:
            row["selected"] = False
        self._refresh_tree()

    def _toggle_all(self) -> None:
        all_selected = all(row.get("selected", True) for row in self._all_rows)
        for row in self._all_rows:
            row["selected"] = not all_selected
        self._refresh_tree()

    def _select_visible(self) -> None:
        for row in self._rows:
            row["selected"] = True
        self._refresh_tree()

    def _clear_visible(self) -> None:
        for row in self._rows:
            row["selected"] = False
        self._refresh_tree()

    def _apply_range_selection(self) -> None:
        total_rows = len(self._all_rows)
        if total_rows == 0:
            return

        start_value = self._parse_range_index(self.range_start_entry.get() if hasattr(self, "range_start_entry") else "")
        end_value = self._parse_range_index(self.range_end_entry.get() if hasattr(self, "range_end_entry") else "")
        start_value = start_value or 1
        end_value = end_value or total_rows
        start_value, end_value = sorted((min(start_value, total_rows), min(end_value, total_rows)))

        for row in self._all_rows:
            row["selected"] = start_value <= int(row.get("position") or 0) <= end_value

        self._refresh_tree()

    def _download(self) -> None:
        selected_entries = [row["entry"] for row in self._all_rows if row.get("selected", True)]
        if not selected_entries:
            return
        self._on_download(selected_entries)
        self.destroy()
