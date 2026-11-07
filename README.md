# image-generation-pipeline

Local text-to-image service. No cloud APIs. GPU only.  
Generates **320×240 retro pixel art** in the style of Sierra/LucasArts 90s adventure games.

---

## How it works

```
Your Python app
      │
      │  "R3TR0, moonlit forest path..."
      ▼
generate_image.py
      │  POST /prompt  (workflow JSON + prompt)
      ▼
ComfyUI  ←── running locally on port 8188
      │
      │  loads workflow, queues the job
      ▼
 ┌─────────────────────────────────────┐
 │  GPU inference (NVIDIA card)        │
 │                                     │
 │  CheckpointLoader                   │
 │    └─ RealisticVision v5.1          │  ← base SD 1.5 model
 │  LoraLoader                         │
 │    └─ Retro Game Art (R3TR0)        │  ← bends style toward DOS/Amiga art
 │  CLIPTextEncode  (your prompt)      │  ← text → conditioning signal
 │  CLIPTextEncode  (negative)         │  ← what to avoid
 │  EmptyLatentImage  512×384          │  ← blank noise canvas, 4:3
 │  KSampler  25 steps, CFG 3.5        │  ← denoises noise → image
 │  VAEDecode                          │  ← latent → pixels
 │  ImageScale → 320×240 nearest       │  ← snaps to Sierra pixel grid
 │  SaveImage                          │  ← writes PNG to ComfyUI output/
 └─────────────────────────────────────┘
      │
      │  GET /history/{id}  (polling)
      │  GET /view?filename=...
      ▼
generate_image.py saves PNG to ./output/
```

### What each layer does

**Stability Matrix** — installer and launcher. Manages Python, PyTorch, CUDA, and ComfyUI as a package. Once ComfyUI is running you barely touch it again.

**ComfyUI** — the engine. Runs a local HTTP server and executes *workflows* — graphs of nodes where each node does one thing (load a model, encode text, sample, decode). You submit a workflow as JSON and it runs it on the GPU.

**RealisticVision v5.1** — a fine-tuned SD 1.5 checkpoint. It knows what things look like; it's the base knowledge. ~2 GB.

**Retro Game Art LoRA** — a 72 MB adapter on top of the checkpoint that pulls the output style toward MS-DOS/Amiga pixel art. The trigger word `R3TR0` activates it. Without it you'd get a realistic photo; with it you get the Sierra look.

**KSampler** — the core diffusion loop. Starts with random noise and runs 25 guided denoising steps, nudging the result toward your prompt and away from your negative prompt. CFG 3.5 means "follow the prompt moderately loosely" — lower CFG lets the LoRA style dominate more.

**ImageScale → nearest-exact** — after decoding to 512×384, this snaps every pixel to a nearest-neighbour grid at 320×240. That's what creates the chunky authentic pixel look rather than a smooth scaled-down photo.

**generate_image.py** — a ~100-line stdlib-only Python script. It injects your prompt into the workflow, POSTs it to ComfyUI, polls until the job finishes, then downloads and saves the PNG. No third-party dependencies.

---

## Quick start

### Prerequisites
- Windows 10/11, NVIDIA GPU with ≥ 4 GB VRAM
- Python 3.8+
- ComfyUI running (see [Fresh install](#fresh-install) below)

### Generate an image

ComfyUI must be running first (Stability Matrix → Launch ComfyUI).

```bash
python generate_image.py "R3TR0, moonlit forest path, ancient ruins, adventure game background"
```

Images are saved to `./output/`.

### Options

```
python generate_image.py "<prompt>"
    --out ./output                              # output directory
    --workflow workflows/sd15_retro_pixel.json  # workflow to use
    --timeout 300                               # max seconds to wait
```

### Integrating into another application

There are three patterns. Pick the one that fits your app.

### Pattern 1 — pip install (recommended)

Install the pipeline as a local package once; import it anywhere.

```bash
# run once per environment, from anywhere
pip install -e "C:/path/to/image-generation-pipeline"
```

```python
from pipeline import generate

# one-line call, returns a list of saved Path objects
paths = generate("a wizard's library at candlelight", style="kleinbottle")
print(paths[0])  # e.g. PosixPath('output/kleinbottle_00001_.png')
```

### Pattern 2 — sys.path import (no install needed)

```python
import sys
sys.path.insert(0, r"C:\path\to\image-generation-pipeline")

from pipeline import generate
paths = generate("a harbour at dusk", style="projectmapper", out_dir="./assets")
```

### Pattern 3 — subprocess (language-agnostic)

Works from any language. Fire and forget; check the output directory.

```python
import subprocess
subprocess.run([
    "python",
    r"C:\path\to\image-generation-pipeline\generate_image.py",
    "a harbour at dusk",
    "--style", "projectmapper",
    "--out", "./assets",
], check=True)
```

### Per-call setting overrides

Any parameter from the style profile can be overridden for a single call
without touching the profile file:

```python
from pipeline import generate

# use the kleinbottle style but bump CFG and steps for this one image
paths = generate(
    "a dramatic throne room",
    style="kleinbottle",
    cfg=5.0,
    steps=35,
    lora_strength=1.3,
)
```

The profile file is never modified. The override applies to this call only.

---

The service is an abstraction — treat it like Ollama for language models.
Applications describe *what* they want; the pipeline handles the model, GPU, and style.

---

## Prompt tips

- Always start with `R3TR0` to activate the LoRA style
- Describe the scene type explicitly: `point and click adventure game background`, `exterior`, `interior`
- Good scene descriptors: `cobblestone street`, `tavern interior`, `castle corridor`, `forest path at dusk`
- Good negative prompt (already in the workflow): `modern, photo, 3d render, blurry, bad anatomy`
- CFG is set to 3.5 — lower values give more stylised results, higher values follow the prompt more literally

---

## Fresh install

```powershell
git clone https://github.com/jacobmentalconstruct/image-generation-pipeline
cd image-generation-pipeline
PowerShell -ExecutionPolicy Bypass -File bootstrap.ps1
```

The bootstrap script downloads `StabilityMatrix.exe` and the RealisticVision v5.1 checkpoint automatically.

**After running bootstrap:**
1. Run `StabilityMatrix.exe` — set the data directory to `.\data` when prompted
2. Install **ComfyUI** from the Packages screen and launch it once
3. Re-run `bootstrap.ps1` to download the checkpoint into the correct folder
4. Download the **Retro Game Art LoRA** manually (free CivitAI account required):
   - Sign in at https://civitai.com
   - Download from https://civitai.com/models/550675
   - Rename to `SD15Lora-RetroGameArt-v1.1.safetensors`
   - Place in `data\Packages\ComfyUI\models\loras\`

Total download: ~2.1 GB (checkpoint + LoRA).

---

## Stack

| Layer | Choice |
|-------|--------|
| Package manager | Stability Matrix |
| Engine | ComfyUI (HTTP API on `http://127.0.0.1:8188`) |
| Checkpoint | RealisticVision v5.1 (SD 1.5 fine-tune, ~2 GB) |
| LoRA | Retro Game Art — MS-DOS/Amiga style (`R3TR0` trigger, 72 MB) |
| Resolution | 512×384 → downscaled to 320×240 (Sierra VGA grid) |
| VRAM | ~4 GB required |

## Workflows

| File | Description |
|------|-------------|
| `workflows/sd15_retro_pixel.json` | **Primary** — SD 1.5 + Retro Game Art LoRA, 320×240 Sierra style |
| `workflows/flux2_klein_t2i.json` | Optional — FLUX.2 Klein 4B, high-fidelity (requires ~13 GB VRAM + model download) |

## Branching / evolving

```
main              — SD 1.5 retro pixel art (this setup)
flux-hifi         — FLUX.2 Klein 4B for high-fidelity work
wan2gp-video      — future: local video generation
```

Add a new workflow JSON under `workflows/` and update `bootstrap.ps1` with any new model downloads.
