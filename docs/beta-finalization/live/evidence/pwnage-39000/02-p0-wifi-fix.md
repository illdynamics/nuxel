# P0 Wi-Fi fix — NetworkManager D-Bus late-connect retry

Root cause (live, after cold boot):
- nuxel-bridge.service started before NetworkManager's D-Bus name was available.
  Log: `NetworkManager connect failed: org.freedesktop.DBus.Error.ServiceUnknown`
- `NetworkManagerConnector.get_status()` returned `available:false` permanently
  when `self.connected` was False, without ever retrying. So the Quick Settings
  UI (and /api/v1/phone/status) showed `wifi_state=unavailable` while NM was
  actually connected to `Nuxel Ziggo5501109` — a real UI/NM discrepancy.

Fix:
- Added bounded retry to `NetworkManagerConnector.connect(force=False)`
  (NUXEL_NM_RETRY default 5s, mirroring GeoClueConnector).
- `get_status()` and `set_wifi_enabled()` now attempt `self.connect()` on demand
  instead of caching a permanent unavailable state.
- Deployed to /usr/lib/nuxel/nuxel-bridge/bridge.py (backup:
  bridge.py.bak-pwnage39000-20261030T115235Z) and to repo
  services/nuxel-bridge/src/bridge.py.

Verification (runtime, after `systemctl restart nuxel-bridge`):
- GET /api/v1/phone/status -> network.available=true, wifi_enabled=true,
  wifi_connected=true, wifi_state=internet, wifi_stage=online.
- py_compile OK on device and repo.
