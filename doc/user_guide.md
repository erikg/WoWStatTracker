# User Guide

## Overview

WoW Stat Tracker is a desktop application for tracking World of Warcraft character statistics, gear progression, and weekly activities.

## Installation

### macOS App Bundle

1. Download or build `WoWStatTracker.app`
2. Copy to `/Applications/` or run directly
3. On first run, macOS may require you to allow the app in Security & Privacy settings

### Running from Source

```bash
# Install dependencies
brew install gtk+3 gobject-introspection
pip install PyGObject

# Run the application
python3 wowstat.py
```

## Configuration

Configuration and data files are stored in platform-specific locations:

- **macOS**: `~/Library/Application Support/wowstat/`
- **Linux**: `~/.config/wowstat/` (or `$XDG_CONFIG_HOME/wowstat/`)
- **Windows**: `%APPDATA%/wowstat/`

Files:
- `wowstat_data.json` - Character data
- `wowstat_config.json` - Window position, column widths, theme preference

## Features

### Character Management

- **Add Character**: File menu > Add Character (or use the menu)
- **Edit Character**: Double-click any row in the table
- **Delete Character**: Double-click to edit, then click Delete (confirmation required)

### Tracking Columns

| Column | Type | Description |
|--------|------|-------------|
| Realm | Text | Character's server |
| Name | Text | Character name |
| Guild | Text | Guild name |
| Item Level | Number | Average item level |
| Heroic Items | Number | Count of heroic-tier gear |
| Champion Items | Number | Count of champion-tier gear |
| Veteran Items | Number | Count of veteran-tier gear |
| Adventure Items | Number | Count of adventure-tier gear |
| Old Items | Number | Count of outdated gear |
| Vault Visited | Checkbox | Weekly Great Vault completion |
| Delves | Number | Weekly delves completed (0-8) |
| Gilded | Number | Gilded stash keys collected (0-3) |
| Gundarz | Checkbox | Weekly Gundarz quest |
| Quests | Checkbox | Weekly quests completion |
| Timewalk | Number | Timewalking dungeons (0-5) |
| Notes | Text | Free-form notes |

### Color Coding

Weekly columns use color backgrounds to indicate progress:

- **Green**: Goal met
- **Yellow**: Partial progress
- **Red**: Needs attention

Specific thresholds:
- Delves: Green (4+), Yellow (1-3), Default (0)
- Gilded Stash: Green (3), Yellow (1-2), Red (0)
- Timewalk: Green (5), Yellow (1-4), Default (0)
- Vault Visited: Green (visited), Red (not visited but weeklies done)

### Data Import

Import character data from the WoWStatTracker addon:

- **File > Import from WoW Addon**: Imports from WoWStatTracker addon SavedVariables

### Weekly Reset

**File > Reset Weekly Data** clears all weekly progress columns (Vault, Delves, Gundarz, Quests, Timewalk) for all characters.

### Themes

**View > Theme** allows switching between:
- Auto (follows system preference)
- Light
- Dark

## Keyboard Shortcuts

- Double-click row: Edit character
- Click column header: Sort by column
- Drag column edges: Resize columns
