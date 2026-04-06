"""
RAVN - Tool Health and Status Model
Shared tool-health checking for FFmpeg, FFprobe, yt-dlp, and aria2c.
"""

import subprocess
import shutil
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ravn_app.core.runners.base import get_hidden_subprocess_kwargs

logger = logging.getLogger(__name__)


class ToolStatus(Enum):
    """Tool availability status"""
    AVAILABLE = "available"
    MISSING = "missing"
    OUTDATED = "outdated"
    ERROR = "error"


@dataclass
class ToolInfo:
    """Information about a specific tool"""
    name: str
    status: ToolStatus
    path: Optional[str] = None
    version: Optional[str] = None
    error_message: Optional[str] = None
    required: bool = True
    affected_features: List[str] = field(default_factory=list)


class ToolHealthChecker:
    """Check health and availability of external tools"""
    
    # Define tool requirements and affected features
    TOOL_REQUIREMENTS = {
        'ffmpeg': {
            'required': True,
            'affected_features': [
                'video_conversion',
                'audio_extraction',
                'format_conversion',
                'subtitle_embedding',
                'filters',
                'mixer',
                'utilities',
                'post_download_processing'
            ]
        },
        'ffprobe': {
            'required': True,
            'affected_features': [
                'media_info',
                'metadata_extraction',
                'format_detection',
                'library_indexing'
            ]
        },
        'yt-dlp': {
            'required': True,
            'affected_features': [
                'url_download',
                'playlist_download',
                'metadata_fetch',
                'subtitle_download'
            ]
        },
        'aria2c': {
            'required': False,
            'affected_features': [
                'torrent_download',
                'magnet_download',
                'torrent_streaming'
            ]
        }
    }
    
    def __init__(self):
        self._cache: Dict[str, ToolInfo] = {}
    
    def check_tool(self, tool_name: str, use_cache: bool = True) -> ToolInfo:
        """
        Check if a tool is available and get its info.
        
        Args:
            tool_name: Name of the tool (ffmpeg, ffprobe, yt-dlp, aria2c)
            use_cache: Use cached result if available
            
        Returns:
            ToolInfo object with tool status and details
        """
        if use_cache and tool_name in self._cache:
            return self._cache[tool_name]
        
        requirements = self.TOOL_REQUIREMENTS.get(tool_name, {})
        required = requirements.get('required', False)
        affected_features = requirements.get('affected_features', [])
        
        # Check if tool is in PATH
        tool_path = shutil.which(tool_name)
        
        if not tool_path:
            info = ToolInfo(
                name=tool_name,
                status=ToolStatus.MISSING,
                required=required,
                affected_features=affected_features,
                error_message=f"{tool_name} not found in PATH"
            )
            self._cache[tool_name] = info
            return info
        
        # Get version information
        version = self._get_tool_version(tool_name, tool_path)
        
        info = ToolInfo(
            name=tool_name,
            status=ToolStatus.AVAILABLE,
            path=tool_path,
            version=version,
            required=required,
            affected_features=affected_features
        )
        
        self._cache[tool_name] = info
        return info
    
    def _get_tool_version(self, tool_name: str, tool_path: str) -> Optional[str]:
        """Get version string for a tool"""
        try:
            # Different tools use different version flags
            if tool_name == 'aria2c':
                result = subprocess.run(
                    [tool_path, '--version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    **get_hidden_subprocess_kwargs(),
                )
            else:
                result = subprocess.run(
                    [tool_path, '-version'],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    **get_hidden_subprocess_kwargs(),
                )
            
            if result.returncode == 0:
                # Extract first line which usually contains version
                first_line = result.stdout.split('\n')[0]
                return first_line.strip()
            else:
                return None
                
        except Exception as e:
            logger.debug(f"Failed to get version for {tool_name}: {e}")
            return None
    
    def check_all_tools(self, use_cache: bool = True) -> Dict[str, ToolInfo]:
        """
        Check all required and optional tools.
        
        Returns:
            Dictionary mapping tool names to ToolInfo objects
        """
        results = {}
        for tool_name in self.TOOL_REQUIREMENTS.keys():
            results[tool_name] = self.check_tool(tool_name, use_cache=use_cache)
        return results
    
    def get_missing_required_tools(self) -> List[str]:
        """Get list of missing required tools"""
        all_tools = self.check_all_tools()
        return [
            name for name, info in all_tools.items()
            if info.required and info.status == ToolStatus.MISSING
        ]
    
    def get_missing_optional_tools(self) -> List[str]:
        """Get list of missing optional tools"""
        all_tools = self.check_all_tools()
        return [
            name for name, info in all_tools.items()
            if not info.required and info.status == ToolStatus.MISSING
        ]
    
    def get_affected_features(self, tool_name: str) -> List[str]:
        """Get list of features affected by a tool"""
        return self.TOOL_REQUIREMENTS.get(tool_name, {}).get('affected_features', [])
    
    def is_feature_available(self, feature: str) -> bool:
        """
        Check if a feature is available (all required tools present).
        
        Args:
            feature: Feature name (e.g., 'torrent_download', 'video_conversion')
            
        Returns:
            True if all required tools for the feature are available
        """
        all_tools = self.check_all_tools()
        
        # Find which tools affect this feature
        required_tools = [
            tool_name for tool_name, requirements in self.TOOL_REQUIREMENTS.items()
            if feature in requirements.get('affected_features', [])
        ]
        
        # Check if all required tools are available
        for tool_name in required_tools:
            tool_info = all_tools.get(tool_name)
            if not tool_info or tool_info.status == ToolStatus.MISSING:
                return False
        
        return True
    
    def get_health_summary(self) -> Dict[str, any]:
        """
        Get overall health summary.
        
        Returns:
            Dictionary with health status information
        """
        all_tools = self.check_all_tools()
        missing_required = self.get_missing_required_tools()
        missing_optional = self.get_missing_optional_tools()
        
        # Determine overall status
        if missing_required:
            overall_status = "critical"
        elif missing_optional:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        # Collect unavailable features
        unavailable_features = set()
        for tool_name, tool_info in all_tools.items():
            if tool_info.status == ToolStatus.MISSING:
                unavailable_features.update(tool_info.affected_features)
        
        return {
            'overall_status': overall_status,
            'total_tools': len(all_tools),
            'available_tools': sum(1 for t in all_tools.values() if t.status == ToolStatus.AVAILABLE),
            'missing_required': missing_required,
            'missing_optional': missing_optional,
            'unavailable_features': sorted(list(unavailable_features)),
            'tools': all_tools
        }
    
    def clear_cache(self):
        """Clear the tool info cache"""
        self._cache.clear()


# Global instance
_health_checker = None


def get_tool_health_checker() -> ToolHealthChecker:
    """Get the global tool health checker instance"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ToolHealthChecker()
    return _health_checker


def check_tool_availability(tool_name: str) -> bool:
    """
    Quick check if a tool is available.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        True if tool is available
    """
    checker = get_tool_health_checker()
    info = checker.check_tool(tool_name)
    return info.status == ToolStatus.AVAILABLE


def get_missing_tools_message() -> Optional[str]:
    """
    Get user-friendly message about missing tools.
    
    Returns:
        Message string if tools are missing, None if all required tools are present
    """
    checker = get_tool_health_checker()
    summary = checker.get_health_summary()
    
    if not summary['missing_required'] and not summary['missing_optional']:
        return None
    
    messages = []
    
    if summary['missing_required']:
        messages.append(
            f"⚠️  Required tools missing: {', '.join(summary['missing_required'])}"
        )
        messages.append(
            "The application cannot function properly without these tools."
        )
    
    if summary['missing_optional']:
        messages.append(
            f"ℹ️  Optional tools missing: {', '.join(summary['missing_optional'])}"
        )
        messages.append(
            "Some features will be unavailable:"
        )
        
        for tool in summary['missing_optional']:
            features = checker.get_affected_features(tool)
            if features:
                messages.append(f"  • {tool}: {', '.join(features)}")
    
    return '\n'.join(messages)


# Test and validation
if __name__ == "__main__":
    import json
    import sys
    
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    
    checker = ToolHealthChecker()
    summary = checker.get_health_summary()
    
    print("Tool Health Summary:")
    print("=" * 60)
    print(f"Overall Status: {summary['overall_status'].upper()}")
    print(f"Available Tools: {summary['available_tools']}/{summary['total_tools']}")
    print()
    
    if summary['missing_required']:
        print("Missing Required Tools:")
        for tool in summary['missing_required']:
            print(f"  - {tool}")
        print()
    
    if summary['missing_optional']:
        print("Missing Optional Tools:")
        for tool in summary['missing_optional']:
            features = checker.get_affected_features(tool)
            print(f"  - {tool}: affects {', '.join(features)}")
        print()
    
    print("Tool Details:")
    print("-" * 60)
    for tool_name, tool_info in summary['tools'].items():
        status_icon = "[OK]" if tool_info.status == ToolStatus.AVAILABLE else "[MISSING]"
        print(f"{status_icon} {tool_name}:")
        print(f"   Status: {tool_info.status.value}")
        if tool_info.path:
            print(f"   Path: {tool_info.path}")
        if tool_info.version:
            print(f"   Version: {tool_info.version}")
        if tool_info.error_message:
            print(f"   Error: {tool_info.error_message}")
        print(f"   Required: {'Yes' if tool_info.required else 'No'}")
        print(f"   Affects: {', '.join(tool_info.affected_features)}")
        print()
    
    if summary['unavailable_features']:
        print("Unavailable Features:")
        print("-" * 60)
        for feature in summary['unavailable_features']:
            print(f"  - {feature}")
