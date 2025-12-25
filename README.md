# WoW Character Stat Tracker

A GUI application for tracking World of Warcraft character statistics including gear and weekly progress.

## Features

- Track character realm, name, item level, and gear counts
- Import character data directly from the WoW addon
- Weekly progress tracking for vault visits, delves, gilded stash, Gearing Up for Trouble, quests, and timewalk
- Visual indicators with color-coded backgrounds for weekly activities
- Status bar notifications with auto-dismiss and history
- Auto-import when window is focused (optional)
- Customizable toolbar (icons, text, both, or hidden)
- Light/dark theme support with system auto-detection
- Persistent data storage in JSON format

## Menu Structure

- **File**: Properties, Quit
- **Characters**: Add Character, Reset Weekly Data
- **Addon**: Import from Addon, Set WoW Location, Install Addon, Uninstall Addon
- **View**: Theme selection

## Requirements

- Python 3.6+
- GTK+ 3.0
- PyGObject (GI Python bindings for GTK)
- slpp (Lua table parser)

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
- **Static columns**: Realm, Name, Guild, Item Level, Heroic/Champion/Veteran/Adventure/Old Items
- **Weekly columns**: Vault Visited, Delves, Gilded Stash, Gearing Up, Quests, Timewalk, Notes

Double-click any row to edit character data. Use Characters → Add Character to create new entries and Characters → Reset Weekly Data to clear weekly progress.

### Properties Dialog (File → Properties)

- **Game Location**: Set your WoW installation path
- **Theme**: Auto (system), Light, or Dark
- **Toolbar**: Icons and Text, Icons Only, Text Only, or Hidden
- **Auto-import**: Automatically import from addon when window gains focus

Data is automatically saved to the user's config directory (`~/Library/Application Support/wowstat/` on macOS).

## License

BSD 3-Clause License. See [LICENSE](LICENSE) for details.