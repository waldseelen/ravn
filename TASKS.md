# RAVN Roadmap

This file tracks the **public-facing roadmap** for RAVN. It is intentionally shorter and cleaner than an internal sprint board.

## Current release focus

RAVN already covers its core product loop. The near-term goal is to make the public release feel as polished as the feature set itself.

### Now
- Final clean-machine validation of the packaged Windows build
- Release trust improvements: signing guidance, checksum verification, and clearer install notes
- Documentation, screenshots, and onboarding polish for first-time users

## What is already solid

- Unified download workflows for URLs, playlists, batches, magnets, and `.torrent` files
- FFmpeg-backed studio tooling for convert, subtitle, filters, mixer, and utilities
- Local library, queue, and history flows across desktop and CLI usage
- Shared runner architecture for the main external-tool execution paths
- Windows packaging pipeline with GitHub Actions build and release automation

## Near-term roadmap

- Keep the Windows packaged build easy to validate on fresh machines
- Continue reducing setup friction around required tools and first-run expectations
- Improve release presentation: demo assets, release notes, and troubleshooting clarity

## Later / exploratory

- Evaluate additional packaged targets beyond Windows when release maintenance cost makes sense
- Expand automation surfaces only where they clearly improve real workflows
- Revisit the experimental extension boundary only if it graduates into a supported product surface

## Scope notes

- **Windows** is the only active packaged-release target today.
- Linux and macOS may work from source, but they are not current distribution priorities.
- The plugin system is experimental and should not be presented as a supported runtime plugin platform.
- The `serve` CLI command is reserved and not part of the current public feature set.
