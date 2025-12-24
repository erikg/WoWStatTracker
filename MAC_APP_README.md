# WoW Stat Tracker - Mac App

A standalone Mac application for tracking World of Warcraft character statistics and weekly progress.

## Features

- **Dark/Light Mode Support**: Automatically follows system theme or manual selection
- **Character Management**: Add, edit, and track multiple characters
- **Weekly Progress Tracking**: Vault visits, delves, quests, timewalking, and more
- **WoW Addon Integration**: Import character data from WoWStatTracker addon
- **Native Mac App**: Proper Mac integration with app bundle, icon, and system theming

## Installation

### Option 1: Pre-built App (Recommended)
1. Download the `WoWStatTracker.app` from the `dist/` folder
2. Run the installation script:
   ```bash
   ./mac/install_mac_app.sh
   ```
3. The app will be installed to your Applications folder

### Option 2: Build from Source
1. Ensure you have the required dependencies:
   ```bash
   brew install pygobject3 gtk+3
   pipx install pyinstaller
   ```
2. Build the app:
   ```bash
   ./mac/build_mac_app.sh
   ```
3. Install the built app:
   ```bash
   ./mac/install_mac_app.sh
   ```

## System Requirements

- macOS 10.14 (Mojave) or later
- GTK+3 and PyGObject (installed via Homebrew)

## Dependencies

The app bundle includes all necessary Python dependencies, but requires system-level GTK libraries:

```bash
brew install pygobject3 gtk+3
```

## Usage

1. Launch the app from Applications or Spotlight
2. Add your characters using the "Add Character" button
3. Track weekly progress by clicking on the colored cells
4. Double-click any row to edit character details
5. Use "Import from WoW Addon" to import addon data
6. Change theme using the View menu

## File Locations

The app stores data in `~/Library/Application Support/wowstat/`:
- `wowstat_data.json` - Character data
- `wowstat_config.json` - App settings and preferences

## Troubleshooting

### App Won't Launch
- Ensure GTK dependencies are installed: `brew install pygobject3 gtk+3`
- Check macOS security settings (System Preferences > Security & Privacy)
- Try running from Terminal to see error messages

### "ModuleNotFoundError: No module named 'gi'" Error
This has been fixed in the latest build. If you encounter this error:
1. Ensure you have the latest version of the app
2. Rebuild using the updated build script: `./mac/build_mac_app.sh`
3. The app now includes all necessary GTK libraries in the bundle

### "App is damaged" Message
This can happen due to macOS Gatekeeper. To fix:
```bash
sudo xattr -rd com.apple.quarantine /Applications/WoWStatTracker.app
```

### Theme Issues
- The app automatically detects system dark/light mode
- You can manually override in the theme dropdown
- Restart the app if theme changes don't apply immediately

## Development

### Building
```bash
# Install dependencies
pipx install pyinstaller
brew install pygobject3 gtk+3

# Build the app
./mac/build_mac_app.sh

# Install locally
./mac/install_mac_app.sh
```

### Project Structure
- `src/` - GUI source code
  - `wowstat.py` - Main application entry point
  - `model.py` - Data model and business logic
  - `view.py` - UI components
- `mac/` - macOS build files
  - `WoWStatTracker.spec` - PyInstaller configuration
  - `build_mac_app.sh` - Build script
  - `install_mac_app.sh` - Installation script
  - `create_dmg.sh` - DMG creation script
  - `icon.icns` - App icon
- `WoWStatTracker_Addon/` - WoW addon for data collection
- `test/` - Test suite

## License

Open source - feel free to modify and distribute.

## Support

For issues and feature requests, please check the main project repository or create an issue.