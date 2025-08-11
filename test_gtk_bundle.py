#!/usr/bin/env python3
"""
Test script to verify GTK libraries work in the Mac app bundle
"""

import sys
import os

def test_gtk_import():
    """Test if GTK can be imported successfully"""
    try:
        print("Testing GTK import...")
        
        # Test basic gi import
        import gi
        print("✅ gi imported successfully")
        print(f"   gi location: {gi.__file__}")
        
        # Test GTK version requirement
        gi.require_version('Gtk', '3.0')
        print("✅ GTK 3.0 version requirement set")
        
        # Test GTK repository imports
        from gi.repository import Gtk, Gdk, Gio, GObject, Pango
        print("✅ GTK repository modules imported successfully")
        
        # Test GTK initialization
        Gtk.init(sys.argv)
        print("✅ GTK initialized successfully")
        
        # Test creating a simple window (don't show it)
        window = Gtk.Window(title="Test")
        print("✅ GTK Window created successfully")
        
        # Test theme detection
        settings = Gtk.Settings.get_default()
        if settings:
            theme_name = settings.get_property("gtk-theme-name")
            print(f"✅ GTK theme detected: {theme_name}")
        
        print("\n🎉 All GTK tests passed! The Mac app should work correctly.")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ GTK error: {e}")
        return False

def show_environment():
    """Show relevant environment variables"""
    print("\n📋 Environment Variables:")
    env_vars = [
        'GI_TYPELIB_PATH',
        'DYLD_LIBRARY_PATH', 
        'PKG_CONFIG_PATH',
        'PYTHONPATH'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'Not set')
        print(f"   {var}: {value}")

def show_bundle_info():
    """Show information about the bundle environment"""
    print("\n📦 Bundle Information:")
    
    # Check if running in PyInstaller bundle
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS
        print(f"   Running in PyInstaller bundle: {bundle_dir}")
        
        # Check for GTK files in bundle
        gi_typelibs = os.path.join(bundle_dir, 'gi_typelibs')
        if os.path.exists(gi_typelibs):
            typelibs = os.listdir(gi_typelibs)
            print(f"   GTK typelibs found: {len(typelibs)} files")
            for typelib in typelibs[:5]:  # Show first 5
                print(f"      - {typelib}")
            if len(typelibs) > 5:
                print(f"      ... and {len(typelibs) - 5} more")
        else:
            print("   No GTK typelibs found in bundle")
            
    else:
        print("   Running from source (not bundled)")

if __name__ == "__main__":
    print("🧪 GTK Bundle Test for WoW Stat Tracker Mac App")
    print("=" * 50)
    
    show_bundle_info()
    show_environment()
    
    print("\n" + "=" * 50)
    success = test_gtk_import()
    
    if success:
        sys.exit(0)
    else:
        print("\n💡 If you see errors, try:")
        print("   1. Ensure GTK is installed: brew install pygobject3 gtk+3")
        print("   2. Rebuild the app: ./build_mac_app.sh")
        print("   3. Check the build output for warnings")
        sys.exit(1)