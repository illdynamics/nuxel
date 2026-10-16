#!/usr/bin/env bash
# nuxel-keyboard-apply.sh — the REAL consumer of /etc/nuxel/keyboard/keyboard.json
# (mission area 29 "native virtual keyboard", mission area 48 group "Input").
#
# WHY THIS FILE EXISTS
#   The Settings app and nuxelctl both write /etc/nuxel/keyboard/keyboard.json.
#   A document with no consumer is a cosmetic switch, so this applier is that
#   consumer: it reads the document, configures the on-screen keyboard provider
#   that is ACTUALLY installed (stevia / stevia-phosh-osk-provider on the phone
#   rootfs, squeekboard in the UTM VM image), and records one honest verdict per
#   setting in /run/nuxel-keyboard.state — `applied`, `not_applied:<reason>`,
#   `provider-managed` or `delegated`. The launcher host exposes that file to the
#   Settings UI as the status channel `keyboard-state`, so the UI can show the
#   application verdict instead of a wish.
#
# THE INPUT PATH IT CONFIGURES
#   finger -> OSK provider (stevia/squeekboard) -> phoc (zwp_text_input_manager_v3)
#          -> WebKitGTK -> the focused PWA text field
#   Nothing here re-implements that path. It configures it, and it PROVES it only
#   as far as a machine can: tools/s10plus/a33/keyboard-probe.html is the last hop
#   and is run by a human/VM session (never auto-promoted to VERIFIED_ON_S10PLUS).
#
# WHAT IT NEVER DOES
#   * no block device, no partition, no /dev/block access, no dd, no mount;
#   * no Heimdall/Odin/fastboot/Download Mode/Recovery (NO-FLASHING invariant);
#   * no kernel, DTB, initramfs or bootloader change;
#   * no writes outside $ROOT (which defaults to / and is a temporary directory
#     during the offline selftest).
#
# Usage
#   nuxel-keyboard-apply.sh apply [--root DIR] [--dry-run] [--json]
#   nuxel-keyboard-apply.sh status [--json]
#   nuxel-keyboard-apply.sh stack [--json]
#   nuxel-keyboard-apply.sh set keyboard.layout de        (validated, atomic)
#   nuxel-keyboard-apply.sh selftest
#
# Offline testability: --root DIR (or NUXEL_ROOT) prefixes /etc, /run, /var,
# /usr, /sys. NUXEL_DIAG_NO_SYSTEM=1 additionally hides host state tools so a
# fixture run can never read (or write) the workstation's real session.
set -uo pipefail

SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="${NUXEL_ROOT:-/}"
DOC_DEFAULT="/etc/nuxel/keyboard/keyboard.json"
LOG_DEFAULT="/var/log/nuxel/keyboard.log"
STATE_DEFAULT="/run/nuxel-keyboard.state"
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
    -h|--help) sed -n '2,40p' "$SELF_PATH"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-apply}"; [ $# -gt 0 ] && shift || true
case "$ROOT" in
  /) ;;
  *) ROOT="${ROOT%/}" ;;
esac

abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
DOC="${NUXEL_KEYBOARD_DOC:-$DOC_DEFAULT}"
LOG="${NUXEL_KEYBOARD_LOG:-$LOG_DEFAULT}"
STATE="${NUXEL_KEYBOARD_STATE:-$STATE_DEFAULT}"
: "${NUXEL_DIAG_SAFE_TOOLS:=python3}"

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >>"$(abs "$LOG")" 2>/dev/null || true; }
say() { [ "$JSON" = 1 ] || printf '%s\n' "$*"; }
die() { printf 'nuxel-keyboard-apply: %s\n' "$*" >&2; exit 2; }

run_tool() {                     # fake-root/isolated tool resolution
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    [ -x "$p" ] && { "$p" "$@"; return $?; }
  done
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then
    case " $NUXEL_DIAG_SAFE_TOOLS " in *" $t "*) ;; *) return 127 ;; esac
  fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}

# ----------------------------------------------------------------- documents --
# defaults MUST equal the defaults in pwa/nuxel-apps/settings/settings-model.js;
# tests/simulated-keyboard.py fails the build if the two ever drift apart.
DEFAULTS_JSON='{
  "keyboard.enabled": true, "keyboard.auto_show": true, "keyboard.layout": "us",
  "keyboard.numeric_layout": true, "keyboard.height_dp": 300,
  "keyboard.key_repeat": true, "keyboard.key_repeat_delay_ms": 500,
  "keyboard.key_repeat_interval_ms": 30, "keyboard.haptics": true,
  "keyboard.clipboard": true, "keyboard.hardware_passthrough": true
}'

read_doc() {   # -> KEY<TAB>VALUE<TAB>source  on stdout; exit 3 invalid, 4 unreadable
  NUXEL_DEFAULTS="$DEFAULTS_JSON" python3 - "$(abs "$DOC")" <<'PY'
import json, os, sys
defaults = json.loads(os.environ["NUXEL_DEFAULTS"])
path = sys.argv[1]
doc, src = {}, "absent"
if os.path.exists(path):
    try:
        with open(path) as f:
            doc = json.load(f)
        src = "document"
    except Exception as exc:
        print("INVALID\tdocument\tnot valid JSON: %s" % exc); sys.exit(3)
if not isinstance(doc, dict):
    print("INVALID\tdocument\troot of the document must be an object"); sys.exit(3)

RANGES = {
    "keyboard.height_dp": (160, 560),
    "keyboard.key_repeat_delay_ms": (100, 2000),
    "keyboard.key_repeat_interval_ms": (10, 200),
}
TYPES = {
    "keyboard.enabled": bool, "keyboard.auto_show": bool, "keyboard.numeric_layout": bool,
    "keyboard.key_repeat": bool, "keyboard.haptics": bool, "keyboard.clipboard": bool,
    "keyboard.hardware_passthrough": bool, "keyboard.layout": str,
    "keyboard.height_dp": int, "keyboard.key_repeat_delay_ms": int,
    "keyboard.key_repeat_interval_ms": int,
}
bad = []
for key, default in defaults.items():
    if key in doc:
        val = doc[key]
        want = TYPES.get(key)
        if want is bool and not isinstance(val, bool):
            bad.append("%s must be a boolean, got %r" % (key, val)); continue
        if want is int and (isinstance(val, bool) or not isinstance(val, int)):
            bad.append("%s must be an integer, got %r" % (key, val)); continue
        if want is str and (not isinstance(val, str) or not (2 <= len(val) <= 16)):
            bad.append("%s must be a 2-16 character string, got %r" % (key, val)); continue
        if key in RANGES:
            lo, hi = RANGES[key]
            if not (lo <= val <= hi):
                bad.append("%s must be within %d..%d, got %r" % (key, lo, hi, val)); continue
        s = "document"
    else:
        val, s = default, "default"
    out = "true" if val is True else "false" if val is False else str(val)
    print("%s\t%s\t%s" % (key, out, s))
if bad:
    for b in bad:
        print("INVALID\tdocument\t%s" % b)
    sys.exit(3)
PY
}

load_table() {  # validates the document; fills globals from the merged table
  local out rc
  out="$(read_doc)"; rc=$?
  if [ "$rc" != 0 ]; then
    printf '%s\n' "$out" >&2
    die "keyboard document $(abs "$DOC") is unusable (rc=$rc) — refusing to apply a document the applier cannot honour"
  fi
  declare -gA CFG=() SRC=()
  local key val src
  while IFS=$'\t' read -r key val src; do
    [ -n "${key:-}" ] || continue
    CFG["$key"]="$val"; SRC["$key"]="$src"
  done <<<"$out"
}

# ------------------------------------------------------------------- probing --
OSK=""; OSK_PATH=""
COMPOSITOR="unknown"; TEXT_INPUT="unknown"; HWKBD="absent"

probe_osk() {
  local cand
  for cand in usr/bin/squeekboard usr/libexec/squeekboard; do
    [ -x "$ROOT/$cand" ] && { OSK="squeekboard"; OSK_PATH="/$cand"; return; }
  done
  for cand in usr/bin/stevia usr/libexec/stevia usr/libexec/stevia-osk \
              usr/lib64/stevia/stevia usr/share/stevia/stevia; do
    [ -x "$ROOT/$cand" ] && { OSK="stevia"; OSK_PATH="/$cand"; return; }
  done
  # the provider may be installed without the shell binary being on PATH
  for cand in usr/share/applications/*osk*.desktop usr/share/phosh/osk/*; do
    if [ -e "$ROOT/$cand" ] 2>/dev/null; then
      case "$cand" in *stevia*) OSK="stevia" ;; *squeekboard*) OSK="squeekboard" ;; esac
      [ -n "$OSK" ] && { OSK_PATH="/$cand"; return; }
    fi
  done
  OSK="none"
}

probe_compositor() {
  if [ "$ROOT" != "/" ]; then
    local sock
    sock="$(ls "$ROOT"/run/user/*/wayland-* 2>/dev/null | head -n1 || true)"
    if [ -n "$sock" ] && [ -n "${WAYLAND_DISPLAY:-}" ]; then COMPOSITOR="wayland"; fi
  else
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
      COMPOSITOR="wayland"
      run_tool pgrep -x phoc >/dev/null 2>&1 && COMPOSITOR="phoc"
    elif [ -e /dev/fb0 ]; then
      COMPOSITOR="none(fbdev-only)"
    else
      COMPOSITOR="none"
    fi
  fi
  case "$COMPOSITOR" in
    phoc|wayland|"phosh"*) TEXT_INPUT="zwp_text_input_manager_v3" ;;
    *) TEXT_INPUT="unknown" ;;
  esac
}

probe_hwkbd() {
  local f name
  for f in "$ROOT"/sys/class/input/event*/device/name; do
    [ -r "$f" ] || continue
    name="$(cat "$f" 2>/dev/null || true)"
    case "$name" in
      *Keyboard*|*keyboard*|*kbd*|*gpio_keys*) case "$name" in
        *gpio_keys*|*sec_key_notifier*) ;;                 # phone buttons, not a keyboard
        *) HWKBD="present"; printf -v HWKBD_NAME '%s' "$name" ;; esac ;;
    esac
  done
  [ -n "${HWKBD_NAME:-}" ] || HWKBD_NAME="none"
}

# ------------------------------------------------------- applying the document
declare -A RESULT=()
gs_ok() { run_tool gsettings list-schemas 2>/dev/null | grep -qx "$1"; }
gs_set() { # schema key value
  if [ "$DRY" = 1 ]; then printf '  would: gsettings set %s %s %s\n' "$1" "$2" "$3"; return 0; fi
  run_tool gsettings set "$1" "$2" "$3" >/dev/null 2>&1
}

apply_keyboard() {
  local enabled="${CFG[keyboard.enabled]}" auto="${CFG[keyboard.auto_show]}"
  local layout="${CFG[keyboard.layout]}" numeric="${CFG[keyboard.numeric_layout]}"
  local height="${CFG[keyboard.height_dp]}" repeat="${CFG[keyboard.key_repeat]}"
  local clip="${CFG[keyboard.clipboard]}" haptics="${CFG[keyboard.haptics]}"
  local passthru="${CFG[keyboard.hardware_passthrough]}"
  local applied_via=""

  # --- enable / show-on-focus: the key phosh's OSK manager watches -----------
  if [ "$OSK" = "none" ] && [ "$ROOT" = "/" ]; then
    RESULT[keyboard.enabled]="not_applied:no-osk-installed"
    RESULT[keyboard.auto_show]="not_applied:no-osk-installed"
  elif [ "$OSK" = "none" ] && [ "$ROOT" != "/" ] && ! gs_ok org.gnome.desktop.a11y.applications; then
    RESULT[keyboard.enabled]="not_applied:no-osk-installed"
    RESULT[keyboard.auto_show]="not_applied:no-osk-installed"
  elif gs_ok org.gnome.desktop.a11y.applications; then
    gs_set org.gnome.desktop.a11y.applications screen-keyboard-enabled "$enabled" \
      && RESULT[keyboard.enabled]="applied" || RESULT[keyboard.enabled]="not_applied:gsettings-write-failed"
    applied_via="org.gnome.desktop.a11y.applications"
    if [ "$enabled" = "true" ]; then
      RESULT[keyboard.auto_show]="$([ "$auto" = "true" ] && echo applied || echo "not_applied:manual-only")"
    else
      RESULT[keyboard.auto_show]="not_applied:keyboard-disabled"
    fi
  else
    RESULT[keyboard.enabled]="not_applied:no-enable-key-on-this-stack"
    RESULT[keyboard.auto_show]="not_applied:no-enable-key-on-this-stack"
  fi

  # --- layout: compositor input sources -------------------------------------
  if gs_ok org.gnome.desktop.input-sources; then
    gs_set org.gnome.desktop.input-sources sources "[('xkb', '$layout')]" \
      && RESULT[keyboard.layout]="applied" || RESULT[keyboard.layout]="not_applied:gsettings-write-failed"
  else
    RESULT[keyboard.layout]="not_applied:no-input-sources-schema"
  fi

  # --- squeekboard-specific knobs (the VM provider) --------------------------
  if [ "$OSK" = "squeekboard" ]; then
    local home_dir
    if [ "$ROOT" = "/" ]; then home_dir="${NUXEL_OSK_HOME:-$HOME}"; else home_dir="$ROOT/home/${NUXEL_OSK_USER:-nuxel}"; fi
    local ini="$home_dir/.config/squeekboard/config.ini"
    if [ "$DRY" = 1 ]; then
      printf '  would write %s (layout=phone, clipboard=%s)\n' "$ini" "$clip"
      RESULT[keyboard.clipboard]="dry-run"
    else
      mkdir -p "$(dirname "$ini")" 2>/dev/null || true
      {
        echo '[keyboard]'
        echo 'layout=phone'
        echo "show-clipboard-button=$clip"
        echo "show-emoji-button=$enabled"
        echo "auto-capitalize=$numeric"
      } >"$ini" 2>/dev/null && RESULT[keyboard.clipboard]="applied:config.ini" \
                          || RESULT[keyboard.clipboard]="not_applied:config-unwritable"
    fi
    RESULT[keyboard.height_dp]="provider-managed:squeekboard-theme (requested ${height}dp)"
    RESULT[keyboard.numeric_layout]="$([ "$numeric" = "true" ] && echo "provider-managed:squeekboard-numeric-view" || echo "not_applied:disabled-by-setting")"
  elif [ "$OSK" = "stevia" ]; then
    # stevia 0.54 sizes and lays out from its own theme/provider; there is no
    # user height or layout-file knob, so those two are reported as managed by
    # the provider instead of being pretend-applied.
    RESULT[keyboard.height_dp]="provider-managed:stevia-theme (requested ${height}dp)"
    RESULT[keyboard.numeric_layout]="$([ "$numeric" = "true" ] && echo "provider-managed:stevia-numeric-view" || echo "not_applied:disabled-by-setting")"
    RESULT[keyboard.clipboard]="provider-managed:stevia-clipboard"
  else
    RESULT[keyboard.height_dp]="not_applied:no-osk-installed"
    RESULT[keyboard.numeric_layout]="not_applied:no-osk-installed"
    RESULT[keyboard.clipboard]="not_applied:no-osk-installed"
  fi

  # --- key repeat (physical + OSK backspace repeat) -------------------------
  if gs_ok org.gnome.desktop.peripherals.keyboard; then
    gs_set org.gnome.desktop.peripherals.keyboard repeat "$repeat" \
      && gs_set org.gnome.desktop.peripherals.keyboard delay "${CFG[keyboard.key_repeat_delay_ms]}" \
      && gs_set org.gnome.desktop.peripherals.keyboard repeat-interval "${CFG[keyboard.key_repeat_interval_ms]}" \
      && RESULT[keyboard.key_repeat]="applied" || RESULT[keyboard.key_repeat]="not_applied:gsettings-write-failed"
  else
    RESULT[keyboard.key_repeat]="not_applied:no-keyboard-schema"
  fi

  # --- haptics: delegated, never duplicated ---------------------------------
  RESULT[keyboard.haptics]="$([ "$haptics" = "true" ] && echo "delegated:haptics-component" || echo "not_applied:disabled-by-setting")"

  # --- physical keyboard passthrough ---------------------------------------
  RESULT[keyboard.hardware_passthrough]="$([ "$passthru" = "true" ] && echo "observed:${HWKBD}" || echo "not_applied:disabled-by-setting")"

  log "apply root=$ROOT osk=$OSK compositor=$COMPOSITOR enabled=${RESULT[keyboard.enabled]} layout=${RESULT[keyboard.layout]} via=${applied_via:-none}"
}

write_state() {
  local tmp; tmp="$(abs "$STATE").tmp.$$"
  mkdir -p "$(dirname "$(abs "$STATE")")" 2>/dev/null || true
  if [ "$DRY" = 1 ]; then say "(dry-run: would write $(abs "$STATE"))"; return 0; fi
  {
    echo "schema_version=1"
    echo "updated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "root=$ROOT"
    echo "document=$(abs "$DOC")"
    echo "osk=$OSK"
    echo "osk_path=${OSK_PATH:-none}"
    echo "compositor=$COMPOSITOR"
    echo "text_input=$TEXT_INPUT"
    echo "hardware_keyboard=$HWKBD"
    echo "hardware_keyboard_name=${HWKBD_NAME:-none}"
    local k
    for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
             keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
             keyboard.hardware_passthrough; do
      echo "${k}=${RESULT[$k]:-unknown}"
    done
    echo "verdict=$([ "$OSK" = none ] && echo NO_OSK_INSTALLED || echo OSK_CONFIGURED)"
  } >"$tmp" 2>/dev/null && mv -f "$tmp" "$(abs "$STATE")" 2>/dev/null || {
    rm -f "$tmp" 2>/dev/null
    die "cannot write $(abs "$STATE")"
  }
}

json_status() {
  local k first=1
  printf '{'
  local -A meta=( [osk]="$OSK" [osk_path]="${OSK_PATH:-none}" [compositor]="$COMPOSITOR" \
                  [text_input]="$TEXT_INPUT" [hardware_keyboard]="$HWKBD" \
                  [document]="$(abs "$DOC")" [state_file]="$(abs "$STATE")" )
  for k in osk osk_path compositor text_input hardware_keyboard document state_file; do
    [ $first = 1 ] || printf ','; first=0
    printf '"%s":"%s"' "$k" "${meta[$k]}"
  done
  printf ',"settings":{'
  first=1
  for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
           keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
           keyboard.hardware_passthrough; do
    [ $first = 1 ] || printf ','; first=0
    printf '"%s":"%s"' "$k" "${RESULT[$k]:-unknown}"
  done
  printf '}}\n'
}

cmd_apply() {
  load_table
  probe_osk; probe_compositor; probe_hwkbd
  apply_keyboard
  write_state
  if [ "$JSON" = 1 ]; then json_status; else
    say "Nuxel keyboard apply — root=$ROOT"
    say "  osk=$OSK (${OSK_PATH:-none})  compositor=$COMPOSITOR  text_input=$TEXT_INPUT  hardware_keyboard=$HWKBD"
    local k
    for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
             keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
             keyboard.hardware_passthrough; do
      printf '  %-32s %s\n' "$k" "${RESULT[$k]:-unknown}"
    done
    say "  evidence: $(abs "$STATE")"
    [ "$OSK" = none ] && say "  NOTICE: no OSK provider is installed in this root — the Settings switch is reported as not_applied, never as on."
  fi
  return 0
}

cmd_stack() {
  probe_osk; probe_compositor; probe_hwkbd
  if [ "$JSON" = 1 ]; then
    printf '{"osk":"%s","osk_path":"%s","compositor":"%s","text_input":"%s","hardware_keyboard":"%s","hardware_keyboard_name":"%s"}\n' \
      "$OSK" "${OSK_PATH:-none}" "$COMPOSITOR" "$TEXT_INPUT" "$HWKBD" "$HWKBD_NAME"
  else
    say "osk=$OSK path=${OSK_PATH:-none}"
    say "compositor=$COMPOSITOR text_input=$TEXT_INPUT"
    say "hardware_keyboard=$HWKBD name=$HWKBD_NAME"
  fi
}

cmd_status() {
  local sf; sf="$(abs "$STATE")"
  if [ ! -f "$sf" ]; then
    say "no keyboard state recorded yet ($sf) — run '$0 apply'"
    return 1
  fi
  cat "$sf"
  say "# probe: $(abs "$LOG") · probe page tools/s10plus/a33/keyboard-probe.html"
}

cmd_set() {   # set <key> <value>  — validated, atomic, then re-applied
  local key="${1:-}" value="${2:-}"
  [ -n "$key" ] || die "set needs <key> <value>"
  case "$key" in
    keyboard.enabled|keyboard.auto_show|keyboard.numeric_layout|keyboard.key_repeat|\
keyboard.haptics|keyboard.clipboard|keyboard.hardware_passthrough)
      case "$value" in true|false) ;; *) die "$key must be true or false (got '$value')" ;; esac ;;
    keyboard.layout)
      [ "${#value}" -ge 2 ] && [ "${#value}" -le 16 ] || die "keyboard.layout must be 2-16 characters" ;;
    keyboard.height_dp) case "$value" in ''|*[!0-9]*) die "keyboard.height_dp must be an integer" ;; esac
      [ "$value" -ge 160 ] && [ "$value" -le 560 ] || die "keyboard.height_dp must be 160..560" ;;
    keyboard.key_repeat_delay_ms) case "$value" in ''|*[!0-9]*) die "delay must be an integer" ;; esac ;;
    keyboard.key_repeat_interval_ms) case "$value" in ''|*[!0-9]*) die "interval must be an integer" ;; esac ;;
    *) die "unknown keyboard setting '$key' — refusing to write a key the applier cannot honour" ;;
  esac
  if [ "$ROOT" != "/" ] || [ "$DRY" = 0 ]; then
    mkdir -p "$(dirname "$(abs "$DOC")")" 2>/dev/null || true
    python3 - "$(abs "$DOC")" "$key" "$value" <<'PY'
import json, os, sys, tempfile
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
doc = {}
if os.path.exists(path):
    try:
        with open(path) as f: doc = json.load(f)
    except Exception as exc:
        print("refusing to modify an unparsable document: %s" % exc, file=sys.stderr); sys.exit(3)
if not isinstance(doc, dict): sys.exit(3)
if value in ("true", "false"):
    doc[key] = (value == "true")
elif value.isdigit():
    doc[key] = int(value)
else:
    doc[key] = value
doc.setdefault("schema_version", 1)
doc["set_by"] = "user"
doc["updated_at"] = int(__import__("time").time())
d = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(dir=d, prefix=".keyboard.", suffix=".json")
with os.fdopen(fd, "w") as f:
    json.dump(doc, f, indent=2); f.write("\n")
os.replace(tmp, path)
PY
    [ $? = 0 ] || die "failed to update $(abs "$DOC") atomically"
    say "set $key=$value in $(abs "$DOC")"
  fi
  cmd_apply
}

# ------------------------------------------------------------------ selftest --
selftest() {
  local tmp fails=0 checks=0
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-kbd.XXXXXX")" || die "mktemp failed"
  trap 'rm -rf "$tmp"' EXIT
  ck() { checks=$((checks+1)); if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; fails=$((fails+1)); fi; }

  mkdir -p "$tmp/etc/nuxel/keyboard" "$tmp/run" "$tmp/var/log/nuxel" "$tmp/usr/bin" \
           "$tmp/sys/class/input" "$tmp/home/nuxel"

  # 1. missing document -> defaults, no OSK in this root, honest verdicts
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  ck $? "apply with no document uses defaults and exits 0"
  grep -q '^osk=none$' "$tmp/run/nuxel-keyboard.state"
  ck $? "no OSK in the fake root is reported as osk=none"
  grep -q '^keyboard.enabled=not_applied:no-osk-installed$' "$tmp/run/nuxel-keyboard.state"
  ck $? "keyboard.enabled is not_applied:no-osk-installed (never a fake 'on')"

  # 2. broken document -> refuse (exit 2), no state written
  rm -f "$tmp/run/nuxel-keyboard.state"
  printf '{ this is not json' >"$tmp/etc/nuxel/keyboard/keyboard.json"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an unparsable document is refused with exit 2"
  [ ! -f "$tmp/run/nuxel-keyboard.state" ]; ck $? "a refused document writes no state"

  # 3. out-of-range value -> refuse
  printf '{"schema_version":1,"keyboard.height_dp":9000}' >"$tmp/etc/nuxel/keyboard/keyboard.json"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an out-of-range keyboard.height_dp is refused"

  # 4. real document + stub OSK + stub gsettings -> applied verdicts
  cp "$(dirname "$SELF_PATH")/../../..//configs/nuxel/keyboard/keyboard.json" "$tmp/etc/nuxel/keyboard/keyboard.json" 2>/dev/null || \
    printf '{"schema_version":1,"keyboard.enabled":true,"keyboard.auto_show":true,"keyboard.layout":"us","keyboard.numeric_layout":true,"keyboard.height_dp":300,"keyboard.key_repeat":true,"keyboard.haptics":true,"keyboard.clipboard":true,"keyboard.hardware_passthrough":true}' \
      >"$tmp/etc/nuxel/keyboard/keyboard.json"
  printf '#!/bin/sh\n[ "$1" = list-schemas ] && { echo org.gnome.desktop.a11y.applications; echo org.gnome.desktop.input-sources; echo org.gnome.desktop.peripherals.keyboard; exit 0; }\necho "$@" >>"%s/gsettings.calls"\nexit 0\n' "$tmp" >"$tmp/usr/bin/gsettings"
  chmod +x "$tmp/usr/bin/gsettings"
  printf '#!/bin/sh\nexit 0\n' >"$tmp/usr/bin/stevia"; chmod +x "$tmp/usr/bin/stevia"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  ck $? "apply with a stevia provider and a writable gsettings exits 0"
  grep -q '^osk=stevia$' "$tmp/run/nuxel-keyboard.state"; ck $? "provider probe finds stevia"
  grep -q '^keyboard.enabled=applied$' "$tmp/run/nuxel-keyboard.state"; ck $? "enable is applied when the enable key exists"
  grep -q '^keyboard.layout=applied$' "$tmp/run/nuxel-keyboard.state"; ck $? "layout is applied through input-sources"
  grep -q '^keyboard.height_dp=provider-managed:' "$tmp/run/nuxel-keyboard.state"; ck $? "a provider-managed height is reported as provider-managed"
  grep -q '^keyboard.haptics=delegated:' "$tmp/run/nuxel-keyboard.state"; ck $? "haptics is delegated to the haptics component"
  grep -q '^text_input=zwp_text_input_manager_v3$' "$tmp/run/nuxel-keyboard.state" || \
    grep -q '^text_input=unknown$' "$tmp/run/nuxel-keyboard.state"
  ck $? "text_input is reported (never blank)"
  grep -q 'set org.gnome.desktop.a11y.applications screen-keyboard-enabled true' "$tmp/gsettings.calls"
  ck $? "the enable switch really reached gsettings"

  # 5. set: valid change persists atomically and re-applies
  NUXEL_ROOT="$tmp" "$SELF_PATH" set keyboard.layout de >/dev/null 2>&1
  ck $? "set keyboard.layout de succeeds"
  python3 -c "import json,sys; sys.exit(0 if json.load(open('$tmp/etc/nuxel/keyboard/keyboard.json'))['keyboard.layout']=='de' else 1)"
  ck $? "the new layout is durable in the document"
  grep -q "('xkb', 'de')" "$tmp/gsettings.calls"; ck $? "the new layout reached the compositor input sources"

  # 6. set: unknown key is refused
  NUXEL_ROOT="$tmp" "$SELF_PATH" set keyboard.facepalm true >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an unknown setting key is refused"

  # 7. no flashing primitives anywhere in this tool
  ! grep -Eqi 'heimdall|odin|fastboot|/dev/block|download.mode' "$SELF_PATH"
  ck $? "the applier contains no flashing/bootloader primitive"

  echo "== keyboard applier selftest: $((checks-fails))/$checks checks passed =="
  [ "$fails" = 0 ] || { echo "SELFTEST FAILED"; return 1; }
  echo "SELFTEST PASSED"
}

case "$CMD" in
  apply)    cmd_apply ;;
  stack)    cmd_stack ;;
  status)   cmd_status ;;
  set)      cmd_set "$@" ;;
  selftest) selftest ;;
  *) die "unknown command '$CMD' (apply|status|stack|set|selftest)" ;;
esac
