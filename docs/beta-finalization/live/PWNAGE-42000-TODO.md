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

---

## Re-run 2026-10-31 20:30–20:55 — live root cause, top-bar visibility and full Podman rebuild

| # | Source | Live deployed path | Finding | Root cause | Repair | Test / result | Status |
|---|---|---|---|---|---|---|---|
| R1 | `images/s10plus/build-phone-rootfs-inside-fedora.sh`, `tools/s10plus/a33/nuxel-provision-services.sh` | `/var/lib/nuxel`, `/var/lib/nuxel/permissions` | Bridge reported `enabled=false` while `location-policy.json` said `enabled=true`; all first-party grants were invisible | `/var/lib/nuxel` is `0770 root:nuxel-notifications`; `nuxel-bridge` was not in that group and had no traverse permission. `_read_policy()` and `_load_all_grants()` silently failed closed. | `chmod 0771 /var/lib/nuxel`, plus exact POSIX ACLs: `nuxel-bridge:r-x` on the parent and `rwx` on `permissions/`. `acl` added to the image. | Live: bridge reads policy + grants; status flips to enabled; ACLs survive in ext4 image (`debugfs` shows `system.posix_acl_access`). | VERIFIED |
| R2 | `services/nuxel-bridge/src/bridge.py` | `/usr/lib/nuxel/nuxel-bridge/bridge.py` | Missing GeoClue timestamp was replaced with observation time and reported fresh | `_remember_fix()` synthesised `observed_at`; `_fix_view()` then aged it as a real provider time | Missing/invalid timestamp stays `null` with `timestamp_source=missing/invalid`; such a result is stale-only and `freshness_evidence=false`. Policy OFF also disconnects the GeoClue client. | `44 passed` pytest; live provider response carries `timestamp_source=provider`; no synthetic freshness. | VERIFIED |
| R3 | `pwa/nuxel-home/css/status-bar.css`, `pwa/nuxel-home/js/status-bar.js`, `tools/s10plus/a45/nuxel-statusbar.c` | `/usr/share/nuxel/pwa/nuxel-home/...` | Top-bar Wi-Fi/location icons were dark grey and nearly invisible; Quick Settings location artwork was mid-grey | Wi-Fi disconnected used `#666` at opacity `0.4`; location PNG was `grayscale(1)` at opacity `0.45`; several glyphs inherited theme text tokens | Explicit high-contrast palette (`#f5f9ff`), masked location glyph (network blue / GNSS green / neutral visible), brighter Wi-Fi neutral, explicit sound/USB/battery/clock colours, Quick Settings artwork lift; native A45 layer-shell bar now draws high-contrast Wi-Fi/location/battery glyphs instead of text-only muted state; PWA cache key `v72-p42000`. | WebKit computed style probe: `locBg=rgb(105,183,255)`, `locMask` present, `soundColor=rgb(245,249,255)`, `wifiColor=#7ee29a`. Live screenshot `68-statusbar-final-image.png`; no dark-grey glyph remains. | VERIFIED |
| R4 | `locations` end-to-end | Bridge `/rpc` | Network location fallback works independently of GNSS | Previously blocked by R1 (policy unreadable), not by GeoClue itself | No new daemon; real GeoClue 2.8.2 with the narrow agent + `CAP_NET_RAW` drop-in | Live: `source=network_wifi`, `kind=network`, `gnss=false`, accuracy 48 m / 25000 m, provider timestamp; GeoClue auto-stopped after 60 s idle. | VERIFIED |
| R5 | BCM4773 path | `/dev/ttyBCM`, `/dev/bbd_*`, `spi17.0`, GPIO145 | Driver bound and rail readable, but no GNSS firmware or BBD/LHD userspace | Repository/rootfs contains no `bcm_sensorhub_a1.patch`, no `/vendor/bin/hw/lhd`, no `gpsd`, no Android linker/HIDL runtime; SSP logs `GPS: false` | No unsafe substitution. Diagnostic reports `BLOCKED_FIRMWARE`, first failing stage `firmware`; no power applied with no consumer. | `43-gnss-truth.txt`; rail `0`; no satellite fix claimed. | BLOCKED (external artifact) |
| R6 | Full ARM64 userspace image | Podman `nuxel-build-42000` | Clean image rebuilt from current source with the permission/UI/bridge repairs | Previous image predated the root-cause fix | `fedora:43` linux/arm64 container; output `nuxel-beyond2lte-rootfs-fedora-phone-p42000.img`; `e2fsck -fn` + offline verifier PASS; ACLs verified inside image. | Build log `66-podman-rootfs-final-build.log.txt`; sha256 `150a9518…f6116`; source parity checks PASS. | VERIFIED |
| R7 | Privacy default | `/var/lib/nuxel/permissions/location-policy.json` | Must remain OFF by default | Re-run had to enable location for tests | Final policy reset to OFF, stale fix cleared, GeoClue idle, GPS rail `0`. | Final post-reboot verification. | VERIFIED |
