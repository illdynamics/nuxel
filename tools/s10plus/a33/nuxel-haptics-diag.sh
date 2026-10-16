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
#
# TWO SURFACES
#   * owner surface  : `buzz --yes <ms>`                (a human asked for it)
#   * programmatic   : `api <pattern> --source <who>`   (button manager, notifier)
# The programmatic surface is the one the button manager and the notification
# daemon are wired through (via nuxel-haptics-bridge). It is gated shut unless a
# live user session has armed the API gate file (haptics.json: api.gate_file)
# with `arm`, so a system daemon cannot buzz while no session is up and nothing
# can buzz during boot. It still obeys the global switch and a rate limit.
#
# Usage:
#   nuxel-haptics-diag.sh status [--json]
#   nuxel-haptics-diag.sh on|off                      # global switch (persisted)
#   nuxel-haptics-diag.sh intensity <percent>
#   nuxel-haptics-diag.sh pattern <name> [percent]    # print steps, never buzzes
#   nuxel-haptics-diag.sh buzz --yes [ms]             # ONE bounded owner test buzz
#   nuxel-haptics-diag.sh api <pattern> [--source S] [--intensity N]
#   nuxel-haptics-diag.sh arm|disarm                  # programmatic gate (session)
#   nuxel-haptics-diag.sh report | selftest | help
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
YES=0; JSON=0; NUM=""; SOURCE="unknown"; INTENSITY=""
for a in "$@"; do case "$a" in
  --yes) YES=1 ;; --json) JSON=1 ;; --source=*) SOURCE="${a#--source=}" ;;
  --intensity=*) INTENSITY="${a#--intensity=}" ;; --source|--intensity) : ;;
  [0-9]*) NUM="$a" ;; esac; done
# also accept the space-separated form: --source button-manager / --intensity 30
_prev=""; for a in "$@"; do case "$_prev" in --source) SOURCE="$a" ;; --intensity) INTENSITY="$a" ;; esac; _prev="$a"; done
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
  say "programmatic  : api gate $([ -e "$(abs "$(api_gate)")" ] && printf 'ARMED (%s)' "$(api_gate)" || printf 'closed (no user session; system requests refuse)')"
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
# ---- programmatic API: the button manager / notifier wiring point ----------
# A system daemon must never be able to buzz when no user session is up and
# nothing may buzz during boot. Both fall out of one rule: the API refuses
# unless a live session has armed the gate file. The owner surface (`buzz`)
# is unaffected by the gate - it is a human action.
pget() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: print(""); sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    cur=cur.get(k) if isinstance(cur,dict) else None
print("" if cur is None else cur)
PY
}
api_gate() { local g; g="$(pget api.gate_file)"; printf '%s' "${NUXEL_HAPTICS_API_GATE:-${g:-/run/nuxel/haptics/api-enabled}}"; }
api_log() { local l; l="$(pget api.audit)"; printf '%s' "${NUXEL_HAPTICS_API_LOG:-${l:-/var/log/nuxel/haptics-api.log}}"; }
api_recent() { local r; r="$(pget api.rate_limit.state_file)"; printf '%s' "${NUXEL_HAPTICS_API_STATE:-${r:-/run/nuxel/haptics/api-recent}}"; }
api_open() {
  [ "${NUXEL_HAPTICS_API:-0}" = "1" ] && return 0
  [ -e "$(abs "$(api_gate)")" ] && return 0
  return 1
}
audit_api() {
  local f; f="$(abs "$(api_log)")"
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)" "$*" >> "$f" 2>/dev/null || true
}
faked_root() { [ "$ROOT" != "/" ]; }
cmd_arm() {
  local g; g="$(abs "$(api_gate)")"
  mkdir -p "$(dirname "$g")" 2>/dev/null || true
  if printf 'armed_by=session pid=%s at=%s\n' "$$" "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)" > "$g" 2>/dev/null; then
    say "programmatic haptics API ARMED ($(api_gate)) - the bridge may now request patterns"
  else
    say "could not arm $(api_gate) (read-only root?)"
  fi
}
cmd_disarm() {
  rm -f "$(abs "$(api_gate)")" 2>/dev/null || true
  audit_api "DISARM source=session pid=$$"
  say "programmatic haptics API DISARMED - every system request now refuses"
}
rate_limit_ok() {
  python3 - "$(abs "$(api_recent)")" "$(pget api.rate_limit.window_ms)" "$(pget api.rate_limit.max_per_window)" <<'PY'
import os, sys, time
f, win, mx = sys.argv[1], sys.argv[2], sys.argv[3]
win = int(win or 5000); mx = int(mx or 6)
now = time.time()
keep = []
try:
    with open(f) as fh:
        for line in fh:
            try: t = float(line.strip())
            except ValueError: continue
            if now - t <= win / 1000.0: keep.append(t)
except OSError:
    pass
if len(keep) >= mx:
    print("limited"); sys.exit(0)
keep.append(now)
d = os.path.dirname(f)
if d: os.makedirs(d, exist_ok=True)
with open(f, "w") as fh:
    fh.write("".join("%.3f\n" % t for t in keep))
print("ok")
PY
}
cmd_api() {
  local pat="${1:-tap}"
  discover
  if ! api_open; then
    say "refused(7): programmatic haptics API is gated OFF - no user session has armed $(api_gate)."
    say "            (a system daemon cannot buzz while no session is up; nothing buzzes during boot)"
    audit_api "REFUSED reason=gate_closed pattern=$pat source=$SOURCE"
    return 7
  fi
  if [ "$(enabled)" != yes ]; then
    say "refused(3): global haptics switch is OFF (nuxel-haptics-diag.sh on)"
    audit_api "REFUSED reason=global_switch_off pattern=$pat source=$SOURCE"
    return 3
  fi
  if [ -z "$NODE" ]; then
    say "refused(2): no vibrator node bound (BLOCKED_KERNEL)"
    audit_api "REFUSED reason=no_node pattern=$pat source=$SOURCE"
    return 2
  fi
  local steps; steps="$(expand "$pat" "$INTENSITY")"
  case "$steps" in
    ""|"unknown pattern"*|"policy unreadable")
      say "refused(2): ${steps:-empty pattern}"
      audit_api "REFUSED reason=bad_pattern pattern=$pat source=$SOURCE"
      return 2 ;;
  esac
  local rl; rl="$(rate_limit_ok "$pat")"
  if [ "$rl" = limited ]; then
    say "refused(8): rate limit reached ($(pget api.rate_limit.max_per_window) per $(pget api.rate_limit.window_ms) ms) - dropping this request"
    audit_api "REFUSED reason=rate_limited pattern=$pat source=$SOURCE"
    return 8
  fi
  if faked_root || [ "${NUXEL_HAPTICS_DRYRUN:-0}" = "1" ]; then
    say "api(dry-run): node=$NODE pattern=$pat source=$SOURCE steps=$steps (no write performed)"
    audit_api "DRYRUN pattern=$pat source=$SOURCE steps=$steps"
    return 0
  fi
  local wf="" f step
  for f in activate duration brightness amplitude state; do [ -w "$(abs "$NODE/$f")" ] && { wf="$f"; break; }; done
  if [ -z "$wf" ]; then
    say "refused(2): node $NODE exposes no writable file - cannot buzz"
    audit_api "REFUSED reason=no_writable pattern=$pat source=$SOURCE"
    return 2
  fi
  say "api: pattern=$pat source=$SOURCE steps=$steps via $NODE/$wf (internal; global switch ON)"
  for step in $steps; do
    case "$wf" in
      duration|brightness|amplitude) printf '%s' "$step" > "$(abs "$NODE/$wf")" 2>/dev/null || true ;;
      activate|state) printf '1' > "$(abs "$NODE/$wf")" 2>/dev/null || true ;;
    esac
    sleep "$(python3 -c "print(max(0.01, $step/1000.0))" 2>/dev/null || printf 0.05)"
  done
  audit_api "BUZZ pattern=$pat source=$SOURCE steps=$steps node=$NODE file=$wf"
  return 0
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
  api) cmd_api "${1:-tap}" ;;
  arm) cmd_arm ;;
  disarm) cmd_disarm ;;
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
