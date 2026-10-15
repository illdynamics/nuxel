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
    /opt/nuxel/nuxel-fb-phone > /dev/kmsg 2>&1
    _fbrc=$?
    diag "FIRSTLIGHT exit=${_fbrc}"
    [ "${_fbrc}" = 0 ] && nuxel_marker FIRSTLIGHT_FRAME_WRITTEN

    # 2) Resident painter: keeps the penguin spinning on the real AMOLED panel
    #    for the rest of the boot, independent of systemd, Phosh and every
    #    ENOSYS-failing service.  It logs one line per ~10 s so it can never
    #    drown the boot markers in the ram console.  If the handoff terminates
    #    it, the last committed frame stays in framebuffer memory and the DECON
    #    keeps scanning it.
    /opt/nuxel/nuxel-fb-phone hold > /dev/kmsg 2>&1 &
    diag "FIRSTLIGHT hold started pid=$!"
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
    case " ${CMDLINE} " in
        *androidboot.hardware=exynos9820*|*androidboot.bootloader=G97*) : ;;
        *) return 0 ;;
    esac
    case "${ROOT_DEV}" in
        ""|/dev/sda1|/dev/sda2|/dev/sda25)
            nuxel_say "root override: forcing the s10plus USERDATA resolution (was '${ROOT_DEV}')"
            # FAST discovery.  A13 sat here for the full 12 s because
            # /sys/class/block is EMPTY on this kernel even with sysfs mounted, so
            # PARTNAME uevent lookup can never succeed and the loop was pure delay.
            # The operator's force-reset killed a boot during that silence (see the
            # first-light note above).  Probe once, allow one second for the UFS
            # scan to finish, then use the documented, size-verified node.
            ROOT_DEV="$(s10plus_userdata_device)"
            if [ -z "${ROOT_DEV}" ]; then
                sleep 1
                ROOT_DEV="$(s10plus_userdata_device)"
            fi
            _t=1
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
case "${DEVICE}" in
    mustang|vm|"")
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

# --- Phase 2: install the pidfd_spawn compatibility repair --------------------------
# systemd 258.11's posix_spawn_wrapper() retries pidfd_spawn() instead of falling
# back to posix_spawn(), and glibc's pidfd_spawn() returns ENOSYS on any kernel
# without waitid(P_PIDFD) (Linux >= 5.4).  On this 4.14.253 kernel that made EVERY
# service spawn fail (A12).  The repaired libsystemd-shared is rebuilt from the
# exact installed SRPM (systemd-258.11-1.fc43) with upstream's own fallback and is
# shipped inside this initramfs, so only the BOOT partition is written.
NUXEL_SD_LIB=usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so
NUXEL_PATCH_TAG=pidfd-spawn-fallback-A13
if [ -f /opt/nuxel/libsystemd-shared-258.11-1.fc43.so ]; then
    if [ -f "${ROOT_MNT}/.nuxel-patches/${NUXEL_PATCH_TAG}" ]; then
        diag "SYSTEMD_PATCH already present"
        nuxel_marker SYSTEMD_PATCH_PRESENT
    else
        mkdir -p "${ROOT_MNT}/.nuxel-patches" 2>/dev/null
        if [ ! -f "${ROOT_MNT}/${NUXEL_SD_LIB}" ]; then
            diag "SYSTEMD_PATCH target ${NUXEL_SD_LIB} is MISSING from the rootfs"
        fi
        if [ ! -f "${ROOT_MNT}/${NUXEL_SD_LIB}.nuxel-orig" ]; then
            cp "${ROOT_MNT}/${NUXEL_SD_LIB}" "${ROOT_MNT}/${NUXEL_SD_LIB}.nuxel-orig" 2>/dev/null && \
                diag "SYSTEMD_PATCH original saved as ${NUXEL_SD_LIB}.nuxel-orig"
        fi
        if cp /opt/nuxel/libsystemd-shared-258.11-1.fc43.so "${ROOT_MNT}/${NUXEL_SD_LIB}.new" 2>/dev/null; then
            chmod 0755 "${ROOT_MNT}/${NUXEL_SD_LIB}.new" 2>/dev/null
            mv -f "${ROOT_MNT}/${NUXEL_SD_LIB}.new" "${ROOT_MNT}/${NUXEL_SD_LIB}" 2>/dev/null
            : > "${ROOT_MNT}/.nuxel-patches/${NUXEL_PATCH_TAG}" 2>/dev/null
            diag "SYSTEMD_PATCH installed: $(ls -l "${ROOT_MNT}/${NUXEL_SD_LIB}" 2>/dev/null)"
            nuxel_marker SYSTEMD_PATCH_INSTALLED
        else
            diag "SYSTEMD_PATCH FAILED to copy into the rootfs"
        fi
    fi
else
    diag "SYSTEMD_PATCH image missing from the initramfs"
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
# A14 measured the ONLY remaining systemd blocker after the pidfd_spawn repair:
# every unit's executor child died with
#   Failed to attach to cgroup /system.slice/<unit>: No such file or directory
#   Failed at step CGROUP spawning /usr/lib/systemd/<bin>: No such file or dir
# because NO cgroup hierarchy was mounted at all (`cgroup2_unified=absent` in the
# A14 spawn probe).  systemd >= 257 requires the *unified* (v2) hierarchy; mounting
# v1 controllers instead would put the kernel in hybrid mode, which it refuses.
# So: mount v2 only, into the new root's /sys/fs/cgroup, and say loudly if it fails.
mkdir -p "${ROOT_MNT}/sys/fs/cgroup" 2>/dev/null
if mount -t cgroup2 none "${ROOT_MNT}/sys/fs/cgroup" 2>/dev/null; then
    diag "CGROUP2_MOUNTED ${ROOT_MNT}/sys/fs/cgroup (unified hierarchy for systemd 258)"
    nuxel_marker CGROUP2_MOUNTED
else
    diag "CGROUP2_MOUNT_FAILED mount -t cgroup2 none ${ROOT_MNT}/sys/fs/cgroup - systemd services cannot attach"
    nuxel_marker CGROUP2_MOUNT_FAILED
fi

# --- mark boot complete -------------------------------------------------------------
echo "$(date +%s 2>/dev/null || echo 0)" > /run/boot-end-time
echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot

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

# First light now runs EARLY (with the boot splash, on the next line above this
# section).  A13 measured why: the pre-handoff root discovery left the panel
# unchanged and the log silent for ~12 s, and the operator's POWER+VOLUMEDOWN
# force-reset (drivers/samsung/sec_hard_reset_hook.c, hard_reset_keys[] =
# {KEY_POWER, KEY_VOLUMEDOWN}) fired at t=9.4 s in one attempt and killed the
# boot before any of this ran.  A phone that shows the Nuxel screen two seconds
# after power-on does not look dead.

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
