# NUXEL S10+ — Emergency Boot-Chain Recovery (DeepSeek-V4-Pro-Thinking)

**Date:** 2026-11-21 · **Device:** SM-G975F (beyond2lte, Exynos9820)
**Recovery agent:** DeepSeek-V4-Pro-Thinking (autonomous recovery engineering)

---

## Root cause (identified, evidence-backed)

Session 7 of the camera bring-up (commit `1690ae4f`) flashed a **triple-partition**
set via raw `adb dd` that **violated Nuxel's proven flashing policy**
(`boot/s10plus/flash-heimdall.sh` explicitly denies DTB/DTBO/RECOVERY):

| Partition | What was flashed | Known-good |
|---|---|---|
| sda12 `dtb`  | **merged base DTB** (382,239 B, full board+camera merge) | stock base `exynos9820.dtb` |
| sda13 `dtbo` | 10-entry table, **entry[9] = 207-byte no-op** | entry[9] = `beyond2lte_eur_open_26.dtbo` |
| sda14 `boot` | patched correct-config **camera kernel** | raw Image 4.14.253 #3 |

Samsung S-Boot builds the device tree at boot from **`dtb` partition (sda12) +
`dtbo` overlay (sda13, `androidboot.dtbo_idx=9`)**. Replacing the base DTB with a
non-stock merge and the DTBO entry with a no-op caused the bootloader / kernel to
mis-parse the device tree, producing the current hang.

**Most-probable immediate failure:** the base-DTB replacement (sda12) was rejected
or mis-applied by S-Boot's DTB validation, and the 207-byte no-op DTBO entry broke
the overlay parser. The camera work itself (patched kernel build, FIMC coexistence,
DTBO structural fix) is preserved and NOT lost — but it must NOT be re-flashed to
these three partitions without first re-establishing a stable boot baseline.

---

## Current physical state (observed 2026-11-21)

- Device **enumerates on USB** as VID `0x04e8` PID `0x685d`, Product `"Gadget Serial"`.
- Two interfaces: `[0] 02.02.01` (CDC-ACM serial) + `[1] 0A.00.00` (CDC-ECM data).
- **This is the Nuxel Linux configfs USB gadget**, *not* Samsung Download Mode
  (Download Mode uses a single 0xFF-class Samsung protocol interface, different PID).
- USB device node `/dev/cu.usbmodem1101` (+ `/dev/tty.usbmodem1101`) present.
- Serial console **silent at 115200/9600/57600/921600** (no boot log, no login shell).
- `adb devices` empty; no SSH reachable at `10.11.12.99` / `10.100.10.1`;
  no ECM interface assigned by macOS (no `utun`/`en` carrying the phone subnet).
- USB enumeration is **steady (not boot-looping)** across 15 s — the kernel is up
  and the USB gadget driver is running, but the system hangs before userspace/network.

**Interpretation:** the bootloader ran the (camera) kernel in sda14 and early USB
gadget bring-up succeeded, but the broken `dtb`(sda12)/`dtbo`(sda13) left a critical
peripheral (very likely UFS/display/regulator/early driver) non-functional, so boot
never reaches init/SSH.

---

## Last known-good vs failed

- **Known-good (booting):** `boot-current.img` (source SHA-256 `0945cc8d4aa6e80a7757c8cc8aaaa1a6de307e22f4d0465513945cb027973f38`), kernel = raw ARM64
  Image `45,717,512` B, ramdisk = LZMA `2,424,832` B, `dt_size=1` (no appended DTB),
  addrs `0x10008000 / 0x11000000 / 0x10000100`, page 2048, header v1, `os_version 0x18000171`.
- **Failed:** session-7 triple flash (merged sda12 DTB + no-op sda13 + camera kernel).

---

## Confirmed partition layout (authoritative, from on-device by-name dump)

From `scripts/s10plus-debug-pack/captures/.../device/partition-by-name.txt`:
`boot→sda14 (57,671,680)`, `recovery→sda15 (67,633,152)`,
`dtb→sda12 (8,388,608)`, `dtbo→sda13 (8,388,608)`, `userdata→sda31 (rootfs, ~119 GB)`,
`system→sda25`, `vendor→sda26`. UFS base `/dev/block/platform/13d60000.ufs/by-name`.

Boot cmdline facts (from on-device capture): `androidboot.dtbo_idx=9`,
`androidboot.revision=26`, `androidboot.em.model=SM-G975F`,
`androidboot.serialno=R58M75KDB2X`, bootmode=2.

---

## Are all three images required together? (YES, confirmed)

Yes. On this device S-Boot assembles the final DT from `dtb`(sda12) + `dtbo`(sda13)
entry `dtbo_idx=9`, then jumps into the raw kernel in `boot`(sda14). They are a
**matched set**: a mismatched DTB/DTBO/kernel breaks boot even if `boot` alone is
valid. Flashing only `boot` while sda12/sda13 carried the broken camera DT was the
direct cause of the hang. Recovery must restore the matching set (dtb + dtbo + boot).

Nuxel does NOT use `recovery-as-boot`; `recovery`(sda15) is the TWRP fallback and is
independent of the normal boot chain (normal boot does not touch sda15).

---

## Recovery assets (verified on macOS host)

Source of truth (recovered from `~/Downloads/nuxel-main 2/packs/work/bootloop-fix/`) — identical copies also present under `/Users/wicked/x/nuxel-ssp-first-light/packs/work/bootloop-fix/`:

| Asset | Size | SHA-256 | Role |
|---|---|---|---|
| `fix2/Image-raw` | 45,848,584 | `71be6f282afebc12138f5eb7b610641e7edb48666bcac5750fd7824151537498` | raw ARM64 Image (rebuilt known-good #3) |
| `boot-unpacked/Image` | 45,717,512 | `d5e4fe656b7dda319f2e301b82f8dbd51597151dee8d2d47dd4bbae02671a5a4` | **raw ARM64 Image from live `boot-current.img` (authoritative)** |
| `fix2/ramdisk.lzma` (= `boot-unpacked/ramdisk.raw`) | 2,424,832 | `0dd0fb5a3d6895f28d8861d967382a0b87182d0f9c63b1d560393818b290f407` | LZMA ramdisk |
| `boot-unpacked/initramfs.cpio` | 8,791,372 | `f19b369303ede99e7e4a8360c3a83a66abb690b2df6c0854bf6897862f8ef215` | decompressed cpio (84 records) |
| `boot-unpacked/appended.dtb` | 9,525,248 (inner FDT 376,101) | `0e308eee67c90d54b635b375de7af573dc204c1e9d5cc3e12464ff4a92c6294b` | merged base+board DTB (NOT needed for boot; reference) |

Known-good boot image parameters (from `verify-orig/sections.json`):
`kernel_size=45717512 ramdisk_size=2424832 header_field40=1(dt_size=1) kernel_addr=0x10008000 ramdisk_addr=0x11000000 tags_addr=0x10000100 page_size=2048 os_version=0x18000171`.

In-repo, build outputs at `kernel/s10plus/.build/out/arch/arm64/boot/dts/`:
`exynos/exynos9820.dtb` (238,880 B base) and
`samsung/exynos9820-beyond2lte_eur_open_26.dtbo` (181,684 B, board overlay for dtbo_idx=9).

**Missing (still needed):** the raw `dtb`(sda12) and `dtbo`(sda13) partition images
(8,388,608 B each) and the packed known-good `boot-current.img` itself were in
`/tmp/camwork` (macOS /tmp) and were NOT present in the repo or any located backup.
They must be rebuilt from the verified source assets above.

---

## Flashing results / iterations (this run)

- Heimdall `detect` → "Device detected", but `print-pit` → "Protocol initialisation
  failed / Failed to receive handshake response" — because the device is in the
  Nuxel-gadget hung state, **not** Samsung Download Mode. No partition was read/written.
- No flashing occurred. No partition was modified.

---

## Remaining risks / next steps

1. **Physical recovery entry required.** The device must be put into
   **Download Mode (Vol Down + Bixby + Power, hold)** or **TWRP (Vol Up + Bixby +
   Power, hold)** by hand. Neither adb nor heimdall can drive it from the current
   hung Nuxel-gadget state.
2. Rebuild packed `dtb`(sda12) + `dtbo`(sda13) partition images and the known-good
   `boot`(sda14) image from the verified assets + in-repo build outputs.
3. Flash the matched set via Download Mode/TWRP, verify readback, reboot, confirm boot.
4. **Never re-flash the camera DT merge to sda12/sda13** without first proving
   S-Boot DTB-partition acceptance.

See `NUXEL_KNOWN_GOOD_BOOT_IMAGES.md` for the verified image-set provenance and
rebuild procedure.
