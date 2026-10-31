#!/usr/bin/env bash
# nuxel-gnss-diag.sh — S10+ (beyond2lte) GNSS/GPS bring-up diagnostic + offline map check.
#
# The S10+ GNSS receiver is a BCM4773 behind Broadcom BBD/LHD RPC:
#   /dev/ttyBCM        BBD packet transport (NOT an NMEA serial port)
#   /dev/bbd_patch     sensor-hub patch loader used by the vendor lhd daemon
#   /vendor/bin/hw/lhd Android/Bionic location-hub daemon
#   /vendor/bin/hw/gpsd Android/Bionic GNSS daemon
# Stages stop at the FIRST genuine failure. A node, an SPI binding, an SPI
# register response or raw BBD bytes are never promoted to a position fix.
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
if isinstance(cur,list): print("\n".join(str(x) for x in cur))
elif cur is not None: print(cur)
PY
}
lookup_paths() { # print existing candidate paths from a policy key
  local p
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    case "$p" in /*) [ -e "$(abs "$p")" ] && printf '%s' "$p" ;; esac
  done < <(pol "$1")
}
stage_node() {
  local d
  for d in $(pol 'evidence_sources.device_nodes'); do
    if [ -e "$(abs "$d")" ]; then printf 'node:%s' "$d"; return; fi
  done
  if [ -d "$(abs /sys/class/gnss)" ]; then for d in "$(abs /sys/class/gnss)"/*; do [ -e "$d" ] && { printf 'sysfs:%s' "$(basename "$d")"; return; }; done; fi
  if [ -d "$(abs /sys/kernel/debug/gnss)" ]; then for d in "$(abs /sys/kernel/debug/gnss)"/*; do [ -e "$d" ] && { printf 'debug:%s' "$(basename "$d")"; return; }; done; fi
  printf 'absent'
}
stage_module() {
  local m d g
  # A driver can be built in and bound through sysfs without appearing in
  # /proc/modules.  The BCM4773 GPS driver directory contains a literal space.
  for d in $(pol 'evidence_sources.driver_bindings'); do
    [ -e "$(abs "$d")" ] && { printf 'bound:%s' "$d"; return; }
  done
  d="$(abs "/sys/bus/spi/drivers/brcm gps spi/spi17.0")"
  [ -e "$d" ] && { printf 'bound:%s' "/sys/bus/spi/drivers/brcm gps spi/spi17.0"; return; }
  for g in $(pol 'evidence_sources.driver_globs'); do
    case "$g" in /*) ;; *) continue ;; esac
    for d in "$(abs "$g")"; do [ -e "$d" ] && { printf 'bound:%s' "${d#"$ROOT"}"; return; }; done
  done
  [ -r "$(abs /proc/modules)" ] || { printf 'proc-modules-unreadable'; return; }
  for m in $(pol 'evidence_sources.driver_candidates'); do
    grep -q "^$m " "$(abs /proc/modules)" 2>/dev/null && { printf 'loaded:%s' "$m"; return; }
  done
  printf 'none-loaded'
}
is_bbd() { # node module
  case "$1" in node:/dev/ttyBCM|node:/dev/bbd_sensor) return 0 ;; esac
  case "$2" in *'brcm gps spi'*|*ssp_bcm4773*) return 0 ;; esac
  return 1
}
stage_firmware() { # protocol
  local dir f p
  # Device-specific BBD patch firmware first.  A loader device node
  # (/dev/bbd_patch) is NOT firmware; only a real patch file counts.
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    case "$p" in /dev/*) continue ;; esac
    [ -f "$(abs "$p")" ] && { printf 'found:%s' "$p"; return; }
  done < <(pol 'evidence_sources.firmware_device_candidates')
  for dir in $(pol 'evidence_sources.firmware_dirs'); do
    for f in $(pol 'evidence_sources.firmware_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && { printf 'found:%s/%s' "$dir" "$f"; return; }
    done
  done
  [ -e "$(abs /dev/bbd_patch)" ] && { printf 'loader-only:/dev/bbd_patch'; return; }
  printf 'missing'
}
stage_vendor_runtime() {
  local key path present=() missing=()
  for key in lhd gpsd android_linker lhd_config gps_config gnss_hidl_impl; do
    local found=0
    while IFS= read -r path; do
      [ -n "$path" ] || continue
      case "$path" in /*) [ -e "$(abs "$path")" ] && found=1 ;; esac
    done < <(pol "evidence_sources.vendor_runtime.$key")
    if [ "$found" = 1 ]; then present+=("$key"); else missing+=("$key"); fi
  done
  if [ "${#missing[@]}" -eq 0 ]; then printf 'complete'; else printf 'missing:%s' "$(IFS=,; printf '%s' "${missing[*]}")"; fi
}
stage_stream() { # protocol
  local d
  if [ "$1" = "bbd" ]; then
    for d in /dev/ttyBCM /dev/bbd_sensor; do
      [ -e "$(abs "$d")" ] && { printf 'bbd-transport:%s' "$d"; return; }
    done
    printf 'no-bbd-transport'
    return
  fi
  for d in $(pol 'evidence_sources.device_nodes'); do
    [ -r "$(abs "$d")" ] && { printf 'readable:%s' "$d"; return; }
  done
  printf 'unreadable'
}
stage_userspace() { # protocol
  local c
  if [ "$1" = "bbd" ]; then
    if [ "$(stage_vendor_runtime)" = "complete" ]; then printf 'android-vendor-runtime'; return; fi
    printf 'no-native-bbd-lhd-decoder'
    return
  fi
  for c in $(pol 'evidence_sources.userspace.client_candidates'); do
    [ -x "$(abs "/usr/bin/$c")" ] && { printf 'client:%s' "$c"; return; }
    [ "$ROOT" = "/" ] && command -v "$c" >/dev/null 2>&1 && { printf 'client:%s' "$c"; return; }
  done
  printf 'no-consumer'
}
verdict() { # node module firmware userspace stream protocol
  local n="$1" m="$2" f="$3" u="$4" s="$5" p="$6"
  case "$n" in absent) printf 'BLOCKED_KERNEL'; return ;; esac
  case "$m" in none-loaded) printf 'PARTIAL'; return ;; esac
  case "$f" in missing|loader-only:*) printf 'BLOCKED_FIRMWARE'; return ;; esac
  if [ "$p" = bbd ]; then
    case "$u" in
      no-native-bbd-lhd-decoder) printf 'BLOCKED_PROTOCOL' ;;
      android-vendor-runtime) case "$s" in bbd-transport:*) printf 'READY_FOR_SKY' ;; *) printf 'BLOCKED_PROTOCOL' ;; esac ;;
      *) printf 'BLOCKED_PROTOCOL' ;;
    esac
    return
  fi
  case "$u" in no-consumer) printf 'BLOCKED_EXTERNAL_RESOURCE' ;; *) printf 'READY_FOR_SKY' ;; esac
}
first_failing() { # node module firmware userspace protocol
  local n="$1" m="$2" f="$3" u="$4" p="$5"
  case "$n" in absent) printf 'device_node'; return ;; esac
  case "$m" in none-loaded) printf 'module'; return ;; esac
  case "$f" in missing|loader-only:*) printf 'firmware'; return ;; esac
  if [ "$p" = bbd ]; then
    case "$u" in no-native-bbd-lhd-decoder|no-consumer) printf 'userspace'; return ;; esac
  else
    case "$u" in no-consumer) printf 'userspace'; return ;; esac
  fi
  printf 'fix'
}
protocol_of() { if is_bbd "$1" "$2"; then printf bbd; else printf generic; fi; }
cmd_status() {
  local n m f u s p v ff
  n="$(stage_node)"; m="$(stage_module)"; p="$(protocol_of "$n" "$m")"
  f="$(stage_firmware "$p")"; u="$(stage_userspace "$p")"; s="$(stage_stream "$p")"
  v="$(verdict "$n" "$m" "$f" "$u" "$s" "$p")"; ff="$(first_failing "$n" "$m" "$f" "$u" "$p")"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-gnss-diag","protocol":"%s","stages":{"device_node":"%s","module":"%s","firmware":"%s","vendor_runtime":"%s","userspace":"%s","stream":"%s"},"first_failing_stage":"%s","state":"%s","fix_verified":false,"nmea_stream":%s,"owner_test":"docs/beta-finalization/manual-proof/13-gps.md"}\n' \
      "$p" "$(jesc "$n")" "$(jesc "$m")" "$(jesc "$f")" "$(jesc "$(stage_vendor_runtime)")" "$(jesc "$u")" "$(jesc "$s")" "$ff" "$v" "$([ "$p" = generic ] && printf true || printf false)"
    return 0
  fi
  if [ "$p" = bbd ]; then
    say "device : beyond2lte   GNSS : BCM4773 (Broadcom BBD/LHD RPC, not NMEA)"
  else
    say "device : beyond2lte   GNSS : generic kernel GNSS path"
  fi
  say ""
  say "stages:"
  say "  device_node   : $n"
  say "  module        : $m"
  say "  firmware      : $f"
  say "  vendor_runtime: $(stage_vendor_runtime)"
  say "  userspace     : $u"
  say "  stream        : $s"
  say ""
  say "first failing stage : $ff"
  say "verdict             : $v"
  case "$v" in
    READY_FOR_SKY)
      if [ "$p" = bbd ]; then
        say "  the BBD/LHD provider path is present. A fix remains NEEDS_OWNER_TEST and"
        say "  must be observed OUTDOORS via the real provider (not by cat/grep on ttyBCM)."
      else
        say "  a readable stream exists. A fix is NEEDS_OWNER_TEST and can only be observed"
        say "  OUTDOORS: run 'nuxel-gnss-diag.sh monitor 180' with a clear sky view."
      fi ;;
    BLOCKED_KERNEL) say "  no GNSS node/driver bound on this kernel; no coordinate is invented here." ;;
    BLOCKED_FIRMWARE)
      say "  driver/node present but no compatible BCM4773 BBD sensor-hub patch firmware."
      say "  /dev/bbd_patch is only a loader node, not firmware. Do not rename an unrelated blob." ;;
    BLOCKED_PROTOCOL)
      say "  BBD/LHD transport exists but no compatible userspace decoder is wired."
      say "  Stock Linux gpsd cannot decode BBD/LHD; the vendor lhd+gpsd pair is Android/Bionic." ;;
    BLOCKED_EXTERNAL_RESOURCE)
      say "  the receiver path exists but no compatible userspace consumer is installed." ;;
    PARTIAL) say "  read the per-stage lines; a node without a driven module is not a receiver." ;;
  esac
}
cmd_firmware() {
  local dir f p
  say "GNSS firmware candidate inventory (device-specific BBD first):"
  if [ "$(protocol_of "$(stage_node)" "$(stage_module)")" = bbd ]; then
    say "  BBD/LHD patch candidates:"
    while IFS= read -r p; do [ -n "$p" ] && say "    -      $p"; done < <(pol 'evidence_sources.firmware_device_candidates')
    say "  note: $(pol 'evidence_sources.firmware_absent_reason')"
  fi
  for dir in $(pol 'evidence_sources.firmware_dirs'); do
    say "  $dir:"
    for f in $(pol 'evidence_sources.firmware_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && say "    FOUND  $f" || say "    -      $f"
    done
  done
}
cmd_stream() {
  local secs="${1:-10}" cap node p
  cap="$(pol 'diagnostics.monitor_seconds_max')"; cap="${cap:-600}"
  [ "$secs" -gt "$cap" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${cap}s"; secs="$cap"; }
  node="$(stage_node)"; p="$(protocol_of "$node" "$(stage_module)")"
  case "$node" in node:*) : ;; *) say "no readable GNSS device node ($node) — nothing to sample"; return 2 ;; esac
  if [ "$p" = bbd ]; then
    if [ "$ROOT" != "/" ]; then
      say "BBD/LHD fixture: ${node#node:} is a BBD RPC transport, not NMEA; no coordinate is fabricated"
      return 0
    fi
    say "REFUSING NMEA interpretation of ${node#node:}: the BCM4773 uses BBD/LHD RPC."
    say "Use a compatible BBD/LHD provider. Raw bytes/SPI responses are not a fix; no coordinate is fabricated."
    return 3
  fi
  say "bounded NMEA sample for ${secs}s from ${node#node:}"
  if [ "$ROOT" = "/" ]; then
    timeout "$secs" cat "${node#node:}" 2>/dev/null | head -200 | \
      grep -E '^\$(GP|GN|GL|GA|BD)' | sort | uniq -c | sort -rn | sed 's/^/  /' || true
    say "  (counts above are the ONLY evidence; no coordinate is printed by 'stream')"
  else
    say "  (offline/faked root: would read ${node#node:} for ${secs}s; no coordinate is fabricated)"
  fi
}
cmd_monitor() {
  local secs="${1:-180}" cap node p fix=""
  cap="$(pol 'diagnostics.monitor_seconds_max')"; cap="${cap:-600}"
  [ "$secs" -gt "$cap" ] 2>/dev/null && { say "capping ${secs}s to the policy maximum ${cap}s"; secs="$cap"; }
  node="$(stage_node)"; p="$(protocol_of "$node" "$(stage_module)")"
  case "$node" in node:*) : ;; *) say "no readable GNSS device node ($node) — cannot monitor"; return 2 ;; esac
  if [ "$p" = bbd ]; then
    if [ "$ROOT" != "/" ]; then
      say "BBD/LHD fixture: a fix cannot be decoded by NMEA parsing; no coordinate is fabricated"
      return 0
    fi
    say "BBD/LHD device: this diagnostic cannot decode the Broadcom RPC protocol."
    say "Start the compatible provider and observe its provider timestamp/source outdoors."
    say "NO_FIX claimed; no coordinate is fabricated."
    return 3
  fi
  say "bounded fix monitor for ${secs}s (OWNER: this must be done OUTDOORS with a clear sky view)"
  if [ "$ROOT" = "/" ]; then
    fix="$(timeout "$secs" cat "${node#node:}" 2>/dev/null | grep -E '^\$(GP|GN)GGA' | grep -v ',0,,' | grep -E ',(1|2|4|5),' | head -1 || true)"
    if [ -n "$fix" ]; then
      say "decoded position sentence:"
      say "  $fix"
      say "  (parse lat/lon per NMEA 0183 and compare with the offline map before marking PASS)"
    else
      say "NO_FIX: no position sentence with a non-empty lat/lon and fix quality >= 1 was"
      say "observed in ${secs}s. Indoors this is expected; re-run outdoors."
    fi
  else
    say "  (offline/faked root: would read ${node#node:} for ${secs}s; no coordinate is fabricated)"
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
  help|-h|--help) sed -n '2,16p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
