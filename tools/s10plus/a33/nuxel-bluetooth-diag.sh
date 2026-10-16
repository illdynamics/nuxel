#!/usr/bin/env bash
# nuxel-bluetooth-diag.sh — S10+ (beyond2lte) Bluetooth bring-up diagnostic.
#
# WHAT THIS IS
#   A per-stage evidence report for the BCM4375 Bluetooth radio: adapter node,
#   rfkill state, driver/module binding, HCD firmware presence, bluetoothd
#   service — and the FIRST failing stage plus a verdict. Plus explicit owner
#   actions (`on`, `off`, bounded `scan`).
#
# WHAT THIS IS NOT
#   It never claims the radio works. A registered module is not proof of a
#   working radio and config alone is not a pairing: the terminal verdict stays
#   NEEDS_OWNER_TEST until a real peer pairs on the handset. Nothing is powered
#   at boot (AutoEnable=false in the BlueZ drop-in).
#
# Usage:
#   nuxel-bluetooth-diag.sh status [--json]
#   nuxel-bluetooth-diag.sh firmware
#   nuxel-bluetooth-diag.sh on | off
#   nuxel-bluetooth-diag.sh scan [secs]
#   nuxel-bluetooth-diag.sh report
#   nuxel-bluetooth-diag.sh selftest
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_BT_POLICY:-/etc/nuxel/bluetooth/bluetooth.json}"
LOG="${NUXEL_BT_LOG:-/var/log/nuxel/bluetooth-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; NUM=""
for a in "$@"; do case "$a" in --json) JSON=1 ;; [0-9]*) NUM="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/bluetooth/bluetooth.json"
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
pol() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    cur=cur.get(k) if isinstance(cur,dict) else None
if isinstance(cur,list): print(" ".join(str(x) for x in cur))
elif cur is not None: print(cur)
PY
}

# ---- stage collectors ------------------------------------------------------
stage_adapter() {
  local d
  for d in "$(abs /sys/class/bluetooth)"/*; do [ -e "$d" ] && { printf 'present:%s' "$(basename "$d")"; return; }; done
  printf 'absent'
}
stage_rfkill() {
  local d out=""
  for d in "$(abs /sys/class/rfkill)"/*; do
    [ -e "$d" ] || continue
    [ "$(cat "$d/type" 2>/dev/null | tr -d '\r\n')" = bluetooth ] || continue
    local soft hard; soft="$(cat "$d/soft" 2>/dev/null | tr -d '\r\n')"; hard="$(cat "$d/hard" 2>/dev/null | tr -d '\r\n')"
    out="$(basename "$d") soft=${soft:-?} hard=${hard:-?}"
    if [ "${soft:-0}" = 0 ] && [ "${hard:-0}" = 0 ]; then printf 'unblocked:%s' "$out"; else printf 'blocked:%s' "$out"; fi
    return
  done
  printf 'no-rfkill-node'
}
stage_module() {
  local m found=""
  [ -r "$(abs /proc/modules)" ] || { printf 'proc-modules-unreadable'; return; }
  for m in $(pol 'evidence_sources.driver_candidates'); do
    grep -q "^$m " "$(abs /proc/modules)" 2>/dev/null && found="$found $m"
  done
  [ -n "$found" ] && printf 'loaded:%s' "${found# }" || printf 'none-loaded'
}
stage_firmware() {
  local f dir base
  for dir in $(pol 'evidence_sources.hcd_dirs'); do
    for f in $(pol 'evidence_sources.hcd_candidates'); do
      for base in "$(abs "$dir")" "$(abs "/$f")"; do
        [ -f "$base" ] && { printf 'found:%s' "${base#$ROOT}"; return; }
        [ -f "$(abs "$dir/$f")" ] && { printf 'found:%s' "$dir/$f"; return; }
      done
    done
  done
  printf 'missing'
}
stage_service() {
  if [ -d "$(abs /sys/fs/cgroup/system.slice)" ] || [ -d "$(abs /run/systemd/system)" ] || [ -d "$(abs /etc/systemd/system)" ]; then
    if [ -e "$(abs /usr/lib/systemd/system/bluetooth.service)" ] || [ -e "$(abs /etc/systemd/system/bluetooth.service)" ] || [ -e "$(abs /usr/lib/systemd/system/dbus-org.bluez.service)" ]; then
      printf 'unit-present'; return
    fi
  fi
  if command -v bluetoothctl >/dev/null 2>&1 && [ "$ROOT" = "/" ]; then printf 'client-present'; return; fi
  printf 'unit-missing'
}
verdict() { # $1 adapter $2 rfkill $3 module $4 firmware
  case "$1" in absent)
      case "$2$3" in *unblocked*|*loaded*) printf 'PARTIAL' ;; *) printf 'BLOCKED_HARDWARE' ;; esac ;;
    *) case "$2" in blocked:*) printf 'RFKILL_BLOCKED' ;;
       *) case "$3" in none-loaded) case "$4" in found:*) printf 'PARTIAL' ;; *) printf 'BLOCKED_FIRMWARE' ;; esac ;;
          *) case "$4" in found:*) printf 'READY_FOR_PAIRING' ;; *) printf 'BLOCKED_FIRMWARE' ;; esac ;; esac ;;
       esac ;;
  esac
}
first_failing_stage() { # adapter rfkill module firmware
  case "$1" in absent) printf 'adapter' ;; *) case "$2" in blocked:*) printf 'rfkill' ;;
    *) case "$3" in none-loaded) printf 'module' ;; *) case "$4" in found:*) printf 'pairing' ;; *) printf 'firmware' ;; esac ;; esac ;; esac ;; esac
}
cmd_status() {
  local a r m f s v ff
  a="$(stage_adapter)"; r="$(stage_rfkill)"; m="$(stage_module)"; f="$(stage_firmware)"; s="$(stage_service)"
  v="$(verdict "$a" "$r" "$m" "$f")"; ff="$(first_failing_stage "$a" "$r" "$m" "$f")"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-bluetooth-diag","stages":{"adapter":"%s","rfkill":"%s","module":"%s","firmware":"%s","service":"%s"},"first_failing_stage":"%s","state":"%s","pairing_verified":false,"auto_enable_at_boot":false,"owner_test":"docs/beta-finalization/manual-proof/11-bluetooth.md"}\n' \
      "$(jesc "$a")" "$(jesc "$r")" "$(jesc "$m")" "$(jesc "$f")" "$(jesc "$s")" "$ff" "$v"
    return 0
  fi
  say "device : beyond2lte   radio : Broadcom BCM4375 (BT 5.0)"
  say ""
  say "stages:"
  say "  adapter  : $a"
  say "  rfkill   : $r"
  say "  module   : $m"
  say "  firmware : $f   (candidates: $(pol 'evidence_sources.hcd_candidates' | cut -d' ' -f1-3) ...)"
  say "  service  : $s"
  say ""
  say "first failing stage : $ff"
  say "verdict             : $v"
  case "$v" in
    READY_FOR_PAIRING) say "  an adapter is enumerated and unblocked. Pairing is still NEEDS_OWNER_TEST: a real" 
                       say "  peer must pair and the DATA path (audio/file) must be exercised." ;;
    RFKILL_BLOCKED)    say "  the adapter exists but rfkill blocks it. Re-enable it explicitly:" 
                       say "  nuxel-bluetooth-diag.sh on   (never at boot; AutoEnable=false)" ;;
    BLOCKED_FIRMWARE)  say "  module/stack present but no HCD blob found in the candidate dirs." 
                       say "  Deploy the HCD into /lib/firmware/brcm (repository-only step); never a flash." ;;
    BLOCKED_HARDWARE)  say "  no adapter, no bluetooth rfkill entry and no driver: the radio has not" 
                       say "  come up at all on this kernel. Kernel/driver-side work (offline)." ;;
    PARTIAL)           say "  some stages present, some missing — read the per-stage lines above." ;;
  esac
  say ""
  say "nothing powers the adapter at boot (BlueZ drop-in AutoEnable=false)"
}
cmd_firmware() {
  local dir f base
  say "HCD candidate inventory for the BCM4375 ($(pol 'device.hcd_filename')):"
  for dir in $(pol 'evidence_sources.hcd_dirs'); do
    say "  $dir:"
    for f in $(pol 'evidence_sources.hcd_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && say "    FOUND  $f" || say "    -      $f"
    done
  done
}
cmd_on() {
  local r; r="$(stage_rfkill)"
  say "explicit adapter power (owner action; nothing does this at boot)"
  if [ "$ROOT" = "/" ] && command -v bluetoothctl >/dev/null 2>&1; then
    bluetoothctl power on 2>&1 | sed 's/^/  /' || true
    bluetoothctl list 2>&1 | sed 's/^/  /' || true
  else
    say "  (offline/faked root: would run 'bluetoothctl power on' and 'rfkill unblock bluetooth')"
    say "  rfkill before: $r"
  fi
  say "verify with: $0 status"
}
cmd_off() {
  say "explicit adapter power-off (leaves the phone as found)"
  if [ "$ROOT" = "/" ] && command -v bluetoothctl >/dev/null 2>&1; then
    bluetoothctl power off 2>&1 | sed 's/^/  /' || true
  else
    say "  (offline/faked root: would run 'bluetoothctl power off')"
  fi
}
cmd_scan() {
  local secs="${1:-10}" max; max="$(pol 'diagnostics.scan_seconds_max')"; max="${max:-60}"
  [ "$secs" -gt "$max" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${max}s"; secs="$max"; }
  say "bounded scan for ${secs}s (owner action; results are the peer's evidence, not a claim)"
  if [ "$ROOT" = "/" ] && command -v bluetoothctl >/dev/null 2>&1; then
    timeout "$secs" bluetoothctl --timeout "$secs" scan on 2>&1 | sed 's/^/  /' || true
    bluetoothctl devices 2>&1 | sed 's/^/  /' || true
  else
    say "  (offline/faked root: would run 'bluetoothctl scan on' for ${secs}s)"
  fi
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/bluetooth-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-30s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-30s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  firmware) cmd_firmware ;;
  on) cmd_on ;;
  off) cmd_off ;;
  scan) cmd_scan "${NUM:-10}" ;;
  report) { say "=== nuxel-bluetooth report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; cmd_firmware; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || true; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,24p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
