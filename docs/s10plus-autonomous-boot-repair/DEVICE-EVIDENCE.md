# DEVICE-EVIDENCE (cycle 2, started 2026-10-15T07:05Z)

Capture: `scripts/s10plus-debug-pack/captures/20261015T070500Z-A1-postfail/`
Raw logs stay on disk; only conclusions are recorded here.

## E1 — S-Boot boot-record: Nuxel BOOT image was loaded 7 times, then recovery
`last_kmsg.txt` contains, in sequence, eight S-Boot boot records. Each record
prints the UFS byte offset of the boot image it loaded:

| Record | `load_kernel: loading boot image from` | kernel size | ramdisk size | maps to |
|---|---|---|---|---|
| 1..7 | `218112` | `0xf4a000` | `0x5be800` | **sda14 = BOOT (Nuxel)** |
| 8 (last) | `330752` | `0x2ac3800` | `0xa66800` | **sda15 = RECOVERY (TWRP)** |

Verified against sysfs: `sda14 start=218112` (PARTNAME=boot, 112640 sectors),
`sda15 start=330752` (PARTNAME=recovery, 132096 sectors). Offsets are absolute
LBA starts, so the mapping is exact.

**Conclusion:** the A1 reboot was real. S-Boot loaded the Nuxel BOOT image and
jumped to it **seven consecutive times**, and the eighth recorded boot is the
recovery session that is running now. This is a genuine bootloop, not a missing
reboot.

## E2 — zero kernel console output on every Nuxel boot
Between consecutive Nuxel S-Boot records there is **no kernel text at all** — the
next thing in the buffer is the following S-Boot banner. For the TWRP record the
same buffer holds a long kernel log (Android `init:` lines, `exynos-ufs` probe,
`mmc_host`, timestamps to 2581 s). The buffer therefore does capture kernel
output when a kernel produces it.

`grep -a nuxel last_kmsg.txt` -> 0 matches: the instrumented `/init` never wrote
its `nuxel-init:` lines to the console either.

**Conclusion:** on all 7 Nuxel boots the kernel produced no console bytes before
reset — no `Linux version`, no panic text (panics are level<4 and would pass
`loglevel=4`), and no initramfs `/init` output.

## E3 — no persistent diagnostic artifact from A1
* USERDATA mounts read-only and cleanly (ext4, Fedora 43 layout present), but
  there is **no `/nuxel-boot-diag.log`**.
* The BOOT-partition diagnostic slot (last 128 sectors, offset 57,606,144)
  contains no `nuxel-init` record.
* `/sys/fs/pstore` empty; `/proc/last_kmsg` 2 MiB (see E1).

**Conclusion:** A1's initramfs never reached a state in which it could write a
record — consistent with E2 (it may never have run at all).

## E4 — the flashed BOOT container differs from the only known-booting container
| field (byte offset) | Nuxel image | TWRP `recovery.img` (boots) |
|---|---|---|
| `0` magic | `ANDROID!` | `ANDROID!` |
| `8` kernel_size | 16,030,259 (`0xf49a33`) | 44,838,924 |
| `12/20/32/36` addrs/page | 0x10008000 / 0x11000000 / 0x10000100 / 2048 | identical |
| **`40`** | **376,101** (= merged-DTB size) | **1** (`header_version`) |
| **`44`** | **0** | **0x18000171** (`os_version` 12.0.0) |
| kernel payload | **gzip** (`1f 8b 08 …`) | **raw arm64 `Image`** (`ARMd` @0x38) |
| ramdisk | 6,022,352 gzip newc | 10,905,577 |
| DTB after ramdisk | 376,101 B, `d00dfeed` | 1,805,256 B (v1 dtbo slot) |

S-Boot parsed offset 44 as `os_version` (`patch_month_year : 0.0 , os_version :
0.0.0` -> `[CM] set os_version & patch_month_year: fail`) whereas for TWRP it
logged `1.23 / 12.0.0 -> success`. So S-Boot read the header as v1 and *accepted*
it far enough to print `Starting kernel...`.

## E5 — facts about provenance
* Nuxel kernel = `Linux version 4.14.253 (nuxel@nuxel-phosh) gcc 15.3.1 … #1 SMP
  PREEMPT Sun Oct 11 12:35:53 UTC 2026`, built from
  `Linux4/android_kernel_samsung_exynos9820@f7194c1d`, defconfig
  `exynos9820-beyond2lte_defconfig`. Raw `Image` = 44,980,232 B (`ARMd` header,
  `text_offset=0x80000`, `image_size=0x32bc000`).
* TWRP kernel = `Linux version 4.14.113-g55f042627 (runner@fv-az572-167)`,
  clang-built. Raw, uncompressed, 44,838,924 B. **Different build, same SoC
  family, and it executes on this handset.**
* `backups/s10plus/boot-original.img` is **not** a real backup — it begins with
  `DUMMY\0\0\0` and contains no `ANDROID!` magic. The true stock BOOT contents
  were never captured. RECOVERY backup (`twrp-recovery-original.img`) is real and
  valid.
* S-Boot cannot persist its own log on this unit: it repeatedly reports
  `UFS Write 10 Command Error` / `CHECK CONDITION` at `LBA(79872) LUN(0)`.

## Not evidence of anything
* ADB disappearance during a boot attempt (the Fedora image ships no adbd).
* Flash readback SHA equality (storage only).
