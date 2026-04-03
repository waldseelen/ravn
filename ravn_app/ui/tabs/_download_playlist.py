"""Playlist-related behavior for the download tab."""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Dict, List

import customtkinter as ctk

from ravn_app.core.downloader import DownloadFormat, DownloadQuality
from ravn_app.core.i18n import t
from ravn_app.ui.components.playlist_item import PlaylistItemRow
from ravn_app.ui.components.playlist_sort_dialog import PlaylistSortDialog
from ravn_app.ui.design_tokens import Colors, Icons


class PlaylistMixin:
    def _get_playlist_entry_quality_metrics(self, entry: Dict[str, Any], quality_label: str) -> Dict[str, Any]:
        size_by_quality = entry.get("size_by_quality_mb") or {}
        resolution_by_quality = entry.get("resolution_by_quality") or {}
        format_note_by_quality = entry.get("format_note_by_quality") or {}

        size_mb = size_by_quality.get(quality_label)
        resolution = resolution_by_quality.get(quality_label)
        format_note = format_note_by_quality.get(quality_label)

        best_aliases = (
            t("download.qualityBest"),
            "Best",
            "En Iyi",
            "En İyi",
        )

        if size_mb is None:
            for alias in best_aliases:
                if alias in size_by_quality:
                    size_mb = size_by_quality.get(alias)
                    break
            if size_mb is None:
                size_mb = entry.get("filesize_mb", 0) or 0

        if resolution is None:
            for alias in best_aliases:
                if alias in resolution_by_quality:
                    resolution = resolution_by_quality.get(alias)
                    break
            if resolution is None:
                resolution = entry.get("resolution", t("common.unknown")) or t("common.unknown")

        if format_note is None:
            for alias in best_aliases:
                if alias in format_note_by_quality:
                    format_note = format_note_by_quality.get(alias)
                    break
            if format_note is None:
                format_note = entry.get("format_note", "") or ""

        return {
            "size_mb": float(size_mb or 0),
            "resolution": str(resolution),
            "format_note": str(format_note),
        }

    def _build_playlist_detail_text(self, entry: Dict[str, Any], quality_label: str) -> str:
        duration = self._format_duration(entry.get("duration"))
        metrics = self._get_playlist_entry_quality_metrics(entry, quality_label)
        size_mb = metrics["size_mb"]
        resolution = metrics["resolution"]
        format_note = metrics["format_note"]

        parts: List[str] = []
        if duration:
            parts.append(f"{Icons.HISTORY} {duration}")
        if resolution and resolution != t("common.unknown"):
            parts.append(f"{Icons.QUALITY_SELECT} {resolution}")
        if size_mb > 0:
            parts.append(f"{Icons.INFO} {self._format_size_from_mb(size_mb)}")
        if format_note:
            parts.append(f"{Icons.FORMAT_SELECT} {format_note}")
        return " • ".join(parts)

    def _clear_playlist_selection(self):
        self.playlist_entries = []
        self.playlist_selection_vars = []
        self.playlist_detail_rows = []
        self.playlist_source_url = ""
        self.is_playlist_fetching = False
        self.is_info_fetching = False
        self._last_video_info = None
        self._update_size_estimate()

        for child in self.playlist_list_frame.winfo_children():
            child.destroy()

        self.playlist_frame.pack_forget()
        restore_text = getattr(self, "_active_btn_restore_text", f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
        self.download_btn.configure(text=restore_text, state="normal")

    def _update_playlist_summary(self):
        if not self.playlist_entries or not self.playlist_selection_vars:
            return

        selected_count = sum(1 for var in self.playlist_selection_vars if var.get())
        total_count = len(self.playlist_entries)
        quality_label = self._get_selected_quality_label()

        total_size_mb = 0.0
        for index, variable in enumerate(self.playlist_selection_vars):
            if variable.get() and index < len(self.playlist_entries):
                metrics = self._get_playlist_entry_quality_metrics(
                    self.playlist_entries[index],
                    quality_label,
                )
                total_size_mb += metrics["size_mb"]

        summary = f"{Icons.QUEUED_STATUS} {t('download.playlistSelectedSummary', selected=selected_count, total=total_count)}"
        if total_size_mb > 0:
            summary += f" • {Icons.INFO} ~{self._format_size_from_mb(total_size_mb)} ({quality_label})"

        self.playlist_summary_label.configure(text=summary)

    def _select_all_playlist_items(self):
        for variable in self.playlist_selection_vars:
            variable.set(True)
        self._update_playlist_summary()

    def _clear_all_playlist_items(self):
        for variable in self.playlist_selection_vars:
            variable.set(False)
        self._update_playlist_summary()

    def _get_selected_playlist_entries(self) -> List[Dict[str, Any]]:
        selected: List[Dict[str, Any]] = []
        for entry, variable in zip(self.playlist_entries, self.playlist_selection_vars):
            if variable.get():
                selected.append(entry)
        return selected

    def _start_playlist_fetch(self, url: str):
        if self.is_playlist_fetching or self.is_info_fetching:
            return

        # Playlists always use the video side (format menus, quality menus, etc.)
        if hasattr(self, "_activate_video_side"):
            self._activate_video_side()

        self.is_playlist_fetching = True
        self.error_panel.hide_error()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        selected_quality = self._get_selected_quality_label()
        self._start_processing_feedback(t("download.playlistInfoLoading", quality=selected_quality))
        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.fetchData')}...")
            self._set_button_loading_state(fetch_data_btn, is_loading=True)
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.playlistInfoLoading', quality=selected_quality)}")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        def run_playlist_fetch():
            entries = self.downloader.extract_playlist_entries(url, quality_label=selected_quality)
            self.after(0, self._on_playlist_fetch_complete, url, entries)

        threading.Thread(target=run_playlist_fetch, daemon=True).start()

    def _on_playlist_fetch_complete(self, url: str, entries: List[Dict[str, Any]]):
        self.is_playlist_fetching = False
        self._stop_processing_feedback()
        self._hide_progress()
        fetch_data_btn = self.__dict__.get("fetch_data_btn")
        if fetch_data_btn is not None:
            self._set_button_loading_state(fetch_data_btn, is_loading=False)

        if not entries:
            self._set_button_loading_state(self.download_btn, is_loading=False)
            self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
            self.download_status_label.configure(text="")
            if fetch_data_btn is not None:
                fetch_data_btn.configure(text=f"{Icons.SEARCH} {t('download.fetchPlaylistData')}")
            self._show_download_error(
                t("download.playlistInfoFailed"),
                "Playlist entries not found",
            )
            return

        self.playlist_entries = entries
        self.playlist_source_url = url
        self.playlist_selection_vars = [ctk.BooleanVar(value=True) for _ in entries]
        self.playlist_detail_rows = []
        quality_label = self._get_selected_quality_label()

        self._set_button_loading_state(self.download_btn, is_loading=False)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
        self.download_status_label.configure(text=t("download.playlistSelectionPrompt"))
        self._set_url_validation_state(Icons.SUCCESS_INDICATOR, Colors.SUCCESS)
        if fetch_data_btn is not None:
            fetch_data_btn.configure(text=f"{Icons.REFRESH} {t('download.refreshPlaylistData')}")

        if getattr(self, "_playlist_sort_dialog_enabled", False):
            self.playlist_frame.pack_forget()
            self._open_playlist_sort_dialog(entries, quality_label)
            return

        self._render_inline_playlist_entries(entries, quality_label)

    def _render_inline_playlist_entries(self, entries: List[Dict[str, Any]], quality_label: str):
        from ravn_app.ui.tabs import download_tab as download_tab_module

        playlist_item_cls = getattr(download_tab_module, "PlaylistItemRow", PlaylistItemRow)

        for child in self.playlist_list_frame.winfo_children():
            child.destroy()

        for index, entry in enumerate(entries, start=1):
            variable = self.playlist_selection_vars[index - 1]
            item_widget = playlist_item_cls(
                self.playlist_list_frame,
                index=index,
                entry=entry,
                variable=variable,
                detail_text=self._build_playlist_detail_text(entry, quality_label),
                on_toggle=self._update_playlist_summary,
            )
            item_widget.pack(fill="x", padx=2, pady=1)
            self.playlist_detail_rows.append((item_widget, entry))

        self._update_playlist_summary()
        columns_frame = getattr(self, "_columns_frame", None)
        pack_kwargs = {"fill": "x", "padx": 15, "pady": (0, 10)}
        if columns_frame is not None:
            pack_kwargs["before"] = columns_frame
        self.playlist_frame.pack(**pack_kwargs)
        self.download_btn.configure(text=f"{Icons.DOWNLOAD_BTN} {t('download.downloadSelected')}")

    def _open_playlist_sort_dialog(self, entries: List[Dict[str, Any]], quality_label: str):
        def on_download(selected_entries: List[Dict[str, Any]]):
            if not selected_entries:
                self._show_download_error(t("download.playlistSelectAtLeastOne"), "")
                return
            self._start_playlist_download_from_popup(selected_entries)

        PlaylistSortDialog(
            self,
            entries=entries,
            quality_label=quality_label,
            metrics_getter=self._get_playlist_entry_quality_metrics,
            duration_formatter=self._format_duration,
            size_formatter=self._format_size_from_mb,
            on_download=on_download,
        )

    def _start_playlist_download_from_popup(self, selected_entries: List[Dict[str, Any]]):
        if hasattr(self, "queue_paused_getter") and callable(self.queue_paused_getter):
            if self.queue_paused_getter():
                self._show_download_error(t("download.queuePaused"), "")
                return

        from ravn_app.ui.tabs import download_tab as download_tab_module

        if hasattr(self, "_resolve_effective_download_selection"):
            format_type, quality, _audio_bitrate = self._resolve_effective_download_selection(prefer_music=False)
        else:
            quality_map = getattr(download_tab_module, "_QUALITY_MAP", {})
            format_map = getattr(download_tab_module, "_FORMAT_MAP", {})
            quality = quality_map.get(self.quality_menu.get(), DownloadQuality.BEST)
            format_type = format_map.get(self.format_menu.get(), DownloadFormat.MP4)

        if hasattr(self, "_resolve_download_output_dir"):
            output_dir = self._resolve_download_output_dir()
        else:
            default_path = self.config_manager.get(
                "default_download_path",
                str(Path.home() / "Downloads" / "RAVN"),
            )
            output_dir = str(Path(default_path))

        self._start_playlist_download(selected_entries, output_dir, format_type, quality)

    def _start_playlist_download(
        self,
        selected_entries: List[Dict[str, Any]],
        output_dir: str,
        format_type: DownloadFormat,
        quality: DownloadQuality,
    ):
        total = len(selected_entries)
        self.error_panel.hide_error()
        self.download_progress.set(0)
        self._download_progress_value = 0.0
        self.download_progress.pack(padx=15, pady=(5, 0), fill="x")
        self._start_processing_feedback(t("download.downloadLoading"))
        self.download_btn.configure(text=f"{Icons.RUNNING_STATUS} {t('download.downloadLoading')}...")
        self._set_button_loading_state(self.download_btn, is_loading=True)

        download_settings = self._get_download_behavior_settings()

        def run_playlist_download():
            all_files: List[str] = []
            for index, entry in enumerate(selected_entries, start=1):
                entry_url = entry.get("url", "")
                entry_title = entry.get("title", t("download.itemLabel", index=index))
                if not entry_url:
                    continue

                def item_progress(percent: int, message: str, current=index, title=entry_title):
                    overall = int(((current - 1) + max(0, min(100, percent)) / 100.0) / total * 100)
                    prefix = f"{current}/{total} • {title}"
                    if message:
                        self._on_download_progress(overall, f"{prefix} • {message}")
                    else:
                        self._on_download_progress(overall, prefix)

                result = self.downloader.download(
                    url=entry_url,
                    output_dir=output_dir,
                    format_type=format_type,
                    quality=quality,
                    progress_callback=item_progress,
                    **download_settings,
                )

                if not result.success:
                    self.after(
                        0,
                        self._on_download_failure,
                        t("download.playlistDownloadFailed", index=index, total=total, message=result.error_message),
                    )
                    return

                all_files.extend(result.output_files or [])

            class _PlaylistResult:
                def __init__(self, files: List[str]):
                    self.output_files = files

            self.after(0, self._on_download_success, _PlaylistResult(all_files))

        threading.Thread(target=run_playlist_download, daemon=True).start()
