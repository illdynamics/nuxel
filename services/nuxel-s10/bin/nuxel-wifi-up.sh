#!/bin/sh
# Nuxel S10+ Wi-Fi boot policy: restore the radio state NetworkManager saved.
#
# NetworkManager already persists WirelessEnabled in
# /var/lib/NetworkManager/NetworkManager.state.  This boot helper must therefore
# NOT force Wi-Fi back ON: an owner who turned the radio OFF expects it to stay
# OFF after a reboot, exactly like Bluetooth/NFC/GNSS.  On a fresh image the
# NetworkManager default is ON, so the first boot still brings Wi-Fi up.
# NetworkManager remains the single owner of the radio and every saved profile.
#
# This unit deliberately does NOT:
#   * block rfkill (a stale software block is cleared after the radio
#     enable; hardware blocks are never touched),
#   * modify profile autoconnect flags or passwords,
#   * select a profile or run `nmcli connection up` (autoconnect owns that),
#   * start a second wpa_supplicant.
set -u

say() { printf '%s nuxel-wifi: %s\n' "$(date -u +%FT%TZ 2>/dev/null || date)" "$*"; }

# NetworkManager may still be starting when this oneshot runs.  Read the
# authoritative radio property in a bounded loop; never toggle/disconnect.
read_radio() {
    nmcli -t -f WIFI radio 2>/dev/null | tail -n1
}

i=0
while [ "$i" -lt 30 ]; do
    if command -v nmcli >/dev/null 2>&1; then
        radio=$(read_radio)
        [ -n "$radio" ] && break
    fi
    i=$((i + 1))
    sleep 0.5
done

if ! command -v nmcli >/dev/null 2>&1; then
    say "nmcli unavailable; leaving Wi-Fi unchanged"
    exit 0
fi

radio=$(read_radio)
if [ "$radio" = "disabled" ]; then
    # This is the persisted owner choice, not a stale failure.  Leave rfkill
    # and every profile untouched; a later UI toggle will enable the radio.
    say "Wi-Fi radio=disabled in persisted NetworkManager state; leaving OFF"
    exit 0
fi

# A software block can survive a userspace-only radio off.  Clear only that
# stale soft block before asking NetworkManager to enable the radio; never
# block the radio and never touch a hardware block.
if command -v rfkill >/dev/null 2>&1 && \
   rfkill list wifi 2>/dev/null | grep -q 'Soft blocked: yes'; then
    say "clearing stale software rfkill block on Wi-Fi"
    rfkill unblock wifi >/dev/null 2>&1 || true
fi
if command -v rfkill >/dev/null 2>&1 && \
   rfkill list wifi 2>/dev/null | grep -q 'Soft blocked: yes'; then
    say "software rfkill is still blocked; refusing to claim Wi-Fi enabled"
    exit 1
fi

if [ "$radio" != "enabled" ]; then
    # Enable through NetworkManager.  This is the fresh-image default; a
    # persisted OFF was handled above and is never overridden here.
    say "Wi-Fi radio=${radio:-unknown}; enabling baseline via NetworkManager"
    nmcli radio wifi on >/dev/null 2>&1 || true

    # Verify the readback.  Do not claim success from the set command alone.
    i=0
    while [ "$i" -lt 20 ]; do
        radio=$(read_radio)
        [ "$radio" = "enabled" ] && break
        i=$((i + 1))
        sleep 0.25
    done
fi

if [ "$radio" != "enabled" ]; then
    say "Wi-Fi radio verification failed (state=${radio:-unknown}); leaving profiles alone"
    exit 1
fi
say "Wi-Fi radio enabled (verified by NetworkManager; software rfkill clear)"

# Inspect actual Wi-Fi device names; do not assume the primary interface is
# wlan0.  NetworkManager autoconnects saved profiles by itself, so only wait
# for the device to settle.  Never call `nmcli connection up` here.
i=0
while [ "$i" -lt 30 ]; do
    wifi_dev=$(nmcli -t -f DEVICE,TYPE device 2>/dev/null | awk -F: '$2=="wifi" {print $1; exit}')
    [ -n "$wifi_dev" ] && break
    i=$((i + 1))
    sleep 0.5
done

if [ -z "${wifi_dev:-}" ]; then
    say "Wi-Fi radio enabled, but no NetworkManager Wi-Fi device appeared"
    exit 0
fi

i=0
while [ "$i" -lt 15 ]; do
    state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: -v d="$wifi_dev" '$1==d{print $2; exit}')
    case "$state" in
        connected|disconnected|unavailable) break ;;
    esac
    i=$((i + 1))
    sleep 1
done
state=$(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: -v d="$wifi_dev" '$1==d{print $2; exit}')
addr=$(ip -4 -brief addr show "$wifi_dev" 2>/dev/null | awk '{print $3}')
say "wifi radio=enabled device=$wifi_dev state=${state:-unknown} addr=${addr:-none}"
exit 0
