#!/usr/bin/env python3
"""Nuxel A18 initramfs /init edits.

WHY (measured on the handset, 2026-10-15, candidate A17):

toybox 0.8.14 treats an EMPTY pattern alternative in a `case` list as a WILDCARD.
The dispatch was written as

    case "${DEVICE}" in
        mustang|vm|"")   ...generic...
        s10plus)         ...s10plus...
        g7power)         ...g7power...

so a device value of exactly `s10plus` matched the FIRST branch.  The s10plus and
g7power branches were unreachable dead code and every boot went through the
generic probe.  Reproduced in podman with the initramfs's own /bin/toybox:

    $ toybox sh -c 'D=s10plus; case "$D" in mustang|vm|"") echo G ;; s10plus) echo S ;; esac'
    G

A16 survived that only because the generic branch rewrites DEVICE=s10plus and the
separate force_s10plus_root() rescue then found /dev/sda31 one second later.
A17 lost the rescue (its own gate also depended on case patterns) and died with
    nuxel-init: [FATAL] no root block device found (slot=a)
t = 7.27 s, before switch_root, before systemd ever started -- while its A17
kernel and initramfs WERE correct (the new ANIMATION_HOLD_PID marker and the
A17 kernel banner are both in that record).

A18 replaces every load-bearing `case` pattern test in the root-resolution path
with explicit `[ ... ]` tests and `grep -q`, makes the USERDATA wait heartbeat so
the operator never sees silence, and emits the (long, otherwise truncated) kernel
cmdline in 200-byte chunks so the ram console can never hide it again.
"""
import os
import sys

PATH = os.environ.get("INIT_SH", "boot/initramfs/init.sh")
text = open(PATH).read()

errors = []


def sub(old, new, label, count=1):
    global text
    n = text.count(old)
    if n != count:
        errors.append("%s: expected %d occurrence(s), found %d" % (label, count, n))
        return
    text = text.replace(old, new, count)
    print("OK  %s" % label)


# ---------------------------------------------------------------- helper -------
# The helper must exist BEFORE its first caller (POSIX sh resolves functions at
# run time, in order), so it is defined here, immediately after the cmdline parse.
sub(
    """# HARD IDENTITY PIN.""",
    """# A18: no load-bearing `case` PATTERN test survives in the root-resolution path.
# toybox 0.8.14 treats an empty alternative as a wildcard (see the dispatch note
# further down), so the only primitives used here are `[ ... ]` tests and `grep -q`.
cmdline_matches_samsung() {
    printf '%s' "${CMDLINE}" | grep -q 'androidboot.hardware=exynos9820' && return 0
    printf '%s' "${CMDLINE}" | grep -q 'androidboot.bootloader=G97'        && return 0
    return 1
}

# HARD IDENTITY PIN.""",
    "A18-inline-1 cmdline_matches_samsung() helper (defined before first use)",
)

# ------------------------------------------- chunked, untruncatable cmdline ----
sub(
    """log "slot=${SLOT} device=${DEVICE:-unknown} quiet=${QUIET:-0} verity=$([ -n "${VERITY_HASH}" ] && echo on || echo off)\"""",
    """log "slot=${SLOT} device=${DEVICE:-unknown} quiet=${QUIET:-0} verity=$([ -n "${VERITY_HASH}" ] && echo on || echo off)"

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
fi""",
    "A18-inline-2 chunked cmdline logging",
)

# ------------------------------------------------- force_s10plus_root rewrite -
old_force = """force_s10plus_root() {
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
}"""

new_force = """force_s10plus_root() {
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
        nuxel_say "USERDATA waiting t=${_t}s blockdevs='$(ls /dev/sd* 2>/dev/null | tr '\\n' ' ')'"
        sleep 1
    done
    if [ -z "${ROOT_DEV}" ]; then
        nuxel_say "USERDATA could not be located in 20s (no PARTNAME, no /dev/sda31)"
    fi
}"""
sub(old_force, new_force, "A18-core-1 force_s10plus_root rewritten (no case patterns, heartbeat wait)")

# ----------------------------------------------------------- dispatch rewrite --
lines = text.split("\n")
start = None
end = None
for i, l in enumerate(lines):
    if l == 'case "${DEVICE}" in':
        start = i
        break
if start is None:
    errors.append("dispatch: 'case \"${DEVICE}\" in' not found")
else:
    depth = 0
    for j in range(start, len(lines)):
        if lines[j] == "esac":
            end = j
            break
    if end is None:
        errors.append("dispatch: closing esac not found")

if start is not None and end is not None:
    body = lines[start + 1:end]
    # split the four branches by their header lines
    idx = {}
    cur = None
    branches = {}
    order = []
    for l in body:
        if l == "    mustang|vm|\"\")":
            cur = "generic"; branches[cur] = []
            order.append(cur); continue
        if l == "    s10plus)":
            cur = "s10plus"; branches[cur] = []
            order.append(cur); continue
        if l == "    g7power)":
            cur = "g7power"; branches[cur] = []
            order.append(cur); continue
        if l == "    *)":
            cur = "unknown"; branches[cur] = []
            order.append(cur); continue
        if cur:
            branches[cur].append(l)
    missing = [k for k in ("generic", "s10plus", "g7power", "unknown") if k not in branches]
    if missing:
        errors.append("dispatch: branches not found: %s" % missing)
    else:
        def strip_trailer(b):
            b = list(b)
            while b and (b[-1].strip() == "" or b[-1].strip() == ";;"):
                b.pop()
            return b

        generic = strip_trailer(branches["generic"])
        s10plus = strip_trailer(branches["s10plus"])
        g7power = strip_trailer(branches["g7power"])
        unknown = strip_trailer(branches["unknown"])

        new = []
        new.append("# A18: DEVICE dispatch without any `case` pattern test.")
        new.append("# toybox 0.8.14 treats `\"\"` in a case list as a WILDCARD, so the old")
        new.append("# `case \"${DEVICE}\" in mustang|vm|\"\") ... s10plus) ...` made the s10plus and")
        new.append("# g7power branches unreachable: a boot with DEVICE=s10plus matched the")
        new.append("# generic branch.  Measured on the handset in A16 (survived only via")
        new.append("# force_s10plus_root) and fatal in A17.  Explicit tests only.")
        new.append("if [ -z \"${DEVICE}\" ] || [ \"${DEVICE}\" = mustang ] || [ \"${DEVICE}\" = vm ]; then")
        new.extend(generic)
        new.append("elif [ \"${DEVICE}\" = s10plus ]; then")
        new.extend(s10plus)
        new.append("elif [ \"${DEVICE}\" = g7power ]; then")
        new.extend(g7power)
        new.append("else")
        new.extend(unknown)
        new.append("fi")
        lines[start:end + 1] = new
        text = "\n".join(lines)
        print("OK  A18-core-2 DEVICE dispatch rewritten as if/elif (generic=%d s10plus=%d g7power=%d unknown=%d lines)"
              % (len(generic), len(s10plus), len(g7power), len(unknown)))

# ------------------------------------- s10plus branch: wait for /dev/sda31 ----
# With the dispatch fixed, the s10plus branch actually runs now -- and it must not
# depend on /dev/sda31 already existing.  A16 measured that the UFS node appears
# about a second after the first probe, and the branch's single `[ -b /dev/sda31 ]`
# test has no retry, so on a real device it would fall straight through to
# fail_boot.  Bounded wait with a per-second heartbeat (never silent: the operator
# has force-reset a boot during exactly this kind of silence).
sub(
    """        if [ -z "${ROOT_DEV}" ] && [ -b /dev/sda31 ]; then
            ROOT_DEV=/dev/sda31
            nuxel_say "PARTNAME discovery unavailable; using documented fallback /dev/sda31 (by-name userdata) - rootfs will be verified"
            diag "USERDATA_FALLBACK /dev/sda31"
        fi""",
    """        # A18: bounded wait for the UFS node, with a heartbeat every second.
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
                nuxel_say "s10plus: waiting for /dev/sda31 t=${_t}s blockdevs='$(ls /dev/sd* 2>/dev/null | tr '\\n' ' ')'"
                sleep 1
            done
        fi""",
    "A18-core-3 s10plus branch waits for /dev/sda31 with a heartbeat",
)

if errors:
    print("FATAL:")
    for e in errors:
        print("   " + e)
    sys.exit(1)

open(PATH, "w").write(text)
print("init.sh written")
