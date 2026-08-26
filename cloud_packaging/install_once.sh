#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_PATH="${PHOENIX_CONDA_ENV:-${PHOENIX_OFFICIAL_CONDA_ENV:-/root/autodl-tmp/conda_envs/cosyvoice-official}}"
OFFICIAL_ROOT="${PHOENIX_OFFICIAL_COSYVOICE_ROOT:-/root/autodl-tmp/official/CosyVoice-official}"
OFFICIAL_MODEL="${PHOENIX_OFFICIAL_MODEL_DIR:-$OFFICIAL_ROOT/pretrained_models/Fun-CosyVoice3-0.5B}"
PIP_INDEX="${PHOENIX_PIP_INDEX:-https://pypi.org/simple}"
PIP_TRUSTED_HOST="${PHOENIX_PIP_TRUSTED_HOST:-}"

if [ -f /opt/conda/etc/profile.d/conda.sh ]; then
  source /opt/conda/etc/profile.d/conda.sh
elif [ -f /root/miniconda3/etc/profile.d/conda.sh ]; then
  source /root/miniconda3/etc/profile.d/conda.sh
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
  source "$HOME/miniconda3/etc/profile.d/conda.sh"
else
  echo "Conda not found. Please use an AutoDL PyTorch/Miniconda image."
  exit 1
fi

mkdir -p "$(dirname "$ENV_PATH")" /root/autodl-tmp/official

conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true

if [ ! -d "$ENV_PATH" ]; then
  conda create -p "$ENV_PATH" -y python=3.10
fi

conda activate "$ENV_PATH"

python -m pip install --upgrade pip
PIP_INDEX_ARGS=(-i "$PIP_INDEX" --no-cache-dir --retries 10 --timeout 120)
if [ -n "$PIP_TRUSTED_HOST" ]; then
  PIP_INDEX_ARGS+=("--trusted-host" "$PIP_TRUSTED_HOST")
fi

python -m pip install "setuptools<70" --force-reinstall "${PIP_INDEX_ARGS[@]}"
conda install -y -c conda-forge pynini==2.1.5
python -m pip install -r "$ROOT/cloud_packaging/requirements-cloud.txt" "${PIP_INDEX_ARGS[@]}"
python -m pip install --force-reinstall --no-deps torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu121 --no-cache-dir

if [ ! -d "$OFFICIAL_ROOT/.git" ]; then
  rm -rf "$OFFICIAL_ROOT"
  git clone https://github.com/FunAudioLLM/CosyVoice.git "$OFFICIAL_ROOT"
fi

mkdir -p "$OFFICIAL_ROOT/third_party"
if [ ! -d "$OFFICIAL_ROOT/third_party/Matcha-TTS" ] && [ -d "$ROOT/third_party/Matcha-TTS" ]; then
  cp -r "$ROOT/third_party/Matcha-TTS" "$OFFICIAL_ROOT/third_party/"
fi

if [ ! -d "$OFFICIAL_MODEL" ] || [ ! -f "$OFFICIAL_MODEL/llm.pt" ]; then
  python - <<PY
from modelscope import snapshot_download
snapshot_download(
    "FunAudioLLM/Fun-CosyVoice3-0.5B-2512",
    local_dir="$OFFICIAL_MODEL",
)
PY
fi

mkdir -p "$ROOT/logs" "$ROOT/projects/outputs" "$ROOT/projects/temp" "$ROOT/projects/history" "$ROOT/projects/voice_library/audio"

echo "Official CosyVoice cloud environment is ready."
echo "Start with:"
echo "  cd $ROOT"
echo "  bash cloud_packaging/start_official_cloud.sh"
