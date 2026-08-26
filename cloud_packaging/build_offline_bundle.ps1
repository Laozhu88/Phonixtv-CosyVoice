param(
    [string]$OutputDir = "release_staging",
    [string]$BundleName = "Phonixtv-CosyVoice-AutoDL-Offline-V1",
    [string]$ImageName = "phoenix-cosyvoice-cloud-v1:latest",
    [switch]$IncludeLocalConfig
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$StageRoot = Join-Path $Root $OutputDir
$Stage = Join-Path $StageRoot $BundleName
$Runtime = Join-Path $Stage "offline_runtime"

if (Test-Path $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
New-Item -ItemType Directory -Force -Path $Runtime | Out-Null

$items = @(
    "app",
    "config",
    "docs",
    "cloud_packaging",
    "PhoenixTV_LogoA.png",
    "PhoenixTV_LogoB.png",
    "README.md",
    "start_offline.sh"
)

foreach ($item in $items) {
    $src = Join-Path $Root $item
    if (Test-Path $src) {
        Copy-Item -LiteralPath $src -Destination (Join-Path $Stage $item) -Recurse -Force
    }
}

$localConfig = Join-Path $Stage "config\app.local.json"
if ((Test-Path $localConfig) -and -not $IncludeLocalConfig) {
    Remove-Item -LiteralPath $localConfig -Force
} elseif ((Test-Path $localConfig) -and $IncludeLocalConfig) {
    Write-Host "Included private config/app.local.json for cloud translation settings."
}

$projectDirs = @(
    "projects",
    "projects/outputs",
    "projects/temp",
    "projects/history",
    "projects/history/reference_audio",
    "projects/voice_library",
    "projects/voice_library/audio",
    "logs"
)
foreach ($dir in $projectDirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Stage $dir) | Out-Null
}

$senseVoiceCandidates = @(
    (Join-Path $Root "models\SenseVoiceSmall"),
    (Join-Path $Root "release_staging\PhoenixTV-IndexTTS-Cloud-V1\models\SenseVoiceSmall"),
    (Join-Path $Root "release_staging\凤凰卫视中文台多语种、多方言智能配音工作台_V1\runtime\rainfall\models\SenseVoiceSmall")
)
$senseVoiceSource = $senseVoiceCandidates | Where-Object { Test-Path (Join-Path $_ "model.pt") } | Select-Object -First 1
if ($senseVoiceSource) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Stage "models") | Out-Null
    Copy-Item -LiteralPath $senseVoiceSource -Destination (Join-Path $Stage "models\SenseVoiceSmall") -Recurse -Force
    Write-Host "Embedded SenseVoiceSmall from: $senseVoiceSource"
} else {
    Write-Host "WARNING: SenseVoiceSmall model not found. Reference audio ASR will not work offline."
}

if (Test-Path (Join-Path $Root "projects\channel_templates.json")) {
    Copy-Item -LiteralPath (Join-Path $Root "projects\channel_templates.json") -Destination (Join-Path $Stage "projects\channel_templates.json") -Force
} else {
    "[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\channel_templates.json") -Encoding UTF8
}
"[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\history\task_history.json") -Encoding UTF8
"[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\voice_library\metadata.json") -Encoding UTF8

$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    throw "Docker is required on the build machine to export the already-built image."
}

$runtimeForDocker = $Runtime.Replace("\", "/")
docker run --rm -v "${runtimeForDocker}:/export" $ImageName bash -lc "set -euo pipefail; tar -cf /export/conda_env.tar -C /opt/conda/envs phoenix-cosyvoice; tar -cf /export/official_cosyvoice.tar -C /opt/phoenix/official CosyVoice"
if ($LASTEXITCODE -ne 0) {
    throw "docker runtime export failed"
}

$readme = @"
# AutoDL no-Docker offline runtime

Upload and extract this package under /root/autodl-tmp, then run:

```bash
cd /root/autodl-tmp/Phonixtv-CosyVoice-AutoDL-Offline-V1
chmod +x start_offline.sh cloud_packaging/*.sh
bash start_offline.sh
```

Open AutoDL custom service port 6006 after startup.

Notes:
- Docker is not required on AutoDL.
- Python environment, official CosyVoice source, and model files are included.
- If config/app.local.json is included, translation credentials are read automatically.
- Runtime data is stored in projects/ and logs/.
"@
$readme | Set-Content -LiteralPath (Join-Path $Stage "AUTODL_OFFLINE_README.md") -Encoding UTF8

$tarPath = Join-Path $StageRoot "$BundleName.tar"
if (Test-Path $tarPath) {
    Remove-Item -LiteralPath $tarPath -Force
}

tar -cf $tarPath -C $StageRoot $BundleName
if ($LASTEXITCODE -ne 0) {
    throw "tar packaging failed"
}

Write-Host "Offline bundle staged at: $Stage"
Write-Host "Offline bundle tar: $tarPath"
