# Local Image Generation — Setup & Usage

Locally hosted text-to-image pipeline using **Stability Matrix → ComfyUI → FLUX.2 Klein 4B**.  
No cloud APIs. GPU inference only. HTTP API on `http://127.0.0.1:8188`.

---

## Requirements

| Item | Minimum |
|------|---------|
| GPU  | NVIDIA with ≥ 13 GB VRAM (RTX 3090 / 4080 / 4090 …) |
| VRAM note | FLUX.2 Klein 4B base uses ~13 GB; 16 GB recommended |
| OS | Windows 10/11 |
| Python | 3.8+ (for the client script only) |

---

## 1 — Install Stability Matrix

1. Download the latest Windows release from  
   **https://github.com/LykosAI/StabilityMatrix/releases**  
   (file: `StabilityMatrix-win-x64.zip` or `.exe`)
2. Extract / run it. Choose a data directory when prompted.  
   Portable mode (storing everything in one folder) is recommended.
3. Skip any initial model downloads — models are installed in step 3.

---

## 2 — Install ComfyUI

1. In Stability Matrix, go to **Add Package → ComfyUI** and click Install.
2. Wait for PyTorch and CUDA dependencies to download (~2–5 GB).
3. When done, click **Launch**. ComfyUI opens at `http://127.0.0.1:8188`.
4. Verify: open that URL in a browser — you should see the ComfyUI canvas.

> **GPU check:** In the ComfyUI terminal output, look for a line like  
> `Using device: cuda` or `Model loaded on: CUDA`. If it says `cpu`, see Troubleshooting.

---

## 3 — Install FLUX.2 Klein 4B Models

Three files are required. Download them from Hugging Face and place them in the
ComfyUI model directories shown below.  
The default base path is the `ComfyUI\models` folder inside your Stability Matrix
data directory (e.g. `C:\StabilityMatrix\Packages\ComfyUI\models\`).

| File | Destination subfolder | HuggingFace URL |
|------|-----------------------|-----------------|
| `flux-2-klein-base-4b.safetensors` | `diffusion_models\` | https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/diffusion_models/flux-2-klein-base-4b.safetensors |
| `qwen_3_4b.safetensors` | `text_encoders\` | https://huggingface.co/Comfy-Org/flux2-klein/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors |
| `flux2-vae.safetensors` | `vae\` | https://huggingface.co/Comfy-Org/flux2-dev/resolve/main/split_files/vae/flux2-vae.safetensors |

> File sizes are large (several GB each). Download with `wget`, your browser, or  
> HuggingFace's CLI (`huggingface-cli download`).

Alternatively, inside ComfyUI load the workflow (`workflows\flux2_klein_t2i.json`)
and click the model nodes — ComfyUI will offer to download missing files automatically.

---

## 4 — Load the Workflow

1. Open ComfyUI in your browser (`http://127.0.0.1:8188`).
2. Click **Load** (top menu) and select `workflows\flux2_klein_t2i.json`.
3. Run once from the UI to confirm all models load and an image is produced.
4. Generated images appear in `ComfyUI\output\` inside the Stability Matrix package folder.

---

## 5 — Generate an Image with the Python Script

Ensure ComfyUI is running, then:

```bash
cd "C:\Jacob\Apps & Tools\image-generation-pipeline"
python generate_image.py "a glowing crystal cave, cinematic lighting"
```

The script:
- Submits the prompt to `http://127.0.0.1:8188/prompt`
- Polls until the image is ready (up to 5 minutes by default)
- Downloads the PNG and saves it to `.\output\`

### Options

```
python generate_image.py "your prompt here"
    --out ./output          # output directory (default: ./output)
    --workflow workflows/flux2_klein_t2i.json   # workflow JSON file
    --timeout 300           # max seconds to wait (default: 300)
```

### Example

```bash
python generate_image.py "portrait of an arctic fox in silver armour, dramatic rim lighting" --out ./output
```

Expected output:
```
Queuing prompt: 'portrait of an arctic fox in silver armour, dramatic rim lighting'
Prompt queued (id=abc123...). Waiting for image…
Saved: output\flux2_klein_00001_.png
Done. 1 image(s) saved to C:\Jacob\Apps & Tools\image-generation-pipeline\output
```

---

## 6 — Using the API from Other Applications

Any Python application can call the same API without importing this script.
Minimal standalone example:

```python
import json, urllib.request, urllib.parse, uuid, time

COMFYUI = "http://127.0.0.1:8188"

def generate(prompt: str, output_dir: str = ".") -> str:
    """Submit a prompt, wait, return the saved file path."""
    from pathlib import Path
    import sys, os
    sys.path.insert(0, os.path.dirname(__file__))  # or just copy generate_image.py
    from generate_image import queue_prompt, wait_for_completion, download_image, set_prompt_text

    workflow = json.loads(Path("workflows/flux2_klein_t2i.json").read_text())
    workflow = set_prompt_text(workflow, prompt)
    prompt_id = queue_prompt(workflow, str(uuid.uuid4()))
    result = wait_for_completion(prompt_id)
    for node_out in result["outputs"].values():
        for img in node_out.get("images", []):
            return str(download_image(img["filename"], img.get("subfolder",""), img.get("type","output"), Path(output_dir)))
    raise RuntimeError("No image in output")
```

Or call the ComfyUI HTTP API directly — see  
https://docs.comfy.org/development/comfyui-server/api-examples

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Could not reach ComfyUI` | Start ComfyUI from Stability Matrix first |
| `Using device: cpu` in ComfyUI log | Reinstall with CUDA-enabled PyTorch; check Stability Matrix settings |
| Out-of-memory error on GPU | In Stability Matrix launch settings add `--lowvram` to extra args |
| `unet_name not found` | Model file is not in `diffusion_models\`; check the path |
| Generation never finishes | Increase `--timeout`; check the ComfyUI terminal for errors |
| Node `Flux2Scheduler` not found | Update ComfyUI via Stability Matrix to the latest version |

---

## Starting and Stopping

**Start:**  Open Stability Matrix → select ComfyUI → click Launch.

**Stop:**  Close the ComfyUI terminal window, or click Stop in Stability Matrix.

ComfyUI does not need to be running when you are not generating images.
It does not expose itself to the internet by default.

---

## File Layout

```
image-generation-pipeline\
├── generate_image.py          # Python API client
├── SETUP.md                   # this file
├── workflows\
│   └── flux2_klein_t2i.json   # FLUX.2 Klein 4B text-to-image workflow (API format)
└── output\                    # generated PNGs land here
```
