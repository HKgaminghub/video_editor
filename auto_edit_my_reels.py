import os, random, requests
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import TextClip

# === CONFIGURATION ===
INPUT_DIR = "reels_downloads"      # folder with 1.mp4, 1.txt, etc.
OUTPUT_DIR = "output_reels"        # edited files will go here
WATERMARK_TEXT = "@my_page"        # watermark text
FONT_SIZE = 50
FONT_COLOR = "white"
STROKE_COLOR = "black"
STROKE_WIDTH = 2

EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Ensure a font exists (GitHub runners have none) ===
FONT_PATH = "Roboto-Regular.ttf"
if not os.path.exists(FONT_PATH):
    print("📥 Downloading Roboto font for watermark text...")
    url = "https://github.com/google/fonts/raw/main/apache/roboto/Roboto-Regular.ttf"
    r = requests.get(url)
    with open(FONT_PATH, "wb") as f:
        f.write(r.content)
    print("✅ Font downloaded")

def make_watermark(text, duration):
    """Create watermark text using Pillow backend."""
    try:
        wm = (TextClip(
                text,
                fontsize=FONT_SIZE,
                color=FONT_COLOR,
                font=FONT_PATH,              # explicit font
                stroke_color=STROKE_COLOR,
                stroke_width=STROKE_WIDTH,
                method="caption")
              .set_duration(duration)
              .set_position(("right", "bottom"))
              .margin(right=40, bottom=40, opacity=0))
        return wm
    except Exception as e:
        print(f"⚠️  TextClip failed ({e}), skipping watermark.")
        return None

# === PROCESSING LOOP ===
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

    # Trim 0.2 s start & end
    start = 0.2
    end = max(clip.duration - 0.2, 0.5)
    subclip = clip.subclip(start, end)

    # Random speed change (1–3 %)
    speed = 1 + random.uniform(0.01, 0.03)
    subclip = subclip.fx(lambda c: c.speedx(speed))

    # Add watermark
    watermark = make_watermark(WATERMARK_TEXT, subclip.duration)
    final_clip = CompositeVideoClip([subclip, watermark]) if watermark else subclip

    # Export video
    final_clip.write_videofile(
        output_video_path,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None
    )

    # Caption tweak
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
    print(f"✅ Done: {output_video_path}")

print("🎉  All videos processed successfully!")
