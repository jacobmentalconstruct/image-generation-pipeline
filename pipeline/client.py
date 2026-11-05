"""
ComfyUI HTTP client — raw API operations.

All network calls go through here. Import this module; do not call
the ComfyUI API directly from generate_image.py or dial_in.py.
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"


def queue_prompt(workflow: dict, client_id: str) -> str:
    """POST a workflow to ComfyUI and return the prompt_id."""
    payload = json.dumps({"client_id": client_id, "prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["prompt_id"]


def wait_for_completion(
    prompt_id: str,
    poll_interval: float = 1.0,
    timeout: float = 300.0,
) -> dict:
    """Poll /history until the job is done; return the history entry."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with urllib.request.urlopen(f"{COMFYUI_URL}/history/{prompt_id}") as resp:
            history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(poll_interval)
    raise TimeoutError(f"Generation timed out after {timeout}s (id={prompt_id})")


def download_image(
    filename: str,
    subfolder: str,
    folder_type: str,
    dest_dir: Path,
) -> Path:
    """Download one generated image and save it to dest_dir."""
    params = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": folder_type}
    )
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename
    with urllib.request.urlopen(f"{COMFYUI_URL}/view?{params}") as resp:
        dest_path.write_bytes(resp.read())
    return dest_path


def collect_images(result: dict, dest_dir: Path) -> list[Path]:
    """Extract all output images from a completed history entry and download them."""
    saved = []
    for node_output in result.get("outputs", {}).values():
        for img in node_output.get("images", []):
            path = download_image(
                filename=img["filename"],
                subfolder=img.get("subfolder", ""),
                folder_type=img.get("type", "output"),
                dest_dir=dest_dir,
            )
            saved.append(path)
    return saved
