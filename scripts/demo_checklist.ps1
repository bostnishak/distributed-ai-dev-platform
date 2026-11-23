<#
.SYNOPSIS
    OPS-23 & PROC-06: 10-Minute Pre-Demo Readiness Checklist & Demo Mode Launcher.
#>
param(
    [string]$MasterUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Continue"
Write-Host "=== CM6453 Pre-Demo Checklist (OPS-23) ==="

$checks = @(
    @{ Name = "Master /health"; Url = "$MasterUrl/health" },
    @{ Name = "Master /ready"; Url = "$MasterUrl/ready" },
    @{ Name = "Gateway /api/gateway/status"; Url = "$MasterUrl/api/gateway/status" },
    @{ Name = "Orchestrator 30 Intents"; Url = "$MasterUrl/api/orchestrator/intents" },
    @{ Name = "Distributed Taxonomy"; Url = "$MasterUrl/api/distributed/taxonomy" },
    @{ Name = "UX Health Wizard"; Url = "$MasterUrl/api/ux/health-wizard" },
    @{ Name = "Ollama /api/tags"; Url = "http://127.0.0.1:11434/api/tags" }
)

$failed = 0
foreach ($c in $checks) {
    try {
        $resp = Invoke-WebRequest -Uri $c.Url -TimeoutSec 5 -UseBasicParsing
        Write-Host "[OK]   $($c.Name) -> HTTP $($resp.StatusCode)"
    } catch {
        Write-Host "[FAIL] $($c.Name) -> $($_.Exception.Message)"
        $failed++
    }
}

$ts = Get-Command tailscale -ErrorAction SilentlyContinue
if ($ts) {
    Write-Host "[INFO] Tailscale CLI kurulu; 'tailscale status' ile ajanlari kontrol edin."
} else {
    Write-Host "[WARN] Tailscale CLI bulunamadi; lokal demo modu kullanilacak."
}

if ($failed -eq 0) {
    Write-Host "=== TUM DEMO KONTROLLERI BASARILI ==="
    exit 0
} else {
    Write-Host "=== $failed KONTROL BASARISIZ: docs/runbooks/ kilavuzlarina bakin ==="
    exit 1
}
