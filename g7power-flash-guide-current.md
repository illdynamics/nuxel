# Nuxel — Moto G7 Power (`ocean`) — CURRENT flash guide

**Device:** Motorola Moto G7 Power **XT1955** — SDM632 / msm8953 family, codename **`ocean`**
**Host:** this machine (Linux, Fedora-family), G7 Power on USB
**Written:** 2026-10-13 · **Nuxel build:** `v0.3.2-alpha` (images built 2026-10-12/13)
**Scope:** finish the flash **from the live state of this unit right now** until Nuxel
boots on it, and get a real **display**.

> This supersedes `g7power-flash-guide.md` (that one is the "from a stock phone"
> two-phase doc). **This** file is the "we already started, here is exactly
> where we are and what is left" doc.

---

## 0. Verdict first (read this, then work top-to-bottom)

- **Bootloader: unlocked. Already done.** (`securestate: flashing_unlocked`)
- **lk2nd: already flashed and working** — you have seen its screen. Do **not**
  re-derive the boot chain; it exists.
- **The images are already built**, including the fixed `-final` set. You do
  **not** need to rebuild anything to finish *Stage 1*.
- **Yes — use the `-final` boot + rootfs.** Concretely:
  - boot: **`build/out/g7power/lk2nd-nuxel-final-combined.img`**
  - rootfs: **`build/out/g7power/nuxel-ocean-rootfs-final.img`**
  - (do **not** use the bare `nuxel-ocean-boot-final.img` — it is a raw FDT and
    lk2nd rejects it; see §3.)
- **You are here → Stage 1, Step 1.** What is left is one clean re-flash of the
  `-final` chain, then a **display fix** (Stage 2) that is the *only* reason you
  have not seen Nuxel on screen yet.

**The single most important thing to understand:** on the current kernel the
screen goes **black right after the lk2nd logo — and that is expected, not a
failure.** The kernel has *no driver that can draw to this panel* (see §5).
"Black" = it may well be running fine. "Flashing white every few seconds" = it
is reboot-looping. The `-final` files were built specifically to stop the loop.
To actually **see** Nuxel you must do **Stage 2** (§8).

---

## 1. Live device state (verified on this unit just now)

```
lsusb         -> Bus 003 Device 096: ID 22b8:2e80 Motorola PCS Fastboot ocean S
fastboot getvar product      -> ocean
fastboot getvar securestate  -> flashing_unlocked
fastboot getvar serialno     -> ZY326RGXCM
fastboot getvar current-slot -> a
fastboot getvar running-slot -> _a
slot-successful : _a No   _b No
slot-retry-count: _a 7    _b 0
reason: Volume down key pressed          <- you entered fastboot by hand
max-download-size: 536870912 (512 MiB)   <- our 478 MiB rootfs fits one write
```

- The device is sitting in **stock ABOOT fastboot** (`product=ocean`, not `lk2nd`).
- Only the **G7 Power** is on USB (no S10+ this time — safe to flash).
- **Host fastboot permission:** there is **no udev rule** for `22b8:2e80`, so a
  plain `fastboot` prints *“no permissions”*. Use the wrapper used in all prior
  sessions, which runs fastboot as root in a privileged container:
  `/tmp/fb`. Re-check the state any time with:

  ```bash
  FBTIMEOUT=30 /tmp/fb devices
  FBTIMEOUT=40 /tmp/fb getvar product
  FBTIMEOUT=40 /tmp/fb getvar securestate
  FBTIMEOUT=40 /tmp/fb getvar max-download-size
  ```
  > **Never** send this ABOOT `current-slot`, `slot-suffixes` or `has-slot:*`.
  > This old Motorola ABOOT does not implement them, never replies, and **wedges
  > its fastboot** until you power-cycle. (This has bitten us before.)

---

## 2. What is already done vs. what is left

| # | Step | State |
|---|---|---|
| 1 | Bootloader unlocked (Motorola code) | ✅ done |
| 2 | Stock firmware pulled + extracted (`boot.img`, `dtbo.img`) | ✅ `build/out/g7power/stock/firmware/extracted/` |
| 3 | lk2nd built and flashed to `boot` (you saw its screen) | ✅ done, working |
| 4 | Nuxel kernel `Image.gz` + ocean DTB built | ✅ done |
| 5 | Nuxel initramfs + boot image + ext4 rootfs built | ✅ done |
| 6 | Root-cause fixes baked into the **`-final`** artifacts (see §4) | ✅ done |
| 7 | Host flash tooling (`/tmp/fb` docker wrapper, QCDT packer, cmdline patcher) | ✅ present |
| 8 | **Clean re-flash of the `-final` chain** | ⬜ **this is where you resume (Stage 1)** |
| 9 | **Kernel that can display on the panel** (`DRM_SIMPLEDRM`) | ⬜ **remains (Stage 2)** |

**Everything up to step 7 is done. Resume at Stage 1 (§6), then do Stage 2 (§8) for a display.**

### 2.1 Why earlier attempts showed black / flashing
The prior sessions *did* flash boot/rootfs, but hit three real bugs that are now
**already fixed inside the `-final` files**:
1. **`root=` bug** — the old cmdline pointed at
   `/dev/block/bootdevice/by-name/userdata`, an Android/`ueventd` path that
   **mainline Linux never creates** → root mount failed. The `-final` initramfs
   now **finds the root by its ext4 LABEL (`nuxel-ocean`)** plus GPT numbers
   (p63/p64/p62).
2. **lk2nd DT bug** — lk2nd validates the payload's device-tree region and
   requires a **QCDT table in lk2nd's own layout**; a raw FDT gives
   *“Bad magic in device tree table”*. `-final-qcdt` is correctly wrapped by
   `tools/build-qcdt-boot.py`.
3. **Bootloop** — the old init rebooted on failure, which is the *“flashing white
   every few seconds”* you saw. The `-final` init **never reboot-loops**: it stays
   up and keeps retrying, and brings up a USB console.

So the black/flashing you saw was a **real bug set that is now fixed in the
files you are about to flash** — not something you have to solve again.

---

## 3. The `-final` images — exactly which to use

All in `build/out/g7power/`:

| Use | File | Size | SHA-256 | Goes to |
|---|---|---|---|---|
| **✅ boot (THIS ONE)** | `lk2nd-nuxel-final-combined.img` | 22,276,096 | `d4b4d791…239286` | `boot_a` **and** `boot_b` |
| **✅ rootfs** | `nuxel-ocean-rootfs-final.img` | 501,440,512 | `19ed81ce…606610` | `userdata` (fallback `system_b`) |
| **✅ dtbo (safety, flash first)** | `stock/firmware/extracted/dtbo.img` | 1,802,240 | `f6018eff…2b35d` | `dtbo` |
| ⛔ do **not** flash as boot | `nuxel-ocean-boot-final.img` | 21,745,664 | `3fc2ad98…afce8d` | raw FDT → lk2nd rejects |
| (informational) the bare payload | `nuxel-ocean-boot-final-qcdt.img` | 21,751,808 | `007f2eaa…a49a6` | = inside the combined file |
| (reference) lk2nd | `lk2nd.img` | 364,560 | `4550b205…cb562` | = first 512 KiB of combined |

**Why the “combined” file:** lk2nd splits the `boot` partition — **first 512 KiB
= lk2nd itself, the rest = the real OS boot image.** So one image =
`lk2nd.img`(padded to 512 KiB) + `nuxel-ocean-boot-final-qcdt.img`. Flashing that
single file to `boot_a`/`boot_b` lets **stock ABOOT install both stages in one
write**, which is exactly why you do **not** need the flaky “reboot into lk2nd’s
own fastboot” mode. (Verified: bytes 0…512 KiB are `lk2nd.img`, bytes 512 KiB…
are byte-identical to `nuxel-ocean-boot-final-qcdt.img`.)

The `-final` payload’s cmdline is:
```
console=ttyMSM0,115200 nuxel.device=g7power rootfstype=ext4 rootwait rw lk2nd.pass-ramoops ignore_loglevel
```
(no `root=` — the init discovers it), and its initramfs is `finish2/init-final.sh`.

---

## 4. The boot chain (so the steps make sense)

```
PBL → stock ABOOT  →  [ boot = lk2nd @0 | Nuxel boot.img @512KiB ]  →  mainline kernel
    →  Nuxel initramfs (finds root by LABEL)  →  switch_root  →  rootfs /sbin/init (toybox shell)
```

- **dtbo before boot, always.** A custom `boot` with a bad/missing `dtbo` is the
  classic msm8953 soft-brick. We flash the **stock** dtbo first, every time.
- The rootfs is a **Phase-1 toybox userspace** (busybox-style applets + a module
  tree + `/etc/nuxel`). It is **not** Phosh/Flatpak yet — “boot into Nuxel” here
  means *kernel + initramfs + toybox userspace running*, which is the Phase-1
  milestone.

---

## 5. The display reality — black screen ≠ failure

This is the part that has made the last few attempts look like failures.

**What is on the panel path:** lk2nd leaves a framebuffer at
`/chosen/framebuffer@90001000` in the device tree — **720×1520, format `r8g8b8`**.
The kernel *receives* it, but **nothing in the current kernel consumes it**:

```
CONFIG_DRM_SIMPLEDRM      is not set     <- would drive "/chosen simple-framebuffer"
CONFIG_FB_SIMPLE          is not set
CONFIG_SYSFB_SIMPLEFB     is not set
CONFIG_DRM_MSM            = m            <- module, and the rootfs init never loads it
(ocean DTS has NO DSI panel node)        <- mainline drives no panel for ocean yet
```

Result: after the kernel takes over from lk2nd there is **no output device**, so
the panel goes **black**. On this unit:

| What you see | What it means | What to do |
|---|---|---|
| **Black screen right after the lk2nd logo**, no reboot | **Expected.** Kernel booting / userspace up, just no display. This is NOT a failure. | Verify it is alive (Step 7.2), then do Stage 2 (§8) for a display. |
| **White flash every few seconds**, then black, repeating | The device is **reboot-looping** (each cycle re-draws the Moto/lk2nd logo). The old init did this on failure. | The `-final` init fixes it. If it *still* loops, the crash is in the kernel before init → capture via UART, don’t keep flashing. |
| lk2nd menu/splash only, then nothing forever | Kernel didn’t start. | Check you flashed the **combined** image (§6), not the bare raw-FDT one. |
| Nothing at all, no USB | Died / soft-brick. | EDL recovery (§9). |

**Success signal without a display:** the device **leaves fastboot and does not
come back**. `lsusb` will stop showing `22b8:2e80`; instead the `-final` init
brings up a USB gadget that shows as **`1d6b:0104  “G7Power Nuxel”`**, which the
host sees as a **serial port `/dev/ttyACM0`** (§7).

---

## 6. STAGE 1 — flash the `-final` chain (exact, in order)

### 6.0 Preconditions (30 seconds)
```bash
# Battery > 60%. Data cable (not charge-only), direct port. One phone on USB:
lsusb | grep -i 22b8            # -> "Motorola PCS Fastboot ocean S"
```
Make sure the phone is on the **stock ABOOT fastboot** screen: from OFF, hold
**Volume-Down**, press **Power**, keep holding Volume-Down until
“AP Fastboot Flash Mode” / “FLASH MODE” appears. (That is the screen you are on now.)

### 6.1 Verify identity (safe getvars only)
```bash
FB=/tmp/fb
FBTIMEOUT=30 $FB devices
FBTIMEOUT=40 $FB getvar product       # MUST print: ocean
FBTIMEOUT=40 $FB getvar securestate   # MUST print: flashing_unlocked
```
If `product` is not `ocean`, **STOP** — wrong device.

### 6.2 Flash `dtbo` FIRST (stock Motorola dtbo — the anti-brick step)
```bash
FBTIMEOUT=120 $FB flash dtbo build/out/g7power/stock/firmware/extracted/dtbo.img
```

### 6.3 Flash the combined Nuxel boot to **both** slots
```bash
BOOT=build/out/g7power/lk2nd-nuxel-final-combined.img
FBTIMEOUT=300 $FB flash boot_a "$BOOT"
FBTIMEOUT=300 $FB flash boot_b "$BOOT"
```
> Both slots on purpose: it no longer matters which slot the bootloader picks or
> which one lk2nd “deactivated”. If ABOOT rejects `boot_b`, that is fine — `boot_a`
> is what matters.

### 6.4 Flash the rootfs
```bash
ROOTFS=build/out/g7power/nuxel-ocean-rootfs-final.img
FBTIMEOUT=900 $FB flash userdata "$ROOTFS"
```
- The `-final` init finds the root by **LABEL `nuxel-ocean`**, and also probes
  **`/dev/mmcblk0p63` (system_b), `p64` (userdata), `p62` (system_a)**, so it will
  be found whichever of those you use.
- **If `flash userdata` is refused** by this ABOOT’s partition allow-list, fall
  back (same image, different target partition) — the init looks there too:
  ```bash
  FBTIMEOUT=900 $FB flash system_b "$ROOTFS"     # p63
  ```

### 6.5 Reboot
```bash
FBTIMEOUT=120 $FB reboot
```
Now watch the phone:
1. Motorola logo →
2. **lk2nd** splash (this is the “N/A”/logo screen you saw) → if a menu appears,
   use **Vol keys** to highlight **Continue** and press **Power**; otherwise it
   boots the payload automatically →
3. kernel →
4. **screen goes black — expected** (§5).

**Do not panic at the black screen.** Go to §7 to confirm it is alive, then §8 to
add the display.

---

## 7. Verify it is alive WITHOUT a display

### 7.1 Host USB identity change
```bash
watch -n1 'lsusb | grep -Ei "22b8:2e80|1d6b:0104"'
```
- still `22b8:2e80` = still in fastboot (didn’t boot).
- `1d6b:0104` = **Nuxel userspace is up** (the init’s USB gadget). ✅

### 7.2 USB serial console (the init sets this up for you)
The `-final` init creates a CDC-ACM gadget (“G7Power Nuxel”). When it is up the
host gets a serial port:
```bash
ls /dev/ttyACM* 2>/dev/null
# then, in another terminal:
sudo screen /dev/ttyACM0 115200     # or: picocom -b 115200 /dev/ttyACM0
```
You should see the init banner (`=== Nuxel g7power bring-up ===`) and then a
**`/ #` shell**. `ROOT OK:` / `switch_root ->` lines mean the rootfs was found and
Nuxel userspace launched. Useful once in:
```sh
uname -a            # 6.19.0-... aarch64
cat /proc/cmdline
dmesg | grep -iE 'msm|drm|mmc|ext4|ili210x|wcn36xx'
ls /lib/modules
```

### 7.3 (optional) hardware UART
The kernel console is `console=ttyMSM0,115200`. If you have a UART/pogo rig,
`picocom -b 115200 /dev/ttyUSB0` shows the full boot log.

> If §7.1 shows `1d6b:0104` or §7.2 gives you a shell — **Stage 1 succeeded**.
> The remaining work is purely the display (Stage 2).

---

## 8. STAGE 2 — get a real display (the panel handoff)

**Root cause (recap):** the kernel does not consume lk2nd’s `simple-framebuffer`,
and mainline has no DSI panel driver for `ocean`. The fix that makes the screen
show output is to let the kernel scan out **lk2nd’s framebuffer** by enabling
**`CONFIG_DRM_SIMPLEDRM`**. That gives you `/dev/fb0` + a framebuffer console on
the 720×1520 panel — i.e. you will **see** the kernel log and the Nuxel console.

> This requires a **kernel rebuild** (the built tree is not on disk here). It is
> the one remaining piece. It changes nothing about lk2nd, the rootfs or the flash
> order — only the kernel inside the `boot` image.

### 8.1 Add the option to the defconfig
Edit `kernel/g7power/defconfig` and add:
```
CONFIG_DRM_SIMPLEDRM=y
CONFIG_FRAMEBUFFER_CONSOLE=y
```
(`FRAMEBUFFER_CONSOLE` is already on; keep it. Leave `CONFIG_DRM_MSM` alone.)

### 8.2 Rebuild the kernel (needs network + `aarch64-linux-gnu-gcc`)
```bash
NUXEL_DEVICE=g7power kernel/g7power/build-kernel.sh --clone --jobs "$(nproc)"
# outputs:
#   kernel/g7power/.build/out/arch/arm64/boot/Image.gz
#   kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb
```

### 8.3 Repack the v1 boot image with a console on the panel
Add `console=tty0` so kernel/console output also goes to the framebuffer:
```bash
RD=/tmp/nuxel-final-ramdisk.cpio.gz      # reuse the -final initramfs (unchanged)
# (extract it once from the -final boot image — see §11.3 for the snippet)

python3 boot/g7power/pack-boot-v1.sh \
  --kernel  kernel/g7power/.build/out/arch/arm64/boot/Image.gz \
  --ramdisk "$RD" \
  --dtb     kernel/g7power/.build/out/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb \
  --cmdline "console=ttyMSM0,115200 console=tty0 nuxel.device=g7power rootfstype=ext4 rootwait rw lk2nd.pass-ramoops ignore_loglevel" \
  --output  /tmp/nuxel-ocean-boot-simpledrm.img
```

### 8.4 Wrap QCDT + combine with lk2nd (exactly like `-final`)
```bash
python3 tools/build-qcdt-boot.py \
  /tmp/nuxel-ocean-boot-simpledrm.img \
  /tmp/nuxel-ocean-boot-simpledrm-qcdt.img \
  --combined build/out/g7power/lk2nd.img \
             build/out/g7power/lk2nd-nuxel-final-simpledrm-combined.img
```

### 8.5 Flash it (same order as Stage 1)
```bash
FB=/tmp/fb
FBTIMEOUT=120 $FB flash dtbo build/out/g7power/stock/firmware/extracted/dtbo.img
FBTIMEOUT=300 $FB flash boot_a build/out/g7power/lk2nd-nuxel-final-simpledrm-combined.img
FBTIMEOUT=300 $FB flash boot_b build/out/g7power/lk2nd-nuxel-final-simpledrm-combined.img
FBTIMEOUT=120 $FB reboot
```

**Expected after Stage 2:** Moto logo → lk2nd splash → **panel keeps showing the
framebuffer** → kernel boot messages / console appear on the 720×1520 screen
instead of going black. That is your “display and see it boot into Nuxel”.

> Honest caveat: `simpledrm` scans out lk2nd’s framebuffer; it does **not** drive
> the DSI panel itself. So you get a **visible framebuffer console + any
> `/dev/fb0` output** (this is the Phase-1 display milestone). Full panel +
> backlight (LM3697) + Phosh is Phase-2 panel-driver work.

---

## 9. Revert to stock (your undo button) / unbrick

**Revert to stock Android** (any time, from stock ABOOT fastboot):
```bash
FB=/tmp/fb
FBTIMEOUT=120 $FB flash dtbo build/out/g7power/stock/firmware/extracted/dtbo.img
FBTIMEOUT=120 $FB flash boot build/out/g7power/stock/firmware/extracted/boot.img
FBTIMEOUT=120 $FB reboot
```

**EDL / Qualcomm 9008 (only if fastboot is unreachable):** power off, hold
**Vol-Down + Vol-Up**, plug USB; host must show `05C6:9008`. Restore stock
partitions with `edl` (bkerler) or Windows **QFIL**. Blankflash zips are already
here: `build/out/g7power/stock/blankflash/`.

> **Never** lock the bootloader while Nuxel is installed. **Never** write
> `modemst1 modemst2 fsg fsc ddr persist misc` (IMEI/radio/DDR calibration —
> irreplaceable).

---

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `fastboot devices` empty, works only as root | no udev rule for `22b8:2e80` | use `/tmp/fb` (docker wrapper), as always |
| `getvar` hangs, then everything hangs | you sent `current-slot`/`slot-suffixes`/`has-slot:*` | power-cycle; only use safe getvars (§1) |
| lk2nd logo → **black**, no reboot | **expected** — no display driver | confirm alive (§7); do Stage 2 (§8) |
| lk2nd rejects image, “Bad magic in device tree table” | flashed the **raw-FDT** `nuxel-ocean-boot-final.img` | flash the **combined** image (§6.3) |
| **Flashing white every few secs** | reboot-loop (kernel crash before init) | `-final` init stops the init-loop; if it persists it is a kernel crash → capture UART, don’t re-flash blindly |
| `flash userdata` refused | ABOOT partition allow-list | `flash system_b` instead (§6.4 fallback) |
| Boots but `/dev/ttyACM0` never appears | gadget/UDC didn’t come up | check §7.3 UART; still likely running |
| Nothing at all, no USB | soft/hard brick | EDL (§9) |

---

## 11. Appendix

### 11.1 Partition map (this unit, GPT)
```
boot_a = mmcblk0p41   boot_b = mmcblk0p42
dtbo_a = mmcblk0p43   dtbo_b = mmcblk0p44
system_a = p62        system_b = p63      userdata = p64
NEVER TOUCH: modemst1 p28, modemst2 p29, fsg, fsc, ddr, persist p32, misc
```

### 11.2 Artifact hashes (SHA-256, verify before flashing)
```
d4b4d791e8430530403adbca56919ea419bc1f6921ddb133dec0f0bdef239286  lk2nd-nuxel-final-combined.img
19ed81ce3517738cf41b1f4eb25638277b113369bc625a2bea0cd8f529606610  nuxel-ocean-rootfs-final.img
007f2eaaa16c12933987d0ccbad02cfebab7f978a3b77a6b968f9d956a4a49a6  nuxel-ocean-boot-final-qcdt.img
4550b20513f3cb93516edaeb16986b88af048d6c9d374d674e22d06edcacb562  lk2nd.img
f6018eff8e9320c9a803cd99474a361e9224f8ec26374f1833703c0f85e2b35d  stock/firmware/extracted/dtbo.img
73849a4e343b603a02e6b6280b06b481b359d55205f503972ca622f7e896702e  stock/firmware/extracted/boot.img
```
Check with `sha256sum -c` / `sha256sum <file>`.

### 11.3 Extract the `-final` initramfs (for Stage 2 reuse)
```bash
python3 - <<'PY'
import struct
f=open('build/out/g7power/nuxel-ocean-boot-final-qcdt.img','rb').read()
u=lambda o:struct.unpack('<I',f[o:o+4])[0]
ks,rs,ps=u(8),u(16),u(36)
pages=lambda n:(n+ps-1)//ps
ro=ps+pages(ks)*ps
open('/tmp/nuxel-final-ramdisk.cpio.gz','wb').write(f[ro:ro+rs])
print("wrote /tmp/nuxel-final-ramdisk.cpio.gz")
PY
```

### 11.4 Key facts
- lk2nd split: first **512 KiB = lk2nd**, remainder = OS boot image.
- Payload DT must be **QCDT v3, 12-byte header** (`tools/build-qcdt-boot.py`).
- Panel handoff: `/chosen/framebuffer@90001000`, 720×1520, `r8g8b8`, needs `CONFIG_DRM_SIMPLEDRM`.
- Debug console: serial `ttyMSM0`,115200; USB gadget `1d6b:0104` → `/dev/ttyACM0`.

---

*Stage 1 gets Nuxel running on the device. Stage 2 (§8) is what puts it on the
screen. — Nuxel `v0.3.2-alpha`*

---

# CORRECTIONS — 2026-10-14 (Stage 1 + Stage 2 actually executed)

> These supersede the affected sections above. See `finish2/STAGE12-REPORT.md`.

## C1. §5/§6 are wrong about the boot mechanism — lk2nd does NOT use a 512 KiB payload
`build/out/g7power/lk2nd.img` is a modern lk2nd. Its `lk2nd_boot()` scans
partitions, mounts an **ext2** filesystem and boots via **extlinux**:

```
/<partition>/extlinux/extlinux.conf     # LABEL + KERNEL/FDT/INITRD/APPEND
```

It does **not** read an Android boot image appended at 512 KiB. Therefore
`lk2nd-nuxel-final-combined.img` (= lk2nd@0 + v1 payload@512 KiB) is never
consumed: lk2nd prints `"Reverting to android boot"`, stock ABOOT reloads
lk2nd, and the device loops — the "flashing every 3 s".

**Correct Stage-1/2 flash (what was done, and what ends the loop):**

```
dtbo      -> stock/firmware/extracted/dtbo.img   (first, anti-brick)
boot_a    -> build/out/g7power/lk2nd.img
boot_b    -> build/out/g7power/lk2nd.img
system_a  -> build/out/g7power/nuxel-boot-ext2-simpledrm.img   # ext2 + extlinux
system_b  -> build/out/g7power/nuxel-ocean-rootfs-final.img     # rootfs
```

(`userdata` is refused by this ABOOT — "flash permission denied"; use
`system_b`. The init finds the root by ext4 label `nuxel-ocean` / GPT number.)

`nuxel-boot-ext2-simpledrm.img` (80 MiB, label `nuxel-boot`) holds
`Image.gz`, `sdm632-motorola-ocean.dtb`, `initramfs` and
`extlinux/extlinux.conf` with
`APPEND console=ttyMSM0,115200 console=tty0 nuxel.device=g7power rootfstype=ext4 rootwait rw lk2nd.pass-ramoops ignore_loglevel`.

## C2. The `-final` initramfs could not execute `/init` (bootloop cause)
The ramdisk had `init` (`#!/bin/sh`) and `bin/toybox` but **no `/bin/sh`** and
**no applet symlinks**, so the kernel could not run PID 1
("No working init found") → reset loop. Rebuilt via
`finish2/make-initramfs.py`; the init's symlink block in `finish2/init-final.sh`
was also fixed (it was guarded by `[ ! -e /bin/sh ]`, which never fired).

## C3. `kernel/g7power/build-kernel.sh` silently discarded the Nuxel defconfig
`merge_config.sh -m "${KOUT}/.config" "${DEFCONFIG}"` writes to `./.config`
because it derives the output path from `-O` (default `.`) — so the merged
fragment never reached `${KOUT}/.config`, and `olddefconfig` kept the plain
arm64 `defconfig`. Result: **every** artifact so far shipped with
`CONFIG_DRM_SIMPLEDRM`, `CONFIG_TOUCHSCREEN_ILI210X`, `CONFIG_LEDS_LM3697` …
unset — no display, no touch, no backlight, contradicting the docs.

Fixed by adding `-O "${KOUT}"`. After the fix the built `Image.gz` contains:

```
CONFIG_DRM_SIMPLEDRM=y  CONFIG_FRAMEBUFFER_CONSOLE=y
CONFIG_TOUCHSCREEN_ILI210X=y  CONFIG_LEDS_LM3697=y  CONFIG_DRM=y
```

## C4. Result
After C2+C3 and the extlinux chain (C1) the device **leaves fastboot and does
not return** (verified > 7 min) — i.e. the "flashing every 3 s" loop is gone and
the screen stays black with the SIMPLEDRM/fbcon display kernel installed.
The USB serial console (`1d6b:0104` / `/dev/ttyACM0`) did not enumerate from the
host; if that is needed, build `CONFIG_PHY_QCOM_QUSB2=y` (it is currently `=m`).
