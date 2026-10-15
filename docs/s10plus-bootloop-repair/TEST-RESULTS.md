# Test results (offline)

Device: SM-G975F R58M75KDB2X in TWRP 3.7.0_9-2, root ADB. No writes performed.

## 1. Device evidence collection

| Command | Result |
|---|---|
| `bash scripts/12-full-diagnostics.sh` (pack, read-only) | exit 0, 7/7 collectors OK, capture `20261015T063659Z-full-collection-5886/` |
| targeted reads (`dd` from `sda12/13/14/15`, `/proc/device-tree`, sysfs uevents) | exit 0, capture `20261015T063922Z-mission-cybertiel/` |
| recovery-backup integrity vs on-device partition | **identical**: `4cc71d6277e020cdec729b85934cfb6111e9abee8db2fbcc344aad3173335d87` |

## 2. Hypothesis tests

| Test | Command | Result |
|---|---|---|
| H1 S-Boot drops the image cmdline | `cat /proc/device-tree/chosen/bootargs` vs `/proc/cmdline` vs recovery header | **SUPPORTED** — no `buildvariant` anywhere; header says `buildvariant=eng` |
| H3 DTBO double-apply | `fdtoverlay -i merged.dtb -o out.dtb dtbo9.dtb; cmp merged.dtb out.dtb` | **REJECTED** — byte-identical (idempotent) |
| H4 load addresses | header of flashed image vs TWRP recovery header | **REJECTED** — identical (`0x10008000/0x11000000/0x10000100`) |
| H6 rootfs integrity | `e2fsck -fn <rootfs.img>` | exit 0, clean; 21571/262144 files |
| H8 display stack | `ls /dev/dri /sys/class/drm /dev/graphics` on device | **SUPPORTED** — fbdev only, no DRM/KMS |

## 3. Regression test (new)

```
$ sh boot/s10plus/tests/test-init-cmdline-independence.sh
  PASS  T1 real S-Boot cmdline + beyond2lte DTB => s10plus
  PASS  T2 detection from compatible only
  PASS  T3 foreign DTB not claimed as s10plus
  PASS  T4 PARTNAME=userdata resolved by identity = /dev/disk0
  PASS  T5 s10plus root resolver uses PARTNAME = /dev/disk0
  PASS  T6 BOOT-slack diagnostic offset = /dev/disk0s1 57606144
  PASS  T7 init.sh has device auto-detection + persistent diagnostics
  PASS  T8 USERDATA-not-found path persists then reboots (no silent hang)
  ---- 8 passed, 0 failed, 0 skipped ----
```

## 4. Candidate image verification

`build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img`
(22,433,792 bytes, sha256 `eb77d658fb4fa95930fd13166970a00d6c9ab49dd439c6517b1da349a36e14e5`)

| Check | Result |
|---|---|
| Android boot magic / page size | `ANDROID!`, 2048 ✓ |
| Header v0/v1 (`hdrver=0`) + `dt_size` | ✓ |
| kernel `Image.gz`, 16,030,259 B → 44,980,232 B | identical to flashed image (`33cac63a…`) ✓ |
| merged DTB 376,101 B (`0xd00dfeed`) | identical to flashed image (`6107d2e4…`) ✓ |
| load addresses | `0x10008000 / 0x11000000 / 0x10000100` ✓ |
| initramfs | gzip newc, 65 entries, 0 pack warnings ✓ |
| `/init` | mode 0755, `#!/bin/sh`, byte-identical to patched `boot/initramfs/init.sh` ✓ |
| `/bin/sh` | symlink → `toybox` ✓ |
| required applets (mount, mountpoint, switch_root, grep, tr, dd, cp, dmesg, …) | all present ✓ |
| fit in BOOT partition | 22.4 MB ≤ 57.7 MB ✓ |
| pack inspector `09-inspect-boot-image.sh` | parsed, 1 FDT, 65 entries, **warnings 0** ✓ |
| flash pack `05-preflight.sh --profile s10plus` | **PREFLIGHT PASS** (read-only) ✓ |
| determinism | rebuild produced the identical SHA-256 ✓ |
| Fedora rootfs | unchanged; `e2fsck` clean; `/sbin/init → ../lib/systemd/systemd`; systemd/phosh/phoc/python3 present ✓ |

**No milestone requiring the physical Samsung is claimed.** The candidate is
"offline-verified", not "boot-verified".

## 5. Reproduce

```bash
cd ~/x/nuxel
sh boot/s10plus/tests/test-init-cmdline-independence.sh
bash boot/s10plus/build-debug-candidate.sh
shasum -a 256 build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img
```
