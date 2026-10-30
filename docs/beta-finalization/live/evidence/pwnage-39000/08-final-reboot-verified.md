# PWNAGE-39000 final reboot verification (2026-10-30)

Final boot ID: a2c7d4c5-4111-4d47-8210-28d8d0c53531
Wi-Fi SSH reconnected (10 retries x5s) -> root@192.168.178.167.

Verified after final reboot:
- NetworkManager: running:connected; radio wifi=enabled; wlan0 connected
  SSID "Nuxel Ziggo5501109"; IPv4 192.168.178.167/24.
- HTTP /api/v1/phone/status network: available=true, wifi_enabled=true,
  wifi_connected=true, wifi_state=internet, wifi_stage=online.
- Bridge journal shows the fixed on-demand retry: initial
  `NetworkManager connect failed: ServiceUnknown` at 13:11:46, then
  `NetworkManager connected` at 13:12:01.
- New P2 nuxel-pwa-host binary active (PID 6596; strings contain restart/
  `{"ok":true,...,"pending":true}`), launcher ready, all six critical services
  active: nuxel-wayland, nuxel-wl-fb, nuxel-bridge, nuxel-http-bridge,
  nuxel-bluetooth, nuxel-web.
- P8 assets served HTTP 200 for nuxel-connection-mode.png and
  nuxel-file-transfer.png.

Two deliberate reboots performed:
1. Post-P0 Wi-Fi fix (boot 6752d742...).
2. Final reboot (boot a2c7d4c5...).
