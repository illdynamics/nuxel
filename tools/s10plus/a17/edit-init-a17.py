#!/usr/bin/env python3
"""Nuxel A17 initramfs /init edits (boot/initramfs/init.sh).

Every edit is anchored on unique existing text and FAILS LOUDLY if the anchor is
missing, so a silently-unapplied edit is impossible.

A17-INIT-1  cgroup2 mount moved AFTER the sysfs mount, then VERIFIED
A17-INIT-2  systemd library deployment is hash+ELF verified, atomic and marked
            only after post-install re-verification
A17-INIT-3  boot-stage progress record written into the real root
A17-INIT-4  animation hold PID captured + published, so a UI can stop it
A17-INIT-5  live USB (CDC-ACM) diagnostic console + kernel-log stream started
"""
import os
import sys

PATH = os.environ.get("INIT_SH", "boot/initramfs/init.sh")
SHA = os.environ.get("NUXEL_SD_SHA256", "__NUXEL_SD_SHA256__")
BYTES = os.environ.get("NUXEL_SD_BYTES", "__NUXEL_SD_BYTES__")

lines = open(PATH).read().split("\n")
errors = []


def find(pred, start=0, what=""):
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    errors.append("anchor not found: %s" % what)
    return -1


def replace_block(start_pred, end_pred, new_text, what):
    """Replace [first line matching start_pred .. first following line matching
    end_pred] inclusive."""
    s = find(start_pred, 0, what + " (start)")
    if s < 0:
        return
    e = find(end_pred, s, what + " (end)")
    if e < 0:
        return
    new_text = new_text.replace("@@SHA@@", SHA).replace("@@BYTES@@", BYTES)
    lines[s:e + 1] = new_text.split("\n")
    print("OK  %s (lines %d..%d replaced)" % (what, s + 1, e + 1))


# --------------------------------------------------------------- (1) cgroup2 ---
replace_block(
    lambda l: l.startswith("# --- cgroup v2 (unified hierarchy) for systemd 258"),
    lambda l: l == "fi",
    """# --- cgroup v2 (unified hierarchy) for systemd 258 --------------------------------
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
# status.  See "cgroup v2 -- mounted last, then verified" below.""",
    "A17-INIT-1 cgroup2 block deferred",
)

# ------------------------------------------------------- (2) systemd library ---
replace_block(
    lambda l: l.startswith("# --- Phase 2: install the pidfd_spawn compatibility repair"),
    lambda l: l == "fi",
    """# --- Phase 2: install the systemd compatibility library (content-verified) ----------
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
NUXEL_SD_SHA256="@@SHA@@"
NUXEL_SD_BYTES="@@BYTES@@"
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
if nuxel_sd_verify "${SD_TARGET}"; then
    diag "SYSTEMD_LIB already correct: ${NUXEL_SD_LIB} matches ${NUXEL_SD_SHA256} (no write)"
    nuxel_marker SYSTEMD_LIB_VERIFIED_PRESENT
    mkdir -p "${NUXEL_MARKER_DIR}" 2>/dev/null
    : > "${NUXEL_MARKER_DIR}/${NUXEL_PATCH_TAG}" 2>/dev/null
elif [ -f "${NUXEL_SD_SRC}" ]; then
    diag "SYSTEMD_LIB target needs installation"
    nuxel_sd_verify "${NUXEL_SD_SRC}" || diag "SYSTEMD_LIB WARNING: the initramfs copy itself fails verification"
    mkdir -p "${NUXEL_MARKER_DIR}" 2>/dev/null
    if [ -f "${SD_TARGET}" ] && [ ! -f "${SD_TARGET}.nuxel-orig" ]; then
        cp "${SD_TARGET}" "${SD_TARGET}.nuxel-orig" 2>/dev/null && \\
            diag "SYSTEMD_LIB original preserved as ${NUXEL_SD_LIB}.nuxel-orig"
    fi
    rm -f "${SD_TARGET}.new" 2>/dev/null
    if ! cp "${NUXEL_SD_SRC}" "${SD_TARGET}.new" 2>/dev/null; then
        diag "SYSTEMD_LIB FAILED to copy into the rootfs"
        nuxel_marker SYSTEMD_LIB_COPY_FAILED
    else
        chmod 0755 "${SD_TARGET}.new" 2>/dev/null
        mv -f "${SD_TARGET}.new" "${SD_TARGET}" 2>/dev/null
        sync 2>/dev/null
        if nuxel_sd_verify "${SD_TARGET}"; then
            : > "${NUXEL_MARKER_DIR}/${NUXEL_PATCH_TAG}" 2>/dev/null
            diag "SYSTEMD_LIB installed and re-verified: ${NUXEL_SD_LIB}"
            nuxel_marker SYSTEMD_LIB_INSTALLED_VERIFIED
        else
            diag "SYSTEMD_LIB POST-INSTALL VERIFICATION FAILED - rolling back"
            [ -f "${SD_TARGET}.nuxel-orig" ] && \\
                cp "${SD_TARGET}.nuxel-orig" "${SD_TARGET}" 2>/dev/null
            nuxel_marker SYSTEMD_LIB_VERIFY_FAILED
        fi
    fi
else
    diag "SYSTEMD_LIB image missing from the initramfs"
    nuxel_marker SYSTEMD_LIB_IMAGE_MISSING
fi""",
    "A17-INIT-2 verified systemd library deployment",
)

# ------------------------------------------- (3) cgroup2 mount + verification ---
replace_block(
    lambda l: l.startswith("mount -t devtmpfs none     \"${ROOT_MNT}/dev\""),
    lambda l: l.startswith("    mount --move /dev  \"${ROOT_MNT}/dev\""),
    """mount -t devtmpfs none     "${ROOT_MNT}/dev"  2>/dev/null || \\
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
fi""",
    "A17-INIT-1b cgroup2 mounted after sysfs and verified",
)

# --------------------------------------------------- (4) live USB console ------
replace_block(
    lambda l: l == 'diag "ROOTFS_HANDOFF_STARTED -> ${ROOT_MNT}"',
    lambda l: l == 'diag "ROOTFS_HANDOFF_STARTED -> ${ROOT_MNT}"',
    """# --- live diagnostics over USB (Phase 3) -------------------------------------------
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

diag "ROOTFS_HANDOFF_STARTED -> ${ROOT_MNT}\"""",
    "A17-INIT-5 live USB console",
)

# --------------------------------------------- (5) boot stage / progress file ---
replace_block(
    lambda l: l == 'echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot',
    lambda l: l == 'echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot',
    """echo "nuxel booted slot=${SLOT} device=${DEVICE:-unknown} console=${CONSOLE:-default} root=${ROOT_DEV}" > /run/nuxel-boot

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
    printf 'STAGE=SYSTEM_STARTING\\n'   > "${NUXEL_STATE_DIR}/boot-stage"   2>/dev/null
    printf 'ANIM_STAGE=FIRST_LIGHT\\n'  > "${NUXEL_STATE_DIR}/animation"    2>/dev/null
    printf '%s\\n' "${NUXEL_HOLD_PID:-}"  > "${NUXEL_STATE_DIR}/fb-hold.pid" 2>/dev/null
    printf 'root=%s device=%s slot=%s\\n' "${ROOT_DEV}" "${DEVICE:-unknown}" "${SLOT}" \\
        > "${NUXEL_STATE_DIR}/boot-context" 2>/dev/null
    diag "BOOT_STAGE written ${NUXEL_STATE_DIR}/boot-stage=SYSTEM_STARTING hold_pid=${NUXEL_HOLD_PID:-none}"
    nuxel_marker BOOT_STAGE_SYSTEM_STARTING
else
    diag "BOOT_STAGE could not create ${NUXEL_STATE_DIR}"
fi""",
    "A17-INIT-3 boot stage record",
)

# ------------------------------------------------ (6) publish the hold pid -------
replace_block(
    lambda l: l.startswith("    /opt/nuxel/nuxel-fb-phone hold > /dev/kmsg 2>&1 &"),
    lambda l: l.startswith('    diag "FIRSTLIGHT hold started pid=$!"'),
    """    /opt/nuxel/nuxel-fb-phone hold > /dev/kmsg 2>&1 &
    NUXEL_HOLD_PID=$!
    diag "FIRSTLIGHT hold started pid=${NUXEL_HOLD_PID}"
    nuxel_marker "ANIMATION_HOLD_PID=${NUXEL_HOLD_PID}"
""",
    "A17-INIT-4 animation hold pid",
)

if errors:
    print("FATAL:")
    for e in errors:
        print("   " + e)
    sys.exit(1)

open(PATH, "w").write("\n".join(lines))
print("init.sh written (%d lines)" % len(lines))
