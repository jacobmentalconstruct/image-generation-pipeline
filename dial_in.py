"""
dial_in.py — Style tuning helper.

Generates a comparison grid of images at different LoRA strengths and CFG values
so you can see the effect of each parameter side by side, then lock in the values
that look best to your styles/<name>.json.

Usage:
    python dial_in.py "a tavern at night" --style kleinbottle
    python dial_in.py "a forest path" --style default --lora 0.8 1.0 1.2 --cfg 2.5 3.5

Images are saved to output/dial_in/<style>/ with parameter values in the filename.
When you find the combo you want, copy those values into styles/<name>.json and commit.

Requires: Python 3.8+, no third-party packages.
ComfyUI must be running at http://127.0.0.1:8188.
"""

import argparse
import sys
import urllib.error
import uuid
from pathlib import Path

from pipeline.client import collect_images, queue_prompt, wait_for_completion
from pipeline.styles import load_style, load_workflow_for_style, apply_style

DEFAULT_LORA_STRENGTHS = [0.85, 1.0, 1.15, 1.3]
DEFAULT_CFG_VALUES     = [2.5, 3.5, 5.0]


def run_variation(
    base_prompt: str,
    style_name: str,
    lora_strength: float,
    cfg: float,
    out_dir: Path,
    timeout: float,
) -> Path | None:
    """Generate one image at the given parameter values and return its path."""
    style = load_style(style_name)
    style["lora_strength"] = lora_strength
    style["cfg"] = cfg
    style["filename_prefix"] = f"dial_lora{lora_strength:.2f}_cfg{cfg:.1f}"

    workflow = load_workflow_for_style(style)
    workflow = apply_style(workflow, style, base_prompt)

    try:
        prompt_id = queue_prompt(workflow, str(uuid.uuid4()))
    except urllib.error.URLError as exc:
        print(f"  ERROR reaching ComfyUI: {exc}", file=sys.stderr)
        return None

    result = wait_for_completion(prompt_id, timeout=timeout)
    saved = collect_images(result, out_dir)
    return saved[0] if saved else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a style tuning comparison grid.")
    parser.add_argument("prompt", help="Scene description to use across all variations")
    parser.add_argument(
        "--style",
        default="default",
        help="Base style profile to tune (default: default)",
    )
    parser.add_argument(
        "--lora",
        nargs="+",
        type=float,
        default=DEFAULT_LORA_STRENGTHS,
        metavar="STRENGTH",
        help=f"LoRA strength values to test (default: {DEFAULT_LORA_STRENGTHS})",
    )
    parser.add_argument(
        "--cfg",
        nargs="+",
        type=float,
        default=DEFAULT_CFG_VALUES,
        metavar="CFG",
        help=f"CFG values to test (default: {DEFAULT_CFG_VALUES})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Max seconds per image (default: 120)",
    )
    args = parser.parse_args()

    out_dir = Path("output") / "dial_in" / args.style
    total = len(args.lora) * len(args.cfg)

    print(f"\nDial-in grid: {total} images")
    print(f"  Style:  {args.style}")
    print(f"  Prompt: {args.prompt!r}")
    print(f"  LoRA strengths: {args.lora}")
    print(f"  CFG values:     {args.cfg}")
    print(f"  Output: {out_dir.resolve()}\n")

    results = []
    n = 0
    for lora in args.lora:
        for cfg in args.cfg:
            n += 1
            label = f"lora={lora:.2f}  cfg={cfg:.1f}"
            print(f"  [{n}/{total}]  {label} … ", end="", flush=True)
            path = run_variation(args.prompt, args.style, lora, cfg, out_dir, args.timeout)
            if path:
                print(f"→ {path.name}")
                results.append({"lora": lora, "cfg": cfg, "file": str(path)})
            else:
                print("FAILED")

    print(f"\nDone. {len(results)}/{total} images saved to {out_dir.resolve()}")
    print("\nTo lock in settings, edit styles/{}.json with your preferred values".format(args.style))
    print("then run: git add styles/{}.json && git commit -m 'style: lock {} look'".format(
        args.style, args.style
    ))


if __name__ == "__main__":
    main()
