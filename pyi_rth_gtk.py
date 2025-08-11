# PyInstaller runtime hook for GTK
import os
import sys

# Set up environment variables for GTK/GI
if getattr(sys, 'frozen', False):
    # We're running in a PyInstaller bundle
    bundle_dir = sys._MEIPASS
    
    # Set up GI typelib path
    gi_typelib_path = os.path.join(bundle_dir, 'gi_typelibs')
    if os.path.exists(gi_typelib_path):
        current_path = os.environ.get('GI_TYPELIB_PATH', '')
        if current_path:
            os.environ['GI_TYPELIB_PATH'] = f"{gi_typelib_path}:{current_path}"
        else:
            os.environ['GI_TYPELIB_PATH'] = gi_typelib_path
    
    # Add system paths as fallback
    system_gi_path = '/usr/local/lib/girepository-1.0'
    if os.path.exists(system_gi_path):
        current_path = os.environ.get('GI_TYPELIB_PATH', '')
        if current_path:
            os.environ['GI_TYPELIB_PATH'] = f"{current_path}:{system_gi_path}"
        else:
            os.environ['GI_TYPELIB_PATH'] = system_gi_path
    
    # Set up library path for dylibs
    dylib_path = os.path.join(bundle_dir)
    current_dyld_path = os.environ.get('DYLD_LIBRARY_PATH', '')
    if current_dyld_path:
        os.environ['DYLD_LIBRARY_PATH'] = f"{dylib_path}:{current_dyld_path}"
    else:
        os.environ['DYLD_LIBRARY_PATH'] = dylib_path
    
    # Add system library paths
    system_lib_paths = ['/usr/local/lib', '/opt/homebrew/lib']
    for lib_path in system_lib_paths:
        if os.path.exists(lib_path):
            current_dyld_path = os.environ.get('DYLD_LIBRARY_PATH', '')
            if current_dyld_path:
                os.environ['DYLD_LIBRARY_PATH'] = f"{current_dyld_path}:{lib_path}"
            else:
                os.environ['DYLD_LIBRARY_PATH'] = lib_path