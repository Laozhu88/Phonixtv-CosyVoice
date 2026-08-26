#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${PHOENIX_IMAGE:-phoenix-cosyvoice-cloud-v1:latest}"
CUDA_BASE_IMAGE="${PHOENIX_CUDA_BASE_IMAGE:-nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04}"
UBUNTU_APT_MIRROR="${PHOENIX_UBUNTU_APT_MIRROR:-http://mirrors.aliyun.com/ubuntu}"
OUTPUT_DIR="${PHOENIX_IMAGE_OUTPUT_DIR:-$ROOT/release_staging}"
SAFE_IMAGE_NAME="$(printf '%s' "$IMAGE_NAME" | sed 's#[/:\\]#_#g')"
IMAGE_TAR="$OUTPUT_DIR/${SAFE_IMAGE_NAME}.tar"
DOCKER_CONFIG="${DOCKER_CONFIG:-$OUTPUT_DIR/.docker-config}"
export DOCKER_CONFIG

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not available. Install Docker or run this script on a Docker-enabled Linux build host." >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
mkdir -p "$DOCKER_CONFIG"
if [ ! -f "$DOCKER_CONFIG/config.json" ]; then
  printf '{}\n' > "$DOCKER_CONFIG/config.json"
fi

echo "Building Docker image: $IMAGE_NAME"
docker build --progress=plain --build-arg "CUDA_BASE_IMAGE=$CUDA_BASE_IMAGE" --build-arg "UBUNTU_APT_MIRROR=$UBUNTU_APT_MIRROR" -t "$IMAGE_NAME" -f "$ROOT/cloud_packaging/Dockerfile" "$ROOT"

echo "Saving Docker image tar: $IMAGE_TAR"
rm -f "$IMAGE_TAR"
docker save -o "$IMAGE_TAR" "$IMAGE_NAME"

echo "Done."
echo "Upload this image tar to AutoDL with the source zip:"
echo "  $IMAGE_TAR"
