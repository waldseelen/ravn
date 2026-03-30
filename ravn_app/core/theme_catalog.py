"""Central theme catalog shared by config and UI layers."""

from __future__ import annotations

from typing import Dict, List


THEMES: Dict[str, Dict[str, str]] = {
    "nordic": {
        "name": "Nordic Dark",
        "appearance_mode": "Dark",
        "color_theme": "dark-blue",
        "primary": "#987a4e",
        "secondary": "#A68A6E",
        "background": "#141414",
        "surface": "#1E1E1E",
        "text": "#E8E0D8",
    },
    "graphite": {
        "name": "Graphite Dark",
        "appearance_mode": "Dark",
        "color_theme": "blue",
        "primary": "#5B6470",
        "secondary": "#88919C",
        "background": "#101214",
        "surface": "#1A1D21",
        "text": "#E6EAEE",
    },
    "paper": {
        "name": "Paper Light",
        "appearance_mode": "Light",
        "color_theme": "blue",
        "primary": "#8C6A4A",
        "secondary": "#C2A98E",
        "background": "#F7F3EE",
        "surface": "#FFFFFF",
        "text": "#221814",
    },
    "sand": {
        "name": "Sand Light",
        "appearance_mode": "Light",
        "color_theme": "green",
        "primary": "#7B8B6F",
        "secondary": "#B5C2A6",
        "background": "#F3F1E8",
        "surface": "#FFFDF7",
        "text": "#1F1B16",
    },
}

THEME_ALIASES = {
    "nordic dark": "nordic",
    "graphite dark": "graphite",
    "paper light": "paper",
    "sand light": "sand",
    "forest": "sand",
    "aurora": "graphite",
    "dark": "graphite",
    "light": "paper",
    "blue": "paper",
    "green": "sand",
    "dark-blue": "nordic",
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
    return "nordic"


def get_theme_definition(theme_id: str | None) -> Dict[str, str]:
    """Get normalized theme definition."""
    return THEMES[normalize_theme_id(theme_id)]


def get_theme_display_name(theme_id: str | None) -> str:
    """Get display label for a normalized theme."""
    return get_theme_definition(theme_id)["name"]


def get_theme_display_names() -> List[str]:
    """Get display labels in stable UI order."""
    return [theme["name"] for theme in THEMES.values()]
