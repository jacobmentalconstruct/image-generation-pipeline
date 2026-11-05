"""
modules/text_adventure/item_viewer.py

King's Quest-style item display for text adventures.

Generates an image for an in-game item via the ComfyUI pipeline, then
shows it in a Tkinter window with the classic era layout:
  - bordered image panel (top)
  - item name in a title bar
  - description text in a scrollable panel (bottom)

Usage from your text adventure:

    import sys
    sys.path.insert(0, "/path/to/image-generation-pipeline")
    from modules.text_adventure import show_item

    show_item(
        name="Ancient Amulet",
        description="A tarnished silver amulet inscribed with runes. "
                    "It hums faintly when you hold it.",
        style="default",   # pipeline style profile
    )

The window blocks until the player closes it, matching the KQ "examine item"
interaction model.  Call it in a thread if your adventure loop needs to stay
responsive while the image generates.

Requirements: Python 3.8+, tkinter (stdlib), Pillow (pip install pillow).
ComfyUI must be running at http://127.0.0.1:8188.
"""

from __future__ import annotations

import sys
import textwrap
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# tkinter — stdlib on all supported platforms; Pillow is pip-installable
# ---------------------------------------------------------------------------
import tkinter as tk

try:
    from PIL import Image, ImageTk  # type: ignore[import-untyped]
    _PILLOW = True
except ImportError:
    _PILLOW = False

# Pipeline lives two levels up from this file
_PIPELINE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_ROOT))

from pipeline.client import collect_images, queue_prompt, wait_for_completion
from pipeline.styles import build_workflow


# ---------------------------------------------------------------------------
# KQ-era palette (EGA-inspired, dark backgrounds with bright accents)
# ---------------------------------------------------------------------------
_PALETTE = {
    "bg":         "#0a0a1a",   # near-black background
    "panel_bg":   "#000000",   # image panel fill
    "border":     "#2255aa",   # CGA/EGA-style blue border
    "title_bg":   "#1133cc",   # title bar blue
    "title_fg":   "#ffffff",
    "text_bg":    "#000820",   # description area
    "text_fg":    "#aaccff",   # light blue text
    "scrollbar":  "#1133cc",
    "caption":    "#ffcc00",   # gold item name in description
    "busy_fg":    "#44ff44",   # green "generating…" indicator
}

# Display dimensions (pixels)
_WIN_W   = 640
_IMG_H   = 320
_DESC_H  = 160
_BORDER  = 6
_TITLE_H = 28


# ---------------------------------------------------------------------------
# Image generation (pipeline integration)
# ---------------------------------------------------------------------------

def generate_item_image(
    name: str,
    description: str,
    style: str = "default",
    out_dir: Optional[Path] = None,
    timeout: float = 300.0,
) -> Path:
    """
    Generate an image for a text-adventure item and return the saved path.

    The prompt is constructed from the item name + description so the model
    knows what to draw without the caller having to craft ComfyUI prompts.
    """
    if out_dir is None:
        out_dir = _PIPELINE_ROOT / "output" / "text_adventure"

    prompt = f"{name}, {description}, inventory item, isolated on black, detailed illustration"

    workflow, _ = build_workflow(prompt, style)
    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(workflow, client_id)
    result = wait_for_completion(prompt_id, timeout=timeout)
    saved = collect_images(result, out_dir)

    if not saved:
        raise RuntimeError("Generation completed but no images were returned.")
    return saved[0]


# ---------------------------------------------------------------------------
# Tkinter display
# ---------------------------------------------------------------------------

class ItemViewer:
    """
    Blocking Tkinter window that shows an item image with KQ-style chrome.

    Can be used in two modes:
      - generate=True  (default): triggers image generation then shows result
      - generate=False: supply image_path directly to skip generation
    """

    def __init__(
        self,
        name: str,
        description: str,
        style: str = "default",
        image_path: Optional[Path] = None,
        out_dir: Optional[Path] = None,
        timeout: float = 300.0,
    ) -> None:
        if not _PILLOW:
            raise ImportError("Pillow is required: pip install pillow")

        self.name = name
        self.description = description
        self.style = style
        self.image_path = image_path
        self.out_dir = out_dir
        self.timeout = timeout

        self._root: tk.Tk = None  # type: ignore
        self._photo: ImageTk.PhotoImage = None  # type: ignore
        self._status_var: tk.StringVar = None  # type: ignore

    # ------------------------------------------------------------------
    def show(self) -> None:
        """Build the window and block until it is closed."""
        self._root = tk.Tk()
        self._root.title(f"Examine: {self.name}")
        self._root.resizable(False, False)
        self._root.configure(bg=_PALETTE["bg"])

        self._build_chrome()

        if self.image_path and self.image_path.exists():
            self._display_image(self.image_path)
        else:
            self._start_generation()

        self._root.mainloop()

    # ------------------------------------------------------------------
    def _build_chrome(self) -> None:
        p = _PALETTE
        root = self._root

        # Outer frame (double border effect)
        outer = tk.Frame(root, bg=p["border"], bd=0)
        outer.pack(padx=_BORDER, pady=_BORDER)

        inner = tk.Frame(outer, bg=p["bg"], bd=0)
        inner.pack(padx=2, pady=2)

        # Title bar
        title_bar = tk.Frame(inner, bg=p["title_bg"], height=_TITLE_H)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        tk.Label(
            title_bar,
            text=f"  {self.name.upper()}  ",
            bg=p["title_bg"],
            fg=p["title_fg"],
            font=("Courier", 12, "bold"),
            anchor="w",
        ).pack(side="left", padx=4, pady=4)

        # Image canvas
        self._canvas = tk.Canvas(
            inner,
            width=_WIN_W - _BORDER * 4,
            height=_IMG_H,
            bg=p["panel_bg"],
            highlightthickness=0,
        )
        self._canvas.pack()

        # Status / busy label (shown during generation)
        self._status_var = tk.StringVar(value="Generating image…")
        self._status_label = tk.Label(
            inner,
            textvariable=self._status_var,
            bg=p["panel_bg"],
            fg=p["busy_fg"],
            font=("Courier", 10),
        )
        self._canvas.create_window(
            (_WIN_W - _BORDER * 4) // 2,
            _IMG_H // 2,
            window=self._status_label,
        )

        # Separator line
        tk.Frame(inner, bg=p["border"], height=2).pack(fill="x")

        # Description text area
        desc_frame = tk.Frame(inner, bg=p["text_bg"])
        desc_frame.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(desc_frame, bg=p["scrollbar"])
        scrollbar.pack(side="right", fill="y")

        self._text_widget = tk.Text(
            desc_frame,
            width=76,
            height=8,
            bg=p["text_bg"],
            fg=p["text_fg"],
            font=("Courier", 10),
            wrap="word",
            bd=0,
            highlightthickness=0,
            yscrollcommand=scrollbar.set,
            state="disabled",
            padx=10,
            pady=8,
        )
        self._text_widget.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self._text_widget.yview)

        # Insert description text
        self._text_widget.config(state="normal")
        self._text_widget.tag_configure("caption", foreground=p["caption"], font=("Courier", 10, "bold"))
        self._text_widget.insert("end", f"{self.name}\n", "caption")
        wrapped = textwrap.fill(self.description, width=72)
        self._text_widget.insert("end", "\n" + wrapped)
        self._text_widget.config(state="disabled")

        # Close hint
        tk.Label(
            inner,
            text="[ Press ENTER or close window to continue ]",
            bg=p["bg"],
            fg=p["border"],
            font=("Courier", 9),
        ).pack(pady=(0, 4))

        root.bind("<Return>", lambda _e: root.destroy())
        root.bind("<Escape>", lambda _e: root.destroy())

    # ------------------------------------------------------------------
    def _display_image(self, path: Path) -> None:
        """Load the image into the canvas, scaling to fit."""
        self._status_label.place_forget()
        self._status_var.set("")

        canvas_w = _WIN_W - _BORDER * 4
        canvas_h = _IMG_H

        img = Image.open(path)  # type: ignore[possibly-undefined]
        resample = getattr(Image, "Resampling", Image).LANCZOS  # type: ignore[possibly-undefined]
        img.thumbnail((canvas_w, canvas_h), resample)

        # Center on black canvas
        x = (canvas_w - img.width) // 2
        y = (canvas_h - img.height) // 2

        self._photo = ImageTk.PhotoImage(img)  # type: ignore[possibly-undefined]
        self._canvas.create_image(x, y, anchor="nw", image=self._photo)

    # ------------------------------------------------------------------
    def _start_generation(self) -> None:
        """Kick off image generation in a background thread."""
        self._animate_busy()

        def _worker() -> None:
            try:
                path = generate_item_image(
                    self.name,
                    self.description,
                    self.style,
                    self.out_dir,
                    self.timeout,
                )
                self._root.after(0, lambda: self._display_image(path))
            except Exception as exc:
                self._root.after(
                    0,
                    lambda: self._status_var.set(f"Error: {exc}"),
                )

        threading.Thread(target=_worker, daemon=True).start()

    def _animate_busy(self) -> None:
        """Cycle the status dot to show activity."""
        dots = ["Generating .  ", "Generating .. ", "Generating ..."]
        idx = [0]

        def _tick() -> None:
            if self._root.winfo_exists() and self._status_var.get().startswith("Gen"):
                self._status_var.set(dots[idx[0] % 3])
                idx[0] += 1
                self._root.after(500, _tick)

        self._root.after(500, _tick)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

def show_item(
    name: str,
    description: str,
    style: str = "default",
    image_path: Optional[Path] = None,
    out_dir: Optional[Path] = None,
    timeout: float = 300.0,
) -> None:
    """
    Generate (if needed) and display a KQ-style item viewer window.

    Blocks until the player dismisses the window.

    Args:
        name:        Item name shown in the title bar and description header.
        description: Flavour text shown in the description panel.
        style:       Pipeline style profile (default: "default").
        image_path:  Pre-generated image path; skips generation if supplied.
        out_dir:     Where to save generated images (default: output/text_adventure/).
        timeout:     Max seconds to wait for ComfyUI (default: 300).
    """
    viewer = ItemViewer(
        name=name,
        description=description,
        style=style,
        image_path=image_path,
        out_dir=out_dir,
        timeout=timeout,
    )
    viewer.show()
