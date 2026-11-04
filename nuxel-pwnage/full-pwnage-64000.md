# FULL-PWNAGE-64000 — Nuxel S10+ GNSS / GPS Completion Mission

**Mission class:** hardware bring-up, Linux GNSS integration, firmware provenance, protocol implementation, location-stack integration, and physical-device validation  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Nuxel Fedora-based ARM64 userspace  
**Current repository baseline:** Nuxel v0.7.5-beta archive supplied for this mission  
**Primary outcome:** obtain a genuine, fresh, independently verifiable satellite GNSS position through Nuxel's native Linux location stack, without pretending that hardware detection, BBD bytes, SPI responses, or network geolocation are a satellite fix.

---

## 0. Mission directive — read this before editing anything

You are continuing an existing, substantial Nuxel GPS implementation. **Do not restart from generic Linux GPS instructions. Do not install `gpsd` and point it at `/dev/ttyBCM`. Do not parse `/dev/ttyBCM` as NMEA. Do not treat the presence of `/dev/bbd_patch` as proof that firmware is installed. Do not enable the GPS rail merely because the hardware exists.** These shortcuts have already been investigated and are incorrect for this phone's currently identified GNSS transport.

The S10+ uses a Broadcom BCM4773 GNSS subsystem integrated into the Exynos 9820 platform. The observed Linux-facing path is a Broadcom BBD/LHD packet/RPC stack, not a conventional NMEA UART. The current Nuxel source explicitly documents this distinction. `/dev/ttyBCM` is the BBD packet transport; `/dev/bbd_patch` is a character-device firmware loader; `/dev/bbd_control`, `/dev/bbd_sensor`, and `/dev/bbd_urgent_patch` are related interfaces. The current source has correctly avoided inventing an NMEA stream or coordinate.

The project is already well beyond generic node discovery. Physical-device evidence recorded:

- `/dev/ttyBCM`
- `/dev/bbd_patch`
- `/dev/bbd_control`
- `/dev/bbd_sensor`
- `/dev/bbd_urgent_patch`
- SPI device `spi17.0` bound to `brcm gps spi`
- GPS power rail `GPS_PWR_EN` exposed at `/sys/devices/virtual/sec/gps/GPS_PWR_EN/value`, corresponding to GPIO145 in the current device work
- the rail was toggled during controlled diagnostic investigation and the SPI register path returned a non-`0xFFFFFFFF` response when powered, showing that the hardware path can respond

But **Nuxel has not yet acquired a genuine satellite fix**. Previous device evidence showed `GPS: false` in SSP debug output when sampled, and the GPS rail was returned to OFF after testing. Network-based location through GeoClue works separately. Do not conflate it with GPS.

The current key blocker is the compatible BCM4773 BBD/LHD sensor-hub patch firmware and a compatible userspace consumer/protocol implementation. The current GNSS config references the patch filename `bcm_sensorhub_a1.patch`, including a vendor hint that it may be located at `/system/bin/bcm_sensorhub_a1.patch`. The Fedora root filesystem does not currently contain that verified device-specific patch. The repository also does not contain a native BBD/LHD RPC decoder. The stock Samsung vendor `lhd`/`gpsd` path is Android/Bionic/HIDL-dependent and is not a drop-in Linux `gpsd` executable.

Your task is to **implement the complete repository-side solution that can be implemented safely, establish exactly what can be established about the missing device-specific components, and get as close as possible to a real on-device fix.** If the exact firmware or protocol artefact is genuinely absent and cannot be lawfully/properly obtained from the supplied material, report that as a precise external prerequisite. Do not fabricate a substitute, silently substitute a different BCM firmware, or mark the mission PASS.

### Non-negotiable Nuxel architecture

Nuxel is a native Linux phone OS. Preserve its stated architecture: no Android framework dependency, no AOSP runtime, no APK execution, no Waydroid, no Halium, and no libhybris as a shortcut. Native Fedora/Linux services and APIs are preferred. A narrowly isolated compatibility experiment using authentic S10+ vendor components may be investigated as a last-resort feasibility branch, but it must be disabled by default, must not become a shipped runtime dependency, must not modify the normal boot/userspace architecture, must not be enabled without explicit owner approval, and must be documented as a deviation requiring a separate decision. **Do not silently compromise the zero-Android-dependency architecture to claim GPS support.**

### Required working style

- Work from the repository itself. Inspect existing implementation before changing it.
- Make code changes, not merely a research report.
- Preserve working network location, privacy controls, Maps, offline tiles, and other S10+ functionality.
- Never claim a hardware feature is working based solely on a config flag or unit-test mock.
- Use bounded operations, explicit timeouts, careful ownership, and least privilege.
- Do not flash bootloader, modem, EFS, radio/NV, or kernel partitions. Do not modify EFS/NV calibration. Do not use undocumented firmware-flashing procedures.
- Do not leave GPS power on after a diagnostic or test. The default state remains OFF.
- Do not collect or print precise coordinates in normal logs. Use a restricted, owner-requested evidence file for an actual outdoor test.
- If an action requires a physical-device owner decision, implement the safe offline work first and clearly mark only that action as requiring approval. Do not halt the entire repository task for a question that can be resolved by inspection.

---

## 1. Repository baseline and known facts

Read these files first and use them as the source of truth for the current implementation:

1. `configs/nuxel/gnss/gnss.json`
2. `services/nuxel-bridge/src/hw_providers.py` — `GnssProvider`
3. `services/nuxel-bridge/src/bridge.py` — `_gnss_hardware()`, location result handling, `_remember_fix()`
4. `services/nuxel-bridge/systemd/nuxel-bridge.service`
5. `tools/s10plus/a33/nuxel-gnss-diag.sh`
6. `services/nuxel-s10/bin/nuxel-gps-status`
7. `services/nuxel-s10/udev/90-nuxel-s10.rules`
8. `services/nuxel-s10/geoclue/geoclue.conf`
9. `pwa/nuxel-common/geolocation.js`
10. Maps, Settings, Quick Settings, Camera, and location-permission consumers that use the common geolocation API
11. `docs/a73/LOCATION-PRIVACY-STATUS.md`
12. `docs/beta-finalization/live/PWNAGE-42000-REPORT.md`
13. `full-pwnage-42000.md` and earlier GNSS mission/report material, especially the corrected BBD/LHD findings
14. `tests/pwnage42000/test_gnss_provider.py` and all GNSS diagnostic test scripts
15. Rootfs and device package manifests for the actual `beyond2lte` target

Search for every occurrence of `ttyBCM`, `bbd_patch`, `GPS_PWR_EN`, `bcm_sensorhub`, `bcm4773`, `lhd.conf`, `vendor.samsung.hardware.gnss`, `location_fix_available`, `fix_source`, and `nuxel-gnss-provider`. Build a dependency map before editing.

### Existing configuration facts

`configs/nuxel/gnss/gnss.json` already identifies:

- device: `Samsung Galaxy S10+ SM-G975F`
- codename: `beyond2lte`
- SoC: Exynos 9820
- protocol: `broadcom-bbd-lhd-rpc`
- transport node: `/dev/ttyBCM`
- patch loader: `/dev/bbd_patch`
- control node: `/dev/bbd_control`
- sensor node: `/dev/bbd_sensor`
- vendor hint: `PortName=tcp:127.0.0.1:300; LheName=bbd; LhePatch=/dev/bbd_patch`
- `nmea_over_ttybcm: false`
- `stock_gpsd_can_decode: false`
- `android_vendor_runtime_required: true` in the current vendor-stack model
- expected firmware candidate: `/system/bin/bcm_sensorhub_a1.patch` (also candidate names under firmware directories)
- vendor runtime candidates: `lhd`, `gpsd`, Android `linker64`, `lhd.conf`, `gps.xml`, and Samsung GNSS HIDL implementation library

The config uses ordered stages:

`device_node -> module -> firmware -> vendor_runtime -> userspace -> stream -> fix`

Keep these stages explicit. Improve their truthfulness and observability; do not collapse them into a vague `gps_available` boolean.

### Existing provider behaviour

`GnssProvider` in `hw_providers.py` is intentionally conservative. It has:

- a GPS power-rail helper
- policy checks
- lease/refcount handling for power ownership
- bounded BBD byte observation
- device/runtime inventory
- explicit refusal to parse BBD as NMEA
- explicit refusal to provide a coordinate or fix

It currently cannot produce a fix. Its docstring says so. Preserve this truthful behaviour until there is a validated provider.

### Existing bridge behaviour

`_gnss_hardware()` is a read-only inventory function. It detects device nodes and SPI driver binding, looks for firmware candidates, checks the vendor runtime file paths, and deliberately returns `fix_supported: false` until a compatible provider exists.

Audit and fix inconsistencies:

- The bridge inventory currently searches `/lib/firmware/gnss`, `/lib/firmware`, and `/vendor/firmware`, but omits the `/system/bin/bcm_sensorhub_a1.patch` candidate referenced in `gnss.json`.
- Firmware detection currently uses broad filename heuristics (`gps`, `gnss`, `sensorhub`, `ssp`, `bcm477`), which can produce false positives from unrelated files.
- The provider and bridge use partly different candidate lists and different definitions of “complete”.
- A firmware file being present is not equivalent to firmware being compatible, loaded, or accepted by the receiver.
- The bridge runs with `PrivateDevices=true`; a device node hidden from the bridge process is not necessarily absent from the host. Do not disable systemd hardening just to make the bridge see devices.

Create one canonical, typed inventory schema and consume it in the provider, diagnostic script, bridge and Settings status presentation. Do not maintain four subtly different firmware/device lists.

### Existing GeoClue and UI behaviour

`services/nuxel-s10/geoclue/geoclue.conf` currently enables `[ip]` and `[wifi]`, with Wi-Fi data submission disabled. Other GNSS-like GeoClue plugins are disabled. The existing network location path is useful and must keep working.

`pwa/nuxel-common/geolocation.js` and app consumers already distinguish source, accuracy, timestamp, stale/fresh state, and GNSS/network information. Keep the source semantics correct. `network_wifi` or `network_ip` must never be presented as `gps`, `gnss`, `satellite`, or “GPS fix”. Keep the existing location policy default OFF.

### Existing systemd security boundary

`nuxel-bridge.service` is deliberately unprivileged/hardened, including `PrivateDevices=true`. The bridge is not the correct place to give broad raw GNSS device access. Add a distinct narrowly scoped GNSS device service if a real provider is implemented. Do not make the whole bridge root and do not turn off `PrivateDevices`, `ProtectSystem`, `NoNewPrivileges`, or other hardening to get around a device-access issue.

### Existing test baseline

The focused provider suite at `tests/pwnage42000/test_gnss_provider.py` has previously passed 9 tests. Re-run it against the current tree and record the actual result.

The GNSS diagnostic self-test has previously hung or exceeded a bounded test run (the shell selftest exceeded a 20-second external limit and a related Python integration run exceeded a 120-second command limit). Investigate this, make all test subprocesses bounded, fix any hang, and do not report the diagnostic suite as passed until it completes normally.

---

## 2. Phase 0 — safety, branch and baseline capture

Before making changes:

1. Record `git status --short --branch`, current branch, HEAD hash, and uncommitted changes. Do not overwrite the owner's work.
2. Record repository version, target image profile, target architecture, kernel version metadata, device codename and build manifest.
3. Identify whether the current environment is the physical S10+, a build host, a container, or a test fixture. Never mistake host `/dev` or host kernel results for phone evidence.
4. Save current GNSS configuration, udev rules, systemd units and relevant package manifests in the patch history so rollback is straightforward.
5. Run focused baseline tests and capture them.
6. Do not run an unbounded GNSS monitor. All commands which wait for bytes, firmware, device state, GeoClue, or a fix must have a hard timeout and a cleanup/finally path.
7. Do not enable persistent GPS power during build-host tests.
8. Do not perform raw reads from BBD nodes simply to “see what comes out”. Use the existing bounded diagnostic code or a carefully scoped, read-only test that is known not to consume protocol messages required by the provider.
9. Do not access `/dev/bbd_patch` or write firmware bytes until the exact loader ABI and expected patch have been established from source or verified implementation.

Produce a baseline table with:

- kernel/build and phone identity
- SPI binding state
- driver/module state
- device-node existence and permissions
- GPS rail state and readback
- exact firmware artefacts found and their SHA-256 hashes
- firmware provenance and target compatibility (or `unknown`)
- runtime component files found
- systemd provider state
- location policy state
- GeoClue provider state
- network location source state
- GNSS diagnostics verdict
- test outcomes

Mask or omit personal coordinates and Wi-Fi identifiers from general logs.

---

## 3. Phase 1 — determine exact firmware and vendor artefact requirements

This is the most important forensic phase. Avoid guessing from a filename.

### 3.1 Build an exact beyond2lte artefact inventory

Inspect the exact S10+ vendor/device references already identified in the repo and upstream source manifests. Public reference inventories show that Samsung's beyond2lte vendor package has included items such as:

- `/vendor/bin/hw/lhd`
- `/vendor/bin/hw/gpsd`
- `vendor.samsung.hardware.gnss@2.0-service`
- `vendor.samsung.hardware.gnss@2.0-impl` / GNSS implementation libraries
- `/vendor/etc/sensor/lhd.conf`
- `/vendor/etc/gnss/gps.xml`
- `libwrappergps` and GPS configuration/certificate material in some vendor manifests
- init/service configuration files

These manifests are **reference inventories**, not permission to download arbitrary vendor blobs or proof that a particular binary/patch revision is compatible with the user's currently installed S10+ firmware. Cross-check all artefacts against the exact device's stock firmware build and kernel branch.

References to consult carefully:

- Evolution-X beyond2lte vendor makefile: `https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk`
- beyond2lte proprietary file inventory: `https://github.com/whatawurst/android_device_samsung_beyond2lte/blob/lineage-17.1/proprietary-files-vendor.txt`

Use these to understand filenames and dependency relationships, not as a reason to bundle blobs from an arbitrary branch. Do not infer that the currently referenced `bcm_sensorhub_a1.patch` is guaranteed to be the right revision for every SM-G975F device firmware.

### 3.2 Create a canonical firmware manifest

Extend or replace the current GNSS config with a machine-readable manifest whose records include:

- logical component name
- exact expected path(s)
- expected filename
- target device/codename
- SoC and subsystem/chip family
- firmware/vendor build or revision where known
- SHA-256 (only when the exact known artefact is available and verified)
- size (only when measured from the actual artefact)
- provenance/source and extraction method
- license/redistribution note
- whether it is required, optional or diagnostic-only
- whether it is a file, character-device loader, executable, shared object, configuration, or service unit
- status: absent / present_unverified / identity_verified / ABI_verified / accepted_by_device

Treat `/dev/bbd_patch` as a **character device loader**, never as a firmware file. Do not list it as the firmware artefact. The firmware is the payload that a compatible loader/daemon submits to that node.

The current broad filename matching must be removed or heavily constrained. A random `gps.bin`, unrelated modem blob, `bcm47752` image, `bcm47755` patch, or another phone's sensor-hub image must not satisfy the BCM4773 requirement. Only an exact component with credible provenance and explicit compatibility may progress to `identity_verified`.

### 3.3 Search the actual target safely

On the physical device, read-only search only the relevant mounted firmware/vendor/system locations. Include the paths the config claims, including `/system/bin`, as well as current rootfs firmware directories. Record symlinks and mount origins. Do not recursively dump unrelated user data or EFS/NV.

If the expected patch is not already on the device, provide an owner-controlled extraction procedure that uses a stock firmware package the owner already possesses or a read-only extraction from the same device's mounted vendor/system image. Do not download or redistribute copyrighted proprietary firmware. Do not modify boot, vendor, modem, EFS or radio partitions. Do not run an opaque “one click firmware extractor” with broad write permissions.

An extraction helper, if added, must:

- accept an owner-provided firmware archive or mounted image as input
- verify the model/build metadata and partition identity before extraction
- extract only explicitly listed GNSS files
- never flash or write to device partitions
- output to a staging directory, not straight into `/lib/firmware`
- hash every extracted file
- write a provenance manifest
- reject unknown model, build, partition or path combinations
- clearly state that an extracted blob is not automatically compatible

### 3.4 Inspect binary compatibility before execution

For any vendor binary that might be used in a strictly isolated experiment, inspect it statically first:

- architecture / ELF class / endianness
- interpreter path, e.g. Android `linker64`
- `DT_NEEDED` libraries
- symbol versions
- required HIDL interfaces/services
- sensor-hub service dependencies
- config file references
- device nodes and expected permissions
- init property/service expectations
- 32-bit vs 64-bit ABI
- firmware path and patch loader expectations

Use `file`, `readelf -h -l -d`, `objdump -p` or equivalent read-only analysis. Do not execute an unknown binary on the phone just to see whether it starts. Do not create misleading symlinks from Android runtime paths into Fedora system paths.

### 3.5 Stop condition for missing proprietary material

If the only viable implementation is dependent on an absent proprietary firmware patch or proprietary executable that cannot be supplied/verified, do not make a fake decoder and do not mark the mission as fixed. Continue all repository-side work: schema, diagnostics, service design, unit tests, native protocol research, safe preflight, correct UI status, fallback behaviour, docs and build integration. End with an exact user-action blocker that names the missing artefact(s), the exact expected source/path, what metadata is required, and why it cannot safely be substituted.

---

## 4. Phase 2 — native BBD/LHD protocol implementation feasibility

The preferred result is a native Linux provider that does not require Android/Bionic. Do not assume the BBD protocol is NMEA or that a generic `gpsd` can decode it.

### 4.1 Establish protocol facts before implementing

Search the current kernel driver source, headers, ioctl definitions, device-tree nodes, vendor configs and any legally available protocol documentation/reference code. Determine:

- framing and packet boundaries
- message identifiers and directionality
- length fields and maximum payload size
- endianness and alignment
- checksum/CRC or integrity field
- request/response correlation and transaction identifiers
- sequence counters
- timeouts/retry rules
- transport read/write semantics
- whether `/dev/ttyBCM` is stream-like, packet-like, or ioctl-mediated
- whether `lhd` speaks to a local TCP endpoint as the `lhd.conf` hint suggests, and which process owns that endpoint
- which process loads the patch and in what order
- how sensor-hub readiness is signalled
- how raw receiver/navigation data reaches GNSS HAL or gpsd
- which part actually produces a position fix

Do not infer framing from a handful of bytes or a packet hexdump. Do not treat a string match within binary BBD data as NMEA. Do not publish raw packet dumps in normal logs; they may contain sensitive identifiers or location-related data.

### 4.2 Evaluate possible native paths

Evaluate, with evidence, the following options in order:

**Option A — native BBD/LHD-compatible provider (preferred).**

If the protocol is documented or can be implemented using lawful, verifiable source information, create a small standalone native Linux provider. It should have a clear protocol module, transport module, firmware-loader module, and provider adapter. Keep it independent of the main bridge and UI. Reuse a maintained library only after confirming it supports BCM4773's exact protocol, its license, architecture, and current maintenance status.

**Option B — native adapter around a well-defined existing Linux service.**

If a native driver/library exposes a standard GNSS or NMEA stream after the correct initialization, document and verify that boundary. Only then may `gpsd` or a GeoClue GPS plugin consume that standard stream. Verify with real protocol-level evidence that the stream is actually NMEA or a supported standard format. Do not just set a `Device` path to `/dev/ttyBCM`.

**Option C — isolated vendor compatibility feasibility study (not default/shipped).**

Only if native options are demonstrated infeasible, investigate whether exact same-device Samsung vendor components can be executed in an isolated compatibility environment. This must remain a separate, disabled-by-default experimental branch, require explicit owner approval before first execution, avoid changing normal system boot, and not introduce full Android, AOSP, Waydroid, Halium or libhybris. The investigation must explain the minimal required runtime services and why the architecture boundary can or cannot be preserved. Do not set this up as a stealth dependency.

**Option D — blocked with evidence.**

If no safe protocol implementation or authentic matching firmware/runtime is available, stop at a precise technical blocker. This is a valid, honest outcome. Do not fabricate a NMEA sentence generator, coordinates, satellite list, accuracy, timestamp or “GPS ready” status.

### 4.3 Requirements for any protocol decoder

A native decoder must be defensive and testable:

- parse from arbitrary partial reads and multiple frames per read
- enforce a small, documented maximum frame size
- reject malformed lengths before allocation
- handle split headers and resynchronization safely
- verify checksums/CRC where defined
- reject invalid sequence numbers/duplicate responses as specified
- bound pending transactions and queues
- never allow unbounded memory or CPU use from malformed data
- use monotonic deadlines for transport and RPC timeouts
- distinguish transport connected, protocol initialized, receiver tracking, navigation solution available, and fresh position fix
- report receiver time only if it is actually supplied and validated
- validate latitude/longitude ranges and fix dimensionality
- map accuracy/HDOP/VDOP only if defined by the protocol
- identify satellite count/constellation only from decoded source fields
- never promote a stale last-known position to a fresh fix
- expose protocol errors with redacted diagnostic context
- include a replayable fixture corpus for valid, invalid, truncated, unknown and out-of-order frames

If the protocol cannot be documented or the necessary message IDs are not available, do not invent them. Produce a protocol-gap report and keep the decoder disabled.

---

## 5. Phase 3 — firmware loading and hardware sequencing

### 5.1 Power rail and lease lifecycle

The GPS power rail is at:

`/sys/devices/virtual/sec/gps/GPS_PWR_EN/value`

Current evidence associates it with GPIO145. Verify this against the live target and driver/device-tree information before relying on it. Preserve the existing `GnssProvider` on-demand lease/refcount principle.

Required lifecycle:

1. location policy is enabled by an authorized user
2. an app with `location:read` requests a position
3. the broker/service checks whether a compatible provider and matching firmware are ready
4. the GNSS device service acquires a lease
5. the hardware service performs the documented power-up sequence
6. the BBD/LHD stack is initialized, patch is loaded using its real loader ABI, and readiness is confirmed
7. the receiver begins acquisition
8. the fix is reported only after a valid protocol navigation solution arrives
9. the lease is released when clients stop requesting or the bounded request window ends
10. the rail powers down only when no owner remains and restoring the initial state is correct

Do not turn GPS on at every boot. Do not leave it on because an app crashed. Enforce lease expiry even if the consumer dies. Use monotonic time for deadlines. Ensure a daemon restart does not forget a powered rail or double-count owner references.

### 5.2 Firmware loader safety

Do not write `cat firmware.patch > /dev/bbd_patch` unless the exact driver ABI explicitly documents that write protocol and its framing. Determine whether the loader expects a sequence of ioctls, chunk headers, firmware class requests, a vendor daemon, or another mechanism. Confirm the kernel driver's write/ioctl implementation before coding.

The loader must:

- accept only a manifest-verified matching BCM4773 payload
- reject zero-length, unexpectedly short, oversized and hash-mismatched files
- use bounded chunking and handle partial writes
- distinguish transfer completion from device acceptance
- verify acknowledgement/status from the driver or receiver
- handle interruption and power-loss safely
- never retry indefinitely
- never leave the receiver rail on after failure
- expose `firmware_present`, `firmware_identity_verified`, `transfer_started`, `transfer_complete`, and `device_accepted` as separate states

Firmware present is not firmware loaded. Transfer complete is not device accepted. Device accepted is not GNSS fix.

### 5.3 Verify driver/firmware compatibility

Record exact kernel version/source, module hash, SPI driver binding, compatible device-tree data, receiver/patch identity and vendor firmware build. Do not mix a BCM4773 patch with BCM47752/BCM47755 or another Samsung model simply because a filename looks similar.

No kernel flash or module replacement is in scope unless an explicitly reviewed patch is necessary and can be staged/rolled back safely. Prefer userspace and manifest-level changes first.

---

## 6. Phase 4 — service and provider architecture

### 6.1 Separate device access from the main bridge

If a working native provider can be built, create a dedicated system service, for example `nuxel-gnss-provider.service` (final name may follow repo conventions). Do not give `nuxel-bridge.service` unrestricted access to device nodes and do not run the entire bridge as root.

Use the narrowest practical systemd sandbox:

- dedicated service user/group where feasible
- only exact required device nodes exposed through `DeviceAllow`/device policy
- read/write permissions only for nodes actually required
- `ProtectSystem=strict` or the closest compatible existing policy
- narrow writable state/runtime directories only
- `NoNewPrivileges=true` where compatible
- private tmp and a bounded runtime directory
- explicit service restart policy with a rate limit
- startup/stop timeouts and watchdog where appropriate
- no broad `CAP_SYS_ADMIN`
- no blanket `PrivateDevices=false` on unrelated services

If a root-owned helper is required for one narrowly scoped rail/loader operation, isolate it as a small privileged helper with strict argument validation, a fixed allowlist and no arbitrary path/command execution. Do not add a general root RPC endpoint.

### 6.2 Define an explicit IPC contract

Use a private Unix domain socket or a D-Bus service with an explicit interface. Include:

- provider status and capability query
- start/acquire request with bounded duration
- stop/release request with lease identifier
- stream/fix subscription or query
- structured diagnostic status
- client identity/permission checks

Do not pass shell commands through IPC. Validate every request. Use restrictive socket ownership/mode and SELinux/AppArmor policy if present in Nuxel's target security model. A random local process must not be able to turn the GPS rail on or retrieve a precise position without the location broker's authorization.

### 6.3 Provider result schema

Use one canonical source-aware location result schema across bridge, GeoClue, PWA and GTK clients. At minimum:

```json
{
  "available": true,
  "fix_available": true,
  "source": "gnss",
  "source_detail": "bcm4773",
  "latitude": 0.0,
  "longitude": 0.0,
  "accuracy_m": 0.0,
  "altitude_m": null,
  "speed_mps": null,
  "heading_deg": null,
  "timestamp": 0,
  "timestamp_source": "receiver",
  "fix_type": "3d",
  "satellites_visible": null,
  "satellites_used": null,
  "constellations": [],
  "stale": false
}
```

The example is a **schema only**. Do not use the numeric zeros as sample fixes, defaults or emitted coordinates. Missing fields stay null/unknown. Only fields genuinely delivered by the provider are populated. Use clear field names and match the existing API style if already standardized.

Allowed source labels should be explicit, e.g. `gnss`, `network_wifi`, `network_ip`, `manual`, `unknown`. Do not label a network provider as `gnss` just because a GNSS request fell back to network.

### 6.4 GeoClue integration

Inspect the installed GeoClue version and its actual supported provider/plugin interface before configuring it. Do not assume a `[gps]` section or a particular daemon plugin exists without verifying the package build.

Possible integration paths:

- a native GeoClue provider supported by the installed version; or
- a Nuxel location broker that combines GeoClue network results with the dedicated GNSS provider while retaining source metadata.

Preserve current GeoClue network providers:

- `[ip] enable=true method=ichnaea`
- `[wifi] enable=true submit-data=false`

Do not turn on Wi-Fi data submission. Do not change privacy policy defaults. If GNSS is unavailable, network geolocation may still work and should return a network source with its real accuracy/timestamp.

Define fallback order and semantics explicitly. A network result may be used while GNSS is acquiring or unavailable, but the UI must clearly say `Network location` and must not claim GPS is active or a satellite fix was obtained.

### 6.5 Permission and privacy contract

Preserve the existing permission separation:

- `location:manage` governs permission/policy and hardware-level control.
- `location:read` governs access to location data by an authorized client.
- persisted policy default is OFF.
- the user must have an understandable indication when GNSS is powered/acquiring.
- location policy OFF immediately denies new requests, cancels active requests/subscriptions, revokes leases and returns the rail to the correct safe state.
- do not return cached precise coordinates to an app after permission is revoked.
- stale/last-known position can only be displayed as explicitly stale and only while the current permission policy allows it.
- no continuous background location collection by default.
- no upload of coordinates, Wi-Fi scans or identifiers for diagnostics.

---

## 7. Phase 5 — improve diagnostic truthfulness and eliminate false positives

Create a single structured GNSS status model consumed by `nuxel-gnss-diag.sh`, `nuxel-gps-status`, `GnssProvider`, bridge inventory and Settings.

Recommended stages and state names:

1. `target_identity` — exact supported model/codename/SoC confirmed
2. `device_nodes` — expected BBD nodes visible to the authorized device service
3. `kernel_driver` — exact SPI driver bound
4. `power_rail` — currently on/off, readback verified, and who owns lease
5. `firmware_artifact` — exact firmware file found
6. `firmware_identity` — provenance/hash/target compatibility verified
7. `firmware_transfer` — transfer attempted/completed, with bounded status
8. `firmware_acceptance` — receiver/driver confirms patch accepted
9. `provider_runtime` — native provider available; if not, exact reason
10. `protocol_transport` — BBD transport opened by its sole owner
11. `protocol_initialized` — valid handshake/frames observed
12. `receiver_tracking` — receiver reports tracking/acquisition state
13. `navigation_solution` — valid fix message decoded
14. `fresh_fix` — position has a validated provider timestamp and meets freshness policy
15. `geoclue_or_broker` — location result reaches the public API
16. `client_delivery` — one authorized app successfully receives source/accuracy/timestamp

Every stage should include `state`, `reason`, `evidence`, and optionally a bounded timestamp. Use values like `missing`, `present_unverified`, `ready`, `active`, `failed`, `unsupported`, `blocked`, `not_tested`. Avoid ambiguous booleans that overstate success.

Use clear top-level verdicts:

- `BLOCKED_KERNEL`
- `BLOCKED_FIRMWARE`
- `BLOCKED_FIRMWARE_IDENTITY`
- `BLOCKED_FIRMWARE_ABI`
- `BLOCKED_PROVIDER`
- `BLOCKED_PROTOCOL`
- `NO_DATA`
- `ACQUIRING`
- `NO_FIX`
- `FIX_STALE`
- `NETWORK_ONLY`
- `GNSS_FIX`
- `GNSS_FIX_DELIVERED`

`READY_FOR_SKY` may be retained only if it means all provider/transport prerequisites are ready and an owner outdoor test is still required. It must never be interpreted as a fix.

### Firmware inventory rules

- Do not include `/dev/bbd_patch` in `firmware_present`.
- Do not let any generic filename containing `gps` satisfy the BCM4773 firmware requirement.
- Check the exact configured `/system/bin/bcm_sensorhub_a1.patch` path if it is mounted and accessible.
- Do not treat vendor executables or `.so` files as firmware patch payloads.
- `firmware_loaded` remains false until actual load/acknowledgement evidence exists.
- If the bridge cannot see a node due to `PrivateDevices`, return `not_visible_to_service` and obtain authorized service-side inventory; do not infer host absence.

### Sensitive diagnostics

Normal status output should not print precise coordinates, raw GNSS frames, device serial numbers, Wi-Fi BSSIDs or other unnecessary identifiers. A separate owner-only evidence mode may record precise fix evidence under restrictive permissions, with an explicit warning.

### Bound every diagnostic

- max monitor duration: use existing configured upper bound, no hidden infinite loops
- each select/poll/read operation bounded
- each subprocess has explicit timeout and kill/reap on timeout
- test harness does not wait forever for a child process
- service stop and lease release always run in `finally`/trap cleanup
- use monotonic deadlines rather than wall-clock for timeout accounting

The existing diagnostic self-test has previously timed out. Fix it. A test suite that hangs is not a pass, even if its first fixture printed `PASS`.

---

## 8. Phase 6 — integrate with Nuxel UI and apps without regressing location

The existing Nuxel location UI, source attribution, location permission and Maps/offline map path are already useful. Extend them rather than rebuilding them.

### Settings / Quick Settings

Show separate, unambiguous states:

- Location permission OFF
- Location permission ON, no provider
- Network location available
- GNSS hardware detected but firmware/provider blocked
- GNSS initializing/acquiring
- GNSS satellite fix available (with timestamp/accuracy)
- GNSS fix stale/lost

Provide a user-visible GNSS diagnostic detail page for capability and blocker. Only expose start/stop/acquire controls through the permission-aware broker. Never have Settings toggle raw GPIO or open `/dev/ttyBCM` itself.

### Maps

- Preserve offline OSM tile functionality and attribution.
- Preserve network location when satellite GNSS is unavailable.
- Show the real source and accuracy on the location indicator.
- Do not automatically center on an old/stale fix without a stale marker.
- Do not draw or display fake satellite metadata.
- Keep online tile access optional and do not require internet for cached areas.

### Camera and other clients

Only add GNSS geotagging where the app already requests location permission. The source metadata must be preserved. If the fix is network-derived, do not label the camera result as GPS geotagging. If no fresh fix exists, omit precise location rather than using an unqualified stale coordinate.

### Common JS API

Audit `pwa/nuxel-common/geolocation.js` for all result consumers. Ensure it handles:

- absent GNSS provider
- network-only result
- GNSS acquiring with network fallback
- fresh GNSS fix
- GNSS fix lost/stale
- timestamp absent/invalid
- permission revoked mid-request
- service restart and reconnect

A missing timestamp must remain missing/unknown. Do not replace it with the time Nuxel happened to observe the response and then call it a receiver timestamp. This was previously corrected in `_remember_fix()` and must not regress.

---

## 9. Phase 7 — tests required before integration

### 9.1 Provider unit tests

Expand `tests/pwnage42000/test_gnss_provider.py` or create a clearly grouped `tests/gnss/` suite. Cover:

- S10+ target detection and unsupported model rejection
- exact path inventory
- no false firmware match from random GNSS/GPS-named files
- exact patch file found and hash match/mismatch
- `/dev/bbd_patch` treated as loader, not firmware
- missing patch blocks power-on
- invalid firmware identity blocks power-on
- provider unavailable blocks power-on
- policy OFF blocks read and power operations
- permission denied for unauthorized caller
- lease refcount across multiple clients
- one client release does not power off another client's rail
- process crash/lease expiry cleanup
- daemon restart recovery
- initial rail state preserved correctly
- no persistent rail ON at idle
- power failure and readback mismatch
- hard timeout and cancellation

### 9.2 Protocol decoder tests

Only after the actual protocol is established, add fixture-driven tests:

- one valid initialization/handshake sequence
- split frame across reads
- multiple frames in one read
- partial header and malformed length
- invalid CRC/checksum
- unknown message type
- duplicate/out-of-order response
- stale receiver timestamp
- invalid lat/lon
- fix-invalid/no-fix status
- 2D/3D distinction where defined
- valid fresh fix with provider timestamp
- corrupted fixture must never create a fix
- parser fuzz/property tests with strict memory/time budgets

Fixtures must be captured from legitimate device evidence or generated from documented protocol definitions. Synthetic fixtures are never a physical-device fix proof.

### 9.3 Integration tests

Use mocks for hardware and provider IPC. Test:

- policy/permission flow end-to-end
- network fallback remains available
- network provider source remains `network_wifi` or `network_ip`
- GNSS source only follows provider GNSS message
- no location leakage after revoke
- GeoClue/broker timeouts
- service unavailable and reconnect
- app subscription cancellation
- daemon crash cleanup
- no duplicate device owner opening `/dev/ttyBCM`
- systemd unit package installation and hardening
- udev ownership/group rule
- rootfs target package includes all intended files

### 9.4 Diagnostic tests

Make `tools/s10plus/a33/nuxel-gnss-diag.sh` selftest fully deterministic and bounded. Its Python/shell fixtures must not depend on physical hardware or wait for live GPS data. Add explicit test timeouts. Investigate why the existing self-test hangs; don't paper it over with a longer timeout.

### 9.5 Regression tests

Re-run relevant location policy, bridge, GeoClue, Maps, common geolocation, permissions, systemd packaging and S10+ image build tests. Also re-run the existing 9 provider tests. Report each result honestly.

---

## 10. Phase 8 — physical S10+ validation protocol

A GNSS feature cannot be marked done by unit tests. A real owner-controlled outdoor test is mandatory before declaring GPS working.

### Preparation

- Exact phone must identify as SM-G975F / `beyond2lte` with the expected Exynos 9820 hardware.
- Record Nuxel build ID, kernel release and device firmware build.
- Enable Location using the existing UI; keep it OFF by default otherwise.
- Use a controlled test session and ensure the correct matched firmware/provider is active.
- Ensure the GPS power rail is initially OFF and its readback works.
- Keep the owner aware that a cold start can take several minutes.

### Outdoor test

1. Go outdoors with a clear view of the sky, away from a window/roof where possible.
2. Start a cold GNSS acquisition via the public location API (not a raw shell read).
3. Record provider state transitions and time-to-first-fix with monotonic timestamps.
4. Allow up to 300 seconds for first cold fix, unless the receiver's verified design specifies another appropriate window.
5. Require a valid receiver/provider timestamp, fix-valid state, and provider-reported accuracy.
6. Cross-check the position with a known offline map or a separate trusted receiver. Keep the exact coordinate in a restricted owner evidence file, not general console output.
7. Require accuracy at or better than 50 m for the initial acceptance test, unless the provider honestly reports a poorer value; poorer accuracy is a measured partial result, not a pass.
8. Record satellites visible/used only if the actual provider reports them.
9. Stop acquisition, release the lease, and verify GPS_PWR_EN returns to the correct OFF state.
10. Repeat for at least two warm starts and one new cold start after a full power-down.

### Indoor/no-sky control

Repeat an acquisition indoors or with sky view blocked. It must not fabricate a fix. If network location is returned, it must be clearly identified as network source. This control validates that the app is not merely displaying cached/network coordinates under a GPS label.

### Soak and lifecycle test

- Keep a location client active for at least 10 minutes with no crash, runaway CPU, unbounded log growth or unexpected reboot.
- Terminate the client and verify lease release.
- Toggle location permission OFF during a live request and verify cancellation, location-data revocation and safe rail handling.
- Restart the provider service and verify it recovers cleanly without leaving the rail stuck ON.
- Verify battery behavior at idle and after screen-off; no continuous GNSS power absent an authorized active client.

### Evidence required for full PASS

- correct hardware identity and driver bound
- exact matching patch firmware identity/provenance
- firmware load accepted by device/driver
- native (or separately approved) compatible BBD/LHD provider active
- valid BBD/LHD protocol transaction/receiver state
- actual fresh satellite fix with provider timestamp
- provider-reported accuracy
- outdoor cross-check within tolerance
- source reported as `gnss`
- GeoClue/Nuxel broker delivers the same fix to an authorized client
- permission revocation and power lease cleanup pass
- network location remains separately functional
- no regression in Maps/Settings or battery default state

Without these items, the status must remain `BLOCKED_*`, `NO_FIX`, `ACQUIRING`, or `PARTIAL` as appropriate.

---

## 11. Phase 9 — packaging, rollout and rollback

### Packaging

Update the actual `beyond2lte` image manifest, not only a generic package list. Include:

- canonical GNSS manifest/config
- service unit and IPC policy
- provider binary/library, if implemented
- udev rule, if needed
- diagnostic/status tools
- required open-source dependencies and their licenses
- firmware staging support (not a proprietary binary unless distribution is explicitly legal and approved)
- documentation and tests

Do not ship vendor proprietary blobs in the public repository or release image without clear redistribution permission. Prefer an owner-provided firmware staging flow with hash verification.

### Deployment

- Build the complete S10+ image/package set.
- Run all tests and image validation before touching the phone.
- Provide an explicit deploy-over-Wi-Fi-SSH command sequence compatible with existing Nuxel S10+ debug/deploy tooling.
- Preserve current working SSH access and keep the install atomic where possible.
- Back up only the files being replaced and record hashes.
- Avoid reboot unless required and explicitly documented.
- After install, verify systemd units, permissions, diagnostics and safe OFF state before any RF acquisition test.
- The first power-on/fix test must be owner initiated.

### Rollback

Provide one deterministic rollback script or exact commands that:

- stop/disable the new provider
- release/force-safe any provider-owned GPS lease through a narrow authorized helper
- verify the GPS rail OFF (or restore its recorded safe initial state)
- restore previous service, config, udev and package files
- restore previous GeoClue settings
- remove only new files that were added by the patch
- not delete user data or GNSS owner-provided firmware source files
- restore location UI/network provider behaviour
- record rollback outcome

Never roll back by blindly removing all firmware or device configuration from the phone.

---

## 12. Required engineering deliverables

Complete the work and return all of the following:

1. **Implementation patch**: actual repository code changes, not pseudo-code.
2. **Canonical GNSS manifest**: exact stages, artefact identity, provenance and truthful status.
3. **Native provider or protocol feasibility result**: implementation if verified; otherwise a precise reason it cannot be safely implemented without missing artefacts/specification.
4. **Firmware staging/extraction helper**: safe, read-only, model/build-verified and hash-generating, if applicable.
5. **Dedicated least-privilege provider service** if a real provider is implemented.
6. **GeoClue/Nuxel broker integration** preserving network fallback and source identity.
7. **Permission/privacy integration** preserving default OFF and `location:manage` vs `location:read`.
8. **Diagnostic improvements**: no filename false positives, no fake readiness, all waits bounded, no hang.
9. **Unit, protocol, integration and regression tests** with results.
10. **S10+ build/package integration**.
11. **Deployment and rollback instructions**.
12. **Physical test protocol and evidence template**.
13. **A final report** with completed / partially completed / blocked table.

### Final report format

Use these headings:

- Executive result (do not overstate)
- Exact tested hardware and software versions
- Findings from source and live device (label source of evidence)
- What changed (file-by-file)
- Firmware provenance and compatibility result
- Driver/transport/protocol state
- Provider and location API state
- Permissions/privacy and power behavior
- Unit/integration/regression test results
- Physical-device test results (or explicitly `NOT RUN`)
- Battery/performance observations
- Remaining blockers and exact required owner artefacts/actions
- Deployment instructions
- Rollback instructions

Use one of these final statuses:

- `FULLY_FIXED_AND_PHYSICALLY_VERIFIED`
- `IMPLEMENTED_PENDING_OWNER_OUTDOOR_TEST`
- `REPOSITORY_READY_BLOCKED_BY_EXACT_FIRMWARE`
- `REPOSITORY_READY_BLOCKED_BY_PROTOCOL_OR_VENDOR_RUNTIME`
- `PARTIAL_IMPLEMENTATION`
- `NO_SAFE_IMPLEMENTATION_FOUND`

Do not use `FULLY_FIXED_AND_PHYSICALLY_VERIFIED` without an actual outdoor satellite fix on the target phone and evidence meeting Section 10.

---

## 13. Explicit anti-patterns — prohibited shortcuts

Do not:

- point stock `gpsd` directly at `/dev/ttyBCM`
- use `gpspipe`, `cgps` or `gpsmon` as proof that BBD transport is NMEA
- parse `$GPGGA`-like substrings out of raw BBD payloads
- report any SPI register response as a position fix
- equate node presence with firmware or service readiness
- equate `GPS_PWR_EN=1` with a working receiver
- mark `/dev/bbd_patch` as firmware installed
- use arbitrary `bcm47752`, `bcm47755`, `bcm4773` or generic `gps.bin` files without exact compatibility evidence
- blindly copy Android binaries into `/usr/bin`
- symlink Android `linker64` into Fedora system paths
- install full Android runtime / AOSP / Waydroid / Halium / libhybris
- silently make an experimental vendor runtime a required dependency
- change the main bridge to root or disable its sandbox
- keep the GPS rail powered at boot or when no authorized lease exists
- run unbounded monitor loops or blocking hardware calls on the UI thread
- fabricate coordinates, accuracy, timestamps, satellite counts, ephemeris or fix status
- label GeoClue Wi-Fi/IP results as GNSS
- enable Wi-Fi data submission as a workaround
- collect or upload location evidence without owner approval
- flash bootloader, modem, EFS/NV, radio or kernel partitions
- claim success based only on passing mocked unit tests

---

## 14. Definition of success

The desired end state is a native Nuxel location stack on the Galaxy S10+ where:

- the receiver's exact hardware path is understood;
- matching firmware is verified and loaded by the proper mechanism;
- a compatible BBD/LHD protocol provider exists and is isolated with least privilege;
- GNSS acquisition is demand-driven and battery-safe;
- a real satellite fix, timestamp, accuracy and receiver status are decoded without fabrication;
- Nuxel's common location API and Maps/Settings/authorized applications receive accurate source-labelled data;
- network location continues to function as an explicitly separate fallback;
- permission OFF stops location activity and prevents data delivery;
- diagnostics explain every stage and never turn partial hardware detection into false GPS success;
- all tests are bounded and repeatable;
- the physical phone passes outdoor cold/warm acquisition and no-sky control tests;
- there is a tested rollback path.

**Begin with the repository audit and baseline. Then implement every safe, evidence-backed improvement in this mission. Do not stop after writing a plan. If a specific missing vendor artefact or protocol fact prevents a real fix, make the remaining system production-ready around that blocker, identify the exact required input, and report the blocker honestly.**
