# Nuxel S10+ GNSS — Reflash Manifest

> **No flash was performed, and none is authorized by this document.**
> This records what would change on a partition image *if and only if* an
> explicitly approved, separately-batched reflash is requested after the
> blocker in `GPS-BLOCKERS.md` is resolved.

## 1. Decision: kernel/boot reflash is NOT required

- `CONFIG_BCM_GPS_SPI_DRIVER=y`, `CONFIG_SENSORS_SSP_BBD=y`,
  `CONFIG_SENSORS_SSP_BEYOND=y` are **built into the running kernel**.
- The BCM4773 patch firmware is **already embedded** in the kernel and served
  read-only via `/dev/bbd_patch` (SHA-256 verified, §firmware provenance).
- BBD nodes `/dev/ttyBCM`, `/dev/bbd_control`, `/dev/bbd_patch`,
  `/dev/bbd_sensor`, `/dev/bbd_urgent_patch` exist and the SPI driver is bound.

**Therefore the system image and boot/kernel do NOT need changing for the GNSS
transport, firmware, or device nodes.** No speculative kernel/DT entries are
listed because none are needed.

## 2. Only-if entry (optional): isolated vendor runtime (path B)

These entries apply **only** if the owner pursues the isolated Android-compat
runtime (handoff option B) using their **own** stock `SM-G975F` binaries. They
are conditional, provenance-gated, and must not be flashed without B1
resolution + explicit approval. Hashes are placeholders to be filled from the
owner's own extraction (they must never be substituted from another device).

| Destination | Owner:Group | Mode | SELinux | Source (owner's own stock) | SHA-256 (to fill) |
|---|---|---|---|---|---|
| `/opt/nuxel/gnss-android/lhd` | root:root | 0750 | `u:object_r:vendor_file:s0` | `vendor/bin/hw/lhd` | `TBD-from-owner` |
| `/opt/nuxel/gnss-android/gpsd` | root:root | 0750 | `u:object_r:vendor_file:s0` | `vendor/bin/hw/gpsd` | `TBD` |
| `/opt/nuxel/gnss-android/lib/libwrappergps.so` | root:root | 0644 | `u:object_r:vendor_file:s0` | `vendor/lib64/libwrappergps.so` | `TBD` |
| `/opt/nuxel/gnss-android/etc/lhd.conf` | root:root | 0644 | `u:object_r:vendor_file:s0` | `vendor/etc/sensor/lhd.conf` | `TBD` |
| `/opt/nuxel/gnss-android/etc/gps.xml` | root:root | 0644 | `u:object_r:vendor_file:s0` | `vendor/etc/gnss/gps.xml` | `TBD` |
| `/opt/nuxel/gnss-android/linker64` | root:root | 0755 | `u:object_r:system_file:s0` | `system/bin/linker64` | `TBD` |
| Bionic/HIDL/Binder dependency set | root:root | 0644 | vendor/system labels | owner's `system`/`vendor` libs | `TBD` |

> These are **not** copied into `/usr/bin`; they live in an isolated chroot and
> are not the default Nuxel location design. This table documents what a
> reflash would carry; it does not certify ABI portability.

## 3. Native Nuxel daemon (no reflash — normal userspace deploy)

These ship over the existing SSH/deploy path (no partition write, no dm-verity
impact):

| Source file | Destination | Mode |
|---|---|---|
| `services/nuxel-gnss/src/nuxel_bbd_tl.py` | `/usr/lib/nuxel/nuxel-gnss/nuxel_bbd_tl.py` | 0644 |
| `services/nuxel-gnss/src/nuxel_control.py` | `/usr/lib/nuxel/nuxel-gnss/nuxel_control.py` | 0644 |
| `services/nuxel-gnss/src/nuxel_lhd.py` | `/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py` | 0755 |
| `services/nuxel-gnss/systemd/nuxel-gnss-lhd.service` | `/etc/systemd/system/nuxel-gnss-lhd.service` | 0644 |

## 4. Rollback

- Native daemon: `mv` the deployed files back from their `.bak` copies and
  `systemctl stop nuxel-gnss-lhd`; no boot/kernel/firmware was written.
- Conditional vendor runtime: boot the previous A/B slot; the runtime was never
  the boot-critical path.
- Serial/ACM recovery console and charger-mode recovery remain available.

## 5. Explicit statement

**NO FLASH WAS PERFORMED.** Kernel/DT reflash: **not required**. Firmware
flash: **not required** (already in-kernel). Only the optional, owner-approved,
proprietary vendor runtime (path B) would touch a partition, and it is
provenance-gated and not authorized here.
