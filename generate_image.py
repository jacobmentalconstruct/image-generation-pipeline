"""
generate_image.py — CLI entry point for the image-generation pipeline.

Usage:
    python generate_image.py "a glowing crystal cave"
    python generate_image.py "a tavern at night" --style kleinbottle
    python generate_image.py "a forest path" --style projectmapper --out ./assets

The --style flag loads a profile from styles/<name>.json, which controls
prompt framing, LoRA strength, CFG, resolution, and more.
Omit --style to use styles/default.json.

Requires: Python 3.8+, no third-party packages.
ComfyUI must be running at http://127.0.0.1:8188.
"""

import argparse
import sys
import urllib.error
import uuid
from pathlib import Path

from pipeline.client import collect_images, queue_prompt, wait_for_completion
from pipeline.styles import build_workflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an image with ComfyUI.")
    parser.add_argument("prompt", help="Scene description (plain language)")
    parser.add_argument(
        "--style",
        default="default",
        help="Style profile name from styles/ (default: default)",
    )
    parser.add_argument(
        "--out",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Max seconds to wait for generation (default: 300)",
    )
    args = parser.parse_args()

    try:
        workflow, _ = build_workflow(args.prompt, args.style)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    client_id = str(uuid.uuid4())
    print(f"Style:  {args.style}")
    print(f"Prompt: {args.prompt!r}")

    try:
        prompt_id = queue_prompt(workflow, client_id)
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not reach ComfyUI: {exc}", file=sys.stderr)
        print("Make sure ComfyUI is running (Stability Matrix → Launch).", file=sys.stderr)
        sys.exit(1)

    print(f"Queued (id={prompt_id}). Waiting for image…")
    result = wait_for_completion(prompt_id, timeout=args.timeout)

    saved = collect_images(result, Path(args.out))
    if not saved:
        print("WARNING: Generation finished but no images were found.", file=sys.stderr)
        sys.exit(1)

    for path in saved:
        print(f"Saved:  {path}")
    print(f"Done.   {len(saved)} image(s) -> {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
