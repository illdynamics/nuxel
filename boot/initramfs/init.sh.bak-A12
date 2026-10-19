#!/bin/sh
# --- mission milestone marker channel -----------------------------------------
# These markers are emitted by EXECUTING code, never by a build step.  They go to
# the kernel console (Samsung `console=ram`, which survives a bootloop and is
# readable as /proc/last_kmsg from TWRP) and to PID 1's stdout.  Only shell
# builtins are used, so the markers work even if the initramfs is incomplete.
#   INITRAMFS_EXECUTED     /init reached main under this kernel
#   USERDATA_DISCOVERED    USERDATA partition resolved (never SYSTEM)
#   ROOTFS_MOUNTED         Fedora rootfs mounted read-write
#   ROOTFS_HANDOFF_STARTED about to switch_root into the real root
# EVIDENCE CHANNEL (measured on this handset, 2026-10-15):
#   /dev/console exists as char 5:1 but open() returns ENODEV — this kernel's
#   `console=ram` driver provides no tty, so kernel_init prints "Warning: unable
#   to open an initial console" and PID 1 has no working stdio.  The kernel ring
#   buffer is still reachable and S-Boot's cmdline sets `printk.devkmsg=on`, so
#   evidence goes to /dev/kmsg (char 1:11) first and to the console only as a
#   fallback.  Everything printed below therefore lands in the Samsung ram
#   console and is readable as /proc/last_kmsg from recovery after a failed boot.
nuxel_say() {
    printf 'nuxel-init: %s\n' "$1" > /dev/kmsg 2>/dev/null && return 0
    printf 'nuxel-init: %s\n' "$1" > /dev/console 2>/dev/null && return 0
    printf 'nuxel-init: %s\n' "$1" 2>/dev/null || true
}

# Everything this script's shell reports on stderr (failed mounts, missing
# commands, unreadable files) must reach the kernel log too, otherwise those
# failures are silently lost on a device with no usable /dev/console.
exec 2>/dev/kmsg
nuxel_marker() { nuxel_say "NUXEL_MARKER $1"; }

# A boot that never signals success is reset by Samsung's kernel-side
# `hard_reset_hook` 35-70 s in (observed: three A7 boots died at 37 s, 68 s and
# 242 s).  This watchdog makes the attempt end deterministically *after* the
# evidence has been written, instead of hanging until the user intervenes.
( sleep "${NUXEL_BOOT_WATCHDOG:-30}"
  nuxel_say "WATCHDOG: ${NUXEL_BOOT_WATCHDOG:-30}s elapsed - persisting and rebooting"
  sync; reboot -f ) >/dev/null 2>&1 &
NUXEL_WATCHDOG_PID=$!

nuxel_marker INITRAMFS_EXECUTED
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
#
# CMDLINE INDEPENDENCE (2026-10-15): on Samsung S-Boot the kernel cmdline is
# built by the bootloader, which REPLACES /chosen/bootargs and drops the Android
# boot image header `cmdline` field. nuxel.device=/root= must therefore not be
# required: the device is auto-detected from /proc/device-tree/model|compatible
# (exynos9820/beyond2lte => s10plus) and the root is resolved by the kernel's
# PARTNAME=userdata uevent. Every failure is persisted (rootfs file
# /nuxel-boot-diag.log + raw copy in the BOOT partition tail) before rebooting.
# =============================================================================

# toybox usually needs no PATH override, but keep a sane default for busybox.
export PATH=/sbin:/bin:/usr/sbin:/usr/bin

# --- essential pseudo filesystems --------------------------------------------
# Mount results are logged, not silenced: in A9 devtmpfs mounted but the
# device-tree and PARTNAME reads were still empty, and 2>/dev/null hid why.
nuxel_mount() {  # nuxel_mount <target> <fstype> [options]
    _t="$1"; _fs="$2"; _opt="${3:-}"
    if [ ! -d "$_t" ]; then nuxel_say "WARNING: ${_t} missing from the initramfs"; return 0; fi
    if [ -n "$_opt" ]; then
        if mount -t "$_fs" -o "$_opt" none "$_t"; then nuxel_say "mounted ${_fs} on ${_t}"
        else nuxel_say "WARNING: mount -t ${_fs} -o ${_opt} ${_t} FAILED"; fi
    else
        if mount -t "$_fs" none "$_t"; then nuxel_say "mounted ${_fs} on ${_t}"
        else nuxel_say "WARNING: mount -t ${_fs} ${_t} FAILED"; fi
    fi
}
nuxel_mount /proc proc noexec,nosuid,nodev
nuxel_mount /sys sysfs noexec,nosuid,nodev
if [ -d /dev  ]; then
    if mount -t devtmpfs none /dev 2>/dev/null; then
        nuxel_say "devtmpfs mounted on /dev"
    else
        nuxel_say "WARNING: devtmpfs mount on /dev FAILED - using the initramfs device nodes"
    fi
fi
nuxel_say "probe: /sys/class/block=$(ls /sys/class/block 2>/dev/null | wc -l | tr -d ' ') entries; sysfs-dt=$( [ -d /sys/firmware/devicetree ] && echo yes || echo no ); /dev/sd*=$(ls /dev/sd* 2>/dev/null | tr '\n' ' ')"

# Mounting devtmpfs over /dev HIDES the device nodes shipped inside the
# initramfs, and this kernel's UFS scan completes a few ms after PID 1 starts
# (A10/A11: /dev/sd* was empty at t=1.95 s but /dev/sda2 existed by t=1.97 s).
# Recreate the two documented nodes if devtmpfs has not published them yet;
# the numbers come from the live device's /dev/block/by-name and from the
# kernel's own "VFS: Mounted root (ext4 filesystem) ... device 259:9" for
# sda25, which fixes the extended-partition dev_t numbering (259:(part-16)).
for spec in "sda14 8 14" "sda31 259 15"; do
    set -- $spec
    if [ ! -b "/dev/$1" ]; then
        if mknod "/dev/$1" b "$2" "$3" 2>/dev/null; then
            nuxel_say "created /dev/$1 ($2:$3) because devtmpfs had not published it yet"
        fi
    fi
done
mkdir -p /dev/pts /dev/mapper /dev/disk/by-partlabel
mount -t devpts none /dev/pts 2>/dev/null


# --- vendor kernel leashes ------------------------------------------------------
# S-Boot's cmdline is out of our hands and it carries `oops=panic`,
# `softdog.soft_margin=100 softdog.soft_panic=1`.  Measured in A7/A8: a boot that
# does not reach userspace quickly is killed by Samsung's own mechanisms
# (hung_task panic at 242 s, hard_reset_hook BUG at 10-68 s).  Temper them from
# userspace where the interfaces exist; the kernel-side hard_reset_hook is a
# force-reset *key combo* and fires because the operator holds the recovery
# buttons, so it is left alone.
if [ -w /proc/sys/kernel/hung_task_panic ]; then
    echo 0   > /proc/sys/kernel/hung_task_panic     2>/dev/null && nuxel_say "hung_task_panic=0"
fi
if [ -w /proc/sys/kernel/hung_task_timeout_secs ]; then
    echo 600 > /proc/sys/kernel/hung_task_timeout_secs 2>/dev/null && nuxel_say "hung_task_timeout_secs=600"
fi
if [ -w /proc/sys/kernel/panic ]; then
    echo 0 > /proc/sys/kernel/panic 2>/dev/null || true
fi
# Keep the software watchdog (softdog.soft_margin=100 soft_panic=1) fed.  The
# node is shipped in the initramfs so this works even before devtmpfs.
if [ -c /dev/watchdog ]; then
    ( while : ; do printf 'x' > /dev/watchdog 2>/dev/null || exit 0; sleep 10; done ) >/dev/null 2>&1 &
    nuxel_say "softdog keeper started"
fi

# --- runtime state ------------------------------------------------------------
mkdir -p /run /tmp
: > /run/nuxel-boot
echo "Nuxel" > /run/ostree-boot
echo "$(date +%s 2>/dev/null || echo 0)" > /run/boot-start-time

log() { nuxel_say "$*"; }
warn() { echo "nuxel-init: [warn] $*"; }
err()  { echo "nuxel-init: [ERROR] $*"; }

# --- persistent boot diagnostics --------------------------------------------------
# Samsung S-Boot REPLACES /chosen/bootargs with its own command line and does not
# propagate the Android boot image header `cmdline` field (device-verified on
# beyond2lte: TWRP's own "buildvariant=eng" never reaches /proc/cmdline). The
# Nuxel kernel therefore cannot be configured through the cmdline alone, and the
# Samsung persistent log buffer is cleared by S-Boot on the *next* boot, so a
# failed attempt normally leaves no evidence at all.
#
# Everything below exists so that a failed boot still produces hard evidence:
#   * /run/nuxel-diag.log            in-RAM working copy (always)
#   * <rootfs>/nuxel-boot-diag.log   written once the root is mounted
#   * raw tail of the BOOT partition mount-free copy readable with `dd` alone
# Path roots (overridable only so the decision logic can be unit-tested off
# device; the defaults are the real kernel paths).
# arm64 does not provide /proc/device-tree (that is a CONFIG_PROC_DEVICETREE
# feature of other architectures); the flattened tree is under sysfs.  Measured
# on this handset in A8: with /proc/device-tree every DT read was empty, so
# device identification and the initrd-address log silently failed.
if [ -d /sys/firmware/devicetree/base ]; then
    NUXEL_DT="${NUXEL_DT:-/sys/firmware/devicetree/base}"
else
    NUXEL_DT="${NUXEL_DT:-/proc/device-tree}"
fi
NUXEL_DT_FALLBACK=/proc/device-tree
NUXEL_BLOCK_SYS="${NUXEL_BLOCK_SYS:-/sys/class/block}"
NUXEL_DEV="${NUXEL_DEV:-/dev}"

DIAG_RAM=/run/nuxel-diag.log
: > "${DIAG_RAM}" 2>/dev/null || DIAG_RAM=/tmp/nuxel-diag.log
: > "${DIAG_RAM}" 2>/dev/null || true

diag() {
    printf 'nuxel-init: %s\n' "$*" >> "${DIAG_RAM}" 2>/dev/null || true
    log "$*"
}

# Find a block device by the kernel-provided PARTNAME uevent. devtmpfs does not
# create Android's /dev/block/platform/.../by-name links (those are made by
# Android userspace/ueventd), so detect the partition by identity, never by
# guessing a partition number.
block_by_partname() {
    _pn="$1"
    for _u in "${NUXEL_BLOCK_SYS}"/*/uevent; do
        [ -f "$_u" ] || continue
        if grep -qx "PARTNAME=${_pn}" "$_u" 2>/dev/null; then
            _b="${_u%/uevent}"; _b="${_b##*/}"
            if [ -b "${NUXEL_DEV}/${_b}" ]; then printf '%s/%s\n' "${NUXEL_DEV}" "${_b}"; return 0; fi
        fi
    done
    return 1
}

# Mount-free diagnostic slot: the unused tail of the BOOT partition (the boot
# image occupies ~22 MiB of a ~55 MiB partition). Read it back from recovery:
#   dd if=/dev/block/by-name/boot bs=512 skip=$(( $(cat /sys/class/block/sda14/size) - 128 )) 2>/dev/null | head -c 4096
diag_raw_slot() {
    _boot="$(block_by_partname boot 2>/dev/null)" || return 1
    [ -n "${_boot}" ] || return 1
    _blk="${_boot##*/}"
    _sec="$(cat "${NUXEL_BLOCK_SYS}/${_blk}/size" 2>/dev/null)" || return 1
    case "${_sec}" in ''|*[!0-9]*) return 1 ;; esac
    [ "${_sec}" -gt 1024 ] || return 1
    printf '%s %s\n' "${_boot}" "$(( (_sec - 128) * 512 ))"
}

diag_persist() {
    if [ -n "${ROOT_MNT:-}" ] && [ -d "${ROOT_MNT}" ]; then
        cp "${DIAG_RAM}" "${ROOT_MNT}/nuxel-boot-diag.log" 2>/dev/null || true
    fi
    _slot="$(diag_raw_slot 2>/dev/null)" || return 0
    [ -n "${_slot}" ] || return 0
    _dev="${_slot%% *}"; _off="${_slot##* }"
    # The free tail is 128 sectors; never write more than 120 of them, and keep
    # the head of the record (version/cmdline/device-tree/reason) if it is long.
    if [ -b "${_dev}" ]; then
        head -c 61440 "${DIAG_RAM}" 2>/dev/null \
            | dd of="${_dev}" bs=512 seek="$(( _off / 512 ))" conv=notrunc 2>/dev/null || true
    fi
    sync
}

# Early heartbeat: once devtmpfs is up the BOOT partition slack is reachable, so
# persist the diagnostic record immediately instead of only at the end.  If the
# boot later dies of Samsung's hard_reset_hook / a hung_task panic, this record
# is still readable with a single dd from recovery.
if command -v dd >/dev/null 2>&1; then
    diag_raw_slot >/dev/null 2>&1 || true
    nuxel_say "early heartbeat: block devices $(ls /dev/sd* 2>/dev/null | tr '\n' ' ')"
fi

# The kernel ring buffer holds the hard evidence, but it is read from recovery
# (/proc/last_kmsg), NOT from here: on this kernel toybox's `dmesg` blocks for
# ever on /dev/kmsg (measured in A8 - PID 1 slept until the watchdog rebooted
# it, with the last log line being "block-devices:" immediately before the
# dmesg call).  Never call dmesg from the initramfs.
diag_dump_kmsg() {
    printf -- '--- kernel log: read /proc/last_kmsg from recovery ---\n' \
        >> "${DIAG_RAM}" 2>/dev/null || true
}

diag_environment() {
    diag "version: $(cat /proc/version 2>/dev/null)"
    diag "cmdline: $(cat /proc/cmdline 2>/dev/null)"
    if [ -f "${NUXEL_DT}/model" ]; then
        diag "dt-model: $(tr -d '\0' < "${NUXEL_DT}/model" 2>/dev/null)"
    fi
    if [ -f "${NUXEL_DT}/compatible" ]; then
        diag "dt-compat: $(tr '\0' ' ' < "${NUXEL_DT}/compatible" 2>/dev/null)"
    fi
    for _p in linux,initrd-start linux,initrd-end; do
        if [ -f "${NUXEL_DT}/chosen/${_p}" ]; then
            _v="$(hexdump -e '1/4 "%08x"' "${NUXEL_DT}/chosen/${_p}" 2>/dev/null || true)"
            diag "chosen ${_p}: ${_v:-unreadable}"
        fi
    done
    diag "block-devices: $(ls /dev/sd* /dev/mmcblk* 2>/dev/null | tr '\n' ' ')"
    diag "initrd-declared-by-bootloader: start=$(cat "${NUXEL_DT}/chosen/linux,initrd-start" 2>/dev/null | hexdump -e '1/4 "%08x"' 2>/dev/null) end=$(cat "${NUXEL_DT}/chosen/linux,initrd-end" 2>/dev/null | hexdump -e '1/4 "%08x"' 2>/dev/null)"
}

# Single failure exit: always record the reason + kernel log, then persist.
fail_boot() {
    diag "[FATAL] $*"
    diag_dump_kmsg
    diag_persist
    err "$*"
}

# --- command provider ----------------------------------------------------------
# Prefer toybox, then busybox.  If neither is present we still carry on using
# whatever coreutils are installed in the initramfs.
if [ ! -e /bin/sh ]; then
    if [ -x /bin/toybox ]; then
        ln -sf toybox /bin/sh
        for cmd in mount umount switch_root modprobe mknod mkswap mkfs.ext4 \
                   tar gzip gunzip ls cat printf echo sed grep awk find sleep date ps \
                   df du sh sync reboot poweroff dd cp mv rm mkdir ln chown \
                   chmod blkid losetup head tail cut tr touch wc; do
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

# HARD IDENTITY PIN.  S-Boot's own command line always carries the board, and on
# A10 the inferred path proved unreliable: the cmdline branch reported
# device=s10plus yet the dispatch resolved a generic root.  Pin it here (before
# the device-tree inference block) so the s10plus root-resolution branch is
# guaranteed to run on this board.
case " ${CMDLINE} " in
    *androidboot.hardware=exynos9820*|*androidboot.bootloader=G97*)
        DEVICE=s10plus
        nuxel_say "identity pin: S-Boot cmdline reports exynos9820 -> DEVICE=s10plus" ;;
esac
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
# HARD OVERRIDE (added after A10/A11): on this board the dispatch below was
# observed to run the *generic* probe even with DEVICE='s10plus' logged, and the
# generic probe's candidates (/dev/sda1, /dev/sda2) are bootloader partitions.
# The board identity comes from S-Boot's own command line, so resolve USERDATA
# explicitly here and never let a bootloader partition become the root.
force_s10plus_root() {
    [ -n "${NUXEL_FORCE_S10PLUS_DONE:-}" ] && return 0
    case " ${CMDLINE} " in
        *androidboot.hardware=exynos9820*|*androidboot.bootloader=G97*) : ;;
        *) return 0 ;;
    esac
    case "${ROOT_DEV}" in
        ""|/dev/sda1|/dev/sda2|/dev/sda25)
            nuxel_say "root override: forcing the s10plus USERDATA resolution (was '${ROOT_DEV}')"
            ROOT_DEV=""
            _t=0
            while [ "$_t" -lt 12 ]; do
                ROOT_DEV="$(s10plus_userdata_device)"
                [ -n "${ROOT_DEV}" ] && break
                _t=$((_t + 1)); sleep 1
            done
            if [ -n "${ROOT_DEV}" ]; then
                nuxel_say "USERDATA discovered by PARTNAME after ${_t}s: ${ROOT_DEV}"
            elif [ -b /dev/sda31 ]; then
                ROOT_DEV=/dev/sda31
                nuxel_say "PARTNAME discovery failed after ${_t}s; using documented /dev/sda31 (by-name userdata) - the rootfs is verified below"
                diag "USERDATA_FALLBACK /dev/sda31"
            else
                nuxel_say "USERDATA could not be located at all (no PARTNAME, no /dev/sda31)"
            fi
            ;;
        *) nuxel_say "root override: leaving ROOT_DEV='${ROOT_DEV}'" ;;
    esac
    NUXEL_FORCE_S10PLUS_DONE=1
}

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

# The Samsung downstream Linux kernel does not necessarily create Android's
# /dev/block/platform/.../by-name symlinks.  Those are normally made by
# Android userspace (ueventd).  devtmpfs exposes /dev/sdXn, and the kernel's
# uevent files expose PARTNAME.  Never guess a partition number.
s10plus_userdata_device() {
    # Existing Android-style links or udev-created links, when available.
    for candidate in \
        /dev/block/platform/13d60000.ufs/by-name/userdata \
        /dev/block/by-name/userdata \
        /dev/disk/by-partlabel/userdata \
        /dev/disk/by-partlabel/USERDATA; do
        [ -b "$candidate" ] && { printf '%s\n' "$candidate"; return 0; }
    done
    # mdev populates /dev when devtmpfs alone has no partition node; it does
    # not magically create Android by-name links, so use sysfs PARTNAME below.
    command -v mdev >/dev/null 2>&1 && mdev -s 2>/dev/null || true
    for uevent in "${NUXEL_BLOCK_SYS}"/*/uevent; do
        [ -f "$uevent" ] || continue
        if grep -iq '^PARTNAME=userdata$' "$uevent" 2>/dev/null; then
            blockname="${uevent%/uevent}"
            blockname="${blockname##*/}"
            [ -b "${NUXEL_DEV}/$blockname" ] && {
                printf '%s/%s\n' "${NUXEL_DEV}" "$blockname"; return 0;
            }
        fi
    done
    return 1
}

# --- device identity without the kernel cmdline ------------------------------------
# nuxel.device= may be absent on a perfectly good boot because S-Boot rewrote
# /chosen/bootargs (see the diagnostics note above). Identify the platform from
# the device tree the bootloader actually handed us, instead of falling through
# to the generic A/B probe, which cannot resolve this device's root (there is no
# /dev/disk/by-partlabel here, and the early /dev/sdaN candidates are bootloader
# partitions).
diag_environment
if [ -z "${DEVICE}" ]; then
    _dt_model="$(tr -d '\0' < "${NUXEL_DT}/model" 2>/dev/null || true)"
    _dt_compat="$(tr '\0' ' ' < "${NUXEL_DT}/compatible" 2>/dev/null || true)"
    if [ -z "${_dt_model}" ] && [ -f "${NUXEL_DT_FALLBACK}/model" ]; then
        NUXEL_DT="${NUXEL_DT_FALLBACK}"
        _dt_model="$(tr -d '\0' < "${NUXEL_DT}/model" 2>/dev/null || true)"
        _dt_compat="$(tr '\0' ' ' < "${NUXEL_DT}/compatible" 2>/dev/null || true)"
    fi
    nuxel_say "device-tree source: ${NUXEL_DT} model='${_dt_model}'"
    # S-Boot's own command line is the most reliable identity signal on this
    # board: it always carries androidboot.hardware=exynos9820 even when the
    # device tree cannot be read from the initramfs.
    case " ${CMDLINE} " in
        *androidboot.hardware=exynos9820*|*androidboot.bootloader=G97*)
            DEVICE=s10plus
            nuxel_say "auto-detected device=s10plus from the S-Boot cmdline" ;;
    esac
    warn "no nuxel.device= on cmdline; identifying device from the device tree"
    case "${_dt_model}" in
        *BEYOND2LTE*|*beyond2lte*|*BEYOND1LTE*|*beyond1lte*) DEVICE=s10plus ;;
    esac
    if [ -z "${DEVICE}" ]; then
        case " ${_dt_compat} " in
            *exynos9820*|*exynos9*) DEVICE=s10plus ;;
        esac
    fi
    if [ -n "${DEVICE}" ]; then
        log "auto-detected device=${DEVICE} from device tree ('${_dt_model}')"
    fi
fi

# Dispatch on nuxel.device= — each target resolves its own root device:
#   mustang / vm / ""   -> existing A/B dynamic-partition probe (unchanged)
#   s10plus             -> A-only UFS probe: root= > userdata ONLY (not SYSTEM)
#   g7power             -> eMMC probe: root= > userdata > system_a > system
ROOT_DEV=""
nuxel_say "dispatch: DEVICE='${DEVICE}' ROOT_SPEC='${ROOT_SPEC}' ROOT_FSTYPE='${ROOT_FSTYPE}'"
case "${DEVICE}" in
    mustang|vm|"")
        # Existing A/B + generic probe (mustang dynamic partitions; vm/QEMU
        # virtio).  Byte-equivalent to the pre-multi-device behaviour:
        # explicit root= > /dev/disk/by-partlabel/system_${SLOT} > generic.
        ROOT_DEV="$(find_root)"
        nuxel_say "generic probe selected '${ROOT_DEV}'"
        case " ${CMDLINE} " in
            *androidboot.hardware=exynos9820*)
                nuxel_say "refusing the generic probe on an exynos9820 board: its candidates (/dev/sdaN) are bootloader and Android partitions, not a Nuxel rootfs"
                ROOT_DEV="" ;;
        esac
        ;;
    s10plus)
        # S10+ A-only UFS layout:
        # Boot -> Samsung downstream kernel Linux. Root is on USERDATA only.
        # UFS path: /dev/block/platform/13d60000.ufs/by-name/
        # Probe order: explicit USERDATA root= > PARTNAME=userdata
        # Only USERDATA is expected in this image's flashing plan. Do NOT
        # silently fall back to SYSTEM, which may hold unrelated user data.
        # A root= by-name/userdata path is a hint, not proof it exists.
        if [ -n "${ROOT_SPEC}" ] && [ -b "${ROOT_SPEC}" ]; then
            ROOT_DEV="${ROOT_SPEC}"
        elif [ -z "${ROOT_SPEC}" ] || [ "${ROOT_SPEC##*/}" = userdata ]; then
            tries=0
            while [ "$tries" -lt 30 ]; do
                ROOT_DEV="$(s10plus_userdata_device)" && [ -n "$ROOT_DEV" ] && break
                tries=$((tries + 1))
                sleep 1
            done
        else
            err "s10plus: explicit root= is not a block device: ${ROOT_SPEC}"
        fi
        # Documented fallback for this board when sysfs PARTNAME discovery is
        # unavailable: /dev/block/by-name/userdata is sda31 on beyond2lte (read
        # from the live device), and the kernel's own
        # "VFS: Mounted root (ext4 filesystem) ... device 259:9" for sda25
        # confirms the extended-partition dev_t numbering (259:(part-16)).  The
        # partition image is *verified* below before it is trusted as the rootfs.
        if [ -z "${ROOT_DEV}" ] && [ -b /dev/sda31 ]; then
            ROOT_DEV=/dev/sda31
            nuxel_say "PARTNAME discovery unavailable; using documented fallback /dev/sda31 (by-name userdata) - rootfs will be verified"
            diag "USERDATA_FALLBACK /dev/sda31"
        fi
        if [ -z "${ROOT_DEV}" ] || [ ! -b "${ROOT_DEV}" ]; then
            fail_boot "s10plus: USERDATA not found after probe; refusing SYSTEM fallback"
            emergency_shell
            # The diagnostic record is already persisted; reboot so the operator
            # can read it from recovery instead of hanging forever. PID 1 must
            # never continue into a guessed partition, and must never exit.
            sync
            sleep 15 || true
            reboot -f 2>/dev/null || true
            while :; do sleep 60; done
        fi
        log "s10plus: root -> ${ROOT_DEV} (fstype: ${ROOT_FSTYPE:-ext4})"
        diag "USERDATA_DISCOVERED ${ROOT_DEV}"
        nuxel_marker USERDATA_DISCOVERED
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

force_s10plus_root

if [ -z "${ROOT_DEV}" ]; then
    fail_boot "no root block device found (slot=${SLOT})"
    emergency_shell
    echo "=== NUXXEL PANIC: no root device ==="
    sleep 15 || true
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
# Fedora phone userspace expects a writable /var, /etc and journal. Keep the
# minimal phase-1 image safe on first mount, but for s10plus + rw kernel
# command line prefer rw. Never turn a mount failure into a SYSTEM fallback.
ROOT_MOUNT_MODE=ro
if [ "$DEVICE" = s10plus ]; then
    # Fedora/systemd needs the root writable (journal, /var, /etc) and the
    # diagnostic record is written into it. This cannot come from the kernel
    # cmdline: S-Boot replaces /chosen/bootargs and drops the boot image header
    # cmdline. Default to rw here, still overridable with an explicit `ro`.
    ROOT_MOUNT_MODE=rw
    case " ${CMDLINE} " in *' ro '*) ROOT_MOUNT_MODE=ro ;; esac
fi
if ! mount -t "${FS_TYPE}" -o "${ROOT_MOUNT_MODE}" "${ROOT_DEV}" "${ROOT_MNT}" 2>/dev/null; then
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
            fail_boot "root mount failed"
            emergency_shell
            err "=== NUXXEL PANIC: root mount failed ==="
            sleep 15 || true
            reboot -f 2>/dev/null || true
        fi
    fi
    # Preserve writable mode for Fedora systemd; other paths retain legacy ro.
    ( mount -o remount,"${ROOT_MOUNT_MODE}" "${ROOT_MNT}" 2>/dev/null ) || true
fi
log "root mounted: ${ROOT_DEV} (${FS_TYPE}, mode=${ROOT_MOUNT_MODE})"
diag "root mounted: ${ROOT_DEV} (${FS_TYPE}, mode=${ROOT_MOUNT_MODE})"
diag "ROOTFS_MOUNTED ${ROOT_DEV} ${FS_TYPE} ${ROOT_MOUNT_MODE}"
nuxel_marker ROOTFS_MOUNTED
diag_dump_kmsg
diag_persist

# --- validate that the root really is a Nuxel OS ----------------------------------
_osrel="$(cat "${ROOT_MNT}/usr/lib/os-release" "${ROOT_MNT}/etc/os-release" 2>/dev/null | head -4 | tr '\n' ' ')"
diag "rootfs os-release: ${_osrel:-<none>}"
nuxel_say "rootfs os-release: ${_osrel:-<none>}"
case "${_osrel}" in
    *Fedora*|*Nuxel*) : ;;
    *) diag "ROOTFS_NOT_FEDORA ${_osrel}"
       fail_boot "the mounted root is not identified as a Nuxel/Fedora rootfs"
       emergency_shell
       sync; sleep 10; reboot -f 2>/dev/null || true
       while :; do sleep 60; done ;;
esac

if [ ! -f "${ROOT_MNT}/sbin/init" ] && [ ! -f "${ROOT_MNT}/init" ] && [ ! -f "${ROOT_MNT}/bin/sh" ]; then
    err "no /sbin/init, /init or /bin/sh found in root — not a bootable OS!"
    err "contents:"
    ls -la "${ROOT_MNT}" 2>/dev/null
    diag "root listing: $(ls -la "${ROOT_MNT}" 2>/dev/null | tr '\n' '|')"
    fail_boot "invalid root: no /sbin/init, /init or /bin/sh"
    emergency_shell
    err "=== NUXXEL PANIC: invalid root ==="
    sleep 15 || true
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

diag "ROOTFS_HANDOFF_STARTED -> ${ROOT_MNT}"
nuxel_marker ROOTFS_HANDOFF_STARTED
# The real root's init owns the boot from here; disarm the reboot watchdog.
[ -n "${NUXEL_WATCHDOG_PID:-}" ] && kill "${NUXEL_WATCHDOG_PID}" 2>/dev/null
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
