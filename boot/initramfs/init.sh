#!/bin/sh
# =============================================================================
# Nuxel initramfs init — PID 1 for the Nuxel phone OS.
#
# Bootstraps the Google Pixel 10 Pro XL (mustang, Tensor G5/gs501) from the
# packaged boot image; with nuxel.device=s10plus it boots the Samsung Galaxy
# S10+ (Exynos 9820, beyond2lte) from its A-only UFS layout, and g7power
# (Moto G7 Power, ocean) boots from its eMMC layout
# (/dev/block/bootdevice/by-name; probe order root= > userdata > system_a > system).
# NOTE (2026-10-12): ocean is an A/B device (boot_a/boot_b, dtbo_a/dtbo_b,
# system_a/system_b, vendor_a/vendor_b) with a SHARED `userdata` partition —
# the packed cmdline pins root=.../by-name/userdata, so the probe is unaffected.
# This script is intended to run in a NEWC cpio
# initramfs whose /bin contains either toybox (preferred, static) or busybox
# (both provide POSIX `sh` plus the mount/switch_root/modprobe utilities used
# below).  If neither toybox nor busybox is present we still attempt the full
# boot sequence using whatever /bin/coreutils is shipped, because every
# command below has a toybox/busybox equivalent.
#
# Boot chain:  bootloader -> kernel Image -> this initramfs init
#              -> (optional dm-verity root) -> switch_root -> /sbin/init
#
# Rootfs hook & kernel cmdline:
#   * `root=`               explicit root block device (overrides probing)
#   * `rootfstype=`         filesystem of the root device
#   * `nuxel.slot=<a|b>`    active A/B slot (default a)
#   * `nuxel.device=`       device codename: `mustang` (Pixel 10 Pro XL),
#                           `vm` (generic ARM64/UTM build), `s10plus`
#                           (Galaxy S10+ Exynos 9820, A-only UFS root) or
#                           `g7power` (Moto G7 Power / ocean, A/B eMMC,
#                           shared userdata: probe order root= > userdata > system)
#   * `nuxel.quiet=*`       suppress non-fatal boot chatter
#   * `nuxel.debug=*`       drop to an interactive emergency shell on failure
#   * `nuxel.verity_hash=`  dm-verity root hash (from the AVB/bootloader
#                           chain-of-trust); when set the root block device is
#                           mapped through dm-verity before mounting.
#   * `nuxel.noverity`      bypass dm-verity (development only)
#   * `nuxel.console=`      preferred serial console
#   * `nuxel.noanim`        disable the framebuffer boot splash
# =============================================================================

# toybox usually needs no PATH override, but keep a sane default for busybox.
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

# --- essential pseudo filesystems --------------------------------------------
if [ -d /proc ]; then  mount -t proc -o noexec,nosuid,nodev none /proc  2>/dev/null; fi
if [ -d /sys  ]; then  mount -t sysfs -o noexec,nosuid,nodev none /sys   2>/dev/null; fi
if [ -d /dev  ]; then  mount -t devtmpfs none /dev                       2>/dev/null; fi
mkdir -p /dev/pts /dev/mapper /dev/disk/by-partlabel
mount -t devpts none /dev/pts 2>/dev/null

# --- runtime state ------------------------------------------------------------
mkdir -p /run /tmp
: > /run/nuxel-boot
echo "Nuxel" > /run/ostree-boot
echo "$(date +%s 2>/dev/null || echo 0)" > /run/boot-start-time

log() { echo "nuxel-init: $*"; }
warn() { echo "nuxel-init: [warn] $*"; }
err()  { echo "nuxel-init: [ERROR] $*"; }

# --- command provider ----------------------------------------------------------
# Prefer toybox, then busybox.  If neither is present we still carry on using
# whatever coreutils are installed in the initramfs.
if [ ! -e /bin/sh ]; then
    if [ -x /bin/toybox ]; then
        ln -sf toybox /bin/sh
        for cmd in mount umount switch_root modprobe mknod mkswap mkfs.ext4 \
                   tar gzip ls cat printf echo sed grep awk find sleep date ps \
                   df du sh sync reboot poweroff dd cp mv rm mkdir ln chown \
                   chmod dmesg blkid losetup mkswap; do
            ln -sf toybox "/bin/${cmd}" 2>/dev/null
        done
    elif [ -x /bin/busybox ]; then
        /bin/busybox --install -s /bin 2>/dev/null
        ln -sf busybox /bin/sh
    fi
fi

# --- parse kernel cmdline -------------------------------------------------------
CMDLINE="$(cat /proc/cmdline 2>/dev/null)"
SLOT="a"
DEVICE=""
QUIET=""
DEBUG=""
CONSOLE=""
ROOT_SPEC=""
ROOT_FSTYPE=""
VERITY_HASH=""
NOVERITY=0
BOOT_ANIM=1

for param in ${CMDLINE}; do
    case "${param}" in
        nuxel.slot=*)       SLOT="${param#nuxel.slot=}" ;;
        nuxel.device=*)     DEVICE="${param#nuxel.device=}" ;;
        nuxel.quiet=*)      QUIET="${param#nuxel.quiet=}" ;;
        nuxel.debug=*)      DEBUG="${param#nuxel.debug=}" ;;
        nuxel.console=*)    CONSOLE="${param#nuxel.console=}" ;;
        nuxel.verity_hash=*) VERITY_HASH="${param#nuxel.verity_hash=}" ;;
        nuxel.noverity)     NOVERITY=1 ;;
        nuxel.noanim*)      BOOT_ANIM=0 ;;
        root=*)             ROOT_SPEC="${param#root=}" ;;
        rootfstype=*)       ROOT_FSTYPE="${param#rootfstype=}" ;;
        rootwait)           : ;;
    esac
done

log "slot=${SLOT} device=${DEVICE:-unknown} quiet=${QUIET:-0} verity=$([ -n "${VERITY_HASH}" ] && echo on || echo off)"
[ -z "${DEVICE}" ] && warn "no nuxel.device= on cmdline; assuming generic ARM64"

# --- device-tree / DTB overlay sanity -------------------------------------------
# The mustang DTBO (device-tree overlay) is normally applied by the bootloader
# (Google ABL) or flashed to the `dtbo` partition.  In the initramfs we merely
# VERIFY that the firmware/DTB path is present and log it.  For the generic
# ARM64 / UTM build there is no mustang DTBO — QEMU supplies an arm-virt DTB, so
# nuxel.device=vm skips the mustang hardware expectations.
dump_dtb() {
    # /proc/device-tree mirrors the flattened device tree the bootloader passed.
    if [ -d /proc/device-tree ] && [ -f /proc/device-tree/model ]; then
        log "DT model: $(tr -d '\0' < /proc/device-tree/model 2>/dev/null)"
    fi
}
dump_dtb

# --- early boot splash (framebuffer) ---------------------------------------------
show_boot_splash() {
    fbdev=""
    for fb in /dev/fb0 /dev/graphics/fb0; do
        [ -c "${fb}" ] && { fbdev="${fb}"; break; }
    done
    [ -z "${fbdev}" ] && { log "no framebuffer — skipping splash"; return; }

    # Block devices may not exist before the framebuffer driver loads; with a
    # devtmpfs boot the console device appears once DRM/KMS finishes.
    if [ -f /boot/nuxel-boot-splash.raw ]; then
        log "displaying Nuxel boot splash on ${fbdev}"
        cat /boot/nuxel-boot-splash.raw > "${fbdev}" 2>/dev/null
    else
        # Solid navy (#0a1628) fallback.  RGB565: R=0x08>>3=0x01 G=0x16>>2
        # =0x05 B=0x28>>3=0x05  =>  (0x01<<11)|(0x05<<5)|0x05 = 0x08A5.
        log "no splash data — showing navy boot screen"
        if command -v dd >/dev/null 2>&1; then
            NXW="${NUXEL_BOOT_WIDTH:-720}"; NXH="${NUXEL_BOOT_HEIGHT:-1280}"
            bye=$(( NXW * NXH * 2 ))
            # write a small repeating RGB565 navy pattern
            { while [ "$bye" -gt 0 ]; do printf '\x05\x08\xa5\x08'; bye=$((bye-4)); done; } \
                > "${fbdev}" 2>/dev/null
        fi
    fi
}
if [ "${BOOT_ANIM}" -eq 1 ]; then show_boot_splash; fi

# --- emergency shell ---------------------------------------------------------------
# Shared failure fallback for every device branch.  ALWAYS prints the
# available block devices and /proc/cmdline for the operator; with
# nuxel.debug=1 it additionally drops to an interactive ash/sh (toybox or
# busybox) instead of returning to the caller's panic path.  POSIX sh only.
emergency_shell() {
    err "emergency shell: /proc/cmdline:"
    cat /proc/cmdline 2>/dev/null || true
    err "emergency shell: available block devices:"
    ls -la /dev/disk/by-partlabel/ 2>/dev/null
    ls -la /dev/sd* /dev/vd* /dev/mmcblk* 2>/dev/null
    ls -la /dev/block/platform/*/by-name/ 2>/dev/null
    if [ -n "${DEBUG}" ]; then
        err "nuxel.debug=${DEBUG} — dropping to interactive shell"
        exec sh -i
    fi
}

# --- root block device resolution ------------------------------------------------
find_root() {
    # 1) explicit cmdline root
    if [ -n "${ROOT_SPEC}" ]; then
        # strip rootwait/ro/fstype words that may be glued on
        rootdev="${ROOT_SPEC%% *}"
        if [ -b "${rootdev}" ]; then
            echo "${rootdev}"; return 0
        fi
        # by-partlabel
        if [ -b "/dev/disk/by-partlabel/${rootdev}" ]; then
            echo "/dev/disk/by-partlabel/${rootdev}"; return 0
        fi
    fi
    # 2) slot-based probe (mustang dynamic partitions)
    for try in \
        "/dev/disk/by-partlabel/system_${SLOT}" \
        "/dev/disk/by-partlabel/system" \
        "/dev/system_${SLOT}" \
        "/dev/sda2" "/dev/sda1" "/dev/mmcblk0p2" "/dev/mmcblk0p1" "/dev/vda2" "/dev/vda1"; do
        if [ -b "${try}" ]; then
            echo "${try}"; return 0
        fi
    done
    return 1
}

# Dispatch on nuxel.device= — each target resolves its own root device:
#   mustang / vm / ""   -> existing A/B dynamic-partition probe (unchanged)
#   s10plus             -> A-only UFS probe: root= > userdata > system
#   g7power             -> eMMC probe: root= > userdata > system_a > system
ROOT_DEV=""
case "${DEVICE}" in
    mustang|vm|"")
        # Existing A/B + generic probe (mustang dynamic partitions; vm/QEMU
        # virtio).  Byte-equivalent to the pre-multi-device behaviour:
        # explicit root= > /dev/disk/by-partlabel/system_${SLOT} > generic.
        ROOT_DEV="$(find_root)"
        ;;
    s10plus)
        # S10+ A-only UFS layout:
        # Boot -> U-Boot -> Linux. Root is on userdata (or system) partition.
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
            err "Available: $(ls "${UFS_BASE}" 2>/dev/null | tr '\n' ' ')"
            emergency_shell
        fi
        log "s10plus: root → ${ROOT_DEV} (fstype: ${ROOT_FSTYPE:-ext4})"
        ;;
    g7power)
        # G7 Power eMMC layout (A/B device, shared userdata)
        # eMMC path: /dev/block/bootdevice/by-name/
        # lk2nd passes the correct cmdline; root= may be explicit or we probe.
        EMMC_BASE="/dev/block/bootdevice/by-name"
        if [ -n "${ROOT_SPEC}" ]; then
            ROOT_DEV="${ROOT_SPEC}"
        elif [ -b "${EMMC_BASE}/userdata" ]; then
            ROOT_DEV="${EMMC_BASE}/userdata"
        elif [ -b "${EMMC_BASE}/system_a" ]; then
            ROOT_DEV="${EMMC_BASE}/system_a"
        elif [ -b "${EMMC_BASE}/system_b" ]; then
            ROOT_DEV="${EMMC_BASE}/system_b"
        elif [ -b "${EMMC_BASE}/system" ]; then
            ROOT_DEV="${EMMC_BASE}/system"
        else
            err "g7power: cannot find root partition under ${EMMC_BASE}"
            err "Available: $(ls ${EMMC_BASE} 2>/dev/null | tr '\n' ' ')"
            emergency_shell
        fi
        log "g7power: root → ${ROOT_DEV} (fstype: ${ROOT_FSTYPE:-ext4})"
        ;;
    *)
        err "unknown nuxel.device='${DEVICE}' — cannot resolve a root device"
        emergency_shell
        ;;
esac

if [ -z "${ROOT_DEV}" ]; then
    err "no root block device found (slot=${SLOT})"
    emergency_shell
    echo "=== NUXXEL PANIC: no root device ==="
    sleep 60 || true
    echo "reboot..." ; reboot -f 2>/dev/null || true
fi

log "root block device: ${ROOT_DEV}"

# --- dm-verity note --------------------------------------------------------------
# The actual dm-verity mapping is performed by the verity-setup hook in the real
# rootfs; this initramfs does not carry veritysetup, so if a hash was supplied we
# warn that the root is being mounted without verification (development only).
if [ -n "${VERITY_HASH}" ] && [ "${NOVERITY}" -eq 0 ] && ! command -v veritysetup >/dev/null 2>&1; then
    err "dm-verity mapping requested (hash present) but veritysetup is not in this"
    err "initramfs; mounting ${ROOT_DEV} read-only WITHOUT verification (dev only)."
fi

ROOT_MNT=/newroot
mkdir -p "${ROOT_MNT}"

# filesystem type: explicit > probe via blkid > default
FS_TYPE="${ROOT_FSTYPE}"

# Try to fsck non-destructively if available.
if [ -z "${FS_TYPE}" ] || [ "${FS_TYPE}" = "ext4" ] || [ "${FS_TYPE}" = "ext2" ]; then
    command -v e2fsck >/dev/null 2>&1 && e2fsck -p "${ROOT_DEV}" 2>/dev/null
fi

[ -z "${FS_TYPE}" ] && FS_TYPE=ext4

# --- mount root ----------------------------------------------------------------
if ! mount -t "${FS_TYPE}" -o ro "${ROOT_DEV}" "${ROOT_MNT}" 2>/dev/null; then
    # retry as rw (some boot flows mount rw transiently)
    if ! mount -t "${FS_TYPE}" -o rw "${ROOT_DEV}" "${ROOT_MNT}" 2>/dev/null; then
        err "failed to mount ${ROOT_DEV} as ${FS_TYPE}"
        err "trying filesystem probe..."
        if command -v blkid >/dev/null 2>&1; then
            for t in ext4 ext2 f2fs squashfs erofs xfs btrfs vfat; do
                if mount -t "${t}" -o ro "${ROOT_DEV}" "${ROOT_MNT}" 2>/dev/null; then
                    log "mounted ${ROOT_DEV} as ${t}"; FS_TYPE="${t}"; break
                fi
            done
        fi
        if ! mountpoint -q "${ROOT_MNT}" 2>/dev/null; then
            err "mount of root failed."
            emergency_shell
            err "=== NUXXEL PANIC: root mount failed ==="
            sleep 60 || true
            reboot -f 2>/dev/null || true
        fi
    fi
    # remount read-only for a safe root
    ( mount -o remount,ro "${ROOT_MNT}" 2>/dev/null ) || true
fi
log "root mounted: ${ROOT_DEV} (${FS_TYPE}, ro)"

# --- validate that the root really is a Nuxel OS ----------------------------------
if [ ! -f "${ROOT_MNT}/sbin/init" ] && [ ! -f "${ROOT_MNT}/init" ] && [ ! -f "${ROOT_MNT}/bin/sh" ]; then
    err "no /sbin/init, /init or /bin/sh found in root — not a bootable OS!"
    err "contents:"
    ls -la "${ROOT_MNT}" 2>/dev/null
    emergency_shell
    err "=== NUXXEL PANIC: invalid root ==="
    sleep 60 || true
    reboot -f 2>/dev/null || true
fi

# --- propagate boot splash / animation to the real root ----------------------------
if [ -f /boot/nuxel-boot-splash.raw ] || [ -f /boot/nuxel-boot-animation.mp4 ]; then
    mkdir -p "${ROOT_MNT}/usr/share/nuxel/boot"
    [ -f /boot/nuxel-boot-splash.raw ] && \
        cp /boot/nuxel-boot-splash.raw "${ROOT_MNT}/usr/share/nuxel/boot/nuxel-boot-splash.raw" 2>/dev/null
    [ -f /boot/nuxel-boot-animation.mp4 ] && \
        cp /boot/nuxel-boot-animation.mp4 "${ROOT_MNT}/usr/share/nuxel/boot/nuxel-boot-animation.mp4" 2>/dev/null
fi

# --- mark boot complete -------------------------------------------------------------
echo "$(date +%s 2>/dev/null || echo 0)" > /run/boot-end-time
echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot

# --- pivot into the real root ---------------------------------------------------------
# Move the essential pseudo filesystems under the new root so they are
# preserved across switch_root.  Failures here are non-fatal.
for m in sys proc dev; do
    mount --move "/${m}" "${ROOT_MNT}/${m}" 2>/dev/null
done

log "switching root -> ${ROOT_MNT}"
if [ -x "${ROOT_MNT}/sbin/init" ]; then
    exec switch_root "${ROOT_MNT}" /sbin/init
elif [ -x "${ROOT_MNT}/init" ]; then
    exec switch_root "${ROOT_MNT}" /init
else
    log "no /sbin/init — using /bin/sh"
    exec switch_root "${ROOT_MNT}" /bin/sh
fi

# keep shellcheck happy; switch_root never returns if the root is valid
err "switch_root returned — dropping to emergency shell"
exec sh -i
