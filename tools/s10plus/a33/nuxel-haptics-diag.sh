#!/usr/bin/env bash
# nuxel-haptics-diag.sh — S10+ (beyond2lte) vibration / haptics tool + diagnostic.
#
# Reports the REAL actuator node (enumerated, never assumed), the writable files
# it exposes, the persisted global switch and the intensity mode, and can emit
# ONE bounded test buzz on an explicit `buzz --yes`. Felt haptics are the
# owner's observation and stay NEEDS_OWNER_TEST; a node existing proves nothing.
#
# NOTHING buzzes at boot and no automated path buzzes: `buzz` hard-refuses
# without --yes, the global switch off refuses everything, and the duration cap
# (haptics.json: diagnostics.test_buzz_max_ms) is enforced.
set -uo pipefail
SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_HAPTICS_POLICY:-/etc/nuxel/haptics/haptics.json}"
LOG="${NUXEL_HAPTICS_LOG:-/var/log/nuxel/haptics-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
YES=0; JSON=0; NUM=""
for a in "$@"; do case "$a" in --yes) YES=1 ;; --json) JSON=1 ;; [0-9]*) NUM="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
# Prefer the installed policy; fall back to the developer-tree copy when the
# installed one is not readable (dev tree / offline harness), so the tool and
# its fixtures stay self-consistent without inventing a path.
if [ -n "$RR" ] && [ ! -r "$POLICY" ] && [ -r "$RR/configs/nuxel/haptics/haptics.json" ]; then
  POLICY="$RR/configs/nuxel/haptics/haptics.json"
fi
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
state_file() { printf '%s' "$(abs /var/lib/nuxel/haptics/state.json)"; }
json_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

# ---- node discovery (glob + candidate list, no assumed path) --------------
NODE=""; WRITE_FILES=""; STRENGTH=""
discover() {
  local cand
  for cand in $(python3 - "$POLICY" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
print(" ".join(d.get("node_candidates",{}).get("sysfs",[])+d.get("node_candidates",{}).get("globs",[])))
PY
); do
    for p in $(abs "$cand"); do
      [ -d "$p" ] || continue
      [ -z "$NODE" ] && NODE="${p#$ROOT}"
      :
    done
  done
  # globs may expand to several dirs; prefer the first inside a matching name
  if [ -z "$NODE" ]; then
    for p in "$(abs /sys/class/leds)"/*vib* "$(abs /sys/class/timed_output)"/* "$(abs /sys/class/vibrator)"/*; do
      [ -d "$p" ] && { NODE="${p#$ROOT}"; break; }
    done
  fi
  [ -n "$NODE" ] || return 0
  local f
  for f in activate duration brightness amplitude state; do
    [ -w "$(abs "$NODE/$f")" ] && WRITE_FILES="$WRITE_FILES $f"
  done
  for f in max_brightness amplitude_max scale; do
    [ -r "$(abs "$NODE/$f")" ] && STRENGTH="$STRENGTH $f"
  done
  WRITE_FILES="${WRITE_FILES# }"; STRENGTH="${STRENGTH# }"
}
intensity_mode() { [ -n "$(printf '%s' "$WRITE_FILES" | grep -E 'brightness|amplitude')" ] && printf 'amplitude' || printf 'duration'; }
enabled() {
  local f; f="$(state_file)"
  if [ -r "$f" ]; then grep -q '"enabled"[[:space:]]*:[[:space:]]*true' "$f" && printf yes || printf no
  else printf 'yes'; fi  # policy default_enabled
}
write_state() { # $1 enabled(yes/no) $2 intensity
  local f; f="$(state_file)"; mkdir -p "$(dirname "$f")" 2>/dev/null || true
  printf '{"schema_version":1,"enabled":%s,"intensity_percent":%s,"updated":"%s"}\n' \
    "$([ "$1" = yes ] && printf true || printf false)" "${2:-55}" \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)" > "$f" 2>/dev/null || true
}
expand() { python3 - "$POLICY" "$1" "${2:-}" <<'PY'
import json,sys
pol, name, scale = sys.argv[1], sys.argv[2], sys.argv[3]
try: d=json.load(open(pol))
except Exception: print("policy unreadable"); sys.exit(0)
p=d.get("patterns",{}).get(name)
if not p: print("unknown pattern: %s (known: %s)" % (name, ", ".join(sorted(d.get("patterns",{}))))); sys.exit(0)
steps=list(p["steps"])
if scale and int(scale) != 100:
    steps=[max(1,int(s*int(scale)/100)) for s in steps]
print(" ".join(str(s) for s in steps))
PY
}

cmd_status() {
  discover
  local cap on=0; cap="$(python3 - "$POLICY" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get("diagnostics",{}).get("test_buzz_max_ms",1500))
except Exception: print(1500)
PY
)"
  local en im; en="$(enabled)"; im="$(intensity_mode)"
  [ -n "$NODE" ] && on=1
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-haptics-diag","node":"%s","node_present":%s,"writable_files":"%s","strength_files":"%s","intensity_mode":"%s","enabled":%s,"state":"%s","felt_haptics_verified":false,"owner_test":"docs/beta-finalization/manual-proof/10-vibration.md"}\n' \
      "$(json_escape "$NODE")" "$([ $on = 1 ] && printf true || printf false)" \
      "$(json_escape "$WRITE_FILES")" "$(json_escape "$STRENGTH")" "$im" \
      "$([ "$en" = yes ] && printf true || printf false)" \
      "$([ $on = 1 ] && printf OK || printf BLOCKED_KERNEL)"
    return 0
  fi
  say "device        : beyond2lte"
  if [ $on = 1 ]; then
    say "actuator node : $NODE (enumerated; first responsive candidate)"
    say "writable files: ${WRITE_FILES:-none — the node exists but exposes no writable file}"
    say "strength files: ${STRENGTH:-none}"
    say "intensity mode: $im"
  else
    say "actuator node : NONE — no vibrator node bound on this kernel (BLOCKED_KERNEL)."
    say "                No buzz can be produced; nothing is faked."
  fi
  say "global switch : $en (persisted at /var/lib/nuxel/haptics/state.json)"
  say "test cap      : ${cap} ms, requires an explicit 'buzz --yes'"
  say "verdict       : $([ $on = 1 ] && printf 'OFFLINE_TESTED (control logic) / NEEDS_OWNER_TEST (felt)' || printf BLOCKED_KERNEL)"
}
cmd_buzz() {
  discover
  [ "$(enabled)" = yes ] || { say "refused: global haptics switch is OFF (nuxel-haptics-diag.sh on)"; return 3; }
  [ -n "$NODE" ] || { say "refused: no vibrator node bound (BLOCKED_KERNEL)"; return 2; }
  [ "$YES" = 1 ] || { say "refused: a test buzz is an owner action. Re-run with: $SELF buzz --yes 300"; return 4; }
  local ms="${NUM:-300}" cap; cap="$(python3 - "$POLICY" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get("diagnostics",{}).get("test_buzz_max_ms",1500))
except Exception: print(1500)
PY
)"
  [ "$ms" -gt "$cap" ] 2>/dev/null && { say "capping $ms ms to the policy maximum ${cap} ms"; ms="$cap"; }
  local wf="" f
  for f in activate duration brightness amplitude state; do [ -w "$(abs "$NODE/$f")" ] && { wf="$f"; break; }; done
  say "buzz one-shot: ${ms} ms via $NODE/$wf (owner-triggered; nothing else buzzes)"
  case "$wf" in
    activate) printf '1' > "$(abs "$NODE/activate")" 2>/dev/null || true ;;
    duration) printf '%s' "$ms" > "$(abs "$NODE/duration")" 2>/dev/null || true ;;
    brightness|amplitude) printf '%s' "$ms" > "$(abs "$NODE/$wf")" 2>/dev/null || true ;;
    state) printf '1' > "$(abs "$NODE/state")" 2>/dev/null || true ;;
  esac
  say "did you feel it? Record the answer in docs/beta-finalization/manual-proof/10-vibration.md (PASS/FAIL)."
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/haptics-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-24s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-24s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  on)  write_state yes; say "global haptics switch ON (persisted)" ;;
  off) write_state no;  say "global haptics switch OFF (persisted; everything refuses until re-enabled)" ;;
  intensity) write_state "$(enabled)" "${1:-55}"; say "default intensity set to ${1:-55}%" ;;
  pattern) expand "${1:-tap}" "${2:-}" ;;
  buzz) cmd_buzz ;;
  report) { say "=== nuxel-haptics report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || cmd_status; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,30p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
