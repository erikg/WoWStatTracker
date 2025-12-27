#!/bin/bash
#
# WoW Stat Tracker - DMG Creation Script
# BSD 3-Clause License
#
# Creates a distributable DMG file from the app bundle.
#
# Usage: ./packaging/macos/create_dmg.sh [--notarize APPLE_ID]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build-macos-Release"
NOTARIZE=""
APPLE_ID=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --notarize)
            NOTARIZE="1"
            APPLE_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--notarize APPLE_ID]"
            exit 1
            ;;
    esac
done

# Check for app bundle
APP_BUNDLE="$BUILD_DIR/WoWStatTracker.app"
if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle not found at $APP_BUNDLE"
    echo "Run ./packaging/macos/build.sh first"
    exit 1
fi

# Get version from Info.plist
VERSION=$(defaults read "$APP_BUNDLE/Contents/Info" CFBundleShortVersionString 2>/dev/null || echo "1.0.0")
DMG_NAME="WoWStatTracker-${VERSION}-macOS"
DMG_PATH="$BUILD_DIR/$DMG_NAME.dmg"

echo "=== Creating DMG ==="
echo "App: $APP_BUNDLE"
echo "Version: $VERSION"
echo "Output: $DMG_PATH"

# Create temporary directory for DMG contents
TEMP_DIR=$(mktemp -d)
trap "rm -rf '$TEMP_DIR'" EXIT

# Copy app to temp directory
echo ""
echo "=== Preparing DMG contents ==="
cp -R "$APP_BUNDLE" "$TEMP_DIR/"

# Create Applications symlink
ln -s /Applications "$TEMP_DIR/Applications"

# Create DMG
echo ""
echo "=== Creating DMG file ==="

# Remove existing DMG
rm -f "$DMG_PATH"

# Create DMG using hdiutil
hdiutil create -volname "WoW Stat Tracker" \
    -srcfolder "$TEMP_DIR" \
    -ov -format UDZO \
    "$DMG_PATH"

echo ""
echo "=== DMG created ==="
echo "Location: $DMG_PATH"
du -h "$DMG_PATH"

# Notarize if requested
if [ -n "$NOTARIZE" ]; then
    if [ -z "$APPLE_ID" ]; then
        echo "Error: Apple ID required for notarization"
        exit 1
    fi

    echo ""
    echo "=== Notarizing DMG ==="
    echo "This may take several minutes..."

    # Submit for notarization
    xcrun notarytool submit "$DMG_PATH" \
        --apple-id "$APPLE_ID" \
        --team-id "YOUR_TEAM_ID" \
        --password "@keychain:AC_PASSWORD" \
        --wait

    # Staple the ticket
    echo ""
    echo "=== Stapling notarization ticket ==="
    xcrun stapler staple "$DMG_PATH"

    echo ""
    echo "=== Notarization complete ==="
fi

echo ""
echo "=== Done ==="
echo "DMG ready for distribution: $DMG_PATH"
