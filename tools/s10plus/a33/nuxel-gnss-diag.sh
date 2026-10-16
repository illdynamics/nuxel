#!/usr/bin/env bash
# nuxel-gnss-diag.sh — S10+ (beyond2lte) GNSS/GPS bring-up diagnostic + offline map check.
#
# Per-stage evidence (device_node -> module -> firmware -> stream -> fix) with the
# FIRST failing stage and a verdict. `monitor` samples the real NMEA stream for a
# bounded time and prints a coordinate ONLY if a position sentence was actually
# decoded — indoor/absent fixes are reported as NO_FIX, never invented.
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_GNSS_POLICY:-/etc/nuxel/gnss/gnss.json}"
MAP="${NUXEL_GNSS_MAP:-/etc/nuxel/gnss/osm-tiles.json}"
LOG="${NUXEL_GNSS_LOG:-/var/log/nuxel/gnss-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; NUM=""
for a in "$@"; do case "$a" in --json) JSON=1 ;; [0-9]*) NUM="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/gnss/gnss.json"
[ -n "$RR" ] && [ ! -r "$MAP" ] && MAP="$RR/configs/nuxel/gnss/osm-tiles.json"
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
stage_node() {
  local d
  for d in $(pol 'evidence_sources.device_nodes'); do [ -e "$(abs "$d")" ] && { printf 'node:%s' "$d"; return; }; done
  if [ -d "$(abs /sys/class/gnss)" ]; then for d in "$(abs /sys/class/gnss)"/*; do [ -e "$d" ] && { printf 'sysfs:%s' "$(basename "$d")"; return; }; done; fi
  if [ -d "$(abs /sys/kernel/debug/gnss)" ]; then for d in "$(abs /sys/kernel/debug/gnss)"/*; do [ -e "$d" ] && { printf 'debug:%s' "$(basename "$d")"; return; }; done; fi
  printf 'absent'
}
stage_module() {
  local m
  [ -r "$(abs /proc/modules)" ] || { printf 'proc-modules-unreadable'; return; }
  for m in $(pol 'evidence_sources.driver_candidates'); do
    grep -q "^$m " "$(abs /proc/modules)" 2>/dev/null && { printf 'loaded:%s' "$m"; return; }
  done
  printf 'none-loaded'
}
stage_firmware() {
  local dir f
  for dir in $(pol 'evidence_sources.firmware_dirs'); do
    for f in $(pol 'evidence_sources.firmware_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && { printf 'found:%s/%s' "$dir" "$f"; return; }
    done
  done
  printf 'missing'
}
stage_stream() {
  local d
  for d in $(pol 'evidence_sources.device_nodes'); do
    [ -r "$(abs "$d")" ] && { printf 'readable:%s' "$d"; return; }
  done
  printf 'unreadable'
}
stage_userspace() {
  local c
  for c in $(pol 'evidence_sources.userspace.client_candidates'); do
    [ -x "$(abs "/usr/bin/$c")" ] && { printf 'client:%s' "$c"; return; }
    [ "$ROOT" = "/" ] && command -v "$c" >/dev/null 2>&1 && { printf 'client:%s' "$c"; return; }
  done
  printf 'no-consumer'
}
verdict() { # node module firmware stream
  case "$1" in absent) printf 'BLOCKED_KERNEL' ;;
    *) case "$2" in none-loaded) printf 'PARTIAL' ;;
       *) case "$3" in missing) printf 'BLOCKED_FIRMWARE' ;;
          *) case "$4" in readable:*) printf 'READY_FOR_SKY' ;; *) printf 'BLOCKED_KERNEL' ;; esac ;; esac ;; esac ;;
  esac
}
first_failing() {
  case "$1" in absent) printf 'device_node' ;; *) case "$2" in none-loaded) printf 'module' ;;
    *) case "$3" in missing) printf 'firmware' ;; *) case "$4" in readable:*) printf 'fix' ;; *) printf 'stream' ;; esac ;; esac ;; esac ;; esac
}
cmd_status() {
  local n m f s u v ff
  n="$(stage_node)"; m="$(stage_module)"; f="$(stage_firmware)"; s="$(stage_stream)"; u="$(stage_userspace)"
  v="$(verdict "$n" "$m" "$f" "$s")"; ff="$(first_failing "$n" "$m" "$f" "$s")"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-gnss-diag","stages":{"device_node":"%s","module":"%s","firmware":"%s","stream":"%s","userspace":"%s"},"first_failing_stage":"%s","state":"%s","fix_verified":false,"owner_test":"docs/beta-finalization/manual-proof/13-gps.md"}\n' \
      "$(jesc "$n")" "$(jesc "$m")" "$(jesc "$f")" "$(jesc "$s")" "$(jesc "$u")" "$ff" "$v"
    return 0
  fi
  say "device : beyond2lte   GNSS : Exynos 9820 integrated path (vendor-assisted)"
  say ""
  say "stages:"
  say "  device_node : $n"
  say "  module      : $m"
  say "  firmware    : $f"
  say "  stream      : $s"
  say "  userspace   : $u"
  say ""
  say "first failing stage : $ff"
  say "verdict             : $v"
  case "$v" in
    READY_FOR_SKY) say "  a readable stream exists. A fix is NEEDS_OWNER_TEST and can only be observed"
                   say "  OUTDOORS: run 'nuxel-gnss-diag.sh monitor 180' with a clear sky view." ;;
    BLOCKED_KERNEL) say "  no GNSS node/module bound on this kernel. Offline driver work; no coordinate"
                    say "  will ever be invented here." ;;
    BLOCKED_FIRMWARE) say "  driver/node present but no GNSS firmware blob. Deploy into /lib/firmware/gnss"
                      say "  (repository-only); never a partition write." ;;
    PARTIAL) say "  read the per-stage lines; a node without a module is not a working receiver." ;;
  esac
}
cmd_firmware() {
  local dir f
  say "GNSS firmware candidate inventory:"
  for dir in $(pol 'evidence_sources.firmware_dirs'); do
    say "  $dir:"
    for f in $(pol 'evidence_sources.firmware_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && say "    FOUND  $f" || say "    -      $f"
    done
  done
}
cmd_stream() {
  local secs="${1:-10}" cap node
  cap="$(pol 'diagnostics.monitor_seconds_max')"; cap="${cap:-600}"
  [ "$secs" -gt "$cap" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${cap}s"; secs="$cap"; }
  node="$(stage_node)"
  case "$node" in node:*) : ;; *) say "no readable GNSS device node ($node) — nothing to sample"; return 2 ;; esac
  say "bounded NMEA sample for ${secs}s from ${node#node:}"
  if [ "$ROOT" = "/" ]; then
    local t="0"; local counts=""
    # Consume the real stream; count only sentences we actually saw.
    timeout "$secs" cat "${node#node:}" 2>/dev/null | head -200 | \
      grep -E '^\$(GP|GN|GL|GA|BD)' | sort | uniq -c | sort -rn | sed 's/^/  /' || true
    say "  (counts above are the ONLY evidence; no coordinate is printed by 'stream')"
  else
    say "  (offline/faked root: would read ${node#node:} for ${secs}s and count NMEA sentences;"
    say "   no coordinate is fabricated by this command)"
  fi
}
cmd_monitor() {
  local secs="${1:-180}" cap node fix=""
  cap="$(pol 'diagnostics.monitor_seconds_max')"; cap="${cap:-600}"
  [ "$secs" -gt "$cap" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${cap}s"; secs="$cap"; }
  node="$(stage_node)"
  case "$node" in node:*) : ;; *) say "no readable GNSS device node ($node) — cannot monitor"; return 2 ;; esac
  say "bounded fix monitor for ${secs}s (OWNER: this must be done OUTDOORS with a clear sky view)"
  if [ "$ROOT" = "/" ]; then
    fix="$(timeout "$secs" cat "${node#node:}" 2>/dev/null | grep -E '^\$(GP|GN)GGA' | grep -v ',0,,' | grep -E ',(1|2|4|5),' | head -1 || true)"
    if [ -n "$fix" ]; then
      say "decoded position sentence:"
      say "  $fix"
      say "  (parse lat/lon per NMEA 0183 and compare with the offline map before marking PASS)"
    else
      say "NO_FIX: no position sentence with a non-empty lat/lon and fix quality >= 1 was"
      say "observed in ${secs}s. Indoors this is the expected result, not a failure of the"
      say "repository. Re-run outdoors; after three indoor attempts, change strategy (do"
      say "NOT repeat the same indoor run)."
    fi
  else
    say "  (offline/faked root: would read ${node#node:} for ${secs}s and decode \$..GGA only"
    say "   if a real fix sentence appeared; no coordinate is fabricated)"
  fi
}
cmd_map() {
  python3 - "$MAP" <<'PY'
import json, os, sys
p = sys.argv[1]
try: d = json.load(open(p))
except Exception as e:
    print("osm-tiles.json unreadable (%s)" % e); sys.exit(0)
print("offline-first OSM contract (attribution: %s)" % d["attribution"])
t = d["tiles"]
print("  tile layout   : %s (zoom %s..%s, %dpx rasters)" % (t["layout"], t["min_zoom"], t["max_zoom"], t["tile_size_px"]))
for d0 in t["search_order"]:
    n = 0
    if os.path.isdir(d0):
        for _root, _dirs, files in os.walk(d0):
            n += len(files)
    print("  %-38s %s" % (d0, ("%d tile files" % n) if os.path.isdir(d0) else "not present"))
print("  network optional: %s ; cached area must load offline: %s"
      % (d["network"]["optional"], d["offline_first"]["requires_network_for_cached_area"] is False))
print("  no fixed coordinate in the repository: %s" % d["geolocation"]["no_fixed_coordinate_in_repo"])
PY
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/gnss-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-28s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-28s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  firmware) cmd_firmware ;;
  stream) cmd_stream "${NUM:-10}" ;;
  monitor) cmd_monitor "${NUM:-180}" ;;
  map) cmd_map ;;
  report) { say "=== nuxel-gnss report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; cmd_firmware; cmd_map; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || true; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,20p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
