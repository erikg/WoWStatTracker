# WoW Stat Tracker

Native C implementation of WoW Stat Tracker with platform-specific GUIs:
- **macOS**: Cocoa/AppKit (Objective-C)
- **Windows**: Win32 API (C)

## Features

- Track character realm, name, item level, and gear counts
- Import character data directly from the WoW addon
- Weekly progress tracking for vault visits, delves, gilded stash, Gearing Up for Trouble, quests, and timewalk
- Visual indicators with color-coded backgrounds for weekly activities
- Status bar notifications with auto-dismiss and history
- Auto-import when window is focused (optional)
- Light/dark theme support with system auto-detection
- Persistent data storage in JSON format

## Directory Structure

```
├── CMakeLists.txt          # Main build configuration
├── deps/
│   ├── cjson/              # JSON parsing (MIT license)
│   └── lua-5.1/            # Lua parser for SavedVariables (MIT license)
├── src/
│   ├── core/               # Platform-agnostic C library
│   │   ├── character.c/h   # Character data model
│   │   ├── character_store.c/h  # CRUD operations, JSON persistence
│   │   ├── config.c/h      # Key-value configuration
│   │   ├── lua_parser.c/h  # Parse WoW SavedVariables
│   │   ├── notification.c/h # Notification system
│   │   ├── paths.c/h       # Platform config directories
│   │   ├── week_id.c/h     # WoW weekly reset calculation
│   │   ├── util.c/h        # String/memory helpers
│   │   └── version.h.in    # Version template (CMake generates version.h)
│   ├── platform/
│   │   ├── platform.h      # Abstract platform interface
│   │   ├── macos/          # macOS: theme, HTTP, file locking
│   │   └── windows/        # Windows: theme, HTTP, file locking
│   └── gui/
│       ├── macos/          # Cocoa/AppKit GUI
│       └── windows/        # Win32 GUI
├── test/                   # Unity test framework
├── packaging/
│   ├── macos/              # DMG creation, Info.plist
│   └── windows/            # ZIP/MSI packaging
└── WoWStatTracker_Addon/   # WoW addon for data collection
```

## Building

### Prerequisites

**macOS:**
- Xcode Command Line Tools: `xcode-select --install`
- CMake 3.20+: `brew install cmake`

**Windows:**
- Visual Studio 2022 with C++ workload
- CMake 3.20+ (included with VS or install separately)

### Build Commands

**macOS (Release):**
```bash
mkdir build-macos-Release
cd build-macos-Release
cmake .. -DCMAKE_BUILD_TYPE=Release -DWST_BUILD_PLATFORM=ON -DWST_BUILD_GUI=ON
cmake --build .
```

**Windows (Release, from Developer Command Prompt):**
```batch
mkdir build-windows-Release
cd build-windows-Release
cmake .. -G "Visual Studio 17 2022" -DWST_BUILD_PLATFORM=ON -DWST_BUILD_GUI=ON
cmake --build . --config Release
```

### Build Options

| Option | Default | Description |
|--------|---------|-------------|
| `WST_BUILD_TESTS` | ON | Build unit tests |
| `WST_BUILD_PLATFORM` | OFF | Build platform abstraction layer |
| `WST_BUILD_GUI` | OFF | Build GUI application (requires platform) |
| `WST_ENABLE_LTO` | ON | Enable Link Time Optimization |

## Testing

```bash
# Configure with tests enabled
mkdir build-test
cd build-test
cmake .. -DWST_BUILD_TESTS=ON -DWST_BUILD_PLATFORM=ON

# Build and run tests
cmake --build . --target wst_tests
./test/wst_tests
```

## Version Management

Version is defined in a single location (`CMakeLists.txt`) and automatically propagated:

```cmake
project(WoWStatTracker VERSION 1.2.0 LANGUAGES C)
```

CMake generates:
- `generated/version.h` - C header with version macros
- `VERSION` - Plain text file for packaging scripts

## Packaging

**macOS DMG:**
```bash
cd build-macos-Release
../packaging/macos/create_dmg.sh
```

**Windows ZIP:**
```batch
cd build-windows-Release
..\packaging\windows\package.bat
```

## Dependencies

All dependencies are embedded (no external package managers required):

| Library | Version | License | Purpose |
|---------|---------|---------|---------|
| cJSON | 1.7.18 | MIT | JSON parsing |
| Lua | 5.1 | MIT | SavedVariables parsing |
| Unity | 2.6.0 | MIT | Unit testing |

## License

BSD 3-Clause License - see [LICENSE](LICENSE)
