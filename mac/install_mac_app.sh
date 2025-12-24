#!/bin/bash

# Installation script for WoW Stat Tracker Mac App

set -e

# Change to project root directory
cd "$(dirname "$0")/.."

echo "🚀 Installing WoW Stat Tracker..."

# Check if the app exists
if [ ! -d "dist/WoWStatTracker.app" ]; then
    echo "❌ App not found. Please build the app first using: mac/build_mac_app.sh"
    exit 1
fi

# Copy to Applications folder
echo "📦 Copying app to Applications folder..."
sudo cp -r "dist/WoWStatTracker.app" "/Applications/"

# Set proper permissions
echo "🔐 Setting proper permissions..."
sudo chmod -R 755 "/Applications/WoWStatTracker.app"

echo "✅ Installation complete!"
echo "📱 You can now find 'WoW Stat Tracker' in your Applications folder"
echo "🔍 Or search for it using Spotlight (Cmd+Space)"

# Option to launch the app
read -p "Would you like to launch the app now? (y/N): " launch_app
if [[ $launch_app =~ ^[Yy]$ ]]; then
    echo "🚀 Launching WoW Stat Tracker..."
    open "/Applications/WoWStatTracker.app"
fi

echo "Done! 🎉"