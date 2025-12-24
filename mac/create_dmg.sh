#!/bin/bash
# Create styled DMG with background image and drag-to-Applications interface

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

APP_NAME="WoWStatTracker"
DMG_NAME="${APP_NAME}.dmg"
DMG_TEMP_NAME="${APP_NAME}_temp.dmg"
VOLUME_NAME="${APP_NAME}"
APP_PATH="dist/${APP_NAME}.app"
BACKGROUND_IMG="mac/dmg_background.png"

# DMG window dimensions (must match background image)
WINDOW_WIDTH=600
WINDOW_HEIGHT=400

# Icon positions (centered vertically, spaced horizontally)
APP_ICON_X=140
APP_ICON_Y=200
APPS_ICON_X=460
APPS_ICON_Y=200

# Check app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run mac/build_mac_app.sh first."
    exit 1
fi

# Check background image exists
if [ ! -f "$BACKGROUND_IMG" ]; then
    echo "Creating background image..."
    python3 mac/create_dmg_background.py || {
        echo "Warning: Could not create background image, continuing without it"
        BACKGROUND_IMG=""
    }
fi

# Clean up any previous DMG
rm -f "dist/${DMG_NAME}"
rm -f "dist/${DMG_TEMP_NAME}"

# Create temporary directory for DMG contents
DMG_TEMP="dist/dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP/.background"

# Copy app
cp -R "$APP_PATH" "$DMG_TEMP/"

# Create Applications symlink
ln -s /Applications "$DMG_TEMP/Applications"

# Copy background image if it exists
if [ -n "$BACKGROUND_IMG" ] && [ -f "$BACKGROUND_IMG" ]; then
    cp "$BACKGROUND_IMG" "$DMG_TEMP/.background/background.png"
fi

# Calculate DMG size (app size + 20MB buffer)
APP_SIZE=$(du -sm "$APP_PATH" | cut -f1)
DMG_SIZE=$((APP_SIZE + 20))

echo "Creating DMG (${DMG_SIZE}MB)..."

# Create a read-write DMG first
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDRW \
    -size ${DMG_SIZE}m \
    "dist/${DMG_TEMP_NAME}"

# Mount the DMG
echo "Mounting DMG for customization..."
MOUNT_DIR=$(hdiutil attach -readwrite -noverify "dist/${DMG_TEMP_NAME}" | grep "/Volumes/" | sed 's/.*\(\/Volumes\/.*\)/\1/' | head -1)

if [ -z "$MOUNT_DIR" ]; then
    echo "Error: Failed to mount DMG"
    exit 1
fi

echo "Mounted at: $MOUNT_DIR"

# Wait for mount to be ready
sleep 2

# Use AppleScript to customize the DMG window appearance
echo "Customizing DMG appearance..."

osascript <<EOF
tell application "Finder"
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {100, 100, $((100 + WINDOW_WIDTH)), $((100 + WINDOW_HEIGHT))}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 100
        set text size of viewOptions to 12

        -- Set background if it exists
        if exists file ".background:background.png" then
            set background picture of viewOptions to file ".background:background.png"
        end if

        -- Position icons
        set position of item "${APP_NAME}.app" of container window to {$APP_ICON_X, $APP_ICON_Y}
        set position of item "Applications" of container window to {$APPS_ICON_X, $APPS_ICON_Y}

        close
        open
        update without registering applications
        delay 2
        close
    end tell
end tell
EOF

# Sync and unmount
sync
hdiutil detach "$MOUNT_DIR" -quiet

# Convert to compressed read-only DMG
echo "Creating final compressed DMG..."
hdiutil convert "dist/${DMG_TEMP_NAME}" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "dist/${DMG_NAME}"

# Clean up
rm -f "dist/${DMG_TEMP_NAME}"
rm -rf "$DMG_TEMP"

echo ""
echo "✅ Created dist/${DMG_NAME}"
echo ""
ls -lh "dist/${DMG_NAME}"
