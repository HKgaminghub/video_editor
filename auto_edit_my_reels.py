import os, random, requests, tempfile
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, vfx
from PIL import Image, ImageDraw, ImageFont

# === CONFIGURATION ===
INPUT_DIR = "reels_downloads"
OUTPUT_DIR = "output_reels"
WATERMARK_TEXT = "@my_page"
FONT_SIZE = 50
FONT_COLOR = (255, 255, 255, 255)
STROKE_COLOR = (0, 0, 0, 255)
STROKE_WIDTH = 2

EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Font resolution ===
LOCAL_FONT = "Roboto-Regular.ttf"
SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

def ensure_local_font(path=LOCAL_FONT):
    """Download a valid TTF if we truly need a local file; validate response."""
    if os.path.exists(path):
        return path
    print("📥 Downloading Roboto font for watermark text (fallback)...")
    url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
    r = requests.get(url, allow_redirects=True, timeout=30)
    r.raise_for_status()
    # Basic content check: TTFs won't be HTML
    if b"<html" in r.content[:200].lower():
        raise RuntimeError("Downloaded HTML instead of TTF (rate-limited/redirect).")
    with open(path, "wb") as f:
        f.write(r.content)
    print("✅ Font downloaded successfully")
    return path

def resolve_font_path():
    for p in SYSTEM_FONTS:
        if os.path.exists(p):
            try:
                ImageFont.truetype(p, FONT_SIZE)  # probe
                return p
            except Exception:
                pass
    try:
        p = ensure_local_font()
        ImageFont.truetype(p, FONT_SIZE)  # probe
        return p
    except Exception as e:
        print(f"⚠️  Warning: Could not load Roboto ({e}). Falling back to default font.")
        return None  # will use ImageFont.load_default()

FONT_PATH = resolve_font_path()

def make_watermark(text, duration, w, h):
    """Render watermark text to a temporary PNG file and load as ImageClip."""
    try:
        # Draw text on transparent RGBA image
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE) if FONT_PATH else ImageFont.load_default()

        # Use textbbox for accurate size
        bbox = draw.textbbox((0, 0), text, font=font, stroke_width=STROKE_WIDTH)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        x = w - text_w - 40
        y = h - text_h - 40

        # Outline via stroke parameters (simpler & faster than manual loops if supported)
        try:
            draw.text((x, y), text, font=font, fill=FONT_COLOR,
                      stroke_width=STROKE_WIDTH, stroke_fill=STROKE_COLOR)
        except TypeError:
            # Pillow too old: do manual outline
            for dx in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
                for dy in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
                    draw.text((x + dx, y + dy), text, font=font, fill=STROKE_COLOR)
            draw.text((x, y), text, font=font, fill=FONT_COLOR)

        # Save to a temporary PNG file
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            img.save(tmp.name, format="PNG")
            tmp_path = tmp.name

        # Load the saved image as an ImageClip
        watermark_clip = (
            ImageClip(tmp_path)
            .set_duration(duration)
            .set_position(("right", "bottom"))
            .margin(right=40, bottom=40)
        )
        return watermark_clip

    except Exception as e:
        print(f"⚠️  Warning: Pillow watermark failed ({e}), skipping watermark.")
        return None

# === MAIN PROCESS ===
for file in sorted(os.listdir(INPUT_DIR)):
    if not file.lower().endswith(".mp4"):
        continue

    base = os.path.splitext(file)[0]
    video_path = os.path.join(INPUT_DIR, f"{base}.mp4")
    caption_path = os.path.join(INPUT_DIR, f"{base}.txt")
    output_video_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
    output_caption_path = os.path.join(OUTPUT_DIR, f"{base}.txt")

    print(f"🎞️  Processing {video_path} ...")

    clip = VideoFileClip(video_path)
    w, h = clip.size

    # Trim & speed
    start = 0.2
    end = max(clip.duration - 0.2, 0.5)
    subclip = clip.subclip(start, end)
    speed = 1 + random.uniform(0.01, 0.03)
    # Use vfx.speedx for clarity
    subclip = subclip.fx(vfx.speedx, speed)

    # Add watermark
    watermark = make_watermark(WATERMARK_TEXT, subclip.duration, w, h)
    final_clip = CompositeVideoClip([subclip, watermark]) if watermark else subclip

    # Export
    final_clip.write_videofile(
        output_video_path,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None,
    )

    # Caption
    if os.path.exists(caption_path):
        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read().strip()
    else:
        caption = ""
    caption = (caption + " " + random.choice(EMOJIS)).strip() + f"\n{random.choice(HASHTAGS)}"
    with open(output_caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    clip.close()
    subclip.close()
    final_clip.close()
    print(f"✅  Done: {output_video_path}")

print("🎉  All videos processed successfully!")
