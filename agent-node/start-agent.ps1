<#
  Starts the agent that setup.ps1 installed. Keep this window open while you want your
  computer to take part in the platform.
  Usage (from the repo folder):  powershell -ExecutionPolicy Bypass -File agent-node\start-agent.ps1
#>
$ErrorActionPreference = "Stop"
$agentDir = Join-Path (Split-Path -Parent $PSScriptRoot) "agent"
$python = Join-Path $agentDir ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ajan kurulu değil. Önce şunu çalıştırın: powershell -ExecutionPolicy Bypass -File agent-node\setup.ps1 -AgentId <uyeN>"
}
& $python (Join-Path $agentDir "agent.py")
