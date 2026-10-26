# A75 — Wi-Fi Restoration

## Backend found
- NetworkManager `1.54.3` + `NetworkManager-wifi`, D-Bus `org.freedesktop.NetworkManager`.
- wpa_supplicant `2.11` present.
- Two Wi-Fi interfaces enumerated by NM: `wlan0` and `wlan1`
  (`/org/freedesktop/NetworkManager/Devices/2` and `…/3`), both type 2.
- Broadcom `brcmfmac`/dhd radio is enumerating and scanning (real APs returned).

## State before/after
| Metric | Before | After |
|---|---|---|
| Bridge version | 0.6.1-beta | 0.6.5-beta (repo) |
| `NetworkWifiSetEnabled` | worked via D-Bus when bridge was up | works, readback confirmed |
| `NetworkWifiScan` | real AP list | real AP list (multiple SSIDs, BSSIDs, security, strength) |
| `NetworkWifiConnect` | stale_scan error on a vanished AP (truthful) | real association + DHCP |

## End-to-end evidence (real, on-device)
1. **Scan** — returned `"Undetektable"` (WPA3), `"A23 van Yasmiin"` (WPA2),
   `"XPA-900BT"`, and `"HotspotArriva_B_9746"` (open) with verified AP object
   paths/BSSIDs/frequencies. `success: true`.
2. **Connect (open, no credentials)** to public `HotspotArriva_B_9746`:
   `{"success":true,"state":"connecting","stage":"associating",…}`
   → `AddAndActivateConnection` returned `Settings/5` + `ActiveConnection/1`.
3. **IP/route** — `wlan0` up with `192.168.3.236/24`, default route
   `via 192.168.3.1 dev wlan0 proto dhcp`.
4. **NetworkManager state** — `State=100` (activated), `Connectivity=4`
   (full internet), `wifi_state="internet"`, `wifi_stage="online"`.
5. **DNS** — `getent hosts example.com` resolved real addresses.
6. **HTTP** — `http://example.com/` → `HTTP 200` in ~0.08s.
7. **TLS/HTTPS** — `curl https://example.com/` failed with
   `SSL routines::unexpected eof while reading`. This is **not a Nuxel defect**:
   `http://neverssl.com/` returned a `WISPAccessGatewayParam` captive-portal
   document, proving the public hotspot intercepts HTTPS until its terms are
   accepted. Nuxel TLS/browser behaviour was already the regression target and
   was not modified; an HTTPS proof on a non-captive/owner network remains
   `NOT_TESTED`.

## Cleanup / privacy
- Disconnected (`NetworkWifiDisconnect` → `success: true`).
- Removed only the transient public profile I created (`NetworkWifiForget`
  `/org/freedesktop/NetworkManager/Settings/5` → `success: true`).
- The four owner saved profiles remain untouched (no secrets were printed):
  `Studio E Guest`, `Undetektable`, `Ziggo5501109`, `Snoerbreuk`.

## Rollback
Same as the bridge rollback in `00-CURRENT-STATE-AND-DEPLOYED-HASHES.md`;
no NetworkManager config or saved profile was changed.
