# Status before final reboot (2026-10-30)

Fixes deployed this run:
- P0 bridge.py NetworkManager retry-on-demand (live + repo), verified cold boot.
- P1 nuxel-audio-route.timer OnUnitActiveSec 300s -> 600s (live + repo).
- P2 nuxel-pwa-host rebuilt from a45 source with async reboot + immediate ack,
  deployed, running (PID 10474), service active.
- P5 assets present/byte-identical; screenshot saved.
- P8 nuxel-connection-mode.png + nuxel-file-transfer.png deployed (HTTP 200);
  nuxel-usb-mode.sh helper deployed; charging verified.

Honest blockers (documented, not claimed done):
- P3: Flatpak unavailable and rootfs 98% full; native firefox/vlc exist.
- P4: apps.register endpoint missing -> install is local-only, not launchable.
- P6: launcher WebKitWebProcess idle CPU 62-85% (profiled).
- P7: top-bar lacks BT/GPS/audio/cellular UI; real state = BT on, GPS
  unavailable (geoclue inactive), cellular no modem.
- P8: file-transfer genuinely unsupported (no MTP responder; no raw mass
  storage used) -> honest failure, charging mode works.
- P9: hci0 UP/RUNNING but file-send UI + OBEX transfer backend not implemented.
