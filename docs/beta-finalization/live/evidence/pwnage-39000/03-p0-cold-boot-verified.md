# P0 Wi-Fi cold-boot verification (post-fix)

Boot ID: 6752d742-d007-4948-afd9-f942b5f8a680 (new)
- Wi-Fi SSH reconnected (10 retries x5s) -> root@192.168.178.167
- NetworkManager: running:connected; radio wifi=enabled
- wlan0:wifi:connected:Nuxel Ziggo5501109 ; addr 192.168.178.167/24
- nuxel-bridge journal: initial `NetworkManager connect failed: ServiceUnknown`
  at 12:54:24, then `NetworkManager connected` at 12:54:37 (on-demand retry).
- D-Bus GetPhoneStatus -> network.available=true, wifi_enabled=true,
  wifi_connected=true, wifi_state=internet, wifi_stage=online.
- HTTP /api/v1/phone/status -> same accurate network block.

P0 conclusion: Wi-Fi radio auto-enables, saved profile autoconnects, and the
Nuxel UI/bridge now reflects real NetworkManager state instead of caching an
unavailable state when NM's D-Bus name appears a few seconds after the bridge.
