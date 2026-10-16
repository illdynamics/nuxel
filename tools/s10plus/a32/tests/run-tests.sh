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
echo "-- button manager / host sources parse"
for f in "$HERE/../nuxel-button-manager.c" "$HERE/../nuxel-pwa-host.c"; do
  [ -f "$f" ] && echo "PASS present $(basename "$f")"
done
echo "== $FAIL failing suite(s) =="
exit "$FAIL"
