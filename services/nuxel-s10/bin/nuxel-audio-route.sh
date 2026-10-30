#!/bin/sh
# Nuxel S10+ ABOX playback route (RDMA1 -> SIFS1 -> UAIF1 -> CS35L41).
#
# RDMA0 starts but its DSP never advances hw_ptr on this unit; RDMA1 is the
# working 48 kHz path, selected by /etc/asound.conf (card 0, device 1).
# 44.1 kHz leaves hw_ptr at 0 and returns EIO on this unit (measured
# 2026-10-29); PipeWire and the static sink therefore run at 48 kHz.
# The ABOX crossbar defaults to "no route", so this script programs the exact
# enum/boolean mixer controls observed on the beyond-madera card.
#
# Corrected for the real 2026-10-28 card control namespace:
#   * Left/Right AMP Enable Switch are BOOLEAN controls.
#   * ABOX SPUS IN1/OUT1, ABOX SIFS1 and ABOX UAIF1 SPK are ENUMERATED and are
#     written as integer indices (verified against amixer cget).
#   * There is no 'ABOX RDMA0_EN' / 'ABOX RDMA1_EN' mixer control on this card;
#     RDMA0/RDMA1 are PCM devices, not mixer elements.
#
# FAIL-OPEN AT BOOT: for the first seconds after cold boot the ABox
# power/control write or the first amixer open can block in uninterruptible
# rpm_resume (D-state).  Every step is therefore bounded with `timeout`, and any
# failure exits 0 with a "deferred" state.  nuxel-audio-route-retry.service
# (started by nuxel-audio-route.timer at OnBootSec=45s) re-runs this same script
# once the DSP is awake, so the route is applied without blocking the UI.
set -u

C=${NUXEL_AUDIO_CARD:-0}
say() { echo "$(date -u +%FT%TZ) nuxel-audio-route: $*"; }
STATE=/run/nuxel-audio-route.state

# Card presence is read from procfs; aplay -l and amixer both open the card and
# can block on this vendor kernel.
if [ ! -r /proc/asound/cards ] || ! grep -Eq "^[[:space:]]*${C}[[:space:]]+\[" /proc/asound/cards; then
    say "card $C absent in /proc/asound/cards; leaving mixer untouched"
    echo "state=absent card=$C" >"$STATE" 2>/dev/null || true
    exit 0
fi

# Bounded runtime-resume.  The write is usually ~10-90 ms once the ABox is up,
# but can block during early boot; `timeout` keeps it from wedging the service.
resume_ok=0
for ctl in /sys/devices/platform/*.abox/power/control; do
    [ -w "$ctl" ] || continue
    if timeout -k 1 3 sh -c 'printf on > "$1"' _ "$ctl" 2>/dev/null; then
        resume_ok=1
        say "runtime-pm $ctl=on"
    else
        say "runtime-pm $ctl write deferred (not ready)"
    fi
done

# One bounded probe on a control that really exists on this card.  If the ABox
# is not awake yet, defer instead of leaving blocked amixer processes behind.
if ! timeout -k 1 5 amixer -c "$C" cget name='ABOX UAIF1 Switch' >/dev/null 2>&1; then
    say "ABOX controls not ready on card $C; deferring route"
    echo "state=deferred card=$C" >"$STATE" 2>/dev/null || true
    exit 0
fi

mix() {
    _desc=$1; shift
    if timeout -k 1 3 amixer -c "$C" "$@" >/dev/null 2>&1; then
        say "ok   $_desc"
        return 0
    fi
    say "warn $_desc (timeout or unsupported control)"
    return 1
}

# Speaker/receiver amplifier DAPM enables (BOOLEAN).
mix 'Left AMP Enable Switch'  cset name='Left AMP Enable Switch' on || exit 0
mix 'Right AMP Enable Switch' cset name='Right AMP Enable Switch' on || exit 0

# RDMA1 -> SPUS IN1 -> SPUS OUT1 -> SIFS1 -> UAIF1 SPK -> UAIF1 OUT.
mix 'SPUS IN1=RDMA'     cset name='ABOX SPUS IN1' 0 || exit 0
mix 'SPUS OUT1=SIFS1'   cset name='ABOX SPUS OUT1' 0 || exit 0
mix 'SIFS1=SPUS OUT1'   cset name='ABOX SIFS1' 1 || exit 0
mix 'UAIF1 SPK=SIFS1'   cset name='ABOX UAIF1 SPK' 2 || exit 0
mix 'SIFS1 OUT on'      cset name='ABOX SIFS1 OUT Switch' on || exit 0
mix 'UAIF1 on'          cset name='ABOX UAIF1 Switch' on || exit 0

for n in 'ABOX UAIF1 Switch' 'ABOX SIFS1 OUT Switch' 'Left AMP Enable Switch' 'Right AMP Enable Switch'; do
    v=$(timeout -k 1 2 amixer -c "$C" cget name="$n" 2>/dev/null | sed -n 's/.*values=//p' | head -1)
    say "verify $n=${v:-unreadable}"
done
say "route applied"
echo "state=applied card=$C" >"$STATE" 2>/dev/null || true
exit 0
