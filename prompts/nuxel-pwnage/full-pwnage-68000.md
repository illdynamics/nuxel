# FULL-PWNAGE-68000 — Finish and safely validate Exynos 9820 MFC hardware decoding on Nuxel

**Mission ID:** PWNAGE-68000  
**Project:** Nuxel — Mobile Linux for Control Freaks  
**Target handset:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Target OS:** Nuxel / Fedora 43 aarch64  
**Kernel family:** Samsung/Linux4 Exynos9820 downstream Linux 4.14.253  
**Pinned source revision recorded by the previous mission:** `f7194c1d15eded1c2a1a4dc63825b26103435cc0`  
**Mission type:** continuation, safe deployment preparation, physical hardware validation, decoder integration, measurable performance proof and rollback  
**Primary objective:** close the final gap between a successfully built MFC-safe kernel/userspace implementation and a real, verified hardware-decoded frame on the physical S10+.  
**Secondary objective:** deliver a precise, low-risk BOOT-only deployment/recovery procedure that does not repeat the previous failed TWRP attempt blindly.  

---

## 0. Mission order — continue from PWNAGE-61000; do not restart it

This is a continuation of PWNAGE-61000. The previous agent has already performed substantial kernel, firmware, diagnostic, policy, test, and rollback work. Do not discard that work, recreate it from scratch, or return another research-only report.

The supplied PWNAGE-61000 completion report is the immediate source of truth for this mission. Revalidate it against the current checkout and handset before acting, because the report itself says that the physical phone still runs the pre-patch kernel.

### 0.1 The exact state left by PWNAGE-61000

The report says all of the following:

**Built and implemented on the development host:**

- MFC fail-closed kernel patch `kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch` plus its `.required` sidecar.
- The patch changes `request_firmware()` to `request_firmware_direct()` so a missing firmware file fails immediately rather than waiting for the 60-second userspace firmware-helper timeout while the MFC open path holds a mutex.
- Firmware is checked for null, empty and oversized cases and released through the error path.
- Unknown device-tree MFC `ip_ver` is rejected in `mfc_probe()` before firmware/register access.
- Kernel config fragments and `live-required.config` were updated for MFC/media/IOMMU support; the reported parity gate is 53/53.
- Firmware manifest and generator now record provenance, size, request name, expected IP revision, license and redistribution policy. The entry remains `required: false` by design.
- `install-firmware.sh --verify-mfc` checks the candidate MFC blob, including its expected size and hash.
- A local, gitignored firmware blob exists in the agent's working tree at `firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin` according to the report.
- Inventory-first diagnostic `nuxel-mfc-diag` is implemented. It does not open video nodes by default.
- The diagnostic supports `--query-only` / `--decode-test`, but those hardware operations require `--device`, `--allow-hardware-open`, and a matching owner-approved safety receipt.
- A vendor-ABI decoder helper, `nuxel-mfc-decode.c`, was cross-compiled.
- A player wrapper, `nuxel-mfc-play`, has a default software path and a hardware path that refuses to run until hardware-decode proof is recorded.
- Safety-receipt tooling, JSON status schema, media test manifest, image verification and rollback scripts were implemented.
- The clean rootfs builder now installs the MFC diagnostic, policy, schema, helper and GStreamer guard.

**Build/test results reported:**

- Kernel build exited 0.
- `Image.gz` size approximately 16 MiB; reported SHA-256 begins `cfc80df9` and ends `90ed7` (retrieve the full hash from the build artifact and do not copy an abbreviated hash into a deployment command).
- Built `.config` SHA-256 begins `74d61637` and ends `add2d`.
- `exynos9820.dtb` built; reported SHA-256 begins `a6b67b46` and ends `e95`.
- Kernel capability parity: 53/53 PASS.
- `pytest -q tests/pwnage61000`: 36 passed.
- `nuxel-mfc-diag --self-test`: 17 checks passed.
- `install-firmware.sh --verify-mfc`: PASS on the development host.
- AArch64 helper cross-compilation: PASS.
- Existing software playback fallback after reboot: PASS.

**What has emphatically NOT happened on the physical phone:**

- The patched PWNAGE-61000 kernel has NOT been flashed or booted.
- The MFC firmware has NOT been installed in the live root filesystem.
- `/dev/video6` has NEVER been opened by the MFC diagnostic.
- No `VIDIOC_QUERYCAP`, `VIDIOC_ENUM_FMT`, `REQBUFS`, `STREAMON`, `DQBUF`, decoded-frame checksum or visual frame proof has been collected on hardware.
- No hardware decode has been proven.
- No codec-resolution matrix has been tested on hardware.
- No matched software-vs-MFC performance or thermal benchmark has been run.

The live diagnostic still reports `BLOCKED_FIRMWARE_MISSING`, with `safe_open_allowed=false`. The live handset is still on its previous kernel:

```text
4.14.253-gf7194c1d15ed-dirty
```

The previous task rebooted the phone at approximately `2026-11-03T01:37:26+01:00`; SSH returned, Phoc and WirePlumber were running, `/dev/video6` existed, and the MFC diagnostic still reported firmware missing. The boot ID recorded by that report was:

```text
95b82b79-3d51-4a48-955e-b446551ccffd
```

The new kernel and DTB were staged on the host only. This is the current critical gap. Do not describe MFC as working until a decoded frame is proven on the handset.

### 0.2 Mission outcome

Move the system through these states, in order:

```text
HOST_BUILD_VERIFIED
    -> BOOT_IMAGE_ASSEMBLED_AND_VERIFIED
    -> ROLLBACK_IMAGE_CAPTURED_AND_VERIFIED
    -> OWNER_APPROVED_FOR_ONE_BOOT_PARTITION_WRITE
    -> PATCHED_KERNEL_BOOTED
    -> MFC_FIRMWARE_PRESENT_AND_HASH_VERIFIED
    -> MFC_DRIVER_PROBED_WITH_EXPECTED_IP
    -> FIRST_QUERY_ONLY_PASSED
    -> SINGLE_OPEN_CLOSE_PASSED
    -> QUEUE_SETUP_PASSED
    -> ONE_KNOWN_TEST_FRAME_DECODED
    -> FRAME_CONTENT_VERIFIED
    -> PLAYER_HARDWARE_PATH_PROVEN
    -> MATCHED_SOFTWARE_VS_MFC_BENCHMARK
    -> LIMITED_HARDWARE_DECODE_AVAILABLE
```

Any failure must stop progression, preserve the working software path, and leave the phone recoverable. Do not skip a state.

### 0.3 Hard safety requirements

1. **Do not flash anything during initial investigation or build verification.**
2. **Do not ask the owner to enter TWRP yet.** First establish why the previous attempt did not boot or complete and build a verified BOOT image.
3. Do not repeat the same TWRP procedure unchanged. Diagnose the prior failure from logs, build artifacts, image headers, partition readback, command history and the device's actual boot state.
4. Do not make a new bootloader unlock request, toggle OEM unlocking, relock the bootloader, wipe data, reset FRP, modify KG state, or change secure-download settings.
5. Do not touch `EFS`, modem, `persist`, `super`, `userdata`, `recovery`, `vbmeta`, `dtbo`, or any partition other than the precisely verified BOOT target. Do not modify recovery as a shortcut.
6. Do not install MFC firmware into the currently running old kernel before the patched kernel is active. The old kernel may retain the known firmware wait / open hang risk.
7. Do not open `/dev/video6` or any other candidate MFC node until the patched kernel is proven live, the exact firmware is present and verified, device identity matches, the diagnostic says the node is safe, and the required owner-approved receipt exists.
8. Do not remove or bypass the GStreamer guard or WirePlumber video-capture block globally.
9. Do not restore camera capture, generic V4L2 scanning, KMS or OpenGL plugins as a side effect of enabling MFC decode.
10. Keep `mpv --hwdec=no` software playback as the always-available fallback. Boot/preload video must remain independent of MFC.
11. One controlled first-open attempt only. Do not use `--repeat 5/20/100` until a single query/open/close has succeeded and the kernel log is clean.
12. Never claim hardware decode from a device node, driver name, firmware file, successful build, plugin presence, or software playback. Only a verified frame decoded by the physical MFC counts.
13. No flash, reboot, firmware installation or hardware-open operation without explicit owner approval at that stage. The current request to create this prompt is not authorization to flash the phone.
14. If the phone hangs, enters D state, loops, or loses SSH during the first MFC operation, stop. Do not repeat the operation automatically.

---

## 1. Understand the separation: Mali GPU vs MFC fixed-function decoder

Do not conflate these two hardware blocks:

- **Mali-G76 MP12** is the graphics GPU. It renders GLES, compositor content and UI surfaces.
- **Exynos 9820 MFC** is a separate fixed-function codec engine. It decodes compressed video streams such as H.264/HEVC through its own firmware, driver, memory queues and V4L2-like vendor ABI.

A video may be decoded by the CPU and later composited by Mali. That is GPU-assisted display with software decode, not MFC hardware decoding.

A video may be decoded by MFC and then copied through CPU memory before display. That is real hardware video decoding but not a zero-copy presentation pipeline.

A V4L2 node existing, a codec appearing in a list, a successful `QUERYCAP`, or a player showing a video does not alone prove hardware decode. The proof must tie the tested stream and output frame to the MFC queue/driver and hardware execution.

The mission's MFC scope is decoding only. Do not expand this mission into encoder, camera capture, USB-C display, Miracast or a wholesale GPU rewrite.

---

## 2. Repository and live-device inventory — read-only first

Start in the actual current repository checkout, not a stale extracted archive. Record:

```sh
git status --short --branch
git rev-parse HEAD
git log -12 --oneline --decorate
```

Locate and inspect the new PWNAGE-61000 implementation. At minimum, verify these reported paths exist and match the completion report:

```text
kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch
kernel/s10plus/patches/0008-mfc-firmware-fail-closed.patch.required
kernel/s10plus/configs/nuxel-drm-kbase.fragment
kernel/s10plus/configs/live-required.config
firmware/s10plus/manifest.yml
firmware/s10plus/gen-manifest.py
firmware/s10plus/install-firmware.sh
firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin
 tools/s10plus/a61/nuxel-mfc-diag
 tools/s10plus/a61/nuxel-mfc-decode.c
 tools/s10plus/a61/nuxel-mfc-play
 tools/s10plus/a61/nuxel-mfc-safety-receipt.py
 tools/s10plus/a61/mfc-status.schema.json
 tools/s10plus/a61/mfc-test-media.json
 tools/s10plus/a61/rollback-pwnage61000.sh
 tests/pwnage61000/
 docs/beta-finalization/live/PWNAGE-61000-MFC-REPORT.md
 docs/beta-finalization/live/PWNAGE-61000-MFC-BASELINE.md
 docs/beta-finalization/live/PWNAGE-61000-MFC-TODO.md
 docs/beta-finalization/live/PWNAGE-61000-MFC-OPERATOR.md
 docs/beta-finalization/live/evidence/pwnage-61000/
```

Correct path typos if a real source path differs; do not create duplicate files merely to match this list. The indented paths above are a checklist, not permission to overwrite files blindly.

Check the full firmware hash and exact size from the file itself:

```sh
stat -c '%s %n' firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin
sha256sum firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin
```

The previous report expects:

```text
size = 685832 bytes
sha256 = f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f
ARM header = ea000077
request name = mfc_fw.bin
```

Do not trust an abbreviated hash. If the file is missing, differs, or comes from a source with no redistributable license, stop and report `BLOCKED_FIRMWARE_PROVENANCE` or `BLOCKED_FIRMWARE_MISSING`. Do not fetch a random similarly named file.

### 2.1 Capture the phone's current state without opening the decoder

The phone should remain in its normal Nuxel boot for this inventory, connected over the already-working USB/SSH transport where possible. Do not switch it into TWRP at this phase.

Read-only commands, when available:

```sh
uname -a
cat /proc/version
cat /proc/cmdline
cat /etc/os-release
cat /proc/sys/kernel/random/boot_id
find /lib/firmware -maxdepth 3 -type f -name '*mfc*' -o -name 'mfc_fw.bin' 2>/dev/null
ls -l /dev/video* /dev/media* 2>/dev/null || true
readlink -f /sys/class/video4linux/video6/device/driver 2>/dev/null || true
cat /sys/class/video4linux/video6/name 2>/dev/null || true
cat /sys/class/video4linux/video6/device/modalias 2>/dev/null || true
dmesg -T | grep -iE 'mfc|firmware|s5p-mfc|video codec|iommu|sysmmu|188d0000|RISC_ON|SYS_INIT' | tail -250
systemctl is-active phoc wireplumber 2>/dev/null || true
```

Also record the graphics stack state (read-only) to ensure the MFC mission does not regress it:

```sh
cat /etc/nuxel/graphics/graphics-profile.json 2>/dev/null || true
/usr/lib/nuxel/nuxel-graphics-profile status --json 2>/dev/null || true
```

Do **not** run `v4l2-ctl --all`, `gst-inspect` in a way that loads unsafe plugins, `ffmpeg -f video4linux2`, a player against `/dev/video6`, or a generic media probe before the safety gate. Do not `cat` or `dd` a video node. Directory listing and sysfs reads are allowed; opening the suspect node is not.

Record a fresh live snapshot in `docs/beta-finalization/live/evidence/pwnage-68000/preflight/`. Include command, timestamp, boot ID, exit status and hashes. Redact Wi-Fi credentials, tokens and private network secrets.

---

## 3. Reconstruct the previous TWRP attempt before planning another one

The owner reports that a previous attempt involving reflash/reboot/TWRP did not work and resulted in a hang or bootloop. Do not dismiss this and do not ask the owner to repeat the same operation.

The immediate PWNAGE-61000 report says **no flash happened during that mission**. It says the phone rebooted normally into its existing kernel and SSH returned. Therefore the failure described by the owner may refer to a different attempt, a prior deployment step, a return-to-recovery flow, or a boot-image installation performed outside PWNAGE-61000. Determine which one from the repository and evidence.

### 3.1 Search and correlate evidence

Inspect:

- `docs/beta-finalization/live/` and all PWNAGE-61000 operator/report/TODO/evidence files;
- previous PWNAGE boot deployment reports (especially boot-image assembly, TWRP transfer and post-flash validation logs);
- build output timestamps and hashes for `Image.gz`, DTB, initramfs and any assembled BOOT images;
- existing `flash.md`, deployment scripts and boot verifiers;
- shell history or captured ADB logs only if available and safe;
- any `dmesg`, boot ID, kernel version, recovery device identity and partition hash captured after the failed attempt.

Answer these questions with evidence:

1. Was a BOOT image actually flashed during the failed attempt, or was it only copied/staged?
2. Was the image a complete Android boot image or merely a raw `Image.gz` / kernel file?
3. Did it include the correct DTB, ramdisk/initramfs and command line for this exact device and boot arrangement?
4. Was the selected partition definitely the `boot` partition, not recovery or another partition?
5. Was the write complete, synced, read back and hash-verified?
6. Did the device return to TWRP because the user explicitly selected Recovery, because the recovery key combination was held, because the boot image failed, or because the normal system chain redirected it?
7. Did the kernel start and then hang in early userspace, or did the kernel fail before userspace?
8. Did SSH ever return? Was the lockscreen/Home displayed? Was the hang actually the boot video/preload stage?
9. Was the correct firmware absent when MFC first probed, or did the patched kernel never boot?
10. Was an old or wrong rollback image used?

If evidence is unavailable, say `PREVIOUS_FAILURE_ROOT_CAUSE_UNKNOWN`. Do not guess. Add a targeted evidence collection step before any flash.

### 3.2 No bootloader/recovery agreement reset

Do not request that the owner repeat OEM unlock, bootloader unlock, FRP, KG or secure-download setup. Do not relock the bootloader or wipe userdata. Those are not normal prerequisites for a BOOT-partition image update when the device is already in the known working development configuration.

Do not promise that a bootloader confirmation screen will or will not appear; verify the actual current boot state and known device workflow. The goal is to avoid unnecessary changes to bootloader state.

### 3.3 Understand TWRP navigation

If a later, separately approved deployment uses TWRP, the final action after a successful BOOT-only flash is to choose **Reboot → System**. Do not choose **Reboot → Recovery** unless intentionally returning to TWRP. Returning to TWRP after a flash is not evidence that the kernel was successfully booted.

Never perform repeated flash/reboot cycles just to see whether a different result appears. One approved write, one readback verification, one normal-system boot attempt, one controlled recovery if necessary.

---

## 4. Verify the kernel patch, driver and device-tree identity

The previous report gives the exact MFC baseline. Treat it as a strong starting point, then verify the current source and compiled outputs.

### 4.1 Expected hardware description

```text
SoC:                 Exynos 9820
DT compatible:      samsung,exynos-mfc
DT ip_ver:           0x1300 (32-bit big-endian property; parse as DT u32)
MMIO base:           0x188d0000
IRQ:                 SPI 0x152 as represented by the device tree
clocks:              aclk_mfc and any additional source-defined clocks
SysMMUs:             two MFC-associated SysMMUs in the reported node
power domain:        pd-mfc
video node:          /dev/video6
sysfs video name:    s5p-mfc-dec0
platform device:     188d0000.mfc
driver:              s5p-mfc
firmware request:    mfc_fw.bin
```

The kernel source is pinned at:

```text
f7194c1d15eded1c2a1a4dc63825b26103435cc0
```

Do not assume `/dev/video6` will always be the decoder after boot. Resolve its current identity through `/sys/class/video4linux/*/name`, parent device, driver symlink and the expected platform node. If a different video index appears, use that index only after the exact sysfs identity matches. Never hardcode a node number as proof.

### 4.2 Re-review `0008-mfc-firmware-fail-closed.patch`

Verify the patch applies to the exact pinned kernel and is marked required by its `.required` sidecar. Inspect the resulting source and built object, not just the patch file.

Required behaviors:

- `request_firmware_direct()` is the actual compiled call site in MFC firmware loading.
- Missing firmware returns quickly and propagates a clear negative error.
- Null, zero-length and oversized firmware payloads are rejected.
- All failure paths release firmware and memory cleanly.
- Unknown `ip_ver` returns `-ENODEV` before register access or firmware/RISC startup.
- IRQ waits and hardware-lock waits remain bounded and have meaningful error logs.
- failed probe/open does not leave clocks, regulators, power domains or IOMMU references stuck on.
- `mfc_open()` does not wait on userspace firmware helpers while holding the device mutex.

Use source inspection plus object/disassembly checks where practical. The previous report states that objdump confirmed `mfc_load_firmware` calls `request_firmware_direct`; re-run that verification on the exact final object.

Do not weaken the early error handling to make a test pass. A missing or incorrect firmware blob must fail promptly and leave the UI responsive.

### 4.3 Kconfig and DTB validation

- Verify all required MFC/media/IOMMU symbols are enabled in the final `.config`.
- Compare the final kernel config against the approved `live-required.config`; retain the 53/53 parity or document any intentional schema change.
- Check that the MFC node is enabled (`status = "okay"`) for the correct board.
- Verify the `ip_ver` property is encoded and read correctly as a big-endian device-tree u32.
- Verify clocks, resets, IRQ, two SysMMUs, power domain, memory-region/reserved-memory and DMA coherency details exactly match the source driver.
- Run DTB structural checks and extract the final MFC node from the compiled DTB; do not rely only on DTS text.
- Ensure the final BOOT image contains the exact new DTB. A separately built DTB that is never packaged into the boot image is not deployed.

---

## 5. Firmware provenance and rootfs staging

The local firmware candidate recorded by the previous report is:

```text
path:       firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin
size:       685832 bytes
SHA-256:    f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f
header:     ea000077
request:    mfc_fw.bin
installed:  /lib/firmware/mfc_fw.bin
```

### 5.1 Verify exact origin and rights

- Verify the manifest's source repository and immutable vendor commit.
- Verify the binary hash, size and expected ARM header bytes.
- Verify the binary has not been truncated, converted, padded or modified.
- Verify the firmware is for the Exynos 9820 MFC IP revision represented by `ip_ver=0x1300`.
- Confirm license and redistribution policy. Do not put a proprietary blob into a public release artifact unless its license permits that.
- Do not silently download from an untrusted mirror or replace a hash mismatch.

### 5.2 Rootfs installation behavior

The install script must:

- install as `/lib/firmware/mfc_fw.bin` with correct owner/mode;
- create only required directories;
- verify the installed file's full size and SHA-256;
- be idempotent;
- write atomically (temporary file, fsync where available, rename);
- not modify unrelated ABOX/audio/NFC/GPS/camera firmware;
- clearly distinguish `MFC_FIRMWARE_PRESENT_VERIFIED` from `MFC_FIRMWARE_MISSING`, `MFC_FIRMWARE_HASH_MISMATCH` and `MFC_FIRMWARE_LICENSE_BLOCKED`;
- refuse to stage a wrong blob;
- support offline rootfs image inspection before the phone is touched.

### 5.3 Firmware activation timing — determine it from the exact source before deployment

The existing live kernel is pre-PWNAGE-61000 and the report documents a 60-second firmware-helper wait in the old open path. Do not copy the blob into `/lib/firmware` and then probe/open the decoder on that old kernel as an experiment.

However, do not assume that firmware must always be present before the patched kernel boots. The PWNAGE-61000 report identifies the problematic request as part of the MFC open path (`mfc_open()` / `mfc_load_firmware()`), but the exact current source and any probe-time request must be checked.

Choose the activation method only after proving the request timing from the driver source:

- **If firmware is requested only from the first explicit MFC open:** the blob may be atomically installed into the live rootfs after the patched kernel has booted, but before any diagnostic or service is allowed to open the MFC node. Confirm that no boot service, plugin scanner, compositor, PipeWire/WirePlumber monitor or diagnostic opens the node automatically. Verify the file's full hash and permissions before issuing the first receipt-bound open.
- **If firmware is requested during probe/early boot:** it must be present in the rootfs/initramfs before the patched kernel boots. Prepare a narrow, reversible file-only staging method. This may require one approved TWRP session to mount the actual Nuxel root filesystem and copy exactly `/lib/firmware/mfc_fw.bin`, or a verified initramfs staging mechanism. Do not flash a whole rootfs image to deliver a 685,832-byte firmware blob.
- **If firmware request timing cannot be proven:** stop with `BLOCKED_FIRMWARE_ACTIVATION_ORDER`; do not guess and do not test by opening the node.

A non-active staging copy may be placed under `/var/lib/nuxel/staging/pwnage68000/`, but that is not activation and will not satisfy a kernel firmware request unless an audited early-boot mechanism installs it at the correct time.

In all cases, preserve the sequence: verify blob provenance/hash -> establish safe activation timing -> package the patched kernel/DTB -> capture rollback -> obtain approval -> use the minimum necessary deployment operation -> verify live firmware hash -> only then request approval for a hardware open. Do not install the firmware on the old kernel and then open the decoder.

---

## 6. Build a correct complete BOOT image — do not flash a raw kernel by mistake

This is the most important deployment-preparation workstream. The previous mission built `Image.gz` and a DTB, but the physical phone was not updated. The next step is not to send a raw `Image.gz` to TWRP and hope that the recovery writes it correctly.

### 6.1 Inspect the known-good BOOT image construction path

Find the repository's working S10+ BOOT image builder, verifier and deployment notes from the most recent successful boot-only update. The previous deployment record includes:

```text
TWRP device observed:        R58M75KDB2X (re-detect; do not hardcode)
TWRP product observed:        omni_beyond2lte (re-detect)
previous BOOT partition:     /dev/block/by-name/boot
previous block alias:        /dev/block/sda14
previous BOOT size:          57,671,680 bytes
previous working image:      nuxel-beyond2lte-boot-a52d-padded.img
previous live BOOT hash:     2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc
```

These values are historical evidence only. Re-read them from the live handset/recovery for this deployment. Never assume device serial, block alias, partition size or hash still match.

Inspect the image format, Android boot header version, kernel payload offset/size, ramdisk/initramfs layout, DTB placement, bootconfig/command-line fields and any padding. Reuse the exact proven packaging path that created the last BOOT image known to boot on this device. Do not hand-roll `mkbootimg` arguments if a project-specific builder already establishes the correct format.

### 6.2 Inputs to the new image

The final MFC BOOT image must contain:

- the exact PWNAGE-61000 patched `Image.gz` (not a stale kernel);
- the exact rebuilt `exynos9820.dtb` containing the validated MFC node and all previously working touchscreen, NFC, GPU, audio and power fixes;
- the same known-good ramdisk/initramfs unless a documented MFC dependency requires a change;
- unchanged verified command line and boot header settings;
- correct board identity and image padding/partition-fit constraints.

Do not combine a new kernel with an old DTB. Do not use the wrong board's DTB. Do not update the initramfs or userspace unnecessarily. Do not reflash the full rootfs as part of this mission.

### 6.3 Pre-flash verification gate

Before any owner approval request, the agent must produce:

- exact full SHA-256 of the new BOOT image;
- exact SHA-256 of `Image.gz`, final DTB, initramfs, config and source commit;
- successful boot-image parser output showing all segments and offsets;
- BOOT image size less than the currently detected BOOT partition capacity, with appropriate margin;
- successful `verify-a25-boot.py` or the current authoritative project verifier;
- extracted kernel hash equal to the intended `Image.gz` hash;
- extracted DTB hash equal to the intended DTB hash;
- extracted initramfs hash equal to intended unchanged initramfs hash;
- exact partition path and size read from the physical handset/recovery;
- matching current live BOOT readback and a separately saved rollback copy;
- readback SHA-256 of the rollback copy matching the live partition before write;
- a documented route to restore the exact pre-flash image from TWRP ADB;
- an assessment of the prior failed attempt and the corrective action taken.

If any segment cannot be extracted or verified, do not ask the owner to flash. State `BLOCKED_BOOT_IMAGE_PACKAGE`.

### 6.4 Capture a fresh rollback image

Do not rely blindly on the old PWNAGE-51000 rollback image. It may be a valid older kernel but it is not automatically the exact pre-PWNAGE-68000 BOOT state.

Capture the current BOOT partition byte-for-byte to a timestamped backup, preferably through the same trusted recovery readback mechanism used by the previously successful deployment. Verify:

- source block path resolves to the verified BOOT partition;
- byte count equals the actual partition size or the exact image readback convention used by the project's boot tool;
- backup hash;
- backup can be parsed as a boot image;
- backup artifact is copied off the phone to the host;
- backup hash is recorded in the operator instructions.

Never overwrite the only backup. Make at least one independent host-side copy and verify its hash after transfer.

### 6.5 Do not flash in this phase

Complete the image and rollback preparation, run all offline tests and report the exact one-step deployment plan. Then stop and request explicit owner approval for a single BOOT-only write. The current user request does not authorize the agent to perform the flash.

---

## 7. TWRP and USB deployment plan — only after the owner approves

The owner asks whether the phone must be placed in TWRP with USB connected again. The answer for the current stage is **no**: keep it booted into the normal Nuxel system and keep the existing working USB/SSH link available while the agent finishes preflight, builds the image, verifies it and investigates the prior failure.

If the final verified deployment requires TWRP, use this single controlled procedure only after explicit approval:

1. Confirm battery and cable stability; do not start with a low battery or a flaky USB connection.
2. Confirm the device identity in TWRP using `adb devices` and read-only properties. Ensure it is the same `beyond2lte` device.
3. Confirm `boot` resolves to the expected block device and check its exact size. Never rely on the old `/dev/block/sda14` mapping without re-reading.
4. Verify the host copy of the new BOOT image hash immediately before transfer.
5. Push the image to a temporary path on the recovery RAM disk (for example `/tmp/nuxel-pwnage68000-boot.img`). Verify the copied hash on the device where tools permit.
6. Re-check that the target is exactly the BOOT partition and that the image fits.
7. Write **only** the BOOT partition using the repository's reviewed operator procedure. Use a bounded, explicit block size; check the write exit status; run `sync`.
8. Read back the BOOT partition and compare its hash to the new image, accounting only for documented partition padding conventions. Do not proceed on a mismatch.
9. Save the TWRP command log and verification output to the evidence directory.
10. Select **Reboot → System**. Do not select Recovery. Do not hold the recovery key combination during normal boot.
11. Allow one bounded first boot attempt. Monitor USB/ADB and Wi-Fi SSH if available, but do not repeatedly power-cycle. Use the previously measured normal boot timing as context; set a generous but finite first-boot observation window (up to 180 seconds unless real evidence justifies a different limit).
12. If Nuxel boots, collect `uname -a`, boot ID, dmesg, firmware hash, MFC driver binding and service status before any MFC open.
13. If the new system does not boot, stop and restore the fresh pre-flash BOOT backup. Do not attempt another new image until the failure is diagnosed.

### 7.1 Recovery/boot failure response

If it returns to TWRP, stays black, bootloops or fails to return SSH:

- do not run the MFC diagnostic;
- do not install firmware by hand;
- do not repeat the same flash;
- capture what is available: TWRP logs, kernel/boot log, device identity and BOOT partition hash;
- restore the exact fresh BOOT backup;
- verify readback hash after rollback;
- reboot once to System;
- if rollback does not restore normal boot, stop and escalate to a separate recovery task rather than modifying more partitions.

Do not change `vbmeta`, AVB, recovery, bootloader state, EFS or modem to “make it boot.” Do not wipe data.

---

## 8. Post-boot firmware and kernel verification — still no node open

Once the patched kernel is running, validate all of the following using read-only operations:

```sh
uname -a
cat /proc/version
cat /proc/cmdline
cat /proc/sys/kernel/random/boot_id
sha256sum /lib/firmware/mfc_fw.bin
stat -c '%s %n' /lib/firmware/mfc_fw.bin
cat /sys/class/video4linux/*/name 2>/dev/null
```

Resolve the current MFC node from sysfs and verify:

- the kernel version/build identifier matches the PWNAGE-61000 build;
- the active BOOT image readback matched the deployed image;
- the firmware path is exactly `/lib/firmware/mfc_fw.bin`;
- firmware size/hash/header match the manifest;
- the DT compatible is `samsung,exynos-mfc`;
- `ip_ver` resolves to `0x1300`;
- `188d0000.mfc` is bound to `s5p-mfc`;
- the video node name is `s5p-mfc-dec0`;
- clock, power-domain and SysMMU resources are present without errors;
- dmesg shows firmware request/load and MFC system initialization without timeout, RISC halt, IRQ storm or IOMMU fault;
- the userspace diagnostic returns a state that permits the next approved operation.

Do not treat `ls /dev/video*` as sufficient. Do not open the node during this read-only stage.

If the firmware loads during probe and logs show `SYS_INIT` / RISC initialization success, record the evidence. If the firmware is not requested until `.open()`, do not infer that it loaded merely because the file exists.

If the live kernel hash, device-tree identity, firmware hash or driver binding differs from expectation, stop with a specific blocked status.

---

## 9. Owner-approved first hardware open — one operation, one session

The previous diagnostic intentionally requires a safety receipt. Preserve that design. Do not weaken receipt checks to make the first test easier.

Before creating or enabling the receipt, show the owner:

- exact handset identity;
- exact running kernel build/hash;
- exact live MFC device identity;
- exact firmware SHA-256 and size;
- exact diagnostic version/hash;
- exact command to be run;
- expected side effects and worst credible failure mode;
- exact rollback/recovery path.

The receipt must bind to the exact device identity and expected kernel/firmware/driver tuple. It must be time- or scope-limited where practical, must not be a generic permanent “allow all V4L2” switch, and must not allow camera nodes or arbitrary video devices.

After the owner explicitly approves, first run the exact inventory/query operation reported by PWNAGE-61000 from a **second SSH session** so that the control channel remains available:

```sh
nuxel-mfc-diag \
  --device /dev/video6 \
  --allow-hardware-open \
  --receipt /etc/nuxel/mfc/safety-receipt.json \
  --query-only \
  --json
```

Before executing, resolve `/dev/video6` again and replace it with the current path only if its sysfs identity is exactly the expected MFC decoder. If the device index changed, use the actual verified path; never blindly reuse `video6`.

The command should perform only the bounded query operations its source documents. Verify that it does not allocate queues, stream, start decode, touch camera nodes or load unrelated plugins. If the code's actual behavior differs, do not run it until corrected and reviewed.

### 9.1 Required first-open stop conditions

Stop immediately if:

- open blocks beyond its documented timeout;
- the process enters D state;
- SSH responsiveness drops;
- the UI or compositor stalls;
- dmesg shows IRQ wait timeout, IOMMU fault, kernel warning/oops, mutex hang or lockup;
- the driver reports IP/firmware mismatch;
- device identity or firmware receipt fails validation.

Do not kill-loop, reopen or run a second diagnostic while a first operation remains stuck. Preserve the process state, logs, kernel stacks and exact command for diagnosis. A blocked process in uninterruptible sleep may not be killable from userspace.

### 9.2 If query-only passes

Only after a clean query-only pass and owner approval for a second operation:

1. perform one explicit open/close test;
2. verify file descriptor closure, device power release and resource state;
3. inspect dmesg and MFC clocks/power state;
4. run a second query only if there were no errors;
5. do not run the helper's repeat counts yet.

Then test `--repeat 5` only after the one-open and one-close path is stable. `--repeat 20` and `--repeat 100` belong to a later stress phase and must have a distinct approval because they increase exposure to a driver hang.

---

## 10. Prove the actual vendor V4L2 ABI before queue allocation

The PWNAGE-61000 source audit classifies the decoder as a vendor-specific, nonstandard V4L2 memory-to-memory-style ABI. The report says it has OUTPUT/CAPTURE multiplanar queues, but:

- no `VIDIOC_DECODER_CMD`;
- no `V4L2_EVENT_SOURCE_CHANGE`;
- no Request API;
- no MMAP;
- OUTPUT uses USERPTR;
- CAPTURE uses DMA-BUF through `/dev/udmabuf`;
- generic FFmpeg/GStreamer M2M clients do not match the driver contract.

Reconfirm all of these against the exact running kernel's ioctl implementation and helper code before relying on them. A driver API audit from source does not prove the running device implements it as expected.

### 10.1 Diagnostic order

Do not jump to `REQBUFS` or `STREAMON`. Discover capabilities in this order:

1. `VIDIOC_QUERYCAP` and exact driver/card/bus info.
2. `VIDIOC_ENUM_FMT` for OUTPUT and CAPTURE queue types separately.
3. `VIDIOC_G_FMT` / `S_FMT` only in a later approved operation, with known-supported formats.
4. `VIDIOC_ENUM_FRAMESIZES` / `ENUM_FRAMEINTERVALS` only if supported and known safe.
5. Determine exact queue memory models from source and returned capabilities.
6. Check required udmabuf device, alignment, DMA address constraints and cache coherency.
7. Verify no unsupported ioctl is attempted.

Keep all ioctls under the same strict deadline and safety receipt. Avoid generic `v4l2-ctl` unless its behavior is fully understood and limited to the intended ioctl.

### 10.2 Build the smallest possible decoder test

The existing `nuxel-mfc-decode.c` helper is experimental and not yet hardware-proven. Audit it carefully:

- correct ioctl structs and queue types;
- OUTPUT USERPTR buffers have exact lengths, alignment and lifetime;
- CAPTURE DMA-BUF allocations are valid for this exact driver;
- `/dev/udmabuf` allocation and import are supported by the running kernel;
- every mmap/fd is closed on every error path;
- buffer ownership and queue/dequeue sequence match the driver;
- cache clean/invalidate and DMA synchronization match architecture/driver rules;
- sequence headers, EOS and drain behavior are correct for this vendor ABI;
- timeouts are bounded and do not block the Nuxel UI;
- no unsupported standard V4L2 event/decoder command is assumed;
- the helper does not accidentally use MMAP or allocate from camera queues.

Use a tiny known H.264 elementary stream or minimal test clip with a deterministic expected frame count/checksum. Start with 320x240 or the smallest valid dimensions accepted by the actual hardware, if the driver supports them. Do not use 4K as the first hardware stream.

The first test should produce one or a few decoded NV12 frames and stop cleanly. It should not start a player, GStreamer registry scan or WebKit process.

### 10.3 First real decode proof

A successful decode requires all of:

- the MFC driver is the active hardware engine;
- queue buffers were accepted and completed by the MFC path;
- no CPU software decoder was invoked;
- an output buffer was dequeued successfully;
- payload length/plane sizes are valid;
- frame count is nonzero;
- a frame checksum is generated and reproducible for the known fixture;
- a raw frame can be rendered through a simple, independently verified display/test utility;
- kernel logs show no firmware, IRQ, SysMMU or reset errors;
- the diagnostic records `MFC_DECODE_PROVEN` with input fixture hash, format, resolution, frame count, output checksum and kernel/firmware identities.

If the helper cannot prove the frame came from MFC, status remains `NOT_PROVEN`.

---

## 11. Media integration — keep it narrow and reversible

The previous report describes the intended architecture:

```text
nuxel-mfc-diag
    -> nuxel-mfc-decode (vendor-specific ABI helper)
        -> raw NV12 frames
            -> nuxel-mfc-play
                -> mpv rawvideo display path
```

This is a two-stage path and is not zero-copy. The current packaged `mpv` is an FFmpeg-free/lean build and does not have a `v4l2m2m` hardware decoder. Do not pretend an `mpv --hwdec` option can use the S10+ MFC directly.

### 11.1 Preserve default behavior

- `nuxel-mfc-play --software` must remain the default.
- Software mode must continue to run `mpv --hwdec=no`.
- Existing boot/preloading video remains `mpv --hwdec=no`.
- Do not make login, Home, lockscreen, boot animation or system services depend on MFC.
- Do not auto-probe MFC at every boot.
- Do not let a player hang the desktop if the MFC device is busy or unavailable.

### 11.2 Hardware path behavior

`nuxel-mfc-play --hardware` must refuse unless the system's proof record says a supported hardware decode has succeeded on the currently running kernel/firmware/driver tuple. A stale proof from a different kernel or firmware must not authorize playback.

The wrapper must:

- validate input codec/profile/resolution against an explicit hardware capability record;
- fall back only when configured or requested; explain the fallback reason;
- display a clear notification when hardware decode is unavailable;
- use a bounded worker process for decode;
- handle cancellation, seek, EOS and process death without leaking buffers;
- avoid synchronous work on the UI thread;
- keep diagnostics and logs privacy-safe;
- not run a global GStreamer plugin scan.

### 11.3 Do not remove the GStreamer guard globally

The guard remains in place:

```text
libgstvideo4linux2.so
libgstv4l2codecs.so
libgstkms.so
libgstopengl.so
```

The WirePlumber configuration continues to keep `hardware.video-capture = disabled`.

If a carefully isolated MFC-specific integration later needs a component currently guarded, use an explicit per-process/private plugin path or a tiny dedicated service only after proving it cannot scan camera nodes. Do not unhide all four plugins globally. `v4l2codecs` is designed for stateless decoders and is not a fit merely because MFC has V4L2-style ioctls.

---

## 12. Codec capability matrix — advertise nothing until proven

All codec and resolution rows in the previous PWNAGE-61000 report are `NOT_TESTED_ON_DEVICE`. Keep that status until a real successful test exists.

Use a staged matrix like this:

| Codec/profile | Resolution/fps | Initial priority | Status until tested |
|---|---|---:|---|
| H.264 Baseline/Main | 320x240 / low fps | 1 | NOT_TESTED |
| H.264 Main/High | 720p30 | 2 | NOT_TESTED |
| H.264 High | 1080p30 | 3 | NOT_TESTED |
| H.264 High | 1080p60 | 4 | NOT_TESTED |
| HEVC Main | 720p30 | 5 | NOT_TESTED |
| HEVC Main | 1080p30 | 6 | NOT_TESTED |
| 4K H.264/HEVC | 30 fps | 7 | NOT_TESTED |
| 4K H.264/HEVC | 60 fps | 8 | NOT_TESTED |
| 10-bit / HDR / 4:2:2 | appropriate supported mode | 9 | NOT_TESTED |

The device-tree may advertise pixel formats such as 10-bit, P010, 4:2:2 or HDR metadata. That is not proof of end-to-end decode, buffer layout, display color management, HDR tone mapping or sustained playback. Do not advertise 4K60, 10-bit, HDR or 8K simply from silicon marketing specifications or DT declarations.

Test only formats enumerated by the actual driver. Capture and record the complete negotiated formats, plane sizes, stride, alignment and framerate.

---

## 13. Performance and thermal benchmarking

The prior report explicitly records `NOT_RUN` for MFC performance. Do not make an energy, CPU, battery or 4K smoothness claim before measuring it.

After a stable real frame decode succeeds, create matched CPU-vs-MFC runs using:

- the exact same test stream and file hash;
- identical output resolution and framerate;
- same player/display configuration where practical;
- same screen brightness and background services;
- the same phone temperature range at start;
- a fixed duration (e.g. 60 seconds initially, then 10–15 minutes for sustained test);
- separate decode-only and decode-plus-display results.

Measure:

- process CPU time / per-core CPU utilization;
- total system CPU utilization;
- decoded and dropped frames;
- actual output frame rate;
- decode latency and queue wait time;
- MFC clock/power usage if readable;
- device skin/battery temperature and thermal throttling indicators;
- battery drain or energy estimate if a trustworthy source exists;
- memory bandwidth / copy cost if instrumentation exists;
- crashes, buffer errors and dropped frames.

Report mean, median, p95, min/max and run duration. Do not compare a cold software run to a warm MFC run without noting the temperature difference.

Separate these conclusions:

1. MFC hardware decode efficiency.
2. CPU cost of copying NV12 frames to the player.
3. GPU composition cost.
4. final CPU framebuffer bridge cost.

The existing display path is not zero-copy: raw NV12 can still be copied/converted and passed to mpv. A successful MFC decode does not remove `nuxel-wl-fb` CPU scanout copying.

---

## 14. GPU regression protection — do not destabilize the current Mali path

The current PWNAGE-53000 graphics report records a **partial but real Mali acceleration stack** on the S10+:

- Phoc → Mali kbase/Panfrost: PASS.
- Surfaceless GLES2/GLES 3.2 on Mali-G76 MC12: PASS.
- EGL Wayland window surface/swap: PASS.
- GTK3 `GtkGLArea` on Mali: PASS.
- Wayland linux-dmabuf v3 import of LINEAR RGB formats: PASS.
- WebKitGTK accelerated compositing in a diagnostic profile: GPU-rendered, but SHM-presented.
- WebKit DMA-BUF export/import: BLOCKED because there is no DRM/GBM device identity / `/dev/dri` path.
- Final scanout: CPU copy/scale through `nuxel-wl-fb` to `/dev/fb0` remains.
- Home, Settings and lockscreen remain configured to `software-safe` in that report; only the diagnostic app uses `gpu-rendered-shm-presented`.
- `gpu-rendered-dmabuf-presented` and `fully-accelerated` profiles are explicitly unavailable.

The graphics report measured active userspace UI CPU at about 47.0% of one core before the Mali path and 27.8–31.3% after it in the same measured scenario. This is a specific historical benchmark, not a universal speed multiplier and not proof of MFC decode.

PWNAGE-68000 must not:

- replace Mesa libraries or GLVND symlinks;
- alter the kbase EGL configuration;
- change Phoc/wlroots DMA-BUF format advertisement;
- replace `nuxel-wl-fb`;
- change framebuffer mode or panel geometry;
- alter `graphics-profile.json`;
- remove the GStreamer guard globally;
- enable DRM/KMS/camera plugins as a shortcut.

Run the existing GPU health checks before and after any kernel/BOOT deployment. Preserve:

- `FRAMES_OK`;
- `decon_pan_failed=0`;
- exactly one `/dev/fb0` writer;
- no llvmpipe regression where the approved active profile is supposed to use Mali;
- expected kbase node opens and EGL renderer identity;
- no new compositor crashes or black screens.

If a kernel change causes Mali regression, stop and report it. Do not hide it by switching to software rendering silently.

---

## 15. Automated test plan

Preserve and extend the existing test suite. Run at least:

```sh
pytest -q tests/pwnage61000
```

The previous baseline was 36 passed. New code must not reduce the baseline or weaken tests to make them pass.

Add tests for:

### 15.1 Kernel/build tests

- required patch is applied exactly once;
- missing patch or patch failure aborts the build;
- final source uses `request_firmware_direct()` at the intended call site;
- DTB `ip_ver` parsing handles big-endian property correctly;
- unknown `ip_ver` fails before MMIO/firmware access;
- config parity retains all required symbols;
- no unrelated boot config regressions;
- boot image builder embeds exact expected kernel, DTB and initramfs;
- boot image verifier catches a missing or stale DTB;
- output fits the target partition size.

### 15.2 Firmware tests

- correct exact blob passes;
- missing blob fails;
- wrong hash fails;
- wrong size fails;
- malformed header fails;
- install is atomic and idempotent;
- release/license restrictions are reflected in build/release behavior;
- no unrelated firmware path is modified.

### 15.3 Diagnostic and receipt tests

- default status/inventory never opens `/dev/video*`;
- only the exact MFC node with matching sysfs identity can be opened;
- wrong video node is rejected;
- stale kernel hash receipt rejected;
- wrong firmware hash receipt rejected;
- expired or revoked receipt rejected;
- `--allow-hardware-open` without a receipt rejected;
- no camera capture node can be authorized;
- all operations have bounded timeouts;
- JSON output conforms to `mfc-status.schema.json`;
- error states are truthful and stable.

### 15.4 Decoder helper tests

Use mocked ioctl/fd providers for:

- QUERYCAP parsing;
- unsupported formats;
- queue allocation failure;
- invalid plane sizes;
- invalid DMA-BUF fd;
- alignment failure;
- timeout and cancellation;
- EOS/drain handling;
- partial queue failure cleanup;
- fd leak detection;
- NV12 output checksum for known synthetic fixtures.

Mocks do not count as physical decode proof. Keep hardware status `NOT_TESTED_ON_DEVICE` in CI.

### 15.5 Regression tests

- default software playback remains unchanged;
- boot/preload command remains `mpv --hwdec=no`;
- GStreamer guard still disables global unsafe plugins;
- WirePlumber video-capture remains disabled;
- audio, Bluetooth, microphone, camera privacy and UI services remain unchanged;
- Mali graphics tests pass;
- framebuffer bridge remains single-writer and `FRAMES_OK`;
- rollback script only removes/restores MFC-specific files and does not touch unrelated firmware.

Do not claim full-repository pytest is green if existing tests abort or have unrelated failures. Report the exact per-suite results and distinguish pre-existing failures.

---

## 16. Status service and diagnostics contract

Keep the reported schema name `nuxel.mfc.status/1` or introduce a versioned successor only with migration tests.

The service/status API should expose honest states such as:

```text
NOT_PRESENT
BLOCKED_KERNEL
BLOCKED_FIRMWARE_MISSING
BLOCKED_FIRMWARE_HASH_MISMATCH
BLOCKED_FIRMWARE_PROVENANCE
BLOCKED_DRIVER_MISMATCH
BLOCKED_IP_VERSION
BLOCKED_RECEIPT_REQUIRED
READY_QUERY_ONLY
QUERY_FAILED
OPEN_CLOSE_PROVEN
QUEUE_SETUP_PROVEN
DECODE_PROVEN
AVAILABLE_HARDWARE_DECODE
THERMAL_LIMITED
FAILED_SAFE
```

Do not use generic `AVAILABLE` when only the firmware is installed or QUERYCAP works. The UI and player should only show hardware decode as available when a proof record matches the current kernel, DTB, firmware, driver and helper.

The proof record should include:

- source revision and patch hashes;
- running kernel build ID and image hash;
- DTB hash and `ip_ver`;
- firmware file hash, size and version identity;
- sysfs MFC device identity and resolved node;
- driver name;
- ioctl and format capabilities;
- fixture name/hash;
- negotiated codec/profile/dimensions/framerate;
- number of decoded frames;
- output format/stride/plane lengths/checksum;
- decode log hash;
- test date and device boot ID;
- whether the result was decode-only or decode-plus-display.

A proof from a previous kernel must become stale after a kernel/DTB/firmware update.

---

## 17. Rootfs/release packaging

Update the S10+ Fedora 43 image builder and package manifest so a clean image includes:

- verified MFC firmware at the exact request path, only where license policy allows;
- `nuxel-mfc-diag`;
- `nuxel-mfc-decode`;
- `nuxel-mfc-play`;
- safety receipt tooling;
- JSON schema and test-media manifest;
- status service/policy;
- MFC-only GStreamer guard integration;
- rollback script;
- operator documentation.

The package builder must not enable global video capture or restore guarded plugins. Ensure AArch64 binaries are used and record their hashes.

Create a clean rootfs candidate and offline-verify its contents. Do not flash or replace userdata/rootfs as part of this mission. The deployment to the phone should be a minimal BOOT update plus any specifically approved firmware/rootfs file staging, not a full phone reinstall.

---

## 18. Rollback design

There are two distinct rollback layers:

### 18.1 BOOT rollback

Restore the fresh exact pre-PWNAGE-68000 BOOT backup captured from the actual phone. Do not assume the historical PWNAGE-51000 rollback image is the right current rollback. Verify byte count and hash after restore.

### 18.2 MFC userspace/firmware rollback

Use the existing MFC rollback script, but inspect it before execution. It must:

- remove only the MFC firmware file installed by this mission;
- remove only PWNAGE-61000/68000 diagnostic/helper/receipt/proof files;
- restore the pre-MFC GStreamer guard state;
- leave ABOX/audio, NFC, GPS, fingerprint, camera privacy, Wi-Fi, Bluetooth and GPU components untouched;
- never remove unrelated firmware;
- never write a partition;
- require explicit target rootfs and print a dry-run plan first.

The current software player path must still work after rollback.

---

## 19. Required execution order

Do these in order. Do not jump ahead.

### Phase A — source/evidence audit (no phone state change)

1. Read the entire PWNAGE-61000 report, baseline, TODO and operator guide.
2. Verify actual repo paths, git status, source commit, patch and artifacts.
3. Inspect firmware blob and license/provenance.
4. Inspect the exact MFC driver, DTB and user helper.
5. Review all previous TWRP/BOOT deployment evidence and establish the cause of the owner's earlier failure, or explicitly report it unknown.
6. Capture a read-only live-phone baseline while it remains in normal Nuxel, if connected.
7. Confirm current GPU health/profile state without altering it.

### Phase B — finish build and BOOT package (no flash)

8. Rebuild kernel from pinned source with required patch and config.
9. Rebuild DTB.
10. Verify kernel direct-firmware behavior and all required error paths.
11. Stage exact MFC blob in the new rootfs/image candidate, not the live old-kernel `/lib/firmware`.
12. Build complete BOOT image using the known-good project packaging method.
13. Verify its contents, image header, exact sizes, partition fit and source hashes.
14. Capture/verify a fresh BOOT rollback image from the handset.
15. Run all targeted tests, including the existing 36-test suite and new deployment tests.
16. Prepare a full operator plan and stop before flash.

### Phase C — owner-approved BOOT-only deployment

17. Ask the owner for explicit approval once, with exact image hash, target partition, rollback hash and risks.
18. Only after approval, use TWRP/USB if the verified project path requires it.
19. Re-read device identity and BOOT partition mapping in TWRP.
20. Flash only BOOT, read it back and verify exact hash.
21. Select Reboot → System once.
22. If the system does not boot within the bounded window, restore the fresh BOOT backup and stop.

### Phase D — firmware/kernel read-only proof

23. Verify patched kernel is live.
24. Verify correct firmware exists at `/lib/firmware/mfc_fw.bin` and matches hash.
25. Verify MFC device-tree identity and driver binding.
26. Verify dmesg, clocks, power domain and SysMMU status.
27. Run inventory-only status and confirm `safe_open_allowed` state.
28. Prepare and present exact owner-approved safety receipt scope.
29. Stop until owner approves first hardware open.

### Phase E — first physical MFC test

30. From a second SSH session, execute the single QUERYCAP/query-only command with exact receipt.
31. Inspect result and logs.
32. If clean, request/confirm approval for one open-close test, then run it.
33. If clean, proceed to minimal queue setup.
34. Decode one known fixture frame.
35. Verify frame checksum and visual output.
36. Write hardware proof record.

### Phase F — playback integration and benchmarks

37. Enable hardware mode only in the dedicated MFC player wrapper.
38. Keep software playback default and boot preload unaffected.
39. Run H.264 small test, then 720p30, then 1080p30; add HEVC only if enumerated.
40. Benchmark software vs MFC under matched conditions.
41. Run thermal/sustained test only after short runs pass.
42. Keep 4K tests last and only where actual advertised formats permit.
43. Run GPU, display, audio, UI and boot regression checks.
44. Package rootfs files, evidence, hashes, report, rollback and operator steps.

---

## 20. Definition of done

The mission is **not** done just because the kernel builds, the firmware hash passes or `/dev/video6` exists.

### Minimum mission completion (hardware path proven)

- [ ] Exact kernel/DTB source and build hashes recorded.
- [ ] MFC fail-closed patch is present, required and compiled.
- [ ] Complete BOOT image assembled and independently verified.
- [ ] Fresh pre-flash BOOT rollback captured and verified.
- [ ] Prior TWRP failure investigated and corrective plan documented.
- [ ] Owner-approved BOOT-only update completed, if required.
- [ ] Patched kernel actually running on the S10+.
- [ ] Exact MFC firmware present and hash-verified in live rootfs.
- [ ] `s5p-mfc` bound to exact `188d0000.mfc` device.
- [ ] `ip_ver=0x1300` confirmed live.
- [ ] First safe QUERYCAP/query-only passed.
- [ ] Single open-close passed without D-state hang.
- [ ] Queue setup completed on the vendor ABI.
- [ ] At least one actual MFC-decoded frame produced.
- [ ] Decoded output checksum and fixture provenance recorded.
- [ ] No camera capture or global plugin guard was enabled.
- [ ] Software playback fallback still works.
- [ ] Boot/preload remains `mpv --hwdec=no`.
- [ ] GPU/Phoc/framebuffer invariants pass after deployment.
- [ ] Rollback path and artifacts verified.

### Extended completion (player path available)

- [ ] `nuxel-mfc-play --hardware` only runs with a valid current proof record.
- [ ] Known H.264 stream plays through MFC in the player path.
- [ ] CPU-vs-MFC benchmark completed under matched conditions.
- [ ] Supported codec/resolution matrix updated only with measured results.
- [ ] Sustained playback/thermal test completed or clearly marked not run.

### Claims must match evidence

Allowed status examples:

- `MFC_KERNEL_BUILT_NOT_DEPLOYED`
- `MFC_KERNEL_DEPLOYED_FIRMWARE_VERIFIED_NOT_OPENED`
- `MFC_QUERY_ONLY_PROVEN`
- `MFC_OPEN_CLOSE_PROVEN`
- `MFC_SINGLE_FRAME_DECODE_PROVEN`
- `MFC_H264_720P30_PROVEN`

Do not use `MFC_WORKING`, `4K_READY`, `HARDWARE_ACCELERATED` or `FULLY_ACCELERATED` without matching evidence.

---

## 21. Required final artifacts and final response

Create/update:

```text
docs/beta-finalization/live/PWNAGE-68000-MFC-REPORT.md
docs/beta-finalization/live/PWNAGE-68000-MFC-OPERATOR.md
docs/beta-finalization/live/PWNAGE-68000-MFC-ROLLBACK.md
docs/beta-finalization/live/evidence/pwnage-68000/
```

Include:

- source commit and clean/dirty status;
- complete kernel/DTB/BOOT/rootfs artifact hashes;
- firmware origin, license, size and hash;
- actual live kernel version and boot ID;
- BOOT partition path/size and pre/post/rollback hashes;
- exact TWRP steps used if performed;
- exact reason the previous attempt failed, or explicitly unknown;
- MFC sysfs/node identity;
- diagnostic result and every ioctl tested;
- queue memory model and buffer layout;
- decoded fixture hash, codec/profile/dimensions, frame count and checksum;
- performance/thermal results or `NOT_RUN`;
- GPU regression status;
- software fallback proof;
- all tests and exact pass/fail counts;
- rollback steps and verified recovery image hash;
- anything not tested, blocked or only inferred.

The final response must start with a plain status such as:

```text
MFC STATUS: <exact state>
PATCHED KERNEL LIVE: YES/NO
FIRMWARE LIVE + VERIFIED: YES/NO
VIDEO NODE OPENED: YES/NO
FIRST FRAME DECODED: YES/NO
HARDWARE PLAYBACK: YES/NO
TWRP/BOOT FLASH PERFORMED: YES/NO
GPU ACCELERATION: PARTIAL / FULL / REGRESSED (with evidence)
```

Then answer:

1. What was actually changed?
2. What was built and with which hashes?
3. What is live on the phone now?
4. Did the phone enter TWRP? Why or why not?
5. Was anything flashed? Which partition, exact hash and readback result?
6. Did `/dev/video6` (or the resolved MFC node) get opened? If so, what exact ioctl/queue tests passed?
7. Was a real frame decoded by MFC? Show fixture and checksum evidence.
8. What codecs/resolutions are genuinely proven?
9. What CPU/thermal improvement was measured?
10. Did GPU/Phoc/framebuffer behavior remain healthy?
11. What remains blocked, and what exact owner action is needed next?
12. Where are the operator, report, evidence and rollback files?

Do not hide an unsuccessful boot, failed ioctl, decoder timeout, incomplete deployment or lack of physical proof behind a successful build summary.

---

## 22. Agent behavior: decisive, cautious and implementation-oriented

- Implement and test the remaining work. Do not stop after analysis.
- Do not ask the owner questions that can be answered from the current checkout, logs or the supplied report.
- Do not wait for later/background work; complete all work possible in this run.
- Do not claim access to the handset if it is not connected.
- Do not flash, reboot, install live firmware or open the MFC node without the approval gates above.
- Do not interpret “make the prompt” as authorization to perform device operations.
- If a hardware-only phase is blocked, finish all build, test, packaging and operator preparation, then provide one concise exact next action for the owner.
- If a task has to stop at an approval boundary, make that boundary explicit and preserve all artifacts.
- Do not sacrifice existing Nuxel functions to make MFC appear functional.
- Do not change GPU acceleration, panel configuration, framebuffer bridge, TEE, NFC, GPS, fingerprint, modem or bootloader code outside a direct, proven dependency.

**Ultimate goal:** Nuxel on the S10+ must decode real H.264/HEVC video using the Exynos 9820's dedicated MFC safely, measurably and repeatably—without sacrificing the working desktop, the existing Mali graphics path, or the phone's ability to boot and recover.
