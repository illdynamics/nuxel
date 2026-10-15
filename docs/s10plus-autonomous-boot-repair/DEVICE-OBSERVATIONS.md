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


---

# DEVICE-OBSERVATIONS — cycle 4 addendum (from the A12 capture, 2026-10-15)

## 1. A12's reboot was triggered by *our* watchdog, not by Samsung
Session 3 (kernel `4.14.253 #6`), lines 6263–6275 of the session region:
```
[   31.971401]  [6:           init: 3466] debug-snapshot: reboot_notifier_list -> dhd_reboot_callback call +
[   31.971417]  [6:           init: 3466] debug-snapshot: normal reboot starting
[   31.971424]  [6:           init: 3466] sec_debug: set magic code (0x0)
```
`comm = init`, PID 3466 = the forked watchdog subshell (`NUXEL_BOOT_WATCHDOG=30`
armed at t≈1.971 s → 31.971 s). `sec_debug: set magic code (0x0)` (a *normal
reboot*) rather than a panic magic confirms a userspace `reboot(2)`.

**Why the disarm failed:** the initramfs `bin/` has no `kill` applet — the
initramfs toybox build provides `killall`, `chroot`, `sha256sum`, `setsid`,
`timeout`, `unshare`, `nsenter`, but **not `kill`** (verified with `strings` on
`x/toybox-a12`). `[ -n "${NUXEL_WATCHDOG_PID:-}" ] && kill … 2>/dev/null` was a
silent no-op, so the watchdog outlived `switch_root` — `switch_root` only
`chroot()`s PID 1; other processes keep running.

**Why its message was lost:** the `mount --move /sys|proc|dev` loop moved the
devtmpfs out of the old root, so `/dev/kmsg` stopped resolving *by path* for
anything still on the old root. The watchdog's `nuxel_say` had no working channel
left — which is exactly why `grep -c WATCHDOG` is 0 despite the reboot happening
on schedule.

## 2. There is a working framebuffer
`show_boot_splash()` reached its `no splash data — showing navy boot screen`
branch, which is only reachable **after** the `for fb in /dev/fb0
/dev/graphics/fb0; do [ -c "$fb" ]` loop found a character device. So `/dev/fb0`
(or `/dev/graphics/fb0`) exists at t≈1.96 s. Consistent with the kernel's own
`decon_event_log_setup`, `s3cfb.bootloaderfb=0xca000000`, `lcdtype=10555411` and
the panel driver (`s6e3ha9`, `system rev : 26`, `PANEL:INFO:init_decon:xres 1440
yres 3040`).

The absence of `s3cfb`/`decon` *info* lines from the log is expected, not a
negative result: the vendor cmdline sets `loglevel=4`, so KERN_INFO(6) never
reaches the ram console.

## 3. What systemd did before it failed
* `Unable to determine whether tmpfs supports 'usrquota' mount option, assuming
  not: Function not implemented` — the **fsopen family** (Linux 5.2) is absent;
  systemd degrades gracefully.
* `Attaching device control BPF program to cgroup … failed: Argument list too
  long` then `Proceeding WITHOUT applying ACL (all devices will be accessible)!` —
  graceful degradation, not the blocker.
* `/sys/fs/cgroup/system.slice/…` paths are in use, so a **cgroup2 (unified)**
  hierarchy was up.
* `systemd-gpt-auto-generator` **really executed** (PID 3450, `exynos-ufs … ufshcd_ioctl`
  from that process). This is important evidence: the parts of systemd that do not
  go through `posix_spawn_wrapper()` worked fine on this kernel.
* `SELinux: Could not open policy file <= /etc/selinux/targeted/policy/policy.35`
  — no policy installed, so SELinux is not enforcing.

---

# CYCLE 5 DEVICE OBSERVATIONS

## A14 boot attempt (operator report + capture, 2026-10-15 11:18:53Z → TWRP)

* Samsung logo → screen goes black → stays black for 1–2 minutes → spontaneous
  reboot; entering recovery became difficult; operator recovered to TWRP manually.
* The capture *explains* the report exactly: the screen was black because the
  DECON never displayed our frame (see DISPLAY-BRINGUP.md), and the phone stayed
  black for ~60 s *after* a userspace `reboot()` was issued at t=47.17 s while the
  kernel spent that time shutting devices down (abox, PCIe, UFS, panel;
  `reboot: Restarting system` finally at t=107.804 s).
* The operator's forced recovery produced no `hard_reset_hook` BUG in this
  capture (unlike A13), i.e. recovery entry this time happened without the
  Samsung hard-reset path firing.
* Battery health is `Full`, `Health(Good)`, `Vnow 4329 mV`, `SOC 100%`,
  `Temp 246` (0.1 °C = 24.6 °C) with `sec_bat_check_recharge`, and the charge path
  was `PDIC`/`cable_type 19` before detach. There is **no** evidence of a
  depleted battery or a power-safety event; the low-battery glyph seen in an
  earlier attempt is not reproduced here.
* `/proc/uptime` in the recovery session at capture time: 4469 s, root ADB fine,
  `sec_debug.reset_reason=7` (= the normal-reboot/SWRESET path, consistent with
  the userspace reboot in the log, *not* a watchdog/panic reset).

## Device state verified before the A15 write

* `adb devices -l` → `R58M75KDB2X recovery usb:... product:omni_beyond2lte
  model:Galaxy_S10_ device:beyond2lte transport_id:15`
* `adb shell id` → `uid=0(root) … context=u:r:su:s0`
* `ro.product.device` → `beyond2lte`; `ro.twrp.version` → `3.7.0_9-2`
* `/dev/block/by-name/` map read live: `boot -> sda14`, `recovery -> sda15`,
  `userdata -> sda31` (unchanged from the A12–A14 cycles).

## A15 boot attempt — live observation (2026-10-15, cycle 5)

* `CANDIDATE=A15`, `boot.img sha256=e23d004d083b3137bc8ff1819b7b954c50700abe9ae8fd971e4cc8bf854fc966`,
  write + full SHA-256 readback PASS, `REBOOT_AT=2026-10-15T13:24:59Z`.
* Monitoring (`adb devices` + USB, 5 min from 13:25:04Z):
  **ADB absent for the whole window — the device did NOT return to TWRP.**
  For comparison A13 returned to TWRP 3.4 min after its reboot; A14 also stayed
  away 5 min. A TWRP return would have been the agreement's failure signal; it did
  not happen.
* `system_profiler SPUSBDataType` / `ioreg -p IOUSB`: **no Samsung USB device
  enumerated** (the recovery ADB gadget is gone).
* Important calibration fact measured offline from the rootfs image: there is
  **no `adbd` in the Fedora rootfs at all** (`/usr/lib/systemd/system` contains no
  adb unit; grep of the image finds none). Therefore "no ADB" is the *expected*
  state of a successful Nuxel boot and must never by itself be read as failure —
  nor as success.
* The boot's own state can only be read back from TWRP (ram console
  `/proc/last_kmsg` + BOOT slack) or from the panel. `STATE=AWAITING_OPERATOR_OBSERVATION`.
* Rootfs composition confirmed from the image (offline): `nuxel-firstlight.service`
  exists in `/etc/systemd/system`; `/etc/greetd/config.toml` still starts
  `agreety --cmd /bin/sh` (not a Phosh session); `/etc/fstab` **absent**; no
  serial console is configured (`serial-getty@.service` is available but unused),
  which is the obvious next observability channel.
* Status re-check after the 5-minute window: still no ADB device, still no
  Samsung USB node. `STATE=AWAITING_OPERATOR_OBSERVATION`.

---

# CYCLE 6 — device observations

* 2026-10-15T13:57Z — handset in TWRP after the operator manually recovered it.
  `adb devices`: `R58M75KDB2X recovery product:omni_beyond2lte model:Galaxy_S10_`;
  `adb shell id` → `uid=0(root) … context=u:r:su:s0`; `ro.product.device=beyond2lte`;
  `ro.twrp.version=3.7.0_9-2`; `ro.boot.bootloader=G975FXXSEFUL1`;
  `ro.boot.hardware=exynos9820`; `ro.boot.revision=26`; `ro.boot.dtbo_idx=9`.
* 2026-10-15T13:57Z — pstore holds exactly one record,
  `dmesg-ramoops-0.enc.z` (5084 B, Samsung `.enc.z` naming = encrypted+compressed).
  It was copied off the phone, **never cleared**.
* 2026-10-15T13:57Z — `/proc/last_kmsg` 2,097,152 B read and archived.
* 2026-10-15T13:57Z — BOOT readback identity: 50,604,032-byte prefix of
  `/dev/block/by-name/boot` hashes to `e23d004d…` = A15. **A15 was genuinely flashed.**
* Operator report triage: "screen black, device stays black for a prolonged period,
  then reboots after 1–2 min or longer, recovery entry became difficult" is
  consistent with a healthy 31.5-minute boot on a black panel that the operator
  then force-reset. Difficulty entering recovery is explained by the same hook:
  the force-reset hook needs the power+volume combination held long enough, and a
  black screen gives no feedback that the phone is alive.
* Battery during the A15 session: `level(100%)`, `Health(Good)`,
  `Status(Full)`, `Vnow(4327mV)`, `Cycle(-1)` — the "low-battery-looking icon" is
  **not** a depleted battery. TWRP agrees. Do not act on the icon.
* Thermal: `Tbat(263)` (26.3 °C), `Tusb(275)` at t=1723 s — no thermal event.
  No thermal/power protection was touched.
* 2026-10-15T14:06Z — A16 BOOT flash with automatic BOOT backup
  (`backups/s10plus/20261015T140626Z-R58M75KDB2X`), readback verified.
  USERDATA and RECOVERY not written.
* 2026-10-15T14:07:20Z — single controlled `adb reboot` issued; device left ADB
  within 5 s (`adb devices` empty) — expected, the Fedora rootfs has no ADB daemon.
* 2026-10-15T14:07:20Z→14:17:29Z — passive watch (`NUXEL_WATCH_SECONDS=600`,
  `NUXEL_WATCH_INTERVAL=5`, capture `captures/20261015T140729Z-adb-watch-84130`):
  `adb devices` returned **no device for the entire 10 minutes**, and the macOS USB
  tree showed no change. This is the expected signature of a Nuxel boot and is
  **not** a success or failure signal — the Fedora rootfs ships no `adbd`, so ADB
  absence cannot distinguish "black but alive" from "black and dead". Only the
  operator's observation (or the handset returning to TWRP) settles it.
  For reference, A15 stayed alive and healthy for 1892 s in exactly this state.

---

# CYCLE 7 — device observations (2026-10-15)

## Live TWRP re-validation (start of cycle, before anything was written)

| Item | Value |
|---|---|
| `adb devices -l` | `R58M75KDB2X recovery usb:2097152X product:omni_beyond2lte model:Galaxy_S10_ device:beyond2lte` |
| `adb shell id` | `uid=0(root)` `context=u:r:su:s0` |
| `ro.product.device` / TWRP / bootloader | `beyond2lte` / `3.7.0_9-2` / `G975FXXSEFUL1` |
| `ro.boot.hardware` / revision / dtbo_idx | `exynos9820` / `26` / `9` |
| BOOT | `/dev/block/by-name/boot` -> `/dev/block/sda14`, 57,671,680 B (112,640 sectors) |
| USERDATA | `/dev/block/by-name/userdata` -> `/dev/block/sda31`, 119,126,622,208 B |
| RECOVERY | `/dev/block/by-name/recovery` -> `/dev/block/sda15` (never written) |

## The Fedora rootfs as it exists on the handset (read-only inspection)

Mounted read-only as part of the A16 forensic capture:

* `/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so`
  sha256 `502507a7b6237a03cfcff49e389d2a38836916abdea40e36e5ba4653e9bc1234`,
  5,073,168 B — the A13 artifact, hash-identical to what A16's initramfs shipped.
* `/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so.nuxel-orig`
  5,071,376 B — the pristine Fedora library, preserved for rollback.
* `/usr/lib64/systemd/systemd` 201,024 B, `/usr/lib64/systemd/systemd-executor`
  1,400,024 B; only **one** `libsystemd-shared` on the whole filesystem (the
  "systemd loads a different copy" hypothesis is dead).
* `.nuxel-patches/pidfd-spawn-fallback-A13` present (the marker-only tag).
* `nuxel-boot-diag.log` (3,175 B) — the A16 boot record, ending with
  `FB_SYSFS … modes=U:1440x3040p-0`, `FIRSTLIGHT exit=0`,
  `FIRSTLIGHT hold started pid=` (empty), `USERDATA_FALLBACK /dev/sda31`.

## UDC / USB gadget availability (live)

```
$ adb shell ls /sys/class/udc/
10c00000.dwc3
$ adb shell ls /sys/kernel/config
sdcardfs  usb_gadget
```

A16's own boot log confirms the controller comes up as a gadget controller:
`dwc3 10c00000.dwc3: Binding gadget dwc3-gadget`, `dwc3_otg_init`,
`exynos-dwc3 10c00000.usb: dwc3_exynos_rsw_start`.

## Host-side USB inventory

* Before the A17 reboot the Mac saw the TWRP gadget as
  `Galaxy S10+ · Product ID 0x6860 · Vendor 0x04e8 · Speed 5 Gb/s · Serial R58M75KDB2X`.
* After `adb reboot` into A17 at 15:07:35Z, **no USB device enumerated at all**
  over the following minutes (no `0x04e8`, no `0x18d1`, no `/dev/cu.usbmodem*`).
  This matches the A16 behaviour (a Nuxel boot creates no userspace gadget), and
  is the open question for A17: did `nuxel-console` bind?

---

# CYCLE 7 — Phase 6 prerequisites measured from the A16 ram console

## The kernel has NO loadable modules at all

`grep -cE '^CONFIG_.*=m$' .config` on the A16/A17 kernel config → **0**.
Everything is built into the kernel image (`=y`). Consequences:

* The failing `modprobe@drm.service` in A16 is a **non-issue**: there is no `drm`
  module and no module tree to load from. The Fedora rootfs needs no Samsung
  modules, so there is no module/hardware version-skew problem to solve.
* Any future driver we need must be built into the kernel.

## Display driver stack (confirmed, Path B is the only short-term option)

```
t=0.500  register_common_panel panel:s6e3ha9_beyond2_a3_s0_default id:0xA01011 rev:2
t=1.242  find_panel_ddi_lut, found s6e3ha9_beyond2 (id:0x00A11013)
t=1.242  LCD(/s6e3ha9_beyond2) resolution: xres(1440), yres(3040)
t=1.999  find_common_panel_with_name, found panel:s6e3ha9_beyond2_a3_s0_default
t=2.001  panel_poc_probe total_size:753670 registered successfully
t=2.002  mdnie registered successfully / copr_probe registered successfully
```

There is **no `/dev/dri` and no DRM**: `# CONFIG_DRM is not set`. The only display
interface is the Samsung DECON/DSIM fbdev path (`/dev/fb0`, 32 bpp,
`stride=5760`, `virtual_size=1440,6080`). Only `beyond-madera:card0` (an ALSA
sound card) contains the string "card0" anywhere in the boot log.

**Therefore Phoc/wlroots cannot start on this kernel today.** The transitional
path is an fbdev-native Nuxel UI (`PHONE-UI-HANDOFF.md` §3, Path B).

## Touchscreen: the driver is present but deliberately declines to init

```
t=0.955951  __init_sec_tsp_command_history: init done
t=0.955968  __init_sec_tsp_raw_data: init done
t=1.534311  [sec_input] sec_ts_init: Do not load driver due to : lpm 1
```

`CONFIG_TOUCHSCREEN_SEC_TS_Y771=y` (Samsung's TSP driver for the S10+) is built
in and runs its init, then **returns early because the panel is in LPM=1** (the
display was never properly brought out of low-power mode by an Android-style
userspace). That is why the A16 input list stops at:

| node | device |
|---|---|
| input0 | `meta_event` (virtual) |
| input1 | `gpio_keys` (POWER/VOLUME) |
| input2 | `grip_sensor` (virtual) |
| input3 | `ssp_context` (virtual) |
| input4 | `Headset` (madera-extcon) |
| input5 | `hall` |
| input6 | `certify_hall` |

**No `sec_touchscreen` / TSP input device exists yet.** So the "touchscreen"
milestone is not just untested — as of A16 there is no touch input node at all.

Next step for touch (A18/Phase 6): find and clear the LPM gate from userspace
after the display is up (`/sys/class/lcd/panel/*`, the DECON/panel LPM attribute,
or the driver's own resume path), then re-trigger `sec_ts` init and confirm
`/dev/input/event*` for the TSP. The sensor hub itself is healthy
(`[SSP] ssp_probe` registered accel/gyro/mag/light/prox/step as iio devices at
t=1.72 s), so input *infrastructure* works — only the touch panel is gated.

---

# CYCLE 7 — WHY THE TOUCHSCREEN IS ABSENT: charger-mode boot (LPM), not a driver bug

This is the single highest-value finding of the cycle for Phase 6, and it is fully
deterministic.

## The mechanism

`drivers/samsung/misc/sec_batt.c`:

```c
unsigned int lpcharge;
static int sec_bat_is_lpm_check(char *str)
{
        if (strncmp(str, "charger", 7) == 0)
                lpcharge = 1;
        pr_info("%s: Low power charging mode: %d\n", __func__, lpcharge);
        return lpcharge;
}
__setup("androidboot.mode=", sec_bat_is_lpm_check);
```

`drivers/input/touchscreen/sec_ts/y771/sec_ts.c`:

```c
static int __init sec_ts_init(void)
{
#ifdef CONFIG_BATTERY_SAMSUNG
        if (lpcharge == 1) {
                pr_err("%s %s: Do not load driver due to : lpm %d\n", SECLOG, __func__, lpcharge);
                return -ENODEV;
        }
#endif
        pr_info("%s %s\n", SECLOG, __func__);
        return i2c_add_driver(&sec_ts_driver);
}
```

The same `lpcharge == 1` gate exists in `sec_ts.c:797` (probe), in
`drivers/fingerprint/qbt2000_common.c:1363` and in
`drivers/input/wacom/wacom_i2c.c:3281`.

## Proof that A16 booted in that mode

```
t = 0.000000  sec_bat_is_lpm_check: Low power charging mode: 1      (A16 session, line 66)
t = 1.534311  [sec_input] sec_ts_init: Do not load driver due to : lpm 1
```

`androidboot.mode=charger` is consumed by the `__setup` handler, which is why the
string does not appear in any later `Kernel command line:` printout — but the
handler's own message at t = 0 is conclusive: **A16 ran with `lpcharge = 1`.**

## Consequences, exactly as observed

`sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`, so the TSP never
probes: no `sec_touchscreen` input device can exist. The A16 input list stops at
`input0..input6` (meta_event, gpio_keys, grip_sensor, ssp_context, Headset, hall,
certify_hall) — exactly what a charger-mode boot produces. The sensor hub itself
is healthy, so this is *only* the LPM gate. Fingerprint and S-Pen are gated the
same way.

## The operational consequence — CHANGE THE REBOOT PROCEDURE

The observed workflow was: phone connected to the MacBook → `adb reboot` from
TWRP → S-Boot boots the Nuxel kernel with the charger-mode marker → `lpcharge=1`
→ no touchscreen, no fingerprint, no wacom.

So for any candidate where input matters:

1. **Reboot with USB detached** (or power on from the key combo with no cable),
   so `androidboot.mode` is not `charger`;
2. verify `sec_bat_is_lpm_check: Low power charging mode: 0` and the absence of
   `sec_ts_init: Do not load driver due to : lpm 1` in the ram console, then
3. **attach USB after the boot** — the dwc3 role switch
   (`dwc3_exynos_rsw_start`) will then bring up device mode and the A17 CDC-ACM
   console can bind.

Both A16 and A17 were/are almost certainly LPM boots, so "touchscreen does not
work" is **not yet a finding about anything**; it is a boot-mode artefact. Do not
record `TOUCHSCREEN=FAILED` from an LPM boot.

## Also implied: `MODULES` are irrelevant here

`grep -cE '^CONFIG_.*=m$'` on the kernel config is **0** — nothing is built as a
module. The `modprobe@drm.service` failure in A16 was therefore always a no-op.
