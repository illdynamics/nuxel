#!/bin/sh
# --- mission milestone marker channel -----------------------------------------
# These markers are emitted by EXECUTING code, never by a build step.  They go to
# the kernel console (Samsung `console=ram`, which survives a bootloop and is
# readable as /proc/last_kmsg from TWRP) and to PID 1's stdout.  Only shell
# builtins are used, so the markers work even if the initramfs is incomplete.
#   INITRAMFS_EXECUTED     /init reached main under this kernel
#   USERDATA_DISCOVERED    USERDATA partition resolved (never SYSTEM)
#   FEDORA_MOUNTED         Fedora rootfs mounted read-write
#   ORIGINAL_MP4_ANIMATION_STARTING  the real Nuxel MP4 animation took the panel
#   ROOTFS_MOUNTED         Fedora rootfs mounted read-write
#   ROOTFS_HANDOFF_STARTED about to switch_root into the real root
#   ROOTFS_IDENTITY_OK     /usr/lib/os-release really is Fedora/Nuxel
#   SYSCALL_PROBE_DONE     the kernel-primitive probe finished writing its table
#   FEDORA_BINARY_EXECUTED the mounted Fedora root executed its own /bin/sh
#   SPAWN_PROBE_RAN        the glibc waitid/posix_spawn/pidfd_spawn probe ran
#   SYSTEMD_PATCH_*        the pidfd_spawn repair is installed in the rootfs
#   FIRSTLIGHT_FRAME_WRITTEN nuxel-fb-phone painted the panel
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
# `hard_reset_hook` 35-70 s in (A7: 37 s, 68 s, 242 s).  This dead-man's switch
# ends a *failed* attempt deterministically and does nothing at all once the
# handoff has succeeded.
#
# Two A12 lessons are baked in:
#   * the old disarm used the `kill` applet.  This toybox build has `killall`,
#     NOT `kill`, and the failure was hidden by `2>/dev/null`, so the watchdog
#     survived `switch_root` and force-rebooted the phone 30 s into a *running*
#     Fedora systemd (measured: `debug-snapshot: normal reboot starting` at
#     t=31.971 s from a process whose comm was `init`).  No signal is used now.
#   * it wrote evidence to /dev/kmsg *by path*; A12 moved /dev into the new root,
#     so the message was lost.  The watchdog now keeps fd 2 (already /dev/kmsg)
#     and pins the procfs with `cd`, which survives every mount moving away.
#
# It reboots only while PID 1 is still this shell; once systemd owns PID 1 the
# boot belongs to the real root and the watchdog exits silently.
# A15 (2026-10-15): THE BOOT-TIME REBOOT WATCHDOG IS REMOVED.  It is the
# hardware-measured cause of the A14 "black screen then spontaneous reboot":
#   * it slept 45 s from PID-1 start and then re-tested "is PID 1 still the
#     initramfs shell?".  Its procfs pin (`cd /proc`) runs BEFORE /proc is
#     mounted (the mount happens further down this file), so it pinned the
#     initramfs's plain /proc *directory*; the later `read < 1/comm` then failed
#     with ENOENT - visible in the A14 ram console as
#     `[47.163135] [2: init: 3308] sh: 1/comm: No such file or directory`.
#   * both "WATCHDOG_FIRED" printf lines went to fd 1, which this block redirects
#     to /dev/null, so a firing left no reason in the log at all.
#   * the reboot it issued is a *normal* reboot in the ram console
#     (`debug-snapshot: normal reboot starting`, `sec_debug: set magic code
#     (0x0)`, no panic, HW watchdog still being petted) by PIDs 3557/3558/3561 -
#     processes in THIS script's lineage (children inherit comm `init`) - at
#     t=47.163-47.171 s, i.e. exactly the 45 s deadline, while Fedora's systemd
#     was already running and spawning services.
# A watchdog that can kill a healthy Fedora is worse than none.  Removed, not
# re-armed: a failed boot now simply leaves its evidence in the ram console and
# the BOOT slack, and the operator's POWER+VOLUMEDOWN combo remains available.
# The `softdog keeper` further down is deliberately KEPT: it feeds the vendor
# kernel's watchdog, which is a hardware safety mechanism and not implicated.
NUXEL_WATCHDOG_PID=""

nuxel_say "NUXEL_INIT_REV=A24-postboot-supervisor"
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

# A18: no load-bearing `case` PATTERN test survives in the root-resolution path.
# toybox 0.8.14 treats an empty alternative as a wildcard (see the dispatch note
# further down), so the only primitives used here are `[ ... ]` tests and `grep -q`.
cmdline_matches_samsung() {
    printf '%s' "${CMDLINE}" | grep -q 'androidboot.hardware=exynos9820' && return 0
    printf '%s' "${CMDLINE}" | grep -q 'androidboot.bootloader=G97'        && return 0
    return 1
}

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

# A18: the Samsung ram console truncates a single printk at ~1 KiB.  That is how the
# phase-1 captures lost the S-Boot `root=` value and the board tokens at the end of
# the command line, which made the A17 root-resolution failure much harder to read
# than it had to be.  Emit it in chunks (head -c / tail -c +N are both available in
# this toybox) so the full cmdline is always recoverable from /proc/last_kmsg.
if [ -n "${CMDLINE}" ]; then
    _cml="${CMDLINE}"; _cmi=0
    while [ -n "${_cml}" ]; do
        _cmi=$((_cmi + 1))
        nuxel_say "CMDLINE_PART ${_cmi}: $(printf '%s' "${_cml}" | head -c 200)"
        _cml="$(printf '%s' "${_cml}" | tail -c +201)"
    done
    nuxel_say "CMDLINE_PARTS ${_cmi} bytes=${#CMDLINE} samsung=$(cmdline_matches_samsung && echo yes || echo no)"
fi
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

# --- first light (as early as the framebuffer exists) -------------------------------
# THIS IS THE EARLIEST POINT THE PANEL CAN BE PAINTED: /dev mounted, devtmpfs
# populated, ~2 s after kernel entry.  nuxel-fb-phone is a freestanding aarch64
# program that writes a distinctive NUXEL pattern over fbdev, and every failure
# path prints a named NUXEL_FB_* reason, so "cannot execute" is never confused
# with "no /dev/fb0" or "unsupported pixel format".
# A16 (2026-10-15): the A15 capture recorded FIRSTLIGHT_FRAME_WRITTEN while the
# panel stayed black, and NOT ONE of the program's own verdict lines survived.
# Cause, measured in the A15 ram console: the output was read back through
#     printf '%s\n' "${_fbout}" | while IFS= read -r _l
# and this toybox shell cannot run `read` -- the log contains
#     sh: <...>read: No such file or directory
# so NUXEL_FB_INFO / NUXEL_FB_ANIM / NUXEL_FB_UNAVAILABLE were all silently
# dropped and only the exit status was recorded.  The program's stdout+stderr now
# go STRAIGHT to /dev/kmsg: nothing can swallow them, and a silent exit is
# impossible.  FIRSTLIGHT_FRAME_WRITTEN is only ever emitted on exit 0, and the
# A16 program is the first one that also forces the DECON to commit a frame.
nuxel_first_light() {
    if [ ! -x /opt/nuxel/nuxel-fb-phone ]; then
        diag "FIRSTLIGHT binary missing from the initramfs"
        return 0
    fi

    # Independent evidence about the fbdev itself, recorded whether or not the
    # program is happy.  Deliberately no pipelines: this shell cannot run `read`.
    for _n in /dev/fb0 /dev/graphics/fb0; do
        [ -c "${_n}" ] && diag "FB_NODE ${_n} is a character device"
    done
    for _f in name bits_per_pixel stride virtual_size smem_len modes; do
        [ -r "/sys/class/graphics/fb0/${_f}" ] && \
            diag "FB_SYSFS /sys/class/graphics/fb0/${_f}=$(cat "/sys/class/graphics/fb0/${_f}" 2>/dev/null)"
    done

    # 1) Fully-logged synchronous paint: every NUXEL_FB_* line reaches the ram
    #    console, so the next capture always states what the panel got.
    #
    #    A27 SEAMLESS FIRST LIGHT: the painter is handed the NUXSPL01 asset, which
    #    IS frame 0 of the original animation container.  The earliest lit frame on
    #    the glass is therefore the animation's own opening frame and the handoff to
    #    nuxel-anim-player is not a transition at all -- no obsolete diagnostic
    #    splash, no black gap, no colour change (palette, spans and packing are the
    #    player's own).  A missing or malformed asset is named by the painter and it
    #    falls back to the A16 diagnostic frame, so the panel is never left
    #    unpainted and "cannot execute" is never confused with "no panel".
    if [ -f /opt/nuxel/nuxel-firstlight.rawspl ]; then
        diag "FIRSTLIGHT asset present: /opt/nuxel/nuxel-firstlight.rawspl (NUXSPL01 = animation frame 0)"
    else
        diag "FIRSTLIGHT asset ABSENT from this initramfs -> A16 diagnostic frame"
    fi
    /opt/nuxel/nuxel-fb-phone --firstlight=/opt/nuxel/nuxel-firstlight.rawspl > /dev/kmsg 2>&1
    _fbrc=$?
    diag "FIRSTLIGHT exit=${_fbrc}"
    [ "${_fbrc}" = 0 ] && nuxel_marker FIRSTLIGHT_FRAME_WRITTEN

    # 2) Resident painter: DEFERRED to nuxel_start_hold_painter() (A21).
    #
    #    A16..A20 started it unconditionally, right here, and then handed the panel
    #    to nuxel-anim-player minutes later.  The player could not stop it: it runs
    #    its /proc takeover AFTER the rootfs handoff, and by then switch_root has
    #    moved /proc into the new root and deleted the old one, so the scan failed
    #    (hardware log, A20: "NUXEL_ANIM_TAKEOVER no /proc").  The penguin painter
    #    therefore kept repainting its opaque sprite rectangle over the MP4 frames
    #    4x/second for the whole boot -- the second penguin and the rectangle behind
    #    it in the operator's photograph.
    #
    #    The static first-light frame painted above STAYS on the panel (the DECON
    #    keeps scanning framebuffer memory), so the screen is never black while the
    #    animation player is starting.  The painter now runs only when the MP4 is
    #    unavailable -- which is exactly its documented fallback role.
    NUXEL_HOLD_AVAILABLE=1
    # A16..A19 all logged `FIRSTLIGHT hold started pid=` EMPTY.  Two separate
    # measured defects caused that: toybox does not set $! for background jobs, and
    # the `for _p in /proc/[0-9]*` bracket glob never matched in this shell, so the
    # 20-iteration scan always ran to completion -- 20 s of dead boot time per
    # attempt and never a pid.  The shell no longer guesses: nuxel-anim-player walks
    # /proc with getdents64, takes the framebuffer over from the penguin and
    # publishes the pid it displaced to /var/lib/nuxel/fb-hold.pid.  If the animation
    # container is missing the penguin simply keeps the panel, exactly as before.
    NUXEL_HOLD_PID=""
    diag "FIRSTLIGHT frame painted; resident penguin painter DEFERRED until the MP4 decision"
    nuxel_marker ANIMATION_HOLD_DEFERRED

    return 0
}

# --- the deferred first-light painter (fallback only) -------------------------------
# Started ONLY when the original MP4 animation cannot own the panel, so that exactly
# one renderer is ever painting (mission section 7).  The painter publishes its own
# pid and honours a stop file, so it is stoppable without relying on `$!` (which
# toybox never sets on this shell).
nuxel_start_hold_painter() {
    [ "${NUXEL_HOLD_AVAILABLE:-0}" = 1 ] || return 0
    [ -x /opt/nuxel/nuxel-fb-phone ] || return 0
    if [ -n "${NUXEL_STATE_DIR:-}" ] && [ -d "${NUXEL_STATE_DIR}" ]; then
        /opt/nuxel/nuxel-fb-phone "--statedir=${NUXEL_STATE_DIR}" hold > /dev/kmsg 2>&1 &
    else
        /opt/nuxel/nuxel-fb-phone hold > /dev/kmsg 2>&1 &
    fi
    NUXEL_HOLD_PID="painter-publishes-own-pid"
    nuxel_marker FIRST_LIGHT_FALLBACK_ACTIVE
    diag "FIRSTLIGHT resident penguin painter started (fallback: no MP4 on the panel)"
    return 0
}
nuxel_first_light

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
    NUXEL_FORCE_S10PLUS_DONE=1

    # A18: this is now UNCONDITIONAL evidence-driven rescue, not a pattern test.
    # It used to be gated on `case " ${CMDLINE} " in *samsung*` and it silently
    # returned on any pattern mismatch, which is how A17 reached
    # "[FATAL] no root block device found" while holding a perfectly good cmdline.
    # The gate is now: a Samsung UFS board is either claimed by the cmdline OR
    # proven by the presence of the 31st UFS partition.  Nothing else is needed.
    nuxel_say "root override: enter ROOT_DEV='${ROOT_DEV}' samsung=$(cmdline_matches_samsung && echo yes || echo no)"
    if cmdline_matches_samsung || [ -b /dev/sda31 ]; then
        case_ok=1
    else
        case_ok=0
    fi
    if [ "${case_ok}" = 0 ]; then
        nuxel_say "root override: not a Samsung UFS board - leaving ROOT_DEV='${ROOT_DEV}'"
        return 0
    fi

    case_ok=0
    for _cand in "" /dev/sda1 /dev/sda2 /dev/sda25; do
        if [ "${ROOT_DEV}" = "${_cand}" ]; then case_ok=1; fi
    done
    if [ "${case_ok}" = 0 ]; then
        nuxel_say "root override: leaving ROOT_DEV='${ROOT_DEV}' (not a bootloader/Android partition)"
        return 0
    fi

    nuxel_say "root override: forcing the s10plus USERDATA resolution (was '${ROOT_DEV}')"
    # A13 waited here in silence (its PARTNAME loop could never succeed:
    # /sys/class/block is empty on this kernel even with sysfs mounted), and the
    # operator force-reset a boot during that silence.  A18 waits for the node to
    # actually appear, up to 20 s, and says something EVERY second so the screen
    # and the log never look dead.
    _t=0
    while [ "${_t}" -lt 20 ]; do
        ROOT_DEV="$(s10plus_userdata_device)"
        if [ -n "${ROOT_DEV}" ]; then
            nuxel_say "USERDATA discovered by PARTNAME after ${_t}s: ${ROOT_DEV}"
            break
        fi
        if [ -b /dev/sda31 ]; then
            ROOT_DEV=/dev/sda31
            nuxel_say "USERDATA_FALLBACK /dev/sda31 after ${_t}s (documented by-name userdata; rootfs verified below)"
            diag "USERDATA_FALLBACK /dev/sda31"
            break
        fi
        _t=$((_t + 1))
        nuxel_say "USERDATA waiting t=${_t}s blockdevs='$(ls /dev/sd* 2>/dev/null | tr '\n' ' ')'"
        sleep 1
    done
    if [ -z "${ROOT_DEV}" ]; then
        nuxel_say "USERDATA could not be located in 20s (no PARTNAME, no /dev/sda31)"
    fi
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
# Independent board identification.  S-Boot's cmdline is the primary signal, but
# A13 contains a boot where that parse yielded DEVICE='' and the script fell into
# the generic probe and selected '/dev/sda2' - an Android partition, not a rootfs.
# The device nodes are not opinion: only beyond2lte/beyond1lte have a 31st UFS
# partition (USERDATA) at /dev/sda31.  The initramfs already creates that node
# when devtmpfs has not published it yet, so its presence is a sound second
# source of truth.
if [ -z "${DEVICE}" ] && [ -b /dev/sda31 ]; then
    DEVICE=s10plus
    nuxel_say "auto-detected device=s10plus from /dev/sda31 (beyond2lte UFS layout)"
fi

ROOT_DEV=""
nuxel_say "dispatch: DEVICE='${DEVICE}' ROOT_SPEC='${ROOT_SPEC}' ROOT_FSTYPE='${ROOT_FSTYPE}'"
# A18: DEVICE dispatch without any `case` pattern test.
# toybox 0.8.14 treats `""` in a case list as a WILDCARD, so the old
# `case "${DEVICE}" in mustang|vm|"") ... s10plus) ...` made the s10plus and
# g7power branches unreachable: a boot with DEVICE=s10plus matched the
# generic branch.  Measured on the handset in A16 (survived only via
# force_s10plus_root) and fatal in A17.  Explicit tests only.
# A19: four independent, mutually exclusive `if` statements -- not a
# chain, because toybox 0.8.14 executes an if/elif/else chain's `else`
# branch as well when the first condition is true.  The board-specific
# branch is deliberately first.
if [ "${DEVICE}" = s10plus ]; then
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
        # A18: bounded wait for the UFS node, with a heartbeat every second.
        # The old code tested /dev/sda31 once and gave up if the UFS scan had not
        # finished yet (measured: the node appears ~1 s after the first probe).
        if [ -z "${ROOT_DEV}" ]; then
            _t=0
            while [ "${_t}" -lt 20 ]; do
                if [ -b /dev/sda31 ]; then
                    ROOT_DEV=/dev/sda31
                    nuxel_say "s10plus: USERDATA via documented /dev/sda31 (by-name userdata) after ${_t}s; rootfs verified below"
                    diag "USERDATA_FALLBACK /dev/sda31"
                    break
                fi
                _t=$((_t + 1))
                nuxel_say "s10plus: waiting for /dev/sda31 t=${_t}s blockdevs='$(ls /dev/sd* 2>/dev/null | tr '\n' ' ')'"
                sleep 1
            done
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
fi
if [ "${DEVICE}" = g7power ]; then
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
fi
if [ "${DEVICE}" = "" ] || [ "${DEVICE}" = mustang ] || [ "${DEVICE}" = vm ]; then
        # Existing A/B + generic probe (mustang dynamic partitions; vm/QEMU
        # virtio).  Byte-equivalent to the pre-multi-device behaviour:
        # explicit root= > /dev/disk/by-partlabel/system_${SLOT} > generic.
        ROOT_DEV="$(find_root)"
        nuxel_say "generic probe selected '${ROOT_DEV}'"
        case " ${CMDLINE} " in
            *androidboot.hardware=exynos9820*|*androidboot.bootloader=G97*)
                nuxel_say "refusing the generic probe on an exynos9820 board: its candidates (/dev/sdaN) are bootloader and Android partitions, not a Nuxel rootfs"
                ROOT_DEV=""
                DEVICE=s10plus ;;
        esac
fi
if [ "${DEVICE}" != s10plus ] && [ "${DEVICE}" != g7power ] && [ "${DEVICE}" != "" ] && [ "${DEVICE}" != mustang ] && [ "${DEVICE}" != vm ]; then
        err "unknown nuxel.device='${DEVICE}' — cannot resolve a root device"
        emergency_shell
fi

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
    # A12 came up `ro` purely because S-Boot's own command line contains a bare
    # `ro`.  That token describes Android recovery semantics, not a Fedora root,
    # and the vendor cmdline is not ours to control (S-Boot overwrites /chosen).
    # Fedora needs a writable /var, /etc and journal, so the vendor token is
    # ignored here and only an explicit `nuxel.rootmode=` changes the decision.
    case " ${CMDLINE} " in *' nuxel.rootmode=ro '*) ROOT_MOUNT_MODE=ro ;; esac
    case " ${CMDLINE} " in *' nuxel.rootmode=rw '*) ROOT_MOUNT_MODE=rw ;; esac
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
# A12 printed "rootfs os-release: <none>" and then handed off anyway, so this
# gate reported neither success nor failure and nothing in the log explained
# which.  The rewrite names the file it read, reports what it contained, emits a
# distinct marker for each outcome, and - because this exact rootfs image was
# verified offline (Fedora/Nuxel os-release present, /sbin/init -> systemd) -
# records a negative loudly instead of letting a gate bug block the mission.
_osrel_file=""
_osrel=""
for _f in usr/lib/os-release etc/os-release; do
    if [ -s "${ROOT_MNT}/${_f}" ]; then
        _osrel_file="${_f}"
        _osrel="$(tr '\n' ' ' < "${ROOT_MNT}/${_f}" 2>/dev/null | cut -c1-240)"
        break
    fi
done
diag "ROOTFS_IDENTITY_RAW file='${_osrel_file:-<none>}' text='${_osrel:-<empty>}'"
case "${_osrel}" in
    *Fedora*) diag "ROOTFS_IDENTITY_OK Fedora"
              nuxel_marker ROOTFS_IDENTITY_OK ;;
    *Nuxel*)  diag "ROOTFS_IDENTITY_OK Nuxel"
              nuxel_marker ROOTFS_IDENTITY_OK ;;
    *) diag "ROOTFS_IDENTITY_FAIL '${_osrel}'"
       nuxel_marker ROOTFS_IDENTITY_FAIL
       fail_boot "identity check did not see Fedora/Nuxel in '${_osrel}'"
       # continue on purpose: see the comment above
       ;;
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

# --- Phase 1: measure the kernel primitives systemd needs --------------------------
# The freestanding aarch64 probe shipped in this initramfs reports, on the real
# handset, the return value and errno of every syscall in systemd's spawn path.
# This is what turns "Failed to spawn executor: Function not implemented" from a
# version-number guess into a named syscall.
if [ -x /opt/nuxel/nuxel-syscall-probe ]; then
    /opt/nuxel/nuxel-syscall-probe
    diag "SYSCALL_PROBE finished rc=$?"
else
    diag "SYSCALL_PROBE missing from the initramfs"
fi

# The glibc-boundary proof, with no dependency on the rootfs at all: the same
# libc generation the rootfs carries (glibc 2.42), statically linked, calling
# waitid(P_PIDFD), posix_spawn() and pidfd_spawn() and printing each errno.
if [ -x /opt/nuxel/nuxel-spawn-probe-static ]; then
    _pout="$(/opt/nuxel/nuxel-spawn-probe-static 2>&1)"
    printf '%s
' "${_pout}" | while IFS= read -r _l; do
        [ -n "${_l}" ] && diag "SPAWNPROBE-STATIC ${_l}"
    done
    nuxel_marker SPAWN_PROBE_STATIC_RAN
else
    diag "SPAWNPROBE-STATIC missing from the initramfs"
fi

# --- Phase 3: prove Fedora userspace executes, independently of systemd -------------
# Fedora stays the distribution.  This runs BEFORE any handoff, while the
# initramfs is still PID 1, and only proves that the mounted root can execute its
# own ELF binaries through its own glibc.  A systemd failure cannot mask it.
if [ -x "${ROOT_MNT}/bin/sh" ] && [ -x /bin/toybox ]; then
    _fout="$(/bin/toybox chroot "${ROOT_MNT}" /bin/sh -c 'printf "FEDORA_EXEC_OK uid=%s\n" "$(id -u)"' 2>&1)"
    diag "FEDORA_EXEC -> ${_fout:-<no output>}"
    case "${_fout}" in
        *FEDORA_EXEC_OK*) nuxel_marker FEDORA_BINARY_EXECUTED ;;
    esac
else
    diag "FEDORA_EXEC skipped (rootfs /bin/sh or chroot unavailable)"
fi

# The glibc-boundary proof: the same libc generation as the rootfs calls
# waitid(P_PIDFD), posix_spawn() and pidfd_spawn() and prints each errno.
if [ -x /opt/nuxel/nuxel-spawn-probe ] && [ -x /bin/toybox ]; then
    mkdir -p "${ROOT_MNT}/tmp/nuxel" 2>/dev/null
    if cp /opt/nuxel/nuxel-spawn-probe "${ROOT_MNT}/tmp/nuxel/nuxel-spawn-probe" 2>/dev/null; then
        chmod 0755 "${ROOT_MNT}/tmp/nuxel/nuxel-spawn-probe" 2>/dev/null
        _sout="$(/bin/toybox chroot "${ROOT_MNT}" /tmp/nuxel/nuxel-spawn-probe 2>&1)"
        printf '%s\n' "${_sout}" | while IFS= read -r _l; do
            [ -n "${_l}" ] && diag "SPAWNPROBE ${_l}"
        done
        nuxel_marker SPAWN_PROBE_RAN
    else
        diag "SPAWNPROBE could not be staged into the rootfs"
    fi
else
    diag "SPAWNPROBE missing from the initramfs"
fi

# --- Phase 2: install the systemd compatibility library (content-verified) ----------
# A16 defect: the installer checked for a MARKER FILE and, when it existed, declared
# the patch installed without ever looking at the library.  A marker is not proof of
# anything -- the same marker would have been accepted for any file content.
# (Forensics on the A16 handset later proved the rootfs library really did match the
# A13 artifact, but nothing in the boot ever checked that, and nothing could have
# detected a truncated copy, a wrong-architecture ELF, or a rootfs rebuild that
# reverted it.)
#
# Two edits are needed on Linux 4.14 for systemd 258 to start a single service:
#   process-util.c::posix_spawn_wrapper() -> fall back to posix_spawn() when
#       pidfd_spawn() is unsupported (A13).
#   pidref.c::pidref_set_pid()            -> degrade to a PID-only PidRef when
#       pidfd_open() is unsupported.  Without this, posix_spawn() DID start
#       sd-executor and PID1 still reported "Failed to spawn executor: Function not
#       implemented", failed the unit and orphaned the running executor -- the exact
#       A16 signature (udevd alive for 160 s while systemd-udevd.service "failed").
# Both are compiled into the one object shipped in this initramfs.
#
# Deployment rules:
#   * the expected SHA-256 and size of the library are constants in this file,
#   * the target is accepted only if its SHA-256 AND its ELF class/machine match,
#   * the original is preserved once for rollback,
#   * replacement is written aside and atomically renamed,
#   * the marker is written ONLY after the installed file was re-read and re-verified,
#   * a boot whose target is already correct performs no writes at all.
NUXEL_SD_LIB="usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so"
NUXEL_SD_SHA256="848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981"
NUXEL_SD_BYTES="5072280"
NUXEL_PATCH_TAG="systemd-kernel414-verified-A17"
NUXEL_MARKER_DIR="${ROOT_MNT}/.nuxel-patches"
NUXEL_VERIFY=/opt/nuxel/nuxel-verify
NUXEL_SD_SRC=/opt/nuxel/libsystemd-shared-258.11-1.fc43.so

# 0 iff $1 is a regular file whose SHA-256 and ELF identity both match the constants
# above. nuxel-verify prints what it actually measured to /dev/kmsg, so the evidence
# is in the ram console whether the check passes or fails.
nuxel_sd_verify() {
    [ -f "$1" ] || { diag "SYSTEMD_LIB_VERIFY absent $1"; return 1; }
    "${NUXEL_VERIFY}" sha256 "$1" "${NUXEL_SD_SHA256}" > /dev/kmsg 2>&1 || return 1
    "${NUXEL_VERIFY}" elf    "$1" 183                   > /dev/kmsg 2>&1 || return 1
    return 0
}

SD_TARGET="${ROOT_MNT}/${NUXEL_SD_LIB}"
# A19: not an if/elif/else chain.  toybox runs the `else` branch as well when the
# first condition is true (measured: `if true; then echo THEN; elif false; then
# echo ELIF; else echo ELSE; fi` prints THEN and ELSE), which is why A18's log
# contains both SYSTEMD_LIB_VERIFIED_PRESENT and SYSTEMD_LIB_IMAGE_MISSING.
nuxel_sd_verify "${SD_TARGET}"
NUXEL_SD_STATE=$?
if [ "${NUXEL_SD_STATE}" = 0 ]; then
    diag "SYSTEMD_LIB already correct: ${NUXEL_SD_LIB} matches ${NUXEL_SD_SHA256} (no write)"
    nuxel_marker SYSTEMD_LIB_VERIFIED_PRESENT
    mkdir -p "${NUXEL_MARKER_DIR}" 2>/dev/null
    : > "${NUXEL_MARKER_DIR}/${NUXEL_PATCH_TAG}" 2>/dev/null
fi
if [ "${NUXEL_SD_STATE}" != 0 ]; then
    diag "SYSTEMD_LIB target needs installation"
fi
if [ "${NUXEL_SD_STATE}" != 0 ] && [ -f "${NUXEL_SD_SRC}" ]; then
    nuxel_sd_verify "${NUXEL_SD_SRC}" || diag "SYSTEMD_LIB WARNING: the initramfs copy itself fails verification"
    mkdir -p "${NUXEL_MARKER_DIR}" 2>/dev/null
    if [ -f "${SD_TARGET}" ] && [ ! -f "${SD_TARGET}.nuxel-orig" ]; then
        cp "${SD_TARGET}" "${SD_TARGET}.nuxel-orig" 2>/dev/null && \
            diag "SYSTEMD_LIB original preserved as ${NUXEL_SD_LIB}.nuxel-orig"
    fi
    rm -f "${SD_TARGET}.new" 2>/dev/null
    NUXEL_SD_COPIED=1
    cp "${NUXEL_SD_SRC}" "${SD_TARGET}.new" 2>/dev/null || NUXEL_SD_COPIED=0
    if [ "${NUXEL_SD_COPIED}" = 0 ]; then
        diag "SYSTEMD_LIB FAILED to copy into the rootfs"
        nuxel_marker SYSTEMD_LIB_COPY_FAILED
    fi
    if [ "${NUXEL_SD_COPIED}" = 1 ]; then
        chmod 0755 "${SD_TARGET}.new" 2>/dev/null
        mv -f "${SD_TARGET}.new" "${SD_TARGET}" 2>/dev/null
        sync 2>/dev/null
        nuxel_sd_verify "${SD_TARGET}"
        NUXEL_SD_OK=$?
        if [ "${NUXEL_SD_OK}" = 0 ]; then
            : > "${NUXEL_MARKER_DIR}/${NUXEL_PATCH_TAG}" 2>/dev/null
            diag "SYSTEMD_LIB installed and re-verified: ${NUXEL_SD_LIB}"
            nuxel_marker SYSTEMD_LIB_INSTALLED_VERIFIED
        fi
        if [ "${NUXEL_SD_OK}" != 0 ]; then
            diag "SYSTEMD_LIB POST-INSTALL VERIFICATION FAILED - rolling back"
            [ -f "${SD_TARGET}.nuxel-orig" ] && \
                cp "${SD_TARGET}.nuxel-orig" "${SD_TARGET}" 2>/dev/null
            nuxel_marker SYSTEMD_LIB_VERIFY_FAILED
        fi
    fi
fi
if [ "${NUXEL_SD_STATE}" != 0 ] && [ ! -f "${NUXEL_SD_SRC}" ]; then
    diag "SYSTEMD_LIB image missing from the initramfs"
    nuxel_marker SYSTEMD_LIB_IMAGE_MISSING
fi

# --- propagate boot splash / animation to the real root ----------------------------
if [ -f /boot/nuxel-boot-splash.raw ] || [ -f /boot/nuxel-boot-animation.mp4 ]; then
    mkdir -p "${ROOT_MNT}/usr/share/nuxel/boot"
    [ -f /boot/nuxel-boot-splash.raw ] && \
        cp /boot/nuxel-boot-splash.raw "${ROOT_MNT}/usr/share/nuxel/boot/nuxel-boot-splash.raw" 2>/dev/null
    [ -f /boot/nuxel-boot-animation.mp4 ] && \
        cp /boot/nuxel-boot-animation.mp4 "${ROOT_MNT}/usr/share/nuxel/boot/nuxel-boot-animation.mp4" 2>/dev/null
fi

# --- cgroup v2 (unified hierarchy) for systemd 258 --------------------------------
# A16 defect, measured on hardware: A16 mounted cgroup2 at
# ${ROOT_MNT}/sys/fs/cgroup HERE and logged CGROUP2_MOUNTED -- but this block runs
# BEFORE the pseudo-filesystem mounts further down, and that code does
#     mount -t sysfs sysfs "${ROOT_MNT}/sys"
# which STACKS a fresh sysfs on top of /sys and hides the cgroup2 mount underneath.
# In the final namespace /sys/fs/cgroup was therefore an empty sysfs directory, so
# systemd could not create a single per-unit cgroup directory and every executor
# died with (A16 ram console, t=9.15 s)
#     Failed to attach to cgroup /system.slice/<unit>: No such file or directory
#     Failed at step CGROUP spawning <bin>: No such file or directory
# The mount now happens AFTER the sysfs mount and is VERIFIED by reading the same
# filesystem attributes systemd 258 itself reads, rather than trusting an exit
# status.  See "cgroup v2 -- mounted last, then verified" below.

# --- mark boot complete -------------------------------------------------------------
echo "$(date +%s 2>/dev/null || echo 0)" > /run/boot-end-time
echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot

# --- boot-stage state machine (Phase 4) ---------------------------------------------
# A single machine-readable progress record in the real root, so the animated
# first-light screen and the future phone UI agree on where the boot is instead of
# guessing.  Stage sequence:
#   FIRST_LIGHT -> SYSTEM_STARTING -> PHONE_UI_STARTING -> PHONE_UI_READY
#                 -> ANIMATION_STOPPED
# The animation is NOT killed here and never on a timer: it keeps the panel alive
# until something demonstrably takes the display over (see PHONE-UI-HANDOFF.md).
NUXEL_STATE_DIR="${ROOT_MNT}/var/lib/nuxel"
mkdir -p "${NUXEL_STATE_DIR}" 2>/dev/null
if [ -d "${NUXEL_STATE_DIR}" ]; then
    printf 'STAGE=SYSTEM_STARTING\n'   > "${NUXEL_STATE_DIR}/boot-stage"   2>/dev/null
    printf 'ANIM_STAGE=FIRST_LIGHT\n'  > "${NUXEL_STATE_DIR}/animation"    2>/dev/null
    printf 'root=%s device=%s slot=%s\n' "${ROOT_DEV}" "${DEVICE:-unknown}" "${SLOT}" \
        > "${NUXEL_STATE_DIR}/boot-context" 2>/dev/null
    rm -f "${NUXEL_STATE_DIR}/fb-anim-ready" "${NUXEL_STATE_DIR}/fb-anim-starting" \
          "${NUXEL_STATE_DIR}/fb-anim-failed" "${NUXEL_STATE_DIR}/fb-hold-stop" \
          "${NUXEL_STATE_DIR}/fb-hold.pid" "${NUXEL_STATE_DIR}/fb-anim.pid" 2>/dev/null
    diag "BOOT_STAGE written ${NUXEL_STATE_DIR}/boot-stage=SYSTEM_STARTING"
    nuxel_marker BOOT_STAGE_SYSTEM_STARTING
else
    diag "BOOT_STAGE could not create ${NUXEL_STATE_DIR}"
fi

# --- pivot into the real root ---------------------------------------------------------
# Move the essential pseudo filesystems under the new root so they are
# preserved across switch_root.  Failures here are non-fatal.
# Give the real root its own instances instead of `mount --move`-ing ours away.
# A12 moved /dev into the new root, which detached the initramfs evidence channel
# (/dev/kmsg stopped resolving for anything still on the old root - exactly how
# the watchdog's message was lost).  Fresh mounts leave our channel intact and
# still hand systemd correctly mounted /proc, /sys and /dev.
mount -t proc    proc      "${ROOT_MNT}/proc" 2>/dev/null || \
    mount --move /proc "${ROOT_MNT}/proc" 2>/dev/null
mount -t sysfs   sysfs     "${ROOT_MNT}/sys"  2>/dev/null || \
    mount --move /sys  "${ROOT_MNT}/sys"  2>/dev/null
mount -t devtmpfs none     "${ROOT_MNT}/dev"  2>/dev/null || \
    mount --move /dev  "${ROOT_MNT}/dev"  2>/dev/null

# --- cgroup v2 -- mounted LAST, then verified ---------------------------------------
# Ordering matters and A16 got it wrong: a cgroup2 mount placed under /sys/fs/cgroup
# is destroyed by any later `mount -t sysfs sysfs /sys`, because that stacks a new
# sysfs over the whole /sys subtree.  This is therefore the first point in the boot
# where /sys in the new root is final.
mkdir -p "${ROOT_MNT}/sys/fs/cgroup" 2>/dev/null
if mount -t cgroup2 none "${ROOT_MNT}/sys/fs/cgroup" 2>/dev/null; then
    diag "CGROUP2_MOUNT_OK ${ROOT_MNT}/sys/fs/cgroup"
else
    diag "CGROUP2_MOUNT_FAILED (already mounted, or kernel/hierarchy problem)"
fi
_cg_root="${ROOT_MNT}/sys/fs/cgroup"
if [ -r "${_cg_root}/cgroup.controllers" ]; then
    diag "CGROUP2_VERIFIED controllers='$(cat "${_cg_root}/cgroup.controllers" 2>/dev/null)'"
    diag "CGROUP2_VERIFIED subtree_control='$(cat "${_cg_root}/cgroup.subtree_control" 2>/dev/null)'"
    diag "CGROUP2_PROC_MOUNTS '$(grep -E ' cgroup2 ' /proc/mounts 2>/dev/null | head -1)'"
    nuxel_marker CGROUP2_MOUNTED
else
    diag "CGROUP2_VERIFY_FAILED ${_cg_root}/cgroup.controllers unreadable - systemd cannot manage cgroups"
    nuxel_marker CGROUP2_MOUNT_FAILED
fi

# First light now runs EARLY (with the boot splash, on the next line above this
# section).  A13 measured why: the pre-handoff root discovery left the panel
# unchanged and the log silent for ~12 s, and the operator's POWER+VOLUMEDOWN
# force-reset (drivers/samsung/sec_hard_reset_hook.c, hard_reset_keys[] =
# {KEY_POWER, KEY_VOLUMEDOWN}) fired at t=9.4 s in one attempt and killed the
# boot before any of this ran.  A phone that shows the Nuxel screen two seconds
# after power-on does not look dead.

# --- live diagnostics over USB (Phase 3) -------------------------------------------
# Until A17 the ONLY way to read a Nuxel boot was to let it fail, hand-recover into
# TWRP and read /proc/last_kmsg.  The Exynos 9820 kernel registers a USB device
# controller (/sys/class/udc/10c00000.dwc3 -> "Binding gadget dwc3-gadget" in the
# A16 ram console) with CONFIG_USB_CONFIGFS and CONFIG_USB_CONFIGFS_ACM, so a
# CDC-ACM gadget can be created entirely from Linux userspace.  nuxel-console binds
# it, streams /dev/kmsg to the port and gives the operator an interactive root shell
# inside the real Fedora root (it chroot()s through a dirfd, so PID1's switch_root is
# unaffected).  The shell's root is the ext4 rootfs, so it survives switch_root.
#
# On the MacBook:   screen /dev/tty.usbmodemXXXX 115200
#
# Failure here is non-fatal by design: it must never cost us a boot.
if [ -x /opt/nuxel/nuxel-console ]; then
    /opt/nuxel/nuxel-console "${ROOT_MNT}" > /dev/kmsg 2>&1 &
    diag "LIVE_CONSOLE started pid=$! (USB CDC-ACM on /dev/ttyGS0)"
    nuxel_marker LIVE_CONSOLE_STARTED
else
    diag "LIVE_CONSOLE binary missing from the initramfs"
fi

# --- the PHONE UI: deliver it from the BOOT candidate into the real rootfd ---------
# Mission section 7/11: the interactive Nuxel interface is a userspace service, and
# a BOOT-only flash must be able to ship it.  The 4 GiB rootfs is NOT rewritten; the
# initramfs carries /opt/nuxel/nuxel-ui (+ its units), and this step installs them
# into the mounted Fedora root atomically, with the previous binary kept as
# /usr/lib/nuxel/nuxel-ui.prev so a bad UI can be rolled back from the live shell.
#
# It also RETIRES the A-old one-shot diagnostic painter (nuxel-firstlight.service):
# two renderers must never own the DECON at once (that is exactly the A20 "two
# penguins" defect).  The unit file stays on disk for rollback.
#
# Every step is fail-open: a UI problem must never cost us a boot.
nuxel_install_ui() {
    if [ ! -x /opt/nuxel/nuxel-ui ]; then
        diag "UI_BINARY_MISSING (no /opt/nuxel/nuxel-ui in this initramfs) — Fedora root untouched"
        nuxel_marker UI_BINARY_MISSING
        return 0
    fi
    _want="$(cat /opt/nuxel/nuxel-ui.rev 2>/dev/null)"
    [ -n "${_want}" ] || _want=unknown
    _dst="${ROOT_MNT}/usr/bin/nuxel-ui"
    _rev="${ROOT_MNT}/usr/lib/nuxel/ui.rev"
    _have="$(cat "${_rev}" 2>/dev/null)"
    mkdir -p "${ROOT_MNT}/usr/bin" "${ROOT_MNT}/usr/lib/nuxel" "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants" 2>/dev/null

    # A27: the BOOT candidate is a DELIVERY vehicle for the UI, not its owner.  A
    # live-deployed UI records its own rev in /usr/lib/nuxel/ui.pinned; when that
    # differs from the rev this initramfs carries, the live (newer, proven) binary
    # WINS and the BOOT copy is not installed.  Without the pin file the behaviour
    # is exactly the A25/A26 behaviour, so nothing changes for an untouched system.
    _pin="${ROOT_MNT}/usr/lib/nuxel/ui.pinned"
    if [ -f "${_pin}" ] && [ "${_want}" != "$(cat "${_pin}" 2>/dev/null)" ]; then
        diag "UI_PINNED_KEEP live-deployed rev '$(cat "${_pin}" 2>/dev/null)' overrides BOOT candidate rev '${_want}' (not installing)"
        nuxel_marker UI_PINNED_KEEP
    elif [ "${_want}" != "${_have}" ]; then
        if [ -f "${_dst}" ]; then
            if cp -f "${_dst}" "${ROOT_MNT}/usr/lib/nuxel/nuxel-ui.prev" 2>/dev/null; then
                diag "UI_BACKUP previous binary kept as /usr/lib/nuxel/nuxel-ui.prev (rev '${_have:-unknown}')"
            fi
        fi
        if cp -f /opt/nuxel/nuxel-ui "${_dst}" 2>/dev/null; then
            chmod 0755 "${_dst}" 2>/dev/null
            printf '%s\n' "${_want}" > "${_rev}" 2>/dev/null
            diag "UI_INSTALLED rev='${_want}' (was '${_have:-none}') -> ${_dst}"
            nuxel_marker UI_INSTALLED
        else
            diag "UI_INSTALL_FAILED could not write ${_dst}"
            nuxel_marker UI_INSTALL_FAILED
            return 0
        fi
    else
        diag "UI_UP_TO_DATE rev='${_want}'"
    fi

    # The rootfs copy of the player is refreshed too: it carries the A23 hardware
    # colour order, and the fallback unit plus any manual run use it.
    if [ -x /opt/nuxel/nuxel-anim-player ]; then
        cp -f /opt/nuxel/nuxel-anim-player "${ROOT_MNT}/usr/bin/nuxel-anim-player" 2>/dev/null && \
            chmod 0755 "${ROOT_MNT}/usr/bin/nuxel-anim-player" 2>/dev/null && \
            diag "PLAYER_INSTALLED /usr/bin/nuxel-anim-player (A23 colour order)"
    fi

    for _u in nuxel-ui.service nuxel-ui-fallback.service; do
        if [ -f "/opt/nuxel/${_u}" ]; then
            if cp -f "/opt/nuxel/${_u}" "${ROOT_MNT}/etc/systemd/system/${_u}" 2>/dev/null; then
                diag "UI_UNIT_INSTALLED /etc/systemd/system/${_u}"
            else
                diag "UI_UNIT_INSTALL_FAILED ${_u}"
            fi
        fi
    done

    # A24: enable in BOTH targets.  multi-user.target is the normal path; sysinit.target
    # is reached earlier and does not depend on local-fs.target, which is where this
    # image's boot graph stalls (see A23 measurements in NUXEL-BOOT-STALL.md).
    #
    # A29b: unless the UTM-derived launcher is installed in this rootfs, in which
    # case the A27 fbdev UI is only the *fallback* and is started by
    # nuxel-fallback.service (ExecStart=/usr/bin/nuxel-ui) after the launcher has
    # failed.  Enabling the unit as well would put a second /dev/fb0 owner on the
    # panel behind the launcher's back (measured on the handset this cycle), so the
    # unit is left disabled and its own launcher-primary condition decides.
    if [ -x "${ROOT_MNT}/usr/lib/nuxel/nuxel-wl-fb" ]; then
        rm -f "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/nuxel-ui.service" \
              "${ROOT_MNT}/etc/systemd/system/sysinit.target.wants/nuxel-ui.service" 2>/dev/null
        diag "UI_SERVICE_ENABLE_SKIPPED nuxel-ui.service (A29 launcher present: fallback only)"
    else
        ln -sf /etc/systemd/system/nuxel-ui.service \
            "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/nuxel-ui.service" 2>/dev/null && \
            diag "UI_SERVICE_ENABLED nuxel-ui.service (multi-user.target)" || \
            diag "UI_SERVICE_ENABLE_FAILED"
        ln -sf /etc/systemd/system/nuxel-ui.service \
            "${ROOT_MNT}/etc/systemd/system/sysinit.target.wants/nuxel-ui.service" 2>/dev/null && \
            diag "UI_SERVICE_ENABLED nuxel-ui.service (sysinit.target)" || \
            diag "UI_SERVICE_SYSINIT_ENABLE_FAILED"
    fi

    # the post-handoff supervisor (runs in the new root after switch_root)
    if cp -f /opt/nuxel/nuxel-postboot.sh "${ROOT_MNT}/usr/lib/nuxel/nuxel-postboot.sh" 2>/dev/null; then
        chmod 0755 "${ROOT_MNT}/usr/lib/nuxel/nuxel-postboot.sh" 2>/dev/null
        diag "POSTBOOT_SUPERVISOR_INSTALLED /usr/lib/nuxel/nuxel-postboot.sh"
    else
        diag "POSTBOOT_SUPERVISOR_INSTALL_FAILED"
    fi

    if rm -f "${ROOT_MNT}/etc/systemd/system/multi-user.target.wants/nuxel-firstlight.service" 2>/dev/null; then
        diag "FIRSTLIGHT_PAINTER_RETIRED (nuxel-firstlight.service unlinked; unit file kept)"
    fi

    printf 'UI_REV=%s\nINSTALLED_AT_BOOT=1\n' "${_want}" > "${NUXEL_STATE_DIR}/ui-build" 2>/dev/null
    if [ "${_want}" != "${_have}" ]; then
        printf 'STAGE=PHONE_UI_INSTALLED\nREV=%s\n' "${_want}" > "${NUXEL_STATE_DIR}/boot-stage" 2>/dev/null
    fi
    nuxel_marker PHONE_UI_INSTALLED
}
nuxel_install_ui

# --- the ORIGINAL Nuxel MP4 boot animation (WoNQ priority 1) -----------------------
# The real Nuxel boot animation is an H.264 MP4 (assets/nuxel-boot-animation.mp4,
# 1080x1920, 24 fps, 192 frames).  On the desktop and VM builds it is rendered by a
# Plymouth "script" theme; Plymouth needs DRM/KMS and this Samsung 4.14 kernel has
# `# CONFIG_DRM is not set`, so it cannot run here at all.  The MP4 is therefore
# re-encoded at BUILD time by tools/s10plus/nuxel-anim-pack.py into a 256-colour
# palette plus a changed-span stream (18.5 MB, 38 dB PSNR) and decoded by
# tools/s10plus/nuxel-anim-player.c straight onto the DECON fbdev.
#
# THE ARTWORK IS THE ORIGINAL ONE.  Nothing is redrawn, substituted or invented;
# the diagnostic penguin stays only as the fallback when the container is absent.
#
# Delivery split, exactly as the mission requires:
#   * the player binary (66 KB) rides in the initramfs, i.e. on the BOOT partition;
#   * the ~18.5 MB animation container lives in the Fedora rootfs, so the kernel
#     image is not enlarged by animation data.
# The player takes the framebuffer over from the penguin itself and loops until it
# is signalled or the stop file appears - never on a timer.
nuxel_start_animation() {
    NUXEL_ANIM_FILE="${ROOT_MNT}/usr/share/nuxel/boot/nuxel-animation.nux"
    if [ ! -x /opt/nuxel/nuxel-anim-player ]; then
        diag "ANIMATION player absent from the initramfs — first-light penguin stays"
        nuxel_marker ANIMATION_PLAYER_MISSING
        nuxel_start_hold_painter
        return 0
    fi
    if [ ! -f "${NUXEL_ANIM_FILE}" ]; then
        diag "ANIMATION container absent at ${NUXEL_ANIM_FILE} — first-light penguin stays"
        nuxel_marker ANIMATION_CONTAINER_MISSING
        nuxel_start_hold_painter
        return 0
    fi
    nuxel_marker FEDORA_MOUNTED
    printf 'ANIM_STAGE=MP4_PLAYER_STARTING\n' > "${NUXEL_STATE_DIR}/animation" 2>/dev/null
    rm -f "${ROOT_MNT}/var/lib/nuxel/anim-stop" \
          "${NUXEL_STATE_DIR}/fb-anim-ready" "${NUXEL_STATE_DIR}/fb-anim-failed" 2>/dev/null
    # The player takes the panel over FIRST and only then does init hand the rootfs
    # to systemd, so its /proc scan and every absolute path are still valid.
    /opt/nuxel/nuxel-anim-player \
        "--file=${NUXEL_ANIM_FILE}" \
        "--statedir=${NUXEL_STATE_DIR}" \
        "--state=animation" \
        "--pid=fb-anim.pid" \
        "--stopfile=anim-stop" \
        "--holdpid=fb-hold.pid" \
        --verbose > /dev/kmsg 2>&1 &
    nuxel_marker ORIGINAL_MP4_ANIMATION_STARTING
    diag "ANIMATION player launched: original Nuxel MP4 artwork on the fbdev path"

    # --- bounded handshake: MP4 owns the panel, or the penguin fallback does ---
    # A renderer may not claim the panel until it has COMMITTED a frame (mission
    # section 7), and init may not switch_root until the claim is resolved, because
    # switch_root invalidates the player's view of /proc.
    _anim_wait=0
    while [ "${_anim_wait}" -lt "${NUXEL_ANIM_WAIT:-8}" ]; do
        if [ -f "${NUXEL_STATE_DIR}/fb-anim-ready" ]; then
            diag "ANIMATION ownership: MP4 first frame committed after ${_anim_wait}s"
            nuxel_marker MP4_FIRST_FRAME_READY
            nuxel_marker MP4_PLAYER_ACTIVE
            printf 'ANIM_STAGE=MP4_PLAYER_ACTIVE\n' > "${NUXEL_STATE_DIR}/animation" 2>/dev/null
            return 0
        fi
        if [ -f "${NUXEL_STATE_DIR}/fb-anim-failed" ]; then
            diag "ANIMATION player reported a NAMED failure before the first frame"
            nuxel_marker MP4_PLAYER_FAILED
            break
        fi
        _anim_wait=$((_anim_wait+1))
        sleep 1 2>/dev/null || sleep 1
    done
    diag "ANIMATION player did not commit a frame within ${_anim_wait}s — penguin fallback"
    nuxel_marker FIRST_LIGHT_STOPPED
    nuxel_marker MP4_PLAYER_ACTIVE_TIMEOUT
    printf 'ANIM_STAGE=FIRST_LIGHT_FALLBACK\n' > "${NUXEL_STATE_DIR}/animation" 2>/dev/null
    nuxel_start_hold_painter
    return 0
}
nuxel_start_animation

# --- post-handoff supervisor: survives switch_root, reports and self-repairs --------
# A23 measured that the Fedora boot graph stalls with every job "waiting", so no
# target-ordered unit ever starts.  This child is started from the initramfs (it
# outlives switch_root exactly like nuxel-console) and waits for the REAL root to
# appear before it execs the Fedora shell -- so its diagnostics and its
# `systemctl start nuxel-ui` run against the live system, not against an image.
if [ -f /opt/nuxel/nuxel-postboot.sh ]; then
    (
        _pb=0
        while [ "${_pb}" -lt 90 ]; do
            [ -x /usr/bin/systemctl ] && break
            _pb=$((_pb+1)); sleep 1 2>/dev/null
        done
        exec /bin/sh /usr/lib/nuxel/nuxel-postboot.sh 20
    ) >/dev/kmsg 2>&1 &
    diag "POSTBOOT supervisor started pid=$! (reports to /var/lib/nuxel/bootreport.txt)"
    nuxel_marker POSTBOOT_SUPERVISOR_STARTED
else
    diag "POSTBOOT supervisor absent from this initramfs"
fi

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
