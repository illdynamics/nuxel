# Nuxel g7power — Stage 1 + Stage 2, second pass (2026-10-14, afternoon)

Device: Moto G7 Power `ocean` (XT1955, SDM632). Host: dextronux, G7 Power on USB.

## TL;DR
1. The unit arrived **hard-bricked at the bootloader level**, not merely looping:
   stock ABOOT reported `securestate: oem_locked`, `cid: 0xDEAD`, a bogus
   serial `126bc9fa`, and **no partition table at all** (`partition-size:*` empty,
   `oem partition` empty). Every `fastboot flash` failed with
   `Invalid partition name`, and even `flash partition gpt.bin` failed with
   `Preflash validation failed`. Nothing can be written in that state.
2. Recovered the unit with a **blankflash (EDL)**: `fastboot oem blankflash` put
   it in `05c6:9008`, then the ocean blankflash restored GPT + the full bootloader
   chain. The phone came back as the real unit: `serialno ZY326RGXCM`,
   `securestate flashing_unlocked`, `cid: 0x0032`, full partition table.
3. The **bootloop root cause was lk2nd, not the kernel.** `build/out/g7power/lk2nd.img`
   is a modern lk2nd that boots only via **ext2 + extlinux**; the guide's
   "payload at 512 KiB" combined image is never consumed, so ABOOT -> lk2nd ->
   "reverting to android boot" -> ABOOT -> ... loops.
4. Fixed by **removing lk2nd from the path entirely**: flash the Nuxel kernel as a
   normal Moto/QCDT Android boot image straight into `boot`. ABOOT boots the
   kernel directly; no lk2nd, no extlinux.
5. After that flash the device **left fastboot and did not return for ~9 minutes**
   (no `22b8:2e80`, no EDL, no reboot loop). Screen no longer flashes.

## What is flashed now (direct-boot chain)
```
dtbo_a    <- build/out/g7power/stock/firmware/extracted/dtbo.img
boot_a    <- build/out/g7power/nuxel-ocean-boot-simpledrm-qcdt.img
boot_b    <- build/out/g7power/nuxel-ocean-boot-simpledrm-qcdt.img
system_b  <- build/out/g7power/nuxel-ocean-rootfs-final.img      (rootfs, label nuxel-ocean)
```
`nuxel-ocean-boot-simpledrm-qcdt.img` = Android boot image v1 (page 2048) with:
* kernel  `Image.gz` (sha256 b9d177ae…, `CONFIG_DRM_SIMPLEDRM=y`,
  `CONFIG_FRAMEBUFFER_CONSOLE=y`, `CONFIG_TOUCHSCREEN_ILI210X=y`,
  `CONFIG_LEDS_LM3697=y`, `CONFIG_DRM=y`),
* initramfs = the fixed (`bin/sh` + toybox applets) `nuxel-initramfs-initfix.cpio.gz`,
* DT = QCDT v3 table (136 entries) wrapping `sdm632-motorola-ocean.dtb`,
* cmdline `console=ttyMSM0,115200 console=tty0 nuxel.device=g7power rootfstype=ext4 rootwait rw lk2nd.pass-ramoops ignore_loglevel`.

## Display (Stage 2)
`arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dts` itself declares
`/chosen/framebuffer@90001000` (`simple-framebuffer`, 720x1520, stride 2160,
`r8g8b8`) plus a `no-map` reservation `cont-splash@90001000` of exactly that
size. So with `CONFIG_DRM_SIMPLEDRM=y` + `CONFIG_FRAMEBUFFER_CONSOLE=y` +
`console=tty0` the kernel scans out the bootloader's continuous-splash
framebuffer and fbcon prints the boot log on the 720x1520 panel — with or
without lk2nd.

## Not yet possible to confirm from the host
* **Screen contents** — no camera; only the operator can see the panel.
* **USB serial console** (`1d6b:0104` -> `/dev/ttyACM0`) still does not enumerate.
  The kernel has `CONFIG_PHY_QCOM_QUSB2=m`; the initramfs `modprobe`s it (the .ko
  has no deps, so it should load), yet no UDC appears, so `dwc3` never gets a
  gadget. A kernel with `CONFIG_PHY_QCOM_QUSB2=y` (built-in) is the reliable fix,
  but it needs a flash -> the device must be in fastboot.

## Recovery procedure (proven today)
```
# if aboot is wedged/blank (no partitions, Invalid partition name):
/tmp/fb oem blankflash                       # -> 05c6:9008
docker run --rm --privileged -v /dev/bus/usb:/dev/bus/usb \
  -v /x/nuxel/finish2/bl:/bf -w /bf centos:7 ./qboot blank-flash
# -> back in fastboot, serial ZY326RGXCM, flashing_unlocked, GPT restored
```
Blankflash used: `blankflash_from_QCO30.85-18.zip` (ocean_vzw bootloader).
