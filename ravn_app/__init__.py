"""
RAVN - Media Downloader
YouTube indirici ve medya yönetim aracı
"""

__version__ = "1.0.0"
__author__ = "RAVN Project"

# Avoid importing heavy modules at package import time (UI, network) to prevent side effects
# Users should import specific classes from submodules, e.g. `from ravn_app.ui.main_window import YouTubeDownloaderApp`
__all__ = []

# Configure a minimal logging setup for the package if none is configured by the application
import logging

logger = logging.getLogger("ravn")
if not logger.handlers:
	handler = logging.StreamHandler()
	fmt = logging.Formatter("[RAVN] %(asctime)s - %(levelname)s - %(message)s")
	handler.setFormatter(fmt)
	logger.addHandler(handler)
	logger.setLevel(logging.INFO)
