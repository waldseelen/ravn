"""Home workspace for the Phase 8 shell."""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

import customtkinter as ctk

from ravn_app.core.i18n import t
from ravn_app.core.tool_health import get_tool_health_checker
from ravn_app.ui.design_tokens import Colors, Cursors, Fonts, Icons, Sizes, Spacing


class _SummaryCard(ctk.CTkFrame):
    def __init__(self, parent, title: str, value: str, subtitle: str, **kwargs):
        kwargs.setdefault("fg_color", Colors.BG_SURFACE)
        super().__init__(parent, **kwargs)
        self.configure(corner_radius=Sizes.CORNER_MD)

        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.title_label.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.XS))

        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=Fonts.TITLE,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        )
        self.value_label.pack(fill="x", padx=Spacing.MD)

        self.subtitle_label = ctk.CTkLabel(
            self,
            text=subtitle,
            font=Fonts.SMALL,
            text_color=Colors.TEXT_MUTED,
            anchor="w",
        )
        self.subtitle_label.pack(fill="x", padx=Spacing.MD, pady=(Spacing.XS, Spacing.MD))

    def update_content(self, title: str, value: str, subtitle: str) -> None:
        self.title_label.configure(text=title)
        self.value_label.configure(text=value)
        self.subtitle_label.configure(text=subtitle)


class _ActionCard(ctk.CTkButton):
    def __init__(self, parent, title: str, detail: str, command: Callable[[], None], **kwargs):
        kwargs.setdefault("fg_color", Colors.BG_SURFACE)
        kwargs.setdefault("hover_color", Colors.BG_HOVER)
        super().__init__(
            parent,
            text=f"{title}\n{detail}",
            command=command,
            font=Fonts.LABEL,
            text_color=Colors.TEXT_PRIMARY,
            height=96,
            anchor="w",
            corner_radius=Sizes.CORNER_MD,
            cursor=Cursors.POINTER,
            **kwargs,
        )


class HomeWorkspace(ctk.CTkFrame):
    """Dashboard-like landing workspace for quick navigation."""

    def __init__(
        self,
        parent,
        db_manager: Any,
        task_queue: Any,
        open_download_view: Callable[[str], None],
        open_studio_view: Callable[[str], None],
        open_library_view: Callable[[Optional[str]], None],
        open_queue_view: Callable[[], None],
        **kwargs,
    ):
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(parent, **kwargs)
        self.configure(fg_color=Colors.BG_PRIMARY)

        self.db_manager = db_manager
        self.task_queue = task_queue
        self.open_download_view = open_download_view
        self.open_studio_view = open_studio_view
        self.open_library_view = open_library_view
        self.open_queue_view = open_queue_view

        self._summary_cards: dict[str, _SummaryCard] = {}
        self._recent_frame = None
        self._build_ui()
        self.refresh_dashboard()

    def refresh_i18n(self) -> None:
        for child in list(self.winfo_children()):
            child.destroy()
        self._summary_cards = {}
        self._recent_frame = None
        self._build_ui()
        self.refresh_dashboard()

    def _build_tool_health_summary(self) -> None:
        """Build compact tool health status banner."""
        checker = get_tool_health_checker()
        summary = checker.get_health_summary()
        
        # Only show if there are issues or user wants to see it
        if summary['overall_status'] == 'critical' or summary['overall_status'] == 'degraded':
            health_frame = ctk.CTkFrame(
                self,
                fg_color=Colors.WARNING_BG if summary['overall_status'] == 'degraded' else Colors.ERROR,
                border_width=1,
                border_color=Colors.WARNING if summary['overall_status'] == 'degraded' else Colors.ERROR,
                corner_radius=Sizes.CORNER_MD
            )
            health_frame.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))
            
            inner = ctk.CTkFrame(health_frame, fg_color="transparent")
            inner.pack(fill="x", padx=Spacing.MD, pady=Spacing.SM)
            
            if summary['overall_status'] == 'critical':
                icon = Icons.ERROR
                status_text = t("home.toolHealthCritical")
                status_color = Colors.ERROR
            else:
                icon = Icons.WARNING
                status_text = t("home.toolHealthDegraded")
                status_color = Colors.WARNING
            
            ctk.CTkLabel(
                inner,
                text=f"{icon}  {status_text}",
                font=Fonts.LABEL_BOLD,
                text_color=status_color,
                anchor="w"
            ).pack(anchor="w")
            
            # Show missing tools
            if summary['missing_required']:
                missing_text = t("home.toolHealthMissingRequired", tools=", ".join(summary['missing_required']))
                ctk.CTkLabel(
                    inner,
                    text=missing_text,
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w",
                    wraplength=1000
                ).pack(anchor="w", pady=(Spacing.XS, 0))
            
            if summary['missing_optional']:
                missing_text = t("home.toolHealthMissingOptional", tools=", ".join(summary['missing_optional']))
                ctk.CTkLabel(
                    inner,
                    text=missing_text,
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w",
                    wraplength=1000
                ).pack(anchor="w", pady=(Spacing.XS, 0))
            
            # Show affected features
            if summary['unavailable_features']:
                features_text = t(
                    "home.toolHealthUnavailableFeatures",
                    features=", ".join(summary['unavailable_features'][:5])
                )
                if len(summary['unavailable_features']) > 5:
                    features_text += f" +{len(summary['unavailable_features']) - 5} more"
                
                ctk.CTkLabel(
                    inner,
                    text=features_text,
                    font=Fonts.SMALL,
                    text_color=Colors.TEXT_MUTED,
                    anchor="w",
                    wraplength=1000
                ).pack(anchor="w", pady=(Spacing.XS, 0))
            
            # Help link
            ctk.CTkLabel(
                inner,
                text=t("home.toolHealthHelp"),
                font=Fonts.SMALL,
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).pack(anchor="w", pady=(Spacing.SM, 0))

    def _build_ui(self) -> None:
        # Tool health summary
        self._build_tool_health_summary()

        quick_actions = ctk.CTkFrame(self, fg_color="transparent")
        quick_actions.pack(fill="x", padx=Spacing.LG, pady=(Spacing.SM, Spacing.MD))

        ctk.CTkLabel(
            quick_actions,
            text=t("home.quickActions"),
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, Spacing.SM))

        actions_grid = ctk.CTkFrame(quick_actions, fg_color="transparent")
        actions_grid.pack(fill="x")
        for column in range(3):
            actions_grid.grid_columnconfigure(column, weight=1)

        actions = [
            (t("home.actionPasteUrl"), t("home.actionPasteUrlDetail"), lambda: self.open_download_view("url")),
            (t("home.actionPlaylist"), t("home.actionPlaylistDetail"), lambda: self.open_download_view("playlist")),
            (t("home.actionTorrent"), t("home.actionTorrentDetail"), lambda: self.open_download_view("torrent")),
            (t("home.actionConvert"), t("home.actionConvertDetail"), lambda: self.open_studio_view("convert")),
            (t("home.actionFilters"), t("home.actionFiltersDetail"), lambda: self.open_studio_view("filters")),
            (t("home.actionLibrary"), t("home.actionLibraryDetail"), lambda: self.open_library_view("library")),
        ]
        for index, (title, detail, command) in enumerate(actions):
            row, column = divmod(index, 3)
            _ActionCard(actions_grid, title=title, detail=detail, command=command).grid(
                row=row,
                column=column,
                sticky="nsew",
                padx=Spacing.XS,
                pady=Spacing.XS,
            )

        summary = ctk.CTkFrame(self, fg_color="transparent")
        summary.pack(fill="x", padx=Spacing.LG, pady=(0, Spacing.MD))

        ctk.CTkLabel(
            summary,
            text=t("home.overview"),
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(anchor="w", pady=(0, Spacing.SM))

        summary_grid = ctk.CTkFrame(summary, fg_color="transparent")
        summary_grid.pack(fill="x")
        for column in range(4):
            summary_grid.grid_columnconfigure(column, weight=1)

        card_specs = [
            ("downloads", t("home.cardDownloads")),
            ("conversions", t("home.cardConversions")),
            ("operations", t("home.cardOperations")),
            ("queue", t("home.cardQueue")),
        ]
        for column, (key, title) in enumerate(card_specs):
            card = _SummaryCard(summary_grid, title=title, value="0", subtitle="—")
            card.grid(row=0, column=column, sticky="nsew", padx=Spacing.XS, pady=Spacing.XS)
            self._summary_cards[key] = card

        recent = ctk.CTkFrame(self, fg_color=Colors.BG_SURFACE, corner_radius=Sizes.CORNER_MD)
        recent.pack(fill="both", expand=True, padx=Spacing.LG, pady=(0, Spacing.LG))

        recent_header = ctk.CTkFrame(recent, fg_color="transparent")
        recent_header.pack(fill="x", padx=Spacing.MD, pady=(Spacing.MD, Spacing.SM))

        ctk.CTkLabel(
            recent_header,
            text=t("home.recentActivity"),
            font=Fonts.H2,
            text_color=Colors.TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            recent_header,
            text=f"{Icons.QUEUE} {t('home.openQueue')}",
            command=self.open_queue_view,
            fg_color=Colors.BTN_SECONDARY,
            hover_color=Colors.BTN_SECONDARY_HOVER,
            text_color=Colors.TEXT_PRIMARY,
            font=Fonts.SMALL,
            height=Sizes.BTN_HEIGHT_SM,
            cursor=Cursors.POINTER,
        ).pack(side="right")

        self._recent_frame = ctk.CTkFrame(recent, fg_color="transparent")
        self._recent_frame.pack(fill="both", expand=True, padx=Spacing.MD, pady=(0, Spacing.MD))

    def refresh_dashboard(self) -> None:
        stats = self.db_manager.get_statistics()
        pending = len(self.task_queue.get_pending_tasks())
        active = len(self.task_queue.get_active_tasks())
        completed = len(self.task_queue.get_completed_tasks())

        self._update_summary_card(
            "downloads",
            t("home.cardDownloads"),
            str(stats.get("total_downloads", 0)),
            t("home.cardDownloadsDetail", success=stats.get("successful_downloads", 0)),
        )
        self._update_summary_card(
            "conversions",
            t("home.cardConversions"),
            str(stats.get("total_conversions", 0)),
            t("home.cardConversionsDetail"),
        )
        self._update_summary_card(
            "operations",
            t("home.cardOperations"),
            str(stats.get("total_operations", 0)),
            t("home.cardOperationsDetail"),
        )
        self._update_summary_card(
            "queue",
            t("home.cardQueue"),
            str(active + pending),
            t("home.cardQueueDetail", active=active, completed=completed),
        )

        entries: list[tuple[str, str]] = []
        for download in self.db_manager.get_downloads(limit=4):
            title = download.title or t("history.noTitle")
            detail = f"{download.format or '—'}  •  {download.status}"
            entries.append((title, detail))

        for operation in self.db_manager.get_operations(limit=3):
            title = operation.title or operation.operation or operation.task_type
            detail = f"{operation.task_type or 'operation'}  •  {operation.status}"
            entries.append((title, detail))

        self._render_recent_entries(entries[:6])

    def _update_summary_card(self, key: str, title: str, value: str, subtitle: str) -> None:
        card = self._summary_cards.get(key)
        if card is None:
            return
        card.update_content(title=title, value=value, subtitle=subtitle)

    def _render_recent_entries(self, entries: Iterable[tuple[str, str]]) -> None:
        if self._recent_frame is None:
            return

        for child in list(self._recent_frame.winfo_children()):
            child.destroy()

        entries = list(entries)
        if not entries:
            ctk.CTkLabel(
                self._recent_frame,
                text=t("home.noRecentActivity"),
                font=Fonts.LABEL,
                text_color=Colors.TEXT_MUTED,
            ).pack(anchor="w", pady=Spacing.SM)
            return

        for title, detail in entries:
            row = ctk.CTkFrame(self._recent_frame, fg_color=Colors.BG_CARD, corner_radius=Sizes.CORNER_MD)
            row.pack(fill="x", pady=Spacing.XS)
            ctk.CTkLabel(
                row,
                text=title,
                font=Fonts.LABEL_BOLD,
                text_color=Colors.TEXT_PRIMARY,
                anchor="w",
            ).pack(fill="x", padx=Spacing.MD, pady=(Spacing.SM, 2))
            ctk.CTkLabel(
                row,
                text=detail,
                font=Fonts.SMALL,
                text_color=Colors.TEXT_MUTED,
                anchor="w",
            ).pack(fill="x", padx=Spacing.MD, pady=(0, Spacing.SM))
