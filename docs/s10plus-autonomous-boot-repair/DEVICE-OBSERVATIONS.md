# DEVICE-OBSERVATIONS

Chronological. Only tool-confirmed observations are recorded here; physical
actions (button presses) are never claimed unless a tool result shows them.

## 2026-10-15T06:55Z — cycle start, device in TWRP
* `adb devices -l` -> `R58M75KDB2X recovery usb:...  product:omni_beyond2lte model:Galaxy_S10_ device:beyond2lte`.
* `adb shell id` -> `uid=0(root) ... context=u:r:su:s0` (root shell confirmed by the tool).
* `getprop ro.product.device` -> `beyond2lte`; `ro.boot.bootloader` -> `G975FXXSEFUL1`.
* Live cmdline tokens include `androidboot.revision=26`, `androidboot.hardware=exynos9820`,
  `androidboot.dtbo_idx=9`, `root=PARTUUID=52444E41-494F-2044-7379-7374656D0000`.
* `/proc/mounts` shows no `sda31` / userdata mount -> Fedora rootfs untouched.
* BOOT partition readback (22,431,744 B) hashes to `ceba64ab…`: the previously
  flashed image is still intact on storage.
* `/sys/fs/pstore` empty; `/proc/last_kmsg` = the *current recovery* S-Boot log.
* USB: device present in recovery mode; no Nuxel/Fedora USB interface has ever
  been observed on this unit.

## 2026-10-15T07:05–07:13Z — cycle 2 reconnaissance (device in TWRP)
* ADB `R58M75KDB2X recovery`; `ro.product.device=beyond2lte`; `ro.twrp.version=3.7.0_9-2`;
  `ro.boot.bootloader=G975FXXSEFUL1`; root shell `uid=0` in `u:r:su:s0`.
* `/proc/uptime` = 223 s at 07:05Z -> TWRP restarted ~07:01:42Z, corroborating the
  USB drop at 07:01:12Z recorded by the previous watch.
* Live cmdline still has **no** `nuxel.*` token and **no** `buildvariant=eng`
  (TWRP's own boot-image cmdline) -> S-Boot replaces the header cmdline.
* USERDATA mounted read-only: clean ext4 Fedora 43 tree; **no `/nuxel-boot-diag.log`**.
* BOOT diag slot (57,606,144) has no `nuxel-init` record.
* `/proc/last_kmsg` (2 MiB) captured to
  `captures/20261015T070500Z-A1-postfail/last_kmsg.txt`; analysis = E1/E2.
* Boot-image / kernel / header comparison = E4/E5.

## 2026-10-15T07:13:19Z — A2 candidate flashed, reboot issued
* `adb reboot` rc=0; `adb devices` empty 5 s later.
* State: `AWAITING_BOOT_RESULT`. Watch log:
  `captures/20261015T071300Z-hardware-attempt-A2/usb-watch.log`.

## 2026-10-15T07:15:0xZ — recovery returned after A2 (agreed failure signal)
* `adb devices` -> `R58M75KDB2X recovery`; `ro.product.device=beyond2lte`;
  `ro.twrp.version=3.7.0_9-2`; `/proc/uptime` 43.96 s.
* **New pstore file**: `/sys/fs/pstore/dmesg-ramoops-0` (27,174 B) — a panic dump
  from `Linux version 4.14.253 (nuxel@nuxel-phosh)`. Saved to
  `captures/20261015T071500Z-A2-postfail/dmesg-ramoops-0.txt`.
* `/proc/last_kmsg` (767,365 B) saved to the same capture; it contains, in order,
  the A2 S-Boot record (`load_kernel: loading boot image from 218112`,
  `kernel size = 0x2ae6000`, `ramdisk size = 0x5be800`), the Nuxel kernel log
  including the full initramfs/SAR_RD failure chain and the panic, then the
  S-Boot record for the recovery boot it is running now.
* `sec_debug.reset_reason=7`, `sec_reset.reset_reason=7`, `androidboot.ulcnt=1`.
* S-Boot parsed our header as `[UFDT] BOOT IMG HDR V376101` and the recovery
  image as `[UFDT] BOOT IMG HDR V1` — direct evidence that S-Boot branches on
  the header-version field we had filled with the DTB size.
* Live DT `/chosen`: `linux,initrd-start = 0x89000000`,
  `linux,initrd-end = 0x89a66800` -> S-Boot relocates the initrd and ignores the
  header `ramdisk_addr`.

## 2026-10-15T07:21:13Z — A3 candidate flashed, reboot issued
* `adb reboot` rc=0. Watch: `captures/20261015T072100Z-hardware-attempt-A3/usb-watch.log`.
* State: `AWAITING_BOOT_RESULT`.

## 2026-10-15T07:23:19Z — recovery returned after A3 (agreed failure signal)
* USB absent 07:21:15Z -> present as recovery 07:23:19Z; `ro.product.device=beyond2lte`,
  `ro.twrp.version=3.7.0_9-2`; `/proc/uptime` 38.97 s.
* New `dmesg-ramoops-0` (27,248 B) -> a second Nuxel panic (saved to
  `captures/20261015T072330Z-A3-postfail/dmesg-ramoops-0.txt`).
* S-Boot record for A4's predecessor A3: `[UFDT] BOOT IMG HDR V1` and
  `kernel size = 0x2ae6000, ramdisk size = 0x7d0800` (8,194,048 - the exact
  header value, so the header fix is confirmed at the S-Boot level).
* Kernel log: `Freeing initrd memory: 8000K` = 8,192,000 = `round_down(size,4096)`.
* `sec_debug.reset_reason=7`, `androidctl`… (unchanged), `androidboot.ulcnt=1`.

## 2026-10-15T07:24:26Z — A4 candidate flashed, reboot issued
* `adb reboot` rc=0. Watch: `captures/20261015T072500Z-hardware-attempt-A4/usb-watch.log`.
* State: `AWAITING_BOOT_RESULT`.

## 2026-10-15T08:02-08:04Z — cycle 3 reconnaissance + A6 flash (device in TWRP)
* `adb devices -l` -> `R58M75KDB2X recovery product:omni_beyond2lte model:Galaxy_S10_ device:beyond2lte`;
  `getprop ro.twrp.version=3.7.0_9-2`; `ro.boot.bootloader=G975FXXSEFUL1`; `ro.boot.dtbo_idx=9`;
  `ro.boot.revision=26`; root shell confirmed by the tool (`uid=0`).
* Read-only forensics this cycle (no writes):
  * `/proc/device-tree/chosen/linux,initrd-start` = `89 00 00 00` (**0x89000000**),
    `linux,initrd-end` = `89 a6 68 00` (**0x89a66800**) -> delivered initrd length
    `0xa66800` = round_up(10,905,577, 2048). The ramdisk sits at a **fixed**
    0x89000000 although TWRP's header also says `ramdisk_addr = 0x11000000`.
  * `/proc/device-tree/reserved-memory/sec_rdx_bootdev` reg = `0x88000000` size
    `0x0ad00000` -> 0x89000000 lies inside it; the node carries `no-ship`, and the
    kernel logs `OF: fdt: Reserved memory: skip to reserve memory for node
    'sec_rdx_bootdev'`.
  * `/proc/device-tree/{model,compatible}` = `Samsung BEYOND2LTE EUR OPEN 26 board
    based on EXYNOS9820`, `samsung,armv8`/`samsung,exynos9820`.
  * `/proc/device-tree/memory@80000000/reg` = base `0x80000000` size `0x3ab00000`
    -> the ramdisk window is inside DRAM.
  * `/proc/cmdline` contains `bootmode=2` (recovery). The **normal** BOOT boots in
    the retained ram console contain **no `bootmode=` token at all**.
  * `/proc/last_kmsg` (2 MiB) retains three Nuxel boots (`load_kernel from 218112`,
    `ramdisk size = 0x7f0000`) plus the recovery record (`from 330752`,
    `ramdisk size = 0xa66800`), and shows S-Boot's full UFDT/DTBO/dtb_update path.
  * BOOT partition = `/dev/block/sda14`, capacity 57,671,680 B.
  * `/proc/memsize` exists but is empty for this kernel; `/sys/fs/pstore` holds one
    `dmesg-ramoops-0` (27,114 B) from A5.
* A6 preflight: **PREFLIGHT PASS** (BOOT -> /dev/block/sda14, no USERDATA target).
* A6 flash: backup of the A5 BOOT taken (`6ac9c61c…`), write 51,390,464 B,
  readback **VERIFIED `ba4f70c6…`**.
* `adb reboot` at **2026-10-15T08:04:38Z**; `adb devices` empty 4 s later.
  State `AWAITING_BOOT_RESULT`; watch log
  `scripts/s10plus-debug-pack/captures/20261015T080500Z-hardware-attempt-A6/usb-watch.log`.

## 2026-10-15T08:07:36Z — recovery returned after A6 (agreed failure signal)
* `adb devices` -> `R58M75KDB2X recovery`; `ro.twrp.version=3.7.0_9-2`;
  `/proc/uptime` 1 min; boot id `1bb04143-c930-4393-afc1-64cbc58eed61`.
* `BOOT_RESULT=FAILED_USER_RETURNED_TO_TWRP`, `RECOVERY_ACCESS=RESTORED`,
  `NEXT_ACTION=COLLECT_FRESH_KERNEL_LOGS` -> done immediately:
  * `/proc/last_kmsg` (2,097,152 B) -> `captures/20261015T080700Z-A6-postfail/last_kmsg.txt`
  * `/sys/fs/pstore/dmesg-ramoops-0` (27,251 B) -> same capture dir
  * `/proc/cmdline`, properties -> `device-state.txt`. It records
    `sec_debug.reset_reason=7`, `sec_reset.reset_reason=7`, `androidboot.ulcnt=1`,
    and `bootmode=2` (the recovery boot now running).
* Three Nuxel boot attempts are retained in the ram console (S-Boot retries):
  each `load_kernel from 218112.. kernel size = 0x2ae6000, ramdisk size = 0x5c0000`.
  `0x5c0000 = 6,029,312` is **exactly A6's new ramdisk size** — the bootloader did
  read our new container.
* Each attempt: `Trying to unpack rootfs image as initramfs...` at t=0.962 then
  `rootfs image is not initramfs (junk in compressed archive)` at t=0.962455 —
  **0.21 ms**, i.e. an immediate rejection, plus `Freeing initrd memory: 5888K`
  (again exactly A6's ramdisk size), then `Warning: unable to open an initial
  console.`, `SAR_RD: ... Out of memory`, `EXT4-fs (sda25)`, and
  `Kernel panic - not syncing: init group exit`.
* `grep -c nuxel-init` = 0 and `grep -c NUXEL_MARKER` = 0 across the whole 2 MiB
  console. Unlike cycles 1-2 this is now a *meaningful* negative result: A6 put
  `/dev/console` in the archive, so had `/init` run, its output would have been
  captured.
* Interpretation recorded in ROOT-CAUSE.md / HYPOTHESES.md: the ramdisk's contents
  are not at the address the kernel reads on the normal BOOT path. The bootloader
  advertises the initrd (length derived from our header) without populating it.
