#!/usr/bin/env bash
# test-camera-dt-gate.sh — negative-fixture fail-closed proof + golden no-op.
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
GATE="$ROOT/tools/s10plus/camera-dt-gate.py"
FIX="$ROOT/tools/s10plus/tests/fixtures"
GOOD_DTB="$ROOT/pwn/recovery-artifacts/fixed/dtb-sda12.img"
GOOD_DTBO="$ROOT/pwn/recovery-artifacts/fixed/dtbo-sda13.img"

PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }

expect() { # want:pass|fail, label, img...
  local want="$1" label="$2"; shift 2
  local img="$1"
  if [ ! -f "$img" ]; then
    printf '  skip %s (missing %s)\n' "$label" "$img"; return
  fi
  if python3 "$GATE" "$img" >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then ok "$label -> $want"
  else bad "$label -> $got (expected $want)"; python3 "$GATE" "$img" 2>&1 | sed 's/^/     /'; fi
}

# Golden no-op baseline MUST pass.
printf 'Golden baselines:\n'
expect pass "known-good fixed dtb" "$GOOD_DTB"
expect pass "known-good fixed dtbo" "$GOOD_DTBO"

printf '\nNegative fixtures (all MUST fail-closed):\n'
expect fail "empty file"            "$FIX/empty.img"
expect fail "truncated dtb"         "$FIX/truncated-dtb.img"
expect fail "bad FDT magic"         "$FIX/bad-magic-dtb.img"
expect fail "wrong board model"     "$FIX/wrong-board-dtb.img"

# sha-mismatch via --golden: golden=same file should pass, golden=other should fail
printf '\nGolden sha identity checks:\n'
if python3 "$GATE" "$GOOD_DTB" --golden "$GOOD_DTB" >/dev/null 2>&1; then ok "golden self-match -> pass"; else bad "golden self-match -> fail"; fi
if python3 "$GATE" "$GOOD_DTB" --golden "$GOOD_DTBO" >/dev/null 2>&1; then bad "golden cross-mismatch -> pass (should fail)"; else ok "golden cross-mismatch -> fail"; fi

printf '\nRESULT: %d pass, %d fail\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
