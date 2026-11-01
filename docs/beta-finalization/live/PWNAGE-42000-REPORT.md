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

---

## Re-run addendum — 2026-10-31 (root cause, top-bar contrast, Podman rebuild)

### 1. Why Location looked disabled even when the policy file said ON

The bridge was not lying about its own state; it could not read the policy. The
shared data directory was:

```
/var/lib/nuxel            0770 root:nuxel-notifications
/var/lib/nuxel/permissions 0770 nuxel:nuxel
```

`nuxel-bridge` is in group `nuxel`, but it had no execute/traverse permission on
the parent `0770 root:nuxel-notifications` directory. Therefore both
`LocationConnector._read_policy()` and `_load_all_grants()` failed closed:
`enabled` became `false` and every first-party capability grant disappeared.
This is why `Manager.GetClient` itself was healthy after the earlier agent fix,
yet the bridge still reported `Location is disabled` and `CAPABILITY_DENIED`.

Repair (source + live):

- `chmod 0771 /var/lib/nuxel` (traverse, not listable by unrelated users)
- narrow ACL `u:nuxel-bridge:r-x` on `/var/lib/nuxel`
- narrow ACL `u:nuxel-bridge:rwx` on `/var/lib/nuxel/permissions`
- `acl` added to the Fedora package set and the image builder
- the same operations added to `nuxel-provision-services.sh` for future live
  deployments

The fresh ext4 image was inspected with `debugfs`: the `system.posix_acl_access`
xattr is present on both directories, so the fix is carried by the image and not
only by the live handset.

### 2. Location provider result

Live bridge response after the repair:

```
success=true state=fixed source=network_wifi kind=network
gnss=false network=true accuracy=48.0 m timestamp=<provider seconds>
```

A second observation returned the same network source with ±25000 m (the
provider-reported coarse fallback). Neither result is labelled GNSS. After
policy OFF, the position was cleared, the client disconnected, and GeoClue
exited after its normal 60-second idle window. The BCM4773 rail remained `0`.

### 3. Missing timestamps are no longer made fresh

`LocationConnector._remember_fix()` previously substituted `observed_at` when
GeoClue omitted `Timestamp`. That made an un-timed coordinate look fresh. It now
stores `timestamp: null` with `timestamp_source: missing` (or `invalid`), and
`_fix_view()` classifies it as stale with `freshness_evidence=false`. The API
exposes `fix_timestamp_source` and `freshness_evidence` so Maps/Settings can
make the same distinction.

### 4. Top-bar icon visibility repair

The dark-grey/invisible glyphs had concrete causes:

- disconnected Wi-Fi was drawn `#666` at opacity `0.4`
- the location artwork was a mid-grey PNG rendered with
  `filter: grayscale(1)` and opacity `0.45`
- sound/USB/location glyphs inherited theme text tokens

The status bar now has a final, explicit high-contrast palette. Location uses the
same artwork as a CSS mask, so the source PNG's grey pixels cannot dim it:
neutral is visible grey-blue, network is `#69b7ff`, GNSS is `#6ee7a8`. Wi-Fi
neutral is `#c8d7ea`; connected Wi-Fi remains green. Quick Settings artwork is
brightness-lifted without changing its files. The PWA cache key is
`v72-p42000`.

WebKit computed-style evidence from the live image:

```
locBg=rgb(105, 183, 255)  locMask=url(.../09-location.png)  locOp=1
soundColor=rgb(245, 249, 255)  wifiColor=#7ee29a  wifiOp=1
```

The native A45 layer-shell bar (`nuxel-statusbar`) was also repaired: it now
draws explicit Cairo Wi-Fi, location and battery glyphs instead of a text-only
muted `Wi-Fi 100%` string. The live compositor capture
`71-topbar-final-unlocked.png` contains the expected saturated pixels:
`(115,225,153)` green Wi-Fi and, when Location is ON, `(104,184,255)` blue
location. The deployed binary is
`f98f5584c6e057d09925a85734f1a3fea18cc9bd841df647689e988fec8385b4`.

### 5. Satellite GNSS truth

No satellite fix was obtained. The BCM4773 SPI driver is bound and the GPIO145
rail is readable, but:

- `/dev/ttyBCM` is a BBD/LHD RPC transport, not NMEA
- the rootfs/image contains no compatible `bcm_sensorhub_a1.patch`
- it contains no Android `lhd`, `gpsd`, linker64, HIDL GNSS implementation or
  vendor runtime
- SSP continues to report `GPS: false`

The diagnostic therefore reports `BLOCKED_FIRMWARE` at the `firmware` stage.
This is a genuine external-artifact blocker, not a software pass.

### 6. Full Podman rebuild

A clean Fedora 43 aarch64 rootfs was built in container `nuxel-build-42000`:

```
build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-p42000.img
sha256 150a9518984048a85ec0f1c40ab0ec48f1f474e7f875491066f8b677333f6116
```

`e2fsck -fn` and the offline rootfs verifier passed. Source parity for
`bridge.py`, `status-bar.css`, `status-bar.js`, `index.html`, `manifest.json`
and `sw.js` was checked against the staged image; the ACL fix was verified in
the image with `debugfs`.

### 7. Evidence

- `evidence/pwnage-42000/40-permission-store-root-cause.txt`
- `41-geoclue-network-location.txt`
- `42-network-location-RESTRICTED.txt` (owner-only full coordinates)
- `43-gnss-truth.txt`
- `45-podman-rootfs-build.log`
- `46-new-image-sha256.txt`
- `49-live-provider-lifecycle.txt`
- `50`–`54`, `56`, `64`, `68`, `71` top-bar capture series
  (`68-statusbar-final-image.png` shows blue network + green Wi-Fi; `71-topbar-final-unlocked.png`
  is the post-reboot live capture with Location OFF and a visible green Wi-Fi glyph)
- `57-tests-pytest.txt`, `58-tests-geolocation-shim.txt`,
  `58b-tests-maps-core.txt`

### 8. Final privacy state

The final policy is OFF. Stale coordinates are cleared, no acquisition lease
remains, GeoClue auto-stops when idle, and `GPS_PWR_EN` is `0`.

### 9. Final post-reboot state

The handset rebooted and returned on Wi-Fi SSH. All core units were active;
`location-policy.json` is `{"enabled": false}`, `GPS_PWR_EN=0`, the bridge
reports `state=disabled` with null coordinates, and the native status bar is
hidden while the session is locked. The final live status-bar binary hash is
`f98f5584c6e057d09925a85734f1a3fea18cc9bd841df647689e988fec8385b4`.
Evidence: `69-final-post-reboot.txt`, `70-final-topbar-unlocked.txt`,
`71-topbar-final-unlocked.png`.
