#!/bin/sh
# A74 USB-unplug evidence logger — runs on-device, survives the USB drop.
#
# SAFETY (the whole point of A74): it NEVER reads the DWC3 debugfs link_state
# (or any debugfs/register node).  On the S10+ downstream 4.14 kernel that
# debugfs register read is what hard-locked-up the kernel after a physical
# detach (bus SLVERR on FSYS0 -> watchdog reset).  This logger only samples
# safe sysfs/proc attributes.
#
# Bounded + rate-limited: it writes only on state change plus a heartbeat every
# 15 s, and rotates the log at 256 KiB so it can never fill the filesystem.
LOG=/var/lib/nuxel/a74-usb-unplug.log
MAX=262144
mkdir -p /var/lib/nuxel

rotate() {
  if [ -f "$LOG" ] && [ "$(stat -c %s "$LOG" 2>/dev/null || echo 0)" -gt "$MAX" ]; then
    mv -f "$LOG" "$LOG.1" 2>/dev/null || true
  fi
}

boot_line() {
  printf '{"t":%s,"boot_id":"%s","up":%s}' \
    "$(date +%s)" "$(cat /proc/sys/kernel/random/boot_id 2>/dev/null)" \
    "$(cut -d' ' -f1 /proc/uptime 2>/dev/null)"
}

echo "=== A74 logger start $(date -u +%FT%TZ) ===" >> "$LOG"
rotate
last=""
i=0
while true; do
  i=$((i+1))
  TS=$(date +%s)
  dr=$(cat /sys/class/typec/port0/data_role 2>/dev/null | tr -d '\n')
  udc=$(cat /sys/class/udc/10c00000.dwc3/state 2>/dev/null | tr -d '\n')
  spd=$(cat /sys/class/udc/10c00000.dwc3/current_speed 2>/dev/null | tr -d '\n')
  ac=$(cat /sys/class/power_supply/ac/online 2>/dev/null | tr -d '\n')
  usb=$(cat /sys/class/power_supply/usb/online 2>/dev/null | tr -d '\n')
  ind=$(python3 /usr/lib/nuxel/nuxel-bridge/system_indicators.py 2>/dev/null | tr -d '\n')
  boot="$(boot_line)"
  line="${boot},\"data_role\":\"$dr\",\"udc\":\"$udc\",\"speed\":\"$spd\",\"ac\":\"$ac\",\"usb\":\"$usb\",\"ind\":$ind}"
  if [ "$line" != "$last" ]; then
    rotate
    echo "$line" >> "$LOG"
    last="$line"
  fi
  if [ $((i % 30)) -eq 0 ]; then
    rotate
    echo "${boot},\"heartbeat\":true,\"data_role\":\"$dr\",\"udc\":\"$udc\",\"speed\":\"$spd\"}" >> "$LOG"
  fi
  sleep 0.5
done
