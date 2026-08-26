#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PHOENIX_PYTHON:-python}"
OFFICIAL_ROOT="${PHOENIX_OFFICIAL_COSYVOICE_ROOT:-$ROOT/runtime/official/CosyVoice}"
OFFICIAL_MODEL="${PHOENIX_OFFICIAL_MODEL_DIR:-$OFFICIAL_ROOT/pretrained_models/Fun-CosyVoice3-0.5B}"

if [ ! -d "$OFFICIAL_ROOT" ] && [ -f "$ROOT/runtime/official_cosyvoice.tar" ]; then
  echo "Extracting official CosyVoice runtime and model..."
  mkdir -p "$ROOT/runtime/official"
  tar -xf "$ROOT/runtime/official_cosyvoice.tar" -C "$ROOT/runtime/official"
fi

if [ ! -f "$OFFICIAL_ROOT/third_party/Matcha-TTS/matcha/__init__.py" ] && [ -d "$ROOT/third_party/Matcha-TTS" ]; then
  echo "Installing bundled Matcha-TTS into official CosyVoice runtime..."
  rm -rf "$OFFICIAL_ROOT/third_party/Matcha-TTS"
  mkdir -p "$OFFICIAL_ROOT/third_party"
  cp -a "$ROOT/third_party/Matcha-TTS" "$OFFICIAL_ROOT/third_party/"
fi

export PHOENIX_ENGINE_BACKEND=official
export PHOENIX_OFFICIAL_COSYVOICE_ROOT="$OFFICIAL_ROOT"
export PHOENIX_OFFICIAL_MODEL_DIR="$OFFICIAL_MODEL"
export PHOENIX_RAINFALL_HOME="$ROOT"
export PHOENIX_ASR_PYTHON="$PYTHON_BIN"
export PHOENIX_HOST="${PHOENIX_HOST:-0.0.0.0}"
export PHOENIX_PORT="${PHOENIX_PORT:-6006}"
export PYTHONUNBUFFERED=1
export PYTHONUTF8=1
export PYTHONPATH="$OFFICIAL_ROOT:$OFFICIAL_ROOT/third_party/Matcha-TTS:${PYTHONPATH:-}"

mkdir -p "$ROOT/logs" "$ROOT/projects/outputs" "$ROOT/projects/temp" "$ROOT/projects/history" "$ROOT/projects/voice_library/audio"

if [ ! -f "$OFFICIAL_MODEL/llm.pt" ]; then
  echo "Official CosyVoice model not found: $OFFICIAL_MODEL" >&2
  exit 1
fi

"$PYTHON_BIN" - <<'PY'
import os
import sys
from pathlib import Path
import torch
import torchaudio
import torchvision
import whisper

print("Python:", sys.executable)
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())
print("Torchaudio:", torchaudio.__version__)
print("Torchvision:", torchvision.__version__)
print("Whisper:", getattr(whisper, "__version__", "installed"))
print("Backend:", os.environ.get("PHOENIX_ENGINE_BACKEND"))
print("Official model:", os.environ.get("PHOENIX_OFFICIAL_MODEL_DIR"))
print("SenseVoice:", Path(os.environ.get("PHOENIX_RAINFALL_HOME", "."), "models", "SenseVoiceSmall", "model.pt").exists())
PY

exec "$PYTHON_BIN" -m uvicorn app.backend.main:app \
  --host "$PHOENIX_HOST" \
  --port "$PHOENIX_PORT" \
  --app-dir "$ROOT"
