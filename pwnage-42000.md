# PWNAGE-42000 — NUXEL GPS & LOCATION ULTIMATE FIXER
## Real Satellite GNSS + Working Network Location + Honest Location UI

The full prompt is located at ./full-pwnage-42000.md, use it.

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**OS:** Nuxel Fedora-based ARM64  
**Connection:** Existing Wi-Fi SSH  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`

## THE ACTUAL PROBLEMS FOUND IN THE REPOSITORY

This is not simply a missing GPS toggle.

The repository exposes several concrete blockers:

### 1. BCM4773 hardware is partially responding, but no usable GNSS provider exists.

Evidence from `docs/s10plus-live-fixes-20261028.md`:

- `/dev/ttyBCM` exists.
- `brcm gps spi` is bound to `spi17.0`.
- GPS power is controlled by GPIO 145 through `GPS_PWR_EN`.
- Enabling the rail makes the chip respond on SPI.
- `/dev/ttyBCM` does not output NMEA.
- The BCM4773 uses Broadcom BBD/LHD RPC.

The Android vendor `gpsd` requires Android Bionic, `/system/bin/linker64`, and Android HIDL/sensor services. Standard Linux `gpsd` cannot decode the raw Broadcom protocol.

**Do not waste time repeatedly running stock gpsd against `/dev/ttyBCM`.**

### 2. GNSS firmware and userspace are missing

The repository reports `BLOCKED_FIRMWARE` / `no-consumer`.

Find a legitimate, compatible firmware and userspace solution using the actual S10+ hardware. Do not invent firmware, substitute another device's blobs, or blindly run an Android binary in Fedora.

### 3. GeoClue network location is also failing

GeoClue is configured to support Wi-Fi/IP location:

- `[ip] enable=true`
- `method=ichnaea`
- `[wifi] enable=true`
- `submit-data=false`

However, the recorded `org.freedesktop.GeoClue2.Manager.GetClient` call returned `NoReply`, including a root test with a 12-second timeout. The earlier bridge D-Bus `AccessDenied` issue was addressed, but this did not fix GeoClue itself.

**Make network-based location work independently of satellite GNSS. Label it as approximate network location, never GPS.**

### 4. The existing GNSS provider makes incorrect assumptions

Inspect `services/nuxel-bridge/src/hw_providers.py`.

`GnssProvider.sample_nmea()` turns the GPS rail on, reads `/dev/ttyBCM` as if it were NMEA, and turns the rail off again. That is incompatible with the documented BBD/LHD protocol.

`power_rail()` also reports success even if the requested state cannot be verified.

### 5. The geolocation frontend contains correctness problems

Inspect `pwa/nuxel-common/geolocation.js`.

- Missing coordinates can be converted into `0,0`.
- Missing timestamps can be replaced with the current time.
- `watchPosition()` currently performs one request rather than a continuing watch.

Fix these instead of allowing bogus location results.

## REQUIRED EXECUTION ORDER

1. Create a TODO and evidence directory.
2. Audit the live S10+ device and current repository.
3. Fix GeoClue's D-Bus/service activation and obtain a genuine Wi-Fi/IP location where possible.
4. Diagnose the real BCM4773 firmware, SSP and BBD/LHD requirements.
5. Find a safe and compatible route to a real satellite GNSS provider.
6. Repair bridge privileges, GNSS acquisition lifecycle, and location API semantics.
7. Fix the geolocation shim and Quick Settings/Settings reporting.
8. Verify Maps receives genuine provider coordinates.
9. Perform physical outdoor GNSS testing.
10. Document any genuine external firmware/kernel limitation without faking success.

## NON-NEGOTIABLE RULES

- No fabricated coordinates.
- No fake satellite counts or accuracy.
- Network/IP location must never be labelled GPS.
- Preserve the privacy-safe default of Location OFF.
- Keep GNSS power on only while an authorized acquisition or active client requires it.
- Do not create a permanent GPS-power-on service that drains the battery.
- Do not let `nuxel-bridge` bypass `PrivateDevices=true`.
- Use a narrowly scoped privileged GNSS helper if physical device access is needed.
- Require `location:manage` for hardware-power changes and preserve `location:read` for position requests.
- Preserve existing Maps tiles, Wi-Fi SSH, user data and recovery.
- No kernel, boot image, modem, EFS, firmware-partition or bootloader flashing.

## DEFINITION OF DONE

- GeoClue responds correctly through the real bridge.
- A real network-location result can be obtained when the fallback is enabled and available.
- BCM4773 GNSS is correctly diagnosed and its compatible userspace protocol path is implemented where possible.
- A real outdoor satellite fix is obtained and verified before claiming GPS works.
- The Location Quick Setting controls the actual global privacy policy.
- The top-bar GPS/location indicator shows accurate state.
- The location API never returns fake `0,0` or fabricated fresh timestamps.
- `watchPosition()` genuinely watches and stops when cleared.
- Maps displays a live marker only from a real, fresh location result.
- Battery-safe acquisition and release work.
- All unresolved hardware blockers are documented honestly.

**Make location genuinely work. Do not confuse a location icon, an IP-derived estimate, a device node, or an SPI response with a real satellite fix.** 🐧
