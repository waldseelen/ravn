"""Feedback and progress behavior for the download tab."""

from __future__ import annotations

from pathlib import Path

from ravn_app.core.error_handler import YtDlpErrorParser, format_error_for_user
from ravn_app.core.i18n import t
from ravn_app.ui.advanced_features import NotificationManager
from ravn_app.ui.design_tokens import Colors, Icons, Motion


class FeedbackMixin:
    def _on_download_progress(self, percent: int, message: str):
        self.after(0, self._apply_progress_update, percent, message)

    def _apply_progress_update(self, percent: int, message: str):
        target = max(0.0, min(1.0, percent / 100.0))
        self._download_progress_value = self.animation_manager.smooth_progress(
            self._download_progress_value,
            target,
            max_step=0.08,
        )
        self.download_progress.set(self._download_progress_value)
        if message:
            self.download_status_label.configure(text=message)

    def _on_download_success(self, result):
        self._stop_processing_feedback()
        self.download_progress.set(1.0)
        self._download_progress_value = 1.0
        files = ", ".join(result.output_files) if result.output_files else t("download.completedFallback")
        self.download_status_label.configure(
            text=t("download.downloadComplete", files=files),
            text_color=Colors.STATUS_DONE,
        )
        self.animation_manager.animate_success_flash(
            self.download_status_label,
            duration=Motion.SLOW,
            base_color=Colors.STATUS_DONE,
            flash_color=Colors.SUCCESS_FLASH,
        )
        self._animate_download_completion_pulse()

        try:
            self.bell()
        except Exception:
            pass

        if result.output_files:
            NotificationManager.show_download_complete(Path(result.output_files[0]).name)

        toast_manager = self.toast_manager_getter()
        if toast_manager:
            filename = Path(result.output_files[0]).name if result.output_files else t("common.unknown")
            toast_manager.show_success(t("download.downloadComplete", files=filename))

        self._set_button_loading_state(self.download_btn, is_loading=False)
        restore_text = getattr(self, "_active_btn_restore_text", f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
        self.download_btn.configure(text=restore_text)
        self.after(
            3000,
            lambda: (
                self._hide_progress(),
                self.download_status_label.configure(text="", text_color=Colors.TEXT_SECONDARY),
            ),
        )

    def _on_download_failure(self, error_message: str):
        self._stop_processing_feedback()
        self._hide_progress()
        self._set_button_loading_state(self.download_btn, is_loading=False)
        restore_text = getattr(self, "_active_btn_restore_text", f"{Icons.DOWNLOAD_BTN} {t('download.downloadButton')}")
        self.download_btn.configure(text=restore_text)
        self._show_download_error(error_message, error_message)

        toast_manager = self.toast_manager_getter()
        if toast_manager:
            short_msg = error_message[:50] + "..." if len(error_message) > 50 else error_message
            toast_manager.show_warning(t("download.downloadFailed", message=short_msg))

    def _animate_download_completion_pulse(self):
        self.download_progress.configure(progress_color=Colors.SUCCESS_FLASH)
        self.after(
            Motion.SLOW,
            lambda: self.download_progress.configure(progress_color=Colors.ACCENT),
        )

    def _hide_progress(self):
        self.download_progress.pack_forget()

    def _show_download_error(self, raw_error: str, raw_text: str):
        error_info = YtDlpErrorParser.parse(raw_error)
        user_message = format_error_for_user(error_info)
        self._set_url_validation_state(Icons.ERROR_INDICATOR, Colors.ERROR)
        self.error_panel.show_error(user_message, raw_text or raw_error)

    def _toggle_error_details(self):
        self.error_panel.toggle_details()

    def _start_processing_feedback(self, base_text: str | None = None):
        status_label = self.__dict__.get("download_status_label")
        if status_label is None:
            return

        self._stop_processing_feedback()
        self._processing_text_base = base_text or t("download.downloadLoading")
        self._processing_tick = 0
        self._processing_spinner_index = 0
        self._download_progress_value = 0.0

        if self._spinner_animation_id:
            self.animation_manager.stop_animation(self._spinner_animation_id)
            self._spinner_animation_id = None

        self._update_processing_feedback()

    def _update_processing_feedback(self):
        spinner_frames = ("◐", "◓", "◑", "◒")
        spinner = spinner_frames[self._processing_spinner_index % len(spinner_frames)]

        text = self.animation_manager.format_processing_text(
            self._processing_text_base,
            self._processing_tick,
        )
        self.download_status_label.configure(
            text=f"{spinner} {text}",
            text_color=Colors.STATUS_RUNNING,
        )
        self._processing_tick += 1
        self._processing_spinner_index += 1
        self._processing_after_id = self.after(125, self._update_processing_feedback)

    def _stop_processing_feedback(self):
        processing_after_id = self.__dict__.get("_processing_after_id")
        if processing_after_id is not None:
            try:
                self.after_cancel(processing_after_id)
            except Exception:
                pass
            self._processing_after_id = None

        spinner_animation_id = self.__dict__.get("_spinner_animation_id")
        if spinner_animation_id:
            self.animation_manager.stop_animation(spinner_animation_id)
            self._spinner_animation_id = None

    def _set_button_loading_state(self, button, is_loading: bool):
        if button is None:
            return
        try:
            if is_loading:
                button.configure(state="disabled")
                self.animation_manager.animate_button_disabled(
                    button,
                    duration=Motion.MICRO,
                    target_opacity=0.5,
                )
            else:
                button.configure(state="normal")
                self.animation_manager.animate_button_enabled(
                    button,
                    duration=Motion.MICRO,
                    target_color=Colors.TEXT_PRIMARY,
                )
        except Exception:
            return

    def _apply_button_press_state(self, button):
        if button is None:
            return
        try:
            if not hasattr(button, "_ravn_base_width"):
                button._ravn_base_width = int(button.cget("width"))
            if button._ravn_base_width > 40:
                button.configure(width=max(40, int(button._ravn_base_width * 0.95)))
            button.configure(border_width=1, border_color=Colors.ACCENT_LIGHT)
        except Exception:
            return

    def _apply_button_release_state(self, button):
        if button is None:
            return
        try:
            base_width = int(getattr(button, "_ravn_base_width", button.cget("width")))
            button.configure(width=base_width, border_width=0)
        except Exception:
            return
