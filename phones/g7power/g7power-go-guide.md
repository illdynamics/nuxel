# Nuxel on the Motorola Moto G7 Power (`ocean`) — GO guide to flash & test

**Written:** 2026-10-11 · **Updated:** 2026-10-12 (touchscreen root-cause + on-hardware stock evidence) · **Device:** Motorola Moto G7 Power XT1955-4 (`ocean`, Snapdragon 632 / SDM632, msm8953 family) · **Nuxel v0.2.0**

This is the single, action-oriented guide produced by the automated prep pass. It tells you **exactly what is already done for you**, **what only you can do by hand**, and **the step-by-step path to the first flash and first boot of Nuxel on your phone**. The longer background documents are `docs/g7power-bringup.md`, `moto-g7-power-quickstart.md`, `g7power-requirements.md` and `phones/g7power/nuxel-g7power.md`; read those for the full rationale. This file is the "do it now" checklist.

---

## 0. TL;DR — readiness snapshot

| Item | State after this pass |
|---|---|
| lk2nd (msm8953 bootloader) image | ✅ **built + verified** (official 23.1 sha256 matches upstream) |
| Mainline kernel `Image.gz` (Linux 6.19, msm8953-mainline) | ✅ **built** from source (native aarch64) |
| Ocean device tree `sdm632-motorola-ocean.dtb` | ✅ **built** from the same tree |
| Nuxel initramfs (static toybox + splash + init) | ✅ **built + verified** |
| Nuxel boot image `nuxel-ocean-boot.img` (Android header **v1**, page 2048) | ✅ **built + header re-parsed OK** |
| Phase-1 ext4 rootfs `nuxel-ocean-rootfs.img` (toybox shell) | ✅ **built** (label `nuxel-ocean`) |
| Load addresses (`0x80008000 / 0x81000000 / 0x80000100`) | ✅ **resolved from authoritative upstream sources** |
| Phase-0 inventory gate | ✅ **unblocked** (pre-filled with sourced values — you must still verify on your unit) |
| Host tooling (`adb`, `fastboot`, EDL unbrick tool, cross/native toolchains) | ✅ installed |
| **Touch driver (Ilitek ILI2117)** | ✅ **root-caused + fixed** — the fragment asked for `CONFIG_TOUCHSCREEN_ILI2117`, which **does not exist**; the real driver is mainline `ili210x` (`CONFIG_TOUCHSCREEN_ILI210X`). Fragment fixed, kernel rebuilt, `nuxel-ocean-boot.img` **repacked** (driver built in, `=y`). Still unproven on hardware. |
| **USB data link to the Mac** | ⛔ **BLOCKER** — the phone currently does **not** enumerate on USB at all (charge-only/broken link). `fastboot` is USB-only. See §0.1. |
| **Bootloader state** | ⚠️ **almost certainly LOCKED** (`ro.boot.verifiedbootstate=green`, `veritymode=enforcing`). Flashing requires unlocking first. |
| **Stock `boot`/`dtbo` backup** | ⛔ **not possible yet** — `/dev/block/*` and `/vendor/firmware` are root-only on this stock build and adb is unrooted. Needs unlock + a booted TWRP, or a stock firmware package. See §3.2. |
| EDL (Qualcomm 9008) unbrick tool | ✅ `edl` v3 installed (`~/.venvs/edl/bin/edl`) |
| **Bootloader unlock (Motorola code)** | ⛔ **you must do this** (needs your IMEI + Motorola portal) |
| **Stock firmware backup (`dtbo.img`, `boot.img`)** | ⛔ **you must do this** (from your device) |
| **The physical flash + test** | ⛔ **you must do this** (needs the phone) |

**Bottom line (updated 2026-10-12):** the touchscreen question is **answered — there is no missing driver**; it was a one-line Kconfig name bug in this repo, and it is now fixed and baked into a freshly repacked boot image. The remaining work is **not** software: it is the **USB link, the bootloader unlock, and the stock backup** — see §0.1. You are *not* able to flash tonight until §0.1 items 1–3 are cleared.

> ⚠️ **Honest statement of what is and isn't proven.** The artifacts above are real and structurally correct (headers, formats, addresses verified; the kernel config was extracted back out of the built image and checked). What is **not** yet proven is a successful boot *on hardware*, and — new as of 2026-10-12 — the touch controller is bound on **stock Android by the out-of-tree vendor driver `ILITEK_TDDI`, not by `ili210x`**. Mainline's ocean DTS was written for `ilitek,ili2117`, so `ili210x` is expected to bind, but treat it as **unproven until first boot**. Do not treat "built" as "boots".

---

## 0.1 Blockers right now (read this before planning the flash)

Verified live against the handset on 2026-10-12 (evidence kept in `g7power/stock-evidence/`). The phone boots stock Android 10 (`QPO30.52-5`, XT1955-4, slot `_b`) and is reachable **only** over network adb (`10.20.30.15:5555`).

| # | Blocker / finding | Evidence | What it blocks | Fix |
|---|---|---|---|---|
| 1 | **No USB data link.** The Mac sees no Motorola USB device at all, and the phone's port negotiates **DFP/host** (`current_mode=dfp`, `data_role=host`, `power_role=source`, `device_manager.connected=false`, `usb_charging=false`, `USB powered: false`) while `adb` works over Wi-Fi. I.e. the phone tries to be a USB *host* and never a peripheral — the Mac can never see it. | `system_profiler SPUSBDataType` (no 22b8 device); `dumpsys-usb.txt`; `dumpsys-battery.txt` | **Everything fastboot**: unlock, flash, EDL, TWRP. | Try another **data** USB-C cable and a direct Mac port (no hub). A charge-only or damaged cable looks exactly like this. |
| 2 | **Bootloader appears LOCKED.** `ro.boot.verifiedbootstate=green`, `ro.boot.veritymode=enforcing`, no `ro.boot.flash.locked`; Motorola `ro.boot.bl_state=2`. | `getprop` dump in `g7power/stock-evidence/boot-props.txt` | `fastboot flash *` is refused on a locked bootloader. | Confirm with `fastboot getvar unlocked` (§3.3) once USB works, then unlock with the Motorola code. **Unlock wipes the device.** |
| 3 | **OEM unlocking is already enabled on the phone** (`sys.oem_unlock_allowed=1`), so the toggle is done — you still need the **unlock code** from Motorola's portal (IMEI-based, manual, can take minutes→hours). | `lock-props.txt` | Unlock. | Get the code now (§3.3) — it is the longest-lead item. |
| 4 | **No root ⇒ no stock backup and no blobs.** `dd` of `/dev/block/bootdevice/by-name/*` and listing `/vendor/firmware` both fail with `Permission denied` for the `shell` user. | `by-name.txt`, `dumpsys`/`ls` attempts | Revert path (`stock-boot.img`, `stock-dtbo.img`) and WiFi/BT/GPU firmware blobs. | After unlock: `fastboot boot twrp-ocean.img` (boot, don't flash) → `adb root` → pull `/vendor/firmware` and `dd` `boot_*`/`dtbo_*`. Or fetch a stock firmware package (§3.5). |
| 5 | **The device is A/B, not A-only.** Partitions are `boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, `slot_suffix=_b`. | `by-name.txt` | The earlier guide's `fastboot flash boot`/`dtbo` and `dd .../by-name/boot` instructions were slot-blind. | Use `fastboot getvar current-slot` and slot-aware backup paths (§3.2, §3.7). |

**Touch status: ✅ no blocker** — see §1.2/§1.7. The touchscreen "gap" was a Nuxel config-name bug, and the boot image has been rebuilt with the correct driver.

---

## 1. What was prepared and verified in this pass

All device-specific work stays strictly under the `g7power` key (`NUXEL_DEVICE=g7power` → dirs `g7power`/`google-pixel-10-xl` separation is enforced by `tools/nuxel-device-select.sh`).

### 1.1 Flash-ready artifact bundle → `build/out/g7power/`

| File | Bytes | SHA-256 | What it is |
|---|---|---|---|
| `nuxel-ocean-boot.img` | 21,645,312 | `05f5adfb07ae54bb64df59def88157b3b8d264fcdd402d3bda6da639ffccbcb1` | Nuxel boot image: Linux 6.19 `Image.gz` + initramfs + ocean DTB, Android boot header **v1**, page 2048, `name=nuxel-g7power`. **Repacked 2026-10-12** with `ili210x` built in (touch fix) |
| `nuxel-ocean-rootfs.img` | 501,440,512 | `58146f60af59e9d3e5ce1bbbd5a01c6eb2de7f6c40ae05208c6a955236e6e3da` | Phase-1 ext4 rootfs (label `nuxel-ocean`), static toybox **+ the full `lib/modules/6.19.0-g05f7e89ab973` (1455 modules)**, drops to a shell |
| `lk2nd.img` | 364,560 | `4550b20513f3cb93516edaeb16986b88af048d6c9d374d674e22d06edcacb562` | lk2nd built from source for msm8953 (`build-lk2nd-msm8953/`) |
| `lk2nd-msm8953.img` | 368,656 | `2170c90c4b28a0d6dd31ec942500dc1fc4da94a34dbfd0676238ba1de1353cfa` | Official lk2nd 23.1 release binary (cross-check; sha256 matches upstream `sha256sums.txt`) |
| `build-manifest.json` | — | — | Device key, kernel commit, load addresses, per-artifact hashes |

### 1.2 Kernel build (from source, in a Linux VM)

- Source: `https://github.com/msm8953-mainline/linux` (the postmarketOS `linux-postmarketos-qcom-msm8953` tree), **Linux 6.19**, commit `05f7e89ab`.
- Built natively for aarch64 with GCC 15.3.1 + the repo fragment `kernel/g7power/defconfig` merged in.
- Outputs copied to `kernel/g7power/.build/out/arch/arm64/boot/`:
  - `Image.gz` — 15,582,233 bytes — sha256 `8224631c036605cd0e45e3ce5177935b6187024b866b3f451b2e8ad85549ffef`  (**rebuilt 2026-10-12 with `CONFIG_TOUCHSCREEN_ILI210X=y`**)
  - `dts/qcom/sdm632-motorola-ocean.dtb` — 40,384 bytes
- Driver set verified in the built config (as **modules** unless noted): `DRM_MSM` (Adreno 506 / freedreno), `WCN36XX` + `QCOM_WCNSS_PIL` (WCN3680B WiFi), `SND_SOC_WCD9335` (cajon-v2 audio), `BMI160_I2C`, `EXT4_FS=y`, `DEVTMPFS=y`, `MMC_SDHCI_MSM=y`, `ARCH_QCOM=y`, and — after the 2026-10-12 rebuild — `TOUCHSCREEN_ILI210X=y` (ILI2117 touch, built in) and `LEDS_LM3697=y` (backlight, built in).
- **Rebuild note (2026-10-12):** the config is produced as `make defconfig` (the in-tree arm64 defconfig — there is **no** `msm8953_defconfig` in this tree) merged with `kernel/g7power/defconfig`, then `olddefconfig`. That is why an option *not* named explicitly in the fragment (e.g. `ILI210X`) ends up **unset**: the postmarketOS config that does set it (`config-postmarketos-qcom-msm8953.aarch64`, `CONFIG_TOUCHSCREEN_ILI210X=m`) is **not** used by this build.
- **Two honest driver findings from the real build** — the first one now has a definitive answer, and it explains the community "no touchscreen" reports:
  1. **Touch: CORRECTED 2026-10-12 — this was a Nuxel config bug, not a missing driver.** Nuxel requested `CONFIG_TOUCHSCREEN_ILI2117=y`, a symbol that **does not exist**; `olddefconfig` silently dropped it and `CONFIG_TOUCHSCREEN_ILI210X` stayed **unset**, and therefore **no touch driver was built at all** in the artifacts of the previous pass (verified: the built `Image.gz` contained `# CONFIG_TOUCHSCREEN_ILI210X is not set`, and the rootfs contained no ilitek module). ILI2117 support lives in the multi-chip mainline driver `drivers/input/touchscreen/ili210x.c` (`CONFIG_TOUCHSCREEN_ILI210X`), whose OF table maps `compatible = "ilitek,ili2117"` → `ili211x_chip` (43-byte ILI211x frame, checksum-checked, 10 contacts, **no firmware blob**). The ocean DTS node was always correct and *does* have a driver. Fixed here; see §1.7. Full analysis: `nuxel-g7power-touchscreen.md`.
  2. **Backlight: corrected symbol names.** The fragment asked for `CONFIG_BACKLIGHT_TI_LM3697`, which does not exist; the real symbol is `CONFIG_LEDS_LM3697` (it was `=m` from the base config, and the module `leds-lm3697.ko` + `leds-ti-lmu-common.ko` do exist in the rootfs). Both symbol names are now correct and `LEDS_LM3697=y` (built in).

### 1.3 lk2nd (the mandatory msm8953 bootloader)

- Source: `https://github.com/msm8916-mainline/lk2nd`, built with `arm-none-eabi-` → `build-lk2nd-msm8953/lk2nd.img` (28 appended DTBs).
- The stock Motorola **ABOOT cannot boot a mainline kernel**; lk2nd is chainloaded from the `boot` partition and provides the fastboot that loads the Nuxel boot image. This is why the flash is **two-phase**.

### 1.4 Boot image packer + header reader

- `boot/g7power/pack-boot-v1.sh` (legacy **v1**, page 2048) and `tools/read-boot-header-v1.py` were round-trip tested: pack → re-parse gives `magic=ANDROID!`, `page_size=2048`, `kernel_addr=0x80008000`, `ramdisk_addr=0x81000000`, `tags_addr=0x80000100`, `dt_size=40384`, correct name/cmdline.

### 1.5 Load addresses — how they were derived (not fabricated)

The G7 Power boot-image load addresses were resolved from two authoritative upstream sources and **agree**:

- postmarketOS `device-motorola-ocean/deviceinfo`: `flash_offset_base=0x80000000`, `flash_offset_kernel=0x00008000`, `flash_offset_ramdisk=0x01000000`, `flash_offset_tags=0x00000100`, `flash_pagesize=2048` → `kernel=0x80008000`, `ramdisk=0x81000000`, `tags=0x80000100`.
- TWRP `android_device_motorola_ocean/BoardConfig.mk`: `BOARD_KERNEL_BASE=0x80000000`, `BOARD_RAMDISK_OFFSET=0x01000000`, `BOARD_KERNEL_TAGS_OFFSET=0x00000100`, `BOARD_BOOTIMG_HEADER_VERSION=1`, `BOARD_KERNEL_PAGESIZE=2048`.
- lk2nd `target/msm8953/rules.mk`: `BASE_ADDR = 0x80000000`.

These were written into `docs/g7power-device-inventory.md` and `boot/g7power/boot-config.txt`, which unblocks the Phase-0 inventory gate in every build/flash script. **You must still confirm them from your own unit's stock `boot.img` (Step 3.6) before the first flash.**

### 1.6 Host tooling installed/verified

- `adb` + `fastboot` (platform-tools, `/opt/homebrew/bin`).
- `edl` (bkerler/edl) v3 in a venv: `~/.venvs/edl/bin/edl` (needs `libusb`, present).
- Cross/native toolchains used for the builds (in throwaway Linux VMs): `aarch64-linux-gnu-gcc` 12, `arm-none-eabi-gcc` 12, GCC 15.3 (native aarch64), `dtc` 1.7.2.
- All G7 Power shell scripts pass `bash -n` and `shellcheck -S warning`.

### 1.7 The touchscreen fix (2026-10-12) — what changed and how it was verified

Root cause: **one wrong symbol name.** `kernel/g7power/defconfig` asked for
`CONFIG_TOUCHSCREEN_ILI2117` — the *hardware* name — which no tree defines.
Kconfig's `olddefconfig` silently dropped it, so `CONFIG_TOUCHSCREEN_ILI210X`
was never enabled and `ili210x.ko` was never built.

The fix, applied in this pass:

```diff
 # Touch
-CONFIG_TOUCHSCREEN_ILI2117=y      # <-- this symbol does not exist anywhere
+CONFIG_TOUCHSCREEN_ILI210X=y      # ILI2117 hardware; ili210x.c matches ilitek,ili2117
-# Backlight (wrong symbol)
-CONFIG_BACKLIGHT_TI_LM3697=y
+# Backlight (real symbol)
+CONFIG_LEDS_LM3697=y
+CONFIG_I2C_CHARDEV=y              # i2cdetect/i2cget diagnostics (built in: no module autoload)
```

Then the kernel was rebuilt in the repo's aarch64 UTM VM and the boot image
repacked. Verification actually performed (not assumed):

> **Note on the initramfs.** `boot/initramfs/initramfs.cpio.gz` was **not**
> regenerated in this pass. The `/init` inside it predates the source edit to
> `boot/initramfs/init.sh` (comment/`system_a`-fallback only — functionally
> identical, because the packed cmdline pins
> `root=/dev/block/bootdevice/by-name/userdata`). Regenerate it with
> `python3 images/bootpack/assembler.py --stage <dir> --out boot/initramfs/initramfs.cpio.gz
> --width 720 --height 1520` on the next full rebuild.

| Check | Result |
|---|---|
| Upstream tree really has the match | `ili210x.c`: `{ .compatible = "ilitek,ili2117", .data = &ili211x_chip }`, `#define ILI211X_DATA_SIZE 43`, `input->name = "ILI210x Touchscreen"` |
| Mainline ocean DTS | `touchscreen@41 { compatible = "ilitek,ili2117"; reg = <0x41>; interrupts = <65 IRQ_TYPE_EDGE_FALLING>; touchscreen-inverted-x; }` — confirmed from `msm8953-mainline/linux` |
| Rebuilt `.config` | `CONFIG_TOUCHSCREEN_ILI210X=y`, `CONFIG_LEDS_LM3697=y` |
| Built `Image.gz` (config extracted back out with `scripts/extract-ikconfig`) | `CONFIG_TOUCHSCREEN_ILI210X=y` |
| Built `Image` strings | contains `ILI210x Touchscreen` and `ilitek,ili2117` |
| Repacked boot image header | `kernel_size=15582233`, `dt_size=40384`, page 2048, v1, cmdline unchanged — re-parsed with `tools/read-boot-header-v1.py` |
| Compiled DTB | still contains `ilitek,ili2117` |

Why `=y` and not the guide's earlier `=m` suggestion: the Phase-1 rootfs is a
static-toybox image whose `/sbin/init` is a 607-byte script that **loads no
modules** (no udev, no systemd). A module would simply never be loaded, so the
driver is built into the kernel. Switch to `=m` + `modprobe ili210x` only if
you want reload/debug bring-up over a serial console.

Other Nuxel files corrected in the same pass (all were pointing at the
non-existent `ili2117` driver/product name):

* `device/g7power/nuxel-ocean.conf` → `NUXEL_TOUCH_DRIVER=ili210x` (+ module/input-name keys)
* `device/g7power/90-nuxel-ocean.rules` → `ATTRS{name}=="ILI210x Touchscreen"`
* `configs/g7power/libinput/99-nuxel-ocean-touch.conf` → **disabled** (`.disabled`) because it carried a duplicate X-inversion; see §1.7 note below
* `device/g7power/deviceinfo`, `kernel/g7power/patches/README.md`, `firmware/g7power/manifest.yml`, `docs/g7power-bringup.md` §8

> **Do not double-invert X.** The DT already sets `touchscreen-inverted-x` and
> `ili210x` reports through the generic touchscreen-property helpers, so the
> kernel inverts X once. The old Xorg InputClass also applied
> `TransformationMatrix "-1 0 1 0 1 0 0 0 1"` (it matched `ILI2117*`, a name
> the kernel never registers, so it never ran). It is now disabled on purpose.

---

## 2. Prerequisites

### 2.1 Hardware
- Motorola Moto G7 Power **XT1955** (`ocean`) — a spare device; flashing wipes it.
- A **data-capable USB-C cable** (many charge-only cables do not enumerate fastboot).
- Battery **> 60 %**.
- Optional but strongly recommended: a working **microSD card** (used for the on-device stock backup) and, for EDL, a Linux host or a Windows box with QFIL as a fallback.

### 2.2 Host software (already installed on this Mac; listed for reproducibility)
```sh
# macOS (this machine — already present)
brew install android-platform-tools libusb
adb version && fastboot --version        # platform-tools >= 34
~/.venvs/edl/bin/edl --help              # EDL 9008 unbrick tool (bkerler/edl v3)

# Linux equivalent
sudo apt install android-tools-adb android-tools-fastboot libusb-1.0-0
pip install --user edl          # or the venv method used on this Mac
```

### 2.3 Accounts / information only you have
- **Motorola bootloader unlock code**: obtained once from the Motorola portal using your device's IMEI + serial (see Step 3.3). There is no way to automate this — **it is the longest-lead item, request it before anything else.**
- Decide beforehand: **you will keep the bootloader UNLOCKED** during all testing. **Never run `fastboot oem lock`** while Nuxel is installed.

> **Status 2026-10-12:** the phone (`ZY326RGXCM`, XT1955-4) reports
> `sys.oem_unlock_allowed=1`, i.e. the **"OEM unlocking" developer toggle is
> already ON**. What is still missing is the Motorola unlock *code*.

### 2.4 Critical safety facts (read once, internalize)
1. **`dtbo` must be flashed before `lk2nd`** — a missing/corrupt dtbo is the classic msm8953 soft-brick.
2. **Never flash or pull** the protected partitions: `modemst1 modemst2 fsg fsc ddr persist misc` (per-unit IMEI/radio/DDR calibration, irreplaceable).
3. **EDL (Qualcomm 9008) is the safety net** — confirm it enumerates *before* your first flash (Step 3.4).
4. **Back up stock `boot` and `dtbo` first** (Step 3.3) — you need them to revert and to confirm load addresses.
5. Device identity is checked before every flash: `fastboot getvar product` must be **`ocean`**, otherwise every script refuses.
6. **A working USB *data* link is mandatory.** `fastboot` does not work over the network-adb path. Verify *before* planning a flash: `system_profiler SPUSBDataType | grep -i motorola` (macOS) must show the phone. As of 2026-10-12 it does **not** (blocker #1, §0.1).
7. **This device is A/B** (`boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, current slot `_b`). Always check `fastboot getvar current-slot`; the current slot is what `fastboot flash boot`/`dtbo` writes, and it is where a stock backup must be read from (`by-name/boot_a` vs `boot_b`).
8. **`/vendor/firmware` and `/dev/block/*` are root-only on stock Android 10 here.** With unrooted adb you cannot list blobs or `dd` the stock images — plan on a booted TWRP (after unlock) or a stock firmware package.

---

## 3. Step-by-step: from here to flashed-and-tested

### Step 3.1 — Turn on Developer Options + USB debugging (on the phone, in stock Android)
1. Settings → About phone → tap **Build number** 7×.
2. Settings → System → **Developer options** → enable **USB debugging** and **OEM unlocking**.
3. Connect USB-C; accept the "Allow USB debugging?" RSA prompt.

```sh
adb devices            # expect: <serial>   device
adb shell getprop ro.product.device    # MUST print: ocean
```

> **Carrier-lock check (do this now):** Settings → About phone → SIM status. If it says the device is **network/carrier locked**, the bootloader **cannot** be unlocked — stop here. (This unit's `sys.oem_unlock_allowed=1`, which is a good sign, but it is not proof the carrier-lock check passes.)

> **Status 2026-10-12 — already done / known:**
> * USB debugging is on, but the phone is reachable **only over Wi-Fi adb**
>   (`adb connect 10.20.30.15:5555` → `ocean`). The USB cable currently gives
>   **no data link and no charging** (`connected=false`, `USB powered: false`).
>   Fix the cable/port before Step 3.3 — without USB there is no fastboot.
> * `adb shell getprop ro.product.device` → `ocean` ✅
> * `ro.build.fingerprint` → `motorola/ocean_retail/ocean:10/QPO30.52-5/58b45:user/release-keys`; model `moto g(7) power`; SKU `XT1955-4`; slot `_b`.

### Step 3.2 — Full stock backup + Phase 0 inventory (DESTRUCTIVE STEP LATER — do backups first)
> ⚠️ **2026-10-12 reality check: most of this step is NOT possible on this
> unit yet.** The `shell` uid is denied `/dev/block/*` **and**
> `/vendor/firmware*` (`Permission denied`), and `dmesg`/`/proc/cmdline` are
> restricted too (`klogctl: Permission denied`). So the stock `boot`/`dtbo`
> backup **and** the vendor-blob inventory require **root**, which requires
> **unlock first**. Do the non-root parts now (they already ran and are stored
> in `g7power/stock-evidence/`), then come back to the `dd` parts after
> Step 3.3 using a booted TWRP (§3.2b).

Run these with the phone booted into stock Android and `adb` authorized:
```sh
mkdir -p ~/g7power-backup && cd ~/g7power-backup

# --- Identity + hardware inventory ---
adb shell getprop ro.product.device            > g7power-props.txt   # ocean
adb shell getprop ro.product.model            >> g7power-props.txt
adb shell getprop ro.bootloader               >> g7power-props.txt
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|qcom|msm|sdm' >> g7power-props.txt
adb shell cat /proc/cmdline                   >> g7power-props.txt
adb shell dmesg                               >  g7power-dmesg.txt      # touch/WiFi/BT/audio/camera IDs
adb shell getevent -pl 2>/dev/null            >  g7power-input.txt       # confirms Ilitek ILI2117
adb shell ls -laR /dev/block/bootdevice/by-name/ > g7power-partitions.txt

# --- Vendor firmware inventory (fills firmware/g7power/manifest.yml) ---
adb shell ls -laR /vendor/firmware/        >  g7power-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/   >>  g7power-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/    >  g7power-vendor-modules.txt
adb shell ls /vendor/firmware/WCNSS*      2>/dev/null | tee g7power-wifi-fw.txt
adb shell ls /vendor/firmware/wlan/prima/ 2>/dev/null | tee -a g7power-wifi-fw.txt
adb shell ls /vendor/firmware/qca/        2>/dev/null | tee g7power-bt-fw.txt
adb shell cat /proc/asound/cards          2>/dev/null | tee g7power-audio.txt

# --- Stock boot image (for load addresses + revert) ---
# NOTE: this is an A/B unit. Resolve the slot first and use boot_<slot>:
SLOT=$(adb shell getprop ro.boot.slot_suffix | tr -d '\r')     # -> _b on this unit
adb shell "ls -l /dev/block/bootdevice/by-name/boot${SLOT}"     # boot_b = mmcblk0p42 here
adb shell "su -c 'dd if=/dev/block/bootdevice/by-name/boot${SLOT} of=/sdcard/stock-boot.img'" 2>/dev/null || \
  adb shell "dd if=/dev/block/bootdevice/by-name/boot${SLOT} of=/sdcard/stock-boot.img"
adb pull /sdcard/stock-boot.img . 2>/dev/null || echo "dd denied without root — use §3.2b (TWRP) or §3.5"
python3 <repo>/tools/read-boot-header-v1.py stock-boot.img   # confirm kernel/ramdisk/tags addrs + page 2048
```
Then, **while still in Android**, also copy the stock `dtbo` (needed for revert). The easiest safe path is on-device `dd` to internal storage or microSD:
```sh
# Beware: only 'boot_<slot>', 'dtbo_<slot>', 'recovery' are safe. NEVER dd
# modemst*/fsg/fsc/ddr/persist/misc (per-unit IMEI/calibration).
adb shell "su -c 'dd if=/dev/block/bootdevice/by-name/dtbo${SLOT}  of=/sdcard/stock-dtbo.img'" || \
adb shell   "dd if=/dev/block/bootdevice/by-name/dtbo${SLOT}  of=/sdcard/stock-dtbo.img"       || \
echo "dd denied without root — use §3.2b (TWRP) or §3.5 (firmware package)."
adb pull /sdcard/stock-dtbo.img . 2>/dev/null || true
```
**Keep `stock-boot.img` and `stock-dtbo.img` forever — these are your revert.**

### Step 3.2b — Get root *without* flashing: boot TWRP (after unlock) → pull everything

Once the bootloader is **unlocked** (Step 3.3) you can get a root shell without
changing the device permanently by *booting* (not flashing) a recovery:

```sh
# 1) Download a TWRP for ocean (slot-aware; e.g. twrp-*-ocean.img) — host side.
# 2) Boot it transiently (does NOT write the recovery partition):
adb reboot bootloader
fastboot boot twrp-ocean.img
# 3) In TWRP: adb is root; now pull the blobs and dd the stock images:
adb shell id                                   # uid=0
adb shell 'ls -l /vendor/firmware /vendor/firmware_mnt'   # now readable
mkdir -p ~/g7power-backup/vendor-firmware
adb pull /vendor/firmware       ~/g7power-backup/vendor-firmware/    2>/dev/null || true
adb pull /vendor/firmware_mnt   ~/g7power-backup/vendor-firmware-mnt/ 2>/dev/null || true
# stock revert images (confirm the slot: getprop ro.boot.slot_suffix in stock, or
# check /dev/block/by-name in TWRP):
adb shell 'dd if=/dev/block/by-name/boot_b  of=/tmp/stock-boot.img'
adb shell 'dd if=/dev/block/by-name/dtbo_b  of=/tmp/stock-dtbo.img'
adb pull /tmp/stock-boot.img  ~/g7power-backup/stock-boot.img
adb pull /tmp/stock-dtbo.img  ~/g7power-backup/stock-dtbo.img
python3 <repo>/tools/read-boot-header-v1.py ~/g7power-backup/stock-boot.img
```

Then fill the real WiFi/BT firmware filenames + sha256 into
`firmware/g7power/manifest.yml` from the pulled tree. (WiFi/BT/GPU blobs are
required for those subsystems to work at all; touch needs none — see §1.7.)

> If `fastboot boot` is unavailable on your bootloader, the fallback is to
> extract the same blobs from a **stock firmware package** (§3.5).

### Step 3.3 — Unlock the bootloader (WIPES THE DEVICE)

> **State as of 2026-10-12:** the bootloader looks **locked**
> (`ro.boot.verifiedbootstate=green`). The "OEM unlocking" toggle is already
> enabled on the phone, so the remaining input is the **Motorola unlock code**.
> You also need item #1 from §0.1 (USB data link) before `fastboot` can talk to
> the phone at all.
```sh
adb reboot bootloader
fastboot devices                      # expect: <serial>  fastboot
fastboot getvar product               # expect: ocean
fastboot getvar unlocked              # expect: no  (before unlock)
fastboot oem get_unlock_data          # prints a long string — copy it in full
```
1. Paste the unlock data into the Motorola portal:
   `https://motorola-global-portal.custhelp.com/app/standalone/bootloader/unlock-your-device`
2. Wait for the e-mail with your **unlock code** (may take minutes to hours).
3. Unlock (this erases userdata):
```sh
fastboot oem unlock <YOUR_UNLOCK_CODE>
```
4. Reboot, re-enable Developer options + USB debugging. (You can also use the helper: `bash boot/g7power/flash.sh --device g7power --unlock-help`.)

### Step 3.4 — Verify the EDL (Qualcomm 9008) unbrick path BEFORE flashing anything
1. Power the phone **off**.
2. Hold **Volume Down + Volume Up** together, then plug in USB-C.
3. The host must enumerate a **Qualcomm HS-USB QDLoader 9008** port:
```sh
# macOS
system_profiler SPUSBDataType | grep -iA6 -E 'Qualcomm|9008'
# Linux
lsusb | grep -iE '05c6:9008'
```
If you see it, you have a working last-resort recovery path. (Tool: `~/.venvs/edl/bin/edl`. A Linux host is the most reliable EDL environment; QFIL on Windows is the alternative.) Then unplug and boot normally.

### Step 3.5 — Get the stock firmware package (for `dtbo`/recovery + missing blobs)
If `dd` could not pull `dtbo` (no root — which is the case **now**, §0.1 #4), download the **stock Motorola G7 Power (ocean) firmware** for your retail variant (**this unit is XT1955-4**). lolinet removed the 2019 ocean packages from its main tree (older than the 5-year retention window), so use an archive mirror / XDA thread / the exact retail variant package. Places worth trying, in order:

1. `https://mirrors.lolinet.com/firmware/moto/ocean/official/` (mirror tree; may still carry ocean)
2. XDA ocean firmware/recovery threads (search `XT1955-4` + `QPO30.52-5` — matching your build avoids a downgrade/verity mess)
3. `fastboot boot twrp-ocean.img` → `dd` the partitions (§3.2b) — the most reliable route and it needs no third-party host

This pass could not fetch the package automatically (both upstream sources are gone/gated); it is listed as an open external dependency. From the package keep `boot.img`, `dtbo.img` (mandatory) and the `vendor`/`firmware` blobs. Record every source path in `firmware/g7power/manifest.yml`.
```sh
# After downloading, sanity-check the two files you will need:
python3 <repo>/tools/read-boot-header-v1.py boot.img
```

### Step 3.6 — (Rebuild step — optional for you because it is already done)
The artifacts in `build/out/g7power/` were produced for you. To reproduce them from scratch (needs a Linux host or the repo VM — the kernel build does not work on bare macOS due to a case-insensitive-FS collision in lk2nd and the missing GNU toolchain):
```sh
# 1) lk2nd (needs arm-none-eabi- gcc) — must be built on a case-SENSITIVE filesystem
git clone --depth=1 https://github.com/msm8916-mainline/lk2nd
cd lk2nd && make TOOLCHAIN_PREFIX=arm-none-eabi- lk2nd-msm8953 -j"$(nproc)"
#   -> build-lk2nd-msm8953/lk2nd.img

# 2) mainline msm8953 kernel (native aarch64 or aarch64-linux-gnu-)
git clone --depth=1 https://github.com/msm8953-mainline/linux
cd linux && make ARCH=arm64 defconfig
scripts/kconfig/merge_config.sh -m .config <repo>/kernel/g7power/defconfig
make ARCH=arm64 olddefconfig
make ARCH=arm64 -j"$(nproc)" Image.gz dtbs modules
#   -> arch/arm64/boot/Image.gz, arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb
# (note: display/GPU/WiFi land as modules; install them to the rootfs /lib/modules)

# 3) Nuxel boot image (v1) — the repo orchestrator does this for you:
NUXEL_DEVICE=g7power bash <repo>/images/g7power/build.sh
#   or pack directly (what this pass did):
python3 <repo>/boot/g7power/pack-boot-v1.sh \
  --kernel  linux/arch/arm64/boot/Image.gz \
  --ramdisk <repo>/boot/initramfs/initramfs.cpio.gz \
  --dtb     linux/arch/arm64/boot/dts/qcom/sdm632-motorola-ocean.dtb \
  --kernel-addr 0x80008000 --ramdisk-addr 0x81000000 --tags-addr 0x80000100 \
  --cmdline "console=ttyMSM0,115200 nuxel.device=g7power root=/dev/block/bootdevice/by-name/userdata rootfstype=ext4 rootwait rw" \
  --output  <repo>/build/out/g7power/nuxel-ocean-boot.img
```
Convenience wrapper (uses the same env/keys everywhere):
```sh
cd <repo>
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh --device g7power --help   # see all flags
```

### Step 3.7 — FLASH IT (two-phase, fastboot + lk2nd)
Make sure the phone is **unlocked**, **> 60 %**, and you are in **stock ABOOT fastboot** (power off → hold **Volume Down + Power**, or `adb reboot bootloader`).

**Phase 1 — stock ABOOT fastboot (flash dtbo FIRST, then lk2nd to `boot`):**
```sh
cd <repo>/build/out/g7power
fastboot devices                       # sanity (USB ONLY — see §0.1 #1)
fastboot getvar product                # MUST be: ocean
fastboot getvar unlocked               # MUST be: yes
fastboot getvar current-slot           # this unit: b  → writes boot_b / dtbo_b

fastboot flash dtbo  ../path/to/stock-dtbo.img     # 1) dtbo FIRST (mandatory)
fastboot flash boot  lk2nd.img                     # 2) install lk2nd on the boot partition
fastboot reboot                                    # 3) device now boots lk2nd
```
**Enter lk2nd fastboot:** as the device boots lk2nd, press and hold **Volume Down** to stop in lk2nd's fastboot menu (lk2nd also auto-continues to boot otherwise). Verify you are in lk2nd (not ABOOT) by the on-screen menu / `fastboot getvar product` still answering `ocean`.

**Phase 2 — lk2nd fastboot (flash the Nuxel boot image + rootfs):**
```sh
fastboot flash boot     nuxel-ocean-boot.img       # mainline kernel + initramfs + ocean DTB
fastboot flash userdata nuxel-ocean-rootfs.img     # ext4 userdata rootfs (wipes userdata — expected)
fastboot reboot
```
`lk2nd` automatically writes `fastboot flash boot <img>` at the **512 KiB offset** inside the boot partition, so it does **not** overwrite itself. Do not use a raw `dd` for this.

**One-command helper (does the same, with guards, prompts and a revert path):**
```sh
cd <repo>
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh --device g7power \
  --dtbo ../path/to/stock-dtbo.img \
  --lk2nd build/out/g7power/lk2nd.img \
  --boot  build/out/g7power/nuxel-ocean-boot.img \
  --rootfs build/out/g7power/nuxel-ocean-rootfs.img
# Preview without touching the phone: add --dry-run
```

### Step 3.8 — TEST IT (first boot)
Watch the screen. The expected first-boot sequence on the G7 Power:
1. **Motorola/ABOOT splash → lk2nd splash** (if lk2nd is installed correctly you will see the lk2nd logo/menu instead of a spinning stock Android logo).
2. lk2nd loads the Nuxel `boot.img` → **kernel 6.19 starts** → the Nuxel initramfs runs → `switch_root` to `/dev/block/bootdevice/by-name/userdata` → the Phase-1 rootfs `/sbin/init` prints a banner and **drops to a toybox shell**.

What to check and how:
```text
# If you get a shell on the console (or over an added UART), run:
dmesg | grep -iE 'msm|drm|ili210x|wcn36xx|wcd9335|mmc|sdm632'   # driver bring-up
cat /proc/asound/cards            # expect a WCD9335 / cajon card
ls /sys/class/drm                 # expect a card0-* if DRM_MSM bound
ip link                           # wlan0 appears once wcn36xx + firmware load
uname -a                          # Linux 6.19 ... aarch64
cat /proc/device-tree/model       # Motorola Moto G7 Power
```
Because this is a headless-ish bring-up, the primary observables are the **screen** and (if you solder/attach a UART) **serial on `ttyMSM0` @ 115200**. lk2nd can also be debugged while in its fastboot:
```sh
fastboot oem log && fastboot get_staged lk2nd-log.txt   # lk2nd's own boot log
```

**Interpreting results honestly:**
- **lk2nd menu appears** → Phase 1 success (bootloader chain works).
- **Kernel/initramfs banner / shell appears** → the mainline kernel booted on your hardware. This is the milestone this guide targets.
- **No display but device stays alive / enumerates** → expected on the first pass: `DRM_MSM` and friends build as **modules**, and the Phase-1 rootfs `/sbin/init` **loads no modules** (no udev/systemd). The modules are present in the rootfs — the display comes up once you `modprobe msm` (+ panel/backlight) from the console. The kernel console itself should already be visible via the lk2nd framebuffer handoff. **Touch is now built into the kernel** (`CONFIG_TOUCHSCREEN_ILI210X=y`), so it needs no module — but it is unproven until this boot (§1.7).
- **Nothing at all / back to ABOOT** → re-check §4 and revert (Step 3.9).

### Step 3.9 — Revert to stock / unbrick

**Revert (fastboot reachable) — must be done from STOCK ABOOT fastboot, not lk2nd:**
> Important: while lk2nd is installed, `fastboot flash boot` from **lk2nd's** fastboot writes at a +512 KiB offset (it deliberately protects itself), which will **not** restore the stock boot. To truly revert you must be in **stock ABOOT fastboot** (power off → hold **Volume Down + Power**), where `fastboot flash boot` writes at offset 0.
```sh
# In stock ABOOT fastboot (A/B unit — current slot is what gets written):
fastboot getvar current-slot            # this unit: b
fastboot flash dtbo stock-dtbo.img      # dtbo first (writes dtbo_<current>)
fastboot flash boot stock-boot.img      # original stock boot (removes lk2nd)
fastboot reboot
# Also re-flash the stock system/vendor/userdata you backed up, or run the full
# stock firmware flash-all script from your retail package, to be fully stock.
```

**Full unbrick (fastboot gone) — Qualcomm EDL 9008:**
```sh
~/.venvs/edl/bin/edl --help
# Enter EDL: phone off, hold Vol Down + Vol Up, plug USB (host shows 05c6:9008)
~/.venvs/edl/bin/edl printgpt                                  # confirm connection (read-only)
~/.venvs/edl/bin/edl w boot_b  stock-boot.img                  # restore the boot chain (slot b on this unit)
~/.venvs/edl/bin/edl w dtbo_b  stock-dtbo.img
# EDL also needs USB — same cable/port caveat as fastboot (§0.1 #1).
# If needed, restore the full stock package with the vendor's rawprogram XML
# (edl / QFIL). NEVER write modemst1/modemst2/fsg/fsc/ddr/persist/misc from
# a dump that is not your own unit's — you would destroy your IMEI/calibration.
```

---

## 4. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `fastboot devices` empty | charge-only/damaged cable, wrong port, not in fastboot, driver | **this is the current blocker** (§0.1 #1): the device does not enumerate on USB at all — try a known-good data cable on a direct Mac port; power off → Vol Down + Power; macOS: `system_profiler SPUSBDataType \| grep -i motorola` |
| `flash.sh` refuses: "Device mismatch" | `fastboot getvar product` ≠ `ocean` | you are on the wrong device/port — reconnect the G7 Power |
| `flash.sh` refuses: "Bootloader is LOCKED" | not unlocked | Step 3.3 (`fastboot oem unlock <code>`) |
| `flash.sh` refuses: "inventory incomplete" | Phase-0 fields still placeholder | they are pre-filled; ensure `docs/g7power-device-inventory.md` still has `KERNEL_ADDR/RAMDISK_ADDR/TAGS_ADDR/WIFI_FW_FILENAMES` set |
| Soft-brick after flashing lk2nd | `dtbo` was not flashed first / corrupt | re-enter ABOOT fastboot, `fastboot flash dtbo stock-dtbo.img`, then stock boot; else EDL |
| Boots to lk2nd then hangs | kernel/DTB mismatch or bad boot.img | re-pack `nuxel-ocean-boot.img`; check DTB is `sdm632-motorola-ocean`; `fastboot oem log` |
| No touch | (was a config bug — now fixed, §1.7) driver built-in but not binding / IRQ not firing / controller differs | `dmesg \| grep -iE 'ili210\|ilitek\|78b7000'`; `find /sys/bus/i2c/devices -name '*-0041'`; `readlink -f /sys/bus/i2c/devices/*-0041/driver` (expect `ili210x_i2c`); `grep ili /proc/interrupts`. Layer-by-layer table: `docs/g7power-bringup.md` §8 |
| No WiFi | firmware blobs / module not loaded | install the WCNSS blobs from your `/vendor/firmware` into `/lib/firmware` and load `wcn36xx`+`qcom_wcnss_pil` |
| `Couldn't parse partition size '0x'` | old fastboot quirk | `fastboot flash:raw boot lk2nd.img` then `fastboot boot lk2nd.img` |
| Device won't boot at all | — | EDL (Step 3.9) is the guaranteed recovery |

---

## 5. Quick reference

### 5.1 Key device facts
| Field | Value |
|---|---|
| Codename / key | `ocean` / `g7power` |
| SoC | Qualcomm Snapdragon 632 (SDM632, msm8953 family) |
| GPU / display | Adreno 506 (freedreno) / 6.2" IPS 1520×720, TI LM3697 backlight |
| Touch | Ilitek ILI2117 hardware, mainline **`ili210x`** driver (`CONFIG_TOUCHSCREEN_ILI210X=y`, i2c_3 @ 0x41, IRQ tlmm 65, inverted-x). Input name `ILI210x Touchscreen` |
| WiFi/BT | WCN3680B — `wcn36xx` + `QCOM_WCNSS_PIL`, BT `hci_qca` (NOT ath10k/brcmfmac) |
| Audio | Qualcomm WCD9335 (cajon-v2) ASoC |
| Modem | Snapdragon X9 LTE — **not ModemManager-ready** in Phase 1 |
| Boot image | Android header **v1**, page **2048**, `name=nuxel-g7power` |
| Partitions | **A/B**: `boot_a`/`boot_b`, `dtbo_a`/`dtbo_b`, `system`/`vendor`/`userdata`; current slot **`_b`** |
| Load addrs | kernel `0x80008000`, ramdisk `0x81000000`, tags `0x80000100` |
| Boot chain | PBL → SBL → ABOOT → **lk2nd** → Linux 6.19 → initramfs → rootfs |
| Verified on unit | model `moto g(7) power` XT1955-4, serial `ZY326RGXCM`, build `QPO30.52-5`, slot `_b`, touch i2c `3-0041`, IRQ 286 = msmgpio 65 Edge (`ilitek`), stock touch driver **`ILITEK_TDDI`** |

### 5.2 Command cheat-sheet
```sh
# Tools
adb devices ; fastboot devices
adb connect 10.20.30.15:5555          # this unit's network adb (USB is dead — §0.1)
fastboot getvar product ; fastboot getvar unlocked ; fastboot getvar current-slot ; fastboot getvar all

# Build (Linux host / repo VM)
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone
NUXEL_DEVICE=g7power bash images/g7power/build.sh

# Flash (from build/out/g7power/)
fastboot flash dtbo stock-dtbo.img             # ABOOT mode, FIRST
fastboot flash boot lk2nd.img                  # ABOOT mode
# (reboot into lk2nd — hold Vol Down at boot)
fastboot flash boot     nuxel-ocean-boot.img   # lk2nd mode (+512KiB offset)
fastboot flash userdata nuxel-ocean-rootfs.img # lk2nd mode
fastboot reboot

# Revert / unbrick
fastboot flash dtbo stock-dtbo.img ; fastboot flash boot stock-boot.img   # ABOOT mode
~/.venvs/edl/bin/edl printgpt  ; ~/.venvs/edl/bin/edl w boot stock-boot.img

# Verify a boot image header (host)
python3 tools/read-boot-header-v1.py build/out/g7power/nuxel-ocean-boot.img
```

### 5.3 Files this pass created / touched
- **New bundle:** `build/out/g7power/` (`nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`, `lk2nd.img`, `lk2nd-msm8953.img`, `sha256sums.txt`, `build-manifest.json`).
- **Kernel artifacts:** `kernel/g7power/.build/out/arch/arm64/boot/{Image.gz,dts/qcom/sdm632-motorola-ocean.dtb}`.
- **lk2nd build:** `boot/g7power/lk2nd/.build/build-msm8953/lk2nd.img` (+ `boot/g7power/lk2nd/lk2nd-official-23.1.img`).
- **Initramfs:** `boot/initramfs/initramfs.cpio.gz`.
- **Updated:** `docs/g7power-device-inventory.md` (gate fields pre-filled with sourced values + provenance banner), `boot/g7power/boot-config.txt` (real load addresses).
- **Updated 2026-10-12 (touch fix):** `kernel/g7power/defconfig`, `device/g7power/{nuxel-ocean.conf,90-nuxel-ocean.rules,deviceinfo}`, `configs/g7power/libinput/99-nuxel-ocean-touch.conf` → `.disabled` (+ README), `kernel/g7power/patches/README.md`, `firmware/g7power/manifest.yml`, `docs/g7power-bringup.md` §8, `build/out/g7power/{nuxel-ocean-boot.img,build-manifest.json}`.
- **New 2026-10-12:** `g7power/stock-evidence/` — the raw on-device inventory (`getprop`, `getevent -pl`, `/proc/interrupts`, i2c sysfs, partitions, boot flags, `dumpsys usb`).

---

## 6. Honest limitations & exact next steps

1. **Not yet hardware-proven.** Everything built is structurally correct; the first real boot is the test in Step 3.8.
2. **Display/GPU, WiFi, audio are modules** and are already installed into `nuxel-ocean-rootfs.img` (`lib/modules/6.19.0-g05f7e89ab973`, 1455 modules, incl. `msm.ko`, `wcn36xx.ko`, `qcom_wcnss_pil.ko`, `snd-soc-wcd9335.ko`, `leds-lm3697.ko`). To light up WiFi/audio you additionally need the **firmware blobs** in `lib/firmware` (from your `/vendor/firmware`; see Step 3.2 and `firmware/g7power/manifest.yml`).
3. **Touch is no longer a driver gap** — it was a config-name bug, now fixed and rebuilt into the boot image (§1.7). It is **still unproven on hardware**, and stock Android binds this node with the vendor `ILITEK_TDDI` driver rather than `ili210x`; first boot is the real test (§3.8). Do **not** write or port a driver.
4. **Modem (X9 LTE) is out of scope** for Phase 1 (WiFi/USB only).
5. **Stock firmware download** was the one external dependency this pass could not fetch automatically: lolinet has retired the 2019 ocean packages, and the pmOS vendor-blob repo is access-restricted. Get your variant's stock package (Step 3.5) so you have `dtbo.img`/`boot.img` + blobs.
6. **The full Nuxel userspace (Flatpak/Phosh immutable rootfs)** is Phase 2; this pass produced the Phase-1 bring-up rootfs so you can flash and test *now*. `images/mkrootfs.sh` needs Flatpak/`org.gnome.Platform//46` on a Linux build host.

**The single next physical action for you:** fix the **USB data cable/port** (§0.1 #1), then request the **Motorola unlock code** (§3.3) — those two are the long poles, and everything else waits on them.

---

## 7. What YOU must do before the first flash (ordered checklist)

The software side is done. The remaining items are physical/manual, in the order that minimises wasted time:

| # | Action | Why / notes |
|---|---|---|
| 1 | **Swap to a known-good USB *data* cable on a direct Mac port.** Verify with `system_profiler SPUSBDataType \| grep -i motorola` **and** that the phone shows `USB powered: true` in `dumpsys battery`. | Without USB there is no `fastboot`, no unlock, no flash, no EDL. Currently the phone isn't even charging over the cable. |
| 2 | **Get the Motorola unlock code** (portal; serial/`ro.boot.serialno` is `ZY326RGXCM`, and you need the device **IMEI** too — Settings → About phone, or `*#06#`; the portal also wants `fastboot oem get_unlock_data`). | Longest lead time; can be hours. The OEM-unlocking toggle is already ON. |
| 3 | **Confirm the bootloader lock state** with `fastboot getvar unlocked` and, if needed, unlock (`fastboot oem unlock <code>`). **Unlock wipes userdata** — back up anything personal first (photos/SMS/downloads). | The unit currently reports `verifiedbootstate=green` (locked). |
| 4 | **Boot a TWRP, then pull the stock blobs + `dd` the stock `boot_b`/`dtbo_b`** (§3.2b), or download the stock firmware package (§3.5). | Gives you the revert path **and** the WiFi/BT/GPU firmware blobs. Not possible with the current unrooted stock ROM. |
| 5 | **Charge to > 60 %.** | Motorola flashes refuse/abort on low battery. |
| 6 | **Confirm EDL 9008 enumerates** with the *same* working cable (power off, Vol Down + Vol Up, plug in). | Last-resort unbrick path; worthless if the cable is the problem. |
| 7 | Fill `firmware/g7power/manifest.yml` with the real blob filenames + sha256 you pulled in step 4, and drop them into `firmware/g7power/blobs/`. | Needed for WiFi/BT/GPU at runtime; touch needs **no** blob. |
| 8 | Only then: §3.7 flash, §3.8 test. | — |

**Not required:** writing/porting a touchscreen driver, installing `ilitek/ili251x.bin`, reset-gpio or regulator DT additions (see `nuxel-g7power-touchscreen.md` — do not fabricate those).

---

## 8. On-hardware evidence collected 2026-10-12 (stock Android, unrooted adb)

All raw files are in `g7power/stock-evidence/`. Headline facts:

| Fact | Observed value |
|---|---|
| Model / SKU / serial | `moto g(7) power` / **`XT1955-4`** / `ZY326RGXCM` |
| Build | `QPO30.52-5` (Android 10, `user/release-keys`), kernel `4.9.221-XT1955-X+` |
| Slot | **`_b`** (A/B device: `boot_a`=mmcblk0p41, `boot_b`=mmcblk0p42, `dtbo_a`=p43, `dtbo_b`=p44) |
| Boot state | `verifiedbootstate=green`, `veritymode=enforcing`, `bl_state=2`, `sys.oem_unlock_allowed=1` |
| Touch I²C client | `3-0041` on `78b7000.i2c` (i2c-3) — **matches mainline DT** |
| Touch IRQ | IRQ 286, `msmgpio 65 Edge`, owner string **`ilitek`** — matches DT `tlmm 65`, falling edge |
| Touch input node | `/dev/input/event1`, name **`tchip`**, `INPUT_PROP_DIRECT`, ABS_MT X 0..719, Y 0..1519, slots 0..9 |
| Touch driver (stock) | `/sys/bus/i2c/drivers/**ILITEK_TDDI**` (out-of-tree vendor driver, not `ili210x`) |
| Other i2c | `3-0038` → `focaltech_ts`, `3-0062` (undriven), `5-0036` (LM3697 backlight), `2-0020/0028/0034` (sensors) |
| USB | `device_manager: connected=false, configured=false, data_role=host, source_power=true`; battery `USB powered: false` → **no working USB link** |
| Blocked without root | `dmesg`, `/proc/cmdline`, `/proc/bus/input/devices`, `/vendor/firmware*`, `dd /dev/block/*` — all `Permission denied` |
| Network adb | `10.20.30.15:5555` (host is `10.20.30.12`) |
