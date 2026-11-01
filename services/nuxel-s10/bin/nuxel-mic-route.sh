#!/bin/sh
# Nuxel S10+ built-in microphone capture route (CS47L93 -> UAIF0 -> NSRC0 ->
# SIFM0/WDMA1).  Derived from the device's own vendor mixer_paths.xml:
#
#   recording-mic
#     -> media-mic
#        -> dev-main-mic   (LHPF1<-IN3L, ASRC1IN1L<-LHPF1,
#                           ISRC1INT1<-ASRC1IN1L, AIF1TX1/2<-ISRC1INT1,
#                           DMIC1=on)
#        -> route-ap-record (ABOX NSRC0=UAIF0, ABOX SIFM0=WDMA)
#
# WDMA1 (ALSA card 0 device 13) is the PCM that the vendor route names
# "route-nsrc0-to-wdma1".  Only controls listed in the vendor file are written;
# this script does not invent register values and never touches playback
# (RDMA/UAIF1/CS35L41) controls.
#
# The script is idempotent and read-back verified.  A single failed control
# leaves the route unapplied and exits non-zero so the unit can report it.
set -u

AMIXER=${NUXEL_AMIXER:-amixer}
STATE=/run/nuxel-mic-route.state
WAIT_SECONDS=0
case "${1:-}" in
    --wait) WAIT_SECONDS=${2:-120} ;;
esac

say() { echo "$(date -u +%FT%TZ) nuxel-mic-route: $*"; }
fail() {
    say "FAIL: $*"
    printf 'state=failed\nreason=%s\nat=%s\n' "$*" "$(date -u +%FT%TZ)" >"$STATE" 2>/dev/null || true
    exit 1
}

# The ABOX firmware reload and playback route run asynchronously after boot.
# WDMA1_EN is not writable until Calliope is MUB0, so wait for the audio route
# to report success before touching the capture crossbar.  The unit also has
# Restart=on-failure, so a slow boot is retried rather than left failed.
if [ "$WAIT_SECONDS" -gt 0 ]; then
    deadline=$(( $(date +%s) + WAIT_SECONDS ))
    while [ "$(date +%s)" -lt "$deadline" ]; do
        if grep -q '^state=applied$' /run/nuxel-audio-route.state 2>/dev/null \
           && grep -q '^calliope=MUB0$' /run/nuxel-audio-route.state 2>/dev/null; then
            break
        fi
        sleep 2
    done
fi

if [ -n "${NUXEL_AUDIO_CARD:-}" ]; then
    C=$NUXEL_AUDIO_CARD
else
    [ -r /proc/asound/cards ] || fail "no /proc/asound/cards"
    C=$(awk '/beyond-madera/ {print $1; exit}' /proc/asound/cards)
fi
[ -n "${C:-}" ] || fail "beyond-madera card absent"
grep -Eq "^[[:space:]]*${C}[[:space:]]+\[beyondmadera" /proc/asound/cards \
    || fail "card $C is not beyond-madera"

read_ctl() {
    timeout -k 1 3 "$AMIXER" -c "$C" cget name="$1" 2>/dev/null \
        | sed -n 's/^[[:space:]]*: values=//p' | head -1
}
set_ctl() { # set_ctl <label> <control> <value>
    got=$(read_ctl "$2")
    if [ "$got" = "$3" ]; then
        say "ok   $1 (already set)"
        return 0
    fi
    if timeout -k 1 5 "$AMIXER" -c "$C" cset name="$2" "$3" >/dev/null 2>&1; then
        got=$(read_ctl "$2")
        if [ "$got" = "$3" ]; then
            say "ok   $1"
            return 0
        fi
        say "FAIL $1 (readback '$got' != '$3')"
        return 1
    fi
    say "FAIL $1 (timeout or unsupported control)"
    return 1
}

# Probe one control before writing anything: early boot can leave an amixer open
# blocked in rpm_resume on this vendor 4.14 kernel.
timeout -k 1 5 "$AMIXER" -c "$C" cget name='ABOX SIFM0' >/dev/null 2>&1 \
    || fail "ABOX capture mixer controls not ready"

printf 'state=pending\ncard=%s\nat=%s\n' "$C" "$(date -u +%FT%TZ)" >"$STATE" 2>/dev/null || true

# ABOX: codec transmit (UAIF0) -> capture source 0 -> WDMA1.
set_ctl 'NSRC0=UAIF0'      'ABOX NSRC0' 8 || fail 'ABOX NSRC0 route failed'
set_ctl 'SIFM0=WDMA'       'ABOX SIFM0' 0 || fail 'ABOX SIFM0 route failed'
set_ctl 'SIFM0 autoconfig' 'ABOX SIFM0 Auto Config' on || fail 'SIFM0 autoconfig failed'
set_ctl 'SIFM0 min 8000'   'ABOX SIFM0 Rate Min' 8000 || fail 'SIFM0 minimum rate failed'
set_ctl 'WDMA1 gate on'    'ABOX WDMA1_EN' 1 || fail 'ABOX WDMA1_EN failed'

# CS47L93: built-in main microphone (the vendor "dev-main-mic" path).
set_ctl 'LHPF1=IN3L'         'LHPF1 Input 1' 12 || fail 'main-mic input failed'
set_ctl 'ASRC1IN1L=LHPF1'    'ASRC1IN1L Input 1' 58 || fail 'main-mic ASRC failed'
set_ctl 'ISRC1INT1=ASRC1IN1L' 'ISRC1INT1 Input 1' 104 || fail 'main-mic ISRC failed'
set_ctl 'AIF1TX1=ISRC1INT1'  'AIF1TX1 Input 1' 112 || fail 'AIF1TX1 failed'
set_ctl 'AIF1TX2=ISRC1INT1'  'AIF1TX2 Input 1' 112 || fail 'AIF1TX2 failed'
set_ctl 'DMIC1 on'           'DMIC1 Switch' on || fail 'DMIC1 switch failed'

printf 'state=applied\ncard=%s\npcm=hw:%s,13\nroute=uaif0-nsrc0-sifm0-wdma1\nat=%s\n' \
    "$C" "$C" "$(date -u +%FT%TZ)" >"$STATE"
say "microphone route applied (hw:$C,13 WDMA1)"
