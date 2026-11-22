#!/usr/bin/env bash
# test-camera-dt-gate.sh — fail-closed proof for the camera DT graph gate.
#
# Covers:
#   * golden no-op baselines (real live dtb/dtbo + merged FDT) MUST PASS
#   * every injected structural/graph defect MUST fail-closed (nonzero exit)
#   * board-revision selection: wrong-rev dtbo entry MUST fail
#   * golden SHA identity: self-match passes, cross-mismatch fails
#   * PROMPT 00 merge-containment proof (dt-merge-verify.py) holds
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
GATE="$ROOT/tools/s10plus/camera-dt-gate.py"
MERGE_VERIFY="$ROOT/tools/s10plus/dt-merge-verify.py"
FIX="$ROOT/tools/s10plus/tests/fixtures"
GOOD_DTB="$ROOT/pwn/recovery-artifacts/fixed/dtb-sda12.img"
GOOD_DTBO="$ROOT/pwn/recovery-artifacts/fixed/dtbo-sda13.img"
GOOD_MERGED="$ROOT/pwn/recovery-artifacts/current/merged-fdt/fdt-merged.img"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }

# run gate; want=pass|fail; extra args appended
expect() {
  local want="$1" label="$2"; shift 2
  local img="$1"; shift
  if [ ! -f "$img" ]; then
    printf '  skip %s (missing %s)\n' "$label" "$img"; return
  fi
  if python3 "$GATE" "$img" "$@" >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then ok "$label -> $want"
  else bad "$label -> $got (expected $want)"; python3 "$GATE" "$img" "$@" 2>&1 | sed 's/^/     /' | head -20; fi
}

# --- Golden baselines (real live artifacts) MUST PASS -----------------------
printf 'Golden baselines (MUST PASS):\n'
expect pass "known-good fixed dtb"      "$GOOD_DTB"
expect pass "known-good fixed dtbo idx9" "$GOOD_DTBO" --dtbo-idx 9
expect pass "active merged FDT (hermetic)" "$GOOD_MERGED" --merged

# --- Structural/magic defects MUST fail ------------------------------------
printf '\nStructural defects (MUST FAIL):\n'
expect fail "empty file"               "$FIX/empty.img"
expect fail "truncated dtb"            "$FIX/truncated-dtb.img"
expect fail "bad FDT/DTH magic"        "$FIX/bad-magic-dtb.img"
expect fail "wrong board model"        "$FIX/wrong-board-dtb.img"

# --- Real device-tree graph defects MUST fail ------------------------------
printf '\nGraph defects (MUST FAIL):\n'
expect fail "dangling remote-endpoint" "$FIX/broken-endpoint.dtb" --merged
expect fail "I2C reserved-owner theft" "$FIX/i2c-collision.dtb" --merged
expect fail "FIMC+CSIS co-binding"     "$FIX/fimc-csis-conflict.dtb" --merged
expect fail "invalid data-lanes"       "$FIX/bad-lanes.dtb" --merged

# --- Board revision selection MUST reject wrong rev -------------------------
printf '\nBoard revision selection (MUST FAIL on wrong rev):\n'
expect fail "wrong-rev dtbo (rev 4..15 vs 26)" "$FIX/wrong-rev-dtbo.img" --dtbo-idx 0
expect pass "correct-rev dtbo (rev 26..255)"  "$GOOD_DTBO" --dtbo-idx 9

# --- Golden SHA identity: self-match passes, cross-mismatch fails ----------
printf '\nGolden SHA identity checks:\n'
if python3 "$GATE" "$GOOD_DTB" --golden "$GOOD_DTB" >/dev/null 2>&1; then ok "golden self-match -> pass"; else bad "golden self-match -> fail"; fi
if python3 "$GATE" "$GOOD_DTB" --golden "$GOOD_DTBO" >/dev/null 2>&1; then bad "golden cross-mismatch -> pass (should fail)"; else ok "golden cross-mismatch -> fail"; fi

# --- PROMPT 00 merge-containment proof holds --------------------------------
printf '\nPROMPT 00 merge-containment proof:\n'
if [ -f "$GOOD_MERGED" ]; then
  if python3 "$MERGE_VERIFY" --merged "$GOOD_MERGED" --dtb "$GOOD_DTB" --dtbo "$GOOD_DTBO" --board-rev 26 --dtbo-idx 9 >/dev/null 2>&1; then
    ok "merge proof -> holds"
  else
    bad "merge proof -> failed"; python3 "$MERGE_VERIFY" --merged "$GOOD_MERGED" --dtb "$GOOD_DTB" --dtbo "$GOOD_DTBO" 2>&1 | sed 's/^/     /' | head -20
  fi
else
  printf '  skip merge proof (missing merged FDT)\n'
fi

printf '\nRESULT: %d pass, %d fail\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
