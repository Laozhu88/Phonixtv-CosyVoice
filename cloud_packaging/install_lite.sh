#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PHOENIX_PYTHON:-python}"
PIP_INDEX="${PHOENIX_PIP_INDEX:-https://pypi.org/simple}"
PIP_TRUSTED_HOST="${PHOENIX_PIP_TRUSTED_HOST:-}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python not found. Please create the AutoDL instance with a PyTorch or Miniconda image." >&2
  exit 1
fi

PIP_INDEX_ARGS=(-i "$PIP_INDEX" --no-cache-dir --retries 10 --timeout 120)
if [ -n "$PIP_TRUSTED_HOST" ]; then
  PIP_INDEX_ARGS+=("--trusted-host" "$PIP_TRUSTED_HOST")
fi

"$PYTHON_BIN" - <<'PY'
import sys
try:
    import torch
except Exception as exc:
    raise SystemExit(f"Torch is not available in this image: {exc}")
print("Python:", sys.executable)
print("Torch:", torch.__version__, "CUDA:", torch.cuda.is_available())
PY

"$PYTHON_BIN" -m pip install --upgrade "pip<26" "setuptools<70" wheel "${PIP_INDEX_ARGS[@]}"

"$PYTHON_BIN" - <<'PY' > /tmp/phoenix_torch_companions_install.sh
import re
import torch

version = torch.__version__
base = version.split("+", 1)[0]
cuda = torch.version.cuda or ""
if "+cu" in version:
    cu_tag = version.split("+", 1)[1]
elif cuda:
    parts = cuda.split(".")
    cu_tag = f"cu{parts[0]}{parts[1]}"
else:
    cu_tag = "cpu"

if cu_tag == "cpu":
    index = "https://download.pytorch.org/whl/cpu"
    audio_spec = f"torchaudio=={base}+cpu"
    vision_suffix = "+cpu"
else:
    index = f"https://download.pytorch.org/whl/{cu_tag}"
    audio_spec = f"torchaudio=={base}+{cu_tag}"
    vision_suffix = f"+{cu_tag}"

vision_map = {
    "2.0": "0.15",
    "2.1": "0.16",
    "2.2": "0.17",
    "2.3": "0.18",
    "2.4": "0.19",
    "2.5": "0.20",
    "2.6": "0.21",
    "2.7": "0.22",
    "2.8": "0.23",
}
major_minor = ".".join(base.split(".")[:2])
vision_base = vision_map.get(major_minor)
if vision_base:
    patch = base.split(".")[2] if len(base.split(".")) > 2 else "0"
    vision_spec = f"torchvision=={vision_base}.{patch}{vision_suffix}"
else:
    vision_spec = "torchvision"

print("python -m pip uninstall -y torchaudio torchvision || true")
print(f'python -m pip install --no-cache-dir --force-reinstall --no-deps "{audio_spec}" "{vision_spec}" --index-url "{index}"')
PY
bash /tmp/phoenix_torch_companions_install.sh

"$PYTHON_BIN" -m pip install -r "$ROOT/cloud_packaging/requirements-lite.txt" --no-build-isolation "${PIP_INDEX_ARGS[@]}"

if command -v conda >/dev/null 2>&1; then
  conda install -y -c conda-forge pynini==2.1.5 || true
fi

echo "Lite runtime dependencies are ready."
