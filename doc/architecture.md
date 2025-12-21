# Architecture

## Overview

WoW Stat Tracker is a GTK3 application written in Python, organized into three main modules:

- **model.py**: Data structures, persistence, and business logic (no GTK dependencies)
- **view.py**: GTK UI components, theming, and display logic
- **wowstat.py**: Main controller that orchestrates model and view

## Main Components

### WoWStatTracker Class

The main application class handles:

- **Initialization**: Config directory setup, file migration, window creation
- **Data Management**: Loading/saving character data and configuration
- **UI Setup**: Menu bar, TreeView table, theme management
- **Event Handling**: User interactions, window events

### Data Storage

#### Character Data (`wowstat_data.json`)

JSON array of character objects:

```json
[
  {
    "realm": "ServerName",
    "name": "CharacterName",
    "guild": "GuildName",
    "item_level": 480.0,
    "heroic_items": 5,
    "champion_items": 3,
    "veteran_items": 2,
    "adventure_items": 1,
    "old_items": 0,
    "vault_visited": true,
    "delves": 4,
    "gilded_stash": 3,
    "gundarz": false,
    "quests": true,
    "timewalk": 0,
    "notes": "Main character"
  }
]
```

#### Configuration (`wowstat_config.json`)

```json
{
  "window": {
    "width": 1200,
    "height": 600,
    "x": 100,
    "y": 100,
    "maximized": false
  },
  "columns": {
    "0": 80,
    "1": 100
  },
  "sort": {
    "column_id": 0,
    "order": 0
  },
  "theme": "auto"
}
```

## Key Classes

### model.py

- **Character**: Dataclass for character data with validation
- **CharacterStore**: CRUD operations and JSON persistence for characters
- **Config**: Application configuration storage
- **LockManager**: Single-instance file locking

### view.py

- **ThemeManager**: GTK theme application and dark/light mode
- **CharacterTable**: TreeView display with color-coded cells
- **CharacterDialog**: Add/edit character form

### wowstat.py

- **WoWStatTracker**: Main controller orchestrating model and view

## Key Functions

### Data Import (wowstat.py)

- `find_wow_addon_data()`: Locate WoWStatTracker addon SavedVariables
- `parse_wow_addon_data()`: Parse addon Lua data format
- `update_from_wow_addon()`: Import workflow from custom addon

### Utilities (model.py)

- `get_config_dir()`: Platform-specific config directory
- `migrate_old_files()`: Migrate from old file locations
- `detect_system_theme()`: Query OS for dark mode preference

## Threading

The application uses threading for:

- **Config debouncing**: Window resize/move events are debounced with a 500ms timer to prevent excessive disk I/O
- **Geometry caching**: Window geometry is cached immediately but saved asynchronously

## Single Instance

The `LockManager` class prevents multiple instances from running simultaneously using a lock file (`wowstat.lock`):

- `acquire()`: Create lock file with PID, uses fcntl on Unix with fallback
- `release()`: Remove lock file on exit

## Theme System

The `ThemeManager` class handles theming:

- Applies GTK dark/light theme based on preference
- Auto mode detects system preference via `detect_system_theme()`
- Custom CSS for consistent styling across themes
