#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
FILE="${1:-}"
[ -f "$FILE" ] || die 'Usage: 17-pstore-decode-offline.sh /path/to/pstore-file'
init_out pstore-decode
python3 "$PACK_DIR/tools/decode_pstore.py" "$FILE" --out "$NUXEL_OUT/pstore-decoded"
say 'Only operates on a local copy; raw pstore files are never modified.'
