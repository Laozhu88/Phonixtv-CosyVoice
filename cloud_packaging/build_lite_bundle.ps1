param(
    [string]$OutputDir = "release_staging",
    [string]$BundleName = "Phonixtv-CosyVoice-AutoDL-Lite-V1",
    [switch]$IncludeLocalConfig,
    [string]$OfficialCosyVoiceTar = "",
    [string]$SenseVoiceDir = ""
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$StageRoot = Join-Path $Root $OutputDir
$Stage = Join-Path $StageRoot $BundleName
$Runtime = Join-Path $Stage "runtime"

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
    "install_lite.sh",
    "start_lite.sh"
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

$officialCandidates = @()
if (-not [string]::IsNullOrWhiteSpace($OfficialCosyVoiceTar)) {
    $officialCandidates += $OfficialCosyVoiceTar
}
$officialCandidates += @(
    (Join-Path $Root "release_staging\Phonixtv-CosyVoice-AutoDL-Offline-V1\offline_runtime\official_cosyvoice.tar"),
    (Join-Path $StageRoot "Phonixtv-CosyVoice-AutoDL-Offline-V1\offline_runtime\official_cosyvoice.tar")
)
$officialSource = $officialCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $officialSource) {
    throw "official_cosyvoice.tar not found. Build the offline package once or pass -OfficialCosyVoiceTar."
}
Copy-Item -LiteralPath $officialSource -Destination (Join-Path $Runtime "official_cosyvoice.tar") -Force
Write-Host "Embedded official CosyVoice runtime/model tar: $officialSource"

$senseCandidates = @()
if (-not [string]::IsNullOrWhiteSpace($SenseVoiceDir)) {
    $senseCandidates += $SenseVoiceDir
}
$senseCandidates += @(
    (Join-Path $Root "models\SenseVoiceSmall"),
    (Join-Path $Root "release_staging\Phonixtv-CosyVoice-AutoDL-Offline-V1\models\SenseVoiceSmall"),
    (Join-Path $Root "release_staging\PhoenixTV-IndexTTS-Cloud-V1\models\SenseVoiceSmall")
)
$discoveredSenseVoice = Get-ChildItem -Path (Join-Path $Root "release_staging") -Recurse -Filter "model.pt" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like "*SenseVoiceSmall*" } |
    ForEach-Object { $_.Directory.FullName } |
    Select-Object -Unique
$senseCandidates += $discoveredSenseVoice
$senseSource = $senseCandidates | Where-Object { Test-Path (Join-Path $_ "model.pt") } | Select-Object -First 1
if ($senseSource) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Stage "models") | Out-Null
    Copy-Item -LiteralPath $senseSource -Destination (Join-Path $Stage "models\SenseVoiceSmall") -Recurse -Force
    Write-Host "Embedded SenseVoiceSmall from: $senseSource"
} else {
    Write-Host "WARNING: SenseVoiceSmall model not found. Reference audio ASR will not work until copied."
}

$matchaCandidates = @(
    (Join-Path $Root "third_party\Matcha-TTS")
)
$discoveredMatcha = Get-ChildItem -Path (Join-Path $Root "release_staging") -Recurse -Filter "__init__.py" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -like "*Matcha-TTS*matcha*" } |
    ForEach-Object { $_.Directory.Parent.FullName } |
    Select-Object -Unique
$matchaCandidates += $discoveredMatcha
$matchaSource = $matchaCandidates | Where-Object { Test-Path (Join-Path $_ "matcha\__init__.py") } | Select-Object -First 1
if ($matchaSource) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Stage "third_party") | Out-Null
    Copy-Item -LiteralPath $matchaSource -Destination (Join-Path $Stage "third_party\Matcha-TTS") -Recurse -Force
    Write-Host "Embedded Matcha-TTS from: $matchaSource"
} else {
    Write-Host "WARNING: Matcha-TTS not found. Official CosyVoice generation will fail until copied."
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
if (Test-Path (Join-Path $Root "projects\channel_templates.json")) {
    Copy-Item -LiteralPath (Join-Path $Root "projects\channel_templates.json") -Destination (Join-Path $Stage "projects\channel_templates.json") -Force
} else {
    "[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\channel_templates.json") -Encoding UTF8
}
"[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\history\task_history.json") -Encoding UTF8
"[]" | Set-Content -LiteralPath (Join-Path $Stage "projects\voice_library\metadata.json") -Encoding UTF8

$readme = @"
# AutoDL Lite runtime

This package does not include a conda/Python environment. Create the AutoDL instance with a PyTorch image, upload this tar under /root/autodl-tmp, then run:

```bash
cd /root/autodl-tmp
tar -xf Phonixtv-CosyVoice-AutoDL-Lite-V1.tar
cd Phonixtv-CosyVoice-AutoDL-Lite-V1
chmod +x install_lite.sh start_lite.sh cloud_packaging/*.sh
bash install_lite.sh
bash start_lite.sh
```

Open AutoDL custom service port 6006.

Notes:
- Docker is not required on AutoDL.
- Official CosyVoice source/model and SenseVoiceSmall are included.
- Matcha-TTS is bundled and copied into the official CosyVoice runtime at startup if missing.
- Python packages are installed into the selected AutoDL image environment.
- If config/app.local.json is included, translation credentials are read automatically.
"@
$readme | Set-Content -LiteralPath (Join-Path $Stage "AUTODL_LITE_README.md") -Encoding UTF8

$tarPath = Join-Path $StageRoot "$BundleName.tar"
if (Test-Path $tarPath) {
    Remove-Item -LiteralPath $tarPath -Force
}

tar -cf $tarPath -C $StageRoot $BundleName
if ($LASTEXITCODE -ne 0) {
    throw "tar packaging failed"
}

Write-Host "Lite bundle staged at: $Stage"
Write-Host "Lite bundle tar: $tarPath"
