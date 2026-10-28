#!/bin/sh
# Remove the "charger/LPM boot has no touch" dead end.
#
# S-Boot passes androidboot.mode=charger when it powers the board up with a
# charger attached; sec_ts then refuses to bind for that boot.  The vendor
# kernel decision is irreversible for the boot, but an OS-initiated
# `systemctl reboot` does NOT re-enter charger mode.  Reboot once, normally,
# with a persisted cooldown so a broken boot can never become a reboot loop.
set -u
say() { echo "$(date -u +%FT%TZ) nuxel-charger-mode: $*"; }

cmdline=$(cat /proc/cmdline 2>/dev/null || true)
case "$cmdline" in
    *androidboot.mode=charger*|*lpcharge=1*|*androidboot.lpm=1*) ;;
    *) exit 0 ;;
esac

online=$(cat /sys/class/power_supply/battery/online 2>/dev/null || echo 0)
[ "$online" = "1" ] || { say "LPM marker seen but charger offline; not rebooting"; exit 0; }

stamp=/var/lib/nuxel/charger-mode-recovery.stamp
now=$(date +%s)
last=$(cat "$stamp" 2>/dev/null || echo 0)
case "$last" in ''|*[!0-9]*) last=0 ;; esac
if [ $((now - last)) -lt 600 ]; then
    say "LPM boot; normal reboot suppressed by 600s cooldown (last=$last)"
    exit 0
fi
mkdir -p /var/lib/nuxel
echo "$now" >"$stamp"
say "LPM boot detected with charger online; rebooting into normal (touch) mode"
systemctl reboot
