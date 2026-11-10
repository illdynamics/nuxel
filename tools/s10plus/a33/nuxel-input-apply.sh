#!/usr/bin/env bash
# nuxel-input-apply.sh — the GSettings consumer for the physical pointer
# document /etc/nuxel/input/input.json (USB HID mouse / touchpad).
#
# The libinput shim applies the same document directly to each accepted device;
# this applier keeps phoc's own org.gnome.desktop.peripherals handlers in sync,
# so a settings change is live and a phoc hotplug cannot restore stale defaults.
# It also records one honest verdict per key in /run/nuxel-input-gsettings.state,
# which the Settings app reads as `input-gsettings-state`.
#
# It deliberately does NOT touch keyboard layout / repeat: those live in
# /etc/nuxel/keyboard/keyboard.json and are applied by nuxel-keyboard-apply.sh.
#
# Usage:
#   nuxel-input-apply.sh apply [--root DIR] [--dry-run] [--json]
#   nuxel-input-apply.sh status
#   nuxel-input-apply.sh selftest
set -uo pipefail

SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="${NUXEL_ROOT:-/}"
DOC_DEFAULT="/etc/nuxel/input/input.json"
STATE_DEFAULT="/run/nuxel-input-gsettings.state"
LOG_DEFAULT="/var/log/nuxel/input.log"
JSON=0
DRY=0
CMD=""
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?--root needs a directory}"; shift 2 ;;
    --root=*) ROOT="${1#--root=}"; shift ;;
    --json) JSON=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -h|--help) sed -n '2,25p' "$SELF_PATH"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-apply}"; [ $# -gt 0 ] && shift || true
[ "$ROOT" = "/" ] || ROOT="${ROOT%/}"

abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
DOC="${NUXEL_INPUT_DOC:-$DOC_DEFAULT}"
STATE="${NUXEL_INPUT_STATE:-$STATE_DEFAULT}"
LOG="${NUXEL_INPUT_LOG:-$LOG_DEFAULT}"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-input-work.XXXXXX")" || { echo "nuxel-input-apply: mktemp failed" >&2; exit 1; }
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)" "$*" >>"$(abs "$LOG")" 2>/dev/null || true; }
say() { [ "$JSON" = 1 ] || printf '%s\n' "$*"; }
die() { printf 'nuxel-input-apply: %s\n' "$*" >&2; exit 2; }

run_tool() {
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ -x "$p" ]; then "$p" "$@"; return $?; fi
  done
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}

DEFAULTS_JSON='{
  "mouse.speed": 0.0, "mouse.accel_profile": "default",
  "mouse.natural_scroll": false, "mouse.left_handed": false,
  "mouse.middle_emulation": false,
  "touchpad.speed": 0.0, "touchpad.accel_profile": "default",
  "touchpad.natural_scroll": true, "touchpad.tap_to_click": true,
  "touchpad.two_finger_scroll": true, "touchpad.disable_while_typing": true,
  "touchpad.left_handed": false
}'

load_table() {   # KEY<TAB>VALUE into table.tsv
  NUXEL_DEFAULTS="$DEFAULTS_JSON" python3 - "$(abs "$DOC")" >"$WORK/table.tsv" 2>"$WORK/table.err" <<'PY'
import json, os, sys
defaults = json.loads(os.environ["NUXEL_DEFAULTS"])
path = sys.argv[1]
doc = {}
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception as exc:
        sys.stderr.write("document is not JSON: %s\n" % exc)
        sys.exit(3)
    if not isinstance(doc, dict):
        sys.stderr.write("document root is not an object\n")
        sys.exit(3)
BOOLS = ["mouse.natural_scroll", "mouse.left_handed", "mouse.middle_emulation",
         "touchpad.natural_scroll", "touchpad.tap_to_click",
         "touchpad.two_finger_scroll", "touchpad.disable_while_typing",
         "touchpad.left_handed"]
FLOATS = ["mouse.speed", "touchpad.speed"]
PROFILES = ["mouse.accel_profile", "touchpad.accel_profile"]
values = dict(defaults)
for k in BOOLS:
    if k in doc:
        if not isinstance(doc[k], bool):
            sys.stderr.write("%s must be a boolean\n" % k); sys.exit(3)
        values[k] = doc[k]
for k in FLOATS:
    if k in doc:
        if isinstance(doc[k], bool) or not isinstance(doc[k], (int, float)) or not (-1.0 <= float(doc[k]) <= 1.0):
            sys.stderr.write("%s must be a number in -1..1\n" % k); sys.exit(3)
        values[k] = round(float(doc[k]), 2)
for k in PROFILES:
    if k in doc:
        if doc[k] not in ("default", "flat", "adaptive"):
            sys.stderr.write("%s must be default, flat or adaptive\n" % k); sys.exit(3)
        values[k] = doc[k]
for k in sorted(values):
    v = values[k]
    if isinstance(v, bool): v = "true" if v else "false"
    elif isinstance(v, float): v = "%.2f" % v
    print("%s\t%s" % (k, v))
PY
  local rc=$?
  [ "$rc" -eq 0 ] || die "input document rejected: $(cat "$WORK/table.err" 2>/dev/null)"
}

cfg() { awk -F '\t' -v k="$1" '$1 == k { print $2; found=1 } END { if (!found) exit 1 }' "$WORK/table.tsv"; }
res() { printf '%s=%s\n' "$1" "$2" >>"$WORK/res.tsv"; }
res_get() { awk -F '=' -v k="$1" '$1 == k { sub(/^[^=]*=/, ""); print; found=1 } END { if (!found) print "missing" }' "$WORK/res.tsv"; }

gs_ok() {
  run_tool gsettings list-schemas 2>/dev/null | grep -qx "$1"
}
gs_set() {
  if [ "$DRY" = 1 ]; then printf 'would: gsettings set %s %s %s\n' "$1" "$2" "$3"; return 0; fi
  run_tool gsettings set "$1" "$2" "$3" >/dev/null 2>&1
}

apply_pointer() {
  local speed profile natural left middle tp_speed tp_profile tp_natural tp_tap tp_two tp_dwt tp_left
  local schema_mouse="org.gnome.desktop.peripherals.mouse"
  local schema_touchpad="org.gnome.desktop.peripherals.touchpad"
  speed="$(cfg mouse.speed)"; profile="$(cfg mouse.accel_profile)"
  natural="$(cfg mouse.natural_scroll)"; left="$(cfg mouse.left_handed)"
  middle="$(cfg mouse.middle_emulation)"
  tp_speed="$(cfg touchpad.speed)"; tp_profile="$(cfg touchpad.accel_profile)"
  tp_natural="$(cfg touchpad.natural_scroll)"; tp_tap="$(cfg touchpad.tap_to_click)"
  tp_two="$(cfg touchpad.two_finger_scroll)"; tp_dwt="$(cfg touchpad.disable_while_typing)"
  tp_left="$(cfg touchpad.left_handed)"

  if gs_ok "$schema_mouse"; then
    gs_set "$schema_mouse" speed "$speed"          && res mouse.speed applied          || res mouse.speed "not_applied:gsettings-write-failed"
    gs_set "$schema_mouse" accel-profile "$profile" && res mouse.accel_profile applied || res mouse.accel_profile "not_applied:gsettings-write-failed"
    gs_set "$schema_mouse" natural-scroll "$natural" && res mouse.natural_scroll applied || res mouse.natural_scroll "not_applied:gsettings-write-failed"
    gs_set "$schema_mouse" left-handed "$left"      && res mouse.left_handed applied     || res mouse.left_handed "not_applied:gsettings-write-failed"
    gs_set "$schema_mouse" middle-click-emulation "$middle" && res mouse.middle_emulation applied || res mouse.middle_emulation "not_applied:gsettings-write-failed"
  else
    for k in mouse.speed mouse.accel_profile mouse.natural_scroll mouse.left_handed mouse.middle_emulation; do
      res "$k" "not_applied:no-mouse-schema"
    done
  fi

  if gs_ok "$schema_touchpad"; then
    gs_set "$schema_touchpad" speed "$tp_speed"      && res touchpad.speed applied      || res touchpad.speed "not_applied:gsettings-write-failed"
    gs_set "$schema_touchpad" accel-profile "$tp_profile" && res touchpad.accel_profile applied || res touchpad.accel_profile "not_applied:gsettings-write-failed"
    gs_set "$schema_touchpad" natural-scroll "$tp_natural" && res touchpad.natural_scroll applied || res touchpad.natural_scroll "not_applied:gsettings-write-failed"
    gs_set "$schema_touchpad" tap-to-click "$tp_tap" && res touchpad.tap_to_click applied || res touchpad.tap_to_click "not_applied:gsettings-write-failed"
    gs_set "$schema_touchpad" two-finger-scrolling-enabled "$tp_two" && res touchpad.two_finger_scroll applied || res touchpad.two_finger_scroll "not_applied:gsettings-write-failed"
    gs_set "$schema_touchpad" disable-while-typing "$tp_dwt" && res touchpad.disable_while_typing applied || res touchpad.disable_while_typing "not_applied:gsettings-write-failed"
    local handed="mouse"; [ "$tp_left" = "true" ] && handed="left"
    gs_set "$schema_touchpad" left-handed "$handed" && res touchpad.left_handed applied || res touchpad.left_handed "not_applied:gsettings-write-failed"
  else
    for k in touchpad.speed touchpad.accel_profile touchpad.natural_scroll touchpad.tap_to_click \
             touchpad.two_finger_scroll touchpad.disable_while_typing touchpad.left_handed; do
      res "$k" "not_applied:no-touchpad-schema"
    done
  fi
}

write_state() {
  local out; out="$(abs "$STATE")"
  if [ "$DRY" = 1 ]; then say "(dry-run: would write $out)"; return 0; fi
  mkdir -p "$(dirname "$out")" 2>/dev/null || true
  local verdict="APPLIED"
  grep -q "not_applied" "$WORK/res.tsv" 2>/dev/null && verdict="PARTIAL"
  {
    echo "schema_version=1"
    echo "updated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"
    echo "root=$ROOT"
    echo "document=$(abs "$DOC")"
    echo "consumer=nuxel-input-apply.sh -> gsettings -> phoc"
    echo "verdict=$verdict"
    cat "$WORK/res.tsv" 2>/dev/null
  } >"$out.tmp.$$" && mv -f "$out.tmp.$$" "$out" || { rm -f "$out.tmp.$$"; die "cannot write $out"; }
  log "apply verdict=$verdict speed=$(cfg mouse.speed) touchpad_natural=$(cfg touchpad.natural_scroll)"
}

apply_all() {
  : >"$WORK/res.tsv"
  load_table
  apply_pointer
  write_state
  say "pointer settings: $(res_get mouse.speed) / $(res_get touchpad.tap_to_click)"
}

status() {
  cat "$(abs "$STATE")" 2>/dev/null || die "no state at $(abs "$STATE")"
}

selftest() {
  local tmp; tmp="$(mktemp -d "$WORK/selftest.XXXXXX")" || return 1
  mkdir -p "$tmp/etc/nuxel/input" "$tmp/usr/bin" "$tmp/run" "$tmp/var/log/nuxel"
  cat >"$tmp/usr/bin/gsettings" <<'STUB'
#!/bin/sh
echo "$@" >>"${GS_LOG:?}"
case "$1" in
  list-schemas) printf 'org.gnome.desktop.peripherals.mouse\norg.gnome.desktop.peripherals.touchpad\n' ;;
esac
exit 0
STUB
  chmod +x "$tmp/usr/bin/gsettings"
  cat >"$tmp/etc/nuxel/input/input.json" <<'DOC'
{"mouse.speed": 0.5, "mouse.natural_scroll": true,
 "touchpad.tap_to_click": false, "touchpad.left_handed": true}
DOC
  GS_LOG="$tmp/gs.calls" NUXEL_ROOT="$tmp" NUXEL_INPUT_STATE=/run/nuxel-input-gsettings.state \
    NUXEL_INPUT_LOG=/var/log/nuxel/input.log \
    "$SELF_PATH" apply >/dev/null 2>&1 || { echo "SELFTEST_FAIL apply"; return 1; }
  grep -q "peripherals.mouse speed 0.50" "$tmp/gs.calls" || { echo "SELFTEST_FAIL mouse speed"; return 1; }
  grep -q "peripherals.mouse natural-scroll true" "$tmp/gs.calls" || { echo "SELFTEST_FAIL natural"; return 1; }
  grep -q "peripherals.touchpad tap-to-click false" "$tmp/gs.calls" || { echo "SELFTEST_FAIL tap"; return 1; }
  grep -q "peripherals.touchpad left-handed left" "$tmp/gs.calls" || { echo "SELFTEST_FAIL handed"; return 1; }
  grep -q "^mouse.speed=applied$" "$tmp/run/nuxel-input-gsettings.state" || { echo "SELFTEST_FAIL state"; return 1; }
  echo "SELFTEST_OK"
}

case "$CMD" in
  apply) apply_all ;;
  status) status ;;
  selftest) selftest ;;
  *) die "unknown command: $CMD" ;;
esac
