# FULL-PWNAGE-42000
# NUXEL — REAL GNSS, GEOCLUE, LOCATION PROVIDER & END-TO-END LOCATION REPAIR

## ULTIMATE GPS AND LOCATION IMPLEMENTATION MISSION

**Mission:** PWNAGE-42000  
**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820  
**OS:** Nuxel custom Fedora-based ARM64 Linux  
**SSH connection:** Existing Wi-Fi SSH  
**SSH identity:** `~wicked/.ssh/wicked_wqn_id_rsa`

---

# 0. MISSION OBJECTIVE

Make Nuxel location functionality genuinely operational.

The phone must have a working location architecture that can use real GNSS when supported and can independently use an explicitly identified network-location fallback when satellite GNSS is unavailable.

This is a real hardware and userspace integration mission.

Do not just create another location icon.

Do not just change `No fix` to `GPS ready`.

Do not install stock Linux `gpsd` and assume it understands the S10+ GNSS protocol.

Do not use manual coordinates, geocoding results, cached map pins, IP lookup results, or saved locations as evidence of satellite GPS.

The mission is to fix the entire path:

```text
                  REAL LOCATION SOURCES
                          |
             +------------+------------+
             |                         |
             v                         v
        SATELLITE GNSS            NETWORK LOCATION
        BCM4773 / SSP             GeoClue Wi-Fi / IP
             |                         |
             v                         v
      BBD/LHD FIRMWARE              GeoClue2
      + USERSPACE                       |
             |                         |
             v                         v
       GNSS PROVIDER              NETWORK PROVIDER
             |                         |
             +------------+------------+
                          |
                          v
                 NUXEL LOCATION BRIDGE
                          |
                          v
               PERMISSION / POLICY GATE
                          |
             +------------+------------+
             |                         |
             v                         v
       QUICK SETTINGS             SETTINGS / MAPS
             |                         |
             v                         v
        STATUS ICON             LIVE POSITION MARKER
```

Both source paths must remain distinguishable.

A network-derived position must never be labelled as a satellite GPS fix.

---

# 1. CRITICAL FINDINGS FROM THE UPLOADED REPOSITORY

Use these findings as investigation starting points. Verify all of them on the current handset and checkout before changing anything.

## 1.1 The S10+ BCM4773 hardware path is partially alive

The repository records the following live findings in:

`docs/s10plus-live-fixes-20261028.md`

- `/dev/ttyBCM` exists.
- The driver `brcm gps spi` is bound to `spi17.0`.
- The GPS power control is:

  `/sys/devices/virtual/sec/gps/GPS_PWR_EN/value`

- This maps to GPIO 145.
- Writing `1` makes the hardware respond on SPI.
- The observed SPI register changes from `0xFFFFFFFF` to actual values such as `0x40104094`.

This means the hardware path is not simply absent.

However, it does not prove the GNSS receiver is initialized or that a satellite position can be obtained.

The device also has historical SSP diagnostics:

- `ssp_down == true`.
- `ssp_send_cmd failed -1`.
- `[SSP] GPS: false`.
- No functioning sensor-hub firmware/userspace stack.

Reconcile these observations rather than treating them as mutually exclusive.

Distinguish:

1. The presence of the SPI driver.
2. Power-rail functionality.
3. Hardware register responsiveness.
4. A working GNSS firmware/command path.
5. A usable userspace location provider.
6. An actual fresh satellite fix.

Do not report the receiver ready just because stage 2 or 3 succeeds.

## 1.2 The BCM4773 protocol is not NMEA

The important hardware detail:

**The BCM4773 uses Broadcom BBD/LHD RPC, not a simple serial NMEA stream.**

The repository explicitly reports:

`/dev/ttyBCM` does not emit NMEA by itself.

This means the current implementation must not treat `/dev/ttyBCM` as an ordinary NMEA receiver.

The stock Linux `gpsd` cannot directly decode the raw Broadcom RPC protocol.

The required userspace protocol layer is missing.

## 1.3 The Android vendor gpsd is not a drop-in Linux binary

The repository identifies the vendor binary at:

`beyond2lte/proprietary/vendor/bin/hw/gpsd`

It is an Android/Bionic executable.

The documented requirements include:

- Android Bionic runtime.
- `/system/bin/linker64`.
- Android HIDL services.
- Android sensor services.
- The associated vendor runtime environment.

Nuxel currently uses a Fedora Linux userspace rather than a booted Android system partition.

The Android linker and its required services are not present in the normal Nuxel environment.

Do not copy the binary to `/usr/bin/gpsd` and assume it will work.

Do not create fake linker symlinks.

Do not bundle a large and incomplete Android framework runtime merely to make one vendor daemon launch.

Investigate whether there is a proven compatible native userspace implementation or a safely isolated vendor runtime that can genuinely provide the required hardware interface.

## 1.4 GNSS firmware is missing from the recorded vendor blob set

The reports for v0.7.0-beta and v0.7.2-beta explicitly state:

- No usable BCM4773 GNSS firmware/reader in the vendor blob set.
- GNSS remains `BLOCKED_FIRMWARE`.
- No genuine coordinates may be claimed.

The generic firmware inventory in:

`configs/nuxel/gnss/gnss.json`

includes names such as:

- `gnss.bin`
- `gnss_firmware.bin`
- `gps.bin`
- `bcm4773.bin`
- `bcm47752.bin`

However, generic filenames are not proof that these are the actual required Broadcom firmware files.

Identify the true firmware filenames, format, loading mechanism, compatibility and dependency chain from the actual S10+ vendor implementation.

Do not rename an unrelated binary to `gnss.bin`.

Do not copy a BCM4775x file from a different device without proving hardware compatibility.

Do not use another Exynos model's firmware because its chip family looks similar.

## 1.5 The current GnssProvider implementation is not a valid BBD/LHD provider

Inspect:

`services/nuxel-bridge/src/hw_providers.py`

Current class:

`GnssProvider`

It currently:

- Writes to `GPS_PWR_EN`.
- Opens `/dev/ttyBCM`.
- Reads it as raw text.
- Searches for NMEA-like `$G...` sentence identifiers.
- Returns `stream=empty` if none are found.
- Turns the power rail OFF after the read.

This is not a valid implementation of the BCM4773 BBD/LHD protocol.

### Specific implementation defects

#### `power_rail()`

It currently returns:

`success: true`

after a successful write even if the subsequent readback is missing or does not equal the requested state.

Fix this so success requires a verified readback.

Return explicit:

- requested state.
- actual state.
- write result.
- readback result.
- error reason.

A successful sysfs write is not enough.

#### `sample_nmea()`

It currently assumes that `/dev/ttyBCM` carries NMEA.

This contradicts the repository's hardware evidence.

Replace it with either:

- A real, compatible BCM4773 BBD/LHD reader/provider, or
- A truthful unsupported-protocol status.

Do not continue advertising an empty NMEA read as a complete GNSS acquisition attempt.

It also currently turns the power rail OFF after sampling without preserving the previous state or coordinating with concurrent acquisition requests.

Redesign this lifecycle.

#### `timeout`

The `timeout` parameter is accepted by the method and passed through from `api.py`, but the current implementation uses the `seconds` loop and does not enforce the supplied timeout as a complete operation deadline.

Implement a real bounded deadline for the full operation.

## 1.6 The current diagnostic assumes NMEA

Inspect:

`tools/s10plus/a33/nuxel-gnss-diag.sh`

and:

`configs/nuxel/gnss/gnss.json`

The configuration describes:

- Generic GNSS nodes.
- Generic firmware candidates.
- A stream with `baud: 9600`.
- `NMEA-0183`.
- `$GPGGA`, `$GNGGA`, `$GPRMC`, `$GNRMC`.

That is an inappropriate assumption for the S10+ BCM4773 BBD/LHD interface.

The current diagnostic checks whether `/dev/ttyBCM` is readable and can then use it as the candidate stream.

A readable character device is not a data stream.

A data stream is not necessarily NMEA.

NMEA sentences are not necessarily a valid fix.

**Update the diagnostic to understand the real S10+ protocol and report the first genuine failing stage.**

Preserve generic GNSS support for other devices only where it is explicitly applicable.

## 1.7 GeoClue network location is configured but unresponsive

Inspect:

- `services/nuxel-bridge/src/bridge.py`
- `services/nuxel-s10/geoclue/geoclue.conf`
- `configs/s10plus/geoclue/geoclue.conf`
- `services/nuxel-s10/dbus/99-geoclue-nuxel.conf`
- `configs/nuxel/gnss/99-geoclue-nuxel.conf`
- `services/nuxel-bridge/systemd/nuxel-bridge.service`

The S10+ GeoClue configuration explicitly enables:

```ini
[ip]
enable=true
method=ichnaea

[wifi]
enable=true
submit-data=false
```

It disables:

- Network NMEA.
- 3G.
- CDMA.
- Modem GPS.
- Compass.
- Static source.

This is an intended Wi-Fi/IP network-location fallback.

It is not a satellite GPS provider.

The repository's October 27 live test found:

- First GeoClue request failed with `AccessDenied`.
- The bridge D-Bus policy was narrowed and corrected.
- The error changed to `NoReply`.
- `Manager.GetClient` still returned `NoReply` in a root test with a 12-second timeout.
- The bridge therefore reported `provider_ready=false`.
- No network-derived coordinate was obtained.

The first D-Bus policy issue was not the only failure.

Do not simply add more broad D-Bus allow rules and assume the provider works.

## 1.8 The bridge has a deliberate device-isolation boundary

Inspect:

`services/nuxel-bridge/systemd/nuxel-bridge.service`

It runs:

- As `nuxel-bridge`.
- With `PrivateDevices=true`.
- With a restricted capability set.

The bridge cannot directly access `/dev/ttyBCM` or root-only SSP devices.

The HTTP bridge is a different service and runs as root with `PrivateDevices=no`.

Do not solve GNSS by removing `PrivateDevices=true` from the primary bridge or running the entire bridge as root.

If raw hardware access is needed, implement a narrowly scoped privileged provider service/helper with a small authenticated API.

Only expose the minimum required operations and results.

## 1.9 The current API authorization is too broad for physical GPS power control

Inspect:

`services/nuxel-bridge/src/api.py`

The `gnss` hardware-provider action currently checks:

`location:read`

before allowing both:

- `gnss-power`
- GNSS sampling.

Powering a physical GNSS rail is a hardware-management operation.

Preserve the distinction:

- `location:read` — request or consume an authorized location result.
- `location:manage` — change global location policy or control the provider's hardware lifecycle where explicitly exposed.

Do not let a read-only capability become unrestricted hardware power control.

The provider may acquire power automatically for an authorized `location:read` request, but the actual power lifecycle must remain governed by the central privacy policy and active request leases.

## 1.10 The location privacy policy is already designed

Inspect:

`docs/a73/LOCATION-PRIVACY-STATUS.md`

The intended semantics are:

- Location global policy defaults OFF.
- The policy persists in:

  `/var/lib/nuxel/permissions/location-policy.json`

- `enabled` and `permission_enabled` represent global policy.
- `provider_ready` represents provider availability.
- `location_fix_available` represents an actual fix.
- `fix_source`, `fix_timestamp`, and `accuracy` describe the real result.
- GNSS hardware presence is reported independently.
- OFF blocks new location reads.
- Stale location is invalidated when OFF.
- GeoClue auto-stops when idle.

Preserve this model.

Do not make Location default ON just because GNSS is being implemented.

Do not leave GPS powered continuously in the background.

---

# 2. PHASE ZERO — AUDIT THE LIVE DEVICE AND REPOSITORY

## 2.1 Connect safely

Use existing Wi-Fi SSH:

`~wicked/.ssh/wicked_wqn_id_rsa`

Use the actual existing phone address and account.

Do not guess the phone IP.

Do not expose the private key.

Do not disable host-key checking.

Preserve the current SSH connection and the device's recovery path.

## 2.2 Preserve pre-existing work

Record:

- `git status --short`.
- Current branch.
- Current commit.
- Existing uncommitted changes.
- Relevant file hashes.
- Deployed source hashes.
- Active services.
- Recent system journal entries.

Do not discard unrelated user changes.

## 2.3 Create the TODO and evidence directory

Create:

`docs/beta-finalization/live/PWNAGE-42000-TODO.md`

Create:

`docs/beta-finalization/live/evidence/pwnage-42000/`

The TODO must list:

- Source path.
- Live deployed path.
- Finding.
- Root cause.
- Planned repair.
- Test.
- Result.
- Status: TODO / IN PROGRESS / BLOCKED / VERIFIED.

## 2.4 Initial hardware inventory

Capture:

- Device identity.
- Kernel version.
- OS version.
- `/dev/ttyBCM`.
- `/dev/gnss*`.
- `/dev/ssp*`.
- Relevant sysfs sensor-hub entries.
- SPI device `spi17.0`.
- Actual bound driver.
- GPS power GPIO mapping.
- Actual power-rail state.
- SSP state.
- Kernel GNSS/SSP messages.
- Relevant firmware files.
- Current GeoClue package/version.
- GeoClue service/socket/D-Bus activation state.
- Active D-Bus owner for `org.freedesktop.GeoClue2`.
- Bridge service identity and sandbox.
- Location policy.
- Location capability grants.

Do not read or dump unrelated private user data.

Do not dump precise coordinates or location history into general logs.

---

# 3. TRACK A — BRING UP REAL SATELLITE GNSS

This is the primary hardware objective.

## 3.1 Reproduce the hardware findings

Inspect the live device and verify:

- `/dev/ttyBCM` exists.
- Its actual owner/group/mode.
- The SPI driver binding.
- `GPS_PWR_EN` existence and readback.
- The GPIO-to-hardware relationship.
- Actual SSP state.
- Actual kernel probe messages.

The archive records that toggling the power rail allows real SPI registers to respond.

Repeat only a safe, bounded read-only validation.

Do not continuously power-cycle the receiver.

Do not alter other SSP devices.

Do not write arbitrary SPI register values.

Do not use undocumented commands.

## 3.2 Understand the actual Broadcom protocol

The BCM4773 interface is documented as Broadcom BBD/LHD RPC.

Identify the actual protocol boundary.

Investigate:

- Available source code.
- Matching S10+ vendor userspace.
- `gpsd` and `lhd` roles.
- BBD transport.
- Shared sensor-hub services.
- Firmware loading.
- Required messages and state initialization.
- Required permissions.
- Whether location data is delivered over a separate interface rather than `/dev/ttyBCM`.

Do not infer protocol details from generic NMEA GPS documentation.

Do not invent command bytes or SPI transactions.

Do not copy protocol implementations from unrelated Broadcom or Qualcomm devices without evidence of compatibility.

If protocol implementation must be created, require a real trace/specification or a verified compatible reference implementation.

## 3.3 Locate and verify required firmware

Search the repository, its firmware manifest, local development workspace and safely accessible existing device files for:

- S10+ BCM4773/BCM47752 GNSS firmware.
- Sensor-hub firmware.
- BBD/LHD runtime components.
- Matching vendor HAL libraries.
- Matching userspace daemon dependencies.

The repository currently reports the GNSS firmware/reader missing from the vendor blob set.

Investigate whether the exact required assets exist in an owner-supplied or otherwise authorized stock S10+ firmware image.

If a local authorized image is available:

1. Identify the exact image and device variant.
2. Extract read-only.
3. Identify the firmware component and its loader expectations.
4. Check hashes.
5. Verify compatibility with SM-G975F / beyond2lte.
6. Identify runtime dependencies.
7. Document provenance.
8. Do not modify the source image or flash any partition.

Do not download random firmware blobs from unrelated repositories.

Do not use firmware from the G973/G975/G977 variants without verifying exact compatibility.

Do not substitute the ABOX Calliope audio firmware for GNSS firmware.

Do not confuse modem firmware with sensor-hub/GNSS firmware.

If no compatible firmware is available, report the exact missing artifact and required source.

Do not rename a random blob to satisfy the diagnostic.

## 3.4 Investigate the vendor Android runtime boundary

The repository identifies the vendor daemon:

`beyond2lte/proprietary/vendor/bin/hw/gpsd`

The documented binary is Android/Bionic and requires:

- `/system/bin/linker64`.
- Android HIDL/sensor services.
- The matching vendor runtime.

Do not assume it can run directly under Fedora.

Evaluate these options in order:

### Option A — Native compatible provider

Best option:

Build or integrate a Linux-native BBD/LHD implementation if a known compatible source/reference protocol is available.

Requirements:

- Actual target compatibility.
- Proper transport handling.
- Bounded RPC.
- Correct firmware initialization.
- Structured location output.
- Clean lifecycle.
- Error reporting.
- No invented fix.

### Option B — Safely isolated vendor compatibility runtime

Only if a verified S10+ vendor runtime is available:

Evaluate whether a minimally scoped compatible runtime can host the exact required vendor components.

It must not require replacing Nuxel with Android.

It must not replace the normal Fedora init system.

It must not destabilize the rest of the phone.

It must not create an uncontrolled compatibility environment with broad system privileges.

### Option C — Explicit hardware blocker

If neither approach is technically viable with the available source/firmware:

- Stop before unsafe implementation.
- Record the exact blocker.
- Provide the required proprietary inputs.
- Identify the missing initialization protocol.
- Identify the Android service dependencies.
- Provide a technically grounded next-step plan.

Do not claim GPS works merely because the vendor `gpsd` process launches.

A process that starts but cannot obtain a real location is not a working provider.

## 3.5 Do not confuse SSP and GNSS state

The repository contains historical SSP evidence:

- `ssp_down == true`.
- `ssp_send_cmd failed -1`.
- `raw_data=0,0,0`.
- `[SSP] GPS: false`.

It also contains later evidence of a live GPIO-powered BCM4773 SPI response.

These observations are not proof of a working GNSS position path.

Investigate whether the GPS receiver can be operated independently of the broken general sensor-hub services or whether the vendor stack requires those services.

Do not repair unrelated accelerometer/gyro orientation functionality as a side effect.

Do not replace or reflash the kernel to repair SSP.

If kernel/firmware support is genuinely required, mark the dependency explicitly for separate authorization.

---

# 4. GNSS POWER MANAGEMENT — ON DEMAND ONLY

The current code can turn the GPS rail on and back off, but does not have a robust ownership model.

Do not make GPS permanently enabled at boot.

The archive explicitly notes that the rail was not persisted because leaving it powered without a consumer risks unnecessary battery drain.

## 4.1 Correct provider lifecycle

Implement a proper lifecycle:

```text
LOCATION POLICY OFF
        |
        v
NO GNSS POWER / NO ACQUISITION
        |
        v
AUTHORIZED LOCATION REQUEST
        |
        v
ACQUIRE GNSS POWER LEASE
        |
        v
POWER RAIL ON + VERIFIED READBACK
        |
        v
FIRMWARE / PROVIDER INITIALIZATION
        |
        v
SEARCHING FOR SATELLITES
        |
        v
REAL FIX OR HONEST NO_FIX
        |
        v
ACTIVE CLIENTS FINISH / RELEASE
        |
        v
STOP GNSS CONSUMER
        |
        v
POWER RAIL OFF IF NO OTHER OWNER
```

The exact behavior must respect the actual hardware and firmware.

## 4.2 Power-rail verification

Update `GnssProvider.power_rail()`.

Requirements:

- Check write result.
- Read back state.
- Compare actual with requested.
- Return failure when readback is unavailable.
- Return failure if the value does not match.
- Record the exact error.
- Do not report `success=true` without verified state.

## 4.3 Concurrent users and state restoration

If multiple location requests overlap:

- Do not let one request power the hardware OFF while another request is still active.
- Use an appropriate reference-count/lease model.
- Enforce maximum acquisition duration.
- Cancel safely.
- Release leases after client disconnect or timeout.
- Preserve the initial rail state where appropriate.
- Do not shut down a receiver owned by another validated subsystem.

Do not use arbitrary sleeps to coordinate users.

Use explicit ownership and deadlines.

## 4.4 Authorization

Power-control operations must not be authorized solely by a read-only location capability.

Use:

- `location:read` for location requests.
- `location:manage` for direct location policy/provider management.

An app's authorized location request may acquire the provider on its behalf through the central system service, subject to the global policy.

An arbitrary `location:read` caller must not be able to freely toggle physical hardware.

---

# 5. TRACK B — FIX GE OCLUE AND NETWORK-BASED LOCATION

This is a separate and useful deliverable even if satellite GNSS remains blocked.

A working network location provider provides approximate coordinates without claiming satellite GPS.

## 5.1 Verify actual GeoClue installation and activation

Inspect:

- GeoClue version.
- D-Bus service file.
- `geoclue.service`.
- Socket or D-Bus activation.
- Service executable.
- System user.
- Runtime directories.
- Service dependencies.
- Journal.
- D-Bus name ownership.
- Object-path availability.
- Manager introspection.

Use the actual deployed unit and service file.

The repository has a `GeoClueConnector` in:

`services/nuxel-bridge/src/bridge.py`

It checks for:

`/usr/share/dbus-1/system-services/org.freedesktop.GeoClue2.service`

That only proves the service file exists. It does not prove that GeoClue is running or responding.

The connector executes `Manager.GetClient`.

That call was documented to return `NoReply` even from root with a 12-second timeout.

Find the actual reason.

Do not blame only the two-second bridge timeout.

## 5.2 D-Bus diagnostics

Inspect:

- D-Bus daemon policy.
- D-Bus service activation.
- Actual GeoClue daemon user.
- Name ownership.
- Message sender/destination rules.
- Manager object.
- Method replies.
- GeoClue logs.
- Service process state.
- Stale systemd or D-Bus activation jobs.

Relevant files:

- `services/nuxel-s10/dbus/99-geoclue-nuxel.conf`
- `configs/nuxel/gnss/99-geoclue-nuxel.conf`
- `services/nuxel-bridge/src/bridge.py`
- `configs/s10plus/geoclue/geoclue.conf`
- `services/nuxel-s10/geoclue/geoclue.conf`

The prior bridge policy change removed an `AccessDenied` failure, but the observed result became `NoReply`.

Do not repeatedly widen bus permissions.

Do not allow every process to bypass GeoClue.

Do not allow arbitrary applications to impersonate authorized clients.

Use the minimal correct rules for the specific service and client.

## 5.3 GeoClue client identity and policy

The connector currently identifies itself as:

`org.nuxel.Bridge`

It calls:

- `SetDesktopId`.
- `SetRequestedAccuracyLevel`.
- `Start`.
- `GetLocation`.

Verify that the supplied desktop ID is appropriate and accepted by the running GeoClue version.

Review the client/application authorization configuration.

The GeoClue agent whitelist and client/application policy are not interchangeable.

Preserve per-app capability enforcement in Nuxel.

If a system-level bridge is allowed as a trusted GeoClue client, make this a narrow and documented grant.

Do not simply authorize every browser and PWA globally to get around the missing agent.

## 5.4 GeoClue network backend

The S10+ configuration already intends to use Wi-Fi/IP location:

```ini
[ip]
enable=true
method=ichnaea

[wifi]
enable=true
submit-data=false
```

Keep the privacy setting:

`submit-data=false`

Test the actual provider behavior.

Determine:

- Whether the source uses Wi-Fi access point observations.
- Whether it can obtain enough network information.
- Whether network access works under the GeoClue daemon identity.
- Whether DNS/TLS requests succeed.
- Whether the configured BeaconDB/Ichnaea endpoint is valid and reachable.
- Whether the service returns coordinates.
- Whether the accuracy is realistic for network positioning.

Do not change to a service requiring a private API key that the user has not supplied.

Do not embed API keys.

Do not silently transmit Wi-Fi observations or location data to a different service.

Document the network geolocation provider and privacy behavior.

## 5.5 Do not confuse network and GNSS results

The GeoClue `source` must not simply be presented as `GPS`.

Network location must be distinguishable from satellite positioning.

When the source is known to be network/Wi-Fi/IP, expose it as:

- `network`
- `wifi`
- `ip`

or an equivalent explicit source enum.

When GeoClue cannot identify a precise method, use:

`geoclue_unknown`

rather than fabricating `gnss`.

Use a sensible low-confidence/coarse accuracy display.

Never invent an accuracy of 5 m or 20 m.

Use the actual provider-reported accuracy if valid.

---

# 6. REPAIR THE LOCATION CONNECTOR AND PROVIDER STATE MACHINE

Inspect:

`services/nuxel-bridge/src/bridge.py`

Current class:

`GeoClueConnector`

It already has:

- A two-second D-Bus timeout.
- A 20-second retry interval.
- Bounded calls.
- Connection state.
- Acquisition state.
- Last error.

Preserve bounded behavior.

Do not reintroduce unbounded D-Bus calls.

## 6.1 Provider readiness

Current documentation reports that GeoClue can auto-stop while idle.

This may be normal.

A stopped provider must not be permanently treated as broken if a valid acquisition can start it.

However:

`provider_ready=false`

must accurately describe that it is not currently usable.

When acquisition is requested:

1. Validate global Location policy.
2. Validate caller capability.
3. Connect to GeoClue.
4. Verify the actual Manager response.
5. Create/initialize the client.
6. Start the client.
7. Wait for actual provider data.
8. Return fresh provider information.
9. Stop or release when no clients need it.

Use bounded operations and proper client lifecycle management.

Do not restart GeoClue on every poll.

Do not cause a 20-second stale retry cache to conceal newly repaired provider behavior.

Allow controlled force-retry after a meaningful service restart or an explicit user request.

## 6.2 Separate acquisition from reading

A request to obtain location is not a fix.

The state machine must differentiate:

- Provider unavailable.
- Disabled by privacy policy.
- Permission denied.
- Starting.
- Acquiring.
- Searching.
- No fix.
- Network approximate result.
- GNSS fix.
- Stale result.
- Provider error.

Use the existing naming convention if appropriate.

A location request may succeed as a command while still having no fix.

Do not represent this as a successful position.

## 6.3 Source-aware location result

A valid position response should include:

- Latitude.
- Longitude.
- Accuracy.
- Provider timestamp.
- Source.
- Freshness.
- Whether source is GNSS or network.
- Available provider detail.
- Whether the fix has been independently validated.

Reject:

- Missing coordinates.
- NaN coordinates.
- Infinity.
- Latitude outside -90..90.
- Longitude outside -180..180.
- Negative accuracy.
- Invalid timestamps.
- Stale timestamps presented as fresh.
- Synthetic data on physical hardware.
- A location from an untrusted source.

Never substitute the bridge poll time for a missing provider timestamp.

---

# 7. REPAIR THE G N S S DIAGNOSTIC TOOLING

Inspect:

`tools/s10plus/a33/nuxel-gnss-diag.sh`

and:

`configs/nuxel/gnss/gnss.json`

The current diagnostic is useful because it reports stage-by-stage evidence, but its S10+ protocol assumptions need fixing.

## 7.1 Separate hardware detection from usable receiver readiness

Keep stages such as:

1. Hardware device detected.
2. Driver bound.
3. Power rail accessible.
4. Hardware responds.
5. Required firmware present.
6. Required firmware initialized.
7. Correct protocol userspace present.
8. Protocol communication successful.
9. Location messages decoded.
10. Valid current fix obtained.

A readable device node must not count as a usable stream.

An SPI register response must not count as firmware ready.

A valid protocol response must not count as a satellite fix.

## 7.2 Make diagnostics protocol-aware

For the BCM4773 S10+ route:

- Identify BBD/LHD.
- Do not claim an NMEA stream from `/dev/ttyBCM`.
- Do not use 9600-baud serial assumptions unless the actual hardware interface proves them.
- Do not call generic gpsd as a compatibility shortcut.
- Identify the real required firmware and reader.
- Report missing dependencies explicitly.

For generic GNSS devices that really use NMEA, retain separate NMEA diagnostics.

## 7.3 Correct `stage_firmware()`

The current firmware stage searches generic candidate filenames.

Replace this with device-specific firmware definitions:

- Expected filename.
- Firmware family.
- Hardware compatibility.
- Expected checksum if available.
- Required location.
- Loader.
- Runtime confirmation.

Do not report firmware ready merely because any file with a plausible GPS name exists.

## 7.4 Correct `stage_stream()`

The current function only checks whether a device node is readable.

That is not proof of a stream.

Use separate states:

- Node readable.
- Bytes observed.
- Protocol-valid data observed.
- Position data decoded.
- Position fix valid.

A zero-byte read from `/dev/ttyBCM` must remain no data.

An RPC stream must be parsed by the correct RPC implementation, not grepped for `$G`.

## 7.5 Correct verdicts and fixtures

Add test fixtures for:

- Device absent.
- Driver absent.
- Power rail absent.
- Hardware present but not responding.
- SPI responds but firmware missing.
- Firmware present but not initialized.
- Android vendor runtime missing.
- BBD/LHD userspace missing.
- BBD/LHD service running but no response.
- GeoClue D-Bus unavailable.
- GeoClue network source working.
- Network location with no GNSS.
- Valid NMEA receiver, if applicable.
- Valid BBD/LHD GNSS fix.
- Stale position.
- Invalid coordinates.
- Synthetic/VM-only location.

Never promote a fixture's mock coordinate into a physical-device PASS.

---

# 8. REPAIR THE GEOLOCATION SHIM

Inspect:

`pwa/nuxel-common/geolocation.js`

This file is important because it affects every PWA using browser geolocation.

## 8.1 Prevent false Null Island coordinates

The current code contains logic equivalent to:

```javascript
latitude: Number(c.latitude) || 0,
longitude: Number(c.longitude) || 0,
```

Missing or invalid coordinates can therefore turn into:

`0, 0`

That is not a legitimate fix.

Require:

- Actual numeric latitude.
- Actual numeric longitude.
- Finite numeric values.
- Latitude range -90 to +90.
- Longitude range -180 to +180.

Reject invalid results.

Never convert missing fields into valid-looking coordinates.

## 8.2 Do not fabricate timestamps

The current shim can substitute:

`Date.now()`

when a provider timestamp is missing.

That creates the appearance of a fresh position even when the provider did not provide a timestamp.

Do not do this.

Require a valid provider timestamp or explicitly classify the result as lacking freshness evidence.

A missing timestamp must not become a fresh GPS fix.

## 8.3 Correct accuracy handling

The current accuracy expression can produce `NaN` when the provider omits the value.

Validate:

- Finite numeric accuracy.
- Non-negative value.
- Proper unit: metres.
- No arbitrary fabricated default.

If accuracy is unknown, use `null` or an explicit unknown status.

## 8.4 Correct W3C PositionOptions mapping

The current shim uses:

`options.accuracy`

This does not correspond to the standard W3C `enableHighAccuracy` option.

Map:

- `enableHighAccuracy`
- `timeout`
- `maximumAge`

correctly.

Preserve Nuxel's source/synthetic metadata.

Return standard error codes and meaningful error messages.

## 8.5 Fix watchPosition

The current implementation stores callbacks but makes only one request.

A valid watch must continue updating while active.

Prefer provider notifications/subscriptions if available.

Otherwise implement a bounded polling mechanism only while at least one watch is active.

Requirements:

- Multiple watches work independently.
- Each ID can be cleared.
- No timer remains after `clearWatch`.
- No location request happens after all watches are cleared.
- No hidden always-on background tracking.
- Respect global privacy OFF immediately.
- Respect each caller's capability.
- Report changes only when appropriate.
- Avoid polling faster than the provider can update.

The provider's timestamp must remain the source of location freshness.

Polling time is not a new location timestamp.

## 8.6 Shared consistency

The bridge, geolocation shim, Maps and Settings must agree about:

- Position.
- Timestamp.
- Accuracy.
- Source.
- Freshness.
- Permission.
- Error.

Do not allow the shim to turn an unavailable provider into an apparent success.

---

# 9. LOCATION PERMISSIONS AND PRIVACY

Preserve:

`docs/a73/LOCATION-PRIVACY-STATUS.md`

and the policy:

`/var/lib/nuxel/permissions/location-policy.json`

## 9.1 Global location policy

Default must remain OFF.

Do not automatically enable location at boot just because GPS is being implemented.

When OFF:

- New location acquisition is denied.
- Existing stale location is not shown as current.
- Active GNSS leases are released according to policy.
- No background GNSS acquisition remains active.
- UI correctly shows Location OFF.

When ON:

- Only authorized clients receive location.
- Hardware is acquired only when needed.
- Actual provider state is reflected.
- No fix is claimed unless a real one exists.

## 9.2 Capabilities

Preserve distinct capabilities:

- `location:read`
- `location:manage`

A PWA with no `location:read` grant must not receive coordinates.

A PWA with `location:read` must not receive permission to freely modify hardware or global policy.

Do not bypass the permission portal with blanket application grants.

Do not silently add every PWA to GeoClue's allowed-app list.

Preserve the explicit first-party grants already introduced.

## 9.3 Privacy of logs and storage

Do not log exact coordinates in normal system logs.

Do not persist a continuous location history unless explicitly requested by the user.

Do not transmit precise location to a network provider without an authorized user request.

Keep GeoClue `submit-data=false`.

Do not expose Wi-Fi AP identifiers or cell IDs in application logs.

Provide a privacy explanation for network-location requests.

---

# 10. LOCATION QUICK SETTINGS AND TOP-BAR INDICATOR

Inspect:

- `pwa/nuxel-home/js/qs.js`
- `services/nuxel-bridge/src/bridge.py`
- `pwa/nuxel-apps/settings/location-maps.js`
- The actual top-bar/status indicator implementation.

The Location tile is a global privacy/provider policy switch.

It is not a guarantee of a satellite fix.

## 10.1 Location Quick Setting

Display distinct states:

- Location OFF.
- Permission denied.
- Provider unavailable.
- Starting.
- Searching/acquiring.
- No fix.
- Network location available.
- Real GNSS fix available.
- Stale last-known location.
- Error.

The tile should not report `GPS fixed` simply because the global location policy is ON.

When the user toggles Location:

1. Require the proper `location:manage` authorization.
2. Update the persistent global policy.
3. Read it back.
4. Start/release providers as appropriate.
5. Refresh provider state.
6. Update the UI from authoritative state.

Do not optimistically claim the hardware has been enabled.

## 10.2 Top-bar GPS/location icon

Use the existing Nuxel location asset where suitable:

`./assets/nuxel-quicksettings-icon-pack/09-location.png`

The indicator must communicate real state.

Suggested semantics:

- Neutral/off: location privacy policy OFF.
- Neutral/unavailable: no usable provider.
- Searching/acquiring: location request active without a fix.
- Active/fixed: a current real location is available.
- Optional source marker or tooltip to distinguish GNSS from network-derived location.

Do not use the same visual state for a GPS satellite fix and a coarse IP-derived position.

Do not keep displaying the active indicator using a stale coordinate.

If space is limited, keep the top bar compact and use a tooltip or status detail for provider/source.

## 10.3 Settings → Location & Maps

Preserve the existing Location & Maps tab and improve it where necessary.

It should show:

- Global policy enabled/disabled.
- Permission state.
- GNSS hardware state.
- GNSS driver state.
- GPS power state.
- Firmware readiness.
- GNSS protocol/provider readiness.
- GeoClue state.
- Network provider state.
- Real-fix availability.
- Source.
- Accuracy.
- Last-fix timestamp/age.
- Current blocker.
- Last meaningful error.

The panel must not freeze while GeoClue or GNSS is unresponsive.

Use bounded requests.

---

# 11. MAPS AND OTHER PWA INTEGRATION

The repository's PWNAGE-27000 report already establishes that the Maps tile pipeline and IndexedDB tile cache work at the software/network level.

Do not rewrite the OSM tile system unnecessarily.

Keep this task focused on live location.

## 11.1 Maps

Inspect:

`pwa/nuxel-apps/maps/js/maps.js`

Ensure:

- Current location comes from the canonical Nuxel provider.
- A GNSS marker is displayed only from a fresh real GNSS fix.
- Network-derived location is visibly labelled approximate/network.
- Stale location is clearly distinguished.
- No location is claimed from a manual coordinate.
- Search results remain transient.
- Saved pins do not become current location.
- No fallback coordinate is hardcoded.

If the provider is unavailable, Maps must remain usable with manual coordinates and saved pins.

## 11.2 Weather and other PWAs

Inspect applications using:

`navigator.geolocation`

Ensure they use the shared Nuxel shim.

Do not add native WebKit geolocation permissions as a bypass.

Preserve the bridge capability model.

A PWA must not receive a location fix just because another PWA has permission.

## 11.3 Camera geotagging

The location service may later support camera geotagging.

Do not add automatic continuous geotagging in this mission.

If the camera consumes location:

- Require its own permission.
- Capture only the fix current at the time the photo is taken.
- Preserve the source and timestamp.
- Do not use an old location as though it were the camera's actual position.
- Do not add location metadata when no valid fix exists.

---

# 12. SYSTEMD, BRIDGE AND PRIVILEGED SERVICE ARCHITECTURE

Keep the main bridge security boundary.

Do not remove:

`PrivateDevices=true`

from:

`services/nuxel-bridge/systemd/nuxel-bridge.service`

If GNSS hardware requires elevated access, use a dedicated, narrow hardware provider.

Possible design:

```text
UNPRIVILEGED NUXEL BRIDGE
          |
          | authorized request
          v
LOCATION PROVIDER API
          |
          v
PRIVILEGED GNSS SERVICE
          |
          | limited device access
          v
BCM4773 / SSP / GPS POWER RAIL
```

The privileged service should:

- Run only when required.
- Have minimal filesystem access.
- Have explicitly scoped device access.
- Accept only defined operations.
- Validate input.
- Authenticate its caller.
- Enforce acquisition deadlines.
- Enforce global privacy OFF.
- Keep hardware access out of untrusted PWAs.
- Avoid exposing raw arbitrary sysfs writes.
- Avoid exposing arbitrary serial/character-device access.
- Release resources reliably.

Do not run the whole bridge as root.

Do not change broad systemd sandboxing without demonstrating why it is needed.

---

# 13. BATTERY AND SUSPEND BEHAVIOUR

GPS must not become another overnight battery drain.

Requirements:

- No GNSS power-on at boot without an active location requirement.
- No permanent GPS polling.
- No continuous acquisition after location policy is OFF.
- No timer running after the last watch has been cleared.
- No unbounded retries when firmware is absent.
- No continuous GeoClue reconnect loop.
- Stop acquiring when no authorized client needs location.
- Preserve fresh fix briefly if policy permits, without representing it as live.

Inspect suspend/resume behavior.

When the phone sleeps:

- Release or suspend acquisition according to active-client policy.
- Do not strand GPS power in an unowned state.
- Resume cleanly.
- Do not invent a new fix from an old coordinate.

Measure idle power behavior before and after.

---

# 14. AUTOMATED TESTING

Update and extend the existing tests.

Relevant files include:

- `tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py`
- `tests/a72/test_location_provider.py`
- `tests/a72/test_maps_location_integration.py`
- `services/nuxel-bridge/test-bluetooth-location.py` only if shared provider logic is affected.
- `pwa/nuxel-common/geolocation.js` tests or a new dedicated test suite.
- Bridge permission tests.
- GeoClue connector tests.

## 14.1 GNSS negative tests

Test:

- Device node absent.
- Driver absent.
- GPIO missing.
- GPIO write failure.
- GPIO readback failure.
- Hardware does not respond.
- Firmware absent.
- Firmware incompatible.
- Firmware present but not initialized.
- BBD/LHD runtime missing.
- Vendor binary architecture mismatch.
- Missing Android linker.
- Missing HIDL dependency.
- BBD/LHD timeout.
- Malformed protocol data.
- No location fix.
- Stale fix.
- Invalid coordinates.

## 14.2 GeoClue tests

Test:

- GeoClue service absent.
- D-Bus name unavailable.
- Service activation works.
- Manager.GetClient succeeds.
- Manager.GetClient times out.
- Client Start fails.
- Client Start succeeds but no fix.
- IP location succeeds.
- Wi-Fi location succeeds.
- Offline network.
- Invalid provider result.
- Location policy OFF.
- Capability denied.
- GeoClue stops when idle and successfully restarts for an authorized request.

## 14.3 Geolocation shim tests

Test:

- Valid coordinates.
- Latitude/longitude missing.
- Coordinates NaN.
- Coordinates infinite.
- Out-of-range latitude.
- Out-of-range longitude.
- Missing timestamp.
- Invalid timestamp.
- Invalid accuracy.
- Network source labeling.
- GNSS source labeling.
- Synthetic VM result.
- Permission denied.
- Provider unavailable.
- Stale location.
- One active watch.
- Multiple active watches.
- `clearWatch`.
- Global OFF during an active watch.
- No timer or polling after all watches are cleared.

## 14.4 Privacy tests

Test:

- Default global policy OFF.
- Location OFF denies new reads.
- Location ON allows only authorized requests.
- `location:read` cannot freely control GPS rail.
- `location:manage` authorizes appropriate management.
- Revocation stops acquisition.
- No location coordinates are emitted to unrelated logs.
- No static or synthetic position leaks into hardware results.

---

# 15. PHYSICAL DEVICE ACCEPTANCE TESTS

A real GNSS fix requires an outdoor owner test.

Do not claim hardware PASS from automated fixtures.

## 15.1 Outdoor GNSS test

Once a valid BBD/LHD provider is implemented:

1. Ensure Location policy is ON.
2. Ensure permission is granted to the test surface.
3. Go outdoors with a clear sky view.
4. Keep the device stationary in a suitable position.
5. Start a bounded cold-start acquisition.
6. Record the actual receiver/provider state.
7. Wait up to 300 seconds for a cold start.
8. If a fix appears, capture the actual coordinates, timestamp and accuracy.
9. Confirm the source is satellite GNSS rather than Wi-Fi/IP.
10. Cross-check the location against the existing Maps view.
11. Record time to first fix.
12. Repeat as a warm-start test after a valid fix.

Acceptance should require:

- A real provider-generated location.
- Valid latitude and longitude.
- A provider timestamp.
- Valid reported accuracy.
- A genuine GNSS source.
- A confirmed physical outdoor fix.
- Reasonable agreement with the map.

Use the existing 50 m target from `configs/nuxel/gnss/gnss.json` as the project's initial acceptance threshold when the receiver supplies a comparable accuracy estimate.

Do not apply an NMEA GGA fix-quality threshold to BBD/LHD without a verified protocol mapping.

Do not claim a fix from an indoor test.

## 15.2 Network-location test

Independently verify GeoClue Wi-Fi/IP location.

Requirements:

- Location policy ON.
- Authorized test client.
- Working network.
- GeoClue Manager/GetClient responds.
- Acquisition starts.
- A genuine provider coordinate is returned.
- Source is explicitly network/IP/Wi-Fi.
- Accuracy is plausible and provider-reported.

If network location is not available, report the exact failure separately from GNSS.

---

# 16. DEPLOYMENT AND SAFETY

Before deploying:

1. Record the current branch and git status.
2. Back up affected files.
3. Preserve pre-existing working changes.
4. Run the focused automated tests.
5. Validate Python and JavaScript syntax.
6. Validate systemd units and D-Bus policy.
7. Check bridge service permissions.
8. Deploy only required userspace components.
9. Verify installed hashes.
10. Restart only the affected services.
11. Preserve the Wi-Fi SSH connection.
12. Provide rollback instructions.

Do not:

- Flash the kernel.
- Flash a boot image.
- Modify the bootloader.
- Write to modem, EFS or firmware partitions.
- Repartition storage.
- Install random vendor binaries.
- Copy blobs from another handset without validating compatibility.
- Make GNSS power permanent.
- Disable `PrivateDevices` on the main bridge.
- Bypass the location privacy model.

If a kernel-level or proprietary vendor component is unavoidable, mark it as a separate blocked dependency and document exactly what is needed.

---

# 17. ACCEPTANCE MATRIX

Use PASS / FAIL / BLOCKED / NOT TESTED.

| ID | Requirement | Required evidence |
|---|---|---|
| HW-01 | BCM4773 device | Actual node/driver evidence |
| HW-02 | GPS power rail | GPIO write/readback |
| HW-03 | SPI response | Real hardware response |
| HW-04 | Firmware | Exact compatible firmware verified |
| HW-05 | BBD/LHD userspace | Compatible provider operating |
| HW-06 | Protocol exchange | Valid protocol communication |
| HW-07 | Real GNSS fix | Outdoor, source-confirmed result |
| GEO-01 | GeoClue D-Bus | GetClient success |
| GEO-02 | GeoClue client | Start/GetLocation functional |
| GEO-03 | Network fallback | Real Wi-Fi/IP-derived coordinate |
| GEO-04 | Source labeling | Network never shown as GPS |
| GEO-05 | Provider idle lifecycle | Stops when no active client |
| BRIDGE-01 | Provider readiness | Authoritative readback |
| BRIDGE-02 | Hardware isolation | Main bridge retains PrivateDevices |
| BRIDGE-03 | Capability enforcement | Separate read/manage permissions |
| API-01 | Coordinate validation | Invalid data rejected |
| API-02 | Timestamp correctness | Provider timestamp preserved |
| API-03 | Accuracy correctness | Valid metric or explicitly unknown |
| API-04 | Source metadata | GNSS/network/synthetic distinct |
| PWA-01 | Geolocation current position | Genuine result or real error |
| PWA-02 | watchPosition | Repeated updates while active |
| PWA-03 | clearWatch | Stops future updates |
| PWA-04 | Invalid coordinate protection | No fabricated 0,0 |
| UI-01 | Location tile | Actual global policy state |
| UI-02 | GPS indicator | Actual provider/fix status |
| UI-03 | Settings Location panel | Real provider detail/blocker |
| MAP-01 | GNSS marker | Only from fresh GNSS fix |
| MAP-02 | Network marker | Clearly identified as approximate |
| PRIV-01 | Default OFF | Confirmed |
| PRIV-02 | Revocation | Stops acquisition |
| POWER-01 | GPS resource lifecycle | No permanent idle power |
| POWER-02 | Suspend/resume | No stuck acquisition |
| FINAL-01 | Evidence | Complete report and test matrix |

---

# 18. EVIDENCE AND DOCUMENTATION

Create:

`docs/beta-finalization/live/PWNAGE-42000-TODO.md`

Create:

`docs/beta-finalization/live/PWNAGE-42000-REPORT.md`

Store evidence in:

`docs/beta-finalization/live/evidence/pwnage-42000/`

Include:

- Initial system inventory.
- Actual hardware/driver evidence.
- GPIO readbacks.
- SPI response evidence.
- SSP state.
- Firmware inventory and hashes.
- Vendor binary dependency analysis.
- GeoClue D-Bus traces.
- GeoClue service logs.
- Network-location tests.
- GNSS protocol/provider logs.
- Location API tests.
- Privacy tests.
- Geolocation shim tests.
- UI verification.
- Physical outdoor test evidence.
- Time to first fix.
- Source and accuracy.
- Power measurements.
- Remaining blockers.
- Rollback.

Do not include unrequested persistent location history.

Redact precise coordinates from ordinary logs; place owner-approved outdoor test evidence in a dedicated restricted evidence file.

---

# 19. FINAL REPORT FORMAT

## 1. Actual S10+ GNSS hardware state

Explain the driver, node, power rail, SSP condition and hardware response.

## 2. Actual GNSS blocker

State whether the remaining blocker is firmware, BBD/LHD protocol, Android vendor userspace, kernel/SSP, or another layer.

Name the exact missing components.

## 3. Real satellite GNSS status

Report whether a physical outdoor fix was obtained.

Include source, timestamp, accuracy and time to first fix.

## 4. GeoClue

Explain the original `NoReply` cause, the actual fix and the network provider result.

## 5. Location architecture

Explain bridge, security, permissions, provider lifecycle and source semantics.

## 6. App/API

Report the geolocation shim, validation and watchPosition repairs.

## 7. UI

Report Location Quick Setting, GPS indicator, Settings and Maps integration.

## 8. Battery and privacy

Report hardware power lifecycle, default OFF, revocation and idle consumption.

## 9. Files changed

List source, configuration, deployed services and hashes.

## 10. Remaining blockers

Be precise. Separate genuine hardware blockers from software defects.

## 11. Evidence and rollback

Give exact paths.

---

# FINAL NON-NEGOTIABLE INSTRUCTIONS

1. Do not invent coordinates.
2. Do not mistake `/dev/ttyBCM` readability for an NMEA stream.
3. Do not use stock Linux gpsd as a BBD/LHD decoder.
4. Do not assume the Android vendor gpsd is directly runnable under Fedora.
5. Do not mistake SPI register response for a satellite fix.
6. Do not confuse network location with GNSS.
7. Fix GeoClue's actual `NoReply` rather than merely widening D-Bus permissions.
8. Fix the incorrect GNSS power/readback lifecycle.
9. Preserve the bridge's `PrivateDevices=true` security boundary.
10. Keep global location policy OFF by default.
11. Do not leave GPS powered in the background without an authorized active acquisition.
12. Fix bogus coordinate/timestamp behavior in the geolocation shim.
13. Make `watchPosition()` genuinely continuous and cleanly cancellable.
14. Reuse the existing Maps implementation.
15. Physically verify the real GNSS fix outdoors.
16. If proprietary firmware or a vendor runtime is genuinely missing, document the exact dependency instead of faking completion.

**The goal is a working location system, with genuine satellite GPS wherever the hardware stack can support it, a real network-location fallback, and absolutely no fake fixes.**

# PWNAGE-42000 — GIVE THE PENGUIN A REAL POSITION. 🐧📍
