# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import subprocess
from pathlib import Path

block_cipher = None

# Get the current working directory
spec_root = Path.cwd()

# Find GTK and GI library paths
def find_gtk_libraries():
    binaries = []
    datas = []
    
    # Get library paths from pkg-config
    try:
        # Get GObject Introspection libraries
        gi_output = subprocess.check_output(['pkg-config', '--libs-only-L', 'gobject-introspection-1.0'], 
                                          universal_newlines=True)
        gi_paths = [path.strip()[2:] for path in gi_output.split() if path.startswith('-L')]
        
        # Get GTK libraries  
        gtk_output = subprocess.check_output(['pkg-config', '--libs-only-L', 'gtk+-3.0'], 
                                           universal_newlines=True)
        gtk_paths = [path.strip()[2:] for path in gtk_output.split() if path.startswith('-L')]
        
        lib_paths = list(set(gi_paths + gtk_paths))
        
        # Add essential libraries
        essential_libs = [
            'libgirepository-1.0.dylib',
            'libgtk-3.0.dylib', 
            'libgdk-3.0.dylib',
            'libgobject-2.0.dylib',
            'libglib-2.0.dylib',
            'libgio-2.0.dylib',
            'libgmodule-2.0.dylib',
            'libgthread-2.0.dylib',
            'libpango-1.0.dylib',
            'libpangocairo-1.0.dylib',
            'libcairo.dylib',
            'libcairo-gobject.dylib',
            'libgdk_pixbuf-2.0.dylib',
            'libatk-1.0.dylib',
            'libharfbuzz.dylib',
            'libfontconfig.dylib',
            'libfreetype.dylib',
            'libintl.dylib',
        ]
        
        for lib_path in lib_paths:
            if os.path.exists(lib_path):
                for lib in essential_libs:
                    lib_file = os.path.join(lib_path, lib)
                    if os.path.exists(lib_file):
                        binaries.append((lib_file, '.'))
        
        # Add GI typelib files
        gi_typelib_path = '/usr/local/lib/girepository-1.0'
        if os.path.exists(gi_typelib_path):
            typelibs = ['Gtk-3.0.typelib', 'Gdk-3.0.typelib', 'GObject-2.0.typelib', 
                       'GLib-2.0.typelib', 'Gio-2.0.typelib', 'Pango-1.0.typelib',
                       'PangoCairo-1.0.typelib', 'cairo-1.0.typelib', 'Atk-1.0.typelib']
            for typelib in typelibs:
                typelib_file = os.path.join(gi_typelib_path, typelib)
                if os.path.exists(typelib_file):
                    datas.append((typelib_file, 'gi_typelibs'))
                    
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: Could not find GTK libraries via pkg-config")
    
    return binaries, datas

# Get GTK binaries and data
gtk_binaries, gtk_datas = find_gtk_libraries()

# Include WoW addon in bundle Resources
addon_datas = [(str(spec_root / 'WoWStatTracker_Addon'), 'WoWStatTracker_Addon')]

a = Analysis(
    [str(spec_root / 'src' / 'wowstat.py')],
    pathex=[
        str(spec_root),
        str(spec_root / 'src'),
        '/usr/local/lib/python3.13/site-packages',
        '/usr/local/opt/pygobject3/lib/python3.13/site-packages',
    ],
    binaries=gtk_binaries,
    datas=gtk_datas + addon_datas,
    hiddenimports=[
        'gi',
        'gi.repository',
        'gi.repository.Gtk',
        'gi.repository.Gdk', 
        'gi.repository.Gio',
        'gi.repository.GObject',
        'gi.repository.Pango',
        'gi.repository.PangoCairo',
        'gi.repository.cairo',
        'gi.repository.Atk',
        'gi.repository.GdkPixbuf',
        'gi._gi',
        'gi._gi_cairo',
        '_gi',
        '_gi_cairo',
        'cairo._cairo',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_root / 'mac' / 'pyi_rth_gtk.py')],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WoWStatTracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WoWStatTracker'
)

app = BUNDLE(
    coll,
    name='WoWStatTracker.app',
    icon=str(spec_root / 'mac' / 'icon.icns'),
    bundle_identifier='com.wowstattracker.app',
    version='1.0.0',
    info_plist={
        'CFBundleName': 'WoW Stat Tracker',
        'CFBundleDisplayName': 'WoW Stat Tracker',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.wowstattracker.app',
        'CFBundlePackageType': 'APPL',
        'CFBundleExecutable': 'WoWStatTracker',
        'CFBundleIconFile': 'icon.icns',
        'LSMinimumSystemVersion': '10.14.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,  # Enable dark mode support
        'LSApplicationCategoryType': 'public.app-category.games',
        'LSEnvironment': {
            'GI_TYPELIB_PATH': '@executable_path/../Resources/gi_typelibs:/usr/local/lib/girepository-1.0',
            'DYLD_LIBRARY_PATH': '@executable_path/../Frameworks:/usr/local/lib',
        },
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'JSON Document',
                'CFBundleTypeExtensions': ['json'],
                'CFBundleTypeRole': 'Editor',
            }
        ],
    },
)