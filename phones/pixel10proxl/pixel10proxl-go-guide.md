# Nuxel on the Google Pixel 10 Pro XL (`mustang`) — GO guide to flash & test

**Written:** 2026-10-11 · **Device:** Google Pixel 10 Pro XL (`mustang`, Google Tensor G5 / `gs501`) · **Nuxel v0.2.0**

This is the single, action-oriented guide produced by an automated prep pass on your Mac. It tells you **exactly what is already done for you**, **what only you can do by hand**, and **the step-by-step path to the first flash and first boot of Nuxel on your Pixel**. The longer background documents are `phones/pixel10proxl/pixel10proxl-requirements.md`, `phones/pixel10proxl/nuxel-pixel10proxl.md`, `phones/pixel10proxl/pixel10proxl-prompt.md` and `phones/pixel10proxl/google-pixel-10-pro-xl-quickstart.md`; read those for the full rationale. This file is the "do it now" checklist.

> **Honest one-line status.** The repo tooling, host tooling, AVB tooling, device package and every "wet-run" test that does **not** need your phone or Google's private vendor kernel have been prepared and verified. What remains **cannot** be done from this Mac: (1) downloading the factory image (Google's browser consent flow), (2) extracting the 30 vendor blobs, (3) the **private** Tensor G5 vendor kernel (`android-gs-mustang-6.12`), and (4) the physical unlock + flash. Those are the explicit manual steps below.

---

## 0. TL;DR — readiness snapshot after this pass

| Item | State after this pass |
|---|---|
| Host tooling (`adb`, `fastboot`, `openssl`, `dtc`) | ✅ installed + verified (`platform-tools` 37.0.1) |
| `avbtool` (AVB signing / `make_vbmeta_image` / key extraction) | ✅ **fetched from AOSP into `external/avbtool/`** and verified (1.3.0) |
| `tools/gen-keys.sh` (production AVB keygen) | ✅ **fixed** to use the in-repo avbtool (was failing: "Missing dependency: avbtool") |
| `firmware/…/install-firmware.sh --list-files` | ✅ **bug fixed** (embedded-Python `IndentationError`); now runs, reports **30 required + 2 optional**, CONSISTENCY CHECK PASSED |
| `firmware/…/verify-firmware.sh --strict` | ✅ runs; correctly reports **0 ok / 30 missing** and refuses a non-mustang key |
| `boot/…/flash.sh --help` + device gate | ✅ works; exits early with no mustang attached; refuses stubs |
| `boot/…/recovery.sh --help/--version` | ✅ **added** (previously ran the on-device menu even for `--help`) |
| `kernel/…/build-kernel.sh` per-device wrapper | ✅ **added** (Task-3 deliverable); dispatcher `--help` shebang fixed |
| Device package `APKBUILD` udev/modprobe | ✅ **canonical files added** (`90-nuxel-mustang.rules`, `nuxel-mustang.conf`); APKBUILD installs them (was inline) |
| `boot/…/boot-config.txt` (device boot config) | ✅ **added** (mustang header v4 / fastboot / partitions / load addresses) |
| Phase-0 inventory template + gate | ✅ **added** `docs/pixel10proxl-device-inventory.md` |
| `ci/validate-build.sh` (mustang) | ✅ **57 PASS / 0 FAIL** |
| `images/…/build.sh --quick` | ✅ context verified |
| UTM `nuxel-aarch64-phosh` VM (booted + suites) | ✅ services **PASS=22/0**, phosh-agent **HARD PASS**, PWA 11/1 (WebKit exit race, see §6) |
| **Firmware blobs (30)** | ⛔ **0/30 — needs factory image (you)** |
| **Kernel `Image.gz` + mustang DTB** | ⛔ **blocked on private vendor tree** |
| **Flashable image set (`boot.img` v4, `vendor_boot`, `init_boot`, `dtbo`, `vbmeta`, `system.img`)** | ⛔ **not present** |
| **Bootloader unlock + physical flash** | ⛔ **you must do this** (needs the phone) |

**Bottom line:** you have never been closer from the *software* side — every gate that a Mac can close is closed and tested. The remaining work is gated on **your phone** and **Google** (factory image + private vendor kernel), not on this repo.

---

## 1. What was prepared and verified in this pass

All device-specific work stays strictly under the `mustang` key (`NUXEL_DEVICE=mustang` → dir `google-pixel-10-pro-xl`); separation from `s10plus`/`g7power` is enforced by `tools/nuxel-device-select.sh`. A cross-device grep for `ocean`, `beyond2lte`, `lk2nd`, `odin`, `twrp`, `wcd9335`, `ili210x`, `panfrost`, `msm8953` inside the mustang trees returns **nothing**.

### 1.1 Bugs fixed (all were pre-existing and blocked a "wet run")

1. **`firmware/google-pixel-10-pro-xl/install-firmware.sh`** — the embedded Python manifest checker ended with a broken string concatenation:
   ```
   print("...covers all expected mustang blobs "
         "(Exynos 5500 modem, BCM4390 WiFi/BT, PowerVR GPU).")   # <- orphaned literal
   ```
   This raised `IndentationError: unexpected indent` (at parser line 107) so `--list-files`, `--verify-only` and `--checksums` **all died**. Fixed to a proper implicit concatenation. It now prints the full 32-row manifest table and `CONSISTENCY CHECK: PASSED`. (`bash -n` OK.)
2. **`tools/gen-keys.sh`** required `avbtool` on `PATH` and aborted before generating the production AVB key. It now resolves `avbtool` from `PATH`, then `external/avbtool/avbtool`, then `external/avbtool/avbtool.py`. (`shellcheck -S warning` clean.)
3. **`boot/google-pixel-10-pro-xl/recovery.sh`** ignored arguments, so `recovery.sh --help` started the interactive on-device recovery menu (and blocked on a `read`). Added `--help`/`-h`/`--version` that print usage on a host and exit 0. (`sh -n` OK, `shellcheck -S warning` clean.)
4. **`kernel/build-kernel.sh`** `usage()` printed a mangled first line (`!/usr/bin/env bash`) because it stripped the `#` off the shebang; now starts at line 2.

### 1.2 New / completed artifacts (mirroring the finished `g7power` pass)

| File | Purpose |
|---|---|
| `external/avbtool/avbtool` (+ `avbtool.py`) | Official AOSP AVB 1.3.0 tool. Unblocks `make_vbmeta_image`, `avb_custom_key` enrolment and `gen-keys.sh`. With `--flag 2` it produces the AVB-disabled `vbmeta` used by the dev flash path. |
| `device/google-pixel-10-pro-xl/90-nuxel-mustang.rules` | Canonical udev rules (touch S6SY791, MHI modem, PowerVR, brcmfmac Wi-Fi, hci BCM BT, UFS, PMIC, Type-C). |
| `device/google-pixel-10-pro-xl/nuxel-mustang.conf` | Canonical modprobe autoload list (PowerVR, AMB655X, S6SY791, MHI/Exynos5500, BCM4390, CS42L43/CS35L45, sensors, PMIC, charger, UFS), annotated with which modules are **vendor-tree-only**. |
| `device/google-pixel-10-pro-xl/APKBUILD` (edited) | Now lists those two files in `source=` and **installs them** instead of generating them inline (matches `device/g7power/APKBUILD`). |
| `kernel/google-pixel-10-pro-xl/build-kernel.sh` | Thin per-device wrapper that pins `--device mustang` and forwards to `kernel/build-kernel.sh` (Task-3 deliverable). |
| `boot/google-pixel-10-pro-xl/boot-config.txt` | Device boot config: header **v4**, page 4096, mandatory `init_boot`, A/B, AVB 2.0, load addresses (`0x10008000/0x11000000/0x10000100`), partition sizes, dev flash sequence, recovery key combo. |
| `docs/pixel10proxl-device-inventory.md` | Phase-0 operator inventory template: exact `adb`/`fastboot` collection commands, the 5 gate fields, the load-address block, and the safety rules. |

### 1.3 Command results captured on this Mac

```text
$ NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh --list-files
  required count: 30   optional count: 2
  CONSISTENCY CHECK: PASSED
  exit 0

$ NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict
  [verify-fw] Verify summary: 0 ok, 30 missing, 0 mismatch, 0 placeholder.
  exit 2                 # honest refusal (blobs not on disk yet)

$ NUXEL_DEVICE=mustang bash ci/validate-build.sh
  ALL VALIDATIONS PASSED   Passed: 57   Failed: 0   Warnings: 15
  exit 0

$ NUXEL_DEVICE=mustang images/google-pixel-10-pro-xl/build.sh --quick
  Quick-mode context verified -> build/out/mustang/quick-manifest.txt
  exit 0

$ NUXEL_DEVICE=mustang boot/google-pixel-10-pro-xl/flash.sh            # no device attached
  [OK]    fastboot available (fastboot version 37.0.1-15733141)
  [ERROR] No device in fastboot mode detected.
  exit 1                 # never flashes without a mustang in fastboot

$ NUXEL_DEVICE=mustang boot/google-pixel-10-pro-xl/recovery.sh --version
  nuxel-recovery 0.2.0 (mustang)
```

### 1.4 UTM VM verification (booted on this Mac)

The UTM ARM64 VM `nuxel-aarch64-phosh` (UUID `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Fedora 43, Phosh 0.54.0/phoc) was **started** and the Nuxel verify suites were run over SSH (guest `192.168.64.3`, user `nuxel`):

| Suite | Result |
|---|---|
| `vm/vm-verify-services.sh` | ✅ **PASS=22 FAIL=0** (bridge D-Bus name, portal auth/permission round-trip, notification + persistence, live backends) |
| `vm/vm-verify-phosh-agent.sh` | ✅ **HARD PASS** (S3 signal-driven push delivery + S4a `RequestPermission` auto-grant round-trip; S4b dialog screenshot captured) |
| `vm/vm-verify-pwa.sh` | ⚠️ **PASS=11 FAIL=1** — PART B (live WebKitGTK JS harness) aborts with `WebProcess didn't exit as expected after the UI process connection was closed`; the harness *did* produce a full result (`bridgeCall ok`, `apiFetch 200`, screenshot written) but the WebKitGTK exit-race makes the wrapper report no in-page result. This is a **userspace/VM harness quirk, unrelated to the Pixel flash path**; PART A (HTTP/PWA layer) is 11/11. |

This is the only "hardware-adjacent" green result in the tree: it validates **userspace** (Phosh, D-Bus services, PWA, sandbox wiring), **not** the Pixel silicon.

### 1.5 What could NOT be produced here (and why)

- **Firmware blobs (30).** Require the factory image `mustang-bp1a.250405.001-factory-*.zip`, which is behind Google's browser consent flow (the images page is JS-rendered; a direct `dl.google.com` URL could not be confirmed → not downloadable unattended). Self-service, 5-minute step in §3.4/§3.5.
- **Kernel `Image.gz` + mustang DTB.** `gs501_defconfig` and the Tensor G5 SoC/GPU/panel/touch/modem drivers live in the **private** tree `android-gs-mustang-6.12`; additionally there is **no Linux-targeted aarch64 cross-compiler** on this Mac (only `aarch64-elf-gcc` bare-metal). See §3.6/§6.
- **A real `boot.img`/`system.img` set.** Needs the kernel + DTB + firmware. `images/build.sh` refuses to emit a boot image without a real kernel and refuses to emit zero-filled stubs as flashable.
- **Unlock / flash.** Needs the physical handset.

---

## 2. Prerequisites

### 2.1 Hardware

- **Google Pixel 10 Pro XL (`mustang`)** — carrier-unlocked. Flashing **wipes** it; treat it as the test device, not a daily driver.
- A **USB-C data cable** (not charge-only; USB 3.2 Gen2 preferred). Many charge-only cables do not enumerate `fastboot`.
- Battery **> 60 %**.
- The factory image zip (`mustang-bp1a.250405.001-factory-*.zip`) kept somewhere safe — it is your only stock restore.

### 2.2 Host software (already installed on this Mac; listed for reproducibility)

```sh
# macOS (this machine — verified present)
brew install android-platform-tools libusb
adb version && fastboot --version      # platform-tools 37.0.1
openssl version                        # LibreSSL/OpenSSL present (gen-keys/open)
dtc --version                          # device-tree compiler (for the dtbo step)

# AVB tool is vendored in the repo (fetched this pass) — no brew needed:
python3 external/avbtool/avbtool version   # => avbtool 1.3.0
```

For the (still-blocked) kernel build you would additionally need a **Linux host or VM** with `gcc-aarch64-linux-gnu`, `bc bison flex libssl-dev libelf-dev` — macOS cannot produce the Android arm64 kernel reliably. See §6.

### 2.3 Accounts / information only you have

- **Google factory image** for `mustang` (browser consent flow, §3.4).
- **Access to the private vendor kernel tree** `android-gs-mustang-6.12` (or a signed prebuilt vendor kernel) — the single biggest blocker. Google does not publish it for anonymous cloning (anonymous fetch returns 404).
- Decision: **keep the bootloader UNLOCKED during all testing.** Never `fastboot flashing lock` until Nuxel boots in dev mode and you have enrolled your AVB key.

### 2.4 Critical safety facts (read once, internalize)

1. **`fastboot flashing unlock` (and `unlock_critical`) WIPE the device** and cannot be undone without a re-lock (which itself wipes).
2. **Verify device identity before every flash:** `fastboot getvar product` must be `mustang`. Nuxel's `flash.sh` refuses on mismatch.
3. **The Google factory image is the safety net.** Download + SHA-256 verify it *before* the first flash; its `flash-all.sh` is the canonical restore.
4. **`init_boot.img` is mandatory** on mustang (Android 13+ split-ramdisk). Skipping it = no boot.
5. **Never relock with wrong/missing AVB images.** Enroll your Nuxel AVB public key and sign `vbmeta` first.
6. **A/B slots:** never mix slot artifacts; confirm `current-slot`.
7. **Protected partitions:** do NOT erase `persist` / `metadata` outside an explicit clean install.

---

## 3. Step-by-step: from here to flashed-and-tested

### Step 3.1 — Enable Developer Options + OEM unlocking (on the phone, in stock Android)

1. Settings → About phone → tap **Build number** 7× rapidly ("You are now a developer!").
2. Settings → System → **Developer options**:
   - Toggle **OEM unlocking** ON. **If it is greyed out, the device is carrier-locked — STOP.**
   - Toggle **USB debugging** ON. Accept the RSA prompt.
3. Connect the USB-C cable and authorize the host.

```sh
adb devices
# expect: <your-serial>    device
adb shell getprop ro.product.name       # => mustang
adb shell getprop ro.build.id           # SAVE this (e.g. BP1A.250405.001)
adb shell getprop ro.bootloader         # SAVE this (bootloader revision)
adb shell settings get global oem_unlock_allowed   # 1 = can unlock
```

### Step 3.2 — Full backup + Phase-0 inventory (do this BEFORE unlocking)

`fastboot flashing unlock` factory-resets the phone, so back up first. Then run the Phase-0 collection in **`docs/pixel10proxl-device-inventory.md`** — it fills in the build string, bootloader revision, carrier-lock state, `current-slot`, the **exact vendor blob filenames** in `/vendor/firmware` + `vendor.img`/`modem_*.img`, and the private-tree access flag. Copy:

```sh
cd ~ && mkdir -p mustang-inventory && cd mustang-inventory
adb shell getprop | grep -iE 'ro.product|ro.build|ro.boot|ro.hardware|gs501|mustang' > mustang-props.txt
adb shell getprop ro.build.fingerprint >> mustang-props.txt
adb shell ls -laR /vendor/firmware/            > mustang-vendor-firmware.txt
adb shell ls -laR /vendor/firmware_mnt/image/ >> mustang-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/         > mustang-vendor-modules.txt
adb shell dmesg                                > mustang-dmesg.txt
adb shell getevent -pl 2>/dev/null             > mustang-input-devices.txt   # confirms S6SY791
# Save everything irreplaceable (photos, 2FA seeds, password-manager export).
```

### Step 3.3 — Reboot to fastboot + unlock (DESTRUCTIVE)

```sh
adb reboot bootloader
fastboot devices            # expect: <serial>   fastboot
fastboot getvar product     # MUST be: mustang
fastboot getvar current-slot
fastboot getvar unlocked    # yes/no

fastboot flashing unlock
# On-device: Volume keys → "Unlock the bootloader" → Power to confirm.
# The device factory-resets and reboots. Re-enable USB debugging afterwards.

fastboot getvar unlocked    # expect: yes
# Only if you also intend to flash bootloader/radio partitions:
# fastboot flashing unlock_critical    (also wipes)
```

### Step 3.4 — Download the factory image (you, in a browser)

```text
https://developers.google.com/android/images#mustang
```
Find build **`mustang-bp1a.250405.001`** and download `mustang-bp1a.250405.001-factory-<xxxxx>.zip`. The `<xxxxx>` suffix and the SHA-256 are shown on that page at download time.

```sh
shasum -a 256 mustang-bp1a.250405.001-factory-*.zip    # compare to the published hash
# Keep the untouched zip — this is your stock recovery asset.
```

### Step 3.5 — Extract + verify the firmware blobs

```sh
cd /Users/wicked/x/nuxel

# Dry run first (no device, no factory image needed):
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh --list-files
# => required count: 30   optional count: 2  (CONSISTENCY CHECK PASSED)

# Extract from the factory image (unpacks vendor.img/modem_*.img paths):
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/install-firmware.sh \
    /path/to/mustang-bp1a.250405.001-factory-<xxxxx>.zip \
    --output-dir ./firmware-out --install

# Verify (target: 30/30 verified):
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/verify-firmware.sh --root ./firmware-out -v
NUXEL_DEVICE=mustang firmware/google-pixel-10-pro-xl/verify-firmware.sh --strict
# The manifest entries whose `source_path`/`checksum` are still PLACEHOLDER must be
# replaced with the REAL filenames found in Step 3.2 before --strict can pass.
```

Firmware the manifest covers (30 required + 2 optional): Exynos 5500 modem (`modem.bin`, `modem_pr.bin`, `modem_cal.bin`, `modem_cfg.txt`, `exynos5500_shm.bin`), BCM4390 Wi-Fi/BT (`brcmfmac4390*.bin`, `.nvm`, `.clm_blob`, `BCM4390.hcd`), PowerVR GPU (`pvr_*.fw`, `pvr_drv.so`), AMB655X panel, S6SY791 touch, CS35L45/CS42L43 audio, BMI270/LSM6DSV/TCS3710 sensors, SN220 NFC, GF3636 fingerprint, MAX77729/MAX77826 PMIC, BQ2597x/MAX1720x charger.

### Step 3.6 — Build the kernel (BLOCKED on the private vendor tree)

```sh
# Kernel dispatcher (per-device wrapper added this pass):
NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh --help

# REAL mustang build (needs the private tree):
#   git clone https://android.googlesource.com/kernel/google-modules/gs \
#       -b android-gs-mustang-6.12 kernel/.build/vendor      # currently 404 anonymous
NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh --vendor
#   -> kernel/google-pixel-10-pro-xl/.build/out/Image.gz
#   -> kernel/google-pixel-10-pro-xl/.build/out/dtbs/mustang.dtb

# Public-GKI scaffold only (NOT bootable on mustang hardware; labels output as such):
NUXEL_DEVICE=mustang bash kernel/google-pixel-10-pro-xl/build-kernel.sh
```

### Step 3.7 — Build the Nuxel boot-image set (after Step 3.6)

```sh
NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --android
# produces (only from a real kernel + DTB + firmware):
#   build/out/mustang/flashable/{boot.img,vendor_boot.img,init_boot.img,dtbo.img,vbmeta.img,system.img}

# Context-only smoke test (works today):
NUXEL_DEVICE=mustang bash images/google-pixel-10-pro-xl/build.sh --quick
```

### Step 3.8 — (Production only) Generate Nuxel AVB keys + enroll

```sh
# Dev flashing does NOT need this. Do it only before relocking.
bash tools/gen-keys.sh --avb            # writes keys/nuxel-avb.pem + nuxel-avb-public.bin
# (now works — uses external/avbtool/avbtool)
fastboot flash avb_custom_key keys/nuxel-avb-public.bin
```

---

## 4. Flash the device

### 4.1 Pre-flash checklist (all must be TRUE)

- [ ] `fastboot devices` shows your serial in **fastboot** mode
- [ ] `fastboot getvar product` == `mustang`; `fastboot getvar serial` == your unit
- [ ] `fastboot getvar unlocked` == `yes`
- [ ] Full backup done; factory image downloaded + SHA-256 verified
- [ ] Firmware extracted + `verify-firmware.sh --strict` == **30/30**
- [ ] Boot images built (Step 3.7) — **not** zero-filled stubs
- [ ] Battery > 50 %

### 4.2 Device identity gate (run every session)

```sh
fastboot getvar product       # must be: mustang
fastboot getvar serial        # must be: your unit
fastboot getvar unlocked      # must be: yes
fastboot getvar secure        # yes  (Titan M3 active — expected)
fastboot getvar current-slot  # a or b
```

`boot/google-pixel-10-pro-xl/flash.sh` performs exactly this check and **refuses** on mismatch (or without a device). `NUXEL_EXPECTED_SERIAL` can pin the serial.

### 4.3 Development flash (AVB disabled — the recommended first path)

```sh
# One command (uses build/out/mustang/flashable/*):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh \
    --device mustang --skip-avb --allow-unverity-dev --slot a

# Equivalent manual sequence (what flash.sh does):
fastboot flash vbmeta_a --disable-verity --disable-verification vbmeta.img
fastboot flash dtbo_a        dtbo.img
fastboot flash boot_a        boot.img
fastboot flash init_boot_a   init_boot.img
fastboot flash vendor_boot_a vendor_boot.img
fastboot reboot fastboot                     # enter fastbootd (dynamic partitions)
fastboot flash system_a      system.img
fastboot set_active a
fastboot reboot

# First flash / clean install:
fastboot -w            # wipes userdata + metadata only
```

> If `flash.sh` aborts with "DEV STUB, NOT FLASHABLE" or "Required images missing",
> the image set is not real yet (kernel/firmware not built). That refusal is
> intentional — do **not** bypass it.

### 4.4 Production flash (custom AVB key + relock) — later, not first

```sh
# ONLY after Nuxel boots in dev mode and the AVB key is enrolled (Step 3.8):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh \
    --device mustang --relock-custom-key keys/nuxel-avb-private.pem --production
# --relock-custom-key triggers `fastboot flashing lock`, which WIPES the device.
```

---

## 5. Test it on the phone

```sh
# Once Nuxel boots:
adb devices

# Boot evidence (kernel cmdline + nuxel init):
adb shell dmesg | grep -i nuxel           # expect: "nuxel.device=mustang" + dm-verity mount
adb shell cat /proc/cmdline               # nuxel.device=mustang nuxel.slot=...

# Phosh / display (expect 3120x1440; the VM runs 720x1440):
adb shell systemctl --user status phosh --no-pager
adb shell "XDG_RUNTIME_DIR=/run/user/\$(id -u) wlr-randr" 2>/dev/null | head

# Nuxel services + D-Bus:
adb shell systemctl status nuxel-web nuxel-bridge nuxel-portal nuxel-notifications --no-pager
adb shell ss -ltnp | grep -E ':(8000|8080)'
adb shell curl -s 'http://127.0.0.1:8080/api/v1/ping?message=hello'

# Failed units:
adb shell systemctl --failed --no-pager
```

Driver reality check per subsystem (from `docs/driver-status.md`): UFS 4.0 / USB (dwc3) / AppArmor / namespaces are mainline; BCM4390 Wi-Fi needs firmware + a chip-entry patch; **GPU (PowerVR DXT), panel (AMB655X), touch (S6SY791), modem (Exynos 5500), audio (CS35L45/CS42L43), NFC (SN220), fingerprint (GF3636) are vendor-tree-only**. Expect the first boot to exercise **display + touch + UFS**, with GPU falling back to llvmpipe and Wi-Fi/BT/modem arriving in later phases.

---

## 6. Recovery / how to restore stock Android

```sh
# Enter fastboot: power off -> hold Volume Down + Power; or: adb reboot bootloader
fastboot devices
fastboot getvar product      # must be mustang

# Option 1 (safest) — Google's own restore script from the factory zip:
cd /path/to/mustang-bp1a.250405.001-factory-<xxxxx>/ && ./flash-all.sh

# Option 2 — Nuxel revert to stock boot chain (keeps your data):
NUXEL_DEVICE=mustang bash boot/google-pixel-10-pro-xl/flash.sh --revert

# Option 3 — manual restore of the boot chain:
fastboot flash boot_a        boot.img
fastboot flash vendor_boot_a vendor_boot.img
fastboot flash init_boot_a   init_boot.img
fastboot flash dtbo_a        dtbo.img
fastboot flash vbmeta_a      vbmeta.img
fastboot reboot fastboot
fastboot flash system_a      system.img && fastboot -w && fastboot set_active a && fastboot reboot
```

Recovery console (on-device): power off → hold **Volume Up + Power**; release Power at the Google logo; on "No command" press Volume Up + Power → select "Enter recovery". `boot/google-pixel-10-pro-xl/recovery.sh --help` now documents this and prints without starting the menu on a host.

---

## 7. A/B slots & partition reference (mustang)

```sh
fastboot getvar current-slot
SLOT=$(fastboot getvar current-slot 2>&1 | grep -o '[ab]' | head -1)
fastboot flash boot_${SLOT} boot.img      # etc.
fastboot set_active b && fastboot set_active a   # slot-switch test
```

| Partition | Size | Notes |
|---|---|---|
| `boot_a/b` | 96 MB | Android boot header **v4** |
| `vendor_boot_a/b` | 96 MB | vendor ramdisk + DTBO (required for panel/touch) |
| `init_boot_a/b` | 8 MB | generic ramdisk — **REQUIRED** (Android 13+) |
| `dtbo_a/b` | 16 MB | device tree overlay |
| `vbmeta_a/b` | 64 KB | AVB 2.0 (dev: `--disable-verity --disable-verification`) |
| `super` | ~8 GB | dynamic: system/system_ext/product/vendor |
| `modem_a/b` | 200 MB | Exynos 5500 baseband |
| `persist` | 32 MB | **NEVER wipe** |
| `metadata` | 64 MB | dynamic-partition metadata |

Load addresses (header v4 / page 4096): `kernel=0x10008000`, `ramdisk=0x11000000`, `tags=0x10000100`.

---

## 8. Honest gaps & FAQ

**Q: Why is the Pixel the hardest target even though it is the primary one?**
Its Tensor G5 (`gs501`) vendor kernel tree is **private** and almost every peripheral driver (GPU, panel, touch, modem, audio, NFC, fingerprint) is downstream-only. The `s10plus`/`g7power` siblings exist precisely so userspace/sandbox/flash work can be proven on mainline-friendly hardware.

**Q: What is the exact remaining blocker?**
Two, in order:
1. **Private vendor kernel** `android-gs-mustang-6.12` (`gs501_defconfig` + Tensor G5 drivers) — without it there is no mustang `Image.gz`/DTB, hence no `boot.img`. Anonymous clone returns 404.
2. **Factory image** (your consent flow) → real blob filenames/checksums → `verify-firmware.sh --strict` 30/30.

**Q: Is `make ci` green?**
`ci/validate-build.sh` alone is **57 PASS / 0 FAIL**. `make ci` additionally runs the full `images/build.sh`, which deliberately **exits 3** with "BOOT ARTIFACT NOT_DONE: kernel Image.gz missing" — that is the honest "kernel not built" gate, not a regression. It goes green the moment a real kernel exists.

**Q: Did the PWA verify suite pass?**
PART A (HTTP/PWA layer) 11/11. PART B (live WebKitGTK JS harness) reports 1 FAIL due to a WebKitGTK `WebProcess didn't exit as expected after the UI process connection was closed` race — the harness output (bridge call, API fetch, screenshot) is complete; it is a VM userspace quirk, not a device/flash issue.

**Q: What is proven vs not proven?**
Proven: repo tooling runs; `avbtool` works; VM userspace (Phosh + services + PWA) passes; device package + configs are coherent. **Not proven:** a successful boot on Pixel hardware — that is exactly what the physical flash in §4 tests.

---

## 9. Key URLs

| Resource | URL |
|---|---|
| Google Pixel factory images | https://developers.google.com/android/images#mustang |
| Android platform tools | https://developer.android.com/studio/releases/platform-tools |
| GKI kernel (`android16-6.12`, public scaffold) | https://android.googlesource.com/kernel/common |
| mustang vendor kernel (PRIVATE) | https://android.googlesource.com/kernel/google-modules/gs (`android-gs-mustang-6.12`) |
| AVB tool (vendored here) | https://android.googlesource.com/platform/external/avb |
| Nuxel repo | `/Users/wicked/x/nuxel` |

---

*Build the bunker first. Add the rave lights later.*
*— Nuxel v0.2.0*
