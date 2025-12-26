# -*- mode: python ; coding: utf-8 -*-
import sys
import os
import subprocess
from pathlib import Path

block_cipher = None

# Get the current working directory
spec_root = Path.cwd()

# Find GTK and GI library paths for Windows (MSYS2)
def find_gtk_libraries():
    binaries = []
    datas = []

    # MSYS2 paths - adjust based on installation
    msys2_paths = [
        'C:/msys64/mingw64',
        'C:/msys64/ucrt64',
        os.environ.get('MINGW_PREFIX', ''),
    ]

    mingw_root = None
    for path in msys2_paths:
        if path and os.path.exists(os.path.join(path, 'bin', 'libgtk-3-0.dll')):
            mingw_root = path
            break

    if not mingw_root:
        print("Warning: Could not find MSYS2/MinGW GTK installation")
        return binaries, datas

    bin_dir = os.path.join(mingw_root, 'bin')
    lib_dir = os.path.join(mingw_root, 'lib')
    share_dir = os.path.join(mingw_root, 'share')

    # Essential GTK DLLs
    essential_dlls = [
        'libgtk-3-0.dll',
        'libgdk-3-0.dll',
        'libgobject-2.0-0.dll',
        'libglib-2.0-0.dll',
        'libgio-2.0-0.dll',
        'libgmodule-2.0-0.dll',
        'libgirepository-1.0-1.dll',
        'libpango-1.0-0.dll',
        'libpangocairo-1.0-0.dll',
        'libpangowin32-1.0-0.dll',
        'libcairo-2.dll',
        'libcairo-gobject-2.dll',
        'libgdk_pixbuf-2.0-0.dll',
        'libatk-1.0-0.dll',
        'libharfbuzz-0.dll',
        'libfontconfig-1.dll',
        'libfreetype-6.dll',
        'libintl-8.dll',
        'libiconv-2.dll',
        'libffi-8.dll',
        'libpng16-16.dll',
        'zlib1.dll',
        'libpixman-1-0.dll',
        'libepoxy-0.dll',
        'libfribidi-0.dll',
        'libbz2-1.dll',
        'libbrotlidec.dll',
        'libbrotlicommon.dll',
        'libexpat-1.dll',
        'libpcre2-8-0.dll',
        # GCC runtime
        'libgcc_s_seh-1.dll',
        'libstdc++-6.dll',
        'libwinpthread-1.dll',
    ]

    for dll in essential_dlls:
        dll_path = os.path.join(bin_dir, dll)
        if os.path.exists(dll_path):
            binaries.append((dll_path, '.'))

    # Add GI typelib files
    gi_typelib_path = os.path.join(lib_dir, 'girepository-1.0')
    if os.path.exists(gi_typelib_path):
        typelibs = [
            'Gtk-3.0.typelib', 'Gdk-3.0.typelib', 'GObject-2.0.typelib',
            'GLib-2.0.typelib', 'Gio-2.0.typelib', 'Pango-1.0.typelib',
            'PangoCairo-1.0.typelib', 'cairo-1.0.typelib', 'Atk-1.0.typelib',
            'GdkPixbuf-2.0.typelib', 'GModule-2.0.typelib', 'PangoWin32-1.0.typelib',
            'GdkWin32-3.0.typelib', 'HarfBuzz-0.0.typelib', 'freetype2-2.0.typelib',
            'fontconfig-2.0.typelib', 'win32-1.0.typelib',
        ]
        for typelib in typelibs:
            typelib_file = os.path.join(gi_typelib_path, typelib)
            if os.path.exists(typelib_file):
                datas.append((typelib_file, 'gi_typelibs'))

    # Add GTK schemas
    schemas_dir = os.path.join(share_dir, 'glib-2.0', 'schemas')
    if os.path.exists(schemas_dir):
        datas.append((schemas_dir, 'share/glib-2.0/schemas'))

    # Add icon themes (needed for GTK to render properly)
    icons_dir = os.path.join(share_dir, 'icons')
    if os.path.exists(icons_dir):
        # Include Adwaita theme for default icons
        adwaita_dir = os.path.join(icons_dir, 'Adwaita')
        if os.path.exists(adwaita_dir):
            datas.append((adwaita_dir, 'share/icons/Adwaita'))
        hicolor_dir = os.path.join(icons_dir, 'hicolor')
        if os.path.exists(hicolor_dir):
            datas.append((hicolor_dir, 'share/icons/hicolor'))

    # Add pixbuf loaders
    pixbuf_loaders_dir = os.path.join(lib_dir, 'gdk-pixbuf-2.0')
    if os.path.exists(pixbuf_loaders_dir):
        datas.append((pixbuf_loaders_dir, 'lib/gdk-pixbuf-2.0'))

    return binaries, datas

# Get GTK binaries and data
gtk_binaries, gtk_datas = find_gtk_libraries()

# Include WoW addon in bundle
addon_datas = [(str(spec_root / 'WoWStatTracker_Addon'), 'WoWStatTracker_Addon')]

a = Analysis(
    [str(spec_root / 'src' / 'wowstat.py')],
    pathex=[
        str(spec_root),
        str(spec_root / 'src'),
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
        'slpp',
        'six',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(spec_root / 'win' / 'pyi_rth_gtk.py')],
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
    console=False,  # Set to True for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(spec_root / 'win' / 'icon.ico') if (spec_root / 'win' / 'icon.ico').exists() else None,
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
