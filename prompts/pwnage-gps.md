# PWNAGE GPS --- Kickstart Prompt for Nuxel S10+ GNSS

You are working in the Nuxel repository for the Samsung Galaxy S10+
SM-G975F (`beyond2lte`, Exynos 9820). The S10+ GNSS handoff pack has
already been extracted into **`./gps/` at the repository root**.

Your mission is to take GPS from its current partially exposed hardware
state to a fully working Nuxel location subsystem, and to verify that
our **existing Nuxel Maps app can locate and pinpoint the phone's real
position**.

## Non-negotiable rules

-   Begin by reading `./gps/agent/AGENT-HANDOFF.md`,
    `./gps/agent/TARGET-FILE-MANIFEST.md`,
    `./gps/repo-evidence/AUDIT-FINDINGS.md`, and the rest of `./gps/`.
-   Inspect the actual repository implementation and Maps app before
    editing.
-   Do not flash, reboot, run `dd`, use Heimdall, invoke TWRP, or write
    partitions. This is a development/validation task. Produce a reflash
    manifest only; wait for explicit approval before any flash.
-   Never load a Broadcom patch merely because its filename looks right.
    Verify exact SM-G975F/beyond2lte/BCM4773 compatibility, firmware
    provenance, format and hash.
-   Samsung Android vendor binaries may depend on Bionic, Binder/HIDL,
    Android init and proprietary services. Audit their ELF interpreter
    and dependencies; do not assume they run natively on Fedora.
-   Do not fabricate GPS fixes. Mock, cached, IP, Wi-Fi or network
    coordinates are not physical GNSS.
-   Preserve recoverability. Bound hardware tests with timeouts and
    guaranteed cleanup. Do not weaken security controls.

## Kickstart work order

### 1. Establish facts

Confirm target model/build/kernel, inspect the whole `./gps/` handoff,
verify hashes, and inventory all payloads. Trace the existing BCM4773
SPI driver, `/dev/ttyBCM`, `/dev/bbd_patch`, `/dev/bbd_control`,
`/dev/bbd_sensor`, GPS power control and SSP interaction from actual
source and live evidence.

### 2. Acquire and audit the missing runtime

Find the exact stock SM-G975F GNSS files and firmware expected by this
board. The S10 vendor stack is known to reference `lhd`, `gpsd`, Samsung
GNSS HAL/service, `libwrappergps`, `gps.xml`, `lhd.conf` and init rules;
verify which are actually present. Generate ELF/ABI/dependency reports.
If proprietary payloads are absent, provide exact extraction
instructions from the user's own stock firmware and report the
blocker---do not substitute another device's files.

### 3. Implement the hardware path

Trace and implement the correct firmware-loader ABI, power sequencing,
BBD transport, packet framing, handshake, runtime lifecycle and GNSS
message parsing. Use only protocol details proven by source or captured
device evidence. Add bounded retries, timeouts, cancellation, recovery
and cleanup. Ensure one service owns the transport.

### 4. Implement Nuxel location integration

Use the existing location broker/provider architecture (inspect first;
likely Geoclue or an existing Nuxel service). Publish valid fixes with
source, timestamp, accuracy and fix state. Keep GNSS distinct from
network/IP/Wi-Fi/cached location. Add permissions, service packaging,
diagnostics and useful error states. Do not block boot.

### 5. Test the actual Maps app

Find our existing Maps app and trace its location request to the OS
provider. Fix any broken permission flow, provider selection,
hardcoded/demo coordinate, coordinate-order bug, stale cache, marker
rendering or "Locate me" behavior. Add clear UI states for permission
required, disabled, acquiring, no fix, fix acquired, stale and error.
Show source and accuracy. Network fallback must be explicit and
labelled.

First test Maps with a deterministic mock provider. Then test on the
real phone outdoors with cached data excluded. Require a fresh
receiver-originated fix, verify the marker against an independent
reference, move the phone and confirm the marker updates, then
disable/restart the service and verify correct state transitions. Keep
exact coordinates out of committed logs.

### 6. Tests and reflash readiness

Run unit, integration, packaging, Maps UI, failure/recovery and
live-device tests. Clearly label mock vs live results. Produce: - GPS
implementation/architecture document. - GPS test report with evidence. -
Exact reflash manifest with destination, owner, mode, labels and
SHA-256. - Blocker list and stock-firmware acquisition steps. - Safe
post-flash verification script. - Maps integration and regression tests.

Do not include speculative firmware or unnecessary kernel changes in the
reflash manifest. Determine whether a kernel/device-tree reflash is
actually required.

## Completion standard

Do not call GPS fixed because device nodes exist or a daemon runs. The
final pass requires: 1. Correct target firmware accepted by the
BCM4773/BBD loader. 2. Real receiver-originated GNSS data. 3. Fresh
outdoor physical fix with timestamp and accuracy. 4. Nuxel provider
publishes the fix correctly. 5. Existing Nuxel Maps displays that exact
fix and updates after physical movement. 6. Permission, service restart,
no-fix, stale and shutdown behavior all pass. 7. No regressions or
unsafe power state.

If a proprietary blob is still missing, implement and test everything
else that can safely be done, then report the exact missing artifact and
the exact next action. Never mark the system fully working when the
physical fix has not been proven.

**Start now. Inspect, implement, test, and report. Do not merely return
another plan. No flashing or rebooting without explicit approval.**
