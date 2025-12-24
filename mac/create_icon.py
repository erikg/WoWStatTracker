#!/usr/bin/env python3
"""
Create a simple app icon for WoW Stat Tracker
"""

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow not installed, trying with basic approach...")
    import subprocess
    import os
    
    # Create a simple colored rectangle as an icon base
    # This is a fallback when PIL is not available
    os.system("""
    cat > /tmp/create_icon.py << 'EOF'
import os
import subprocess

# Create a simple PNG using built-in macOS tools
width, height = 512, 512

# Use AppleScript to create a simple icon
applescript = f'''
tell application "Image Events"
    launch
    set this_image to make new image with properties {{name:"WoWStatIcon", dimensions:{{{width}, {height}}}}}
    -- Fill with a blue gradient background
    tell this_image to pad to dimensions {{{width}, {height}}} with pad color {{0, 20000, 40000}}
    save this_image as PNG in POSIX file "/tmp/wowstat_icon.png"
end tell
'''

subprocess.run(['osascript', '-e', applescript])
EOF
    python3 /tmp/create_icon.py
    """)
    
# Create icon sizes for macOS app bundle
sizes = [16, 32, 64, 128, 256, 512, 1024]
icon_name = "icon"

def create_icns_from_png(png_path, output_path):
    """Convert PNG to ICNS using iconutil"""
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as temp_dir:
        iconset_path = os.path.join(temp_dir, f"{icon_name}.iconset")
        os.makedirs(iconset_path, exist_ok=True)
        
        # Generate all required icon sizes
        for size in sizes:
            # Standard resolution
            output_file = os.path.join(iconset_path, f"icon_{size}x{size}.png")
            subprocess.run([
                'sips', '-z', str(size), str(size), png_path, '--out', output_file
            ], check=True)
            
            # High resolution (@2x) for larger sizes
            if size <= 512:
                output_file_2x = os.path.join(iconset_path, f"icon_{size}x{size}@2x.png")
                subprocess.run([
                    'sips', '-z', str(size*2), str(size*2), png_path, '--out', output_file_2x
                ], check=True)
        
        # Convert iconset to icns
        subprocess.run(['iconutil', '-c', 'icns', iconset_path, '-o', output_path], check=True)

if __name__ == "__main__":
    import os
    import subprocess
    
    # Create a simple base image using Python
    base_png = "wowstat_base.png"
    
    # Create a simple gradient background using sips/convert
    subprocess.run([
        'convert', '-size', '512x512', 
        'gradient:#1a4d7a-#2d5aa0',  # Blue gradient
        '-gravity', 'center',
        '-pointsize', '48',
        '-fill', 'white',
        '-font', 'Arial-Bold',
        '-annotate', '+0-20', 'WoW',
        '-pointsize', '24',
        '-annotate', '+0+20', 'Stat Tracker',
        base_png
    ], check=True)
    
    # Convert to ICNS
    create_icns_from_png(base_png, "icon.icns")
    
    print("✅ Icon created: icon.icns")
    
    # Clean up
    os.remove(base_png)