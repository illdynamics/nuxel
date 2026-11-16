# FULL PWNAGE — Nuxel Samsung Galaxy S10+ Exynos Camera Bring-up, Secure Permissions, PipeWire/XDG Portal and App Integration

the full camera pack with all you need is located in ./cam

**Target:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 / `universal9820`  
**OS:** Nuxel, Fedora-derived ARM64 userspace  
**Kernel baseline:** Samsung downstream Linux 4.14.253 (`Linux4/android_kernel_samsung_exynos9820`, pinned by the repo)  
**Starting device state:** TWRP recovery connected over USB/ADB  
**Owner-authorized recovery flow:** build the kernel/boot candidate and flash through the repository's verified S10+ scripts; reboot; an automatic return to TWRP means the Nuxel boot attempt failed; investigate, repair and retry. When the phone reaches Nuxel, connect over Wi-Fi SSH using the exact owner-provided key and address below.  
**Owner SSH target:** `root@192.168.178.167`  
**Owner SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa` (private key; never print, copy into repo, upload, or include in logs)  
**Scope:** all five camera modules where physically supported, at minimum rear-main + front-main real preview/stills/video, a real native Nuxel Camera app, standard camera access for compatible apps such as ZapZap and Ferdium, Permission Manager integration, privacy indicator, and truthful deployment/test evidence.

---

# 0. MISSION — REAL FRAMES, NOT CAMERA NODE ENUMERATION

Bring up the actual built-in S10+ camera pipeline under Nuxel. Do not stop at a sensor driver being bound, a `/dev/video*` node existing, a camera Settings tile, or a UI that opens. The final acceptance requires real frames from the handset's physical camera sensors, visible in the Nuxel Camera app and available through the standard Linux camera application path to compatible apps.

The current repository snapshot is not a blank slate. It already contains:

- a Samsung downstream Exynos FIMC-IS 4.14.253 kernel with five observed sensor modules bound;
- dozens of Samsung `exynos-fimc-is-*` video nodes;
- OIS actuator/controller and EEPROM driver probe evidence;
- SMC secure-camera `SETENV/INIT` handshake evidence;
- camera policy/config, diagnostic tooling, Camera and Photos PWAs, a native GTK camera shell, a private `org.nuxel.Camera` broker, file-backed media storage, bridge/API verbs and offline tests;
- an existing canonical `camera` permission and a Camera label in Permission Manager.

But the previous hardware verdict is `BLOCKED_FIRMWARE`: no actual camera frame has been produced; expected sensor/ISP firmware and setfiles are absent from the Nuxel filesystem; no `/dev/media*` or `/dev/v4l-subdev*` graph was observed; and standard capture ioctls on the examined Samsung nodes fail (`VIDIOC_S_FMT` returns `ENOTTY`, `REQBUFS`/`QUERYBUF` return `EINVAL`). The existing portal is a **private** broker, not a complete standard XDG Camera portal.

Treat all of those as snapshot findings that must be rechecked against the phone currently connected to TWRP and the running Nuxel build. Do not invent progress or downgrade a blocker without new evidence.

## 0.1 Definition of DONE

The task is complete only when all applicable conditions below pass:

- [ ] Device identity is positively verified as SM-G975F / `beyond2lte` / Exynos 9820.
- [ ] Exact FIMC-IS kernel driver, sensor topology, private ioctl/control ABI, firmware loader, sensor setfile requests, clock/power/GPIO/reset/MIPI sequence and DMA path are identified from the pinned downstream source and live evidence.
- [ ] Genuine, exact-target Samsung sensor/ISP firmware, setfiles and required tuning/calibration inputs are obtained from a legitimate matching source, integrity-checked and used without modification or cross-device substitution.
- [ ] The primary rear-main S5K2L4 sensor produces a genuine live preview and decoded still frame.
- [ ] The front-main S5K3J1 sensor produces a genuine live preview and decoded still frame.
- [ ] Rear tele S5K3M3 and rear ultra-wide S5K3P9 work if their actual module/power topology and supplied vendor support permit; any unsupported lens is separately explained with evidence.
- [ ] The S5K4H7 front IR/depth sensor is classified and handled safely as a depth/IR sensor; do not expose an IR feed as an ordinary RGB camera or bypass its privacy/security requirements.
- [ ] At least 100 consecutive frames per accepted main camera stream complete without kernel oops, memory corruption, DMA errors, buffer starvation or thermal instability.
- [ ] Photo capture writes a valid, decodable still to the existing file-backed media store.
- [ ] A 10-second or longer video recording completes and plays back; mic capture is separately permission-gated and does not get enabled implicitly.
- [ ] Actual native Nuxel Camera app opens and displays the live physical camera image on the phone. The owner can see the live preview and take a real picture.
- [ ] Standard PipeWire/XDG Desktop Portal camera access works for compatible clients; a private Nuxel broker is not represented as the freedesktop portal.
- [ ] ZapZap and Ferdium are discovered by their actual installed package/app IDs and individually tested with the physical camera where those installed builds support Linux camera access.
- [ ] Permission Manager grants/denies/revokes the canonical camera capability, and the actual acquisition path enforces the decision. Apps do not receive direct unrestricted `/dev/video*` access as a shortcut.
- [ ] A visible camera-in-use indicator is active for every preview/recording session and always clears on release, app exit, lock, denial or provider failure.
- [ ] Privacy OFF/blocked state prevents new streams and terminates an active stream according to policy. Provider errors fail closed.
- [ ] The boot/flash process reaches Nuxel after the verified image is flashed. The current boot image is backed up and the recovery path remains viable.
- [ ] Live userspace changes are deployed over Wi-Fi SSH after boot, with exact target identity, before/after hashes and rollback evidence.
- [ ] The final reports and a combined reflash manifest are complete.

A sensor binding, device node, successful firmware `stat`, a test-pattern frame, USB webcam frame, portal service status, fake `getUserMedia`, or `CameraCapture` call with caller-supplied bytes is not proof that the S10+ built-in camera works.

## 0.2 Truth labels

Use these exact statuses, with subcomponent-specific status where helpful:

- `PASS_PHYSICAL` — actual built-in sensor frame/path was physically captured and verified.
- `PASS_BUILD` — compiled only; no hardware claim.
- `PASS_RUNTIME` — service/device initialized; no frame claim.
- `BLOCKED_FIRMWARE` — exact matching setfile/ISP firmware is still missing or rejected.
- `BLOCKED_VENDOR_ABI` — private Samsung ABI is not sufficiently understood or callable.
- `BLOCKED_PIPELINE` — no working kernel-to-userspace capture pipeline.
- `BLOCKED_PORTAL` — camera source works but standard portal/PipeWire handoff is incomplete.
- `BLOCKED_PERMISSION` — permission decision is not enforced by the real device access path.
- `BLOCKED_COMPATIBILITY` — a named third-party app cannot use the available Linux camera protocol.
- `FAIL` — a test ran and failed.
- `NOT_TESTED` — not run; identify missing operator/hardware/application prerequisite.
- `UNSUPPORTED` — limitation is demonstrated by exact hardware/software evidence.

Never report READY because one firmware candidate is present or a media node exists. Never change a status based solely on a code comment or mock fixture.

---

# 1. OPERATOR WORKFLOW, TWRP START, FLASH/BOOT LOOP AND SSH HANDOFF

The owner will have the phone physically booted into TWRP and connected over USB before launching you.

## 1.1 Start state and target confirmation

Before any write:

1. Run `adb devices -l`; select exactly the intended recovery device. Refuse if multiple devices exist and no explicit serial is selected.
2. Read TWRP properties and device tree: `getprop`, `/proc/device-tree/model`, `/proc/device-tree/compatible`, board/hardware identity, and available partition metadata.
3. Verify the device is the SM-G975F `beyond2lte` Exynos 9820. TWRP may not expose the same Android properties as a normal Nuxel boot; use multiple independent identity signals. Do not override a failed identity check with `--force`.
4. Record `adb shell uname -a`, TWRP version, mount table, recovery log paths and pstore/last-kmsg availability.
5. Inspect `git status --short --branch`, commit, all current working-tree changes and any concurrent NFC/USBNET/GPS/SSP changes before editing.

Do not automatically mount any partition. If the stock vendor/system filesystem is not mounted in TWRP, use a verified TWRP read-only mount flow only after positively identifying the correct partition. Do not mount vendor or system read-write for acquisition.

## 1.2 Back up the current boot state

Before flashing:

- read the exact current boot partition using the repository's approved backup method or a verified read-only `adb exec-out` read;
- save a host-side copy and SHA256;
- inspect the image header/format/DTB/ramdisk using the repo tools;
- record current kernel release, boot image provenance and partition size;
- verify the backup can be read and its checksum matches;
- record the exact target boot partition path from the live PIT/by-name inventory.

Do not back up by guessing `/dev/block` paths. Do not write to any partition outside the explicit verified target described below.

## 1.3 Important reflash-plan discrepancy: verify A/B before trusting it

`REFLASH-PLAN.md` describes an inactive A/B slot strategy, but the existing S10+ TWRP flash helper writes the Nuxel boot image to a single `boot` partition and defaults `--rootfs` to the `userdata` partition. The S10+ must not be assumed to have A/B slots simply because the plan mentions slots.

Inspect the actual PIT, `/dev/block/platform/13d60000.ufs/by-name`, `getprop ro.boot.slot_suffix`, mount table and exact Nuxel rootfs layout. Update the plan if its A/B assumption does not match the physical device. Do not invent `_a`/`_b` partitions or switch slots where none exist.

**Critical:** `boot/s10plus/flash.sh --rootfs` defaults to `userdata`; a rootfs flash can overwrite user data. Do not use `--rootfs`, `--rootfs-partition userdata`, Heimdall `--USERDATA`, or any full filesystem write unless the exact image format, target partition, backup, data impact and operator authorization are explicitly verified. The owner has authorized the boot/kernel flash and the camera bring-up, not a blind userdata wipe.

## 1.4 Required build and flash tools

Inspect and use the repository's existing scripts, not generic fastboot instructions:

- `kernel/s10plus/build-kernel.sh` — authoritative pinned kernel build and patch application.
- `boot/s10plus/build-candidate.sh` — packages a kernel/DTB into a verified S10+ boot image from a known-good base.
- `tools/s10plus/verify-boot-image.py` — boot-image validation gate.
- `boot/s10plus/flash.sh` — TWRP + ADB path, only after inspecting every target/write in the script and satisfying the device inventory gate.
- `boot/s10plus/flash-heimdall.sh` — Download Mode only; not the current TWRP path.
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` — existing Tri-Link SSH/console launcher.
- `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` — existing verified deploy tool; inspect its transport (the current implementation is serial-console framed deployment, not automatically Wi-Fi SSH).

The kernel build script emits `Image.gz` and DTBs, but the boot-candidate packer expects the correct **raw arm64 Image** format. Use the validated uncompressed `arch/arm64/boot/Image` or carefully decompress/verify the exact payload. Never put an `Image.gz` payload into the boot container as if it were the raw Image; the repo documents a prior silent-load regression caused by that mistake.

Follow the normal kernel patch sort/application order. The builder treats patches as optional unless a `.required` sidecar exists. Do not make an unverified camera patch mandatory. Never overwrite, reset, stash, clean or revert concurrent NFC/USBNET changes.

## 1.5 Flash/boot acceptance loop — owner explicitly authorizes this flow

The owner explicitly authorizes you to build the kernel/boot candidate, flash it with the verified repo script, and reboot from the starting TWRP state.

Before the flash, require all of these:

- exact target identity verified;
- complete `docs/s10plus-device-inventory.md` critical fields; do not bypass the gate with `--force`;
- current boot image backed up with matching SHA256;
- the next candidate passes `verify-boot-image.py` and partition-capacity gate;
- all required current NFC/other kernel work that is ready has been integrated in the same coherent build (do not do a camera-only flash if the concurrent NFC batch is part of the owner's one-reflash goal and its patch is already ready);
- the selected script and target partition have been source-reviewed;
- no rootfs/userdata write is implicit.

Use the TWRP path through `boot/s10plus/flash.sh` only after confirming its exact command and arguments. Do not use generic Android fastboot on this phone. Do not flash recovery, bootloader, modem/baseband, EFS, persist, PIT, userdata, or unrelated partitions.

After flashing, reboot using the existing tested recovery procedure. Then observe:

**If the phone returns to TWRP after the reboot, that means the Nuxel boot attempt failed. The owner did not manually put it back into TWRP.** Treat it as a boot failure/bootloop/hang/crash, not as success. Collect the TWRP logs, pstore/ramoops, `/proc/last_kmsg` if available, boot image checksum, kernel/initramfs errors, DTB messages, filesystem mount errors, firmware-load failures and watchdog/panic evidence. Identify the root cause, modify the source, rebuild, pass all gates, flash the corrected boot image and reboot again.

If the phone remains on a black Samsung logo or is not reachable, treat that as a failed/incomplete boot too. Use the repo's bootloop decision tree and recovery diagnostics; do not repeat the same failing image.

**If the phone reaches the Nuxel environment and its boot health check proves userspace is running, that is a successful Nuxel boot.** Do not call a splash frame alone proof. Move to the Wi-Fi SSH handoff below.

Continue evidence-based repair/reflash while TWRP and the known-good boot backup remain available. Do not reflash an identical image. After three consecutive attempts with the same unresolved failure mechanism, stop repeating and perform a deeper root-cause review. If the recovery route or partition identity becomes uncertain, stop before another write.

## 1.6 Wi-Fi SSH handoff after Nuxel boots

Once Nuxel has booted, connect over Wi-Fi SSH to the exact owner-provided address:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167

more info:

# Nuxel camera bring-up — repository analysis and agent pack

ZIP verified

13 November 2026 · 270 KB

Download Nuxel-Camera-Pwnage-Pack.zip

Also available separately:

- full-pwnage-cam.md
- pwnage-cam.md
- Read-only camera asset acquisition helper
- Pack README

ZIP SHA256: `e16978c99659a5089985b24a2c494f99c1460039e2d076e76327327aaae6a57d` · archive integrity test passed · acquisition helper Python syntax check passed

## What the repo actually tells us

This is a much more substantial camera bring-up than simply enabling a missing kernel option.

The low-level hardware support is partly there already. The repository's camera report records five bound sensor modules:

| Camera role     | Reported sensor | Initial priority                 |
| --------------- | --------------- | -------------------------------- |
| Rear main       | Samsung S5K2L4  | First camera to get working      |
| Rear telephoto  | Samsung S5K3M3  | Next, if supported               |
| Rear ultra-wide | Samsung S5K3P9  | Next, if supported               |
| Front main      | Samsung S5K3J1  | Required                         |
| Front IR/depth  | Samsung S5K4H7  | Separate depth/IR classification |

There are also numerous Exynos FIMC-IS video nodes, MIPI/CSI and OIS-related driver evidence, EEPROM driver probes and a reported secure-camera initialization handshake.

But the pipeline has never produced a verified physical frame. The recorded blocker is `BLOCKED_FIRMWARE`. Expected Samsung sensor setfiles and ISP/FIMC-IS firmware are missing, the previous capture environment did not expose `/dev/media*` or `/dev/v4l-subdev*`, and the generic V4L2 ioctls tried against the examined Samsung nodes failed. A video node is not necessarily a capture node.

The tiny `s5k2l4_setfile.bin` in the test fixture is only three bytes. It is a placeholder, not firmware. The ZIP deliberately excludes it as a deployable asset and tells the agent to reject it.

### The permission manager is not starting from zero

The canonical high-risk `camera` capability and its Permission Manager label already exist. The outstanding work is to make the permission effective across the real camera path:

- distinguish live camera preview/capture from reading saved Photos;
- verify aliases and app declarations against the central permission store;
- fix the camera privacy provider's fail-open error handling;
- ensure the native camera app, PWA and third-party clients all go through an authorized provider;
- reflect every active camera session in the system-wide privacy indicator.

The prompt explicitly prevents the agent from adding a second duplicate Camera permission just to make a UI checkbox appear.

### ZapZap and Ferdium need a standard Linux camera path

The current private `org.nuxel.Camera` broker is not the standard freedesktop camera portal. The required compatibility path uses the XDG Camera portal's `AccessCamera` request and `OpenPipeWireRemote` handoff, with PipeWire/WirePlumber enforcing app-scoped camera access. These are real protocol requirements, not just naming conventions.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://flatpak.github.io\&sz=32)

XDG Desktop Portal+1



The prompt tells the agent to identify the actual installed ZapZap and Ferdium packages and runtimes before testing them. It must not assume Flatpak, Electron or WebKit packaging, and must not disable sandboxing or grant blanket device access to get a test to pass.

## What is in the ZIP

The pack includes both prompts, selected camera/reflash/kernel/permission/app source snapshots from your uploaded repository, camera reports and regression tests, plus a read-only ADB acquisition helper.

The helper starts with inventory-only mode and can collect matching ordinary files from already-mounted stock vendor/system/odm filesystem paths after review. It does not mount, flash, reboot or use `dd`, and excludes user data, EFS, persist, raw EEPROM, TEE memory and keystore material.

There are no genuine Samsung camera firmware or calibration blobs in the uploaded repo to bundle. I have not fabricated any. The agent is instructed to obtain only matching SM-G975F Exynos 9820 assets from a legitimate source and verify their provenance, hashes, ABI and actual driver consumers. If Samsung's required files are not available, it must report the exact remaining blocker rather than substituting another device's blobs.

## Your requested agent workflow is included

The two prompts explicitly say:

1. Start with the phone in TWRP connected over USB.
2. Verify device identity, current boot backup and actual partition topology.
3. Inspect and use the repo's kernel build, boot-candidate and guarded TWRP flash scripts.
4. If reboot returns automatically to TWRP, treat that as a failed Nuxel boot; gather evidence, fix the cause, rebuild, reflash and retry. Do not blindly repeat an identical image.
5. Once Nuxel boots, connect over Wi-Fi SSH to `root@192.168.178.167` using `~wicked/.ssh/wicked_wqn_id_rsa`, retaining normal host-key verification.
6. Deploy safe userspace changes with backups, staged transfer, SHA256 verification and rollback.
7. Open the actual native Nuxel Camera app on the phone and show a real physical preview.
8. Test the rear and front cameras, then other modules where supported.
9. Test ZapZap and Ferdium through the standard portal path.
10. Preserve NFC and other concurrent work so kernel changes can be part of the single coherent reflash batch.

One important guardrail: the repo's flash helper has a `--rootfs` option whose default target is `userdata`. The prompt explicitly forbids treating that as a normal camera deployment option or writing it blindly. It also tells the agent to verify whether the S10+ really has A/B slots rather than trusting the reflash plan's wording.

## 1. `full-pwnage-cam.md`

Save this in the Nuxel repository root. It is the full implementation and acceptance specification.

````
# FULL PWNAGE — Nuxel Samsung Galaxy S10+ Exynos Camera Bring-up, Secure Permissions, PipeWire/XDG Portal and App Integration

**Target:** Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 / `universal9820`
**OS:** Nuxel, Fedora-derived ARM64 userspace
**Kernel baseline:** Samsung downstream Linux 4.14.253 (`Linux4/android_kernel_samsung_exynos9820`, pinned by the repo)
**Starting device state:** TWRP recovery connected over USB/ADB
**Owner-authorized recovery flow:** build the kernel/boot candidate and flash through the repository's verified S10+ scripts; reboot; an automatic return to TWRP means the Nuxel boot attempt failed; investigate, repair and retry. When the phone reaches Nuxel, connect over Wi-Fi SSH using the exact owner-provided key and address below.
**Owner SSH target:** `root@192.168.178.167`
**Owner SSH key:** `~wicked/.ssh/wicked_wqn_id_rsa` (private key; never print, copy into repo, upload, or include in logs)
**Scope:** all five camera modules where physically supported, at minimum rear-main + front-main real preview/stills/video, a real native Nuxel Camera app, standard camera access for compatible apps such as ZapZap and Ferdium, Permission Manager integration, privacy indicator, and truthful deployment/test evidence.

---

# 0. MISSION — REAL FRAMES, NOT CAMERA NODE ENUMERATION

Bring up the actual built-in S10+ camera pipeline under Nuxel. Do not stop at a sensor driver being bound, a `/dev/video*` node existing, a camera Settings tile, or a UI that opens. The final acceptance requires real frames from the handset's physical camera sensors, visible in the Nuxel Camera app and available through the standard Linux camera application path to compatible apps.

The current repository snapshot is not a blank slate. It already contains:

- a Samsung downstream Exynos FIMC-IS 4.14.253 kernel with five observed sensor modules bound;
- dozens of Samsung `exynos-fimc-is-*` video nodes;
- OIS actuator/controller and EEPROM driver probe evidence;
- SMC secure-camera `SETENV/INIT` handshake evidence;
- camera policy/config, diagnostic tooling, Camera and Photos PWAs, a native GTK camera shell, a private `org.nuxel.Camera` broker, file-backed media storage, bridge/API verbs and offline tests;
- an existing canonical `camera` permission and a Camera label in Permission Manager.

But the previous hardware verdict is `BLOCKED_FIRMWARE`: no actual camera frame has been produced; expected sensor/ISP firmware and setfiles are absent from the Nuxel filesystem; no `/dev/media*` or `/dev/v4l-subdev*` graph was observed; and standard capture ioctls on the examined Samsung nodes fail (`VIDIOC_S_FMT` returns `ENOTTY`, `REQBUFS`/`QUERYBUF` return `EINVAL`). The existing portal is a **private** broker, not a complete standard XDG Camera portal.

Treat all of those as snapshot findings that must be rechecked against the phone currently connected to TWRP and the running Nuxel build. Do not invent progress or downgrade a blocker without new evidence.

## 0.1 Definition of DONE

The task is complete only when all applicable conditions below pass:

- [ ] Device identity is positively verified as SM-G975F / `beyond2lte` / Exynos 9820.
- [ ] Exact FIMC-IS kernel driver, sensor topology, private ioctl/control ABI, firmware loader, sensor setfile requests, clock/power/GPIO/reset/MIPI sequence and DMA path are identified from the pinned downstream source and live evidence.
- [ ] Genuine, exact-target Samsung sensor/ISP firmware, setfiles and required tuning/calibration inputs are obtained from a legitimate matching source, integrity-checked and used without modification or cross-device substitution.
- [ ] The primary rear-main S5K2L4 sensor produces a genuine live preview and decoded still frame.
- [ ] The front-main S5K3J1 sensor produces a genuine live preview and decoded still frame.
- [ ] Rear tele S5K3M3 and rear ultra-wide S5K3P9 work if their actual module/power topology and supplied vendor support permit; any unsupported lens is separately explained with evidence.
- [ ] The S5K4H7 front IR/depth sensor is classified and handled safely as a depth/IR sensor; do not expose an IR feed as an ordinary RGB camera or bypass its privacy/security requirements.
- [ ] At least 100 consecutive frames per accepted main camera stream complete without kernel oops, memory corruption, DMA errors, buffer starvation or thermal instability.
- [ ] Photo capture writes a valid, decodable still to the existing file-backed media store.
- [ ] A 10-second or longer video recording completes and plays back; mic capture is separately permission-gated and does not get enabled implicitly.
- [ ] Actual native Nuxel Camera app opens and displays the live physical camera image on the phone. The owner can see the live preview and take a real picture.
- [ ] Standard PipeWire/XDG Desktop Portal camera access works for compatible clients; a private Nuxel broker is not represented as the freedesktop portal.
- [ ] ZapZap and Ferdium are discovered by their actual installed package/app IDs and individually tested with the physical camera where those installed builds support Linux camera access.
- [ ] Permission Manager grants/denies/revokes the canonical camera capability, and the actual acquisition path enforces the decision. Apps do not receive direct unrestricted `/dev/video*` access as a shortcut.
- [ ] A visible camera-in-use indicator is active for every preview/recording session and always clears on release, app exit, lock, denial or provider failure.
- [ ] Privacy OFF/blocked state prevents new streams and terminates an active stream according to policy. Provider errors fail closed.
- [ ] The boot/flash process reaches Nuxel after the verified image is flashed. The current boot image is backed up and the recovery path remains viable.
- [ ] Live userspace changes are deployed over Wi-Fi SSH after boot, with exact target identity, before/after hashes and rollback evidence.
- [ ] The final reports and a combined reflash manifest are complete.

A sensor binding, device node, successful firmware `stat`, a test-pattern frame, USB webcam frame, portal service status, fake `getUserMedia`, or `CameraCapture` call with caller-supplied bytes is not proof that the S10+ built-in camera works.

## 0.2 Truth labels

Use these exact statuses, with subcomponent-specific status where helpful:

- `PASS_PHYSICAL` — actual built-in sensor frame/path was physically captured and verified.
- `PASS_BUILD` — compiled only; no hardware claim.
- `PASS_RUNTIME` — service/device initialized; no frame claim.
- `BLOCKED_FIRMWARE` — exact matching setfile/ISP firmware is still missing or rejected.
- `BLOCKED_VENDOR_ABI` — private Samsung ABI is not sufficiently understood or callable.
- `BLOCKED_PIPELINE` — no working kernel-to-userspace capture pipeline.
- `BLOCKED_PORTAL` — camera source works but standard portal/PipeWire handoff is incomplete.
- `BLOCKED_PERMISSION` — permission decision is not enforced by the real device access path.
- `BLOCKED_COMPATIBILITY` — a named third-party app cannot use the available Linux camera protocol.
- `FAIL` — a test ran and failed.
- `NOT_TESTED` — not run; identify missing operator/hardware/application prerequisite.
- `UNSUPPORTED` — limitation is demonstrated by exact hardware/software evidence.

Never report READY because one firmware candidate is present or a media node exists. Never change a status based solely on a code comment or mock fixture.

---

# 1. OPERATOR WORKFLOW, TWRP START, FLASH/BOOT LOOP AND SSH HANDOFF

The owner will have the phone physically booted into TWRP and connected over USB before launching you.

## 1.1 Start state and target confirmation

Before any write:

1. Run `adb devices -l`; select exactly the intended recovery device. Refuse if multiple devices exist and no explicit serial is selected.
2. Read TWRP properties and device tree: `getprop`, `/proc/device-tree/model`, `/proc/device-tree/compatible`, board/hardware identity, and available partition metadata.
3. Verify the device is the SM-G975F `beyond2lte` Exynos 9820. TWRP may not expose the same Android properties as a normal Nuxel boot; use multiple independent identity signals. Do not override a failed identity check with `--force`.
4. Record `adb shell uname -a`, TWRP version, mount table, recovery log paths and pstore/last-kmsg availability.
5. Inspect `git status --short --branch`, commit, all current working-tree changes and any concurrent NFC/USBNET/GPS/SSP changes before editing.

Do not automatically mount any partition. If the stock vendor/system filesystem is not mounted in TWRP, use a verified TWRP read-only mount flow only after positively identifying the correct partition. Do not mount vendor or system read-write for acquisition.

## 1.2 Back up the current boot state

Before flashing:

- read the exact current boot partition using the repository's approved backup method or a verified read-only `adb exec-out` read;
- save a host-side copy and SHA256;
- inspect the image header/format/DTB/ramdisk using the repo tools;
- record current kernel release, boot image provenance and partition size;
- verify the backup can be read and its checksum matches;
- record the exact target boot partition path from the live PIT/by-name inventory.

Do not back up by guessing `/dev/block` paths. Do not write to any partition outside the explicit verified target described below.

## 1.3 Important reflash-plan discrepancy: verify A/B before trusting it

`REFLASH-PLAN.md` describes an inactive A/B slot strategy, but the existing S10+ TWRP flash helper writes the Nuxel boot image to a single `boot` partition and defaults `--rootfs` to the `userdata` partition. The S10+ must not be assumed to have A/B slots simply because the plan mentions slots.

Inspect the actual PIT, `/dev/block/platform/13d60000.ufs/by-name`, `getprop ro.boot.slot_suffix`, mount table and exact Nuxel rootfs layout. Update the plan if its A/B assumption does not match the physical device. Do not invent `_a`/`_b` partitions or switch slots where none exist.

**Critical:** `boot/s10plus/flash.sh --rootfs` defaults to `userdata`; a rootfs flash can overwrite user data. Do not use `--rootfs`, `--rootfs-partition userdata`, Heimdall `--USERDATA`, or any full filesystem write unless the exact image format, target partition, backup, data impact and operator authorization are explicitly verified. The owner has authorized the boot/kernel flash and the camera bring-up, not a blind userdata wipe.

## 1.4 Required build and flash tools

Inspect and use the repository's existing scripts, not generic fastboot instructions:

- `kernel/s10plus/build-kernel.sh` — authoritative pinned kernel build and patch application.
- `boot/s10plus/build-candidate.sh` — packages a kernel/DTB into a verified S10+ boot image from a known-good base.
- `tools/s10plus/verify-boot-image.py` — boot-image validation gate.
- `boot/s10plus/flash.sh` — TWRP + ADB path, only after inspecting every target/write in the script and satisfying the device inventory gate.
- `boot/s10plus/flash-heimdall.sh` — Download Mode only; not the current TWRP path.
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` — existing Tri-Link SSH/console launcher.
- `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` — existing verified deploy tool; inspect its transport (the current implementation is serial-console framed deployment, not automatically Wi-Fi SSH).

The kernel build script emits `Image.gz` and DTBs, but the boot-candidate packer expects the correct **raw arm64 Image** format. Use the validated uncompressed `arch/arm64/boot/Image` or carefully decompress/verify the exact payload. Never put an `Image.gz` payload into the boot container as if it were the raw Image; the repo documents a prior silent-load regression caused by that mistake.

Follow the normal kernel patch sort/application order. The builder treats patches as optional unless a `.required` sidecar exists. Do not make an unverified camera patch mandatory. Never overwrite, reset, stash, clean or revert concurrent NFC/USBNET changes.

## 1.5 Flash/boot acceptance loop — owner explicitly authorizes this flow

The owner explicitly authorizes you to build the kernel/boot candidate, flash it with the verified repo script, and reboot from the starting TWRP state.

Before the flash, require all of these:

- exact target identity verified;
- complete `docs/s10plus-device-inventory.md` critical fields; do not bypass the gate with `--force`;
- current boot image backed up with matching SHA256;
- the next candidate passes `verify-boot-image.py` and partition-capacity gate;
- all required current NFC/other kernel work that is ready has been integrated in the same coherent build (do not do a camera-only flash if the concurrent NFC batch is part of the owner's one-reflash goal and its patch is already ready);
- the selected script and target partition have been source-reviewed;
- no rootfs/userdata write is implicit.

Use the TWRP path through `boot/s10plus/flash.sh` only after confirming its exact command and arguments. Do not use generic Android fastboot on this phone. Do not flash recovery, bootloader, modem/baseband, EFS, persist, PIT, userdata, or unrelated partitions.

After flashing, reboot using the existing tested recovery procedure. Then observe:

**If the phone returns to TWRP after the reboot, that means the Nuxel boot attempt failed. The owner did not manually put it back into TWRP.** Treat it as a boot failure/bootloop/hang/crash, not as success. Collect the TWRP logs, pstore/ramoops, `/proc/last_kmsg` if available, boot image checksum, kernel/initramfs errors, DTB messages, filesystem mount errors, firmware-load failures and watchdog/panic evidence. Identify the root cause, modify the source, rebuild, pass all gates, flash the corrected boot image and reboot again.

If the phone remains on a black Samsung logo or is not reachable, treat that as a failed/incomplete boot too. Use the repo's bootloop decision tree and recovery diagnostics; do not repeat the same failing image.

**If the phone reaches the Nuxel environment and its boot health check proves userspace is running, that is a successful Nuxel boot.** Do not call a splash frame alone proof. Move to the Wi-Fi SSH handoff below.

Continue evidence-based repair/reflash while TWRP and the known-good boot backup remain available. Do not reflash an identical image. After three consecutive attempts with the same unresolved failure mechanism, stop repeating and perform a deeper root-cause review. If the recovery route or partition identity becomes uncertain, stop before another write.

## 1.6 Wi-Fi SSH handoff after Nuxel boots

Once Nuxel has booted, connect over Wi-Fi SSH to the exact owner-provided address:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
````

Resolve the `~wicked` home directory on the development host correctly if the shell/account does not expand it. Do not quote the tilde in a way that prevents expansion. Do not inspect or print the private key contents. Do not copy the key into the repository or device.

Use normal SSH host-key verification. Do not use `StrictHostKeyChecking=no`, `UserKnownHostsFile=/dev/null`, or other host-key bypasses. If the host key is unknown or changed, verify its fingerprint through the trusted USB/TWRP/console path before accepting it.

After connection, positively verify the target with `id`, `uname -a`, `/etc/os-release`, device tree model/compatible and Nuxel service state. Check that the phone is the SM-G975F currently running Nuxel—not the host or a different device.

If Nuxel boots but Wi-Fi SSH is unavailable, do not immediately classify the camera as failed or reflash again. Use the preserved USB ACM console/recovery route to diagnose networking while keeping the booted device intact.

# 2. INITIAL REPOSITORY AUDIT AND PRESERVE CURRENT WORK

Read these first, and compare them with the actual code at the current HEAD:

- `REPORT-CAMERA.md`
- `REFLASH-PLAN.md`
- `configs/nuxel/camera/camera.json`
- `configs/nuxel/privacy/camera.json`
- `docs/a52-camera/*`
- `docs/a53/CAMERA-PIPELINE-BLOCKERS.md`
- `docs/a53/FLATPAK-SANDBOX-PORTALS.md`
- `docs/a54-reliability/CAMERA-INSTALL.md`
- `tools/s10plus/a33/nuxel-camera-diag.sh`
- `services/nuxel-bridge/src/bridge.py`
- `services/nuxel-bridge/src/api.py`
- `services/nuxel-bridge/src/media_store.py`
- `services/nuxel-bridge/src/privacy_provider.py`
- `shell/nuxel-camera-portal/`
- `shell/nuxel-camera-native/`
- `pwa/nuxel-apps/camera-gallery/`
- `pwa/nuxel-apps/photos/`
- `shell/nuxel-shell/nuxel-permissions/capabilities.json`
- `pwa/nuxel-apps/permissions/app.js`
- `tools/s10plus/a33/verify-permissions.py`
- camera/frontend/portal/media-store regression tests under `tests/`.

Record `git status --short --branch`, `git diff --stat`, untracked files and the exact base commit. The uploaded archive is a snapshot, not the live worktree. Do not assume the current phone or live deployment matches it.

Keep work isolated or edit only owned paths. Preserve in-progress NFC changes. Coordinate shared edits to `REFLASH-PLAN.md`, kernel fragments, permission registry, bridge API and the launcher/app registry. Never use broad cleanup/reset/stash/revert commands.

# 3. HARDWARE INVENTORY AND EXACT SENSOR TOPOLOGY

The previous live inventory identified the following sensor-module strings; verify each one on the current phone:

| Role            | Previous kernel sensor  | Expected identity | Target acceptance                                         |
| --------------- | ----------------------- | ----------------- | --------------------------------------------------------- |
| Rear main       | `fimc-is_sensor_2l4@20` | S5K2L4            | First camera to bring up; mandatory real preview/still    |
| Rear tele       | `fimc-is_sensor_3m3@5A` | S5K3M3            | Real frame and lens switch, if module/runtime supports it |
| Rear ultra-wide | `fimc-is_sensor_3p9@2D` | S5K3P9            | Real frame and lens switch, if module/runtime supports it |
| Front main      | `fimc-is_sensor_3j1@10` | S5K3J1            | Mandatory real preview/still                              |
| Front IR/depth  | `fimc-is_sensor_4ha@10` | S5K4H7            | Identify as IR/depth, not ordinary RGB without proof      |

Previous kernel evidence also lists FIMC-IS core at `170e0000.fimc_is`, sensor controllers, OIS actuators (`ak737x`), OIS controller, EEPROM drivers, MIPI CSI PHYs, GDC, ION camera heaps and reserved memory. Reconfirm source paths and live probe messages.

## 3.1 Inspect the full hardware path

From the exact downstream kernel checkout, trace:

- FIMC-IS platform driver/probe and firmware request paths;
- each sensor module driver's probe, `s_stream`, mode tables, setfile names, controls and power sequencing;
- V4L2 node registration, capabilities, ioctl handlers, private ioctl numbers and vendor-specific structs;
- sensor subdevice/media-controller registration (or the exact reason it is absent);
- CSIS/MIPI receiver, DPHY, FIMC-IS, 3A, ISP, RTA/MCU and capture-node ownership;
- IOMMU, DMA-buf, ION camera heaps, reserved-memory mapping and buffer lifecycle;
- CSI lane maps, clocks, regulators, pinctrl, reset GPIOs, I2C bus/address, GPIO interrupts and module switch lines;
- OIS controller/actuator firmware and calibration dependencies;
- EEPROM calibration flow as exposed by the existing driver.

Do not guess device-tree properties or sensor register values. Do not write EEPROM, raw calibration, I2C registers, SPI registers, sensor reset lines or power GPIOs experimentally. Read-only inventory first; any hardware write must be a documented bounded operation from the exact driver/vendor initialization sequence.

## 3.2 Investigate the rear ultra-wide GPIO failure

The prior report observed `gpio_subcam_sel` and `gpio_mipi_sel` failures for the S5K3P9 path. Trace the exact DTS, GPIO lookup names, board revision and current boot log. Correct only from matching stock DTS/vendor evidence. Never assign guessed GPIO numbers or change pinctrl because another S10 variant has a similar label.

## 3.3 EEPROM versus setfile/calibration distinction

Prior docs say camera EEPROM drivers probed and calibration data is present, while separate camera setfile/ISP firmware files were missing. Reconcile these statements. Distinguish:

- factory calibration stored/read by the board's EEPROM driver;
- sensor mode setfiles;
- FIMC-IS MCU firmware;
- ISP/RTA/library firmware;
- lens/OIS firmware and calibration;
- vendor camera tuning/3A tables.

A successful EEPROM probe does not mean all sensor setfiles/tuning files are installed. Do not dump raw EEPROM bytes or overwrite factory calibration. Use the driver's supported read path and only report whether the calibrated state is accepted.

# 4. ACQUIRE GENUINE SAMSUNG CAMERA FIRMWARE — EXACT DEVICE ONLY

The uploaded Nuxel repository contains no usable proprietary S10+ camera firmware bundle. The `camera-ready` unit-test fixture has a 3-byte placeholder named `s5k2l4_setfile.bin`; it is fake test data and must never be copied into `/lib/firmware` or treated as a real setfile.

Candidate names from existing report/config include:

- `s5k2l4_setfile.bin`
- `s5k3m3_setfile.bin`
- `s5k3p9_setfile.bin`
- `s5k3j1_setfile.bin`
- `s5k4h7_setfile.bin`
- `exynos9820_camera.bin`
- `is-camera.bin`, `is-camera-3.bin`
- `fimc_is_fw_mcu.bin`, `fimc_is_lib.bin`, `fimc_is_rta*.bin`
- `camera_calibration.bin`, `setfile.bin`, exact vendor-named tuning files
- exact compatible OIS firmware/config where the driver requests it.

Derive the actual requested filenames and formats from the pinned kernel source and the matching stock userspace, not from this candidate list alone.

## 4.1 Read-only acquisition script supplied in this pack

Run on the development host while the exact phone is connected in TWRP:

```
python3 scripts/acquire-s10plus-camera-assets.py --output ./camera-acquisition
```

That is inventory-only. After reviewing the candidate paths and confirming that the connected device/partitions are the owner's exact SM-G975F stock vendor/system data, copy only allowlisted ordinary files to the host:

```
python3 scripts/acquire-s10plus-camera-assets.py --pull --output ./camera-acquisition
```

If camera calibration files are needed and the owner explicitly authorizes collecting normal files from the matching vendor/odm/system filesystem paths, use:

```
python3 scripts/acquire-s10plus-camera-assets.py --pull --include-vendor-calibration --output ./camera-acquisition
```

The helper does not mount partitions, modify the phone, reboot, flash, invoke `dd`, read `/data`, `/efs`, `/persist`, RPMB, raw EEPROM, TEE memory, keystore material, or user biometric/media data. If vendor/system partitions are not mounted in TWRP, the script reports that and stops; use a verified read-only TWRP mount procedure and rerun. Never mount them read-write just to collect files.

## 4.2 Firmware source acceptance

Only accept blobs whose provenance can be tied to:

- the owner's exact handset stock firmware/vendor image for SM-G975F / `beyond2lte` / Exynos 9820 and a compatible bootloader/firmware family; or
- a user-supplied exact matching Samsung firmware package whose model, region/CSC, build family, file version and architecture are independently verified.

An older `beyond1lte` or another Exynos 9820 model can be an inventory/search lead only. It is not automatic compatibility proof. Qualcomm S10+ firmware, Pixel firmware, different SoC generation files, random GitHub binaries, fake fixtures and undocumented mirrors are not substitutes.

For each file record original path, size, SHA256, owner/source, package build, ELF ABI/interpreter/dependencies (for binaries), strings/build ID (where useful), expected loader path, and the exact kernel/vendor consumer. Do not patch, hex-edit, truncate, rename to trick the loader, strip, resign or repackage signed firmware.

If the matching OEM blobs are not present on the device or obtainable from a legitimate matching package, report `BLOCKED_FIRMWARE` with an exact list. Do not fabricate firmware. Continue native/kernel ABI investigation and build/tests, but do not claim physical camera success.

## 4.3 Vendor HAL investigation

The existing camera policy says not to install Android camera HAL libraries. Do not silently reverse that decision. First determine whether a native Linux implementation is viable. If only the proprietary Samsung HAL can operate the ISP:

- inventory its exact binaries and HIDL/service dependencies from the same-device stock image;
- verify architecture (32/64-bit), Bionic linker and dependencies;
- inspect required init/service/property/Binder/HIDL/Keymaster/TEE dependencies;
- assess lawful use on the owner's device and whether redistribution is prohibited;
- isolate any compatibility runtime and avoid pulling in the whole Android framework by default;
- never disable signature verification or mix firmware generations.

A vendor HAL can be used only after the real binary and complete dependency graph are proven compatible with Nuxel. Otherwise use a properly implemented native adapter/driver path or report `BLOCKED_COMPATIBILITY`.

# 5. CHOOSE AND IMPLEMENT THE ACTUAL CAPTURE PIPELINE

The previous snapshot shows the Samsung nodes advertise `V4L2_CAP_VIDEO_CAPTURE_MPLANE` plus Samsung `V4L2_CAP_EXT_PIX_FORMAT`, but standard `VIDIOC_S_FMT` returns `ENOTTY`, `REQBUFS`/`QUERYBUF` return `EINVAL`, and no `/dev/media*` or `/dev/v4l-subdev*` graph was found.

Do not assume that installing libcamera, GStreamer or PipeWire fixes the kernel interface. The official libcamera pipeline-handler model manages real hardware pipelines and accesses media-controller/V4L2 devices, configuring streams and buffers. This handset's missing media graph and non-standard ioctls are a fundamental gap that must be resolved explicitly.

Investigate three routes and choose one from evidence:

Route A — native Linux/libcamera pipeline: implement a real Exynos FIMC-IS pipeline handler against the exact existing downstream ABI. It must correctly match/enumerate the device, configure the sensor/CSIS/ISP stages, program modes/controls, allocate/export DMA buffers, queue/dequeue requests and handle errors. If the standard libcamera `MediaDevice` path requires `/dev/media*`, either expose a correct media-controller graph in the kernel (if feasible) or implement the smallest legitimate integration that the pinned libcamera version supports. Do not claim a handler works just because it compiles.

Route B — narrowly scoped kernel adaptation: modify the FIMC-IS driver/device tree to expose a coherent standard Media Controller + V4L2 subdevice/capture interface, with correct entity pads/links, formats, buffer queueing, DMA ownership, controls and power-management. This may require a significant patch. Preserve vendor functionality, test all error paths and build against the exact 4.14.253 source. Do not partially expose fake `/dev/media0` nodes without a real graph.

Route C — same-device vendor camera provider/HAL adapter: use only exact, legitimate, matching vendor components from the owner's SM-G975F stock image and a minimal documented compatibility layer. Do not install random Android HAL files or create fake binder responses. Keep proprietary code/artifacts local to the owner device where redistribution is not permitted.

The route may combine a small kernel fix with a native userspace pipeline. It must not combine competing owners of the same sensor/ISP or expose two independent control paths that race.

## 5.1 Exact Samsung private ABI audit

From the pinned source, build an ABI map containing:

- private ioctl number, direction, type/number, structure size and exact structure definition;
- which node accepts each ioctl and which stage owns it;
- sensor/stream setup ordering;
- firmware/setfile request and validation logic;
- buffer allocation, mapping, queue/dequeue and completion semantics;
- pixel formats, plane count, strides, dimensions, alignment and memory type;
- control IDs/structures for exposure, focus, white balance, frame rate, stabilization and flash;
- teardown/stop order and reset recovery.

Use exact source and documented calls. Do not brute-force private ioctl numbers against live hardware. Do not run generic `v4l2-ctl --stream-mmap` against the first discovered `/dev/video*` node. Do not write read-only `ifname`-style attributes or raw register values. Never capture from a codec, MFC, JPEG, scaler or unrelated M2M node just because it is a video node.

## 5.2 Primary first-light milestone

Bring up only the rear-main S5K2L4 first:

1. Load matching FIMC-IS MCU/ISP firmware and the S5K2L4 mode setfile using the driver's actual request path.
2. Complete sensor power/clock/reset/MIPI sequence.
3. Verify sensor ID and mode programming through existing read-only diagnostics or documented driver logs.
4. Configure one conservative mode (e.g. supported 1920×1080 at safe frame rate—derive from actual sensor mode table; do not guess).
5. Configure the exact vendor V4L2/private pipeline and DMA buffer layout.
6. Start stream and verify live frame completion.
7. Save one JPEG/PNG through a real decoder/encoder path and inspect it visually.
8. Confirm it depicts a scene physically aimed at by the owner, with a fresh timestamp and a hash.

Then add front-main S5K3J1, tele S5K3M3 and UW S5K3P9. Do not require the depth/IR sensor as an RGB preview device.

## 5.3 Fix the S5K3P9 switch path only from evidence

Investigate `gpio_subcam_sel` and `gpio_mipi_sel`, their DTS consumers and correct board routing. Record the actual DTS values/source. Correct only if the exact board configuration proves the current value/wiring wrong. Test switching between modules repeatedly without deadlocking or leaving the wrong MIPI route selected.

# 6. CAMERA DIAGNOSTIC TOOL AND TEST FIXTURE REPAIRS

Audit `tools/s10plus/a33/nuxel-camera-diag.sh` before using its verdict as a gate.

Current weaknesses to repair:

1. Its `verdict()` can return `READY_UNTESTED` when at least one candidate firmware filename exists and a media node exists. One file does not prove all sensor/ISP dependencies are loaded, valid or compatible.
2. Its fixture `camera-ready` includes a 3-byte placeholder `s5k2l4_setfile.bin`. The test fixture must never be interpreted as valid firmware. Add fixture metadata/size/hash/format validity checks or rename it explicitly as synthetic invalid data.
3. `cmd_capture()` picks the first enumerated `/dev/video*` node and runs generic `v4l2-ctl --stream-mmap`. That is unsafe on this Samsung pipeline because arbitrary nodes can be M2M/vendor-only and generic ioctls have already been shown to fail.
4. Status fields should distinguish node enumeration, sensor binding, required firmware identity/version/hash, private ABI capability, media graph readiness, stream initialization, real frame capture and physical app integration.
5. A status output must never infer frame success from metadata.

The hardened diagnostic should:

- map sensor names to sensor modules and exact V4L2 nodes based on sysfs parent/name/driver evidence;
- enumerate `/dev/media*`, subdevices and graph entities when present;
- report the actual firmware files requested by the driver, not just a broad list of candidate names;
- check file sizes, hashes, version/ABI metadata where available and known exact-target provenance;
- report firmware load success from kernel logs/status, not only file presence;
- run read-only format/capability queries only where the node supports them;
- have an explicit, bounded owner-confirmed `capture` action that uses the chosen verified pipeline/backend, not an arbitrary video node;
- refuse capture when no supported pipeline backend is active;
- label USB-UVC/webcam, synthetic colorbar, test-pattern and integrated S10+ camera sources distinctly;
- never claim a frame from synthetic/UVC as an S10+ integrated frame;
- save JSON, kernel logs, test outputs, exact device node map and hashes.

Keep all offline fixtures and regression tests; expand them to prove that incomplete firmware, placeholder/truncated blobs, wrong device family, missing firmware load, wrong ABI and unverified frames all stay BLOCKED.

# 7. NATIVE CAMERA APP AND FILE-BACKED MEDIA

Existing relevant components:

- `pwa/nuxel-apps/camera-gallery/` — Camera PWA with `getUserMedia`, front/rear state, photo/video controls and bridge persistence;
- `pwa/nuxel-apps/photos/` — file-backed gallery;
- `shell/nuxel-camera-native/nuxel_camera_native.py` — native GTK4 app, currently an honest hardware-status shell without a live viewfinder;
- `services/nuxel-bridge/src/media_store.py` — file-backed media store under `/var/lib/nuxel/media`;
- `services/nuxel-bridge/src/bridge.py` and `api.py` — current camera status/list/capture/open/delete bridge actions.

Complete the native camera surface, not just the PWA. The owner specifically wants the Camera app opened on the handset after the real camera pipeline works so the live preview can be seen on the phone.

The native app must:

- show a live physical frame, not a placeholder, screenshot, video file or test pattern;
- expose front/rear camera selection only for live cameras that the provider reports as available;
- provide user-initiated photo and video capture;
- save to the existing media store and verify the resulting file decodes;
- show resolution/frame-rate and truthful state/error details;
- support stop/release and close camera cleanly when the app backgrounds, exits or device locks;
- show flash/focus/zoom/OIS only when the actual provider supports the corresponding control;
- not call raw `/dev/video*` ioctls from the unprivileged UI;
- show a persistent camera-use indicator and keep a stop control visible;
- never enable microphone capture without a distinct microphone permission.

Avoid duplicating the media store, capture daemons or camera owners. One well-defined broker owns the physical capture pipeline. The native app, PWA, PipeWire and system portal consume that shared provider through documented APIs.

Do not let the Bridge's `CameraCapture` endpoint accept arbitrary caller-provided base64 as proof of a physical capture. If it stores a captured blob, require a valid short-lived stream/session handle issued by the privileged camera provider and bind the data to an authorized capture session. Maintain size limits, MIME validation, atomic writes, fsync/rename and media-store ownership.

# 8. STANDARD PIPEWIRE + XDG CAMERA PORTAL — ZAPZAP AND FERDIUM

The current `shell/nuxel-camera-portal/` exposes a private D-Bus interface named `org.nuxel.Camera`. It does not implement the standard `org.freedesktop.portal.Camera` contract. The existing private service has methods such as `RunCamera` and `Release`; that is not a replacement for standard portal methods.

For normal Linux apps, browsers and Electron/WebRTC clients, integrate the real session-scoped PipeWire/XDG camera path. The standard camera portal includes:

- `IsCameraPresent` property;
- `version` property;
- `AccessCamera(options) → request object path`;
- standard `org.freedesktop.portal.Request.Response` completion signal;
- `OpenPipeWireRemote(options) → Unix file descriptor` after permission has been granted.

PipeWire and its session manager must enforce access so the app receives a limited PipeWire camera remote/node, not broad direct access to all `/dev/video*` devices. Use the supported `xdg-desktop-portal`, an appropriate portal backend/configuration, PipeWire and WirePlumber session components. The portal must run in the same user/session D-Bus and runtime context as the compositor/browser. Do not install the camera portal as a system unit if the implementation is session-scoped.

## 8.1 Existing snapshot limits

The A53 evidence snapshot recorded:

- `xdg-desktop-portal` and GTK backend absent;
- PipeWire and WirePlumber absent;
- Flatpak absent;
- `CONFIG_USER_NS` not enabled in the measured kernel, so Bubblewrap/Flatpak user namespaces failed;
- the private `org.nuxel.Camera` broker is not a standard XDG camera portal.

Recheck all of these on the current device. Do not assume stale evidence is still true. If ZapZap/Ferdium are Flatpak apps and require user namespaces, do not bypass their sandbox with `--no-sandbox`, `--filesystem=host`, `--device=all` or global grants. Investigate a properly scoped kernel/userns and portal path as part of the combined batch only if needed and supported.

## 8.2 App discovery and compatibility

The uploaded repo does not contain ZapZap or Ferdium package manifests. Discover the actual installed app identities and packaging on the booted phone:

- RPM/native desktop package and `.desktop` ID;
- Flatpak app ID and permissions if installed;
- Electron/Chromium version/build flags;
- WebKitGTK version if a PWA container is used;
- effective user/session bus, `XDG_RUNTIME_DIR`, PipeWire remote and portal backend;
- camera request logs and denial/permission behavior.

Do not guess IDs or assume these apps exist just because the owner named them.

After the standard portal works:

1. Test a local `getUserMedia()` diagnostic page in Ferdium (or its embedded browser) that uses the physical rear camera, then front camera.
2. Test the actual ZapZap camera preview/video-call camera chooser and verify it shows the S10+ physical camera.
3. Where an actual remote call is unavailable, test the local camera preview surface and record that two-way network calling was not tested.
4. Confirm each app needs a separate camera permission grant.
5. Test deny and revoke: no new frames must be delivered, active stream must stop, indicator must clear.
6. Test one app cannot enumerate/access another app's PipeWire remote or a raw V4L2 node.

Do not grant access globally to every app merely to get the test green. If an installed build bypasses the standard portal and opens `/dev/video*` directly, record that as an enforcement problem and implement a supported app-scoped restriction or mark the app unsupported; never use mode `0666` for the video nodes as a shortcut.

## 8.3 Avoid fake portal compatibility

Do not claim `org.freedesktop.portal.Camera` unless all required methods/properties/signals/FD semantics work and the portal is visible through the session bus. Preserve the private `org.nuxel.Camera` broker only for internal Nuxel-specific operations if it remains useful. Add protocol tests for actual portal signatures and a client that requests a PipeWire camera FD and receives a real camera node.

# 9. CAMERA PERMISSION MANAGER — AUDIT THE EXISTING CAPABILITY AND FINISH ENFORCEMENT

The canonical `camera` capability already exists in:

`shell/nuxel-shell/nuxel-permissions/capabilities.json`

The Permission Manager PWA already has a Camera label and includes `camera` in its canonical capability map. The Camera app manifest already declares `camera:capture`, `camera:preview`, and `camera:read`. Do not blindly add a second `camera` capability or a duplicate UI row. The task is to verify aliases, correct the token mapping and enforce the permission all the way to the physical camera provider and PipeWire portal.

## 9.1 Canonical permission semantics

Keep one canonical high-risk camera capability for live hardware use:

- `camera:preview` — permission to receive a live camera stream;
- `camera:capture` — permission to initiate user-visible still/video capture through the trusted provider;
- `camera` — canonical Permission Manager row and grant record.

Audit `camera:read`: reading already-saved media from the file-backed Photos/media library is not the same as opening the live sensor. Move saved-media listing/opening to the existing media-library read capability or another precise canonical media permission. Do not let `camera:preview` silently grant access to the user's entire saved gallery. Deletion must have an explicit write/delete policy; do not broaden the existing low-risk `media_library` read grant to allow destructive operations without documenting a separate policy.

Update together:

- `capabilities.json` aliases/manifest tokens/description/risk/group/mechanisms/limitations/verdict/test;
- `pwa/nuxel-apps/permissions/app.js` `CAP_LABELS`, `CANONICAL`, `TOKEN_MAP`, resolution and grant display;
- Camera/Photos manifests;
- `nuxel-permd.py` resolution/default-deny behavior;
- portal permission request and persistent grant store;
- Bridge/API capability checks;
- per-app grants only when explicitly approved by the owner.

Use exact canonical aliases rather than letting a generic `token.split(':')[0]` silently map a semantically different permission to `camera`.

## 9.2 Grant and enforcement rules

- Camera permission is high risk and default deny.
- A manifest declaration is a request, never a grant.
- Permission decisions are stored by central `nuxel-permd`/portal policy, not a PWA localStorage flag.
- The grant is scoped to the actual installed app ID and user/session.
- A portal grant provides access only to the authorized PipeWire camera node/stream.
- Revoke stops active streams and blocks new ones.
- An app cannot spoof its own `app_id`, `is_system` or origin via JavaScript parameters.
- Camera hardware device nodes remain unavailable to arbitrary web apps. Do not chmod `/dev/video*` world-readable/writable.
- Verify AppArmor from `/sys/kernel/security/lsm` on the live 4.14 kernel before claiming it enforces anything. The repository states Landlock is absent on 4.14 and systemd `DeviceAllow` is not proven due missing BPF device-controller support. Report actual enforcement limits honestly.

## 9.3 Audit the current fail-open/error and data path

The uploaded snapshot contains risky conditions that must be reviewed:

- `bridge.py` catches exceptions from the camera privacy provider and treats them as `private=False` / unblocked. `privacy_provider.camera_capture_blocked()` also returns `False` on any read error. This is fail-open. Make privacy-state uncertainty fail closed for new camera opens/captures.
- `camera_status()` reports `active_sessions: 0` with `active_session_tracking: bridge_camera_capture_only`; replace with actual provider/portal session state once camera streams work.
- `CameraCapture` accepts app-supplied base64 and stores it. This is media persistence, not proof that the sensor captured the data. Bind writes to a valid active camera session and keep actual acquisition inside the trusted provider.
- `CameraListCaptures`/`CameraOpen` currently use `camera:preview`, which conflates live sensor use with reading saved files. Correct this permission model as defined above.
- The private portal has a GStreamer source defaulting to `/dev/video0`, even though `/dev/video0` has not been proven to be a capture node on this phone. Remove hard-coded generic camera paths; the real provider must select an enumerated supported capture source.

Add regression tests proving provider error, malformed privacy state, portal unavailable, permission denied, lock screen, and app revoke all fail closed and release the active stream.

# 10. PRIVACY INDICATOR, SESSION CONTROL AND HARDWARE ACCESS OWNERSHIP

The camera may be opened only through one privileged provider that owns the FIMC-IS hardware. Browser/PWA/native applications receive mediated PipeWire streams, never raw device-node access.

Implement:

- session start/end registry with app ID, stream type, sensor, timestamp and status (no frame data);
- per-app permission approval before provider opens the physical source;
- visible persistent camera-use indicator in Nuxel system chrome/Quick Settings while any stream is active;
- a user-accessible stop/kill-camera control;
- indicator for third-party ZapZap/Ferdium sessions too, not only Nuxel Camera;
- hardware source close on last client disconnect, app termination, screen lock, user revoke, privacy-block and service shutdown;
- no hidden camera access or stealth/background capture;
- no camera/microphone coupling: audio input remains a separate permission;
- no EXIF GPS by default; only add location metadata with an explicit separate consent;
- bounded frame buffers and no raw-frame logging;
- error handling that leaves the camera blocked if the permission store, privacy provider or portal cannot be contacted.

A GUI tile must not say camera is OFF if another app holds an active stream. It must say `In use by <app>` where the identity is reliable, otherwise `Camera active`. It must not reveal other app data unnecessarily.

# 11. KERNEL/DT, BUILD AND SOURCE CONTROL REQUIREMENTS

The authoritative S10+ kernel build script pins:

`https://github.com/Linux4/android_kernel_samsung_exynos9820`\
`f7194c1d15eded1c2a1a4dc63825b26103435cc0`\
`Linux 4.14.253`, defconfig `exynos9820-beyond2lte_defconfig`\
active fragment `kernel/s10plus/configs/nuxel-drm-kbase.fragment`.

Re-fetch/verify that commit. Inspect the full FIMC-IS source and board DTS, not only out-of-tree notes.

- Preserve the existing active config fragment and all previously validated display/GPU/MFC/NFC/USBNET settings.
- Add only camera-specific Kconfig options whose dependencies and need are proven by source/tests.
- Verify resulting `.config` after `olddefconfig`; do not edit informational `defconfig` only.
- If the kernel doesn't need a new patch, do not make one merely for appearance.
- If a patch is required, use a unique filename, explain root cause/scope, validate forward and reverse application, add regression tests, update patch README, and mark `.required` only after it is proven essential.
- Keep patch sort order compatible with the concurrently developed NFC patch.
- Build kernel and DTBs with `kernel/s10plus/build-kernel.sh`; run the repo's config-parity and artifact gates.
- Build a boot candidate from a known-good verified base with `boot/s10plus/build-candidate.sh`; verify it with `tools/s10plus/verify-boot-image.py` and partition size/PIT checks.
- Do not package a gzip-compressed kernel payload in place of raw `Image`.
- Run existing `make`/test gates relevant to camera, permissions, portal, bridge and launchers; retain logs.

The lack of `/dev/media*` and vendor private ioctls does not automatically justify a device-tree patch. Trace the actual media graph and capture driver logic first.

# 12. LIVE DEPLOYMENT AFTER THE SUCCESSFUL NUXEL BOOT

Once booted and connected to `root@192.168.178.167` over Wi-Fi SSH with the owner key, inspect the live OS and deployment filesystem before changing files.

The repository's `scripts/s10plus-debug-pack/nuxel-live-deploy.sh` is a serial-console framed deploy tool, not automatically a Wi-Fi SSH deployer. The owner specifically asked you to continue over Wi-Fi SSH. Use verified `scp`/`rsync` or a carefully designed SSH staging/deploy path with atomic rename and checksum verification. Do not misrepresent a serial deploy as SSH.

Before deployment:

1. Record host fingerprint and expected target identity.
2. Record git commit/build ID, unit state and each destination file's SHA256, owner, mode and symlink target.
3. Back up every destination file exactly.
4. Stage new files under a temporary directory on the device.
5. Verify transferred hashes and syntax there.
6. Atomically replace only the intended files.
7. Restart only affected service units; capture `systemctl status` and `journalctl`.
8. Verify live API responses, portal bus name/methods, Permission Manager UI state and the Camera app.
9. If a check regresses, restore the exact backup and verify original hashes and service health.

Safe userspace/PWA/permission/provider/portal components should be deployed live when tests pass. Matching proprietary firmware, kernel/DT changes, protected/system-image files or changes blocked by immutable/verified system layout belong in the combined reflash payload. Do not claim that every system change was deployed live when it actually requires an image.

Do not replace the whole bridge tree or restart all services blindly. Preserve currently deployed LED/edge/PWNAGE-93000 and NFC/USBNET work.

# 13. PHYSICAL HARDWARE VALIDATION

Owner must be present for physical aiming/preview checks. Never simulate these.

## 13.1 Rear-main first-light

1. Open the native Nuxel Camera app on the actual handset.
2. Grant camera permission explicitly in Permission Manager/portal.
3. Point the rear camera at a real, well-lit scene that the owner can change/recognize.
4. Confirm live preview changes when the scene moves; no repeated/static image.
5. Capture a still, open it in Photos, inspect image dimensions and decode it, compare its scene content to the live view, record timestamp and SHA256.
6. Record at least 100 frames with monotonically increasing timestamps and valid completion sequence; verify no stale/reused buffers.
7. Stop preview; verify sensor stream stops and indicator clears.

## 13.2 Front camera

Repeat with S5K3J1, including a real self-view preview and still image. Do not treat the S5K4H7 IR/depth sensor as the front RGB camera.

## 13.3 Other lenses and controls

Where supported, physically test tele, ultrawide, autofocus, exposure, white balance, flash/torch, OIS and video. Each feature needs independent evidence. A flash icon is not proof of a working flash control. A fixed-focus sensor should be labelled accurately; do not invent focus control.

## 13.4 Video

Record at least 10 seconds of a moving real scene. Confirm increasing timestamps/frames, correct duration, valid container/codec, and playback in Photos. Test microphone independently with the microphone permission granted; test muted video with microphone denied.

## 13.5 Thermal/power/reliability

Run repeated preview/capture, bounded soak, suspend/resume, lock/unlock and app close/reopen. Monitor battery/thermal state, memory, DMA errors, dmesg, ISP firmware resets and camera service crashes. Stop on abnormal thermal/power behaviour and diagnose before retrying.

## 13.6 Third-party interoperability

- ZapZap: test actual camera chooser/preview with the real device camera and a permission prompt. If a full call cannot be placed, record `preview tested; network call not tested`.
- Ferdium: load a local diagnostic page that calls `navigator.mediaDevices.getUserMedia({video: true})`; verify physical frame, stop and revoke.
- Test denial, revocation, app restart, permission persistence and app isolation.
- Record exact installed IDs, package type, runtime versions and any unsupported portal behavior.

# 14. AUTOMATED TESTS AND SECURITY GATES

At minimum add/run:

### Kernel/ABI

- exact pinned source commit check;
- camera patch applies in sorted order and reverse-checks;
- `.config` contains only required resolved media/FIMC options;
- no standard ioctl is reported supported unless its handler really exists;
- private ioctl structures and ABI sizes match source;
- error/unwind/buffer lifetime review;
- no raw sensor/EEPROM writes in test helpers.

### Firmware

- required file set completeness;
- minimum size/magic/version/architecture checks derived from actual loader;
- hashes match acquired/approved manifest;
- wrong model/build/ABI rejected;
- test placeholder (3-byte fixture) rejected;
- corrupt/truncated file remains blocked;
- load success checked via driver status/log—not file presence only.

### Userspace/portal

- native provider status;
- PipeWire node discovered from live provider;
- standard portal introspection signatures/properties;
- `AccessCamera` request/response lifecycle;
- `OpenPipeWireRemote` returns a real usable FD only after grant;
- denial/revoke disconnects stream;
- session close releases hardware;
- no synthetic/UVC source counted as handset.

### Permission/privacy

- canonical aliases resolve as designed;
- default deny;
- manifest declaration is not a grant;
- only genuine app identity can receive app-scoped permission;
- no caller-supplied app ID spoofing;
- camera preview and media-library read are distinct;
- provider/privacy read failure denies new stream;
- active indicator follows all clients;
- no `/dev/video*` world access;
- no frame bytes or secrets in logs/API status.

### App/UI

- Camera PWA opens actual preview and captures real still/video;
- native Camera app opens and shows real viewfinder;
- Photos lists/opens saved capture;
- ZapZap/Ferdium physical camera access where supported;
- deny/revoke/stop/lock/app-exit flows work;
- other Nuxel launcher/bridge functionality remains healthy.

Synthetic vectors, `videotestsrc`, USB-UVC and mock portal tests are allowed as software regression tests only. They never satisfy a built-in-camera physical acceptance gate.

# 15. ONE COHERENT REFLASH BATCH — CAMERA + NFC + READY KERNEL WORK

The owner's overarching goal is one coordinated reflash for all kernel/vendor-gated additions. The NFC agent is working in parallel.

- Preserve the current NFC source/patch work and include it in the same final kernel build if it is ready and compatible.
- Preserve USBNET/GPS/SSP/mobile/display/GPU/MFC changes already accepted.
- Do not perform a separate camera-only flash if the NFC patch is concurrently ready and the combined plan can be built safely.
- If the camera needs no kernel patch, only add its firmware/userspace payload to the appropriate rootfs/system staging plan; do not modify the boot image needlessly.
- If camera requires kernel/DT changes, combine them with NFC and any other completed kernel work, run a clean full build from one source/patch set, and produce one verified boot candidate.
- Reconcile the plan's A/B terminology with actual S10+ PIT/partition topology before any write. If the phone is single-slot and uses a custom rootfs on userdata, explicitly document that. Never wipe userdata without specific owner approval and a verified backup.
- Do not flash vendor/system/userdata/efs/persist/modem/recovery/bootloader/PIT unless the exact partition image/target/protection/data impact is explicitly defined and approved.
- The current authorized flashing scope is the verified kernel/boot image using repository scripts. Any additional partition write must be justified by the plan and safe workflow; do not infer blanket authorization.

# 16. REQUIRED DELIVERABLES

Create/update these in the repo:

1. `PWNAGE-CAM-REPORT.md` — executive verdict; exact working sensors/features; blocker matrix; physical proof.
2. `PWNAGE-CAM-HARDWARE-MAP.md` — sensors, buses, I2C, GPIO, regulators, clocks, CSI, FIMC-IS entities/nodes, power and ownership.
3. `PWNAGE-CAM-FIRMWARE-INVENTORY.md` — every firmware/setfile/tuning/OIS file, exact origin, matching device/build, ABI, SHA256, loader consumer and status.
4. `PWNAGE-CAM-ABI-ANALYSIS.md` — private ioctls, structures, formats, buffers, media-controller state, source references and chosen pipeline architecture.
5. `PWNAGE-CAM-PERMISSION-MATRIX.md` — canonical camera permission, aliases, app IDs, media-library separation, portal, PipeWire and actual enforcement limits.
6. `PWNAGE-CAM-APP-INTEGRATION.md` — native app, PWA, standard portal, PipeWire, ZapZap and Ferdium results.
7. `PWNAGE-CAM-TEST-RESULTS.md` — exact automated/physical tests, camera role, resolution, frame count, hashes, video and thermal data.
8. `PWNAGE-CAM-REFLASH-MANIFEST.md` — final combined kernel/DT/firmware/system/user-space files, patch order, image hashes, flash target and evidence; note exact boot outcome.
9. New kernel patch and `.required` only if proven necessary; update patch README and active config fragment.
10. Updated camera diagnostic, firmware manifest/provenance checks, regression tests, portal/backend, provider, native app and PWA/API/permission changes.

Record all installed file hashes, kernel commit, final `.config` hash, image hash, firmware origin and test logs. Do not include private keys, raw frames, user photos or raw EEPROM dumps in the repo/ZIP.

# 17. FINAL RESPONSE AND CONTINUATION RULE

Final report must separately state:

- rear-main camera: preview/still/video PASS or blocker;
- front-main camera: preview/still/video PASS or blocker;
- tele/ultrawide/depth roles: separate status;
- camera firmware/setfile inventory and provenance;
- kernel/DT modifications and actual boot candidate hash;
- exact TWRP flash/reboot outcomes, including every failed return to TWRP and fix;
- whether Nuxel booted and Wi-Fi SSH connected to `root@192.168.178.167` with the supplied key;
- live-deployed userspace files and hashes;
- native Camera app opened and actual preview visible to owner;
- Camera permission shown in Permission Manager and real allow/deny/revoke proof;
- standard `org.freedesktop.portal.Camera`/PipeWire functionality;
- ZapZap and Ferdium exact app IDs, preview tests and unsupported limitations;
- remaining external Samsung firmware/ABI/compatibility requirements.

Do not say “camera fixed” unless real built-in S10+ frames are visible in Nuxel Camera and the end-to-end app stack has been tested. Do not claim ZapZap or Ferdium camera compatibility from a passing synthetic portal test.

Keep implementing, building, flashing the verified combined batch when justified, repairing failed Nuxel boots, deploying safe userspace changes over Wi-Fi SSH, and physically testing until the actual camera works. If the exact matching proprietary firmware/ABI is unavailable, report `BLOCKED_FIRMWARE` or `BLOCKED_VENDOR_ABI` with the exact missing OEM input. Never bypass secure/driver checks or fabricate frames to force a PASS.

````

## 2. `pwnage-cam.md` — agent kickstarter

Save this in the same directory as the full prompt. Start the agent with this shorter file.

```markdown
# PWNAGE CAM — Samsung Galaxy S10+ Camera Bring-up for Nuxel

**Read and obey `full-pwnage-cam.md` completely.** It contains the detailed hardware investigation, firmware requirements, TWRP/flash loop, SSH handoff, permission-manager work, PipeWire/XDG portal requirements, app validation, security policy and acceptance tests.

## Starting state and owner authorization

I will start you with the Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) already booted into **TWRP and connected over USB/ADB**.

You are authorized to:

- inspect the exact repo and device;
- acquire ordinary matching camera firmware/HAL/config files from the owner's own already-mounted stock vendor/system filesystem using the read-only acquisition script in this pack;
- build the pinned kernel and DTBs;
- build a verified boot candidate;
- flash the verified boot image using the repository's guarded TWRP script;
- reboot and diagnose failed boot attempts;
- once Nuxel boots, connect over Wi-Fi SSH with my key and continue implementing/testing/deploying camera userspace.

Do not use generic fastboot on this S10+. Inspect `boot/s10plus/flash.sh`, `build-candidate.sh`, `kernel/s10plus/build-kernel.sh`, the completed device inventory and actual partition topology before writing anything. The current plan mentions A/B, but the real S10+ partition layout must be measured; do not invent slots. Never flash userdata/rootfs, EFS, persist, modem, recovery, bootloader or PIT without an independently verified target and explicit data-impact approval.

## Critical reboot interpretation

**If you flash/reboot and the phone returns to TWRP, that means the Nuxel boot attempt failed. I did not manually return it to TWRP.** Treat it as a bootloop/hang/crash. Collect TWRP/pstore/last-kmsg/kernel/initramfs/filesystem logs, identify the root cause, fix the source, rebuild, pass the gates, reflash the corrected boot candidate and reboot again. Never repeat the same failing image blindly.

**When the phone reaches the Nuxel environment and its boot health check confirms userspace, that is a successful boot.** Then connect to the owner-provided Wi-Fi address using:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
````

Resolve the key path correctly on the workstation. Never print/copy the private key or disable SSH host-key checking. Verify the target identity after connecting. If Wi-Fi SSH is unavailable, use the preserved USB console; do not reflash just because Wi-Fi did not come up.

## Current camera state — do not start from zero

The uploaded repo already has:

- five observed FIMC-IS sensor modules: rear S5K2L4, tele S5K3M3, UW S5K3P9, front S5K3J1, IR/depth S5K4H7;
- dozens of Samsung Exynos FIMC-IS `/dev/video*` nodes;
- OIS/EEPROM/MIPI/FIMC-IS kernel support and secure-camera handshake evidence;
- camera diagnostic, Camera and Photos apps, native GTK Camera shell, bridge/API media store, private `org.nuxel.Camera` broker and camera Permission Manager capability.

The previous measured verdict was `BLOCKED_FIRMWARE`: no genuine sensor/ISP setfiles/firmware on the Nuxel rootfs, no `/dev/media*` or `/dev/v4l-subdev*`, standard `VIDIOC_S_FMT` on the inspected Samsung nodes returned `ENOTTY`, `REQBUFS`/`QUERYBUF` returned `EINVAL`, and no real S10+ frame has ever been verified. The test fixture's `s5k2l4_setfile.bin` is only 3 bytes: it is fake placeholder data and must never be installed.

The current private camera broker is NOT `org.freedesktop.portal.Camera`. The current Camera app UI is substantially implemented but does not have a real hardware source. The current native Camera app is an honest status shell and needs a genuine live viewfinder/capture path.

## Your immediate tasks

1. Inspect `git status`, `REFLASH-PLAN.md`, the complete camera report/docs, current deployed state and concurrent NFC agent changes. Preserve them; do not reset/stash/clean/revert.
2. Reverify the exact handset, five sensor IDs, FIMC-IS nodes, media graph, camera firmware paths, kernel logs, TEE secure-camera path and actual source commit.
3. Read the exact pinned Linux4 Exynos9820 4.14.253 kernel source. Trace FIMC-IS sensor drivers, firmware request names, private ioctls/structs, mode tables, media-controller setup, CSI/ISP/DMA path and sensor power sequencing. Investigate the S5K3P9 `gpio_subcam_sel`/`gpio_mipi_sel` errors using matching DTS evidence only.
4. Run `scripts/acquire-s10plus-camera-assets.py` in inventory-only mode. Then use `--pull` to acquire exact ordinary files from the owner's own matching, already-mounted vendor/system/odm paths. Use `--include-vendor-calibration` only for owner-authorized regular vendor calibration files. Do not mount/write partitions, read EFS/persist/RPMB/raw EEPROM/TEE memory or access user data.
5. Obtain only genuine, compatible Samsung camera sensor setfiles, Exynos9820 FIMC-IS MCU/ISP/RTA libraries, OIS firmware and calibration/tuning files from the exact SM-G975F firmware family. Verify paths, SHA256, sizes, versions, ELF ABI, dependencies and driver consumers. Do not use Qualcomm/Pixel/other-device blobs or fake fixtures. Do not edit or re-sign proprietary firmware.
6. Prove the pipeline architecture from source. A generic libcamera install will not fix missing media graph/private Samsung ioctls. Choose a working native libcamera/private-ABI handler, safe kernel media-controller adaptation, or a narrowly scoped exact-device vendor provider. Do not create a fake media graph or blindly stream from `/dev/video0`.
7. Start with rear-main S5K2L4 real preview + still, then front-main S5K3J1, then tele/UW if supported. Handle S5K4H7 as IR/depth, not an ordinary RGB webcam.
8. Fix the camera diagnostic's false readiness path: one present blob is not enough, the 3-byte fixture must be rejected, and capture must not pick the first arbitrary video node. Require verified firmware load, exact supported pipeline and decoded real frames.
9. Finish the native GTK Camera app so it shows the real physical live preview and captures real still/video into the existing file-backed media store. Keep Camera PWA and Photos working through the same provider; no duplicate capture owners.
10. Properly finish the Permission Manager and privacy enforcement. The canonical `camera` capability and label already exist; verify aliases (`camera:preview`, `camera:capture`, existing `camera:read`), default-deny, central permD storage, real portal/PipeWire enforcement and app identity. Separate live camera permission from saved-media read/delete permission. Fix fail-open privacy-provider exceptions. No world-writable `/dev/video*` devices.
11. Implement the actual standard XDG `org.freedesktop.portal.Camera` + PipeWire/WirePlumber path (AccessCamera request/response, OpenPipeWireRemote FD, per-app node access). Keep private `org.nuxel.Camera` separate; never claim it is the freedesktop portal.
12. Discover actual ZapZap and Ferdium app IDs/package type/runtime on the phone. Test each with physical `getUserMedia`/video preview, explicit permission, denial and revoke. Do not assume those packages or Flatpak are installed. Never disable sandboxing to make tests pass.
13. Preserve visible camera-use indicator and stop control for every app, and stop streams on revoke, lock, app exit or privacy block. Mic remains a separate permission.

## One coherent reflash

The owner wants one combined reflash batch with NFC and any other ready kernel/vendor-gated work. Do not perform a camera-only flash that omits the in-progress NFC patch if it is ready to integrate. Build from one exact pinned source tree and coherent patch/config set. Add a camera patch only if source/evidence proves it is needed. The authorized boot flash is through the guarded repo TWRP script, after backup/checksum/partition/inventory/build gates. Do not write the userdata rootfs default just because `flash.sh --rootfs` accepts it.

After the combined boot image boots, finish and hash-verify safe userspace deployment over the specified Wi-Fi SSH session. The repo live deploy helper is currently framed serial-console deployment; do not call that SSH. Use an atomic/hash-verified SSH staging workflow for Wi-Fi deployment and keep exact rollback copies.

## Required final acceptance

- Rear-main and front-main actual S10+ camera preview + still verified; video verified; other lenses separately classified.
- 100+ frames per accepted stream with no driver/ISP/DMA crash.
- Native Camera app foregrounded on the phone and real preview visible to the owner.
- Photos opens saved capture.
- Standard XDG Camera portal and PipeWire provide the camera to compatible clients.
- ZapZap and Ferdium tested with actual camera where their installed builds support it; exact app IDs and unsupported cases documented.
- Permission Manager camera grant/deny/revoke really gates acquisition; privacy errors fail closed; indicator reflects all active clients.
- Camera diagnostic correctly distinguishes enumeration, firmware load, pipeline readiness and physical frame capture.
- Boot/reflash log includes every candidate hash and every return-to-TWRP failure/repair. Live deploy log includes target identity and installed file hashes.
- Final reports and a combined `PWNAGE-CAM-REFLASH-MANIFEST.md` are saved.

Use `PASS_PHYSICAL`, `PASS_BUILD`, `PASS_RUNTIME`, `BLOCKED_FIRMWARE`, `BLOCKED_VENDOR_ABI`, `BLOCKED_PIPELINE`, `BLOCKED_PORTAL`, `BLOCKED_PERMISSION`, `BLOCKED_COMPATIBILITY`, `FAIL`, `NOT_TESTED` or `UNSUPPORTED` accurately. Do not claim the camera is fixed until real built-in S10+ frames are visible in Nuxel Camera and the app stack has been tested.

Continue implementing and physically verifying the real camera until it works. If the exact OEM firmware or private ABI is genuinely unavailable, document the precise missing Samsung input—do not fabricate a blob, bypass checks or substitute synthetic frames.

```

**Usage:** extract `Nuxel-Camera-Pwnage-Pack.zip` into your Nuxel working tree, keep the reference directory and acquisition helper, and launch the agent with `pwnage-cam.md`. The full prompt is the binding specification.

One practical point: the agent can build and flash the authorized boot image, but the camera may still be blocked by Samsung-only firmware or private ISP dependencies. The task is deliberately set up to pursue the real implementation rather than declaring victory from device nodes or a working-looking Camera app.
```

and you can find that python script here ./acquire-s10plus-camera-assets.py and README.md is renamed README-CAM.md in repo root else it overwrites our repo readme.

here is how to use that acquire script:

chmod +x scripts/acquire-s10plus-camera-assets.py

# 1. Inventory only — safe first step
python3 scripts/acquire-s10plus-camera-assets.py \
  --output ./camera-acquisition

# 2. Pull matching firmware and libraries
python3 scripts/acquire-s10plus-camera-assets.py \
  --pull \
  --output ./camera-acquisition

# 3. Include matching vendor calibration files, if needed
python3 scripts/acquire-s10plus-camera-assets.py \
  --pull \
  --include-vendor-calibration \
  --output ./camera-acquisition
