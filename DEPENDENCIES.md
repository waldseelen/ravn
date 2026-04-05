# RAVN Dependencies

This document provides detailed information about RAVN's dependencies, both required and optional, and the features they enable.

## Overview

RAVN relies on external tools for media processing, downloads, and torrent management. Understanding these dependencies helps you:

- Know which tools are critical for basic operation
- Understand which features require optional tools
- Troubleshoot missing functionality
- Plan installation on new systems

## Required Dependencies

### Python 3.9+

**Purpose:** Runtime environment for RAVN  
**Affected Features:** Entire application  
**Installation:**
- Windows: Download from [python.org](https://python.org)
- macOS: `brew install python` or download from python.org
- Linux: Usually pre-installed, or `sudo apt install python3 python3-pip`

### FFmpeg

**Purpose:** Video and audio processing engine  
**Affected Features:**
- Video conversion
- Audio extraction
- Format conversion
- Subtitle embedding
- Filters
- Mixer
- Utilities
- Post-download processing

**Installation:**
- Windows: `winget install FFmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html)
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

**Verification:**
```bash
ffmpeg -version
```

### FFprobe

**Purpose:** Media file analysis and metadata extraction  
**Affected Features:**
- Media info
- Metadata extraction
- Format detection
- Library indexing

**Installation:**
- Usually bundled with FFmpeg
- Same installation process as FFmpeg

**Verification:**
```bash
ffprobe -version
```

### yt-dlp

**Purpose:** Media download engine  
**Affected Features:**
- URL download
- Playlist download
- Metadata fetch
- Subtitle download

**Installation:**
- Windows: `winget install yt-dlp` or `pip install yt-dlp`
- macOS: `brew install yt-dlp` or `pip install yt-dlp`
- Linux: `sudo apt install yt-dlp` or `pip install yt-dlp`

**Verification:**
```bash
yt-dlp --version
```

**Note:** yt-dlp should be kept up-to-date for best compatibility with video platforms:
```bash
pip install --upgrade yt-dlp
```

## Optional Dependencies

### aria2c

**Purpose:** Torrent and magnet link download engine  
**Affected Features:**
- Torrent download
- Magnet download
- Torrent streaming

**Installation:**
- Windows: `winget install aria2`
- macOS: `brew install aria2`
- Linux: `sudo apt install aria2`

**Verification:**
```bash
aria2c --version
```

**Impact if Missing:**
- Torrent tab will show a warning banner
- Torrent downloads will fail gracefully
- Magnet links cannot be processed
- All other features remain fully functional

### tkinterdnd2 (Python package)

**Purpose:** Drag-and-drop functionality in the UI  
**Affected Features:**
- Drag-and-drop file input in various tabs
- Enhanced UX for file selection

**Installation:**
```bash
pip install tkinterdnd2
```

**Impact if Missing:**
- No drag-and-drop support
- Manual file selection still works via browse buttons
- All other features remain fully functional

## Python Package Dependencies

All required Python packages are listed in `requirements.txt`. Install with:

```bash
pip install -r requirements.txt
```

Key packages include:
- `customtkinter` - Modern UI framework
- `click` - CLI framework
- `yt-dlp` - Download engine (also available as system package)
- Other supporting libraries

## Checking Tool Health

RAVN includes built-in tool health checking:

### Via Desktop UI
1. Open RAVN
2. Navigate to Settings (Ctrl+,)
3. Look for the "Tool Status and Dependencies" section at the top
4. Click "Refresh Status" to re-check all tools

### Via Startup Logs
When RAVN starts, it logs the status of all dependencies:
- **Healthy:** All required and optional tools available
- **Degraded:** Optional tools missing, some features unavailable
- **Critical:** Required tools missing, core features affected

Check the console or log files for detailed messages.

### Via Command Line
Run the tool health checker directly:
```bash
python -m ravn_app.core.tool_health
```

This will display:
- Overall health status
- Status of each tool (available/missing)
- Tool versions and paths
- Affected features for missing tools

## Common Issues

### FFmpeg not found
**Symptom:** Conversion, filters, mixer, and utilities fail  
**Solution:**
1. Install FFmpeg (see Required Dependencies above)
2. Ensure FFmpeg is in your system PATH
3. Restart RAVN
4. Verify in Settings > Tool Status

### yt-dlp not found
**Symptom:** Downloads fail with "yt-dlp not available" error  
**Solution:**
1. Install yt-dlp (see Required Dependencies above)
2. If installed via pip, ensure Python Scripts directory is in PATH
3. Restart RAVN

### aria2c not found
**Symptom:** Torrent tab shows warning banner, torrent downloads fail  
**Solution:**
1. Install aria2c (see Optional Dependencies above)
2. Ensure aria2c is in your system PATH
3. Restart RAVN
4. Verify torrent tab shows no warning

### Tools installed but not detected
**Solution:**
1. Ensure the tool is in your system PATH
2. Try running the tool from command line to verify
3. Restart RAVN
4. Check Settings > Tool Status > Refresh Status
5. If still not detected, check the tool path in Settings

## Feature Matrix

| Feature | FFmpeg | FFprobe | yt-dlp | aria2c |
|---------|--------|---------|--------|--------|
| URL Download | | ✓ | ✓ | |
| Playlist Download | | ✓ | ✓ | |
| Video Conversion | ✓ | | | |
| Audio Extraction | ✓ | | | |
| Subtitle Download | | | ✓ | |
| Subtitle Embedding | ✓ | | | |
| Filters | ✓ | | | |
| Mixer | ✓ | | | |
| Utilities | ✓ | ✓ | | |
| Media Info | | ✓ | | |
| Library Indexing | | ✓ | | |
| Torrent Download | | | | ✓ |
| Magnet Links | | | | ✓ |

## Platform-Specific Notes

### Windows
- Use `winget` package manager when available for consistent installations
- Add tool directories to system PATH if not done automatically
- Some tools may require administrator privileges to install

### macOS
- Homebrew (`brew`) is the recommended package manager
- Xcode Command Line Tools may be required for some tools
- Check PATH in both Terminal and GUI applications

### Linux
- Package names may vary by distribution
- Ubuntu/Debian: Use `apt`
- Fedora/RHEL: Use `dnf` or `yum`
- Arch: Use `pacman`
- Verify tools are in `/usr/bin` or `/usr/local/bin`

## Getting Help

If you encounter dependency issues:

1. Check the tool health status in Settings
2. Review startup logs for detailed error messages
3. Verify each tool works from command line
4. Consult this document for installation instructions
5. Check the main README.md for system requirements
6. File an issue with tool health status output if problems persist

## Updating Dependencies

Keep your tools updated for best compatibility and security:

```bash
# Update Python packages
pip install --upgrade -r requirements.txt

# Update yt-dlp specifically (important for site compatibility)
pip install --upgrade yt-dlp

# Update system tools (examples)
# Windows
winget upgrade ffmpeg
winget upgrade yt-dlp
winget upgrade aria2

# macOS
brew upgrade ffmpeg
brew upgrade yt-dlp
brew upgrade aria2

# Linux (Ubuntu/Debian)
sudo apt update
sudo apt upgrade ffmpeg yt-dlp aria2
```

RAVN will automatically detect updated tool versions when restarted.
