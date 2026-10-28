# Nuxel S10+ live fixes — 2026-10-28

Device: SM-G975F (beyond2lte), Exynos 9820, TWRP → Nuxel Fedora rootfs.
Kernel: 4.14.253-gf7194c1d15ed-dirty, Nuxel build.
Release: shipped in `v0.7.2-beta` (PWNAGE-36000).

## 1. Bootloop — fixed

### Evidence
`/tmp/nuxel-logs/last_kmsg` (boot at 13:34:33) showed the kernel stopped at
~62.5 s while the lock screen was up:

```
Unable to handle kernel paging request at virtual address ffffff8023ab006c
Internal error: Oops: 96000021
PC is at abox_is_calliope_incompatible.isra.0+0x44/0x8c
LR is at abox_system_ipc_handler+0x64/0x580
Kernel panic - not syncing: Fatal exception in interrupt
```

The fault is the `memcpy(&msg, data->sram_base + 0x30040, 0x3C)` inside
`abox_is_calliope_incompatible()`, called from the ABOX boot-done hard IRQ.
It is only used to print a compatibility warning.

### Fix
`kernel/s10plus/.build/src/sound/soc/samsung/abox/abox.c`:
use the boot-done IPC's `system_msg->param3` (already copied to normal memory)
instead of re-reading ABOX SRAM+0x30040 from IRQ context.

Patch saved at:
`kernel/s10plus/patches/0004-nuxel-abox-boot-done-and-bt-hciuart.patch`

### Hardware result
Flashed `build/out/s10plus/nuxel-boot-aboxbt.img`
(sha256 `0e0ad06de1b02f5b80879647c2761b419d697cbb2c4b19609bdaabfffbffda13`).
After reboot the Nuxel console appeared at 30 s and stayed up for >130 s,
then remained up for >11 minutes while BT/audio tests ran. No ABOX panic.

## 2. Bluetooth — fixed

The rebuilt kernel had lost `CONFIG_BT_HCIUART` because
`build-kernel.sh` re-runs the in-tree defconfig. Added to
`arch/arm64/configs/exynos9820-beyond2lte_defconfig`:

```
CONFIG_BT_HCIUART=y
CONFIG_BT_HCIUART_H4=y
```

(`CONFIG_BT_HCIUART_3WIRE` is ignored unless `SERIAL_DEV_BUS` is enabled; H4 is
what `btattach -P h4` needs.)

Runtime result after the final reboot:

```
nuxel-bluetooth.service  active (running)
  └─ btattach -B /dev/ttySAC1 -P h4 -S 115200
/sys/class/bluetooth/hci0 -> .../ttySAC1/hci0
Controller 43:75:B1:00:1F:AC (public)
  Powered: yes
```

A 12 s `bluetoothctl scan on` completed and discovered a peer
(`67:BC:9D:9D:37:7F`).

## 3. Audio — playback working via RDMA1

The card/controls are present, but RDMA0 starts and then the ABox DSP never
advances `hw_ptr` (aplay gets EIO after one buffer). RDMA1 works:

```
aplay -D hw:0,1 -f S16_LE -c 2 -r 48000 -d 3 /dev/zero
  state: RUNNING
  hw_ptr: 36000   appl_ptr: 60000
  rc=0
```

The ABOX crossbar defaults to “no route”, so the route is applied by
`/usr/lib/nuxel/nuxel-audio-route.sh` (enabled as
`nuxel-audio-route.service`):

```
Left/Right AMP Enable Switch = on
ABOX RDMA0_EN = 0
ABOX SPUS IN1 = RDMA
ABOX SPUS OUT1 = SIFS1
ABOX SIFS1 = SPUS OUT1
ABOX UAIF1 SPK = SIFS1
ABOX SIFS1 OUT Switch = on
ABOX UAIF1 Switch = on
ABOX RDMA1_EN = on
```

`/etc/asound.conf` sends `default` playback to card 0 / device 1 (RDMA1), so
`aplay -D default ...` returns 0 with `hw_ptr` advancing.

Vendor ABox extra firmware was downloaded on-device from
`Linux4/proprietary_vendor_samsung@05c9ef8f...` into `/lib/firmware`
(`AP_AUDIO_SLSI.bin`, `APBargeIn_*`, `APDV/APSV/APTV`, `SoundBoosterParam`,
`bidirmic`, `dnn`, `fmsb`, `rxse`, `txse1/2/3`, `usbin`, `usbout`,
`a2dpcom`). They load after a reboot; `txse3.bin` and `AP_AUDIO_SLSI.bin`
checksums match `firmware/s10plus/manifest.yml`.

## 4. GPS — hardware path present, userspace blocked

* `/dev/ttyBCM` exists; `brcm gps spi` is bound to `spi17.0`.
* The GPS rail is GPIO 145:
  `/sys/devices/virtual/sec/gps/GPS_PWR_EN` → `.../gpio145`.
  Writing 1 makes the chip respond on SPI (registers change from
  `0xFFFFFFFF` to real values such as `0x40104094`).
* `/dev/ttyBCM` does **not** emit NMEA by itself. The BCM4773 uses Broadcom's
  BBD/LHD RPC protocol; the vendor `gpsd`
  (`beyond2lte/proprietary/vendor/bin/hw/gpsd`) is an Android/bionic binary
  that needs `/system/bin/linker64` plus Android HIDL/sensor services.
  The device's `system` partition is currently a Linux rootfs, so those
  Android system libraries are absent. The open-source `gpsd` cannot decode
  the BCM4773 raw measurement RPC.

Current diagnostic verdict: `BLOCKED_FIRMWARE` (also `no-consumer`).
Real blocker: missing vendor `gpsd`/lhd userspace, not the SPI driver.

Manual power-on (not persisted, to avoid draining the rail without a
consumer):

```
echo 1 > /sys/devices/virtual/sec/gps/GPS_PWR_EN/value
```

## Final state (2026-10-28 15:11 CET)

```
up 11 min
nuxel-bluetooth.service   active
nuxel-audio-route.service active
aplay -D default ...      rc=0
bluetoothctl show         Powered: yes
GPS                       hardware responds, no NMEA consumer
```
