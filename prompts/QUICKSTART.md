# Nuxel Quickstart Guide

**v0.2.0 — Design scaffold + code prototype. Not a flashable OS.**

## Flashable ready state

**❌ NOT READY TO FLASH — all targets** (Nuxel v0.2.0, deep-analyze 2026-08-29).

| Target | Device key | Ready? | Blocking |
|---|---|---|---|
| Google Pixel 10 Pro XL | `mustang` | ❌ No | No kernel build, 0/30 firmware blobs, no `boot.img`/`vbmeta.img` set |
| Samsung Galaxy S10+ (Exynos) | `s10plus` | ❌ No | Phase 0 inventory + U-Boot + kernel + firmware extraction |
| Motorola Moto G7 Power | `g7power` | ❌ No | Phase 0 inventory + lk2nd + kernel + firmware extraction |

No device has a real, verified boot-image set yet: no per-device kernel has
been compiled (`kernel/*/.build/out/Image.gz` absent), no firmware blobs are
installed, and no physical flash has been performed. The sections below
document the correct procedure for when those gates pass.

> ⛔ **DO NOT FLASH TO HARDWARE.** The build produces zero-filled dev stubs for
> init_boot.img, vendor_boot.img, and dtbo.img. Real mustang boot requires kernel
> compilation, DTBO generation, AVB signing, and firmware extraction — none of
> which are automated yet. See README.md for the honest 10-area status matrix.



---

## Kiosk Mode — Auto-Launch Nuxel Home Fullscreen

After login, Phosh auto-opens Nuxel Home in kiosk (no browser chrome):

```bash
cd ~/nuxel

# Install Chromium
sudo dnf install -y chromium

# Install the kiosk launcher
mkdir -p ~/bin
cp shell/nuxel-kiosk/nuxel-home-kiosk ~/bin/
chmod +x ~/bin/nuxel-home-kiosk

# Install desktop entry (appears in Phosh app drawer)
mkdir -p ~/.local/share/applications
sed "s|/home/wicked|$HOME|g" shell/config/nuxel-home.desktop   > ~/.local/share/applications/nuxel-home.desktop

# Install systemd user service (auto-launch on login)
mkdir -p ~/.config/systemd/user
sed "s|/home/wicked|$HOME|g" shell/config/systemd-user/nuxel-home-kiosk.service   > ~/.config/systemd/user/nuxel-home-kiosk.service

# Set up Wayland environment for user services
dbus-update-activation-environment --systemd   WAYLAND_DISPLAY DISPLAY XDG_CURRENT_DESKTOP XDG_SESSION_TYPE XDG_RUNTIME_DIR

systemctl --user daemon-reload
systemctl --user enable nuxel-home-kiosk.service
systemctl --user restart nuxel-home-kiosk.service

# Test manually
~/bin/nuxel-home-kiosk
```

Reboot and Nuxel Home opens fullscreen automatically via systemd user service.


---

## Green Stack — All Services Running

Once all services are up, verify with:

```bash
# Check all Nuxel services
sudo systemctl status nuxel-web nuxel-http-bridge nuxel-bridge \
  nuxel-portal nuxel-notifications --no-pager -l

# Verify ports are listening
ss -ltnp | grep -E ':(8000|8080)\b'

# Test the bridge API
curl -s 'http://127.0.0.1:8080/api/v1/ping?message=hello' | python3 -m json.tool

# Open the home launcher
# http://127.0.0.1:8000/pwa/nuxel-home/index.html
```

Expected output:
```
Port 8000 → nuxel-web (PWA static files)
Port 8080 → nuxel-http-bridge (REST API)
D-Bus   → nuxel-bridge, nuxel-portal, nuxel-notifications
```

If all green, snapshot the VM: **nuxel-greenstack-pwa-http-dbus**


---

**v0.2.0** — Get Nuxel running in UTM or on Pixel 10 Pro XL hardware.

---


---

## PWA Dev Testing (http.server)

For quick browser testing of all PWAs:

```bash
cd ~/nuxel

# Copy wallpaper to PWA asset dirs (needed for background to load)
cp nuxel-background.png pwa/nuxel-home/assets/nuxel-background.png
for app in pwa/nuxel-apps/*/; do
  mkdir -p "${app}assets"
  cp nuxel-background.png "${app}assets/nuxel-background.png"
done

# Start dev server from repo root
python3 -m http.server 8000 --bind 127.0.0.1
```

Then in another terminal, start the bridge API (needed for phone status,
notifications, and app permissions in the home launcher):

```bash
cd ~/nuxel
python3 services/nuxel-bridge/src/api.py &
# Bridge listens on http://127.0.0.1:8080
```

> **Why two servers?** Port 8000 serves the PWA HTML/JS/CSS files.
> Port 8080 is the REST API bridge that the home launcher calls for
> phone status, notifications, permissions, etc. In VM dev mode,
> the bridge returns mock data when the real D-Bus services aren't running.

Then open in browser:

| App | URL |
|---|---|
| Home launcher | `http://127.0.0.1:8000/pwa/nuxel-home/index.html` |
| Mail | `http://127.0.0.1:8000/pwa/nuxel-apps/mail/index.html` |
| Calendar | `http://127.0.0.1:8000/pwa/nuxel-apps/calendar/index.html` |
| Notes | `http://127.0.0.1:8000/pwa/nuxel-apps/notes/index.html` |
| Files | `http://127.0.0.1:8000/pwa/nuxel-apps/files/index.html` |
| Camera | `http://127.0.0.1:8000/pwa/nuxel-apps/camera-gallery/index.html` |

The camera app shows a portal consent dialog then requests camera access.
In a browser, the camera permission is handled by the browser's native
permission prompt. In the Nuxel OS, it goes through nuxel-portal.


## Option 1: UTM VM on Apple Silicon (fastest path)

### Prerequisites
- Mac with Apple Silicon (M1/M2/M3/M4)
- [UTM](https://mac.getutm.app/) installed
- At least 8GB free RAM and 40GB free disk

### Steps

```bash
# 1. Bootstrap the VM
cd /Users/wicked/x/nuxel
bash vm/nuxel-vm-bootstrap.sh

# 2. Set phone-shaped display (414×896 portrait)
bash vm/phosh-phone-resolution.sh 414x896

# 3. (Optional) Take a snapshot before experimenting
bash vm/nuxel-vm-snapshot.sh create "clean-install-v0.2.0"
```

The VM will boot into Phosh on Wayland at phone resolution with:
- Nuxel wallpaper (`nuxel-background.png`)
- PWA launcher (`nuxel-home`)
- Core services running (bridge, portal, notifications)
- AppArmor + nftables + hardened_malloc active

### Starting services manually inside the VM

```bash
# Start the capability bridge
sudo -u nuxel-bridge /usr/bin/nuxel-bridge &

# Start the portal daemon (consent dialogs)
sudo -u nuxel-portal /usr/bin/nuxel-portal &

# Start the notification daemon
sudo -u nuxel-notifications /usr/bin/nuxel-notifications &

# Launch a PWA
/usr/bin/nuxel-pwa-launcher org.nuxel.Home
```

---


---

## Dev Build Targets (produces stubs, not flashable images)

Nuxel is not flashable yet. Use these targets for development:

```bash
# Validate syntax and configs only (no images needed)
bash ci/validate-build.sh --config-only

# Build VM rootfs for UTM testing (requires VM running)
bash images/mkrootfs.sh

# Build full image set (DEV ONLY — contains zero stubs, NOT FLASHABLE)
NUXEL_DEVICE=mustang bash images/build.sh --quick

# Clean build
NUXEL_DEVICE=mustang bash images/build.sh --clean
```

**Do not run `boot/flash.sh` on hardware.** The build produces dev stubs for
init_boot.img and dtbo.img. These are zero-filled placeholders that will
satisfy file existence checks but will NOT make a Pixel boot.

Real mustang boot images require:
- Working kernel compile (gs501_defconfig, 6.12 LTS, aarch64 cross-compiler)
- Real DTBO from compiled device tree overlays
- Real init_boot with actual ramdisk
- Real vbmeta with AVB signing keys
- Extracted firmware blobs from Google factory image

---

## Option 2: Build Dev Images (NOT FLASHABLE)

### Prerequisites
```bash
# macOS
brew install aarch64-linux-gnu-binutils cpio gzip

# Or on Linux (Debian/Ubuntu)
sudo apt install gcc-aarch64-linux-gnu cpio gzip android-sdk-platform-tools
```

### Build

```bash
cd /Users/wicked/x/nuxel

# Full build (requires kernel source clone — one time; device key is explicit)
NUXEL_DEVICE=mustang bash images/build.sh

# Quick build (skip kernel compilation)
NUXEL_DEVICE=mustang bash images/build.sh --quick

# Validate the build
NUXEL_DEVICE=mustang bash ci/validate-build.sh
```

Output goes to `build/output/` and `build/flashable/`:
```
build/output/
├── Image.gz              # Kernel
├── initramfs.cpio.gz     # Initramfs (includes boot animation)
├── boot.img              # Boot image (header v4)
├── init_boot.img         # Init boot (mustang requirement)
├── vendor_boot.img       # Vendor boot
├── dtbo.img              # Device tree overlay
├── system.img            # Immutable rootfs (ext4 + dm-verity)
├── system.img.verity     # dm-verity hash tree
├── system.root_hash      # Root hash for AVB
└── vbmeta.img            # AVB verification metadata
```

---

## Option 3: Flash to Pixel 10 Pro XL — ⛔ DO NOT USE YET

### ⚠️ CRITICAL WARNING — DO NOT FLASH HARDWARE YET
THIS FLASH PATH IS ASPIRATIONAL. Flashing will factory-reset the device. Unlocking the bootloader wipes all data.
Relocking prevents booting stock Android. **v0.2.0 status**: The flash/build path has image/build mismatches, placeholder-ish image creation, fragile partition assumptions, and hardcoded device serials. Do not run on a real phone yet unless you are intentionally doing recovery-level bring-up work and are ready to unbrick. Always keep factory images for recovery.

### Prerequisites
- Google Pixel 10 Pro XL (mustang) — serial 58211FDCQ001LA
- USB-C cable (data-capable)
- Google factory image (for firmware extraction + recovery)

### Steps

```bash
# 1. Extract firmware from factory image
NUXEL_DEVICE=mustang bash firmware/install-firmware.sh /path/to/factory-image.zip

# 2. Enable OEM Unlock on device
#    Settings → About Phone → tap Build Number 7 times
#    Settings → System → Developer Options → OEM Unlocking → Enable

# 3. Reboot to bootloader
adb reboot bootloader

# 4. Unlock bootloader (WIPES DEVICE)
fastboot flashing unlock
# Confirm on device screen

# 5. Unlock critical partitions
fastboot flashing unlock_critical

# 6. Flash Nuxel (development mode, AVB disabled)
NUXEL_DEVICE=mustang bash boot/flash.sh --unlock --wipe --skip-avb

# 7. Reboot
fastboot reboot
```

### Production mode (re-locked bootloader with custom keys)

```bash
# Generate signing keys
bash tools/gen-keys.sh

# Sign all images
bash tools/sign-image.sh all

# Flash with relock (WARNING: prevents booting stock Android)
bash boot/flash.sh --production --relock
```

### Recovery

```bash
# Boot to recovery
fastboot oem reboot-recovery

# Or: Volume Up + Power during boot

# From recovery shell:
NUXEL_DEVICE=mustang bash boot/recovery.sh
```

---

## S10+ Quick Start — Samsung Galaxy S10+ (Exynos 9820, beyond2lte)

> ⚠️ **NOT FLASHABLE YET.** The S10+ path is a bring-up in progress: the Phase 0
> device inventory + real firmware + a real kernel build must all complete
> before any image is flashed. The S10+ (Exynos) has **no fastboot** — flashing
> is TWRP (`adb` + `dd`) and Download Mode (Odin/`heimdall`) only. Never relock
> the bootloader (Knox fuse is already tripped; ODIN LOCK may brick) and never
> touch the protected partitions (`efs efsg persist param up_param steady
> keystorage carrier cp_debug misc`).

### Phase 0 — device inventory (REQUIRED FIRST)

The S10+ is already in TWRP. Follow `docs/s10plus-device-inventory.md` and
fill at minimum `KERNEL_ADDR`, `RAMDISK_ADDR`, `TAGS_ADDR`,
`WIFI_FW_FILENAME`. Every S10+ build/flash script refuses to run while those
fields are still `PLACEHOLDER`/`UNKNOWN`.

### Build + flash (device key is explicit)

```bash
# Phase 1: U-Boot + kernel
NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh --clone
NUXEL_DEVICE=s10plus bash boot/s10plus/uboot-chainload.sh

# Phase 2: rootfs + boot images -> build/out/s10plus/
NUXEL_DEVICE=s10plus bash images/s10plus/build.sh

# Flash (device in TWRP)
NUXEL_DEVICE=s10plus bash boot/s10plus/flash.sh \
    --device s10plus \
    --uboot build/out/s10plus/u-boot-beyond2lte.img \
    --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs.img
```

### Revert to stock at any time

```text
Hold  Vol Down + Bixby + Power  -> Download Mode
heimdall flash --BL BL.tar.md5 --AP AP.tar.md5 --CP CP.tar.md5 --CSC CSC.tar.md5
```

Full details, boot-chain diagram, protected-partition rationale, Knox
reality and the driver matrix: **`docs/s10plus-bringup.md`**.

## G7 Power Quick Start — Motorola Moto G7 Power (SDM632, ocean)

> ⚠️ **NOT FLASHABLE YET.** The G7 Power path is a bring-up in progress: the
> Phase 0 device inventory (load addresses, WiFi firmware filenames), real
> firmware and a real kernel build must all complete before any image is
> flashed. The G7 Power is **A-only eMMC** (no A/B slots, no vendor_boot, no
> fastbootd, no dynamic partitions) with a legacy **header v1** boot image
> (page 2048). Flashing is **two-phase fastboot**: stock ABOOT fastboot first
> (dtbo → lk2nd), then lk2nd fastboot (Nuxel boot.img → userdata rootfs).
> **dtbo must ALWAYS be flashed before lk2nd** — that order is enforced in
> code and prevents the classic msm8953 soft-brick. Never relock the
> bootloader during development and never touch the protected partitions
> (`modemst1 modemst2 fsg fsc ddr persist misc`).

### Phase 0 — device inventory (REQUIRED FIRST)

Follow `docs/g7power-device-inventory.md` on the physical device (stock
Android, USB debugging enabled) and fill at minimum `KERNEL_ADDR`,
`RAMDISK_ADDR`, `TAGS_ADDR`, `WIFI_FW_FILENAMES`. Every G7 Power
build/flash script refuses to run while those fields are still
`PLACEHOLDER`/`UNKNOWN`.

### Build (device key is explicit)

```bash
# Phase 1: kernel + lk2nd
bash boot/g7power/lk2nd/README.md        # read lk2nd build instructions
NUXEL_DEVICE=g7power bash kernel/g7power/build-kernel.sh --clone

# Phase 2: rootfs + boot images -> build/out/g7power/
NUXEL_DEVICE=g7power bash images/g7power/build.sh
```

### Flash (two-phase fastboot)

```bash
# Phase 1 — stock ABOOT fastboot mode: dtbo FIRST, then lk2nd
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power --dtbo stock-dtbo.img --lk2nd lk2nd.img

# Phase 2 — lk2nd fastboot mode: Nuxel boot.img + rootfs
NUXEL_DEVICE=g7power bash boot/g7power/flash.sh \
    --device g7power \
    --boot build/out/g7power/nuxel-ocean-boot.img \
    --rootfs build/out/g7power/nuxel-ocean-rootfs.img
```

### Unlock + revert + unbrick

```text
Unlock:  fastboot oem get_unlock_data -> Motorola unlock portal
         (https://motorola-global-portal.custhelp.com) -> email code ->
         fastboot oem unlock <code>   (WIPES DEVICE — backup first)
Revert:  stock ABOOT fastboot mode ->
         fastboot flash dtbo stock-dtbo.img; fastboot flash boot stock-boot.img
Unbrick: EDL (Qualcomm 9008) — power off, hold Vol Down + Vol Up, plug USB;
         verify with: lsusb | grep "05C6:9008"
         then bkerler/edl or QFIL (Windows) to flash the stock partitions.
```

Full details, boot-chain diagram, the dtbo-first rule, protected-partition
rationale and the honest driver matrix: **`docs/g7power-bringup.md`**.

---

## Testing Checklist

### UTM VM
- [ ] Phosh desktop loads at phone resolution
- [ ] Wallpaper displays correctly
- [ ] Core services start (bridge, portal, notifications)
- [ ] PWA launcher opens nuxel-home
- [ ] Service workers register and cache offline

### Pixel Hardware
- [ ] Bootloader unlocks (`fastboot flashing unlock`)
- [ ] Images flash without errors
- [ ] Kernel boots to console (`console=ttyGSI0`)
- [ ] Display initializes (AMB655X panel)
- [ ] Touch responds (S6SY791)
- [ ] WiFi connects (BCM4390)
- [ ] Modem registers (Exynos 5500)
- [ ] Calls work (ModemManager)
- [ ] SMS works (ModemManager)
- [ ] Audio plays (CS35L45 + CS42L43)
- [ ] Sensors report (BMI270, LSM6DSV)
- [ ] Charging works (BQ2597x)

---

## Common Issues

### "fastboot: device not found"
```bash
# Check USB connection
lsusb | grep Google
# Reboot device to bootloader: Volume Down + Power
```

### "No root device found" (initramfs panic)
```bash
# Check partition layout
fastboot getvar all | grep partition
# Verify system.img was flashed
fastboot getvar partition-size:system_a
```

### Phosh not starting
```bash
# Check Wayland socket
ls /run/user/*/wayland-*
# Check Phosh logs
journalctl -u phosh -f
```

### PWA not loading
```bash
# Check bridge socket
ls /run/nuxel/bridge/
# Check portal daemon
dbus-send --system --print-reply --dest=org.nuxel.Portal /org/nuxel/Portal org.nuxel.Portal.Ping string:test
```

---

## Next Steps After Testing

1. Read the [full design document](nuxel-linux-phone-design.md)
2. Read the [architecture overview](Nuxel%20Phone%20OS%20Project%20Plan%20and%20Architecture.md)
3. Check [driver status](docs/driver-status.md) for hardware bring-up progress
4. Review the [security model](docs/security-model.md)
5. See [milestones](docs/milestones.md) for development roadmap

---

_Nuxel v0.2.0 — Build the bunker first._

---

## Boot Animation System

Nuxel has a **two-phase boot animation system** for a smooth visual experience:

### Phase 1: Initramfs Static Splash (Early Boot)

In the initramfs (before rootfs mounts), a **static first-frame image** is displayed on the framebuffer. This is a raw RGB565 frame extracted from the MP4 boot animation at build time.

- No MP4 decoding happens in the initramfs — it's strictly a static framebuffer write
- Acts as immediate visual feedback while the kernel loads drivers
- The raw splash is generated by `images/build.sh` during the initramfs build step

### Phase 2: Plymouth Animated Sequence (Rootfs)

After the rootfs mounts, **Plymouth** takes over with a full animated PNG frame sequence:

1. At build time, the MP4 → PNG frame extraction is shared by `tools/build-nuxel-boot-theme.sh`; `images/mkrootfs.sh` uses it for the image build, and the UTM VM path uses it on the host
2. Frames are stored in `/usr/share/plymouth/themes/nuxel/` as `frame-0001.png` ... `frame-NNNN.png`
3. A Plymouth `script` module loops through the frames until Plymouth quits
4. Plymouth quits cleanly before Phosh/Nuxel Home launch

For the **UTM VM** (as opposed to the device image), the boot animation is
installed by `vm/nuxel-vm-bootstrap.sh`: `vm/deploy-vm.sh` / `vm/build-vm-image.sh`
build the theme on the **host** (where ffmpeg/H.264 decode is available) and
ship it into the guest, so the guest does not need ffmpeg.

UTM gotcha: QEMU's SPCR makes `ttyAMA0` the only active kernel console, and
Plymouth then forces the text/details splash on that serial console — the
graphical display stays black until GDM. The bootstrap therefore adds
`console=tty0` (a graphical fbcon console that overrides the device-tree serial
console), `plymouth.ignore-serial-consoles` + `plymouth.graphical` (so
plymouthd uses the DRM renderer on virtio-gpu instead of the serial console),
`rd.driver.pre=virtio_gpu` (early KMS device) and `video=720x1440` to the
kernel cmdline, and switches GRUB to the graphical `gfxterm` terminal with the
Nuxel boot background. This makes the UTM display active from the moment GRUB
runs, so the "Display output is not active" window before Plymouth is gone. The
UTM bundle has no serial Terminal device so only the single display window is
shown.

### Debug Boot

To bypass the animated boot and see kernel messages:

```bash
# On the kernel cmdline, add:
nuxel.debug=1

# Or at GRUB, edit the kernel line and remove "quiet splash"
```

### Build Configuration

The boot animation resolution and framerate are configurable via environment variables:

```bash
export NUXEL_BOOT_WIDTH=720
export NUXEL_BOOT_HEIGHT=1280
export NUXEL_BOOT_FPS=12
```

For the UTM VM (720x1440 display) the host-side theme builders pass
`--width 720 --height 1440`, so the Plymouth frames and the GRUB background
match the VM screen.

### Requirements

- **ffmpeg** must be available at build time to extract frames
- Plymouth packages are listed in `images/config/packages.yml` under `boot_animation`
- For VM builds, `vm/nuxel-vm-bootstrap.sh` configures GRUB with `quiet splash`, installs the `nuxel` Plymouth theme, and rebuilds initramfs/GRUB; `vm/deploy-vm.sh` / `vm/build-vm-image.sh` ship a host-built theme so in-guest ffmpeg is optional
- Real Pixel hardware still needs proper boot image creation + AVB signing for the full animation pipeline
