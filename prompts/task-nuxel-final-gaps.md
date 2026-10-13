You are completing the final missing pieces of the Nuxel phone OS for Google Pixel 10 Pro XL (mustang). Serial 58211FDCQ001LA, HW MP1.0, SKU G45RY. Tensor G5 SoC.

Read the two reference documents first:
1. `/workspace/Fonux, NuDroid, and the Best Path to a Linux-Only PWA-First Smartphone.md`
2. `/workspace/Building a Post-Android Phone OS on Existing Android Hardware.pdf`

## CURRENT STATE
The project has 145 files across 58 directories. Core build system, configs, kernel defconfig, flash scripts, PWA apps (6 total), native GTK4 shell apps (4), nuxel-bridge D-Bus service, notifications daemon, all docs, bootloader unlock guide, and driver status matrix are all complete and targeted to mustang.

## MISSING PIECES TO BUILD

### 1. OpenRC Init Scripts for Alpine
Create `/shell/config/openrc/` directory with init scripts for:
- `nuxel-bridge` — starts the bridge D-Bus service
- `nuxel-notifications` — starts the notification daemon  
- `nuxel-firstboot` — runs on first boot only, sets up user
Each script needs: `#!/sbin/openrc-run`, proper `depend()`, `start()`, `stop()` functions.

### 2. postmarketOS Device Package (APKBUILD)
Create `/device/APKBUILD` for mustang:
```bash
pkgname=device-google-mustang
pkgver=0.2.0
pkgrel=0
pkgdesc="Google Pixel 10 Pro XL (mustang)"
arch="aarch64"
```
Include the proper `package()` function that installs the nuxel device-info, hooks, and kernel config.

### 3. First-Boot Setup System
Create `/shell/nuxel-shell/nuxel-firstboot/` with a Python+Gtk script that:
- Runs on first boot (detected by `/etc/nuxel/.firstboot` marker)
- Welcomes user to Nuxel
- Prompts for: username, display name, WiFi network connection
- Creates the nuxel user account
- Removes the `.firstboot` marker when done

### 4. Basic Validation Script
Create `/ci/validate-build.sh` that checks:
- boot.img has correct magic bytes (ANDROID!)
- vbmeta.img is present with verification disabled
- init_boot.img exists (required on mustang)
- DTBO image exists
- All PWA apps have valid manifest.json
- Kernel defconfig contains mustang-specific configs
- Flash script references correct device serial

### 5. Phosh Launcher Integration
Create `/shell/config/phosh/nuxel-phosh-override.ini` that:
- Sets the nuxel-home PWA as default launcher
- Configures the 3120x1440@120 display
- Sets proper gesture mappings for mobile use
- Disables unnecessary desktop components

### 6. postmarketOS deviceinfo file
Create `/device/deviceinfo` with all mustang-specific device info in the format postmarketOS expects:
```
deviceinfo_format_version="2"
deviceinfo_name="Google Pixel 10 Pro XL"
deviceinfo_manufacturer="Google"
deviceinfo_codename="mustang"
deviceinfo_year="2025"
deviceinfo_arch="aarch64"
deviceinfo_chassis="handset"
... (all standard pmOS deviceinfo fields)
```

### 7. Recovery/Failsafe Boot Mode
Create `/boot/recovery.sh` — a minimal script that boots to a recovery shell if the main boot fails. Include:
- How to enter recovery (hold Volume Up + Power on boot)
- Basic diagnostic commands (check partitions, mount root, view logs)
- How to re-flash from recovery
- Emergency shell with busybox

### 8. Install/firmware extraction helper
Create `/firmware/install-firmware.sh` that automates extracting firmware from a Google factory image:
- Takes factory image zip path as argument
- Extracts all required firmware blobs
- Installs them to correct /lib/firmware paths
- Verifies checksums
- Reports which blobs are still missing

## RULES
1. Create real, functional code — no TODOs or stubs
2. All OpenRC scripts must follow the OpenRC specification
3. The APKBUILD must be valid Alpine/postmarketOS format
4. The first-boot setup must work with Phosh on mustang
5. The validation script must exit with non-zero on failures
6. Reference the exact device serial (58211FDCQ001LA) where appropriate
7. Do not modify existing files unless necessary
8. Continue until all 8 items are complete
