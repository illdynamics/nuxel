#!/bin/sh
# Nuxel S10+ ABOX playback route (RDMA1 -> SIFS1 -> UAIF1 -> CS35L41).
#
# RDMA0 starts but its DSP never advances hw_ptr on this unit; RDMA1 is the
# working 44.1 kHz path.  Every mixer open is bounded and the script STOPS after
# the first timeout: on the 2026-10-28 image a blocked amixer sits in
# uninterruptible rpm_resume and each extra open adds another D-state task.
# A route failure must never restart-loop, hang boot, or own the sound server.
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

# Keep the ABox platform device runtime-resumed.  amixer can otherwise block in
# rpm_resume for minutes on this 4.14 vendor kernel.
for ctl in /sys/devices/platform/*.abox/power/control; do
    [ -w "$ctl" ] || continue
    echo on >"$ctl" 2>/dev/null || true
    say "runtime-pm $ctl=$(cat "$ctl" 2>/dev/null || echo '?')"
done

# One bounded probe only.  If the ABox is not awake yet, skip rather than
# leaving a queue of blocked amixer processes behind.
if ! timeout -k 1 4 amixer -c "$C" cget name='ABOX RDMA1_EN' >/dev/null 2>&1; then
    say "ABOX controls not ready on card $C; leaving mixer untouched"
    echo "state=not-ready card=$C" >"$STATE" 2>/dev/null || true
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

# Speaker/receiver amplifier DAPM enables.  Abort on the first failure so a
# single stuck control cannot accumulate more D-state processes.
mix 'Left AMP Enable'  cset name='Left AMP Enable Switch' on || exit 0
mix 'Right AMP Enable' cset name='Right AMP Enable Switch' on || exit 0
# Disconnect RDMA0 (its DSP never consumes) and route RDMA1.
mix 'RDMA0 off'        cset name='ABOX RDMA0_EN' 0 || exit 0
mix 'SPUS IN1=0'       cset name='ABOX SPUS IN1' 0 || exit 0
mix 'SPUS OUT1=0'      cset name='ABOX SPUS OUT1' 0 || exit 0
mix 'SIFS1=1'          cset name='ABOX SIFS1' 1 || exit 0
mix 'UAIF1 SPK=2'      cset name='ABOX UAIF1 SPK' 2 || exit 0
mix 'SIFS1 OUT on'     cset name='ABOX SIFS1 OUT Switch' on || exit 0
mix 'UAIF1 on'         cset name='ABOX UAIF1 Switch' on || exit 0
mix 'RDMA1 on'         cset name='ABOX RDMA1_EN' 1 || exit 0

for n in 'ABOX RDMA1_EN' 'ABOX UAIF1 Switch' 'ABOX SIFS1 OUT Switch'; do
    v=$(timeout -k 1 2 amixer -c "$C" cget name="$n" 2>/dev/null | sed -n 's/.*values=//p' | head -1)
    say "verify $n=${v:-unreadable}"
done
say "route applied"
echo "state=applied card=$C" >"$STATE" 2>/dev/null || true
exit 0
