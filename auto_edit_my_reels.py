import os
import random
import sys
import tempfile

from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip, vfx
from PIL import Image, ImageDraw, ImageFont

# =========================
# CONFIGURATION
# =========================
INPUT_DIR = "reels_downloads"
OUTPUT_DIR = "output_reels"
WATERMARK_TEXT = "@my_page"

# Visual defaults (tuned for vertical videos like 1080x1920)
EMOJIS = ["🔥", "💫", "🎬", "✨", "⚡", "🎵"]
HASHTAGS = ["#reels", "#foryou", "#explore", "#trending", "#viral"]

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)


# =========================
# FONT RESOLUTION (robust)
# =========================
SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/roboto/Roboto-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "Roboto-Regular.ttf",  # optional local fallback if you commit the file
]

def resolve_font(size_px: int) -> ImageFont.FreeTypeFont:
    """
    Try common system fonts installed in the workflow (Roboto/DejaVu),
    then fall back to Pillow's default if none work.
    """
    for path in SYSTEM_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size_px)
            except Exception:
                pass
    # Final fallback: load_default (bitmap) - not ideal, but prevents failure
    return ImageFont.load_default()


# =========================
# WATERMARK MAKER (visible)
# =========================
def make_watermark_badge(text: str, duration: float, w: int, h: int) -> ImageClip | None:
    """
    Creates a compact RGBA badge (rounded dark background + white text + stroke),
    sized relative to video height for consistent visibility. Returns an ImageClip.
    """
    try:
        # ~5% of video height is a good watermark size (tweak if desired)
        font_px = max(28, int(h * 0.05))
        pad_x = max(12, int(font_px * 0.5))
        pad_y = max(6, int(font_px * 0.3))
        stroke_w = max(2, int(font_px * 0.08))

        font = resolve_font(font_px)

        # Measure text
        tmp_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        tmp_draw = ImageDraw.Draw(tmp_img)
        try:
            bbox = tmp_draw.textbbox((0, 0), text, font=font, stroke_width=stroke_w)
        except TypeError:
            bbox = tmp_draw.textbbox((0, 0), text, font=font)
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

        badge_w = text_w + pad_x * 2
        badge_h = text_h + pad_y * 2

        # Draw badge
        badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)

        # Semi-transparent rounded rect background
        bg = (0, 0, 0, 120)  # increase alpha (last value) if you want stronger contrast
        radius = max(6, int(badge_h * 0.3))
        try:
            draw.rounded_rectangle((0, 0, badge_w, badge_h), radius=radius, fill=bg)
        except AttributeError:
            draw.rectangle((0, 0, badge_w, badge_h), fill=bg)

        # Text with stroke for crisp edges
        text_pos = (pad_x, pad_y)
        try:
            draw.text(
                text_pos,
                text,
                font=font,
                fill=(255, 255, 255, 255),
                stroke_width=stroke_w,
                stroke_fill=(0, 0, 0, 255),
            )
        except TypeError:
            # Very old Pillow: manual shadow
            for dx in (-stroke_w, 0, stroke_w):
                for dy in (-stroke_w, 0, stroke_w):
                    draw.text((text_pos[0] + dx, text_pos[1] + dy), text, font=font, fill=(0, 0, 0, 255))
            draw.text(text_pos, text, font=font, fill=(255, 255, 255, 255))

        # Save to a temporary PNG & wrap as ImageClip
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            badge.save(tmp.name, "PNG")
            tmp_path = tmp.name

        margin_r = max(40, int(w * 0.035))
        margin_b = max(40, int(h * 0.035))

        return (
            ImageClip(tmp_path)
            .set_duration(duration)
            .set_opacity(0.92)
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

            # Watermark
            watermark = make_watermark_badge(WATERMARK_TEXT, subclip.duration, w, h)
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
            # Clean up resources
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
    # Ensure deterministic emoji/hashtag if needed by CI (comment out to keep random)
    random.seed()
    main()
