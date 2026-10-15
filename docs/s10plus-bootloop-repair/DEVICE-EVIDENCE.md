# Phase 1 — real device evidence (TWRP ADB, read-only)

All data captured 2026-10-15 UTC. No device writes, mounts, reboots or wipes.

Capture directories (under `scripts/s10plus-debug-pack/captures/`):

- `20261015T063659Z-full-collection-5886/` — pack `12-full-diagnostics.sh`
  (pstore, last_kmsg, TWRP logs, partitions, recovery kernel info, image audits).
- `20261015T063922Z-mission-cybertiel/` — targeted mission reads
  (partition headers, DT table partitions, uevents, chosen/bootargs).

## 1. Connection / identity

| Item | Value | Source |
|---|---|---|
| ADB device | `R58M75KDB2X  recovery` | `adb devices -l` |
| Codename | beyond2lte / SM-G975F | `device/boot-properties.txt` |
| Board revision | 26 | `androidboot.revision=26` |
| Region | EUR OPEN | `region1=EUR region2=OPEN` |
| Bootloader | G975FXXSEFUL1 | `androidboot.bootloader` |
| VB state | orange | `androidboot.verifiedbootstate=orange` |
| recovery kernel | `4.14.113-g55f042627 #1 SMP PREEMPT ... aarch64` | `kernel/uname.txt` |

## 2. Previous-boot logs — what exists and what it really is

- `/sys/fs/pstore/` → **empty** (`pstore/NO-PSTORE-FILES.txt`; directory listing
  shows only `.` and `..`). ramoops parameters in the *recovery* kernel:
  `console_size=0`, `pmsg_size=16384`, `record_size=16384`, `dump_oops=1`
  (`kernel/pstore-settings.txt`). With `console_size=0` there is **no
  console-ramoops**, so no dmesg survives a reset on this kernel.
- `/proc/last_kmsg` → 41.7 KB, **735 lines** (`previous-boot/last_kmsg.txt`).

### The last_kmsg is the *recovery* boot's S-Boot log, not Nuxel's

Evidence (all inside `previous-boot/last_kmsg.txt`):

- exactly **one** `Samsung S-Boot 4.0 for SM-G975F (Dec 1 2021)` header and one
  `Starting kernel...` line, at t=4.842 s — i.e. a bootloader log only, no kernel
  ring buffer content;
- `avb_slot_verify ... DEBUG: recovery: Loading entire partition`;
- `make_security_decisions : (RECOVERY)`, `set_ddi_kernel_type : RECOVERY, 0x8`;
- `check_samsung_secure_info : Error validating footer (recovery)`,
  `[TIMA trusted boot]: SEAndroid MAGIC failure (recovery.img)`;
- device cmdline has `bootmode=2` (recovery mode).

Conclusion: **this is the bootloader log of the currently running TWRP boot.**
It must not be attributed to the failed Nuxel boot. A Nuxel kernel log is simply
**not available**, and it cannot be: the on-device buffer is cleared at the next
S-Boot run (`[SECD] sec_debug_init_buffer: this is PIN RESET, clear all`,
clearing `first2m_kmsg`, `boot_history`, `auto_analysis`, … at t=1.76 s).

## 3. Reset / watchdog state

| Item | Value | Source |
|---|---|---|
| `sec_debug.reset_reason` | 9 (`NP`) | `previous-boot/boot-reason.txt`, `kernel/cmdline.txt` |
| raw power source | `0x0000100140010000` (PIN reset) | S-Boot log |
| `bootmode` | 2 (recovery) | S-Boot log / cmdline |
| `oops=panic` | present in the bootloader cmdline | `kernel/cmdline.txt` |
| `softdog.soft_margin=100`, `softdog.soft_panic=1` | present | `kernel/cmdline.txt` |
| `console=ram loglevel=4` | present | `kernel/cmdline.txt` |

`sec_debug.reset_reason=9` describes the reset **into the current TWRP boot**
(power-key/PIN reset performed to reach recovery). It is *not* a record of the
Nuxel failure mode. `softdog.soft_margin=100` matters: a hung kernel/init is
rebooted by the hardware watchdog after ~100 s — a hang and an explicit `reboot`
are indistinguishable to a human watching only the Samsung logo.

## 4. Partitions (bytes, verified on device)

| Name | Node | Bytes | Source |
|---|---|---|---|
| BOOT | `/dev/block/sda14` | 57,671,680 | `device/read-only-block-sizes.txt`, `/sys/class/block/sda14/size` |
| RECOVERY | `/dev/block/sda15` | 67,633,152 | same |
| USERDATA | `/dev/block/sda31` | 119,126,622,208 | same |
| DTB | `/dev/block/sda12` | 8,388,608 | same |
| DTBO | `/dev/block/sda13` | 8,388,608 | same |
| SYSTEM | `/dev/block/sda25` | 5,976,883,200 | same |

USERDATA was **not mounted** during capture (`mount | grep sda31` empty) — the
Fedora rootfs is untouched.

## 5. What S-Boot really does with the boot image (from its own log)

```
[0: 2.954] [UFDT] BOOT IMG HDR V1.. FINDING DTB ENTRY
[0: 2.956] [UFDT] Little Find DTB Entry[0]: Rev:(S:0, E:255, X:0, D:26)
[0: 2.957] [UFDT] FINDING DTBO ENTRY
[0: 2.969] [UFDT] Little Find DTBO Entry[9]: Rev:(S:26, E:255, X:0, D:26)
[0: 3. 12] [UFDT] DT Overlay Complete!
```

S-Boot takes the **base DTB from the boot image's appended DTB section**, then
**always overlays DTBO entry[9]** taken from the `dtbo` partition. It also
rewrites the boot args:

```
[0: 1.82] [SECD] update_cmdline: add cmdline as 9
[0: 1.82] init_cmdline: default: console=ram loglevel=4
[0: 3.100] dtb_merge_bootargs: bootargs_ext not found
[0: 3.100] get_cmdline_buffer: last Index: 84e|1000
[0: 4.379] Updating device tree @0x8a000000: done
```

Real device tables read read-only from `dtb`/`dtbo` partitions
(`20261015T063922Z-mission-cybertiel/device/dtb_part_256k.bin`,
`dtbo_part_1920k.bin`):

- `dtb` (sda12): dt_table, 1 entry, rev `0x00..0xff` (wildcard), 239,644 bytes.
- `dtbo` (sda13): dt_table, 10 entries, rev minors
  `0x0f,0x10,0x11,0x12,0x13,0x14-0x16,0x17,0x18,0x19,0x1a-0xff`.
  `0x1a` = 26 decimal ⇒ **entry[9] is the rev-26 overlay**, matching
  `androidboot.dtbo_idx=9`. Extraction: `/tmp/dtbo9.dtb` (181,684 bytes).

## 6. Backups — important negative result

| File | Verdict |
|---|---|
| `backups/s10plus/twrp-recovery-original.img` | **VALID.** sha256 `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87`, byte-identical to on-device `/dev/block/sda15` |
| `backups/s10plus/boot-original.img` | **NOT A BACKUP.** 57,671,680 bytes of zeros; first 8 bytes are `DUMMY\0\0\0`; header magic is not `ANDROID!` |

⇒ A working recovery restore path exists (TWRP), but **the stock BOOT partition is
not backed up**; restoring Android would require Odin firmware.

## 7. Display path on this kernel (Stage E pre-check)

In TWRP (same downstream Samsung 4.14 kernel family):

- `/dev/dri` → **does not exist**; `/sys/class/drm` → **does not exist**;
- `/dev/graphics/fb0`, `fb1` exist (legacy fbdev, major 29).

⇒ The downstream kernel exposes **fbdev only**. Wayland compositors (Phoc/Phosh)
need DRM/KMS; they cannot run on this kernel unmodified. This is independent of
the bootloop but caps Milestone 6 with the current kernel.
Source: `20261015T063922Z-mission-cybertiel/device/display-state.txt`.

## 8. Kernel payload

- Boot image kernel: gzip `Image.gz`, 16,030,259 bytes → 44,980,232 bytes raw
  (`Image`), sha256 `33cac63a8b0c0f575a2e1bc782c1efe54018658f65ba741679531c113ac0ec57`
  (`build/out/s10plus/build-manifest.json`).
- TWRP recovery image kernel: 44,838,924 bytes uncompressed — same downstream
  4.14 Exynos 9820 kernel family, and that kernel boots on this unit.
