import os, random
from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.VideoClip import TextClip

# === CONFIGURATION ===
INPUT_DIR = "reels_downloads"          # your folder with 1.mp4, 1.txt, etc.
OUTPUT_DIR = "output_reels"            # edited files will go here
WATERMARK_TEXT = "@my_page"            # your watermark text
FONT_SIZE = 50                         # adjust to your preference
FONT_COLOR = "white"                   # watermark text color

# Emoji & hashtag pools for small caption edits
EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

# Create output folder if not exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

def make_watermark(text, duration):
    """Use PIL-based text rendering (no ImageMagick required)."""
    try:
        return (TextClip(text,
                         fontsize=FONT_SIZE,
                         color=FONT_COLOR,
                         method="caption")  # uses Pillow
                .set_duration(duration)
                .set_position(("right", "bottom"))
                .margin(right=40, bottom=40, opacity=0))
    except Exception as e:
        print(f"⚠️ Warning: TextClip failed ({e}), skipping watermark.")
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

    print(f"Processing {video_path} ...")

    # Load video
    clip = VideoFileClip(video_path)

    # Trim 0.2s from start & end
    start = 0.2
    end = max(clip.duration - 0.2, 0.5)
    subclip = clip.subclip(start, end)

    # Slight random speed change (1–3%)
    speed = 1 + random.uniform(0.01, 0.03)
    subclip = subclip.fx(lambda c: c.speedx(speed))

    # Add watermark (if possible)
    watermark = make_watermark(WATERMARK_TEXT, subclip.duration)
    if watermark:
        final_clip = CompositeVideoClip([subclip, watermark])
    else:
        final_clip = subclip

    # Export edited video
    final_clip.write_videofile(
        output_video_path,
        codec="libx264",
        audio_codec="aac",
        threads=4,
        logger=None
    )

    # Modify caption text
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

print("🎉 All videos processed successfully!")
