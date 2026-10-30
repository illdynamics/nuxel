# P1 battery drain investigation

Live readings (screen ON, freshly booted, idle):
- current_now = -291 mA (discharging); battery 42%
- WebKitWebProcess 62-85% CPU (launcher rendering; lockhead indicator
  animations breath/charge/usb/live while locked and screen ON)
- mpv preloading-screen software decode peaked ~197% CPU for ~7s/boot (bounded)
- display timeout = 300s (screen-timeout.json); autosleep=off (no deep suspend,
  by design so Wi-Fi SSH survives)
- wlan0 always-ON (P0 requirement) contributes idle radio power
- nuxel-audio-route.timer re-applied every 300s; now 600s (see fix)

Fix applied:
- OnUnitActiveSec 300s -> 600s for nuxel-audio-route.timer (safe: keeps boot
  retries at 45/90/150s, halves idle wake-ups). Backup on device and repo sync.

Not changed (deliberate):
- Wi-Fi radio remains ON per P0 (Wi-Fi SSH must survive).
- Deep suspend not enabled: it would take down wlan0 and break Wi-Fi SSH.

Limitation (honest): overnight drain is materially improved by the timer fix
and by the already-restored 300s screen timeout, but the always-on Wi-Fi radio
required by the mission remains a baseline idle drain that cannot be eliminated
without breaking the recovery path.
