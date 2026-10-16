# A27 — BOOT FLASH RECEIPT (seamless original-animation first light)

Cycle: A27 (2026-10-16, UTC 22:31). Operator action: the handset was placed in
TWRP 3.7.0_9-2 for ONE planned BOOT-only update. Nothing else was written.

## What was on the device before the flash (measured, not assumed)

```
$ adb shell id                        -> uid=0(root) ... context=u:r:su:s0
$ adb shell ls -l /dev/block/by-name/boot,userdata
  boot     -> /dev/block/sda14        (56320 sectors = 57,671,680 bytes)
  userdata -> /dev/block/sda31
$ dd if=/dev/block/by-name/boot -> 57,671,680 bytes
  sha256 b702fc7c8b6f643c499a0b9deaeb8d733e28c78d9bf941957ec56cc155c73d13
  first 51,718,144 bytes == debug-candidates/A25/boot.img (sha256 ad5ca5d9…) EXACTLY
  (the remaining 5,953,536 bytes are stale bytes from an older, larger image;
   S-Boot only reads header-declared sizes)
  embedded kernel payload sha256 48b9810f… == debug-candidates/A25/Image-A25
=> the handset was running the A25 BOOT candidate, as recorded.
```

Evidence captured before any write (kept under
`docs/s10plus-autonomous-boot-repair/evidence-a27/`):

| File | What it is |
|---|---|
| `last_kmsg.txt` | 2,097,152 bytes of the PREVIOUS boot's ram console (S-Boot → kernel) |
| `pstore-dmesg-ramoops-0.txt` | 27,117 bytes still live in pstore |
| `boot-installed.img` (build/out/s10plus/a27/) | byte copy of the installed BOOT partition |
| `scripts/nuxel-adb-flash-pack/backups/nuxel-adb/20261015T223153Z-R58M75KDB2X/boot-before.img` | the same bytes, in the flash pack's own backup layout |

USERDATA was **not** written, mounted read-write, or erased at any point.

## The candidate

```
candidate      A27
boot.img       build/out/s10plus/debug-candidates/A27/boot.img
               51,605,504 bytes  sha256 48ad61afa91b6fe50278443ecae0695724f706a80de383e0acb021d030620cea
Image-A27      48,912,392 bytes  sha256 e104da7e9be713f8b45f84561ba50e614f7f8ff4e9ba2ba4c9a6c0978309cd1e
initramfs      10,896,628 bytes  sha256 0a3655b59b3c8eb26a0d5ceabee5693a19609904a5d92a149fcae074091ddcf7
nuxel-fb-phone 66,104 bytes      sha256 702956d676439e3f19a5fe663822c12f0be1008447222bbdb6078f0c43a9902c
first-light    2,074,144 bytes   sha256 128e9f0250ef0e4a0a372744bbd85d2ab1c4be8561511e2da906920ed9be06fc
partition      57,671,680 bytes  slack 6,066,176 bytes
```

Base: the A25 archive that boots today (`sha256 88e9b60f…`). Exactly three members
differ from it:

1. `opt/nuxel/nuxel-fb-phone` — rebuilt from `tools/s10plus/nuxel-fb-phone.c` with
   the NUXSPL01 renderer (release gate: the *binary* must contain
   `NUXEL_FIRSTLIGHT_FRAME0_PAINTED`, not a comment);
2. `opt/nuxel/nuxel-firstlight.rawspl` — frame 0 of the original MP4-derived
   container, uncompressed, produced by `tools/s10plus/a26/make-firstlight-asset.py`;
3. `/init` — passes the asset to the painter, logs its presence, and honours the
   new `/usr/lib/nuxel/ui.pinned` rule so a BOOT candidate can never overwrite a
   UI that was deployed live (see `NUXEL-LIVE-DEPLOYMENT-QUALITY.md`).

## Pre-flash verification (fail-closed, all PASS)

* `tools/s10plus/a27/test-firstlight.sh`: 16 checks — the C renderer's frame is
  byte-identical to an independent Python implementation of the *player's* maths
  (`c341463ac39b5a10…`), the asset regenerates byte-for-byte, its palette byte
  order is the original's (MAE 4.875/255 vs an ffmpeg decode of MP4 frame 0, and
  18.762/255 if the palette is byte-swapped), and every malformed asset is
  rejected by name (short header, bad magic, reserved, unsupported flags,
  palette count, bad dimensions, size overflow, truncated plane, trailing bytes,
  flat palette).
* `tools/s10plus/verify-a25-boot.py`: PASS — ANDROID! v1 header, page 2048, raw
  arm64 Image (not gzip), initramfs embedded at offset 33,809,680 and identical
  member-by-member to the built archive, ramdisk == built initramfs + 64 KiB
  padding, pinned systemd payload `848149cf…`, fits the partition.
* `scripts/nuxel-adb-flash-pack/05-preflight.sh`: PASS (device identity,
  partition capacity, image type).

## The write

```
$ bash scripts/nuxel-adb-flash-pack/scripts/03-flash.sh --profile s10plus \
      --serial R58M75KDB2X --boot .../A27/boot.img --boot-only \
      --backup-dir .../backups/nuxel-adb --execute
  BACKING UP BOOT to Mac: backups/nuxel-adb/20261015T223153Z-R58M75KDB2X
  FLASHING BOOT: 51,605,504 bytes -> /dev/block/sda14
  VERIFIED BOOT: 48ad61afa91b6fe50278443ecae0695724f706a80de383e0acb021d030620cea
PASS: every written partition matches its local image by full SHA256 readback.
```

Independent readback (not the flashing tool's own claim):

```
$ adb shell dd if=/dev/block/by-name/boot ... | adb pull
  51,605,504 bytes sha256 48ad61afa91b6fe50278443ecae0695724f706a80de383e0acb021d030620cea
  == the candidate byte-for-byte
```

No RECOVERY, DTB, DTBO, EFS/SEC_EFS, PIT, bootloader, radio or USERDATA write.

## Expected visual result (must be observed, not assumed)

`SAMSUNG BOOTLOADER → NUXEL ORIGINAL FIRST FRAME → FULL ORIGINAL ANIMATION →
NUXEL HOME UI`. The obsolete two-second diagnostic splash must not appear; if the
asset were malformed the painter would print `NUXEL_FIRSTLIGHT_REJECTED=<reason>`
and fall back to that diagnostic frame, which is the honest failure mode.

## Rollback

```
# the exact previous BOOT (A25), 57,671,680 bytes:
scripts/nuxel-adb-flash-pack/backups/nuxel-adb/20261015T223153Z-R58M75KDB2X/boot-before.img
build/out/s10plus/a27/boot-installed.img
# 51,718,144-byte candidate form: build/out/s10plus/debug-candidates/A25/boot.img
bash scripts/nuxel-adb-flash-pack/scripts/03-flash.sh --profile s10plus \
     --serial R58M75KDB2X --boot <that file> --boot-only --execute
```
