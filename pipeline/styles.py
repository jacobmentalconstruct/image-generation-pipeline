"""
Style profile loader and workflow injector.

A style profile is a JSON file in the styles/ directory that captures every
parameter needed to reproduce a consistent visual look:
  - which workflow to use
  - prompt prefix and suffix (trigger words, style keywords)
  - negative prompt
  - LoRA strength, CFG, steps, resolution

apply_style() injects all of these into a loaded workflow dict before it is
submitted to ComfyUI, so callers only need to supply the scene description.
"""

import json
from pathlib import Path

STYLES_DIR = Path(__file__).parent.parent / "styles"
WORKFLOWS_DIR = Path(__file__).parent.parent / "workflows"


def load_style(name: str) -> dict:
    """
    Load a style profile by name (e.g. "kleinbottle") or path.
    Falls back to 'default' if the named profile doesn't exist.
    """
    candidate = Path(name)
    if candidate.suffix == ".json" and candidate.exists():
        path = candidate
    else:
        path = STYLES_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Style '{name}' not found at {path}.\n"
                f"Available styles: {[p.stem for p in STYLES_DIR.glob('*.json')]}"
            )
    return json.loads(path.read_text(encoding="utf-8"))


def load_workflow_for_style(style: dict) -> dict:
    """Load the workflow JSON referenced by a style profile."""
    workflow_path = WORKFLOWS_DIR / style["workflow"]
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow not found: {workflow_path}")
    return json.loads(workflow_path.read_text(encoding="utf-8"))


def apply_style(workflow: dict, style: dict, user_prompt: str) -> dict:
    """
    Inject style parameters into a workflow dict.

    The user_prompt is the plain scene description ("a forest path at dusk").
    The style profile wraps it with trigger words, style keywords, and sets
    all sampler/model parameters.

    Returns a new workflow dict ready to submit to ComfyUI.
    """
    workflow = json.loads(json.dumps(workflow))  # deep copy

    prefix = style.get("prompt_prefix", "").strip()
    suffix = style.get("prompt_suffix", "").strip()
    full_prompt = ", ".join(filter(None, [prefix, user_prompt.strip(), suffix]))

    negative = style.get("negative_prompt", "")
    lora_strength = style.get("lora_strength")
    cfg = style.get("cfg")
    steps = style.get("steps")
    gen_width = style.get("width")
    gen_height = style.get("height")
    out_width = style.get("output_width")
    out_height = style.get("output_height")
    filename_prefix = style.get("filename_prefix")

    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        cls = node.get("class_type", "")
        inputs = node.get("inputs", {})
        title = (node.get("_meta") or {}).get("title", "").lower()

        if cls in ("CLIPTextEncode", "CLIPTextEncodeFlux"):
            if "positive" in title or "pos" in title:
                inputs["text"] = full_prompt
            elif "negative" in title or "neg" in title:
                if negative:
                    inputs["text"] = negative

        elif cls == "KSampler":
            if cfg is not None:
                inputs["cfg"] = cfg
            if steps is not None:
                inputs["steps"] = steps

        elif cls == "LoraLoader":
            if lora_strength is not None:
                inputs["strength_model"] = lora_strength
                inputs["strength_clip"] = lora_strength

        elif cls == "EmptyLatentImage":
            if gen_width is not None:
                inputs["width"] = gen_width
            if gen_height is not None:
                inputs["height"] = gen_height

        elif cls == "ImageScale":
            if out_width is not None:
                inputs["width"] = out_width
            if out_height is not None:
                inputs["height"] = out_height

        elif cls == "SaveImage":
            if filename_prefix:
                inputs["filename_prefix"] = filename_prefix

    return workflow


def build_workflow(user_prompt: str, style_name: str = "default") -> tuple[dict, dict]:
    """
    Convenience function: load a style and return (workflow, style).
    The workflow is fully configured and ready to queue.
    """
    style = load_style(style_name)
    workflow = load_workflow_for_style(style)
    workflow = apply_style(workflow, style, user_prompt)
    return workflow, style
