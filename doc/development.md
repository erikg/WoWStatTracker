# Development Guide

## Prerequisites

- Python 3.8+
- GTK+ 3.0
- PyGObject

### macOS Setup

```bash
brew install gtk+3 gobject-introspection pkg-config
pip install PyGObject pytest pytest-cov black
```

### Linux Setup

```bash
sudo apt install libgirepository1.0-dev gcc libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
pip install PyGObject pytest pytest-cov black
```

## Project Structure

```
wowstat/
├── wowstat.py           # Main application controller
├── model.py             # Data structures and persistence
├── view.py              # GTK UI components
├── icon.icns            # macOS app icon
├── WoWStatTracker.spec  # PyInstaller spec file
├── build_mac_app.sh     # macOS build script
├── Makefile             # Build/test automation
├── doc/                 # Documentation
│   ├── README.md
│   ├── user_guide.md
│   ├── development.md
│   └── architecture.md
└── test/                # Test suite
    ├── __init__.py
    ├── conftest.py
    ├── test_model.py
    └── test_wowstat.py
```

## Development Workflow

### Running the Application

```bash
python3 wowstat.py
```

### Running Tests

```bash
make test          # Run tests with coverage
make test-quick    # Run tests without coverage
```

### Code Formatting

```bash
make format        # Format code with black
make lint          # Check formatting without changing files
```

### Building the macOS App

```bash
make build         # Build macOS .app bundle
```

### Clean Build Artifacts

```bash
make clean         # Remove build artifacts
```

## Code Style

- Code is formatted with [black](https://github.com/psf/black)
- Line length: 88 characters (black default)
- Run `make format` before committing

## Testing

Tests are located in `test/` and use pytest.

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=model --cov=wowstat --cov-report=html

# Run specific test
pytest test/test_wowstat.py::test_function_name
```

Coverage reports are generated in `htmlcov/`.

## Configuration Files

The application stores data in platform-specific locations:

- **macOS**: `~/Library/Application Support/wowstat/`
- **Linux**: `~/.config/wowstat/` (or `$XDG_CONFIG_HOME/wowstat/`)
- **Windows**: `%APPDATA%/wowstat/`

Files:
- `wowstat_data.json` - Character data array
- `wowstat_config.json` - UI configuration (window size, column widths, theme)
- `wowstat.lock` - Single-instance lock file

## Building for Distribution

### macOS

```bash
make build
```

This creates `dist/WoWStatTracker.app` using PyInstaller.

To install:
```bash
cp -r dist/WoWStatTracker.app /Applications/
```
