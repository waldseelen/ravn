"""Torrent / Magnet download tab."""

from __future__ import annotations

import os
import platform
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable, Optional

import customtkinter as ctk
from tkinter import filedialog

from ravn_app.core.i18n import t
from ravn_app.core.torrent_downloader import TorrentDownloader, TorrentDownloadMode
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Motion, Sizes, Spacing

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
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.config_manager = config_manager
        self.toast_manager_getter = toast_manager_getter

        aria2c_path = self.config_manager.get("aria2c_path", "aria2c")
        self._downloader = TorrentDownloader(aria2c_path)
        self._download_thread: Optional[threading.Thread] = None
        self._stream_url: Optional[str] = None

        self._setup_ui()
        self._check_aria2c()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        # ── Header ────────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color="transparent")
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
        # packed conditionally in _check_aria2c

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

        # Mode selector
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
        )
        self._mode_selector.set(t("torrent.modeFull"))
        self._mode_selector.pack(anchor="w", pady=(Spacing.XS, 0))

        # Output directory
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
            cursor=Cursors.POINTER,
        )
        self._download_btn.pack(side="left", padx=(0, Spacing.XS))

        self._cancel_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.STOP} {t('torrent.cancelBtn')}",
            command=self._cancel_download,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.DANGER,
            hover_color=Colors.DANGER_HOVER,
            state="disabled",
            text_color=Colors.TEXT_MUTED,
            cursor=Cursors.POINTER,
        )
        self._cancel_btn.pack(side="left", padx=(0, Spacing.XS))

        self._open_player_btn = ctk.CTkButton(
            action_frame,
            text=f"{Icons.PLAY} {t('torrent.openPlayerBtn')}",
            command=self._open_stream_in_player,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_LG,
            fg_color=Colors.SUCCESS,
            hover_color=Colors.SUCCESS_HOVER,
            state="disabled",
            text_color=Colors.TEXT_MUTED,
            cursor=Cursors.POINTER,
        )
        self._open_player_btn.pack(side="left")

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

    # ------------------------------------------------------------------
    # aria2c availability check
    # ------------------------------------------------------------------

    def _check_aria2c(self):
        available = self._downloader.is_available()
        if not available:
            self._aria2c_banner.pack(fill="x", padx=Spacing.MD, pady=Spacing.XS, after=None)
            # Re-order: insert banner right after header (index trick via pack)
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
        # tkinterdnd2 wraps paths with braces on Windows
        path = raw.strip("{}").strip("'\"")
        if not path.lower().endswith(".torrent"):
            tm = self.toast_manager_getter()
            if tm:
                tm.show_warning(".torrent uzantili bir dosya suruklemeniz gerekiyor.")
            return
        self._source_entry.delete(0, "end")
        self._source_entry.insert(0, path)

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

        self._set_downloading_state(True)
        self._stream_url = None
        self._open_player_btn.configure(state="disabled")
        self._progress_bar.set(0)
        self._log_append(f"[↓] {source}\n[⌂] {output_dir}\n")

        self._download_thread = threading.Thread(
            target=self._run_download,
            args=(source, output_dir, mode, seed_time),
            daemon=True,
        )
        self._download_thread.start()

    def _run_download(
        self,
        source: str,
        output_dir: str,
        mode: TorrentDownloadMode,
        seed_time: int,
    ):
        def progress_cb(percent: int, message: str):
            self.after(0, self._on_progress, percent, message)

        result = self._downloader.download(
            source=source,
            output_dir=output_dir,
            mode=mode,
            progress_callback=progress_cb,
            seed_time=seed_time,
        )
        self.after(0, self._on_download_done, result)

    def _cancel_download(self):
        self._downloader.cancel()
        self._set_downloading_state(False)
        self._set_status(t("torrent.cancelled"), Colors.WARNING)
        self._log_append(f"[×] {t('torrent.cancelled')}\n")
        tm = self.toast_manager_getter()
        if tm:
            tm.show_warning(t("torrent.cancelled"))

    # ------------------------------------------------------------------
    # Callbacks (main-thread only)
    # ------------------------------------------------------------------

    def _on_progress(self, percent: int, message: str):
        self._progress_bar.set(max(0, min(percent, 100)) / 100.0)
        self._set_status(f"{percent}%  {message}", Colors.STATUS_RUNNING)
        if message:
            self._log_append(f"{message}\n")

    def _on_download_done(self, result):
        self._set_downloading_state(False)

        if result.success:
            self._progress_bar.set(1.0)
            count = len(result.output_files)
            self._set_status(t("torrent.completed"), Colors.SUCCESS)
            self._log_append(f"[✓] {t('torrent.completed')}\n")
            self._log_append(t("torrent.outputFiles", count=count) + "\n")
            for f in result.output_files:
                self._log_append(f"    {f}\n")

            if result.stream_url:
                self._stream_url = result.stream_url
                self._open_player_btn.configure(state="normal")
                self._set_status(t("torrent.streamReady"), Colors.SUCCESS)
                self._log_append(f"[▶] {result.stream_url}\n")

            tm = self.toast_manager_getter()
            if tm:
                tm.show_success(t("torrent.completed"))
        else:
            self._progress_bar.set(0)
            msg = t("torrent.failed", error=result.error_message)
            self._set_status(msg, Colors.ERROR)
            self._log_append(f"[×] {msg}\n")
            tm = self.toast_manager_getter()
            if tm:
                tm.show_error(msg)

    # ------------------------------------------------------------------
    # Stream player
    # ------------------------------------------------------------------

    def _open_stream_in_player(self):
        if not self._stream_url:
            return
        try:
            if platform.system() == "Windows":
                os.startfile(self._stream_url)  # noqa: S606
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", self._stream_url])
            else:
                subprocess.Popen(["xdg-open", self._stream_url])
        except Exception as exc:
            self._log_append(f"[!] Oynatici acilamadi: {exc}\n")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_mode(self) -> TorrentDownloadMode:
        label = self._mode_selector.get()
        if label == t("torrent.modeSequential"):
            return TorrentDownloadMode.SEQUENTIAL
        if label == t("torrent.modeStream"):
            return TorrentDownloadMode.STREAM
        return TorrentDownloadMode.FULL

    def _set_downloading_state(self, is_downloading: bool):
        if is_downloading:
            self._download_btn.configure(state="disabled", text_color=Colors.TEXT_MUTED)
            self._cancel_btn.configure(state="normal", text_color=Colors.TEXT_PRIMARY)
            self._set_status(t("torrent.downloading"), Colors.STATUS_RUNNING)
        else:
            self._download_btn.configure(state="normal", text_color=Colors.TEXT_PRIMARY)
            self._cancel_btn.configure(state="disabled", text_color=Colors.TEXT_MUTED)

    def _set_status(self, text: str, color: str = Colors.TEXT_MUTED):
        self._status_label.configure(text=text, text_color=color)

    def _log_append(self, text: str):
        self._log_text.configure(state="normal")
        self._log_text.insert("end", text)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")
