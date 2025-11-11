import os
import random
import numpy as np
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, vfx
from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIGURATION
# =========================
INPUT_DIR = "reels_downloads"
OUTPUT_DIR = "output_reels"
WATERMARK_TEXT = "@my_page"  # <-- change this

EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# FONT RESOLUTION
# =========================
SYSTEM_FONTS = (
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Roboto-Regular.ttf",
)

def resolve_font(size_px: int):
    """Try system fonts, fallback to Pillow default."""
    for p in SYSTEM_FONTS:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size_px)
        except Exception:
            continue
    return ImageFont.load_default()

# =========================
# WATERMARK BUILDER (center-bottom, semi-transparent)
# =========================
def make_watermark_clip(text: str, duration: float, frame_w: int, frame_h: int):
    """
    Text-only watermark centered at bottom, small and 50% transparent.
    Uses RGB + alpha mask directly, avoiding black bars.
    """
    try:
        font_px  = max(24, int(frame_h * 0.035))   # smaller size
        stroke_w = max(2, int(font_px * 0.07))
        font     = resolve_font(font_px)

        # Measure text
        dummy = Image.new("L", (10, 10))
        d = ImageDraw.Draw(dummy)
        bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Render RGBA
        img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text(
            (0, 0),
            text,
            font=font,
            fill=(255, 255, 255, 128),  # 50% opacity white
            stroke_width=stroke_w,
            stroke_fill=(0, 0, 0, 180),  # slightly transparent black stroke
        )

        arr = np.array(img)
        rgb = arr[..., :3]
        alpha = arr[..., 3] / 255.0

        # Create RGB + alpha clips
        txt_clip = ImageClip(rgb, ismask=False)
        mask_clip = ImageClip(alpha, ismask=True)
        txt_clip = txt_clip.set_mask(mask_clip).set_duration(duration)

        # Center horizontally, bottom vertically
        margin_bottom = max(40, int(frame_h * 0.035))
        x = (frame_w - text_w) / 2
        y = frame_h - text_h - margin_bottom

        return txt_clip.set_position((x, y))

    except Exception as e:
        print(f"⚠️  Watermark creation failed: {e}")
        return None

# =========================
# MAIN PROCESS
# =========================
def main():
    files = sorted(f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".mp4")) if os.path.isdir(INPUT_DIR) else []
    if not files:
        print("ℹ️  No MP4 files found. Place videos in 'reels_downloads/' and rerun.")
        return

    for file in files:
        base = os.path.splitext(file)[0]
        video_path = os.path.join(INPUT_DIR, f"{base}.mp4")
        caption_path = os.path.join(INPUT_DIR, f"{base}.txt")
        output_video_path = os.path.join(OUTPUT_DIR, f"{base}.mp4")
        output_caption_path = os.path.join(OUTPUT_DIR, f"{base}.txt")

        print(f"🎞️  Processing {video_path} ...")
        try:
            clip = VideoFileClip(video_path)
        except Exception as e:
            print(f"❌ Failed to open '{video_path}': {e}")
            continue

        try:
            w, h = clip.size

            # Trim 0.2s from start and end
            start = 0.2
            end = max(clip.duration - 0.2, 0.5)
            subclip = clip.subclip(start, end)

            # Random speed-up 1–3%
            speed = 1 + random.uniform(0.01, 0.03)
            subclip = subclip.fx(vfx.speedx, speed)

            # Watermark centered bottom
            wm = make_watermark_clip(WATERMARK_TEXT, subclip.duration, w, h)
            final_clip = CompositeVideoClip([subclip, wm]) if wm else subclip

            fps = getattr(clip, "fps", 30)
            final_clip.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                fps=fps,
                threads=4,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                logger=None,
            )

            # Caption update
            caption = ""
            if os.path.exists(caption_path):
                with open(caption_path, "r", encoding="utf-8") as f:
                    caption = f.read().strip()
            caption = (caption + " " + random.choice(EMOJIS)).strip()
            caption += f"\n{random.choice(HASHTAGS)}"
            with open(output_caption_path, "w", encoding="utf-8") as f:
                f.write(caption)

            print(f"✅  Done: {output_video_path}")

        except Exception as e:
            print(f"❌ Error processing '{video_path}': {e}")

        finally:
            try:
                final_clip.close()
                subclip.close()
                clip.close()
            except Exception:
                pass

    print("🎉  All videos processed successfully!")

if __name__ == "__main__":
    random.seed()
    main()
