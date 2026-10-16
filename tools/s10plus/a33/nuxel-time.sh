#!/usr/bin/env bash
# nuxel-time.sh — S10+ (SM-G975F / beyond2lte) time, RTC and timesync diagnoser.
#
# WHAT IT REPORTS (from observable state only)
#   * the system clock, timezone and whether the clock is even set,
#   * the RTC that actually exists (/sys/class/rtc/*) and the real delta between
#     it and the system clock,
#   * which timesync backend is installed AND active (systemd-timesyncd, chrony,
#     others) — or NO_TIMESYNC_BACKEND, never a pretence,
#   * whether journald timestamps agree with the system clock,
#   * whether the launcher clock (the bridge's phone-status "time" field, which
#     is what the status bar renders) agrees with the system clock,
#   * the recorded RTC delta across an ordinary reboot (owner-driven mark/compare).
#
# WHAT IT DOES NOT DO
#   It never claims an RTC is persistent because the files exist, and it never
#   claims a reboot's clock survived without a before/after pair. Those states
#   are NEEDS_OWNER_TEST (docs/beta-finalization/manual-proof/05-timekeeping.md).
#   It writes nothing outside /var/lib/nuxel/time and /var/log/nuxel — no
#   partition, no kernel cmdline, no RTC register poking.
#
# Usage (also reachable as `nuxelctl time <sub>`):
#   nuxel-time.sh status [--json]     clock/RTC/backend/journald/launcher report
#   nuxel-time.sh verify [--json] [--log]   PASS/FAIL per check; exit 1 on a real failure
#   nuxel-time.sh rtc                 RTC inventory
#   nuxel-time.sh mark                record RTC + boot id before an ordinary reboot
#   nuxel-time.sh compare             after the reboot: delta, with verdict
#   nuxel-time.sh sync                ask the real backend for a sync
#   nuxel-time.sh set <ISO8601>       set the clock, then systohc to the RTC
#   nuxel-time.sh selftest            run the bundled offline fixtures
#
# OFFLINE TESTABILITY: NUXEL_DIAG_ROOT (or --root DIR) prefixes /sys, /proc,
# /var, /run; $ROOT/usr/bin/<tool> wins over the system tool. Tests also set
# NUXEL_DIAG_NO_SYSTEM=1 so fixtures can never silently read the host's state.
set -uo pipefail

SELF="$(basename "$0")"
SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY_DEFAULT="/etc/nuxel/time/time.json"
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

POLICY="${NUXEL_TIME_POLICY:-$POLICY_DEFAULT}"
STATE_DIR_DEFAULT="/var/lib/nuxel/time"
EVIDENCE_LOG="${NUXEL_TIME_LOG:-/var/log/nuxel/time.log}"
# Tools that measure rather than read device state: never blocked by the
# fixture isolation flag (see run_tool).
: "${NUXEL_DIAG_SAFE_TOOLS:=date uname}"

say()  { printf '%s\n' "$*"; }
hdr()  { printf '\n== %s ==\n' "$*"; }
abs()  { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }

run_tool() {
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ -x "$p" ] && [ "$ROOT" != "/" ]; then "$p" "$@"; return $?; fi
  done
  # NUXEL_DIAG_NO_SYSTEM=1 blocks *state* tools so a fixture run can never read
  # the host's real state. Harmless clock/identity tools stay allowed: `date`
  # and `uname` are the measuring stick, not the state under test (and a fixture
  # that wants to pin the clock ships its own usr/bin/date, which wins above).
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then
    case " $NUXEL_DIAG_SAFE_TOOLS " in
      *" $t "*) ;;
      *) return 127 ;;
    esac
  fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}
have_tool() { run_tool "$1" --version >/dev/null 2>&1 || run_tool "$1" -v >/dev/null 2>&1; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' | tr -d '\r\n'; }

# policy_get KEY DEFAULT — the policy file is optional; a missing/broken file
# yields the documented default and is reported, never guessed around silently.
POLICY_LOADED=0
policy_get() {
  local key="$1" dflt="$2" v=""
  if [ -r "$(abs "$POLICY")" ]; then
    POLICY_LOADED=1
    v="$(python3 - "$(abs "$POLICY")" "$key" <<'PY' 2>/dev/null
import json,sys
doc=json.load(open(sys.argv[1]))
cur=doc
for part in sys.argv[2].split('.'):
    if isinstance(cur,dict) and part in cur: cur=cur[part]
    else: print(""); sys.exit(0)
print(cur if not isinstance(cur,(dict,list)) else "")
PY
)"
  fi
  [ -n "$v" ] && printf '%s' "$v" || printf '%s' "$dflt"
}

# ---------------------------------------------------------------------------
# collectors
# ---------------------------------------------------------------------------
sys_epoch() { run_tool date +%s 2>/dev/null; }

rtc_devices() {
  # Prints one line per RTC: name date time since_epoch
  local d found=0
  for d in "$(abs /sys/class/rtc)"/*; do
    [ -e "$d" ] || continue
    found=1
    local n; n="$(basename "$d")"
    local nm date time since
    nm="$(cat "$d/name" 2>/dev/null || echo '?')"
    date="$(cat "$d/date" 2>/dev/null || echo '?')"
    time="$(cat "$d/time" 2>/dev/null || echo '?')"
    since="$(cat "$d/since_epoch" 2>/dev/null || echo '?')"
    printf '%s name=%s date=%s time=%s since_epoch=%s\n' "$n" "$nm" "$date" "$time" "$since"
  done
  [ "$found" = "1" ] || return 1
  return 0
}

rtc_device_path() {
  local p
  for p in /dev/rtc0 /dev/rtc; do [ -e "$(abs "$p")" ] && { printf '%s' "$p"; return 0; }; done
  return 1
}

rtc_epoch() {
  # Preference: sysfs since_epoch (no root needed) -> `hwclock --show`.
  local d since
  for d in "$(abs /sys/class/rtc)"/*; do
    [ -e "$d" ] || continue
    since="$(cat "$d/since_epoch" 2>/dev/null)"
    [ -n "${since:-}" ] && { printf '%s' "$since"; return 0; }
  done
  local hw; hw="$(run_tool hwclock --show --utc 2>/dev/null)"
  [ -n "$hw" ] || return 1
  run_tool date -u -d "$hw" +%s 2>/dev/null || run_tool date -j -f "%Y-%m-%d %H:%M:%S" "$hw" +%s 2>/dev/null
}

timesync_backend() {
  # Prints: active_backend|installed_list
  local active="none" installed=""
  local u
  for u in systemd-timesyncd chronyd chrony ntpsec ntpd openntpd; do
    local state
    state="$(run_tool systemctl is-active "$u" 2>/dev/null | tr -d '\r')"
    [ "$state" = "active" ] && [ "$active" = "none" ] && active="$u"
  done
  local p
  for p in systemd-timesyncd chrony ntpsec openntpd; do
    if [ -d "$(abs "/usr/lib/systemd/system")" ]; then
      [ -e "$(abs "/usr/lib/systemd/system/$p.service")" ] && installed="$installed$p "
    fi
    run_tool rpm -q "$p" >/dev/null 2>&1 && installed="$installed$p "
  done
  printf '%s|%s' "$active" "$(printf '%s' "$installed" | xargs 2>/dev/null || printf '%s' "$installed")"
}

timesync_detail() {
  local active="$1"
  case "$active" in
    systemd-timesyncd)
      run_tool timedatectl show-timesync --all 2>/dev/null | sed -n '1,12p' \
        || run_tool timedatectl status 2>/dev/null | sed 's/^/  /'
      ;;
    chronyd|chrony)
      run_tool chronyc tracking 2>/dev/null | sed 's/^/  /'
      run_tool chronyc sources 2>/dev/null | sed -n '1,8p' | sed 's/^/  /'
      ;;
    *) say "  (no timesync backend active — the clock is only as good as the RTC)" ;;
  esac
}

journal_epoch() {
  # Newest journal entry epoch, so a frozen journald is detectable.
  local out
  out="$(run_tool journalctl -n 1 -o short-unix --no-pager 2>/dev/null | awk 'NR==1{print $1}')"
  case "$out" in ''|*[!0-9.]*) return 1 ;; esac
  printf '%.0f' "$out"
}

bridge_json() {
  local url="$1" tok="${2:-}"
  if [ -n "$tok" ]; then
    run_tool curl -s -m 5 -H "Authorization: Bearer $tok" "$url"
  else
    run_tool curl -s -m 5 "$url"
  fi
}

launcher_clock() {
  # Prints: "time=<HH:MM> source=bridge" or "UNKNOWN reason=..."
  # The launcher's status bar renders bridge.phone.status.time
  # (services/nuxel-bridge/src/api.py -> _get_system_phone_status), so this is
  # the same value the user sees, read from the same place.
  local health; health="$(bridge_json "http://127.0.0.1:8080/api/v1/health")"
  if [ -z "$health" ]; then printf 'UNKNOWN reason=bridge-not-reachable'; return 0; fi
  local tok; tok="$(run_tool curl -s -m 5 -X POST -H 'Content-Type: application/json' \
        -d '{"app_id":"org.nuxel.Diagnostics"}' \
        "http://127.0.0.1:8080/api/v1/auth/token" 2>/dev/null \
      | sed -n 's/.*"token"[ ]*:[ ]*"\([^"]*\)".*/\1/p')"
  if [ -z "$tok" ]; then printf 'UNKNOWN reason=bridge-token-unavailable'; return 0; fi
  local st; st="$(bridge_json "http://127.0.0.1:8080/api/v1/phone/status" "$tok")"
  local t; t="$(printf '%s' "$st" | sed -n 's/.*"time"[ ]*:[ ]*"\([^"]*\)".*/\1/p')"
  if [ -n "$t" ]; then printf 'time=%s source=bridge-phone-status' "$t"; else printf 'UNKNOWN reason=no-time-field'; fi
}

# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------
ST_CLOCK_SET=unknown; ST_RTC_PRESENT=no; ST_RTC_DELTA=; ST_BACKEND=none
ST_JOURNAL=; ST_LAUNCHER=unknown; ST_RTC_NAME=""

do_status() {
  local json="${1:-}"
  local now_epoch now_iso tz
  now_epoch="$(sys_epoch)"; now_iso="$(run_tool date -u +%FT%TZ 2>/dev/null)"; tz="$(run_tool date +%Z 2>/dev/null)"
  say "nuxel-time — device=beyond2lte (SM-G975F)"
  say "root_prefix=$ROOT  policy=$POLICY (loaded=$POLICY_LOADED)"

  hdr "system clock"
  say "utc=${now_iso:-?} local=$(run_tool date +'%Y-%m-%dT%H:%M:%S%z' 2>/dev/null) tz=${tz:-?} epoch=${now_epoch:-?}"
  if [ -n "$now_epoch" ] && [ "$now_epoch" -gt 1577836800 ] 2>/dev/null; then
    ST_CLOCK_SET=yes
    say "clock_set=yes (epoch is after 2020-01-01)"
  else
    ST_CLOCK_SET=no
    say "clock_set=no (epoch is at or before 2020-01-01 — a phone with no RTC and no NTP"
    say "clock_set=no  boots at the epoch; every log line then carries a useless timestamp)"
  fi
  say "timedatectl:"
  run_tool timedatectl status 2>/dev/null | sed 's/^/  /' || say "  (timedatectl unavailable)"

  hdr "RTC"
  local rtcs; rtcs="$(rtc_devices)" && { ST_RTC_PRESENT=yes; printf '%s\n' "$rtcs"; ST_RTC_NAME="$(printf '%s' "$rtcs" | head -1 | awk '{print $2}' | sed 's/name=//')"; } \
    || say "(no /sys/class/rtc/* — no RTC driver is bound; time cannot persist across power-off)"
  local dev; dev="$(rtc_device_path)" && say "device=$dev" || say "device=(none of /dev/rtc0,/dev/rtc present)"
  local r_epoch; r_epoch="$(rtc_epoch)" || r_epoch=""
  if [ -n "$r_epoch" ]; then
    say "rtc_epoch=$r_epoch ($(run_tool date -u -d "@$r_epoch" +%FT%TZ 2>/dev/null || echo '?'))"
    if [ -n "$now_epoch" ]; then
      ST_RTC_DELTA=$(( now_epoch - r_epoch ))
      say "rtc_delta_s=$ST_RTC_DELTA (system minus RTC; negative = system behind)"
      local warn fail
      warn="$(policy_get rtc.max_drift_s_warn 60)"; fail="$(policy_get rtc.max_drift_s_fail 300)"
      local ad=${ST_RTC_DELTA#-}
      if [ "$ad" -le "$warn" ] 2>/dev/null; then say "rtc_drift=ok (<= ${warn}s)"
      elif [ "$ad" -le "$fail" ] 2>/dev/null; then say "rtc_drift=warn (${ad}s > ${warn}s)"
      else say "rtc_drift=fail (${ad}s > ${fail}s)"; fi
    fi
  else
    say "rtc_epoch=unreadable (no reading — this is a finding, not an assumption)"
  fi
  say "drift marks: before=$( [ -e "$(abs "$(policy_get rtc.drift_before /var/lib/nuxel/time/rtc-before.json)")" ] && echo present || echo absent) after=$( [ -e "$(abs "$(policy_get rtc.drift_after /var/lib/nuxel/time/rtc-after.json)")" ] && echo present || echo absent)"

  hdr "timesync"
  local tb backend installed; tb="$(timesync_backend)"; backend="${tb%%|*}"; installed="${tb#*|}"
  ST_BACKEND="$backend"
  say "active_backend=$backend"
  say "installed_candidates=${installed:-<none detected>}"
  [ "$backend" = "none" ] && say "MEANING: no timesync daemon is active. The clock will NOT be corrected automatically;"
  [ "$backend" = "none" ] && say "MEANING: this is reported as NO_TIMESYNC_BACKEND, not silently ignored."
  timesync_detail "$backend"

  hdr "journald clock agreement"
  local j; j="$(journal_epoch)" || j=""
  if [ -n "$j" ] && [ -n "$now_epoch" ]; then
    local d=$(( now_epoch - j )); ST_JOURNAL="$d"
    say "journal_newest_epoch=$j delta_s=$d (system minus newest entry)"
    local jtol; jtol="$(policy_get journal.tolerance_s 120)"
    local ad=${d#-}
    [ "$ad" -le "$jtol" ] && say "journald_agrees=yes (<= ${jtol}s)" || say "journald_agrees=NO (${ad}s > ${jtol}s — journald may be frozen or reading a stale clock)"
  else
    ST_JOURNAL="unknown"; say "journald_agrees=UNKNOWN (journalctl unavailable or produced no parsable entry)"
  fi

  hdr "launcher clock agreement"
  local lc; lc="$(launcher_clock)"
  ST_LAUNCHER="$lc"
  say "$lc"
  case "$lc" in
    time=*)
      local lt="${lc#time=}"; lt="${lt%% *}"
      local lt_sys; lt_sys="$(run_tool date +%H:%M 2>/dev/null)"
      local tol; tol="$(policy_get launcher.tolerance_s 120)"
      # Compare as minutes-of-day with wrap-around.
      local lm sm diff
      lm=$(( 10#${lt%%:*} * 60 + 10#${lt##*:} )) 2>/dev/null
      sm=$(( 10#${lt_sys%%:*} * 60 + 10#${lt_sys##*:} )) 2>/dev/null
      diff=$(( lm - sm )); [ "$diff" -lt 0 ] && diff=$(( -diff ))
      [ "$diff" -gt 720 ] && diff=$(( 1440 - diff ))
      say "system_local=$lt_sys delta_min=$diff tolerance_min=$(( tol / 60 ))"
      if [ "$diff" -le $(( tol / 60 )) ]; then say "launcher_agrees=yes"
      else say "launcher_agrees=NO (launcher shows $lt, system is $lt_sys)"; fi
      ;;
    *) say "launcher_agrees=UNKNOWN — the bridge is not reachable from this shell; the launcher"
       say "launcher_agrees=UNKNOWN   clock is therefore NOT being verified here (never assumed correct)" ;;
  esac

  hdr "verdict"
  local v
  if [ "$ST_RTC_PRESENT" = "no" ]; then
    v="RTC_ABSENT"
  elif [ "$ST_BACKEND" = "none" ]; then
    v="NO_TIMESYNC_BACKEND"
  elif [ "$ST_CLOCK_SET" = "no" ]; then
    v="CLOCK_NOT_SET"
  elif [ "$ST_LAUNCHER" = "unknown" ] || [ "$ST_JOURNAL" = "unknown" ]; then
    v="PARTIAL_EVIDENCE"
  else
    v="CLOCK_OK_UNVERIFIED_PERSISTENCE"
  fi
  say "$v"
  say "meaning: none of these states equals 'persistence across a reboot is proven'. That"
  say "meaning: requires the owner mark/compare procedure (manual-proof area 5)."

  if [ "$json" = "--json" ]; then
    printf '{"tool":"nuxel-time","device":"beyond2lte","verdict":"%s","clock_set":"%s","rtc_present":"%s","rtc_name":"%s","rtc_delta_s":"%s","backend":"%s","journal_delta_s":"%s","launcher":"%s","policy_loaded":%s,"root":"%s"}\n' \
      "$(jesc "$v")" "$ST_CLOCK_SET" "$ST_RTC_PRESENT" "$(jesc "$ST_RTC_NAME")" "$(jesc "$ST_RTC_DELTA")" \
      "$(jesc "$ST_BACKEND")" "$(jesc "$ST_JOURNAL")" "$(jesc "$ST_LAUNCHER")" "$([ "$POLICY_LOADED" = 1 ] && echo true || echo false)" "$(jesc "$ROOT")"
  fi
}

# ---------------------------------------------------------------------------
# verify — per-check PASS/FAIL, exit 1 when a check is genuinely wrong
# ---------------------------------------------------------------------------
V_JSON=""
field() { printf '%s' "$V_JSON" | sed -n "s/.*\"$1\":\"\{0,1\}\([^\",}]*\)\"\{0,1\}.*/\1/p"; }

do_verify() {
  local json="${1:-}" log="${2:-}" fails=0 checked=0 unknown=0
  local out; out="$(do_status --json)"; local report; report="$(do_status)"
  local p v; v="$(printf '%s' "$out" | tail -1)"
  V_JSON="$v"
  local clock_set rtc_present rtc_delta backend jdelta launcher
  clock_set="$(field clock_set)"; rtc_present="$(field rtc_present)"; rtc_delta="$(field rtc_delta_s)"
  backend="$(field backend)"; jdelta="$(field journal_delta_s)"; launcher="$(field launcher)"

  hdr "checks"
  chk() { printf '%s %s%s\n' "$1" "$2" "${3:+ — $3}"; }
  if [ "$clock_set" = "yes" ]; then chk PASS "system clock is set"; checked=$((checked+1));
  else chk FAIL "system clock is set" "epoch is before 2020-01-01"; fails=$((fails+1)); fi

  if [ "$rtc_present" = "yes" ]; then chk PASS "RTC driver bound"; checked=$((checked+1));
  else chk FAIL "RTC driver bound" "no /sys/class/rtc entry"; fails=$((fails+1)); fi

  if [ -n "$rtc_delta" ]; then
    local fail_s; fail_s="$(policy_get rtc.max_drift_s_fail 300)"; local ad=${rtc_delta#-}
    if [ "$ad" -le "$fail_s" ] 2>/dev/null; then chk PASS "RTC drift within ${fail_s}s" "delta=${rtc_delta}s"; checked=$((checked+1))
    else chk FAIL "RTC drift within ${fail_s}s" "delta=${rtc_delta}s"; fails=$((fails+1)); fi
  else chk UNKNOWN "RTC drift" "no readable RTC epoch"; unknown=$((unknown+1)); fi

  case "${backend:-}" in
    none) chk FAIL "timesync backend active" "NO_TIMESYNC_BACKEND — the clock is never corrected"; fails=$((fails+1)) ;;
    "")   chk UNKNOWN "timesync backend active" "not reported"; unknown=$((unknown+1)) ;;
    *)    chk PASS "timesync backend active" "backend=$backend"; checked=$((checked+1)) ;;
  esac

  case "${jdelta:-unknown}" in
    unknown|"") chk UNKNOWN "journald timestamps agree with the clock" "journalctl unavailable"; unknown=$((unknown+1)) ;;
    *) local jtol; jtol="$(policy_get journal.tolerance_s 120)"; local aj=${jdelta#-}
       if [ "$aj" -le "$jtol" ] 2>/dev/null; then chk PASS "journald timestamps agree with the clock" "delta=${jdelta}s"; checked=$((checked+1))
       else chk FAIL "journald timestamps agree with the clock" "delta=${jdelta}s"; fails=$((fails+1)); fi ;;
  esac

  case "${launcher:-unknown}" in
    time=*)
      if printf '%s\n' "$report" | grep -q 'launcher_agrees=yes'; then
        chk PASS "launcher clock agrees with the system clock" "$(printf '%s' "$launcher")"; checked=$((checked+1))
      else
        chk FAIL "launcher clock agrees with the system clock" "$(printf '%s' "$launcher")"; fails=$((fails+1))
      fi ;;
    *) chk UNKNOWN "launcher clock agrees with the system clock" "bridge unreachable — not verifiable from here"; unknown=$((unknown+1)) ;;
  esac

  if [ -e "$(abs "$(policy_get rtc.drift_before /var/lib/nuxel/time/rtc-before.json)")" ] && [ -e "$(abs "$(policy_get rtc.drift_after /var/lib/nuxel/time/rtc-after.json)")" ]; then
    local d; d="$(do_compare_quiet)"
    case "$d" in
      PASS*) chk PASS "RTC survived the recorded reboot" "$d"; checked=$((checked+1)) ;;
      FAIL*) chk FAIL "RTC survived the recorded reboot" "$d"; fails=$((fails+1)) ;;
      *)     chk UNKNOWN "RTC survived the recorded reboot" "$d"; unknown=$((unknown+1)) ;;
    esac
  else
    chk NEEDS_OWNER_TEST "RTC persistence across an ordinary reboot" "run: nuxelctl time mark; reboot; nuxelctl time compare"; unknown=$((unknown+1))
  fi

  say ""
  say "summary: pass=$checked fail=$fails unknown_or_owner=$unknown"
  if [ "$log" = "--log" ]; then
    local dir; dir="$(dirname "$(abs "$EVIDENCE_LOG")")"
    mkdir -p "$dir" 2>/dev/null || true
    { printf '\n--- %s ---\n' "$(run_tool date -u +%FT%TZ 2>/dev/null)"; printf '%s\n' "$report"; } >> "$(abs "$EVIDENCE_LOG")" 2>/dev/null \
      && say "evidence appended to $EVIDENCE_LOG"
  fi
  if [ "$json" = "--json" ]; then
    printf '{"tool":"nuxel-time","check":"verify","pass":%s,"fail":%s,"unknown":%s,"clock_set":"%s","rtc_present":"%s","backend":"%s"}\n' \
      "$checked" "$fails" "$unknown" "$clock_set" "$rtc_present" "$(jesc "${backend:-}")"
  fi
  if [ "$fails" -eq 0 ]; then return 0; fi
  return 1
}

# ---------------------------------------------------------------------------
# mark / compare — the reboot-persistence evidence pair
# ---------------------------------------------------------------------------
state_dir() { printf '%s' "$(abs "$(policy_get rtc.state_dir "$STATE_DIR_DEFAULT")")"; }

do_mark() {
  local dir; dir="$(state_dir)"; mkdir -p "$dir" || { say "cannot create $dir"; return 1; }
  local before; before="$(policy_get rtc.drift_before /var/lib/nuxel/time/rtc-before.json)"
  local now; now="$(sys_epoch)"; local r; r="$(rtc_epoch)" || r=""
  local bid=""; bid="$(cat "$(abs /proc/sys/kernel/random/boot_id)" 2>/dev/null)"
  [ -z "$bid" ] && bid="$(run_tool cat /proc/sys/kernel/random/boot_id 2>/dev/null)"
  python3 - "$(abs "$before")" "$now" "${r:-}" "$bid" <<'PY'
import json,sys,os
path,sys_epoch,rtc_epoch,boot_id=sys.argv[1:5]
os.makedirs(os.path.dirname(path),exist_ok=True)
doc={"schema_version":1,"system_epoch":int(sys_epoch) if sys_epoch.isdigit() else None,
     "rtc_epoch":int(rtc_epoch) if rtc_epoch.isdigit() else None,
     "boot_id":boot_id or None,"iso":None}
import time
doc["iso"]=time.strftime("%FT%TZ",time.gmtime(doc["system_epoch"])) if doc["system_epoch"] else None
json.dump(doc,open(path,"w"),indent=2)
print("mark written: %s system_epoch=%s rtc_epoch=%s boot_id=%s"%(path,doc["system_epoch"],doc["rtc_epoch"],(doc["boot_id"] or "?")[:8]))
PY
  say "next: perform ONE ordinary reboot, then run: nuxelctl time compare"
}

do_compare_quiet() {
  local before after
  before="$(abs "$(policy_get rtc.drift_before /var/lib/nuxel/time/rtc-before.json)")"
  after="$(abs "$(policy_get rtc.drift_after /var/lib/nuxel/time/rtc-after.json)")"
  [ -r "$before" ] && [ -r "$after" ] || { printf 'NO_MARKS'; return 0; }
  python3 - "$before" "$after" "$(policy_get reboot_persistence.max_delta_s 10)" "$(policy_get reboot_persistence.require_boot_id_change true)" <<'PY'
import json,sys
b=json.load(open(sys.argv[1])); a=json.load(open(sys.argv[2]))
maxd=int(sys.argv[3]); req=sys.argv[4].lower()=="true"
if req and b.get("boot_id") and a.get("boot_id") and b["boot_id"]==a["boot_id"]:
    print("FAIL same boot_id — no reboot happened between mark and compare (the mark/compare pair is invalid)")
    sys.exit(0)
if b.get("rtc_epoch") is None:
    print("UNKNOWN the pre-reboot RTC was unreadable — persistence cannot be judged")
    sys.exit(0)
drift=a["rtc_epoch"]-b["rtc_epoch"]
wall=a["system_epoch"]-b["system_epoch"]
d=drift-wall
if abs(d)<=maxd:
    print("PASS rtc_epoch advanced by %ds, wall clock by %ds (RTC error %+ds <= %ds)"%(drift,wall,d,maxd))
else:
    print("FAIL rtc_epoch advanced by %ds, wall clock by %ds (RTC error %+ds > %ds)"%(drift,wall,d,maxd))
PY
}

do_compare() {
  local before after
  before="$(abs "$(policy_get rtc.drift_before /var/lib/nuxel/time/rtc-before.json)")"
  after="$(abs "$(policy_get rtc.drift_after /var/lib/nuxel/time/rtc-after.json)")"
  if [ ! -r "$before" ]; then say "no pre-reboot mark: run 'nuxelctl time mark' before the reboot"; return 2; fi
  local dir; dir="$(state_dir)"; mkdir -p "$dir" || true
  local now r bid
  now="$(sys_epoch)"; r="$(rtc_epoch)" || r=""
  bid="$(cat "$(abs /proc/sys/kernel/random/boot_id)" 2>/dev/null)"
  python3 - "$after" "$now" "${r:-}" "$bid" <<'PY'
import json,sys,os,time
path,sys_epoch,rtc_epoch,boot_id=sys.argv[1:5]
os.makedirs(os.path.dirname(path),exist_ok=True)
doc={"schema_version":1,"system_epoch":int(sys_epoch) if sys_epoch.isdigit() else None,
     "rtc_epoch":int(rtc_epoch) if rtc_epoch.isdigit() else None,"boot_id":boot_id or None,
     "iso":time.strftime("%FT%TZ",time.gmtime())}
json.dump(doc,open(path,"w"),indent=2)
print("post-reboot reading written: %s"%path)
PY
  local verdict; verdict="$(do_compare_quiet)"
  hdr "reboot persistence"
  say "$verdict"
  say "log this verdict in docs/beta-finalization/manual-proof/05-timekeeping.md (area 5)."
  case "$verdict" in PASS*) return 0 ;; FAIL*) return 1 ;; *) return 2 ;; esac
}

# ---------------------------------------------------------------------------
# rtc / sync / set / selftest
# ---------------------------------------------------------------------------
do_rtc() {
  hdr "RTC inventory"
  rtc_devices || say "(no RTC on this root)"
  say "device: $(rtc_device_path || echo none)"
  say "sysfs tree:"
  local d; for d in "$(abs /sys/class/rtc)"/*; do [ -e "$d" ] && say "  ${d#"$ROOT"}"; done
  say "kernel support (reported, never assumed):"
  local krel kpath kval
  krel="$(run_tool uname -r 2>/dev/null || uname -r)"
  kpath="$(abs "/boot/config-$krel")"
  for k in CONFIG_RTC_CLASS CONFIG_RTC_DRV_S5M CONFIG_RTC_HCTOSYS CONFIG_RTC_SYSTOHC; do
    kval="$(grep -m1 "^$k=" "$kpath" 2>/dev/null | cut -d= -f2)"
    say "  $k = ${kval:-unknown}"
  done
  say "  (unknown = the config could not be read here; that is stated, not hidden)"
}

do_sync() {
  local tb backend; tb="$(timesync_backend)"; backend="${tb%%|*}"
  case "$backend" in
    systemd-timesyncd) run_tool timedatectl set-ntp true && say "asked systemd-timesyncd for a sync (set-ntp true)";;
    chronyd|chrony)    run_tool chronyc makestep && say "asked chrony to step the clock";;
    none) say "no timesync backend is active: nothing to ask"; return 1;;
    *) say "backend $backend: no sync command is implemented for it — reported, not faked"; return 1;;
  esac
  run_tool timedatectl status 2>/dev/null | sed 's/^/  /'
  local r; r="$(rtc_epoch)" || r=""
  [ -n "$r" ] && say "RTC now reads $r — persist the corrected system clock with: nuxelctl time set <ISO8601>"
  say "(a sync corrects the running clock; only systohc writes it back to the RTC)"
}

do_set() {
  local val="${1:-}"
  [ -z "$val" ] && { say "usage: nuxelctl time set <ISO8601 e.g. 2026-10-16T12:00:00Z>"; return 2; }
  case "$val" in *[!0-9TZ:.+-]*) say "refusing: '$val' is not an ISO-8601 timestamp"; return 2 ;; esac
  run_tool date -u -s "$val" >/dev/null 2>&1 || run_tool timedatectl set-time "$val" || { say "setting the clock failed (need root/CAP_SYS_TIME)"; return 1; }
  say "system clock set to $val"
  if run_tool hwclock --systohc --utc 2>/dev/null; then say "RTC updated (hwclock --systohc --utc)"
  else say "RTC NOT updated: hwclock failed or is unavailable — record this, do not assume persistence"; fi
}

do_selftest() {
  local fx="${NUXEL_TIME_FIXTURES:-$(dirname "$SELF_PATH")/tests/fixtures-p3}"
  local fail=0 n
  [ -d "$fx" ] || { say "FAIL fixtures directory not found: $fx"; return 1; }
  for n in "$fx"/time-*/; do
    [ -d "$n" ] || continue
    local name exp got
    name="$(basename "$n")"
    exp="$(cat "$n/EXPECTED" 2>/dev/null || echo '')"
    [ -z "$exp" ] && { say "SKIP $name (no EXPECTED)"; continue; }
    got="$(NUXEL_DIAG_ROOT="$n" NUXEL_DIAG_NO_SYSTEM=1 NUXEL_TIME_POLICY="/etc/nuxel/time/time.json" "$SELF_PATH" status 2>&1 \
           | sed -n '/== verdict ==/,+1p' | sed -n '2p' | sed 's/^ *//' | cut -d' ' -f1)"
    if [ "$got" = "$exp" ]; then say "PASS $name verdict=$got"; else say "FAIL $name expected=$exp got=${got:-<none>}"; fail=$((fail+1)); fi
  done
  say "== $fail failing fixture(s) =="
  return "$fail"
}

case "$CMD" in
  status)   do_status "${1:-}" ;;
  verify)   do_verify "${1:-}" "${2:-}" ;;
  rtc)      do_rtc ;;
  mark)     do_mark ;;
  compare)  do_compare ;;
  sync)     do_sync ;;
  set)      do_set "${1:-}" ;;
  selftest) do_selftest ;;
  help|-h|--help) sed -n '2,32p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) say "unknown command: $CMD (try: $SELF help)"; exit 2 ;;
esac
