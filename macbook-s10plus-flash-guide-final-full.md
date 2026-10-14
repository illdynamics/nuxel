# Nuxel S10+ Exynos — MacBook Fedora phone build & controlled flash guide

**Date:** 2026-10-14  
**Device target:** Samsung Galaxy S10+ Exynos 9820 (`beyond2lte`, e.g. SM-G975F/FD). **NOT** Snapdragon variants.  
**Stage:** Experimental first-light boot candidate and separate untested Fedora ARM64 userspace builder. **NOT production-ready or known bootable on a physical S10+.**

## Read this first — what has and has not been fixed

- **Yes:** The PIT you provided reports `CPU/bootloader tag: LSI9820`, **41 entries**, and separate UFS `DTB`, `DTBO`, `BOOT`, `SYSTEM`, `USERDATA` partitions. The release includes your text PIT and a read-only checker.
- **No:** A PIT does **not** identify hardware revision 26, the contents of `DTBO`, or whether S-Boot will apply a second overlay. The uploaded **merged** DTB contains `BEYOND2LTE EUR OPEN 26`; it may not match your physical device.
- **No:** BOOT's 14,080 PIT blocks cannot be turned into a reliable size in *bytes* without independently establishing the partition block unit; USERDATA's PIT block count is **0** (extends to disk end). Do not assume the image fits merely from those counts.
- **Yes:** The newly packaged boot image preserves the original ARM64 Exynos kernel and merged DTB, has `/bin/sh` and a USERDATA PARTNAME resolver, and now mounts the root writable on the supplied `rw` command line. This only passes *offline* tests, not handset boot.
- **Yes:** The supplied `nuxel-beyond2lte-rootfs-diagnostic-fixed.img` is a clean S10+ bring-up root with Motorola-specific configuration removed. It contains a static first-light framebuffer diagnostic and Nuxel Home *assets*, but it **does not** contain the full Fedora phone environment.
- **No:** The Heimdall 100%-then-`Failed to receive session end confirmation!` problem is **not resolved by these images**. This is a missing Odin protocol EndSession reply. A 100% progress bar by itself does not prove data committed on flash. The wrapper logs and explicitly fails rather than asserting success.
- **Yes:** There is now a Fedora 43 **aarch64 RPM** build recipe for real Python 3 + systemd + Phosh + Phoc. It must be executed on a network-connected Mac running Docker. This sandbox could not run it and **no full Fedora phone rootfs binary is included**. OpenRC was used by the abandoned Alpine path; Fedora uses **systemd**.

If your requirement is *a guarantee that the device displays a working touchscreen Nuxel phone UI immediately after the next flash*, **none of these files yet meets that requirement**. Actual kernel panel/DRM/GPU/touch, bootloader DTBO, and a hardware boot test remain necessary.

## 1. Find the output artifacts

Unpack `nuxel-s10plus-fedora-updated-dropin.zip` and work inside the `nuxel-main` directory.

| Path | What it contains |
|---|---|
| `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img` | ARM64 S10+ boot v1, merged DTB rev26 **unmatched to device** |
| `build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img` | **Diagnostic** S10+ rootfs (not Fedora full runtime) |
| `images/s10plus/build-phone-rootfs-fedora.sh` | Mac Docker Fedora 43 ARM64 full-runtime builder |
| `build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img` | **Only appears after** successful Fedora build on your machine |
| `tools/s10plus/check-device-pit.py` | Safe text PIT check |
| `tools/s10plus/verify-artifacts.py` | Boot + diagnostic rootfs offline verifier |
| `tools/s10plus/verify-fedora-phone-rootfs.py` | Full Fedora ARM64 package verifier |
| `build/out/s10plus/RELEASE-VALIDATION.txt` | Offline verification result and limitations |
| `S10PLUS-PROGRESS.md` | Evidence-based progress table |

Check archive contents and hashes:

```bash
cd ~/x/nuxel # use your own extracted repo directory
shasum -a 256 build/out/s10plus/*-fixed.img
cat build/out/s10plus/SHA256SUMS-fixed.txt
python3 tools/s10plus/verify-artifacts.py \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
```

Expected: `BOOT PASS` and `ROOT PASS`. This does **not** validate DTBO compatibility or boot acceptance.

For a read-only view of ext4 without native macOS mounting:

```bash
brew install e2fsprogs
"$(brew --prefix e2fsprogs)/sbin/debugfs" -R 'ls -l /' \
  build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
```

For a full filesystem integrity check on macOS (without mounting):

```bash
"$(brew --prefix e2fsprogs)/sbin/e2fsck" -fn \
  build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
```

Stop if the image fails either integrity check.

## 2. Match the exact handset and DTBO — HARD STOP if unknown

Your specific PIT has the expected entries:

| Entry | PIT identifier | Block count |
|---|---:|---:|
| DTB | 12 | 2,048 |
| DTBO | 13 | 2,048 |
| BOOT | 14 | 14,080 |
| SYSTEM | 25 | 1,459,200 |
| USERDATA | 31 | 0 (extends to disk end) |

Run the included checker:

```bash
python3 tools/s10plus/check-device-pit.py \
  docs/s10plus-device-pit-2026-10-14.txt \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
```

**Do not confuse this with verifying `BEYOND2LTE EUR OPEN 26`.** You must identify the board hardware revision from the actual phone's bootloader/recovery environment or its model- and revision-matched stock DTBO/kernel information. With an actual working TWRP or Android system that exposes it, useful *read-only* evidence may include:

```bash
adb devices
adb shell 'cat /proc/device-tree/model 2>/dev/null; cat /proc/cmdline 2>/dev/null'
adb shell 'getprop ro.boot.hw_rev 2>/dev/null; getprop ro.product.model 2>/dev/null'
```

These commands are only expected to work in Android/TWRP with ADB, **not** in Samsung Download Mode. Different firmware may not expose a readable `hw_rev`. If the revision cannot be confirmed, **do not treat the merged boot image as approved for flashing**. Never flash or overwrite the DTB/DTBO partitions as a shortcut.

Also verify BOOT and USERDATA byte capacities via a trusted device-aware mechanism before flashing. The checker intentionally refuses to infer a byte unit from Heimdall's text PIT.

## 3. Build the **real Fedora ARM64 Nuxel phone runtime** on your MacBook

Requirements: Apple Silicon, Docker Desktop running, internet access to Fedora 43 repositories, adequate disk space (allow ~8 GiB free). The Docker *container* is ARM64; the host Mac architecture is not itself the rootfs's provenance.

```bash
cd ~/x/nuxel
docker info >/dev/null
docker run --rm --platform linux/arm64 fedora:43 uname -m
# Expected output: aarch64
bash images/s10plus/build-phone-rootfs-fedora.sh
```

This runs real Fedora 43 DNF/RPM package installation inside the ARM64 container, stages S10+ overlays and the Nuxel Home assets, generates ext4 with e2fsprogs, and checks actual **ARM64 ELF binaries** for Python 3, Phosh, Phoc, systemd, and init. Dependencies must resolve; a missing package aborts. **Do not treat a skeleton /etc directory as a successful installation.**

Default destination (created **only if that build succeeds**):

```text
build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

Check it:

```bash
python3 tools/s10plus/verify-fedora-phone-rootfs.py \
  --ext4 build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
"$(brew --prefix e2fsprogs)/sbin/e2fsck" -fn \
  build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
shasum -a 256 build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

**Fedora runs systemd, not OpenRC.** Both Phosh and Phoc are installed as Fedora ARM64 binaries, but a graphical phone login is deliberately not enabled. A real DRM/KMS/GPU/seat and working input device must be shown on the S10+ before enabling a login manager or compositor; otherwise the system can boot headlessly with a black phone display. The Nuxel first-light service only tries to draw through `/dev/fb0` if the kernel creates it. Even a successful Fedora image build does not prove the Exynos display driver works.

This branch also does **not** manufacture Samsung proprietary firmware, working modem integration, or a complete Nuxel Home runtime merely by copying Python source. To get a fully usable Linux phone UI you still need hardware-specific porting on the actual unit.

## 4. Backups, download mode, Heimdall status

USERDATA flashing **DESTROYS ALL USERDATA**. Have exact model-matched stock firmware/BOOT and a functioning recovery route before trying. Do not modify EFS, modem, bootloader, DTBO, or KG/FRP state to make a custom image work.

Use a direct data cable, no hub. On the Mac:

```bash
heimdall version
heimdall detect
heimdall print-pit --no-reboot | tee s10plus-pit-current.txt
```

Use your actual downloaded PIT to compare with the included `docs/` reference. The `print-pit` operation can leave Heimdall in a session that requires deliberately re-entering Download Mode before the next command.

**Heimdall error interpretation:**

```text
Uploading BOOT 100%                  # host transfer reached 100%
BOOT upload successful               # host says transfer completed
Uploading USERDATA 100%              # host transfer reached 100%
USERDATA upload successful           # host says transfer completed
Ending session...
ERROR: Failed to receive session end confirmation!  # FLASH NOT CONFIRMED
```

This final error is an Odin/Heimdall session protocol acknowledgment problem. It has been reported even when the flashed image was **not installed**. Changing ext4/rootfs files does not repair this protocol. `--no-reboot` avoids a host-initiated reboot request, but is **not a proven workaround** for the missing EndSession reply. Do not repeatedly overwrite an unverified phone just to make the progress bar disappear.

The patched wrapper captures the full Heimdall log and exits nonzero when the session fails. If the same failure repeats with Mac and Fedora 43, an independently validated Samsung Odin flashing process on Windows, or a recovery-mode installation after verifying actual block-device identities, may be more appropriate; neither is automatically safe or guaranteed on this device.

## 5. Controlled diagnostic flash (only after all hard-stop checks pass)

**Do not substitute this diagnostic image for the full Fedora phone rootfs.** It is only the smallest possible test for a framebuffer first-light screen.

```bash
bash boot/s10plus/flash-heimdall.sh \
  --device s10plus \
  --pit-text docs/s10plus-device-pit-2026-10-14.txt \
  --boot build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img \
  --dry-run
```

After verifying the **physical board revision**, independent partition byte capacities, clean filesystem, bootloader unlock state, complete backups and actual recovery path, remove `--dry-run` if you accept the risk of an unverified hardware flash. The wrapper asks for confirmation and refuses partition aliases other than BOOT and USERDATA.

For the Fedora full-runtime image **only after section 3 succeeded and you've first established a bootable diagnostic baseline**, change the `--rootfs` path to:

```text
build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

If you are unable to confirm the board revision, **STOP**; flashing the wrong merged DTB can prevent boot. An image can be internally valid and completely wrong for the actual board.

## 6. If Download Mode remains at 100%

- Wait until USB activity ceases; do not unplug midway through transfer.
- Treat an EndSession error as a failed **confirmation**, regardless of 100% transfer bars.
- If the device stays stuck after activity has stopped, Samsung S10+ commonly force-restarts with **Volume Down + Power** for roughly 7–10 seconds. To attempt Recovery, switch promptly to **Volume Up + Bixby + Power** when the screen goes dark, USB connected. Timing can vary by unit/firmware.
- Try recovery first where possible; keep a known-good compatible stock BOOT image and Odin/Heimdall restoration plan available. Do not deliberately boot an unverified image when recovery would let you inspect the state safely.
- A boot loop, black display, or a Download Mode return does not identify the exact cause: missing session commit, wrong DTBO, S-Boot verification, kernel panic, UFS mount and missing panel drivers can all contribute.

## 7. What counts as actual success

1. **Heimdall stage:** Session ended successfully *or* the actual installed partitions have independently been verified. Host 100% by itself is insufficient.
2. **Boot stage:** The Samsung hands off to the custom ARM64 kernel; a real log proves initramfs executed.
3. **Rootfs stage:** `/sys/class/block` identifies the correct USERDATA partition by `PARTNAME`; ext4 mounts and `switch_root` reaches Fedora systemd (or diagnostic PID1).
4. **Display first-light:** Nuxel diagnostic pattern appears on the AMOLED via a real framebuffer/DRM driver. A successful binary write to `/dev/fb0` without a visible screen is not full proof.
5. **Fedora phone UI:** Real Phoc/Phosh starts with working display, touch, session services and Nuxel Home. Then separately verify power, radio, audio, camera, WiFi, sensors and suspend.

Until step 5 succeeds, the device is in **bring-up**, not a completed Fedora Nuxel phone release.

## 8. Sources for external protocol/distro facts

- Heimdall `BridgeManager.cpp` implements EndSession with `SendPacket` and `ReceivePacket` (upstream): https://github.com/Benjamin-Dobell/Heimdall/blob/master/heimdall/source/BridgeManager.cpp
- Recorded Heimdall EndSession failures where 100% upload did not install recovery: https://gitlab.com/BenjaminDobell/Heimdall/-/issues/486
- Fedora Phosh ARM64 RPM: https://packages.fedoraproject.org/pkgs/phosh/phosh/
- Fedora Phoc package: https://packages.fedoraproject.org/pkgs/phoc/phoc/
- Fedora systemd: https://packages.fedoraproject.org/pkgs/systemd/systemd/

The firmware-specific partition values in this guide come from **your**
`docs/s10plus-device-pit-2026-10-14.txt`, not from a generic Samsung example.
