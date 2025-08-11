# WoW Stat Tracker Addon

A World of Warcraft addon that automatically collects character statistics and exports them for use with the WoW Stat Tracker application.

## Features

- **Automatic Data Collection**: Collects character stats, item levels, and weekly progress
- **Real-time Updates**: Updates data when you change gear, complete quests, or earn achievements
- **Seamless Export**: Exports data in a format compatible with the WoW Stat Tracker application
- **Minimal Impact**: Lightweight addon with minimal performance impact
- **Cross-Character Support**: Tracks all characters on your account

## Installation

1. **Download the Addon**:
   - Copy the `WoWStatTracker_Addon` folder to your WoW AddOns directory
   - Location: `World of Warcraft/_retail_/Interface/AddOns/`

2. **Enable the Addon**:
   - Launch World of Warcraft
   - At the character selection screen, click "AddOns"
   - Ensure "WoW Stat Tracker" is checked/enabled
   - Click "Okay"

3. **First Login**:
   - Log in with each character you want to track
   - The addon will automatically start collecting data

## Usage

### Automatic Operation
The addon works automatically once installed:
- Collects data when you log in
- Updates when you change equipment
- Tracks quest completions and achievements
- Updates every 5 minutes while playing

### Manual Commands
- `/wst` or `/wowstat` - Show available commands
- `/wst update` - Force immediate data update
- `/wst export` - Export data for the stat tracker app
- `/wst status` - Show addon status and statistics
- `/wst debug` - Toggle debug mode for troubleshooting

### Minimap Button
- **Left Click**: Force data update
- **Right Click**: Show status information

## Integration with Stat Tracker App

1. **In-Game**: Use `/wst export` to export your data
2. **In App**: Click "Update from WoW Addon" button
3. **Automatic Sync**: The app will import all your character data

### Data Collected

The addon automatically tracks:
- **Character Info**: Name, realm, guild, class, level
- **Equipment**: Average item level and gear quality counts
- **Weekly Progress**: 
  - Great Vault visits
  - Delves completed
  - World boss kills (Gundarg, etc.)
  - Weekly quests
  - Timewalking dungeons
- **Timestamps**: Last login, last update

## Configuration

The addon includes a simple configuration panel accessible via slash commands:
- Auto-update settings
- Debug mode toggle
- Export preferences

## File Locations

The addon stores data in:
- `WoW/_retail_/WTF/Account/[ACCOUNT]/SavedVariables/WoWStatTracker.lua`

This file contains all your character data and can be read by the stat tracker application.

## Troubleshooting

### Addon Not Loading
- Ensure the folder is named exactly `WoWStatTracker_Addon`
- Check that it's in the correct AddOns directory
- Verify it's enabled in the AddOns menu

### No Data Being Collected
- Log in with each character at least once
- Check if the addon is enabled for that character
- Use `/wst debug` to enable debug messages
- Try `/wst update` to force a manual update

### Stat Tracker App Can't Find Data
- Run `/wst export` in-game first
- Check that the SavedVariables file exists
- Ensure the app is looking in the correct WoW directory
- Try running the app as administrator (Windows) if needed

### Missing Weekly Progress Data
Some weekly progress tracking requires specific game events:
- Vault visits: Detected automatically when available
- Delves: Currently requires manual tracking
- World bosses: Based on quest completion
- Weekly quests: Tracked via achievement system

## Technical Details

### Event Handling
The addon responds to these WoW events:
- `PLAYER_EQUIPMENT_CHANGED` - Gear updates
- `QUEST_TURNED_IN` - Quest completion
- `ACHIEVEMENT_EARNED` - Achievement progress
- `ENCOUNTER_END` - Dungeon/raid completion
- `PLAYER_LOGIN` - Character login

### Data Format
Data is exported in JSON-compatible Lua tables that can be parsed by the Python application.

### Performance
- Minimal memory usage (< 1MB)
- Updates are throttled to prevent spam
- Only active during relevant game events

## Support

For issues or feature requests:
1. Enable debug mode: `/wst debug`
2. Check the error messages in chat
3. Report issues with debug information

## Version History

**v1.0.0**
- Initial release
- Automatic character data collection
- Weekly progress tracking
- Integration with stat tracker app
- Minimap button and slash commands