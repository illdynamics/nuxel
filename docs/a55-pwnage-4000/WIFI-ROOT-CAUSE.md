# A55 Wi-Fi — Root Cause & Live Verification

## Symptom (owner-reported, prior cycle)
"Connect hangs at **Associating DHCP…**" after password submit.

## Root cause (already fixed, preserved this cycle)
1. **Backend (A51, `9fe0ebc`):** pre-A51 code passed `specific_object='/new'` to
   `AddAndActivateConnection` → NM `Device.SpecificObjectNotFound`. Fixed with a
   verified AP object path from the current scan list + bounded rescan +
   `ActivateConnection` reuse. **Not reintroduced.**
2. **Frontend (A54):** `wifi-settings.js` rendered "Associating/DHCP" once and
   never re-rendered the authoritative NM state, although the connection actually
   completed. Fixed with honest per-stage labels + bounded polling.

## Live evidence this cycle (device, redacted)
- `nmcli -t -f DEVICE,TYPE,STATE,CONNECTION dev status` →
  `wlan0:wifi:connected:<network>` (association + auth complete).
- `ip -br addr` → `wlan0 192.168.178.167/24` + global IPv6.
- `ip route` → `default via 192.168.178.1 dev wlan0 proto dhcp src 192.168.178.167 metric 600`.
- `getent ahosts www.google.nl` → resolves (IPv6).
- `curl -s -o /dev/null -w '%{http_code}' --max-time 15 https://www.gstatic.com/generate_204` → `204`.
- `curl -s -o /dev/null -w '%{http_code}' --max-time 20 -L https://www.google.nl` → `200`.
- `date -u` correct; CA bundle present (`/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt`).

## Gate
- **WIFI-L2 / WIFI-IP:** PASS_INTEGRATION (live association, IP, route, DNS, verified HTTPS).
- **WIFI-PERSIST (autoconnect after cold boot):** NOT_TESTED — requires owner-approved reboot.

Redaction: SSID/PSK/BSSID/MAC omitted.
