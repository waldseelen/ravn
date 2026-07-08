"""Central theme catalog shared by config and UI layers."""

from __future__ import annotations

from typing import Dict, List

THEMES: Dict[str, Dict[str, str]] = {
    "dark": {
        "name": "Dark",
        "appearance_mode": "Dark",
        "color_theme": "dark-blue",
        "primary": "#987a4e",
        "secondary": "#A68A6E",
        "background": "#141414",
        "surface": "#1E1E1E",
        "text": "#E8E0D8",
    },
    "light": {
        "name": "Light",
        "appearance_mode": "Light",
        "color_theme": "blue",
        "primary": "#8C6A4A",
        "secondary": "#C2A98E",
        "background": "#F7F3EE",
        "surface": "#FFFFFF",
        "text": "#221814",
    },
}

THEME_ALIASES = {
    "dark": "dark",
    "light": "light",
    "nordic": "dark",
    "graphite": "dark",
    "paper": "light",
    "sand": "light",
    "nordic dark": "dark",
    "graphite dark": "dark",
    "paper light": "light",
    "sand light": "light",
    "forest": "light",
    "aurora": "dark",
    "blue": "light",
    "green": "light",
    "dark-blue": "dark",
    "karanlik": "dark",
    "aydinlik": "light",
}


def get_theme_ids() -> List[str]:
    """Return supported theme identifiers."""
    return list(THEMES.keys())


def normalize_theme_id(value: str | None) -> str:
    """Normalize stored/display theme names to a supported theme id."""
    normalized = str(value or "").strip().lower()
    if normalized in THEMES:
        return normalized
    if normalized in THEME_ALIASES:
        return THEME_ALIASES[normalized]
    return "dark"


def get_theme_definition(theme_id: str | None) -> Dict[str, str]:
    """Get normalized theme definition."""
    return THEMES[normalize_theme_id(theme_id)]


def get_theme_display_name(theme_id: str | None) -> str:
    """Get display label for a normalized theme."""
    return get_theme_definition(theme_id)["name"]


def get_theme_display_names() -> List[str]:
    """Get display labels in stable UI order."""
    return [theme["name"] for theme in THEMES.values()]
