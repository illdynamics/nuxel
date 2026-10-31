# PWNAGE-42000 — Real GNSS, GeoClue, location provider and end-to-end location repair

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
**OS:** Nuxel (Fedora 43 aarch64), kernel `4.14.253`
**Live host:** `root@192.168.178.167` over Wi-Fi SSH
**Date:** 2026-10-31 (two reboot cycles verified)
**Released in:** `v0.7.4-beta`
**Evidence:** `docs/beta-finalization/live/evidence/pwnage-42000/`

> **Honesty statement.** A genuine **network-derived** location works. No
> satellite fix was obtained. The BCM4773 path stops at missing BBD/LHD patch
> firmware and the Android/Bionic `lhd` + `gpsd` runtime. No coordinate,
> satellite count, accuracy value or fresh timestamp was fabricated anywhere in
> this change.

## 1. What works

```
latitude 51.4005  longitude 5.47196  accuracy +/-25000 m  source network_wifi
```

The fix was obtained through GeoClue 2.8.2 and verified after a full reboot
(`41-final-post-reboot-verification.txt`, `42-final-idle-state.txt`).

## 2. Root cause 1 — GeoClue needs a per-UID agent

`Manager.GetClient` returned `NoReply`. GeoClue queues that call until an agent
is registered for the **calling UID**; there was no agent, so the client
connection vanished before one appeared:

```
Client `:1.170` waiting for agent for user ID '0'
Client `:1.170` vanished before agent appeared
```

Embedding the agent inside `nuxel-bridge` did **not** work: `GetClient` blocks
the bridge's single-threaded D-Bus loop while GeoClue calls back into the agent
on the same connection, reproducing the timeout.

**Fix:** a separate narrow service, `nuxel-geoclue-agent.service`, runs as the
`nuxel-bridge` user, exports `org.freedesktop.GeoClue2.Agent`, authorizes only
`org.nuxel.Bridge`, and re-registers after a GeoClue restart
(`services/nuxel-bridge/src/geoclue_agent.py`,
`services/nuxel-bridge/systemd/nuxel-geoclue-agent.service`).

## 3. Root cause 2 — the kernel denies `AF_INET` without `CAP_NET_RAW`

GeoClue's Wi-Fi/IP source could not resolve DNS. On this Samsung 4.14 vendor
kernel, `socket(AF_INET, SOCK_DGRAM)` returns `EACCES` for uid 999 and succeeds
with `CAP_NET_RAW`. A narrow ambient capability on GeoClue only:

```ini
# services/nuxel-s10/systemd/geoclue.service.d/10-nuxel-network.conf
[Service]
CapabilityBoundingSet=CAP_NET_RAW
AmbientCapabilities=CAP_NET_RAW
```

## 4. Bridge correctness — the real GeoClue 2.8.2 API

- `DesktopId` and `RequestedAccuracyLevel` are read/write properties
  (`org.freedesktop.DBus.Properties`), not methods.
- `Location` is a read-only property; **there is no `GetLocation` method.**
- `Timestamp` is a `(seconds, microseconds)` tuple.
- The client reconnects once after a provider restart.
- The bridge stays bounded (`NUXEL_GEOCLUE_TIMEOUT`, connect timeout) so a
  wedged provider cannot stall Quick Settings.

## 5. GNSS hardware truth

| Item | Observed |
|---|---|
| SPI device | `spi17.0` at `/spi@10970000/BCM4773@0`, driver `brcm gps spi` |
| Transport | `/dev/ttyBCM` — Broadcom **BBD/LHD RPC**, not NMEA |
| Loader/control | `/dev/bbd_patch`, `/dev/bbd_control`, `/dev/bbd_sensor` |
| Power rail | `GPS_PWR_EN` GPIO145 read/write verified 0 → 1 → 0 |
| Sensor hub | kernel repeats `[SSP] ... GPS: false` |
| GNSS firmware | none in `/lib/firmware`, `/vendor/firmware` or `/system` |

A readable node, a bound SPI driver or an SPI register response is **not** a
fix.

## 6. Why satellite GNSS is blocked

1. **Missing compatible BBD sensor-hub patch firmware.** `lhd.conf` points at
   `/dev/bbd_patch` (fallback `/system/bin/bcm_sensorhub_a1.patch`); no such
   patch exists in the Nuxel rootfs, the vendor blob set or a local stock image.
2. **Missing Android/Bionic location runtime.** The vendor `lhd` and `gpsd`
   binaries are Android aarch64 ELF with interpreter `/system/bin/linker64`;
   they need Bionic, Android HIDL and the vendor `/system` + `/vendor` trees.
3. **No native BBD/LHD decoder exists.** Stock Linux `gpsd` cannot decode
   Broadcom BBD/LHD RPC.

Verdict: `BLOCKED_FIRMWARE`, first failing stage `firmware`.
`LocationConnector` reports `gnss_fix=false` and `fix_supported=false`.

## 7. PWA and UI correctness

- `pwa/nuxel-common/geolocation.js` rejects missing/NaN/out-of-range
  coordinates (never `0,0`), preserves a missing provider timestamp (never
  substitutes `Date.now()`), leaves unknown accuracy `null`, maps W3C options
  and owns one shared polling watch that stops all timers when the last watch
  is cleared or policy goes OFF.
- `maps-core.js` / `maps.js` distinguish GNSS, network and stale fixes; a fix
  without a timestamp is stale, never fresh.
- Quick Settings distinguishes network vs GNSS; the top-bar indicator is
  source-aware (blue network, green GNSS, pulse searching, hidden OFF).
- `gnss-power` requires `location:manage`; the read-only `gnss-probe` keeps
  `location:read`, so Maps cannot power the rail.

## 8. Diagnostics and configuration

- `tools/s10plus/a33/nuxel-gnss-diag.sh` reports stages
  device node → module → firmware → vendor runtime → userspace → stream → fix
  and the first failing stage.
- `configs/nuxel/gnss/gnss.json` records the BBD/LHD protocol
  (`nmea_over_ttybcm: false`, `stock_gpsd_can_decode: false`,
  `android_vendor_runtime_required: true`) and the verdict vocabulary.

## 9. Final state

| Item | Result |
|---|---|
| Network location | **PASS** — real GeoClue Wi-Fi/IP fix, source `network_wifi` |
| Satellite GNSS | **BLOCKED** — no BBD patch firmware / Android LHD runtime; no fix claimed |
| Location UI/API/watch shim | **PASS** (unit, integration and live D-Bus) |
| Privacy policy | **OFF** at the end; OFF clears the fix, stops acquisition and leaves the rail at 0 |
| GPS rail | `0` at rest; verified write/readback |

## 10. Remaining work

Outdoor satellite acceptance requires a compatible S10+ BBD sensor-hub patch
and a safe BBD/LHD runtime. Until then, the outdoor procedure in
`docs/beta-finalization/manual-proof/13-gps.md` remains `BLOCKED_FIRMWARE`.
