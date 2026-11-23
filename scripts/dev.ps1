<#
.SYNOPSIS
  SEC-24: Secure launcher for the Master service.
  - Default mode binds strictly to loopback (`127.0.0.1:8000`) so LAN / public Wi-Fi hosts cannot connect.
  - `-Tailscale` mode queries `tailscale ip -4` and binds ONLY to the Tailscale interface IP (100.64.0.0/10).
  - Never binds to `0.0.0.0`.
#>
param(
    [switch]$Tailscale,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$bindHost = "127.0.0.1"
if ($Tailscale) {
    $tsIp = (& tailscale ip -4 2>$null | Select-Object -First 1).Trim()
    if (-not $tsIp -or ($tsIp -notmatch '^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.')) {
        throw "Geçerli bir Tailscale IPv4 adresi (100.64.0.0/10) alınamadı. Tailscale bağlı mı?"
    }
    $bindHost = $tsIp
    Write-Host "Tailscale arayüzüne bağlanılıyor (yalnız tailnet): http://$($bindHost):$Port" -ForegroundColor Green
} else {
    Write-Host "Yerel loopback arayüzüne bağlanılıyor (LAN kapalı): http://127.0.0.1:$Port" -ForegroundColor Cyan
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $repoRoot "master")
try {
    & ".\venv\Scripts\python.exe" -m uvicorn app:app --host $bindHost --port $Port
} finally {
    Pop-Location
}
