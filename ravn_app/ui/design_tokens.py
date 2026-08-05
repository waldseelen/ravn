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

    # Backgrounds (Nordic dark theme with kahverengi harmony)
    BG_PRIMARY = ("#F5F0EC", "#141414")   # (light, dark) base
    BG_SURFACE = ("#EDE8E3", "#1E1E1E")   # (light, dark) slightly lighter
    BG_CARD    = ("#E6DFD8", "#252525")   # (light, dark) card background
    BG_INPUT   = ("#DDD6CE", "#2D2D2D")   # (light, dark) input field background
    BG_HOVER   = ("#D8D0C8", "#2A2A2A")   # (light, dark) hover state background

    # Accent / brand (RAVN brass theme — brightened evolution of the Nordic brown)
    # Warmer, higher-energy brass keeps the brand lineage but reads livelier on dark surfaces.
    ACCENT       = "#C99A5B"   # brass-500 (primary brand; on #141414 ≈ 6.9:1, AA)
    ACCENT_HOVER = "#A87C42"   # brass-600 (darker on hover)
    ACCENT_LIGHT = "#D8AC6E"   # brass-400 (lighter accent / active glow)
    ACCENT_BEIGE = "#E0CBB3"   # sand-200 (secondary accent, contrasting)

    # Semantic feedback (all WCAG AA compliant on BG_PRIMARY)
    SUCCESS        = "#22c55e"   # green-500 (8.08:1)
    SUCCESS_BG     = "#14291e"   # dark green bg
    SUCCESS_HOVER  = "#16a34a"   # green-600
    WARNING        = "#f59e0b"   # amber-500 (8.58:1)
    WARNING_BG     = "#2d2410"   # dark amber bg
    WARNING_HOVER  = "#d97706"   # amber-600
    ERROR          = "#ef4444"   # red-500 (4.90:1)
    ERROR_BG       = ("#FDF0F0", "#2D1515")   # (light, dark) red bg
    ERROR_HOVER    = "#dc2626"   # red-600
    INFO           = "#C99A5B"   # brass-500 brand info (AA on dark)
    INFO_BG        = "#2a2320"   # dark brass bg

    # Destructive
    DANGER       = "#ef4444"
    DANGER_HOVER = "#dc2626"

    # Text (WCAG AA contrast compliant: ≥4.5:1 for normal text)
    TEXT_PRIMARY   = ("#1A1210", "#E8E0D8")   # (light, dark) primary text
    TEXT_SECONDARY = ("#4A3D35", "#B8A99A")   # (light, dark) secondary text
    TEXT_MUTED     = ("#7A6B60", "#A09080")   # light/dark — darker bg needs lighter muted text
    TEXT_DISABLED  = "#4b5563"   # gray-600 (intentionally low contrast)

    # Borders
    BORDER        = ("#C4B5A8", "#3A3330")   # (light, dark)
    BORDER_STRONG = ("#A89080", "#5A4A40")   # (light, dark)
    BORDER_ACCENT = "#C99A5B"   # brass for accent borders (WCAG AA)
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
    BTN_SECONDARY       = ("#D4C5B9", "#3A3330")   # (light, dark)
    BTN_SECONDARY_HOVER = ("#C4B0A0", "#4A4340")   # (light, dark)
    BTN_DISABLED        = ("#C8BFB8", "#303030")   # (light, dark) disabled button bg (MIC-07)

    # Interactive states (brass-aligned)
    FOCUS_RING = "#D8AC6E"   # brass-400 for focus indicators (high visibility)
    DRAG_OVER  = ("#EAE0D5", "#2A2218")   # (light, dark) drag-drop target
    HOVER_BEIGE = "#3b332f"  # subtle beige hover tint (POL-03)
    PROGRESS_BG = "#3a312c"  # beige-brown progress track
    PROGRESS_FILL = "#C99A5B"  # brass progress fill
    SUCCESS_FLASH = "#4ade80"  # brief success flash color


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
    def BTN(self):
        """13 bold — legacy button label alias"""
        return self.LABEL_BOLD

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
    """Standard component dimensions (POL-22)."""
    BTN_HEIGHT_SM = 32
    BTN_HEIGHT_MD = 40
    BTN_HEIGHT_LG = 48
    INPUT_HEIGHT  = 36
    # Corner radius: 8px for cards, 6px for buttons/inputs (POL-22)
    CORNER_SM     = 6   # buttons, inputs, small elements
    CORNER_MD     = 8   # cards, panels, containers
    CORNER_LG     = 12  # modals, large containers
    # Focus ring width (POL-23)
    FOCUS_RING_WIDTH = 2
    # Tooltip delay in ms (POL-34)
    TOOLTIP_DELAY = 300


class Motion:
    """Animation duration tokens in milliseconds."""
    FAST = 100
    MICRO = 150
    STANDARD = 200
    SLOW = 300


class Cursors:
    """Cursor tokens for interactive elements (POL-27)."""
    POINTER = "hand2"       # Buttons, links, clickable icons
    TEXT = "xterm"          # Text inputs
    DEFAULT = ""            # Default arrow
    WAIT = "watch"          # Loading state
    NOT_ALLOWED = "circle"  # Disabled elements


class Icons:
    """
    Unicode icon set for consistent UI elements.
    Uses Unicode characters for cross-platform compatibility.
    All icons are carefully selected to avoid emoji (which can render inconsistently).

    For production, consider replacing with actual icon font or SVG system.
    """
    # Primary workspace nav (top tab bar) — one clear glyph per destination
    HOME        = "⌂"   # Home workspace
    STUDIO      = "❖"   # Studio workspace (processing tools)

    # Navigation & Tabs (ICN-01 to ICN-06)
    DOWNLOAD    = "↓"   # Minimalist download (ICN-01)
    UPLOAD      = "↑"
    CONVERT     = "⇄"   # Convert/exchange icon (ICN-02)
    SUBTITLE    = "≡"   # Subtitle/text lines icon (ICN-03)
    HISTORY     = "◷"   # History/clock icon (ICN-04)
    SETTINGS    = "⚙"   # Settings/cog icon (ICN-05)
    QUEUE       = "☰"   # Queue/list icon (ICN-06)
    TORRENT     = "⊕"   # Torrent/magnet icon (ICN-07b)
    MIXER       = "∿"   # Audio/video mixing tab
    FILTERS     = "◫"   # Filters/effects tab
    LIBRARY     = "▦"   # Local media library tab

    # Action Buttons (ICN-07 to ICN-11)
    DOWNLOAD_BTN = "↓"   # Large download button indicator (ICN-07)
    CONVERT_BTN  = "⟳"   # Process/circular arrow icon (ICN-08)
    BROWSE       = "⌂"   # Folder/home icon (ICN-09)
    FOLDER       = "▤"   # Folder icon (minimalist)
    CANCEL_BTN   = "×"   # Cancel/stop button (ICN-10)
    RETRY        = "↻"   # Retry/refresh icon (ICN-11)

    # Status Indicators (ICN-12 to ICN-16)
    QUEUED_STATUS   = "○"   # Queued status - circle outline (ICN-12)
    RUNNING_STATUS  = "◐"   # Running status - spinner frame (ICN-13)
    SPINNER         = "◐"   # Generic spinner alias for loading button text
    SUCCESS_STATUS  = "✓"   # Success status - checkmark (ICN-14)
    ERROR_STATUS    = "×"   # Error status - X (ICN-15)
    PAUSED_STATUS   = "⏸"   # Paused status - pause symbol (ICN-16)

    # Form & Input Icons (ICN-17 to ICN-22)
    LINK_INPUT      = "⚭"   # URL input prefix - link icon (ICN-17)
    QUALITY_SELECT  = "◐"   # Quality selector - video/quality icon (ICN-18)
    FORMAT_SELECT   = "⎚"   # Format selector - file type icon (ICN-19)
    ERROR_INDICATOR = "⚠"   # Error indicator - exclamation (ICN-20)
    SUCCESS_INDICATOR = "✓" # Success indicator - checkmark (ICN-21)
    CLEAR_BTN       = "⌫"   # Clear/Reset button - backspace icon (ICN-22)

    # Actions (General)
    PLAY        = "▶"
    PAUSE       = "⏸"
    STOP        = "⏹"
    REFRESH     = "↻"
    SEARCH      = "⌕"   # Search icon (replaced emoji)
    FILE        = "⎚"   # File icon (replaced emoji)
    ADD         = "+"
    REMOVE      = "−"
    CLOSE       = "×"
    CHECK       = "✓"
    CANCEL      = "×"

    # Status (Legacy compatibility)
    SUCCESS     = "✓"
    ERROR       = "×"
    WARNING     = "⚠"
    INFO        = "ⓘ"
    PENDING     = "⧗"   # Hourglass (replaced emoji)
    RUNNING     = "▶"
    COMPLETED   = "✓"   # Checkmark (replaced emoji)
    FAILED      = "×"   # X (replaced emoji)
    QUEUED      = "☰"   # List (replaced emoji)
    PAUSED      = "⏸"
    CANCELLED   = "×"

    # Empty state (POL-25)
    EMPTY_FOLDER = "▢"  # Empty folder placeholder
    EMPTY_LIST   = "∅"  # Empty list placeholder

    # Other
    ARROW_RIGHT = "→"
    ARROW_LEFT  = "←"
    ARROW_UP    = "↑"
    ARROW_DOWN  = "↓"
    CHEVRON_RIGHT = "›"
    CHEVRON_LEFT  = "‹"
    EXTERNAL    = "↗"
    LINK        = "⚭"   # Link chain (replaced emoji)

