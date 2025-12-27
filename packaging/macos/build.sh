#!/bin/bash
#
# WoW Stat Tracker - macOS Build Script
# BSD 3-Clause License
#
# Builds the native macOS application bundle.
#
# Usage: ./packaging/macos/build.sh [--release|--debug] [--sign IDENTITY]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_TYPE="Release"
SIGN_IDENTITY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --release)
            BUILD_TYPE="Release"
            shift
            ;;
        --debug)
            BUILD_TYPE="Debug"
            shift
            ;;
        --sign)
            SIGN_IDENTITY="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--release|--debug] [--sign IDENTITY]"
            exit 1
            ;;
    esac
done

echo "=== WoW Stat Tracker macOS Build ==="
echo "Build type: $BUILD_TYPE"
echo "Project dir: $PROJECT_DIR"

# Create build directory
BUILD_DIR="$PROJECT_DIR/build-macos-$BUILD_TYPE"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with CMake
echo ""
echo "=== Configuring with CMake ==="
cmake "$PROJECT_DIR" \
    -DCMAKE_BUILD_TYPE="$BUILD_TYPE" \
    -DWST_BUILD_PLATFORM=ON \
    -DWST_BUILD_GUI=ON \
    -DWST_BUILD_TESTS=OFF \
    -DWST_ENABLE_LTO=ON

# Build
echo ""
echo "=== Building ==="
cmake --build . --config "$BUILD_TYPE" -j$(sysctl -n hw.ncpu)

# Check if app bundle was created
APP_BUNDLE="$BUILD_DIR/WoWStatTracker.app"
if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle not found at $APP_BUNDLE"
    exit 1
fi

echo ""
echo "=== App bundle created ==="
echo "Location: $APP_BUNDLE"

# Copy addon to Resources
ADDON_SRC="$PROJECT_DIR/../WoWStatTracker_Addon"
if [ -d "$ADDON_SRC" ]; then
    echo ""
    echo "=== Copying addon to bundle ==="
    RESOURCES_DIR="$APP_BUNDLE/Contents/Resources"
    mkdir -p "$RESOURCES_DIR"
    cp -R "$ADDON_SRC" "$RESOURCES_DIR/"
    echo "Addon copied to: $RESOURCES_DIR/WoWStatTracker_Addon"
fi

# Code sign if identity provided
if [ -n "$SIGN_IDENTITY" ]; then
    echo ""
    echo "=== Code signing ==="
    codesign --force --deep --sign "$SIGN_IDENTITY" \
        --options runtime \
        --entitlements "$SCRIPT_DIR/entitlements.plist" \
        "$APP_BUNDLE"

    echo "Verifying signature..."
    codesign --verify --verbose "$APP_BUNDLE"
    echo "Code signing complete."
fi

# Show bundle info
echo ""
echo "=== Build Complete ==="
echo "App: $APP_BUNDLE"
du -sh "$APP_BUNDLE"

# Show binary size
BINARY="$APP_BUNDLE/Contents/MacOS/WoWStatTracker"
if [ -f "$BINARY" ]; then
    echo "Binary size: $(du -h "$BINARY" | cut -f1)"
fi

echo ""
echo "To create DMG, run: ./packaging/macos/create_dmg.sh"
