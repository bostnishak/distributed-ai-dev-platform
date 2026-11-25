# Installs Stable Diffusion WebUI (AUTOMATIC1111) with its API so the platform can make realistic images.
# The platform already talks to http://127.0.0.1:7860/sdapi/v1/txt2img when it is running.
#
# Needs: git, Python 3.10.x on PATH, ~10 GB free disk, an NVIDIA GPU (8 GB is enough with --medvram).
# Downloads: PyTorch (~2.5 GB) on first start and one model checkpoint (~2-4 GB).
#
# Usage (PowerShell):   .\scripts\install_sd_webui.ps1 [-Target C:\ai\sd-webui]

param([string]$Target = "$HOME\sd-webui")

$ErrorActionPreference = "Stop"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw "git not found" }
if (-not (Test-Path $Target)) {
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git $Target
}

# A small, fast checkpoint that fits an 8 GB GPU. Replace the URL with any model you prefer.
$ModelDir = Join-Path $Target "models\Stable-diffusion"
New-Item -ItemType Directory -Force $ModelDir | Out-Null
$Model = Join-Path $ModelDir "v1-5-pruned-emaonly.safetensors"
if (-not (Test-Path $Model)) {
    Invoke-WebRequest -Uri "https://huggingface.co/stable-diffusion-v1-5/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" -OutFile $Model
}

# --api turns on /sdapi/v1/*, --medvram keeps it inside 8 GB, --listen is NOT set: stays on localhost.
Set-Content -Path (Join-Path $Target "webui-user.bat") -Value @"
@echo off
set COMMANDLINE_ARGS=--api --medvram --xformers
call webui.bat
"@

Write-Host "Done. Start it with:  $Target\webui-user.bat   (first start installs PyTorch and takes a while)"
Write-Host "When http://127.0.0.1:7860 answers, ask the platform for a realistic image; it detects the API automatically."
