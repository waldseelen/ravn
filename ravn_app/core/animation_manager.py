"""
animation_manager — compatibility shim.

AnimationManager is a presentation-layer concern and has been moved to
ravn_app.ui.animation_manager.  This shim re-exports everything from the
new location so that any code that still imports from ravn_app.core.animation_manager
continues to work during the incremental Tauri migration.

TODO(tauri-migration): Once ravn_app/ui/ is retired, delete this shim entirely.
detect_reduced_motion() will be replaced by a frontend implementation that uses
the standard `prefers-reduced-motion` media query / Tauri APIs.
"""

from ravn_app.ui.animation_manager import (  # noqa: F401
    AnimationManager,
    EasingFunction,
    detect_reduced_motion,
    get_animation_manager,
)

__all__ = [
    "AnimationManager",
    "EasingFunction",
    "detect_reduced_motion",
    "get_animation_manager",
]
