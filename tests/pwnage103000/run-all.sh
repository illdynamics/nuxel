#!/bin/sh
# PWNAGE-103000 gate: every mission test, then the touched baseline suites.
set -u
R="$(cd "$(dirname "$0")/../.." && pwd)"
fail=0
for t in test_edge_lighting_js.py test_edge_panel_gesture.py test_edge_lighting_provider.py test_edge_fx_fixes.py \
         test_pwnage103000_contract.py test_torch_safety.py \
         test_live_v085_notifications_audio.py; do
  echo "=== $t"
  python3 "$R/tests/pwnage103000/$t" || fail=1
done
for t in tests/pwnage44000/test_flashlight_provider.py tests/pwnage45000/test_pwnage45000.py \
         tests/pwnage50000/test_drawer_gesture_guard.py tests/pwnage85000/test_motion_contract.py \
         tests/pwnage93000/test_pwnage93000.py; do
  echo "=== baseline $t"
  python3 "$R/$t" || fail=1
done
[ "$fail" = 0 ] && echo "PWNAGE-103000 GATE: PASS" || echo "PWNAGE-103000 GATE: FAIL"
exit "$fail"
