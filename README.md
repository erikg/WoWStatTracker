# WoW Character Stat Tracker

A GUI application for tracking World of Warcraft character statistics including gear and weekly progress.

## Features

- Track character realm, name, item level, and gear counts
- Weekly progress tracking for vault visits, delves, Gearing Up for Trouble, quests, and timewalk
- Visual indicators with color-coded backgrounds:
  - **Delves**: Green (4+), Yellow (2-3), Red (<2)
  - **Gearing Up**: Green (completed), Red (not completed)
  - **Quests**: Green (completed), Red (not completed)
  - **Timewalk**: Green (5+), Red (<5)
- Reset button for weekly data
- Persistent data storage in JSON format

## Requirements

- Python 3.6+
- GTK+ 3.0
- PyGObject (GI Python bindings for GTK)

## Installation

A virtual environment is recommended for Python dependencies.

### macOS
```bash
# Install system dependencies
brew install gtk+3 gobject-introspection

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### Ubuntu/Debian
```bash
# Install system dependencies
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

```bash
python3 src/wowstat.py
```

## Interface

The main table displays:
- **Static columns**: Realm, Name, Item Level, Heroic Items, Champion Items, Veteran Items, Adventure Items, Old Items
- **Weekly columns**: Vault Visited, Delves Completed, Gearing Up, Quests, Timewalk

Double-click any row to edit character data. Use "Add Character" to create new entries and "Reset Weekly Data" to clear weekly progress for all characters.

Data is automatically saved to `wowstat_data.json` in the same directory.

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.