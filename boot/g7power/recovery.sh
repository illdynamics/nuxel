#!/usr/bin/env bash
# =============================================================================
# Nuxel Recovery Helper — Motorola Moto G7 Power (ocean, SDM632 / msm8953)
#
# The G7 Power recovery model has TWO distinct fastboot modes:
#   * Stock ABOOT fastboot — Motorola's bootloader. Entered from power-off
#     with Vol Down + Power (hold until the fastboot menu appears), or from
#     Android with `adb reboot bootloader`. It accepts ONLY stock images:
#     flashing mainline DTBs/boot images here is not supported by ABOOT.
#     Use it to flash dtbo, lk2nd (to boot), stock backups, and to run
#     `fastboot oem unlock <code>`.
#   * lk2nd fastboot — the msm8916-mainline/lk2nd bootloader (msm8953
#     target) after it is installed on the boot partition. Entered by
#     `fastboot reboot bootloader` from stock ABOOT (lk2nd auto-chainloads)
#     or by simply booting the device. It understands mainline DTBs and the
#     Nuxel v1 boot image; use it to flash boot.img and the rootfs.
#
# To tell them apart: stock ABOOT answers `fastboot getvar product` with
# "ocean" and reports `unlocked: yes`; lk2nd reports the same product but
# is the ONLY mode that will accept a mainline Nuxel boot.img.
#
# Full stock restore (removes lk2nd + Nuxel):
#   fastboot flash dtbo  /path/to/stock-dtbo-backup.img
#   fastboot flash boot  /path/to/stock-boot-backup.img
#   fastboot reboot
#   (stock dtbo MUST be flashed before/with stock boot — never flash boot
#    alone on msm8953 while lk2nd is present)
#
# EDL (Qualcomm 9008) unbrick path — when fastboot is inaccessible:
#   Power off, hold Vol Down + Vol Up, plug USB.
#   Verify the host sees the download port:
#     lsusb | grep "05C6:9008"
#   Install the bkerler/edl tool:
#     pip install edl
#   Flash the stock boot partition:
#     edl --port /dev/ttyUSB0 flash boot stock-boot.img
#   (or use QFIL on Windows with the full stock firmware XML to restore
#    every partition). See boot/g7power/lk2nd/README.md.
#
# This helper ONLY prints guidance — it NEVER flashes anything itself and
# NEVER touches the protected partitions
# (modemst1 modemst2 fsg fsc ddr persist misc).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BOOT_CONFIG="${NUXEL_ROOT}/boot/g7power/boot-config.txt"
LK2ND_README="${NUXEL_ROOT}/boot/g7power/lk2nd/README.md"

PROTECTED_PARTITIONS="modemst1 modemst2 fsg fsc ddr persist misc"

log()  { echo "[recovery-g7power] $*"; }

usage() {
    cat <<EOF
Usage: boot/g7power/recovery.sh [--help]

G7 Power recovery reference (Motorola Moto G7 Power, ocean, SDM632).
Machine-readable boot facts: ${BOOT_CONFIG}
lk2nd build/flash/EDL details: ${LK2ND_README}

THE TWO FASTBOOT MODES
  1. Stock ABOOT fastboot (Motorola bootloader)
       Enter: power off, then hold Vol Down + Power
              (or from Android: adb reboot bootloader)
       Use for: fastboot oem unlock, flash dtbo, flash lk2nd to boot,
                flash stock backups (dtbo + boot), fastboot reboot bootloader
       NOTE: stock ABOOT CANNOT flash or boot mainline DTBs / Nuxel images.
  2. lk2nd fastboot (msm8916-mainline/lk2nd, msm8953 target)
       Enter: after lk2nd is installed, 'fastboot reboot bootloader' from
              stock ABOOT; lk2nd auto-chainloads on every boot.
       Use for: flash Nuxel boot.img (v1, page 2048), flash rootfs to
                userdata, fastboot reboot
       Identify: it is the ONLY mode that accepts a mainline Nuxel boot.img.

FULL STOCK RESTORE (removes lk2nd + Nuxel kernel + rootfs):
  # Enter stock ABOOT fastboot (Vol Down + Power from off), then:
  fastboot flash dtbo  /path/to/stock-dtbo-backup.img
  fastboot flash boot  /path/to/stock-boot-backup.img
  fastboot reboot
  # dtbo FIRST is mandatory on msm8953 (prevents soft-brick).

EDL (QUALCOMM 9008) UNBRICK PATH:
  # Power off, hold Vol Down + Vol Up, plug USB.
  # Verify the download port is visible:
  lsusb | grep "05C6:9008"
  # Install the edl tool (bkerler/edl) and restore stock:
  pip install edl
  edl --port /dev/ttyUSB0 flash boot stock-boot.img
  # Or use QFIL (Windows) with the stock firmware XML for a full restore.

PROTECTED PARTITIONS — NEVER flash (per-unit IMEI/MAC/radio calibration):
  ${PROTECTED_PARTITIONS}
  These carry irreplaceable per-unit data; any loop over the eMMC by-name
  partition list must skip them (see docs/g7power-bringup.md).

This helper prints guidance only — it never flashes anything.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --help|-h) usage; exit 0 ;;
        *) log "Unknown option: $arg"; usage; exit 1 ;;
    esac
done

usage
