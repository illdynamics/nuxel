#!/bin/sh
# ============================================================================
# nuxel-postboot.sh — the Nuxel post-handoff supervisor (A24).
#
# WHY THIS EXISTS (measured on A23, 2026-10-15):
#   The Fedora userspace on this image NEVER finishes booting.  Six minutes after
#   `switch_root`, `systemctl is-system-running` was still "initializing" and
#   EVERY job was in state "waiting": sysinit.target, basic.target, local-fs.target,
#   multi-user.target, systemd-udevd, getty@tty1, ModemManager, dbus-broker ...
#   Nothing was running.  Consequently any unit that depends on a target (that is,
#   every normally-enabled service) could never start -- which is why a UI unit
#   enabled into multi-user.target.wants stayed "inactive" and why
#   `systemctl start nuxel-ui` blocked forever.
#
#   That is the real answer to "the spinning penguin never becomes a phone UI":
#   there was no stalled renderer -- there was a stalled *boot*.
#
# So the UI must not be gated behind that graph, and something must still run
# after switch_root to notice and act.  This script is that something: /init
# starts it BEFORE switch_root (so it survives it, like nuxel-console), it waits
# for the real root, then
#   1. records a full boot report into /var/lib/nuxel/bootreport.txt,
#   2. starts the phone UI directly if it is not up,
#   3. keeps watching and re-starting it.
#
# It never touches battery, thermal or storage, and it is fail-open: nothing here
# can prevent a boot.
# ============================================================================
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export PATH
SYSCTL=/usr/bin/systemctl
[ -x "$SYSCTL" ] || SYSCTL=/bin/systemctl
STATE=/var/lib/nuxel
REPORT=$STATE/bootreport.txt

# --- A29b: who owns the panel? ----------------------------------------------------
# When the UTM-derived launcher is installed (nuxel-wl-fb + nuxel-wayland), IT is
# the panel owner: the A27 fbdev UI is only the fallback.  Measured on the
# handset: this supervisor started nuxel-ui 9 s after `systemctl stop nuxel-ui`,
# which would put a second /dev/fb0 owner behind the launcher's back.  The
# launcher units are enabled by the rootfs builder, so this script must not fight
# them; /usr/lib/nuxel/nuxel-launcher-ready-wait (used by nuxel-fallback.service)
# is the authoritative "did the launcher come up" test.
launcher_owns_panel() {
    [ -x /usr/lib/nuxel/nuxel-wl-fb ] || return 1
    [ -f /run/nuxel-launcher-ready ] && return 0
    $SYSCTL is-active --quiet nuxel-wl-fb 2>/dev/null && return 0
    return 1
}
WAIT="${1:-20}"

mkdir -p "$STATE" 2>/dev/null
sleep "$WAIT" 2>/dev/null

report() {
    {
        echo "===== NUXEL POST-HANDOFF REPORT $(date -u 2>/dev/null) ====="
        echo "is-running : $($SYSCTL is-system-running 2>&1)"
        echo "ui         : $($SYSCTL is-active nuxel-ui 2>&1)"
        echo "ui-stage   : $(cat $STATE/ui-stage 2>/dev/null)"
        echo "anim-stage : $(cat $STATE/animation 2>/dev/null)"
        echo "--- jobs ---"
        $SYSCTL list-jobs --no-pager 2>&1 | head -25
        echo "--- failed ---"
        $SYSCTL --failed --no-pager 2>&1 | head -12
        echo "--- procs ---"
        ps -eo pid,ppid,comm 2>/dev/null | grep -E 'nuxel|systemd|udev' | head -25
        echo "--- panel ---"
        ls -l /dev/fb0 2>&1
        echo "--- input ---"
        ls -l /dev/input/ 2>&1 | head -12
        echo "--- warnings (journal) ---"
        journalctl -b -p warning --no-pager 2>&1 | tail -25
    } >> "$REPORT" 2>&1
}
report

# --- self-repair: the UI owns the panel; it must not depend on the stalled graph
if ! $SYSCTL is-active --quiet nuxel-ui 2>/dev/null; then
    if launcher_owns_panel; then
        echo "$(date -u 2>/dev/null) postboot: launcher owns the panel -> nuxel-ui NOT started" >> "$REPORT"
        $SYSCTL start --no-block nuxel-touch-arm nuxel-wayland nuxel-wl-fb >> "$REPORT" 2>&1
    else
        echo "$(date -u 2>/dev/null) postboot: nuxel-ui not active -> starting it" >> "$REPORT"
        $SYSCTL start --no-block nuxel-ui >> "$REPORT" 2>&1
    fi
fi

sleep 15 2>/dev/null
{
    echo "--- 15 s later ---"
    echo "ui         : $($SYSCTL is-active nuxel-ui 2>&1)"
    echo "ui-pid     : $(pgrep -x nuxel-ui 2>/dev/null | head -1)"
    echo "ui-stage   : $(cat $STATE/ui-stage 2>/dev/null)"
    echo "fb-ready   : $(cat $STATE/ui-fb-ready 2>/dev/null)"
    echo "anim-stop  : $(cat $STATE/anim-stop 2>/dev/null)"
    echo "anim-pid   : $(cat $STATE/fb-anim.pid 2>/dev/null)"
} >> "$REPORT" 2>&1

# --- keep the panel owned: restart the UI if it ever goes away
i=0
while [ "$i" -lt 240 ]; do
    i=$((i+1))
    sleep 30 2>/dev/null
    if ! $SYSCTL is-active --quiet nuxel-ui 2>/dev/null; then
        if launcher_owns_panel; then
            echo "$(date -u 2>/dev/null) postboot: iteration $i - launcher owns the panel (nuxel-ui not started)" >> "$REPORT"
            $SYSCTL is-active --quiet nuxel-wl-fb 2>/dev/null || $SYSCTL start --no-block nuxel-wayland nuxel-wl-fb 2>/dev/null
        else
            echo "$(date -u 2>/dev/null) postboot: nuxel-ui went away -> restart (iteration $i)" >> "$REPORT"
            $SYSCTL start --no-block nuxel-ui 2>/dev/null
        fi
    fi
done
exit 0
