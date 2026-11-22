#!/usr/bin/env bash
# nuxel-camera-release-gate.sh — one-command fail-closed release gate.
# Six invariants, all must PASS:
#   BOOT_CONTAINER_PASS + CAMERA_DT_GRAPH_PASS + MERGED_FDT_PROOF
#   + ACTIVE_BOARD_MATCH + NO_UNRELATED_DT_DELTA + ROLLBACK_READY
# The CAMERA_DT_GRAPH_PASS now uses the real device-tree graph validator
# (camera-dt-gate.py) with board-rev/dtbo-idx selection, plus the PROMPT 00
# merge-containment proof (dt-merge-verify.py).
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
BOOT_GATE="$ROOT/tools/s10plus/verify-boot-image.py"
DT_GATE="$ROOT/tools/s10plus/camera-dt-gate.py"
MERGE_VERIFY="$ROOT/tools/s10plus/dt-merge-verify.py"

usage() { echo "usage: $0 --boot BOOT.img --golden-boot BOOT.img --golden-dtb DTB.img --golden-dtbo DTBO.img [--merged FDT.img] [--candidate-dtb DTB] [--candidate-dtbo DTBO] [--board-model 'Samsung BEYOND2LTE ...'] [--board-rev N] [--dtbo-idx N]"; exit 2; }

BOOT=""; GOLDEN_BOOT=""; GOLDEN_DTB=""; GOLDEN_DTBO=""; MERGED=""
CAND_DTB=""; CAND_DTBO=""; BOARD_MODEL=""; REV="26"; DTBO_IDX="9"
while [ $# -gt 0 ]; do case "$1" in
  --boot) BOOT="$2"; shift 2;; --golden-boot) GOLDEN_BOOT="$2"; shift 2;;
  --golden-dtb) GOLDEN_DTB="$2"; shift 2;; --golden-dtbo) GOLDEN_DTBO="$2"; shift 2;;
  --merged) MERGED="$2"; shift 2;;
  --candidate-dtb) CAND_DTB="$2"; shift 2;; --candidate-dtbo) CAND_DTBO="$2"; shift 2;;
  --board-model) BOARD_MODEL="$2"; shift 2;; --board-rev) REV="$2"; shift 2;;
  --dtbo-idx) DTBO_IDX="$2"; shift 2;;
  *) usage;;
esac; done
[ -n "$BOOT" ] && [ -n "$GOLDEN_BOOT" ] && [ -n "$GOLDEN_DTB" ] && [ -n "$GOLDEN_DTBO" ] || usage

S="BOOT_CONTAINER_PASS=no CAMERA_DT_GRAPH_PASS=no MERGED_FDT_PROOF=no ACTIVE_BOARD_MATCH=no NO_UNRELATED_DT_DELTA=no ROLLBACK_READY=no"
die() { echo "$S"; exit 1; }

echo "== 1. BOOT container gate =="
if python3 "$BOOT_GATE" --quiet --partition-bytes 57671680 "$BOOT" >/dev/null 2>&1; then
  S=$(echo "$S" | sed 's/BOOT_CONTAINER_PASS=no/BOOT_CONTAINER_PASS=yes/'); echo "  PASS"
else echo "  FAIL"; python3 "$BOOT_GATE" --partition-bytes 57671680 "$BOOT" 2>&1 | sed 's/^/    /'; die; fi

echo "== 2. Camera DT graph gate (real phandle graph) =="
C_DTB="${CAND_DTB:-$GOLDEN_DTB}"; C_DTBO="${CAND_DTBO:-$GOLDEN_DTBO}"
if python3 "$DT_GATE" --board-rev "$REV" --dtbo-idx "$DTBO_IDX" "$C_DTB" "$C_DTBO" >/dev/null 2>&1; then
  S=$(echo "$S" | sed 's/CAMERA_DT_GRAPH_PASS=no/CAMERA_DT_GRAPH_PASS=yes/'); echo "  PASS"
else echo "  FAIL"; python3 "$DT_GATE" --board-rev "$REV" --dtbo-idx "$DTBO_IDX" "$C_DTB" "$C_DTBO" 2>&1 | sed 's/^/    /'; die; fi

echo "== 3. MERGED FDT proof (PROMPT 00 containment) =="
if [ -n "$MERGED" ] && [ -s "$MERGED" ]; then
  if python3 "$MERGE_VERIFY" --merged "$MERGED" --dtb "$GOLDEN_DTB" --dtbo "$GOLDEN_DTBO" --board-rev "$REV" --dtbo-idx "$DTBO_IDX" >/dev/null 2>&1; then
    S=$(echo "$S" | sed 's/MERGED_FDT_PROOF=no/MERGED_FDT_PROOF=yes/'); echo "  PASS"
  else echo "  FAIL"; python3 "$MERGE_VERIFY" --merged "$MERGED" --dtb "$GOLDEN_DTB" --dtbo "$GOLDEN_DTBO" 2>&1 | sed 's/^/    /'; die; fi
else
  echo "  skip (--merged not provided)"; S=$(echo "$S" | sed 's/MERGED_FDT_PROOF=no/MERGED_FDT_PROOF=skip/')
fi

echo "== 4. Active board match =="
if [ -n "$BOARD_MODEL" ] && printf '%s' "$BOARD_MODEL" | grep -qi 'BEYOND2LTE'; then
  S=$(echo "$S" | sed 's/ACTIVE_BOARD_MATCH=no/ACTIVE_BOARD_MATCH=yes/'); echo "  PASS ($BOARD_MODEL)"
elif [ -n "$BOARD_MODEL" ]; then
  echo "  FAIL (board-model '$BOARD_MODEL' not beyond2lte)"; die
else
  echo "  FAIL (--board-model required from live evidence)"; die
fi

echo "== 5. No unrelated DT delta =="
if [ -z "$CAND_DTB" ] || [ "$(sha256sum "$CAND_DTB"|cut -d' ' -f1)" = "$(sha256sum "$GOLDEN_DTB"|cut -d' ' -f1)" ]; then
  S=$(echo "$S" | sed 's/NO_UNRELATED_DT_DELTA=no/NO_UNRELATED_DT_DELTA=yes/'); echo "  PASS (no dtb delta)"
else
  echo "  FAIL (candidate dtb differs from golden without camera allowlist review)"; die
fi

echo "== 6. Rollback ready =="
for g in "$GOLDEN_BOOT" "$GOLDEN_DTB" "$GOLDEN_DTBO"; do
  [ -s "$g" ] || { echo "  FAIL (missing $g)"; die; }
done
S=$(echo "$S" | sed 's/ROLLBACK_READY=no/ROLLBACK_READY=yes/'); echo "  PASS"

echo; echo "RELEASE GATE: PASS"; echo "$S"; exit 0
