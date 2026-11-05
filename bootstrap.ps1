#Requires -Version 5.1
<#
.SYNOPSIS
    Bootstrap the local image-generation pipeline on a fresh Windows machine.

.DESCRIPTION
    1. Downloads StabilityMatrix.exe (if not already present)
    2. Downloads the RealisticVision v5.1 checkpoint from HuggingFace into the
       correct ComfyUI models folder (once Stability Matrix has been run once
       and ComfyUI installed, so the folder exists)
    3. Prints manual steps for anything that requires a browser or login

.USAGE
    PowerShell -ExecutionPolicy Bypass -File bootstrap.ps1
#>

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot

Write-Host ""
Write-Host "=== Image Generation Pipeline — Bootstrap ===" -ForegroundColor Cyan
Write-Host "Root: $Root"
Write-Host ""

# ── 1. Stability Matrix ───────────────────────────────────────────────────────
$SmExe = Join-Path $Root "StabilityMatrix.exe"
$SmVersion = "v2.16.5"
$SmUrl = "https://github.com/LykosAI/StabilityMatrix/releases/download/$SmVersion/StabilityMatrix.exe"

if (Test-Path $SmExe) {
    Write-Host "[OK] StabilityMatrix.exe already present" -ForegroundColor Green
} else {
    Write-Host "[↓]  Downloading StabilityMatrix $SmVersion (~100 MB)..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $SmUrl -OutFile $SmExe -UseBasicParsing
    Write-Host "[OK] Downloaded StabilityMatrix.exe" -ForegroundColor Green
}

# ── 2. ComfyUI models folder ──────────────────────────────────────────────────
$ModelsRoot = Join-Path $Root "data\Packages\ComfyUI\models"
$CheckpointsDir = Join-Path $ModelsRoot "checkpoints"
$LorasDir       = Join-Path $ModelsRoot "loras"

if (-not (Test-Path $CheckpointsDir)) {
    Write-Host ""
    Write-Host "[!] ComfyUI models folder not found at:" -ForegroundColor Yellow
    Write-Host "    $CheckpointsDir"
    Write-Host ""
    Write-Host "    Run StabilityMatrix.exe first, set the data directory to:" -ForegroundColor Yellow
    Write-Host "    $Root\data" -ForegroundColor White
    Write-Host "    Then install ComfyUI from the Packages screen and launch it once."
    Write-Host "    Re-run this script afterwards to download the model files."
    Write-Host ""
} else {
    # ── 3. RealisticVision v5.1 checkpoint ───────────────────────────────────
    $RvFile = Join-Path $CheckpointsDir "Realistic_Vision_V5.1_fp16-no-ema.safetensors"
    $RvUrl  = "https://huggingface.co/SG161222/Realistic_Vision_V5.1_noVAE/resolve/main/Realistic_Vision_V5.1_fp16-no-ema.safetensors"

    if (Test-Path $RvFile) {
        Write-Host "[OK] RealisticVision v5.1 checkpoint already present" -ForegroundColor Green
    } else {
        Write-Host "[↓]  Downloading RealisticVision v5.1 (~2 GB)..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $RvUrl -OutFile $RvFile -UseBasicParsing
        Write-Host "[OK] Downloaded RealisticVision v5.1" -ForegroundColor Green
    }

    # ── 4. Retro Game Art LoRA ────────────────────────────────────────────────
    $LoraFile = Join-Path $LorasDir "SD15Lora-RetroGameArt-v1.1.safetensors"

    if (Test-Path $LoraFile) {
        Write-Host "[OK] Retro Game Art LoRA already present" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "[!] Retro Game Art LoRA not found — requires a free CivitAI account:" -ForegroundColor Yellow
        Write-Host "    1. Sign in at https://civitai.com"
        Write-Host "    2. Download from https://civitai.com/models/550675"
        Write-Host "    3. Rename the file to: SD15Lora-RetroGameArt-v1.1.safetensors"
        Write-Host "    4. Place it in: $LorasDir"
        Write-Host ""
    }
}

# ── 5. Summary ────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1. Launch StabilityMatrix.exe"
Write-Host "2. Start ComfyUI (Packages → Launch)"
Write-Host "3. Test from the command line:"
Write-Host ""
Write-Host '   python generate_image.py "R3TR0, forest clearing at dusk, adventure game background"' -ForegroundColor White
Write-Host ""
Write-Host "Generated PNGs are saved to: $Root\output"
Write-Host ""
