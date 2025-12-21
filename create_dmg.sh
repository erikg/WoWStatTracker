#!/bin/bash
# Create DMG with drag-to-Applications interface

set -e

APP_NAME="WoWStatTracker"
DMG_NAME="${APP_NAME}.dmg"
VOLUME_NAME="${APP_NAME}"
APP_PATH="dist/${APP_NAME}.app"

# Check app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run build_mac_app.sh first."
    exit 1
fi

# Clean up any previous DMG
rm -f "dist/${DMG_NAME}"

# Create temporary directory for DMG contents
DMG_TEMP="dist/dmg_temp"
rm -rf "$DMG_TEMP"
mkdir -p "$DMG_TEMP"

# Copy app and create Applications symlink
cp -R "$APP_PATH" "$DMG_TEMP/"
ln -s /Applications "$DMG_TEMP/Applications"

# Create DMG
hdiutil create -volname "$VOLUME_NAME" \
    -srcfolder "$DMG_TEMP" \
    -ov -format UDZO \
    "dist/${DMG_NAME}"

# Clean up
rm -rf "$DMG_TEMP"

echo "Created dist/${DMG_NAME}"
