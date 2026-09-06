#!/usr/bin/env python3
"""Draw the integration's brand icon.

HACS looks for `custom_components/<domain>/brand/icon.png` and falls back to
the Home Assistant brands repository if it is not there. Home Assistant's
brands repository wants 256x256 and 512x512 PNGs, square, transparent,
trimmed to the mark. Generating them from code keeps the asset reproducible
and lets the mark be adjusted without a design tool.

**The mark is deliberately original.** It does not use Sungrow's logo,
wordmark or brand colours: this is a third-party community integration, and
borrowing a manufacturer's trademark both risks the trademark and implies an
endorsement that does not exist.

What it shows: a rayed sun above a battery — solar generation and storage,
which is exactly what an SH-series hybrid inverter is. Two shapes, two
colours, and deliberately no more: the icon is displayed at around 32 pixels
in Home Assistant's own UI, where anything finer turns to mush.

    python scripts/make_brand_icon.py            # writes the brand/ folder
    python scripts/make_brand_icon.py --preview  # also writes a large preview
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parent.parent
BRAND = REPO / "custom_components" / "sungrow_modbus" / "brand"

#: Drawn far larger than needed and downsampled, which is the cheapest way to
#: get clean edges out of Pillow's non-antialiased primitives.
SUPERSAMPLE = 8
SIZES = (512, 256)

#: Warm amber for the sun and a deep slate for the flow. The amber carries on
#: both light and dark backgrounds; the slate does not, which is why there is
#: a separate dark variant that lifts it to a pale blue.
LIGHT = {"sun": (245, 166, 35, 255), "flow": (38, 55, 71, 255)}
DARK = {"sun": (250, 183, 70, 255), "flow": (208, 222, 235, 255)}


def draw_mark(size: int, palette: dict[str, tuple[int, int, int, int]]) -> Image.Image:
    """Draw the mark at ``size`` pixels square, on transparency.

    Two shapes stacked and centred: a rayed sun above a battery. They are
    deliberately different silhouettes — round over rectangular — so the mark
    still reads at the ~32 pixels Home Assistant actually displays it at,
    where any finer detail disappears.
    """
    s = size * SUPERSAMPLE
    image = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def box(cx, cy, w, h):
        return [(cx - w / 2) * s, (cy - h / 2) * s, (cx + w / 2) * s, (cy + h / 2) * s]

    # --- the sun: disc plus eight stubby rays, centred on the upper third.
    sun_cx, sun_cy = 0.5, 0.285
    draw.ellipse(box(sun_cx, sun_cy, 0.325, 0.325), fill=palette["sun"])

    ray_inner, ray_outer, ray_w = 0.208, 0.284, 0.056
    for i in range(8):
        angle = math.radians(i * 45)
        dx, dy = math.cos(angle), math.sin(angle)
        x0 = (sun_cx + dx * ray_inner) * s
        y0 = (sun_cy + dy * ray_inner) * s
        x1 = (sun_cx + dx * ray_outer) * s
        y1 = (sun_cy + dy * ray_outer) * s
        draw.line([x0, y0, x1, y1], fill=palette["sun"], width=int(ray_w * s))
        # Round the ends; Pillow's line joins are square.
        for px, py in ((x0, y0), (x1, y1)):
            r = ray_w * s / 2
            draw.ellipse([px - r, py - r, px + r, py + r], fill=palette["sun"])

    # --- the battery: a wide block with a terminal, centred below the sun.
    body_w, body_h = 0.66, 0.265
    body_cx, body_cy = 0.472, 0.760
    draw.rounded_rectangle(
        box(body_cx, body_cy, body_w, body_h), radius=0.055 * s, fill=palette["flow"]
    )
    draw.rounded_rectangle(
        box(body_cx + body_w / 2 + 0.032, body_cy, 0.064, 0.105),
        radius=0.020 * s,
        fill=palette["flow"],
    )

    # Charge cells knocked back out, which is what makes the block a battery
    # rather than a bar.
    cell_w, cell_h, gap = 0.116, 0.125, 0.055
    span = cell_w * 3 + gap * 2
    first = body_cx - span / 2 + cell_w / 2
    for i in range(3):
        draw.rounded_rectangle(
            box(first + i * (cell_w + gap), body_cy, cell_w, cell_h),
            radius=0.018 * s,
            fill=(0, 0, 0, 0),
        )

    return image.resize((size, size), Image.LANCZOS)


def trimmed(image: Image.Image) -> Image.Image:
    """Trim transparent edges, then pad back to square.

    The brands repository asks for the minimum empty space at the edges while
    still being 1:1, so the mark is trimmed to its content and re-centred in a
    square rather than left floating in its original canvas.
    """
    box = image.getbbox()
    if box is None:
        return image
    cropped = image.crop(box)
    side = max(cropped.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(
        cropped, ((side - cropped.width) // 2, (side - cropped.height) // 2), cropped
    )
    return square


def render(name: str, palette: dict[str, tuple[int, int, int, int]]) -> list[Path]:
    """Write the 512 and 256 pixel variants of one mark."""
    written = []
    master = trimmed(draw_mark(SIZES[0] * 2, palette))
    for size in SIZES:
        filename = f"{name}@2x.png" if size == 512 else f"{name}.png"
        path = BRAND / filename
        master.resize((size, size), Image.LANCZOS).save(path, "PNG", optimize=True)
        written.append(path)
    return written


def main() -> int:
    """Render every brand asset."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preview", action="store_true", help="also write a large preview sheet"
    )
    args = parser.parse_args()

    BRAND.mkdir(exist_ok=True)
    written = render("icon", LIGHT) + render("dark_icon", DARK)

    if args.preview:
        # Both marks at display size and at inspection size, on the two
        # backgrounds they have to survive.
        sheet = Image.new("RGBA", (760, 300), (255, 255, 255, 255))
        ImageDraw.Draw(sheet).rectangle([380, 0, 760, 300], fill=(28, 30, 33, 255))
        for x0, palette in ((0, LIGHT), (380, DARK)):
            big = trimmed(draw_mark(512, palette)).resize((200, 200), Image.LANCZOS)
            sheet.paste(big, (x0 + 30, 50), big)
            for i, size in enumerate((64, 48, 32)):
                small = trimmed(draw_mark(512, palette)).resize(
                    (size, size), Image.LANCZOS
                )
                sheet.paste(small, (x0 + 260, 50 + i * 80), small)
        path = BRAND / "preview.png"
        sheet.convert("RGB").save(path, "PNG")
        written.append(path)

    for path in written:
        print(f"{path.relative_to(REPO)}  {path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
