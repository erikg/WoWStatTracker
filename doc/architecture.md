# Architecture

## Overview

WoW Stat Tracker is a single-file GTK3 application written in Python. It uses a simple MVC-like pattern where the `WoWStatTracker` class manages both the UI and data.

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
    "item_level": 480,
    "heroic_items": 5,
    "champion_items": 3,
    "veteran_items": 2,
    "adventure_items": 1,
    "old_items": 0,
    "vault_visited": true,
    "delves": 4,
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

## Key Methods

### Lifecycle

- `__init__()`: Initialize application, load data, create UI
- `on_destroy()`: Save state, cleanup, quit

### Data Operations

- `load_data()` / `save_data()`: Character data persistence
- `load_config()` / `save_config()`: Configuration persistence
- `_migrate_old_files()`: Migrate from old file locations

### UI Operations

- `setup_ui()`: Create menu bar and table
- `populate_table()`: Fill TreeView with character data
- `add_character()` / `edit_character()`: Character dialogs
- `cell_data_func()`: Color coding for weekly columns

### Import Functions

- `find_altoholic_data()`: Locate Altoholic SavedVariables
- `parse_altoholic_data()`: Parse Lua SavedVariables format
- `update_from_altoholic()`: Import workflow
- `merge_datastore_data()`: Merge multiple DataStore files

## Threading

The application uses threading for:

- **Config debouncing**: Window resize/move events are debounced with a 500ms timer to prevent excessive disk I/O
- **Geometry caching**: Window geometry is cached immediately but saved asynchronously

## Single Instance

A lock file (`wowstat.lock`) prevents multiple instances from running simultaneously:

- `acquire_lock()`: Create lock file with PID
- `release_lock()`: Remove lock file on exit

## Theme System

Themes are managed through GTK settings:

- `setup_theme_system()`: Initialize theme from config
- `set_theme()`: Apply theme preference
- `detect_system_theme()`: Query OS for dark mode preference
