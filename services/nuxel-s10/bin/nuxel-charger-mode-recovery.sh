#!/bin/sh
# Nuxel charger/LPM boot fallback (PWNAGE-52000).
#
# Permanent acceptance is a normal interactive boot from OFF with a charger
# attached.  That requires the exact-source BOOT/kernel patch
# kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch (TWRP-gated; see the mission
# evidence).  This userspace unit is a ONE-SHOT FALLBACK only, never a claim that
# the cold-boot defect is fixed.
#
# It performs at most one normal reboot per boot, and only when every gate below
# passes: the authoritative boot mode says charger/LPM, touch is actually absent,
# the device has been up long enough, no owner-test/capture lock exists, a charger
# is present AND the fuel gauge reports Charging, and the 900 s cooldown is clear.
# There is no bootloader/partition write, no loop, and no wake from a stale file.
set -u
say() { echo "$(date -u +%FT%TZ) nuxel-charger-mode: $*"; }
STATE=/run/nuxel-bootmode.state
GUARD_JSON=/run/nuxel-bootmode.json
COOLDOWN_FILE=/var/lib/nuxel/charger-mode-recovery.stamp
ONESHOT_FILE=/run/nuxel-charger-mode-recovery.done

touch_present() {
    grep -qi 'Name="sec_touchscreen"' /proc/bus/input/devices 2>/dev/null && return 0
    [ -d /sys/class/sec/tsp ] && return 0
    return 1
}

bypass_ttl() {
    # A stale charger marker must not cause a reboot after the mode has changed.
    [ -f "$STATE" ] || return 1
    [ "$(cat "$STATE" 2>/dev/null | grep -c 'BOOTMODE=CHARGER_LPM')" -gt 0 ]
}

# A patched kernel binds touch even in LPM: nothing to recover.
if touch_present; then
    say "sec_touchscreen is registered; no charger-mode recovery needed"
    exit 0
fi

# Only the authoritative state, never a bare prose match.
if [ -f "$STATE" ]; then
    bypass_ttl || { say "bootmode state is not CHARGER_LPM; refusing reboot"; exit 0; }
else
    # First boot after deploying the guard.  Classify read-only from cmdline.
    cmdline=$(cat /proc/cmdline 2>/dev/null || true)
    case "$cmdline" in
        *androidboot.mode=charger*) ;;
        *) say "normal or unknown boot mode; refusing reboot"; exit 0 ;;
    esac
fi

# Once per boot, so a broken userspace cannot reboot in a loop.
if [ -e "$ONESHOT_FILE" ]; then
    say "one-shot fallback already used on this boot; not rebooting"
    exit 0
fi

# Owner locks always win.
for lock in /run/nuxel-touch-capture.lock /run/nuxel-owner-test.lock \
            /run/nuxel-manual-proof.lock /var/lib/nuxel/owner-test.lock; do
    if [ -e "$lock" ]; then
        say "owner lock present ($lock); not rebooting"
        exit 0
    fi
done

# Uptime floor: do not reboot during early boot settling.
uptime=${UPTIME:-$(cut -d. -f1 /proc/uptime 2>/dev/null || echo 0)}
case "$uptime" in ''|*[!0-9]*) uptime=0 ;; esac
if [ "$uptime" -lt 120 ]; then
    say "uptime ${uptime}s < 120s; deferring the one-shot fallback"
    # Exit 75 tells the unit to retry after RestartSec=60.  This is not a
    # reboot loop: the script can only reach the reboot after 120 s uptime.
    exit 75
fi

# Charger must be present AND the battery must report Charging.  Unknown is a
# refusal, not a permit.
online=$(cat /sys/class/power_supply/battery/online 2>/dev/null || echo unknown)
status=$(cat /sys/class/power_supply/battery/status 2>/dev/null || echo unknown)
if [ "$online" != "1" ] || [ "$status" != "Charging" ]; then
    say "power safety gate: online=$online status=$status; not rebooting"
    exit 0
fi

# Cooldown survives reboots.
now=$(date +%s)
last=$(cat "$COOLDOWN_FILE" 2>/dev/null || echo 0)
case "$last" in ''|*[!0-9]*) last=0 ;; esac
if [ $((now - last)) -lt 900 ]; then
    say "LPM boot; normal reboot suppressed by 900s cooldown (last=$last)"
    exit 0
fi

mkdir -p /var/lib/nuxel
: > "$ONESHOT_FILE"
echo "$now" > "$COOLDOWN_FILE"
say "LPM boot with no touch; all gates passed; ONE normal reboot fallback"
systemctl reboot
