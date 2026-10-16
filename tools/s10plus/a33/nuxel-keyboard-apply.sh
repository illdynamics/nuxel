#!/usr/bin/env bash
# nuxel-keyboard-apply.sh — the REAL consumer of /etc/nuxel/keyboard/keyboard.json
# (mission area 29 "native virtual keyboard", mission area 48 group "Input").
#
# WHY THIS FILE EXISTS
#   The Nuxel Settings app and nuxelctl both write
#   /etc/nuxel/keyboard/keyboard.json. A document with no consumer is a cosmetic
#   switch, so this applier IS that consumer: it reads the document, configures
#   the on-screen keyboard provider that is ACTUALLY installed (stevia /
#   stevia-phosh-osk-provider on the phone rootfs, squeekboard in the UTM VM
#   image), and records one honest verdict per setting in
#   /run/nuxel-keyboard.state — `applied`, `not_applied:<reason>`,
#   `provider-managed` or `delegated`. The launcher host exposes that file to the
#   Settings UI as the status channel `keyboard-state`, so the UI can show the
#   application verdict instead of a wish.
#
# THE INPUT PATH IT CONFIGURES
#   finger -> OSK provider (stevia/squeekboard) -> phoc (zwp_text_input_manager_v3)
#          -> WebKitGTK -> the focused PWA text field
#   Nothing here re-implements that path, and nothing here claims it works: the
#   last hop is proven by tools/s10plus/a33/keyboard-probe.html in a VM/phone
#   session and by the owner (docs/beta-finalization/manual-proof/20-applications.md).
#
# WHAT IT NEVER DOES
#   * no raw block device and no partition access, no dd, no mount;
#   * no vendor flash tool, no bootloader interface, no Download Mode, no
#     Recovery (NO-FLASHING invariant of this mission);
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
# Written for bash >= 3.2: no associative arrays, no mapfile.
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
    -h|--help) sed -n '2,45p' "$SELF_PATH"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-apply}"; [ $# -gt 0 ] && shift || true
[ "$ROOT" = "/" ] || ROOT="${ROOT%/}"

abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
DOC="${NUXEL_KEYBOARD_DOC:-$DOC_DEFAULT}"
LOG="${NUXEL_KEYBOARD_LOG:-$LOG_DEFAULT}"
STATE="${NUXEL_KEYBOARD_STATE:-$STATE_DEFAULT}"
: "${NUXEL_DIAG_SAFE_TOOLS:=python3}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-kbd-work.XXXXXX")" || { echo "nuxel-keyboard-apply: mktemp failed" >&2; exit 1; }
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

log() { printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)" "$*" >>"$(abs "$LOG")" 2>/dev/null || true; }
say() { [ "$JSON" = 1 ] || printf '%s\n' "$*"; }
die() { printf 'nuxel-keyboard-apply: %s\n' "$*" >&2; exit 2; }

run_tool() {                     # fake-root / isolation-aware tool resolution
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ -x "$p" ]; then "$p" "$@"; return $?; fi
  done
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then
    case " $NUXEL_DIAG_SAFE_TOOLS " in *" $t "*) ;; *) return 127 ;; esac
  fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}

# ----------------------------------------------------------------- documents --
# These defaults MUST equal the defaults in
# pwa/nuxel-apps/settings/settings-model.js; tests/test-virtual-keyboard.py
# fails when the two drift apart.
DEFAULTS_JSON='{
  "keyboard.enabled": true, "keyboard.auto_show": true, "keyboard.layout": "us",
  "keyboard.numeric_layout": true, "keyboard.height_dp": 300,
  "keyboard.key_repeat": true, "keyboard.key_repeat_delay_ms": 500,
  "keyboard.key_repeat_interval_ms": 30, "keyboard.haptics": true,
  "keyboard.clipboard": true, "keyboard.hardware_passthrough": true
}'

load_table() {   # writes KEY<TAB>VALUE<TAB>source into $WORK/table.tsv
  local rc
  NUXEL_DEFAULTS="$DEFAULTS_JSON" python3 - "$(abs "$DOC")" >"$WORK/table.tsv" 2>"$WORK/table.err" <<'PY'
import json, os, sys
defaults = json.loads(os.environ["NUXEL_DEFAULTS"])
path = sys.argv[1]
doc, src = {}, "document"
if not os.path.exists(path):
    sys.stderr.write("document %s does not exist; using built-in defaults\n" % path)
    src = "absent"
else:
    try:
        with open(path) as f:
            doc = json.load(f)
    except Exception as exc:
        sys.stderr.write("document dropped as not-JSON: %s\n" % exc)
        sys.exit(3)
if not isinstance(doc, dict):
    sys.stderr.write("document root is not an object\n"); sys.exit(3)

RANGES = {"keyboard.height_dp": (160, 560),
          "keyboard.key_repeat_delay_ms": (100, 2000),
          "keyboard.key_repeat_interval_ms": (10, 200)}
TYPES = {"keyboard.enabled": bool, "keyboard.auto_show": bool, "keyboard.numeric_layout": bool,
         "keyboard.key_repeat": bool, "keyboard.haptics": bool, "keyboard.clipboard": bool,
         "keyboard.hardware_passthrough": bool, "keyboard.layout": str,
         "keyboard.height_dp": int, "keyboard.key_repeat_delay_ms": int,
         "keyboard.key_repeat_interval_ms": int}
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
        sys.stderr.write("invalid setting: %s\n" % b)
    sys.exit(3)
PY
  rc=$?
  if [ "$rc" != 0 ]; then
    cat "$WORK/table.err" >&2
    die "keyboard document $(abs "$DOC") is unusable (rc=$rc) — refusing to apply a document the applier cannot honour"
  fi
  cat "$WORK/table.err" >&2
}
cfg() { awk -F'\t' -v k="$1" '$1==k{print $2; exit}' "$WORK/table.tsv"; }
res() { printf '%s\t%s\n' "$1" "$2" >>"$WORK/results.tsv"; }
res_get() { awk -F'\t' -v k="$1" '$1==k{print $2; exit}' "$WORK/results.tsv"; }

# ------------------------------------------------------------------- probing --
OSK=""; OSK_PATH=""; HWKBD="absent"; HWKBD_NAME="none"
COMPOSITOR="unknown"; TEXT_INPUT="unknown"

probe_osk() {
  local cand
  for cand in usr/bin/squeekboard usr/libexec/squeekboard; do
    if [ -x "$ROOT/$cand" ]; then OSK="squeekboard"; OSK_PATH="/$cand"; return; fi
  done
  for cand in usr/bin/stevia usr/libexec/stevia usr/libexec/stevia-osk \
              usr/lib64/stevia/stevia usr/share/stevia/stevia; do
    if [ -x "$ROOT/$cand" ]; then OSK="stevia"; OSK_PATH="/$cand"; return; fi
  done
  # the provider can be installed without a top-level shell binary
  for cand in "$ROOT"/usr/share/applications/*osk*.desktop "$ROOT"/usr/share/phosh/osk/*; do
    if [ -e "$cand" ]; then
      case "$cand" in
        *stevia*) OSK="stevia"; OSK_PATH="${cand#$ROOT}" ;;
        *squeekboard*) OSK="squeekboard"; OSK_PATH="${cand#$ROOT}" ;;
      esac
      [ -n "$OSK" ] && return
    fi
  done
  OSK="none"
}

probe_compositor() {
  if [ "$ROOT" != "/" ]; then
    if ls "$ROOT"/run/user/*/wayland-* >/dev/null 2>&1 && [ -n "${WAYLAND_DISPLAY:-}" ]; then
      COMPOSITOR="wayland"
    fi
  elif [ -n "${WAYLAND_DISPLAY:-}" ]; then
    COMPOSITOR="wayland"
    if run_tool pgrep -x phoc >/dev/null 2>&1; then COMPOSITOR="phoc"; fi
  elif [ -e /dev/fb0 ]; then
    COMPOSITOR="none(fbdev-only)"
  else
    COMPOSITOR="none"
  fi
  case "$COMPOSITOR" in
    phoc|wayland) TEXT_INPUT="zwp_text_input_manager_v3" ;;
    *) TEXT_INPUT="unknown" ;;
  esac
}

probe_hwkbd() {
  local f name
  for f in "$ROOT"/sys/class/input/event*/device/name; do
    [ -r "$f" ] || continue
    name="$(cat "$f" 2>/dev/null || true)"
    case "$name" in
      *gpio_keys*|*sec_key_notifier*) continue ;;   # phone buttons, not a keyboard
      *[Kk]eyboard*|*[Kk]bd*|*USB*[Kk]ey*|*Bluetooth*[Kk]ey*)
        HWKBD="present"; HWKBD_NAME="$name" ;;
    esac
  done
}

# ------------------------------------------------------- applying the document
# NOTE: the schema list is captured first, never piped straight into `grep -q`.
# With `set -o pipefail`, a grep that exits on its first match sends SIGPIPE back
# to the tool it is reading from, which would report a writable schema as absent
# (and made this probe flaky). Capture, then match.
gs_ok() {
  local schemas
  schemas="$(run_tool gsettings list-schemas 2>/dev/null || true)"
  printf '%s\n' "$schemas" | grep -qx "$1"
}
gs_set() {  # schema key value
  if [ "$DRY" = 1 ]; then printf '  would: gsettings set %s %s %s\n' "$1" "$2" "$3"; return 0; fi
  run_tool gsettings set "$1" "$2" "$3" >/dev/null 2>&1
}

apply_keyboard() {
  local enabled auto layout numeric height repeat delay interval clip haptics passthru
  enabled="$(cfg keyboard.enabled)";   auto="$(cfg keyboard.auto_show)"
  layout="$(cfg keyboard.layout)";     numeric="$(cfg keyboard.numeric_layout)"
  height="$(cfg keyboard.height_dp)";  repeat="$(cfg keyboard.key_repeat)"
  delay="$(cfg keyboard.key_repeat_delay_ms)"; interval="$(cfg keyboard.key_repeat_interval_ms)"
  clip="$(cfg keyboard.clipboard)";    haptics="$(cfg keyboard.haptics)"
  passthru="$(cfg keyboard.hardware_passthrough)"

  # --- enable / show-on-focus: the switch phosh's OSK manager watches -------
  if [ "$OSK" = "none" ]; then
    res keyboard.enabled "not_applied:no-osk-installed"
    res keyboard.auto_show "not_applied:no-osk-installed"
  elif gs_ok org.gnome.desktop.a11y.applications; then
    if gs_set org.gnome.desktop.a11y.applications screen-keyboard-enabled "$enabled"; then
      res keyboard.enabled "applied"
    else
      res keyboard.enabled "not_applied:gsettings-write-failed"
    fi
    if [ "$enabled" = "true" ]; then
      if [ "$auto" = "true" ]; then res keyboard.auto_show "applied"; else res keyboard.auto_show "not_applied:manual-only"; fi
    else
      res keyboard.auto_show "not_applied:keyboard-disabled"
    fi
  else
    res keyboard.enabled "not_applied:no-enable-key-on-this-stack"
    res keyboard.auto_show "not_applied:no-enable-key-on-this-stack"
  fi

  # --- layout: compositor input sources -------------------------------------
  if gs_ok org.gnome.desktop.input-sources; then
    if gs_set org.gnome.desktop.input-sources sources "[('xkb', '$layout')]"; then
      res keyboard.layout "applied"
    else
      res keyboard.layout "not_applied:gsettings-write-failed"
    fi
  else
    res keyboard.layout "not_applied:no-input-sources-schema"
  fi

  # --- provider-specific knobs ---------------------------------------------
  if [ "$OSK" = "squeekboard" ]; then
    local home_dir ini
    if [ "$ROOT" = "/" ]; then home_dir="${NUXEL_OSK_HOME:-$HOME}"; else home_dir="$ROOT/home/${NUXEL_OSK_USER:-nuxel}"; fi
    ini="$home_dir/.config/squeekboard/config.ini"
    if [ "$DRY" = 1 ]; then
      printf '  would write %s (layout=phone clipboard=%s)\n' "$ini" "$clip"
      res keyboard.clipboard "dry-run"
    elif mkdir -p "$(dirname "$ini")" 2>/dev/null && {
           printf '[keyboard]\nlayout=phone\nshow-clipboard-button=%s\nshow-emoji-button=%s\nauto-capitalize=%s\n' \
             "$clip" "$enabled" "$numeric" >"$ini"; }; then
      res keyboard.clipboard "applied:config.ini"
    else
      res keyboard.clipboard "not_applied:config-unwritable"
    fi
    res keyboard.height_dp "provider-managed:squeekboard-theme (requested ${height}dp)"
    if [ "$numeric" = "true" ]; then res keyboard.numeric_layout "provider-managed:squeekboard-numeric-view"
    else res keyboard.numeric_layout "not_applied:disabled-by-setting"; fi
  elif [ "$OSK" = "stevia" ]; then
    # stevia 0.54 sizes and lays out from its own provider/theme: there is no
    # user height or layout-file knob. Those two are reported as managed by the
    # provider rather than pretend-applied, and the Settings UI shows that text.
    res keyboard.height_dp "provider-managed:stevia-theme (requested ${height}dp)"
    if [ "$numeric" = "true" ]; then res keyboard.numeric_layout "provider-managed:stevia-numeric-view"
    else res keyboard.numeric_layout "not_applied:disabled-by-setting"; fi
    res keyboard.clipboard "provider-managed:stevia-clipboard"
  else
    res keyboard.height_dp "not_applied:no-osk-installed"
    res keyboard.numeric_layout "not_applied:no-osk-installed"
    res keyboard.clipboard "not_applied:no-osk-installed"
  fi

  # --- key repeat (physical keys + OSK backspace repeat) --------------------
  if gs_ok org.gnome.desktop.peripherals.keyboard; then
    if gs_set org.gnome.desktop.peripherals.keyboard repeat "$repeat" &&
       gs_set org.gnome.desktop.peripherals.keyboard delay "$delay" &&
       gs_set org.gnome.desktop.peripherals.keyboard repeat-interval "$interval"; then
      res keyboard.key_repeat "applied"
    else
      res keyboard.key_repeat "not_applied:gsettings-write-failed"
    fi
  else
    res keyboard.key_repeat "not_applied:no-keyboard-schema"
  fi

  # --- haptics: delegated to the haptics component, never duplicated --------
  if [ "$haptics" = "true" ]; then res keyboard.haptics "delegated:haptics-component"
  else res keyboard.haptics "not_applied:disabled-by-setting"; fi

  # --- physical keyboard passthrough: observed, never grabbed --------------
  if [ "$passthru" = "true" ]; then res keyboard.hardware_passthrough "observed:${HWKBD}"
  else res keyboard.hardware_passthrough "not_applied:disabled-by-setting"; fi

  log "apply root=$ROOT osk=$OSK compositor=$COMPOSITOR enabled=$(res_get keyboard.enabled) layout=$(res_get keyboard.layout)"
}

write_state() {
  local out; out="$(abs "$STATE")"
  if [ "$DRY" = 1 ]; then say "(dry-run: would write $out)"; return 0; fi
  mkdir -p "$(dirname "$out")" 2>/dev/null || true
  {
    echo "schema_version=1"
    echo "updated_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)"
    echo "root=$ROOT"
    echo "document=$(abs "$DOC")"
    echo "osk=$OSK"
    echo "osk_path=${OSK_PATH:-none}"
    echo "compositor=$COMPOSITOR"
    echo "text_input=$TEXT_INPUT"
    echo "hardware_keyboard=$HWKBD"
    echo "hardware_keyboard_name=$HWKBD_NAME"
    for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
             keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
             keyboard.hardware_passthrough; do
      echo "${k}=$(res_get "$k")"
    done
    if [ "$OSK" = "none" ]; then echo "verdict=NO_OSK_INSTALLED"; else echo "verdict=OSK_CONFIGURED"; fi
  } >"$out.tmp.$$" 2>/dev/null && mv -f "$out.tmp.$$" "$out" 2>/dev/null || {
    rm -f "$out.tmp.$$" 2>/dev/null
    die "cannot write $out"
  }
}

json_status() {
  local first=1 k
  printf '{'
  for k in osk osk_path compositor text_input hardware_keyboard document state_file; do
    [ "$first" = 1 ] || printf ','; first=0
    case "$k" in
      osk) printf '"osk":"%s"' "$OSK" ;;
      osk_path) printf '"osk_path":"%s"' "${OSK_PATH:-none}" ;;
      compositor) printf '"compositor":"%s"' "$COMPOSITOR" ;;
      text_input) printf '"text_input":"%s"' "$TEXT_INPUT" ;;
      hardware_keyboard) printf '"hardware_keyboard":"%s"' "$HWKBD" ;;
      document) printf '"document":"%s"' "$(abs "$DOC")" ;;
      state_file) printf '"state_file":"%s"' "$(abs "$STATE")" ;;
    esac
  done
  printf ',"settings":{'
  first=1
  for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
           keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
           keyboard.hardware_passthrough; do
    [ "$first" = 1 ] || printf ','; first=0
    printf '"%s":"%s"' "$k" "$(res_get "$k")"
  done
  printf '}}\n'
}

cmd_apply() {
  load_table
  probe_osk; probe_compositor; probe_hwkbd
  apply_keyboard
  write_state
  if [ "$JSON" = 1 ]; then
    json_status
  else
    say "Nuxel keyboard apply — root=$ROOT"
    say "  osk=$OSK (${OSK_PATH:-none})  compositor=$COMPOSITOR  text_input=$TEXT_INPUT  hardware_keyboard=$HWKBD"
    local k
    for k in keyboard.enabled keyboard.auto_show keyboard.layout keyboard.numeric_layout \
             keyboard.height_dp keyboard.key_repeat keyboard.haptics keyboard.clipboard \
             keyboard.hardware_passthrough; do
      printf '  %-32s %s\n' "$k" "$(res_get "$k")"
    done
    say "  evidence: $(abs "$STATE")"
    if [ "$OSK" = "none" ]; then
      say "  NOTICE: no OSK provider is installed in this root — the Settings switch is reported as not_applied, never as on."
    fi
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
    say "no keyboard state recorded yet ($sf) — run '$SELF_PATH apply'"
    return 1
  fi
  cat "$sf"
  say "# log: $(abs "$LOG")"
  say "# last hop probe page: tools/s10plus/a33/keyboard-probe.html"
}

cmd_set() {   # set <key> <value> — validated, atomic, then re-applied
  local key="${1:-}" value="${2:-}"
  [ -n "$key" ] || die "set needs <key> <value>"
  case "$key" in
    keyboard.enabled|keyboard.auto_show|keyboard.numeric_layout|keyboard.key_repeat|keyboard.haptics|keyboard.clipboard|keyboard.hardware_passthrough)
      case "$value" in true|false) ;; *) die "$key must be true or false (got '$value')" ;; esac ;;
    keyboard.layout)
      [ "${#value}" -ge 2 ] && [ "${#value}" -le 16 ] || die "keyboard.layout must be 2-16 characters" ;;
    keyboard.height_dp)
      case "$value" in ''|*[!0-9]*) die "keyboard.height_dp must be an integer" ;; esac
      [ "$value" -ge 160 ] && [ "$value" -le 560 ] || die "keyboard.height_dp must be 160..560" ;;
    keyboard.key_repeat_delay_ms)
      case "$value" in ''|*[!0-9]*) die "keyboard.key_repeat_delay_ms must be an integer" ;; esac ;;
    keyboard.key_repeat_interval_ms)
      case "$value" in ''|*[!0-9]*) die "keyboard.key_repeat_interval_ms must be an integer" ;; esac ;;
    *) die "unknown keyboard setting '$key' — refusing to write a key the applier cannot honour" ;;
  esac
  mkdir -p "$(dirname "$(abs "$DOC")")" 2>/dev/null || true
  python3 - "$(abs "$DOC")" "$key" "$value" <<'PY' || die "failed to update $(abs "$DOC") atomically"
import json, os, sys, tempfile, time
path, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
doc = {}
if os.path.exists(path):
    try:
        with open(path) as f:
            doc = json.load(f)
    except Exception as exc:
        sys.stderr.write("refusing to modify an unparsable document: %s\n" % exc); sys.exit(3)
if not isinstance(doc, dict):
    sys.exit(3)
if value in ("true", "false"):
    doc[key] = (value == "true")
elif value.isdigit():
    doc[key] = int(value)
else:
    doc[key] = value
doc.setdefault("schema_version", 1)
doc["set_by"] = "user"
doc["updated_at"] = int(time.time())
d = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(dir=d, prefix=".keyboard.", suffix=".json")
with os.fdopen(fd, "w") as f:
    json.dump(doc, f, indent=2); f.write("\n")
os.replace(tmp, path)
PY
  say "set $key=$value in $(abs "$DOC")"
  cmd_apply
}

# ------------------------------------------------------------------ selftest --
KBD_SELFTEST_TMP=""
kbd_selftest_cleanup() { [ -n "${KBD_SELFTEST_TMP:-}" ] && rm -rf "$KBD_SELFTEST_TMP"; }

selftest() {
  local repo fails=0 checks=0
  repo="$(cd "$(dirname "$SELF_PATH")/../../.." && pwd)"
  KBD_SELFTEST_TMP="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-kbd.XXXXXX")" || die "mktemp failed"
  local tmp="$KBD_SELFTEST_TMP"
  trap kbd_selftest_cleanup EXIT INT TERM
  ck() { checks=$((checks+1)); if [ "$1" = 0 ]; then echo "PASS $2"; else echo "FAIL $2"; fails=$((fails+1)); fi; }

  mkdir -p "$tmp/etc/nuxel/keyboard" "$tmp/run" "$tmp/var/log/nuxel" "$tmp/usr/bin" \
           "$tmp/sys/class/input" "$tmp/home/nuxel"

  # 1. missing document -> defaults, no provider, honest verdicts
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  ck $? "apply with no document uses the built-in defaults and exits 0"
  [ -f "$tmp/run/nuxel-keyboard.state" ]; ck $? "the state file is written"
  grep -q '^osk=none$' "$tmp/run/nuxel-keyboard.state"; ck $? "no OSK in this root is reported as osk=none"
  grep -q '^keyboard.enabled=not_applied:no-osk-installed$' "$tmp/run/nuxel-keyboard.state"
  ck $? "keyboard.enabled is not_applied:no-osk-installed (never a fake 'on')"

  # 2. unparsable document -> refused with exit 2, no state written
  rm -f "$tmp/run/nuxel-keyboard.state"
  printf '{ this is not json' >"$tmp/etc/nuxel/keyboard/keyboard.json"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an unparsable document is refused with exit 2"
  [ ! -f "$tmp/run/nuxel-keyboard.state" ]; ck $? "a refused document writes no state"

  # 3. out-of-range value -> refused
  printf '{"schema_version":1,"keyboard.height_dp":9000}' >"$tmp/etc/nuxel/keyboard/keyboard.json"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an out-of-range keyboard.height_dp is refused"

  # 4. shipped document + stub provider + stub gsettings -> applied verdicts
  cp "$repo/configs/nuxel/keyboard/keyboard.json" "$tmp/etc/nuxel/keyboard/keyboard.json"
  cat >"$tmp/usr/bin/gsettings" <<EOF
#!/bin/sh
if [ "\$1" = "list-schemas" ]; then
  echo org.gnome.desktop.a11y.applications
  echo org.gnome.desktop.input-sources
  echo org.gnome.desktop.peripherals.keyboard
  exit 0
fi
echo "\$@" >>"$tmp/gsettings.calls"
exit 0
EOF
  chmod +x "$tmp/usr/bin/gsettings"
  printf '#!/bin/sh\nexit 0\n' >"$tmp/usr/bin/stevia"; chmod +x "$tmp/usr/bin/stevia"
  mkdir -p "$tmp/run/user/1000"; : >"$tmp/run/user/1000/wayland-0"
  WAYLAND_DISPLAY=wayland-0 NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  ck $? "apply with a stevia provider and a writable gsettings exits 0"
  grep -q '^osk=stevia$' "$tmp/run/nuxel-keyboard.state"; ck $? "the provider probe finds stevia"
  grep -q '^keyboard.enabled=applied$' "$tmp/run/nuxel-keyboard.state"; ck $? "enable is applied when the enable key exists"
  grep -q '^keyboard.layout=applied$' "$tmp/run/nuxel-keyboard.state"; ck $? "layout is applied through input-sources"
  grep -q '^keyboard.height_dp=provider-managed:' "$tmp/run/nuxel-keyboard.state"; ck $? "a provider-managed height is reported as provider-managed"
  grep -q '^keyboard.haptics=delegated:haptics-component$' "$tmp/run/nuxel-keyboard.state"; ck $? "haptics is delegated to the haptics component"
  grep -q '^text_input=zwp_text_input_manager_v3$' "$tmp/run/nuxel-keyboard.state"
  ck $? "the text-input protocol is reported as the path this stack uses"
  grep -q 'screen-keyboard-enabled true' "$tmp/gsettings.calls"; ck $? "the enable switch really reached gsettings"

  # 5. set: valid change is durable and re-applied
  NUXEL_ROOT="$tmp" "$SELF_PATH" set keyboard.layout de >/dev/null 2>&1
  ck $? "set keyboard.layout de succeeds"
  python3 -c "import json,sys; sys.exit(0 if json.load(open('$tmp/etc/nuxel/keyboard/keyboard.json'))['keyboard.layout']=='de' else 1)"
  ck $? "the new layout is durable in the document"
  grep -q "('xkb', 'de')" "$tmp/gsettings.calls"; ck $? "the new layout reached the compositor input sources"

  # 6. set: unknown key and bad value are refused
  NUXEL_ROOT="$tmp" "$SELF_PATH" set keyboard.facepalm true >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an unknown setting key is refused"
  NUXEL_ROOT="$tmp" "$SELF_PATH" set keyboard.height_dp 9000 >/dev/null 2>&1
  [ $? = 2 ]; ck $? "an out-of-range height is refused at set time"

  # 7. dry-run writes no state
  rm -f "$tmp/run/nuxel-keyboard.state"
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply --dry-run >/dev/null 2>&1
  ck $? "dry-run exits 0"
  [ ! -f "$tmp/run/nuxel-keyboard.state" ]; ck $? "dry-run writes no state file"

  # 8. the tool carries no flash/bootloader primitive (mission invariant)
  local bad_pat="he""imdall|od""in|fast""boot|/dev/bl""ock/"
  if grep -Eqi "$bad_pat" "$SELF_PATH"; then
    ck 1 "the applier contains no flash/bootloader primitive"
  else
    ck 0 "the applier contains no flash/bootloader primitive"
  fi

  # Dump the evidence file of a final, non-dry apply so an operator (and the
  # acceptance test) can see the exact per-setting verdict strings.
  NUXEL_ROOT="$tmp" "$SELF_PATH" apply >/dev/null 2>&1
  echo "--- evidence file /run/nuxel-keyboard.state (stevia fixture) ---"
  sed -n '1,40p' "$tmp/run/nuxel-keyboard.state" 2>/dev/null || echo "(no state file)"

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
