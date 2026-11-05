"""
Minimal ComfyUI text-to-image client.

Usage:
    python generate_image.py "a glowing crystal cave, cinematic lighting" --out ./output
    python generate_image.py "portrait of a fox in armour" --workflow workflows/my_workflow.json

The workflow JSON must be exported from ComfyUI with "Save (API Format)".
The default workflow (workflows/flux2_klein_t2i.json) targets FLUX.2 Klein 4B.

Requires: Python 3.8+, no third-party packages.
"""

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_WORKFLOW = Path(__file__).parent / "workflows" / "sd15_retro_pixel.json"


def queue_prompt(workflow: dict, client_id: str) -> str:
    payload = json.dumps({"client_id": client_id, "prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["prompt_id"]


def wait_for_completion(prompt_id: str, poll_interval: float = 1.0, timeout: float = 300.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
            history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"Image generation timed out after {timeout}s")


def download_image(filename: str, subfolder: str, folder_type: str, dest_dir: Path) -> Path:
    params = urllib.parse.urlencode({
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type,
    })
    url = f"{COMFYUI_URL}/view?{params}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    with urllib.request.urlopen(url) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())
    return dest_path


def set_prompt_text(workflow: dict, prompt_text: str) -> dict:
    """Replace the positive prompt text in the workflow.

    Prefers a node whose _meta title contains 'positive'; falls back to the
    first CLIPTextEncode / CLIPTextEncodeFlux node found.
    """
    workflow = json.loads(json.dumps(workflow))  # deep copy
    text_encode_types = ("CLIPTextEncode", "CLIPTextEncodeFlux")
    candidate_node = None

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") not in text_encode_types:
            continue
        inputs = node.get("inputs", {})
        if "text" not in inputs:
            continue
        title = (node.get("_meta") or {}).get("title", "").lower()
        if "positive" in title or "pos" in title:
            # Definitive match — stop looking
            inputs["text"] = prompt_text
            return workflow
        if candidate_node is None:
            candidate_node = inputs

    if candidate_node is not None:
        candidate_node["text"] = prompt_text
        return workflow

    raise ValueError(
        "Could not find a CLIPTextEncode node in the workflow. "
        "Export the workflow from ComfyUI using Save (API Format) and check that it "
        "contains a text-encoding node."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an image with ComfyUI.")
    parser.add_argument("prompt", help="Text prompt for image generation")
    parser.add_argument("--out", default="./output", help="Output directory (default: ./output)")
    parser.add_argument("--workflow", default=str(DEFAULT_WORKFLOW), help="Workflow JSON file")
    parser.add_argument("--timeout", type=float, default=300.0, help="Max seconds to wait (default: 300)")
    args = parser.parse_args()

    workflow_path = Path(args.workflow)
    if not workflow_path.exists():
        print(f"ERROR: Workflow file not found: {workflow_path}", file=sys.stderr)
        print("Export a workflow from ComfyUI using Save (API Format) or see SETUP.md.", file=sys.stderr)
        sys.exit(1)

    workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    workflow = set_prompt_text(workflow, args.prompt)

    client_id = str(uuid.uuid4())
    print(f"Queuing prompt: {args.prompt!r}")

    try:
        prompt_id = queue_prompt(workflow, client_id)
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not reach ComfyUI at {COMFYUI_URL}: {exc}", file=sys.stderr)
        print("Make sure ComfyUI is running (see SETUP.md).", file=sys.stderr)
        sys.exit(1)

    print(f"Prompt queued (id={prompt_id}). Waiting for image…")
    result = wait_for_completion(prompt_id, timeout=args.timeout)

    outputs = result.get("outputs", {})
    saved = []
    for node_output in outputs.values():
        for img in node_output.get("images", []):
            path = download_image(
                filename=img["filename"],
                subfolder=img.get("subfolder", ""),
                folder_type=img.get("type", "output"),
                dest_dir=Path(args.out),
            )
            saved.append(path)
            print(f"Saved: {path}")

    if not saved:
        print("WARNING: Generation finished but no images were found in the output.", file=sys.stderr)
        sys.exit(1)

    print(f"Done. {len(saved)} image(s) saved to {Path(args.out).resolve()}")


if __name__ == "__main__":
    main()
