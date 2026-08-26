#!/usr/bin/env bash
set -euo pipefail

IMAGE="${PHOENIX_IMAGE:-phoenix-cosyvoice-cloud-v1:latest}"
NAME="${PHOENIX_CONTAINER_NAME:-phoenix-cosyvoice}"
PORT="${PHOENIX_PORT:-6006}"
DATA_DIR="${PHOENIX_DATA_DIR:-/root/autodl-tmp/phoenix-cosyvoice-data}"

mkdir -p "$DATA_DIR/projects" "$DATA_DIR/logs"

if docker ps -a --format '{{.Names}}' | grep -qx "$NAME"; then
  docker rm -f "$NAME" >/dev/null
fi

docker run -d \
  --name "$NAME" \
  --gpus all \
  --restart unless-stopped \
  -p "$PORT:6006" \
  -v "$DATA_DIR/projects:/workspace/phoenix-cosyvoice/projects" \
  -v "$DATA_DIR/logs:/workspace/phoenix-cosyvoice/logs" \
  -e PHOENIX_PORT=6006 \
  -e PHOENIX_TRANSLATION_PROVIDER="${PHOENIX_TRANSLATION_PROVIDER:-aliyun}" \
  -e PHOENIX_ALIYUN_ACCESS_KEY_ID="${PHOENIX_ALIYUN_ACCESS_KEY_ID:-${ALIBABA_CLOUD_ACCESS_KEY_ID:-}}" \
  -e PHOENIX_ALIYUN_ACCESS_KEY_SECRET="${PHOENIX_ALIYUN_ACCESS_KEY_SECRET:-${ALIBABA_CLOUD_ACCESS_KEY_SECRET:-}}" \
  -e PHOENIX_ALIYUN_TRANSLATE_REGION="${PHOENIX_ALIYUN_TRANSLATE_REGION:-cn-hangzhou}" \
  -e PHOENIX_ALIYUN_TRANSLATE_ENDPOINT="${PHOENIX_ALIYUN_TRANSLATE_ENDPOINT:-mt.cn-hangzhou.aliyuncs.com}" \
  "$IMAGE"

echo "Phoenix CosyVoice container started: $NAME"
echo "Open AutoDL custom service port: $PORT"
echo "Logs: docker logs -f $NAME"
