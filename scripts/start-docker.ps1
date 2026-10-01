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

  The cleanup only works once Docker Desktop has fully exited, so the script waits for its
  processes to stop, and if the start still crashes on a socket it cleans up and tries again.

  Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-docker.ps1
#>
$ErrorActionPreference = "Stop"

$dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$backendLogDir = "$env:LOCALAPPDATA\Docker\log\host"
$socketFolders = @(
    "$env:LOCALAPPDATA\Docker\run",
    "$env:LOCALAPPDATA\docker-secrets-engine"
)
$dockerProcesses = @("Docker Desktop", "com.docker.backend", "com.docker.build", "docker")
$maxAttempts = 2

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

function Stop-DockerDesktop {
    Get-Process -Name $dockerProcesses -ErrorAction SilentlyContinue | Stop-Process -Force
    for ($i = 0; $i -lt 20; $i++) {
        if (-not (Get-Process -Name $dockerProcesses -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Seconds 1
    }
    # Give Windows a moment to release the folders after the processes are gone.
    Start-Sleep -Seconds 3
}

function Move-StaleSocketFolders {
    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    foreach ($folder in $socketFolders) {
        if (Test-Path $folder) {
            $newName = "$(Split-Path $folder -Leaf).stale-$stamp"
            Rename-Item -Path $folder -NewName $newName
            Write-Host "Bozuk soket klasörü kenara alındı: $newName"
        }
        if (Test-Path $folder) {
            throw "Klasör kenara alınamadı: $folder"
        }
    }
}

function Test-SocketCrashSince([datetime]$since) {
    # The backend logs "backend cancelling with error: starting services: initializing ..."
    # when it trips over a stale socket.
    # Docker rotates this log when it starts, so look at the current and the previous file.
    $logs = Get-ChildItem $backendLogDir -Filter "com.docker.backend.exe.log*" -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending | Select-Object -First 2
    foreach ($line in ($logs | ForEach-Object { Get-Content $_.FullName -Tail 600 })) {
        if ($line -notmatch 'backend cancelling with error: starting services: initializing') { continue }
        # Timestamps look like [2026-10-01T05:47:44.899784600Z] (UTC); seconds precision is enough.
        if ($line -match '^\[(?<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})') {
            $styles = [System.Globalization.DateTimeStyles]::AssumeUniversal -bor [System.Globalization.DateTimeStyles]::AdjustToUniversal
            $when = [datetime]::ParseExact($Matches.ts, "yyyy-MM-ddTHH:mm:ss", [System.Globalization.CultureInfo]::InvariantCulture, $styles)
            if ($when -ge $since.ToUniversalTime()) { return $true }
        }
    }
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

for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    Write-Host "Deneme $attempt/$($maxAttempts): Docker Desktop kapatılıyor ve bozuk soketler temizleniyor..." -ForegroundColor Cyan
    Stop-DockerDesktop
    Move-StaleSocketFolders

    $startedAt = Get-Date
    Write-Host "Docker Desktop başlatılıyor..." -ForegroundColor Cyan
    Start-Process -FilePath $dockerDesktop

    $deadline = $startedAt.AddMinutes(4)
    while ((Get-Date) -lt $deadline) {
        Start-Sleep -Seconds 5
        if (Test-DockerEngine) {
            Write-Host "Docker hazır." -ForegroundColor Green
            exit 0
        }
        if (Test-SocketCrashSince $startedAt) {
            Write-Warning "Docker yine bir soket hatasıyla durdu; temizlik tekrarlanacak."
            break
        }
    }
}

Write-Warning "Docker başlatılamadı. Docker Desktop penceresindeki hata mesajını kontrol edin."
exit 1
