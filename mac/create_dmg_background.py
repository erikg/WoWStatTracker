#!/usr/bin/env python3
"""Create DMG background image for WoW Stat Tracker."""

from PIL import Image, ImageDraw, ImageFont
import os

# DMG window dimensions (standard size for nice DMG)
WIDTH = 600
HEIGHT = 400

# WoW-inspired colors
BG_COLOR_TOP = (30, 25, 35)  # Dark purple-black
BG_COLOR_BOTTOM = (15, 12, 20)  # Darker
GOLD = (255, 209, 0)  # WoW gold
GOLD_DARK = (180, 140, 0)
TEXT_COLOR = (220, 220, 220)
ARROW_COLOR = (100, 90, 110)

def create_background():
    # Create image with gradient background
    img = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR_BOTTOM)
    draw = ImageDraw.Draw(img)

    # Draw gradient background
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_COLOR_TOP[0] * (1 - ratio) + BG_COLOR_BOTTOM[0] * ratio)
        g = int(BG_COLOR_TOP[1] * (1 - ratio) + BG_COLOR_BOTTOM[1] * ratio)
        b = int(BG_COLOR_TOP[2] * (1 - ratio) + BG_COLOR_BOTTOM[2] * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # App name at top
    try:
        # Try to use a nice font
        title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    except:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()

    # Draw title
    title = "WoW Stat Tracker"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - title_width) // 2, 30), title, fill=GOLD, font=title_font)

    # Draw instruction text
    instruction = "Drag to Applications to install"
    bbox = draw.textbbox((0, 0), instruction, font=subtitle_font)
    inst_width = bbox[2] - bbox[0]
    draw.text(((WIDTH - inst_width) // 2, 70), instruction, fill=TEXT_COLOR, font=subtitle_font)

    # Draw arrow in the middle (between icon positions)
    # Icons will be at approximately x=150 (app) and x=450 (Applications)
    # Arrow goes from ~200 to ~400
    arrow_y = HEIGHT // 2 + 20
    arrow_start_x = 220
    arrow_end_x = 380

    # Draw arrow line (dashed effect)
    for x in range(arrow_start_x, arrow_end_x - 20, 15):
        draw.ellipse([x, arrow_y - 3, x + 8, arrow_y + 3], fill=ARROW_COLOR)

    # Draw arrowhead
    arrowhead_x = arrow_end_x - 10
    draw.polygon([
        (arrowhead_x, arrow_y - 12),
        (arrowhead_x + 20, arrow_y),
        (arrowhead_x, arrow_y + 12)
    ], fill=ARROW_COLOR)

    # Add subtle gold accent line at bottom
    draw.rectangle([50, HEIGHT - 40, WIDTH - 50, HEIGHT - 38], fill=GOLD_DARK)

    # Save
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "dmg_background.png")
    img.save(output_path, "PNG")
    print(f"Created: {output_path}")

    # Also save @2x version for retina
    img_2x = img.resize((WIDTH * 2, HEIGHT * 2), Image.LANCZOS)
    output_path_2x = os.path.join(output_dir, "dmg_background@2x.png")
    img_2x.save(output_path_2x, "PNG")
    print(f"Created: {output_path_2x}")

if __name__ == "__main__":
    create_background()
