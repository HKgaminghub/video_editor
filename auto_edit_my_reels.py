# auto_edit_my_reels.py
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
# TEXT-ONLY WATERMARK (no PNG, no black bar)
# =========================
def make_watermark_clip(text: str, duration: float, frame_w: int, frame_h: int):
    """
    Builds the watermark as an RGB clip with a separate MoviePy mask (alpha),
    so ffmpeg never sees a premultiplied PNG. This eliminates black bars.
    """
    try:
        font_px  = max(28, int(frame_h * 0.05))        # ~5% of video height
        stroke_w = max(2,  int(font_px * 0.08))        # proportional stroke
        font     = resolve_font(font_px)

        # Measure tight bounding box
        dummy = Image.new("L", (10, 10))
        d = ImageDraw.Draw(dummy)
        try:
            bbox = d.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        except TypeError:
            bbox = d.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        # Render RGBA with Pillow
        img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            draw.text(
                (0, 0), text, font=font,
                fill=(255, 255, 255, 255),
                stroke_width=stroke_w, stroke_fill=(0, 0, 0, 255),
            )
        except TypeError:
            # Manual stroke fallback for older Pillow
            for dx in (-stroke_w, 0, stroke_w):
                for dy in (-stroke_w, 0, stroke_w):
                    draw.text((dx, dy), text, font=font, fill=(0, 0, 0, 255))
            draw.text((0, 0), text, font=font, fill=(255, 255, 255, 255))

        # Split RGB and Alpha (mask) and hand both directly to MoviePy
        arr = np.array(img)  # HxWx4 uint8
        rgb = arr[..., :3]
        alpha = arr[..., 3]  # HxW

        # Create the RGB clip and the mask clip
        txt_clip = ImageClip(rgb, ismask=False)
        mask_clip = ImageClip(alpha / 255.0, ismask=True)  # MoviePy mask must be float in [0,1]
        txt_clip = txt_clip.set_mask(mask_clip).set_duration(duration)

        # Position (avoid .margin to rule it out)
        margin_r = max(40, int(frame_w * 0.035))
        margin_b = max(40, int(frame_h * 0.035))
        x = frame_w - text_w - margin_r
        y = frame_h - text_h - margin_b

        return txt_clip.set_position((x, y))
    except Exception as e:
        print(f"⚠️  Watermark build failed: {e}")
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

            # Trim 0.2s from start and end (guard for very short videos)
            start = 0.2
            end = max(clip.duration - 0.2, 0.5)
            subclip = clip.subclip(start, end)

            # Random speed-up 1–3%
            speed = 1 + random.uniform(0.01, 0.03)
            subclip = subclip.fx(vfx.speedx, speed)

            # Watermark as RGB + mask (no PNG)
            wm = make_watermark_clip(WATERMARK_TEXT, subclip.duration, w, h)
            final_clip = CompositeVideoClip([subclip, wm]) if wm else subclip

            # Keep FPS stable (source fps if known, else 30)
            try:
                fps = getattr(clip, "fps", None) or getattr(subclip, "fps", None) or 30
            except Exception:
                fps = 30

            # Export (force yuv420p for social media players)
            final_clip.write_videofile(
                output_video_path,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                fps=fps,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
                logger=None,
            )

            # Caption handling
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
            except Exception:
                pass
            try:
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
