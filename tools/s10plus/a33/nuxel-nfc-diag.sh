#!/usr/bin/env bash
# nuxel-nfc-diag.sh — S10+ (beyond2lte) NFC bring-up diagnostic.
#
# Per-stage evidence for the Samsung sec-nfc (S3FWRN5-family, I2C 0x27)
# controller and the FIRST failing stage: controller -> firmware -> subsystem ->
# stack -> tag. Configuration alone is NEVER a working NFC and no UID is ever
# fabricated; a physical tag read by the owner is NEEDS_OWNER_TEST.
set -uo pipefail
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_NFC_POLICY:-/etc/nuxel/nfc/nfc.json}"
LOG="${NUXEL_NFC_LOG:-/var/log/nuxel/nfc-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do case "$1" in
  --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;; *) ARGS+=("$1"); shift ;; esac; done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; NUM=""
for a in "$@"; do case "$a" in --json) JSON=1 ;; [0-9]*) NUM="$a" ;; esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/nfc/nfc.json"
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
stage_controller() {
  local d mod
  if [ -r "$(abs /proc/modules)" ]; then
    for mod in $(pol 'evidence_sources.driver_candidates'); do
      grep -q "^$mod " "$(abs /proc/modules)" 2>/dev/null && { printf 'module:%s' "$mod"; return; }
    done
  fi
  for d in $(pol 'evidence_sources.char_devices'); do [ -e "$(abs "$d")" ] && { printf 'chardev:%s' "$d"; return; }; done
  if [ -d "$(abs /sys/class/nfc)" ]; then
    for d in "$(abs /sys/class/nfc)"/*; do [ -e "$d" ] && { printf 'sysfs:%s' "$(basename "$d")"; return; }; done
  fi
  # i2c address hint (0x27) reported as the weakest form of evidence
  if [ -d "$(abs /sys/bus/i2c/devices)" ]; then
    for d in "$(abs /sys/bus/i2c/devices)"/*; do
      case "$(basename "$d")" in *27|*-0027|*0x27*) printf 'i2c-hint:%s' "$(basename "$d")"; return;; esac
    done
  fi
  printf 'absent'
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
stage_subsystem() { # kernel NFC subsystem: netlink class or /dev/nfcN
  local d
  [ -d "$(abs /sys/class/nfc)" ] && { for d in "$(abs /sys/class/nfc)"/*; do [ -e "$d" ] && { printf 'up:%s' "$(basename "$d")"; return; }; done; }
  for d in /dev/nfc0 /dev/nfc; do [ -e "$(abs "$d")" ] && { printf 'up:%s' "$d"; return; }; done
  printf 'down'
}
stage_stack() {
  local c
  for c in $(pol 'evidence_sources.stack.client_candidates'); do
    if [ -x "$(abs "/usr/bin/$c")" ] || [ -x "$(abs "/usr/sbin/$c")" ]; then printf 'client:%s' "$c"; return; fi
    [ "$ROOT" = "/" ] && command -v "$c" >/dev/null 2>&1 && { printf 'client:%s' "$c"; return; }
  done
  for c in $(pol 'evidence_sources.stack.daemon_candidates'); do
    [ -e "$(abs "/usr/lib/systemd/system/$c")" ] || [ -e "$(abs "/etc/systemd/system/$c")" ] && { printf 'daemon-unit:%s' "$c"; return; }
  done
  printf 'no-stack'
}
verdict() { # controller firmware subsystem stack
  case "$1" in absent) printf 'BLOCKED_KERNEL' ;;
    *) case "$2" in missing) printf 'BLOCKED_FIRMWARE' ;;
       *) case "$3" in down) printf 'BLOCKED_KERNEL' ;;
          *) case "$4" in no-stack) printf 'BLOCKED_EXTERNAL_RESOURCE' ;; *) printf 'READY_FOR_TAG' ;; esac ;; esac ;; esac ;;
  esac
}
first_failing() {
  case "$1" in absent) printf 'controller' ;; *) case "$2" in missing) printf 'firmware' ;;
    *) case "$3" in down) printf 'subsystem' ;; *) case "$4" in no-stack) printf 'stack' ;; *) printf 'tag' ;; esac ;; esac ;; esac ;; esac
}
cmd_status() {
  local c f s st v ff
  c="$(stage_controller)"; f="$(stage_firmware)"; s="$(stage_subsystem)"; st="$(stage_stack)"
  v="$(verdict "$c" "$f" "$s" "$st")"; ff="$(first_failing "$c" "$f" "$s" "$st")"
  if [ "$JSON" = 1 ]; then
    printf '{"device":"beyond2lte","tool":"nuxel-nfc-diag","stages":{"controller":"%s","firmware":"%s","subsystem":"%s","stack":"%s"},"first_failing_stage":"%s","state":"%s","tag_read_verified":false,"owner_test":"docs/beta-finalization/manual-proof/12-nfc.md"}\n' \
      "$(jesc "$c")" "$(jesc "$f")" "$(jesc "$s")" "$(jesc "$st")" "$ff" "$v"
    return 0
  fi
  say "device   : beyond2lte   controller : sec-nfc (S3FWRN5-family) @ I2C 0x27 + eSE"
  say ""
  say "stages:"
  say "  controller : $c"
  say "  firmware   : $f"
  say "  subsystem  : $s   (kernel NFC class / netlink)"
  say "  stack      : $st"
  say ""
  say "first failing stage : $ff"
  say "verdict             : $v"
  case "$v" in
    READY_FOR_TAG) say "  kernel + userspace look usable. NFC is STILL NEEDS_OWNER_TEST: a physical tag"
                   say "  must be tapped and its UID must match. Record it in manual-proof/12-nfc.md." ;;
    BLOCKED_KERNEL) say "  no controller/module bound on this kernel. This is where the honest reporting"
                    say "  ends: the vendor kernel may simply not expose the controller (NOT_SUPPORTED_ON_DEVICE"
                    say "  if no supported path exists). No UID is fabricated." ;;
    BLOCKED_FIRMWARE) say "  controller/module path present but no NFC firmware blob found. Deploy into"
                      say "  /lib/firmware/nfc (repository-only); never a partition write." ;;
    BLOCKED_EXTERNAL_RESOURCE) say "  kernel NFC up but no userspace stack (neard/nfc-list) is installed." ;;
    PARTIAL) say "  read the per-stage lines; do not guess." ;;
  esac
}
cmd_firmware() {
  local dir f
  say "NFC firmware candidate inventory:"
  for dir in $(pol 'evidence_sources.firmware_dirs'); do
    say "  $dir:"
    for f in $(pol 'evidence_sources.firmware_candidates'); do
      [ -f "$(abs "$dir/$f")" ] && say "    FOUND  $f" || say "    -      $f"
    done
  done
}
cmd_read() {
  local secs="${1:-15}" t
  t="$(pol 'diagnostics.read_timeout_s')"; [ -n "${NUM:-}" ] && secs="$NUM"
  say "bounded NFC read: ${secs}s (owner action). Place the tag flat on the upper back of the phone."
  if [ "$ROOT" = "/" ]; then
    for c in nfc-list nfc-emulate-forum-tag4; do
      if command -v "$c" >/dev/null 2>&1; then
        [ "$c" = nfc-list ] && { timeout "$secs" "$c" 2>&1 | sed 's/^/  /' || true; return; }
      fi
    done
    say "  no nfc-list client installed (BLOCKED_EXTERNAL_RESOURCE) — nothing to run"
  else
    say "  (offline/faked root: would run 'nfc-list' for ${secs}s; timeout policy=${t}s)"
  fi
}
selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/nfc-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-26s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-26s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  firmware) cmd_firmware ;;
  read) cmd_read "${NUM:-15}" ;;
  report) { say "=== nuxel-nfc report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; cmd_firmware; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || true; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,20p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
