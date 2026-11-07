"""
ASCII-art converter using gradient-descent character fitting (gradscii approach).

Public API
----------
    from pipeline.convert import to_ascii
    text = to_ascii("path/to/image.png", width=120, iterations=200)

The function is also re-exported from the pipeline package root so callers
that already have the pipeline root on sys.path can do:

    from pipeline import to_ascii
"""

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

_LANCZOS = getattr(getattr(Image, "Resampling", Image), "LANCZOS")

# ---------------------------------------------------------------------------
# Character palette — roughly ordered dark → light for the initial mapping.
# Fine-grained ranking is refined during optimisation.
# ---------------------------------------------------------------------------
_CHARSET = (
    "@%#*+=-:. "
)

# Monospace glyph footprint used to rasterise each character (pixels).
_CHAR_H = 16
_CHAR_W = 8


def _build_glyph_atlas(charset: str, char_h: int, char_w: int) -> torch.Tensor:
    """
    Rasterise every character in *charset* to a (N, char_h, char_w) float32
    tensor of normalised luminance values using PIL's default bitmap font.
    """
    from PIL import ImageDraw, ImageFont

    try:
        font = ImageFont.truetype("cour.ttf", char_h)
    except OSError:
        font = ImageFont.load_default()

    glyphs = []
    for ch in charset:
        img = Image.new("L", (char_w, char_h), color=0)
        draw = ImageDraw.Draw(img)
        draw.text((0, 0), ch, fill=255, font=font)
        glyphs.append(torch.from_numpy(np.array(img, dtype=np.float32)).reshape(char_h, char_w) / 255.0)

    return torch.stack(glyphs)   # (N, H, W)


def _load_as_luma(image_path: str | Path, cols: int, char_h: int, char_w: int) -> torch.Tensor:
    """
    Open *image_path*, resize so it fits *cols* columns of monospace glyphs,
    convert to luminance, and return a (rows, cols) float32 tensor.
    """
    img = Image.open(image_path).convert("L")
    rows = max(1, round(img.height * cols * char_w / (img.width * char_h)))
    img = img.resize((cols * char_w, rows * char_h), _LANCZOS)
    t = torch.from_numpy(np.array(img, dtype=np.float32)).reshape(rows * char_h, cols * char_w) / 255.0
    return t  # (rows*char_h, cols*char_w)


def to_ascii(
    image_path: str | Path,
    width: int = 120,
    iterations: int = 200,
    charset: str = _CHARSET,
) -> str:
    """
    Convert an image to an ASCII-art string via gradient-descent character fitting.

    Parameters
    ----------
    image_path  Path to any PIL-readable image file.
    width       Number of character columns in the output (default 120).
    iterations  Gradient-descent steps used to refine character assignments.
    charset     Characters to choose from, roughly dark-to-light.

    Returns
    -------
    A multi-line string where each line is ``width`` characters wide.
    """
    atlas = _build_glyph_atlas(charset, _CHAR_H, _CHAR_W)  # (N, H, W)
    n_chars = atlas.shape[0]

    target = _load_as_luma(image_path, width, _CHAR_H, _CHAR_W)  # (rows*H, cols*W)
    rows = target.shape[0] // _CHAR_H
    cols = target.shape[1] // _CHAR_W

    # Reshape target into (rows*cols, H*W) patch vectors
    patches = (
        target
        .reshape(rows, _CHAR_H, cols, _CHAR_W)
        .permute(0, 2, 1, 3)
        .reshape(rows * cols, _CHAR_H * _CHAR_W)
    )

    # Atlas as (N, H*W)
    flat_atlas = atlas.reshape(n_chars, _CHAR_H * _CHAR_W)

    # Soft assignment logits: one per (cell, character)
    logits = torch.zeros(rows * cols, n_chars, requires_grad=True)

    # Warm-start: pick the glyph whose average luminance is closest to each patch
    with torch.no_grad():
        patch_mean = patches.mean(dim=1, keepdim=True)       # (cells, 1)
        glyph_mean = flat_atlas.mean(dim=1).unsqueeze(0)     # (1, N)
        best = (patch_mean - glyph_mean).abs().argmin(dim=1) # (cells,)
        logits.data[torch.arange(rows * cols), best] = 2.0

    optimiser = torch.optim.Adam([logits], lr=0.05)

    for _ in range(iterations):
        weights = F.softmax(logits, dim=1)                    # (cells, N)
        composed = weights @ flat_atlas                       # (cells, H*W)
        loss = F.mse_loss(composed, patches)
        optimiser.zero_grad()
        loss.backward()
        optimiser.step()

    # Hard assignment: take argmax of final logits
    chosen = logits.detach().argmax(dim=1).reshape(rows, cols)  # (rows, cols)

    lines = []
    for r in range(rows):
        lines.append("".join(charset[int(chosen[r, c].item())] for c in range(cols)))
    return "\n".join(lines)
