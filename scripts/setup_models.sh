#!/usr/bin/env bash
# Downloads the Kokoro-82M voice model (Apache 2.0) from its GitHub release.
set -euo pipefail
DIR="${KOKORO_DIR:-$HOME/.cache/kokoro}"
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
mkdir -p "$DIR"
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  if [ ! -s "$DIR/$f" ]; then
    curl -sSL -o "$DIR/$f.part" "$BASE/$f"
    mv "$DIR/$f.part" "$DIR/$f"
  fi
done
ls -la "$DIR"
