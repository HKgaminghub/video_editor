import os, random
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip

# === CONFIGURATION ===
INPUT_DIR = "reels_downloads"          # your folder with 1.mp4, 1.txt, etc.
OUTPUT_DIR = "output_reels"         # edited files will go here
WATERMARK_TEXT = "@my_page"         # your watermark text
FONT_SIZE = 50                      # adjust to your preference
FONT_COLOR = "white"                # watermark text color
STROKE_COLOR = "black"              # outline color for visibility
STROKE_WIDTH = 2

# Emoji & hashtag pools for small caption edits
EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

# Create output folder if not exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

    # Add watermark
    watermark = (
        TextClip(WATERMARK_TEXT,
                 fontsize=FONT_SIZE,
                 color=FONT_COLOR,
                 stroke_color=STROKE_COLOR,
                 stroke_width=STROKE_WIDTH,
                 font="Arial-Bold")
        .set_duration(subclip.duration)
        .set_position(("right", "bottom"))
        .margin(right=40, bottom=40, opacity=0)
    )
    final_clip = CompositeVideoClip([subclip, watermark])

    # Export edited video
    final_clip.write_videofile(output_video_path,
                               codec="libx264",
                               audio_codec="aac",
                               threads=4,
                               logger=None)

    # Modify caption text
    if os.path.exists(caption_path):
        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read().strip()
    else:
        caption = ""

    # Add random emoji & hashtag to make caption slightly unique
    caption += f" {random.choice(EMOJIS)}\n{random.choice(HASHTAGS)}"

    with open(output_caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    # Cleanup
    clip.close()
    subclip.close()
    final_clip.close()

    print(f"✅ Done: {output_video_path}")

print("🎉 All videos processed successfully!")
