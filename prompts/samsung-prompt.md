# Nuxel — Samsung Galaxy S10+ (Exynos) Full Implementation Prompt
## For: Build Agent / Senior Embedded-Linux Bring-Up Engineer
## Repo: `/Users/wicked/x/nuxel` (or wherever your repo root lives)
## Based on: Deep analysis of Nuxel v0.1.0 repo (c3c4637, 363 MB, 18,036 LOC cross-tree)

---

> **How to use this file:** This is the complete, self-contained implementation
> prompt for your agent. Copy everything from `## ROLE` downward into your
> agent. The agent must implement every task in order. Do not skip tasks.
> Do not fabricate checksums, firmware blobs, device IDs, or driver status.
> Mark every unknown as `UNKNOWN`/`PLACEHOLDER`/`TBD` and require the operator
> to fill them from the physical device. The S10+ is **already in TWRP** — that
> is the starting point for all physical steps.

---

## ROLE

You are a senior embedded-Linux / phone-OS bring-up engineer working on the
**Nuxel** repository (the repo root is wherever `README.md` and `Makefile`
live — resolve it as `NUXEL_ROOT=$(git rev-parse --show-toplevel)` or the
equivalent). Your job is to implement **Samsung Galaxy S10+ (SM-G975F, Exynos
9820, codename `beyond2lte`)** as a fully-separated second hardware target
alongside the existing **Google Pixel 10 Pro XL (mustang)** scaffold, without
ever breaking the mustang path and without cross-contaminating any
device-specific artifact.

This work is an extension of the `nuxel-s10plus.md` agent prompt already
committed to the repo — that file defines the acceptance criteria and the target
layout. This prompt supersedes it with additional implementation detail drawn
from the deep repo analysis (see §REPO CONTEXT below).

---

## NON-NEGOTIABLE SAFETY RULES

These rules are absolute. Violating any of them is grounds for an unconditional
abort and an error message to the operator.

1. **Every device-specific artifact lives under a per-device directory** keyed
   by `NUXEL_DEVICE`. The three valid keys are:
   - `mustang`  → directory `google-pixel-10-pro-xl`  (Pixel 10 Pro XL)
   - `s10plus`  → directory `s10plus`                 (Galaxy S10+, `beyond2lte`)
   - `g7power`  → directory `g7power`                 (Moto G7 Power, `ocean`)

2. **No device file may contain multiple devices' data.** Shared code must be
   device-agnostic. If a line in a shared file names a device, it must be
   behind a device-key branch or moved to the per-device directory.

3. **The S10+ is a Samsung Exynos device. There is absolutely NO `fastboot`.**
   Never emit a `fastboot` command anywhere in any S10+ script, documentation,
   or comment. Flash tooling is exclusively: **TWRP** (`adb` + `dd` sideload)
   and **Download Mode** (Odin / `heimdall`).

4. **Verify device identity before every flash operation.** In every S10+ flash
   script, execute:
   ```sh
   DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
   [ "$DEVICE_PROP" = "beyond2lte" ] || { echo "ERROR: device is '$DEVICE_PROP', expected 'beyond2lte'. Refusing."; exit 1; }
   ```
   Also check `ro.product.name` equals `beyond2ltexx` (or the operator's
   specific regional variant). Refuse on mismatch.

5. **Never touch the following partitions** (per-unit calibration, IMEI, MAC,
   DRK, Knox state, baseband calibration — irreplaceable if wiped):
   `efs`, `efsg`, `persist`, `param`, `up_param`, `steady`, `keystorage`,
   `carrier`, `cp_debug`, `misc`.
   Any script that lists partitions or iterates over `/dev/block/by-name/`
   must explicitly skip these with a denylist check before `dd`.

6. **Never relock the bootloader or attempt Knox restoration.** The Knox fuse
   is already permanently tripped. Samsung Pay, Secure Folder, and Knox
   attestation are permanently unavailable on this unit. Attempting a relock
   (`ODIN LOCK`) will not restore Knox and may brick the bootloader. Leave it.

7. **Do not invent or fabricate firmware blobs, checksums, device IDs, or driver
   status.** Mark every unknown value explicitly as `UNKNOWN` / `TBD` /
   `PLACEHOLDER`. Require the operator to fill them from the physical device
   (which is already in TWRP). Never promote a placeholder to "verified" without
   a real sha256 from a real blob.

8. **Do not delete or overwrite mustang files without preserving a working
   path.** Move files into their per-device subdirectory and leave a thin
   symlink or wrapper at the old path if any existing script or test references
   the old path.

9. **Pass `bash -n` and `shellcheck -S warning`** on every new shell script.
   Do not use bashisms inside `#!/bin/sh` shebangs (no `local`, no `echo -e`,
   no `[[`). Use `#!/usr/bin/env bash` and `set -euo pipefail` for all new scripts.

---

## REPO CONTEXT (deep analysis — do not hallucinate past this)

### What the Nuxel v0.2.0 repo is and is not

| Area | Score | Honest status |
|---|---|---|
| Design / docs | ~75% | Architecture, security model, PWA spec solid |
| Repo structure | ~80% | Clean layout, all components represented |
| PWA apps | ~45% | Manifests, SWs, JS exist — integration-tested in VM |
| Native GTK4 apps | ~25–35% | C source exists, not proven buildable on aarch64 |
| D-Bus bridge/portal | ~30% | Python parses, dev-grade auth, not integration-tested on hardware |
| Sandbox/security | ~20% | Configs exist, enforcement not wired end-to-end |
| Build system | ~15% | Scripts exist with dev stubs, not proven on mustang |
| Flashable images | **0%** | No verified boot artifact set produced for any target |
| Pixel 10 Pro XL | **~5%** | Public mustang Linux is UART/initramfs-level only |
| UTM VM | **~25%** | VM boots, PASS=22 FAIL=0 on all three verify suites |
| **S10+ support** | **0%** | Does not exist yet; this prompt creates it |

The UTM VM (`711988C4-B34A-4A0F-BA86-B2C4A182E4BE`, Fedora 43 ARM64, Phosh
0.54.0, kernel 6.17.1) boots and passes all three verification suites
(`vm-verify-services.sh` PASS=22, `vm-verify-phosh-agent.sh` HARD PASS,
`vm-verify-pwa.sh` PASS=17). This is the baseline that must not be broken.

### Existing file layout (canonical paths you must know)

```
NUXEL_ROOT/
├── README.md, QUICKSTART.md, Makefile, VERSION (v0.2.0)
├── services/           # Python D-Bus: bridge, portal, notifications (7,234 LOC py)
├── shell/              # GTK4/C native apps: dialer, messages, contacts, settings (4,371 LOC py + C)
├── pwa/                # PWA apps: home, mail, calendar, notes, files, camera
├── boot/               # Currently mustang-only
│   ├── flash.sh        # fastboot-based, mustang-only — DO NOT modify for s10plus
│   ├── recovery.sh     # mustang-only
│   ├── README.md
│   ├── boot.img/       # boot artifact dir (Image.gz, initramfs.cpio.gz, dtbs)
│   └── initramfs/
│       └── init.sh     # Parses nuxel.device=, nuxel.slot=, root=, rootfstype=
│                       # Currently handles mustang A/B + generic VM paths
│                       # MUST be extended for s10plus A-only UFS layout
├── firmware/           # Currently mustang-only
│   ├── manifest.yml    # mustang manifest (30 required blobs, 0 verified)
│   ├── install-firmware.sh
│   └── verify-firmware.sh
├── kernel/             # Currently mustang-only
│   ├── defconfig       # mustang/gs501 fragment — DO NOT reuse for s10plus
│   ├── build-kernel.sh # Builds GKI android16-6.12 + merges defconfig
│   ├── patches/        # Nuxel drivers/nuxel/ patch (0001-nuxel-phone-features)
│   └── host-tools/
├── device/             # Currently mustang-only
│   ├── deviceinfo      # postmarketOS format, mustang
│   └── APKBUILD        # mustang
├── images/             # Currently mustang-only orchestration
│   ├── build.sh        # TARGET_SERIAL=58211FDCQ001LA (mustang)
│   ├── mkrootfs.sh     # Device-agnostic userspace (Phosh/Flatpak/PWA/ext4)
│   ├── mkrootfs.sh.bak
│   ├── bootpack/
│   │   └── mkbootimg.py  # Boot header v3/v4 ONLY — NOT v1. S10+ needs v1.
│   ├── avb/            # AVB signing (mustang)
│   ├── rauc/           # RAUC OTA (mustang A/B)
│   ├── ostree/         # OSTree (mustang)
│   ├── build-ota.sh
│   ├── config/         # packages.yml etc.
│   └── hooks/          # 01-customize-rootfs.sh etc.
├── configs/            # Currently mustang-only device configs
│   ├── display/        # 3120×1440 wlr-randr + AMB655X
│   ├── libinput/       # S6SY791 touch calibration
│   ├── alsa-ucm/       # GoogleMustang UCM (CS42L43/CS35L45)
│   ├── modem/          # Exynos 5500 modem stubs
│   ├── pipewire/
│   ├── wireplumber/
│   ├── apparmor/       # AppArmor profiles
│   ├── dbus/           # D-Bus policy configs
│   └── nftables/       # nftables firewall rules
├── tools/              # sign-image.sh, gen-keys.sh, dedupe-assets.sh
├── vm/                 # UTM VM scripts (device-agnostic, keep untouched)
├── ci/                 # validate-build.sh + Dockerfile
├── docs/               # Architecture, security, build, device setup docs
│   ├── driver-status.md   # mustang driver matrix (s10plus column present)
│   ├── hardware-ids.md    # Canonical 3-device component table
│   ├── s10plus* (add here)
│   └── ...
├── assets/             # Wallpaper, boot animation (device-agnostic)
├── nuxel-s10plus.md    # Previous agent prompt (superseded by this file)
├── s10plus-requirements.md  # S10+ requirements doc (key reference)
└── nuxel-g7power.md    # G7 Power requirements (stub reference)
```

### Critical implementation constraints discovered in analysis

**Boot image format mismatch:** `images/bootpack/mkbootimg.py` implements **only
boot header v3/v4** (mustang/Android 10+). The S10+ requires **legacy boot
header v1** (page 2048, `ANDROID!` magic + kernel + ramdisk, no `vendor_boot`,
no `init_boot`). You must implement a separate v1 packer for the S10+.

**initramfs `init.sh` must be extended:** Currently `boot/initramfs/init.sh`
probes root via `/dev/disk/by-partlabel/system_${SLOT}` (A/B) then generic
devices. The S10+ is **A-only** with a UFS path of
`/dev/block/platform/13d60000.ufs/by-name/`. The init must handle
`nuxel.device=s10plus` by probing `userdata` (or `system`) on the UFS
by-name path without an A/B slot suffix.

**No dm-verity/AVB for S10+ Phase 1:** The mustang path uses AVB 2.0 + Titan
M3 + dm-verity. The S10+ Knox fuse is tripped; do not attempt to wire dm-verity
or AVB for the first S10+ boot cycle. The rootfs is writable in Phase 1.

**Shared userspace is reusable:** `images/mkrootfs.sh`, all of `services/`,
`shell/`, `pwa/`, `configs/apparmor/`, `configs/dbus/`, `configs/nftables/` are
device-agnostic and can be reused for the S10+ rootfs assembly. Only the
per-device configs (display, libinput, alsa-ucm, modem, pipewire, wireplumber)
differ.

**Kernel cross-compiler:** The pmOS U-Boot fork uses `aarch64-linux-gnu-gcc-10`.
The S10+ kernel build must use `aarch64-linux-gnu-` (or clang with the
appropriate sysroot). Do NOT use the same toolchain pinning as the mustang
`kernel/build-kernel.sh` without checking compatibility.

---

## VERIFIED SAMSUNG GALAXY S10+ HARDWARE FACTS
### (Authoritative — do not contradict or extend without a cited source)

| Component | Value | Source |
|---|---|---|
| Device | Samsung Galaxy S10+ (SM-G975F, Exynos variant) | postmarketOS `samsung-beyond2lte` |
| Codename | `beyond2lte` | postmarketOS / TWRP |
| SoC | Samsung **Exynos 9820** (2× Mongoose M4 + 2× Cortex-A75 + 4× Cortex-A55, 8 nm) | pmOS `samsung-exynos9820` |
| GPU | Mali-G76 MP12 (Bifrost architecture) → mainline **Panfrost** | Exynos 9820 spec |
| RAM | 8 GB LPDDR4X | Samsung / pmOS |
| Storage | UFS 2.1 at `/dev/block/platform/13d60000.ufs` | pmOS device page |
| Display | 6.4″ Dynamic AMOLED, **3040×1440**, 19:9, HDR10+; DDIC **S6E3HA9** (`s6e3ha9_beyond2`) | beyond2lte DTS |
| Touch | Samsung **S6SY761**-series (`sec_ts`), I2C `hsi2c_10` @ `0x48`, firmware `y771`/`y771_d`, FOD | beyond2lte DTS (`input_common`) |
| WiFi/BT | Broadcom **BCM4375** (Wi-Fi 6 / 802.11ax, BT 5.0) | DTS `samsung,brcm-wlan` + teardown |
| Modem | Integrated Samsung **Shannon LTE** (Exynos 9820, Cat 20, **no 5G**) | Exynos 9820 spec |
| NFC | Samsung `sec-nfc` (S3FWRN5-family) @ I2C `0x27` + embedded SE (P3) | beyond2lte DTS |
| Audio codec | Cirrus Logic **CS47L93** (MADERA ASoC) | beyond2lte DTS |
| Audio amps | **2× Cirrus Logic CS35L40** speaker amplifiers | beyond2lte DTS |
| Battery | 4100 mAh, 15 W wired, 12–15 W wireless Qi | Samsung |
| Shipped kernel | Samsung 4.14.x downstream (Exynos 9820 BSP) | Samsung OSRC |
| Boot model | **A-only** (no A/B slots) | Samsung partition table |
| Partitions | `boot`, `recovery`, `system`, `vendor`, `product`, `userdata` as separate | Samsung partition table |
| Boot image format | **Legacy Android boot image header v1** (page 2048) | Samsung / pmOS U-Boot notes |
| Flash tooling | **No `fastboot`** — TWRP (adb sideload + `dd`) + Download Mode (Odin/`heimdall`) | pmOS `samsung-exynos9820` |
| UFS partition path | `/dev/block/platform/13d60000.ufs/by-name/` | postmarketOS |
| Boot status | **Already in TWRP** — bootloader unlocked, Knox fuse tripped | Operator context |

### S10+ Boot Chain (verified from postmarketOS)

```
Samsung Boot ROM
    │
    ▼
S-Boot (Samsung primary bootloader)
    │  Initializes: CPU, DRAM, UFS, display
    │  DOES NOT: accept mainline DTBs; DOES NOT: pass kernel cmdline correctly
    │
    ▼ (via TWRP dd to /dev/block/platform/13d60000.ufs/by-name/boot)
Custom U-Boot (chiffathefox/u-boot, branch exynos9820)
    │  Build: exynos9820_defconfig
    │  Chainloads mainline kernel via EFI
    │
    ▼
linux-postmarketos-exynos9820 (close-to-mainline kernel)
    │  nuxel.device=s10plus on cmdline
    │
    ▼
Nuxel initramfs → Nuxel rootfs → Phosh
```

**Why U-Boot is required:** S-Boot ignores the kernel cmdline and boot offset
from `boot.img` and does not accept mainline-compatible device trees. The only
proven path to mainline Linux on Exynos 9820 is S-Boot → custom U-Boot → Linux
via EFI. This is not optional.

### S10+ Community Resources (authoritative)

- **postmarketOS Exynos 9820 port:**
  `https://wiki.postmarketos.org/wiki/Samsung_Exynos_9820_(samsung-exynos9820)`
- **postmarketOS S10+ device page:**
  `https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_(samsung-beyond2lte)`
- **Custom U-Boot fork:**
  `https://github.com/chiffathefox/u-boot` branch `exynos9820`
  (`exynos9820_defconfig`)
- **TWRP for beyond2lte:**
  `https://twrp.me/samsung/samsunggalaxys10plus.html`
- **Samsung open-source kernel (Exynos 9820):**
  `https://opensource.samsung.com` (search `SM-G975F`)

### S10+ Driver Matrix (honest status at Nuxel v0.2.0)

| Subsystem | Driver | Status | Notes |
|---|---|---|---|
| GPU | Mali-G76 MP12 → Panfrost | ✅ Mainline | `CONFIG_DRM_PANFROST`; Mesa 23+ Bifrost support. Prefer over vendor Mali. |
| Display | Exynos9820 DRM/DSI + S6E3HA9 panel | 🚧 pmOS port | In `linux-postmarketos-exynos9820`; not upstream 6.12 |
| Touch | Samsung S6SY761 (`sec_ts`) | 🚧 Downstream/pmOS | sec_ts driver; I2C @ 0x48; firmware `y771`/`y771_d` |
| WiFi | BCM4375 (brcmfmac / cywd) | 🚧 Needs firmware | Base brcmfmac mainline; BCM4375 chip entry + firmware from device |
| Bluetooth | BCM4375 BT 5.0 (hci_uart/btbcm) | 🚧 Needs `.hcd` | `CONFIG_BT_HCIUART_BCM`; `.hcd` firmware from device |
| Modem | Shannon LTE (integrated) | ❌ Not MM-ready | No upstream ModemManager plugin. Phase-1: WiFi only. |
| Audio | CS47L93 codec (MADERA ASoC) | 🚧 Downstream | `CONFIG_MFD_MADERA`, `CONFIG_SND_SOC_CS47L93` |
| Audio amps | 2× CS35L40 | 🚧 Downstream | `CONFIG_SND_SOC_CS35L40` |
| NFC | Samsung sec-nfc (S3FWRN5) | 🚧 Downstream | I2C @ 0x27; no upstream driver |
| Sensors | Sensor hub | ⬜ UNKNOWN | Must collect from physical device via TWRP |
| Camera | ISP + sensors | ⬜ UNKNOWN | Must collect from physical device via TWRP; Phase-7 stretch |
| USB | dwc3 | ✅ Mainline | Standard dwc3; no `fastboot` gadget needed |
| UFS | ufshcd | ✅ Mainline | `CONFIG_SCSI_UFSHCD_PLATFORM` |
| Power | PMIC / charger / fuel gauge | 🚧 Downstream | Exynos9820 PMIC tree |

---

## TARGET DIRECTORY LAYOUT TO IMPLEMENT

Implement this layout. Do **not** delete existing mustang files; move them into
`google-pixel-10-pro-xl/` subdirs and leave thin wrappers/symlinks at old paths.
Add `g7power/` stub slots for consistency.

```
firmware/
├── google-pixel-10-pro-xl/     ← (move existing firmware/* here)
│   ├── manifest.yml
│   ├── install-firmware.sh
│   ├── verify-firmware.sh
│   └── blobs/
├── s10plus/                    ← (create new)
│   ├── manifest.yml            ← S10+ blob inventory (PLACEHOLDER checksums)
│   ├── install-firmware.sh     ← TWRP-pull mode + manual install
│   ├── verify-firmware.sh
│   └── blobs/
└── g7power/                    ← (stub)
    ├── manifest.yml
    ├── install-firmware.sh
    ├── verify-firmware.sh
    └── blobs/

kernel/
├── google-pixel-10-pro-xl/     ← (move existing kernel/* here)
│   ├── defconfig               ← gs501 fragment
│   ├── patches/                ← 0001-nuxel-phone-features.patch
│   └── README-toolchain.md
├── s10plus/                    ← (create new)
│   ├── defconfig               ← Exynos 9820 / linux-postmarketos-exynos9820 fragment
│   ├── build-kernel.sh         ← clones/builds linux-postmarketos-exynos9820
│   ├── patches/                ← Nuxel phone feature patch (or TODO stub)
│   └── README-toolchain.md
└── g7power/                    ← (stub)
    ├── defconfig
    ├── build-kernel.sh
    ├── patches/
    └── README-toolchain.md

device/
├── google-pixel-10-pro-xl/     ← (move existing device/* here)
│   ├── deviceinfo
│   ├── APKBUILD
│   ├── 90-nuxel-mustang.rules
│   └── nuxel-mustang.conf
├── s10plus/                    ← (create new)
│   ├── deviceinfo              ← beyond2lte, Exynos 9820 facts
│   ├── APKBUILD
│   ├── 90-nuxel-beyond2lte.rules
│   └── nuxel-beyond2lte.conf  ← stub; operator fills from TWRP
└── g7power/                    ← (stub)
    ├── deviceinfo
    ├── APKBUILD
    ├── 90-nuxel-ocean.rules
    └── nuxel-ocean.conf

boot/
├── google-pixel-10-pro-xl/     ← (move existing boot/flash.sh, recovery.sh here)
│   ├── flash.sh                ← fastboot-based, unchanged
│   ├── recovery.sh
│   └── boot-config.txt
├── s10plus/                    ← (create new)
│   ├── flash.sh                ← TWRP adb+dd sequence; NO fastboot
│   ├── recovery.sh             ← TWRP/heimdall recovery
│   ├── pack-boot-v1.sh         ← Legacy Android boot image header v1 packer
│   ├── uboot-chainload.sh      ← Clone/build/flash chiffathefox/u-boot exynos9820
│   └── boot-config.txt         ← S10+ U-Boot cmdline, load addresses
└── g7power/                    ← (stub)
    ├── flash.sh
    ├── recovery.sh
    ├── pack-boot-v1.sh
    └── boot-config.txt

configs/
├── google-pixel-10-pro-xl/     ← (move existing configs/* here)
│   ├── display/
│   ├── libinput/
│   ├── alsa-ucm/
│   ├── modem/
│   ├── pipewire/
│   └── wireplumber/
├── s10plus/                    ← (create new)
│   ├── display/                ← 3040×1440 wlr-randr
│   ├── libinput/               ← S6SY761 sec_ts calibration
│   ├── alsa-ucm/               ← CS47L93 + CS35L40 UCM stubs
│   ├── modem/                  ← Shannon LTE stub (not MM-ready)
│   ├── pipewire/
│   └── wireplumber/
└── g7power/                    ← (stub)
    ├── display/
    ├── libinput/
    ├── alsa-ucm/
    ├── modem/
    ├── pipewire/
    └── wireplumber/

images/
├── google-pixel-10-pro-xl/     ← (move existing images/build.sh, avb/, rauc/ here)
│   ├── build.sh
│   ├── avb/
│   ├── rauc/
│   └── ostree/
├── s10plus/                    ← (create new)
│   └── build.sh                ← Consumes kernel/s10plus/.build/out/ → boot.img v1 + rootfs
└── g7power/                    ← (stub)
    └── build.sh

tools/                          ← SHARED device-agnostic (unchanged)
docs/
├── s10plus-bringup.md          ← (create new)
├── s10plus-device-inventory.md ← (create new; operator template)
└── ... (existing, update README.md + QUICKSTART.md cross-refs)
```

---

## DEVICE SELECTION MECHANISM

Implement a single shared selector used by every per-device script. This is the
single most important architectural piece.

### `tools/nuxel-device-select.sh` (new shared library, source from every script)

```bash
#!/usr/bin/env bash
# nuxel-device-select.sh — Resolve NUXEL_DEVICE / --device to a canonical dir.
# Usage: source tools/nuxel-device-select.sh [--device <key>]
# After sourcing, $NUXEL_DEVICE_KEY and $NUXEL_DEVICE_DIR are exported.

_nuxel_resolve_device() {
    local _key="${NUXEL_DEVICE:-}"
    # Allow --device flag override passed as positional args from the caller
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --device) _key="$2"; shift 2 ;;
            *) shift ;;
        esac
    done
    case "${_key}" in
        mustang)  NUXEL_DEVICE_DIR="google-pixel-10-pro-xl" ;;
        s10plus|beyond2lte) _key="s10plus"; NUXEL_DEVICE_DIR="s10plus" ;;
        g7power|ocean)      _key="g7power"; NUXEL_DEVICE_DIR="g7power" ;;
        "") echo "ERROR: NUXEL_DEVICE is not set and --device was not passed." >&2
            echo "       Valid values: mustang, s10plus, g7power" >&2
            exit 1 ;;
        *) echo "ERROR: Unknown device key '${_key}'." >&2
           echo "       Valid values: mustang, s10plus, g7power" >&2
           exit 1 ;;
    esac
    export NUXEL_DEVICE_KEY="${_key}"
    export NUXEL_DEVICE_DIR
    echo "[nuxel] Device key:       ${NUXEL_DEVICE_KEY}"
    echo "[nuxel] Device directory: ${NUXEL_DEVICE_DIR}"
}
_nuxel_resolve_device "$@"
```

**Resolution order:** CLI `--device` flag > `NUXEL_DEVICE` env var > explicit
error (never silently guess). Every script must call this and print the resolved
device key + directory at startup before doing any work.

---

## TASKS (implement in this exact order)

---

### TASK 1 — Refactor mustang into per-device directories (preserve all behavior)

**Goal:** Move mustang-specific files into their `google-pixel-10-pro-xl/`
subdirs without breaking any existing behavior. The existing UTM VM tests
(`vm-verify-services.sh` PASS=22, `vm-verify-phosh-agent.sh` HARD PASS,
`vm-verify-pwa.sh` PASS=17) must still pass after this task.

**Steps:**

1. Create the `google-pixel-10-pro-xl/` subdirs in `firmware/`, `kernel/`,
   `device/`, `boot/`, `configs/`, `images/`.

2. Move these files (do not delete originals yet — `git mv` + create thin
   wrapper/symlink at old path):
   - `firmware/manifest.yml` → `firmware/google-pixel-10-pro-xl/manifest.yml`
   - `firmware/install-firmware.sh` → `firmware/google-pixel-10-pro-xl/install-firmware.sh`
   - `firmware/verify-firmware.sh` → `firmware/google-pixel-10-pro-xl/verify-firmware.sh`
   - `kernel/defconfig` → `kernel/google-pixel-10-pro-xl/defconfig`
   - `kernel/patches/` → `kernel/google-pixel-10-pro-xl/patches/`
   - `kernel/README-toolchain.md` → `kernel/google-pixel-10-pro-xl/README-toolchain.md`
   - `kernel/build-kernel.sh` stays at `kernel/build-kernel.sh` but gains
     `--device mustang` dispatch; copies the gs501 defconfig from
     `kernel/google-pixel-10-pro-xl/defconfig`.
   - `device/deviceinfo` → `device/google-pixel-10-pro-xl/deviceinfo`
   - `device/APKBUILD` → `device/google-pixel-10-pro-xl/APKBUILD`
   - `boot/flash.sh` → `boot/google-pixel-10-pro-xl/flash.sh`
   - `boot/recovery.sh` → `boot/google-pixel-10-pro-xl/recovery.sh`
   - `configs/display/` → `configs/google-pixel-10-pro-xl/display/`
   - `configs/libinput/` → `configs/google-pixel-10-pro-xl/libinput/`
   - `configs/alsa-ucm/` → `configs/google-pixel-10-pro-xl/alsa-ucm/`
   - `configs/modem/` → `configs/google-pixel-10-pro-xl/modem/`
   - `configs/pipewire/` → `configs/google-pixel-10-pro-xl/pipewire/`
   - `configs/wireplumber/` → `configs/google-pixel-10-pro-xl/wireplumber/`
   - `images/build.sh` gains `--device mustang` handling; reads inputs from
     `kernel/google-pixel-10-pro-xl/` and outputs to `build/out/mustang/`.
   - `images/avb/` → `images/google-pixel-10-pro-xl/avb/`
   - `images/rauc/` → `images/google-pixel-10-pro-xl/rauc/`
   - `images/ostree/` → `images/google-pixel-10-pro-xl/ostree/`

3. Create `tools/nuxel-device-select.sh` as documented above.

4. Update every script that hard-codes paths to source `nuxel-device-select.sh`
   and use `${NUXEL_DEVICE_DIR}`.

5. Leave `images/mkrootfs.sh` at its current location — it is device-agnostic
   and used by both mustang and S10+.

6. Leave `boot/initramfs/init.sh` at its current location — it is shared but
   must be extended in Task 2 for the S10+.

**Acceptance:**
- `NUXEL_DEVICE=mustang bash images/build.sh --quick` and
  `bash boot/google-pixel-10-pro-xl/flash.sh --help` still run and print
  device key `mustang`.
- All three UTM VM verify suites still pass (they don't touch device-specific
  dirs; verify with `bash -n` at minimum).
- `grep -r "mustang" s10plus/ 2>/dev/null` returns no device-coupling.

---

### TASK 2 — Extend `boot/initramfs/init.sh` for S10+ A-only UFS layout

**Goal:** The shared initramfs init currently probes root via
`/dev/disk/by-partlabel/system_${SLOT}` (A/B, mustang) then generic. Add S10+
support via `nuxel.device=s10plus`.

**Extend the device-specific root-probe section in `init.sh`:**

```sh
# After parsing nuxel.device= from cmdline:
case "${DEVICE}" in
    mustang|vm|"")
        # Existing A/B probe: /dev/disk/by-partlabel/system_${SLOT}
        # ... (leave existing logic unchanged)
        ;;
    s10plus)
        # S10+ A-only UFS layout:
        # Boot → U-Boot → Linux. Root is on userdata (or system) partition.
        # UFS path: /dev/block/platform/13d60000.ufs/by-name/
        # Probe order: explicit root= cmdline > userdata > system
        UFS_BASE="/dev/block/platform/13d60000.ufs/by-name"
        if [ -n "${ROOT_SPEC}" ]; then
            ROOT_DEV="${ROOT_SPEC}"
        elif [ -b "${UFS_BASE}/userdata" ]; then
            ROOT_DEV="${UFS_BASE}/userdata"
        elif [ -b "${UFS_BASE}/system" ]; then
            ROOT_DEV="${UFS_BASE}/system"
        else
            err "s10plus: cannot find root partition under ${UFS_BASE}"
            err "Available: $(ls ${UFS_BASE} 2>/dev/null | tr '\n' ' ')"
            emergency_shell
        fi
        log "s10plus: root → ${ROOT_DEV} (fstype: ${ROOT_FSTYPE:-ext4})"
        ;;
    g7power)
        # G7 Power stub: similar A-only but eMMC path TBD
        # /dev/mmcblk0p$(cat /sys/class/block/mmcblk0*/uevent | grep PARTNAME=userdata)
        # TODO: implement after g7power kernel bring-up
        err "g7power: root probing not yet implemented"
        emergency_shell
        ;;
esac
```

Also: make sure `emergency_shell` falls back to `nuxel.debug=1` behavior
(drop to `ash`/`sh`) and always prints the available block devices and
`/proc/cmdline` before dropping.

**Acceptance:** `bash -n boot/initramfs/init.sh` passes; `shellcheck` reports
no errors (downgrade bashisms to POSIX-sh if needed, since this uses `#!/bin/sh`).

---

### TASK 3 — S10+ device package (`device/s10plus/`)

Create the following files with **exact values from the verified hardware table
above**. Do not copy any mustang value.

#### `device/s10plus/deviceinfo`

```sh
# Nuxel Device Info — postmarketOS format
# Samsung Galaxy S10+ (SM-G975F, Exynos)
# Codename: beyond2lte

deviceinfo_format_version="2"
deviceinfo_name="Samsung Galaxy S10+"
deviceinfo_manufacturer="Samsung"
deviceinfo_codename="beyond2lte"
deviceinfo_year="2019"
deviceinfo_arch="aarch64"
deviceinfo_chassis="handset"

# SoC
deviceinfo_soc="Samsung Exynos 9820"
deviceinfo_soc_family="exynos9820"
deviceinfo_cpu="2x Mongoose M4 + 2x Cortex-A75 + 4x Cortex-A55 (8nm)"

# GPU
deviceinfo_gpu="Mali-G76 MP12 (Bifrost)"
deviceinfo_gpu_driver="panfrost"

# Display
deviceinfo_display="6.4\" Dynamic AMOLED 3040x1440 HDR10+"
deviceinfo_screen_width="1440"
deviceinfo_screen_height="3040"
deviceinfo_screen_refresh_rate="60"
deviceinfo_display_ddic="S6E3HA9"

# Touch
deviceinfo_touchscreen="Samsung S6SY761 (sec_ts)"
deviceinfo_touchscreen_driver="sec_ts"
deviceinfo_touchscreen_i2c_bus="hsi2c_10"
deviceinfo_touchscreen_i2c_addr="0x48"
deviceinfo_touchscreen_firmware="y771"

# Modem — integrated Shannon LTE, NOT ModemManager-ready in Phase 1
deviceinfo_modem="Samsung Shannon LTE (Exynos 9820 integrated, Cat 20, no 5G)"
deviceinfo_modem_interface="integrated"
deviceinfo_modem_driver="UNKNOWN_NOT_MM_READY"

# Connectivity
deviceinfo_wifi="Broadcom BCM4375 (Wi-Fi 6 / 802.11ax)"
deviceinfo_wifi_driver="brcmfmac"
deviceinfo_bluetooth="5.0"
deviceinfo_bluetooth_driver="btbcm"
deviceinfo_nfc="Samsung sec-nfc (S3FWRN5-family)"
deviceinfo_nfc_i2c_addr="0x27"

# Storage — UFS 2.1
deviceinfo_storage="UFS 2.1"
deviceinfo_storage_driver="ufshcd"
deviceinfo_storage_path="/dev/block/platform/13d60000.ufs"
deviceinfo_storage_filesystem="ext4"

# Memory
deviceinfo_ram="8GB LPDDR4X"

# Battery
deviceinfo_battery="4100mAh"
deviceinfo_battery_charging="15W wired, 12-15W wireless Qi"

# Audio
deviceinfo_audio_codec="Cirrus Logic CS47L93 (MADERA)"
deviceinfo_audio_amps="2x Cirrus Logic CS35L40"

# Sensors — collect from device via TWRP
deviceinfo_sensors="UNKNOWN — collect from real device via adb shell getevent -pl"
deviceinfo_camera_front="UNKNOWN — collect from real device"
deviceinfo_camera_rear="UNKNOWN — collect from real device"

# Boot configuration
deviceinfo_boot_header_version="1"
deviceinfo_boot_page_size="2048"
deviceinfo_boot_slots="none"
deviceinfo_boot_note="A-only partition layout. S-Boot -> custom U-Boot (chiffathefox/u-boot exynos9820) -> mainline Linux via EFI."
deviceinfo_flash_method="twrp-adb"
deviceinfo_flash_note="NO fastboot. Use TWRP (adb+dd) or Download Mode (Odin/heimdall)."

# Kernel
deviceinfo_kernel="linux-postmarketos-exynos9820"
deviceinfo_kernel_cmdline="earlycon=exynos4210,0x10020000 console=ttySAC0,115200 nuxel.device=s10plus root=PLACEHOLDER_fill_from_device rootfstype=ext4 rootwait rw"
```

#### `device/s10plus/APKBUILD`

Create a postmarketOS-format APKBUILD stub for `device-samsung-beyond2lte`.
Model it exactly on the mustang APKBUILD but replace all mustang values with
the S10+ verified hardware facts. Mark camera and sensor sections as
`UNKNOWN — collect from real device`. Include:
- `pkgname=device-samsung-beyond2lte`
- `_pmb_kernel="linux-postmarketos-exynos9820"`
- `_pmb_dtb="exynos9820-beyond2lte.dtb"` (verify DTB name from pmOS tree)
- Correct `depends` for `linux-postmarketos-exynos9820`, `firmware-samsung-beyond2lte` (stub)
- `install_kernel()`, `install_initfs()` functions adapted for TWRP flash method

#### `device/s10plus/90-nuxel-beyond2lte.rules`

Udev rules stub for the S10+. Include rules for:
- `sec_ts` touch (SUBSYSTEM=="input", ATTRS{name}=="sec_touchscreen")
- `sec-nfc` NFC (SUBSYSTEM=="nfc")
- `brcmfmac` WiFi (SUBSYSTEM=="net", KERNEL=="wlan*")
- Camera and sensor rules: stub, mark as `UNKNOWN`

#### `device/s10plus/nuxel-beyond2lte.conf`

Module and device configuration stub. Must include:
```sh
# Nuxel device configuration for Samsung Galaxy S10+ (beyond2lte)
# Fill all UNKNOWN values from real device via TWRP adb shell

NUXEL_DEVICE=s10plus
NUXEL_CODENAME=beyond2lte
NUXEL_UFS_PATH=/dev/block/platform/13d60000.ufs/by-name
NUXEL_DISPLAY_RESOLUTION=3040x1440
NUXEL_DISPLAY_DDIC=S6E3HA9

# WiFi firmware path (fill from real device)
NUXEL_WIFI_FW_PATH=/lib/firmware/brcm/brcmfmac4375-sdio.bin
NUXEL_BT_HCD_PATH=/lib/firmware/brcm/BCM4375.hcd

# Touch firmware path (fill from real device)
NUXEL_TOUCH_FW_PATH=/lib/firmware/tsp_sec/y771.fw

# Inventory incomplete — run docs/s10plus-device-inventory.md Phase 0 first
```

**Acceptance:** All four files exist, parse cleanly, `bash -n` passes on the
APKBUILD stub, no mustang value is present anywhere.

---

### TASK 4 — S10+ firmware manifest and extractor (`firmware/s10plus/`)

#### `firmware/s10plus/manifest.yml`

Create with these blob categories, all checksums/paths as `UNKNOWN`/`PLACEHOLDER`:

```yaml
device: s10plus
codename: beyond2lte
soc: exynos9820
modem: shannon_lte
flash_method: twrp-adb

# Acquisition: TWRP adb pull from the device (already in TWRP)
# adb pull /vendor/firmware ./firmware/s10plus/blobs/vendor-firmware/
# adb pull /vendor/lib/modules ./firmware/s10plus/blobs/vendor-modules/
# adb pull /vendor/etc/firmware ./firmware/s10plus/blobs/vendor-etc-firmware/
# adb pull /system/lib64 ./firmware/s10plus/blobs/system-lib64/
# OR: Extract from Samsung AP firmware tarball via Odin/heimdall

firmware_files:
  gpu_mali:
    - source_path: "vendor/lib64/egl/libGLES_mali.so"
      dest: "/usr/lib/libGLES_mali.so"
      description: "Mali-G76 MP12 Bifrost vendor GLES (fallback to Panfrost preferred)"
      required: false
      checksum: "UNKNOWN — collect from device"
    - source_path: "vendor/lib64/hw/gralloc.exynos5.so"
      dest: "/usr/lib/gralloc.exynos5.so"
      description: "Mali gralloc allocator"
      required: false
      checksum: "UNKNOWN"

  display_panel:
    - source_path: "vendor/firmware/s6e3ha9_beyond2_*.bin"
      dest: "/lib/firmware/"
      description: "S6E3HA9 AMOLED panel init firmware (DDIC beyond2)"
      required: false
      checksum: "UNKNOWN"

  touch:
    - source_path: "vendor/firmware/tsp_sec/y771.fw"
      dest: "/lib/firmware/tsp_sec/y771.fw"
      description: "Samsung S6SY761 touch firmware (sec_ts driver)"
      required: true
      checksum: "UNKNOWN — fill from device"
    - source_path: "vendor/firmware/tsp_sec/y771_d.fw"
      dest: "/lib/firmware/tsp_sec/y771_d.fw"
      description: "Samsung S6SY761 touch firmware (debug variant)"
      required: false
      checksum: "UNKNOWN"

  wifi_bt:
    - source_path: "vendor/firmware/bcm4375*.bin"
      dest: "/lib/firmware/brcm/"
      description: "BCM4375 Wi-Fi 6 firmware"
      required: true
      checksum: "UNKNOWN — fill from device; filename varies by subvariant"
    - source_path: "vendor/firmware/bcm4375*.clm_blob"
      dest: "/lib/firmware/brcm/"
      description: "BCM4375 CLM regulatory blob"
      required: true
      checksum: "UNKNOWN"
    - source_path: "vendor/firmware/BCM4375.hcd"
      dest: "/lib/firmware/brcm/BCM4375.hcd"
      description: "BCM4375 Bluetooth HCD firmware"
      required: true
      checksum: "UNKNOWN"
    - source_path: "vendor/firmware/bcm4375*.nvram"
      dest: "/lib/firmware/brcm/"
      description: "BCM4375 NVRAM calibration data"
      required: true
      checksum: "UNKNOWN"

  audio:
    - source_path: "vendor/firmware/cs47l93-dsp1-*.wmfw"
      dest: "/lib/firmware/"
      description: "CS47L93 MADERA DSP firmware"
      required: true
      checksum: "UNKNOWN"
    - source_path: "vendor/firmware/cs47l93-dsp*.bin"
      dest: "/lib/firmware/"
      description: "CS47L93 coefficient files"
      required: false
      checksum: "UNKNOWN"
    - source_path: "vendor/firmware/cs35l40*.wmfw"
      dest: "/lib/firmware/"
      description: "CS35L40 speaker amp firmware"
      required: false
      checksum: "UNKNOWN"

  nfc:
    - source_path: "vendor/firmware/sec_s3fwrn5_firmware.bin"
      dest: "/lib/firmware/sec_s3fwrn5_firmware.bin"
      description: "Samsung sec-nfc (S3FWRN5) firmware"
      required: false
      checksum: "UNKNOWN"

  modem:
    # CRITICAL: Do NOT flash CP from here. CP lives in the modem partition.
    # DO NOT touch efs/efsg/persist — IMEI and baseband calibration live there.
    # Shannon LTE modem interface is not yet MM-ready. Phase-1: skip modem.
    - source_path: "PLACEHOLDER — Shannon CP image path TBD"
      dest: "DO NOT INSTALL — modem bring-up is Phase 7"
      description: "Shannon LTE CP firmware — NOT for Phase 1"
      required: false
      checksum: "UNKNOWN"

  sensors:
    - source_path: "UNKNOWN — collect sensor hub firmware from real device"
      dest: "UNKNOWN"
      description: "Sensor hub firmware (accel/gyro/ALS/prox — component TBD)"
      required: false
      checksum: "UNKNOWN"

  camera:
    - source_path: "UNKNOWN — collect ISP/sensor firmware from real device"
      dest: "UNKNOWN"
      description: "Camera ISP and sensor firmware (Phase 7)"
      required: false
      checksum: "UNKNOWN"
```

#### `firmware/s10plus/install-firmware.sh`

Implement with ALL of the following modes:

- `--list-files` — Print the full manifest; do not install anything.
- `--verify-only` — Check each installed blob against its (eventual) sha256.
  If checksums are still `UNKNOWN`, report "pending verification" and exit 0
  (not an error — it just means nobody has filled the manifest yet).
- `--checksums` — Print sha256 of every blob under `blobs/`.
- `--twrp-pull` — **Key mode:** use `adb` to pull vendor blobs from the
  already-TWRP'd device. Implement:
  ```sh
  adb shell getprop ro.product.device | grep -q beyond2lte || { echo "ERROR: not connected to beyond2lte"; exit 1; }
  adb pull /vendor/firmware       firmware/s10plus/blobs/vendor-firmware/
  adb pull /vendor/lib/modules    firmware/s10plus/blobs/vendor-modules/
  adb pull /vendor/etc/firmware   firmware/s10plus/blobs/vendor-etc-firmware/
  adb pull /system/lib64          firmware/s10plus/blobs/system-lib64/
  ```
  After pulling, cross-reference the pulled files against the manifest and
  print which manifest entries were found vs. still missing.
- `--install` — Copy blobs from `blobs/` to the rootfs staging area. Refuse
  until real checksums are in the manifest (or `--force-pending` is passed).
- Guard: if `NUXEL_DEVICE` is not `s10plus`, abort immediately.
- Never install into mustang paths. Never read mustang's manifest.

#### `firmware/s10plus/verify-firmware.sh`

Modeled on `firmware/google-pixel-10-pro-xl/verify-firmware.sh`. Enforce that:
- Every `required: true` blob either has a real sha256 and is installed, OR
  is in `pending` state (checksum == `UNKNOWN`) and reports as pending.
- Blobs with `required: false` are advisory.
- Never reference mustang's manifest or paths.

**Acceptance:** `NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --list-files`
runs without touching mustang files and reports the S10+ manifest. Running
`--twrp-pull` with a connected S10+ in TWRP pulls vendor blobs correctly.

---

### TASK 5 — S10+ kernel build wrapper and defconfig (`kernel/s10plus/`)

#### `kernel/s10plus/defconfig`

This is an **Exynos 9820 / linux-postmarketos-exynos9820 Kconfig fragment**,
NOT the mustang gs501 fragment. It must:

- **NOT** include any gs501, BCM4390, PowerVR, AMB655X, S6SY791 (mustang
  touch), or GKI 6.12-specific Kconfig symbols.
- Enable or explicitly enable/keep:

```kconfig
# ============================================================
# Nuxel Exynos 9820 defconfig fragment for Samsung Galaxy S10+
# Applied on top of linux-postmarketos-exynos9820 base config
# ============================================================

# Nuxel phone features (apply only if patch compiles on exynos9820 tree)
# If the patch does not apply cleanly, stub these out with a TODO comment
# CONFIG_NUXEL=y        # conditional; see patches/README
# CONFIG_NUXEL_PHONE=y  # conditional
# CONFIG_NUXEL_BOOT_PARAM=y  # conditional

# GPU — Mali-G76 MP12 Bifrost → Panfrost (preferred over vendor Mali)
CONFIG_DRM=y
CONFIG_DRM_PANFROST=y
# CONFIG_DRM_MALI is not set  # vendor Mali fallback, not preferred

# Display — Exynos DRM/DSI (from pmOS exynos9820 tree)
CONFIG_DRM_EXYNOS=y
CONFIG_DRM_EXYNOS5433_DECON=y
CONFIG_DRM_EXYNOS_DSI=y
CONFIG_DRM_PANEL_SAMSUNG_S6E3HA9=y  # if present in tree; else stub

# Touch — Samsung S6SY761 sec_ts
CONFIG_TOUCHSCREEN_SAMSUNG_SEC_TS=y  # sec_ts driver; verify symbol name in tree

# WiFi — BCM4375 (brcmfmac + cywd)
CONFIG_BRCMFMAC=y
CONFIG_BRCMFMAC_SDIO=y
# CONFIG_BRCMFMAC_PCIE is not set  # BCM4375 is SDIO on S10+
CONFIG_CW1200=n  # not needed

# Bluetooth — BCM4375 BT 5.0
CONFIG_BT=y
CONFIG_BT_HCIUART=y
CONFIG_BT_HCIUART_BCM=y

# Audio — CS47L93 (MADERA) + 2× CS35L40
CONFIG_MFD_MADERA=y
CONFIG_MFD_CS47L93=y
CONFIG_SND_SOC_MADERA=y
CONFIG_SND_SOC_CS47L93=y
CONFIG_SND_SOC_CS35L40=y
CONFIG_SND_SOC_SAMSUNG=y

# NFC — Samsung sec-nfc
# CONFIG_NFC_SEC=y  # verify symbol name in exynos9820 tree

# Storage — UFS 2.1
CONFIG_SCSI_UFSHCD=y
CONFIG_SCSI_UFSHCD_PLATFORM=y
CONFIG_SCSI_UFS_EXYNOS=y

# Filesystems
CONFIG_EXT4_FS=y
CONFIG_F2FS_FS=y

# Device nodes
CONFIG_DEVTMPFS=y
CONFIG_DEVTMPFS_MOUNT=y

# Security — enable where supported by exynos9820 tree
CONFIG_SECURITY=y
CONFIG_SECURITY_APPARMOR=y
CONFIG_SECCOMP=y
CONFIG_USER_NS=y
CONFIG_NET_NS=y
CONFIG_PID_NS=y
CONFIG_IPC_NS=y
CONFIG_UTS_NS=y

# Namespaces (for Nuxel sandbox)
CONFIG_NAMESPACES=y

# NOTE: The following mustang/gs501/6.12-only symbols are NOT set here:
# CONFIG_DRM_POWERVR (PowerVR — mustang GPU only)
# CONFIG_DRM_PANEL_SAMSUNG_AMB655X (mustang display only)
# CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791 (mustang touch only)
# CONFIG_MHI_BUS_PCI_GENERIC (mustang modem only)
# CONFIG_MHI_SAMSUNG_EXYNOS5500 (mustang modem only)
# CONFIG_BRCMFMAC_BCM4390 (mustang WiFi chip, different from BCM4375)
# CONFIG_SND_SOC_CS35L45 (mustang audio amp, different from CS35L40)
# CONFIG_SND_SOC_CS42L43 (mustang audio codec, different from CS47L93)
```

Annotate every symbol that cannot exist in the exynos9820 tree with a comment
explaining why (e.g., "6.12-only symbol not present in linux-postmarketos-exynos9820").

#### `kernel/s10plus/build-kernel.sh`

```bash
#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ Kernel Build Wrapper — linux-postmarketos-exynos9820
# Device: Samsung Galaxy S10+ (SM-G975F), codename beyond2lte
# Kernel: linux-postmarketos-exynos9820 (close-to-mainline Exynos 9820)
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE_KEY="s10plus"
DEVICE_DIR="s10plus"
KOUT="${NUXEL_ROOT}/kernel/s10plus/.build/out"
KSRC="${NUXEL_ROOT}/kernel/s10plus/.build/src"
PATCHES="${NUXEL_ROOT}/kernel/s10plus/patches"
DEFCONFIG="${NUXEL_ROOT}/kernel/s10plus/defconfig"

CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
JOBS="${JOBS:-$(nproc)}"

# pmOS kernel repo
PMOS_KERNEL_REPO="https://github.com/postmarketOS/linux-postmarketos"
PMOS_KERNEL_BRANCH="exynos9820"
# Fallback: Samsung OSRC kernel
# SAMSUNG_KERNEL_REPO="https://opensource.samsung.com/..."  # operator must download manually

echo "[nuxel-s10plus-kernel] Device: ${DEVICE_KEY} (beyond2lte, Exynos 9820)"
echo "[nuxel-s10plus-kernel] Kernel: linux-postmarketos-exynos9820"
echo "[nuxel-s10plus-kernel] Cross:  ${CROSS_COMPILE}"
echo "[nuxel-s10plus-kernel] Output: ${KOUT}"

# Parse args
DO_CLONE=0; DO_BUILD=1; DO_CLEAN=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) grep '^#' "$0" | head -10; exit 0 ;;
        --clone)   DO_CLONE=1; shift ;;
        --clean)   DO_CLEAN=1; shift ;;
        --jobs)    JOBS="$2"; shift 2 ;;
        --cross)   CROSS_COMPILE="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

mkdir -p "${KOUT}" "${KSRC}"

# Step 1 — Clone kernel source
if [[ $DO_CLONE -eq 1 ]] || [[ ! -d "${KSRC}/.git" ]]; then
    echo "[kernel] Cloning linux-postmarketos-exynos9820..."
    git clone --depth=1 -b "${PMOS_KERNEL_BRANCH}" \
        "${PMOS_KERNEL_REPO}" "${KSRC}" || {
        echo "[kernel] ERROR: Clone failed. Check network or use Samsung OSRC kernel manually."
        echo "[kernel] Samsung OSRC: https://opensource.samsung.com (search SM-G975F)"
        exit 1
    }
fi

# Step 2 — Apply Nuxel patches
echo "[kernel] Applying Nuxel patches from ${PATCHES}/..."
for patch in "${PATCHES}"/*.patch; do
    [[ -f "$patch" ]] || continue
    echo "[kernel] Applying: $(basename "$patch")"
    git -C "${KSRC}" apply "$patch" || {
        echo "[kernel] WARN: Patch $(basename "$patch") did not apply cleanly."
        echo "[kernel] This may be expected if Nuxel phone features are 6.12-specific."
        echo "[kernel] See ${PATCHES}/$(basename "$patch" .patch).README for details."
    }
done

# Step 3 — Merge defconfig
echo "[kernel] Merging defconfig..."
cp "${KSRC}/arch/arm64/configs/exynos9820_defconfig" "${KSRC}/.config" 2>/dev/null || \
    make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" exynos9820_defconfig
"${KSRC}/scripts/kconfig/merge_config.sh" -m \
    "${KSRC}/.config" "${DEFCONFIG}"
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" olddefconfig

# Step 4 — Build
echo "[kernel] Building Image.gz + DTBs (jobs=${JOBS})..."
make -C "${KSRC}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    O="${KOUT}" -j"${JOBS}" \
    Image.gz dtbs

echo "[kernel] Done."
echo "[kernel] Image.gz: ${KOUT}/arch/arm64/boot/Image.gz"
echo "[kernel] DTBs:     ${KOUT}/arch/arm64/boot/dts/exynos/"
ls -lh "${KOUT}/arch/arm64/boot/Image.gz" 2>/dev/null || \
    echo "[kernel] WARN: Image.gz not found — build may have failed."
```

#### `kernel/s10plus/patches/README.md`

Document:
- Which Nuxel patches from `kernel/google-pixel-10-pro-xl/patches/` port
  cleanly to the exynos9820 tree and which do not (with reason).
- The Nuxel `drivers/nuxel/` patch (0001-nuxel-phone-features) may use GKI
  6.12-specific kernel symbols — create a stub patch with `TODO: port` if it
  does not apply cleanly.
- Include the command to check: `git apply --check kernel/s10plus/patches/0001*.patch`

#### `kernel/s10plus/README-toolchain.md`

Document:
- Toolchain: `aarch64-linux-gnu-gcc-10` (same as chiffathefox/u-boot requirement)
- Install: `sudo apt install gcc-10-aarch64-linux-gnu` (Debian/Ubuntu)
- macOS: use a prebuilt `aarch64-linux-gnu` cross toolchain from Homebrew
  (`brew tap messense/macos-cross-toolchains && brew install aarch64-unknown-linux-gnu`)
- Kernel source: `linux-postmarketos-exynos9820` from pmOS GitHub
- Samsung OSRC alternative: `https://opensource.samsung.com` (search SM-G975F)

**Acceptance:** `bash kernel/s10plus/build-kernel.sh --help` prints context
correctly. `bash -n kernel/s10plus/build-kernel.sh` passes. Running with
`--clone` + network + toolchain produces `Image.gz` and a
`exynos9820-beyond2lte.dtb` DTB, never touching `kernel/google-pixel-10-pro-xl/`.

---

### TASK 6 — Boot image packer, U-Boot chainload, and flash/recovery scripts (`boot/s10plus/`)

#### `boot/s10plus/pack-boot-v1.sh`

Implement a **legacy Android boot image header v1 packer** (page 2048). This
is completely separate from `images/bootpack/mkbootimg.py` (which is v3/v4
only). The v1 format:

```
Header (2048 bytes):
  magic[8]       = "ANDROID!"
  kernel_size    = <kernel image size in bytes>
  kernel_addr    = <load address>
  ramdisk_size   = <ramdisk size in bytes>
  ramdisk_addr   = <ramdisk load address>
  second_size    = 0
  second_addr    = 0
  tags_addr      = <ATAGS/DTB address>
  page_size      = 2048
  dt_size        = <DTB size or 0>
  os_version     = 0
  name[16]       = "nuxel-s10plus"
  cmdline[512]   = <kernel cmdline>
  id[8]          = 0 (SHA-1 of all pages)
  extra_cmdline[1024] = ""
Padding to page_size
kernel_data (padded to page_size)
ramdisk_data (padded to page_size)
DTB data (optional, padded to page_size)
```

Implement in Python 3 (or bash calling `dd`). Key addresses for Exynos 9820
(from pmOS beyond2lte boot.img analysis):
```
kernel_addr  = 0x80008000   # verify from real device boot.img
ramdisk_addr = 0x84000000   # verify from real device boot.img
tags_addr    = 0x80000100   # verify from real device boot.img
```
**Mark all addresses as `PLACEHOLDER — verify from real device boot.img`.**
Include a `--addresses-from-device` mode that reads a stock `boot.img` and
extracts the addresses automatically.

Usage:
```
boot/s10plus/pack-boot-v1.sh \
    --kernel kernel/s10plus/.build/out/arch/arm64/boot/Image.gz \
    --ramdisk boot/initramfs/initramfs.cpio.gz \
    --dtb kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/exynos9820-beyond2lte.dtb \
    --cmdline "earlycon=exynos4210,0x10020000 console=ttySAC0,115200 nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw" \
    --output /tmp/nuxel-beyond2lte-boot.img
```

#### `boot/s10plus/uboot-chainload.sh`

```bash
#!/usr/bin/env bash
# Clones, builds, and flashes chiffathefox/u-boot (exynos9820) to the S10+.
# Device must be in TWRP (adb connected).
# NEVER uses fastboot.
set -euo pipefail

UBOOT_REPO="https://github.com/chiffathefox/u-boot"
UBOOT_BRANCH="exynos9820"
UBOOT_BUILD_DIR="$(pwd)/kernel/s10plus/.build/u-boot"
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
CC="${CC:-aarch64-linux-gnu-gcc-10}"

UFS_BOOT="/dev/block/platform/13d60000.ufs/by-name/boot"

echo "[uboot-chainload] Building chiffathefox/u-boot for Exynos 9820..."

# Verify S10+ connected in TWRP
DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
[ "${DEVICE_PROP}" = "beyond2lte" ] || {
    echo "ERROR: Expected beyond2lte, got '${DEVICE_PROP}'. Connect S10+ in TWRP first."
    exit 1
}

# Clone U-Boot
if [[ ! -d "${UBOOT_BUILD_DIR}/.git" ]]; then
    git clone --depth=1 -b "${UBOOT_BRANCH}" "${UBOOT_REPO}" "${UBOOT_BUILD_DIR}"
fi

# Build
cd "${UBOOT_BUILD_DIR}"
make CC="${CC}" CROSS_COMPILE="${CROSS_COMPILE}" exynos9820_defconfig
make CC="${CC}" CROSS_COMPILE="${CROSS_COMPILE}" -j"$(nproc)"

# Wrap u-boot.bin as a legacy v1 boot image for S-Boot
# S-Boot reads boot.img format; we wrap u-boot.bin as the "kernel"
python3 "$(pwd)/../../boot/s10plus/pack-boot-v1.sh" \
    --kernel u-boot.bin \
    --ramdisk /dev/null \
    --cmdline "" \
    --output /tmp/u-boot-beyond2lte.img

# Flash to /boot via TWRP dd
echo "[uboot-chainload] Flashing u-boot to ${UFS_BOOT} via TWRP..."
adb push /tmp/u-boot-beyond2lte.img /tmp/u-boot-beyond2lte.img
adb shell "dd if=/tmp/u-boot-beyond2lte.img of=${UFS_BOOT} bs=4096" && echo "[uboot-chainload] Done."
echo ""
echo "[uboot-chainload] U-Boot flashed. Reboot to verify: adb shell twrp reboot"
echo "[uboot-chainload] If the device does not boot, re-flash stock boot.img via Download Mode + heimdall."
```

#### `boot/s10plus/flash.sh`

Full implementation:

```bash
#!/usr/bin/env bash
# =============================================================================
# Nuxel Flash Script — Samsung Galaxy S10+ (beyond2lte, Exynos 9820)
# Flash method: TWRP (adb + dd) and Download Mode (Odin/heimdall)
#
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# WARNING: THIS DEVICE HAS NO fastboot. NEVER use fastboot commands here.
# Flash via: TWRP (adb shell dd) or Download Mode (Odin/heimdall only).
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Protected partitions — NEVER flash these
PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc"

UFS_BASE="/dev/block/platform/13d60000.ufs/by-name"
DEVICE_EXPECTED="beyond2lte"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log_info()  { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()    { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Required args
DEVICE_KEY=""
UBOOT_IMG=""
ROOTFS_IMG=""
ROOTFS_PARTITION="userdata"  # default target partition for rootfs
DO_SIDELOAD=0
DO_REVERT=0
STOCK_BOOT_IMG=""
DRY_RUN=0
FORCE=0

usage() {
    cat <<EOF
Usage: $0 --device s10plus [options]

Options:
  --device s10plus         REQUIRED. Refuses on any other value.
  --uboot <path>           Path to u-boot-beyond2lte.img (boot partition)
  --rootfs <path>          Path to Nuxel rootfs image (default partition: userdata)
  --rootfs-partition <name> Target partition for rootfs (default: userdata)
  --sideload               Use TWRP ADB sideload instead of adb push + dd
  --revert                 Re-flash stock boot.img via heimdall (Download Mode)
  --stock-boot <path>      Stock boot.img for --revert mode
  --dry-run                Print commands but do not execute
  --force                  Skip confirmation prompts

WARNING: NO fastboot on this device. Only TWRP (adb) and heimdall/Odin.
WARNING: Knox fuse is already tripped — do not attempt relock.
WARNING: NEVER flash: ${PROTECTED_PARTITIONS}
EOF
}

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --device) DEVICE_KEY="$2"; shift 2 ;;
        --uboot) UBOOT_IMG="$2"; shift 2 ;;
        --rootfs) ROOTFS_IMG="$2"; shift 2 ;;
        --rootfs-partition) ROOTFS_PARTITION="$2"; shift 2 ;;
        --sideload) DO_SIDELOAD=1; shift ;;
        --revert) DO_REVERT=1; shift ;;
        --stock-boot) STOCK_BOOT_IMG="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --force) FORCE=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Validate device key
[ "${DEVICE_KEY}" = "s10plus" ] || {
    log_error "--device s10plus is required. Got: '${DEVICE_KEY}'"
    log_error "This script is ONLY for the Samsung Galaxy S10+ (beyond2lte)."
    exit 1
}

log_info "Nuxel Flash — Samsung Galaxy S10+ (beyond2lte)"
log_info "Flash method: TWRP (adb+dd) | NO fastboot"

# Verify device identity
log_info "Checking connected device..."
if ! adb devices | grep -q "device$"; then
    log_error "No ADB device found. Is the S10+ in TWRP with USB debugging enabled?"
    exit 1
fi

DEVICE_PROP=$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')
DEVICE_NAME=$(adb shell getprop ro.product.name 2>/dev/null | tr -d '\r')
log_info "Connected: device='${DEVICE_PROP}' name='${DEVICE_NAME}'"

[ "${DEVICE_PROP}" = "${DEVICE_EXPECTED}" ] || {
    log_error "Device mismatch: expected '${DEVICE_EXPECTED}', got '${DEVICE_PROP}'"
    log_error "REFUSING TO FLASH. Connect the correct S10+ (beyond2lte) device."
    exit 1
}
log_ok "Device identity verified: ${DEVICE_PROP}"

# Verify protected partitions are present (we will skip them)
log_info "Protected partitions (will never be touched): ${PROTECTED_PARTITIONS}"

# Validate partition target
for p in ${PROTECTED_PARTITIONS}; do
    [ "${ROOTFS_PARTITION}" = "${p}" ] && {
        log_error "ROOTFS_PARTITION='${p}' is a protected partition. Refusing."
        exit 1
    }
done

# Revert mode
if [[ $DO_REVERT -eq 1 ]]; then
    log_warn "REVERT MODE: Re-flashing stock boot.img via heimdall (Download Mode)"
    log_warn "You must have the device in Download Mode (Vol Down + Bixby + Power)"
    [ -n "${STOCK_BOOT_IMG}" ] || { log_error "--stock-boot required for --revert"; exit 1; }
    [ -f "${STOCK_BOOT_IMG}" ] || { log_error "Stock boot image not found: ${STOCK_BOOT_IMG}"; exit 1; }
    log_info "Command: heimdall flash --BOOT '${STOCK_BOOT_IMG}'"
    [[ $DRY_RUN -eq 0 ]] && heimdall flash --BOOT "${STOCK_BOOT_IMG}" || \
        log_info "[dry-run] heimdall flash --BOOT ${STOCK_BOOT_IMG}"
    log_ok "Revert complete."
    exit 0
fi

# Sideload mode
if [[ $DO_SIDELOAD -eq 1 ]]; then
    log_info "SIDELOAD MODE: Use TWRP ADB Sideload"
    log_info "In TWRP: Advanced → ADB Sideload → Swipe to start"
    log_info "Then run: adb sideload <nuxel-s10plus.zip>"
    log_warn "Sideload ZIP creation not yet implemented. Create via pmbootstrap or manually."
    exit 0
fi

# Normal flash mode
log_info "Normal flash mode: adb push + dd"
[[ -n "${UBOOT_IMG}" ]] || { log_warn "No --uboot specified; skipping boot partition flash."; }
[[ -n "${ROOTFS_IMG}" ]] || { log_warn "No --rootfs specified; skipping rootfs flash."; }

# Flash U-Boot to boot partition
if [[ -n "${UBOOT_IMG}" ]]; then
    [ -f "${UBOOT_IMG}" ] || { log_error "U-Boot image not found: ${UBOOT_IMG}"; exit 1; }
    log_info "Flashing U-Boot: ${UBOOT_IMG} → ${UFS_BASE}/boot"
    [[ $FORCE -eq 0 ]] && read -rp "Confirm flash U-Boot to /boot? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
    if [[ $DRY_RUN -eq 0 ]]; then
        adb push "${UBOOT_IMG}" /tmp/nuxel-uboot.img
        adb shell "dd if=/tmp/nuxel-uboot.img of=${UFS_BASE}/boot bs=4096"
        log_ok "U-Boot flashed to ${UFS_BASE}/boot"
    else
        log_info "[dry-run] adb push ${UBOOT_IMG} /tmp/nuxel-uboot.img"
        log_info "[dry-run] adb shell dd if=/tmp/nuxel-uboot.img of=${UFS_BASE}/boot bs=4096"
    fi
fi

# Flash rootfs
if [[ -n "${ROOTFS_IMG}" ]]; then
    [ -f "${ROOTFS_IMG}" ] || { log_error "Rootfs image not found: ${ROOTFS_IMG}"; exit 1; }
    log_info "Flashing rootfs: ${ROOTFS_IMG} → ${UFS_BASE}/${ROOTFS_PARTITION}"
    log_warn "This will OVERWRITE /${ROOTFS_PARTITION} — ensure backups exist."
    [[ $FORCE -eq 0 ]] && read -rp "Confirm flash rootfs to /${ROOTFS_PARTITION}? [y/N] " c && [[ "$c" =~ ^[Yy]$ ]] || true
    if [[ $DRY_RUN -eq 0 ]]; then
        adb push "${ROOTFS_IMG}" /tmp/nuxel-rootfs.img
        adb shell "dd if=/tmp/nuxel-rootfs.img of=${UFS_BASE}/${ROOTFS_PARTITION} bs=4096"
        log_ok "Rootfs flashed to ${UFS_BASE}/${ROOTFS_PARTITION}"
    else
        log_info "[dry-run] adb push ${ROOTFS_IMG} /tmp/nuxel-rootfs.img"
        log_info "[dry-run] adb shell dd if=/tmp/nuxel-rootfs.img of=${UFS_BASE}/${ROOTFS_PARTITION} bs=4096"
    fi
fi

log_ok "Flash complete."
log_info "Reboot: adb shell twrp reboot"
log_info "If it does not boot, enter Download Mode (Vol Down + Bixby + Power)"
log_info "and re-flash stock: heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5"
```

#### `boot/s10plus/recovery.sh`

Implement a recovery helper that:
- Documents the Download Mode key combo (Vol Down + Bixby + Power on S10+)
- Provides the `heimdall flash` command to restore all four Samsung firmware
  partitions (BL, AP, CP, CSC) from the stock firmware tarballs
- Provides the TWRP re-flash path via ADB sideload
- Explicitly states there is no `fastboot` recovery path on this device

#### `boot/s10plus/boot-config.txt`

```
# Nuxel S10+ Boot Configuration
# S-Boot → U-Boot (exynos9820) → linux-postmarketos-exynos9820 → Nuxel
# Boot image format: legacy Android boot image header v1 (page 2048)
# Flash path: TWRP adb+dd (NO fastboot)

device=s10plus
codename=beyond2lte
ufs_path=/dev/block/platform/13d60000.ufs/by-name

# U-Boot source: https://github.com/chiffathefox/u-boot branch exynos9820
# U-Boot defconfig: exynos9820_defconfig

# Kernel load addresses (VERIFY from real device stock boot.img):
kernel_addr=PLACEHOLDER_0x80008000
ramdisk_addr=PLACEHOLDER_0x84000000
tags_addr=PLACEHOLDER_0x80000100
page_size=2048

# Kernel cmdline (fill placeholders from device inventory):
cmdline_base="earlycon=exynos4210,0x10020000 console=ttySAC0,115200 nuxel.device=s10plus"
cmdline_root="root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw"

# Protected partitions — NEVER flash:
# efs efsg persist param up_param steady keystorage carrier cp_debug misc

# Recovery: Download Mode (Vol Down + Bixby + Power)
# heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
```

**Acceptance:** `bash boot/s10plus/flash.sh --help` prints the TWRP sequence
and all safety warnings. `bash -n boot/s10plus/flash.sh` passes. The script
exits early without a connected S10+ and never references mustang partitions
or `fastboot`.

---

### TASK 7 — S10+ rootfs/boot build orchestration (`images/s10plus/build.sh`)

Create `images/s10plus/build.sh` that:

1. Sources `tools/nuxel-device-select.sh` and verifies `NUXEL_DEVICE_KEY=s10plus`.
2. Checks for required inputs:
   - `kernel/s10plus/.build/out/arch/arm64/boot/Image.gz`
   - A valid DTB at `kernel/s10plus/.build/out/arch/arm64/boot/dts/exynos/`
   - `boot/initramfs/initramfs.cpio.gz` (shared)
3. Calls `boot/s10plus/pack-boot-v1.sh` to build the U-Boot and Nuxel boot images.
4. Calls `images/mkrootfs.sh` (device-agnostic) to assemble the Nuxel userspace.
5. Installs S10+-specific firmware from `firmware/s10plus/blobs/` into the
   rootfs staging area.
6. Installs S10+-specific device configs from `configs/s10plus/` into the rootfs.
7. Installs S10+-specific kernel modules from `kernel/s10plus/.build/out/` into
   the rootfs `/lib/modules/`.
8. Produces all artifacts in `build/out/s10plus/`:
   - `u-boot-beyond2lte.img` (U-Boot wrapped as v1 boot.img)
   - `nuxel-beyond2lte-boot.img` (Nuxel kernel + initramfs as v1 boot.img)
   - `nuxel-beyond2lte-rootfs.img` (ext4 rootfs image for `userdata`)
   - `build-manifest.json` (device key, kernel commit, build timestamp)
9. Does NOT emit a dm-verity/AVB-signed image for Phase 1 (document why in a comment).
10. Does NOT touch `build/out/mustang/` or any mustang artifacts.

**Acceptance:** `NUXEL_DEVICE=s10plus bash images/s10plus/build.sh --help`
prints S10+ context; the script emits artifacts under `build/out/s10plus/` and
never touches `build/out/mustang/`.

---

### TASK 8 — S10+ device configs (`configs/s10plus/`)

#### `configs/s10plus/display/nuxel-s10plus-display.sh`

```bash
#!/usr/bin/env bash
# Set 3040×1440 display mode for S6E3HA9 AMOLED panel on S10+
# Requires wlr-randr and a running Wayland/Phosh session

DISPLAY_W=1440
DISPLAY_H=3040
OUTPUT="${NUXEL_DISPLAY_OUTPUT:-DSI-1}"

echo "[display] Setting ${DISPLAY_W}x${DISPLAY_H} on ${OUTPUT} (S6E3HA9 AMOLED beyond2lte)"
wlr-randr --output "${OUTPUT}" --mode "${DISPLAY_W}x${DISPLAY_H}" || {
    echo "[display] WARN: wlr-randr failed. Display node may not be ready yet."
    echo "[display] Verify: ls /sys/class/drm/ (look for Samsung S6E3HA9 panel)"
}
```

#### `configs/s10plus/libinput/99-nuxel-beyond2lte-touch.conf`

```ini
# Samsung S6SY761 sec_ts touch calibration for S10+ (3040×1440)
# Device: Samsung Galaxy S10+ (beyond2lte)
# Touch controller: S6SY761 (sec_ts), I2C hsi2c_10 @ 0x48

Section "InputClass"
    Identifier "nuxel-s10plus-touch"
    MatchIsTouchscreen "on"
    MatchDevicePath "/dev/input/event*"
    # S6SY761 presents as "sec_touchscreen" in kernel
    MatchProduct "sec_touchscreen"
    Driver "libinput"
    Option "TransformationMatrix" "1 0 0 0 1 0 0 0 1"
    # Calibration values — fill from real device (libinput debug-events)
    # Option "CalibrationMatrix" "UNKNOWN UNKNOWN UNKNOWN UNKNOWN UNKNOWN UNKNOWN"
EndSection
```

#### `configs/s10plus/alsa-ucm/`

Create a stub UCM directory structure:
```
configs/s10plus/alsa-ucm/
├── README.md       — Document CS47L93 + CS35L40 topology; reference pmOS for UCM2 start
└── SamsungBeyond2/ — (stub)
    ├── HiFi.conf   — Stub UCM2 profile for CS47L93 MADERA codec
    └── SamsungBeyond2.conf — Master UCM file linking HiFi
```

`README.md` must note:
- CS47L93 requires `madera` ASoC kernel support and DSP firmware loaded via
  `cs47l93-dsp1-*.wmfw` files
- CS35L40 amps require `cs35l40-dsp*.wmfw` firmware
- UCM routing must be built from real device `tinymix` output via TWRP
- Reference: postmarketOS UCM2 for madera-family devices

#### `configs/s10plus/modem/README.md`

```markdown
# S10+ Shannon LTE Modem — Status

The Samsung Shannon LTE modem (integrated into Exynos 9820) is NOT ready for
ModemManager in Nuxel Phase 1. There is no upstream ModemManager plugin for
the Shannon LTE modem interface.

Phase 1 target: WiFi only. No voice/SMS/data via cellular modem.
Phase 7 (stretch goal): Explore Shannon LTE interface; implement MM plugin.

The modem CP firmware lives in the `modem` partition. DO NOT flash or modify
the modem partition without explicit Phase 7 guidance.

The `efs` and `efsg` partitions hold per-unit IMEI and baseband calibration.
NEVER flash or wipe these partitions.
```

#### `configs/s10plus/pipewire/` and `configs/s10plus/wireplumber/`

Create stub configs that:
- Reference the CS47L93 ALSA card name (TBD from real device `aplay -l`)
- Set a safe default sample rate (48000 Hz, 2ch stereo) as a placeholder
- Document the required ALSA UCM profile path

**Acceptance:** All configs exist under `configs/s10plus/`, are device-keyed,
contain no mustang display/touch/audio values anywhere.

---

### TASK 9 — Operator device-inventory template and build gate

#### `docs/s10plus-device-inventory.md`

Create a comprehensive operator template for Phase 0 data collection:

```markdown
# S10+ Device Inventory Template (Phase 0)
# Fill via TWRP adb session on the physical device BEFORE running any build

## Phase 0 Collection Commands

# Verify device identity
adb shell getprop ro.product.device    # must be: beyond2lte
adb shell getprop ro.product.name      # e.g.: beyond2ltexx
adb shell getprop ro.product.model     # e.g.: SM-G975F

# SoC / hardware identity
adb shell getprop | grep -iE 'ro.product|ro.hardware|ro.board|exynos'
adb shell cat /proc/cmdline
adb shell cat /proc/cpuinfo | head -30

# Full dmesg (critical for driver discovery)
adb shell dmesg > s10plus-dmesg-$(date +%Y%m%d-%H%M%S).txt

# Input / touch identification
adb shell getevent -pl 2>/dev/null > s10plus-input-devices.txt

# Partition table
adb shell ls -la /dev/block/platform/13d60000.ufs/by-name/
adb shell cat /proc/partitions

# Vendor firmware file listing (critical for firmware/s10plus/manifest.yml)
adb shell ls -laR /vendor/firmware/ > s10plus-vendor-firmware.txt
adb shell ls -laR /vendor/lib/modules/ > s10plus-vendor-modules.txt
adb shell ls -laR /vendor/etc/firmware/ > s10plus-vendor-etc-firmware.txt

# Audio card discovery
adb shell cat /proc/asound/cards
adb shell ls /sys/class/sound/

# WiFi firmware filenames (critical — filename varies by subvariant)
adb shell ls /vendor/firmware/bcm4375*
adb shell ls /vendor/firmware/BCM4375*
adb shell ls /vendor/firmware/brcm*

# Kernel boot addresses (extract from stock boot.img)
adb pull /dev/block/platform/13d60000.ufs/by-name/boot /tmp/stock-boot.img
# Then: python3 tools/read-boot-header-v1.py /tmp/stock-boot.img

## Fill these fields after collection:
DEVICE_VARIANT:     UNKNOWN — fill from ro.product.name
BOOTLOADER_VERSION: UNKNOWN — fill from getprop ro.bootloader
ANDROID_BUILD:      UNKNOWN — fill from getprop ro.build.id
KERNEL_ADDR:        PLACEHOLDER — extract from stock boot.img header
RAMDISK_ADDR:       PLACEHOLDER — extract from stock boot.img header
TAGS_ADDR:          PLACEHOLDER — extract from stock boot.img header
SENSOR_HUB:         UNKNOWN — identify from dmesg / getevent
CAMERA_FRONT:       UNKNOWN — identify from dmesg
CAMERA_REAR:        UNKNOWN — identify from dmesg
WIFI_FW_FILENAME:   UNKNOWN — list from /vendor/firmware/bcm4375*
BT_HCD_FILENAME:    UNKNOWN — list from /vendor/firmware/BCM4375*
TOUCH_FW_PATH:      UNKNOWN — list from /vendor/firmware/tsp_sec/
AUDIO_UCM_CARD:     UNKNOWN — collect from aplay -l in TWRP
```

Also add a `tools/read-boot-header-v1.py` script that reads a v1 `boot.img`
and prints the kernel/ramdisk/tags load addresses and cmdline.

#### Gate implementation

Wire the following gate into every S10+ build/flash script:

```bash
_check_s10plus_inventory() {
    local inventory="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
    # Check if UNKNOWN placeholders are still present in critical fields
    if grep -q "KERNEL_ADDR:.*PLACEHOLDER" "${inventory}" 2>/dev/null; then
        echo "ERROR: S10+ device inventory is incomplete."
        echo "       Run Phase 0 collection commands in docs/s10plus-device-inventory.md"
        echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME"
        echo "       Then re-run this script."
        exit 1
    fi
}
```

---

### TASK 10 — Documentation

#### `docs/s10plus-bringup.md`

Create comprehensive documentation (minimum 300 lines) covering:

1. **Multi-device model** — how `NUXEL_DEVICE` / `--device` works; the three
   device keys and their directories.
2. **S10+ boot chain** — detailed S-Boot → U-Boot → Linux diagram with
   explanation of why S-Boot requires U-Boot chainloading.
3. **TWRP/heimdall flash model** — why there is no `fastboot`; how to enter
   TWRP and Download Mode; the full flash sequence.
4. **Knox reality** — what Knox-tripped means, what it does NOT mean
   (device is fully functional for our purposes), what is permanently unavailable.
5. **Protected partitions** — list and explain why each must never be touched.
6. **Phase 0 device inventory** — why it is required before any build.
7. **Exact build commands** for S10+:
   ```bash
   # Phase 0: inventory
   # Phase 1: U-Boot + kernel
   NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
   bash boot/s10plus/uboot-chainload.sh
   # Phase 2: rootfs
   NUXEL_DEVICE=s10plus bash images/s10plus/build.sh
   # Flash
   NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
       --device s10plus \
       --uboot build/out/s10plus/u-boot-beyond2lte.img \
       --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
   ```
8. **Anti-cross-flash rules** — explicit table showing which dirs are S10+ only.
9. **Driver status matrix** — honest table with ✅/🚧/⬜/❌ for each subsystem.
10. **Recovery path** — Download Mode + heimdall full stock restore.

#### Update `README.md`

Add a "Multi-Device Targets" section above the existing "Hardware Target" section:

```markdown
## Multi-Device Targets

Nuxel supports multiple hardware targets. Select via `NUXEL_DEVICE` or `--device`:

| Key | Device | Codename | Status |
|---|---|---|---|
| `mustang` | Google Pixel 10 Pro XL | mustang | Scaffold (0% flashable) |
| `s10plus` | Samsung Galaxy S10+ (Exynos) | beyond2lte | Bring-up in progress |
| `g7power` | Motorola Moto G7 Power | ocean | Stub only |

See `docs/s10plus-bringup.md` for S10+ bring-up guide.
```

#### Update `QUICKSTART.md`

Add a "S10+ Quick Start" section after the existing Pixel section. Reference
the Phase 0 inventory step and `docs/s10plus-bringup.md`.

---

### TASK 11 — G7 Power stub slots (for tree consistency)

Create minimal stubs in all per-device directories for `g7power`:
- `firmware/g7power/manifest.yml` — `device: g7power`, all `UNKNOWN`
- `firmware/g7power/install-firmware.sh` — stub with `--help`
- `firmware/g7power/verify-firmware.sh` — stub
- `kernel/g7power/defconfig` — comment-only stub, SDM632/MSM8953 note
- `kernel/g7power/build-kernel.sh` — stub referencing `msm8953-mainline/linux`
- `kernel/g7power/patches/README.md` — stub
- `device/g7power/deviceinfo` — stub with SDM632/ocean facts from `docs/hardware-ids.md`
- `device/g7power/APKBUILD` — stub
- `boot/g7power/flash.sh` — stub (fastboot + lk2nd + EDL path)
- `boot/g7power/recovery.sh` — stub
- `configs/g7power/` — empty subdirs with `README.md` placeholders

---

## ACCEPTANCE CRITERIA (definition of done)

1. `make validate` / `NUXEL_DEVICE=mustang bash images/build.sh --quick` and
   all three UTM VM verify suites still pass (mustang path unbroken).
2. `NUXEL_DEVICE=s10plus` selects only `s10plus` directories everywhere.
3. `grep -r "mustang" s10plus/ 2>/dev/null` returns no device coupling
   (only documented cross-references in comments are acceptable).
4. `grep -r "fastboot" boot/s10plus/ 2>/dev/null` returns nothing.
5. S10+ flash script (`boot/s10plus/flash.sh`) refuses on device mismatch,
   uses no `fastboot`, and provides a one-command revert via `heimdall`.
6. No fabricated checksums or firmware blobs: all unknowns are
   `UNKNOWN`/`PLACEHOLDER` with real-device collection steps documented.
7. All new shell scripts pass `bash -n` and `shellcheck -S warning`.
8. Build/flash scripts print the resolved device key and abort on missing
   per-device inputs.
9. `docs/s10plus-bringup.md` exists and is consistent with this prompt and
   `s10plus-requirements.md`.
10. Protected partitions (`efs`, `efsg`, `persist`, `param`, `up_param`,
    `steady`, `keystorage`, `carrier`, `cp_debug`, `misc`) are never touched
    by any script.

---

## THINGS YOU MUST NOT DO (absolute)

- Do not claim the S10+ or mustang path is "flashable" or "verified" until
  real device inventory + real firmware + real kernel build are complete.
- Do not emit `fastboot` commands for the S10+ (Samsung Exynos has no fastboot).
- Do not reuse Pixel/BCM4390/PowerVR/AMB655X/gs501/Tensor G5 firmware for the S10+.
- Do not relock the bootloader or attempt to restore Knox.
- Do not touch `efs`/`efsg`/`persist`/`param`/`up_param`/`steady`/`keystorage`/
  `carrier`/`cp_debug`/`misc` in any script, ever.
- Do not delete or overwrite mustang files without preserving a working path.
- Do not fabricate checksums, load addresses, firmware filenames, or driver status.
- Do not use `#!/bin/sh` with bashisms — use `#!/usr/bin/env bash` for all new scripts.
- Do not merge S10+ and mustang device-specific content into any shared file.

---

## DELIVERABLES SUMMARY

```
device/s10plus/deviceinfo
device/s10plus/APKBUILD
device/s10plus/90-nuxel-beyond2lte.rules
device/s10plus/nuxel-beyond2lte.conf

firmware/s10plus/manifest.yml
firmware/s10plus/install-firmware.sh   (--list-files, --twrp-pull, --verify-only, --install)
firmware/s10plus/verify-firmware.sh
firmware/s10plus/blobs/               (empty; filled by --twrp-pull or operator)

kernel/s10plus/defconfig              (Exynos 9820 / pmOS fragment)
kernel/s10plus/build-kernel.sh        (clones linux-postmarketos-exynos9820)
kernel/s10plus/patches/               (Nuxel patch or TODO stub)
kernel/s10plus/README-toolchain.md

boot/s10plus/pack-boot-v1.sh          (legacy v1 boot image packer)
boot/s10plus/uboot-chainload.sh       (clone/build/flash chiffathefox/u-boot)
boot/s10plus/flash.sh                 (TWRP adb+dd; NO fastboot)
boot/s10plus/recovery.sh              (TWRP + heimdall recovery)
boot/s10plus/boot-config.txt

configs/s10plus/display/nuxel-s10plus-display.sh
configs/s10plus/libinput/99-nuxel-beyond2lte-touch.conf
configs/s10plus/alsa-ucm/README.md + SamsungBeyond2/ stub
configs/s10plus/modem/README.md
configs/s10plus/pipewire/ (stub)
configs/s10plus/wireplumber/ (stub)

images/s10plus/build.sh

tools/nuxel-device-select.sh          (shared; sources into all scripts)
tools/read-boot-header-v1.py          (reads stock boot.img v1 header)

docs/s10plus-bringup.md
docs/s10plus-device-inventory.md      (Phase 0 operator template + gate)

device/g7power/ + firmware/g7power/ + kernel/g7power/ +
boot/g7power/ + configs/g7power/ + images/g7power/  (stubs)

Updated: README.md, QUICKSTART.md
Updated: boot/initramfs/init.sh       (s10plus A-only UFS root probe)
Moved:   firmware/* → firmware/google-pixel-10-pro-xl/
Moved:   kernel/defconfig + patches/ → kernel/google-pixel-10-pro-xl/
Moved:   device/deviceinfo + APKBUILD → device/google-pixel-10-pro-xl/
Moved:   boot/flash.sh + recovery.sh → boot/google-pixel-10-pro-xl/
Moved:   configs/{display,libinput,alsa-ucm,modem,pipewire,wireplumber}/
              → configs/google-pixel-10-pro-xl/{...}
```

---

*Nuxel v0.2.0 — Build the bunker first. Add the rave lights later.*
*S10+ bring-up: Phase 0 starts with the device already in TWRP. That's your foundation.*
