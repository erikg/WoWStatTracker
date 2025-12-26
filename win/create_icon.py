#!/usr/bin/env python3
"""
Create a Windows icon (.ico) for WoW Stat Tracker

Requires: pip install Pillow
"""

import os
import sys

def create_icon():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Error: Pillow is required. Install with: pip install Pillow")
        sys.exit(1)

    # Icon sizes for Windows ICO (must include 16, 32, 48, 256 at minimum)
    sizes = [16, 24, 32, 48, 64, 128, 256]

    # Create base image at largest size
    base_size = 256
    img = Image.new('RGBA', (base_size, base_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw gradient background (blue theme matching WoW)
    for y in range(base_size):
        # Gradient from #1a4d7a to #2d5aa0
        ratio = y / base_size
        r = int(26 + (45 - 26) * ratio)
        g = int(77 + (90 - 77) * ratio)
        b = int(122 + (160 - 122) * ratio)
        draw.line([(0, y), (base_size, y)], fill=(r, g, b, 255))

    # Add rounded rectangle border effect
    border_color = (255, 255, 255, 100)
    draw.rounded_rectangle([4, 4, base_size - 5, base_size - 5], radius=20, outline=border_color, width=2)

    # Try to add text (requires a font)
    try:
        # Try to find a suitable font
        font_paths = [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        font_path = None
        for fp in font_paths:
            if os.path.exists(fp):
                font_path = fp
                break

        if font_path:
            font_large = ImageFont.truetype(font_path, 48)
            font_small = ImageFont.truetype(font_path, 20)

            # Draw "WoW" text
            text_wow = "WoW"
            bbox = draw.textbbox((0, 0), text_wow, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (base_size - text_width) // 2
            draw.text((x, 60), text_wow, font=font_large, fill=(255, 255, 255, 255))

            # Draw "Stats" text
            text_stats = "Stats"
            bbox = draw.textbbox((0, 0), text_stats, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (base_size - text_width) // 2
            draw.text((x, 120), text_stats, font=font_small, fill=(200, 220, 255, 255))

            # Draw a simple chart icon
            chart_y = 170
            bar_width = 20
            bar_gap = 10
            bars = [40, 60, 35, 55, 45]
            start_x = (base_size - (len(bars) * (bar_width + bar_gap))) // 2

            for i, height in enumerate(bars):
                x = start_x + i * (bar_width + bar_gap)
                draw.rectangle(
                    [x, chart_y + (60 - height), x + bar_width, chart_y + 60],
                    fill=(100, 180, 255, 200)
                )
        else:
            # No font available, just draw a simple symbol
            draw.ellipse([60, 60, 196, 196], outline=(255, 255, 255, 200), width=4)
            draw.text((100, 110), "WS", fill=(255, 255, 255, 255))
    except Exception as e:
        print(f"Warning: Could not add text to icon: {e}")

    # Generate all sizes and save as ICO
    icon_images = []
    for size in sizes:
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        icon_images.append(resized)

    # Save as ICO
    output_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    img.save(output_path, format='ICO', sizes=[(s, s) for s in sizes])

    print(f"Icon created: {output_path}")
    return output_path


if __name__ == "__main__":
    create_icon()
