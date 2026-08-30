"""
ravn_app/api/routers/settings.py — Application configuration endpoints.

Reads and writes user settings through ConfigManager.  The backend stores
settings as a flat JSON dict; this router exposes them as-is without
adding any opinion about their structure.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from ravn_app.api.deps import ConfigDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatchRequest(BaseModel):
    """Partial settings update — only provided keys are changed."""
    data: Dict[str, Any]


@router.get("/", summary="Return all current application settings")
def get_settings(config: ConfigDep) -> Dict[str, Any]:
    return config.config


@router.patch("/", summary="Update one or more settings keys")
def patch_settings(body: SettingsPatchRequest, config: ConfigDep) -> Dict[str, Any]:
    """
    Merge the provided keys into the existing config.
    Returns the full updated config.
    """
    for key, value in body.data.items():
        config.config[key] = value
    config.save_config()
    logger.info("Settings updated: keys=%s", list(body.data.keys()))
    return config.config


@router.post("/reset", summary="Reset all settings to application defaults")
def reset_settings(config: ConfigDep) -> Dict[str, Any]:
    config.reset()
    return config.config
