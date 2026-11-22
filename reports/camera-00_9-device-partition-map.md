# Camera Prompt 00_9 — LIVE device partition map (2026-11-22, read-only)

**Target:** Nuxel SM-G975F / beyond2lte, kernel 4.14.253-gf7194c1d15ed-dirty.
**Session:** read-only SSH as root@10.11.12.99 (trusted host key in known_hosts).
**Writes:** ZERO device partition writes. **Reboots:** ZERO.

## Verified device identity (fresh, live)

| Field | Value | Source |
|---|---|---|
| Reachable | YES | SSH (ping 67ms; ssh handshake OK) |
| Healthy/normally booted | YES | `up 89550s` ≈ 24.9h |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #1 SMP PREEMPT Sat Nov 21 12:30:11 CET 2026 aarch64` | `/proc/version`, `uname -a` |
| Model | `Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820` | `/sys/firmware/devicetree/base/model` |
| Product | `SM-G975F` | `androidboot.em.model=SM-G975F` cmdline |
| Board revision | `26` | `androidboot.revision=26` + DTBO entry 9 range check |
| DTBO selection index | `9` | `androidboot.dtbo_idx=9` + DTBO table entry 9 `covers board rev 26` |
| Bootloader | `G975FXXSEFUL1` | `androidboot.bootloader=...` |
| Live merged FDT SHA-256 | `761df64ac4417f6dd5bbb468eeb6dc2305cbf45f8541d3639d5a50ca2ffc7cad` | `sha256sum /sys/firmware/fdt` (372657 bytes) |
| Camera STREAMON / Panic#2 | NONE observed | dmesg grep empty |
| pstore | `dmesg-ramoops-0.enc.z` (Samsung-encrypted, 5152 bytes) | `/sys/fs/pstore/` |

## Partition mapping (independently verified)

Discovery method: read-only `blkid` (GPT PARTLABEL + PARTUUID) on the live
device, cross-checked against `fdisk -l /dev/sda` (GPT, sector math) and the
historical `docs/s10plus-autonomous-boot-repair/EVIDENCE.md` map
(`boot=sda14, recovery=sda15, userdata=sda31, dtb=sda12, dtbo=sda13`).
The two sources agree exactly. There is **no** `/dev/block/by-name` on native
Fedora; no sdaN number was guessed.

| Semantic role | Block device | GPT PARTLABEL | PARTUUID (last segment) | Capacity bytes | Corroboration |
|---|---|---|---|---|---|
| BOOT | `/dev/sda14` | `boot` | `626f-6f74` | 57,671,680 | blkid + fdisk + historical map |
| DTB (base) | `/dev/sda12` | `dtb` | `6474-62` | 8,388,608 | blkid + fdisk + historical map |
| DTBO (overlay) | `/dev/sda13` | `dtbo` | `6474-626f` | 8,388,608 | blkid + fdisk + historical map |
| RECOVERY | `/dev/sda15` | `recovery` | `7265-636f` | 67,633,152 | blkid + fdisk + historical map |
| system (Android) | `/dev/sda25` | `system` | `7379-7374` | 5,976,883,200 | blkid (ext4) |
| userdata (Fedora root) | `/dev/sda31` | `userdata` | `7573-6572` | 119,126,622,208 | blkid (ext4, LABEL nuxel-beyond2lte) |

Rejected/ambiguous mappings: rootfs (`/` = sda31 userdata), EFS/EFS-dervs,
modem, persist, param, up_param, etc. — all correctly excluded from camera
write scope. `root=/dev/sda25` in cmdline is the Android system partition; the
native Fedora `/` is actually mounted on sda31 (`findmnt` → `/dev/sda31`).

## Raw readback integrity (bit-exact, two independent checks)

Captured with read-only SSH `dd if=<dev>` / `cat /sys/firmware/fdt`, verified
device-side source SHA before AND after, host-side SHA at capture, plus a
second independent host `sha256sum` re-check. All equal.

| Image | Host file | Size | SHA-256 (host=source) |
|---|---|---|---|
| boot | current-boot.img | 57,671,680 | `0e6aa34c...` |
| dtb | current-dtb.img | 8,388,608 | `abc9d45d...` |
| dtbo | current-dtbo.img | 8,388,608 | `de3bc025...` |
| recovery | current-recovery.img | 67,633,152 | `4cc71d62...` |
| merged fdt | active-merged.fdt | 372,657 | `761df64a...` |

(Full 64-hex SHAs recorded in the private `raw-capture.NOT_SIGNED.json` and
host re-check; they are intentionally NOT duplicated verbatim here to avoid
leaking private device identifiers into Git. Authoritative values live in the
owner's private directory only.)

## BOOT image container (physically verified)

Using `tools/s10plus/verify-boot-image.py`:

- Magic `ANDROID!`, page size 2048, header field@40 = version 1
- Raw arm64 `Image` (NOT gzip), kernel_size 45,848,584, text_offset 0x80000
- ramdisk lzma, cpio 84 records, `/init` → /bin/sh (toybox)
- **`second_size = 0` → no appended DTB** → `dt_layout = separate-dtb-dtbo`,
  `appended_dtb_index = null` (physically proven, not just reported)
- `partition_slack = 0` (boot image fills the 57,671,680-byte partition)
- Result: **PASS**, `dt_source = verified-separate-dtb-dtbo-and-live-fdt`

## Camera DT provenance (real captured images, all PASS)

- DTB base (`current-dtb.img`): samsung-dth(1 entry), 1117 nodes, FIMC=7 CSIS=0 — PASS
- DTBO overlay (`current-dtbo.img`): samsung-dth(10 entries), entry 9 selected,
  "entry 9 covers board rev 26", FIMC=9 CSIS=0 — PASS
- Merged FDT (`active-merged.fdt`): 1860 nodes, 944 phandles, 26 endpoint links,
  23 I2C assignments, 64 GPIOs, FIMC=16 CSIS=0; stock flash/torch GPIO overlaps
  (gpg2 pin4, gpg3 pin6) grandfathered byte-identical — PASS

`bootloader_dt_source_verified` = TRUE for the layout question (no appended DTB +
separate DTB/DTBO physically present + active merged FDT consistent), but the
active-source proof still requires the signed live manifest for the release gate.

## Declaration

- PARTITION_IDENTITY_INDEPENDENTLY_VERIFIED = YES (blkid + historical map + fdisk agree)
- PARTITION_BACKUPS_MATCH = YES (host SHA == device source SHA, before+after)
- DEVICE_PARTITION_WRITES = 0
- DEVICE_REBOOTS = 0
