<#
  Starts Docker Desktop on Windows and works around a Docker Desktop failure seen on the
  master's computer.

  When Docker Desktop is closed uncleanly (for example Windows shuts down while it is running),
  it leaves Unix-socket files behind that Windows can no longer open or delete (error 1920,
  "The file cannot be accessed by the system"). The next start then crashes with
  "initializing Inference manager" or "initializing Secrets Engine", and crashing again leaves
  the other socket broken, so the error keeps coming back. Deleting the files fails, but the
  folders that contain them can be renamed, so this script moves both folders aside before
  starting Docker Desktop. Docker recreates them on start.

  Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-docker.ps1
#>
$ErrorActionPreference = "Stop"

$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$socketFolders = @(
    "$env:LOCALAPPDATA\Docker\run",
    "$env:LOCALAPPDATA\docker-secrets-engine"
)

function Test-DockerEngine {
    # "docker info" can hang while the backend is broken, so give it a hard time limit.
    $job = Start-Job { docker info --format "{{.ServerVersion}}" 2>$null; $LASTEXITCODE }
    if (Wait-Job $job -Timeout 15) {
        $output = @(Receive-Job $job)
        Remove-Job $job -Force
        return ($output.Count -ge 2 -and $output[-1] -eq 0)
    }
    Remove-Job $job -Force
    return $false
}

$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

if (-not (Test-Path $dockerDesktop)) {
    throw "Docker Desktop bulunamadı: $dockerDesktop"
}

if (Test-DockerEngine) {
    Write-Host "Docker zaten çalışıyor." -ForegroundColor Green
    exit 0
}

Write-Host "Yarım kalmış Docker Desktop süreçleri kapatılıyor..." -ForegroundColor Cyan
Get-Process -Name "Docker Desktop", "com.docker.backend", "com.docker.build" -ErrorAction SilentlyContinue |
    Stop-Process -Force
Start-Sleep -Seconds 3

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
foreach ($folder in $socketFolders) {
    if (Test-Path $folder) {
        $newName = "$(Split-Path $folder -Leaf).stale-$stamp"
        Rename-Item -Path $folder -NewName $newName
        Write-Host "Bozuk soket klasörü kenara alındı: $newName"
    }
}

Write-Host "Docker Desktop başlatılıyor..." -ForegroundColor Cyan
Start-Process -FilePath $dockerDesktop

$deadline = (Get-Date).AddMinutes(4)
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-DockerEngine) {
        Write-Host "Docker hazır." -ForegroundColor Green
        exit 0
    }
}
Write-Warning "Docker 4 dakika içinde hazır olmadı. Docker Desktop penceresindeki hata mesajını kontrol edin."
exit 1
