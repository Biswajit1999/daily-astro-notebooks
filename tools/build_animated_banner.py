"""Build the deterministic still and animated repository cover.

The astronomical background is illustrative artwork.  Typography and motion
are added locally so the project title and author are always exact.
"""

from __future__ import annotations

from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "banner-artwork-source.png"
POSTER = ROOT / "assets" / "banner-animated-poster.png"
ANIMATED = ROOT / "assets" / "banner-animated.gif"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def cover_crop(image: Image.Image, width: int, height: int, phase: float = 0.0) -> Image.Image:
    """Return a gentle pan-and-zoom crop at the requested aspect ratio."""
    source = image.convert("RGB")
    zoom = 1.018 + 0.008 * math.sin(phase * 2 * math.pi)
    scale = max(width / source.width, height / source.height) * zoom
    resized = source.resize((round(source.width * scale), round(source.height * scale)), Image.Resampling.LANCZOS)
    travel = max(0, resized.width - width)
    left = round(travel * (0.35 + 0.16 * math.sin(phase * 2 * math.pi)))
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def typography(frame: Image.Image, opacity: float = 1.0) -> Image.Image:
    canvas = frame.convert("RGBA")
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = canvas.size

    # A restrained title plate protects legibility without hiding the artwork.
    plate = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    plate_draw = ImageDraw.Draw(plate)
    plate_draw.rounded_rectangle(
        (0.105 * width, 0.16 * height, 0.61 * width, 0.82 * height),
        radius=round(0.025 * height),
        fill=(3, 13, 27, round(185 * opacity)),
        outline=(80, 187, 204, round(70 * opacity)),
        width=max(1, round(height / 220)),
    )
    plate = plate.filter(ImageFilter.GaussianBlur(radius=max(1, height / 500)))
    overlay.alpha_composite(plate)

    x = round(0.14 * width)
    title_y = round(0.265 * height)
    title_size = round(0.145 * height)
    author_size = round(0.060 * height)
    strap_size = round(0.032 * height)
    white = (244, 248, 252, round(255 * opacity))
    cyan = (118, 217, 224, round(255 * opacity))
    muted = (174, 196, 210, round(255 * opacity))

    draw.text((x, title_y), "DAILY ASTRO", font=font(title_size, True), fill=white, stroke_width=1, stroke_fill=(2, 8, 18, 220))
    draw.text((x, title_y + title_size * 1.02), "NOTEBOOKS", font=font(title_size, True), fill=white, stroke_width=1, stroke_fill=(2, 8, 18, 220))
    draw.rectangle((x, round(0.62 * height), x + round(0.085 * width), round(0.626 * height)), fill=cyan)
    draw.text((x, round(0.655 * height)), "by Biswajit Jana", font=font(author_size), fill=cyan)
    draw.text((x, round(0.755 * height)), "REAL TELESCOPE DATA  •  REPRODUCIBLE ANALYSIS", font=font(strap_size), fill=muted)
    return Image.alpha_composite(canvas, overlay).convert("RGB")


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"Missing illustrative source: {SOURCE}")

    source = Image.open(SOURCE)
    poster = typography(cover_crop(source, 3200, 800, 0.0))
    POSTER.parent.mkdir(parents=True, exist_ok=True)
    poster.save(POSTER, optimize=True)

    frames: list[Image.Image] = []
    frame_count = 24
    for index in range(frame_count):
        phase = index / frame_count
        frame = cover_crop(source, 1600, 400, phase)
        # A very small brightness cycle gives the cover life without implying
        # measured variability in any astronomical source.
        frame = ImageEnhance.Brightness(frame).enhance(0.985 + 0.015 * math.sin(phase * 2 * math.pi))
        frames.append(typography(frame))

    frames[0].save(
        ANIMATED,
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Poster: {POSTER} ({POSTER.stat().st_size / 1_000_000:.2f} MB)")
    print(f"Animation: {ANIMATED} ({ANIMATED.stat().st_size / 1_000_000:.2f} MB)")


if __name__ == "__main__":
    main()
