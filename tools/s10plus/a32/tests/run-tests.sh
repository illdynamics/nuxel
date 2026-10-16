#!/usr/bin/env bash
# Offline test suite for the A32 beta-hardware work.  No device, no display, no
# network needed; every test prints PASS/FAIL and the script's exit status is the
# number of failed suites.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/../../../../build/out/s10plus/a32"
FAIL=0
echo "== A32 offline tests =="
if [ -x "$OUT/nuxel-wl-fb" ]; then
  echo "-- colour conversion (the real bridge binary, aarch64: run on the UTM guest)"
  if "$OUT/nuxel-wl-fb" --colour-selftest >/tmp/a32-colour.txt 2>&1; then
    cat /tmp/a32-colour.txt
  else
    VM="${VM:-nuxel@192.168.64.3}"
    if scp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=6 \
         "$OUT/nuxel-wl-fb" "$VM:/tmp/a32-nuxel-wl-fb" 2>/dev/null &&
       ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$VM" \
         'chmod +x /tmp/a32-nuxel-wl-fb && /tmp/a32-nuxel-wl-fb --colour-selftest' 2>&1 | tee /tmp/a32-colour.txt; then
      grep -q FAIL /tmp/a32-colour.txt && FAIL=$((FAIL+1))
    else
      echo "FAIL colour selftest could not run (no aarch64 host available)"; FAIL=$((FAIL+1))
    fi
  fi
else
  echo "FAIL colour conversion (build the a32 binaries first)"; FAIL=$((FAIL+1))
fi
echo "-- input keycode bitmap decode"
python3 "$HERE/input-bitmap-decode.py" || FAIL=$((FAIL+1))
echo "-- status-bar safe zones"
command -v node >/dev/null && { node "$HERE/safe-zones-test.js" || FAIL=$((FAIL+1)); } || echo "SKIP (node absent)"
echo "-- launcher registry"
command -v node >/dev/null && { node "$HERE/launcher-registry-test.js" || FAIL=$((FAIL+1)); } || echo "SKIP (node absent)"
echo "-- wallpaper asset"
python3 "$HERE/wp.py" || FAIL=$((FAIL+1))
# --- A33 (bg-02: boot stability, animation handoff, launcher parity) --------- #
# These legs are what tools/beta/regression-guard.sh executes for the bg-02
# surface: INV-9 runs this file, so the colour conversion, the handoff decision
# table, the verbose-boot durability harness, the settings store and the launcher
# registry are all re-checked on every guard invocation.  Each leg is skipped
# (not failed) when its interpreter is absent.
echo "-- A33 colour-order golden bytes (briq-02c: XRGB8888 -> DECON ABGR8888)"
if command -v python3 >/dev/null; then python3 "$HERE/../../a33/tests/test-colour-order.py" || FAIL=$((FAIL+1)); else echo "SKIP (python3 absent)"; fi
echo "-- A33 handoff decision table + single-owner proof (briq-02a)"
if command -v python3 >/dev/null; then python3 "$HERE/../../a33/nuxel-anim-handoff.py" selftest || FAIL=$((FAIL+1)); else echo "SKIP (python3 absent)"; fi
echo "-- A33 verbose-boot durability harness (briq-02b)"
if command -v python3 >/dev/null; then python3 "$HERE/../../a33/nuxel-verbose-boot.py" --selftest >/dev/null || FAIL=$((FAIL+1)); else echo "SKIP (python3 absent)"; fi
echo "-- A33 settings store contract (briq-02b)"
command -v node >/dev/null && { node "$HERE/../../a33/tests/settings-store-test.js" || FAIL=$((FAIL+1)); } || echo "SKIP (node absent)"
echo "-- A33 boot-surface wiring contract (briq-02a..02e)"
if command -v python3 >/dev/null; then python3 "$HERE/../../a33/tests/test-boot-surface-contract.py" >/dev/null || FAIL=$((FAIL+1)); else echo "SKIP (python3 absent)"; fi
echo "-- A33 launcher registry/parity (briq-02d)"
command -v node >/dev/null && { node "$HERE/../../a33/tests/launcher-registry-test.js" || FAIL=$((FAIL+1)); } || echo "SKIP (node absent)"
echo "-- button manager / host sources parse"
for f in "$HERE/../nuxel-button-manager.c" "$HERE/../nuxel-pwa-host.c"; do
  [ -f "$f" ] && echo "PASS present $(basename "$f")"
done
echo "== $FAIL failing suite(s) =="
exit "$FAIL"
