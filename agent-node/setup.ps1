<#
  Sets up a team member's agent on Windows: Ollama (localhost only) + the member's model,
  Tailscale, Python and the agent service. Messages are Turkish; see agent-node/README.md.

  Usage (from the repo folder):
    powershell -ExecutionPolicy Bypass -File agent-node\setup.ps1 -AgentId uye2

  -MasterHost     This computer also runs the master (İshak's computer): Ollama's current
                  network setting is kept (Docker containers reach it), Tailscale is not joined
                  here and the master is used through localhost.
  -SkipTailscale  Do not install/join Tailscale (for example when it is already set up).
#>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("uye1", "uye2", "uye3", "uye4", "uye5", "uye6")]
    [string]$AgentId,
    [string]$MasterUrl,
    [switch]$MasterHost,
    [switch]$SkipTailscale
)

$ErrorActionPreference = "Stop"

$members = @{
    uye1 = @{ Name = "İshak Bostan"; Model = "qwen3.5:4b" }
    uye2 = @{ Name = "Zeynep Duru Küçük"; Model = "phi4-mini" }
    uye3 = @{ Name = "Furkan Kaan Özbeyli"; Model = "llama3.2:3b" }
    uye4 = @{ Name = "Semih Sarıca"; Model = "gemma4:e4b" }
    uye5 = @{ Name = "Işıl Karademir"; Model = "qwen2.5-coder:7b" }
    uye6 = @{ Name = "Berfin Yiğit"; Model = "qwen3:1.7b" }
}
$member = $members[$AgentId]
$model = $member.Model
$repoRoot = Split-Path -Parent $PSScriptRoot
$agentDir = Join-Path $repoRoot "agent"
$agentEnv = Join-Path $agentDir ".env"
$ollamaApi = "http://127.0.0.1:11434"

function Write-Step([int]$Number, [string]$Text) {
    Write-Host "`n== $Number/7: $Text ==" -ForegroundColor Cyan
}

function Update-SessionPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
}

function Wait-Ollama {
    for ($i = 0; $i -lt 30; $i++) {
        try {
            Invoke-RestMethod -Uri "$ollamaApi/api/version" -TimeoutSec 2 | Out-Null
            return
        } catch {
            Start-Sleep -Seconds 1
        }
    }
    throw "Ollama 30 saniye içinde yanıt vermedi. Ollama'yı Başlat menüsünden açıp scripti tekrar çalıştırın."
}

function Read-EnvValue([string]$Path, [string]$Key) {
    if (-not (Test-Path $Path)) { return $null }
    foreach ($line in [System.IO.File]::ReadAllLines($Path)) {
        if ($line.StartsWith("$Key=")) { return $line.Substring($Key.Length + 1) }
    }
    return $null
}

function Find-Python {
    # Returns a command that runs Python 3.10+ (the "py" launcher or python.exe), or $null.
    foreach ($candidate in @(@("py", "-3.12"), @("py", "-3"), @("python"))) {
        $exe = $candidate[0]
        $pyArgs = @($candidate | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        try {
            $version = & $exe @pyArgs -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        } catch {
            continue
        }
        if ($LASTEXITCODE -eq 0 -and $version -match '^3\.(\d+)$' -and [int]$Matches[1] -ge 10) {
            return , $candidate
        }
    }
    return $null
}

Write-Host "Ajan kurulumu: $AgentId - $($member.Name) - model $model" -ForegroundColor Green

# --- 1. Ollama ---------------------------------------------------------------------------
Write-Step 1 "Ollama"
Update-SessionPath
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama kurulu değil, winget ile kuruluyor (birkaç dakika sürebilir)..."
    winget install --id Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
    Update-SessionPath
}
$ollama = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollama) {
    $fallback = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $fallback) { $ollama = $fallback } else {
        throw "Ollama kuruldu ama 'ollama' komutu bulunamadı. Yeni bir terminal açıp scripti tekrar çalıştırın."
    }
}

if ($MasterHost) {
    Write-Host "Master bilgisayarı: Ollama'nın ağ ayarına dokunulmuyor."
} elseif ([System.Environment]::GetEnvironmentVariable("OLLAMA_HOST", "User")) {
    # The old setup script opened Ollama to the whole network (OLLAMA_HOST=0.0.0.0). With the
    # pull-based agent only this computer needs to reach Ollama, so that setting is removed.
    [System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", $null, "User")
    Remove-Item Env:OLLAMA_HOST -ErrorAction SilentlyContinue
    Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2
    Start-Process -FilePath $ollama -ArgumentList "serve" -WindowStyle Hidden
    Write-Host "Eski OLLAMA_HOST ayarı kaldırıldı: Ollama artık yalnızca bu bilgisayardan erişilebilir (127.0.0.1)."
}
Wait-Ollama
Write-Host "Ollama hazır: $ollama"

# --- 2. Model -----------------------------------------------------------------------------
Write-Step 2 "Model indiriliyor: $model"
& $ollama pull $model
if ($LASTEXITCODE -ne 0) { throw "Model indirilemedi: $model" }
$tags = Invoke-RestMethod -Uri "$ollamaApi/api/tags"
$modelEntry = $tags.models | Where-Object { $_.name -eq $model -or $_.name -eq "${model}:latest" } | Select-Object -First 1
$ramGb = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
if ($modelEntry) {
    $modelGb = [math]::Round($modelEntry.size / 1GB, 1)
    Write-Host "Model boyutu: $modelGb GB, bilgisayarın RAM'i: $ramGb GB"
    # Rough rule: the model must fit in memory next to Windows and the other open programs.
    if ($ramGb -lt $modelGb + 4) {
        Write-Warning "RAM bu model için az görünüyor (yaklaşık model boyutu + 4 GB önerilir). Model yavaş çalışabilir; ekiple konuşun."
    }
}

# --- 3. Model test ------------------------------------------------------------------------
Write-Step 3 "Model test ediliyor"
$body = @{
    model    = $model
    messages = @(@{ role = "user"; content = "Tek kelimeyle cevap ver: hazır mısın?" })
    think    = $false
    stream   = $false
} | ConvertTo-Json -Depth 5
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$answer = Invoke-RestMethod -Uri "$ollamaApi/api/chat" -Method Post -Body $bytes -ContentType "application/json; charset=utf-8" -TimeoutSec 600
Write-Host "Model yanıtı: $($answer.message.content)"

# --- 4. Tailscale -------------------------------------------------------------------------
Write-Step 4 "Tailscale (ekip ağı)"
if ($MasterHost -or $SkipTailscale) {
    Write-Host "Atlandı."
} else {
    $tailscale = "C:\Program Files\Tailscale\tailscale.exe"
    if (-not (Test-Path $tailscale)) {
        Write-Host "Tailscale kurulu değil, winget ile kuruluyor..."
        winget install --id tailscale.tailscale -e --silent --accept-package-agreements --accept-source-agreements
    }
    if (-not (Test-Path $tailscale)) { throw "Tailscale kurulamadı. https://tailscale.com/download adresinden kurup scripti tekrar çalıştırın." }
    $state = $null
    try { $state = (& $tailscale status --json | ConvertFrom-Json).BackendState } catch { $state = $null }
    if ($state -eq "Running") {
        Write-Host "Bu bilgisayar zaten ekip ağına bağlı."
    } else {
        Write-Host "İshak'ın size özelden gönderdiği Tailscale anahtarını (tskey-auth-...) yapıştırın."
        $secure = Read-Host "Tailscale anahtarı" -AsSecureString
        $authKey = [System.Net.NetworkCredential]::new("", $secure).Password
        & $tailscale up --auth-key=$authKey
        if ($LASTEXITCODE -ne 0) { throw "Tailscale'e bağlanılamadı. Anahtarı kontrol edin." }
        Write-Host "Ekip ağına bağlanıldı."
    }
}

# --- 5. Python and the agent ----------------------------------------------------------------
Write-Step 5 "Python ve ajan paketleri"
$python = Find-Python
if (-not $python) {
    Write-Host "Python 3.10+ bulunamadı, winget ile Python 3.12 kuruluyor..."
    winget install --id Python.Python.3.12 -e --silent --accept-package-agreements --accept-source-agreements
    Update-SessionPath
    $python = Find-Python
    if (-not $python) { throw "Python kuruldu ama bulunamadı. Yeni bir terminal açıp scripti tekrar çalıştırın." }
}
$pyExe = $python[0]
$pyArgs = @($python | Select-Object -Skip 1)
$venvPython = Join-Path $agentDir ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $pyExe @pyArgs -m venv (Join-Path $agentDir ".venv")
}
& $venvPython -m pip install --quiet --disable-pip-version-check -r (Join-Path $agentDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Ajan paketleri kurulamadı." }
Write-Host "Ajan hazır: $venvPython"

# --- 6. Agent settings --------------------------------------------------------------------
Write-Step 6 "Ajan ayarları (agent\.env)"
if (-not $MasterUrl) { $MasterUrl = Read-EnvValue $agentEnv "MASTER_URL" }
if (-not $MasterUrl -and $MasterHost) { $MasterUrl = "http://127.0.0.1:8000" }
if (-not $MasterUrl) {
    $MasterUrl = Read-Host "Master adresi (İshak'tan alın, ör. http://ishak-pc:8000)"
}
$MasterUrl = $MasterUrl.Trim().TrimEnd("/")

$token = Read-EnvValue $agentEnv "AGENT_TOKEN"
if (-not $token -and $MasterHost) { $token = Read-EnvValue (Join-Path $repoRoot ".env") "AGENT_TOKEN" }
if (-not $token) {
    $secureToken = Read-Host "AGENT_TOKEN (İshak'ın size özelden gönderdiği anahtar)" -AsSecureString
    $token = [System.Net.NetworkCredential]::new("", $secureToken).Password
}
if (-not $token) { throw "AGENT_TOKEN boş olamaz." }

$envLines = @(
    "# Created by agent-node/setup.ps1. Contains a secret (AGENT_TOKEN): never commit or share this file.",
    "AGENT_ID=$AgentId",
    "MEMBER_NAME=$($member.Name)",
    "MODEL=$model",
    "MASTER_URL=$MasterUrl",
    "AGENT_TOKEN=$token",
    "OLLAMA_URL=$ollamaApi",
    "AGENT_MODE=node"
)
# python-dotenv expects UTF-8 without a byte order mark.
[System.IO.File]::WriteAllLines($agentEnv, $envLines, (New-Object System.Text.UTF8Encoding $false))
Write-Host "Ayarlar kaydedildi: $agentEnv"

# --- 7. Master connection -----------------------------------------------------------------
Write-Step 7 "Master bağlantısı"
try {
    Invoke-RestMethod -Uri "$MasterUrl/health" -TimeoutSec 10 | Out-Null
    Write-Host "Master'a ulaşılabiliyor: $MasterUrl" -ForegroundColor Green
} catch {
    Write-Warning "Master'a şu an ulaşılamıyor ($MasterUrl). Master kapalı olabilir ya da Tailscale bağlantısı yoktur. Ajan başlatıldığında bağlanana kadar tekrar dener."
}

Write-Host "`nKurulum tamamlandı." -ForegroundColor Green
Write-Host "Ajanı başlatmak için:  powershell -ExecutionPolicy Bypass -File agent-node\start-agent.ps1"
