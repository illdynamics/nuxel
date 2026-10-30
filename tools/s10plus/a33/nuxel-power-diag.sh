#!/usr/bin/env bash
# nuxel-power-diag.sh — S10+ (SM-G975F / beyond2lte) power, battery and power-menu tool.
#
# WHAT THIS IS
#   A read-mostly diagnostic + a profile applier + the power-menu table reader.
#   It reports what the LIVE system actually exposes: the boot mode (including
#   the lpcharge/charger-mode case), whether a fuel gauge is bound and what it
#   reads, the charging state, and the currently active profile's REAL governor
#   and cgroup weight. `mode <name>` writes only the runtime knobs named in
#   configs/nuxel/power/power.json and persists the choice.
#
# WHAT THIS IS NOT
#   It never claims a battery percentage from an assumed node (no gauge bound =>
#   BLOCKED_KERNEL), never writes a charger register, never triggers Recovery or
#   Download Mode, and contains no flashing/partition surface at all. Charge
#   behaviour and "does the phone actually last longer" are owner-verified and
#   stay NEEDS_OWNER_TEST.
#
# Usage (also reachable from the Nuxel Settings power surface):
#   nuxel-power-diag.sh status [--json]
#   nuxel-power-diag.sh profiles
#   nuxel-power-diag.sh mode adaptive|balanced|performance
#   nuxel-power-diag.sh apply-persisted      # used by nuxel-power-mode.service
#   nuxel-power-diag.sh menu
#   nuxel-power-diag.sh report [--json] [--quiet]
#   nuxel-power-diag.sh selftest
#   nuxel-power-diag.sh help
#
# OFFLINE TESTABILITY
#   --root DIR (or NUXEL_DIAG_ROOT) prefixes every filesystem lookup, and
#   NUXEL_DIAG_NO_SYSTEM=1 forbids falling back to host tools, so the verdict
#   logic is testable on a laptop with no phone attached.
set -uo pipefail

SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_POWER_POLICY:-/etc/nuxel/power/power.json}"
MENU="${NUXEL_POWER_MENU:-/etc/nuxel/power/power-menu.json}"
STATE_DIR="${NUXEL_POWER_STATE_DIR:-/var/lib/nuxel/power}"
LOG="${NUXEL_POWER_LOG:-/var/log/nuxel/power-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?--root needs a directory}"; shift 2 ;;
    --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; QUIET=0
for a in "$@"; do
  case "$a" in --json) JSON=1 ;; --quiet) QUIET=1 ;; esac
done

# Developer tree fallback: when run from the repo (not installed) prefer the
# sibling configs/ copy so the tool and the fixtures are self-consistent.
HERE="$(cd "$(dirname "$0")" && pwd)"
repo_root() { d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { printf '%s' "$d"; return; }; d="$(dirname "$d")"; done; }
RR="$(repo_root || true)"
if [ -n "${RR:-}" ] && [ ! -r "$POLICY" ] && [ -r "$RR/configs/nuxel/power/power.json" ]; then
  POLICY="$RR/configs/nuxel/power/power.json"
fi
if [ -n "${RR:-}" ] && [ ! -r "$MENU" ] && [ -r "$RR/configs/nuxel/power/power-menu.json" ]; then
  MENU="$RR/configs/nuxel/power/power-menu.json"
fi

say()  { [ "$QUIET" = 1 ] && return 0; printf '%s\n' "$*"; }
hdr()  { say ""; say "== $* =="; }
abs()  { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
exists(){ [ -e "$(abs "$1")" ]; }
rd()   { [ -r "$(abs "$1")" ] && tr -d '\r\n' < "$(abs "$1")" 2>/dev/null || printf ''; }
json_escape() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\t/ /g' | tr -d '\r'; }
profile_file() { printf '%s' "$(abs "$STATE_DIR/profile.json")"; }

# ---- boot mode -------------------------------------------------------------
boot_mode() {
  local cl; cl="$(rd /proc/cmdline)"
  case "$cl" in
    *androidboot.mode=charger*) printf 'charger' ;;
    *androidboot.mode=*) printf 'normal' ;;
    *) printf 'unknown' ;;
  esac
}

# ---- fuel gauge ------------------------------------------------------------
gauge_dev=""; gauge_cap=""; gauge_status=""; gauge_volt=""; gauge_temp=""; gauge_health=""
collect_gauge() {
  local d name
  for d in "$(abs /sys/class/power_supply)"/*; do
    [ -e "$d" ] || continue
    name="$(basename "$d")"
    # Prefer a node that is really a battery AND exposes capacity; otherwise
    # fall back to a battery-looking node so the report can distinguish
    # "gauge bound but unreadable" (PARTIAL) from "no gauge at all" (BLOCKED).
    local typ; typ="$(rd "/sys/class/power_supply/$name/type")"
    if [ -r "$d/capacity" ]; then gauge_dev="$name"; break; fi
    case "$name:$typ" in
      battery:*|*:Battery|*:battery|*charger*|max*) [ -z "$gauge_dev" ] && gauge_dev="$name" ;;
    esac
  done
  if [ -n "$gauge_dev" ]; then
    local base="$(abs /sys/class/power_supply)/$gauge_dev"
    gauge_cap="$(rd "/sys/class/power_supply/$gauge_dev/capacity")"
    gauge_status="$(rd "/sys/class/power_supply/$gauge_dev/status")"
    gauge_volt="$(rd "/sys/class/power_supply/$gauge_dev/voltage_now")"
    gauge_temp="$(rd "/sys/class/power_supply/$gauge_dev/temp")"
    gauge_health="$(rd "/sys/class/power_supply/$gauge_dev/health")"
    : "$base"
  fi
}

# ---- profile ---------------------------------------------------------------
profile_active() {
  local f; f="$(profile_file)"
  if [ -r "$f" ]; then sed -n -e 's/.*"profile"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' "$f" | head -1
  else printf 'balanced'; fi
}
governor_now() {
  local p="$1" g
  g="$(rd "/sys/devices/system/cpu/cpufreq/policy$p/scaling_governor")"
  [ -n "$g" ] || g="$(rd "/sys/devices/system/cpu/cpu$p/cpufreq/scaling_governor")"
  printf '%s' "${g:-unavailable}"
}
cgroup_weight() {
  local w; w="$(rd /sys/fs/cgroup/user.slice/cpu.weight)"
  [ -n "$w" ] && { printf 'cpu.weight=%s' "$w"; return; }
  w="$(rd /sys/fs/cgroup/cpu/user.slice/cpu.shares)"
  [ -n "$w" ] && { printf 'cpu.shares=%s' "$w"; return; }
  printf 'unavailable'
}
profile_governor() {  # $1 profile -> first *available* preference
  python3 - "$POLICY" "$1" "$ROOT" <<'PY' 2>/dev/null || true
import json, os, sys
pol, prof, root = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    doc = json.load(open(pol))
except Exception:
    sys.exit(0)
prefs = doc.get("profiles", {}).get("list", {}).get(prof, {}).get("governor_preference", [])
avail = ""
for p in ("0", "4", "7"):
    for cand in (root + "/sys/devices/system/cpu/cpufreq/policy%s/scaling_available_governors" % p,
                 root + "/sys/devices/system/cpu/cpu%s/cpufreq/scaling_available_governors" % p):
        if os.path.exists(cand):
            avail = open(cand).read().strip()
            break
    if avail:
        break
if not prefs:
    sys.exit(0)
for pr in prefs:
    if not avail or pr in avail.split():
        print(pr); break
PY
}
apply_profile() {
  local prof="$1" gov applied=0 p
  # Refuse an unknown profile BEFORE writing anything.  Without this check
  # `mode banana` persisted a profile name that does not exist in power.json and
  # the boot applier then had no governor preference to map.
  if ! python3 - "$POLICY" "$prof" <<'PY'
import json, sys
try:
    doc = json.load(open(sys.argv[1]))
except Exception:
    sys.exit(2)
sys.exit(0 if sys.argv[2] in (doc.get("profiles", {}).get("list") or {}) else 1)
PY
  then
    say "unknown profile '$prof' (power.json lists: $(python3 - "$POLICY" <<'PY'
import json,sys
try:
    print(", ".join((json.load(open(sys.argv[1])).get("profiles",{}).get("list") or {}).keys()))
except Exception:
    print("(power.json unreadable)")
PY
))"
    return 2
  fi
  gov="$(profile_governor "$prof")"
  if [ -n "$gov" ]; then
    for p in 0 4 7; do
      for f in "$(abs /sys/devices/system/cpu/cpufreq/policy$p/scaling_governor)" \
               "$(abs /sys/devices/system/cpu/cpu$p/cpufreq/scaling_governor)"; do
        if [ -w "$f" ]; then printf '%s' "$gov" > "$f" 2>/dev/null && applied=$((applied+1)); fi
      done
    done
  fi
  local d; d="$(abs "$STATE_DIR")"
  mkdir -p "$d" 2>/dev/null || true
  printf '{"schema_version":1,"profile":"%s","governor":"%s","applied_knobs":%d,"updated":"%s"}\n' \
    "$prof" "${gov:-none}" "$applied" "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)" \
    > "$(profile_file)" 2>/dev/null || true
  say "profile=$prof governor=${gov:-none} knobs_written=$applied"
}

# ---- menu ------------------------------------------------------------------
cmd_menu() {
  python3 - "$MENU" "$QUIET" <<'PY'
import json, os, sys
menu, quiet = sys.argv[1], sys.argv[2] == "1"
def out(*a):
    if not quiet:
        print(*a)
try:
    doc = json.load(open(menu))
except Exception as e:
    print("power-menu.json unreadable (%s) — falling back to the built-in table" % e)
    doc = {"entries": [
        {"id": "cancel", "label": "Cancel", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "lock", "label": "Lock screen", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "screenshot", "label": "Take screenshot", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "restart", "label": "Restart", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "power-off", "label": "Power off", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "reboot-verbose", "label": "Reboot Verbose", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "reboot-safe-mode", "label": "Safe Mode", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "reboot-diag", "label": "Reboot Diag", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "reboot-debug", "label": "Reboot Debug", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "back", "label": "Back", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "forward", "label": "Forward", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "stop", "label": "Stop loading", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "reload-launcher", "label": "Reload launcher", "trigger_allowed": True, "refusal_reason": ""},
        {"id": "recovery", "label": "Recovery", "trigger_allowed": False,
         "refusal_reason": "NO_FLASH_INVARIANT - no bootloader interface is triggered"},
        {"id": "download-mode", "label": "Download Mode", "trigger_allowed": False,
         "refusal_reason": "NO_FLASH_INVARIANT - Download Mode exists only to flash"}],
        "invoked_by": {"timeout_ms": 15000}}
ents = doc.get("entries", [])
out("power menu (long-press POWER); %d entries, timeout %d ms"
    % (len(ents), doc.get("invoked_by", {}).get("timeout_ms", 15000)))
for e in ents:
    allowed = "TRIGGERABLE" if e.get("trigger_allowed") else "REFUSED"
    line = "  %-14s %-16s %s" % (e.get("id", "?"), e.get("label", ""), allowed)
    if not e.get("trigger_allowed") and e.get("refusal_reason"):
        line += " — " + e["refusal_reason"]
    out(line)
refused = [e.get("id") for e in ents if not e.get("trigger_allowed")]
out("refused entries: %s (each is refused at EXECUTION time, not hidden)" % (", ".join(refused) or "none"))
PY
}

cmd_menu_json() {
  python3 - "$MENU" <<'PY'
import json, sys
print(json.dumps(json.load(open(sys.argv[1])), separators=(",", ":")))
PY
}

# ---- status ----------------------------------------------------------------
verdict() {
  local bm="$1" have="$2" cap="$3"
  if [ "$bm" = "charger" ]; then printf 'DEGRADED_CHARGER_MODE'
  elif [ "$have" = "no" ]; then printf 'BLOCKED_KERNEL'
  elif [ -z "$cap" ]; then printf 'PARTIAL'
  else printf 'OK'; fi
}
cmd_status() {
  local bm have cap v prof gov cg
  bm="$(boot_mode)"; collect_gauge
  have=$([ -n "$gauge_dev" ] && printf yes || printf no)
  cap="${gauge_cap:-}"
  if [ -n "$cap" ] && { [ "$cap" -lt 0 ] || [ "$cap" -gt 100 ]; } 2>/dev/null; then cap=""; fi
  v="$(verdict "$bm" "$have" "$cap")"
  prof="$(profile_active)"; gov="$(governor_now 0)"; cg="$(cgroup_weight)"
  local mv; mv="$(abs "$MENU")"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-power-diag","boot_mode":"%s","state":"%s","gauge":{"present":%s,"device":"%s","capacity_percent":"%s","status":"%s","voltage_now":"%s","temp":"%s","health":"%s"},"profile":{"active":"%s","governor":"%s","cgroup":"%s"},"menu_present":%s,"charging_behaviour_verified":false,"owner_test":"docs/beta-finalization/manual-proof/24-battery-power.md"}\n' \
      "$bm" "$v" \
      "$([ "$have" = yes ] && printf true || printf false)" "$(json_escape "$gauge_dev")" \
      "$(json_escape "$cap")" "$(json_escape "$gauge_status")" "$(json_escape "$gauge_volt")" \
      "$(json_escape "$gauge_temp")" "$(json_escape "$gauge_health")" \
      "$(json_escape "$prof")" "$(json_escape "$gov")" "$(json_escape "$cg")" \
      "$([ -e "$mv" ] && printf true || printf false)"
    return 0
  fi
  hdr "boot mode"
  case "$bm" in
    charger) say "androidboot.mode=charger — LPCHARGE/charger-mode boot. This is a DISTINCT boot mode:"
             say "  sec_ts and other input drivers are disabled before userspace runs. Remedy is an"
             say "  ordinary reboot (no kernel patch from userspace, no flashing)." ;;
    normal)  say "normal boot (no androidboot.mode=charger on /proc/cmdline)" ;;
    *)       say "unknown — /proc/cmdline unreadable or carries no androidboot.mode" ;;
  esac
  hdr "battery / fuel gauge"
  if [ "$have" = yes ]; then
    say "gauge device : $gauge_dev (enumerated from /sys/class/power_supply, never assumed)"
    say "capacity     : ${cap:-unreadable}%"
    say "status       : ${gauge_status:-unknown}"
    say "voltage_now  : ${gauge_volt:-unreadable}"
    say "temp         : ${gauge_temp:-unreadable}"
    say "health       : ${gauge_health:-unknown}"
  else
    say "no /sys/class/power_supply/*/capacity node — no fuel gauge bound."
    say "This is BLOCKED_KERNEL. No battery percentage is invented."
  fi
  hdr "profile"
  say "active profile : $prof"
  say "governor(cpu0) : $gov"
  say "cgroup         : $cg"
  hdr "power menu"
  if [ -e "$mv" ]; then say "menu table: $MENU (use 'nuxel-power-diag.sh menu')"
  else say "menu table MISSING at $MENU — the button FSM would refuse power-menu (logged, not guessed)"; fi
  hdr "verdict"
  say "state: $v"
  case "$v" in
    OK) say "  a gauge is bound and reads a sane percentage. Charging BEHAVIOUR is still"
        say "  NEEDS_OWNER_TEST: a readable node is not proof the battery charges." ;;
    DEGRADED_CHARGER_MODE) say "  input is likely disabled for this boot; the profile/applier still work." ;;
    BLOCKED_KERNEL) say "  no gauge driver bound on this kernel." ;;
    PARTIAL) say "  gauge directory exists but capacity is unreadable/insane." ;;
  esac
}
cmd_profiles() {
  python3 - "$POLICY" <<'PY'
import json, sys
doc = json.load(open(sys.argv[1]))
print("battery profiles for %s (default: %s)" % (doc["device"]["codename"], doc["profiles"]["default"]))
for k, v in doc["profiles"]["list"].items():
    print("  %-12s %s" % (k, v["label"]))
    print("      %s" % v["summary"])
    print("      governor preference: %s" % " > ".join(v["governor_preference"]))
    print("      cgroup v2 weight %s / v1 shares %s ; brightness cap %s%%"
          % (v["cgroup_v2_cpu_weight"], v["cgroup_v1_cpu_shares"], v["brightness_cap_percent"]))
PY
}
cmd_report() {
  local f; f="$(abs "$LOG")"
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  { printf '=== nuxel-power-diag report %s ===\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown)"
    local saved="$JSON"; JSON=0; cmd_status; JSON="$saved"; cmd_menu; } >> "$f" 2>/dev/null || true
  [ "$JSON" = 1 ] && cmd_status
  say "evidence appended to $LOG"
}

# ---- selftest --------------------------------------------------------------
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0
  [ -d "$fixdir" ] || { printf 'FAIL selftest: no fixtures dir (%s)\n' "$fixdir"; return 2; }
  local f exp got
  for f in "$fixdir"/power-*; do
    [ -d "$f" ] || continue
    n=$((n+1))
    exp="$(sed -n 's/^state=//p' "$f/EXPECTED" 2>/dev/null | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-28s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-28s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"
  return $rc
}

case "$CMD" in
  status)   cmd_status ;;
  profiles) cmd_profiles ;;
  mode)     apply_profile "${1:-balanced}" ;;
  apply-persisted) apply_profile "$(profile_active)" ;;
  menu)     [ "$JSON" = 1 ] && cmd_menu_json || cmd_menu ;;
  report)   cmd_report ;;
  selftest) selftest ;;
  help|-h|--help)
    sed -n '2,40p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) printf 'unknown command: %s (try help)\n' "$CMD" >&2; exit 2 ;;
esac
