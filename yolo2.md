# NUXEL — S10+ BOOTLOOP ROOT-CAUSE REPAIR
## DeepSeek V4 Flash · CodeSeeQ · Autonomous Hardware Engineering
### Mission continuation: A5 failed → A6 and beyond

# 1. MISSION

You are the lead Linux kernel, Samsung Exynos 9820, ARM64 boot-chain and Fedora embedded phone-OS engineer responsible for getting Nuxel operational on a Samsung Galaxy S10+.

This is NOT a fresh investigation.

Five physical boot attempts have already been conducted. Real kernel panic logs and previous-boot records exist. You must build on that evidence rather than repeat earlier mistakes.

**PRIMARY OBJECTIVE: Get the Nuxel kernel to launch its initramfs, mount the Fedora rootfs, start a compatible userspace and eventually display Nuxel's phone interface.**

Work autonomously using CodeSeeQ, DeepSeek V4 Flash, terminal tools, Podman, the Nuxel repo and TWRP root ADB.

Do actual engineering: inspect, reproduce, patch, build, test, flash, collect evidence and iterate.

Do not claim success based on offline checks.

---

# 2. EXACT ENVIRONMENT

Project root:

`~/x/nuxel`

Debugging tools:

`scripts/s10plus-debug-pack/`

Flashing tools:

`scripts/nuxel-adb-flash-pack/`

Hardware:

- Samsung Galaxy S10+
- SM-G975F / beyond2lte
- Exynos 9820, ARM64
- EUR OPEN, board revision 26
- Bootloader G975FXXSEFUL1
- DTBO index 9
- TWRP 3.7.0_9-2
- ADB serial R58M75KDB2X

Verified recovery partitions:

- BOOT: `/dev/block/by-name/boot` → `/dev/block/sda14`
- USERDATA: `/dev/block/by-name/userdata` → `/dev/block/sda31`
- RECOVERY: `/dev/block/by-name/recovery` → `/dev/block/sda15`

Nuxel Fedora rootfs:

`build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img`

Experimental boot images:

`build/out/s10plus/debug-candidates/`

Previous engineering journal:

`docs/s10plus-autonomous-boot-repair/`

Previous captures:

`scripts/s10plus-debug-pack/captures/`

**Read the existing journals, boot-image source, candidate manifest and captured kernel logs before editing anything.**

---

# 3. VERIFIED FINDINGS — DO NOT REDISCOVER

## Finding A — The raw kernel now boots

The original Nuxel boot image used a gzip-compressed kernel payload.

Samsung S-Boot failed to execute it correctly.

Attempt A2 replaced it with a raw ARM64 Linux `Image`.

This worked: the physical Samsung produced kernel output and a persistent kernel panic trace.

Evidence:

`captures/20261015T071500Z-A2-postfail/`

The recovered kernel identifies itself as:

`Linux version 4.14.253 (nuxel@nuxel-phosh)`

**This proves the Samsung executes our Linux kernel.**

Do not return to the original gzip kernel packaging.

## Finding B — Current failure is initramfs loading

Attempts A2, A3, A4 and A5 all fail during initramfs processing.

Observed sequence:

```text
Trying to unpack rootfs image as initramfs...
rootfs image is not initramfs (junk in compressed archive)
Freeing initrd memory: 8128K

RAMDISK: Couldn't find valid RAM disk image starting at 0.
SAR_RD: Trying to load Ramdisk
SAR_RD: Out of memory
SAR_RD: Failed to load ramdisk

EXT4-fs (sda25): mounted filesystem
Kernel panic - not syncing: init group exit
```

The kernel discovers UFS partitions, but the intended initial ramdisk is unusable.

The fallback eventually reaches Android SYSTEM (`sda25`), not Nuxel's Fedora USERDATA (`sda31`).

The fallback init exits and Samsung's downstream kernel panics.

**Fix the initramfs delivery/extraction path before debugging systemd or Phosh.**

## Finding C — The boot header was previously malformed

The original packer stored the DTB size at offset 40, which Samsung interprets as Android header version.

Earlier images consequently reported version `376101`.

The working corrected container uses:

- Android boot header version 1
- Page size 2048
- Header size 1648
- Correct kernel/ramdisk size fields
- Raw ARM64 kernel
- Correct S10+ board configuration

A3, A4 and A5 use the corrected structure.

Preserve that fix.

## Finding D — Padding and DTB changes didn't resolve initramfs rejection

A3: uncompressed cpio with 2048-byte padding — FAILED.

A4: additional padding to 8,323,072 bytes — FAILED.

A5: removed placeholder initrd properties — FAILED.

The same initramfs error persists.

Do not perform another padding-only experiment without new evidence.

Important correction: `Freeing initrd memory: 8128K` reports reclaimed pages. It does NOT independently prove that the original ramdisk bytes and length were handed to the kernel intact.

The `junk in compressed archive` error also does not uniquely prove a physical-address mismatch.

The current hypotheses are:

1. Incorrect ramdisk memory contents or placement.
2. Bootloader handoff corruption or truncation.
3. A format/decoding incompatibility.
4. A kernel-specific initramfs parser issue.
5. A malformed payload not detected by existing offline checks.

Investigate them independently.

---

# 4. CRITICAL NEW FINDING — THE REPOSITORY'S DIAGNOSTIC BUILDER CAN REGRESS

Inspect:

`boot/s10plus/build-debug-candidate.sh`

Its default input is still the original:

`build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img`

The produced diagnostic candidate in the previous investigation contains:

- A gzip kernel
- An incorrect Android header-version field
- The earlier broken image layout

This can reintroduce the already identified failure.

**FIX THIS BEFORE BUILDING ANOTHER FLASH CANDIDATE.**

Implement strict release gates:

- Reject gzip kernel payloads in the direct S10+ boot path.
- Require valid Android boot header v1.
- Reject legacy header-version values derived from DTB size.
- Require a valid ARM64 Image header.
- Verify ramdisk offsets and size bounds.
- Verify extracted ramdisk contents.
- Verify partition capacity.
- Reject missing `/init` or its interpreter.
- Run image parsing and SHA-256 checks after every build.

Create regression tests proving that known-bad A1 and legacy diagnostic images fail these gates.

Make the build reproducible and fail closed.

Never overwrite the prior hardware-tested images.

---

# 5. PHASE ONE — FORENSIC COMPARISON

Before another physical reboot:

1. Read A2–A5 `last_kmsg` and pstore dumps.
2. Locate the precise first initramfs-related kernel error.
3. Inspect the corresponding kernel source path.
4. Compare all A2–A5 boot-image headers and offsets.
5. Extract and validate every candidate ramdisk.
6. Compare their exact compression formats and sizes.
7. Independently parse the cpio headers, filenames, sizes, symlinks, alignment and trailer.
8. Inspect the S-Boot ramdisk-load and device-tree messages.
9. Compare these with the known-working TWRP recovery boot image.

Especially inspect the working TWRP ramdisk format.

Previous evidence identified a working LZMA-alone ramdisk with properties beginning:

`5d 00 00 80 00`

Do not assume S-Boot necessarily requires LZMA. Treat it as a controlled hypothesis.

**Also verify which device tree the kernel actually receives.**

S-Boot logs show it loads dedicated DTB and DTBO partitions and applies overlay index 9.

Determine whether the DTB appended to our Android boot image is used, ignored or combined.

A change to an unused embedded DTB must not be counted as an effective device-tree experiment.

---

# 6. PHASE TWO — REPAIR RAMDISK DELIVERY

Prioritize obtaining an actual successful `/init` execution.

## Candidate A6 — Known-good ramdisk format experiment

Rebuild the current, verified Nuxel initramfs using the LZMA-alone container format observed in the booting TWRP recovery.

Preserve, wherever feasible:

- The proven raw ARM64 kernel
- Correct Android v1 header
- Kernel and ramdisk load addresses
- Correct board configuration
- Existing executable `/init`
- Static Toybox
- Necessary initramfs device directories

Use the same LZMA properties as the working recovery image where justified.

Verify the compressed stream can be fully decompressed and its output is valid cpio.

Do not append arbitrary bytes outside an LZMA stream.

Use explicit before/after binary comparisons so the test meaning is clear.

Build the image as:

`build/out/s10plus/debug-candidates/A6/boot.img`

Produce validation logs and a SHA-256 checksum.

Only flash after the new image passes all offline checks.

If A6 fails, recover its new kernel panic evidence and determine whether the error changed.

Do not repeat the same image without a new reason.

## Candidate A7 — Kernel-embedded initramfs

If the bootloader-delivered ramdisk remains unusable, investigate embedding the minimal Nuxel initramfs into the Linux kernel using `CONFIG_INITRAMFS_SOURCE`.

This removes the external ramdisk handoff from the critical boot path.

Required process:

1. Obtain a clean, pinned kernel source checkout matching the current Exynos 9820 kernel.
2. Inspect and validate the existing kernel config.
3. Preserve all hardware-critical Samsung configuration.
4. Enable a built-in Nuxel initramfs.
5. Build an appropriate raw ARM64 Image.
6. Verify the embedded initramfs contains an executable `/init`.
7. Ensure the Android boot container does not introduce a conflicting external initramfs.
8. Validate boot image capacity and structure.
9. Verify the rebuilt kernel is compatible with the device tree.
10. Package a new diagnostic BOOT candidate.

Use the verified Fedora 43/Podman ARM64 environment on the MacBook where useful.

Do not treat an invalid or incomplete kernel checkout as a successful build.

This is a separate candidate requiring its own verification.

## If both experiments fail

Prioritize direct kernel instrumentation over further guesses.

Patch the exact `init/initramfs.c` code path to record:

- Whether an external initrd was supplied.
- Its start and end addresses.
- The input length.
- The first few expected magic bytes.
- The decompressor selected.
- The parser's actual failure reason.
- Whether `/init` was extracted.

Capture these diagnostics through the existing Samsung persistent kernel logging mechanism.

Do not dump arbitrary physical memory or sensitive memory ranges.

Never guess physical addresses.

Use the log evidence to choose the next repair.

---

# 7. PHASE THREE — VERIFY INITRAMFS TO FEDORA HANDOFF

Once `/init` executes, move to the next milestone.

Inspect:

`boot/initramfs/init.sh`

The kernel receives a Samsung-generated command line, not necessarily Nuxel's Android boot-image cmdline.

The initramfs must:

- Identify beyond2lte using the running device tree.
- Discover USERDATA using actual kernel partition metadata.
- Avoid relying on Android-created symlinks.
- Never silently mount SYSTEM as the Nuxel rootfs.
- Mount USERDATA as ext4.
- Initialize `/proc`, `/sys` and `/dev`.
- Capture diagnostic evidence.
- Handoff correctly to the selected rootfs init process.

Use the known device identity rather than hard-code the assumption that USERDATA always appears as `/dev/sda31`.

Record positive evidence:

`INITRAMFS_EXECUTED`

`USERDATA_DISCOVERED`

`ROOTFS_MOUNTED`

`ROOTFS_HANDOFF_STARTED`

These markers must be generated by actual executing code, not just by the build process.

Preserve error logs if handoff fails.

---

# 8. PHASE FOUR — FEDORA 43 / SYSTEMD KERNEL COMPATIBILITY

IMPORTANT: A second compatibility problem has been identified.

The current phone rootfs contains Fedora 43 systemd 258.11.

The current S10+ kernel is Linux 4.14.253.

Systemd 258 raised its minimum supported kernel baseline to Linux 5.4 and removed legacy cgroup v1 support.

Therefore the installed Fedora userspace and current Samsung kernel are not a supported combination.

**DO NOT ASSUME SYSTEMD WILL WORK MERELY BECAUSE ITS ARM64 ELF FILE EXISTS.**

Investigate this incompatibility separately once the initramfs issue is resolved.

Evaluate:

- Actual systemd 258 kernel requirements.
- Cgroup v2 support in the Samsung kernel configuration.
- Kernel syscall requirements.
- Required mount and namespace features.
- Fedora 43 dependency compatibility.
- Availability and practicality of a newer compatible Exynos kernel.
- Alternative compatible init strategies while preserving Fedora userspace.

Prefer a staged approach:

1. Prove USERDATA mounts.
2. Prove a small Fedora userspace process can execute.
3. Establish a supported init strategy.
4. Launch the required system services.
5. Proceed to the phone interface.

Keep Fedora 43 as the target distribution.

Do not silently substitute Alpine, OpenRC or an unrelated userspace.

If a temporary diagnostic init is required, label it as such.

Avoid a wholesale kernel upgrade unless its feasibility and hardware compatibility have been established.

---

# 9. PHASE FIVE — PHONE DISPLAY

After Linux and Fedora userspace execution are confirmed, investigate the display path.

Inspect:

- Exynos display controller
- DECON / DSIM
- AMOLED panel initialization
- DRM/KMS availability
- Framebuffer device
- Display clocks and regulators
- Phoc compositor
- Phosh mobile shell
- greetd session configuration
- Wayland display socket
- Touchscreen devices
- Nuxel Home integration

The existing rootfs capture shows greetd configured as:

`agreety --cmd /bin/sh`

That is not a configured Phosh mobile session.

Correct the graphical session setup once the kernel/userspace foundation is functional.

Do not mistake installed Phosh packages for a working phone display.

A kernel display task appearing in a panic dump does not establish that the AMOLED screen is usable.

First-light display, framebuffer operation, compositor operation and visible Phosh UI are separate milestones.

---

# 10. OUR PERMANENT TWRP FAILURE AGREEMENT

THIS RULE IS MANDATORY.

The user will manually return the Samsung Galaxy S10+ to TWRP whenever an autonomous Nuxel boot test fails.

The initial recovery state at the start of your mission is normal.

After you flash and reboot a new candidate:

1. Record the attempt ID.
2. Record the BOOT and rootfs hashes.
3. Record the reboot time.
4. Transition to `AWAITING_BOOT_RESULT`.
5. Monitor ADB availability.
6. Allow the user to manually recover the phone after a bootloop.

**IF THE SAME SAMSUNG RETURNS TO TWRP AFTER YOUR TEST REBOOT, THE PREVIOUS NUXEL BOOT ATTEMPT FAILED.**

This is our explicit human-agent agreement.

Do not ask the user if it failed.

Do not ask the user to confirm the failure.

Do not ask for permission to continue routine authorized repair work.

Record:

`BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`

`RECOVERY_ACCESS=RESTORED`

`NEXT_ACTION=COLLECT_FRESH_KERNEL_LOGS`

Immediately:

- Capture pstore.
- Capture previous kernel logs.
- Capture reset reasons.
- Preserve raw evidence.
- Compare against the previous attempt.
- Determine whether the failure progressed to a later stage.
- Update the root-cause analysis.
- Continue with the next evidence-backed repair.

TWRP returning establishes a failed attempt under this agreement. It does NOT independently establish why it failed.

If ADB is unavailable, wait for manual recovery without issuing destructive operations.

Do not reboot the device while it is inaccessible.

Never interpret USB disconnection alone as boot success.

---

# 11. AUTONOMOUS DEVICE TESTING AUTHORIZATION

The user has already authorized autonomous testing on this expendable S10+.

You may:

- Edit the Nuxel repository.
- Build and validate new boot images.
- Install necessary local dependencies.
- Run read-only device diagnostics.
- Flash verified Nuxel BOOT candidates.
- Update USERDATA only when a rootfs correction requires it.
- Reboot after a verified flash.
- Automatically resume when TWRP returns.

No separate confirmation is required for routine authorized BOOT/USERDATA experiments.

Absolute restrictions:

- Preserve TWRP RECOVERY.
- Preserve EFS and SEC_EFS.
- Preserve bootloader and PIT.
- Do not repartition.
- Do not write modem or radio calibration.
- Do not flash DTB, DTBO, VBMETA or unrelated partitions.
- Do not modify hardware fuses or thermal protections.
- Do not invent partition addresses.

Before every write, verify the live device, root ADB, target capacity, relevant mount state, image SHA-256 and backup availability.

After each write, require successful byte-for-byte readback.

Prefer BOOT-only tests while investigating initramfs.

Do not rewrite the 4 GiB Fedora rootfs when no Fedora files changed.

Limit consecutive speculative physical tests. After three tests that produce no new diagnostic information, change the observability strategy rather than trying random variations.

---

# 12. ENGINEERING JOURNAL AND DELIVERABLES

Continue using:

`docs/s10plus-autonomous-boot-repair/`

Update:

- `STATUS.md`
- `ROOT-CAUSE.md`
- `BOOT-STAGES.md`
- `HYPOTHESES.md`
- `PATCHES.md`
- `TEST-RESULTS.md`
- `FLASH-ATTEMPTS.md`
- `DEVICE-OBSERVATIONS.md`
- `NEXT-ACTION.md`

For each candidate, record:

- What changed
- Why it changed
- What evidence supports it
- Files modified
- Offline tests
- Kernel/ramdisk structure
- Exact image hash
- Flash/readback confirmation
- Boot result
- New logs
- Next hypothesis

Maintain separately:

- Source-level fixes
- Offline-verified artifacts
- Hardware-proven behavior

Do not confuse those states.

Preserve prior candidates and logs so regressions can be compared.

---

# 13. SUCCESS MILESTONES

Track separately:

1. S-Boot starts Nuxel kernel — **ALREADY PROVEN**
2. Kernel runs and persistent logging works — **ALREADY PROVEN**
3. External or embedded initramfs unpacks
4. Nuxel `/init` executes
5. USERDATA rootfs is discovered
6. Fedora rootfs mounts
7. Fedora userspace executable runs
8. Compatible init system starts
9. Services initialize
10. Display driver becomes usable
11. Nuxel first-light appears
12. Phoc starts
13. Phosh starts
14. Usable Nuxel phone interface appears

Only mark milestones as completed when they are observed on hardware.

---

# 14. EXECUTE NOW

Start in `~/x/nuxel`.

First read the existing A2–A5 logs, candidate image headers and root-cause documentation.

Correct the boot-image builder regression.

Verify the physical BOOT candidate currently installed.

Then prepare a controlled A6 LZMA ramdisk experiment, or a stronger evidence-backed alternative if your source investigation identifies one.

Do not immediately reflash unchanged images.

If A6 fails, use its logs to decide whether to pursue a kernel-embedded initramfs or additional kernel instrumentation.

After initramfs execution is proven, address Fedora systemd/kernel compatibility and then the phone display.

**OUR AGREEMENT REMAINS ACTIVE: WHEN I MANUALLY RETURN THE PHONE TO TWRP AFTER YOUR REBOOT, THAT BOOT ATTEMPT HAS FAILED. RECONNECT, COLLECT LOGS, FIX THE NEXT ISSUE AND CONTINUE AUTONOMOUSLY.**

**FINAL OBJECTIVE: BOOT FEDORA-BASED NUXEL ON THE REAL SAMSUNG GALAXY S10+ AND GET THE PHONE INTERFACE ON SCREEN.**

BEGIN ENGINEERING EXECUTION.
