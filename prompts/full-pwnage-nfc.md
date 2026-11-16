

# FULL PWNAGE — NFC Implementation, Combined Kernel Reflash & Physical Validation

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**Platform:** Exynos 9820 / `universal9820`  
**OS:** Nuxel Linux — Fedora 43 ARM64  
**Current kernel baseline:** Linux 4.14.253  
**Primary objective:** Get the phone's physical NFC hardware working in Nuxel, including kernel, firmware, userspace, service integration and real tag testing.

---

## 0. Mission and completion criteria

This is an implementation task, not a research-only exercise.

You must investigate the existing Nuxel repository, identify the actual NFC hardware and its requirements, implement the kernel and userspace support, build a combined boot image, perform the authorised TWRP reflash, recover from failed boots if necessary, and finish by physically testing NFC.

**The desired outcome is one reflash that includes both:**

1. The new NFC kernel implementation.
2. The existing USB networking implementation described in `PWNAGE-107000-USBNET-REPORT.md`.

Do not regress existing working hardware or discard the USBNET work.

The task is only complete when all of the following are true:

- The device boots successfully into Nuxel using the new kernel.
- The expected kernel is running and the NFC driver successfully binds to the actual controller.
- The controller can be powered on and off correctly.
- Required firmware, reset and initialisation sequences work.
- Nuxel userspace can discover physical NFC tags.
- Real NDEF reading works.
- Real NDEF writing works on an appropriate expendable writable tag, with explicit test confirmation.
- The NFC implementation survives reboot.
- USB networking remains present in the combined kernel and passes its existing regression tests.
- Documentation accurately distinguishes implemented, tested, partially tested and unsupported functionality.

Do not mark NFC as working merely because a kernel option is enabled, a module exists, or a device node appears.

---

## 1. Initial operating agreement — TWRP and reflash

**The operator will manually boot the phone into TWRP before launching this task.**

Once the agent begins, verify that the phone is actually connected to TWRP and that the connected device is the intended Galaxy S10+.

The operator explicitly authorises the agent to perform the necessary boot-image reflash and reboot as part of this task, subject to the safeguards below.

### Expected boot behaviour

The expected sequence is:

1. Operator manually starts the phone in TWRP.
2. Agent performs preflight checks and builds the combined image.
3. Agent verifies the image and backs up the existing boot image.
4. Agent flashes the verified image to the correct boot partition.
5. Agent reboots the phone.
6. The phone boots into Nuxel.
7. Agent verifies the new kernel and continues with NFC userspace and physical testing.

**If the phone returns to TWRP instead of booting Nuxel, treat that as a failed boot.**

A boot hang, reset loop, or return to TWRP is not success. Do not report the new kernel as operational.

### Reflash safety rules

Before writing anything:

- Verify device identity and model.
- Verify the active recovery environment and device connectivity.
- Inspect the actual partition layout and determine the correct boot partition for this device.
- Inspect the existing boot image format, header, DTB arrangement and ramdisk.
- Verify that the image being flashed is built for this exact device.
- Create and verify a backup of the existing known-good boot image.
- Record its size and SHA-256 checksum.
- Verify that a viable TWRP recovery route remains available.
- Verify the candidate image checksum immediately before flashing.
- Record the exact command, target partition, image checksum and result.

**Only flash the verified boot image to the verified boot partition.**

Never write to:

- EFS
- Modem/baseband
- Recovery
- Bootloader
- PIT
- Vendor or system partitions
- Any unrelated partition

Do not alter partition tables, bootloader state, encryption, FRP or KG state.

Do not perform a factory reset, format data, wipe user data or remove unrelated partitions.

Do not assume that a partition named `boot` is correct without inspecting the actual device layout.

### Failure and recovery loop

If the device does not boot into Nuxel:

1. Treat the attempt as failed.
2. Preserve the recovery environment.
3. Collect whatever diagnostics are available:
   - TWRP logs
   - Recovery console output
   - Kernel logs
   - `pstore` / `ramoops`, if available
   - Bootloader reset or failure information
   - Image header and DTB metadata
   - Ramdisk and init diagnostics
4. Compare the failed image against the last known-good image.
5. Identify a plausible root cause before rebuilding.
6. Correct the issue.
7. Rebuild the combined image.
8. Re-run all image gates.
9. Verify the checksum.
10. Flash again using the same guarded procedure.

Allow a maximum of **three total flash attempts** for this task. If the device remains unable to boot after three attempts, stop and report the evidence, current recovery state and safest recovery options. Do not blindly repeat the same flash.

If recovery connectivity or the ability to restore the known-good boot image becomes uncertain, stop immediately and request operator intervention.

A return to TWRP is a failure even if TWRP itself works perfectly.

### Confirming a successful boot

Do not rely exclusively on SSH being available immediately after reboot.

Use available methods to establish that Nuxel has genuinely booted:

- Expected kernel release and build identity.
- Nuxel userspace/init has started.
- Expected root filesystem and systemd state.
- Expected hardware and device tree are active.
- SSH or another Nuxel management interface becomes reachable when networking is ready.

Only after this confirmation may the attempt be classified as a successful boot.

---

## 2. Repository reconnaissance — inspect before changing

Start by inspecting the complete repository and the current working tree.

Do not assume earlier reports describe the current state accurately. Verify their claims against the actual files.

At minimum inspect:

- Repository status and current branch.
- Existing kernel source and build scripts.
- Kernel configuration and defconfig.
- Device tree sources and compiled DTBs.
- Existing Samsung device-specific patches.
- Boot image construction scripts.
- Existing ramdisk and DTB provenance.
- Existing hardware abstraction and service structure.
- Settings and Quick Settings architecture.
- Hardware documentation and previous investigation reports.
- Existing NFC-related source, patches, configuration and userspace code.

Read the complete contents of:

`PWNAGE-107000-USBNET-REPORT.md`

Also inspect the existing patch:

`0007-sec-nfc-class-name.patch`

Do not assume this patch implements NFC. Determine exactly what it changes, whether it is already applied, whether it is relevant to the actual controller, and whether it is safe to retain.

Search the repository and kernel source for:

- `CONFIG_NFC`
- `CONFIG_NFC_NCI`
- `CONFIG_NFC_NXP`
- `CONFIG_NFC_PN544`
- `CONFIG_NFC_PN533`
- Samsung NFC drivers
- NCI core
- I2C/SPI controller drivers
- GPIO and regulator definitions
- NFC device tree nodes
- NFC firmware loading
- IRQ and wakeup handling
- Vendor-specific NFC implementations

These are investigation targets, not instructions to enable every option.

Produce a short initial inventory identifying:

1. Existing NFC implementation.
2. Missing kernel support.
3. Actual hardware identity, if established.
4. Existing userspace support.
5. Existing USBNET implementation and its build integration.
6. The precise changes required for a combined image.

---

## 3. Identify the actual NFC controller

Do not guess the controller.

Determine the physical NFC controller fitted to this exact Galaxy S10+ variant using evidence from as many sources as available:

- Device tree.
- Stock Samsung kernel source.
- Stock device configuration.
- Kernel driver source.
- Existing Nuxel hardware information.
- Board-specific GPIO and regulator definitions.
- Known hardware identifiers and controller strings.
- Available device logs or sysfs information.
- Existing firmware files and their metadata.

Investigate whether the hardware is based on NXP, Samsung-specific NFC hardware, ST or another controller. Do not assume a PN553, PN80T or any other chip until the evidence supports it.

Determine:

- Controller model and revision.
- Bus interface.
- IRQ GPIO.
- Enable/VEN GPIO.
- Firmware/download GPIO, if applicable.
- Required regulators and voltage rails.
- Pin control and reset requirements.
- Clock requirements.
- Wakeup behaviour.
- Firmware-loading requirements.
- Secure element availability and interface, if any.
- Supported NFC protocols and tag technologies.

If the exact controller cannot be established, document the evidence and uncertainty. Do not implement a guessed driver configuration.

---

## 4. Kernel implementation

Implement the correct driver and dependencies for the identified controller.

Investigate and implement the necessary combination of:

- Linux NFC core.
- NCI support, if applicable.
- Correct controller driver.
- Required I2C/SPI support.
- GPIO support.
- Regulator support.
- Pinctrl support.
- Interrupt support.
- Firmware loading.
- Device tree configuration.
- Wakeup and power management.
- Required vendor-specific integration.

Do not enable unrelated drivers simply to make configuration tests pass.

### Device tree

Verify the actual hardware wiring and add or correct the relevant device tree node.

Every GPIO, regulator, interrupt and pinctrl reference must be grounded in the device's real board configuration.

Do not invent GPIO numbers.

Check:

- Correct compatible string.
- Correct bus address.
- Correct interrupt polarity and trigger.
- Correct GPIO polarity.
- Correct regulator names and voltages.
- Correct pinctrl state.
- Correct wakeup configuration.
- Correct reset and firmware-download sequencing.

### Driver behaviour

The driver must:

- Probe successfully.
- Bind to the actual controller.
- Initialise hardware safely.
- Handle reset and power transitions.
- Handle IRQs correctly.
- Support required firmware loading.
- Expose the interface expected by the selected userspace stack.
- Shut down cleanly.
- Recover from controller errors without leaving the hardware in an unusable state.

Inspect error handling and resource cleanup carefully.

Do not leave GPIOs, regulators, IRQs or controller state in an inconsistent condition after failed initialisation.

### Kernel configuration

Make the required options persistent in the actual Nuxel kernel configuration.

Do not rely on temporary configuration changes that are lost during the next build.

Record the final configuration and verify the resulting kernel image contains the expected driver and dependencies.

---

## 5. Preserve and integrate USBNET

The NFC image must retain the existing USB networking work.

The reference report is:

`PWNAGE-107000-USBNET-REPORT.md`

The existing candidate is:

`build/out/s10plus/debug-candidates/p107000-usbnet/boot-usbnet-ecm-ncm-fix.img`

Reported image details:

- Size: 54,593,536 bytes.
- SHA-256: `4501750f5800538cd85fc6b3d314fef4350ceac62e29ffb5057450e63ee702c8`
- Gate: PASS.
- Physical flash: not yet performed.
- Physical USB networking: not yet validated.

The USBNET kernel work includes:

- Fix to NCM teardown in `f_ncm.c` under `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE`.
- Protection against invalid/double `misc_deregister()` through registered-state tracking.
- ECM support.
- ECM-subset support.
- EEM support.
- NAT/masquerade support.
- Cross-build compatibility fixes involving `elf.h` and `asm/types.h`.

The userspace work includes:

- `nuxel-usb-net-helper.sh`
- USB networking monitor.
- systemd persistence and restore.
- `usb_tethering.py` REST/RPC provider.
- Quick Settings USB Net tile.
- Settings USB network tab.

Previously reported tests:

- `test_tri_link.py`: 51 passed.
- `test_usb_net_provider.py`: 5 passed.
- Kernel config gate: PASS.
- Boot image gate: PASS.
- Shell and JavaScript syntax: clean.

### Required integration

Build NFC and USBNET together from a coherent source tree.

Do not simply flash the old USBNET candidate and claim NFC is included.

Do not silently replace or discard the NCM teardown fix.

Verify that the final kernel still contains:

- The NCM teardown fix.
- ECM.
- ECM-subset.
- EEM.
- Required USB gadget support.
- Required NAT/masquerade support.

Re-run the USBNET configuration and regression tests against the final combined tree.

If NFC changes conflict with USBNET changes, resolve the conflict and document it. Do not remove functionality to make the build pass.

If the two implementations cannot safely coexist, explain the exact technical blocker and stop before flashing. The desired result remains one combined reflash.

### USBNET physical validation

The existing report explicitly states that physical USB networking has not yet been tested.

After the successful Nuxel boot, test the actual USB link where practical:

- USB gadget enumeration.
- ECM interface creation.
- Host-side network interface.
- IP assignment.
- Bidirectional connectivity.
- DNS and routing where configured.
- NCM behaviour if exposed.
- Repeated disconnect/reconnect.
- Nuxel reboot and persistence.

macOS may require a suitable CDC-ECM driver or configuration. Do not interpret a missing macOS interface as proof that the phone's gadget implementation is broken. Test with a Linux host if necessary.

---

## 6. Boot image construction

Build one final boot image containing the combined NFC and USBNET kernel.

Use the existing proven image construction workflow where it remains valid.

Do not casually change the ramdisk, DTB, boot image header or command line.

Verify:

- Correct device target.
- Correct kernel architecture.
- Correct kernel image format.
- Correct boot image header/version.
- Correct DTB and DTBO arrangement.
- Correct ramdisk.
- Correct kernel command line.
- Correct page size and offsets, where relevant.
- Correct image size and partition compatibility.
- Correct signing/verification requirements for the existing device setup.

Do not assume that the previous USBNET image's ramdisk and DTB can be reused without checking their provenance and compatibility with the combined build.

Produce:

- Final image.
- Build manifest.
- Kernel configuration snapshot.
- Patch list.
- Image metadata.
- SHA-256 checksum.
- Gate/test report.

The final image must pass the repository's relevant build and image gates before flashing.

---

## 7. NFC userspace implementation

Nuxel is Linux-based and does not use the Android framework as its application platform.

Do not introduce a complete Android NFC framework unless there is a compelling, demonstrated technical requirement.

Evaluate the native Linux NFC stack first.

Investigate the suitability of:

- Kernel NFC/NCI interface.
- `neard`, if compatible with the controller and chosen kernel interface.
- `libnfc`, if it supports the identified controller.
- A small native Nuxel NFC daemon/service.
- Existing Nuxel hardware-service and D-Bus architecture.

Choose the simplest maintainable solution that genuinely supports the controller.

Do not add several competing NFC stacks.

### Service requirements

Implement a service that can:

- Detect controller availability.
- Initialise the controller.
- Report NFC enabled/disabled state.
- Start and stop scanning.
- Discover nearby tags.
- Identify supported tag technologies.
- Read supported NDEF records.
- Write supported NDEF records with user confirmation.
- Report errors clearly.
- Recover from removable tags and controller resets.
- Shut down safely.
- Start reliably after reboot.

Use systemd integration consistent with Nuxel's existing conventions.

### Permissions and security

Apply least-privilege access to the NFC device interface.

Do not expose unrestricted raw device access to every application.

Do not automatically open URLs from discovered tags.

Do not silently write to tags.

Require explicit user confirmation before writing data or initiating an action based on tag contents.

Avoid logging private tag payloads unnecessarily.

Treat all tag contents as untrusted input.

---

## 8. Nuxel UI integration

Integrate NFC into the existing Nuxel settings and hardware architecture.

Provide a useful user-facing NFC control, including:

- NFC availability.
- NFC enabled/disabled state.
- Enable/disable control, if supported by the controller.
- Scanning state.
- Tag discovered notification or view.
- Tag technology and supported information.
- NDEF content display.
- Explicit write workflow.
- Clear errors for unavailable hardware, firmware failure or unsupported tags.

Follow existing Nuxel UI conventions.

Do not add a decorative Quick Settings tile that does not control real hardware.

If a Quick Settings tile is appropriate, it must be connected to the actual service and accurately reflect the hardware state.

Do not claim support for card emulation, payment, transit cards, secure element access or Android Beam-like functionality unless the hardware, kernel, security environment and userspace implementation demonstrably support it.

---

## 9. Physical NFC validation

Physical testing is mandatory.

Once the new kernel boots successfully and userspace is integrated, test the actual NFC controller and real tags.

### Stage A — controller

Verify:

- Driver probe.
- Driver binding.
- Correct device interface.
- Controller power-on.
- Controller power-off.
- Reset.
- Firmware loading, if required.
- NCI initialisation, if applicable.
- IRQ activity.
- No repeated reset or probe errors.

Capture relevant logs.

### Stage B — tag discovery

Use real NFC tags.

Test at least:

- A known NFC Forum-compatible tag.
- A writable NDEF tag.
- A tag with an existing NDEF record.
- A tag with no NDEF data, where available.

Verify discovery and identify the actual technology and protocol.

Do not infer tag discovery merely from an IRQ firing.

### Stage C — reading

Read real tag data.

Test:

- UID or identifier where exposed and permitted.
- Tag technology.
- NDEF record type.
- Text record.
- URI record.
- Empty or unsupported tag.
- Malformed or unsupported NDEF data, where safe.

Display results correctly in Nuxel.

Do not automatically launch discovered URIs.

### Stage D — writing

Use an expendable writable tag.

Ask for explicit confirmation before writing.

Write a simple text NDEF record and read it back.

If supported, also test a URI record, without automatically opening it.

Verify the read-back data matches what was written.

Test a read-only or write-protected tag and report the expected error cleanly.

Never overwrite a tag containing valuable data.

### Stage E — reliability

Test:

- Repeated tag presentation/removal.
- Repeated scans.
- Enable/disable cycles.
- Service restart.
- Phone reboot.
- Controller recovery after an error, if possible.

Record any limitations.

---

## 10. Required automated tests and gates

Run all relevant existing project tests, not just newly written NFC tests.

At minimum:

- Kernel configuration validation.
- Kernel build.
- Device tree validation.
- Driver binding checks.
- NFC service tests.
- NFC API/provider tests.
- UI syntax/build tests.
- systemd unit validation.
- Boot image gate.
- USBNET regression tests.
- Shell syntax checks.
- Relevant integration tests.

Add automated tests for failure cases:

- Controller absent.
- Driver unavailable.
- Firmware missing.
- Initialisation failure.
- Permission denied.
- Tag timeout.
- Unsupported tag.
- Read failure.
- Write-protected tag.
- Service restart.
- Repeated power cycles.

Clearly distinguish automated simulation from physical hardware tests.

---

## 11. Implementation workflow

Follow this sequence:

1. Inspect repository and working tree.
2. Read the USBNET report and inspect the existing NFC patch.
3. Identify the actual NFC controller.
4. Map hardware requirements and existing support.
5. Write a concise implementation plan based on evidence.
6. Implement kernel configuration, driver and device tree changes.
7. Integrate NFC and USBNET in the same kernel tree.
8. Build the combined kernel.
9. Run kernel and device-tree gates.
10. Build the combined boot image.
11. Verify boot image format and metadata.
12. Run image gate and USBNET regression tests.
13. Back up the current boot image.
14. Verify TWRP connectivity and target partition.
15. Verify final image checksum.
16. Flash the combined image.
17. Reboot into Nuxel.
18. If boot fails or returns to TWRP, execute the guarded recovery loop.
19. Once Nuxel boots, verify NFC driver binding and hardware operation.
20. Complete userspace service and UI integration.
21. Test physical tags, including NDEF read and write.
22. Verify USBNET behaviour.
23. Test reboot persistence.
24. Produce the final report.

Do not postpone the actual reflash indefinitely after all gates pass. The operator has explicitly authorised it under the safeguards in this document.

---

## 12. Final deliverables

Create or update the following repository documentation:

- `PWNAGE-NFC-REPORT.md`
- `PWNAGE-NFC-TEST-RESULTS.md`
- `PWNAGE-NFC-HARDWARE-MAP.md`
- `PWNAGE-NFC-REFLASH-LOG.md`
- Combined image build manifest.

The final report must state:

### Kernel
- Controller identification and evidence.
- Driver and configuration.
- Device tree changes.
- Firmware requirements.
- Kernel release and build identity.

### Reflash
- Original boot image backup location and checksum.
- Final image path and checksum.
- Exact partition flashed.
- Flash command/procedure.
- Number of attempts.
- Boot outcome.
- Recovery details if any attempt failed.

### NFC
- Driver binding.
- Device interface.
- Controller initialisation.
- Power control.
- Firmware status.
- Tag discovery.
- Read results.
- Write/read-back results.
- Supported and unsupported tag technologies.

### USBNET
- Confirmation that existing fixes remain in the final kernel.
- Regression test results.
- Physical USB test results, if performed.

### Userspace
- Service status.
- API and UI integration.
- Permissions.
- Reboot persistence.

### Honest status

Use explicit statuses:

- `PASS` — tested successfully.
- `PARTIAL` — implemented but incompletely tested.
- `FAIL` — attempted and failed.
- `NOT TESTED` — no evidence.
- `UNSUPPORTED` — determined not to be supported.

Do not turn `NOT TESTED` into `PASS`.

---

## 13. Final definition of FULLY DONE

The task is `FULLY_DONE` only when:

1. The combined NFC + USBNET kernel image has been flashed successfully.
2. The phone boots into Nuxel.
3. NFC hardware is physically detected and initialised.
4. Real tags are discovered.
5. NDEF read works.
6. NDEF write and read-back work on an expendable writable tag.
7. NFC userspace and UI are functional.
8. USBNET kernel changes remain intact and pass regression tests.
9. The implementation survives reboot.
10. Documentation and logs are complete.

If physical NFC testing cannot be completed, report the exact blocker and leave the task `PARTIAL`. Do not claim completion.

**The objective is real working NFC on Nuxel, not merely a successful kernel compilation.**


