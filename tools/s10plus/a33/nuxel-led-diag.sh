#!/usr/bin/env bash
# nuxel-led-diag.sh — S10+ (beyond2lte) flashlight / notification-LED / edge-lighting tool.
#
# WHAT THIS IS
#   A control + diagnostic that REPORTS which LED classes the hardware actually
#   exposes (flashlight, notification, edge lighting) and their real sysfs paths,
#   can turn the torch on for a bounded time on an explicit owner command, and
#   can force an explicit OFF for every class it found.
#
# WHAT THIS IS NOT
#   It never claims a class exists that does not (absent => NOT_SUPPORTED_ON_DEVICE),
#   never turns anything on at boot or automatically, and never models the S10+'s
#   software "edge lighting" as a hardware LED. Nothing here touches a partition,
#   a block device or a bootloader.
#
# Usage:
#   nuxel-led-diag.sh status [--json]
#   nuxel-led-diag.sh flash --yes <ms>     # torch, bounded by policy max_on_ms
#   nuxel-led-diag.sh off                  # explicit OFF for every class found
#   nuxel-led-diag.sh notify <colour>      # notification LED colour/blink, if present
#   nuxel-led-diag.sh report
#   nuxel-led-diag.sh selftest
set -uo pipefail
SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_LED_POLICY:-/etc/nuxel/leds/leds.json}"
LOG="${NUXEL_LED_LOG:-/var/log/nuxel/led-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
YES=0; JSON=0; NUM=""; COLOUR="red"
for a in "$@"; do case "$a" in --yes) YES=1 ;; --json) JSON=1 ;; [0-9]*) NUM="$a" ;; red|green|blue|white|amber) COLOUR="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/leds/leds.json"
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
policy_get() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    cur = cur.get(k) if isinstance(cur,dict) else None
print("" if cur is None else cur)
PY
}
find_class() { # $1 = class name -> prints real path (no root prefix) or nothing
  python3 - "$POLICY" "$1" "$ROOT" <<'PY'
import glob, json, os, sys
pol, cls, root = sys.argv[1], sys.argv[2], sys.argv[3]
try: d = json.load(open(pol))
except Exception: sys.exit(0)
spec = d.get("classes", {}).get(cls, {})
for c in spec.get("candidates", []):
    p = root.rstrip("/") + c
    if os.path.isdir(p): print(c); sys.exit(0)
for g in spec.get("globs", []):
    for p in sorted(glob.glob(root.rstrip("/") + g)):
        if os.path.isdir(p): print(p[len(root.rstrip("/")):]); sys.exit(0)
PY
}
writable_of() { # $1 class, $2 path -> first writable write file
  local f
  for f in $(python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: print(" ".join(json.load(open(sys.argv[1])).get("classes",{}).get(sys.argv[2],{}).get("write_files",[])))
except Exception: pass
PY
); do [ -w "$(abs "$2/$f")" ] && { printf '%s' "$f"; return; }; done
}
is_on() { # $1 path -> yes when brightness > 0
  local b; b="$(cat "$(abs "$1/brightness")" 2>/dev/null | tr -d '\r\n')"
  [ -n "$b" ] && [ "$b" -gt 0 ] 2>/dev/null && printf yes || printf no
}
set_off() { local p="$1" f; for f in brightness; do [ -w "$(abs "$p/$f")" ] && printf '0' > "$(abs "$p/$f")" 2>/dev/null || true; done; }

collect() { # prints "class=path" lines for present classes
  local c p
  for c in flashlight notification; do
    p="$(find_class "$c")"
    [ -n "$p" ] && printf '%s=%s\n' "$c" "$p"
  done
}
cmd_status() {
  local fp np on_f on_n
  fp="$(find_class flashlight)"; np="$(find_class notification)"
  on_f=$([ -n "$fp" ] && is_on "$fp" || printf no)
  on_n=$([ -n "$np" ] && is_on "$np" && printf yes || printf no)
  local maxon; maxon="$(policy_get safety.max_on_ms)"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-led-diag","classes":{"flashlight":{"present":%s,"path":"%s","on":%s,"state":"%s"},"notification":{"present":%s,"path":"%s","on":%s,"state":"%s"},"edge_lighting":{"present":false,"kind":"display_overlay","hardware_led":false,"state":"NOT_SUPPORTED_ON_DEVICE_AS_LED"}},"flashlight_verified":false,"owner_test":"docs/beta-finalization/manual-proof/09-flashlight.md","max_on_ms":%s}\n' \
      "$([ -n "$fp" ] && printf true || printf false)" "$(jesc "$fp")" "$([ "$on_f" = yes ] && printf true || printf false)" \
      "$([ -n "$fp" ] && printf OK || printf NOT_SUPPORTED_ON_DEVICE)" \
      "$([ -n "$np" ] && printf true || printf false)" "$(jesc "$np")" "$([ "$on_n" = yes ] && printf true || printf false)" \
      "$([ -n "$np" ] && printf OK || printf NOT_SUPPORTED_ON_DEVICE)" "${maxon:-60000}"
    return 0
  fi
  say "device: beyond2lte"
  say ""
  say "LED classes (enumerated, not assumed):"
  if [ -n "$fp" ]; then
    say "  flashlight     : $fp"
    say "                   state=${on_f}; writable=$(writable_of flashlight "$fp"); 'off' forces brightness 0"
  else
    say "  flashlight     : NOT_SUPPORTED_ON_DEVICE (no torch/flash LED class bound)"
  fi
  if [ -n "$np" ]; then
    say "  notification   : $np"
    say "                   state=${on_n}; writable=$(writable_of notification "$np")"
  else
    say "  notification   : NOT_SUPPORTED_ON_DEVICE (no notification LED class bound; the"
    say "                   notifier must fall back to the display overlay instead)"
  fi
  say "  edge_lighting  : NOT_SUPPORTED_ON_DEVICE_AS_LED — the S10+ has no edge-lighting"
  say "                   LED; Samsung's effect is a DISPLAY overlay on the curved AMOLED"
  say "                   and depends on the display bridge (nuxel-wl-fb)."
  say ""
  say "safety         : torch ON is capped at ${maxon:-60000} ms, requires --yes, forced OFF on exit"
  say "auto-on        : none at boot (safety.auto_on_boot=false)"
  say "verdict        : $([ -n "$fp" ] || [ -n "$np" ] && printf 'OFFLINE_TESTED (control) / NEEDS_OWNER_TEST (visible light)' || printf NOT_SUPPORTED_ON_DEVICE)"
}
cmd_flash() {
  local fp; fp="$(find_class flashlight)"
  [ -n "$fp" ] || { say "refused: no flashlight/torch LED class bound (NOT_SUPPORTED_ON_DEVICE)"; return 2; }
  [ "$YES" = 1 ] || { say "refused: lighting the torch is an owner action. Re-run: $SELF flash --yes 3000"; return 4; }
  local ms="${NUM:-3000}" maxon; maxon="$(policy_get safety.max_on_ms)"; maxon="${maxon:-60000}"
  [ "$ms" -gt "$maxon" ] 2>/dev/null && { say "capping ${ms} ms to the policy maximum ${maxon} ms"; ms="$maxon"; }
  local f; f="$(writable_of flashlight "$fp")"
  [ -n "$f" ] || { say "refused: $fp exposes no writable file (PARTIAL)"; return 5; }
  say "torch ON via $fp/$f for ${ms} ms (bounded; forced OFF at the end)"
  printf '255' > "$(abs "$fp/$f")" 2>/dev/null || printf '1' > "$(abs "$fp/$f")" 2>/dev/null || true
  local w=$(( ms / 1000 )); [ "$w" -lt 1 ] && w=1
  sleep "$w"
  set_off "$fp"
  say "torch OFF. Did you see the light? Record PASS/FAIL in manual-proof/09-flashlight.md"
}
cmd_off() {
  local n=0 p
  while IFS= read -r line; do
    p="${line#*=}"; [ -n "$p" ] || continue
    set_off "$p"; n=$((n+1))
  done < <(collect)
  # Belt and braces: any *torch*/*flash*/*notif* class under the faked /sys root.
  for p in "$(abs /sys/class/leds)"/*torch* "$(abs /sys/class/leds)"/*flash* "$(abs /sys/class/leds)"/*notif*; do
    [ -d "$p" ] || continue
    [ -w "$p/brightness" ] && printf '0' > "$p/brightness" 2>/dev/null && n=$((n+1))
  done
  say "explicit OFF applied to $n LED node(s); none will be switched on again at boot"
}
cmd_notify() {
  local np; np="$(find_class notification)"
  [ -n "$np" ] || { say "notification LED class NOT_SUPPORTED_ON_DEVICE — use the display overlay path instead"; return 2; }
  local f; f="$(writable_of notification "$np")"
  say "notification LED $np ($COLOUR) via $f — 3 s, then OFF"
  printf '255' > "$(abs "$np/$f")" 2>/dev/null || true
  sleep 3
  set_off "$np"
  say "notification LED OFF"
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got jf
  for f in "$fixdir"/leds-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); jf="$f/EXPECTED"
    exp="$(sed -n 's/^flashlight=//p' "$jf" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | python3 -c 'import json,sys
try: print("present" if json.load(sys.stdin)["classes"]["flashlight"]["present"] else "absent")
except Exception: print("parse-error")')"
    if [ "$exp" = "$got" ]; then printf 'PASS %-26s flashlight=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-26s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  flash) cmd_flash ;;
  off) cmd_off ;;
  notify) cmd_notify ;;
  report) { say "=== nuxel-led report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || true; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,26p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
