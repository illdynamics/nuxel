# Nuxel g7power — Stage 1 + Stage 2 execution report (2026-10-14)

Device: Motorola Moto G7 Power `ocean` (XT1955, SDM632), serial ZY326RGXCM,
bootloader unlocked, sitting in **stock ABOOT fastboot** (22b8:2e80) at start.

## Outcome

| Goal | Result |
|---|---|
| Stop the "flashing every ~3 s" bootloop | **DONE** — after flashing the corrected chain the device **left fastboot and did not come back** (verified > 7 min, incl. a 210 s poll). Screen = black, not looping. |
| Make the display (Stage 2) | **DONE (kernel-level)** — rebuilt kernel with `CONFIG_DRM_SIMPLEDRM=y` + `CONFIG_FRAMEBUFFER_CONSOLE=y`, `console=tty0`, verified present in the built `Image.gz`, flashed. |
| See Nuxel boot on screen | Not observable from the host (no camera). The USB serial console (`1d6b:0104` / `ttyACM0`) did **not** enumerate, so userspace could not be sampled from here. |

## Three REAL root causes found and fixed

### 1. Initramfs could not exec `/init` — kernel "No working init found" → bootloop
The shipped `-final` ramdisk contained `init` (a `#!/bin/sh` script) and
`bin/toybox`, but **no `/bin/sh`** and **no toybox applet symlinks**
(`mount`, `blkid`, `switch_root`, …). The kernel therefore could not run the
init at all. The init's own "create the symlinks" block was guarded by
`[ ! -e /bin/sh ]`, but `/bin/sh` never existed, and as soon as it were created
the guard would skip the loop. Net effect: PID 1 never started → the device
reset → **screen flashed every few seconds**. This matches the symptom exactly.

Fix (`finish2/init-final.sh` + rebuilt ramdisk):
* guard the applet-symlink loop on `bin/toybox` (not on `/bin/sh`);
* `[ -e /bin/x ] || ln -sf toybox /bin/x` for all needed applets;
* rebuilt the ramdisk with `finish2/make-initramfs.py`, so the initramfs now
  really contains `bin/sh` + all applets.

### 2. The Nuxel kernel defconfig fragment was NEVER applied (display/touch/backlight missing)
`kernel/g7power/build-kernel.sh` called

    merge_config.sh -m "${KOUT}/.config" "${DEFCONFIG}"

`merge_config.sh` derives its **output** path from its `-O` option (default
`.`), so the merged fragment was written to `./.config` (cwd) — **not** to
`${KOUT}/.config`. The following `make olddefconfig` read the un-merged
`${KOUT}/.config` (plain arm64 `defconfig`) and every Nuxel override was
silently dropped. Proof: the original build left `/x/nuxel/.config` behind,
and the built `.config` had `# CONFIG_DRM_SIMPLEDRM is not set`,
`# CONFIG_TOUCHSCREEN_ILI210X is not set`, `# CONFIG_LEDS_LM3697 is not set`,
`CONFIG_DWC_MSM=m` — i.e. **no display, no touch, no backlight**, despite the
repo docs claiming otherwise. This is why Stage 2 "was never done".

Fix: pass `-O "${KOUT}"` (and moved the fragment's inline `# comments` onto
their own lines). After the fix the built `.config` / `Image.gz` contain:

    CONFIG_DRM_SIMPLEDRM=y  CONFIG_FRAMEBUFFER_CONSOLE=y  CONFIG_TOUCHSCREEN_ILI210X=y
    CONFIG_LEDS_LM3697=y    CONFIG_DRM=y                  0 "value not in final .config"

### 3. The guide's "payload at 512 KiB" boot scheme cannot boot on this lk2nd
`build/out/g7power/lk2nd.img` is a modern lk2nd. `lk2nd_boot()` does **not**
read an Android payload appended at 512 KiB; it scans partitions, mounts an
**ext2** filesystem and boots via **extlinux**:

    /<part>/extlinux/extlinux.conf   (LABEL/DEFAULT + KERNEL/FDT/INITRD/APPEND)

The guide's `lk2nd-nuxel-final-combined.img` (lk2nd@0 + v1 payload@512 KiB) is
therefore never consumed. lk2nd falls through to
`"Reverting to android boot"`, stock ABOOT reloads lk2nd, and the loop repeats
forever — the "flashing every 3 s".

Fix: boot via extlinux. `nuxel-boot-ext2-simpledrm.img` is a 80 MiB ext2 fs
(label `nuxel-boot`) containing `Image.gz`, `sdm632-motorola-ocean.dtb`,
`initramfs` and `extlinux/extlinux.conf`, flashed to `system_a` (lk2nd scans it
because it is > 16 MiB).

## What was flashed (final, working state)

    dtbo        stock/firmware/extracted/dtbo.img
    boot_a/b    lk2nd.img                       (4550b205…cb562)
    system_a    nuxel-boot-ext2-simpledrm.img   (b31d8ffb…91c8b7a)  <- extlinux bootfs
    system_b    nuxel-ocean-rootfs-final.img    (rootfs, label nuxel-ocean)

`userdata` is refused by this ABOOT ("flash permission denied"); `system_b`
is accepted, and the init finds the root by ext4 label + GPT numbers anyway.

## How this was verified from the host
* `lsusb` / `fastboot devices` polling: before → device returned to `22b8:2e80`
  (~55–75 s after each reboot); after → **no `22b8:2e80` for > 7 minutes** and
  no reboot. Loop gone.
* Kernel config extracted back out of the flashed-able `Image.gz` with
  `scripts/extract-ikconfig` (SIMPLEDRM / ILI210X / LM3697 all `=y`).
* Ocean DTB confirms `/chosen/framebuffer@90001000` = `simple-framebuffer`
  720×1520 `r8g8b8` and `usb@70f8800 … dr_mode = "peripheral"`.

## Still open
* USB serial console (`1d6b:0104` → `/dev/ttyACM0`) did not enumerate, so
  userspace could not be sampled. `CONFIG_PHY_QCOM_QUSB2=m` is loaded by the
  init; if the console is still absent next boot, build it in
  (`CONFIG_PHY_QCOM_QUSB2=y`) so `dwc3` gets its PHY at probe time.
* The panel itself is verified only at the kernel level (driver + DT present);
  the picture cannot be observed from the host.
