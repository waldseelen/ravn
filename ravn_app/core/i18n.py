"""Runtime i18n manager for RAVN (tr/en)."""

from __future__ import annotations

import json
import locale
import os
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Dict, Optional

_SUPPORTED_LANGUAGES = ("tr", "en")
_DEFAULT_LANGUAGE = "tr"


class I18nManager:
    """Small translation manager with runtime language switching."""

    def __init__(
        self,
        config_manager: Optional[Any] = None,
        default_lang: str = _DEFAULT_LANGUAGE,
        translations_dir: Optional[Path] = None,
    ):
        self._lock = RLock()
        self._config_manager = config_manager
        self._default_lang = default_lang if default_lang in _SUPPORTED_LANGUAGES else _DEFAULT_LANGUAGE
        self._translations_dir = (
            translations_dir
            if translations_dir is not None
            else Path(__file__).resolve().parent.parent / "translations"
        )
        self._translations: Dict[str, Dict[str, Any]] = {}
        self._listeners: list[Callable[[str], None]] = []
        self._current_lang = self._default_lang

        self._load_translations()
        self._current_lang = self._resolve_start_language()

    def _resolve_start_language(self) -> str:
        from_config = None
        if self._config_manager is not None:
            try:
                from_config = self._config_manager.get("language", None)
            except Exception:
                from_config = None

        if from_config in self._translations:
            return str(from_config)

        detected = self.detect_system_language()
        if detected in self._translations:
            return detected

        if self._default_lang in self._translations:
            return self._default_lang

        return "tr" if "tr" in self._translations else next(iter(self._translations), _DEFAULT_LANGUAGE)

    def _load_translations(self) -> None:
        for lang in _SUPPORTED_LANGUAGES:
            file_path = self._translations_dir / f"{lang}.json"
            if not file_path.exists():
                self._translations[lang] = {}
                continue

            with file_path.open("r", encoding="utf-8") as stream:
                self._translations[lang] = json.load(stream)

    @staticmethod
    def detect_system_language() -> Optional[str]:
        """Detect system language and normalize to tr/en."""
        candidates = []

        # LANG and locale environment variables
        for env_name in ("LC_ALL", "LC_MESSAGES", "LANG"):
            env_value = os.environ.get(env_name)
            if env_value:
                candidates.append(env_value)

        # locale module
        try:
            current_locale = locale.getlocale()[0]
            if current_locale:
                candidates.append(current_locale)
        except Exception:
            pass

        try:
            default_locale = locale.getdefaultlocale()[0]  # type: ignore[attr-defined]
            if default_locale:
                candidates.append(default_locale)
        except Exception:
            pass

        for candidate in candidates:
            lang = str(candidate).split(".")[0].split("_")[0].split("-")[0].lower()
            if lang in _SUPPORTED_LANGUAGES:
                return lang

        return None

    @property
    def language(self) -> str:
        return self._current_lang

    def set_language(self, lang: str, persist: bool = True) -> bool:
        with self._lock:
            if lang not in self._translations:
                return False

            if self._current_lang == lang:
                return True

            self._current_lang = lang

            if persist and self._config_manager is not None:
                try:
                    self._config_manager.set("language", lang)
                except Exception:
                    # Never break UI flow because of config write failure.
                    pass

            listeners = list(self._listeners)

        for listener in listeners:
            try:
                listener(lang)
            except Exception:
                continue
        return True

    def register_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def update_config_manager(self, config_manager: Optional[Any]) -> None:
        with self._lock:
            self._config_manager = config_manager

    def t(self, key: str, **kwargs: Any) -> str:
        value = self._resolve_key(self._translations.get(self._current_lang, {}), key)
        if value is None:
            # Fallback to Turkish first for legacy keys.
            value = self._resolve_key(self._translations.get("tr", {}), key)

        if not isinstance(value, str):
            return f"<MISSING: {key}>"

        if kwargs:
            for param_name, param_value in kwargs.items():
                value = value.replace("{" + param_name + "}", str(param_value))

        return value

    @staticmethod
    def _resolve_key(source: Dict[str, Any], key: str) -> Optional[Any]:
        current: Any = source
        for part in key.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(part)
            if current is None:
                return None
        return current

    def format_number(self, number: float, decimals: int = 2) -> str:
        number = float(number)
        formatted = f"{number:,.{decimals}f}"
        if self._current_lang == "tr":
            return formatted.replace(",", "_").replace(".", ",").replace("_", ".")
        return formatted

    def format_currency(self, amount: float) -> str:
        if self._current_lang == "tr":
            return "₺" + self.format_number(amount, decimals=2)
        return "$" + self.format_number(amount, decimals=2)

    def format_date(self, dt: datetime, style: str = "long") -> str:
        if self._current_lang == "tr":
            months = [
                "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
                "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik",
            ]
            if style == "short":
                return f"{dt.day:02d}.{dt.month:02d}.{dt.year}"
            month = months[dt.month - 1]
            return f"{dt.day} {month} {dt.year}"

        if style == "short":
            return dt.strftime("%m/%d/%Y")
        return dt.strftime("%B %d, %Y")

    def format_time(self, dt: datetime, style: str = "short") -> str:
        if style == "full":
            return dt.strftime("%H:%M:%S")
        return dt.strftime("%H:%M")


_global_i18n: Optional[I18nManager] = None


def get_i18n(config_manager: Optional[Any] = None, default_lang: str = _DEFAULT_LANGUAGE) -> I18nManager:
    """Return a shared i18n manager instance."""
    global _global_i18n

    if _global_i18n is None:
        _global_i18n = I18nManager(config_manager=config_manager, default_lang=default_lang)
    elif config_manager is not None:
        _global_i18n.update_config_manager(config_manager)

    return _global_i18n


def t(key: str, **kwargs: Any) -> str:
    """Global translate helper."""
    return get_i18n().t(key, **kwargs)


def reset_i18n_for_tests() -> None:
    """Reset singleton for deterministic tests."""
    global _global_i18n
    _global_i18n = None
