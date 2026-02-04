# WoWStatTracker 1.2.0 Release Notes

**Release Date:** December 31, 2025

## Overview

Version 1.2.0 is a complete rewrite of WoWStatTracker from Python/GTK to native C with platform-specific GUIs. This delivers a dramatically smaller, faster application with native look and feel on both macOS and Windows.

## Highlights

- **Native Application**: Rewrote entire application in C with Cocoa (macOS) and Win32 (Windows) GUIs
- **Smaller Size**: App bundle reduced from ~50MB (Python) to under 1MB
- **Faster Startup**: Near-instant launch vs multi-second Python initialization
- **Native Theme Support**: Automatic light/dark mode on both platforms

## New Features

### Application
- Native macOS app bundle with Cocoa/AppKit interface
- Native Windows executable with Win32 interface
- Auto/Light/Dark theme switching with system theme detection
- Column sorting with click-to-sort headers
- Persistent column widths and sort order
- In-app notification system with history
- Update checking via GitHub releases API

### Addon Management
- Install Addon: Copy addon directly to WoW AddOns folder
- Uninstall Addon: Remove addon from WoW AddOns folder
- Set WoW Location: Configure WoW installation path
- Auto-import on window focus (optional)

### Installers
- macOS: Styled DMG with WoW-themed background and drag-to-install
- Windows: NSIS installer with component options (app, addon, start menu, desktop shortcut)

### Weekly Reset Handling
- Addon stamps exported data with week_id based on WoW's Tuesday 15:00 UTC reset
- GUI detects week_id mismatch and resets weekly fields (delves, vault, timewalk, etc.)
- Prevents stale weekly data from persisting across resets

## Bug Fixes

- Fixed vault_visited not detecting when player claims token rewards (vs gear)
- Fixed import not updating fields when addon reports value of 0
- Fixed various memory management issues in macOS Cocoa code
- Fixed Windows ListView cell coloring for dark mode
- Fixed Windows file save operations (atomic writes with temp files)

## Technical Improvements

- 112 unit tests covering all core modules
- Strict compiler warnings enabled (-Wall -Werror -pedantic on macOS, /W4 /WX on Windows)
- Static analysis with cppcheck and clang-tidy
- Platform abstraction layer for cross-platform code
- Embedded Lua 5.1 for parsing WoW SavedVariables files
- cJSON library for JSON persistence

## Breaking Changes

- Python/GTK version is no longer supported
- Configuration file location unchanged but format simplified
- Requires macOS 10.13+ or Windows 10+

## Addon Changes

- Updated timewalking quest IDs for The War Within expansion
- Fixed vault detection logic for token rewards
- Improved data collection reliability

## File Locations

Configuration and data files are stored in platform-specific locations:
- **macOS**: `~/Library/Application Support/WoWStatTracker/`
- **Windows**: `%APPDATA%\WoWStatTracker\`

Files:
- `wowstat_data.json` - Character data
- `wowstat_config.json` - Application settings
- `notifications.json` - Notification history

## Download

- **macOS**: WoWStatTracker-1.2.0-macOS.dmg
- **Windows**: WoWStatTracker-1.2.0-Setup.exe (when available)
