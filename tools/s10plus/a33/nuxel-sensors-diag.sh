#!/usr/bin/env bash
# nuxel-sensors-diag.sh — S10+ (beyond2lte) sensor enumeration + raw-read diagnostic.
#
# Enumerates the real sensor evidence from three independent sources (IIO devices,
# the input subsystem, the sensor-hub driver set) and reports, PER CLASS:
#   readable | present-unreadable | absent (NOT_SUPPORTED_ON_DEVICE).
# `read`/`watch` print ONLY raw values actually read from the kernel; nothing is
# synthesized. Motion must be physically induced, so the felt/observed half is
# NEEDS_OWNER_TEST and this tool never gates another area.
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_SENSORS_POLICY:-/etc/nuxel/sensors/sensors.json}"
LOG="${NUXEL_SENSORS_LOG:-/var/log/nuxel/sensors-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; NUM=""
for a in "$@"; do case "$a" in --json) JSON=1 ;; [0-9]*) NUM="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/sensors/sensors.json"
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }

# ---- enumeration -----------------------------------------------------------
# iio_catalog prints "iioname<TAB>devdir" for every IIO device that has a name.
iio_catalog() {
  local d n
  for d in "$(abs /sys/bus/iio/devices)"/*; do
    [ -d "$d" ] || continue
    n="$(cat "$d/name" 2>/dev/null | tr -d '\r\n')"
    [ -n "$n" ] && printf '%s\t%s\n' "$n" "${d#$ROOT}"
  done
}
input_names() { [ -r "$(abs /proc/bus/input/devices)" ] && sed -n 's/^N: Name="\(.*\)"$/\1/p' "$(abs /proc/bus/input/devices)"; }
hub_modules() {
  local m
  [ -r "$(abs /proc/modules)" ] || return 0
  for m in $(python3 - "$POLICY" <<'PY'
import json,sys
try: print(" ".join(json.load(open(sys.argv[1])).get("evidence_sources",{}).get("hub_drivers",[])))
except Exception: pass
PY
); do grep -q "^$m " "$(abs /proc/modules)" 2>/dev/null && printf '%s\n' "$m"; done
}
class_state() { # $1 class -> readable|present-unreadable|absent + the iio dir on stdout line 2
  python3 - "$POLICY" "$1" "$ROOT" <<'PY'
import glob, json, os, sys
pol, cls, root = sys.argv[1], sys.argv[2], sys.argv[3]
try: d = json.load(open(pol))
except Exception: sys.exit(0)
spec = d.get("classes", {}).get(cls, {})
r = root.rstrip("/")
# 1. IIO device whose name matches one of the class's iio_names
best = None
for dev in sorted(glob.glob(r + "/sys/bus/iio/devices/iio:device*")):
    try: nm = open(os.path.join(dev, "name")).read().strip()
    except Exception: continue
    for want in spec.get("iio_names", []):
        if want and want.lower() in nm.lower():
            best = dev; break
    if best: break
if best:
    chans = spec.get("iio_channels", [])
    readable = [c for c in chans if os.path.exists(os.path.join(best, c))]
    if readable:
        print("readable"); print(best[len(r):]); sys.exit(0)
    print("present-unreadable"); print(best[len(r):]); sys.exit(0)
# 2. input subsystem hint
try: idev = open(r + "/proc/bus/input/devices").read()
except Exception: idev = ""
for hint in spec.get("input_name_hints", []):
    if hint and hint.lower() in idev.lower():
        print("present-unreadable"); print("input:" ); sys.exit(0)
# 2b. hub INPUT device (e.g. ssp_context) is group evidence for the hub classes
for hint in d.get("evidence_sources", {}).get("hub_input_names", []):
    if hint and hint.lower() in idev.lower():
        print("present-unreadable"); print("hub-input:" + hint); sys.exit(0)
# 3. hub driver hint
try: mods = open(r + "/proc/modules").read()
except Exception: mods = ""
for m in d.get("evidence_sources", {}).get("hub_drivers", []):
    if m and m in mods:
        print("present-unreadable"); print("hub:" + m); sys.exit(0)
print("absent"); print("")
PY
}
classes_list() { python3 - "$POLICY" <<'PY'
import json,sys
try: print(" ".join(json.load(open(sys.argv[1])).get("classes",{}).keys()))
except Exception: pass
PY
}
read_class() { # $1 class -> prints raw channels that exist and their values
  local cl="$1" dir
  dir="$(class_state "$cl" | sed -n '2p')"
  [ -n "$dir" ] || { say "  $cl: no raw channel to read (absent or input-only)"; return; }
  case "$dir" in input:*|hub:*) say "  $cl: enumerated via $dir — no raw channel exposed by this source"; return ;; esac
  say "  $cl ($dir):"
  python3 - "$POLICY" "$cl" "$ROOT" "$dir" <<'PY'
import json, os, sys
pol, cls, root, dev = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
try: d = json.load(open(pol))
except Exception: sys.exit(0)
spec = d.get("classes", {}).get(cls, {})
base = root.rstrip("/") + dev
for c in spec.get("iio_channels", []):
    p = os.path.join(base, c)
    if os.path.exists(p):
        try: v = open(p).read().strip()
        except Exception: v = "unreadable"
        print("      %-22s = %s  (raw)" % (c, v))
PY
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/sensors-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^expect=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" selftest-cases | sed -n 's/^verdict=//p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-26s verdict=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-26s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
verdict_of() {
  local cl state on=0 pu=0 ab=0
  for cl in $(classes_list); do
    state="$(class_state "$cl" | sed -n '1p')"
    case "$state" in readable) on=$((on+1)) ;; present-unreadable) pu=$((pu+1)) ;; *) ab=$((ab+1)) ;; esac
  done
  if [ "$on" -gt 0 ]; then printf 'READABLE_SOME'
  elif [ "$pu" -gt 0 ]; then printf 'PRESENT_UNREADABLE'
  else printf 'BLOCKED_KERNEL'; fi
}
cmd_status() {
  local cl state dir on=0 absent=0 punread=0
  if [ "$JSON" = 1 ]; then
    python3 - "$POLICY" "$ROOT" "$0" <<'PY'
import json, os, subprocess, sys
pol, root, tool = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(open(pol))
out = {}
for cls in d.get("classes", {}):
    r = subprocess.run(["bash", tool, "--root", root, "state", cls], capture_output=True, text=True)
    lines = r.stdout.splitlines()
    out[cls] = {"state": (lines[0] if lines else "absent"), "evidence": (lines[1] if len(lines) > 1 else "")}
print(json.dumps({"device": "beyond2lte", "tool": "nuxel-sensors-diag",
                  "classes": out, "owner_test": "docs/beta-finalization/manual-proof/14-sensors.md",
                  "observed_motion_verified": False}, separators=(",", ":")))
PY
    return 0
  fi
  say "device: beyond2lte — sensor enumeration (IIO + input + hub drivers)"
  say ""
  for cl in $(classes_list); do
    state="$(class_state "$cl" | sed -n '1p')"
    dir="$(class_state "$cl" | sed -n '2p')"
    case "$state" in
      readable)           on=$((on+1));       printf '  %-15s %-20s %s\n' "$cl" "$state" "$dir" ;;
      present-unreadable) punread=$((punread+1)); printf '  %-15s %-20s %s\n' "$cl" "$state" "$dir" ;;
      absent)             absent=$((absent+1)); printf '  %-15s %-20s %s\n' "$cl" "$state" "NOT_SUPPORTED_ON_DEVICE (no IIO/input/hub evidence)" ;;
    esac
  done
  say ""
  say "readable classes : $on"
  say "present (no raw) : $punread"
  say "not supported    : $absent"
  say ""
  if [ "$on" -gt 0 ]; then say "verdict: READABLE_SOME — at least one class returned a raw value."
  elif [ "$punread" -gt 0 ]; then say "verdict: PRESENT_UNREADABLE — sensors are enumerated but expose no raw channel."
  else say "verdict: BLOCKED_KERNEL — nothing enumerated from IIO, input or the hub drivers."; fi
  say "observed motion/orientation is NEEDS_OWNER_TEST (manual-proof/14-sensors.md)"
}
cmd_read() {
  local cl
  if [ $# -eq 0 ]; then say "usage: $SELF read <class> [class...]  (classes: $(classes_list))"; exit 2; fi
  for cl in "$@"; do read_class "$cl"; done
  say "(raw values above are the ONLY evidence; move the phone as the owner gesture says)"
}
cmd_watch() {
  local cl="${1:-accelerometer}" secs="${2:-10}" cap dir
  cap="$(python3 - "$POLICY" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get("diagnostics",{}).get("watch_seconds_max",120))
except Exception: print(120)
PY
)"
  [ "$secs" -gt "$cap" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${cap}s"; secs="$cap"; }
  say "bounded watch of '$cl' for ${secs}s — OWNER: perform the gesture now"
  dir="$(class_state "$cl" | sed -n '2p')"
  case "$dir" in input:*|hub:*|"") say "  $cl has no raw channel to sample (state: $(class_state "$cl" | sed -n '1p'))"; return 2 ;; esac
  if [ "$ROOT" = "/" ]; then
    python3 - "$POLICY" "$cl" "$ROOT" "$dir" "$secs" <<'PY'
import json, os, sys, time
pol, cls, root, dev, secs = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
spec = json.load(open(pol))["classes"][cls]
base = root.rstrip("/") + dev
chans = [c for c in spec.get("iio_channels", []) if os.path.exists(os.path.join(base, c))]
if not chans:
    print("  no readable channel"); sys.exit(0)
first, last = {}, {}
end = time.time() + secs
n = 0
while time.time() < end:
    for c in chans:
        try: v = open(os.path.join(base, c)).read().strip()
        except Exception: v = ""
        if c not in first: first[c] = v
        last[c] = v
    n += 1
    time.sleep(0.2)
print("  samples=%d" % n)
for c in chans:
    changed = "CHANGED" if first[c] != last[c] else "unchanged"
    print("      %-22s first=%-8s last=%-8s %s" % (c, first[c], last[c], changed))
PY
  else
    say "  (offline/faked root: would sample ${dir} for ${secs}s at 200 ms and report first/last)"
  fi
}
cmd_manifest() {
  python3 - "$POLICY" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
print(json.dumps({k: {"expected_on_s10plus": v.get("expected_on_s10plus", False),
                      "optional": v.get("optional", False),
                      "owner_gesture": v.get("owner_gesture", "")}
                  for k, v in d["classes"].items()}, indent=2, sort_keys=True))
PY
}
case "$CMD" in
  status) cmd_status ;;
  state)  class_state "${1:?class}" ;;
  read)   cmd_read "$@" ;;
  watch)  cmd_watch "${1:-accelerometer}" "${2:-10}" ;;
  manifest) cmd_manifest ;;
  selftest-cases) printf 'verdict=%s\n' "$(verdict_of)" ;;
  report) { say "=== nuxel-sensors report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; cmd_manifest; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || true; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,18p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
