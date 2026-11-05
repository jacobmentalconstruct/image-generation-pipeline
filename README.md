# image-generation-pipeline

Local text-to-image service. No cloud APIs. GPU only.  
Generates **320×240 retro pixel art** in the style of Sierra/LucasArts 90s adventure games.

## Stack

| Layer | Choice |
|-------|--------|
| Package manager | Stability Matrix |
| Engine | ComfyUI (HTTP API on `http://127.0.0.1:8188`) |
| Checkpoint | RealisticVision v5.1 (SD 1.5 fine-tune) |
| LoRA | Retro Game Art — MS-DOS/Amiga style (`R3TR0` trigger) |
| Resolution | 512×384 → downscaled to 320×240 (Sierra VGA) |
| VRAM | ~4 GB required |

## Fresh install

```powershell
git clone <this repo>
cd image-generation-pipeline
PowerShell -ExecutionPolicy Bypass -File bootstrap.ps1
```

The script downloads `StabilityMatrix.exe` and the RealisticVision checkpoint automatically.  
The Retro Game Art LoRA requires a **free CivitAI account** — the script will print the link.

After bootstrap:
1. Run `StabilityMatrix.exe` → set data directory to `.\data`
2. Install **ComfyUI** from the Packages screen
3. Launch ComfyUI
4. The pipeline is ready

## Generate an image

ComfyUI must be running first (Stability Matrix → Launch).

```bash
python generate_image.py "R3TR0, moonlit forest path, ancient ruins, adventure game background"
```

Images are saved to `./output/`.

### Options

```
python generate_image.py "<prompt>" --out ./output --workflow workflows/sd15_retro_pixel.json --timeout 300
```

## Workflows

| File | Description |
|------|-------------|
| `workflows/sd15_retro_pixel.json` | **Primary** — SD 1.5 + Retro Game Art LoRA, 320×240 Sierra style |
| `workflows/flux2_klein_t2i.json` | Optional — FLUX.2 Klein 4B, high-fidelity (requires ~13 GB VRAM + model download) |

## Prompt tips

- Always include `R3TR0` as the first token
- Describe scene type: `point and click adventure game background`, `exterior`, `interior`
- Keep CFG low (2–4) — the LoRA is set to 3.5 in the workflow
- Good negative: `modern, photo, 3d render, blurry, bad anatomy`

## Branching / evolving

```
main              — SD 1.5 retro pixel art (this setup)
flux-hifi         — FLUX.2 Klein 4B for high-fidelity work
wan2gp-video      — future: local video generation
```

Add a new workflow JSON under `workflows/` and update `bootstrap.ps1` with any new model downloads.

## Architecture

Treat this service like Ollama: a locally running HTTP API that any Python app can call.  
Applications (KleinBOTTLE, ProjectMapper, etc.) import or call `generate_image.py` directly,  
or POST to `http://127.0.0.1:8188/prompt` with their own workflow.

ComfyUI does not expose itself to the internet by default.
