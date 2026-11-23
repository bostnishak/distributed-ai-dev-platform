<#
.SYNOPSIS
    OPS-05: Windows 11 Guided Installer / Uninstaller for Distributed AI Software Development Platform.
#>
param(
    [switch]$Uninstall,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvDir = Join-Path $RepoRoot "master\venv"

if ($Uninstall) {
    if (Test-Path $VenvDir) { Remove-Item -Recurse -Force $VenvDir }
    Write-Host "[OPS-05] Virtualenv kaldirildi."
    exit 0
}

Write-Host "[OPS-05] Sistem kontrolleri yapiliyor..."
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { throw "Python 3.12+ kurulu degil. https://python.org adresinden kurun." }

$ollama = Get-Command ollama -ErrorAction SilentlyContinue
if (-not $ollama) { Write-Warning "Ollama kurulu degil. Yerel modeller icin https://ollama.com adresinden kurun." }

if ($CheckOnly) {
    Write-Host "[OPS-05] On kontrol tamamlandi."
    exit 0
}

if (-not (Test-Path (Join-Path $VenvDir "Scripts\python.exe"))) {
    python -m venv $VenvDir
}
& (Join-Path $VenvDir "Scripts\pip.exe") install -r (Join-Path $RepoRoot "master\requirements.txt")
Write-Host "[OPS-05] Kurulum tamamlandi. Baslatmak icin: .\scripts\dev.ps1"
