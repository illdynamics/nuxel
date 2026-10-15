# NEXT HARDWARE TEST — requires explicit user approval before execution

**Status: PREPARED, NOT EXECUTED. No device write or reboot has been performed.**

## What is proposed

Flash **one partition only — BOOT (`/dev/block/sda14`)** — with the
cmdline-independent diagnostic build, then observe. The 4 GiB Fedora rootfs in
USERDATA is **not** touched: it is already written, verified, and structurally
sound (`e2fsck` clean); rewriting it is unnecessary and takes much longer.

- Image: `build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img`
- Size: 22,433,792 bytes
- SHA-256: `eb77d658fb4fa95930fd13166970a00d6c9ab49dd439c6517b1da349a36e14e5`
- Kernel and merged DTB inside it are **byte-identical** to the currently flashed
  image; only the initramfs `/init` changed.

## Pre-flight confirmations (all verified 2026-10-15, read-only)

| Requirement | Status |
|---|---|
| Device identity | `R58M75KDB2X`, `beyond2lte` / SM-G975F, TWRP 3.7.0_9-2, ADB root ✓ |
| Partition identity | `boot → /dev/block/sda14`, `userdata → /dev/block/sda31` (verified by-name) ✓ |
| Partition capacity | BOOT 57,671,680 B ≫ image 22,433,792 B ✓ |
| Target fs not mounted | `mount | grep sda31` → empty ✓ |
| Recovery preserved | RECOVERY (`sda15`) untouched; local backup **byte-identical** to the partition (`4cc71d62…`) ⇒ TWRP restore path exists ✓ |
| Stock BOOT backup | **ABSENT** — `backups/s10plus/boot-original.img` is a zero-filled `DUMMY` placeholder. Recovery from a bad BOOT requires Odin firmware. This is a real, accepted risk |
| Structural validity | `ANDROID!` v1, page 2048, ARM64 `Image.gz`, merged DTB, 65-entry gzip newc, `/bin/sh → toybox`, `/init` 0755, 0 pack warnings ✓ |
| Flash-pack preflight | `05-preflight.sh --profile s10plus` → **PREFLIGHT PASS** (read-only) ✓ |
| Partitions that would change | **BOOT only.** No EFS/modem/recovery/bootloader/dtb/dtbo/misc writes |

## Procedure (only after the user says GO)

### 1. Push and flash BOOT from TWRP (never reboots automatically)

```bash
cd ~/x/nuxel
adb devices                       # expect: <serial>  recovery

adb push build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img /tmp/nuxel-boot-diag.img
adb shell 'sha256sum /tmp/nuxel-boot-diag.img'
# MUST print eb77d658fb4fa95930fd13166970a00d6c9ab49dd439c6517b1da349a36e14e5

adb shell 'test -b /dev/block/by-name/boot && echo boot-partition-ok'
adb shell 'dd if=/tmp/nuxel-boot-diag.img of=/dev/block/by-name/boot bs=4096 conv=fsync && sync'
```

### 2. Read back exactly the image length and hash it (flash verification only)

22,433,792 / 4096 = **5477** blocks exactly, so the readback is byte-exact:

```bash
adb exec-out 'dd if=/dev/block/by-name/boot bs=4096 count=5477 2>/dev/null' | shasum -a 256
# MUST equal eb77d658fb4fa95930fd13166970a00d6c9ab49dd439c6517b1da349a36e14e5
```

This proves the bytes, **not** that the bootloader accepted them.

### 3. Observation (do NOT auto-reboot; the operator chooses the moment)

1. Reboot to the normal boot path (TWRP → Reboot → System, or `adb reboot`).
2. Watch the phone for up to **3 minutes** and record:
   - How long the Samsung logo stays; does it disappear (display handoff) or
     fade with a backlight change?
   - Does it reboot by itself (≈100 s would indicate the Samsung softdog
     `softdog.soft_margin=100`, i.e. a hang — not necessarily a panic)?
   - Does any adb/USB device appear? (`adb devices` / `system_profiler SPUSBDataType` — the Fedora rootfs has no adb daemon, so absence proves nothing.)
3. Whatever happens, then force recovery: **Vol Up + Bixby + Power** → TWRP.

### 4. Retrieve the evidence (this is the point of the build)

```bash
# (a) rootfs copy — read-only mount, no writes to the fs
adb shell 'mkdir -p /mnt/diag && mount -o ro -t ext4 /dev/block/sda31 /mnt/diag && cat /mnt/diag/nuxel-boot-diag.log; umount /mnt/diag'

# (b) mount-free copy from the BOOT partition tail (independent of the rootfs)
adb exec-out 'dd if=/dev/block/by-name/boot bs=512 skip=$(( $(cat /sys/class/block/sda14/size) - 128 )) 2>/dev/null' | head -c 16384 | tr -d '\0'

# (c) if Fedora reached systemd, the journal is the proof
adb shell 'mount -o ro -t ext4 /dev/block/sda31 /mnt/diag && ls /mnt/diag/var/log/journal 2>/dev/null; umount /mnt/diag'
```

Save everything under `scripts/s10plus-debug-pack/captures/<new-timestamp>/`.

### 5. Decision tree for the result

| Observation | Meaning | Next action |
|---|---|---|
| `nuxel-boot-diag.log` exists, shows `cmdline` **without** `nuxel.device=`, shows `root mounted: /dev/sdaNN (ext4, mode=rw)` and no `[FATAL]` | H1 was right; the initramfs now finds and mounts the Fedora root | look for systemd evidence; if none, investigate Stage D (kernel features systemd needs) |
| log exists but ends at `[FATAL] s10plus: USERDATA not found after probe` | kernel ran, UFS partitions were not visible to `/init` in time | raise the probe budget / check `PARTNAME` visibility in the logged block-device map |
| log exists with `[FATAL] root mount failed` | kernel ran; the ext4 root was not mountable from the initramfs | examine the logged `dmesg` for UFS/SCSI/EXT4 errors |
| log's `dmesg` shows UFS or EXT4 probe errors | kernel problem, not init | Stage B work (kernel config/module) |
| **No log at all** in either slot, and the boot still loops | the kernel never reached `/init` — Stage A/B | the DTBO/DTB handoff or the kernel itself is failing; needs `console=ram` retrieval or UART |
| Fedora journal present | systemd started (Milestone 5) | move to Stage E: display (see below) |

### 6. Known Stage E blocker (independent of this test)

The downstream Samsung 4.14 kernel exposes **only fbdev** (`/dev/graphics/fb0`);
there is no `/dev/dri` and no `/sys/class/drm`. Phoc/Phosh need DRM/KMS, so a
Phosh session cannot start on this kernel as-is, and `greetd` still runs
`agreety --cmd shell`. A visible Nuxel interface therefore needs either an
fbdev-based compositor/shell path or a kernel with a DRM driver (mainline/`simplestreamer`).
Do not expect the panel to show Nuxel on this test.

## Rollback

- BOOT is recoverable by re-flashing any earlier image, e.g.
  `build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img`
  (`ceba64ab8c831928cffaae2da6b464034ef036be834346015beba3f128e8f510`) with the
  same `dd` procedure, or Odin for a stock BOOT.
- TWRP recovery itself is independent and matches the local backup
  (`4cc71d62…`); it is not modified by this test.
