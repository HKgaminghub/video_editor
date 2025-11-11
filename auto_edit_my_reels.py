import os, random, requests, tempfile
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
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

# === Download font if missing ===
FONT_PATH = "Roboto-Regular.ttf"
if not os.path.exists(FONT_PATH):
    print("📥 Downloading Roboto font for watermark text...")
    url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
    r = requests.get(url)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)
    print("✅ Font downloaded successfully")


def make_watermark(text, duration, w, h):
    """Render watermark text to a temporary PNG file and load as ImageClip."""
    try:
        # Draw text on transparent RGBA image
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        text_w, text_h = draw.textsize(text, font=font)

        x = w - text_w - 40
        y = h - text_h - 40

        # Outline
        for dx in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
            for dy in range(-STROKE_WIDTH, STROKE_WIDTH + 1):
                draw.text((x + dx, y + dy), text, font=font, fill=STROKE_COLOR)
        # Main text
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
    subclip = subclip.fx(lambda c: c.speedx(speed))

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
    caption += f" {random.choice(EMOJIS)}\n{random.choice(HASHTAGS)}"
    with open(output_caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    clip.close()
    subclip.close()
    final_clip.close()
    print(f"✅  Done: {output_video_path}")

print("🎉  All videos processed successfully!")
