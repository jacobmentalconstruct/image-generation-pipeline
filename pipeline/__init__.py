"""
image-generation-pipeline — public API

External applications need two functions:

    from pipeline import generate, to_ascii

    path = generate("a tavern at night", style="kleinbottle")
    paths = generate("a forest", style="default", out_dir="./assets", cfg=2.5)

    text = to_ascii("render.png", width=120, iterations=200)

ComfyUI must be running at http://127.0.0.1:8188 for `generate`.
`to_ascii` works offline; it only requires PIL and PyTorch.
"""

import uuid
from pathlib import Path

from .client import collect_images, queue_prompt, wait_for_completion
from .styles import load_style, load_workflow_for_style, apply_style


def to_ascii(
    image_path: "str | Path",
    width: int = 120,
    iterations: int = 200,
    charset: str = "@%#*+=-:. ",
) -> str:
    """
    Convert an image to ASCII art via gradient descent.

    Lazy wrapper — imports convert (which requires torch + numpy) only when
    called, so plain image generation works without those ML dependencies.
    """
    from .convert import to_ascii as _impl
    return _impl(image_path, width=width, iterations=iterations, charset=charset)


def generate(
    prompt: str,
    style: str = "default",
    out_dir: str | Path = "./output",
    timeout: float = 300.0,
    # --- per-call overrides (take precedence over the style profile) ----------
    cfg: float | None = None,
    steps: int | None = None,
    lora_strength: float | None = None,
    width: int | None = None,
    height: int | None = None,
    output_width: int | None = None,
    output_height: int | None = None,
) -> list[Path]:
    """
    Generate one or more images and return their saved paths.

    Parameters
    ----------
    prompt          Plain-language scene description ("a moonlit harbour").
    style           Name of a profile in styles/ ("kleinbottle", "default", …)
                    or a path to a custom .json file.
    out_dir         Directory to save PNGs into. Created if it doesn't exist.
    timeout         Seconds to wait before raising TimeoutError.
    cfg / steps / lora_strength / width / height / output_width / output_height
                    Optional per-call overrides. When provided, these values
                    replace whatever the style profile specifies for this call
                    only — the profile file is not modified.

    Returns
    -------
    List of Path objects for every saved PNG (usually one).

    Raises
    ------
    FileNotFoundError   Style profile or workflow file not found.
    TimeoutError        Generation did not complete within `timeout` seconds.
    urllib.error.URLError  ComfyUI is not reachable.
    """
    # Build style with any per-call overrides applied
    style_data = load_style(style)
    overrides = {
        k: v for k, v in {
            "cfg": cfg,
            "steps": steps,
            "lora_strength": lora_strength,
            "width": width,
            "height": height,
            "output_width": output_width,
            "output_height": output_height,
        }.items() if v is not None
    }
    style_data = {**style_data, **overrides}

    workflow = load_workflow_for_style(style_data)
    workflow = apply_style(workflow, style_data, prompt)

    prompt_id = queue_prompt(workflow, str(uuid.uuid4()))
    result = wait_for_completion(prompt_id, timeout=timeout)
    return collect_images(result, Path(out_dir))
