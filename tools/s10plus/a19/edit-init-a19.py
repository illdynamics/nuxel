#!/usr/bin/env python3
"""A19 initramfs /init edits — make the shell's defects harmless.

Measured toybox 0.8.14 defects (reproduced in podman with the initramfs's own
/bin/toybox):

  1. an empty `case` alternative is a wildcard  -> fixed in A18
  2. `if A; then a; elif B; then b; else c; fi` runs **a AND c** when A is true
  3. `$!` is not set for background jobs        -> the animation hold PID has been
     empty in every candidate

A19 therefore removes every `if/elif/else` chain and every `$!` use from the
boot-critical path.  Flat `if ... fi` statements are used instead; they are
mutually exclusive by construction.
"""
import os
import re
import sys

PATH = os.environ.get("INIT_SH", "boot/initramfs/init.sh")
lines = open(PATH).read().split("\n")
errors = []


def find_line(pred, start=0, what=""):
    for i in range(start, len(lines)):
        if pred(lines[i]):
            return i
    errors.append("anchor not found: %s" % what)
    return -1


def rebuild_block(start_idx, take_until_line, new_text, what):
    e = find_line(lambda l: l == take_until_line, start_idx, what + " (end)")
    if e < 0 or start_idx < 0:
        return
    del lines[start_idx:e + 1]
    lines[start_idx:start_idx] = new_text.split("\n")
    print("OK  %s (replaced %d lines)" % (what, e - start_idx + 1))


# ---------------------------------------------------------------------------
# 1. systemd-library deployment: no elif chain, no nested if/else
# ---------------------------------------------------------------------------
s = find_line(lambda l: l.strip().startswith('if nuxel_sd_verify "${SD_TARGET}"; then'),
              0, "systemd-lib chain")
if s >= 0:
    e = find_line(lambda l: l == "fi", s + 1, "systemd-lib end")
    # the block's own final "fi" is the first one at column 0 after the block start
    if e >= 0:
        body = "\n".join(lines[s:e + 1])
        # confirm this is the expected chain
        if "elif [ -f" in body and "SYSTEMD_LIB_IMAGE_MISSING" in body:
            new = '''# A19: not an if/elif/else chain.  toybox runs the `else` branch as well when the
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
        cp "${SD_TARGET}" "${SD_TARGET}.nuxel-orig" 2>/dev/null && \\
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
            [ -f "${SD_TARGET}.nuxel-orig" ] && \\
                cp "${SD_TARGET}.nuxel-orig" "${SD_TARGET}" 2>/dev/null
            nuxel_marker SYSTEMD_LIB_VERIFY_FAILED
        fi
    fi
fi
if [ "${NUXEL_SD_STATE}" != 0 ] && [ ! -f "${NUXEL_SD_SRC}" ]; then
    diag "SYSTEMD_LIB image missing from the initramfs"
    nuxel_marker SYSTEMD_LIB_IMAGE_MISSING
fi'''
            lines[s:e + 1] = new.split("\n")
            print("OK  A19-1 systemd-lib block de-chained")

# ---------------------------------------------------------------------------
# 2. DEVICE dispatch: mutually exclusive flat ifs, board-specific first
# ---------------------------------------------------------------------------
s = find_line(lambda l: l == 'if [ -z "${DEVICE}" ] || [ "${DEVICE}" = mustang ] || [ "${DEVICE}" = vm ]; then',
              0, "dispatch chain start")
if s >= 0:
    e = find_line(lambda l: l == "fi", s + 1, "dispatch chain end")
    # the dispatch ends with the last "fi" of the chain; find the line that equals "fi"
    # and whose *next* non-empty line is "force_s10plus_root" or similar
    if e >= 0:
        # locate the true end: the "fi" line immediately followed by a blank then force_s10plus_root
        for j in range(s, len(lines)):
            if lines[j] == "fi" and any(lines[k].strip() == "force_s10plus_root" for k in range(j, min(j + 4, len(lines)))):
                e = j
                break
        body = "\n".join(lines[s:e + 1])
        idx = {}
        # split the chain by its guarsd
        parts = {"generic": [], "s10plus": [], "g7power": [], "unknown": []}
        cur = "generic"
        for l in lines[s + 1:e]:
            if l.startswith('elif [ "${DEVICE}" = s10plus ]'):
                cur = "s10plus"; continue
            if l.startswith('elif [ "${DEVICE}" = g7power ]'):
                cur = "g7power"; continue
            if l == "else":
                cur = "unknown"; continue
            parts[cur].append(l)
        if all(parts[k] for k in parts):
            def dedent(b):
                # bodies are indented one level deeper than the new flat guards
                return [re.sub(r'^    ', '', x) if x.startswith('    ') else x for x in b]
            new = []
            new.append("# A19: four independent, mutually exclusive `if` statements -- not a")
            new.append("# chain, because toybox 0.8.14 executes an if/elif/else chain's `else`")
            new.append("# branch as well when the first condition is true.  The board-specific")
            new.append("# branch is deliberately first.")
            new.append('if [ "${DEVICE}" = s10plus ]; then')
            new.extend(parts["s10plus"])
            new.append("fi")
            new.append('if [ "${DEVICE}" = g7power ]; then')
            new.extend(parts["g7power"])
            new.append("fi")
            new.append('if [ "${DEVICE}" = "" ] || [ "${DEVICE}" = mustang ] || [ "${DEVICE}" = vm ]; then')
            new.extend(parts["generic"])
            new.append("fi")
            new.append('if [ "${DEVICE}" != s10plus ] && [ "${DEVICE}" != g7power ] && [ "${DEVICE}" != "" ] && [ "${DEVICE}" != mustang ] && [ "${DEVICE}" != vm ]; then')
            new.extend(parts["unknown"])
            new.append("fi")
            lines[s:e + 1] = new
            print("OK  A19-2 DEVICE dispatch de-chained (%d/%d/%d/%d lines)"
                  % (len(parts["generic"]), len(parts["s10plus"]), len(parts["g7power"]), len(parts["unknown"])))
        else:
            errors.append("dispatch: could not identify all four branches")

# ---------------------------------------------------------------------------
# 3. animation hold PID without $!
# ---------------------------------------------------------------------------
s = find_line(lambda l: l.strip() == "NUXEL_HOLD_PID=$!", 0, "hold pid capture")
if s >= 0:
    new = '''    # A19: toybox does not set $! for background jobs (measured - the marker has
    # been empty in A16, A17 and A18), so resolve the animator through /proc.
    NUXEL_HOLD_PID=""
    _n=0
    while [ "${_n}" -lt 20 ]; do
        for _p in /proc/[0-9]*; do
            if [ "$(cat "${_p}/comm" 2>/dev/null)" = "nuxel-fb-phone" ]; then
                _cl="$(cat "${_p}/cmdline" 2>/dev/null | tr '\\0' ' ')"
                case "${_cl}" in
                    *hold*) NUXEL_HOLD_PID="${_p#/proc/}"; break ;;
                esac
            fi
        done
        [ -n "${NUXEL_HOLD_PID}" ] && break
        _n=$((_n + 1))
        sleep 1
    done'''
    del lines[s]
    lines[s:s] = new.split("\n")
    print("OK  A19-3 hold PID resolved via /proc (no $!)")

if errors:
    print("FATAL:")
    for e in errors:
        print("   " + e)
    sys.exit(1)
open(PATH, "w").write("\n".join(lines))
print("init.sh written")
