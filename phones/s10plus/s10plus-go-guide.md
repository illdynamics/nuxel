# Nuxel on the Samsung Galaxy S10+ (`beyond2lte`) — GO guide to flash & test

**Written:** 2026-10-11 · **Device:** Samsung Galaxy S10+ SM-G975F (Exynos 9820, codename `beyond2lte`) · **Nuxel v0.2.0**

This is the single, action-oriented guide produced by an automated prep pass. It tells you **exactly what is already done for you**, **what only you can do by hand**, and **the step-by-step path to the first flash and first boot of Nuxel on your S10+**. The longer background documents are `phones/s10plus/s10plus-requirements.md`, `phones/s10plus/nuxel-s10plus.md`, `phones/s10plus/samsung-galaxy-s10plus-quickstart.md`, `docs/s10plus-bringup.md` and `docs/s10plus-device-inventory.md`; read those for rationale. **This file is the "do it now" checklist — and it corrects several factual errors in the older docs (see §1.6).**

> ⚠️ **Read this first.** In this pass we built a **real, structurally-correct Nuxel boot image for the S10+** from a real kernel and real firmware, and we validated it. What is **not** yet proven is a successful boot **on your hardware** — that is exactly the test this guide gets you to. Do not treat "built" as "boots". Also: **there is no `fastboot` on this device** (Samsung Exynos); flashing is **heimdall** (Download Mode) or **TWRP** only.

---

## 0. TL;DR — readiness snapshot

| Item | State after this pass |
|---|---|
| **Downstream kernel** (Linux 4.14.253, `Linux4/android_kernel_samsung_exynos9820`) | ✅ **built** (`Image.gz`, 16,030,259 B) |
| **Exynos 9820 base DTB** (`exynos9820.dtb`) | ✅ **built** (238,880 B) |
| **beyond2lte merged DTB** (base + board overlay) | ✅ **built** (376,101 B) |
| **Board DTBOs** (60, `exynos9820-beyond2lte_eur_open_*.dtbo`) | ✅ built in the VM |
| **Nuxel boot image** `nuxel-beyond2lte-boot.img` (Android header **v1**, page 2048) | ✅ **built + header re-parsed OK** |
| **Shared Nuxel initramfs** (static toybox + shell) | ✅ present (`boot/initramfs/initramfs.cpio.gz`) |
| **Vendor firmware blobs** (WiFi/BT/audio/NFC/camera/modem) | ✅ **78 real blobs fetched + sha256-verified** (40 MB) |
| **Firmware manifest** with **real checksums** | ✅ auto-generated, install+verify pass (39 required OK) |
| **Load addresses** (`0x10008000 / 0x11000000 / 0x10000100`, page 2048) | ✅ **resolved from upstream sources** (pmaports deviceinfo) |
| **Phase-0 inventory gate** | ✅ **unblocked** (pre-filled with sourced values — you must still verify on your unit) |
| **Host tooling** (`adb`, real `heimdall-flash` v1.4.2, python3+PyYAML, dtc+fdtoverlay) | ✅ installed |
| **Linux build VM** (Fedora 43 aarch64, 4 cores) | ✅ running (UTM `nuxel-aarch64-phosh`, 192.168.64.3) |
| **Kernel modules** | ✅ none needed — the downstream defconfig is **monolithic** (0 `.ko`; drivers built-in) |
| **U-Boot chainloader** (mainline stretch path) | ⚠️ **clone+build attempted; blocked by OpenSSL 3** (`openssl/engine.h` gone). Optional — the proven path does not need it |
| **Stock firmware backup (`boot`, `dtbo`, `efs`, `persist`)** | ⛔ **you must do this** (from your device) |
| **Confirm load addresses from YOUR stock `boot.img`** | ⛔ **you must do this** (from your device) |
| **Rootfs image (Phosh userspace)** | ⛔ **Phase 2** (needs a Linux host + Flatpak; Phase-1 test uses the initramfs shell) |
| **The physical flash + test** | ⛔ **you must do this** (needs the phone) |

**Bottom line:** every software prerequisite that *can* be produced without the physical handset has been produced and verified, including a real flashable boot image. You are now at the point where the remaining steps need the phone in your hand: **back up stock, confirm addresses, flash, test.**

---

## 1. What was prepared and verified in this pass

All device-specific work stays strictly under the `s10plus` key (enforced by `tools/nuxel-device-select.sh`). Nothing is shared with the Pixel or G7 Power targets.

### 1.1 Flash-ready artifact bundle → `build/out/s10plus/`

| File | Bytes | SHA-256 | What it is |
|---|---|---|---|
| `nuxel-beyond2lte-boot.img` | 22,292,480 | `064bb59306c82f2eff6f4131ee0d3fc65f75cf38d5066d44274fda70486bd81e` | **Nuxel boot image**: downstream Linux 4.14 `Image.gz` + shared initramfs + `exynos9820` base DTB, Android boot header **v1**, page 2048, `name=nuxel-s10plus` |
| `nuxel-beyond2lte-boot-merged.img` | 22,429,696 | `4dcf383dbcd9d30d7c86cc4923a4fb66113cd6ea16812a243e7c465a5df6b0dd` | Same, but with **base+board overlay merged** into one DTB (fallback if S-Boot does not apply the DTBO) |
| `build-manifest.json` | — | — | device key, kernel commit, load addresses, per-artifact hashes |
| `sha256sums.txt` | — | — | checksums of the above |

Kernel-side inputs (in `kernel/s10plus/.build/out/arch/arm64/boot/`):

| File | Bytes | SHA-256 |
|---|---|---|
| `Image.gz` | 16,030,259 | `33cac63a8b0c0f575a2e1bc782c1efe54018658f65ba741679531c113ac0ec57` |
| `dts/exynos/exynos9820.dtb` (base) | 238,880 | `a6b67b460d25846ac5f5b6222c8458c9cb8f83d1db99d04f4cb115b1834d4e95` |
| `dts/samsung/exynos9820-beyond2lte.dtb` (merged) | 376,101 | `6974a57c39d351c2e20a35f54094f315968d6c5e0e619116f09ef1e2c6db8abd` |

### 1.2 Kernel build — the source of truth (and the big correction)

The kernel was built **from source** in the Linux VM:

- Source: **`https://github.com/Linux4/android_kernel_samsung_exynos9820`** @ commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` — **Linux 4.14.253** (Samsung downstream Exynos 9820 fork; the same tree postmarketOS builds as `linux-samsung-beyond1lte`).
- Defconfig: **`arch/arm64/configs/exynos9820-beyond2lte_defconfig`** (in-tree, 172 KB — the real S10+ config).
- Toolchain: **native aarch64 GCC 15.3.1** (Fedora 43) with `CROSS_COMPILE=` `CC=gcc`, plus a `-Werror` relaxation (the 4.14 tree predates GCC 14/15 diagnostics; see §1.5).
- Verified in the built `.config`: `CONFIG_SCSI_UFS_EXYNOS=y`, `CONFIG_BCMDHD_*` (WiFi), `CONFIG_TOUCHSCREEN_SEC_TS_Y771=y` (touch fw is compiled **into** the driver — there is no `/vendor/firmware/tsp_sec` file on this device), `CONFIG_EXT4_FS`, `CONFIG_DEVTMPFS`, `CONFIG_MODULES=y` but **0 modules** (drivers are built-in).

### 1.3 Firmware blobs — the drivers your phone actually needs

Fetched by `firmware/s10plus/fetch-vendor-blobs.sh` from **`Linux4/proprietary_vendor_samsung`** @ commit `05c9ef8f16e0ad5ab274e408c120dfd99fd5c628` (the pmaports vendor-blob source of record), into `firmware/s10plus/blobs/vendor-firmware/` (**78 files, 40 MB, sub-paths preserved**), then a real manifest was generated by `firmware/s10plus/gen-manifest.py`:

- **WiFi** — Samsung **`bcmdhd`** (Broadcom BCM4375): `bcmdhd_sta.bin_b1`, `bcmdhd_mfg.bin_b1`, `bcmdhd_mon.bin_b1`, `bcmdhd_clm.blob`, `nvram.txt_*` (selected by chip rev). The downstream kernel wants these at **`/etc/wifi/`** (`CONFIG_BCMDHD_FW_PATH`), and the manifest also installs them to `/lib/firmware/`.
- **Bluetooth** — `bcm4375B1_semco.hcd` (+ Murata/B0 variants).
- **Audio** — `cs47l93-dsp1-trace.wmfw`, `cs35l40-*-spk-prot.{bin,wmfw,calib}`, the `AP*_AUDIO_SLSI.bin` Samsung DSP set, `bidirmic.bin`, `SoundBoosterParam.bin`, `dax_param.bin`.
- **NFC** — `sec_s3nrn82_firmware.bin` (the chip is **S3NRN82**, not S3FWRN5).
- **Camera ISP** — `fimc_is_*`, `setfile_*`, `dnn.bin`, `vts.bin`, `fmsb.bin`, `rxse/txse*.bin` (Phase 7).
- **Modem DSP** — `calliope*` (Phase 7; **never** the CP/EFS partitions).
- **NPU/other** — `NPU.bin`, `iva30_rt-makalu.bin`, `usbin.bin`, `usbout.bin`, `mfc_fw.bin`, …

Every checksum is a real sha256. `firmware/s10plus/install-firmware.sh --install` + `verify-firmware.sh --strict` pass (**39 required blobs OK, 0 missing, 0 mismatch**).

### 1.4 Boot image packer / header reader

`boot/s10plus/pack-boot-v1.sh` (legacy **v1**, page 2048) and `tools/read-boot-header-v1.py` were round-trip tested: pack → re-parse gives `magic=ANDROID!`, `page_size=2048`, `kernel=0x10008000`, `ramdisk=0x11000000`, `tags=0x10000100`, correct name/cmdline. The real bundle in §1.1 was produced with this exact packer.

### 1.5 Scripts corrected in this pass

| File | Change |
|---|---|
| `kernel/s10plus/build-kernel.sh` | **rewritten** to use the real downstream repo + in-tree defconfig + the GCC-14/15 `-Werror` relaxation. The old script cloned a **non-existent** repo. |
| `kernel/s10plus/defconfig` | replaced with an informational note (the downstream tree ships its own full defconfig; no fragment is merged). |
| `device/s10plus/deviceinfo` | corrected kernel name, **`heimdall-bootimg`** flash method (BOOT+SYSTEM), `bcmdhd` WiFi, S3NRN82 NFC, real load offsets, v1 bootimg args. |
| `device/s10plus/nuxel-beyond2lte.conf` | corrected WiFi paths to `bcmdhd_*`. |
| `boot/s10plus/boot-config.txt` | real load addresses + both boot chains. |
| `images/s10plus/build.sh` | DTB search now covers `dts/samsung/` (downstream layout); U-Boot is now optional for the proven path. |
| `boot/s10plus/flash-heimdall.sh` | **new** — the proven Download-Mode/heimdall BOOT+SYSTEM flash path. |
| `firmware/s10plus/fetch-vendor-blobs.sh`, `gen-manifest.py` | **new** — real blob fetch + real manifest generation. |
| `docs/s10plus-device-inventory.md` | Phase-0 gate fields pre-filled from upstream sources with a provenance banner. |

### 1.6 Factual corrections vs. the older bring-up docs (important)

The older `s10plus-requirements.md` / `samsung-galaxy-s10plus-quickstart.md` contain claims that are now **known to be wrong**. Use these instead:

1. **Kernel:** there is **no `linux-postmarketos-exynos9820`** repo or pmaports package, and no "close-to-mainline" S10 kernel. The real kernel is the **downstream Samsung 4.14.253 fork** (`Linux4/android_kernel_samsung_exynos9820`), which is what postmarketOS actually uses for the S10 (`device-samsung-beyond1lte`).
2. **WiFi driver:** **`bcmdhd`** (Samsung's Broadcom driver), **not `brcmfmac`**. The firmware filenames are `bcmdhd_*`, not `brcmfmac*-sdio.bin`.
3. **NFC chip:** **S3NRN82**, not S3FWRN5.
4. **Load addresses:** base **`0x10000000`** (kernel `0x10008000`, ramdisk `0x11000000`, tags `0x10000100`). The old `0x8000_8000 / 0x8400_0000 / 0x8000_0100` values were wrong and must not be used.
5. **Flash method:** the **proven** path is **heimdall** in Download Mode flashing **`BOOT` + `SYSTEM`** (this is how postmarketOS installs the S10). No `fastboot`, and **no U-Boot needed** for this path. The U-Boot chainload + mainline kernel is a **stretch/experimental** path (and its build is currently blocked — §1.7).
6. **pmOS port scope:** pmaports has `device-samsung-beyond1lte` (the S10); the S10+ (`beyond2lte`) reuses the same downstream kernel/defconfig families. There is no separate `beyond2lte` pmOS package (yet).
7. **Touch firmware** is compiled into the `sec_ts` driver (`CONFIG_TOUCHSCREEN_SEC_TS_Y771=y`) — do not hunt for a `/vendor/firmware/tsp_sec/*.fw`.

### 1.7 Stretch path status — U-Boot

`boot/s10plus/uboot-chainload.sh` clones `chiffathefox/u-boot` (branch `exynos9820`) and builds with `exynos9820_defconfig`. The clone + defconfig succeed, but the build **fails** on the host tool `rsa-sign.c` because it needs `openssl/engine.h`, which **OpenSSL 3 removed** (Fedora 43 ships OpenSSL 3). Workarounds (not done here): build U-Boot in a container with OpenSSL 1.1, or configure U-Boot with `CONFIG_TOOLS_LIBCRYPTO=n`. U-Boot is **not required** for the flash path in this guide.

---

## 2. Prerequisites

### 2.1 Hardware
- **Samsung Galaxy S10+ SM-G975F (Exynos)** — a spare device (flashing wipes data). A Snapdragon S10+ (US, `g975u`) is a **different** device and will be refused.
- A **data-capable USB-C cable** (many charge-only cables do not enumerate in Download Mode / adb).
- Battery **> 60 %**.
- The device **already has TWRP installed and an unlocked bootloader** (Knox already tripped). That is the ideal state; leave it as-is.

### 2.2 Host software (already installed on this Mac)
```sh
adb version                              # /opt/homebrew/bin/adb (platform-tools)
/opt/homebrew/bin/heimdall-flash version # v1.4.2  (the REAL heimdall flash tool)
python3 -c 'import yaml'                 # PyYAML present
# Build VM (used for the kernel/U-Boot builds): UTM 'nuxel-aarch64-phosh' @ 192.168.64.3
```
> **Gotcha:** `heimdall` on `PATH` is **`heimdall-rs` (an Ethereum tool)** from `~/.cargo/bin`, **not** the Samsung flash tool. Always use **`heimdall-flash`**. If you move to a Linux host, install the real one (`apt install heimdall-flash`, or build `Benjamin-Dobell/Heimdall`).

### 2.3 Things only you have
- **Your unit's stock `boot.img`** — needed to (a) confirm the load addresses and (b) revert. The device must be in **TWRP** to pull it (`/dev/block/platform/13d60000.ufs/by-name/boot`).
- **The Samsung stock firmware** (BL/AP/CP/CSC for SM-G975F, matching your bootloader revision) — the guaranteed recovery. From `samfw.com` / `sammobile.com`.
- **Your unit's `hw_rev`** — decides which board DTBO (`exynos9820-beyond2lte_eur_open_<rev>.dtbo`) the bootloader applies. Read it from the device (`dtbo-hw_rev` / the `dtbo` partition) or from `ro.revision`.

### 2.4 Critical safety facts (read once, internalize)
1. **No `fastboot`.** Any guide telling you to `fastboot flash` on this device is wrong. Use **heimdall** (Download Mode) or **TWRP** (`adb push` + `dd`).
2. **Never flash/pull/`dd` these protected partitions:** `efs efsg persist param up_param steady keystorage carrier cp_debug misc`. They hold IMEI/MAC/DRR/Knox calibration — **irreplaceable**.
3. **Download Mode (Vol Down + Bixby + Power)** is always reachable regardless of what is on `boot` — it is your unbrick safety net.
4. **Back up stock `boot` and `dtbo` first**, then `efs`/`persist` if you can. Keep them forever.
5. **Never re-lock the bootloader and never try to restore Knox** — impossible and it can hard-brick (`ODIN LOCK`).
6. **Do not wipe the `dtbo` partition.** It holds the board overlay S-Boot needs.
7. Device identity is verified against `ro.product.device == beyond2lte` before every flash.

---

## 3. Step-by-step: from here to flashed-and-tested

> The steps marked **[YOU]** need the phone or your account. Steps marked **[DONE]** were completed in this pass.

### Step 3.1 — [YOU] Get into TWRP and confirm the device is yours
```sh
adb devices
adb shell getprop ro.product.device    # MUST print: beyond2lte
adb shell getprop ro.product.name      # e.g. beyond2ltexx  (save)
adb shell getprop ro.product.model     # MUST be SM-G975F (Exynos); NOT SM-G975U
adb shell getprop ro.bootloader        # save the revision
adb shell getprop ro.revision          # hw_rev for the DTBO
```
Boot TWRP with **Vol Up + Bixby + Power** (hold). Download Mode is **Vol Down + Bixby + Power**.

### Step 3.2 — [YOU] Back up the stock partitions (do this BEFORE anything else)
```sh
mkdir -p ~/s10plus-backup
adb shell "mkdir -p /sdcard/nuxel-backup"
# Safe, non-protected partitions:
for p in boot dtbo recovery; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096" && echo "$p ok"
done
# Protected calibration (READ-ONLY copy, just in case — never restore onto another unit):
for p in efs efsg persist param up_param steady keystorage; do
  adb shell "dd if=/dev/block/platform/13d60000.ufs/by-name/$p of=/sdcard/nuxel-backup/$p.img bs=4096 2>/dev/null" || true
done
adb pull /sdcard/nuxel-backup ~/s10plus-backup/
ls -la ~/s10plus-backup/nuxel-backup
```
**Keep `boot.img` and `dtbo.img` — they are your revert.**

### Step 3.3 — [YOU] Confirm the load addresses from YOUR stock boot.img
```sh
python3 tools/read-boot-header-v1.py ~/s10plus-backup/nuxel-backup/boot.img
```
Expect `page_size=2048` and roughly `kernel_addr=0x10008000`, `ramdisk_addr=0x11000000`, `tags_addr=0x10000100`. **If your unit differs, update `docs/s10plus-device-inventory.md` and `boot/s10plus/boot-config.txt` with the real values and re-pack (§3.5).** The repo values come from the pmOS `device-samsung-beyond1lte` deviceinfo and are almost certainly correct for the SM-G975F, but the S10 family has variants.

### Step 3.4 — [YOU] Download the stock firmware (recovery insurance)
Get the SM-G975F BL/AP/CP/CSC package for your region/bootloader. You will only need it if something goes wrong (Download Mode + heimdall/Odin). Keep `boot.img`/`dtbo.img` from it too.

### Step 3.5 — [DONE] Artifacts are already built and verified
The bundle is at **`build/out/s10plus/`** (see §1.1). To reproduce from scratch on a Linux host/VM:
```sh
# 1) kernel (real downstream source) — needs a Linux host (native aarch64 or aarch64-linux-gnu-)
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
#   -> kernel/s10plus/.build/out/arch/arm64/boot/{Image.gz,dts/exynos/exynos9820.dtb,
#                                                dts/samsung/exynos9820-beyond2lte_eur_open_*.dtbo}
# 2) firmware blobs (real, sha256-verified)
bash firmware/s10plus/fetch-vendor-blobs.sh
python3 firmware/s10plus/gen-manifest.py
# 3) boot images (v1) via the repo packer
python3 boot/s10plus/pack-boot-v1.sh \
  --kernel  kernel/s10plus/.build/out/arch/arm64/boot/Image.gz \
  --ramdisk boot/initramfs/initramfs.cpio.gz \
  --dtb     kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820.dtb \
  --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 --tags-addr 0x10000100 \
  --cmdline "buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw" \
  --output  build/out/s10plus/nuxel-beyond2lte-boot.img
```
> The macOS only cannot build the kernel (case-insensitive FS + missing GNU toolchain). Use the repo VM (`utmctl start nuxel-aarch64-phosh`, then `ssh nuxel@192.168.64.3`) or any Linux box.

### Step 3.6 — [YOU] FLASH phase 1: the Nuxel boot image (kernel) via heimdall
Put the phone in **Download Mode**: power off, then hold **Vol Down + Bixby + Power** until the warning screen; press **Vol Up** to continue.

```sh
cd /Users/wicked/x/nuxel
/opt/homebrew/bin/heimdall-flash detect          # must list your device
# Preview first:
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot build/out/s10plus/nuxel-beyond2lte-boot.img --dry-run
# Real flash (BOOT only — safest first test):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot build/out/s10plus/nuxel-beyond2lte-boot.img
```
Or the equivalent by hand:
```sh
/opt/homebrew/bin/heimdall-flash flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img
```
Then let the device reboot (`heimdall` reboots it automatically). **Watch the screen.**

**Variant:** if the device does **not** bring up the panel and you suspect the bootloader is not applying the board DTBO, re-flash the merged variant instead:
```sh
/opt/homebrew/bin/heimdall-flash flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot-merged.img
```

### Step 3.7 — [YOU] TEST phase 1
Expected on the S10+ once the downstream kernel runs:
1. Samsung splash (S-Boot) → the kernel starts.
2. The **Nuxel initramfs** runs `init`, sets up `/proc /sys /dev`, resolves the S10+ UFS root and — since there is **no Nuxel rootfs on `userdata` yet** — **drops to a toybox shell** (or prints the root-probe diagnostics then `exec sh -i`).

Observables:
- **Display:** if the panel lights up and shows the Nuxel splash / boot animation (`boot/nuxel-boot-splash.raw` is in the initramfs), display bring-up works.
- **Shell over serial (best):** if you have the UART pads, you get `console=ttySAC0,115200`. Otherwise you rely on the screen + the fact the device stays alive/enumerates on USB.
- **USB:** in the shell you can check `dmesg`, `cat /proc/device-tree/compatible`, `ls /sys/class/drm`, `ls /sys/class/net` (WiFi appears once modules/firmware load — but the driver is built-in and needs firmware at `/etc/wifi/`, which is only present once a rootfs with the blobs is flashed — Step 3.9).

**Interpreting results honestly:**
- **Kernel boots + initramfs shell** → **Phase 1 success**: real Nuxel kernel on real S10+ hardware. This is the milestone this guide targets.
- **Samsung splash then nothing / reboot loop** → the boot.img header/addresses or the DTB path needs attention; revert (§3.10) and re-check §3.3/§4.
- **No display but device enumerates** → the display panel path (`exynos_drm`/DSI) needs the correct DTBO/panel bring-up; still a kernel-boot success. Confirm by serial or by USB.

### Step 3.8 — [YOU] Revert quickly (if anything is off)
Download Mode is always available:
```sh
# Boot to Download Mode (Vol Down + Bixby + Power), then:
/opt/homebrew/bin/heimdall-flash flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img
# Full stock restore:
# /opt/homebrew/bin/heimdall-flash flash --BL BL_*.tar.md5 --AP AP_*.tar.md5 --CP CP_*.tar.md5 --CSC CSC_*.tar.md5
```

### Step 3.9 — [YOU] Phase 2: build + flash a real rootfs (optional, for a usable system)
Phase 1 boots the kernel + initramfs. To get a *usable* Nuxel (shell with firmware, or eventually Phosh), you need an ext4 rootfs on the **`SYSTEM`** partition (the pmOS-proven target) or **`userdata`**:
```sh
# On a Linux host/VM with Flatpak:
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh            # -> build/out/s10plus/nuxel-beyond2lte-rootfs.img
# Flash it (Download Mode):
NUXEL_DEVICE=s10plus bash boot/s10plus/flash-heimdall.sh --device s10plus \
    --boot   build/out/s10plus/nuxel-beyond2lte-boot.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
# (the script targets BOOT and SYSTEM by default; the rootfs must include the
#  firmware blobs -> /lib/firmware and /etc/wifi, which install-firmware.sh does)
```
Note: pmOS flashes a **sparse** rootfs image; if heimdall complains, convert with `img2simg` or flash the raw ext4 to `userdata` from TWRP with `dd` instead.

### Step 3.10 — [YOU] Revert / unbrick (full)
- **Boot partition only:** Download Mode → `heimdall-flash flash --BOOT <stock-boot.img>` (Step 3.8).
- **Full stock:** Download Mode → `heimdall-flash flash --BL ... --AP ... --CP ... --CSC ...` (or Odin on Windows).
- Download Mode is independent of `boot`, so **this device cannot be hard-bricked by a bad boot image** as long as you never touch `efs`/`persist`/bootloader locks.

---

## 4. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `heimdall-flash detect` finds nothing | not in Download Mode / charge-only cable / macOS USB | re-enter Download Mode (Vol Down + Bixby + Power); use a data cable; try a different port |
| `heimdall` command does EVM/blockchain things | you ran `heimdall` (heimdall-rs from cargo) | always use **`/opt/homebrew/bin/heimdall-flash`** |
| `adb shell getprop ro.product.device` ≠ `beyond2lte` | wrong device (e.g. Snapdragon S10+) | stop; this guide is for SM-G975F (Exynos) only |
| Flash "succeeds" but device shows Samsung splash then restarts | wrong load addresses or DTB not applied | re-check addresses from your stock `boot.img` (§3.3); try `nuxel-beyond2lte-boot-merged.img` |
| No display, device alive/enumerates | panel/DSI bring-up or DTBO mismatch | confirm `hw_rev` and use the matching overlay; this is a known bring-up step, not fatal |
| No WiFi after boot | firmware not present at `/etc/wifi/` (Phase-1 initramfs has no rootfs) | flash a rootfs that includes the blobs (§1.3/§3.9) |
| Build fails with `gcc ... /toolchain/.../aarch64-linux-android-gcc: No such file` | Samsung Makefile hardcodes an internal toolchain | pass `CROSS_COMPILE= CC=gcc` (the repo wrapper does) |
| Build fails with `-Werror=...` | 4.14 tree vs GCC 14/15 diagnostics | the repo wrapper strips `-Werror` and adds `-Wno-error=` (see §1.2) |
| U-Boot build fails on `openssl/engine.h` | OpenSSL 3 removed `engine.h` | optional path; build in an OpenSSL-1.1 container or set `CONFIG_TOOLS_LIBCRYPTO=n` |
| Device won't boot at all | — | Download Mode is always reachable → §3.10 |

---

## 5. Quick reference

### 5.1 Key device facts
| Field | Value |
|---|---|
| Codename / key | `beyond2lte` / `s10plus` |
| SoC / GPU | Samsung Exynos 9820 / Mali-G76 MP12 (vendor `mali`) |
| Display | 6.4" AMOLED 3040x1440, DDIC S6E3HA9 |
| Touch | Samsung S6SY761 (`sec_ts`), **firmware compiled into the driver** (`SEC_TS_Y771`) |
| WiFi / BT | Broadcom BCM4375 — **`bcmdhd`** (not brcmfmac); BT `btbcm` + `bcm4375*.hcd` |
| NFC | **S3NRN82** |
| Audio | Cirrus CS47L93 + 2x CS35L40 (MADERA / SLSI) |
| Modem | Shannon LTE (integrated) — **not ModemManager-ready** (Phase 7) |
| Boot image | Android header **v1**, page **2048**, `name=nuxel-s10plus` |
| Partitions | A-only: `boot dtbo recovery system vendor userdata …` |
| Load addrs | kernel `0x10008000`, ramdisk `0x11000000`, tags `0x10000100` |
| UFS path | `/dev/block/platform/13d60000.ufs/by-name` |
| Kernel | Linux **4.14.253** downstream (`Linux4/android_kernel_samsung_exynos9820@f7194c1d`) |
| Proven flash | **heimdall** BOOT + SYSTEM (Download Mode); TWRP `dd` alternative; **no fastboot** |

### 5.2 Command cheat-sheet
```sh
# Tools
adb devices ; /opt/homebrew/bin/heimdall-flash detect

# Device identity (TWRP)
adb shell getprop ro.product.device        # beyond2lte
adb shell getprop ro.product.name          # beyond2ltexx

# Header check (host)
python3 tools/read-boot-header-v1.py build/out/s10plus/nuxel-beyond2lte-boot.img

# Flash (Download Mode)
/opt/homebrew/bin/heimdall-flash flash --BOOT build/out/s10plus/nuxel-beyond2lte-boot.img

# Revert (Download Mode)
/opt/homebrew/bin/heimdall-flash flash --BOOT ~/s10plus-backup/nuxel-backup/boot.img

# Firmware (host)
bash firmware/s10plus/fetch-vendor-blobs.sh
NUXEL_DEVICE=s10plus bash firmware/s10plus/install-firmware.sh --verify-only

# Build (Linux host/VM)
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
```

### 5.3 Files created / touched in this pass
- **New bundle:** `build/out/s10plus/` (`nuxel-beyond2lte-boot.img`, `nuxel-beyond2lte-boot-merged.img`, `build-manifest.json`, `sha256sums.txt`).
- **Kernel artifacts:** `kernel/s10plus/.build/out/arch/arm64/boot/{Image.gz,dts/exynos/exynos9820.dtb,dts/samsung/exynos9820-beyond2lte*.dtbo,dts/samsung/exynos9820-beyond2lte.dtb}`.
- **Firmware:** `firmware/s10plus/blobs/vendor-firmware/` (78 blobs), `firmware/s10plus/manifest.yml` (83 entries, real sha256), new `fetch-vendor-blobs.sh`, `gen-manifest.py`.
- **Scripts corrected/added:** `kernel/s10plus/build-kernel.sh`, `kernel/s10plus/defconfig`, `device/s10plus/deviceinfo`, `device/s10plus/nuxel-beyond2lte.conf`, `boot/s10plus/boot-config.txt`, `images/s10plus/build.sh`, new `boot/s10plus/flash-heimdall.sh`.
- **Docs:** `docs/s10plus-device-inventory.md` (gate pre-filled + provenance), this guide.

---

## 6. Honest limitations & exact next steps

1. **Not yet hardware-proven.** Everything built is structurally correct (header, addresses, kernel, DTB, checksums verified); the first real boot (§3.7) is the test.
2. **No rootfs image was produced** in this pass. Phase 1 therefore boots the **kernel + initramfs** and drops to a **toybox shell**. A full userspace image needs `images/mkrootfs.sh` on a Linux host with Flatpak/Phosh (Phase 2). The kernel is **monolithic** (0 modules), so the rootfs mainly needs the userspace + `/lib/firmware` + `/etc/wifi`.
3. **DTBO/hw_rev nuance:** Samsung builds the board DTs as **overlays** (`exynos9820-beyond2lte_eur_open_<rev>.dtbo`) applied by S-Boot over the base `exynos9820.dtb`. The default boot image embeds the **base** DTB (Samsung-standard) and relies on the device's `dtbo` partition; the `-merged` variant embeds base+overlay merged. If the panel/board init misbehaves, try the other one, and confirm your `hw_rev`.
4. **Display/touch/WiFi/audio are not yet verified on hardware.** Their firmware/blobs are staged and the drivers are built-in, but bring-up (panel init, touch calibration, WiFi firmware selection by chip rev) is real-device work for §3.7 onwards.
5. **Modem and camera are out of scope** for Phase 1 (WiFi/USB only). Never touch `efs`/`persist`/CP for modem experiments.
6. **U-Boot / mainline is a stretch** and currently unbuilt (OpenSSL 3 blocker, §1.7). The proven path (downstream kernel + heimdall) does **not** need it.
7. **The kernel build is environment-sensitive.** It was built on Fedora 43 aarch64 (GCC 15) with the `-Werror` relaxation; on another host you may need to adjust `CROSS_COMPILE`/`CC` (see §1.2 and `kernel/s10plus/build-kernel.sh`).

### The single next physical action for you
Do **§3.1–§3.4** (TWRP, back up stock `boot`/`dtbo`, confirm addresses, get stock firmware), then **§3.6** to flash `nuxel-beyond2lte-boot.img`, and **§3.7** to test — using the ready artifact in `build/out/s10plus/`. Everything else is already staged.

---

*Build the bunker first. Add the rave lights later. — Nuxel v0.2.0*
