#!/bin/sh
# A43 live read-only diagnostics. Never prints passwords or alters audio mixers.
set -u
printf '\n=== Hardware/platform ===\n'; uname -a; cat /proc/asound/cards 2>/dev/null || true
printf '\n=== NetworkManager ===\n'; nmcli general status 2>&1 || true
nmcli -f DEVICE,TYPE,STATE,CONNECTION device status 2>&1 || true
nmcli -f IN-USE,SSID,SIGNAL,SECURITY device wifi list 2>&1 || true
rfkill list 2>&1 || true
printf '\n=== Wi-Fi firmware (names only) ===\n'; ls /lib/firmware/brcm/*4375* 2>/dev/null || true
printf '\n=== Network connectivity (not success proof until checked) ===\n'; ip -br addr; ip route; getent hosts example.com || true
printf '\n=== Audio devices ===\n'; aplay -l 2>&1 || true; aplay -L 2>&1 | head -45 || true
printf '\n=== ALSA speaker topology (read-only) ===\n'; amixer -c 0 scontrols 2>&1 || true
printf '\n=== Runtime services ===\n'; systemctl is-active nuxel-web nuxel-bridge nuxel-http-bridge NetworkManager 2>&1 || true
printf '\n=== Browser/launcher HTTP routes ===\n'; for route in /pwa/nuxel-home/index.html /pwa/nuxel-apps/settings/wifi-settings.js /pwa/nuxel-apps/browser/index.html /pwa/nuxel-home/assets/nuxel-bottom-bar2.png; do printf '%s -> ' "$route"; curl --max-time 3 -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8000$route" || true; done
printf '\nREAD ONLY: owner must confirm sound, icons, Wi-Fi and browser in physical tests.\n'
