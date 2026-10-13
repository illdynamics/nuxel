# Nuxel — Samsung Galaxy S10+ manual flash guide

**Device:** Samsung Galaxy S10+ **SM-G975F** (Exynos 9820, codename `beyond2lte`)
**Nuxel:** v0.2.0 · **Guide written:** 2026-10-13
**Authoritative repo docs:** this file is the "do it now" checklist; background is in
`phones/s10plus/s10plus-go-guide.md`, `docs/s10plus-bringup.md`, `docs/s10plus-device-inventory.md`.

> Read §3 (modes) and §4 (pre-flight backups) before you flash anything.
> On this device there is **no fastboot, ever** — it is Exynos. You flash with
> **heimdall in Download Mode** (primary) or **TWRP `dd`** (alternative).

---

## 0. TL;DR — the shortest safe path

1. **Back up stock** `boot` + `dtbo` from TWRP (your undo button). → §5
2. **Download Mode** (Vol Down + Bixby + Power) → flash the boot image with heimdall. → §6
3. Reboot and watch. It boots the Nuxel kernel + initramfs. → §7
4. Anything wrong? **Download Mode is always reachable** → re-flash stock boot.img. → §9

The one command that actually flashes Nuxel:

```bash
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
```

---

## 1. What you are flashing (and what is ready today)

Nuxel on the S10+ is a **two-phase** bring-up. Be clear about what exists:

| Phase | Artifact | Status | Flashes to |
|---|---|---|---|
| **Phase 1 — kernel + initramfs** (the proven path) | `build/out/s10plus/nuxel-beyond2lte-boot.img` | ✅ **built & verified, ready to flash** | `BOOT` |
| Phase 1 fallback | `build/out/s10plus/nuxel-beyond2lte-boot-merged.img` | ✅ built (base+DTBO merged DTB) | `BOOT` |
| **Phase 2 — userspace rootfs** (Phosh/shell) | `build/out/s10plus/nuxel-beyond2lte-rootfs.img` | ⛔ **NOT built yet** (needs a Linux host) | `SYSTEM` / `userdata` |

**What Phase 1 gets you:** the real downstream Samsung Linux 4.14 kernel boots on the
real S10+ hardware, the Nuxel initramfs runs, and — because there is **no Nuxel rootfs
on the device yet** — it drops to a **toybox shell** (and prints its root-probe
diagnostics). Display/serial/USB bring-up is what you are testing.

**What is NOT proven:** a successful boot *on your specific unit*. "Built" ≠ "boots".
Phase 1 is exactly the test that closes that gap. Phase 2 (a usable system) comes after.

Artifact facts (already validated, header re-parsed OK — Android boot header **v1**, page 2048):

| File | Bytes | SHA-256 |
|---|---|---|
| `nuxel-beyond2lte-boot.img` | 22,292,480 | `064bb59306c82f2eff6f4131ee0d3fc65f75cf38d5066d44274fda70486bd81e` |
| `nuxel-beyond2lte-boot-merged.img` | 22,429,696 | `4dcf383dbcd9d30d7c86cc4923a4fb66113cd6ea16812a243e7c465a5df6b0dd` |

Boot chain used here (do **not** mix): **S-Boot → downstream Linux 4.14 (v1 boot.img) →
heimdall to `BOOT` (+`SYSTEM`)**. U-Boot / mainline is a separate *stretch* path and is
**not** needed and **not** part of this guide.

---

## 2. What you need

**Hardware**
- A **spare** SM-G975F (Exynos) — flashing wipes data. (A Snapdragon US S10+, `g975u`, is a different device; the scripts refuse it.)
- Bootloader **already unlocked** and **TWRP already installed** (Knox fuse already tripped — leave it that way).
- A **USB-C data cable** (charge-only cables do not enumerate in Download Mode).
- Battery **> 60 %**.
- RECOMMENDED: a working **TWRP backup** and your **stock firmware tarball** (below).

**Host software** (present on this host)
- `adb` → `/usr/bin/adb`
- `heimdall` → `/usr/bin/heimdall` (**v2.2.2**, the real Samsung tool)
  - ⚠️ Gotcha: a different program also called `heimdall` exists (`heimdall-rs`, an Ethereum tool, often from `~/.cargo/bin`). Check `heimdall version` prints `vX.Y.Z`. If not, install the real one (`apt install heimdall-flash`, or Benjamin-Dobell/Heimdall).
- `python3` → for `tools/read-boot-header-v1.py`

**Also required (things only you have)**
- **Your unit's stock `boot.img`** and **`dtbo.img`** — pulled from the device in TWRP (§5). This is your revert.
- **Stock SM-G975F firmware** (BL/AP/CP/CSC `.tar.md5`), matching your bootloader revision/region — the guaranteed recovery (§4.4).
- Your unit's **`hw_rev`** — decides which board DTBO S-Boot applies.

---

## 3. MODES — which button combo, and when

The S10+ has exactly **two** special modes you use. Learn these two; ignore every
"fastboot mode" instruction you find online.

| Mode | Button combo | How it looks | Used for |
|---|---|---|---|
| **Normal / Android** | just Power | Samsung logo → OS | day-to-day (not used here) |
| **Download Mode** (Odin mode) | **Vol Down + Bixby + Power**, hold until the warning screen appears, then release and press **Vol Up** to continue | "Warning" screen, then a Download/Odin screen | **heimdall flashing** (this is where you flash Nuxel and where you revert) |
| **TWRP recovery** | **Vol Up + Bixby + Power**, hold until the TWRP logo appears, then release | TWRP touch UI | **backups** (pull stock boot/dtbo), `adb push` + `dd` flashing, sideload |

Notes:
- **Power off first**, then hold the combo. "Power off" = hold **Power ~10 s** until the screen goes black.
- There is **no fastboot mode** on Exynos. No `fastboot flash …`, no `fastboot reboot recovery`.
- **Download Mode is your safety net** — it is independent of whatever is on `boot`, so a bad boot image cannot hard-brick you as long as you never touch `efs`/`persist` and never re-lock.
- **Download Mode** = Odin/heimdall only. **TWRP** = adb (`adb devices` must list it).

Confirm what mode you're in, from the host:
```bash
adb devices            # lists the phone when in TWRP (with USB debugging), nothing in Download Mode
heimdall detect        # lists the phone when in Download Mode, nothing in TWRP
```

---

## 4. Pre-flight checks (host, no device needed)

### 4.1 Verify the artifact you're about to flash
```bash
cd /x/nuxel
sha256sum build/out/s10plus/nuxel-beyond2lte-boot.img
# expect: 064bb59306c82f2eff6f4131ee0d3fc65f75cf38d5066d44274fda70486bd81e
cat build/out/s10plus/sha256sums.txt    # should match
python3 tools/read-boot-header-v1.py build/out/s10plus/nuxel-beyond2lte-boot.img
# expect: magic=ANDROID!, page_size=2048,
#         kernel=0x10008000, ramdisk=0x11000000, tags=0x10000100, name=nuxel-s10plus
```

### 4.2 Know the protected partitions — NEVER flash/touch these
```
efs  efsg  persist  param  up_param  steady  keystorage  carrier  cp_debug  misc
```
They hold IMEI / MAC / calibration / Knox data — **irreplaceable**. Also **never wipe
`dtbo`** (S-Boot needs it), and **never re-lock the bootloader or "restore Knox"**
(impossible; `ODIN LOCK` can brick the phone).

### 4.3 Get stock firmware (recovery insurance)
Download the SM-G975F **BL / AP / CP / CSC** package for your exact region + bootloader
revision (e.g. from samfw.com / sammobile.com). Keep it forever. You only need it if
something goes wrong — recover from Download Mode with heimdall (§9).

### 4.4 Critical safety facts (internalize)
1. No fastboot. heimdall (Download Mode) or TWRP only.
2. Back up stock `boot` + `dtbo` **before** flashing (§5.2).
3. Download Mode is always reachable → unbrick safety net.
4. Device must be **`beyond2lte` / SM-G975F**. The flash scripts verify `ro.product.device == beyond2lte` and refuse otherwise.

---

## 5. Step 1 — TWRP: back up stock and confirm the device

### 5.1 Enter TWRP
Power off (hold Power ~10 s), then hold **Vol Up + Bixby + Power** until TWRP appears.
Confirm the host sees it and it is your device:
```bash
adb devices
adb shell getprop ro.product.device    # MUST print: beyond2lte
adb shell getprop ro.product.name      # e.g. beyond2ltexx   (save this)
adb shell getprop ro.product.model     # MUST be SM-G975F (Exynos), NOT SM-G975U
adb shell getprop ro.bootloader        # save the revision
adb shell getprop ro.revision          # this is your hw_rev (DTBO selection)
```

### 5.2 Back up stock partitions (YOUR REVERT — do this first)
```bash
mkdir -p ~/s10plus-backup
adb shell "mkdir -p /sdcard/nuxel-backup"
for p in boot dtbo recovery; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096" && echo "$p ok"
done
# Read-only copies of calibration (keep, but NEVER restore onto another unit):
for p in efs efsg persist param up_param steady keystorage; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096 2>/dev/null" || true
done
adb pull /sdcard/nuxel-backup ~/s10plus-backup/
ls -la ~/s10plus-backup/nuxel-backup
```
**Keep `boot.img` and `dtbo.img`. They are how you go back to stock.**

### 5.3 Confirm the boot load addresses from YOUR stock `boot.img`
```bash
python3 tools/read-boot-header-v1.py ~/s10plus-backup/nuxel-backup/boot.img
```
Expect `page_size=2048`, `kernel≈0x10008000`, `ramdisk≈0x11000000`, `tags≈0x10000100`.
If your unit differs, the prebuilt image's header won't match your bootloader → update
`docs/s10plus-device-inventory.md` + `boot/s10plus/boot-config.txt` and **re-pack**
(§10.2). The repo values come from the pmOS S10 deviceinfo and should be correct for
the SM-G975F, but confirm.

---

## 6. Step 2 — Download Mode: flash the Nuxel boot image with heimdall

### 6.1 Enter Download Mode
Power off (hold Power ~10 s until black), then hold **Vol Down + Bixby + Power** until
the warning screen appears → release → press **Vol Up** to continue. You are now in
Download Mode.

### 6.2 Confirm heimdall sees it
```bash
heimdall detect
# expect: "Device detected"
```
If nothing: it's not in Download Mode, or it's a charge-only cable, or try another USB port.

### 6.3 Preview, then flash
```bash
cd /x/nuxel

# Dry-run preview (repo wrapper; prints the exact command, flashes nothing):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot build/out/s10plus/nuxel-beyond2lte-boot.img --dry-run

# REAL FLASH — the actual command (this is what worked and is the proven path):
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
```
heimdall reboots the device automatically at the end. **Watch the screen.**

> The repo wrapper `boot/s10plus/flash-heimdall.sh` runs the same thing plus a
> confirmation prompt and a protected-partition guard. Either is fine; the raw
> `heimdall flash --BOOT …` above is the minimal, proven command.

### 6.4 If it does not bring up the panel (DTB/DTBO fallback)
Samsung builds the board DT as an **overlay** (`exynos9820-beyond2lte_eur_open_<rev>.dtbo`)
that S-Boot applies over the base `exynos9820.dtb`. The default image embeds the **base**
DTB and relies on the device's `dtbo` partition. If display/board init misbehaves, flash
the **merged** variant (base+overlay embedded) instead:

```bash
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot-merged.img
```

---

## 7. Step 3 — Test the boot

Expected sequence on the S10+:
1. Samsung splash (S-Boot) runs.
2. The Nuxel kernel starts; the **Nuxel initramfs** runs `init`, sets up `/proc /sys /dev`,
   resolves the S10+ UFS root, and — with no Nuxel rootfs on `userdata` yet — **drops to a
   toybox shell** (or prints the root-probe diagnostics then `exec sh -i`).

How to read the result honestly:

| What you see | Meaning |
|---|---|
| Display lights up (Nuxel splash) and/or you get the toybox shell | ✅ **Phase 1 success** — real Nuxel kernel on real S10+ hardware |
| Kernel boots + shell, even with a black screen | ✅ kernel boot success; the panel/DSI path (DTBO) is the remaining display bring-up |
| Samsung splash → nothing / reboot loop | ✗ boot.img header/addresses or DTB path issue → revert (§9) and recheck §5.3 / §6.4 |
| Nothing at all, but device enumerates on USB | kernel likely up, display not — confirm over USB/serial |

Useful things to poke at if you have a shell (serial `console=ttySAC0,115200`, or USB):
```sh
cat /proc/device-tree/compatible
ls /sys/class/drm
ls /sys/class/net
dmesg | tail -50
```
(WiFi will not come up in Phase 1: the `bcmdhd` driver is built-in but needs the vendor
firmware at `/etc/wifi` + `/lib/firmware`, which only exists once a rootfs with the blobs
is flashed — Phase 2.)

---

## 8. Step 4 (optional) — Phase 2: build & flash a rootfs

Phase 1 = kernel + initramfs. For a *usable* Nuxel you need an ext4 rootfs on `SYSTEM`
(pmOS-proven target) or `userdata`. **This artifact does not exist yet** — build it on a
Linux host/VM:

```bash
# On a Linux host/VM (needs Flatpak/Phosh; not on the macOS-only path):
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh
#   -> build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

Flash it together with the boot image in **Download Mode**:
```bash
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot   build/out/s10plus/nuxel-beyond2lte-boot.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
# The wrapper targets BOOT + SYSTEM by default.
```

Alternative (rootfs via TWRP, no heimdall): in TWRP,
```bash
adb push build/out/s10plus/nuxel-beyond2lte-rootfs.img /tmp/nuxel-rootfs.img
adb shell "dd if=/tmp/nuxel-rootfs.img of=/dev/block/platform/13d60000.ufs/by-name/userdata bs=4096"
```
Make sure the rootfs you build includes the vendor firmware blobs (`firmware/s10plus/install-firmware.sh`
installs them to `/lib/firmware` and `/etc/wifi`). If heimdall rejects a **sparse** image,
convert with `img2simg` or use the TWRP `dd` path above.

> Full repo flash helper (TWRP `dd` path, with identity check + partition denylist):
> `NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus --uboot <uboot.img> --rootfs <rootfs.img>`
> (U-Boot is the stretch path; you do not need it for the Phase-1/Phase-2 heimdall path.)

---

## 9. Revert / unbrick

Download Mode is always reachable, regardless of what's on `boot`.

**Revert just the boot partition** (fast):
```bash
# Enter Download Mode (Vol Down + Bixby + Power), then:
heimdall flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
# or via the wrapper (device must already be in Download Mode):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh --device s10plus \
    --revert --stock-boot ~/s10plus-backup/nuxel-backup/boot.img
```

**Full stock restore** (guaranteed recovery) — Download Mode + the SM-G975F Odin package:
```bash
heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
```
Use only your region/revision's package. Never a different variant's. (On Windows the
equivalent is Odin.)

**Re-flash TWRP** (if you lose it): TWRP → Advanced → ADB Sideload → Swipe to start →
`adb sideload twrp-beyond2lte.zip`.

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `heimdall detect` finds nothing (in Download Mode) | charge-only cable / USB port / not fully in Download Mode | re-enter Download Mode; data cable; different port |
| `heimdall` does EVM/blockchain things | you ran `heimdall-rs`, not the Samsung tool | use the real tool (`heimdall version` → `vX.Y.Z`) |
| `adb getprop ro.product.device` ≠ `beyond2lte` | wrong device (e.g. Snapdragon S10+) | stop; this guide is SM-G975F (Exynos) only |
| Flash "succeeds", then Samsung splash + restart | wrong load addresses or DTB not applied | recheck §5.3 from your stock boot.img; try `nuxel-beyond2lte-boot-merged.img` (§6.4) |
| No display, but device alive/enumerates | panel/DSI or DTBO `hw_rev` mismatch | confirm `hw_rev`; try the merged image; this is a known bring-up step, not fatal |
| No WiFi after boot | firmware not at `/etc/wifi` (Phase-1 has no rootfs) | flash a rootfs that includes the blobs (§8) |
| `heimdall` "Protocol initialisation failed" | flaky cable/port, or device not settled in Download Mode | re-enter Download Mode, re-plug, retry; try a different cable/port |
| Device won't boot at all | — | Download Mode is always reachable → §9 |

Static facts (from the repo): UFS by-name path is
`/dev/block/platform/13d60000.ufs/by-name`; partitions are **A-only** (no A/B slots);
kernel is downstream **Linux 4.14.253**; WiFi driver is `bcmdhd`; NFC is S3NRN82.

---

## 11. Command cheat-sheet

```bash
# Tools / modes (from the host)
adb devices                                  # TWRP visible
heimdall detect                              # Download Mode visible
heimdall version                             # must print vX.Y.Z (not heimdall-rs)

# Access combos (power off first)
#   Download Mode : Vol Down + Bixby + Power  (hold to warning, then Vol Up)
#   TWRP          : Vol Up   + Bixby + Power  (hold to TWRP logo)

# Device identity (TWRP)
adb shell getprop ro.product.device          # beyond2lte
adb shell getprop ro.product.name            # beyond2ltexx
adb shell getprop ro.revision                # hw_rev

# Verify image (host)
sha256sum build/out/s10plus/nuxel-beyond2lte-boot.img
python3 tools/read-boot-header-v1.py build/out/s10plus/nuxel-beyond2lte-boot.img

# FLASH (Download Mode)
heimdall flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img

# REVERT (Download Mode)
heimdall flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
```

### 11.1 Rebuild the boot image (only if you change addresses/DTB — needs a Linux host/VM)
```bash
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone        # -> Image.gz + dtbs
bash firmware/s10plus/fetch-vendor-blobs.sh && python3 firmware/s10plus/gen-manifest.py
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh                        # -> build/out/s10plus/*
```
Or pack by hand with the repo packer:
```bash
python3 boot/s10plus/pack-boot-v1.sh \
  --kernel  kernel/s10plus/.build/out/arch/arm64/boot/Image.gz \
  --ramdisk boot/initramfs/initramfs.cpio.gz \
  --dtb     kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820.dtb \
  --addresses-from-device ~/s10plus-backup/nuxel-backup/boot.img \
  --cmdline "buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw" \
  --output  build/out/s10plus/nuxel-beyond2lte-boot.img
```

---

*Build the bunker first. Add the rave lights later. — Nuxel v0.2.0*
