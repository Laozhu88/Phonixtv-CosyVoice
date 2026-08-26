#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${PHOENIX_CONDA_ENV:-/root/autodl-tmp/conda_envs/cosyvoice-official}"

if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
  source /opt/conda/etc/profile.d/conda.sh
elif [ -f /root/miniconda3/etc/profile.d/conda.sh ]; then
  source /root/miniconda3/etc/profile.d/conda.sh
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
fi

conda activate "$ENV_PATH"

cd "$ROOT"

export PHOENIX_ENGINE_BACKEND="${PHOENIX_ENGINE_BACKEND:-official}"
export PHOENIX_OFFICIAL_COSYVOICE_ROOT="${PHOENIX_OFFICIAL_COSYVOICE_ROOT:-/root/autodl-tmp/official/CosyVoice-official}"
export PHOENIX_OFFICIAL_MODEL_DIR="${PHOENIX_OFFICIAL_MODEL_DIR:-$PHOENIX_OFFICIAL_COSYVOICE_ROOT/pretrained_models/Fun-CosyVoice3-0.5B}"
export PHOENIX_RAINFALL_HOME="${PHOENIX_RAINFALL_HOME:-$ROOT}"
export PHOENIX_ASR_PYTHON="${PHOENIX_ASR_PYTHON:-$(command -v python)}"
export PHOENIX_HOST="${PHOENIX_HOST:-0.0.0.0}"
export PHOENIX_PORT="${PHOENIX_PORT:-6006}"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1

mkdir -p logs projects/outputs projects/temp projects/history projects/voice_library/audio

python - <<'PY'
import os
import sys
from pathlib import Path
import torch

print("Python:", sys.executable)
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())
print("Backend:", os.environ.get("PHOENIX_ENGINE_BACKEND"))
print("Official root:", os.environ.get("PHOENIX_OFFICIAL_COSYVOICE_ROOT"))
print("Official model:", os.environ.get("PHOENIX_OFFICIAL_MODEL_DIR"))
print("SenseVoice:", Path(os.environ.get("PHOENIX_RAINFALL_HOME", "."), "models", "SenseVoiceSmall").exists())
if not Path(os.environ["PHOENIX_OFFICIAL_MODEL_DIR"]).exists():
    raise SystemExit("Official CosyVoice model directory not found")
PY

python -m uvicorn app.backend.main:app \
  --host "$PHOENIX_HOST" \
  --port "$PHOENIX_PORT" \
  --app-dir "$ROOT"
