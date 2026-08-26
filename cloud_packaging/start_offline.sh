#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${PHOENIX_CONDA_ENV:-$ROOT/offline_runtime/conda_envs/phoenix-cosyvoice}"
OFFICIAL_ROOT="${PHOENIX_OFFICIAL_COSYVOICE_ROOT:-$ROOT/offline_runtime/official/CosyVoice}"
OFFICIAL_MODEL="${PHOENIX_OFFICIAL_MODEL_DIR:-$OFFICIAL_ROOT/pretrained_models/Fun-CosyVoice3-0.5B}"

export PHOENIX_ENGINE_BACKEND=official
export PHOENIX_OFFICIAL_COSYVOICE_ROOT="$OFFICIAL_ROOT"
export PHOENIX_OFFICIAL_MODEL_DIR="$OFFICIAL_MODEL"
export PHOENIX_RAINFALL_HOME="$ROOT"
export PHOENIX_ASR_PYTHON="$ENV_PATH/bin/python"
export PHOENIX_HOST="${PHOENIX_HOST:-0.0.0.0}"
export PHOENIX_PORT="${PHOENIX_PORT:-6006}"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1
export PATH="$ENV_PATH/bin:$PATH"
export PYTHONPATH="$OFFICIAL_ROOT:$OFFICIAL_ROOT/third_party/Matcha-TTS:${PYTHONPATH:-}"

if [ ! -x "$ENV_PATH/bin/python" ]; then
  if [ -f "$ROOT/offline_runtime/conda_env.tar" ]; then
    echo "Extracting offline Python environment..."
    mkdir -p "$ROOT/offline_runtime/conda_envs"
    tar -xf "$ROOT/offline_runtime/conda_env.tar" -C "$ROOT/offline_runtime/conda_envs"
  fi
fi

if [ ! -d "$OFFICIAL_ROOT" ]; then
  if [ -f "$ROOT/offline_runtime/official_cosyvoice.tar" ]; then
    echo "Extracting official CosyVoice runtime and models..."
    mkdir -p "$ROOT/offline_runtime/official"
    tar -xf "$ROOT/offline_runtime/official_cosyvoice.tar" -C "$ROOT/offline_runtime/official"
  fi
fi

if [ ! -x "$ENV_PATH/bin/python" ]; then
  echo "Offline Python environment not found after extraction: $ENV_PATH" >&2
  exit 1
fi

if [ ! -f "$OFFICIAL_MODEL/llm.pt" ]; then
  echo "Official CosyVoice model not found: $OFFICIAL_MODEL" >&2
  exit 1
fi

mkdir -p "$ROOT/logs" "$ROOT/projects/outputs" "$ROOT/projects/temp" "$ROOT/projects/history" "$ROOT/projects/voice_library/audio"

"$ENV_PATH/bin/python" - <<'PY'
import os
import sys
from pathlib import Path
import torch

print("Python:", sys.executable)
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())
print("Backend:", os.environ.get("PHOENIX_ENGINE_BACKEND"))
print("Official root:", os.environ.get("PHOENIX_OFFICIAL_COSYVOICE_ROOT"))
print("Official model:", os.environ.get("PHOENIX_OFFICIAL_MODEL_DIR"))
print("Model llm.pt:", Path(os.environ["PHOENIX_OFFICIAL_MODEL_DIR"], "llm.pt").exists())
PY

exec "$ENV_PATH/bin/python" -m uvicorn app.backend.main:app \
  --host "$PHOENIX_HOST" \
  --port "$PHOENIX_PORT" \
  --app-dir "$ROOT"
