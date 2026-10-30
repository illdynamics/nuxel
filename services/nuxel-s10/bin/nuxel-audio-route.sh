#!/bin/sh
# Nuxel S10+ ABOX playback route (RDMA1 -> SPUS -> SIFS1 -> UAIF1 -> CS35L41).
#
# The live unit has TWO unrelated firmware layers that both have to be ready:
#   * Samsung ABOX Calliope core firmware, exposed as calliope_version=MUB0
#     under /sys/devices/platform/18c50000.abox;
#   * CS35L41 DSP1 protection firmware for BOTH amplifiers (DSP1 Firmware =
#     Protection, DSP1 Preload = on, debugfs dsp1/booted=Y and running=Y).
# Neither one alone makes the speaker audible.
#
# RDMA1 (hw:0,1) is the measured working PCM at 48 kHz.  RDMA0 never advances
# its hardware pointer on this unit; 44.1 kHz on RDMA1 leaves hw_ptr at zero
# and returns EIO.  PipeWire owns hw:0,1 at runtime, so the callers use
# pw-play through the static alsa_output.hw_0_1 sink, never a direct ALSA
# player while PipeWire holds the PCM.
#
# The checked-in script used to deny the existence of ABOX RDMA1_EN.  That was
# wrong: the live beyond-madera card exposes numid=1031, enum Off/On.  With it
# Off, the player and hw_ptr can both advance while ABOX clocks no samples into
# SPUS.  RDMA1_EN=On is therefore a mandatory part of this route, verified by
# name (never by numid).
#
# `--check` is a read-only readiness probe used by the boot cue and diagnostics.
# It exits 0 only when the live route, both DSPs, PipeWire, and the expected
# default sink all verify right now.  A state file alone is never considered
# proof of readiness.
set -u

AMIXER=${NUXEL_AMIXER:-amixer}
PW_RUNTIME=${NUXEL_PW_RUNTIME:-/run/nuxel-wayland}
SINK=${NUXEL_AUDIO_SINK:-alsa_output.hw_0_1}
VOLUME_CAP=${NUXEL_AUDIO_VOLUME_CAP:-0.25}
STATE=/run/nuxel-audio-route.state
ABOX=/sys/devices/platform/18c50000.abox
VERSION="$ABOX/calliope_version"
CHECK_ONLY=0
WAIT_SECONDS=0
case "${1:-}" in
    --check) CHECK_ONLY=1 ;;
    --wait)  CHECK_ONLY=1; WAIT_SECONDS=${2:-120} ;;
esac

say() { echo "$(date -u +%FT%TZ) nuxel-audio-route: $*"; }
fail_state() {
    reason=$1
    say "NOT READY: $reason"
    [ "$CHECK_ONLY" -eq 1 ] && exit 1
    printf 'state=deferred\ncard=%s\nreason=%s\nat=%s\n' "${C:-?}" "$reason" "$(date -u +%FT%TZ)" >"$STATE" 2>/dev/null || true
    exit 0
}
check_fail() { say "readiness failed: $*"; exit 1; }

# Find the card by its stable ALSA id; do not assume index 0 forever.
if [ -n "${NUXEL_AUDIO_CARD:-}" ]; then
    C=$NUXEL_AUDIO_CARD
elif [ -r /proc/asound/cards ]; then
    C=$(awk '/beyond-madera/ {print $1; exit}' /proc/asound/cards)
else
    C=
fi
[ -n "${C:-}" ] || fail_state "beyond-madera card absent"
[ -r /proc/asound/cards ] && grep -Eq "^[[:space:]]*${C}[[:space:]]+\[beyondmadera" /proc/asound/cards \
    || fail_state "card $C is not beyond-madera"

# Both ABOX and CS35L41 changes can block in RPM/I2C on this vendor 4.14
# kernel.  Every operation is bounded; a deferred state is honest and the
# boot-time retry unit runs this script again.
if [ "$CHECK_ONLY" -eq 0 ]; then
    for ctl in "$ABOX"/power/control; do
        [ -w "$ctl" ] || continue
        if timeout -k 1 3 sh -c 'printf on > "$1"' _ "$ctl" 2>/dev/null; then
            say "runtime-pm $ctl=on"
        else
            say "runtime-pm $ctl write deferred"
        fi
    done
fi

calliope_ready() { timeout 2 grep -aq 'MUB0' "$VERSION" 2>/dev/null; }

dsp_ready() {
    n=0; good=1
    for d in /sys/kernel/debug/asoc/beyond-madera/codec:cs35l41-codec.*/dsp1; do
        [ -d "$d" ] || continue
        n=$((n + 1))
        [ "$(cat "$d/booted" 2>/dev/null)" = Y ] || good=0
        [ "$(cat "$d/running" 2>/dev/null)" = Y ] || good=0
    done
    [ "$n" -eq 2 ] && [ "$good" -eq 1 ]
}

read_ctl() {
    timeout -k 1 3 "$AMIXER" -c "$C" cget name="$1" 2>/dev/null \
        | sed -n 's/^[[:space:]]*: values=//p' | head -1
}

want_ctl() { # want_ctl <name> <expected> [description]
    got=$(read_ctl "$1")
    if [ "$got" = "$2" ]; then
        say "verify $1=$got ${3:-}"
        return 0
    fi
    say "verify $1=${got:-unreadable} expected $2 ${3:-}"
    return 1
}

set_ctl() { # set_ctl <description> <control> <value>
    # Idempotent: the retry timer re-runs this script every 5 minutes.  Writing
    # DSP1 firmware/preload again on an already-running amplifier needlessly
    # bounces the protection DSP (and the I2C bus), so read first and only
    # write when the live value actually differs.
    got=$(read_ctl "$2")
    if [ "$got" = "$3" ]; then
        say "ok   $1 (already set)"
        return 0
    fi
    if timeout -k 1 5 "$AMIXER" -c "$C" cset name="$2" "$3" >/dev/null 2>&1; then
        say "ok   $1"
        return 0
    fi
    say "FAIL $1 (timeout or unsupported control)"
    return 1
}

pw_env() {
    env XDG_RUNTIME_DIR="$PW_RUNTIME" PIPEWIRE_RUNTIME_DIR="$PW_RUNTIME" \
        PULSE_SERVER="unix:$PW_RUNTIME/pulse/native" PATH=/usr/sbin:/usr/bin:/sbin:/bin "$@"
}
sink_present() {
    [ -S "$PW_RUNTIME/pipewire-0" ] || return 1
    pw_env timeout 4 pactl list short sinks 2>/dev/null | awk -v s="$SINK" '$2 == s {found=1} END {exit !found}'
}
default_sink_ok() {
    [ "$(pw_env timeout 4 pactl get-default-sink 2>/dev/null)" = "$SINK" ]
}
pipewire_connectable() {
    # pactl (pulse compatibility) can answer while the native PipeWire socket is
    # still being replaced during a session restart.  pw-play then fails with
    # "pw_context_connect() failed: Host is down" against a stale/recreated
    # socket.  Probe the exact socket pw-play uses.  Read-only.
    [ -S "$PW_RUNTIME/pipewire-0" ] || return 1
    # pw-cli exits 0 even when it cannot bind (it prints a connection error
    # and no object), so parse the live core object, not the exit code.
    out=$(pw_env timeout 5 pw-cli info 0 2>&1)
    printf '%s\n' "$out" | grep -Eq 'type:[[:space:]]*PipeWire:Interface:Core'
}
ensure_default_sink() {
    sink_present || { say "static sink $SINK absent"; return 1; }
    if ! pw_env timeout 4 pactl set-default-sink "$SINK" >/dev/null 2>&1; then
        say "pactl set-default-sink $SINK failed"
        return 1
    fi
    default_sink_ok || { say "default sink readback is not $SINK"; return 1; }
    say "default sink $SINK verified"
}
sink_volume() {
    pw_env timeout 4 wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null \
        | awk '/Volume:/ {print $2; exit}'
}
volume_at_cap() {
    v=$(sink_volume)
    [ -n "$v" ] || return 1
    awk -v v="$v" -v cap="$VOLUME_CAP" 'BEGIN { exit !(v + 0 <= cap + 0.0001) }'
}
sink_rate_ok() {
    # The static sink is the only output and must be the RDMA1 48 kHz node.
    # `pactl list short sinks` prints: id<TAB>name<TAB>driver<TAB>spec.
    # A graph/sink mismatch here means PipeWire would resample the stream even
    # though the hardware accepts 48 kHz, so treat it as not-ready.
    line=$(pw_env timeout 4 pactl list short sinks 2>/dev/null | awk -v s="$SINK" '$2 == s {print; exit}')
    [ -n "$line" ] || return 1
    printf '%s\n' "$line" | grep -q '48000Hz'
}

route_controls_ready() {
    ok=1
    want_ctl 'ABOX RDMA1_EN' 1 || ok=0
    want_ctl 'ABOX SPKAMP_EN' 1 || ok=0
    want_ctl 'ABOX SPKAMP_A' 2 '(RDMA1)' || ok=0
    want_ctl 'ABOX SPKAMP_B' 2 '(RDMA1)' || ok=0
    want_ctl 'Left AMP Enable Switch' on || ok=0
    want_ctl 'Right AMP Enable Switch' on || ok=0
    want_ctl 'Left AMP Mute' 1 '(Unmuted)' || ok=0
    want_ctl 'Right AMP Mute' 1 '(Unmuted)' || ok=0
    want_ctl 'Left AMP PCM Gain' 12 '(GAIN_CTRL=0x193)' || ok=0
    want_ctl 'Right AMP PCM Gain' 12 '(GAIN_CTRL=0x193)' || ok=0
    want_ctl 'Left DSP1 Firmware' 9 '(Protection)' || ok=0
    want_ctl 'Right DSP1 Firmware' 9 '(Protection)' || ok=0
    want_ctl 'Left DSP1 Preload Switch' on || ok=0
    want_ctl 'Right DSP1 Preload Switch' on || ok=0
    want_ctl 'Left PCM Source' 0 '(ASP)' || ok=0
    want_ctl 'Right PCM Source' 0 '(ASP)' || ok=0
    want_ctl 'ABOX SPUS IN1' 0 '(RDMA)' || ok=0
    want_ctl 'ABOX SPUS OUT1' 0 '(SIFS1)' || ok=0
    want_ctl 'ABOX SIFS1' 1 '(SPUS OUT1)' || ok=0
    want_ctl 'ABOX UAIF1 SPK' 2 '(SIFS1)' || ok=0
    want_ctl 'ABOX SIFS1 OUT Switch' on || ok=0
    want_ctl 'ABOX UAIF1 Switch' on || ok=0
    want_ctl 'ABOX UAIF1 Rate' 48000 '(48 kHz)' || ok=0
    want_ctl 'ABOX UAIF1 Width' 16 '(16 bit)' || ok=0
    want_ctl 'ABOX UAIF1 Channel' 2 '(2 ch)' || ok=0
    [ "$ok" -eq 1 ]
}

if [ "$CHECK_ONLY" -eq 1 ]; then
    # --check is a single snapshot.  --wait polls the same checks, read-only,
    # until they all pass or the bound expires.  It never applies a route (the
    # retry unit owns that); it exists so a boot-cue ExecStartPre can wait for
    # the CS35L41 DSP1 download instead of failing at the first millisecond.
    deadline=$(( $(date +%s) + WAIT_SECONDS ))
    while :; do
        reason=
        calliope_ready || reason="Calliope core is not MUB0"
        [ -z "$reason" ] && { dsp_ready || reason="both CS35L41 DSP1 protection DSPs are not booted+running"; }
        [ -z "$reason" ] && { route_controls_ready || reason="one or more route controls are not applied"; }
        [ -z "$reason" ] && { sink_present || reason="static PipeWire sink $SINK absent"; }
        [ -z "$reason" ] && { sink_rate_ok || reason="static PipeWire sink $SINK is not running at 48000 Hz"; }
        [ -z "$reason" ] && { default_sink_ok || reason="PipeWire default sink is not $SINK"; }
        [ -z "$reason" ] && { pipewire_connectable || reason="PipeWire native socket is not accepting connections"; }
        [ -z "$reason" ] && { volume_at_cap || reason="PipeWire sink volume is above ${VOLUME_CAP}"; }
        [ -z "$reason" ] && break
        if [ "$WAIT_SECONDS" -le 0 ] || [ "$(date +%s)" -ge "$deadline" ]; then
            check_fail "$reason"
        fi
        say "waiting for readiness: $reason"
        sleep 1
    done
    say "READY: calliope=MUB0 dsp1=2/2 route=verified sink=$SINK rate=48000 default=verified volume<=${VOLUME_CAP}"
    exit 0
fi

printf 'state=pending\ncard=%s\nat=%s\n' "$C" "$(date -u +%FT%TZ)" >"$STATE" 2>/dev/null || true
calliope_ready || fail_state "Calliope core firmware is not MUB0"

# Probe one real ABOX control before writing anything.  Early boot can leave an
# amixer open blocked in rpm_resume; defer rather than wedge the service.
timeout -k 1 5 "$AMIXER" -c "$C" cget name='ABOX UAIF1 Switch' >/dev/null 2>&1 \
    || fail_state "ABOX mixer controls not ready"

# CS35L41 DSP1 protection firmware, per amplifier.  Firmware selection must be
# written before the preload switch.  These are NOT the ABOX Calliope blobs.
set_ctl 'Left DSP1 firmware=Protection'  'Left DSP1 Firmware' 9 || fail_state 'left DSP1 firmware selection failed'
set_ctl 'Right DSP1 firmware=Protection' 'Right DSP1 Firmware' 9 || fail_state 'right DSP1 firmware selection failed'
set_ctl 'Left DSP1 preload on'  'Left DSP1 Preload Switch' on || fail_state 'left DSP1 preload failed'
set_ctl 'Right DSP1 preload on' 'Right DSP1 Preload Switch' on || fail_state 'right DSP1 preload failed'

# Amplifier input and DAPM gates.  Keep the live amplifier PCM gain value; do
# not import an untested gain from an older capture.
set_ctl 'Left AMP Enable'        'Left AMP Enable Switch' on || fail_state 'left AMP enable failed'
set_ctl 'Right AMP Enable'       'Right AMP Enable Switch' on || fail_state 'right AMP enable failed'
set_ctl 'Left AMP Unmute'        'Left AMP Mute' 1 || fail_state 'left AMP unmute failed'
set_ctl 'Right AMP Unmute'       'Right AMP Mute' 1 || fail_state 'right AMP unmute failed'
# Amplifier digital trim.  The live route has been measured at 12 on both
# amps (kernel logs GAIN_CTRL=0x193), and the persistent route restores that
# measured state.  IMPORTANT: later owner-supervised tests at this setting
# still produced no audible speaker output, so this is a verified register
# configuration, NOT an acoustically confirmed gain value.  The physical
# SPEAKER endpoint is fed by Right AMP SPK; do not infer speaker audibility
# from the left/receiver path or from gain readback alone.
set_ctl 'Left AMP PCM Gain=12'   'Left AMP PCM Gain' 12 || fail_state 'left AMP gain failed'
set_ctl 'Right AMP PCM Gain=12'  'Right AMP PCM Gain' 12 || fail_state 'right AMP gain failed'
set_ctl 'Left PCM Source=ASP'    'Left PCM Source' 0 || fail_state 'left PCM source failed'
set_ctl 'Right PCM Source=ASP'   'Right PCM Source' 0 || fail_state 'right PCM source failed'

# CS35L41 amplifier clock/boost patch (owner-confirmed 2026-10-30).
# The DT programs ampclk=6.144MHz, but ABOX UAIF1 actually clocks 1.536MHz
# (16-bit stereo 48k), so the CS35L41 PLL was fed the wrong reference and the
# protection DSP never drove the speaker.  Re-lock both amps to the real wire
# rate and force the 0 dB PCM/unmute and output stage at register level.
CS35_PATCH_HELPER=${NUXEL_CS35_HELPER:-/usr/local/bin/nuxel-cs35.py}
cs35_patch() {
    [ -x "$CS35_PATCH_HELPER" ] || { say "CS35L41 patch helper missing; leaving amp registers untouched"; return 0; }
    for a in 0x40 0x41; do
        timeout -k 1 4 "$CS35_PATCH_HELPER" "$a" 0x4804 0x1b >/dev/null 2>&1 || return 1
        timeout -k 1 4 "$CS35_PATCH_HELPER" "$a" 0x2c04 0x370 >/dev/null 2>&1 || return 1
        timeout -k 1 4 "$CS35_PATCH_HELPER" "$a" 0x6000 0x8000 >/dev/null 2>&1 || return 1
        timeout -k 1 4 "$CS35_PATCH_HELPER" "$a" 0x2024 0x0 >/dev/null 2>&1 || return 1
    done
    say "CS35L41 clock/boost patch applied (4804=0x1b 2c04=0x370 6000=0x8000 2024=0x0)"
    return 0
}

cs35_patch || fail_state 'CS35L41 clock/boost patch failed'

# ABOX crossbar: RDMA1 -> SPUS IN1 -> SPUS OUT1 -> SIFS1 -> UAIF1 SPK.
set_ctl 'SPUS IN1=RDMA'    'ABOX SPUS IN1' 0 || fail_state 'SPUS IN1 failed'
set_ctl 'SPUS OUT1=SIFS1'  'ABOX SPUS OUT1' 0 || fail_state 'SPUS OUT1 failed'
set_ctl 'SIFS1=SPUS OUT1'  'ABOX SIFS1' 1 || fail_state 'SIFS1 routing failed'
set_ctl 'UAIF1 SPK=SIFS1'  'ABOX UAIF1 SPK' 2 || fail_state 'UAIF1 SPK routing failed'
set_ctl 'SIFS1 OUT on'     'ABOX SIFS1 OUT Switch' on || fail_state 'SIFS1 OUT switch failed'
set_ctl 'UAIF1 Rate 48k'   'ABOX UAIF1 Rate' 48000 || fail_state 'UAIF1 rate failed'
set_ctl 'UAIF1 Width 16'   'ABOX UAIF1 Width' 16 || fail_state 'UAIF1 width failed'
set_ctl 'UAIF1 Ch 2'       'ABOX UAIF1 Channel' 2 || fail_state 'UAIF1 channel failed'
set_ctl 'UAIF1 on'         'ABOX UAIF1 Switch' on || fail_state 'UAIF1 switch failed'
set_ctl 'Speaker path on'  'ABOX SPKAMP_EN' 1 || fail_state 'SPKAMP_EN failed'
set_ctl 'SPKAMP_A=RDMA1'   'ABOX SPKAMP_A' 2 || fail_state 'SPKAMP_A failed'
set_ctl 'SPKAMP_B=RDMA1'   'ABOX SPKAMP_B' 2 || fail_state 'SPKAMP_B failed'
set_ctl 'RDMA1 gate on'    'ABOX RDMA1_EN' 1 || fail_state 'ABOX RDMA1_EN failed'

# The DSP firmware download/exec is asynchronous.  Wait briefly, then require
# the debugfs booted/running flags rather than assuming the mixer write worked.
n=0
while [ "$n" -lt 20 ]; do
    dsp_ready && break
    n=$((n + 1)); sleep 0.25
done
dsp_ready || fail_state 'CS35L41 DSP1 not booted/running on both amplifiers'

route_controls_ready || fail_state 'route control readback mismatch'

# PipeWire owns hw:0,1.  This script only selects its static sink; playback is
# done by pw-play.  At 25% the sink is the one attenuation stage.
ensure_default_sink || fail_state 'PipeWire default sink not established'
sink_rate_ok || fail_state 'static PipeWire sink is not running at 48000 Hz'
pipewire_connectable || fail_state 'PipeWire native socket is not accepting connections'
# Only lower a level that is ABOVE the safety ceiling.  The retry timer must
# not silently override a user who deliberately chose a quieter level.
current_volume=$(sink_volume)
[ -n "$current_volume" ] || fail_state 'PipeWire sink volume is unreadable'
if awk -v v="$current_volume" -v cap="$VOLUME_CAP" 'BEGIN { exit !(v + 0 > cap + 0.0001) }'; then
    if pw_env timeout 4 wpctl set-volume @DEFAULT_AUDIO_SINK@ "$VOLUME_CAP" >/dev/null 2>&1; then
        say "sink volume lowered to cap $VOLUME_CAP (was $current_volume)"
    else
        fail_state 'PipeWire sink volume could not be capped'
    fi
else
    say "sink volume $current_volume already within cap $VOLUME_CAP (left unchanged)"
fi
volume_at_cap || fail_state 'PipeWire sink volume readback exceeds cap'
default_sink_ok || fail_state 'PipeWire default sink changed during volume update'
sink_rate_ok || fail_state 'static PipeWire sink stopped running at 48000 Hz'

printf 'state=applied\ncard=%s\ncalliope=MUB0\ndsp1=2/2\nroute=verified\nsink=%s\nrate=48000\ndefault=%s\nvolume_cap=%s\nat=%s\n' \
    "$C" "$SINK" "$SINK" "$VOLUME_CAP" "$(date -u +%FT%TZ)" >"$STATE"
say "route applied and verified"
exit 0
