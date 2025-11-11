import os
import random
import tempfile

from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, vfx
from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIGURATION
# =========================
INPUT_DIR = "reels_downloads"
OUTPUT_DIR = "output_reels"
WATERMARK_TEXT = "@my_page"  # <-- change to your handle

EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

os.makedirs(OUTPUT_DIR, exist_ok=True)

# =========================
# FONT RESOLUTION
# =========================
SYSTEM_FONTS = (
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Roboto-Regular.ttf",  # optional local fallback if you commit the file
)

def resolve_font(size_px: int):
    """Try common system fonts; fall back to Pillow default."""
    for p in SYSTEM_FONTS:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size_px)
        except Exception:
            continue
    return ImageFont.load_default()

# =========================
# TEXT-ONLY WATERMARK
# =========================
def make_watermark(text: str, duration: float, w: int, h: int) -> ImageClip | None:
    """
    White text with black stroke, NO background.
    Produces a tightly-cropped transparent PNG so no black/gray box appears.
    """
    try:
        font_px  = max(28, int(h * 0.05))       # ~5% of video height
        stroke_w = max(2,  int(font_px * 0.08)) # proportional stroke
        font     = resolve_font(font_px)

        # Measure text tightly
        tmp = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        drw = ImageDraw.Draw(tmp)
        try:
            bbox = drw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        except TypeError:
            bbox = drw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Render tight image (no background)
        img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
        d2  = ImageDraw.Draw(img)
        try:
            d2.text(
                (0, 0), text, font=font,
                fill=(255, 255, 255, 255),
                stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255)
            )
        except TypeError:
            # Manual stroke fallback for very old Pillow
            for dx in (-stroke_w, 0, stroke_w):
                for dy in (-stroke_w, 0, stroke_w):
                    d2.text((dx, dy), text, font=font, fill=(0, 0, 0, 255))
            d2.text((0, 0), text, font=font, fill=(255, 255, 255, 255))

        # Save PNG & wrap as ImageClip
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
            img.save(tmpf.name, "PNG")
            path = tmpf.name

        margin_r = max(40, int(w * 0.035))
        margin_b = max(40, int(h * 0.035))

        return (
            ImageClip(path)
            .set_duration(duration)
            .set_position(("right", "bottom"))
            .margin(right=margin_r, bottom=margin_b)
        )
    except Exception as e:
        print(f"⚠️  Warning: watermark generation failed ({e}), skipping watermark.")
        return None

# =========================
# MAIN PROCESS
# =========================
def main():
    if not os.path.isdir(INPUT_DIR):
        print(f"⚠️  Input folder '{INPUT_DIR}' not found. Nothing to process.")
        return

    files = sorted(f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".mp4"))
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

            # Trim 0.2s from start and end (guard for very short clips)
            start = 0.2
            end = max(clip.duration - 0.2, 0.5)
            subclip = clip.subclip(start, end)

            # Random speed-up 1–3%
            speed = 1 + random.uniform(0.01, 0.03)
            subclip = subclip.fx(vfx.speedx, speed)

            # Watermark (text only)
            watermark = make_watermark(WATERMARK_TEXT, subclip.duration, w, h)
            final_clip = CompositeVideoClip([subclip, watermark]) if watermark else subclip

            # Keep FPS stable (source fps if known, else 30)
            try:
                fps = getattr(clip, "fps", None) or getattr(subclip, "fps", None) or 30
            except Exception:
                fps = 30

            # Export
            final_clip.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                fps=fps,
                logger=None,
            )

            # Caption handling
            if os.path.exists(caption_path):
                with open(caption_path, "r", encoding="utf-8") as f:
                    caption = f.read().strip()
            else:
                caption = ""

            caption = (caption + " " + random.choice(EMOJIS)).strip()
            caption += f"\n{random.choice(HASHTAGS)}"

            with open(output_caption_path, "w", encoding="utf-8") as f:
                f.write(caption)

            print(f"✅  Done: {output_video_path}")

        except Exception as e:
            print(f"❌ Error processing '{video_path}': {e}")

        finally:
            try:
                if 'final_clip' in locals() and final_clip is not clip:
                    final_clip.close()
            except Exception:
                pass
            try:
                if 'subclip' in locals() and subclip is not clip:
                    subclip.close()
            except Exception:
                pass
            try:
                clip.close()
            except Exception:
                pass

    print("🎉  All videos processed successfully!")

if __name__ == "__main__":
    random.seed()
    main()
