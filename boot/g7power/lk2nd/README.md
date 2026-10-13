# lk2nd — Mainline Qualcomm Bootloader for Moto G7 Power (msm8953)

## Source
https://github.com/msm8916-mainline/lk2nd (branch: master)
Target: msm8953 (used by ocean/SDM632)

## Build
git clone https://github.com/msm8916-mainline/lk2nd
cd lk2nd
make TOOLCHAIN_PREFIX=arm-none-eabi- msm8953 -j$(nproc)
# Output: build-msm8953/lk2nd.img

## Flash (Phase 1: Stock ABOOT fastboot mode)
# 1. Flash dtbo FIRST (MANDATORY — see dtbo-first rule)
fastboot flash dtbo /path/to/stock-dtbo.img    # use backed-up stock dtbo
# 2. Flash lk2nd to the boot partition
fastboot flash boot build-msm8953/lk2nd.img
# 3. Reboot into lk2nd fastboot
fastboot reboot bootloader
# (Now you are in lk2nd's fastboot, not stock ABOOT)
# 4. Flash mainline kernel boot.img
fastboot flash boot /tmp/nuxel-ocean-boot.img
# 5. Flash rootfs
fastboot flash userdata /path/to/nuxel-ocean-rootfs.img
# 6. Reboot
fastboot reboot

## Recovery / Revert
# If the device does not boot after flashing lk2nd:
# Enter stock ABOOT fastboot (Vol Down + Power from off)
fastboot flash dtbo  /path/to/stock-dtbo-backup.img
fastboot flash boot  /path/to/stock-boot-backup.img
fastboot reboot

## EDL (Qualcomm 9008) Unbrick Path
# If fastboot is inaccessible (hard brick):
# Power off, hold Vol Down + Vol Up, plug USB
# Host should detect: Qualcomm HS-USB QDLoader 9008 (VID:05C6, PID:9008)
# Use edl tool (bkerler/edl) or QFIL (Windows) to flash stock partitions
