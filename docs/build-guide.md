<!-- Nuxel v0.3.2-alpha -->
# Nuxel Build Guide — Immutable Image Assembly

> **No pmbootstrap. No Alpine packages. No `apk add`.**
> **This builds a dm-verity protected, signed, flashable OS image for Pixel 10 Pro XL (mustang).**

---

## 1. Build Philosophy

Nuxel images are **not assembled from packages via package manager**. Instead:

1. The root filesystem is built from a **Flatpak runtime base** (org.gnome.Platform//46)
2. Nuxel services and apps are **copied in as immutable files**
3. The result is a **single system.img with dm-verity hash tree**
4. No package manager exists in the final image
5. Updates replace the entire system image via A/B slots

---

## 2. Host Requirements

### 2.1 Operating System

- **Required:** Linux x86_64 (Debian 12+, Ubuntu 24.04+, Fedora 40+)
- **Not supported:** macOS, Windows/WSL, 32-bit hosts

### 2.2 Packages

```bash
# Debian / Ubuntu
sudo apt update && sudo apt install -y \
    build-essential git wget curl cpio lz4 \
    device-tree-compiler python3 python3-pip python3-setuptools \
    meson ninja-build cmake pkg-config \
    gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
    binutils-aarch64-linux-gnu \
    bc bison flex libssl-dev libncurses-dev libelf-dev \
    rsync fastboot mtools dosfstools e2fsprogs \
    squashfs-tools libgmp-dev libmpfr-dev libmpc-dev \
    openssl libusb-1.0-0-dev \
    flatpak flatpak-builder \
    veritysetup cryptsetup-bin \
    avbtool android-sdk-libsparse

# Fedora
sudo dnf install -y \
    @development-tools git wget curl cpio lz4 dtc \
    python3 python3-pip python3-setuptools \
    meson ninja-build cmake pkgconfig \
    gcc-aarch64-linux-gnu gcc-c++-aarch64-linux-gnu \
    binutils-aarch64-linux-gnu \
    bc bison flex openssl-devel ncurses-devel elfutils-libelf-devel \
    rsync android-tools mtools dosfstools e2fsprogs squashfs-tools \
    gmp-devel mpfr-devel libmpc-devel libusb1-devel \
    flatpak flatpak-builder \
    cryptsetup device-mapper
```

### 2.3 Toolchain Verification

```bash
aarch64-linux-gnu-gcc --version    # >= 12.x
fastboot --version                  # >= 34.0.0
flatpak --version                   # >= 1.14
veritysetup --version               # >= 2.6
openssl version                     # >= 3.0
```

### 2.4 Environment Variables

```bash
export ARCH=arm64
export CROSS_COMPILE=aarch64-linux-gnu-
export CC=aarch64-linux-gnu-gcc
export CXX=aarch64-linux-gnu-g++
export NUXXEL_ROOT="$PWD"
export BUILD_OUT="$NUXXEL_ROOT/build/out"
```

---

## 3. Build the Kernel

### 3.1 Clone

```bash
mkdir -p ~/nuxel-build/kernel
cd ~/nuxel-build/kernel

git clone --depth=1 \
    -b android-gs-mustang-6.12 \
    https://android.googlesource.com/kernel/gs \
    mustang-kernel

cd mustang-kernel
```

### 3.2 Apply Nuxel Patches

```bash
for patch in "$NUXXEL_ROOT"/kernel/patches/*.patch; do
    echo "Applying: $(basename $patch)"
    git am "$patch" 2>/dev/null || patch -p1 < "$patch"
done
```

### 3.3 Configure

```bash
# Start from gs501 defconfig
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- gs501_defconfig

# Apply Nuxel hardening config
./scripts/kconfig/merge_config.sh -m .config \
    "$NUXXEL_ROOT/kernel/defconfig"

# Build
make -j$(nproc) ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    Image dtbs modules

# Install modules to staging
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- \
    INSTALL_MOD_PATH="$BUILD_OUT/modules" \
    INSTALL_MOD_STRIP=1 \
    modules_install
```

### 3.4 Output

```
$BUILD_OUT/
├── Image                    — Kernel image (uncompressed)
├── Image.gz                 — Kernel image (gzip compressed, for boot.img)
├── dtbs/                    — Device tree blobs
│   ├── qcom/mustang.dtb     — Mustang main DT
│   └── qcom/mustang-*.dtbo  — DTBO fragments
└── modules/                 — Kernel modules for initramfs
    └── lib/modules/6.12.0-nuxel/
```

---

## 4. Build the Initramfs

### 4.1 Initramfs Structure

```
initramfs/
├── init                     — /init script (busybox ash)
├── bin/
│   ├── busybox              — Static busybox binary
│   └── cryptsetup           — For LUKS (future use)
├── etc/
│   └── fstab                — Mount table
├── lib/modules/             — Minimal kernel modules (from build)
│   └── 6.12.0-nuxel/
│       ├── kernel/fs/ext4/
│       ├── kernel/fs/f2fs/
│       ├── kernel/drivers/ufs/
│       ├── kernel/drivers/gpu/drm/
│       ├── kernel/drivers/input/touchscreen/
│       └── kernel/drivers/soc/qcom/
└── dev/                     — Device nodes (created at boot)
```

### 4.2 Init Script

```bash
#!/bin/busybox sh
# Nuxel initramfs init script — mustang (Pixel 10 Pro XL)

# Mount essential filesystems
mount -t proc none /proc
mount -t sysfs none /sys
mount -t devtmpfs none /dev
mount -t tmpfs none /tmp

# Initialize logging
echo "Nuxel initramfs: waiting for storage..." > /dev/kmsg

# Load UFS storage driver
modprobe ufs-qcom
modprobe ufshcd-core
modprobe ufshcd-pltfrm

# Wait for root device
ROOT_WAIT=30
while [ $ROOT_WAIT -gt 0 ]; do
    if [ -b /dev/disk/by-partlabel/system_a ]; then
        break
    fi
    sleep 1
    ROOT_WAIT=$((ROOT_WAIT - 1))
done

if [ ! -b /dev/disk/by-partlabel/system_a ]; then
    echo "Nuxel initramfs: root device not found!" > /dev/kmsg
    echo "Nuxel initramfs: dumping block devices..." > /dev/kmsg
    ls -la /dev/disk/by-partlabel/ > /dev/kmsg 2>&1
    echo "Nuxel initramfs: entering recovery shell" > /dev/kmsg
    exec /bin/sh
fi

# Determine active slot from vbmeta or cmdline
ACTIVE_SLOT="a"
if grep -q 'androidboot.slot_suffix=_b' /proc/cmdline; then
    ACTIVE_SLOT="b"
fi

# Mount root filesystem (dm-verity will be set up by kernel/init)
mount -o ro /dev/disk/by-partlabel/system_${ACTIVE_SLOT} /sysroot

# Mount userdata
mount -o rw,nosuid,nodev,noexec /dev/disk/by-partlabel/userdata /sysroot/var

# Switch root to the real filesystem
exec switch_root /sysroot /sbin/init
```

### 4.3 Build Initramfs Image

```bash
#!/bin/bash
# tools/build-initramfs.sh
set -euo pipefail

INITRAMFS_DIR="$BUILD_OUT/initramfs"
INITRAMFS_IMG="$BUILD_OUT/initramfs.img"

mkdir -p "$INITRAMFS_DIR"/{bin,dev,etc,lib/modules,proc,sys,sysroot,tmp}

# Copy busybox (statically linked)
cp /usr/bin/busybox "$INITRAMFS_DIR/bin/"
for cmd in sh mount modprobe insmod ls mkdir cat echo ls dev sleep; do
    ln -sf busybox "$INITRAMFS_DIR/bin/$cmd"
done

# Copy init script
install -m755 scripts/initramfs-init.sh "$INITRAMFS_DIR/init"

# Copy minimal kernel modules
cp -r "$BUILD_OUT/modules/lib/modules/6.12.0-nuxel/" \
    "$INITRAMFS_DIR/lib/modules/"

# Create cpio archive
cd "$INITRAMFS_DIR"
find . | cpio -H newc -o | lz4 -c > "$INITRAMFS_IMG"
cd "$NUXXEL_ROOT"

echo "Initramfs: $INITRAMFS_IMG ($(du -h $INITRAMFS_IMG | awk '{print $1}'))"
```

---

## 5. Build the Root Filesystem

### 5.1 Base from Flatpak Runtime

The rootfs is built on the GNOME Flatpak runtime, **not** from distro packages:

```bash
#!/bin/bash
# images/mkrootfs.sh — Build immutable rootfs
set -euo pipefail

NUXXEL_ROOT="$PWD"
BUILD_OUT="$NUXXEL_ROOT/build/out"
ROOTFS_DIR="$BUILD_OUT/rootfs"
SYSTEM_IMG="$BUILD_OUT/system.img"

# Clean
rm -rf "$ROOTFS_DIR"
mkdir -p "$ROOTFS_DIR"

# ============================================================
# Step 1: Install Flatpak runtime as base
# ============================================================
echo "[1/6] Installing Flatpak runtime base..."

flatpak install --system --noninteractive \
    org.gnome.Platform//46 2>/dev/null || true

# Extract runtime files
RUNTIME_DIR="/var/lib/flatpak/runtime/org.gnome.Platform/aarch64/stable"
if [ -d "$RUNTIME_DIR" ]; then
    # Find the active deployment
    DEPLOY="$(ls -1 "$RUNTIME_DIR" | grep '^active$' || ls -1 "$RUNTIME_DIR" | head -1)"
    if [ -d "$RUNTIME_DIR/$DEPLOY/files" ]; then
        rsync -aHAX "$RUNTIME_DIR/$DEPLOY/files/" "$ROOTFS_DIR/"
    fi
fi

# ============================================================
# Step 2: Add Nuxel core services
# ============================================================
echo "[2/6] Installing Nuxel core services..."

# nuxel-bridge
install -Dm755 services/nuxel-bridge/src/bridge.py \
    "$ROOTFS_DIR/usr/bin/nuxel-bridge"
install -Dm755 services/nuxel-bridge/src/api.py \
    "$ROOTFS_DIR/usr/lib/nuxel/bridge/api.py"
install -Dm755 services/nuxel-bridge/src/capabilities.py \
    "$ROOTFS_DIR/usr/lib/nuxel/bridge/capabilities.py"
install -Dm644 services/nuxel-bridge/dbus/org.nuxel.Bridge.conf \
    "$ROOTFS_DIR/etc/dbus-1/system.d/org.nuxel.Bridge.conf"
install -Dm644 services/nuxel-bridge/systemd/nuxel-bridge.service \
    "$ROOTFS_DIR/usr/lib/systemd/system/nuxel-bridge.service"

# nuxel-portal
install -Dm755 services/nuxel-portal/src/portal.py \
    "$ROOTFS_DIR/usr/bin/nuxel-portal"
install -Dm644 services/nuxel-portal/dbus/org.nuxel.Portal.conf \
    "$ROOTFS_DIR/etc/dbus-1/system.d/org.nuxel.Portal.conf"
install -Dm644 services/nuxel-portal/systemd/nuxel-portal.service \
    "$ROOTFS_DIR/usr/lib/systemd/system/nuxel-portal.service"

# nuxel-notifications
install -Dm755 services/nuxel-notifications/src/notifications.py \
    "$ROOTFS_DIR/usr/bin/nuxel-notifications"
install -Dm644 services/nuxel-notifications/dbus/org.nuxel.Notifications.conf \
    "$ROOTFS_DIR/etc/dbus-1/system.d/org.nuxel.Notifications.conf"
install -Dm644 services/nuxel-notifications/systemd/nuxel-notifications.service \
    "$ROOTFS_DIR/usr/lib/systemd/system/nuxel-notifications.service"

# ============================================================
# Step 3: Add native GTK4 apps
# ============================================================
echo "[3/6] Installing native apps..."

for app in dialer messages contacts settings; do
    app_binary="nuxel-${app}"
    app_dir="shell/nuxel-shell/nuxel-${app}"
    
    if [ -f "$app_dir/main.c" ]; then
        # Cross-compile
        aarch64-linux-gnu-gcc \
            -o "$BUILD_OUT/$app_binary" \
            "$app_dir/main.c" \
            $(pkg-config --cflags --libs gtk4 libadwaita-1) \
            -static-libgcc
        install -Dm755 "$BUILD_OUT/$app_binary" \
            "$ROOTFS_DIR/usr/bin/$app_binary"
    fi
done

# Desktop files
install -Dm644 shell/config/nuxel-dialer.desktop \
    "$ROOTFS_DIR/usr/share/applications/nuxel-dialer.desktop"
install -Dm644 shell/config/nuxel-messages.desktop \
    "$ROOTFS_DIR/usr/share/applications/nuxel-messages.desktop"
install -Dm644 shell/config/nuxel-contacts.desktop \
    "$ROOTFS_DIR/usr/share/applications/nuxel-contacts.desktop"
install -Dm644 shell/config/nuxel-settings.desktop \
    "$ROOTFS_DIR/usr/share/applications/nuxel-settings.desktop"

# Icons
for icon in dialer messages contacts settings; do
    install -Dm644 "shell/config/icons/${icon}.svg" \
        "$ROOTFS_DIR/usr/share/icons/hicolor/scalable/apps/nuxel-${icon}.svg"
done

# GSettings schema
install -Dm644 shell/config/schemas/org.nuxel.settings.gschema.xml \
    "$ROOTFS_DIR/usr/share/glib-2.0/schemas/org.nuxel.settings.gschema.xml"

# Phosh override
install -Dm644 "shell/config/phosh/nuxel-phosh-override.ini" \
    "$ROOTFS_DIR/etc/phosh/phosh.ini"

# ============================================================
# Step 4: Install configs and policies
# ============================================================
echo "[4/6] Installing security configs..."

# hardened_malloc
install -Dm644 configs/hardened-malloc.conf \
    "$ROOTFS_DIR/etc/hardened-malloc.conf"
install -Dm644 configs/hardened-malloc.so \
    "$ROOTFS_DIR/usr/lib/libhardened_malloc.so" 2>/dev/null || true

# AppArmor profiles
for profile in configs/apparmor.d/*; do
    name="$(basename "$profile")"
    install -Dm644 "$profile" \
        "$ROOTFS_DIR/etc/apparmor.d/$name"
done

# nftables firewall
install -Dm644 configs/nftables/nuxel-app-firewall.nft \
    "$ROOTFS_DIR/usr/share/nftables.d/nuxel-app-firewall.nft"

# ============================================================
# Step 5: Set up system directories
# ============================================================
echo "[5/6] Setting up directories..."

mkdir -p "$ROOTFS_DIR/var/app"
mkdir -p "$ROOTFS_DIR/var/lib/flatpak"
mkdir -p "$ROOTFS_DIR/var/lib/nuxel/permissions"
mkdir -p "$ROOTFS_DIR/var/log/nuxel"
mkdir -p "$ROOTFS_DIR/var/home/user"
mkdir -p "$ROOTFS_DIR/var/tmp"

# Symlink home
ln -sf /var/home/user "$ROOTFS_DIR/home"

# Fix permissions
chmod 755 "$ROOTFS_DIR/var/app"
chmod 700 "$ROOTFS_DIR/var/lib/nuxel/permissions"
chmod 755 "$ROOTFS_DIR/var/home/user"

# ============================================================
# Step 6: Create system image with dm-verity
# ============================================================
echo "[6/6] Creating dm-verity system image..."

# Calculate size
ROOTFS_SIZE_MB="$(du -sm "$ROOTFS_DIR" | awk '{print $1}')"
IMAGE_SIZE_MB=$((ROOTFS_SIZE_MB + ROOTFS_SIZE_MB / 4 + 512))

# Create sparse image
dd if=/dev/zero of="$SYSTEM_IMG" bs=1M count=1 seek=$IMAGE_SIZE_MB 2>/dev/null

# Create filesystem
mkfs.ext4 -O ^has_journal -L "nuxel-system" "$SYSTEM_IMG"

# Mount and populate
mkdir -p "$BUILD_OUT/mnt"
sudo mount -o loop "$SYSTEM_IMG" "$BUILD_OUT/mnt"
sudo rsync -aHAX "$ROOTFS_DIR/" "$BUILD_OUT/mnt/"
sudo umount "$BUILD_OUT/mnt"

# Generate dm-verity hash tree
ROOT_HASH="$(veritysetup format --hash=sha256 "$SYSTEM_IMG" \
    "$SYSTEM_IMG.verity" 2>&1 | grep 'Root hash:' | awk '{print $3}')"
echo "Root hash: $ROOT_HASH"
echo "$ROOT_HASH" > "$BUILD_OUT/system.root_hash"

# Resize to minimum
e2fsck -fy "$SYSTEM_IMG" 2>/dev/null || true
resize2fs -M "$SYSTEM_IMG" 2>/dev/null

echo "System image: $SYSTEM_IMG ($(du -h $SYSTEM_IMG | awk '{print $1}'))"
echo "Verity data: $SYSTEM_IMG.verity"
echo "Root hash stored in: $BUILD_OUT/system.root_hash"
```

---

## 6. Create boot.img

```bash
#!/bin/bash
# tools/mkbootimg.sh
set -euo pipefail

KERNEL_IMAGE="$BUILD_OUT/Image.gz"
INITRAMFS_IMG="$BUILD_OUT/initramfs.img"
DTB="$BUILD_OUT/dtbs/qcom/mustang.dtb"
BOOT_IMG="$BUILD_OUT/boot.img"

mkbootimg \
    --kernel "$KERNEL_IMAGE" \
    --ramdisk "$INITRAMFS_IMG" \
    --dtb "$DTB" \
    --cmdline "console=ttyGSI0,115200n8 earlycon=gsihvc0 root=PARTLABEL=system_a rootwait ro init=/sbin/init loglevel=7" \
    --base 0x10000000 \
    --kernel_offset 0x00008000 \
    --ramdisk_offset 0x01000000 \
    --tags_offset 0x00000100 \
    --pagesize 4096 \
    --header_version 4 \
    --os_version 15.0.0 \
    --os_patch_level 2026-05 \
    --output "$BOOT_IMG"

echo "boot.img: $BOOT_IMG ($(du -h $BOOT_IMG | awk '{print $1}'))"
```

---

## 7. Sign Images

```bash
# 7.1 Generate signing keys (first time only)
./tools/gen-keys.sh

# 7.2 Sign boot image
./tools/sign-image.sh boot "$BUILD_OUT/boot.img"

# 7.3 Create dm-verity hash tree for system (already done in mkrootfs)

# 7.4 Sign vbmeta chaining boot + system
ROOT_HASH="$(cat $BUILD_OUT/system.root_hash)"
avbtool make_vbmeta_image \
    --include_descriptors_from_image "$BUILD_OUT/boot.img.signed" \
    --add_hash_footer \
        --image "$BUILD_OUT/system.img" \
        --partition_name system \
        --partition_size "$((IMAGE_SIZE_MB * 1024 * 1024))" \
        --hash_algorithm sha256 \
        --salt "$(openssl rand -hex 32)" \
    --key keys/nuxel-avb.pem \
    --algorithm SHA256_RSA4096 \
    --rollback_index 1 \
    --flags 0 \
    --output "$BUILD_OUT/vbmeta.img"

echo "All images signed. Ready to flash."
```

---

## 8. Flashable Output

```
$BUILD_OUT/flashable/
├── boot.img            — Signed kernel + initramfs (boot header v4)
├── init_boot.img       — Generic ramdisk (from factory)
├── vendor_boot.img     — Vendor ramdisk + DTBO (from factory)
├── dtbo.img            — Device tree overlay (from factory)
├── system.img          — dm-verity protected rootfs
├── system.img.verity   — dm-verity hash tree data
├── vbmeta.img          — AVB descriptor chaining boot + system
└── modem.img           — Exynos 5500 firmware (from factory)
```

---

## 9. CI/CD Pipeline

```yaml
# .github/workflows/build.yml
name: Nuxel Build + Sign
on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-24.04-arm64  # Native aarch64 build, or use QEMU
    steps:
      - uses: actions/checkout@v4
      
      - name: Install dependencies
        run: |
          sudo apt update
          sudo apt install -y build-essential git wget cpio lz4 dtc \
            python3 meson ninja-build cmake gcc-aarch64-linux-gnu \
            bc bison flex libssl-dev libncurses-dev libelf-dev rsync \
            mtools dosfstools e2fsprogs flatpak flatpak-builder \
            cryptsetup busybox-static
      
      - name: Build kernel
        run: |
          export ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu-
          make -j$(nproc) gs501_defconfig
          make -j$(nproc) Image dtbs modules
      
      - name: Build initramfs
        run: ./scripts/build-initramfs.sh
      
      - name: Build rootfs
        run: sudo ./images/mkrootfs.sh
      
      - name: Assemble images
        run: |
          ./tools/mkbootimg.sh
          ./tools/sign-image.sh boot build/out/boot.img
          mv build/out/{boot.img.signed,vbmeta.img} build/out/flashable/
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: nuxel-mustang-images
          path: build/out/flashable/
```

---

## 10. Build Verification

```bash
# Verify boot.img structure
avbtool info --image build/out/boot.img.signed

# Verify dm-verity on system image
veritysetup verify build/out/system.img \
    build/out/system.img.verity \
    "$(cat build/out/system.root_hash)"

# Verify vbmeta chain
avbtool verify_image --image build/out/vbmeta.img

# Check image sizes are within partition limits
ls -lh build/out/flashable/
# boot.img:    < 96 MB
# system.img:  < 4 GB  
# vbmeta.img:  < 64 KB
```

---

## 11. Quick Reference

```bash
# Full build (clean)
make clean
./images/mkrootfs.sh
./tools/mkbootimg.sh
./tools/gen-keys.sh        # First time only
./tools/sign-image.sh all
./boot/flash.sh

# Quick rebuild (kernel only)
make -C build/kernel -j$(nproc) Image
./tools/mkbootimg.sh
fastboot flash boot build/out/boot.img.signed

# Quick rebuild (services only)
./images/mkrootfs.sh --services-only
sudo fastboot flash system build/out/system.img
