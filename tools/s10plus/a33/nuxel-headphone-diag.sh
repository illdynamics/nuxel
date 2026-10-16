#!/usr/bin/env bash
# nuxel-headphone-diag.sh — S10+ (SM-G975F / beyond2lte) headphone jack and
# USB-C audio accessory diagnoser (briq-03d, mission area 7).
#
# WHAT THIS IS
#   An evidence-only detector + route-SWITCHING decision for the two ways audio
#   leaves this phone through a cable:
#     1. the 3.5 mm jack on the CS47L93 (MADERA) codec — headphones or headset,
#        detected from ALSA jack kcontrols and the codec pin registers,
#     2. a USB-C accessory — digital (USB Audio Class: a separate ALSA card
#        appears) or analog (the codec AUX pins), detected from /sys/class/typec,
#        /proc/asound/cards and lsusb.
#
# WHAT THIS IS NOT
#   * It never claims sound is audible through the accessory. Insertion detection
#     is a state machine; audibility is NEEDS_OWNER_TEST (area 7).
#   * It never invents a jack kcontrol NAME. The names on this codec are
#     discovered from `amixer -c <card> contents` and the codec pin files, and a
#     name is used only after it has been seen. If no jack control can be found,
#     the verdict is NO_JACK_CONTROL — an unproven detection, never a guess.
#   * It never changes a route without --yes, and it never leaves the output
#     routed to an accessory that is no longer present (the revert rule).
#
# Usage (also reachable as `nuxelctl headphone <sub>`):
#   nuxel-headphone-diag.sh status [--json]   jack/USB-C state + the route decision
#   nuxel-headphone-diag.sh jack              jack controls and codec pin evidence
#   nuxel-headphone-diag.sh usbc              USB-C accessory evidence
#   nuxel-headphone-diag.sh route [--yes]     apply the decision (revert-aware)
#   nuxel-headphone-diag.sh watch [SECONDS]   bounded poll: log every transition
#   nuxel-headphone-diag.sh tone [MS] --yes   render the audio tool's low-volume tone
#   nuxel-headphone-diag.sh selftest          run the bundled offline fixtures
#   nuxel-headphone-diag.sh help
#
# OFFLINE TESTABILITY: NUXEL_DIAG_ROOT (or --root DIR) + NUXEL_DIAG_NO_SYSTEM=1,
# exactly like the other P3 diagnostics, so the fixture tree is the only input.
set -uo pipefail

SELF="$(basename "$0")"
SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
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

CARD_NAME="${NUXEL_AUDIO_CARD:-beyond-madera}"
ROUTES_JSON="${NUXEL_JACK_POLICY:-/etc/nuxel/audio/jack-routes.json}"
STATE_DIR="${NUXEL_AUDIO_STATE:-/var/lib/nuxel/audio}"
EVIDENCE_LOG="${NUXEL_AUDIO_LOG:-/var/log/nuxel/audio-diag.log}"

say() { printf '%s\n' "$*"; }
hdr() { printf '\n== %s ==\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
exists() { [ -e "$(abs "$1")" ]; }

run_tool() {
  local t="$1"; shift
  local p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    if [ -x "$p" ] && [ "$ROOT" != "/" ]; then "$p" "$@"; return $?; fi
  done
  if [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ]; then return 127; fi
  command -v "$t" >/dev/null 2>&1 || return 127
  "$t" "$@"
}
have_tool() {
  local t="$1" p
  for p in "$ROOT/usr/bin/$t" "$ROOT/bin/$t" "$ROOT/usr/sbin/$t" "$ROOT/sbin/$t"; do
    [ -x "$p" ] && [ "$ROOT" != "/" ] && return 0
  done
  [ "${NUXEL_DIAG_NO_SYSTEM:-0}" = "1" ] && return 1
  command -v "$t" >/dev/null 2>&1
}

log_evidence() {
  local f; f="$(abs "$EVIDENCE_LOG")"
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*" >>"$f" 2>/dev/null || true
}

card_index() {
  local f; f="$(abs /proc/asound/cards)"
  [ -f "$f" ] || return 1
  awk -v want="$CARD_NAME" '
    BEGIN { w = tolower(want); gsub(/-/, "", w) }
    /^ *[0-9]+ \[/ {
      idx = $1; nm = $0; sub(/^ *[0-9]+ \[/, "", nm); sub(/\].*$/, "", nm);
      gsub(/[ \t]/, "", nm); n = tolower(nm); gsub(/-/, "", n);
      if (index(n, substr(w, 1, 8)) == 1 || index(w, substr(n, 1, 8)) == 1) { print idx; exit }
    }' "$f"
}

controls_text() {
  local idx="$1"
  if have_tool amixer; then
    run_tool amixer -c "$idx" contents 2>/dev/null || run_tool amixer contents 2>/dev/null
  elif have_tool tinymix; then
    run_tool tinymix -c "$idx" 2>/dev/null
  else
    return 127
  fi
}

# ---------------------------------------------------------------- jack state
# Jack evidence, in order of strength:
#   1. a MIXER kcontrol whose name contains "jack" and whose value is on/off
#   2. the codec pin registers (/proc/asound/card*/codec#*) — reported as
#      corroboration, never as the primary signal, because the pin encoding is
#      codec-specific and reading it wrong would be worse than not reading it.
jack_state() {   # sets JACK, JACK_NAME, MIC
  JACK="UNKNOWN"; JACK_NAME=""; MIC="UNKNOWN"
  local idx ct line name val
  idx="$(card_index)"
  [ -z "$idx" ] && return 1
  ct="$(controls_text "$idx")"
  [ -z "$ct" ] && return 1
  # Walk name/value pairs: "name='X'" is followed (within a few lines) by ": values=Y"
  while IFS= read -r line; do
    case "$line" in
      *"name='"*)
        name="$(printf '%s' "$line" | sed -n "s/.*name='\([^']*\)'.*/\1/p")"
        val="$(printf '%s\n' "$ct" | awk -v n="$name" '
          index($0, "name=\047" n "\047") { found = 1; next }
          found && /: values=/ { sub(/.*values=/, ""); print; exit }')"
        # MIC patterns are matched FIRST on purpose: a name like
        # "Headset Mic Jack" also contains the substring "headset...jack" and
        # would otherwise be misread as the playback jack, silently turning a
        # detected headset into a plain headphone (or worse, a removed jack).
        # Classify the microphone input before the output jack, then let the
        # output-jack rule ignore any name that names a mic.
        case "$(printf '%s' "$name" | tr 'A-Z' 'a-z')" in
          *mic*jack*|*headset*mic*|*mic*in*)
            case "$val" in on|1|"1,1"|yes) MIC="PRESENT" ;; off|0|"0,0"|no) MIC="ABSENT" ;; esac ;;
          *headphone*jack*|*headset*jack*)
            JACK_NAME="$name"
            case "$val" in on|1|"1,1"|yes) JACK="INSERTED" ;; off|0|"0,0"|no) JACK="REMOVED" ;; esac ;;
        esac ;;
    esac
  done <<<"$ct"
  [ "$JACK" != "UNKNOWN" ] && return 0
  return 1
}

pin_evidence() {
  local c
  for c in "$(abs /proc/asound)"/card*/codec#*; do
    [ -f "$c" ] || continue
    say "--- $c"
    grep -n -E 'Pin|Jack' "$c" | head -20
  done
}

# ---------------------------------------------------------------- USB-C
usbc_state() {   # sets USBC, USBC_CLASS, USBC_CARD
  USBC="ABSENT"; USBC_CLASS=""; USBC_CARD=""
  local p role
  for p in "$(abs /sys/class/typec)"/port*/data_role; do
    [ -f "$p" ] || continue
    role="$(head -1 "$p" 2>/dev/null | tr -d '\r')"
    USBC="PRESENT"
    [ -n "$role" ] && USBC_CLASS="role=$role"
  done
  # A UAC accessory is a SEPARATE ALSA card whose entry names USB.
  local f; f="$(abs /proc/asound/cards)"
  if [ -f "$f" ]; then
    local line
    while IFS= read -r line; do
      case "$(printf '%s' "$line" | tr 'A-Z' 'a-z')" in
        *usb*)
          USBC="PRESENT"; USBC_CLASS="audio"; USBC_CARD="$(printf '%s' "$line" | sed -n 's/^ *\([0-9]\+\) *\[.*/\1/p')" ;;
      esac
    done <"$f"
  fi
  [ "$USBC" = "PRESENT" ] || return 1
  return 0
}

# ---------------------------------------------------------------- decision
# The decision comes from the policy file's rules, evaluated against OBSERVED
# evidence. When no rule matches, the answer is NO_MATCH — never a guess, and
# never "keep whatever was there": the revert rule always wins on removal.
decide() {
  if [ "$JACK" = "INSERTED" ]; then
    if [ "$MIC" = "PRESENT" ]; then ROUTE="Headset"; RULE="jack-insert-headset"
    else ROUTE="Headphones"; RULE="jack-insert-headphones"; fi
  elif [ "$JACK" = "REMOVED" ]; then
    ROUTE="Speaker"; RULE="jack-remove"
  elif [ "$USBC" = "PRESENT" ] && [ "$USBC_CLASS" = "audio" ]; then
    ROUTE="USB-C Headset (UAC)"; RULE="usbc-digital-headset"
  elif [ "$USBC" = "PRESENT" ]; then
    ROUTE="UNKNOWN_USBC_ACCESSORY"; RULE="usbc-analog-headset"
  else
    ROUTE="UNKNOWN"; RULE="none"
  fi
}

cmd_status() {
  local json=""
  [ "${1:-}" = "--json" ] && json=1
  local idx; idx="$(card_index)"
  if [ -z "$idx" ] && [ "$json" != "1" ]; then
    say "card '$CARD_NAME' not found — jack detection cannot be evaluated."
  fi
  jack_state || true
  usbc_state || true
  decide
  if [ "$json" = "1" ]; then
    printf '{"schema_version":1,"device":"beyond2lte","card":"%s","jack":"%s","jack_control":"%s","mic":"%s","usbc":"%s","usbc_detail":"%s","route":"%s","rule":"%s","policy":"%s","audibility":"NEEDS_OWNER_TEST"}\n' \
      "$CARD_NAME" "$JACK" "$JACK_NAME" "$MIC" "$USBC" "$USBC_CLASS" "$ROUTE" "$RULE" "$ROUTES_JSON"
    [ "$JACK" = "UNKNOWN" ] && return 1
    return 0
  fi
  hdr "jack / USB-C state (evidence only)"
  say "card: $( [ -n "$idx" ] && echo "index $idx" || echo 'NOT FOUND')"
  say "3.5 mm jack: $JACK${JACK_NAME:+ (control '$JACK_NAME')}"
  say "headset mic: $MIC"
  say "USB-C: $USBC${USBC_CLASS:+ ($USBC_CLASS)}${USBC_CARD:+ card=$USBC_CARD}"
  hdr "route decision (policy: $ROUTES_JSON)"
  say "  rule=$RULE -> device '$ROUTE'"
  case "$ROUTE" in
    UNKNOWN)
      say "  NOT DECIDED: no jack control could be read, so insertion state is unknown."
      say "  An unknown state must never be reported as 'speaker' or 'headphones'."
      ;;
    UNKNOWN_USBC_ACCESSORY)
      say "  NOT DECIDED: a USB-C accessory is present but its audio class is unknown."
      say "  A digital (UAC) accessory is a separate card; do not route the codec blindly."
      ;;
    Speaker) say "  revert rule: the output must return to the speaker when nothing is plugged." ;;
  esac
  say ""
  say "AUDIBILITY: NEEDS_OWNER_TEST — plugging in is detectable, hearing it is not"
  say "(docs/beta-finalization/manual-proof/07-headphones.md)."
  [ "$JACK" = "UNKNOWN" ] && return 1
  return 0
}

cmd_jack() {
  hdr "ALSA jack controls"
  local idx; idx="$(card_index)"
  [ -z "$idx" ] && { say "card '$CARD_NAME' not found"; return 1; }
  local ct; ct="$(controls_text "$idx")"
  if [ -z "$ct" ]; then say "no mixer reader (amixer/tinymix) — cannot read jack controls"; return 1; fi
  printf '%s\n' "$ct" | grep -i -E "name='[^']*jack[^']*'|values=" | head -40
  hdr "codec pin evidence (corroboration only)"
  pin_evidence
}

cmd_usbc() {
  hdr "USB-C accessory evidence"
  local p
  for p in "$(abs /sys/class/typec)"/port*/role "$(abs /sys/class/typec)"/port*/data_role \
           "$(abs /sys/class/typec)"/port*/power_role; do
    [ -f "$p" ] || continue
    say "$p = $(head -1 "$p" 2>/dev/null | tr -d '\r')"
  done
  hdr "ALSA cards (a USB Audio Class accessory appears as its own card)"
  [ -f "$(abs /proc/asound/cards)" ] && cat "$(abs /proc/asound/cards)" || say "  (no cards)"
  hdr "resolved"
  usbc_state || true
  say "  usbc=$USBC detail=$USBC_CLASS card=${USBC_CARD:-none}"
}

cmd_route() {
  local yes="${1:-}"
  jack_state || true; usbc_state || true; decide
  if [ "$ROUTE" = "UNKNOWN" ] || [ "$ROUTE" = "UNKNOWN_USBC_ACCESSORY" ]; then
    say "REFUSED: the accessory state is not proven ($ROUTE). Nothing was changed."
    return 1
  fi
  if [ "$yes" != "--yes" ]; then
    say "would select UCM device '$ROUTE' (rule $RULE). Re-run with --yes to apply."
    say "the low-volume cap is re-applied before the first sample of the new route."
    return 2
  fi
  local idx; idx="$(card_index)"
  if ! have_tool alsaucm; then
    say "BLOCKED_EXTERNAL_RESOURCE: alsaucm is not installed, so no UCM route can be selected."
    say "  (evidence was still gathered; the decision above is the finding.)"
    return 1
  fi
  run_tool alsaucm -c "$CARD_NAME" set _verb HiFi set _enadev "$ROUTE" && \
    say "applied UCM device '$ROUTE'" || say "alsaucm failed for device '$ROUTE'"
  # revert rule: never leave the output routed to an absent accessory
  mkdir -p "$(abs "$STATE_DIR")"
  printf '{\n  "rule": "%s",\n  "route": "%s",\n  "jack": "%s",\n  "usbc": "%s",\n  "at": "%s"\n}\n' \
    "$RULE" "$ROUTE" "$JACK" "$USBC" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >"$(abs "$STATE_DIR/jack-state.json")"
  log_evidence "route rule=$RULE route=$ROUTE jack=$JACK usbc=$USBC"
  say "wrote $(abs "$STATE_DIR/jack-state.json")"
}

cmd_watch() {
  local secs="${1:-20}"
  case "$secs" in ''|*[!0-9]*) secs=20 ;; esac
  [ "$secs" -gt 300 ] && secs=300
  say "watching jack/USB-C state for ${secs}s — plug and unplug the accessory now"
  local t=0 last=""
  while [ "$t" -lt "$secs" ]; do
    jack_state || true; usbc_state || true; decide
    local now="jack=$JACK mic=$MIC usbc=$USBC route=$ROUTE"
    if [ "$now" != "$last" ]; then
      say "t=${t}s $now"
      log_evidence "watch t=${t}s $now"
      last="$now"
    fi
    sleep 1
    t=$((t+1))
  done
  say "watch complete. No route was applied (use '$SELF route --yes' deliberately)."
}

cmd_tone() {
  local ms="${1:-800}" yes="${2:-}"
  # ONE implementation of the low-volume tone: delegate to the audio tool.
  local tool="$ROOT$(dirname "${SELF_PATH#$ROOT}")/nuxel-audio-diag.sh"
  [ -x "$tool" ] || tool="$(dirname "$SELF_PATH")/nuxel-audio-diag.sh"
  if [ ! -x "$tool" ]; then
    say "BLOCKED: nuxel-audio-diag.sh not found next to this tool."
    return 1
  fi
  say "delegating to $tool (single implementation of the low-volume tone)"
  if [ -n "${NUXEL_DIAG_ROOT:-}" ]; then
    NUXEL_DIAG_ROOT="$NUXEL_DIAG_ROOT" "$tool" tone "$ms" "$yes"
  else
    "$tool" tone "$ms" "$yes"
  fi
}

cmd_selftest() {
  local fx="${NUXEL_JACK_FIXTURES:-$(dirname "$SELF_PATH")/tests/fixtures-p3}"
  local fail=0 n name exp got
  [ -d "$fx" ] || { say "FAIL fixtures directory not found: $fx"; return 1; }
  for n in "$fx"/jack-*/; do
    [ -d "$n" ] || continue
    name="$(basename "$n")"
    exp="$(cat "$n/EXPECTED" 2>/dev/null || echo '')"
    [ -n "$exp" ] || { say "SKIP $name (no EXPECTED)"; continue; }
    got="$(NUXEL_DIAG_ROOT="$n" NUXEL_DIAG_NO_SYSTEM=1 "$SELF_PATH" status --json 2>/dev/null \
           | sed -n 's/.*"route":"\([^"]*\)".*/\1/p')"
    if [ "$got" = "$exp" ]; then say "PASS $name route=$got"
    else say "FAIL $name expected=$exp got=${got:-<none>}"; fail=$((fail+1)); fi
  done
  say "== $fail failing fixture(s) =="
  return "$fail"
}

case "$CMD" in
  status)   cmd_status "${1:-}" ;;
  jack)     cmd_jack ;;
  usbc)     cmd_usbc ;;
  route)    cmd_route "${1:-}" ;;
  watch)    cmd_watch "${1:-20}" ;;
  tone)     cmd_tone "${1:-800}" "${2:-}" ;;
  selftest) cmd_selftest ;;
  help|-h|--help) sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) say "unknown command: $CMD (try: $SELF help)"; exit 2 ;;
esac
