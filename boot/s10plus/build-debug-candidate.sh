#!/usr/bin/env bash
# =============================================================================
# build-debug-candidate.sh — build the S10+ BOOT diagnostic candidate (gated)
#
# REWRITTEN 2026-10-15.  The previous version defaulted to the ORIGINAL,
# hardware-falsified image
#     build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img
# and piped it through tools/s10plus/patch-boot-from-upload.py, which produced a
# container with (a) a GZIP kernel payload and (b) the DTB size written at header
# offset 40 where boot_img_hdr_v1 requires `header_version`.  Both defects are
# hardware-proven to stop this handset dead (attempt A1: seven silent loads).
# That is a *regression generator* and it has been removed from this path.
#
# The default base is now the last hardware-proven container and every build is
# checked by tools/s10plus/verify-boot-image.py before it is reported.
#
# Usage: boot/s10plus/build-debug-candidate.sh [OUTPUT_IMG] [--compress MODE]
# =============================================================================
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)

OUT="$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-gated.img"
MODE="${NUXEL_CANDIDATE_COMPRESS:-none}"
while [ $# -gt 0 ]; do
  case "$1" in
    --compress) MODE="$2"; shift 2 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) OUT="$1"; shift ;;
  esac
done

echo "build-debug-candidate: NOTE this legacy entry point now delegates to"
echo "  boot/s10plus/build-candidate.sh (fail-closed, gated).  Prefer calling it directly."
echo "  For an LZMA ramdisk:  --compress lzma"
exec "$HERE/build-candidate.sh" --compress "$MODE" --out "$OUT"
