# FULL PWNAGE GPS --- Samsung Galaxy S10+ (`beyond2lte`) GNSS Bring-Up, Native Integration, and Maps Acceptance

> **Mission:** Fully bring up and verify GNSS on Nuxel for the Samsung
> Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), using the extracted
> handoff material in `./gps/`. Deliver a working, maintainable
> Nuxel-native location pipeline where possible, prove it with real
> hardware measurements, and prove that the existing Nuxel Maps app can
> obtain and display the phone's actual location.
>
> **Do not confuse file presence, a successful daemon start,
> cached/network location, or a simulated fix with a functioning GNSS
> receiver.** The final result must distinguish all of these.

------------------------------------------------------------------------

## 0. Operating rules --- read before touching anything

1.  Work from the repository root. The handoff ZIP has already been
    extracted to **`./gps/`**. Do not assume a different path.
2.  First inspect the complete repository and `./gps/`; do not
    overwrite, rename, delete, or "clean up" source evidence before
    understanding it.
3.  Do not flash, reboot, power-cycle, write to partitions, run `dd`,
    invoke Heimdall, or issue TWRP commands. This task is
    implementation, host-side validation, and controlled live-device
    testing only. Produce a reflash manifest for a later, separately
    approved batch.
4.  Do not download, copy, or use firmware for a different phone,
    Broadcom GNSS generation, board, region, or Samsung build. In
    particular, do not assume that a file named `SensorHub.patch`,
    `bcm_sensorhub_a1.patch`, or `bcm4773_sensorhub.patch` is compatible
    merely because its name looks plausible.
5.  Never fabricate hardware evidence. A fixture, mock, replay, cached
    coordinate, IP geolocation, Wi-Fi positioning, Android location
    result, or manually supplied coordinate is not a GNSS fix.
6.  Do not claim success from `test -e`, a device node existing, a
    daemon process existing, a zero exit status, or a UI marker
    appearing. Require end-to-end evidence.
7.  Preserve Nuxel's existing architecture, conventions, service
    manager, packaging, UI design, security boundaries, and the existing
    Maps app. Read the code before choosing integration points.
8.  Keep the phone recoverable. Do not alter boot-critical files or
    persistent device state without explicit approval. If a test can
    hang, block, or leave GPS power enabled, put it behind a timeout and
    a guaranteed cleanup/finally path.
9.  Treat proprietary Samsung binaries as untrusted compatibility
    inputs. Audit ELF architecture, interpreter, ABI, dependencies,
    licensing/provenance, and runtime assumptions. Android/Bionic
    binaries are not native Fedora/glibc executables. Do not silently
    copy them into `/usr/bin` or pretend they are portable.
10. If a required proprietary component is absent, say exactly what is
    missing and provide a reproducible acquisition procedure from the
    user's own stock SM-G975F firmware/device. Do not invent or
    synthesize proprietary firmware.
11. Do not weaken SELinux, permissions, sandboxing, signature checks, or
    service isolation as a shortcut.
12. Keep a detailed engineering log: commands, timestamps, return codes,
    files changed, test results, hardware state, and unresolved
    blockers.

## 1. Required initial reconnaissance

### 1.1 Establish target and repository state

-   Confirm repository root, branch, working tree status, latest commit,
    build/test commands, and any existing uncommitted changes.
-   Confirm target identity from Nuxel configuration and the connected
    device: `SM-G975F`, codename `beyond2lte`, Exynos 9820 /
    `universal9820`.
-   Record Android/Samsung source build fingerprint and firmware version
    if available. Do not infer the exact firmware build from the model
    alone.
-   Inspect `./gps/` recursively. Read its README, agent handoff, target
    manifest, audit findings, extraction scripts, verification reports,
    upstream references, and any extracted payloads.
-   Verify ZIP/extraction integrity and every recorded SHA-256. Re-run
    verification scripts where safe.
-   Inventory every file with path, size, type, SHA-256, source
    provenance, target build, and confidence classification.

### 1.2 Inspect the existing Nuxel GPS implementation

Search the entire repository, not just filenames, for: - GNSS/GPS, BBD,
BCM4773, Broadcom, SSP, sensor hub, `lhd`, `gpsd`, NMEA, location
provider, Geoclue, Maps, map marker, permission prompts, location
settings, and location service. - Device-tree nodes, SPI drivers,
GPIO/regulator/pinctrl definitions, kernel configs, firmware search
paths, init scripts, udev rules, systemd units, D-Bus policy, SELinux
policy, packaging, diagnostics, and reflash manifests. - Existing
diagnostic tools and tests, especially anything that reports
`GPS_PWR_EN`, `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control`,
`/dev/bbd_sensor`, SPI binding, SSP status, or a `GPS: false` state.

Read the actual source and tests behind every existing claim. Do not
trust old reports without reproducing the relevant observations.

### 1.3 Build a state diagram

Document the actual device-specific path, based on source: 1. GNSS power
rail / enable GPIO and required regulators. 2. Broadcom BCM4773 SPI
transport and bound driver. 3. BBD patch-loader interface
(`/dev/bbd_patch`) and exact ioctl/write ABI. 4. BBD control and sensor
interfaces. 5. Packet transport (`/dev/ttyBCM`) and framing/protocol. 6.
SSP / sensor-hub coordination, if required by this board. 7.
Firmware/patch handshake and version response. 8. GNSS engine start and
satellite acquisition. 9. Vendor GNSS runtime or native protocol
implementation. 10. Nuxel location-provider API. 11. Permissions and
D-Bus/system service. 12. Maps app request, provider selection, location
update, and rendered position.

For every edge, cite the source file, kernel source, device-tree
property, captured log, or measured device evidence that proves it.

## 2. Firmware and proprietary runtime acquisition

### 2.1 Audit `./gps/` payloads

Classify each candidate as one of: - **Verified target firmware:** exact
hardware/build match and trustworthy provenance. - **Verified target
userspace binary:** exact target source/build and ABI known. -
**Configuration:** known source and intended runtime. - **Unverified
candidate:** filename or partial metadata only. - **Test fixture:**
synthetic/non-device data. - **Wrong target:** incompatible
model/board/generation. - **Missing:** expected but not supplied.

Never promote an unverified candidate to verified based on filename,
size, or a successful copy.

### 2.2 Identify the exact BCM4773 patch

-   Search the supplied stock firmware extraction and repository history
    for the exact Broadcom sensor-hub/GNSS patch expected by the S10+
    driver and Samsung `lhd` configuration.
-   Determine whether the patch is a standalone payload, embedded in a
    vendor image, or delivered through another Samsung firmware
    mechanism.
-   Trace the driver's actual firmware request path and loader ABI. Read
    the exact driver source corresponding to the running kernel, not a
    similarly named upstream driver.
-   Establish expected file format, header, version, board/product
    identifiers, checksum/signature, size bounds, and loader semantics
    from source or verified stock logs.
-   Confirm the patch is for BCM4773 on `beyond2lte` and compatible with
    the exact stock firmware/kernel build.
-   If no exact patch can be verified, stop before loading it. Produce a
    precise missing-artifact report and an extraction command/script for
    the user's own stock firmware.

### 2.3 Audit Samsung GNSS runtime

The known S10-family vendor recipe references components such as: -
`lhd` - `gpsd` - `gps.default` - Android GNSS HAL
(`android.hardware.gnss`) - Samsung GNSS HAL/service
(`vendor.samsung.hardware.gnss`) - `libwrappergps` - `gps.xml` -
`lhd.conf` - GNSS init/service rules

Do not assume all are present in `./gps/`. Confirm each actual file and
provenance.

For each ELF: - Run `file`, `readelf -h`, `readelf -l`, `readelf -d`,
and symbol/version inspection. - Confirm AArch64 vs ARM32 and the
dynamic linker (`/system/bin/linker64`, Bionic, glibc, etc.). -
Enumerate all direct and transitive shared-library dependencies. -
Identify Android properties, Binder/HIDL/AIDL, init, SELinux, vendor
service, socket, device-node, and configuration assumptions. - Determine
whether it can run natively, needs a minimal Android compatibility
environment, or should only be used as protocol/reference material. - Do
not use `patchelf` to change an interpreter or dependency blindly. Any
compatibility experiment must be isolated, reversible, and
evidence-based.

### 2.4 Choose and document the architecture

Evaluate at least these options:

**A. Native Nuxel GNSS service (preferred if protocol is
understood):** - Native service owns BBD transport, firmware lifecycle,
protocol parsing and provider publication. - Use a narrow, documented
interface to the location framework. - Keep device-specific code behind
a backend interface.

**B. Isolated Samsung compatibility runtime:** - Only if vendor binaries
genuinely require Android runtime services. - Define exactly which
minimal Android components are required and how they are isolated. - Do
not turn Nuxel into Android or add a full Android framework just to make
one HAL work. - Demonstrate stable service lifecycle, permissions and
clean shutdown.

**C. Hybrid reference implementation:** - Use Samsung
configuration/protocol behavior as reference while implementing the
transport/provider natively. - Do not reverse-engineer undocumented
protocol fields by guessing; capture and label evidence.

Choose based on measured feasibility, not preference. Record rejected
options and reasons.

## 3. Kernel, power and transport validation

### 3.1 Confirm actual kernel ABI

-   Match the running kernel release and source revision to the kernel
    tree in this repo.
-   Inspect BCM4773 SPI driver, BBD patch loader, control/sensor
    interfaces, tty transport, ioctl numbers, packet framing, locking,
    timeouts and error paths.
-   Verify device-node major/minor, ownership, group, mode,
    udev/systemd-tmpfiles rules and SELinux labels.
-   Ensure no competing process owns the transport.
-   Check kernel logs for probe, firmware request, SPI errors, timeouts,
    resets, IRQs and loader completion.

### 3.2 Power sequencing

-   Find the authoritative GPIO/regulator definition and active
    polarity.
-   Confirm whether `GPS_PWR_EN=0` means off for this board; do not
    infer active polarity.
-   Identify sequencing delays, reset lines, clock requirements and SSP
    coordination.
-   Use existing supported kernel interfaces. Do not poke arbitrary GPIO
    numbers or write undocumented sysfs controls.
-   Test enable/disable only through a reviewed, bounded interface, with
    cleanup guaranteed even after timeout or process termination.
-   Record before/after power state and kernel logs.
-   Ensure the service can recover from a failed firmware load without
    leaving the rail on or the device wedged.

### 3.3 Transport tests

Create deterministic tests for: - Device absent. - Permission denied. -
Driver not bound. - Firmware missing. - Firmware rejected. -
Short/partial packet. - Invalid checksum/header. - Timeout. - Device
reset during transfer. - Concurrent access. - Service restart. - Clean
shutdown.

A transport open/read success is not GNSS success.

## 4. Implement the complete Nuxel GNSS stack

Implement all missing components identified by the audit, with clean
interfaces and tests.

### 4.1 Firmware loader

-   Verify target identity and firmware hash before load.
-   Validate payload bounds and expected format before touching
    hardware.
-   Use the exact kernel loader ABI.
-   Enforce timeout, cancellation and bounded retries.
-   Capture firmware version/acceptance acknowledgement if available.
-   Refuse unknown or wrong-target firmware.
-   Log actionable errors without dumping sensitive data.
-   Never automatically fall back to an unverified blob.

### 4.2 BBD transport / protocol

-   Implement the exact framing and handshake proven by source/captures.
-   Handle partial reads/writes, packet boundaries, checksums, sequence
    numbers, reconnect and reset.
-   Use nonblocking I/O or bounded waits where appropriate.
-   Ensure one owner of the transport and explicit lifecycle states.
-   Add protocol unit tests with known-good captured vectors; mark
    synthetic vectors clearly.
-   No invented packet formats.

### 4.3 GNSS engine and provider

-   Parse actual receiver output and distinguish raw GNSS measurements,
    navigation solution, NMEA, and vendor proprietary messages.
-   Validate latitude/longitude ranges, fix type, timestamp, accuracy,
    altitude, speed and bearing.
-   Reject stale, malformed, impossible or zero-filled coordinates.
-   Expose a stable Nuxel location-provider API.
-   Include provider metadata: source (`gnss`), fix validity, fix
    timestamp, horizontal accuracy, satellites/constellations where
    available, and whether the fix is cached.
-   Support cold start, warm start, hot start if the firmware supports
    them.
-   Handle loss of signal, indoor/no-fix, antenna issues,
    suspend/resume, reboot and service restart.
-   Do not claim multi-constellation support unless observed.

### 4.4 Nuxel service integration

-   Use the project's existing service manager and packaging
    conventions.
-   Add a dedicated service with correct dependencies, user/group,
    device access, restart policy, timeout, shutdown and journal
    logging.
-   Ensure service does not block boot.
-   Provide explicit states: unavailable, blocked, firmware-missing,
    loading, ready-no-fix, acquiring, fix, stale, error.
-   Add a health/status CLI command and structured diagnostic output.
-   Add user-facing permission handling and location enable/disable
    controls consistent with Nuxel.
-   Respect privacy: location must not be exposed to arbitrary local
    users or remote clients by default.

### 4.5 Geoclue / location broker

Inspect whether Nuxel already uses Geoclue or a custom location broker.
Do not create a second competing source without a design reason.

-   Integrate the GNSS provider using the actual supported API.
-   Preserve source attribution and accuracy.
-   Do not let IP/Wi-Fi/network location silently masquerade as GNSS.
-   If network positioning exists, expose it as a distinct
    provider/source and label it accordingly.
-   Verify D-Bus names, interfaces, permission checks and client
    authorization.
-   Add integration tests for provider discovery and client
    subscription.

## 5. Existing Nuxel Maps app --- mandatory end-to-end acceptance

**This is a separate acceptance track, not an optional UI smoke test.**
Locate the actual Maps app source, identify its current location
acquisition path and test it against the real provider.

### 5.1 Audit Maps

-   Find the Maps app entry point, frontend/backend, location API calls,
    permission prompts, settings, map library and marker implementation.
-   Determine whether it currently requests browser geolocation,
    Geoclue, a Nuxel D-Bus API, a mock provider, a static default
    coordinate, IP location, or another source.
-   Identify any hardcoded fallback coordinate, demo mode, fixture,
    cached location or silent fallback.
-   Trace a location request from the Maps UI to the OS provider and
    back to the map marker.
-   Check coordinate order carefully (latitude vs longitude), units,
    timestamps, accuracy and stale handling.
-   Check whether the app is using the correct map projection and
    whether the marker is placed at the returned coordinate.
-   Verify the map tile/network path separately from the location
    provider. A blank map is not proof of GPS failure; a visible map is
    not proof of GPS success.

### 5.2 Fix Maps integration

If Maps cannot request or display the GNSS location: - Implement the
smallest correct integration with the Nuxel location broker/provider. -
Request permission through the existing Nuxel permission mechanism. -
Display clear states: permission required, location disabled, GNSS
unavailable, acquiring, fix acquired, stale fix, provider error. - Add a
"Locate me" control and a follow/center behavior that does not
continuously fight manual map panning. - Display source (`GNSS`,
network, cached) and accuracy in the UI. - Do not silently substitute
network/IP/mock coordinates when the user explicitly requests GNSS. - If
network fallback is supported, make it explicit and visibly label the
source. - Avoid excessive polling; use subscriptions/watch APIs where
available and clean them up when the app closes or loses focus. - Do not
expose precise coordinates in logs, telemetry or remote dashboards
unnecessarily.

### 5.3 Maps acceptance tests

Create automated tests for: - Permission granted and denied. - Location
disabled. - Provider unavailable. - No-fix / acquiring. - Valid GNSS
fix. - Stale fix. - Invalid coordinates. - Network-only location,
visibly labelled. - Cached location, visibly labelled. - Provider
disconnect/reconnect. - App background/foreground. - Manual map pan
followed by "Locate me". - Latitude/longitude not swapped. - Marker and
accuracy circle rendered at the correct coordinates.

Use a mock provider for deterministic UI tests, but label them as mock
tests. Then perform a separate live-device test with a real GNSS fix.

### 5.4 Real-world Maps test procedure

Only after firmware and provider are genuinely working:

1.  Take the phone outdoors with a reasonably open sky view. Record test
    location as private test data; do not commit exact coordinates.
2.  Ensure location permission is granted and GNSS is enabled.
3.  Clear/label cached location so the test cannot pass from stale data.
4.  Start the GNSS service and Maps app.
5.  Record UTC timestamps for power-on, firmware acceptance, acquisition
    start, first satellite data, first valid fix, and Maps marker
    update.
6.  Capture provider diagnostics: fix source, fix timestamp, horizontal
    accuracy, fix type and satellites/constellations if available.
    Redact precise coordinates from committed logs.
7.  Compare the Maps marker against an independent reference position.
    Report distance error and accuracy; do not claim precision beyond
    the provider's reported uncertainty.
8.  Move a meaningful distance and confirm the marker updates with a new
    timestamp and plausible movement.
9.  Disable GNSS and verify Maps transitions to unavailable/stale rather
    than pretending the last point is live.
10. Restart the service and app; verify recovery.

**Real GNSS acceptance requires a fresh receiver-originated fix.** A
mock test, browser mock, network location or cached fix cannot satisfy
this gate.

## 6. Test strategy and release gates

Build a test matrix with columns: test ID, layer, setup, command/action,
expected result, actual result, evidence path, pass/fail/blocker.

Required gates:

### Gate A --- Static integrity

-   All payloads have provenance, target identity and hashes.
-   No wrong-device or unverified firmware is staged for automatic
    loading.
-   All binaries have ABI/dependency reports.
-   No accidental secrets or private coordinates committed.

### Gate B --- Unit tests

-   Firmware manifest/identity/hash validation.
-   Firmware parser/loader state machine.
-   BBD framing/parser.
-   GNSS message parser.
-   Coordinate/fix validation.
-   Provider state machine.
-   Maps location-state and coordinate rendering.

### Gate C --- Host integration

-   Service packaging and startup.
-   D-Bus/provider registration.
-   Permission model.
-   Maps app integration against a mock provider.
-   Service failure/restart and cleanup.
-   No boot blocking.

### Gate D --- Live hardware, no flash

-   Exact device identity.
-   Driver and device-node status.
-   Power sequencing.
-   Verified firmware load/acknowledgement.
-   BBD handshake and actual receiver data.
-   Fresh GNSS fix outdoors.
-   Real Maps app displays that fix and tracks movement.
-   No kernel panic, transport wedge or persistent unexpected power
    state.

### Gate E --- Reflash readiness

Only after Gates A--D: - Produce exact reflash file manifest,
destination paths, owners, modes, labels, hashes and service
enablement. - Separate system/vendor payloads from
boot/kernel/device-tree changes. - State whether a kernel reflash is
truly required. - Include rollback/recovery instructions and preflight
checks. - Include a post-flash verification script. - Do not flash.
Await explicit human approval for the batch.

### Gate F --- Post-flash verification plan

Write a deterministic script/plan that checks: - Target identity. -
Firmware hash and provenance. - Device nodes and driver binding. - Power
state and firmware handshake. - Service health. - Provider
registration. - Maps permission and location request. - Fresh real GNSS
fix. - Logs and cleanup.

## 7. Required deliverables

Create or update these files in the repository (adapt paths to existing
conventions; do not create duplicate documentation if an equivalent
exists):

1.  `docs/hardware/gps/GPS-IMPLEMENTATION.md` --- architecture, state
    machine, firmware provenance, ABI findings, service design and Maps
    integration.
2.  `docs/hardware/gps/GPS-TEST-REPORT.md` --- exact test matrix and
    evidence, clearly separating mocked, host and live-hardware results.
3.  `docs/hardware/gps/GPS-REFLASH-MANIFEST.md` --- exact files and
    destinations, with hashes and rollback notes; no speculative
    entries.
4.  `docs/hardware/gps/GPS-BLOCKERS.md` --- only genuine remaining
    blockers, owner/action and required evidence.
5.  A reproducible diagnostic command/script for GNSS health.
6.  A post-flash verification script that is safe by default and does
    not flash.
7.  Maps app integration and tests, if the audit finds it is incomplete.
8.  Service/config/packaging changes with corresponding tests.

At the end, provide a concise but complete report: - What was already
working. - What you changed and why. - Exact files changed. -
Commands/tests executed and results. - Which tests were mocked vs real
hardware. - Whether a fresh physical GNSS fix was obtained. - Whether
the existing Maps app displayed and tracked that fix. - Remaining
blockers and exact required artifacts. - Exact reflash manifest and
whether a kernel reflash is needed. - Explicit statement: **NO FLASH WAS
PERFORMED**.

## 8. Definition of DONE

GPS is **not** done merely because a service starts.

Mark **GNSS FULLY WORKING** only when all are true: - Correct SM-G975F /
beyond2lte firmware is independently identified and verified. - The
correct Broadcom firmware is accepted by the device's loader. - BBD
transport and GNSS engine produce real receiver-originated data. - A
fresh outdoor GNSS fix is obtained, with timestamp and accuracy. - Nuxel
location provider publishes it with correct metadata. - Permissions and
service lifecycle work. - The existing Nuxel Maps app requests and
displays the real fix, then follows a subsequent physical movement. -
Tests pass and evidence is saved without leaking precise coordinates. -
No unresolved kernel panic, reboot, cleanup or power-state regression
remains.

Otherwise use an honest status: -
`BLOCKED — missing proprietary firmware` -
`BLOCKED — firmware identity unverified` -
`PARTIAL — transport works, no receiver fix` -
`PARTIAL — provider works, Maps integration incomplete` -
`PARTIAL — Maps mock tests pass, live GNSS not proven` -
`PASS — GNSS and Maps verified on real hardware`

**Start now with reconnaissance and evidence collection. Do not stop
after writing a plan. Implement every safe, evidence-supported fix, run
the complete test suite, and clearly identify anything that genuinely
requires additional stock firmware or human approval.**
