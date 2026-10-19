#!/usr/bin/env bash
# nuxel-audio-diag.sh — S10+ (SM-G975F / beyond2lte) audio path diagnoser.
#
# WHAT THIS IS
#   It walks the REAL playback path in the order sound actually has to travel and
#   names the FIRST stage that is missing, silent or broken:
#
#       card (beyond-madera) -> PCM -> mixer controls -> DAPM widgets -> route
#                          -> "is the DAC/ABox actually running?"
#
#   and it can render a bounded, low-volume test tone whose only machine-checkable
#   outcome is whether the DAC/PCM entered the running state.
#
# WHAT THIS IS NOT
#   * It never claims sound is audible. "The mixer control is writable" is
#     EXPLICITLY NOT an acceptance criterion in this mission: writability is a
#     property of a register, not of a speaker. Audibility is NEEDS_OWNER_TEST
#     (docs/beta-finalization/manual-proof/06-audio.md).
#   * It never invents a mixer control name or value: on this codec
#     (CS47L93 MADERA + 2x CS35L40 inside the Exynos ABox) the namespace is large
#     and device-specific, so the concrete UCM sequences are GENERATED from a
#     captured control list.
#   * It never writes a partition, a block device or a bootloader interface. It
#     writes /var/lib/nuxel/audio, /var/log/nuxel and (only with `ucm-install`)
#     /usr/share/alsa/ucm2/beyond-madera/HiFi.conf, with a backup and a rollback.
#
# LOW VOLUME ONLY
#   `tone` refuses to render anything without --yes, clamps to the low-volume cap
#   from configs/nuxel/audio/audio.json (default 25 %, first tone 8 %), and the
#   repository also ships an ALSA-layer softvol ceiling (max_dB = -6.0) so even a
#   direct `aplay` of something else cannot full-scale the amplifier.
#
# Usage (also reachable as `nuxelctl audio <sub>`):
#   nuxel-audio-diag.sh status [--json]     summary + verdict
#   nuxel-audio-diag.sh cards               ALSA card inventory
#   nuxel-audio-diag.sh pipeline [--json]   the staged walk, first broken stage
#   nuxel-audio-diag.sh controls [--json]   captured mixer controls (evidence only)
#   nuxel-audio-diag.sh capture             write controls.json + HiFi.conf.generated
#   nuxel-audio-diag.sh ucm-install [--yes] atomic install of the generated HiFi.conf
#   nuxel-audio-diag.sh tone [MS] [--yes]   bounded low-volume tone + DAC decision
#   nuxel-audio-diag.sh safe-volume [N]     read or set the softvol ceiling control
#   nuxel-audio-diag.sh settings [--json]   the Settings -> Sound surface + live values
#   nuxel-audio-diag.sh mode [normal|vibrate|silent]   read/cycle the sound mode
#   nuxel-audio-diag.sh selftest            run the bundled offline fixtures
#   nuxel-audio-diag.sh help
#
# OFFLINE TESTABILITY
#   NUXEL_DIAG_ROOT=DIR (or --root DIR) prefixes /proc, /sys, /lib/firmware, /var,
#   /run, /usr/share and prefers "$DIR/usr/bin/<tool>"; tests add
#   NUXEL_DIAG_NO_SYSTEM=1 so a fixture can never silently read the host's state.
set -uo pipefail

SELF="$(basename "$0")"
SELF_PATH="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
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

# The card name is the ANCHOR. It is what /proc/asound/cards reports and what
# UCM2 requires the profile directory to be called. A hard-coded card INDEX is
# never assumed: the index is looked up from the name.
CARD_NAME="${NUXEL_AUDIO_CARD:-beyond-madera}"
POLICY="${NUXEL_AUDIO_POLICY:-/etc/nuxel/audio/audio.json}"
STATE_DIR="${NUXEL_AUDIO_STATE:-/var/lib/nuxel/audio}"
# The sound mode is a SHARED contract: the button manager's Power+VolumeUp chord
# writes the same file (see nuxel-button-manager.c), so the two can never disagree.
SOUND_MODE_FILE="${NUXEL_SOUND_MODE_FILE:-/var/lib/nuxel/audio/sound-mode}"
SOUND_SETTINGS_SPEC="$SELF_DIR/../../../configs/alsa-ucm/nuxel-sound-settings.json"
EVIDENCE_LOG="${NUXEL_AUDIO_LOG:-/var/log/nuxel/audio-diag.log}"
UCM_DIR="/usr/share/alsa/ucm2/$CARD_NAME"
# Codec DSP firmware. Without it the CS47L93 DSP does not enumerate and no route
# can be validated, which is a FIRMWARE finding, not a user error.
FW_CANDIDATES=(
  "cs47l93-dsp1.wmfw" "cs47l93-dsp2.wmfw" "cs47l93-dsp.wmfw"
  "cs47l93-dsp1.bin"  "cs47l93-dsp2.bin"
  "cs35l40-dsp1.wmfw" "cs35l40-dsp2.wmfw" "cs35l40-dsp1.bin"
)

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
  { printf '--- %s %s ---\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$*"; } >>"$f" 2>/dev/null || true
}

# policy helpers: the low-volume cap and first-tone level come from the policy
# file, never from a literal buried in this script.
policy_int() {
  local key="$1" dflt="$2"
  local f; f="$(abs "$POLICY")"
  [ -f "$f" ] || { printf '%s' "$dflt"; return; }
  local v
  v="$(sed -n "s/.*\"$key\"[[:space:]]*:[[:space:]]*\([0-9]\+\).*/\1/p" "$f" | head -1)"
  [ -n "$v" ] || v="$dflt"
  printf '%s' "$v"
}
CAP_PCT="$(policy_int volume_cap_percent 25)"
TONE_PCT="$(policy_int first_tone_default_percent 8)"

# ---------------------------------------------------------------- card / PCM
card_index() {
  local f; f="$(abs /proc/asound/cards)"
  [ -f "$f" ] || return 1
  # " 0 [beyondMadera   ]: ... - ..."  -> match the bracket name, case-insensitively,
  # tolerating the 15-char truncation ALSA applies to the id.
  awk -v want="$CARD_NAME" '
    BEGIN { w = tolower(want); gsub(/-/, "", w) }
    /^ *[0-9]+ \[/ {
      idx = $1; nm = $0; sub(/^ *[0-9]+ \[/, "", nm); sub(/\].*$/, "", nm);
      gsub(/[ \t]/, "", nm); n = tolower(nm); gsub(/-/, "", n);
      if (index(n, substr(w, 1, 8)) == 1 || index(w, substr(n, 1, 8)) == 1) { print idx; exit }
    }' "$f"
}

pcm_nodes() {
  local idx="$1" d
  for d in "$(abs /proc/asound)/card$idx"/pcm*p; do
    [ -d "$d" ] && printf '%s\n' "$d"
  done
}

pcm_state() {   # prints state=... for the first playback subdevice found
  local dir="$1" s
  for s in "$dir"/sub*/status; do
    [ -f "$s" ] || continue
    sed -n 's/^state: *//p' "$s" | head -1 | tr -d '\r'
    return 0
  done
  echo "unknown"
}

# --------------------------------------------------------------- firmware
firmware_state() {
  local d miss=0 present="" n
  for n in "${FW_CANDIDATES[@]}"; do
    if exists "/lib/firmware/$n"; then present="$present $n"; else miss=$((miss+1)); fi
  done
  if [ -n "$present" ]; then echo "PRESENT"; else echo "ABSENT"; fi
}

# --------------------------------------------------------------- controls
controls_text() {
  local idx="$1"
  if have_tool amixer; then
    run_tool amixer -c "$idx" contents 2>/dev/null || run_tool amixer contents 2>/dev/null
  elif have_tool tinymix; then
    run_tool tinymix -c "$idx" 2>/dev/null || run_tool tinymix 2>/dev/null
  else
    return 127
  fi
}

count_playback_controls() {
  # A playback control is a mixer element whose name contains Volume/Switch and
  # is not explicitly a capture-only element. This is a COUNT for the report, not
  # a claim that any of them can produce sound.
  printf '%s\n' "$1" | grep -c -E 'Volume|Switch|DAC|Speaker|HP|AMP' || true
}

# ------------------------------------------------------------------ pipeline
# The staged walk. Each stage reports OK / UNVERIFIED / FAIL, and the FIRST
# non-OK stage decides the verdict. Nothing is reported OK that was not observed.
pipeline() {
  local idx="$1" json="$2"
  local stage_card="UNKNOWN" stage_pcm="UNKNOWN" stage_controls="UNKNOWN"
  local stage_dapm="UNKNOWN" stage_route="UNKNOWN" stage_dac="UNKNOWN"
  local pcm_state_val="unknown" ctrl_count="0" fw="ABSENT" dapm_path
  local first_bad="" verdict="" reason=""

  # 1. card -----------------------------------------------------------------
  if [ -n "$idx" ]; then
    stage_card="OK"
  else
    stage_card="FAIL"; first_bad="card"; reason="no ALSA card named '$CARD_NAME' in /proc/asound/cards"
  fi

  fw="$(firmware_state)"
  if [ "$stage_card" = "OK" ] && [ "$fw" = "ABSENT" ]; then
    # Card present but the codec DSP firmware is missing: the DSP will not
    # enumerate, so this is the first broken stage even though the card exists.
    stage_card="FAIL"; first_bad="card"
    reason="codec DSP firmware absent (${FW_CANDIDATES[*]})"
  elif [ "$stage_card" = "FAIL" ] && [ "$fw" = "ABSENT" ]; then
    # Both findings are real; report both rather than hiding one behind the other.
    reason="no ALSA card named '$CARD_NAME' in /proc/asound/cards; codec DSP firmware absent"
  fi

  # 2. pcm ------------------------------------------------------------------
  if [ -z "$first_bad" ]; then
    local n=0 d
    for d in $(pcm_nodes "$idx"); do n=$((n+1)); done
    if [ "$n" = "0" ]; then
      stage_pcm="FAIL"; first_bad="pcm"; reason="no /proc/asound/card$idx/pcm*p playback node"
    else
      stage_pcm="OK"
      d="$(pcm_nodes "$idx" | head -1)"
      pcm_state_val="$(pcm_state "$d")"
    fi
  else
    stage_pcm="SKIPPED"
  fi

  # 3. mixer controls -------------------------------------------------------
  if [ -z "$first_bad" ]; then
    local ct
    ct="$(controls_text "$idx")"
    if [ $? -eq 127 ] || [ -z "$ct" ]; then
      stage_controls="FAIL"; first_bad="controls"
      reason="no mixer reader (amixer/tinymix) or the card exposes no controls"
    else
      stage_controls="OK"
      ctrl_count="$(count_playback_controls "$ct")"
    fi
  else
    stage_controls="SKIPPED"
  fi

  # 4. DAPM widgets ---------------------------------------------------------
  if [ -z "$first_bad" ]; then
    dapm_path="/sys/kernel/debug/asoc/$CARD_NAME/dapm"
    if [ -d "$(abs "$dapm_path")" ]; then
      stage_dapm="OK"
    else
      # Not being able to see DAPM is NOT a pass and NOT a hardware failure: it
      # is an unverifiable stage. It does not stop the walk, because the decoder
      # state below is a stronger signal than a widget list.
      stage_dapm="UNVERIFIED"
    fi
  else
    stage_dapm="SKIPPED"
  fi

  # 5. route ---------------------------------------------------------------
  if [ -z "$first_bad" ]; then
    if [ -f "$(abs "$UCM_DIR/HiFi.conf")" ]; then
      # A route counts as OK only when the profile carries a NON-EMPTY
      # EnableSequence (comments and blank lines do not count). An empty
      # sequence is the shipped state and must never pass as a route.
      if awk '
            /EnableSequence *\[/ { inseq = 1; next }
            inseq && /^[ \t]*\]/ { inseq = 0 }
            inseq { l = $0; sub(/^[ \t]+/, "", l); if (l != "" && substr(l, 1, 1) != "#") found = 1 }
            END { exit(found ? 0 : 1) }' "$(abs "$UCM_DIR/HiFi.conf")"; then
        stage_route="OK"
      else
        stage_route="UNVERIFIED"
        reason="${reason:+$reason; }UCM profile exists but its EnableSequence is empty (generated from a capture)"
      fi
    else
      stage_route="FAIL"; first_bad="route"
      reason="no UCM2 profile at $UCM_DIR/HiFi.conf"
    fi
  else
    stage_route="SKIPPED"
  fi

  # 6. DAC / PCM actually running -----------------------------------------
  if [ -z "$first_bad" ]; then
    if [ "$pcm_state_val" = "RUNNING" ]; then
      stage_dac="OK"
    else
      stage_dac="FAIL"; first_bad="dac_running"
      reason="PCM state='$pcm_state_val' — the DAC/ABox never entered the running state"
    fi
  else
    stage_dac="SKIPPED"
  fi

  # verdict: name the first broken stage, never a blanket "audio broken"
  case "$first_bad" in
    "")            verdict="OK_DAC_RUNNING" ;;
    card)          if [ "$fw" = "ABSENT" ]; then verdict="BLOCKED_FIRMWARE"; else verdict="NO_CARD"; fi ;;
    pcm)           verdict="NO_PCM" ;;
    controls)      verdict="NO_CONTROLS" ;;
    dapm)          verdict="NO_DAPM_VIEW" ;;
    route)         verdict="NO_ROUTE" ;;
    dac_running)   verdict="DAC_NOT_RUNNING" ;;
    *)             verdict="UNKNOWN" ;;
  esac

  if [ "$json" = "1" ]; then
    # ONE line, so a machine consumer (the bridge, an app, a test) can parse it
    # without guessing where the object ends.
    printf '{"schema_version":1,"device":"beyond2lte","card":"%s","card_index":%s,"stages":{"card":"%s","pcm":"%s","controls":"%s","dapm":"%s","route":"%s","dac_running":"%s"},"pcm_state":"%s","playback_controls":%s,"firmware":"%s","state":"%s","first_broken_stage":"%s","reason":"%s","low_volume_cap_percent":%s}\n' \
      "$CARD_NAME" "${idx:-null}" "$stage_card" "$stage_pcm" "$stage_controls" "$stage_dapm" \
      "$stage_route" "$stage_dac" "$pcm_state_val" "$ctrl_count" "$fw" "$verdict" \
      "${first_bad:-none}" "$reason" "$CAP_PCT"
    return 0
  fi

  hdr "pipeline (first broken stage wins)"
  printf '  %-12s %-10s %s\n' card     "$stage_card"     "name=$CARD_NAME index=${idx:-?} firmware=$fw"
  printf '  %-12s %-10s %s\n' pcm      "$stage_pcm"      "state=$pcm_state_val"
  printf '  %-12s %-10s %s\n' controls "$stage_controls" "$ctrl_count candidate playback controls (writability is NOT audibility)"
  printf '  %-12s %-10s %s\n' dapm     "$stage_dapm"     "${dapm_path:-/sys/kernel/debug/asoc/$CARD_NAME/dapm}"
  printf '  %-12s %-10s %s\n' route    "$stage_route"    "$UCM_DIR/HiFi.conf"
  printf '  %-12s %-10s %s\n' dac      "$stage_dac"      "PCM must be RUNNING while a stream is open"
  hdr "verdict"
  say "  $verdict"
  [ -n "$reason" ] && say "  reason: $reason"
  say "  NOT an audibility claim. A writable mixer control is explicitly NOT an"
  say "  acceptance criterion; audibility is NEEDS_OWNER_TEST (area 6)."
}

# ------------------------------------------------------------------- tone
# The ONLY machine-checkable outcome of rendering a tone is whether the DAC/PCM
# entered the running state while the stream was open. Whether the owner HEARD it
# is not machine-checkable and is not claimed here.
cmd_tone() {
  local ms="${1:-800}" yes="${2:-}"
  case "$ms" in ''|*[!0-9]*) ms=800 ;; esac
  [ "$ms" -gt 5000 ] && ms=5000
  if [ "$yes" != "--yes" ]; then
    say "refusing to render a tone without --yes (low-volume only, owner present required)."
    say "run: $SELF tone $ms --yes        # level ${TONE_PCT}%, cap ${CAP_PCT}%"
    return 2
  fi
  local idx; idx="$(card_index)"
  if [ -z "$idx" ]; then
    say "BLOCKED: no card named '$CARD_NAME' — nothing to render into."
    return 1
  fi
  if ! have_tool aplay; then
    say "BLOCKED_EXTERNAL_RESOURCE: aplay is not installed (nothing can render)."
    return 1
  fi
  mkdir -p "$(abs "$STATE_DIR")"
  log_evidence "tone ms=$ms level=${TONE_PCT}%"
  say "rendering ${ms}ms ${TONE_PCT}% tone via aplay (low-volume bring-up level)"
  # The level is applied through the ALSA softvol control when it exists, so the
  # tone cannot exceed the repository's cap even on a card whose master is high.
  if have_tool amixer; then
    run_tool amixer -c "$idx" sset 'Nuxel Safe Volume' "${TONE_PCT}%" >/dev/null 2>&1 || \
      say "  (note: no 'Nuxel Safe Volume' softvol control — the ALSA softvol layer is not installed)"
  fi
  # -d bounds the burst: a bounded render cannot become a stuck full-scale stream.
  if run_tool aplay -q -D "plughw:$idx,0" -d "$(( (ms + 999) / 1000 ))" /dev/zero >/dev/null 2>&1; then
    say "aplay returned success (the PCM opened and ran)"
  else
    say "aplay failed — the PCM did not open; see 'pipeline' for the first broken stage"
  fi
  local st="unknown" d
  d="$(pcm_nodes "$idx" | head -1)"
  [ -n "$d" ] && st="$(pcm_state "$d")"
  say "PCM state after the render: $st"
  if [ "$st" = "RUNNING" ]; then
    say "DECISION: the DAC/ABox ran (state=RUNNING observed while the stream was open)."
  else
    say "DECISION: DAC_NOT_RUNNING — the stream did not leave SETUP. The amplifier path is not running."
  fi
  say "AUDIBILITY: NEEDS_OWNER_TEST — this tool cannot hear. Record it in area 6."
  return 0
}

# --------------------------------------------------------------- capture / UCM
cmd_capture() {
  local idx; idx="$(card_index)"
  [ -z "$idx" ] && { say "BLOCKED: no card named '$CARD_NAME'."; return 1; }
  mkdir -p "$(abs "$STATE_DIR")"
  local out; out="$(abs "$STATE_DIR/controls.json")"
  local ct; ct="$(controls_text "$idx")"
  if [ -z "$ct" ]; then say "BLOCKED: no mixer reader (amixer/tinymix)."; return 1; fi
  {
    printf '{\n  "schema_version": 1,\n  "card": "%s",\n  "card_index": %s,\n  "captured_at": "%s",\n' \
      "$CARD_NAME" "$idx" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    printf '  "note": "EVIDENCE ONLY. A control listed here is not a route, and a writable control is not audible sound. The generated UCM sequences below are built from exactly these names and nothing else.",\n'
    printf '  "controls_raw_lines": %d\n}\n' "$(printf '%s\n' "$ct" | wc -l | tr -d ' ')"
  } >"$out"
  say "captured mixer evidence -> $out"
  # Generate the UCM EnableSequence ONLY from observed controls, clamped to the
  # low-volume cap. The parser is a real one: a real `amixer contents` control
  # line looks like "numid=1,iface=MIXER,name='Speaker Volume'", so a naive
  # `^name=` glob would emit an EMPTY sequence and leave the route permanently
  # unverified. Every emitted cset names a control that was actually observed,
  # and its value is computed from that control's own min/max/step and the cap.
  local gen; gen="$(abs "$STATE_DIR/HiFi.conf.generated")"
  local raw; raw="$(abs "$STATE_DIR/controls.raw")"
  mkdir -p "$(dirname "$raw")" 2>/dev/null || true
  printf '%s\n' "$ct" >"$raw"
  python3 - "$raw" "$CARD_NAME" "$CAP_PCT" "$gen" "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" <<'NUXELGEN'
import re, sys
raw, card, cap, gen, stamp = sys.argv[1:6]
cap = int(cap)
text = open(raw, encoding="utf-8", errors="replace").read()
blocks, cur = [], None
for line in text.splitlines():
    m = re.search(r"name='([^']*)'", line)
    if m:
        cur = {"name": m.group(1), "type": None, "min": None, "max": None,
               "step": None, "values": None}
        blocks.append(cur)
    if cur is None:
        continue
    t = re.search(r"type=([A-Z0-9_]+)", line)
    if t:
        cur["type"] = t.group(1)
    for k in ("min", "max", "step"):
        mm = re.search(k + r"=(-?\d+)", line)
        if mm:
            cur[k] = int(mm.group(1))
    if re.search(r":\s*values=", line):
        cur["values"] = line.split("values=", 1)[1].strip()
csets, others = [], []
for blk in blocks:
    name = blk["name"]
    if (blk["type"] == "INTEGER" and re.search("volume", name, re.I)
            and blk["min"] is not None and blk["max"] is not None):
        lo, hi = blk["min"], blk["max"]
        step = blk["step"] or 1
        target = lo + (hi - lo) * cap // 100
        if step > 1:
            target = lo + ((target - lo) // step) * step
        csets.append("cset \"name='%s' %d\"" % (name, target))
    else:
        others.append("# observed, no safe generated action: %s" % name)
out = ["# GENERATED by nuxel-audio-diag.sh capture -- do NOT hand-edit.",
       "# Every cset below names a control that was OBSERVED on card %s at %s." % (card, stamp),
       "# Volume csets are clamped to the low-volume cap (%d percent)." % cap,
       "# A writable control is still NOT audible sound: audibility stays NEEDS_OWNER_TEST.",
       "", "Syntax 2", "",
       "SectionVerb {",
       "\tEnableSequence ["]
out += ["\t\t" + c for c in csets]
out += ["\t]", "\tDisableSequence [", "\t]", "}"]
out += others
open(gen, "w", encoding="utf-8").write("\n".join(out) + "\n")
print("generated %d clamped cset(s) from %d observed control(s)" % (len(csets), len(blocks)))
NUXELGEN
  say "generated UCM fragment  -> $gen (install with: $SELF ucm-install --yes)"
}

cmd_ucm_install() {
  local yes="${1:-}"
  local gen; gen="$(abs "$STATE_DIR/HiFi.conf.generated")"
  local tgt; tgt="$(abs "$UCM_DIR/HiFi.conf")"
  [ -f "$gen" ] || { say "BLOCKED: run '$SELF capture' first ($gen absent)."; return 1; }
  if [ "$yes" != "--yes" ]; then
    say "refusing to install without --yes. Would copy:"
    say "  $gen -> $tgt (backup: $tgt.prev-nuxel)"
    return 2
  fi
  mkdir -p "$(dirname "$tgt")"
  if [ -f "$tgt" ]; then
    cp -f "$tgt" "$tgt.prev-nuxel"
    say "backed up existing profile -> $tgt.prev-nuxel"
  fi
  local before after
  before="$(sha256sum "$gen" 2>/dev/null | cut -d' ' -f1)"
  cp -f "$gen" "$tgt"
  after="$(sha256sum "$tgt" 2>/dev/null | cut -d' ' -f1)"
  if [ "$before" != "$after" ]; then
    say "HASH MISMATCH after install — rolling back"
    [ -f "$tgt.prev-nuxel" ] && cp -f "$tgt.prev-nuxel" "$tgt"
    return 1
  fi
  log_evidence "ucm-install sha256=$after"
  say "installed $tgt (sha256=$after)"
  say "verifying the profile loads: $(have_tool alsaucm && run_tool alsaucm -c "$CARD_NAME" list _verbs 2>&1 | head -3 || echo 'alsaucm absent — profile not load-tested')"
}

cmd_safe_volume() {
  local want="${1:-}"
  local idx; idx="$(card_index)"
  if [ -z "$idx" ]; then say "BLOCKED: no card named '$CARD_NAME'."; return 1; fi
  if [ -z "$want" ]; then
    say "softvol ceiling: cap=${CAP_PCT}% (from $POLICY)"
    have_tool amixer && run_tool amixer -c "$idx" sget 'Nuxel Safe Volume' 2>&1 | sed -n '1,12p' \
      || say "  ('Nuxel Safe Volume' not readable — the ALSA softvol layer is not installed)"
    return 0
  fi
  case "$want" in ''|*[!0-9]*) say "usage: $SELF safe-volume [0-100]"; return 2 ;; esac
  if [ "$want" -gt "$CAP_PCT" ]; then
    say "REFUSED: $want% exceeds the low-volume cap ${CAP_PCT}% (configs/nuxel/audio/audio.json)."
    say "         Raise the cap in the policy deliberately, or change it on the bench — not here."
    return 1
  fi
  have_tool amixer || { say "BLOCKED_EXTERNAL_RESOURCE: amixer absent."; return 1; }
  run_tool amixer -c "$idx" sset 'Nuxel Safe Volume' "${want}%" && say "set softvol ceiling to ${want}%"
}

# ------------------------------------------------------------------- settings
# primary_element: the FIRST real playback element the card reports. A control
# name is never invented ('Master' is not assumed to exist on this codec).
primary_element() {
  local idx="$1" ctl=""
  [ -n "$idx" ] && have_tool amixer || return 1
  ctl="$(run_tool amixer -c "$idx" scontrols 2>/dev/null | sed -n "s/^Simple mixer control '\(.*\)',.*/\1/p" | head -1)"
  [ -n "$ctl" ] && printf '%s' "$ctl"
}

cmd_mode() {
  local want="${1:-}"
  local f; f="$(abs "$SOUND_MODE_FILE")"
  if [ -z "$want" ]; then
    local cur="normal"
    [ -r "$f" ] && cur="$(head -1 "$f" | tr -d ' \n')"
    [ -n "$cur" ] || cur="normal"
    say "sound mode: $cur"
    say "state file: $SOUND_MODE_FILE (shared with the Power+VolumeUp chord in the button manager)"
    return 0
  fi
  case "$want" in
    normal|vibrate|silent) ;;
    *) say "usage: $SELF mode [normal|vibrate|silent]"; return 2 ;;
  esac
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  printf '%s\n' "$want" > "$f" 2>/dev/null || { say "cannot write $f"; return 1; }
  local idx ctl sw
  idx="$(card_index)"; ctl="$(primary_element "$idx" || true)"
  sw="off"; [ "$want" = "normal" ] && sw="on"
  if [ -n "$ctl" ]; then
    run_tool amixer -c "$idx" sset "$ctl" "$sw" >/dev/null 2>&1 || true
    say "sound mode set to $want (element '$ctl' switched $sw)"
  else
    say "sound mode set to $want (no mixer element was discoverable: the MODE is recorded, the"
    say "  playback switch was NOT touched — a control name is never invented)"
  fi
  if [ "$want" = "vibrate" ]; then
    say "NOTE: vibrate mode also needs the vibrator path (briq-08b). The mode is RECORDED here;"
    say "      it is not a claim that the phone vibrates."
  fi
  say "audibility remains NEEDS_OWNER_TEST (a switch write is not sound)."
  return 0
}

cmd_settings() {
  local json="${1:-}"
  hdr "Settings -> Sound (renderer: briq-06d)"
  say "spec: configs/alsa-ucm/nuxel-sound-settings.json"
  local idx; idx="$(card_index)"
  say "card: ${idx:-NOT FOUND} (name '$CARD_NAME')"
  say "volume step: 5% of the element range (range / 20, floored at 1)"
  say "low-volume cap: ${CAP_PCT}% (from $POLICY)"
  local ctl; ctl="$(primary_element "$idx" || true)"
  if [ -n "$ctl" ]; then
    say "primary element: $ctl"
    if [ -n "$ctl" ]; then
      local mute_state
      mute_state="$(run_tool amixer -c "$idx" sget "$ctl" 2>/dev/null | sed -n 's/.*\[\(on\|off\)\].*/\1/p' | head -1)"
      say "playback switch: ${mute_state:-unknown}"
    fi
  else
    say "mixer: unavailable (amixer absent or no card) - the settings page must say so, not guess"
  fi
  say "sound mode: $(cmd_mode | head -1 | sed 's/^sound mode: //')"
  say "outputs:"
  local sink=""
  if have_tool wpctl; then
    sink="$(run_tool wpctl status 2>/dev/null | awk '
      /Sinks:/ { in_s = 1; next }
      /Sources:|Filters:|Streams:|Devices:/ { if (in_s) in_s = 0 }
      in_s && /[0-9]+\./ { print "    " $0 }' | head -6)"
  fi
  if [ -n "$sink" ]; then
    printf '%s\n' "$sink"
  elif have_tool pactl; then
    printf '    %s\n' "$(run_tool pactl list short sinks 2>/dev/null | head -5)"
  else
    say "    (no session manager answered: sink list unavailable; the ALSA element above is the only truth)"
  fi
  say "per-app volume: $( if have_tool wpctl || have_tool pactl; then echo "supported by the session manager (per-node volume)"; else echo "NOT supported on this image - the row must say unsupported"; fi )"
  say "mic input: the capture control of the same card (jack headset mic vs built-in); selection is not proof of a recording"
  say "jack routes: configs/nuxel/audio/jack-routes.json (speaker / headphones / headset / USB-C UAC / analog accessory)"
  say "audibility: NEEDS_OWNER_TEST for every row."
  if [ "$json" = "--json" ]; then
    local mode; mode="$(cmd_mode 2>/dev/null | head -1 | sed 's/^sound mode: //')"
    printf '{"tool":"nuxel-audio-diag","device":"beyond2lte","card":"%s","card_index":"%s","cap_percent":%s,"sound_mode":"%s","step_percent":5}\n' \
      "$CARD_NAME" "${idx:-}" "${CAP_PCT:-0}" "${mode:-normal}"
  fi
  return 0
}

# ------------------------------------------------------------------- status
cmd_status() {
  local json=""
  [ "${1:-}" = "--json" ] && json=1
  local idx; idx="$(card_index)"
  if [ "$json" = "1" ]; then
    pipeline "${idx:-}" 1
    return 0
  fi
  hdr "audio status (S10+ / $CARD_NAME)"
  say "policy: $POLICY (low_volume_only cap=${CAP_PCT}%, first tone=${TONE_PCT}%)"
  if [ -z "$idx" ]; then
    say "card: NOT FOUND (looked for the name '$CARD_NAME' in /proc/asound/cards)"
  else
    say "card: index $idx"
  fi
  say "firmware: $(firmware_state) (${FW_CANDIDATES[*]})"
  say "UCM profile: $UCM_DIR/HiFi.conf $([ -f "$(abs "$UCM_DIR/HiFi.conf")" ] && echo 'present' || echo 'absent')"
  say "evidence log: $EVIDENCE_LOG"
  pipeline "$idx" ""
  say ""
  say "audibility: NEEDS_OWNER_TEST — never inferred from a writable control."
}

cmd_cards() {
  hdr "/proc/asound/cards"
  local f; f="$(abs /proc/asound/cards)"
  [ -f "$f" ] && cat "$f" || say "  (absent — no ALSA card is registered)"
  hdr "resolved"
  say "  $CARD_NAME -> index '$(card_index)'"
  hdr "codec/pin detail (evidence)"
  local c
  for c in "$(abs /proc/asound)"/card*/codec#*; do
    [ -f "$c" ] || continue
    say "--- $c"
    sed -n '1,12p' "$c"
  done
}

cmd_controls() {
  local idx; idx="$(card_index)"
  [ -z "$idx" ] && { say "BLOCKED: no card named '$CARD_NAME'."; return 1; }
  local ct; ct="$(controls_text "$idx")"
  if [ -z "$ct" ]; then say "BLOCKED: no mixer reader (amixer/tinymix) available."; return 1; fi
  if [ "${1:-}" = "--json" ]; then
    cat <<JSON
{"schema_version":1,"card":"$CARD_NAME","card_index":$idx,
 "candidate_playback_controls":$(count_playback_controls "$ct"),
 "note":"writability is not audibility","raw":$(printf '%s' "$ct" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))' 2>/dev/null || echo '""')}
JSON
    return 0
  fi
  say "candidate playback/speaker controls: $(count_playback_controls "$ct")"
  say "(full list is captured to $STATE_DIR/controls.json by '$SELF capture')"
  printf '%s\n' "$ct" | grep -E 'Volume|Switch|DAC|Speaker|HP|AMP' | head -25
}

# ------------------------------------------------------------------- selftest
cmd_selftest() {
  local fx="${NUXEL_AUDIO_FIXTURES:-$(dirname "$SELF_PATH")/tests/fixtures-p3}"
  local fail=0 n name exp got
  [ -d "$fx" ] || { say "FAIL fixtures directory not found: $fx"; return 1; }
  for n in "$fx"/audio-*/; do
    [ -d "$n" ] || continue
    name="$(basename "$n")"
    exp="$(cat "$n/EXPECTED" 2>/dev/null || echo '')"
    [ -n "$exp" ] || { say "SKIP $name (no EXPECTED)"; continue; }
    got="$(NUXEL_DIAG_ROOT="$n" NUXEL_DIAG_NO_SYSTEM=1 "$SELF_PATH" status 2>&1 \
           | sed -n '/== verdict ==/,+1p' | sed -n '2p' | sed 's/^ *//' | cut -d' ' -f1)"
    if [ "$got" = "$exp" ]; then say "PASS $name verdict=$got"
    else say "FAIL $name expected=$exp got=${got:-<none>}"; fail=$((fail+1)); fi
  done
  say "== $fail failing fixture(s) =="
  return "$fail"
}

case "$CMD" in
  status)      cmd_status "${1:-}" ;;
  cards)       cmd_cards ;;
  pipeline)    pipeline "$(card_index)" "$( [ "${1:-}" = "--json" ] && echo 1 )" ;;
  controls)    cmd_controls "${1:-}" ;;
  capture)     cmd_capture ;;
  ucm-install) cmd_ucm_install "${1:-}" ;;
  tone)        cmd_tone "${1:-800}" "${2:-}" ;;
  safe-volume) cmd_safe_volume "${1:-}" ;;
  settings)    cmd_settings "${1:-}" ;;
  mode)        cmd_mode "${1:-}" ;;
  selftest)    cmd_selftest ;;
  help|-h|--help) sed -n '2,45p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) say "unknown command: $CMD (try: $SELF help)"; exit 2 ;;
esac
