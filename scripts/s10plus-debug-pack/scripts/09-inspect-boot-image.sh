#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
IMG="${1:-}"
[ -n "$IMG" ] && [ -f "$IMG" ] || die "Usage: $0 /path/to/nuxel-beyond2lte-boot-merged-fixed.img"
init_out boot-image
require_cmd python3
python3 "$PACK_DIR/tools/inspect_android_boot.py" "$IMG" --out "$NUXEL_OUT/boot-image"
say 'Offline inspection only; this cannot prove S-Boot acceptance or display driver support.'
