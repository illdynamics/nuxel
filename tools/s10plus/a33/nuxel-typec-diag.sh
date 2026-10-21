#!/usr/bin/env bash
# nuxel-typec-diag.sh — S10+ (beyond2lte) USB-C / DisplayPort Alt Mode probe.
#
# READ-ONLY. Enumerates the real Type-C class, DP alt-mode state, DRM connectors
# and driver/module presence; it NEVER writes, never modesets, never flips a mux,
# and never triggers a USB role change. A missing /sys/class/typec is recorded as
# evidence, not proof that the hardware lacks DP (vendor drivers may replace the
# generic Type-C class). Visible HDMI output is the owner's to confirm.
#
# Verdicts (honest):
#   DP_ALT_MODE_ACTIVE          DP altmode negotiated AND a DRM connector is connected
#   TYPEC_DP_NEGOTIATED         DP altmode present but no connected DRM connector
#   TYPEC_ENUMERATED_NO_DP      Type-C ports exist but no DP altmode is exposed
#   DRM_CONNECTOR_PRESENT       a DRM connector exists with no Type-C evidence
#   NO_TYPEC_NO_DRM             neither Type-C nor a DRM connector is present
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0
for a in "$@"; do case "$a" in --json) JSON=1 ;; esac; done
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
say() { printf '%s\n' "$*"; }

# ---- read-only enumeration ------------------------------------------------
typec_ports() {
  local d
  [ -d "$(abs /sys/class/typec)" ] || return 0
  for d in "$(abs /sys/class/typec)"/*; do
    [ -d "$d" ] && printf '%s\n' "${d#$ROOT}"
  done
}
typec_altmodes() {
  find "$(abs /sys/class/typec)" -maxdepth 3 -type d -name "*altmode*" 2>/dev/null | sed "s#^$ROOT##"
}
dp_altmodes() {
  find "$(abs /sys/class/typec)" -maxdepth 4 -type d \( -name "displayport" -o -name "typec_displayport" \) 2>/dev/null | sed "s#^$ROOT##"
}
drm_connectors() {
  local d s
  for d in "$(abs /sys/class/drm)"/*; do
    [ -d "$d" ] || continue
    s="$(cat "$d/status" 2>/dev/null | tr -d '\r\n')"
    printf '%s\t%s\n' "${d#$ROOT}" "${s:-unknown}"
  done
}
modules() {
  local m
  [ -r "$(abs /proc/modules)" ] || return 0
  for m in tcpm typec typec_displayport displayport drm drm_kms_helper exynos_drm; do
    grep -q "^$m " "$(abs /proc/modules)" 2>/dev/null && printf '%s\n' "$m"
  done
}
cat_file() { [ -r "$1" ] && cat "$1" 2>/dev/null | tr -d '\r\n' || printf ''; }

cmd_status() {
  local ports alts dps cons mods
  ports="$(typec_ports)"
  alts="$(typec_altmodes)"
  dps="$(dp_altmodes)"
  cons="$(drm_connectors)"
  mods="$(modules)"

  if [ "$JSON" = 1 ]; then
    python3 - "$ROOT" "$ports" "$dps" "$cons" "$mods" <<'PY'
import json, sys
root, ports, dps, cons, mods = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
ports = [p for p in ports.splitlines() if p]
dps = [p for p in dps.splitlines() if p]
conns = [c.split("\t")[0] for c in cons.splitlines() if c]
connected = [c.split("\t")[0] for c in cons.splitlines() if c and c.split("\t")[-1] == "connected"]
if dps and connected: verdict = "DP_ALT_MODE_ACTIVE"
elif dps: verdict = "TYPEC_DP_NEGOTIATED"
elif ports: verdict = "TYPEC_ENUMERATED_NO_DP"
elif conns: verdict = "DRM_CONNECTOR_PRESENT"
else: verdict = "NO_TYPEC_NO_DRM"
print(json.dumps({
  "device": "beyond2lte", "tool": "nuxel-typec-diag", "read_only": True,
  "typec_ports": ports, "dp_altmodes": dps,
  "drm_connectors": conns, "drm_connected": connected,
  "modules": mods.splitlines(), "verdict": verdict,
  "owner_proof": "docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md",
  "visible_output_verified": False}, separators=(",", ":")))
PY
    return 0
  fi

  say "device: beyond2lte — USB-C / DisplayPort Alt Mode probe (READ-ONLY)"
  say "typec ports    : ${ports:-none}"
  say "dp alt modes   : ${dps:-none}"
  say "drm connectors : $(printf '%s' "$cons" | tr '\n' ' ')"
  say "kernel modules : ${mods:-none}"
  say ""
  if [ -n "$dps" ] && printf '%s\n' "$cons" | grep -q 'connected$'; then
    say "verdict: DP_ALT_MODE_ACTIVE — DP negotiated and a DRM connector is connected"
  elif [ -n "$dps" ]; then
    say "verdict: TYPEC_DP_NEGOTIATED — DP altmode present, no connected DRM connector"
  elif [ -n "$ports" ]; then
    say "verdict: TYPEC_ENUMERATED_NO_DP — Type-C ports exist but no DP altmode is exposed"
  elif [ -n "$cons" ]; then
    say "verdict: DRM_CONNECTOR_PRESENT — DRM connector present, no Type-C evidence"
  else
    say "verdict: NO_TYPEC_NO_DRM — neither Type-C nor a DRM connector is present"
  fi
  say "visible HDMI output is NEEDS_OWNER_TEST (docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md)"
}
cmd_selftest() {
  local fixdir here n=0 rc=0 f exp got
  here="$(cd "$(dirname "$0")" && pwd)"
  fixdir="$here/tests/hw-subsystems/fixtures"
  for f in "$fixdir"/typec-*; do
    [ -d "$f" ] || continue
    n=$((n+1))
    exp="$(sed -n 's/^expect=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_ROOT="$f" bash "$0" status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["verdict"])' 2>/dev/null)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-28s verdict=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-28s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  selftest) cmd_selftest ;;
  help|-h|--help) sed -n '2,20p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
