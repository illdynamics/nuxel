# NUXEL S10+ — OPERATION SSP FIRST LIGHT: FINAL BREAKTHROUGH
## DeepSeek-V4-Pro-Thinking — Native BCM47752 Cold-Boot, Firmware Download, Sensor Streaming and Auto-Rotation Recovery

### MISSION DIRECTIVE

You are the lead Linux kernel, embedded firmware, SPI transport, reverse-engineering, sensor driver and Nuxel integration engineer.

Our Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos9820, is running Nuxel with a recovered, working boot chain and functioning TWRP recovery.

We have made substantial progress recovering the Broadcom BCM47752 sensor hub, but the physical accelerometer and gyroscope still do not stream.

**YOUR MISSION IS TO FINISH THE IMPLEMENTATION AND OBTAIN REAL PHYSICAL ACCELEROMETER AND GYROSCOPE READINGS ON NUXEL, THEN ENABLE RELIABLE AUTOMATIC ROTATION.**

You are authorized to:

- Inspect, debug, refactor and rewrite the native BBD/SSP implementation.
- Correct the firmware downloader and transport parser.
- Implement verified firmware-download completion handling.
- Reconstruct relevant Samsung vendor initialization behavior.
- Modify the SSP kernel driver where justified.
- Develop an early-boot firmware initialization service or kernel-assisted initialization mechanism.
- Correct SPI runtime power-management integration.
- Build and deploy native userspace components.
- Improve sensor decoding, calibration and orientation handling.
- Research and adapt compatible upstream source code.
- Introduce proper test infrastructure, diagnostics and recovery tooling.

Our requirement remains:

**ZERO ANDROID USERSPACE DEPENDENCIES IN THE FINAL NUXEL RUNTIME.**

You may analyze the original Samsung `lhd` implementation as a reference, but the production implementation must remain native Linux.

The goal is physical hardware functionality—not another report explaining why it might be impossible.

Work continuously through all safe engineering, implementation, build and verification stages. Do not stop at the first failed attempt or at successful compilation.

Do not misrepresent success. If the sole remaining step requires an unapproved hardware operation, complete all possible offline work and present the exact bounded trial for approval.

---

# PHASE 0 — READ AND RECONCILE THE CURRENT WORK

Read the latest report FIRST:

`reports/SSP-BBD-DOWNLOAD-STATEMACHINE-IMPLEMENTED-2026-11-21.md`

This document contains the previous agent's live evidence, kernel state and suspected cold-start timing problem.

Also read:

- `pwn/ssp.md`
- `pwn/ssp2.md`
- `pwn/ssp3.md`
- `pwn/ssp4.md`
- `kernel/s10plus/patches/0020-nuxel-ssp-hub-power-and-pm.patch`
- `kernel/s10plus/patches/0023-nuxel-ssp-native-bringup-reconciled.patch`
- `tools/s10plus/ssp-native/nuxel_bbd_flash.c`
- `tools/s10plus/ssp-native/nuxel_bbd_download.c`
- `tools/s10plus/ssp-native/nuxel_bbd_host.c`
- `tools/s10plus/ssp-native/tests/`
- `tools/s10plus/ssp-runtime/inspect_lhd_init.py`
- `tools/s10plus/ssp-runtime/replay_lhd_response.py`
- `tools/s10plus/ssp-runtime/check_protocol_replay.py`
- Existing `services/nuxel-orientation/` and bridge source.
- All SSP recovery, flashing and rollback reports.
- The currently deployed systemd services.
- Relevant current kernel source on the development host.

The provided repository snapshot did not include the latest `reports/` directory. Find the actual files in the original working checkout and inspect them directly.

The historical development repository is:

`/Users/wicked/x/nuxel`

The physical Nuxel phone has previously been reachable as:

`root@10.11.12.99`

Use the configured SSH identity without exposing private key contents.

Inspect the current working tree, uncommitted changes, build configuration and actual running kernel before making changes.

Do not overwrite previous work.

---

# PHASE 1 — PRESERVE THE RECOVERED BOOT CHAIN

Nuxel and TWRP were only recently recovered after a severe boot failure.

Treat the present bootable installation as a critical protected baseline.

Determine and preserve:

- Actual running kernel and build ID.
- Currently installed BOOT image.
- Matched DTB and DTBO.
- Recovery image.
- Known-good boot artifacts and hashes.
- Current kernel configuration.
- SSP patch application state.
- Working SSH/network configuration.
- Available host recovery route.

The previous agent reports that the reconciled SSP kernel is already deployed and functioning.

Verify this from the live device.

**Do not flash a new kernel merely to investigate a userspace protocol bug.**

Complete read-only diagnostics and offline tests first.

Any necessary boot-critical flash must use the validated matched Nuxel image set, an established rollback path and explicit approval.

Keep all camera and NFC experiments suspended.

---

# PHASE 2 — THE CURRENT HARDWARE FAILURE

The previous agent implemented a native BBD downloader and conducted bounded physical trials.

Reported observations:

```text
MCU register reads: 0xFFFFFFFF
SPI receive count: 0
HSI_ERROR_STATUS: 0xFF
Firmware initialization: NOT VERIFIED
Accelerometer streaming: NOT WORKING
Gyroscope streaming: NOT WORKING
Nuxel boot: HEALTHY
```

It reported that a warm reboot and an SPI runtime-resume attempt did not restore communication.

The previous conclusion was that the BCM47752 boot ROM was unavailable outside a cold power-on window.

**Treat this as the leading hypothesis, not an established exclusive root cause.**

These results prove that communication failed, but several possible causes remain:

- The MCU is not in its firmware-download state.
- The relevant rail never actually lost power.
- A shared regulator kept the hub powered.
- Reset and standby state are incorrect.
- SPI controller state was not fully restored.
- SPI clock, chip select, pinctrl or transport mode is incorrect.
- The host-request or response lines are incorrectly handled.
- IRQ delivery or ownership is wrong.
- The firmware-download window was missed.
- Firmware bytes were encoded or sequenced incorrectly.
- Another process owns or interferes with the BBD transport.
- The MCU is being reset or queried at the wrong point in startup.

Your job is to distinguish these explanations using actual source and saved hardware evidence.

Do not treat repeated all-ones reads as sufficient proof of any particular one.

---

# PHASE 3 — FIX THE EXISTING DOWNLOADER BEFORE ANOTHER HARDWARE TRIAL

Inspect:

`tools/s10plus/ssp-native/nuxel_bbd_flash.c`

I identified several correctness issues in the provided source that must be resolved.

## Issue 1 — False-success process exit

The current downloader can reach `return 0` even when the hub never replies or the firmware download fails.

Fix this.

Define meaningful, distinguishable result states such as:

- Firmware identity invalid.
- Transport unavailable.
- ROM handshake timeout.
- Invalid or unrelated response.
- Transfer rejected.
- Transfer incomplete.
- Application-start confirmation missing.
- Firmware version verification failed.
- Genuine verified success.

Exit zero only when the required success conditions actually pass.

## Issue 2 — Arbitrary bytes interpreted as a valid response

The current code sets `reply=true` when `drain_sensor()` returns any positive byte count.

This is insufficient.

Implement proper receive processing:

- TL frame boundaries.
- Escape decoding.
- Length validation.
- CRC validation.
- Reliable sequence matching.
- Correct RPC decoding.
- Expected response identifiers.
- Stale or unrelated packet rejection.
- ACK/NACK classification.
- Transport ACK versus RPC completion.
- Explicit timeout and cancellation behavior.

Reuse the existing verified native decoder rather than implementing an unrelated second parser.

Do not assume every packet on `/dev/bbd_sensor` came from the boot ROM.

## Issue 3 — Unverified firmware transfer completion

The current downloader sends memory-write messages without independently proving every operation completed.

It can continue to application-start commands after a partial transfer.

Correct this using the source-verified vendor protocol.

Require completion acknowledgment appropriate to each operation.

Handle interrupted downloads, rejected writes and session failure.

Do not start the firmware application after an incomplete transfer.

## Issue 4 — Firmware container interpretation

The existing documentation describes patch record tags F0–F5, including F1 memory-write records with destination addresses.

The new downloader currently treats the decoded blob as a contiguous byte stream written sequentially from `PatchAddress`.

Determine whether that is actually equivalent to the original vendor implementation.

Trace the complete stock firmware parser and interpreter.

Establish whether the correct behavior is:

- Contiguous memory loading.
- Record-by-record memory writes.
- Address changes between records.
- Additional commands or metadata operations.
- Separate entry-point information.
- A hybrid of these behaviors.

Do not assume `PatchAddress` is both the first data destination and executable entry point.

Use the actual pinned Samsung implementation to establish the correct interpretation.

## Issue 5 — Startup and readiness verification

The existing code currently accepts any subsequent bytes as proof that firmware is up.

Do not do that.

Require source-backed proof of the expected startup response and firmware revision.

Do not emit `ESW:READY` until the appropriate state-machine transition has completed.

Do not claim successful firmware loading based only on bytes transmitted.

## Issue 6 — Cleanup and resource ownership

Guarantee correct cleanup on:

- Timeout.
- Write failure.
- Unexpected response.
- Transfer cancellation.
- Application-start failure.
- Interrupted execution.
- Hub disappearance.
- Service restart.

Restore transport ownership and BBD control state consistently.

Avoid leaked file descriptors, wake locks, duplicate initialization attempts and stale ready flags.

---

# PHASE 4 — USE THE VERIFIED SAMSUNG PROTOCOL AS THE SOURCE OF TRUTH

The previous agent recovered these RPC definitions from the matched `lhd` implementation:

| Operation | RPC ID | Known contract |
|---|---|---|
| GetVersion | 0 | Empty request body |
| MemoryWrite | 5 | Little-endian destination, count and data |
| StartScratchApp | 46 | Little-endian entry address |
| ServiceStart | 55 | Entry address and additional fields |
| Autobaud | Transport stage | Pinned vendor behavior |

The matching `lhd` binary is identified by SHA-256:

`6362e80d1f2ae37c76dd5f468bf08abacb89e1c2d2b80976d5b1c3abbf761dfe`

The firmware patch metadata previously established:

```text
ASIC:         BCM47752
ASIC version: 0x004775B0
Blob length:  438895 bytes
Patch addr:   0x00800161
Blob CRC32:   0x93D35BB4
```

Reverify these from the original files.

Use the existing Unicorn replay implementation and static ELF inspector to confirm the state transitions.

Pay special attention to:

- Session initialization.
- ROM state.
- Download state.
- Reliable transport behavior.
- Memory-write responses.
- Firmware start conditions.
- Version comparison.
- DONE transitions.
- Error handling.
- Clean transition into the normal SSP runtime.

Reconstruct the missing behavior; do not invent responses or successful transitions.

Build deterministic offline fixtures from real, documented protocol behavior.

---

# PHASE 5 — RESOLVE THE COLD-START HARDWARE BOUNDARY

This is the critical hardware investigation.

We need to determine how the original Samsung implementation brings the BCM47752 into a state where the AP can communicate with its boot ROM.

Study:

- Original Samsung kernel initialization order.
- BCM47752-specific BBD driver.
- Exynos SPI host initialization.
- SSP device probe.
- Relevant regulator ownership.
- Device-tree power dependencies.
- Reset and standby behavior.
- GPIO and IRQ ownership.
- Runtime PM.
- The original vendor `lhd` startup ordering.
- Recovered boot and service dependencies.
- Firmware-download readiness checks.

Do not rely on generic Broadcom chip assumptions.

## Critical reconciled-kernel finding

The repository's `0023-nuxel-ssp-native-bringup-reconciled.patch` already contains a fallback that calls `regulator_disable()` and `regulator_enable()` after a failed `initialize_mcu()`.

Determine whether this code path was reached during the previous trial.

Check whether the actual regulator voltage changed or whether only the software enable reference changed.

Check for other regulator consumers and shared GNSS/SSP dependencies.

A regulator reported as enabled does not prove the MCU is awake, and requesting disable does not prove the physical rail fell.

**Do not implement another independent power-cycle mechanism on top of the existing kernel fallback without reconciling ownership and state.**

Do not manipulate shared power or reset controls through raw, undocumented operations.

Any proposed physical rail/reset experiment must be reviewed against the device-specific driver and presented for explicit approval before execution.

## Compare alternative initialization architectures

Evaluate three possibilities.

### A — Native early-userspace firmware initializer

Initialize the hub through a dedicated Nuxel service once the required hardware interfaces are available.

Use systemd ordering and device dependencies only where they actually provide the necessary timing.

Do not assume `After=` is enough to preserve an early MCU boot-ROM window.

### B — Initramfs-stage initialization

If the hub is ready before the real root filesystem and loses its download window by the time ordinary services start, investigate initializing it from the Nuxel initramfs.

Determine whether the required device interfaces and firmware are available at that stage.

Avoid unnecessarily expanding the trusted early-boot environment.

### C — Kernel-coordinated cold-start

If the boot ROM can only be entered through a tightly coordinated hardware startup sequence, implement the minimal device-specific kernel support and native userspace coordination needed.

Maintain correct regulator, reset, IRQ and runtime-PM ownership.

Use the kernel driver model rather than ad hoc userspace power toggles.

Avoid any duplicate or competing reset sequences.

## Architecture decision

Choose the architecture that the source and measurements support.

Implement the minimum complete solution.

The key requirement is:

**Firmware download must begin when the MCU is genuinely ready to receive it, not merely when a systemd unit happens to start.**

Produce timestamps and actual state evidence for the selected initialization events.

---

# PHASE 6 — ESTABLISH ONE AUTHORITATIVE SSP OWNER

Review every process and kernel interface that participates in initialization.

Inspect:

- Native BBD downloader.
- Existing BBD host tool.
- Nuxel SSP bridge.
- Nuxel orientation daemon.
- Kernel BBD peer.
- SSP firmware-loading path.
- Any GNSS-related shared services.
- Existing systemd units.

Ensure there is exactly one authoritative firmware initialization state machine.

Avoid:

- Multiple daemons opening the same transport competitively.
- Duplicate boot-ROM handshakes.
- Repeated uncoordinated firmware downloads.
- Premature `ESW:READY`.
- Competing reset handlers.
- Competing IRQ enable/disable operations.
- Duplicate regulator ownership.
- Unbounded service restart loops.

Design a coherent state machine such as:

```text
UNAVAILABLE
    ↓
HARDWARE_READY
    ↓
BOOT_ROM_IDENTIFIED
    ↓
DOWNLOAD_SESSION_ESTABLISHED
    ↓
FIRMWARE_TRANSFER_CONFIRMED
    ↓
APPLICATION_START_CONFIRMED
    ↓
SSP_HANDSHAKE_COMPLETE
    ↓
SENSORS_ENUMERATED
    ↓
SENSORS_STREAMING
    ↓
READY
```

Each transition must be supported by evidence from the hardware or verified protocol.

On failure, transition to a truthful, bounded error state.

Never fabricate a successful state to satisfy downstream services.

---

# PHASE 7 — RECONCILE THE SSP KERNEL BRING-UP ORDER

Inspect the currently active `nuxel_ssp_bringup_hw()` implementation.

Previous source shows:

- SSP data registered during probe.
- Native BBD peer setup.
- `initialize_mcu()` called by bring-up.
- An attempted regulator recovery after failure.
- A second `initialize_mcu()` attempt.
- Failure-state cleanup.

But the vendor design expects the firmware-loading and application-start sequence to be coordinated with MCU initialization.

Determine the exact required ordering.

Ensure that:

1. The kernel and native downloader agree on transport ownership.
2. The boot-ROM transaction occurs at the correct lifecycle stage.
3. `initialize_mcu()` is not called prematurely.
4. The vendor-compatible firmware startup has genuinely completed.
5. Runtime PM cannot suspend the SPI controller during a required transaction.
6. IRQ state and wake configuration are balanced.
7. Error recovery does not recursively reset the MCU.
8. Failure does not permanently poison subsequent clean boot attempts.
9. SSP readiness is propagated only after the legitimate handshake.
10. Sensor enable is attempted only after successful sensor enumeration.

Review kernel locking and concurrency carefully.

Keep existing working SSP code where possible.

Do not apply unrelated kernel patches.

---

# PHASE 8 — BUILD A COMPLETE OFFLINE TEST HARNESS

Before another physical trial, build exhaustive host-side tests for:

- Firmware identity and integrity.
- Firmware container parsing.
- RPC field encoding.
- TL payload length.
- CRC validation.
- Escaping.
- Reliable sequence handling.
- ACK and NACK behavior.
- Memory-write completion.
- Interrupted transfer.
- Short reads and writes.
- Unrelated packets.
- Duplicate responses.
- Late responses.
- Startup failure.
- Firmware version mismatch.
- State-machine cancellation.
- Resource cleanup.
- Service restart behavior.

Build a simulated ROM endpoint using source-verified fixtures.

Test the entire sequence end-to-end in simulation.

Verify that every failure case returns a nonzero status and never emits `ESW:READY`.

Cross-compile with strict warnings.

Run sanitizers where supported.

Review buffer sizes, integer overflow, response parsing, allocations and cleanup.

The offline tests cannot prove physical ROM compatibility, but they should eliminate avoidable software defects before another hardware attempt.

---

# PHASE 9 — CONTROLLED PHYSICAL FIRST LIGHT

Once the software implementation and architecture are justified, prepare a bounded physical validation.

Use the existing Nuxel SSH connection and proper deployment scripts.

Begin with read-only verification.

If a firmware download, hardware restart, rail change or kernel replacement is necessary, present a preflight describing:

- The exact implementation and source revision.
- The intended hardware state transitions.
- Expected transport responses.
- Known firmware identity.
- Device-specific safety assumptions.
- Abort conditions.
- Maximum attempts.
- Log capture.
- Current healthy boot baseline.
- Recovery/rollback.
- Impact on shared GNSS hardware.

Obtain explicit approval for that physical action.

Do not turn a failed attempt into unlimited power/reset cycling.

During the approved trial, record:

- Hardware initialization timestamps.
- SPI activity and controller state.
- Relevant IRQ activity.
- Boot-ROM response validation.
- Firmware transfer progress.
- Transfer completion.
- Firmware start confirmation.
- Firmware version.
- SSP handshake.
- Sensor scanning results.

A successful host write alone is not enough.

**FIRST REQUIRED MILESTONE: VERIFIED TWO-WAY COMMUNICATION WITH THE PHYSICAL BCM47752.**

**SECOND MILESTONE: VERIFIED SSP APPLICATION RUNNING.**

**THIRD MILESTONE: VERIFIED PHYSICAL SENSOR STREAMING.**

If a trial fails, classify the exact failed state and correct the source before proposing another.

---

# PHASE 10 — BRING UP THE REAL ACCELEROMETER AND GYROSCOPE

Once the MCU firmware is running, integrate the normal SSP runtime.

Do not stop at `GetVersion`.

Implement and verify:

- MCU/SSP handshake.
- Sensor identity and scanning information.
- Accelerometer enable.
- Gyroscope enable.
- Correct sensor sampling intervals.
- Kernel event routing.
- Valid sensor sample decoding.
- Timestamps.
- Axis mapping.
- Units and scaling.
- Calibration.
- Clean disable/enable behavior.
- Error handling.

The phone must produce genuine physical motion data.

Test:

- Stationary portrait.
- Landscape left.
- Landscape right.
- Reverse portrait.
- Face-up.
- Face-down.
- Controlled physical movement.

The accelerometer should respond coherently to changes in gravity direction.

The gyro should respond coherently to physical rotation.

Do not replace missing measurements with synthetic samples.

Do not mark a sensor working merely because it appears in a device list.

Acceptance requires actual hardware values that change with real motion.

Required results:

`SSP_MCU_READY = PASS`

`ACCELEROMETER_PHYSICAL_STREAMING = PASS`

`GYROSCOPE_PHYSICAL_STREAMING = PASS`

---

# PHASE 11 — COMPLETE AUTOMATIC ROTATION

After real accelerometer measurements work, integrate them into the existing Nuxel orientation stack.

Do not replace the existing orientation daemon unnecessarily.

Maintain all seven established modes:

- auto
- auto-portrait
- auto-landscape
- portrait
- landscape
- reverse-portrait
- reverse-landscape

Complete:

- Correct gravity-axis mapping for S10+.
- Rotation hysteresis.
- Flat-phone handling.
- Debouncing.
- Orientation cooldown.
- Screen transform.
- Touch-coordinate transformation.
- Native GTK application layout changes.
- Nuxel PWA responsiveness.
- Lock-screen rotation behavior.
- Rotation lock from Settings and Quick Settings.
- Correct restoration after application closure.
- Persistent mode configuration.

Keep manual rotation working.

Prevent stale or invalid sensor samples from triggering screen rotation.

If the sensor service becomes unavailable, report the fault and retain a safe screen orientation.

---

# PHASE 12 — MAKE THE FIX PERMANENT

A manually successful initialization is not enough.

The finished system must bring up the sensor hub automatically.

Verify:

- Normal cold boot.
- Normal warm reboot.
- SSP initialization without manually running a downloader.
- Sensor streaming after startup.
- Recovery after suspend/resume.
- Correct transport ownership.
- No duplicate initialization.
- No unbounded watchdog or reset loop.
- No unintended GNSS regression.
- No Wi-Fi or SSH regression.
- No display or touchscreen regression.
- No camera or NFC changes.
- No kernel crash.
- No bootloop.
- No excessive background CPU activity.

Test that the service's startup ordering is genuinely sufficient across repeated boots.

If successful initialization depends on a physical cold-start event, document and correctly integrate that dependency rather than hiding it with an unreliable delay.

---

# PHASE 13 — REQUIRED FINAL ENGINEERING OUTPUT

Create or update:

`reports/SSP-BBD-DOWNLOAD-STATEMACHINE-IMPLEMENTED-2026-11-21.md`

`reports/SSP-COLD-BOOT-ROOT-CAUSE.md`

`reports/SSP-NATIVE-FIRMWARE-DOWNLOADER-FINAL.md`

`reports/SSP-PHYSICAL-FIRST-LIGHT.md`

`reports/SSP-ACCEL-GYRO-ACCEPTANCE.md`

`reports/NUXEL-AUTO-ROTATION-ACCEPTANCE.md`

`reports/SSP-BOOT-RECOVERY-AND-ROLLBACK.md`

Include:

- Exact source revisions.
- Root cause and supporting evidence.
- Architecture changes.
- Firmware provenance.
- Build results.
- Offline test outcomes.
- Hardware test outcomes.
- Real accelerometer and gyro data.
- Systemd integration.
- Rotation test results.
- Cold-boot verification.
- Known remaining limitations.

Update source documentation, deployment scripts, service definitions, relevant component state, and changelog.

Create clean logical commits.

Do not commit proprietary firmware or device-unique information into public Git history.

---

# FINAL ACCEPTANCE CONTRACT

Your ultimate goal is a **fully working native Nuxel SSP sensor stack**.

The complete mission requires all of the following:

| Component | Required |
|---|---|
| Verified physical ROM communication | PASS |
| Firmware transfer integrity | PASS |
| Firmware application start | PASS |
| SSP MCU handshake | PASS |
| Accelerometer enabled | PASS |
| Gyroscope enabled | PASS |
| Actual motion-dependent samples | PASS |
| Proper units and axis mapping | PASS |
| Sensor streaming through native Linux | PASS |
| Nuxel automatic rotation | PASS |
| Seven orientation modes preserved | PASS |
| Touch/display synchronization | PASS |
| Settings integration | PASS |
| Working normal reboot | PASS |
| Working cold boot | PASS |
| Working suspend/resume | PASS |
| No new bootloop or hardware regression | PASS |

**DO NOT CLAIM SUCCESS BEFORE THE HARDWARE MEETS THESE CONDITIONS.**

Do not stop after a firmware checksum passes.

Do not stop after a download command returns zero.

Do not stop after the MCU responds once.

Do not stop after synthetic sensor tests.

Do not stop after rotation works with fabricated input.

Continue implementing and fixing all safely actionable failures until actual physical sensors work.

If a hardware operation requires new authorization, finish all possible offline work and present the exact next action. If a necessary external dependency is unavailable, report it precisely instead of inventing success.

---

# IMMEDIATE EXECUTION ORDER

1. Read the exact November 21 state-machine report from the live working checkout.
2. Confirm the phone and recovered kernel remain healthy.
3. Fix `nuxel_bbd_flash.c` so it cannot report false success.
4. Implement full receive parsing and operation-level completion verification.
5. Verify the F0–F5 firmware container semantics against the original Samsung implementation.
6. Inspect the existing kernel regulator-recovery code and determine whether the prior trial reached it.
7. Establish the actual cause of the all-ones SPI reads and missing receive activity.
8. Reconstruct the correct cold-start initialization ordering.
9. Implement the smallest safe native early-boot or kernel-coordinated solution.
10. Complete comprehensive offline testing.
11. Prepare and execute only explicitly approved bounded physical operations.
12. Verify MCU firmware startup and SSP handshake.
13. Enable actual accelerometer and gyroscope streaming.
14. Integrate automatic screen rotation.
15. Verify reboot and suspend/resume persistence.
16. Deliver the working implementation, logs, tests and reproducible build.

**STOP RE-INVESTIGATING THINGS WE HAVE ALREADY SOLVED.**

**STOP TREATING SUCCESSFUL TRANSMISSION AS SUCCESSFUL FIRMWARE EXECUTION.**

**FOCUS ON THE REMAINING HARDWARE COMMUNICATION AND STARTUP BLOCKER.**

The next breakthrough is not another simulated RPC transcript.

**IT IS THE FIRST VALID PHYSICAL RESPONSE FROM THE BCM47752, FOLLOWED BY REAL MOTION SENSOR DATA.**

BEGIN OPERATION SSP FIRST LIGHT — FINAL BREAKTHROUGH.
