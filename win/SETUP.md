# Windows Build Setup

This guide explains how to set up a Windows development environment for WoW Stat Tracker.

## Prerequisites

### 1. Install MSYS2

Download and install MSYS2 from https://www.msys2.org/

The default installation path is `C:\msys64`.

### 2. Install GTK3 and Python Dependencies

Open **MSYS2 MINGW64** shell (not the default MSYS2 shell) and run:

```bash
# Update package database
pacman -Syu

# Install GTK3 and PyGObject
pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-python-gobject

# Install Python packages
pacman -S mingw-w64-x86_64-python-pip

# Optional: Install additional Python tools
pip install pyinstaller
```

### 3. Verify Installation

In the MSYS2 MINGW64 shell:

```bash
python -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; print('GTK OK')"
```

## Running the Application

### From MSYS2 MINGW64 Shell

```bash
cd /c/path/to/WoWStatTracker
python src/wowstat.py
```

### From Windows Command Prompt

Add MSYS2 to your PATH first:

```cmd
set PATH=C:\msys64\mingw64\bin;%PATH%
python src\wowstat.py
```

## Building a Standalone Executable

### Using the Build Script

```cmd
win\build_win_app.bat
```

This creates `dist\WoWStatTracker\WoWStatTracker.exe`.

### Manual Build

```cmd
set PATH=C:\msys64\mingw64\bin;%PATH%
set MINGW_PREFIX=C:\msys64\mingw64
pyinstaller win\WoWStatTracker.spec --clean --noconfirm
```

## Creating a Distributable Package

After building, create a ZIP archive:

```powershell
Compress-Archive -Path dist\WoWStatTracker -DestinationPath dist\WoWStatTracker-Windows.zip
```

## Troubleshooting

### "ImportError: cannot import name '_gi'"

Make sure you're using the Python from MSYS2, not a separate Python installation:

```cmd
where python
# Should show: C:\msys64\mingw64\bin\python.exe
```

### "DLL load failed"

Ensure MSYS2 bin directory is in your PATH before other Python installations.

### GTK theme looks wrong

The application uses the system GTK theme. You can install additional themes:

```bash
pacman -S mingw-w64-x86_64-adwaita-icon-theme
```

### Missing typelibs

If you get errors about missing `.typelib` files:

```bash
pacman -S mingw-w64-x86_64-gobject-introspection
```

## Alternative: UCRT64 Environment

If you prefer UCRT64 (newer C runtime) instead of MINGW64:

```bash
# In MSYS2 UCRT64 shell
pacman -S mingw-w64-ucrt-x86_64-gtk3 mingw-w64-ucrt-x86_64-python-gobject
```

Update the build script paths to use `ucrt64` instead of `mingw64`.
