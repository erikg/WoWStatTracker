#!/bin/bash
# Create styled DMG with background image and drag-to-Applications interface

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

APP_NAME="WoWStatTracker"
VERSION="1.0.0"
DMG_NAME="${APP_NAME}-${VERSION}.dmg"
VOLUME_NAME="${APP_NAME}"
APP_PATH="dist/${APP_NAME}.app"
BACKGROUND_IMG="mac/dmg_background.png"

# Check app exists
if [ ! -d "$APP_PATH" ]; then
    echo "Error: $APP_PATH not found. Run mac/build_mac_app.sh first."
    exit 1
fi

# Check background image exists, create if not
if [ ! -f "$BACKGROUND_IMG" ]; then
    echo "Creating background image..."
    ./venv/bin/python3 mac/create_dmg_background.py || {
        echo "Warning: Could not create background image, continuing without it"
        BACKGROUND_IMG=""
    }
fi

# Clean up any previous DMG
rm -f "dist/${DMG_NAME}"

echo "Creating DMG..."

# Build create-dmg command
CREATE_DMG_ARGS=(
    --volname "$VOLUME_NAME"
    --window-pos 200 120
    --window-size 600 400
    --icon-size 100
    --icon "${APP_NAME}.app" 140 200
    --hide-extension "${APP_NAME}.app"
    --app-drop-link 460 200
)

# Add background if it exists
if [ -n "$BACKGROUND_IMG" ] && [ -f "$BACKGROUND_IMG" ]; then
    CREATE_DMG_ARGS+=(--background "$BACKGROUND_IMG")
fi

# Create the DMG
create-dmg "${CREATE_DMG_ARGS[@]}" "dist/${DMG_NAME}" "$APP_PATH"

echo ""
echo "✅ Created dist/${DMG_NAME}"
echo ""
ls -lh "dist/${DMG_NAME}"
