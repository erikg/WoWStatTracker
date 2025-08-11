# WoW Stat Tracker Addon - Installation Guide

## Quick Install

1. **Copy Addon Folder**:
   ```
   Copy: WoWStatTracker_Addon
   To: World of Warcraft/_retail_/Interface/AddOns/
   ```

2. **Enable in WoW**:
   - Launch WoW
   - Character Select → AddOns → Enable "WoW Stat Tracker"

3. **First Use**:
   - Log in with your characters
   - Type `/wst export` in-game
   - In stat tracker app, click "Update from WoW Addon"

## Detailed Installation Steps

### Step 1: Find Your WoW Directory

**Windows:**
- Default: `C:\Program Files (x86)\World of Warcraft\_retail_\`
- Or: `C:\Program Files\World of Warcraft\_retail_\`

**macOS:**
- Default: `/Applications/World of Warcraft/_retail_/`
- Or: `~/Applications/World of Warcraft/_retail_/`

**Linux (Wine/Lutris):**
- Wine: `~/.wine/drive_c/Program Files (x86)/World of Warcraft/_retail_/`
- Lutris: `~/Games/world-of-warcraft/_retail_/`

### Step 2: Copy Addon Files

1. Navigate to your WoW directory
2. Go to `Interface/AddOns/`
3. Copy the entire `WoWStatTracker_Addon` folder here
4. Final path should be:
   ```
   World of Warcraft/_retail_/Interface/AddOns/WoWStatTracker_Addon/
   ```

### Step 3: Verify Installation

The AddOns folder should contain:
```
WoWStatTracker_Addon/
├── WoWStatTracker.toc
├── Core.lua
├── DataCollector.lua
├── EventHandler.lua
├── UI.lua
├── README.md
└── INSTALL.md
```

### Step 4: Enable Addon

1. Launch World of Warcraft
2. At character selection screen, click "AddOns" button
3. Find "WoW Stat Tracker" in the list
4. Check the box to enable it
5. Click "Okay"

### Step 5: First Login

1. Log in with each character you want to track
2. The addon will automatically start collecting data
3. You should see a message: "WoW Stat Tracker addon loaded successfully!"

### Step 6: Export Data

1. Type `/wst export` in chat
2. You should see: "Data exported successfully! X characters exported."
3. The data is now ready for the stat tracker application

## Verification

### Check Addon is Working
- Type `/wst status` to see addon information
- You should see character count and update statistics

### Check Data File Exists
Navigate to:
```
WoW/_retail_/WTF/Account/[YOUR_ACCOUNT]/SavedVariables/WoWStatTracker.lua
```

This file should exist and contain your character data.

### Test Integration
1. In the WoW Stat Tracker app, click "Update from WoW Addon"
2. You should see a success message with import statistics

## Troubleshooting

### "Addon not found" Error
- Check folder name is exactly `WoWStatTracker_Addon`
- Verify it's in the correct AddOns directory
- Restart WoW completely

### "No data exported" Message
- Make sure you've logged in with your characters
- Try `/wst update` then `/wst export`
- Check `/wst debug` for error messages

### App Can't Find Addon Data
- Verify the SavedVariables file exists
- Run `/wst export` in-game first
- Check app is looking in correct WoW directory
- Try running app as administrator (Windows)

### Permission Issues (Linux/macOS)
```bash
# Fix permissions
chmod -R 755 "World of Warcraft/_retail_/Interface/AddOns/WoWStatTracker_Addon/"
```

## Uninstall

To remove the addon:
1. Delete the `WoWStatTracker_Addon` folder from AddOns directory
2. Delete `WoWStatTracker.lua` from SavedVariables (optional)
3. Restart WoW

## Multiple Accounts

If you have multiple WoW accounts:
1. Install the addon once (it works for all accounts)
2. Log in with characters on each account
3. Data is stored per-account in separate SavedVariables files
4. The stat tracker app will find data from all accounts automatically