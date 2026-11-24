# DADP Windows one-command setup and .env hardening wrapper
param(
    [switch]$DryRun,
    [switch]$Json
)
$ErrorActionPreference = "Stop"
$py = Join-Path $PSScriptRoot "..\master\venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py = "python" }
$argsList = @((Join-Path $PSScriptRoot "setup_env.py"))
if ($DryRun) { $argsList += "--dry-run" }
if ($Json) { $argsList += "--json" }
& $py @argsList
