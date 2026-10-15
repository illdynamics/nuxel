# Nuxel ADB Flash Pack — reusable S10+ / G7 Power recovery flasher

A standalone, **macOS-friendly** BOOT + rootfs raw-image flasher that works from a root-capable ADB recovery (TWRP or equivalent). The contents can be copied directly to `~/x/nuxel/scripts/nuxel-adb-flash-pack/`. Python 3.9+ and `adb` are the only required executables. Uses bounded-memory streams, so even a 4 GiB or larger rootfs does not need to be copied to the phone's RAM.

**Not a bootloader unlocker, stock firmware installer, or guarantee of a successful boot.** Writes are explicitly requested and destructive. The first run always should be discovery/preflight, never flash.

## Layout

- `scripts/nuxel-adb-flash.sh`: main CLI (`--action discover|preflight|backup|flash|verify`).
- `scripts/nuxel_adb_flash.py`: implementation; no third-party Python modules.
- `scripts/01-discover.sh`: read-only device partition/mount/slot inventory.
- `scripts/02-backup.sh`: BOOT backup to Mac (optional separate RECOVERY backup).
- `scripts/03-flash.sh`: guarded rootfs → SHA readback → BOOT → SHA readback.
- `scripts/04-verify.sh`: read back both partition image ranges and hash them without writing.
- `scripts/05-preflight.sh`: offline image type/hash and online partition safety validation.
- `tools/doctor-macos.sh`, `tools/install-macos-deps.sh`, `tools/list-device-partitions.sh`.
- `tests/`: self-contained mocked ADB tests; they **never** write to a phone.

## Setup on your MacBook

```bash
unzip nuxel-adb-flash-pack.zip -d ~/x/nuxel/scripts/
cd ~/x/nuxel/scripts/nuxel-adb-flash-pack
bash tools/doctor-macos.sh
# Optional dependencies, explicit opt-in:
bash tools/install-macos-deps.sh --apply
adb devices  # must identify an accessible recovery (preferably TWRP) with root ADB
```

If the ZIP's directory is named `nuxel-adb-flash-pack`, keep that directory within `scripts`; do not overwrite Nuxel's existing scripts.

### 1. S10+ — discover and preflight (NO device writes)

```bash
bash scripts/01-discover.sh --profile s10plus
bash scripts/05-preflight.sh --profile s10plus \
  --boot ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

S10+ profile is locked to the **verified by-name partitions** `/dev/block/by-name/boot` and `/dev/block/by-name/userdata`. The actual partitions are resolved through `readlink -f` at runtime and their capacities checked through `blockdev --getsize64` or sysfs. The profile checks `ro.product.device=beyond2lte`.

### 2. S10+ — backup (read-only)

```bash
bash scripts/02-backup.sh --profile s10plus --backup-recovery \
  --backup-dir ~/x/nuxel/backups/s10plus
```

BACKUPS are stored on the Mac. Backing up USERDATA in full is deliberately **not automatic**; that partition may hold ~111 GiB and the script **does not preserve Android personal data**. Back it up separately *before* you overwrite it.

### 3. S10+ — flash and readback (DESTRUCTIVE)

```bash
bash scripts/03-flash.sh --profile s10plus \
  --boot ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img \
  --backup-dir ~/x/nuxel/backups/s10plus \
  --execute
```

Before **any writes**, you must type the phrase printed on screen: `FLASH <ADB_SERIAL> boot userdata`, followed by `ERASE-USERDATA`. It backs up BOOT to the Mac automatically, writes rootfs, verifies the **entire rootfs** with readback SHA-256, then writes BOOT and verifies it. It does **not** automatically reboot. Do not flash if the target filesystem is mounted, even via dm-crypt/mapper, and do not consider hash equality proof of kernel/device-tree compatibility.

### 3b. S10+ — BOOT-only flash (kernel / initramfs / DTB experiments)

For kernel, initramfs or device-tree work the rootfs must not be rewritten. The
pack supports a BOOT-only mode that never resolves, mounts, writes or verifies
USERDATA:

```bash
bash scripts/05-preflight.sh --profile s10plus --boot-only \
  --boot ~/x/nuxel/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img

bash scripts/03-flash.sh --profile s10plus --boot-only --execute \
  --boot ~/x/nuxel/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img \
  --backup-dir ~/x/nuxel/backups/s10plus
```

* Confirmation phrase for boot-only is `FLASH <ADB_SERIAL> boot` (no
  `ERASE-USERDATA` prompt, because USERDATA is not a target).
* BOOT is still backed up to the Mac first, and the mandatory full SHA-256
  readback still decides pass/fail. The receipt contains `"boot_only": true`.
* `--action verify --boot-only` re-reads and hashes only BOOT.

### 4. Re-verify existing images (read-only)

```bash
bash scripts/04-verify.sh --profile s10plus \
  --boot ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

This compares the exact bytes of both local images with the corresponding prefix of each partition (does not include unused trailing partition space). The 4 GiB USERDATA readback can take several minutes and has no USB transfer progress output while hashing.

## Moto G7 Power (ocean) — A/B slots are different!

The **G7 Power is an A/B-slot device**: BOOT is generally slot-specific (`boot_a` / `boot_b`). The recovery may occupy a boot slot, so **flashing a boot partition can remove your installed recovery**. Recoverability must be established independently before proceeding. The `g7power` profile does **not** choose any flash partitions for you. It requires explicit names and verifies the selected BOOT slot matches `getprop ro.boot.slot_suffix`. Do not copy the S10+ partition assumptions blindly.

Start read-only:

```bash
bash scripts/01-discover.sh --profile g7power
adb shell 'getprop ro.boot.slot_suffix; getprop ro.product.device; ls -l /dev/block/by-name/'
```

If you verified that the recovery exposes `boot_a` and `userdata` and active slot is `_a` (EXAMPLE ONLY), inspect the chosen targets:

```bash
bash scripts/05-preflight.sh --profile g7power \
  --boot-partition boot_a --rootfs-partition userdata \
  --boot /absolute/path/to/g7power-nuxel-boot.img \
  --rootfs /absolute/path/to/g7power-nuxel-rootfs.img
```

**Do not assume USERDATA is the intended G7 rootfs target.** If your G7 mission/layout instead specifies `system_a`, use `--rootfs-partition system_a` **only after inspecting the phone's actual table, format, partition capacity, and root mount logic**. This tool does not decide your rootfs placement or handle dynamic partitioning, AVB/verified-boot configuration, fastboot boot slots, DTBs, or image signing. An ext4 image must be raw (not Android sparse).

Once you have independently verified the installation layout, the same `--action flash --execute` workflow works with those arguments. Always retain a tested recovery path on A/B devices.

## Other devices / serial selection

```bash
bash scripts/01-discover.sh --profile generic --serial DEVICE_ADB_SERIAL
bash scripts/05-preflight.sh --profile generic --serial DEVICE_ADB_SERIAL \
  --boot-partition boot_a --rootfs-partition system_a \
  --boot /path/to/boot.img --rootfs /path/to/raw-ext4.img
```

Generic mode requires explicit partitions; only `boot`, `boot_a`, `boot_b` and `userdata`, `system`, `system_a`, `system_b` are accepted. Safety-critical partitions (EFS, modem, bootloader, RECOVERY, DTBO, VBMETA, etc.) are always blocked as flash destinations. Mount checks reject mounted Data or System targets. Only choose a pair known to be compatible with your kernel and bootloader.

## Safety / guarantees

1. `discover`, `preflight`, `backup`, `verify` never write to device partitions.
2. `flash` requires `--execute` **and** interactive exact device/partition confirmation; rootfs flash to USERDATA asks for explicit data-loss consent.
3. Root shell and positive recovery identity are required. Device codename is checked for device profiles.
4. All image and partition sizes are checked before writes. BOOT must have `ANDROID!` header; rootfs must have raw ext4 magic. Android sparse files are rejected.
5. BOOT is backed up to Mac **before** writing either partition; optionally include recovery if it exists separately (`--backup-recovery`). A JSON receipt records phase and hashes.
6. Rootfs is flashed and fully read back **before BOOT is modified**. If verification fails, flash stops. BOOT also receives a full SHA-256 readback.
7. A successful `dd` or SHA-256 does **not** mean Nuxel can boot, initialize the screen, or start Phosh. No auto-reboot, no wiping, no ADB root escalation.
8. This intentionally does not back up Android user data automatically. A complete data backup is a **precondition** when selecting USERDATA as a target.

### Failure states

If the script prints `STOP`, do **not** reboot into the flashed image, especially if it reports an interrupted or unverified write. Read the receipt under your Mac's `--backup-dir`. If it says `ROOTFS_VERIFIED`, the rootfs succeeded but BOOT was not yet verified. If it says `FLASH_AND_READBACK_VERIFIED`, both exact image ranges matched. This is storage verification only.

### Tests

```bash
python3 -m unittest discover -s tests -v
```

Automated tests use mock ADB or pure functions. **They never interact with a real device.**

### Additional helpers

```bash
bash tools/check-local-images.sh /path/to/boot.img /path/to/rootfs.img
bash tools/list-device-partitions.sh --serial YOUR_ADB_SERIAL
bash tools/run-mock-tests.sh
```

**Hash nuance:** Checking against the original image is appropriate immediately after flashing, while recovery still has the rootfs unmounted. Once a phone has booted and written logs, journal files, or state into its rootfs, a later partition hash may legitimately differ from the original image; that does not necessarily mean the flash originally failed. Keep the first successful readback receipt.
