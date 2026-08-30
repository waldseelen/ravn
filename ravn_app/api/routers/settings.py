"""
ravn_app/api/routers/settings.py — Application configuration endpoints.

Reads and writes user settings through ConfigManager.  The backend stores
settings as a flat JSON dict; this router exposes them as-is without
adding any opinion about their structure.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ravn_app import __version__
from ravn_app.api.deps import ConfigDep
from ravn_app.core import tool_installer
from ravn_app.core.tool_health import get_tool_health_checker
from ravn_app.core.update_manager import UpdateManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsPatchRequest(BaseModel):
    """Partial settings update — only provided keys are changed."""
    data: Dict[str, Any]


class InstallToolsRequest(BaseModel):
    """List of tool names to install."""
    tools: Optional[List[str]] = Field(None, description="Specific tools to install (default: all missing)")


class ExportSettingsRequest(BaseModel):
    output_file: Optional[str] = Field(None, description="Target export file path")


class ImportSettingsRequest(BaseModel):
    file_path: Optional[str] = Field(None, description="Source import file path")
    data: Optional[Dict[str, Any]] = Field(None, description="Direct settings payload to import")


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


@router.get("/updates/check", summary="Check for application updates on GitHub")
def check_updates() -> Dict[str, Any]:
    """Check GitHub releases for updates to ravn."""
    try:
        manager = UpdateManager(current_version=__version__)
        release = manager.get_latest_release()
        if not release:
            return {
                "current_version": __version__,
                "has_update": False,
                "latest_version": __version__,
                "status": "up_to_date",
                "message": "No update found or unable to check GitHub.",
            }

        has_update = manager._is_newer_version(release.version)
        return {
            "current_version": __version__,
            "has_update": has_update,
            "latest_version": release.version,
            "release_name": release.name,
            "release_tag": release.tag,
            "body": release.body,
            "download_url": release.download_url,
            "file_size": release.file_size,
            "published_at": release.published_at,
            "status": "update_available" if has_update else "up_to_date",
        }
    except Exception as e:
        logger.error("Failed to check for updates: %s", e)
        return {
            "current_version": __version__,
            "has_update": False,
            "latest_version": __version__,
            "status": "error",
            "message": str(e),
        }


@router.post("/tools/install", summary="Install missing dependencies via winget / system package manager")
def install_tools(body: InstallToolsRequest) -> Dict[str, Any]:
    """Trigger background installation of missing external tools."""
    checker = get_tool_health_checker()
    checker.clear_cache()
    summary = checker.get_health_summary()

    targets = body.tools or (summary["missing_required"] + summary["missing_optional"])
    if not targets:
        return {"success": True, "message": "All tools are already installed.", "results": {}}

    if not tool_installer.is_install_supported():
        return {
            "success": False,
            "message": "Automatic installation is not supported on this platform.",
            "is_supported": False,
        }

    results = tool_installer.install_missing_tools(targets)
    checker.clear_cache()
    return {
        "success": True,
        "results": {
            name: {
                "success": outcome.success,
                "tool": outcome.tool,
                "package_id": outcome.package_id,
                "message": outcome.message,
                "manual_command": outcome.manual_command,
            }
            for name, outcome in results.items()
        },
    }


@router.post("/export", summary="Export settings configuration to JSON file")
def export_settings(body: ExportSettingsRequest, config: ConfigDep) -> Dict[str, Any]:
    """Export current settings to a JSON file."""
    out_path = body.output_file
    if not out_path:
        out_dir = Path.home() / "Downloads" / "RAVN"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = str(out_dir / "ravn_settings_export.json")

    try:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(config.config, f, indent=2, ensure_ascii=False)
        return {"success": True, "output_file": str(p)}
    except Exception as e:
        logger.error("Failed to export settings: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/import", summary="Import settings configuration from JSON file or payload")
def import_settings(body: ImportSettingsRequest, config: ConfigDep) -> Dict[str, Any]:
    """Import settings and save."""
    imported_data: Dict[str, Any] = {}
    if body.data:
        imported_data = body.data
    elif body.file_path:
        p = Path(body.file_path)
        if not p.exists():
            raise HTTPException(status_code=400, detail=f"File not found: {body.file_path}")
        try:
            with open(p, "r", encoding="utf-8") as f:
                imported_data = json.load(f)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON file: {e}") from e
    else:
        raise HTTPException(status_code=400, detail="Either file_path or data must be provided")

    if not isinstance(imported_data, dict):
        raise HTTPException(status_code=400, detail="Settings payload must be a JSON object")

    for k, v in imported_data.items():
        config.config[k] = v
    config.save_config()
    return {"success": True, "config": config.config}

