$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$rainfallReal = Join-Path $projectRoot "runtime\rainfall"
if (-not (Test-Path (Join-Path $rainfallReal "python\python.exe"))) {
    $rainfallReal = "F:\cosyvoice-rainfall-v2\cosyvoice-rainfall"
}
$rainfallDrive = $null

if (-not (Test-Path (Join-Path $rainfallReal "python\python.exe"))) {
    Write-Host "Rainfall embedded python not found:"
    Write-Host (Join-Path $rainfallReal "python\python.exe")
    Read-Host "Press Enter to exit"
    exit 1
}

foreach ($letter in @("R", "S", "T", "U", "V", "W", "X", "Y", "Z")) {
    if (-not (Test-Path "$letter`:\")) {
        & subst.exe "$letter`:" $rainfallReal
        if (Test-Path "$letter`:\python\python.exe") {
            $rainfallDrive = "$letter`:"
            break
        }
    }
}

if (-not $rainfallDrive) {
    Write-Host "Unable to create an ASCII runtime drive. Please free one drive letter from R: to Z: and try again."
    Read-Host "Press Enter to exit"
    exit 1
}

$rainfallRoot = "$rainfallDrive\"
$pythonPath = Join-Path $rainfallRoot "python\python.exe"
$asrPython = Join-Path $projectRoot "runtime\asr\Scripts\python.exe"
if (-not (Test-Path $asrPython)) {
    $asrPython = $pythonPath
}

try {
    Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique |
        ForEach-Object {
            Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
        }

    Start-Sleep -Seconds 1
    $env:PHOENIX_RAINFALL_HOME = $rainfallRoot
    $env:PHOENIX_ASR_PYTHON = $asrPython
    Start-Process "http://127.0.0.1:8090"
    & $pythonPath -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8090 --app-dir $projectRoot
    exit $LASTEXITCODE
}
finally {
    & subst.exe $rainfallDrive /D | Out-Null
}
