<#
  Ekip uyeleri icin Ollama + atanan model kurulum script'i (Windows).
  Kullanim: .\setup.ps1 -Model "phi4-mini"
  Hangi uyeye hangi model tag'i atandigi icin README.md'ye bakin.
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Model
)

$ErrorActionPreference = "Stop"

function Refresh-Path {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}

Write-Host "== 1/5: Ollama kontrol ediliyor ==" -ForegroundColor Cyan
# Onceki bir kurulumdan sonra bu terminal oturumu acilmis olabilir; PATH'i once tazeleyip oyle kontrol et.
Refresh-Path
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama kurulu degil, winget ile kuruluyor (birkaç dakika sürebilir)..."
    winget install --id Ollama.Ollama -e --silent --accept-package-agreements --accept-source-agreements
    Refresh-Path
}

$ollamaCmd = (Get-Command ollama -ErrorAction SilentlyContinue).Source
if (-not $ollamaCmd) {
    # Winget kurdu ama bu oturumun PATH'i henuz yenilenmedi olabilir
    $fallback = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $fallback) { $ollamaCmd = $fallback } else {
        throw "Ollama kurulumu sonrasi 'ollama' komutu bulunamadi. Bir terminal daha acip tekrar deneyin."
    }
}
Write-Host "Ollama hazir: $ollamaCmd"

Write-Host "`n== 2/5: LAN erisimi acik hale getiriliyor ==" -ForegroundColor Cyan
# ONEMLI: Ollama varsayilan olarak sadece localhost'u dinler -- bu haliyle gateway (baska bir
# bilgisayar) buraya asla ulasamaz. OLLAMA_HOST=0.0.0.0 ile tum ag arayuzlerinden erisilebilir
# hale getiriyoruz. Bu, ayni LAN'daki herkesin (kimlik dogrulamasiz) bu modeli sorgulayabilecegi
# anlamina gelir -- ekip bunu kabul etti (guvenilir ev/okul agi varsayimiyla).
[System.Environment]::SetEnvironmentVariable("OLLAMA_HOST", "0.0.0.0", "User")
$env:OLLAMA_HOST = "0.0.0.0"
Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
Start-Process -FilePath $ollamaCmd -ArgumentList "serve" -WindowStyle Hidden
Start-Sleep -Seconds 3
Write-Host "Ollama artik butun ag arayuzlerinden erisilebilir (0.0.0.0:11434)."

Write-Host "`n== 3/5: Model cekiliyor: $Model ==" -ForegroundColor Cyan
& $ollamaCmd pull $Model

Write-Host "`n== 4/5: Model test ediliyor ==" -ForegroundColor Cyan
$body = @{
    model    = $Model
    messages = @(@{ role = "user"; content = "Tek kelimeyle cevap ver: hazir misin?" })
    think    = $false
    stream   = $false
} | ConvertTo-Json -Depth 5

$resp = Invoke-RestMethod -Uri "http://localhost:11434/api/chat" -Method Post -Body $body -ContentType "application/json"
Write-Host "Model yaniti: $($resp.message.content)"

Write-Host "`n== 5/5: LAN IP adresi ==" -ForegroundColor Cyan
# Sanal adaptorleri (WSL/Hyper-V/VirtualBox/VPN) disarida birakip gercek Wi-Fi/Ethernet IP'sini bulur.
$ip = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '169.254.*' -and
        $_.InterfaceAlias -notmatch 'Loopback|Bluetooth' -and
        (Get-NetAdapter -InterfaceAlias $_.InterfaceAlias -ErrorAction SilentlyContinue).InterfaceDescription -notmatch 'Virtual'
    } |
    Sort-Object { $_.PrefixOrigin -eq 'Dhcp' } -Descending |
    Select-Object -First 1 -ExpandProperty IPAddress

if (-not $ip) {
    Write-Warning "Gercek LAN IP'si otomatik bulunamadi. 'ipconfig' cikti sina bakip Wi-Fi/Ethernet adaptorunun IPv4 adresini elle kontrol edin."
}

Write-Host "`nKurulum tamamlandi." -ForegroundColor Green
Write-Host "Bu bilgisayarin LAN IP adresi: $ip"
Write-Host "Bu IP'yi ve model adini ($Model) gateway'i kuran arkadasa iletin."
