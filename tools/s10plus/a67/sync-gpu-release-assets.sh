#!/usr/bin/env bash
# Copy the canonical GPU helper/policy/session sources into the release asset
# directory and regenerate the pinned manifest.  Used before release images and
# after any graphics policy change.  Fails if a source is missing.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
GPU="$ROOT/release/s10plus/gpu"
install -m 0755 "$ROOT/tools/s10plus/a45/nuxel-graphics-profile" "$GPU/nuxel-graphics-profile"
install -m 0644 "$ROOT/configs/nuxel/graphics/graphics-profile.json" "$GPU/graphics-profile.json"
install -m 0755 "$ROOT/tools/s10plus/a67/nuxel-gpu-status" "$GPU/nuxel-gpu-status"
install -m 0755 "$ROOT/tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh" "$GPU/nuxel-wayland-gpu-wrapper.sh"
install -m 0755 "$ROOT/tools/s10plus/a45/nuxel-session.sh" "$GPU/nuxel-session.sh"
python3 "$ROOT/tools/s10plus/a67/gen-gpu-manifest.py"
( cd "$GPU" && sha256sum -c SHA256SUMS )
