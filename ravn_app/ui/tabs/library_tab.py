"""Phase 7 media library tab for local catalog browsing and export."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path
from time import perf_counter
from tkinter import filedialog
from typing import Any, Callable, Optional

import customtkinter as ctk

from ravn_app.core.database import OperationRecord
from ravn_app.core.i18n import t
from ravn_app.core.persistence.media_library import MediaItemRecord, MediaLibrary, MediaSearchFilters
from ravn_app.core.task_manager import Task, TaskQueue, TaskResult, TaskType
from ravn_app.utils.metadata_handler import MetadataHandler
from ravn_app.ui.components.error_panel import ErrorPanel
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing
from ravn_app.ui.ui_components import EmptyStateWidget, bind_focus_ring, set_button_loading_state, style_combo, style_entry


class LibraryTab(ctk.CTkFrame):
    """Local media library browser and organizer."""

    def __init__(
        self,
        parent,
        config_manager: Any,
        db_manager: Any,
        task_queue: TaskQueue,
        animation_manager: Any,
        toast_manager_getter: Callable[[], Any],
        show_queue_tab_callback: Optional[Callable[[], None]] = None,
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
        self.library_config = self.config_manager.get_section("library") if self.config_manager else {}

        ffmpeg_path = self.config_manager.get("ffmpeg_path", "ffmpeg") if self.config_manager else "ffmpeg"
        self._ffmpeg_path = ffmpeg_path
        metadata_handler = MetadataHandler(ffmpeg_path=ffmpeg_path)
        self.library = MediaLibrary(metadata_handler=metadata_handler)
        self._collection_name_to_id: dict[str, int] = {}
        self._last_results: list[MediaItemRecord] = []
        self._active_task_id: Optional[str] = None
        self._active_task_context: dict[str, Any] = {}
        self._chunked_result_rendering_enabled = True
        self._result_render_after_id: Optional[str] = None
        self._result_render_token = 0
        self._perf_metrics: dict[str, dict[str, Any]] = {}

        self._setup_ui()
        self.refresh_dashboard()

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tags(raw_value: str) -> list[str]:
        tags: list[str] = []
        for candidate in str(raw_value or "").split(","):
            normalized = candidate.strip().lower()
            if normalized and normalized not in tags:
                tags.append(normalized)
        return tags

    @staticmethod
    def format_size(size_bytes: int) -> str:
        value = float(size_bytes or 0)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if value < 1024.0:
                return f"{value:.1f} {unit}"
            value /= 1024.0
        return f"{value:.1f} PB"

    @staticmethod
    def format_duration(duration_seconds: float) -> str:
        total_seconds = int(duration_seconds or 0)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=Spacing.MD, pady=Spacing.MD)

        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x", pady=(0, Spacing.SM))

        ctk.CTkLabel(
            header,
            text=f"{Icons.LIBRARY} {t('library.title')}",
            font=Fonts.H1,
            text_color=Colors.TEXT_PRIMARY,
        ).pack(anchor="w")

        ctk.CTkLabel(
            header,
            text=t("library.subtitle"),
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
        ).pack(anchor="w", pady=(Spacing.XS, 0))

        body = ctk.CTkFrame(content, fg_color="transparent")
        body.pack(fill="both", expand=True)

        main_column = ctk.CTkFrame(body, fg_color="transparent")
        main_column.pack(side="left", fill="both", expand=True, padx=(0, Spacing.SM))

        sidebar = ctk.CTkFrame(body, fg_color="transparent", width=320)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        self._build_import_card(main_column)
        self._build_search_card(main_column)
        self.error_panel = ErrorPanel(main_column, animation_manager=self.animation_manager)
        self._build_results_card(main_column)
        self._build_sidebar(sidebar)

    def _build_import_card(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        card.pack(fill="x", pady=Spacing.XS)

        ctk.CTkLabel(card, text=t("library.importSection"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        file_row = ctk.CTkFrame(card, fg_color="transparent")
        file_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.XS))
        self.file_entry = ctk.CTkEntry(file_row, placeholder_text=t("library.filePlaceholder"), font=Fonts.LABEL)
        style_entry(self.file_entry)
        bind_focus_ring(self.file_entry)
        self.file_entry.configure(cursor=Cursors.TEXT)
        self.file_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))
        ctk.CTkButton(
            file_row,
            text=Icons.BROWSE,
            width=40,
            command=self._browse_media_file,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        meta_row = ctk.CTkFrame(card, fg_color="transparent")
        meta_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.XS))

        self.title_entry = ctk.CTkEntry(meta_row, placeholder_text=t("library.titlePlaceholder"), font=Fonts.LABEL)
        style_entry(self.title_entry)
        bind_focus_ring(self.title_entry)
        self.title_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        self.tags_entry = ctk.CTkEntry(meta_row, placeholder_text=t("library.tagsPlaceholder"), font=Fonts.LABEL)
        style_entry(self.tags_entry)
        bind_focus_ring(self.tags_entry)
        self.tags_entry.pack(side="left", fill="x", expand=True)

        action_row = ctk.CTkFrame(card, fg_color="transparent")
        action_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        self.add_btn = ctk.CTkButton(
            action_row,
            text=f"{Icons.ADD} {t('library.addButton')}",
            command=self._add_media,
            font=Fonts.LABEL_BOLD,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.ACCENT,
            hover_color=Colors.ACCENT_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        )
        self.add_btn.pack(side="right")

    def _build_search_card(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        card.pack(fill="x", pady=Spacing.XS)

        ctk.CTkLabel(card, text=t("library.searchSection"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        search_row = ctk.CTkFrame(card, fg_color="transparent")
        search_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.XS))

        self.search_entry = ctk.CTkEntry(search_row, placeholder_text=t("library.searchPlaceholder"), font=Fonts.LABEL)
        style_entry(self.search_entry)
        bind_focus_ring(self.search_entry)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        self.search_tags_entry = ctk.CTkEntry(search_row, placeholder_text=t("library.searchTagsPlaceholder"), font=Fonts.LABEL)
        style_entry(self.search_tags_entry)
        bind_focus_ring(self.search_tags_entry)
        self.search_tags_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        self.format_combo = ctk.CTkComboBox(
            search_row,
            values=[t("common.all"), "mp4", "mp3", "mkv", "webm", "wav", "flac", "aac", "mov"],
            width=120,
            font=Fonts.LABEL,
        )
        style_combo(self.format_combo)
        self.format_combo.set(t("common.all"))
        self.format_combo.pack(side="left")

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        ctk.CTkButton(
            actions,
            text=f"{Icons.SEARCH} {t('library.searchButton')}",
            command=self._search_media,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text=f"{Icons.CLEAR_BTN} {t('library.resetButton')}",
            command=self._reset_search,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left", padx=(Spacing.XS, 0))

        ctk.CTkButton(
            actions,
            text=t("library.exportJsonButton"),
            command=lambda: self._export_library("json"),
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="right")

        ctk.CTkButton(
            actions,
            text=t("library.exportCsvButton"),
            command=lambda: self._export_library("csv"),
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_MD,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="right", padx=(0, Spacing.XS))

    def _build_results_card(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        card.pack(fill="both", expand=True, pady=Spacing.XS)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        ctk.CTkLabel(header, text=t("library.resultsTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(side="left")
        self.results_info_label = ctk.CTkLabel(header, text="", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED)
        self.results_info_label.pack(side="right")

        self.results_frame = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.results_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))

    def _build_sidebar(self, parent) -> None:
        self.stats_card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        self.stats_card.pack(fill="x", pady=Spacing.XS)
        ctk.CTkLabel(self.stats_card, text=t("library.statsTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        self.stats_label = ctk.CTkLabel(self.stats_card, text="", font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, justify="left")
        self.stats_label.pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.MD))

        self.collections_card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        self.collections_card.pack(fill="x", pady=Spacing.XS)
        ctk.CTkLabel(self.collections_card, text=t("library.collectionsTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        create_row = ctk.CTkFrame(self.collections_card, fg_color="transparent")
        create_row.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.XS))

        self.collection_entry = ctk.CTkEntry(create_row, placeholder_text=t("library.collectionPlaceholder"), font=Fonts.LABEL)
        style_entry(self.collection_entry)
        bind_focus_ring(self.collection_entry)
        self.collection_entry.pack(side="left", fill="x", expand=True, padx=(0, Spacing.XS))

        ctk.CTkButton(
            create_row,
            text=Icons.ADD,
            width=40,
            command=self._create_collection,
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        self.collection_target_combo = ctk.CTkComboBox(self.collections_card, values=[t("library.noCollectionSelected")], width=250, font=Fonts.LABEL)
        style_combo(self.collection_target_combo)
        self.collection_target_combo.set(t("library.noCollectionSelected"))
        self.collection_target_combo.pack(anchor="w", padx=Spacing.MD, pady=(0, Spacing.SM))

        self.collections_list = ctk.CTkScrollableFrame(self.collections_card, fg_color="transparent", height=150)
        self.collections_list.pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.MD))

        self.recent_card = ctk.CTkFrame(parent, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        self.recent_card.pack(fill="both", expand=True, pady=Spacing.XS)
        ctk.CTkLabel(self.recent_card, text=t("library.recentSearchesTitle"), font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))
        self.recent_searches_frame = ctk.CTkScrollableFrame(self.recent_card, fg_color="transparent", height=200)
        self.recent_searches_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))

    # ------------------------------------------------------------------
    # Refresh / rendering
    # ------------------------------------------------------------------

    def refresh_dashboard(self) -> None:
        self._refresh_stats()
        self._refresh_collections()
        self._refresh_recent_searches()
        self._render_results(self.library.list_media(limit=self._max_results()))

    def _refresh_stats(self) -> None:
        stats = self.library.get_statistics()
        text = "\n".join(
            [
                t("library.statsItems", count=stats["total_items"]),
                t("library.statsSize", size=self.format_size(stats["total_size"])),
                t("library.statsCollections", count=stats["collections"]),
                t("library.statsDuplicates", count=stats["duplicate_groups"]),
            ]
        )
        self.stats_label.configure(text=text)

    def _refresh_collections(self) -> None:
        for child in self.collections_list.winfo_children():
            child.destroy()

        collections = self.library.list_collections()
        self._collection_name_to_id = {item.name: int(item.id or 0) for item in collections}
        combo_values = [t("library.noCollectionSelected")] + [item.name for item in collections]
        self.collection_target_combo.configure(values=combo_values)
        if self.collection_target_combo.get() not in combo_values:
            self.collection_target_combo.set(combo_values[0])

        if not collections:
            EmptyStateWidget(
                self.collections_list,
                icon=Icons.EMPTY_LIST,
                message=t("library.noCollections"),
            ).pack(fill="x", pady=Spacing.SM)
            return

        for collection in collections:
            row = ctk.CTkFrame(self.collections_list, fg_color=Colors.BG_CARD, corner_radius=Sizes.CORNER_SM)
            row.pack(fill="x", pady=(0, Spacing.XS))
            ctk.CTkLabel(row, text=collection.name, font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY).pack(anchor="w", padx=Spacing.SM, pady=(Spacing.XS, 0))
            ctk.CTkLabel(row, text=collection.description or t("library.collectionEmptyDescription"), font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, wraplength=260).pack(anchor="w", padx=Spacing.SM, pady=(0, Spacing.XS))

    def _refresh_recent_searches(self) -> None:
        for child in self.recent_searches_frame.winfo_children():
            child.destroy()

        recent = self.library.get_recent_searches(limit=10)
        if not recent:
            EmptyStateWidget(
                self.recent_searches_frame,
                icon=Icons.SEARCH,
                message=t("library.noRecentSearches"),
            ).pack(fill="x", pady=Spacing.SM)
            return

        for item in recent:
            label = item.get("query_text") or t("library.emptyQueryLabel")
            button = ctk.CTkButton(
                self.recent_searches_frame,
                text=f"{label} ({item.get('result_count', 0)})",
                command=lambda q=item.get("query_text", ""): self._apply_recent_search(q),
                font=Fonts.LABEL,
                height=Sizes.BTN_HEIGHT_SM,
                anchor="w",
                fg_color=Colors.BTN_SECONDARY,
                hover_color=Colors.BTN_SECONDARY_HOVER,
                text_color=Colors.TEXT_PRIMARY,
                cursor=Cursors.POINTER,
            )
            button.pack(fill="x", pady=(0, Spacing.XS))

    def _record_perf_metric(self, name: str, *, item_count: int, duration_seconds: float, chunked: bool = False, **extra: Any) -> None:
        metrics = getattr(self, "_perf_metrics", None)
        if metrics is None:
            metrics = {}
            self._perf_metrics = metrics
        metrics[name] = {
            "item_count": int(item_count),
            "duration_ms": round(float(duration_seconds) * 1000.0, 3),
            "chunked": bool(chunked),
            **extra,
        }

    def _render_results(self, items: list[MediaItemRecord]) -> None:
        render_started = perf_counter()
        self._last_results = items

        existing_after = getattr(self, "_result_render_after_id", None)
        if existing_after and hasattr(self, "after_cancel"):
            try:
                self.after_cancel(existing_after)
            except Exception:
                pass
            self._result_render_after_id = None

        for child in self.results_frame.winfo_children():
            child.destroy()

        self.results_info_label.configure(text=t("library.resultsCount", count=len(items)))

        if not items:
            EmptyStateWidget(
                self.results_frame,
                icon=Icons.EMPTY_FOLDER,
                message=t("library.noResults"),
            ).pack(fill="both", expand=True, pady=Spacing.XL)
            self._record_perf_metric("library_results_render", item_count=0, duration_seconds=perf_counter() - render_started)
            return

        chunk_enabled = bool(getattr(self, "_chunked_result_rendering_enabled", False))
        render_in_chunks = chunk_enabled and len(items) > 120 and callable(getattr(self, "after", None))
        batch_size = 40
        render_batches = 0

        def finalize_render(chunked: bool, batches: int) -> None:
            self._record_perf_metric(
                "library_results_render",
                item_count=len(items),
                duration_seconds=perf_counter() - render_started,
                chunked=chunked,
                batches=batches,
            )

        if not render_in_chunks:
            for item in items:
                self._create_result_item(item)
            finalize_render(False, 1 if items else 0)
            return

        self._result_render_token = int(getattr(self, "_result_render_token", 0)) + 1
        active_token = self._result_render_token

        def render_batch(start_index: int = 0) -> None:
            nonlocal render_batches
            if active_token != getattr(self, "_result_render_token", active_token):
                return

            render_batches += 1
            end_index = min(start_index + batch_size, len(items))
            for item in items[start_index:end_index]:
                self._create_result_item(item)

            if end_index < len(items):
                self._result_render_after_id = self.after(1, lambda: render_batch(end_index))
                return

            self._result_render_after_id = None
            finalize_render(True, render_batches)

        render_batch(0)

    def _create_result_item(self, item: MediaItemRecord) -> None:
        card = ctk.CTkFrame(self.results_frame, fg_color=Colors.BG_CARD, corner_radius=Sizes.CORNER_MD)
        card.pack(fill="x", pady=(0, Spacing.SM))

        title = item.title or Path(item.file_path).stem
        ctk.CTkLabel(card, text=title, font=Fonts.LABEL_BOLD, text_color=Colors.TEXT_PRIMARY, anchor="w", wraplength=720).pack(fill="x", padx=Spacing.MD, pady=(Spacing.SM, Spacing.XS))

        details = [
            f"{item.format.upper() if item.format else t('common.unknown')}",
            self.format_duration(item.duration),
            self.format_size(item.size),
        ]
        if item.width and item.height:
            details.append(f"{item.width}x{item.height}")
        elif item.sample_rate:
            details.append(f"{item.sample_rate} Hz")
        if item.tags:
            details.append(", ".join(item.tags))

        ctk.CTkLabel(card, text="  •  ".join(details), font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, anchor="w", wraplength=760).pack(fill="x", padx=Spacing.MD)
        ctk.CTkLabel(card, text=item.file_path, font=Fonts.SMALL, text_color=Colors.TEXT_MUTED, anchor="w", wraplength=760).pack(fill="x", padx=Spacing.MD, pady=(Spacing.XS, 0))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=Spacing.MD, pady=(Spacing.SM, Spacing.SM))

        ctk.CTkButton(
            actions,
            text=t("library.openFileButton"),
            command=lambda path=item.file_path: self._open_file(path),
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left")

        ctk.CTkButton(
            actions,
            text=t("library.openFolderButton"),
            command=lambda path=item.file_path: self._open_folder(path),
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="left", padx=(Spacing.XS, 0))

        ctk.CTkButton(
            actions,
            text=t("library.addToCollectionButton"),
            command=lambda media_id=int(item.id or 0): self._add_to_selected_collection(media_id),
            font=Fonts.LABEL,
            height=Sizes.BTN_HEIGHT_SM,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            cursor=Cursors.POINTER,
        ).pack(side="right")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _max_results(self) -> int:
        return int(self.library_config.get("max_search_results", 100) or 100)

    def _browse_media_file(self) -> None:
        path = filedialog.askopenfilename(title=t("library.selectMediaTitle"), filetypes=[(t("library.mediaFiles"), "*.*")])
        if path:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, path)

    def _set_add_running(self, is_running: bool) -> None:
        if is_running:
            set_button_loading_state(self.add_btn, True, loading_text=t("library.addingButton"))
        else:
            set_button_loading_state(self.add_btn, False, original_text=f"{Icons.ADD} {t('library.addButton')}")

    def _reset_active_task(self) -> None:
        self._active_task_id = None
        self._active_task_context = {}

    def _queue_add_media_worker(self, file_path: str, title: Optional[str], tags: list[str], progress_callback=None) -> TaskResult:
        _ = progress_callback
        worker_library = MediaLibrary(
            db_path=self.library.db_path,
            metadata_handler=MetadataHandler(ffmpeg_path=self._ffmpeg_path),
        )
        try:
            media_id = worker_library.add_media(file_path=file_path, title=title, tags=tags)
        finally:
            worker_library.close()
        return TaskResult(
            success=True,
            output_path=file_path,
            metadata={
                "media_id": media_id,
                "file_path": file_path,
                "title": title or Path(file_path).stem,
                "tags": tags,
            },
        )

    def _persist_task_record(self, task: Task, status_override: Optional[str] = None) -> None:
        if not self.db_manager or not self._active_task_context:
            return
        file_path = self._active_task_context.get("file_path", "")
        metadata = dict(task.result.metadata) if task.result and isinstance(task.result.metadata, dict) else {}
        record = OperationRecord(
            task_type=task.task_type.value,
            operation="import",
            title=metadata.get("title") or Path(file_path).name,
            input_paths=[file_path] if file_path else [],
            output_path=file_path,
            format=Path(file_path).suffix.lstrip(".").lower() if file_path else "",
            started_at=task.started_at.isoformat() if task.started_at else "",
            completed_at=task.completed_at.isoformat() if task.completed_at else "",
            duration=(task.result.duration_seconds if task.result else 0.0),
            status=status_override or task.status.value,
            error_message=(task.result.error_message if task.result else "") or "",
            metadata=metadata,
        )
        try:
            self.db_manager.add_operation(record)
        except Exception:
            pass

    def _add_media(self) -> None:
        if self._active_task_id:
            return

        file_path = self.file_entry.get().strip()
        if not file_path:
            self._show_error(t("library.fileRequired"))
            return
        if not Path(file_path).exists():
            self._show_error(t("library.fileMissing", path=file_path))
            return

        title = self.title_entry.get().strip() or None
        tags = self._parse_tags(self.tags_entry.get())

        self.error_panel.hide_error()
        self._set_add_running(True)
        self._active_task_context = {
            "file_path": file_path,
            "title": title,
            "tags": tags,
        }
        self._active_task_id = self.task_queue.add_task(
            task_type=TaskType.LIBRARY_SCAN,
            name=t("library.addButton"),
            execute_fn=self._queue_add_media_worker,
            kwargs={
                "file_path": file_path,
                "title": title,
                "tags": tags,
            },
            on_complete=self._on_add_media_complete,
            on_error=self._on_add_media_error,
            on_cancel=self._on_add_media_cancel,
        )
        if self.show_queue_tab_callback:
            self.show_queue_tab_callback()

    def _on_add_media_complete(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_add_running(False)
        self._persist_task_record(task)
        self.file_entry.delete(0, "end")
        self.title_entry.delete(0, "end")
        self.tags_entry.delete(0, "end")
        self.refresh_dashboard()
        toast = self.toast_manager_getter()
        if toast:
            toast.show_success(t("library.addedToast", mediaId=(task.result.metadata or {}).get("media_id", "?")))
        self._reset_active_task()

    def _on_add_media_error(self, task: Task, error_message: str) -> None:
        if task.id != self._active_task_id:
            return
        self._set_add_running(False)
        self._persist_task_record(task)
        self._show_error(t("library.addFailed", error=error_message), raw_error=error_message)
        toast = self.toast_manager_getter()
        if toast:
            toast.show_error(error_message)
        self._reset_active_task()

    def _on_add_media_cancel(self, task: Task) -> None:
        if task.id != self._active_task_id:
            return
        self._set_add_running(False)
        self._persist_task_record(task, status_override="cancelled")
        self._reset_active_task()

    def _search_media(self) -> None:
        try:
            filters = MediaSearchFilters(
                format=None if self.format_combo.get() == t("common.all") else self.format_combo.get().strip().lower(),
                tags=self._parse_tags(self.search_tags_entry.get()),
                limit=self._max_results(),
            )
            items = self.library.search_media(query=self.search_entry.get().strip(), filters=filters)
        except Exception as exc:
            self._show_error(t("library.searchFailed", error=exc), raw_error=str(exc))
            return

        self.error_panel.hide_error()
        self._refresh_recent_searches()
        self._render_results(items)

    def _reset_search(self) -> None:
        self.search_entry.delete(0, "end")
        self.search_tags_entry.delete(0, "end")
        self.format_combo.set(t("common.all"))
        self.error_panel.hide_error()
        self._render_results(self.library.list_media(limit=self._max_results()))
        self._refresh_recent_searches()

    def _create_collection(self) -> None:
        name = self.collection_entry.get().strip()
        if not name:
            self._show_error(t("library.collectionNameRequired"))
            return
        try:
            self.library.create_collection(name)
        except Exception as exc:
            self._show_error(t("library.collectionCreateFailed", error=exc), raw_error=str(exc))
            return

        self.collection_entry.delete(0, "end")
        self.error_panel.hide_error()
        self._refresh_collections()
        self._refresh_stats()
        toast = self.toast_manager_getter()
        if toast:
            toast.show_success(t("library.collectionCreated", name=name))

    def _add_to_selected_collection(self, media_id: int) -> None:
        selected_name = self.collection_target_combo.get().strip()
        collection_id = self._collection_name_to_id.get(selected_name)
        if not collection_id:
            self._show_error(t("library.selectCollectionError"))
            return
        try:
            self.library.add_to_collection(media_id=media_id, collection_id=collection_id)
        except Exception as exc:
            self._show_error(t("library.addToCollectionFailed", error=exc), raw_error=str(exc))
            return

        self.error_panel.hide_error()
        self._refresh_stats()
        toast = self.toast_manager_getter()
        if toast:
            toast.show_success(t("library.addedToCollectionToast", collection=selected_name))

    def _export_library(self, export_format: str) -> None:
        suffix = ".json" if export_format == "json" else ".csv"
        path = filedialog.asksaveasfilename(
            title=t("library.selectExportTitle"),
            defaultextension=suffix,
            filetypes=[(suffix.upper().lstrip("."), f"*{suffix}"), (t("library.allFiles"), "*.*")],
        )
        if not path:
            return

        try:
            self.library.export_library(export_format, path)
        except Exception as exc:
            self._show_error(t("library.exportFailed", error=exc), raw_error=str(exc))
            return

        self.error_panel.hide_error()
        toast = self.toast_manager_getter()
        if toast:
            toast.show_success(t("library.exportedToast", path=Path(path).name))

    def _apply_recent_search(self, query: str) -> None:
        self.search_entry.delete(0, "end")
        self.search_entry.insert(0, query)
        self._search_media()

    # ------------------------------------------------------------------
    # OS file helpers
    # ------------------------------------------------------------------

    def _open_file(self, file_path: str) -> None:
        path = Path(file_path)
        if not path.exists():
            self._show_error(t("library.fileMissing", path=file_path))
            return
        try:
            if platform.system() == "Windows":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            self._show_error(str(exc), raw_error=str(exc))

    def _open_folder(self, file_path: str) -> None:
        path = Path(file_path)
        folder = path.parent
        if not folder.exists():
            self._show_error(t("library.fileMissing", path=file_path))
            return
        try:
            if platform.system() == "Windows":
                subprocess.run(["explorer", "/select,", str(path)], check=False)
            elif platform.system() == "Darwin":
                subprocess.run(["open", "-R", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(folder)], check=False)
        except Exception as exc:
            self._show_error(str(exc), raw_error=str(exc))

    def _show_error(self, message: str, raw_error: Optional[str] = None) -> None:
        self.error_panel.show_error(message, raw_error or message)

    # ------------------------------------------------------------------
    # Shortcuts / lifecycle
    # ------------------------------------------------------------------

    def _on_ctrl_enter(self, event=None):
        if not self.winfo_viewable():
            return
        if self.file_entry.get().strip():
            self._add_media()
        else:
            self._search_media()

    def _on_escape(self, event=None):
        if not self.winfo_viewable():
            return
        if self._active_task_id:
            self.task_queue.cancel_task(self._active_task_id)
        else:
            self.error_panel.hide_error()

    def _on_ctrl_l(self, event=None):
        if not self.winfo_viewable():
            return
        self.search_entry.delete(0, "end")
        self.search_tags_entry.delete(0, "end")
        self.format_combo.set(t("common.all"))
        self.file_entry.delete(0, "end")
        self.title_entry.delete(0, "end")
        self.tags_entry.delete(0, "end")
        self.collection_entry.delete(0, "end")
        self.error_panel.hide_error()
        if not self._active_task_id:
            self._render_results(self.library.list_media(limit=self._max_results()))
        return "break"

    def destroy(self):
        try:
            self.library.close()
        except Exception:
            pass
        super().destroy()
