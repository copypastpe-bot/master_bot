"""Generate welcome banner for Master Bot /start command."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 640

# Simple dark gradient: top row → bottom row
img = Image.new("RGB", (W, H))
draw = ImageDraw.Draw(img)

# Draw gradient rows (640 iterations, not 800K)
for y in range(H):
    t = y / H
    r = int(30 + 30 * t)
    g = int(20 + 10 * t)
    b = int(80 + 60 * t)
    draw.line([(0, y), (W, y)], fill=(r, g, b))

# Text
try:
    font_big = ImageFont.truetype("/Library/Fonts/Arial Bold.ttf", 100)
    font_sub = ImageFont.truetype("/Library/Fonts/Arial.ttf", 36)
except Exception:
    try:
        font_big = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
        font_sub = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
    except Exception:
        font_big = ImageFont.load_default()
        font_sub = font_big

draw.text((W // 2, H // 2 - 60), "CRMfit", font=font_big, fill="white", anchor="mm")
draw.text((W // 2, H // 2 + 60), "CRM для мастеров в Telegram", font=font_sub, fill=(200, 200, 220), anchor="mm")

out = Path(__file__).parent.parent / "assets" / "welcome_banner.png"
out.parent.mkdir(exist_ok=True)
img.save(out)
print(f"Banner saved: {out}")
