# Nuxel Samsung Galaxy S10+ — macOS flashing finish guide

**Status: experimental phase-1 hardware bring-up, NOT production-ready and NOT confirmed booting on real hardware.**

Prepared for **Samsung Galaxy S10+ Exynos, codename `beyond2lte`** (verify model, usually SM-G975F/FD), with Heimdall v2.2.2 on macOS. These instructions are **not** for Snapdragon S10+ models, other Galaxy devices, or for a stock daily-driver phone.

The included files are:

- `build/out/s10plus/nuxel-beyond2lte-boot-merged-patched.img` — Android boot-header v1, original ARM64 Exynos9820 kernel and merged device tree, corrected early initramfs.
- `build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img` — ext4 filesystem with `/sbin/init`, static ARM64 Toybox, S10+ configuration and diagnostic bring-up support.
- `build/out/s10plus/nuxel-s10plus-patched-manifest.json` — hashes, provenance and validation scope.

**These are development artifacts.** The kernel/merged DTB were preserved from your provided images, not rebuilt from verified stock firmware. The board overlay in the merged tree identifies `BEYOND2LTE EUR OPEN 26`; the physical phone's board revision has NOT been established. In particular, a merged DTB may be incompatible with the device's S-Boot DTBO application or an unmatched hardware revision. No on-device test has been performed. There is no valid basis to call them "production-grade" or guaranteed bootable.

## 0. Mandatory safety / go-no-go

1. **This will destroy the contents of USERDATA** and can require reinstalling Samsung firmware if boot fails. Continue only on an expendable test handset, after backing up important files. Keep the phone charged (preferably over 60%).
2. Confirm the actual phone is an **Exynos `beyond2lte`** S10+, not just an S10+ by name. Save a photo of Download Mode product name and bootloader status. `FRP LOCK: OFF` is not by itself proof that unsigned custom images are accepted. Do not lock the bootloader or alter KG/FRP/Knox.
3. **Do not flash the merged image until you can confirm the required board overlay/revision.** The build embeds an `eur_open_26` DT overlay; if the device revision is different or cannot be verified, **stop**. The stock boot image, DTBO partition, PIT and the exact phone model are the proper sources for this information.
4. Have a **verified restore path**: model-matched Samsung firmware and a known-good way to restore BOOT (and USERDATA) using Download Mode/Odin or a recovery backup. Stock restore may also wipe data. Do not overwrite EFS, modem, bootloader, or other protected partitions.
5. Confirm the downloaded image SHA-256 values match the supplied manifest and that both images fit the actual PIT partition capacities. **Do not flash on uncertain PIT geometry or partition names.**

## 1. macOS workstation: verify files (no ext4 mount needed)

Use Terminal in the root of the extracted patched repository:

```bash
cd ~/x/nuxel   # adjust to where you actually extracted the drop-in ZIP
ls -lh build/out/s10plus/nuxel-beyond2lte-{boot-merged,rootfs-bringup}-patched.img
shasum -a 256 build/out/s10plus/*-patched.img
python3 tools/s10plus/verify-artifacts.py \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-patched.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img
```

Verify the hashes against `build/out/s10plus/nuxel-s10plus-patched-manifest.json` before continuing. `python3` suffices for the **read-only** image tests; it does not require mounting ext4 on macOS. The verifier checks image structure, embedded ARM64 Toybox, early `/bin/sh`, expected init and S10+ configs. It cannot establish Samsung acceptance, screen initialization or a working boot.

Do **not** use `mount -t tmpfs` or native `mount -t ext4` on macOS: macOS cannot mount ext4 natively. To inspect an ext4 listing with Homebrew:

```bash
brew install e2fsprogs
"$(brew --prefix e2fsprogs)/sbin/debugfs" -R 'ls -l /' \
  build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img
```

## 2. Verify the physical partition map: no assumptions

Connect the **phone directly by a known-good data cable** (no hub; avoid charging-only cables). Start Download Mode by powering down, holding **Volume Down + Bixby**, and connecting USB to the Mac. On some firmware revisions the Power key combination differs; use the on-screen instructions to enter Download Mode. Do not use `adb devices` as the test: **ADB is normally absent in Download Mode**.

```bash
heimdall version
heimdall detect
heimdall print-pit --no-reboot | tee s10plus-device-pit.txt
```

Read `s10plus-device-pit.txt`. You **must** identify both the exact **`BOOT`** and **`USERDATA`** partition entries, confirm they refer to this device, and independently establish their partition size from the PIT's block geometry. The image files must fit. **Never assume that `SYSTEM` and `USERDATA` are interchangeable.** These artifacts expect `/USERDATA` as the ext4 rootfs. The upload log showing both images at 100% previously does **not** prove they are on readable storage or will boot.

`heimdall print-pit --no-reboot` may leave the Download Mode session open. If the next command cannot initialize the protocol, exit/re-enter Download Mode deliberately. Never start another flash just because a stale session exists.

## 3. Why merged vs. normal matters

Your supplied manifest distinguishes the variants:

- **Normal**: a base `exynos9820.dtb`; expects a compatible bootloader / DTBO arrangement.
- **Merged**: an `exynos9820-beyond2lte` DTB with an `eur_open_26` board overlay embedded.

This package patches **only the merged variant**, as requested. Do not treat it as automatically superior: double application of overlays or a mismatched board revision may cause boot failure. **If your board revision and actual DTBO handling aren't verified, do not flash either Nuxel boot image.** The files are structurally valid Android-v1 containers, not proof of bootloader compatibility.

## 4. Controlled flash (only after ALL go/no-go checks pass)

**This step overwrites BOOT and USERDATA, destroying installed OS/user data on those partitions.** The repository has a guarded wrapper, with USERDATA (not SYSTEM) as its default target. Review the command before confirming:

```bash
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh \
  --device s10plus \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-patched.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img \
  --dry-run
```

If the PIT, model, board and recovery checks all pass and you explicitly accept data destruction, execute the real command:

```bash
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh \
  --device s10plus \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-patched.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img
```

The wrapper requires you to confirm; its only permitted targets are **BOOT** and **USERDATA**. It will not flash SYSTEM, EFS, MODEM or DTBO. The exact supported Heimdall command is equivalent to:

```bash
heimdall flash \
  --BOOT build/out/s10plus/nuxel-beyond2lte-boot-merged-patched.img \
  --USERDATA build/out/s10plus/nuxel-beyond2lte-rootfs-bringup-patched.img
```

If your account cannot open the USB device, you may need a correctly authorized USB setup or `sudo`, but first verify which `heimdall` binary will run under privilege. Do **not** mix old and new Heimdall versions or repeatedly reflash on failed USB sessions.

## 5. The "100% + session end confirmation failed" condition

Previously you got:

```text
Uploading BOOT
100%
BOOT upload successful
Uploading USERDATA
100%
USERDATA upload successful
Ending session...
ERROR: Failed to receive session end confirmation!
```

This indicates the **host reported sending the image payloads** but did **not** confirm clean session termination. It is **not a verified flash success** and does not establish bootability. A full progress bar on the phone does not change that. Do not repeatedly re-run the flash without new evidence.

If the screen stays in Download Mode after the session finishes and the phone appears stuck, let the USB activity settle, then try **Volume Down + Power** for approximately 7–10 seconds to force restart. The precise transition timing depends on firmware. For recovery rather than normal boot, switch to **Volume Up + Bixby + Power** when the screen blanks, usually with USB connected to a computer. Recovery may not be available on your damaged installation; Download Mode is your essential fallback.

If the device returns to Download Mode or continuously shows only a Samsung logo, **do not assume the rootfs is defective**. Possibilities include bootloader rejection, DTB/board mismatch, kernel panic, missing UFS driver, initramfs errors, or a transfer not actually committed. Recover or return to known stock before any new experiments.

## 6. Expected result — this is not a GUI release

After successful kernel initialization, the patched initramfs should locate USERDATA by existing by-name links **or** the kernel's `/sys/class/block/*/uevent` `PARTNAME=userdata` entries, mount the ext4 root and enter `/sbin/init`. The bring-up init logs best-effort status to `/dev/kmsg` and `/dev/console`, optionally creates a USB CDC-ACM diagnostic gadget, and remains alive. Neither USB gadget nor framebuffer is guaranteed to be available in this kernel/hardware configuration. **The USB root shell is disabled by default** and may be enabled only by explicitly adding `nuxel.debug=1` to the kernel cmdline in a controlled test build; enabling it permits unauthenticated physical USB root access.

**There is no full Phosh desktop, Python3 runtime, OpenRC, working Wi-Fi/cellular stack or hardware-verified display in this artifact.** Those require additional development and vendor/driver validation. Even a silent/black screen is not enough to distinguish “running headless” from “not booting” without serial/kernel logs.

## 7. Recovery and interpretation

- **Phone still in Download Mode:** this mode is separate from ADB/TWRP. Disconnect/re-enter Download Mode to resolve stale sessions; avoid blind retry loops.
- **Samsung logo loop:** likely early boot failure; restore BOOT from your verified backup or compatible Samsung firmware using the known device-specific recovery procedure. Do not flash guessed DTBO or bootloader versions.
- **Recovery starts:** first preserve any logs/backups. Do not format partitions casually or use a factory reset as a generic fix for a boot image rejection.
- **USB-ACM diagnostic port appears:** on macOS inspect `ls /dev/tty.usbmodem*`; gadget presence depends on the kernel. This is a signal of advanced boot progress, not proof of a functional desktop.
- **Restoring full stock:** obtain exact model/region/bootloader-compatible Samsung firmware; use a verified restore workflow, with full awareness that data may be lost. Keep EFS backups and do not modify security partitions.

## 8. Precisely what has and has not been verified

**Verified offline:** SHA-256 hashes, Android-v1 header fields, unchanged original kernel/merged-DTB bytes, readable gzip/newc initramfs, bundled ARM64 static Toybox, `/bin/sh` interpreter link, patched S10+ UFS partition discovery, ext4 file traversal, presence of corrected bring-up init and S10+ config/udev files.

**Not verified:** the physical phone model/board revision, bootloader/DTBO compatibility, PIT capacity of the actual phone, UFS/controller initialization, USB gadget, panel/touch drivers, completeness of vendor firmware, any on-device boot sequence, clean Heimdall session-end acknowledgment, or full Nuxel desktop operation.

**Recommended stopping point before any further flash:** obtain and preserve the device's PIT, exact Download Mode product name and board revision, and a working stock recovery image. This remains experimental hardware bring-up, not an unattended production installation.
