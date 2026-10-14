# Nuxel — Samsung Galaxy S10+ (`beyond2lte`) — CURRENT flash guide

**Device:** Samsung Galaxy S10+ **SM-G975F** (Exynos 9820), codename **`beyond2lte`**, A-only UFS
**Host:** this machine (Fedora 43, Linux 6.17) · S10+ on USB-C in **Download Mode**
**Written:** 2026-10-14 · **Nuxel build:** `v0.3.3-alpha`
**Scope:** finish the flash **from the live state of this unit right now** until Nuxel
boots on it, and get a real **display**.

> This supersedes `s10plus-flash-guide.md` (that is the "from a stock phone" doc).
> **This** file is the "here is exactly where we are and what is left" doc, written
> from a live inspection of this unit and this host on 2026-10-14.

---

## 0. Verdict first (read this, then work top-to-bottom)

- **Bootloader: unlocked**, Knox already tripped. No action — never re-lock.
- **The boot images are already built and hash-verified.** You do **not** need to
  rebuild the kernel to finish this.
- **The rootfs image does NOT exist yet.** `build/out/s10plus/` contains **only**
  the two boot images — there is **no `nuxel-beyond2lte-rootfs.img`**.
  → **Answer to "can I use the boot and rootfs images from `./build/out/s10plus`?":
  the boot image — yes; the rootfs image — no, it has not been built. You must
  build it first (§5, Step A).**
- **BOOT was already flashed once** in an earlier session with
  `nuxel-beyond2lte-boot.img` (see `heim.md`). But with **no rootfs on `userdata`
  to mount**, the initramfs cannot find a valid root, prints
  `NUXXEL PANIC: root mount failed`, and (with no serial console) **reboots after
  ~60 s** → the phone just boots-loops at the Samsung splash. Nothing usable came
  of it, and there is nothing valuable to preserve on the phone.
- **Nothing usable is on the phone yet.** The remaining work is: **build the
  rootfs (§5)** → **flash BOOT + rootfs together (§6)** → **boot test (§7)** →
  **display (§8)**.
- ⚠️ **Right now `heimdall` can see the device but the protocol handshake FAILS**
  (`Protocol initialisation failed!`). You must **re-enter Download Mode** before
  flashing (§6.1). `heimdall detect` alone is not enough.

**You are here → Step A (§5).**

---

## 1. Live device + host state (verified just now, 2026-10-14)

```
lsusb          -> Bus 002 Device 004: ID 04e8:685d Samsung ... (Download mode)   # the S10+
                  (no Motorola on USB this time — safe)
adb devices    -> (empty — not in TWRP, no Android USB debugging)
heimdall version -> v2.2.2                        # the REAL Samsung tool, correct
heimdall detect  -> Device detected               # in Download Mode
heimdall print-pit -> ERROR: Protocol initialisation failed!   # <-- see §6.1
/dev/ttyACM*   -> none (no USB serial console attached)
```

**Host permission reality.** A plain (non-root) `heimdall` in this shell fails with
`libusb ... errno=13 (write access)` on anything past `detect`. The proven,
working way to run heimdall on this host is the **privileged Docker container
`nuxel-heimdall2`** (fedora:43, `--privileged`, `/dev/bus/usb` + `/x/nuxel→/repo`
mounted, host heimdall bound in). Every flash command below runs via:

```bash
docker exec nuxel-heimdall2 heimdall <args...>     # inside: the repo is /repo
```

This is exactly how the earlier successful BOOT flash was done (`heim.md`).

**Artifacts present and verified (`build/out/s10plus/`):**

| File | Bytes | sha256 (verified OK) | DTB inside |
|---|---|---|---|
| `nuxel-beyond2lte-boot.img` | 22 292 480 | `064bb593…bd81e` | base `exynos9820.dtb` (238 880 B) + header v1 |
| `nuxel-beyond2lte-boot-merged.img` | 22 429 696 | `4dcf383d…f6b0dd` | base **+ board overlay merged** (376 101 B) |
| `nuxel-beyond2lte-rootfs.img` | — | — | **MISSING — not built** |

Both boot images are valid Android boot header v1 (page 2048), verified with
`tools/read-boot-header-v1.py`:

```
magic=ANDROID!  page_size=2048  name=nuxel-s10plus
kernel_addr =0x10008000   kernel_size =16030259
ramdisk_addr=0x11000000   ramdisk_size=6018421
tags_addr   =0x10000100
cmdline: buildvariant=userdebug nuxel.device=s10plus \
         root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw
```

⚠️ **Read that cmdline carefully:** the kernel roots from **`userdata`**. So the
rootfs **must** be flashed to the **`USERDATA`** partition (heimdall name
`USERDATA`) — **not** `SYSTEM`. (`boot/s10plus/flash-heimdall.sh` defaults to
`SYSTEM`; you must pass `--partition-rootfs USERDATA`, or use raw heimdall as in §6.)

---

## 2. What is already done vs. what is left

| # | Step | State | Notes |
|---|---|---|---|
| 0 | Bootloader unlocked / Knox tripped | ✅ **done** (prior work) | never re-lock; never restore Knox |
| 1 | Kernel + boot images built & hash-verified | ✅ **done** | `nuxel-beyond2lte-boot.img` (+ `-merged.img`) |
| 2 | BOOT partition flashed once | ✅ **done once** (`heim.md`) | base-DTB image; nothing to boot into (no rootfs) |
| 3 | **Rootfs image built** | ⬜ **NOT DONE** | no `nuxel-beyond2lte-rootfs.img` anywhere |
| 4 | Stock `boot`/`dtbo` backed up (revert) | ⬜ **NOT DONE** | no backup files found on this host |
| 5 | Flash **BOOT + rootfs together** | ⬜ **NOT DONE** | the actual remaining action |
| 6 | Display (panel) bring-up | ⬜ **NOT DONE** | downstream S6E3HA9/DSI — see §8 |

**Resume at Step A (§5).** Steps 0–2 are behind you; 3–6 are ahead.

---

## 3. Safety (short version — full detail in `s10plus-flash-guide.md`)

- **No fastboot, ever** — this is Exynos. `heimdall` in Download Mode (or TWRP `dd`) only.
- **NEVER flash / `dd` / wipe:** `efs efsg persist param up_param steady keystorage
  carrier cp_debug misc` (IMEI/MAC/calibration — irreplaceable).
- **Never overwrite `dtbo`**, never re-lock the bootloader, never touch Knox.
- **Download Mode is your safety net** (independent of `boot`): a bad boot image is
  always recoverable (§9).
- Real **USB data** cable, direct port, battery **> 60 %**, spare unit (data is wiped).

---

## 4. Modes (button combos)

| Mode | How | Host sees |
|---|---|---|
| **Download Mode** | power off (hold Power ~10 s) → hold **Vol Down + Bixby + Power** → warning → press **Vol Up** | `heimdall detect` → "Device detected"; `lsusb` `04e8:…` |
| **TWRP** | power off → hold **Vol Up + Bixby + Power** | `adb devices` lists it |

---

## 5. STEP A — build the missing rootfs image

The rootfs is the one artifact that does not exist. Produce
`build/out/s10plus/nuxel-beyond2lte-rootfs.img` (writable ext4, Phase 1 — no
dm-verity/AVB) from the device-agnostic userspace staging tree.

### 5.1 Build the staging tree

```bash
cd /x/nuxel
NUXEL_INIT=openrc bash images/mkrootfs.sh      # -> build/out/rootfs  (OpenRC = phone target)
```

> **Flatpak caveat (hit on this host just now):** `mkrootfs.sh` wants the
> `org.gnome.Platform//46` Flatpak runtime. On Fedora the `flatpak … --system`
> calls hit polkit and stop at `Authentication is required to update metadata`.
> Run these once, **interactively, with your password**, then re-run the build:
>
> ```bash
> sudo flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
> sudo flatpak install --system org.gnome.Platform//46
> ```
>
> If Flatpak is unavailable the tree **degrades to a minimal skeleton** — that is
> **not** a bootable Nuxel userspace. The initramfs rejects a root that has none
> of `/sbin/init`, `/init`, `/bin/sh` (`=== NUXXEL PANIC: invalid root ===`, §7).

### 5.2 Add the device overlays (what `images/s10plus/build.sh` would add)

```bash
S=/x/nuxel/build/out/rootfs
mkdir -p "$S/etc/nuxel/device/s10plus" "$S/etc/udev/rules.d"
cp -a configs/s10plus/.                       "$S/etc/nuxel/device/s10plus/"
cp -a device/s10plus/90-nuxel-beyond2lte.rules "$S/etc/udev/rules.d/"
cp -a device/s10plus/nuxel-beyond2lte.conf    "$S/etc/nuxel/"
# Kernel modules (only if present):
[ -d kernel/s10plus/.build/out/lib/modules ] && \
  { mkdir -p "$S/lib/modules"; cp -a kernel/s10plus/.build/out/lib/modules/. "$S/lib/modules/"; }
# Vendor firmware blobs (WiFi/BT/panel — only if you have pulled them, §8.3):
[ -d firmware/s10plus/blobs ] && \
  NUXEL_DEVICE=s10plus bash firmware/s10plus/install-firmware.sh \
      --install --force-pending --rootfs-staging "$S" || true
```

### 5.3 Bake the ext4 image (mke2fs + fakeroot are installed here)

```bash
cd /x/nuxel
SIZE_M=2048    # must be <= the USERDATA partition size; content + slack
fakeroot sh -c '
  chown -R 0:0 /x/nuxel/build/out/rootfs
  exec mke2fs -q -t ext4 -L nuxel-beyond2lte -d /x/nuxel/build/out/rootfs \
       /x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs.img '"${SIZE_M}"'M'
e2fsck -fy build/out/s10plus/nuxel-beyond2lte-rootfs.img >/dev/null 2>&1 || true
ls -la build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

**Alternative (the "official" path).** `images/s10plus/build.sh` does all of the
above automatically — but it **aborts early** without a built kernel
(`kernel/s10plus/.build/out/arch/arm64/boot/Image.gz` + a `*beyond2lte*.dtb`) and
a cross toolchain. Neither is present here (the `.build` tree is empty and
`aarch64-linux-gnu-gcc` is not installed), so re-running it would first require
`kernel/s10plus/build-kernel.sh --clone` (heavy). **You do not need to rebuild
the kernel** — the boot image already exists; do the manual bake above.

### 5.4 Sanity-check the rootfs before flashing

```bash
mkdir -p /tmp/rfs && sudo mount -o loop,ro build/out/s10plus/nuxel-beyond2lte-rootfs.img /tmp/rfs
ls /tmp/rfs            # expect sbin/ or init or bin/sh to exist
sudo umount /tmp/rfs
```

---

## 6. STEP B — flash BOOT + rootfs with heimdall

### 6.1 Re-enter Download Mode (REQUIRED right now)

`heimdall` currently reports **`Protocol initialisation failed!`** even though
`detect` works. That handshake failure means you **cannot flash yet**. Fix it by
re-entering Download Mode:

1. Unplug USB.
2. Power off: hold **Power ~10 s** until the screen goes black.
3. Hold **Vol Down + Bixby + Power** until the warning screen appears.
4. Release, press **Vol Up** to continue into Download Mode.
5. Re-plug the USB-C **data** cable (direct port, no hub).

### 6.2 Confirm heimdall sees it (from the container)

```bash
docker exec nuxel-heimdall2 heimdall detect          # -> "Device detected"
# optional sanity:
docker exec nuxel-heimdall2 heimdall print-pit --no-reboot | head -40
```
Nothing? Re-do §6.1; try another cable/port. Same for another
`Protocol initialisation failed!` — re-enter Download Mode and retry.

### 6.3 THE FLASH — BOOT + rootfs in one session

Inside the container the repo is `/repo`, so paths are `/repo/build/out/s10plus/…`:

```bash
docker exec nuxel-heimdall2 heimdall flash \
    --BOOT     /repo/build/out/s10plus/nuxel-beyond2lte-boot.img \
    --USERDATA /repo/build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

Expected output (this is the shape of the earlier successful BOOT flash):

```
Initialising protocol...
Protocol initialisation successful.
Beginning session...
Session begun.
Downloading device's PIT file...
PIT file download successful.
Uploading BOOT
100%
BOOT upload successful
Uploading USERDATA
100%
USERDATA upload successful
Ending session...
Rebooting device...
```

- `heimdall` **reboots the device automatically** at the end. **Watch the screen.**
- **`USERDATA` (not `SYSTEM`)** — because the boot cmdline roots from `userdata`
  (§1). Flashing the rootfs to the wrong partition = kernel boots, root mount fails.
- Flashing `USERDATA` **erases `/data`** on the phone — fine on this spare.
- **Display variant:** for the best shot at the panel, flash the **merged** boot
  image instead of the plain one (§8.2):
  `--BOOT /repo/build/out/s10plus/nuxel-beyond2lte-boot-merged.img`

### 6.4 Repo wrapper (equivalent, for reference)

```bash
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot   build/out/s10plus/nuxel-beyond2lte-boot.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img \
    --partition-rootfs USERDATA            # <-- REQUIRED (defaults to SYSTEM)
```
(Needs root for the USB claim on this host, hence the container is preferred.)

---

## 7. STEP C — test the boot (what you should see)

After `heimdall` reboots the device:

1. **Samsung splash (S-Boot)** — the bootloader loads `boot`, and applies the
   board overlay from the **`dtbo` partition** over the embedded base DTB.
2. **Downstream Linux 4.14 kernel** starts, then the **Nuxel initramfs** `init`
   runs: mounts `/proc /sys /dev`, draws the boot splash to `/dev/fb0` *if a
   framebuffer exists*, parses the cmdline, resolves the root to
   `/dev/block/platform/13d60000.ufs/by-name/userdata`, mounts it ext4, validates
   that it is a real OS, and `switch_root`s into it.
3. **Nuxel userspace (OpenRC)** comes up from the rootfs; Phosh/Wayland appears on
   the panel **if the display path is up** (§8).

Read the result honestly:

| What you see | Meaning |
|---|---|
| Nuxel splash / console / Phosh comes up | ✅ **success** — real Nuxel kernel + rootfs on real S10+ hardware |
| Kernel boots, **black screen**, device stays alive / enumerates | ✅ kernel boot success; **display** is the remaining bring-up → §8 |
| Samsung splash → restart loop | ✗ boot header/addresses or DTB mismatch → revert (§9), recheck §6 |
| Nothing at all, but Download Mode still reachable | keep going — **Download Mode is always reachable**; reflash or revert |
| `=== NUXXEL PANIC: invalid root ===` (only if you have console) | the rootfs image is empty/not a Nuxel OS → §5 (Flatpak caveat) |
| `=== NUXXEL PANIC: no root device ===` | rootfs not on the partition the cmdline names → flash to `USERDATA` (§6) |

**Observability note:** this unit has **no USB serial console** and the initramfs
does **not** create a USB gadget, so without a display your only signal is *does the
device leave Download Mode and stay alive / re-enumerate on USB*. That is expected
and is not itself a failure — but it means **the display is the thing that makes
bring-up visible**, so go to §8.

---

## 8. STEP D — get the display (the panel)

### 8.1 The honest reality

The S10+ panel is **Samsung S6E3HA9 Dynamic AMOLED, 3040×1440**, driven by the
**downstream `exynos_drm`/DSI + `s6e3ha9_beyond2`** path — this is *downstream*,
and per the repo it is **not yet verified on hardware**. Unlike the G7 Power
(where `lk2nd` leaves a `simple-framebuffer` you can `simpledrm`-scan out), **the
Samsung bootloader does not hand the kernel a ready simple-framebuffer** — so the
**panel driver is the only way to pixels**, and it needs (a) a DTB with the panel
node and (b) the panel init firmware.

The initramfs only paints the splash when `/dev/fb0` exists — i.e. **when the
panel/DRM came up**. If you see the navy Nuxel splash (or any output), display
bring-up worked. If it stays black but the device is alive, the panel needs the
work below.

### 8.2 Try the merged-DTB boot image (the most self-contained panel DTB)

The plain `nuxel-beyond2lte-boot.img` embeds **only the base `exynos9820.dtb`** and
relies on **S-Boot applying the board overlay from the `dtbo` partition**. The
**`nuxel-beyond2lte-boot-merged.img`** embeds **base + board-revision overlay
merged**, so the panel/DSI/regulator nodes are guaranteed present in the kernel's
DTB even if the bootloader's overlay application is off:

```bash
# Back to Download Mode (§6.1), then:
docker exec nuxel-heimdall2 heimdall flash \
    --BOOT     /repo/build/out/s10plus/nuxel-beyond2lte-boot-merged.img \
    --USERDATA /repo/build/out/s10plus/nuxel-beyond2lte-rootfs.img
```
(If the merged image fails to boot — unlikely — go back to the plain image.)

### 8.3 If the panel is still dark: get the panel/board firmware from your unit

The repo ships **no vendor blobs** (`firmware/s10plus/blobs/` is a placeholder);
the panel init firmware `s6e3ha9_beyond2_*.bin` name is **UNKNOWN until Phase 0**.
Pull the real blobs **from your own unit** and re-bake the rootfs:

```bash
# Phone in TWRP (Vol Up + Bixby + Power), USB debugging on:
adb shell getprop ro.product.device        # must be: beyond2lte
bash firmware/s10plus/fetch-vendor-blobs.sh       # pulls /vendor/firmware etc. into blobs/
python3 firmware/s10plus/gen-manifest.py
# then re-run Step A (§5) to bake a rootfs that includes the blobs, and re-flash (§6.3).
```

Also confirm the board revision (`adb shell getprop ro.revision`) and make sure it
matches the overlay merged into the boot DTB; a wrong `hw_rev`/DBTO is a classic
black-panel cause.

> **Bottom line for "working display":** flash the **merged** boot image (§8.2) for
> the panel DTB; if the panel still does not light, the remaining work is the
> **panel init firmware + board DTBO** from your own unit (§8.3) — this is real
> bring-up work, not a flashing mistake.

---

## 9. Revert / unbrick

Download Mode is always reachable, so a bad `boot` cannot hard-brick this phone.

⚠️ **There is currently NO stock `boot`/`dtbo` backup on this host.** Before you
flash, download the **SM-G975F BL/AP/CP/CSC** package for your region + bootloader
revision (samfw / sammobile) and/or pull stock `boot`/`dtbo` in TWRP. You only need
it if something goes wrong.

```bash
# Revert just the boot partition (Download Mode):
docker exec nuxel-heimdall2 heimdall flash --BOOT /path/to/stock-boot.img

# Full stock restore (Download Mode) — the guaranteed undo:
docker exec nuxel-heimdall2 heimdall flash \
    --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
# (Windows equivalent: Odin. Use ONLY your region/revision package.)
```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `heimdall detect` OK but **`Protocol initialisation failed!`** | stale Download-Mode session / cable / port | **re-enter Download Mode** (unplug → power off → Vol Down+Bixby+Power → Vol Up), re-plug a **data** cable, retry (§6.1) |
| non-root `heimdall` → `errno=13` / `libusb ... write access` | needs root to claim the interface | run via the privileged container `docker exec nuxel-heimdall2 heimdall …` |
| `heimdall` does EVM/blockchain things | you ran `heimdall-rs`, not the Samsung tool | use `/usr/bin/heimdall` (v2.2.2); `heimdall version` must print `v2.2.2` |
| rootfs flashed but kernel boots then panics | rootfs on the wrong partition | flash the rootfs to **`USERDATA`** (matches `root=…/userdata`) |
| `NUXXEL PANIC: invalid root` | rootfs is an empty/minimal tree (Flatpak step failed) | install `org.gnome.Platform//46` (with your password) and rebuild the rootfs (§5.1) |
| Samsung splash → restart loop | wrong load addresses / DTB not applied | revert (§9); try the merged boot image (§8.2) |
| No display, device alive | panel/DSI + panel firmware not up | §§8.2–8.3 |
| No WiFi/modem/camera after boot | vendor blobs absent from the rootfs (expected for a CI build) | pull your own blobs and re-bake (§8.3) |
| Device won't boot at all | — | Download Mode is always reachable → §9 |

---

## 11. Quick reference — the exact sequence from here

```bash
# ---- STEP A: build the missing rootfs -------------------------------------
cd /x/nuxel
sudo flatpak install --system org.gnome.Platform//46     # once, with your password
NUXEL_INIT=openrc bash images/mkrootfs.sh               # -> build/out/rootfs
S=/x/nuxel/build/out/rootfs
mkdir -p "$S/etc/nuxel/device/s10plus" "$S/etc/udev/rules.d"
cp -a configs/s10plus/. "$S/etc/nuxel/device/s10plus/"
cp -a device/s10plus/90-nuxel-beyond2lte.rules "$S/etc/udev/rules.d/"
cp -a device/s10plus/nuxel-beyond2lte.conf "$S/etc/nuxel/"
fakeroot sh -c 'chown -R 0:0 /x/nuxel/build/out/rootfs; exec mke2fs -q -t ext4 \
    -L nuxel-beyond2lte -d /x/nuxel/build/out/rootfs \
    /x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs.img 2048M'

# ---- STEP B: flash (re-enter Download Mode FIRST) -------------------------
#   phone: power off -> Vol Down + Bixby + Power -> Vol Up
docker exec nuxel-heimdall2 heimdall detect
docker exec nuxel-heimdall2 heimdall flash \
    --BOOT     /repo/build/out/s10plus/nuxel-beyond2lte-boot.img \
    --USERDATA /repo/build/out/s10plus/nuxel-beyond2lte-rootfs.img
#   (display: use nuxel-beyond2lte-boot-merged.img for --BOOT)

# ---- STEP C/D: watch it boot; if black but alive, do the display work (§8) -

# ---- revert (Download Mode) ----------------------------------------------
docker exec nuxel-heimdall2 heimdall flash --BOOT /path/to/stock-boot.img
```

**Modes:** Download Mode = **Vol Down + Bixby + Power** (then Vol Up) ·
TWRP = **Vol Up + Bixby + Power**.

**Artifact → partition:**

| Artifact | Partition | Tool |
|---|---|---|
| `nuxel-beyond2lte-boot.img` / `-merged.img` | `BOOT` | heimdall |
| `nuxel-beyond2lte-rootfs.img` (build it, §5) | `USERDATA` | heimdall |
| stock `boot.img` (revert — not yet backed up) | `BOOT` | heimdall |

Never touch: `efs efsg persist param up_param steady keystorage carrier cp_debug
misc`; never overwrite `dtbo`; never re-lock.

---

*Build the bunker first. Add the rave lights later. — Nuxel v0.3.3-alpha*
