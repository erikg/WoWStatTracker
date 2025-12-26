#!/bin/bash

# Build script for WoW Stat Tracker Mac App
# This script creates a standalone Mac application bundle

set -e  # Exit on any error

echo "🚀 Building WoW Stat Tracker Mac App..."

# Change to project root directory
cd "$(dirname "$0")/.."

# Ensure venv exists with system site-packages (for Homebrew GTK)
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv --system-site-packages venv
    ./venv/bin/pip install --upgrade pip
fi

# Install PyInstaller in venv if not present
if [ ! -f "./venv/bin/pyinstaller" ]; then
    echo "📦 Installing PyInstaller in venv..."
    ./venv/bin/pip install pyinstaller pyinstaller-hooks-contrib
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ __pycache__/

# Check for GTK installation
if ! ./venv/bin/python3 -c "import gi" 2>/dev/null; then
    echo "❌ GTK/PyGObject not found. Please install with: brew install pygobject3 gtk+3"
    exit 1
fi

# Set up environment for PyInstaller to find GTK libraries
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/opt/homebrew/lib/pkgconfig:$PKG_CONFIG_PATH"
export GI_TYPELIB_PATH="/usr/local/lib/girepository-1.0:/opt/homebrew/lib/girepository-1.0"
export DYLD_LIBRARY_PATH="/usr/local/lib:/opt/homebrew/lib:$DYLD_LIBRARY_PATH"

# Verify GTK libraries can be found
echo "🔍 Checking GTK library installation..."
if ! pkg-config --exists gtk+-3.0; then
    echo "❌ GTK+3 development libraries not found"
    echo "Please install with: brew install gtk+3"
    exit 1
fi

if ! pkg-config --exists gobject-introspection-1.0; then
    echo "❌ GObject Introspection not found"
    echo "Installing missing dependencies..."
    brew install gobject-introspection
fi

echo "✅ GTK libraries found"

# Build the app
echo "🔨 Building Mac application bundle..."
./venv/bin/pyinstaller mac/WoWStatTracker.spec --clean --noconfirm

# Check if build was successful
if [ -d "dist/WoWStatTracker.app" ]; then
    echo "✅ Build successful!"
    echo "📱 Mac app created at: dist/WoWStatTracker.app"
    echo ""
    echo "To run the app:"
    echo "  open dist/WoWStatTracker.app"
    echo ""
    echo "To install the app:"
    echo "  cp -r dist/WoWStatTracker.app /Applications/"
    echo ""
    
    # Make the app executable
    chmod +x "dist/WoWStatTracker.app/Contents/MacOS/WoWStatTracker"
    
    # Try to run the app for testing
    echo "🧪 Testing the built app..."
    if open "dist/WoWStatTracker.app"; then
        echo "✅ App launched successfully!"
    else
        echo "⚠️  App built but failed to launch. Check dependencies."
    fi
else
    echo "❌ Build failed. Check the output above for errors."
    exit 1
fi