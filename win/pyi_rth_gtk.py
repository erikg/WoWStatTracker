# PyInstaller runtime hook for GTK on Windows
import os
import sys

# Set up environment variables for GTK/GI on Windows
if getattr(sys, 'frozen', False):
    # We're running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS

    # Set up GI typelib path
    gi_typelib_path = os.path.join(bundle_dir, 'gi_typelibs')
    if os.path.exists(gi_typelib_path):
        current_path = os.environ.get('GI_TYPELIB_PATH', '')
        if current_path:
            os.environ['GI_TYPELIB_PATH'] = f"{gi_typelib_path};{current_path}"
        else:
            os.environ['GI_TYPELIB_PATH'] = gi_typelib_path

    # Set up XDG_DATA_DIRS for GTK schemas and icons
    share_path = os.path.join(bundle_dir, 'share')
    if os.path.exists(share_path):
        current_xdg = os.environ.get('XDG_DATA_DIRS', '')
        if current_xdg:
            os.environ['XDG_DATA_DIRS'] = f"{share_path};{current_xdg}"
        else:
            os.environ['XDG_DATA_DIRS'] = share_path

    # Set up GDK_PIXBUF_MODULE_FILE for image loading
    pixbuf_loaders = os.path.join(bundle_dir, 'lib', 'gdk-pixbuf-2.0', '2.10.0', 'loaders.cache')
    if os.path.exists(pixbuf_loaders):
        os.environ['GDK_PIXBUF_MODULE_FILE'] = pixbuf_loaders

    # Add bundle directory to PATH for DLL loading
    current_path = os.environ.get('PATH', '')
    os.environ['PATH'] = f"{bundle_dir};{current_path}"

    # Set GTK theme settings for Windows
    os.environ['GTK_CSD'] = '0'  # Disable client-side decorations on Windows
