"""
RAVN - UI Design Tokens
Centralized typography, color, and spacing constants for all UI components.

Usage:
    from ravn_app.ui.design_tokens import Colors, Fonts, Spacing, Sizes, Icons

Note: Fonts uses lazy initialization (cached_property) so CTkFont objects
are only created after the Tk root window exists. Access syntax is identical
to class attributes:  font=Fonts.TITLE
"""

import functools
import customtkinter as ctk


class Colors:
    """Semantic color tokens — all UI hex values must come from here."""

    # Backgrounds (8px gradient scale)
    BG_PRIMARY = "#141414"
    BG_SURFACE = "#1e1e1e"
    BG_CARD    = "#252525"
    BG_INPUT   = "#2b2b2b"
    BG_HOVER   = "#333333"

    # Accent / brand
    ACCENT       = "#3b82f6"   # blue-500
    ACCENT_HOVER = "#2563eb"   # blue-600
    ACCENT_LIGHT = "#60a5fa"   # blue-400

    # Semantic feedback
    SUCCESS        = "#22c55e"   # green-500
    SUCCESS_BG     = "#14291e"   # dark green bg
    SUCCESS_HOVER  = "#16a34a"   # green-600
    WARNING        = "#f59e0b"   # amber-500
    WARNING_BG     = "#2d2410"   # dark amber bg
    WARNING_HOVER  = "#d97706"   # amber-600
    ERROR          = "#ef4444"   # red-500
    ERROR_BG       = "#2d1515"   # dark red bg
    ERROR_HOVER    = "#dc2626"   # red-600
    INFO           = "#3b82f6"   # blue-500
    INFO_BG        = "#1e2940"   # dark blue bg

    # Destructive
    DANGER       = "#ef4444"
    DANGER_HOVER = "#dc2626"

    # Text (WCAG AA contrast compliant)
    TEXT_PRIMARY   = "#f1f5f9"   # slate-100 (14:1 on BG_PRIMARY)
    TEXT_SECONDARY = "#94a3b8"   # slate-400 (7:1 on BG_PRIMARY)
    TEXT_MUTED     = "#64748b"   # slate-500 (4.5:1 on BG_PRIMARY)
    TEXT_DISABLED  = "#4b5563"   # gray-600 (3:1 on BG_PRIMARY)

    # Borders
    BORDER        = "#2e2e2e"
    BORDER_STRONG = "#404040"
    BORDER_ACCENT = "#3b82f6"
    BORDER_HOVER  = "#525252"

    # Status (for status labels / log text)
    STATUS_IDLE     = "#94a3b8"
    STATUS_QUEUED   = "#a855f7"   # purple-500
    STATUS_RUNNING  = "#f59e0b"   # amber-500
    STATUS_DONE     = "#22c55e"   # green-500
    STATUS_ERROR    = "#ef4444"   # red-500
    STATUS_PAUSED   = "#64748b"   # slate-500
    STATUS_CANCELLED = "#6b7280" # gray-500

    # Secondary buttons
    BTN_SECONDARY       = "#374151"   # gray-700
    BTN_SECONDARY_HOVER = "#4b5563"   # gray-600

    # Interactive states
    FOCUS_RING = "#60a5fa"   # blue-400 for focus indicators
    DRAG_OVER  = "#1e3a8a"   # blue-900 for drag-drop target


class _FontRegistry:
    """
    Lazy CTkFont registry.

    Fonts are created on first access so no Tk root window is required at
    import time.  Access syntax is identical to plain class attributes:
        font=Fonts.TITLE
    """

    @functools.cached_property
    def TITLE(self):
        """22 bold — window / app heading"""
        return ctk.CTkFont(size=22, weight="bold")

    @functools.cached_property
    def H1(self):
        """18 bold — tab section heading"""
        return ctk.CTkFont(size=18, weight="bold")

    @functools.cached_property
    def H2(self):
        """15 bold — card / group heading"""
        return ctk.CTkFont(size=15, weight="bold")

    @functools.cached_property
    def LABEL(self):
        """13 normal — form labels, body text"""
        return ctk.CTkFont(size=13)

    @functools.cached_property
    def LABEL_BOLD(self):
        """13 bold — emphasized labels"""
        return ctk.CTkFont(size=13, weight="bold")

    @functools.cached_property
    def SMALL(self):
        """11 normal — helper text, captions"""
        return ctk.CTkFont(size=11)

    @functools.cached_property
    def MONO(self):
        """11 monospace — log output, technical details"""
        return ctk.CTkFont(family="Courier New", size=11)


# Singleton instance — access as Fonts.TITLE, Fonts.H1, etc.
Fonts = _FontRegistry()


class Spacing:
    """8px grid — all padding/margin values must be multiples of 4."""
    XS  = 4
    SM  = 8
    MD  = 16
    LG  = 24
    XL  = 32
    XXL = 48


class Sizes:
    """Standard component dimensions."""
    BTN_HEIGHT_SM = 32
    BTN_HEIGHT_MD = 40
    BTN_HEIGHT_LG = 48
    INPUT_HEIGHT  = 36
    CORNER_SM     = 6
    CORNER_MD     = 8
    CORNER_LG     = 12


class Icons:
    """
    Unicode icon set for consistent UI elements.
    Uses Unicode characters for cross-platform compatibility.
    
    For production, consider replacing with actual icon font or SVG system.
    """
    # Navigation
    DOWNLOAD    = "⬇"
    UPLOAD      = "⬆"
    CONVERT     = "⇄"
    SUBTITLE    = "≡"
    HISTORY     = "◷"
    SETTINGS    = "⚙"
    QUEUE       = "☰"
    
    # Actions
    PLAY        = "▶"
    PAUSE       = "⏸"
    STOP        = "⏹"
    REFRESH     = "↻"
    SEARCH      = "🔍"
    FOLDER      = "📁"
    FILE        = "📄"
    ADD         = "+"
    REMOVE      = "−"
    CLOSE       = "✕"
    CHECK       = "✓"
    CANCEL      = "⏹"
    
    # Status
    SUCCESS     = "✓"
    ERROR       = "✕"
    WARNING     = "⚠"
    INFO        = "ⓘ"
    PENDING     = "⏳"
    RUNNING     = "▶"
    COMPLETED   = "✅"
    FAILED      = "❌"
    QUEUED      = "📋"
    PAUSED      = "⏸"
    CANCELLED   = "⏹"
    
    # Other
    ARROW_RIGHT = "→"
    ARROW_LEFT  = "←"
    ARROW_UP    = "↑"
    ARROW_DOWN  = "↓"
    CHEVRON_RIGHT = "›"
    CHEVRON_LEFT  = "‹"
    EXTERNAL    = "↗"
    LINK        = "🔗"

