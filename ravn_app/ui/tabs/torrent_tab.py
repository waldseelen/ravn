"""Torrent / Magnet download tab."""

from __future__ import annotations

import os
import platform
import subprocess
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from time import perf_counter
from tkinter import filedialog, ttk
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.core.runners.aria2 import TorrentProgressSnapshot
from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing

try:
    from tkinterdnd2 import DND_FILES
    _HAS_DND = True
except ImportError:
    _HAS_DND = False


class TorrentTab(ctk.CTkFrame):
    """Dedicated tab for torrent / magnet link downloads via aria2c."""

    def __init__(
        self,
        parent,
        config_manager: Any,
        toast_manager_getter: Callable[[], Any],
        use_embedded_workspace_source_bar: bool = False,
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.config_manager = config_manager
        self.toast_manager_getter = toast_manager_getter
        self._embedded_workspace_source_bar = bool(use_embedded_workspace_source_bar)

        aria2c_path = self.config_manager.get("aria2c_path", "aria2c")
        self._downloader = TorrentDownloader(aria2c_path)
        self._download_thread: Optional[threading.Thread] = None
        self._stream_url: Optional[str] = None
        self._row_counter = 0
        self._active_download_id: Optional[str] = None
        self._selected_download_id: Optional[str] = None
        self._download_rows: Dict[str, Dict[str, Any]] = {}
        self._file_rows: Dict[str, Dict[str, Any]] = {}
        self._session_order: list[str] = []
        self._download_queue = __import__("collections").deque()
        self._active_filter_key = "all"
        self._perf_metrics: Dict[str, Dict[str, Any]] = {}

        self._setup_ui()
        self._check_aria2c()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        # ── Header ────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
        self._header_frame = header
        if not self._embedded_workspace_source_bar:
            header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

        ctk.CTkLabel(
            header,
            text=f"{Icons.TORRENT} {t('torrent.title')}",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        # ── aria2c warning banner (hidden by default) ──────────────────
        self._aria2c_banner = ctk.CTkFrame(
            self,
            fg_color=Colors.WARNING_BG,
            border_width=1,
            border_color=Colors.WARNING,
            corner_radius=Sizes.CORNER_MD,
        )

        banner_inner = ctk.CTkFrame(self._aria2c_banner, fg_color="transparent")
        banner_inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)

        ctk.CTkLabel(
            banner_inner,
            text=f"{Icons.WARNING}  {t('torrent.aria2cMissing')}",
            font=Fonts.LABEL_BOLD,
            text_color=Colors.WARNING,
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            banner_inner,
            text=t("torrent.aria2cMissingDetail"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
            wraplength=700,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        # ── Source input ───────────────────────────────────────────────
        source_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        self._source_frame = source_frame
        if not self._embedded_workspace_source_bar:
            source_frame.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS)

        ctk.CTkLabel(
            source_frame,
            text=t("torrent.sourceLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.SM, pady=(Spacing.SM, Spacing.XS))

        source_input_row = ctk.CTkFrame(source_frame, fg_color="transparent")
        source_input_row.pack(fill="x", padx=Spacing.SM, pady=(0, Spacing.SM))

        self._source_entry = ctk.CTkEntry(
            source_input_row,
            placeholder_text=t("torrent.sourcePlaceholder"),
            font=Fonts.LABEL,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text_color=Colors.TEXT_MUTED,
            border_color=Colors.BORDER,
        )
        self._source_entry.configure(cursor=Cursors.TEXT)
        self._source_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        ctk.CTkButton(
            source_input_row,
            text=f"{Icons.BROWSE} {t('torrent.browseFile')}",
            command=self._browse_torrent_file,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        # drag-drop onto the entry
        if _HAS_DND:
            try:
                self._source_entry.drop_target_register(DND_FILES)
                self._source_entry.dnd_bind("<<Drop>>", self._on_file_drop)
            except Exception:
                pass

        ctk.CTkLabel(
            source_frame,
            text=t("torrent.dropHint"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", padx=Spacing.SM, pady=(0, Spacing.XS))

        # ── Mode + output row ──────────────────────────────────────────
        options_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        options_frame.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS)

        options_inner = ctk.CTkFrame(options_frame, fg_color="transparent")
        options_inner.pack(fill="x", padx=Spacing.SM, pady=Spacing.SM)

        mode_col = ctk.CTkFrame(options_inner, fg_color="transparent")
        mode_col.pack(side="left", fill="x", expand=True, padx=(0, Spacing.MD))

        ctk.CTkLabel(
            mode_col,
            text=t("torrent.modeLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        self._mode_selector = ctk.CTkSegmentedButton(
            mode_col,
            values=[
                t("torrent.modeFull"),
                t("torrent.modeSequential"),
                t("torrent.modeStream"),
            ],
            font=Fonts.LABEL,
            fg_color=Colors.BG_CARD,
            selected_color=Colors.ACCENT,
            selected_hover_color=Colors.ACCENT_HOVER,
            unselected_color=Colors.BG_INPUT,
            unselected_hover_color=Colors.BG_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            text_color_disabled=Colors.TEXT_MUTED,
        )
        self._mode_selector.set(t("torrent.modeFull"))
        self._mode_selector.pack(anchor="w", pady=(Spacing.XS, 0))

        output_col = ctk.CTkFrame(options_inner, fg_color="transparent")
        output_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            output_col,
            text=t("torrent.outputDirLabel"),
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        output_input_row = ctk.CTkFrame(output_col, fg_color="transparent")
        output_input_row.pack(fill="x", pady=(Spacing.XS, 0))

        self._output_entry = ctk.CTkEntry(
            output_input_row,
            font=Fonts.SMALL,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_PRIMARY,
            border_color=Colors.BORDER,
        )
        self._output_entry.configure(cursor=Cursors.TEXT)
        default_dir = self.config_manager.get("default_download_path") or str(Path.home() / "Downloads")
        self._output_entry.insert(0, default_dir)
        self._output_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        ctk.CTkButton(
            output_input_row,
            text=Icons.BROWSE,
            width=36,
            command=self._browse_output_dir,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        # ── Action buttons ─────────────────────────────────────────────
        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS)

        self._download_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.DOWNLOAD_BTN} {t('torrent.downloadBtn')}",
            command=self._start_download,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self._download_btn.configure(width=160)
        self._download_btn.pack(side="right", padx=(Spacing.XS, 0))

        self._cancel_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.STOP} {t('torrent.cancelBtn')}",
            command=self._cancel_download,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BTN_DISABLED,
            hover_color=Colors.BTN_DISABLED,
            state="disabled",
            text_color=Colors.TEXT_MUTED,
            cursor=Cursors.POINTER,
        )
        self._cancel_btn.configure(width=160)
        self._cancel_btn.pack(side="right", padx=(Spacing.XS, 0))

        self._open_player_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.PLAY} {t('torrent.openPlayerBtn')}",
            command=self._open_stream_in_player,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.BTN_DISABLED,
            hover_color=Colors.BTN_DISABLED,
            state="disabled",
            text_color=Colors.TEXT_MUTED,
            cursor=Cursors.POINTER,
        )
        self._open_player_btn.configure(width=160)
        self._open_player_btn.pack(side="right")

        # ── Torrent table ──────────────────────────────────────────────
        table_wrap = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        table_wrap.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS)

        ctk.CTkLabel(
            table_wrap,
            text=t("torrent.tableTitle"),
            font=Fonts.LABEL_BOLD,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.SM, pady=(Spacing.SM, Spacing.XS))

        table_frame = ctk.CTkFrame(table_wrap, fg_color="transparent")
        table_frame.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))
        self._build_download_table(table_frame)

        # ── Progress ───────────────────────────────────────────────────
        progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        progress_frame.pack(fill="x", padx=Spacing.MD, pady=(Spacing.XS, 0))

        self._progress_bar = ctk.CTkProgressBar(progress_frame)
        self._progress_bar.configure(
            progress_color=Colors.ACCENT,
            fg_color=Colors.PROGRESS_BG,
        )
        self._progress_bar.set(0)
        self._progress_bar.pack(fill="x")

        self._status_label = ctk.CTkLabel(
            progress_frame,
            text="",
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self._status_label.pack(anchor="w", pady=(Spacing.XS, 0))

        # ── Log ────────────────────────────────────────────────────────
        log_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        log_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.SM)

        ctk.CTkLabel(
            log_frame,
            text=t("torrent.logTitle"),
            font=Fonts.LABEL_BOLD,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w", padx=Spacing.SM, pady=(Spacing.SM, Spacing.XS))

        self._log_text = ctk.CTkTextbox(
            log_frame,
            font=Fonts.MONO,
            fg_color=Colors.BG_INPUT,
            text_color=Colors.TEXT_SECONDARY,
            state="disabled",
        )
        self._log_text.pack(fill="both", expand=True, padx=Spacing.SM, pady=(0, Spacing.SM))

    def _build_download_table(self, parent) -> None:
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
        hover_bg = self._resolve_color(Colors.BG_HOVER)
        border_color = self._resolve_color(Colors.BORDER)

        style.configure(
            "Torrent.Treeview",
            background=body_bg,
            fieldbackground=body_bg,
            foreground=body_fg,
            bordercolor=border_color,
            borderwidth=0,
            rowheight=28,
            relief="flat",
        )
        style.configure(
            "Torrent.Treeview.Heading",
            background=header_bg,
            foreground=header_fg,
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Torrent.Treeview",
            background=[("selected", selected_bg), ("hover", hover_bg)],
            foreground=[("selected", body_fg)],
        )
        style.map(
            "Torrent.Treeview.Heading",
            background=[("active", selected_bg)],
            foreground=[("active", header_fg)],
        )

        columns = (
            "name",
            "mode",
            "status",
            "progress",
            "downloaded",
            "remaining",
            "speed",
            "eta",
        )
        self._downloads_tree = ttk.Treeview(
            parent,
            columns=columns,
            show="headings",
            height=6,
            style="Torrent.Treeview",
        )
        self._downloads_tree.heading("name", text=t("torrent.columnName"))
        self._downloads_tree.heading("mode", text=t("torrent.columnMode"))
        self._downloads_tree.heading("status", text=t("torrent.columnStatus"))
        self._downloads_tree.heading("progress", text=t("torrent.columnProgress"))
        self._downloads_tree.heading("downloaded", text=t("torrent.columnDownloaded"))
        self._downloads_tree.heading("remaining", text=t("torrent.columnRemaining"))
        self._downloads_tree.heading("speed", text=t("torrent.columnSpeed"))
        self._downloads_tree.heading("eta", text=t("torrent.columnEta"))

        self._downloads_tree.column("name", width=240, anchor=tk.W)
        self._downloads_tree.column("mode", width=120, anchor=tk.CENTER)
        self._downloads_tree.column("status", width=150, anchor=tk.W)
        self._downloads_tree.column("progress", width=90, anchor=tk.CENTER)
        self._downloads_tree.column("downloaded", width=120, anchor=tk.E)
        self._downloads_tree.column("remaining", width=120, anchor=tk.E)
        self._downloads_tree.column("speed", width=110, anchor=tk.E)
        self._downloads_tree.column("eta", width=90, anchor=tk.CENTER)

        yscroll = ttk.Scrollbar(parent, orient="vertical", command=self._downloads_tree.yview)
        self._downloads_tree.configure(yscrollcommand=yscroll.set)

        self._downloads_tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        self._downloads_tree.bind("<<TreeviewSelect>>", self._on_row_selection_changed)
        self._downloads_tree.bind("<Double-1>", self._on_row_double_click)

    # ------------------------------------------------------------------
    # aria2c availability check
    # ------------------------------------------------------------------

    def _check_aria2c(self):
        available = self._downloader.is_available()
        if not available:
            self._aria2c_banner.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS)
            self._download_btn.configure(state="disabled")
        else:
            self._aria2c_banner.pack_forget()
            self._download_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _browse_torrent_file(self):
        path = filedialog.askopenfilename(
            title=t("torrent.browseFile"),
            filetypes=[("Torrent files", "*.torrent"), ("All files", "*.*")],
        )
        if path:
            self._source_entry.delete(0, "end")
            self._source_entry.insert(0, path)

    def _browse_output_dir(self):
        path = filedialog.askdirectory(title=t("torrent.outputDirLabel"))
        if path:
            self._output_entry.delete(0, "end")
            self._output_entry.insert(0, path)

    def _on_file_drop(self, event):
        raw = event.data.strip()
        path = raw.strip("{}").strip("'\"")
        if not path.lower().endswith(".torrent"):
            tm = self.toast_manager_getter()
            if tm:
                tm.show_warning(t("download.torrentFileOnly"))
            return
        self._source_entry.delete(0, "end")
        self._source_entry.insert(0, path)

    def _on_row_selection_changed(self, _event=None):
        selected = self._get_selected_session_id()
        self._selected_download_id = selected
        self._sync_player_button_state()

    def _on_row_double_click(self, _event=None):
        self._open_stream_in_player()

    def set_source_text(self, value: str) -> None:
        """Mirror workspace source text into the torrent source entry."""
        self._source_entry.delete(0, "end")
        if value:
            first_line = next((line.strip() for line in str(value).splitlines() if line.strip()), str(value).strip())
            if first_line:
                self._source_entry.insert(0, first_line)

    def get_source_text(self) -> str:
        return str(self._source_entry.get() or "")

    def focus_source_input(self) -> None:
        self._source_entry.focus_set()

    def _on_ctrl_enter(self, event=None):
        if not self.winfo_viewable():
            return
        self._start_download()

    def _on_ctrl_l(self, event=None):
        if not self.winfo_viewable():
            return
        self._source_entry.delete(0, "end")
        return "break"

    def _on_escape(self, event=None):
        if not self.winfo_viewable():
            return
        if self._active_download_id is not None:
            self._cancel_download()
            return "break"

    # ------------------------------------------------------------------
    # Download logic
    # ------------------------------------------------------------------

    def _start_download(self):
        source = self._source_entry.get().strip()
        if not source:
            self._set_status(t("torrent.noSource"), Colors.WARNING)
            return

        output_dir = self._output_entry.get().strip() or str(Path.home() / "Downloads")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        mode = self._resolve_mode()
        seed_time = int(self.config_manager.get("torrent_seed_time", 0))
        mode_label = self._mode_label(mode)
        download_id = self._create_download_row(source, mode_label)

        self._active_download_id = download_id
        self._selected_download_id = download_id
        self._stream_url = None
        self._downloads_tree.selection_set(download_id)
        self._downloads_tree.focus(download_id)

        self._set_downloading_state(True)
        self._progress_bar.set(0)
        self._sync_player_button_state()
        self._log_append(f"[↓] {source}\n[⌂] {output_dir}\n")

        self._download_thread = threading.Thread(
            target=self._run_download,
            args=(download_id, source, output_dir, mode, seed_time),
            daemon=True,
        )
        self._download_thread.start()

    def _run_download(
        self,
        download_id: str,
        source: str,
        output_dir: str,
        mode: TorrentDownloadMode,
        seed_time: int,
    ):
        try:
            def progress_cb(progress: TorrentProgressSnapshot):
                self.after(0, self._on_progress, download_id, progress)

            result = self._downloader.download(
                source=source,
                output_dir=output_dir,
                mode=mode,
                progress_callback=progress_cb,
                seed_time=seed_time,
            )
            self.after(0, self._on_download_done, download_id, result)
        except Exception as exc:
            self.after(0, self._on_download_error, download_id, str(exc))

    def _cancel_download(self):
        download_id = self._active_download_id
        cancelled = self._downloader.cancel()
        self._set_downloading_state(False)

        if download_id and download_id in self._download_rows:
            self._download_rows[download_id]["cancel_requested"] = True
            self._update_download_row(download_id, status=t("torrent.cancelled"))

        self._set_status(t("torrent.cancelled"), Colors.WARNING)
        self._log_append(f"[{Icons.ERROR_STATUS}] {t('torrent.cancelled')}\n")
        self._sync_player_button_state()

        tm = self.toast_manager_getter()
        if tm and cancelled:
            tm.show_warning(t("torrent.cancelled"))

    # ------------------------------------------------------------------
    # Callbacks (main-thread only)
    # ------------------------------------------------------------------

    def _on_progress(self, download_id: str, progress: TorrentProgressSnapshot):
        if download_id not in self._download_rows:
            return

        row = self._download_rows[download_id]
        name = progress.name or row.get("name") or self._downloader.infer_display_name(row.get("source", ""))
        downloaded_text = progress.downloaded_text or row.get("downloaded", "0 B")
        remaining_text = progress.remaining_text or row.get("remaining", "—")
        speed_text = progress.speed_text or row.get("speed", "—")
        eta_text = progress.eta_text or row.get("eta", "—")

        self._update_download_row(
            download_id,
            name=name,
            status=t("torrent.downloading"),
            progress=f"{max(0, min(progress.percent, 100))}%",
            downloaded=downloaded_text,
            remaining=remaining_text,
            speed=speed_text,
            eta=eta_text,
        )

        if download_id == self._active_download_id:
            self._progress_bar.set(max(0, min(progress.percent, 100)) / 100.0)
            self._set_status(self._format_progress_status(progress), Colors.STATUS_RUNNING)

    def _on_download_done(self, download_id: str, result):
        if download_id not in self._download_rows:
            return

        if download_id == self._active_download_id:
            self._active_download_id = None
            self._set_downloading_state(False)

        row = self._download_rows[download_id]
        row["cancel_requested"] = False

        if result.success:
            row["output_files"] = list(result.output_files)
            row["stream_url"] = result.stream_url
            row["primary_file"] = result.primary_file
            row["play_target"] = self._resolve_play_target(row)
            self._stream_url = result.stream_url

            self._update_download_row(
                download_id,
                name=result.display_name or row.get("name"),
                status=t("torrent.streamReady") if result.stream_url else t("torrent.completed"),
                progress="100%",
                eta="0s" if row.get("eta") not in ("", "—") else row.get("eta", "—"),
            )

            if download_id == self._selected_download_id or self._selected_download_id is None:
                self._progress_bar.set(1.0)
                self._set_status(
                    t("torrent.streamReady") if result.stream_url else t("torrent.completed"),
                    Colors.SUCCESS,
                )

            self._log_append(f"[{Icons.SUCCESS_STATUS}] {t('torrent.completed')}\n")
            self._log_append(t("torrent.outputFiles", count=len(result.output_files)) + "\n")
            for file_path in result.output_files:
                self._log_append(f"    {file_path}\n")
            if result.stream_url:
                self._log_append(f"[{Icons.PLAY}] {result.stream_url}\n")

            tm = self.toast_manager_getter()
            if tm:
                tm.show_success(t("torrent.completed"))
        else:
            status_text = t("torrent.cancelled") if result.cancelled else t("torrent.failed", error=result.error_message)
            self._update_download_row(download_id, status=status_text)

            if download_id == self._selected_download_id or self._selected_download_id is None:
                self._progress_bar.set(0)
                self._set_status(status_text, Colors.WARNING if result.cancelled else Colors.ERROR)

            self._log_append(f"[{Icons.ERROR_STATUS}] {status_text}\n")
            tm = self.toast_manager_getter()
            if tm:
                if result.cancelled:
                    tm.show_warning(t("torrent.cancelled"))
                else:
                    tm.show_error(status_text)

        self._sync_player_button_state()

    def _on_download_error(self, download_id: str, error_message: str):
        if download_id in self._download_rows:
            self._update_download_row(download_id, status=t("torrent.failed", error=error_message))
        self._active_download_id = None
        self._set_downloading_state(False)
        self._progress_bar.set(0)
        msg = t("torrent.failed", error=error_message)
        self._set_status(msg, Colors.ERROR)
        self._log_append(f"[{Icons.ERROR_STATUS}] {msg}\n")
        self._sync_player_button_state()

        tm = self.toast_manager_getter()
        if tm:
            tm.show_error(msg)

    # ------------------------------------------------------------------
    # Stream player
    # ------------------------------------------------------------------

    def _open_stream_in_player(self):
        download_id = self._selected_download_id or self._find_latest_playable_download_id()
        if not download_id or download_id not in self._download_rows:
            self._handle_player_open_failure(t("torrent.playerNoMedia"))
            return

        row = self._download_rows[download_id]
        target = self._selected_open_target() or self._resolve_play_target(row)
        if not target:
            self._handle_player_open_failure(t("torrent.playerNoMedia"))
            return

        opened, error_message = self._open_target(target)
        if not opened:
            fallback_target = row.get("stream_url") if target != row.get("stream_url") else row.get("primary_file")
            if fallback_target:
                opened, error_message = self._open_target(fallback_target)

        if not opened:
            self._handle_player_open_failure(
                t("torrent.playerOpenFailed", error=error_message or target)
            )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_color(token: str | tuple[str, str]) -> str:
        if not isinstance(token, tuple):
            return token
        return token[0] if ctk.get_appearance_mode().lower() == "light" else token[1]

    def _resolve_mode(self) -> TorrentDownloadMode:
        label = self._mode_selector.get()
        if label == t("torrent.modeSequential"):
            return TorrentDownloadMode.SEQUENTIAL
        if label == t("torrent.modeStream"):
            return TorrentDownloadMode.STREAM
        return TorrentDownloadMode.FULL

    def _mode_label(self, mode: TorrentDownloadMode) -> str:
        if mode == TorrentDownloadMode.SEQUENTIAL:
            return t("torrent.modeSequential")
        if mode == TorrentDownloadMode.STREAM:
            return t("torrent.modeStream")
        return t("torrent.modeFull")

    def _set_downloading_state(self, is_downloading: bool):
        if is_downloading:
            self._download_btn.configure(
                state="disabled",
                fg_color=Colors.BTN_DISABLED,
                hover_color=Colors.BTN_DISABLED,
                text_color=Colors.TEXT_MUTED,
            )
            self._cancel_btn.configure(
                state="normal",
                fg_color=Colors.DANGER,
                hover_color=Colors.DANGER_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )
            self._set_status(t("torrent.downloading"), Colors.STATUS_RUNNING)
        else:
            self._download_btn.configure(
                state="normal",
                fg_color=Colors.ACCENT,
                hover_color=Colors.ACCENT_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )
            self._cancel_btn.configure(
                state="disabled",
                fg_color=Colors.BTN_DISABLED,
                hover_color=Colors.BTN_DISABLED,
                text_color=Colors.TEXT_MUTED,
            )

    def _set_status(self, text: str, color: str = Colors.TEXT_MUTED):
        self._status_label.configure(text=text, text_color=color)

    def _log_append(self, text: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _create_download_row(self, source: str, mode_label: str) -> str:
        self._row_counter += 1
        download_id = f"torrent-{self._row_counter}"
        display_name = self._downloader.infer_display_name(source)
        row = {
            "name": display_name,
            "mode": mode_label,
            "status": t("torrent.statusPending"),
            "progress": "0%",
            "downloaded": "0 B",
            "remaining": "—",
            "speed": "—",
            "eta": "—",
            "source": source,
            "stream_url": None,
            "primary_file": None,
            "play_target": None,
            "output_files": [],
            "cancel_requested": False,
        }
        self._download_rows[download_id] = row
        self._session_order.append(download_id)
        self._downloads_tree.insert("", "end", iid=download_id, values=self._build_row_values(row))
        return download_id

    def _update_download_row(self, download_id: str, **updates) -> None:
        row = self._download_rows.get(download_id)
        if row is None:
            return
        row.update(updates)
        self._downloads_tree.item(download_id, values=self._build_row_values(row))

    @staticmethod
    def _build_row_values(row: Dict[str, Any]) -> tuple[str, ...]:
        return (
            str(row.get("name") or "—"),
            str(row.get("mode") or "—"),
            str(row.get("status") or "—"),
            str(row.get("progress") or "0%"),
            str(row.get("downloaded") or "—"),
            str(row.get("remaining") or "—"),
            str(row.get("speed") or "—"),
            str(row.get("eta") or "—"),
        )

    @staticmethod
    def _resolve_play_target(row: Dict[str, Any]) -> Optional[str]:
        for key in ("primary_file", "play_target", "stream_url"):
            value = row.get(key)
            if value:
                return str(value)
        return None

    def _get_selected_download_id(self) -> Optional[str]:
        selection = self._downloads_tree.selection()
        if not selection:
            return None
        return str(selection[0])

    def _get_selected_session_id(self) -> Optional[str]:
        selected = self._get_selected_download_id()
        if not selected:
            return None

        file_row = getattr(self, "_file_rows", {}).get(selected)
        if file_row and file_row.get("parent_id"):
            return str(file_row["parent_id"])

        if "::file::" in selected:
            return selected.split("::file::", 1)[0]

        parent = self._downloads_tree.parent(selected)
        return str(parent or selected)

    def _enqueue_download(self, download_id: str) -> None:
        if download_id not in self._download_rows:
            return
        if download_id not in self._download_queue:
            self._download_queue.append(download_id)
        self._refresh_queue_statuses()

    def _refresh_queue_statuses(self) -> None:
        for position, queued_id in enumerate(self._download_queue, start=1):
            row = self._download_rows.get(queued_id)
            if row is None:
                continue
            row["queue_state"] = "queued"
            self._update_download_row(queued_id, status=f"Queued #{position}", queue_state="queued")

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

    def _apply_session_filter(self) -> None:
        started = perf_counter()
        tree = getattr(self, "_downloads_tree", None)
        if tree is None:
            return

        active_filter = getattr(self, "_active_filter_key", "all")
        session_ids = getattr(self, "_session_order", list(self._download_rows.keys()))

        file_rows_by_parent: Dict[str, list[str]] = {}
        for file_iid, file_row in getattr(self, "_file_rows", {}).items():
            parent_id = file_row.get("parent_id")
            if not parent_id:
                continue
            file_rows_by_parent.setdefault(str(parent_id), []).append(file_iid)

        for session_id in session_ids:
            row = self._download_rows.get(session_id, {})
            matches = active_filter == "all" or row.get("queue_state") == active_filter
            if matches:
                tree.move(session_id, "", "end")
            else:
                tree.detach(session_id)

            for file_iid in file_rows_by_parent.get(session_id, []):
                if matches:
                    tree.move(file_iid, session_id, "end")
                else:
                    tree.detach(file_iid)

        self._record_perf_metric(
            "torrent_session_filter",
            item_count=len(session_ids),
            duration_seconds=perf_counter() - started,
            file_row_count=len(getattr(self, "_file_rows", {})),
            active_filter=active_filter,
        )

    def _selected_open_target(self) -> Optional[str]:
        selected = self._get_selected_download_id()
        if not selected:
            return None

        file_row = getattr(self, "_file_rows", {}).get(selected)
        if file_row and file_row.get("file_path"):
            return str(file_row["file_path"])

        session_id = self._get_selected_session_id()
        if not session_id:
            return None
        row = self._download_rows.get(session_id)
        if row is None:
            return None
        return self._resolve_play_target(row)

    def _find_latest_playable_download_id(self) -> Optional[str]:
        for download_id in reversed(list(self._download_rows.keys())):
            row = self._download_rows[download_id]
            if self._resolve_play_target(row):
                return download_id
        return None

    def _sync_player_button_state(self) -> None:
        active_id = self._selected_download_id or self._find_latest_playable_download_id()
        has_target = False
        if active_id and active_id in self._download_rows:
            has_target = bool(self._resolve_play_target(self._download_rows[active_id]))

        if has_target:
            self._open_player_btn.configure(
                state="normal",
                fg_color=Colors.SUCCESS,
                hover_color=Colors.SUCCESS_HOVER,
                text_color=Colors.TEXT_PRIMARY,
            )
        else:
            self._open_player_btn.configure(
                state="disabled",
                fg_color=Colors.BTN_DISABLED,
                hover_color=Colors.BTN_DISABLED,
                text_color=Colors.TEXT_MUTED,
            )

    def _format_progress_status(self, progress: TorrentProgressSnapshot) -> str:
        parts = [f"{progress.percent}%"]
        if progress.speed_text:
            parts.append(progress.speed_text)
        if progress.eta_text and progress.eta_text != "--":
            parts.append(f"ETA {progress.eta_text}")
        if progress.downloaded_text and progress.total_text:
            parts.append(f"{progress.downloaded_text} / {progress.total_text}")
        return " • ".join(parts)

    def _open_target(self, target: str) -> tuple[bool, Optional[str]]:
        try:
            if platform.system() == "Windows":
                os.startfile(target)  # noqa: S606
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", target])
            else:
                subprocess.Popen(["xdg-open", target])
            return True, None
        except Exception as exc:
            try:
                if target.startswith(("http://", "https://")):
                    if webbrowser.open(target):
                        return True, None
                elif os.path.exists(target):
                    if webbrowser.open(Path(target).resolve().as_uri()):
                        return True, None
            except Exception:
                pass
            return False, str(exc)

    def _handle_player_open_failure(self, message: str) -> None:
        self._log_append(f"[{Icons.ERROR_STATUS}] {message}\n")
        self._set_status(message, Colors.ERROR)
        tm = self.toast_manager_getter()
        if tm:
            tm.show_error(message)
