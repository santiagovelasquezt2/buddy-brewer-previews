#!/usr/bin/env python3
"""Build deterministic, canonical-logo overlays for the lifecycle videos.

The AI source plates stay untouched. This script creates brand-safe derivatives
using only the approved Buddy Brewer mark rasterized from the canonical SVG.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageStat


ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "assets" / "video"
MARK = Image.open(VIDEO / "brand" / "buddy-brewer-mark.png").convert("RGBA")
CREAM = (253, 248, 242, 255)
PRODUCTS = {
    "energy": Image.open(ROOT / "assets" / "energy-can-v2.png").convert("RGBA"),
    "daily": Image.open(ROOT / "assets" / "daily-can-v2.png").convert("RGBA"),
    "nightly": Image.open(ROOT / "assets" / "nightly-can-v2.png").convert("RGBA"),
}


def resized_mark(width: int) -> Image.Image:
    height = round(width * MARK.height / MARK.width)
    return MARK.resize((width, height), Image.Resampling.LANCZOS)


def paste_mark(canvas: Image.Image, left: int, top: int, width: int) -> None:
    mark = resized_mark(width)
    canvas.alpha_composite(mark, (left, top))


def paste_product(
    canvas: Image.Image,
    product: str,
    left: int,
    top: int,
    height: int,
    angle: float = 0,
) -> None:
    source = PRODUCTS[product]
    width = round(height * source.width / source.height)
    can = source.resize((width, height), Image.Resampling.LANCZOS)
    if angle:
        can = can.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    canvas.alpha_composite(can, (left, top))


def sampled_color(image: Image.Image, x: int, y: int, radius: int = 12) -> tuple[int, int, int, int]:
    crop = image.crop((x - radius, y - radius, x + radius, y + radius)).convert("RGB")
    mean = ImageStat.Stat(crop).mean
    return tuple(round(channel) for channel in mean) + (255,)


def feathered_patch(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int],
    radius: int = 18,
    feather: int = 5,
) -> None:
    left, top, right, bottom = box
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    mask = Image.new("L", canvas.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(box, radius=radius, fill=255)
    if feather:
        mask = mask.filter(ImageFilter.GaussianBlur(feather))
    fill = Image.new("RGBA", canvas.size, color)
    overlay.alpha_composite(fill)
    overlay.putalpha(mask)
    canvas.alpha_composite(overlay)


def cream_label(canvas: Image.Image, box: tuple[int, int, int, int], radius: int = 24) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=radius, fill=CREAM)
    canvas.alpha_composite(layer)


def add_bug(canvas: Image.Image) -> None:
    width, height = canvas.size
    mark_width = round(width * 0.083)
    mark = resized_mark(mark_width)
    center_x = round(width * 0.80)
    center_y = round(height * 0.90)
    left = center_x - mark.width // 2
    top = center_y - mark.height // 2
    pad_x = round(width * 0.012)
    pad_y = round(height * 0.010)
    backing = (left - pad_x, top - pad_y, left + mark.width + pad_x, top + mark.height + pad_y)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(backing, radius=round(width * 0.016), fill=CREAM)
    layer.alpha_composite(mark, (left, top))
    canvas.alpha_composite(layer)


def brand_chatgpt() -> None:
    source_dir = VIDEO / "chatgpt"
    output_dir = VIDEO / "chatgpt-branded"
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene in range(1, 7):
        source = source_dir / f"scene-{scene:02d}-{'raw' if scene == 1 else 'blend' if scene == 2 else 'can' if scene == 3 else 'pack' if scene == 4 else 'ship' if scene == 5 else 'door'}.png"
        image = Image.open(source).convert("RGBA")

        if scene == 3:
            # The exact product cutout fully replaces the generated can and logo.
            paste_product(image, "daily", 438, 336, 880)
        elif scene == 4:
            paste_product(image, "energy", 174, 553, 448, -2)
            paste_product(image, "daily", 333, 505, 474, 0)
            paste_product(image, "nightly", 478, 535, 385, 2)
            cream_label(image, (900, 590, 1165, 814), 28)
            paste_mark(image, 948, 605, 170)
        elif scene == 5:
            cream_label(image, (342, 716, 714, 938), 30)
            paste_mark(image, 430, 730, 196)
        elif scene == 6:
            cream_label(image, (414, 652, 792, 886), 30)
            paste_mark(image, 505, 668, 196)

        image.convert("RGBA").save(output_dir / source.name)


def blank_overlay(size: int = 960) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def brand_grok_overlays() -> None:
    output_dir = VIDEO / "grok-overlays"
    output_dir.mkdir(parents=True, exist_ok=True)

    for scene in range(1, 7):
        overlay = blank_overlay()
        if scene == 3:
            paste_mark(overlay, 380, 485, 200)
        elif scene == 4:
            paste_mark(overlay, 368, 622, 224)
        elif scene == 5:
            paste_mark(overlay, 355, 420, 250)
        elif scene == 6:
            paste_mark(overlay, 360, 510, 250)
        overlay.save(output_dir / f"scene-{scene:02d}-overlay.png")


if __name__ == "__main__":
    brand_chatgpt()
    brand_grok_overlays()
