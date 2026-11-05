"""
modules/retro_monitor/frame.py

RetroMonitorFrame — a generic Tkinter container that wraps any child widget
in a retro CRT monitor illustration.

The bezel is a PNG image. The screen region is defined by screen_rect.json
in the same assets directory. The caller places their content widget in the
`screen` Frame attribute, which sits at the exact screen coordinates on top
of the bezel image.

Runtime dependencies: Python 3.8+, tkinter (stdlib), Pillow (pip install pillow).
No dependency on ComfyUI, the image-generation pipeline, or KleinBOTTLE.

Usage:
    root = tk.Tk()
    monitor = RetroMonitorFrame(root)
    monitor.pack()

    # Put anything you like inside the screen area
    MyWidget(monitor.screen).pack(fill="both", expand=True)
    root.mainloop()

If monitor_bezel.png is absent the frame renders a programmatic CRT shape so
the demo works immediately without requiring a generation run.
"""

from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageTk  # type: ignore[import-untyped]
    _PILLOW = True
except ImportError:
    _PILLOW = False

_ASSETS = Path(__file__).parent / "assets"
_DEFAULT_BEZEL = _ASSETS / "monitor_bezel.png"
_DEFAULT_RECT  = _ASSETS / "screen_rect.json"

# Programmatic fallback palette — CRT in gunmetal grey
_BEZEL_OUTER  = "#6b6b6b"
_BEZEL_MID    = "#8a8a8a"
_BEZEL_INNER  = "#3a3a3a"
_SCREEN_COLOR = "#0a0f0a"
_SCREEN_GLOW  = "#0d1a0d"
_BRAND_TEXT   = "KleinOS"


class RetroMonitorFrame(tk.Frame):
    """
    A tk.Frame that renders a retro CRT monitor bezel and exposes a `screen`
    child Frame at the monitor's display area.

    Parameters
    ----------
    parent      : tk parent widget
    asset_dir   : directory containing monitor_bezel.png and screen_rect.json;
                  defaults to modules/retro_monitor/assets/
    bezel_path  : override path for the bezel PNG
    rect_path   : override path for the screen_rect JSON
    fallback_w  : canvas width used when no PNG is available (default 640)
    fallback_h  : canvas height used when no PNG is available (default 480)
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        asset_dir: Optional[Path] = None,
        bezel_path: Optional[Path] = None,
        rect_path: Optional[Path] = None,
        fallback_w: int = 640,
        fallback_h: int = 480,
        **kw: object,
    ) -> None:
        super().__init__(parent, bd=0, highlightthickness=0, **kw)  # type: ignore[arg-type]

        assets = Path(asset_dir) if asset_dir else _ASSETS
        self._bezel_path = Path(bezel_path) if bezel_path else assets / "monitor_bezel.png"
        self._rect_path  = Path(rect_path)  if rect_path  else assets / "screen_rect.json"

        self._photo: Optional[ImageTk.PhotoImage] = None  # keep ref to prevent GC

        rect = self._load_rect()

        if _PILLOW and self._bezel_path.exists():
            canvas_w, canvas_h, rect = self._prepare_image_bezel(rect)
        else:
            canvas_w, canvas_h = fallback_w, fallback_h
            rect = self._clamp_rect(rect, canvas_w, canvas_h)
            self._canvas = tk.Canvas(
                self, width=canvas_w, height=canvas_h,
                bg="#2a2a2a", bd=0, highlightthickness=0,
            )
            self._draw_fallback(canvas_w, canvas_h, rect)

        self._canvas.pack()

        # The screen Frame is the publicly useful surface — callers pack their
        # content widgets into it.
        self.screen = tk.Frame(
            self._canvas,
            width=rect["width"],
            height=rect["height"],
            bg=_SCREEN_COLOR,
            bd=0,
            highlightthickness=0,
        )
        self.screen.pack_propagate(False)
        self._canvas.create_window(
            rect["x"], rect["y"],
            anchor="nw",
            width=rect["width"],
            height=rect["height"],
            window=self.screen,
        )

    # ------------------------------------------------------------------
    # Asset loading
    # ------------------------------------------------------------------

    def _load_rect(self) -> dict[str, int]:
        """Return screen_rect dict, falling back to sensible defaults."""
        if self._rect_path.exists():
            try:
                data = json.loads(self._rect_path.read_text(encoding="utf-8"))
                return {k: int(data[k]) for k in ("x", "y", "width", "height")}
            except (ValueError, KeyError, OSError):
                pass
        # Sensible default for a 640×480 image
        return {"x": 108, "y": 82, "width": 424, "height": 316}

    def _prepare_image_bezel(self, rect: dict[str, int]) -> tuple[int, int, dict[str, int]]:
        """Load the PNG, build a PhotoImage, create the canvas, draw the image."""
        img = Image.open(self._bezel_path)
        self._photo = ImageTk.PhotoImage(img)
        canvas_w, canvas_h = img.width, img.height
        self._canvas = tk.Canvas(
            self, width=canvas_w, height=canvas_h,
            bd=0, highlightthickness=0,
        )
        self._canvas.create_image(0, 0, anchor="nw", image=self._photo)
        return canvas_w, canvas_h, self._clamp_rect(rect, canvas_w, canvas_h)

    @staticmethod
    def _clamp_rect(rect: dict[str, int], w: int, h: int) -> dict[str, int]:
        x = max(0, min(rect["x"], w - 1))
        y = max(0, min(rect["y"], h - 1))
        return {
            "x": x,
            "y": y,
            "width":  min(rect["width"],  w - x),
            "height": min(rect["height"], h - y),
        }

    # ------------------------------------------------------------------
    # Programmatic fallback bezel (no Pillow / no PNG)
    # ------------------------------------------------------------------

    def _draw_fallback(self, w: int, h: int, rect: dict[str, int]) -> None:
        """Draw a simple but recognisable CRT monitor onto the canvas."""
        c = self._canvas
        bw = 28     # bezel width
        leg_w = 90
        leg_h = 22
        base_h = 14
        cx = w // 2

        # Stand base
        c.create_rectangle(
            cx - leg_w, h - base_h, cx + leg_w, h,
            fill="#555", outline="#333", width=2,
        )
        # Stand column
        c.create_rectangle(
            cx - 18, h - base_h - leg_h, cx + 18, h - base_h,
            fill="#666", outline="#333", width=2,
        )

        body_bottom = h - base_h - leg_h
        # Outer bezel body
        c.create_rectangle(
            bw, bw, w - bw, body_bottom,
            fill=_BEZEL_MID, outline=_BEZEL_OUTER, width=3,
        )
        # Recessed inner bevel
        c.create_rectangle(
            bw + 10, bw + 10, w - bw - 10, body_bottom - 10,
            fill=_BEZEL_INNER, outline="#222", width=2,
        )
        # Screen area (use rect coords)
        sx, sy = rect["x"], rect["y"]
        sw, sh = rect["width"], rect["height"]
        c.create_rectangle(
            sx, sy, sx + sw, sy + sh,
            fill=_SCREEN_COLOR, outline="#111", width=2,
        )
        # Subtle phosphor glow — lighter strip at top
        c.create_rectangle(
            sx + 2, sy + 2, sx + sw - 2, sy + 24,
            fill=_SCREEN_GLOW, outline="",
        )
        # Brand label below screen
        c.create_text(
            cx, body_bottom - 16,
            text=_BRAND_TEXT,
            fill="#aaa", font=("Helvetica", 8),
        )
        # Power LED
        c.create_oval(
            w - bw - 24, body_bottom - 26,
            w - bw - 14, body_bottom - 16,
            fill="#00cc44", outline="#005522",
        )
