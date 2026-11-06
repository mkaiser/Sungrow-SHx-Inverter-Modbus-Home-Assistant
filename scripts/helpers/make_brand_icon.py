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

What it shows: a PV array, and under it an inverter (a box around ~), a
battery and a car -- generation, conversion, storage and the charge point this
integration reads. Two colours, slate and amber, and no text: the icon is shown
at about 32 pixels in Home Assistant's own UI, so every part is a plain
silhouette, and the parts sit in one row under the array so none overlaps
another. Chosen by the maintainer on 2026-11-07 from three drafts.

    python scripts/helpers/make_brand_icon.py            # writes the brand/ folder
    python scripts/helpers/make_brand_icon.py --preview  # also writes a large preview
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw

REPO = Path(__file__).resolve().parents[2]
BRAND = REPO / "custom_components" / "sungrow_modbus" / "brand"

#: Drawn far larger than needed and downsampled, which is the cheapest way to
#: get clean edges out of Pillow's non-antialiased primitives.
SUPERSAMPLE = 4
SIZES = (512, 256)

#: Warm amber for what carries energy and a deep slate for the hardware. The
#: amber carries on both light and dark backgrounds; the slate does not, which
#: is why there is a separate dark variant that lifts it to a pale blue.
LIGHT = {"sun": (245, 166, 35, 255), "flow": (38, 55, 71, 255)}
DARK = {"sun": (250, 183, 70, 255), "flow": (208, 222, 235, 255)}


Colour = tuple[int, int, int, int]
CLEAR: Colour = (0, 0, 0, 0)

#: The car, side on, facing right, in a box one unit wide: the outline, the two
#: windows (cut out) and the two wheel centres.
CAR_OUTLINE = (
    (0.00, 0.30), (0.04, 0.22), (0.20, 0.18), (0.30, 0.04), (0.68, 0.04),
    (0.82, 0.18), (0.96, 0.22), (1.00, 0.30), (1.00, 0.40), (0.00, 0.40),
)  # fmt: skip
CAR_WINDOWS = (
    ((0.32, 0.09), (0.49, 0.09), (0.49, 0.18), (0.27, 0.18)),
    ((0.53, 0.09), (0.665, 0.09), (0.77, 0.18), (0.53, 0.18)),
)
CAR_WHEELS = (0.24, 0.76)


class _Pen:
    """Pillow's primitives in unit coordinates, on a supersampled canvas.

    A unit is the canvas's height. `place` moves and scales what is drawn
    next, so the parts drawn for the square icon can be laid out again for
    the wide logo without a second copy of any of them.
    """

    def __init__(self, size: int, aspect: float = 1.0) -> None:
        self.n = size * SUPERSAMPLE
        self.image = Image.new("RGBA", (round(self.n * aspect), self.n), CLEAR)
        self.draw = ImageDraw.Draw(self.image)
        self.place(0.0, 0.0, 1.0)

    def place(self, ox: float, oy: float, k: float) -> None:
        """Draw what follows at `k` times its size, its origin at (ox, oy)."""
        self.ox, self.oy, self.k = ox, oy, k

    def at(self, x: float, y: float) -> tuple[float, float]:
        return ((self.ox + x * self.k) * self.n, (self.oy + y * self.k) * self.n)

    def polygon(self, points: tuple[tuple[float, float], ...], fill: Colour) -> None:
        self.draw.polygon([self.at(x, y) for x, y in points], fill=fill)

    def box(
        self, cx: float, cy: float, w: float, h: float, r: float, fill: Colour
    ) -> None:
        x0, y0 = self.at(cx - w / 2, cy - h / 2)
        x1, y1 = self.at(cx + w / 2, cy + h / 2)
        self.draw.rounded_rectangle(
            [x0, y0, x1, y1], radius=r * self.k * self.n, fill=fill
        )

    def disc(self, cx: float, cy: float, r: float, fill: Colour) -> None:
        x0, y0 = self.at(cx - r, cy - r)
        x1, y1 = self.at(cx + r, cy + r)
        self.draw.ellipse([x0, y0, x1, y1], fill=fill)

    def stroke(self, points: list[tuple[float, float]], w: float, fill: Colour) -> None:
        """Draw a polyline with round ends and joins."""
        width = max(1, int(w * self.k * self.n))
        self.draw.line([self.at(x, y) for x, y in points], fill=fill, width=width)
        for x, y in points:
            self.disc(x, y, w / 2, fill)


def _array(pen: _Pen, fill: Colour) -> None:
    """Draw the PV array: a quad in perspective, cut into 4 x 2 modules."""
    tl, tr, br, bl = (0.30, 0.06), (0.70, 0.06), (0.90, 0.34), (0.10, 0.34)
    cols, rows, gap = 4, 2, 0.13

    def at(u: float, v: float) -> tuple[float, float]:
        top = (tl[0] + (tr[0] - tl[0]) * u, tl[1] + (tr[1] - tl[1]) * u)
        bottom = (bl[0] + (br[0] - bl[0]) * u, bl[1] + (br[1] - bl[1]) * u)
        return (top[0] + (bottom[0] - top[0]) * v, top[1] + (bottom[1] - top[1]) * v)

    gu, gv = gap / cols, gap / rows
    for i in range(cols):
        for j in range(rows):
            u0, u1 = i / cols + gu / 2, (i + 1) / cols - gu / 2
            v0, v1 = j / rows + gv / 2, (j + 1) / rows - gv / 2
            pen.polygon((at(u0, v0), at(u1, v0), at(u1, v1), at(u0, v1)), fill)


def _inverter(pen: _Pen, box: Colour, wave: Colour) -> None:
    """Draw the inverter: a box around ~."""
    cx, cy, side = 0.13, 0.635, 0.22
    pen.box(cx, cy, side, side, 0.038, box)
    width, amplitude = 0.13, 0.033
    points = [
        (
            cx - width / 2 + width * k / 60,
            cy - amplitude * math.sin(2 * math.pi * k / 60),
        )
        for k in range(61)
    ]
    pen.stroke(points, 0.026, wave)


def _battery(pen: _Pen, body: Colour, cells: Colour) -> None:
    """Draw the battery: upright, four cells, its foot level with the inverter's."""
    w, h = 0.19 * 0.85, 0.31 * 0.85
    cx, cy = 0.355, 0.745 - h / 2
    pen.box(cx, cy, w, h, 0.032 * 0.85, body)
    cell, gap = 0.049 * 0.85, 0.019 * 0.85
    top = cy - (cell * 4 + gap * 3) / 2 + cell / 2
    for k in range(4):
        pen.box(cx, top + k * (cell + gap), w - 0.064 * 0.85, cell, 0.008, cells)


def _car(pen: _Pen, fill: Colour) -> None:
    """Draw the car beside them, windows and hubs cut out."""
    x, y, s = 0.49, 0.515, 0.48

    def at(px: float, py: float) -> tuple[float, float]:
        return (x + px * s, y + py * s)

    pen.polygon(tuple(at(px, py) for px, py in CAR_OUTLINE), fill)
    for window in CAR_WINDOWS:
        pen.polygon(tuple(at(px, py) for px, py in window), CLEAR)
    for wx in CAR_WHEELS:
        cx, cy = at(wx, 0.42)
        pen.disc(cx, cy, 0.115 * s, CLEAR)
        pen.disc(cx, cy, 0.085 * s, fill)
        pen.disc(cx, cy, 0.035 * s, CLEAR)


def draw_mark(size: int, palette: dict[str, Colour]) -> Image.Image:
    """Draw the mark at ``size`` pixels square, on transparency."""
    pen = _Pen(size)
    hardware, energy = palette["flow"], palette["sun"]
    _array(pen, hardware)
    _inverter(pen, hardware, energy)
    _battery(pen, hardware, energy)
    _car(pen, energy)
    return pen.image.resize((size, size), Image.LANCZOS)


#: The wide logo: the array on the left, then the inverter, the battery and
#: the car, generation to the car read left to right. Each part is drawn by the
#: same function as in the icon, placed again: (origin x, origin y, scale), in
#: units of the logo's height.
LOGO_ASPECT = 4.6
LOGO_ARRAY = (-0.20, 0.17, 2.0)
LOGO_ROW = (1.80, -1.087, 2.6)


def draw_logo(height: int, palette: dict[str, Colour]) -> Image.Image:
    """Draw the wide logo, ``height`` pixels high, trimmed to its content."""
    pen = _Pen(height, LOGO_ASPECT)
    hardware, energy = palette["flow"], palette["sun"]
    pen.place(*LOGO_ARRAY)
    _array(pen, hardware)
    pen.place(*LOGO_ROW)
    _inverter(pen, hardware, energy)
    _battery(pen, hardware, energy)
    _car(pen, energy)
    image = pen.image
    box = image.getbbox()
    if box is not None:
        image = image.crop(box)
    return image.resize(
        (round(image.width * height / image.height), height), Image.LANCZOS
    )


def render_logo(name: str, palette: dict[str, Colour]) -> list[Path]:
    """Write the logo at the brands repository's two heights, 256 and 512."""
    written = []
    master = draw_logo(1024, palette)
    for height, suffix in ((512, "@2x"), (256, "")):
        image = master.resize(
            (round(master.width * height / master.height), height), Image.LANCZOS
        )
        path = BRAND / f"{name}{suffix}.png"
        image.save(path, "PNG", optimize=True)
        written.append(path)
    return written


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
    written += render_logo("logo", LIGHT) + render_logo("dark_logo", DARK)

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
