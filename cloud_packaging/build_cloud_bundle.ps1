param(
    [string]$OutputDir = "release_staging",
    [string]$BundleName = "Phonixtv-CosyVoice-Cloud-Official-V1",
    [string]$ResourceZip = "",
    [switch]$IncludeRainfallResources,
    [switch]$SkipLargeResources,
    [switch]$BuildDockerImage,
    [switch]$SaveDockerImage,
    [string]$ImageName = "phoenix-cosyvoice-cloud-v1:latest",
    [string]$CudaBaseImage = "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04",
    [string]$UbuntuAptMirror = "http://mirrors.aliyun.com/ubuntu"
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$StageRoot = Join-Path $Root $OutputDir
$Stage = Join-Path $StageRoot $BundleName

if (Test-Path $Stage) {
    Remove-Item -LiteralPath $Stage -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Stage | Out-Null

$items = @(
    "app",
    "config",
    "docs",
    "cloud_packaging",
    ".dockerignore",
    "PhoenixTV_LogoA.png",
    "PhoenixTV_LogoB.png",
    "README.md"
)

if ($IncludeRainfallResources -and -not $SkipLargeResources) {
    $items += @("models", "resources", "cosyvoice", "third_party")
} elseif (-not $SkipLargeResources) {
    $items += @("models")
}

foreach ($item in $items) {
    $src = Join-Path $Root $item
    if (Test-Path $src) {
        $dst = Join-Path $Stage $item
        Copy-Item -LiteralPath $src -Destination $dst -Recurse -Force
    }
}

$localConfig = Join-Path $Stage "config\app.local.json"
if (Test-Path $localConfig) {
    Remove-Item -LiteralPath $localConfig -Force
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

@'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/cloud_packaging/install_once.sh" "$@"
'@ | Set-Content -LiteralPath (Join-Path $Stage "install_once.sh") -Encoding UTF8

@'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/cloud_packaging/start_cloud.sh" "$@"
'@ | Set-Content -LiteralPath (Join-Path $Stage "start_cloud.sh") -Encoding UTF8

@'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/cloud_packaging/start_container.sh" "$@"
'@ | Set-Content -LiteralPath (Join-Path $Stage "start_container.sh") -Encoding UTF8

@'
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$ROOT/cloud_packaging/build_docker_image.sh" "$@"
'@ | Set-Content -LiteralPath (Join-Path $Stage "build_docker_image.sh") -Encoding UTF8

if ($IncludeRainfallResources -and -not $SkipLargeResources) {
    if ([string]::IsNullOrWhiteSpace($ResourceZip)) {
        $DefaultResourceZip = Join-Path (Split-Path $Root -Parent) "Phonixtv-CosyVoice-AutoDL-V1\cosyvoice-rainfall-linux-resources.zip"
    } else {
        $DefaultResourceZip = $ResourceZip
    }
    if (Test-Path $DefaultResourceZip) {
        Copy-Item -LiteralPath $DefaultResourceZip -Destination (Join-Path $Stage "cloud_packaging\cosyvoice-rainfall-linux-resources.zip") -Force
        Write-Host "Embedded resource zip: $DefaultResourceZip"
    } else {
        Write-Host "WARNING: resource zip not found. Cloud bundle may not contain CosyVoice model/runtime resources: $DefaultResourceZip"
    }
}

if (-not $SkipLargeResources -and -not $IncludeRainfallResources) {
    $SenseResourceZip = Join-Path $StageRoot "Phonixtv-CosyVoice-Cloud-V1\cloud_packaging\cosyvoice-rainfall-linux-resources.zip"
    if (-not (Test-Path $SenseResourceZip)) {
        $SenseResourceZip = Join-Path $Root "release_staging\Phonixtv-CosyVoice-Cloud-V1\cloud_packaging\cosyvoice-rainfall-linux-resources.zip"
    }
    if (Test-Path $SenseResourceZip) {
        $extractScript = Join-Path $env:TEMP "phoenix_extract_official_assets.py"
@'
import os
import sys
import zipfile

zip_path, stage = sys.argv[1], sys.argv[2]
prefixes = ("models/SenseVoiceSmall/", "third_party/Matcha-TTS/")
with zipfile.ZipFile(zip_path) as zf:
    for item in zf.infolist():
        if item.filename.endswith("/"):
            continue
        if item.filename.startswith(prefixes):
            target = os.path.join(stage, item.filename)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with zf.open(item) as src, open(target, "wb") as dst:
                dst.write(src.read())
'@ | Set-Content -LiteralPath $extractScript -Encoding UTF8
        python $extractScript $SenseResourceZip $Stage
        Write-Host "Embedded official cloud assets from: $SenseResourceZip"
    } else {
        Write-Host "WARNING: SenseVoiceSmall/Matcha resource zip not found. Reference ASR may not work until resources are copied."
    }
}

$zipPath = Join-Path $StageRoot "$BundleName.zip"
if (Test-Path $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}

$zipScript = Join-Path $env:TEMP "phoenix_cloud_zip64.py"
@'
import os
import sys
import zipfile

stage = sys.argv[1]
zip_path = sys.argv[2]
base_parent = os.path.dirname(stage)

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
    for root, dirs, files in os.walk(stage):
        dirs.sort()
        files.sort()
        for name in files:
            path = os.path.join(root, name)
            rel = os.path.relpath(path, base_parent)
            if name.lower().endswith((".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz", ".wav", ".mp3", ".mp4")):
                zf.write(path, rel, compress_type=zipfile.ZIP_STORED)
            else:
                zf.write(path, rel)
'@ | Set-Content -LiteralPath $zipScript -Encoding UTF8

python $zipScript $Stage $zipPath

Write-Host "Cloud bundle staged at: $Stage"
Write-Host "Cloud bundle zip: $zipPath"
if ($SkipLargeResources) {
    Write-Host "SkipLargeResources enabled: models/resources/cosyvoice/third_party were not included."
}

if ($BuildDockerImage -or $SaveDockerImage) {
    $docker = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $docker) {
        throw "Docker is not available on this machine. Install Docker Desktop or run this step on a Linux build host."
    }
    $DockerConfigDir = Join-Path $StageRoot ".docker-config"
    New-Item -ItemType Directory -Force -Path $DockerConfigDir | Out-Null
    if (-not (Test-Path (Join-Path $DockerConfigDir "config.json"))) {
        "{}" | Set-Content -LiteralPath (Join-Path $DockerConfigDir "config.json") -Encoding ASCII
    }
    $env:DOCKER_CONFIG = $DockerConfigDir
    docker build --progress=plain --build-arg "CUDA_BASE_IMAGE=$CudaBaseImage" --build-arg "UBUNTU_APT_MIRROR=$UbuntuAptMirror" -t $ImageName -f (Join-Path $Stage "cloud_packaging\Dockerfile") $Stage
    if ($LASTEXITCODE -ne 0) {
        throw "docker build failed"
    }
}

if ($SaveDockerImage) {
    $safeImageName = ($ImageName -replace "[:/\\]", "_")
    $imageTar = Join-Path $StageRoot "$safeImageName.tar"
    if (Test-Path $imageTar) {
        Remove-Item -LiteralPath $imageTar -Force
    }
    docker save -o $imageTar $ImageName
    if ($LASTEXITCODE -ne 0) {
        throw "docker save failed"
    }
    Write-Host "Docker image tar: $imageTar"
    Write-Host "Upload both the source zip and image tar, then run: docker load -i $safeImageName.tar && bash start_container.sh"
}
