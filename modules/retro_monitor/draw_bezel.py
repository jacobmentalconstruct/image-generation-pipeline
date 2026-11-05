"""
modules/retro_monitor/draw_bezel.py

Draw a clean retro CRT monitor bezel using Pillow and save it as
assets/monitor_bezel.png.  Also writes assets/screen_rect.json with
the exact pixel coordinates of the screen cutout — no calibration needed.

Run once; commit the outputs.

    python modules/retro_monitor/draw_bezel.py
    python modules/retro_monitor/draw_bezel.py --width 640 --height 480
    python modules/retro_monitor/draw_bezel.py --style green   # green | amber | white

No ComfyUI needed.  Requires: pip install pillow
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter  # type: ignore[import-untyped]
except ImportError:
    print("Pillow is required:  pip install pillow", file=sys.stderr)
    sys.exit(1)

_ASSETS = Path(__file__).parent / "assets"

# ---------------------------------------------------------------------------
# Colour palettes
# ---------------------------------------------------------------------------
STYLES: dict[str, dict[str, str]] = {
    "green": {
        "screen":        "#020a02",
        "screen_glow":   "#061506",
        "glow_edge":     "#0a2a0a",
        "led":           "#00dd33",
        "led_halo":      "#003311",
    },
    "amber": {
        "screen":        "#0a0500",
        "screen_glow":   "#150a00",
        "glow_edge":     "#2a1200",
        "led":           "#ff8800",
        "led_halo":      "#331a00",
    },
    "white": {
        "screen":        "#020408",
        "screen_glow":   "#050810",
        "glow_edge":     "#0a1020",
        "led":           "#44aaff",
        "led_halo":      "#001133",
    },
}

# Bezel body colours (shared across styles — classic cream/putty plastic)
_BEZEL_FACE    = "#c8bfa0"   # main face
_BEZEL_LIGHT   = "#ddd4b2"   # top/left highlight edge
_BEZEL_SHADOW  = "#8a8068"   # bottom/right shadow edge
_BEZEL_INNER   = "#a09880"   # inset inner bevel
_BEZEL_CORNER  = "#b0a888"   # rounded corner fill
_BG            = "#000000"   # canvas background (pure black — no scene)
_BRAND_COLOR   = "#706858"   # brand text
_BRAND_TEXT    = "KleinOS"


def draw_bezel(
    width: int = 480,
    height: int = 360,
    bevel: int = 36,          # outer bezel thickness
    inset: int = 8,           # inner inset shadow depth
    screen_style: str = "green",
) -> tuple[Image.Image, dict[str, int]]:
    """
    Draw a CRT bezel and return (image, screen_rect).

    screen_rect is the exact pixel bounding box of the dark screen area
    — ready to drop into screen_rect.json.
    """
    colors = STYLES.get(screen_style, STYLES["green"])

    img = Image.new("RGB", (width, height), _BG)
    d = ImageDraw.Draw(img)

    # ------------------------------------------------------------------
    # Outer bezel body
    # ------------------------------------------------------------------
    corner_r = 12
    # Main face
    d.rounded_rectangle(
        [0, 0, width - 1, height - 1],
        radius=corner_r,
        fill=_BEZEL_FACE,
        outline=_BEZEL_SHADOW,
        width=2,
    )

    # Top/left highlight (simulate lighting from top-left)
    for i in range(4):
        alpha = 180 - i * 40
        d.rounded_rectangle(
            [i, i, width - 1 - i, height - 1 - i],
            radius=max(2, corner_r - i),
            outline=_BEZEL_LIGHT if i < 2 else _BEZEL_SHADOW,
            width=1,
        )

    # ------------------------------------------------------------------
    # Screen inset region (the cutout)
    # ------------------------------------------------------------------
    sx = bevel
    sy = bevel
    sw = width  - bevel * 2
    sh = height - bevel * 2

    # Outer shadow ring around screen inset
    for i in range(inset, 0, -1):
        shade = max(0, 90 - i * 8)
        d.rectangle(
            [sx - i, sy - i, sx + sw + i, sy + sh + i],
            outline=f"#{shade:02x}{shade:02x}{shade:02x}",
        )

    # Inset face bevel
    d.rectangle(
        [sx - inset, sy - inset, sx + sw + inset, sy + sh + inset],
        fill=_BEZEL_INNER,
    )
    d.rectangle(
        [sx - 2, sy - 2, sx + sw + 2, sy + sh + 2],
        fill="#303030",
    )

    # Screen face — dark base
    d.rectangle([sx, sy, sx + sw, sy + sh], fill=colors["screen"])

    # Subtle phosphor glow — thin gradient band at top of screen
    for i in range(12):
        t = i / 12
        r1, g1, b1 = (
            int(x, 16)
            for x in (
                colors["glow_edge"][1:3],
                colors["glow_edge"][3:5],
                colors["glow_edge"][5:7],
            )
        )
        r0, g0, b0 = (
            int(x, 16)
            for x in (
                colors["screen"][1:3],
                colors["screen"][3:5],
                colors["screen"][5:7],
            )
        )
        band_color = (
            int(r1 + (r0 - r1) * t),
            int(g1 + (g0 - g1) * t),
            int(b1 + (b0 - b1) * t),
        )
        d.line(
            [sx, sy + i, sx + sw, sy + i],
            fill=band_color,
        )

    # Scanline texture — very subtle horizontal lines every 2px
    for y in range(sy, sy + sh, 2):
        d.line([sx, y, sx + sw, y], fill=(0, 0, 0, 20))

    # ------------------------------------------------------------------
    # Bezel details
    # ------------------------------------------------------------------
    # Brand text below screen
    brand_y = sy + sh + inset + 6
    if brand_y + 10 < height - 4:
        d.text(
            (width // 2, brand_y),
            _BRAND_TEXT,
            fill=_BRAND_COLOR,
            anchor="mt",
        )

    # Power LED — bottom-right of bezel
    led_cx = width - bevel // 2 - 2
    led_cy = height - bevel // 2 - 2
    led_r = 5
    d.ellipse(
        [led_cx - led_r - 2, led_cy - led_r - 2,
         led_cx + led_r + 2, led_cy + led_r + 2],
        fill=colors["led_halo"],
    )
    d.ellipse(
        [led_cx - led_r, led_cy - led_r,
         led_cx + led_r, led_cy + led_r],
        fill=colors["led"],
    )

    # Vent slots — bottom-left corner decoration
    for i in range(4):
        vx = bevel // 2 + i * 7
        d.rectangle(
            [vx, height - bevel + 10, vx + 4, height - bevel + 20],
            fill=_BEZEL_SHADOW,
        )

    # Apply a very mild blur to soften the edges slightly
    img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    screen_rect = {"x": sx, "y": sy, "width": sw, "height": sh}
    return img, screen_rect


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw retro CRT bezel asset.")
    parser.add_argument("--width",  type=int, default=480, help="Canvas width  (default 480)")
    parser.add_argument("--height", type=int, default=360, help="Canvas height (default 360)")
    parser.add_argument("--bevel",  type=int, default=36,  help="Bezel thickness in px (default 36)")
    parser.add_argument(
        "--style", choices=list(STYLES.keys()), default="green",
        help="Screen phosphor colour (default: green)",
    )
    parser.add_argument(
        "--out", type=Path, default=_ASSETS / "monitor_bezel.png",
        help="Output PNG path",
    )
    args = parser.parse_args()

    _ASSETS.mkdir(parents=True, exist_ok=True)
    rect_path = args.out.parent / "screen_rect.json"

    img, screen_rect = draw_bezel(
        width=args.width,
        height=args.height,
        bevel=args.bevel,
        screen_style=args.style,
    )

    img.save(args.out, "PNG")
    print(f"Bezel:  {args.out}  ({args.width}×{args.height})")

    screen_rect["_note"] = (
        "Generated by draw_bezel.py — coordinates are exact. "
        "Re-run draw_bezel.py to regenerate both files together."
    )
    rect_path.write_text(json.dumps(screen_rect, indent=2), encoding="utf-8")
    print(f"Rect:   {rect_path}  (screen at x={screen_rect['x']}, y={screen_rect['y']}, "
          f"{screen_rect['width']}×{screen_rect['height']})")
    print("Done.  No calibration needed.")


if __name__ == "__main__":
    main()
