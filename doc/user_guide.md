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

All configuration and data files are stored in `~/.config/wowstat/`:

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
| Gundarz | Checkbox | Weekly Gundarz quest |
| Quests | Checkbox | Weekly quests completion |
| Timewalk | Number | Timewalking dungeons (0-5) |
| Notes | Text | Free-form notes |

### Color Coding

Weekly columns use color backgrounds to indicate progress:

- **Green**: Goal met
- **Yellow**: Partial progress
- **Red**: Not started or incomplete

Specific thresholds:
- Delves: Green (8), Blue (4+), Yellow (2-3), Red (<2)
- Timewalk: Green (5), Yellow (1-4), Red (0)

### Data Import

Import character data from WoW addons:

- **File > Import from Altoholic**: Imports from Altoholic addon SavedVariables
- **File > Import from WoW Addon**: Imports from custom WoWStatTracker addon

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
