# PWNAGE 27000 — GPS, Location Provider and Maps Repair

**Device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**Kernel:** Linux 4.14.253 #15 SMP PREEMPT (aarch64)  
**Userspace:** Fedora Linux 43  
**Date:** 2026-10-27  
**Scope:** userspace only. No kernel, boot image, partition, modem, EFS or
firmware was written.

## 1. Phase Zero audit

- `git status --short` showed the expected pre-existing working-tree changes
  from earlier tasks; no other PWNAGE agent or deployment process was active.
- Serial `/dev/ttyACM0` was free. The serial lock was taken only for bounded
  deploy/verification commands; no second writer existed.
- The phone was reachable over WLAN SSH (`10.20.30.16`) and serial. Wi-Fi,
  NetworkManager, Wayland/compositor, launcher and the serial Live Console
  remained active across the repair.
- The display was already **off** and the device **locked** before the final
  visual test (`/run/nuxel-wl-fb.state`: `DISPLAY_SLEEP ... display=off
  capture=stopped`; `/run/nuxel-home.state`: `locked=1`). The lockscreen was not
  bypassed or unlocked.

## 2. Root causes, with evidence

| Symptom | Evidence | Root cause | Repair |
|---|---|---|---|
| Location Quick Setting said “No fix” | Old `qs.js` mapped `enabled && !provider_ready` to `Location<br>no fix`; policy file was `{"enabled": false}` | UI collapsed “provider unavailable”, “disabled”, “searching”, “no fix”, “stale” and “fixed” into one label | Explicit state machine in `LocationConnector`; QS renders every state and the real provider detail |
| Location toggle could not be used | `RequestCapability` returned `denied`; no PhoshAgent/systemd user session is installed | Portal consent dialog is unavailable on this handset revision | Explicit first-party grants for Home/Settings/Maps, plus a consent-request fallback in the UI |
| GeoClue is not a working fix provider | First `AccessDenied` from the bridge policy; after fixing that, `GetClient` still returns `NoReply` even for root with a 12 s timeout; bridge `provider_ready=false`, state `unavailable` | Two layers: the bridge D-Bus policy’s broad `receive_sender` deny blocked GeoClue receiving bridge calls, and the GeoClue manager itself still hangs; no GNSS backend is wired | Scoped the deny to signals (provider calls now reach GeoClue), bounded 2 s calls, honest `unavailable` state, no fake coordinate |
| No genuine GNSS fix | `/dev/ttyBCM` exists (0600 root), `spi:BCM4773` bound to `brcm gps spi` on `spi17.0`; `CONFIG_BCM_GPS_SPI_DRIVER=y`; `/lib/firmware` has no GNSS/BCM477x firmware; no `gpsd`/NMEA consumer; 5 s root read of `/dev/ttyBCM` returned 0 bytes; kernel SSP log says `GPS: false` | **BLOCKED_FIRMWARE / BLOCKED_DEPENDENCY**: no BCM4773/sensor-hub firmware and no userspace GNSS reader/provider | Diagnostics now name this exact stage; no kernel or firmware flashing attempted |
| Maps showed “no tile source configured” | Default `state.conf.template=''`, `allowNet=false`; preset only filled the field on a tap | Empty shipped default and an offline-only toggle | Valid default OpenStreetMap template + attribution; visible-viewport-only requests; IndexedDB cache; explicit error states |
| Duplicate Eindhoven/search pins | Every Nominatim result was appended to `state.pins` and persisted; repeated searches appended again | Search results and saved pins shared one persistent list | Search results are transient, replaced per query and de-duplicated; saving a pin is explicit |
| Stale map state / labels | No request sequence; every async search result mutated the live state; labels had no viewport clamp | Asynchronous search and render had no generation token | `beginSearch`/`acceptSearch` sequence tokens; render generation check; label clamping; bounded retries |
| Maps could report a false provider state at startup | `maps.js` is a classic script; `bridge.js` is a deferred ES module | `window.NuxelBridge` was not always published yet | Bounded startup wait/retry in Maps and Settings diagnostics |

## 3. What changed

### Bridge / provider

- `services/nuxel-bridge/src/bridge.py`
  - bounded GeoClue D-Bus calls (`NUXEL_GEOCLUE_TIMEOUT`, default 2 s);
  - real states: `unavailable`, `disabled`, `searching`, `no_fix`, `stale`,
    `fixed`, `error`;
  - provider timestamp is used when present; a repeated poll of the same
    coordinate does not refresh a missing timestamp;
  - freshness policy: fresh ≤ 60 s, stale ≤ 600 s (both configurable);
  - only `fixed`/`stale` states expose coordinates; a disappeared provider
    cannot leave a “current” fix on screen;
  - GNSS inventory reports the BCM GPS SPI binding, firmware absence and the
    bridge's `PrivateDevices` visibility limitation;
  - `fix_kind="provider"` and `gnss_fix=false` make the provider/GNSS
    distinction explicit in the API as well as the UI;
  - `LocationAcquire` added; `GetLocation` refuses stale/no-fix data.
- `services/nuxel-bridge/src/api.py`
  - maps `location.request` → `GetLocation`, `location.acquire` →
    `LocationAcquire`, `location.get-status` → `LocationGetStatus`.
- `pwa/nuxel-common/bridge.js`
  - location verbs never receive a mock success.
- `configs/dbus/org.nuxel.Bridge.conf` and
  `services/nuxel-bridge/dbus/org.nuxel.Bridge.conf`
  - the default `receive_sender="org.nuxel.Bridge"` deny is now scoped to
    signals, so the bridge can call other system services (GeoClue) while its
    own interface/path remains protected. This removed the observed
    `AccessDenied`; the remaining provider failure is GeoClue `NoReply`.

### Quick Setting / Settings

- `pwa/nuxel-home/js/qs.js`
  - distinct labels for every provider state;
  - provider, readiness, last-fix age, accuracy, detail and GNSS blocker in the
    tooltip;
  - bounded 5 s refresh while the panel is open;
  - capability denial is actionable and retryable.
- `pwa/nuxel-apps/settings/index.html`, `settings.js`, `location-maps.js`
  - new **Location & Maps** tab with provider status, real-fix age, accuracy,
    GNSS stage/blocker, tile source, online state, attribution and errors;
  - optional haptics card no longer aborts Settings when its DOM is absent.
- `configs/nuxel/permissions/*.json`
  - explicit first-party grants for the system surfaces; existing network and
    Bluetooth grants are preserved (see the README in that directory).

### Maps

- `pwa/nuxel-apps/maps/js/maps.js`
  - default attributed OpenStreetMap source;
  - only visible tiles are requested, max 4 parallel requests, 9 s timeout,
    retry backoff, in-flight de-duplication;
  - IndexedDB cache first; graceful cache miss/offline/HTTP/network/decode
    states; no blank grid without an explanation;
  - transient, de-duplicated search results with request generations;
  - explicit “Save pin” / “Add pin at selection” using keyboard/map selection,
    never a GPS claim;
  - provider-position marker only from a fresh provider fix; stale is grey and
    labelled “last provider position (stale)”;
  - labels clamped to the viewport; render generation prevents stale tile
    paints.
- `pwa/nuxel-common/maps-core.js` — shared, dependency-free, unit-tested core
  used by Maps and Settings.
- `pwa/nuxel-common/app-registry.json` — Settings declares the same
  location capabilities as its manifest; stale cross-group warning removed.
- `pwa/nuxel-apps/maps/index.html`, `app.json`, `manifest.json`, `css/maps.css`,
  `sw.js` — attribution, status surfaces, cache version and shared core load.
- `configs/nuxel/gnss/gnss.json`, `tools/s10plus/a33/nuxel-gnss-diag.sh` —
  BCM4773/`ttyBCM`/`brcm gps spi` detection, firmware and userspace stages.
- `tools/s10plus/a72/deploy-maps-location-27000.py` and
  `deploy-maps-location-27000-fast.py` — verified deploy/rollback tooling.

## 4. Verification

### Code-level tests (all passed)

```text
node tests/a72/test_maps_core.mjs
  ALL PASS (17 passed)

python3 -m pytest -q tests/a72
  29 passed

python3 -m pytest -q tests/a69
  5 passed

NUXEL_JSDOM=/x/substrate/node_modules python3 tools/s10plus/a33/tests/test-core-apps.py --app maps
  RESULT: PASS=12 FAIL=0 WARN=0 verdict=OFFLINE_RUNTIME_PASSED

python3 tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py
  all checks PASS — OFFLINE_TESTED ...; NEEDS_OWNER_TEST for a real fix

python3 services/nuxel-bridge/test-bluetooth-location.py
  ALL PASS

python3 services/nuxel-bridge/test-grant-store.py
  ALL PASS

node pwa/nuxel-common/test-bridge.js
  [test] ALL TESTS PASSED

node pwa/nuxel-common/verify-wiring.js
  [verify-wiring] ALL 6 PWA SURFACES OK
```

`tools/s10plus/a33/verify-app-registry.py` still reports `verdict=FAILED`
with 4 pre-existing problems (the launcher registry and native copy are
missing several apps, including Maps). This task aligned the Settings entry's
declared capabilities with its manifest and removed one stale warning
(6 → 4 warnings); it did not restructure the global app registry.

The A73 Bluetooth test was made host-independent by forcing the no-adapter
case; an unrelated CI host radio must not decide the phone's expected result.

### Physical-device tests (performed)

- Exact deploy: userspace files installed with per-file SHA-256 readback and
  backups under `/var/lib/nuxel/a72/rollback-fast-*`; evidence in
  `docs/beta-finalization/live/evidence/pwnage-27000-20261027T162501+0100/`
  and `docs/beta-finalization/live/evidence/pwnage-27000-final/final-verification.txt`.
- D-Bus bridge policy installed and `systemctl reload dbus` succeeded; the
  provider error moved from `AccessDenied` to `NoReply`, proving the policy
  repair took effect. GeoClue still does not answer.
- Bridge and HTTP bridge restarted; `NetworkManager`, `nuxel-wayland` and the
  serial console stayed available. `nuxel-console` was already inactive (the
  USB gadget/serial path itself remained reachable).
- Canonical provider readback while the policy is OFF:
  `state=disabled`, `provider_available=true`, `provider_ready=false`,
  `location_fix_available=false`, no coordinates.
- Policy ON via the Home grant then OFF again:
  `success=true`, `enabled=true`, `state=unavailable`,
  `provider_detail="GeoClue2 is installed but unavailable: ...
  org.freedesktop.DBus.Error.NoReply ..."`; then `state=disabled` after
  restoration. No fix was claimed at any point.
- A root `GetClient` call with a 12 s timeout also returned `NoReply`, so the
  remaining GeoClue failure is inside the provider, not a bridge timeout.
- GNSS diagnostic on the device:
  `device_node=node:/dev/ttyBCM`,
  `module=bound:/sys/bus/spi/drivers/brcm gps spi/spi17.0`,
  `firmware=missing`, `userspace=no-consumer`,
  `state=BLOCKED_FIRMWARE`, `fix_verified=false`.
- D-Bus policy: the broad bridge `receive_sender` deny was scoped to signals
  and `systemctl reload dbus` succeeded; the provider error changed from
  `AccessDenied` to `NoReply`, proving the policy repair took effect.
- Real tile network from the phone (root, because the PWA/WebKit runs as root):
  `tile_http=200 size=25501`, `nominatim_http=200` for the configured HTTPS
  endpoints.
- Maps’ actual WebKit IndexedDB cache contains four valid **256×256 PNG** tile
  blobs written when Maps launched:
  `7/65/42`, `7/66/43`, `7/65/43`, `7/66/42`.
  Two are byte-identical to the current OSM tiles; the other two differ only by
  a later OSM tile revision (same 256×256 PNG format). Evidence:
  `docs/beta-finalization/live/evidence/pwnage-27000-photos/maps-idb/`.
  This is direct proof the app’s tile source, renderer request path and cache
  work on the phone; it is **not** proof of a visual screenshot.
- Visual screenshot: **NOT VERIFIED**. The display was already off and the
  device locked (`display=off capture=stopped`, `locked=1`); two captures were
  byte-identical and showed the lockscreen/home wallpaper. The lockscreen was
  deliberately not unlocked.
- Genuine outdoor GNSS fix: **NOT OBTAINED / BLOCKED**. `fix_verified=false`.

## 5. Remaining hardware/dependency blockers

1. **BCM4773/sensor-hub GNSS firmware is absent** from `/lib/firmware` (no
   `/lib/firmware/gnss`, no `bcm477*`/GPS blob). This is a safe follow-up for an
   owner-supplied firmware image; no flashing was attempted.
2. **No userspace GNSS reader/provider** (`gpsd`, `gpspipe`, NMEA socket) is
   installed, and `/dev/ttyBCM` is root-only. The bridge runs with
   `PrivateDevices=true`, so it intentionally cannot read the node.
3. **GeoClue2’s `Manager.GetClient` still returns `NoReply`**, even from root
   with a 12 s timeout, after the bridge D-Bus policy was corrected. GeoClue is
   therefore reported as `unavailable`; it is never reported as “no fix” or as
   a fix. The provider needs vendor GNSS backend work and a GeoClue debugging
   follow-up.
4. The display/lockscreen state prevented a visual Maps screenshot. The real
   tile cache and root HTTPS requests above are the evidence available without
   unlocking the owner’s device.
5. The `nuxel` SSH user has no network egress (socket creation is denied);
   WebKit/root and the PWA host do have working DNS/TLS. Do not infer from an
   SSH `curl` failure that the phone has no internet.

## 6. Rollback

Each deploy created a timestamped backup directory and a
`/var/lib/nuxel/a72/ROLLBACK-27000-<stamp>.txt`. To roll back:

```sh
systemctl stop nuxel-bridge nuxel-http-bridge
# restore files listed in the ROLLBACK file from
#   /var/lib/nuxel/a72/rollback-fast-<stamp>/
# or remove newly-created grant files
systemctl start nuxel-bridge nuxel-http-bridge
```

No kernel, boot, partition, modem, EFS or firmware path is part of the rollback.

## 7. Operator procedure

1. Open **Settings → Location & Maps**; confirm provider state and the GNSS
   blocker. A fix is never shown unless a real provider timestamp/coordinate
   exists.
2. Open **Maps**; confirm the badge is `OpenStreetMap tiles` (not
   `no tile source configured`) and the attribution link is visible.
3. Pan/zoom and confirm new visible tiles appear; turn off online downloads and
   confirm cached tiles still render with an honest cache-only message.
4. Search a place once; confirm results are transient, not saved pins; repeated
   identical searches do not create duplicate pins. Use **Show** to centre and
   **Save pin** only when wanted.
5. Tap the Location Quick Setting. OFF → “Location off”; ON →
   “Location unavailable” on this device (GeoClue/BCM firmware blocker), never
   “fix”.
6. When firmware/userspace GNSS support is supplied, repeat the outdoor
   `nuxel-gnss-diag.sh monitor 180` test and require a real
   `$GNGGA`/`$GPGGA` fix before promoting Maps’ live marker.

## 8. Status table

| Component | Code implemented | Automated tests | Physical-device test | Remaining issue |
|---|---|---|---|---|
| GNSS detection/provider | Yes | 29 passed + GNSS suite | `ttyBCM`/SPI detected, no NMEA, firmware missing | BCM4773 firmware + userspace provider; GeoClue unresponsive |
| Location Quick Setting | Yes | JS/static tests | Policy ON/OFF confirmed; states honest | No fix until provider works |
| Maps tile source | Yes | 17 core + 29 integration | 4 real 256×256 OSM tiles cached from WebKit | Visual screenshot blocked by locked/off display |
| Map rendering/zoom | Yes | jsdom L1–L4 | Tile requests/cache proven; visual not captured | Pending owner visual check after unlock |
| Search/geocoding | Yes | 17 core | Nominatim HTTP 200 from phone root | None observed |
| Pins/current-location marker | Yes | 17 core | No fake marker; provider unavailable | Pending real fix |
| Attribution/cache/offline behavior | Yes | 17 core + jsdom | IndexedDB cache populated; errors classified | None observed |
