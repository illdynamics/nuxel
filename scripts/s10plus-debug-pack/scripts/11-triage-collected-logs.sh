#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
DIR="${1:-${NUXEL_OUT:-}}"
[ -n "$DIR" ] && [ -d "$DIR" ] || die "Usage: $0 /path/to/capture-directory"
require_cmd python3
python3 "$PACK_DIR/tools/triage.py" "$DIR"
