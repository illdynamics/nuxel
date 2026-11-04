# Exynos 9820 MFC decode investigation — PWNAGE-60000

## Live hardware / driver identity

- DT node: `/sys/firmware/devicetree/base/mfc@188D0000`
- compatible: `samsung,exynos-mfc`
- platform driver: `s5p-mfc`
- V4L2 nodes (read from sysfs only):
  - `/dev/video6`  `s5p-mfc-dec0`
  - `/dev/video7`  `s5p-mfc-enc0`
  - `/dev/video8`  `s5p-mfc-dec-secure0`
  - `/dev/video9`  `s5p-mfc-enc-secure0`
  - `/dev/video10` `s5p-mfc-enc-otf0`
  - `/dev/video11` `s5p-mfc-enc-otf-secure0`
- kernel config: `CONFIG_VIDEO_EXYNOS_MFC=y`, `CONFIG_FW_LOADER=y`,
  `CONFIG_FW_LOADER_USER_HELPER=y`, `CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y`,
  `CONFIG_EXTRA_FIRMWARE=""`.
- Driver source: `kernel/s10plus/.build/src/drivers/media/platform/exynos/mfc/`
  (downstream Exynos MFC, `MFC_DRIVER_INFO 180315`).
- Firmware name: `MFC_FW_NAME "mfc_fw.bin"` (`mfc_common.h:68`), requested by
  `mfc_load_firmware()` in `mfc_buf.c:568-615` on the first instance open.

## Precise blocker

`mfc_fw.bin` is **absent** from every firmware path the live system searches:

```
/lib/firmware/mfc_fw.bin       missing
/usr/lib/firmware/mfc_fw.bin   missing
/vendor/firmware/mfc_fw.bin    missing
```

`CONFIG_FW_LOADER_USER_HELPER_FALLBACK=y` means a missing file can fall back to
a userspace helper and wait.  That is the exact historical hazard recorded by
`nuxel-gstreamer-guard.sh`: a plugin scanner or WebKit media process entering
`request_firmware()`/`mfc_open` can sit in uninterruptible sleep.  This mission
therefore did **not** open any `/dev/video*` node.

The `firmware/mfc/mfc_fw_flash*.bin.ihex` files in the kernel tree are wireless
charger firmware (`CONFIG_WIRELESS_FIRMWARE_UPDATE`), not the video MFC firmware.
They are not a substitute for `mfc_fw.bin`.

## What is still plausible

The driver's vb2 queues advertise `VB2_USERPTR | VB2_DMABUF` and the DT node
has clocks, IOMMU, power domain and MFC QoS tables.  A future V4L2 M2M decode
path is technically plausible, but only after:

1. a redistributable `mfc_fw.bin` matching this exact Exynos 9820 MFC is
   supplied and its provenance/license is recorded;
2. `mfc_load_firmware()` is audited so a missing/invalid firmware returns
   promptly (no userspace-helper wait);
3. a supervised, timeout-bounded open/close probe runs in an isolated child
   (not the desktop session, not GStreamer's scanner);
4. 100 repeated open/close cycles and a real V4L2 M2M H.264/HEVC decode pass;
5. only then are the V4L2 plugins selectively restored.

Until then the guard remains installed and the status is `BLOCKED_GUARDED`.
No plugin enumeration is used as proof.

## Evidence

- `01-live-mfc.txt` — nodes, sysfs names, tracepoints, firmware absence
- `02-mfc-abi.txt` — firmware paths, DT node, guard state
- `03-firmware-dt.txt` — DT properties, firmware paths, power state
