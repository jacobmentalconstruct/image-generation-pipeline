"""
modules/retro_monitor/generate_bezel.py

One-shot script: generate the monitor bezel PNG and write the default
screen_rect.json.  Run once with ComfyUI active; commit the outputs.

    python modules/retro_monitor/generate_bezel.py
    python modules/retro_monitor/generate_bezel.py --style kleinbottle
    python modules/retro_monitor/generate_bezel.py --out path/to/image.png

The script writes two files:
  modules/retro_monitor/assets/monitor_bezel.png
  modules/retro_monitor/assets/screen_rect.json

The JSON records where the screen region sits in the PNG so RetroMonitorFrame
can place the content widget there.  Tune the values manually if the
generated image puts the screen in a different position.
"""

import argparse
import json
import sys
import uuid
from pathlib import Path

_MODULE_ROOT   = Path(__file__).resolve().parent
_PIPELINE_ROOT = _MODULE_ROOT.parent.parent
_ASSETS        = _MODULE_ROOT / "assets"

if str(_PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_ROOT))

from pipeline.client import collect_images, queue_prompt, wait_for_completion
from pipeline.styles import build_workflow

# ------------------------------------------------------------------
# Prompt — tuned to produce a front-on CRT monitor with a clearly
# delineated dark screen area that RetroMonitorFrame can overlay.
# ------------------------------------------------------------------
_PROMPT = (
    "retro CRT computer monitor, 1980s IBM PC era, front view, perfectly centered, "
    "beige cream plastic housing, thick rectangular bezel, "
    "screen is a dark flat black rectangle inset in the center, "
    "subtle green phosphor glow on screen edges, power LED indicator, "
    "brand label below screen, isolated on solid black background, "
    "product photography style, clean hard edges, no reflections"
)

# Screen rect that works well for a centered 640×480 monitor illustration.
# Adjust x/y/width/height manually after inspecting the generated image.
_DEFAULT_RECT = {
    "x": 108,
    "y": 82,
    "width": 424,
    "height": 316,
    "_note": (
        "Tune x/y/width/height so the rect covers the monitor's dark screen area. "
        "Reload the demo after each change — no regeneration needed."
    ),
}


def generate(style: str, out_path: Path, timeout: float) -> Path:
    print(f"Style:   {style}")
    print(f"Prompt:  {_PROMPT[:80]}…")
    print("Queuing with ComfyUI…")

    workflow, _ = build_workflow(_PROMPT, style)
    client_id = str(uuid.uuid4())
    prompt_id = queue_prompt(workflow, client_id)
    print(f"Prompt id: {prompt_id}  — waiting (up to {timeout:.0f}s)…")

    result = wait_for_completion(prompt_id, timeout=timeout)
    saved = collect_images(result, out_path.parent)
    if not saved:
        raise RuntimeError("Generation finished but no images were returned.")

    # Rename to the canonical bezel filename
    if saved[0] != out_path:
        saved[0].rename(out_path)
    print(f"Bezel:   {out_path}")
    return out_path


def write_rect(rect_path: Path) -> None:
    rect_path.parent.mkdir(parents=True, exist_ok=True)
    rect_path.write_text(
        json.dumps(_DEFAULT_RECT, indent=2), encoding="utf-8"
    )
    print(f"Rect:    {rect_path}")
    print(
        "\nOpen the demo, inspect the monitor image, then adjust x/y/width/height\n"
        "in screen_rect.json so the rectangle covers the dark screen area.\n"
        "No re-generation needed — the frame re-reads the JSON on each launch."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate retro monitor bezel asset.")
    parser.add_argument("--style", default="default", help="Pipeline style profile")
    parser.add_argument(
        "--out",
        type=Path,
        default=_ASSETS / "monitor_bezel.png",
        help="Output PNG path (default: assets/monitor_bezel.png)",
    )
    parser.add_argument(
        "--timeout", type=float, default=300.0,
        help="Max seconds to wait for ComfyUI (default: 300)",
    )
    parser.add_argument(
        "--rect-only", action="store_true",
        help="Write screen_rect.json without generating a new image",
    )
    args = parser.parse_args()

    _ASSETS.mkdir(parents=True, exist_ok=True)
    rect_path = args.out.parent / "screen_rect.json"

    if not args.rect_only:
        try:
            generate(args.style, args.out, args.timeout)
        except Exception as exc:
            print(f"\nERROR: {exc}", file=sys.stderr)
            print(
                "Make sure ComfyUI is running (Stability Matrix → Launch).\n"
                "The demo works with the programmatic fallback while you wait.",
                file=sys.stderr,
            )
            sys.exit(1)

    write_rect(rect_path)


if __name__ == "__main__":
    main()
