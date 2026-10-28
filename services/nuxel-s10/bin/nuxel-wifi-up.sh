#!/bin/sh
# Ensure Wi-Fi is radio-enabled and a known profile is connected on every boot.
# SSH-over-WLAN is a first-class console path for Nuxel, so this is deliberately
# independent of nuxel-web / the launcher.
set -u
say() { echo "$(date -u +%FT%TZ) nuxel-wifi: $*"; }

rfkill unblock wifi 2>/dev/null || true
nmcli radio wifi on 2>/dev/null || true

i=0
while [ "$i" -lt 40 ]; do
    nmcli -t -f DEVICE,TYPE device 2>/dev/null | grep -q '^wlan0:wifi$' && break
    i=$((i + 1)); sleep 0.5
done

# Make every stored Wi-Fi profile eligible for boot autoconnect.  Passwords are
# untouched; only the two connection flags are changed.
nmcli -t -f NAME,TYPE connection show 2>/dev/null | while IFS=: read -r name type; do
    [ "$type" = "wifi" ] || continue
    nmcli connection modify "$name" connection.autoconnect yes \
        connection.autoconnect-retries 0 >/dev/null 2>&1 || true
done

if ! nmcli -t -f DEVICE,STATE device 2>/dev/null | grep -q '^wlan0:connected'; then
    name=$(nmcli -t -f NAME,TYPE,AUTOCONNECT connection show 2>/dev/null |
           awk -F: '$2=="wifi" && $3=="yes" {print $1; exit}')
    if [ -n "${name:-}" ]; then
        say "bringing up profile: $name"
        timeout 45 nmcli connection up "$name" >/dev/null 2>&1 || true
    fi
fi

for i in $(seq 1 30); do
    state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: '$1=="wlan0"{print $2; exit}')
    [ "$state" = "connected" ] && break
    sleep 1
done
state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: '$1=="wlan0"{print $2; exit}')
addr=$(ip -4 -brief addr show wlan0 2>/dev/null | awk '{print $3}')
say "wifi state=${state:-unknown} addr=${addr:-none}"
exit 0
