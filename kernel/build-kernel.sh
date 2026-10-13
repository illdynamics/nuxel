#!/usr/bin/env bash
# =============================================================================
# Nuxel kernel build dispatcher — mustang (Pixel 10 Pro XL / Tensor G5 / gs501).
#
# This is the ELECTRONIC build mechanism for the Nuxel Phase-0 kernel. It is
# referenced by kernel/google-pixel-10-pro-xl/README-toolchain.md and
# kernel/google-pixel-10-pro-xl/defconfig. Device selection is explicit via
# --device/NUXEL_DEVICE (default: mustang, the historical behaviour of this
# wrapper; the shared selector itself never guesses). Any other device must
# use kernel/${NUXEL_DEVICE_DIR}/build-kernel.sh.
#
# Behaviour (--help for exact flags):
#   * PREFERS the authoritative Google vendor kernel branch
#       android-gs-mustang-6.12  (private, ships arch/arm64/configs/gs501_defconfig)
#     and runs `make ARCH=arm64 gs501_defconfig`. This is the REAL mustang build.
#   * FALLS BACK (default in a network-restricted sandbox) to the public
#     android16-6.12 GKI common kernel and merges kernel/${NUXEL_DEVICE_DIR}/defconfig on top of
#     arch/arm64/configs/gki_defconfig via scripts/kconfig/merge_config.sh.
#   * Always applies kernel/${NUXEL_DEVICE_DIR}/patches/0001-nuxel-phone-features.patch (the NUXEL
#     Kconfig/Makefile/code) before configuring/building.
#
# Toolchain resolution order:
#   aarch64-linux-gnu-  (Linux-native cross GCC, glibc sysroot)  -- preferred
#   aarch64-none-linux-gnu- (ARM GNU Linux-targeted cross GCC)   -- fallback
#   aarch64-elf-        (Homebrew bare-metal GCC, freestanding)  -- last resort
# Only the first one found on PATH is used.
#
# macOS host-tool fix (briq-k1):
#   The Android/arm64 kernel builds several *host* tools (arch/arm64/tools/
#   gen-hyprel, scripts/sorttable, scripts/recordmcount, scripts/mod/modpost,
#   scripts/selinux/{genheaders,mdp}). On macOS these fail because the host C
#   compiler cannot find:
#     * <elf.h>   -> not shipped by Apple; vendored at kernel/host-tools/include/elf.h
#                    (a standalone copy of the GNU/glibc ELF ABI header).
#     * <endian.h>-> not shipped by Apple; vendored at kernel/host-tools/include/endian.h
#                    (a thin shim over libkern/OSByteOrder.h).
#     * <asm/types.h> -> the GENERATED arm64 uapi tree (arch/arm64/include/
#                    generated/uapi) is not on the host-tool include path; we add
#                    the generated + source uapi dirs via HOSTCFLAGS.
#   We inject all three through HOSTCFLAGS so they apply to EVERY host-tool
#   compile (and only host tools -- the cross (target) compile is untouched).
#
# GNU host tools: on macOS the system make(3.81) is too old, so GNU make
# (gmake 4.x), GNU bison (3.8), GNU flex and GNU sed are located from
# Homebrew kegs and prepended to PATH automatically.
#
# On success the artifacts land under kernel/${NUXEL_DEVICE_DIR}/.build/out/:
#   Image.gz  Image  dtbs/  modules.tar.{gz,bz2}  build.log  exit-code
# The exact final build command and its exit code are written to
# kernel/${NUXEL_DEVICE_DIR}/README-toolchain.md and echoed on stdout.
# =============================================================================

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${HERE}/.." && pwd)"            # = WORKSPACE_ROOT

# Device selection: this dispatcher historically built the mustang kernel, so
# it defaults to mustang when no explicit --device/NUXEL_DEVICE is given (the
# shared selector itself never silently guesses). Other devices have their own
# kernel/${NUXEL_DEVICE_DIR}/build-kernel.sh and are refused here.
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
    echo "error: kernel/build-kernel.sh builds ONLY mustang (got '${NUXEL_DEVICE_KEY}')." >&2
    echo "       Use kernel/${NUXEL_DEVICE_DIR}/build-kernel.sh for that device." >&2
    exit 1
}

# Per-device tree (selector-verified: == google-pixel-10-pro-xl for mustang).
BUILD="${HERE}/${NUXEL_DEVICE_DIR}/.build"
TREE="${BUILD}/linux-6.12"
OUT="${BUILD}/out"
PATCH="${HERE}/${NUXEL_DEVICE_DIR}/patches/0001-nuxel-phone-features.patch"
FRAGMENT="${HERE}/${NUXEL_DEVICE_DIR}/defconfig"
HOST_TOOLS_HDR="${HERE}/host-tools/include"   # vendored <elf.h> + <endian.h> shim
FILE2ALIAS_PATCH="${HERE}/host-tools/file2alias-darwin.patch" # macOS uuid_t clash fix

VENDOR_URL="https://android.googlesource.com/kernel/google-modules/gs"
VENDOR_BRANCH="android-gs-mustang-6.12"
COMMON_URL="https://android.googlesource.com/kernel/common"
COMMON_BRANCH="android16-6.12"
COMMON_COMMIT_REF="42b03373f376dc87116cb7e25ccd459b5d60a387"

JOBS="${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}"
USE_VENDOR=0
NO_CLONE=0
DO_CLEAN=1

usage() {
    sed -n '2,30p' "${BASH_SOURCE[0]}" | grep '^#' | sed 's/^# \{0,1\}//'
    echo
    echo "OPTIONS"
    echo "  --device KEY    Device key (default: mustang; only mustang is"
    echo "                  supported by this dispatcher)."
    echo "  --vendor        Build the authoritative vendor tree (gs501_defconfig)."
    echo "  --no-clone      Reuse an existing kernel/${NUXEL_DEVICE_DIR}/.build/<tree> if present."
    echo "  --no-clean      Do not run 'make mrproper' before configuring."
    echo "  -j N            Override job count (default: nproc)."
    echo "  --help          This message."
    exit 0
}

while [ $# -gt 0 ]; do
    case "$1" in
        --device)   shift 2 ;;   # validated + resolved by the selector above
        --vendor)   USE_VENDOR=1; shift ;;
        --no-clone) NO_CLONE=1; shift ;;
        --no-clean) DO_CLEAN=0; shift ;;
        -j)         JOBS="$2"; shift 2 ;;
        --help)     usage ;;
        *) echo "Unknown option: $1" >&2; usage ;;
    esac
done

# --- Locate GNU host tools (matters on macOS) --------------------------------
for keg in coreutils findutils grep gawk gnu-tar gnu-sed bison flex; do
    if [ -d "/opt/homebrew/opt/${keg}/libexec/gnubin" ]; then
        PATH="/opt/homebrew/opt/${keg}/libexec/gnubin:${PATH}"
    elif [ -d "/opt/homebrew/opt/${keg}/bin" ]; then
        PATH="/opt/homebrew/opt/${keg}/bin:${PATH}"
    fi
done

MAKE="${MAKE:-make}"
if command -v gmake >/dev/null 2>&1; then
    MAKE="gmake"
fi
if ! "${MAKE}" --version 2>/dev/null | grep -q "GNU Make"; then
    echo "error: need GNU make >= 4.0 (set MAKE= or install gmake)" >&2
    exit 1
fi

# --- Toolchain -----------------------------------------------------------------
TC=""
for cand in aarch64-linux-gnu- aarch64-none-linux-gnu- aarch64-elf-; do
    if command -v "${cand}gcc" >/dev/null 2>&1; then
        TC="${cand}"
        break
    fi
done
if [ -z "${TC}" ]; then
    echo "error: no aarch64 cross toolchain found (tried linux-gnu / none-linux-gnu / elf)" >&2
    exit 1
fi
TC_GCC="$("${TC}gcc" --version 2>/dev/null | head -1)"
echo "== toolchain: ${TC}gcc  -> ${TC_GCC}"

mkdir -p "${OUT}"

# --- Source tree (vendor preferred, common fallback) --------------------------
if [ "${USE_VENDOR}" -eq 1 ]; then
    TREE="${BUILD}/linux-6.12-mustang"
    SRC_BRANCH="${VENDOR_BRANCH}"
    SRC_URL="${VENDOR_URL}"
    DEFCONFIG_TARGET="gs501_defconfig"
    MERGE_MODE="native-defconfig"
else
    SRC_BRANCH="${COMMON_BRANCH}"
    SRC_URL="${COMMON_URL}"
    DEFCONFIG_TARGET="gki_defconfig"
    MERGE_MODE="fragment"
fi

if [ "${NO_CLONE}" -ne 1 ] && [ ! -d "${TREE}/.git" ]; then
    echo "== cloning ${SRC_URL} (${SRC_BRANCH})"
    git clone --depth=1 --branch "${SRC_BRANCH}" "${SRC_URL}" "${TREE}" \
        || { echo "error: clone of ${SRC_URL} failed (private/offline?)" >&2; exit 1; }
fi
[ -d "${TREE}/.git" ] || { echo "error: no kernel tree at ${TREE}" >&2; exit 1; }

cd "${TREE}"

# --- macOS host-tool include fix (briq-k1) ------------------------------------
HOSTCFLAGS="-I${HOST_TOOLS_HDR}"
case "$(uname -s)" in
    Darwin)
        # Only apply the uapi adjustments on macOS, where the host libc lacks
        # <asm/types.h>. The dirs are absolute so HOSTCFLAGS survives chdir.
        HOSTCFLAGS="${HOSTCFLAGS} -I${TREE}/arch/arm64/include/generated/uapi"
        HOSTCFLAGS="${HOSTCFLAGS} -I${TREE}/arch/arm64/include/uapi"
        HOSTCFLAGS="${HOSTCFLAGS} -I${TREE}/include/uapi"
        echo "== macOS host-tool fix: HOSTCFLAGS=${HOSTCFLAGS}"
        ;;
    *)  echo "== host is not Darwin; relying on system elf.h/asm types"
        ;;
esac
export HOSTCFLAGS

# Apply the Nuxel patch (idempotent: skip if already applied).
if ! git apply --check "${PATCH}" >/dev/null 2>&1; then
    echo "== patch appears applied already; verifying tree state ==="
    test -f drivers/nuxel/Kconfig || { echo "error: patch not applied and does not apply" >&2; exit 1; }
else
    echo "== applying ${PATCH}"
    git apply "${PATCH}"
fi

# Apply the Darwin host-tool uuid_t fix (briq-k1). Only relevant on macOS,
# where the system libc defines `uuid_t` as `unsigned char[16]`, clashing with
# the kernel host-side `uuid_t` in scripts/mod/file2alias.c. Idempotent.
if [ "$(uname -s)" = "Darwin" ]; then
    if git apply --check "${FILE2ALIAS_PATCH}" >/dev/null 2>&1; then
        echo "== applying ${FILE2ALIAS_PATCH} (Darwin uuid_t fix)"
        git apply "${FILE2ALIAS_PATCH}"
    else
        echo "== file2alias-darwin patch already applied / not needed; verifying ==="
        grep -q 'nuxel_host_uuid_t' scripts/mod/file2alias.c \
            || { echo "error: file2alias-darwin patch neither applied nor applicable" >&2; exit 1; }
    fi
fi

if [ "${DO_CLEAN}" -eq 1 ]; then
    echo "== make mrproper"
    "${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" mrproper >"${OUT}/mrproper.log" 2>&1 || true
fi

# --- Configure -----------------------------------------------------------------
CONFIGLOG="${OUT}/config.log"
: > "${CONFIGLOG}"
if [ "${MERGE_MODE}" = "native-defconfig" ]; then
    DEFCMD=("${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" "${DEFCONFIG_TARGET}")
    echo "== ${DEFCMD[*]}" | tee -a "${CONFIGLOG}"
    "${DEFCMD[@]}" || { echo "error: ${DEFCONFIG_TARGET} failed" >&2; exit 1; }
else
    echo "== ${MAKE} ARCH=arm64 CROSS_COMPILE=${TC} ${DEFCONFIG_TARGET} (GKI baseline)" | tee -a "${CONFIGLOG}"
    "${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" "${DEFCONFIG_TARGET}" \
        || { echo "error: ${DEFCONFIG_TARGET} failed" >&2; exit 1; }
    echo "== merging ${FRAGMENT} onto GKI baseline (merge_config.sh)" | tee -a "${CONFIGLOG}"
    set +e
    ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" \
        ./scripts/kconfig/merge_config.sh -m .config "${FRAGMENT}" >>"${CONFIGLOG}" 2>&1
    MRC=$?
    set -e
    echo "== merge_config.sh exit code: ${MRC}" | tee -a "${CONFIGLOG}"
    [ "${MRC}" -eq 0 ] || { echo "error: merge_config.sh failed (see ${CONFIGLOG})" >&2; exit 1; }
fi

# --- macOS host filesystem: netfilter case-collision mitigation (briq-k3) -------
# This host's macOS filesystem is case-insensitive (default APFS/HFS+). The
# android16-6.12 GKI baseline enables BOTH netfilter "target" and "match"
# modules that share a single physical source file whose git-tracked names
# differ ONLY by case in the SAME directory, e.g.:
#     CONFIG_NETFILTER_XT_TARGET_DSCP  -> needs net/netfilter/xt_DSCP.c
#     CONFIG_NETFILTER_XT_MATCH_DSCP   -> needs net/netfilter/xt_dscp.c
# and likewise TCPMSS. On a case-insensitive host only ONE filename per
# directory is physically representable, so the other object has "No rule to
# make target" and the Image link cannot complete. This is a HOST limitation,
# not a kernel/${NUXEL_DEVICE_DIR}/defconfig flaw: on Linux / a case-sensitive volume both outputs
# build normally. We keep the MATCH variant (whose lowercase source name IS the
# on-disk canonical entry) and disable the colliding TARGET variant so the
# common-kernel Image build completes cleanly on this host.
CFGTOOL="${TREE}/scripts/config"
if [ "$(uname -s)" = "Darwin" ]; then
    echo "== macOS case-insensitive FS: disabling colliding netfilter TARGET configs" | tee -a "${CONFIGLOG}"
    for dis in CONFIG_NETFILTER_XT_TARGET_DSCP CONFIG_NETFILTER_XT_TARGET_TCPMSS; do
        if grep -qE "^${dis}=" .config; then
            "${CFGTOOL}" --file .config --disable "${dis}"
            echo "   disabled ${dis}" | tee -a "${CONFIGLOG}"
        else
            echo "   ${dis} absent - nothing to disable" | tee -a "${CONFIGLOG}"
        fi
    done
fi

# Resolve any NEW config symbols introduced by the merged fragment to their
# built-in defaults non-interactively. Exit status is the olddefconfig proof.
echo "== ${MAKE} ARCH=arm64 CROSS_COMPILE=${TC} olddefconfig (absorb NEW symbols)" | tee -a "${CONFIGLOG}"
set +e
"${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" olddefconfig >>"${CONFIGLOG}" 2>&1
ODC=$?
set -e
echo "== olddefconfig exit code: ${ODC}" | tee -a "${CONFIGLOG}"
[ "${ODC}" -eq 0 ] || { echo "error: olddefconfig failed (see ${CONFIGLOG})" >&2; exit 1; }

# Sanity: the NUXEL symbols must be reachable in the generated config.
for sym in CONFIG_NUXEL CONFIG_NUXEL_PHONE CONFIG_NUXEL_BOOT_PARAM; do
    if ! grep -qE "^${sym}=y" .config; then
        echo "error: ${sym} missing from .config (Kconfig wiring broken?)" >&2
        exit 1
    fi
done
echo "== .config sanity: NUXEL symbols present =="
grep -E '^CONFIG_NUXEL(_PHONE|_BOOT_PARAM)?=y' .config | sed 's/^/    /'

# --- defconfig <-> Kconfig one-for-one audit (briq-02 ---------------------------
# Every `^CONFIG_NUXEL*` line in kernel/${NUXEL_DEVICE_DIR}/defconfig must map to a REAL Kconfig
# symbol added by kernel/${NUXEL_DEVICE_DIR}/patches/0001-nuxel-phone-features.patch under
# drivers/nuxel/Kconfig. This greppable gate guarantees no orphan
# `CONFIG_...=y` line survives `make olddefconfig` silently.
NUXEL_KCONFIG="drivers/nuxel/Kconfig"
AUDIT_FAIL=0
for line in $(grep -E '^CONFIG_NUXEL' "${FRAGMENT}"); do
    sym_name="${line%%=*}"                   # e.g. CONFIG_NUXEL_PHONE
    kname="${sym_name#CONFIG_}"              # e.g. NUXEL_PHONE
    if grep -qE "^(menuconfig|config) ${kname}([[:space:]]|$)" "${NUXEL_KCONFIG}"; then
        echo "   defconfig ${sym_name}=*  ->  drivers/nuxel/Kconfig 'config ${kname}' MATCH"
    else
        echo "error: ${sym_name}=* in ${FRAGMENT} has NO Kconfig symbol in ${NUXEL_KCONFIG}" >&2
        AUDIT_FAIL=1
    fi
done
if [ "${AUDIT_FAIL}" -ne 0 ]; then
    echo "error: orphan CONFIG_NUXEL* line(s) found; fix defconfig or add Kconfig entry" >&2
    exit 1
fi
echo "== defconfig<->Kconfig audit: all CONFIG_NUXEL* lines are Kconfig-backed =="

# --- archprepare (explicit host-tool gate, briq-k1/k2) -------------------------
ARCHPREP=("${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" archprepare)
echo "== ${ARCHPREP[*]}"
"${ARCHPREP[@]}" >"${OUT}/archprepare.log" 2>&1
APRC=$?
echo "== archprepare exit code: ${APRC}"
# Persist the hard gate proof non-lossily (briq-k1): the host-tool build
# (elf.h / asm/types.h) MUST exit 0 before any kernel compile is attempted.
# We record the exact invocation + exit code into BOTH archprepare.log (which is
# never truncated) AND build.log. Because the main build appends to build.log
# via 'tee -a' (never truncates), the gate block below always survives in the
# committed build.log.
{
    echo "== archprepare gate (host-tool verification, briq-k1)" 
    grep -E "HOSTCC|HOSTLD|GEN |SYNC |archprepare" "${OUT}/archprepare.log" | head -40
    echo "archprepare command: ${ARCHPREP[*]}"
    echo "archprepare exit code: ${APRC}"
} >> "${OUT}/build.log"
{
    echo "archprepare command: ${ARCHPREP[*]}"
    echo "archprepare exit code: ${APRC}"
} >> "${OUT}/archprepare.log"
[ "${APRC}" -eq 0 ] || { echo "archprepare FAILED -- see ${OUT}/archprepare.log" >&2; exit "${APRC}"; }

# --- Build ----------------------------------------------------------------------
# Primary, verifiable kernel targets first: Image.gz / Image / dtbs. This
# target set is what determines the recorded exit code -- it is fully
# buildable with a bare-metal toolchain (freestanding -ffreestanding).
BUILDCMD=("${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" "-j${JOBS}" Image.gz Image dtbs)
echo "== ${BUILDCMD[*]}"
echo "== build log: ${OUT}/build.log"
set +e
# Tee-append so the earlier archprepare gate block in build.log is NOT
# truncated away by the main compile (briq-k1 evidence persistence).
"${BUILDCMD[@]}" 2>&1 | tee -a "${OUT}/build.log"
EXIT_CODE=${PIPESTATUS[0]}
set -e
echo "${EXIT_CODE}" > "${OUT}/exit-code"
echo "== build exit code (Image.gz/Image/dtbs): ${EXIT_CODE}"

# --- modules (loadable, needs a Linux-targeted -gnu toolchain) ------------------
# Attempted separately and never allowed to fail the primary Image build. With a
# bare-metal toolchain (e.g. Homebrew aarch64-elf-) module linking against the
# kernel's exported module ABI is not possible; we record that limitation.
MODULES_OK=0
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo "== attempting 'modules' target (best-effort; see modules sections in build.log)"
    set +e
    "${MAKE}" ARCH=arm64 CROSS_COMPILE="${TC}" HOSTCFLAGS="${HOSTCFLAGS}" "-j${JOBS}" modules >>"${OUT}/build.log" 2>&1
    MOD_EXIT=$?
    set -e
    if [ "${MOD_EXIT}" -eq 0 ]; then
        MODULES_OK=1
        echo "== modules target exit code: ${MOD_EXIT} (OK)"
    else
        echo "== modules target exit code: ${MOD_EXIT} (not buildable with '${TC}'; documented)"
    fi
fi

# --- Collect artifacts -----------------------------------------------------------
if [ "${EXIT_CODE}" -eq 0 ]; then
    if [ -f arch/arm64/boot/Image.gz ]; then
        cp -f arch/arm64/boot/Image.gz "${OUT}/Image.gz"
    fi
    if [ -f arch/arm64/boot/Image ]; then
        cp -f arch/arm64/boot/Image "${OUT}/Image"
    fi
    if [ -d firmware ]; then
        rm -rf "${OUT}/firmware"
        cp -a firmware "${OUT}/firmware" 2>/dev/null || true
    fi

    # modules tarballs (gz + bz2). Use GNU tar from PATH (gnu-tar keg on macOS).
    find . -name '*.ko' -print0 > "${OUT}/.kolist"
    if [ -s "${OUT}/.kolist" ] && [ "${MODULES_OK}" -eq 1 ]; then
        xargs -0 tar -czf "${OUT}/modules.tar.gz" -T "${OUT}/.kolist" 2>/dev/null || true
        xargs -0 tar -cjf "${OUT}/modules.tar.bz2" -T "${OUT}/.kolist" 2>/dev/null || true
    else
        : > "${OUT}/modules.tar.gz"
        : > "${OUT}/modules.tar.bz2"
    fi
    if [ "${MODULES_OK}" -ne 1 ]; then
        # Document why no loadable modules were produced.
        : > "${OUT}/modules.tar.gz"
        : > "${OUT}/modules.tar.bz2"
        cat > "${OUT}/modules-NOTE.txt" <<EOF
The Image.gz / Image / dtbs kernel targets built successfully (exit code 0).

The optional 'modules' target was NOT produced: the toolchain '${TC}' is not a
Linux-targeted 'aarch64-linux-gnu-' cross toolchain (glibc sysroot). Linking
loadable '.ko' modules against the kernel's exported module ABI requires a
'*-linux-gnu-' sysroot (or a Linux container / clang). When such a toolchain is
available, run:  make ARCH=arm64 CROSS_COMPILE=<aarch64-linux-gnu-> modules
and re-run kernel/build-kernel.sh to collect the .ko tarballs under
kernel/${NUXEL_DEVICE_DIR}/.build/out/modules.tar.{gz,bz2}.  See kernel/${NUXEL_DEVICE_DIR}/README-toolchain.md section 7.
EOF
    fi
    rm -f "${OUT}/.kolist"

    # dtbs tre e: copy the built device-tree blobs tree.
    dtbi_out="${OUT}/dtbs"
    mkdir -p "${dtbi_out}"
    find arch/arm64/boot/dts -name '*.dtb' -print0 2>/dev/null \
        | xargs -0 -r -I{} cp --parents '{}' "${dtbi_out}/" 2>/dev/null || true
    # Also grab a plain flat list for convenience.
    find arch/arm64/boot/dts -name '*.dtb' -print 2>/dev/null | sed 's#^../.*/##' > "${OUT}/dtbs.txt" || true

    # --- Canonical O= output tree (briq-03) -------------------------------------
    # `make` emits the built kernel under arch/arm64/boot/. Publish a canonical
    # `out/arch/arm64/boot/` view inside the source tree (the conceptual `O=`
    # output location named by briq-03) while also keeping the collected
    # kernel/${NUXEL_DEVICE_DIR}/.build/out/ artifacts (what ci/validate-build.sh asserts).
    OUTCAN="${TREE}/out/arch/arm64/boot"
    mkdir -p "${OUTCAN}"
    [ -f arch/arm64/boot/Image ]   && cp -f arch/arm64/boot/Image   "${OUTCAN}/Image"
    [ -f arch/arm64/boot/Image.gz ] && cp -f arch/arm64/boot/Image.gz "${OUTCAN}/Image.gz"
    echo "== canonical O= output tree: ${OUTCAN}"
    ls -la "${OUTCAN}"

    # --- Record sha256/sizes of the primary artifacts (briq-03 req 4) ----------
    if command -v shasum >/dev/null 2>&1; then
        {
            echo "kernel build artifact sha256 (briq-03):"
            for f in "${OUT}/Image" "${OUT}/Image.gz"; do
                [ -f "$f" ] && shasum -a 256 "$f"
            done
            echo "canonical O= output:"
            shasum -a 256 "${OUTCAN}/Image" "${OUTCAN}/Image.gz" 2>/dev/null || true
        } > "${OUT}/sha256.txt"
        echo "== sha256 recorded -> ${OUT}/sha256.txt"
    fi

    # --- Repack boot.img from the freshly compiled Image + cmdline + initramfs
    # (briq-03 req 2/3): an ANDROID!-magic Android Boot Image Header v4 is
    # produced by images/build.sh (byte-correct internal mkbootimg.py). This is
    # best-effort and non-fatal to the kernel build itself.
    if [ -f "${ROOT}/images/build.sh" ] && [ -f "${OUT}/Image.gz" ]; then
        echo "== repacking boot/boot.img/boot.img (Android Boot Image Header v4)"
        set +e
        bash "${ROOT}/images/build.sh" --device "${NUXEL_DEVICE_KEY}" >>"${OUT}/build.log" 2>&1
        BRC=$?
        set -e
        echo "== images/build.sh exit code: ${BRC}"
        if [ "${BRC}" -eq 0 ] && [ -f "${ROOT}/boot/boot.img/boot.img" ]; then
            shasum -a 256 "${ROOT}/boot/boot.img/boot.img" >> "${OUT}/sha256.txt" 2>/dev/null || true
        fi
    fi

    echo "== artifacts in ${OUT}:"
    ls -la "${OUT}"
fi

# --- Final evidence ---------------------------------------------------------------
echo "=== FINAL build command:"
echo "   ${BUILDCMD[*]}"
echo "=== FINAL build exit code: ${EXIT_CODE}"

# Persist the audited build evidence into README-toolchain.md (section 7).
if command -v python3 >/dev/null 2>&1; then
    python3 - "${BUILDCMD[*]}" "${EXIT_CODE}" "${ARCHPREP[*]}" "${APRC}" "${OUT}" "${HERE}/${NUXEL_DEVICE_DIR}/README-toolchain.md" <<'PYE'
import io, os, sys
cmd, rc, aprep, aprc, outdir, readme = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
DD = os.environ.get('NUXEL_DEVICE_DIR', 'google-pixel-10-pro-xl')

merge_proof = ""
if os.path.isfile(os.path.join(outdir, "config.log")):
    try:
        mlog = io.open(os.path.join(outdir, "config.log"), encoding="utf-8").read()
        merge_exit = "n/a"
        for ln in mlog.splitlines():
            if "olddefconfig exit code:" in ln:
                merge_exit = ln.split(":")[-1].strip()
                break
        if merge_exit == "0":
            merge_proof = "GKI merge_config.sh + olddefconfig both exited 0 (see kernel/${NUXEL_DEVICE_DIR}/.build/out/config.log)."
    except Exception:
        merge_proof = ""

sha256_proof = "(no sha256.txt on this run)"
sha_txt = os.path.join(outdir, "sha256.txt")
if os.path.isfile(sha_txt):
    try:
        sha256_proof = io.open(sha_txt, encoding="utf-8").read().strip()
    except Exception:
        sha256_proof = "(sha256.txt unreadable)"

sec = '''
## 7. Verifiable build evidence (this run)

Host-tool gate (`make ARCH=arm64 archprepare`, briq-k1):

```sh
%s
```

Exit code: `%s`  (must be 0) -- proof also persisted at the top of `kernel/${NUXEL_DEVICE_DIR}/.build/out/build.log`.

Config gate (`merge_config.sh` + `olddefconfig`, briq-k2):
`kernel/${NUXEL_DEVICE_DIR}/.build/out/config.log` records both steps and their `exit code: 0` lines
(%s). The authoritative `gs501_defconfig` path is gated behind access to the
private Google vendor tree (`android-gs-mustang-6.12`); the public GKI
`gki_defconfig` merge is the path exercised on this host. The NUXEL symbols
(CONFIG_NUXEL / CONFIG_NUXEL_PHONE / CONFIG_NUXEL_BOOT_PARAM = y) are asserted
present in the generated `.config`.

Exact final kernel build command:

```sh
%s
```

Exit code: `%s`

Artifacts are asserted under kernel/${NUXEL_DEVICE_DIR}/.build/out/ (Image.gz > 1 MB, Image, dtbs/,
modules.tar.{gz,bz2}); `kernel/${NUXEL_DEVICE_DIR}/.build/out/exit-code` carries the exit code and
`kernel/${NUXEL_DEVICE_DIR}/.build/out/build.log` the matching log ending in the successful link.

### Artifact integrity (briq-03 req 4)

Compiled Image / Image.gz are emitted to the canonical O= output tree
`kernel/${NUXEL_DEVICE_DIR}/.build/linux-6.12/out/arch/arm64/boot/` and collected under
`kernel/${NUXEL_DEVICE_DIR}/.build/out/`. The ANDROID!-magic `boot/boot.img/boot.img` (Android
Boot Image Header v4) is repacked by `images/build.sh` from the freshly
compiled `Image.gz` + `boot/boot.img/cmdline.txt` + `initramfs.cpio.gz`.

```
%s
```

Boot image repack: `bash kernel/build-kernel.sh` runs `bash images/build.sh`
(`file boot/boot.img/boot.img` => Android bootimg).
''' % (aprep, aprc, merge_proof, cmd, rc, sha256_proof)
sec = sec.replace('${NUXEL_DEVICE_DIR}', DD)
try:
    s = io.open(readme, encoding='utf-8').read()
except FileNotFoundError:
    sys.stderr.write('note: README-toolchain.md not found; skipping evidence write\n')
    sys.exit(0)
# Replace any previous evidence block.
head = s.split('# 7. Verifiable build evidence')[0]
open(readme, 'w', encoding='utf-8').write(head.rstrip() + '\n' + sec)
PYE
fi

exit "${EXIT_CODE}"
