#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
DIR="${1:-}"
[ -n "$DIR" ] && [ -d "$DIR" ] || die "Usage: $0 /path/to/capture-directory [output.zip]"
DEST="${2:-${DIR%/}-REDACTED.zip}"
python3 "$PACK_DIR/tools/create_share_bundle.py" "$DIR" "$DEST"
say "Inspect the redacted ZIP and TRIAGE.md before sharing; automated masking cannot catch every secret."
