#!/bin/sh
# A73 USB-unplug evidence logger — runs on-device, survives console disconnect.
# Samples physical USB signals + the backend indicator JSON; only writes on
# state change (plus a heartbeat) so the log is compact. Detach/reattach
# timestamps survive the USB link drop.
LOG=/var/lib/nuxel/a73-usb-unplug.log
mkdir -p /var/lib/nuxel
echo "=== A73 logger start $(date -u +%FT%TZ) ===" >> "$LOG"
last=""
i=0
while true; do
  i=$((i+1))
  TS=$(date +%s)
  dr=$(cat /sys/class/typec/port0/data_role 2>/dev/null | tr -d '\n')
  lk=$(cat /sys/kernel/debug/10c00000.dwc3/link_state 2>/dev/null | tr -d '\n')
  udc=$(cat /sys/class/udc/10c00000.dwc3/state 2>/dev/null | tr -d '\n')
  spd=$(cat /sys/class/udc/10c00000.dwc3/current_speed 2>/dev/null | tr -d '\n')
  ac=$(cat /sys/class/power_supply/ac/online 2>/dev/null | tr -d '\n')
  usb=$(cat /sys/class/power_supply/usb/online 2>/dev/null | tr -d '\n')
  ind=$(python3 /usr/lib/nuxel/nuxel-bridge/system_indicators.py 2>/dev/null | tr -d '\n')
  line="{\"t\":$TS,\"data_role\":\"$dr\",\"link_state\":\"$lk\",\"udc\":\"$udc\",\"speed\":\"$spd\",\"ac\":\"$ac\",\"usb\":\"$usb\",\"ind\":$ind}"
  if [ "$line" != "$last" ]; then
    echo "$line" >> "$LOG"
    last="$line"
  fi
  if [ $((i % 30)) -eq 0 ]; then
    echo "{\"t\":$TS,\"heartbeat\":true,\"data_role\":\"$dr\",\"link_state\":\"$lk\",\"udc\":\"$udc\"}" >> "$LOG"
  fi
  sleep 0.5
done
