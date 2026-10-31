# PWNAGE-42000 — Nuxel GPS & Location ultimate fixer

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820
**Live host:** `root@192.168.178.167` over Wi-Fi SSH
**Executed:** 2026-10-31
**Released in:** `v0.7.4-beta`
**Evidence:** `docs/beta-finalization/live/evidence/pwnage-42000/`

| # | Source | Live path | Finding | Root cause | Repair | Result | Status |
|---|---|---|---|---|---|---|---|
| 0 | `services/nuxel-bridge/src/geoclue_agent.py`, `services/nuxel-bridge/systemd/nuxel-geoclue-agent.service` (new) | `/usr/lib/nuxel/nuxel-bridge/geoclue_agent.py`, `/etc/systemd/system/nuxel-geoclue-agent.service` | `Manager.GetClient` returned `NoReply` | GeoClue2 requires an agent registered for the caller UID before `GetClient` completes; embedding it in the single-threaded bridge deadlocked the callback | Separate narrow agent as `nuxel-bridge`, authorizes only `org.nuxel.Bridge`, re-registers after GeoClue restarts | `GetClient` + `Start` work; no `NoReply` | VERIFIED |
| 1 | `services/nuxel-bridge/src/bridge.py` | `/usr/lib/nuxel/nuxel-bridge/bridge.py` | `SetDesktopId`/`SetRequestedAccuracyLevel`/`GetLocation` were called as methods | GeoClue 2.8.2 exposes them as properties; `Location` is read-only; `Timestamp` is `(seconds, microseconds)` | `Properties.Set`/`Get`; tuple timestamp; one reconnect after provider restart | Network fix acquired | VERIFIED |
| 2 | `services/nuxel-s10/systemd/geoclue.service.d/10-nuxel-network.conf` (new) | `/etc/systemd/system/geoclue.service.d/10-nuxel-network.conf` | GeoClue Wi-Fi/IP could not resolve DNS | Samsung kernel denies `AF_INET` socket creation without `CAP_NET_RAW` | Narrow ambient capability on GeoClue only | Real GeoIP coordinate | VERIFIED |
| 3 | `services/nuxel-bridge/src/hw_providers.py` | `/usr/lib/nuxel/nuxel-bridge/hw_providers.py` | `GnssProvider` treated `/dev/ttyBCM` as NMEA; power success without readback; no leases | BCM4773 uses Broadcom BBD/LHD RPC; a sysfs write is not proof | BBD/LHD-aware inventory/probe, verified readback, ref-counted leases, pre-probe state restoration, no NMEA parsing | Honest `BLOCKED_FIRMWARE`; no fake fix | VERIFIED (software) |
| 4 | `services/nuxel-bridge/src/api.py` | `/usr/lib/nuxel/nuxel-bridge/api.py` | `gnss-power` was gated by `location:read` | Hardware lifecycle is management | `gnss-power` requires `location:manage`; `gnss-probe` keeps `location:read` | Maps denied; Settings allowed; rail verified | VERIFIED |
| 5 | `pwa/nuxel-common/geolocation.js` | `/usr/share/nuxel/pwa/nuxel-common/geolocation.js` | missing coords became `0,0`; missing timestamp became now; NaN accuracy; one-shot watch | Stale shim | Strict validation, provider timestamp preserved or `null`, W3C option mapping, shared polling watch with `clearWatch` | All shim checks pass | VERIFIED |
| 6 | `pwa/nuxel-home/js/qs.js`, `pwa/nuxel-home/js/status-bar.js`, `pwa/nuxel-home/index.html`, `pwa/nuxel-home/css/status-bar.css` | same | no source distinction; no top-bar indicator | UI ignored source | Source-aware location tile and indicator (network/GNSS/searching/OFF) | Indicator appears only when ON | VERIFIED |
| 7 | `pwa/nuxel-common/maps-core.js`, `pwa/nuxel-apps/maps/js/maps.js` | same | any fix drawn as GPS | source ignored | GNSS/network/stale markers; no timestamp => stale | Map source semantics pass | VERIFIED |
| 8 | `tools/s10plus/a33/nuxel-gnss-diag.sh`, `configs/nuxel/gnss/gnss.json` | `/usr/local/bin/nuxel-gnss-diag.sh`, `/etc/nuxel/gnss/gnss.json` | assumed NMEA/9600 baud and generic firmware names | S10+ is BBD/LHD with a patch-loader firmware | Protocol-aware stages, vendor-runtime inventory, `BLOCKED_FIRMWARE`/`BLOCKED_PROTOCOL` | `BLOCKED_FIRMWARE`, first stage=firmware | VERIFIED |
| 9 | hardware | `/dev/ttyBCM`, `/dev/bbd_*`, `spi17.0`, GPIO145 | SPI bound, BBD nodes exist, rail verified, SSP reports `GPS: false`; no patch firmware; no Android runtime | Compatible BBD patch + Android/Bionic stack absent | Documented the exact missing artifacts; no unsafe substitution | Real satellite fix NOT obtained | BLOCKED (hardware) |
| 10 | privacy policy | `/var/lib/nuxel/permissions/location-policy.json` | policy persisted ON from a prior session | preserved user state | Final state reset to OFF; OFF clears fix and stops acquisition | Final OFF verified | VERIFIED |
| 11 | boot persistence | `/usr/lib/nuxel/stage36000/...` | first reboot reverted `geoclue.conf` and `nuxel-gps-status` | `nuxel-apply-36000.service` installs stage copies every boot | Updated stage copies to the same hashes; second reboot verified | PASS after second reboot | VERIFIED |

## Final status

- **Network location:** PASS — genuine GeoClue Wi-Fi/IP result
  `51.4005, 5.47196 ±25000 m`, source `network_wifi`.
- **Satellite GNSS:** BLOCKED — no compatible BBD patch firmware and no
  Android vendor LHD+gpsd+HIDL runtime. No fix claimed.
- **Location UI/API/watch shim:** PASS by unit, integration and live D-Bus tests.
- **Final policy:** OFF. **GPS rail:** 0. **GeoClue:** auto-stops when idle.

## v0.7.4-beta packaging

`v0.7.4-beta` wires the agent into the fresh image: the rootfs builder installs
`nuxel-geoclue-agent.service`, the `CAP_NET_RAW` drop-in and
`python3-dbus`/`python3-gobject`, and enables the agent in
`multi-user.target.wants`.
