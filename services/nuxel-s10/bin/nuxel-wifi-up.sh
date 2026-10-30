#!/bin/sh
# Nuxel S10+ Wi-Fi boot bridge: bring up an owner-chosen WLAN console without
# forcing the radio on by default.
#
# PWNAGE-37000 BUTTERSCOTCH: previous revisions ran `rfkill unblock wifi` and
# `nmcli radio wifi on` unconditionally on every boot, so an owner who turned
# Wi-Fi off always found it re-enabled after reboot. That also made the radio
# cost battery and compete with the UI during early boot.
#
# New policy: NetworkManager remains the single owner of the radio. This unit
# only acts when the radio is already enabled and wlan0 is genuinely
# disconnected with a saved autoconnect profile; otherwise it leaves the radio
# and profiles exactly as the owner configured them.
set -u

say() { printf '%s nuxel-wifi: %s\n' "$(date -u +%FT%TZ 2>/dev/null || date)" "$*"; }

# Read the authoritative radio state. `nmcli -t -f WIFI radio` returns exactly
# one line ("enabled" or "disabled"); it is a read, not a toggle.
radio=$(nmcli -t -f WIFI radio 2>/dev/null | tail -n1)
case "$radio" in
    enabled) : ;;
    disabled)
        say "Wi-Fi radio disabled by owner; leaving it off"
        exit 0
        ;;
    *)
        say "Wi-Fi radio state unavailable (${radio:-none}); leaving it unchanged"
        exit 0
        ;;
esac

# wlan0 is the primary radio on this image. If it is absent after a bounded
# wait, report honestly and exit before touching any profile.
i=0
while [ "$i" -lt 30 ]; do
    nmcli -t -f DEVICE,TYPE device 2>/dev/null | grep -q '^wlan0:wifi$' && break
    i=$((i + 1))
    sleep 0.5
done
if ! nmcli -t -f DEVICE,TYPE device 2>/dev/null | grep -q '^wlan0:wifi$'; then
    say "wlan0 not present after 15s; leaving Wi-Fi alone"
    exit 0
fi

# NetworkManager is the single owner of the radio and already autoconnects
# every saved profile whose connection.autoconnect=yes. Do NOT call
# `nmcli connection up` here: on a cold boot it serializes behind an in-flight
# autoconnect and was measured at ~25 s of extra multi-user.target latency
# (PWNAGE-37000). Just wait for wlan0 to leave the activation state; a
# connected link returns on the first sample, and an offline boot is bounded.
i=0
while [ "$i" -lt 15 ]; do
    state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: '$1=="wlan0"{print $2; exit}')
    case "$state" in
        connected|disconnected|unavailable) break ;;
    esac
    i=$((i + 1))
    sleep 1
done
state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: '$1=="wlan0"{print $2; exit}')
addr=$(ip -4 -brief addr show wlan0 2>/dev/null | awk '{print $3}')
say "wifi state=${state:-unknown} addr=${addr:-none}"
exit 0
