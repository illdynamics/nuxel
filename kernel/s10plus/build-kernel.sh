#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ Kernel Build Wrapper — Samsung Galaxy S10+ (beyond2lte)
#
# AUTHORITATIVE kernel source (verified 2026-10-11):
#   https://github.com/Linux4/android_kernel_samsung_exynos9820
#   commit f7194c1d15eded1c2a1a4dc63825b26103435cc0  (Linux 4.14.253 downstream)
#   defconfig: exynos9820-beyond2lte_defconfig
#
# This is the *downstream* Samsung Exynos 9820 kernel fork that the
# postmarketOS S10 port (device-samsung-beyond1lte) actually builds and boots.
# It is the kernel that matches the vendor firmware in firmware/s10plus/
# (bcmdhd WiFi, CS47L93/CS35L40 audio, S3NRN82 NFC, FIMC-IS camera).
#
# CORRECTION (2026-10-11): the previous version of this script cloned
#   https://github.com/postmarketOS/linux-postmarketos branch exynos9820
# which DOES NOT EXIST (404). There is no `linux-postmarketos-exynos9820`
# package in pmaports either — the S10 uses `linux-samsung-beyond1lte`
# (this downstream tree). The `linux-postmarketos-exynos9820` / "close-to-
# mainline" claim in the older bring-up docs was aspirational, not real.
#
# Usage:
#   NUXEL_DEVICE=s10plus bash kernel/s10plus/build-kernel.sh [--clone] [--clean]
#       [--jobs N] [--cross <prefix>] [--fragment FILE] [--no-fragment] [--help]
#
# Outputs (under kernel/s10plus/.build/out/):
#   arch/arm64/boot/Image.gz
#   arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_*.dtb
#
# Flashing is heimdall (BOOT+SYSTEM) or TWRP adb+dd — there is NO fastboot.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DEVICE_KEY="s10plus"

DOWNSTREAM_REPO="https://github.com/Linux4/android_kernel_samsung_exynos9820"
DOWNSTREAM_COMMIT="f7194c1d15eded1c2a1a4dc63825b26103435cc0"
DEFCONFIG="exynos9820-beyond2lte_defconfig"

# The downstream Samsung Makefile hardcodes its internal Android toolchain as
# the default CROSS_COMPILE:
#   CROSS_COMPILE ?= $(srctree)/toolchain/gcc-cfp/.../aarch64-linux-android-
# That toolchain is not shipped with the source, so a bare `make` dies with
#   .../aarch64-linux-android-gcc: No such file or directory
#   Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: ... not supported by compiler
# We therefore always pass CROSS_COMPILE explicitly on the make command line
# (command-line assignments override the Makefile's `?=` default). The default
# matches the Debian/Ubuntu `gcc-aarch64-linux-gnu` package used in CI; override
# with --cross / $CROSS_COMPILE for another toolchain (or `--cross ''` for a
# native aarch64 host build).
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"

# GCC 14/15 turned several C diagnostics into hard errors; the 4.14 downstream
# tree predates that. We relax them (the class of fix the postmarketOS
# downstream-kernel tooling applies) - but this list is only a *wish list*: the
# per-compiler filter below drops any flag the selected compiler does not
# understand. That matters because `-Wno-error=<x>` is itself a HARD ERROR when
# the compiler has no `-W<x>` (e.g. `-Wno-error=return-mismatch`, whose
# `-Wreturn-mismatch` only exists in GCC >= 14, while CI ships GCC 13). The
# downstream tree appends $(KCFLAGS) to KBUILD_CFLAGS (Makefile:963), so one
# unknown flag also breaks every `cc-option` probe - including
# prepare-compiler-check, which then reports the misleading
# "Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: ... not supported by compiler".
# The bare trailing `-Wno-error` is also required: the downstream tree compiles
# with a global `-Werror` (Makefile:428), so ordinary warnings such as
# -Wformat= become hard errors (e.g. arch/arm64/mm/fault.c using %lx with a
# phys_addr_t). KCFLAGS is appended last to KBUILD_CFLAGS (Makefile:963), so the
# trailing -Wno-error downgrades those back to warnings.
DEFAULT_KCFLAGS="-fcommon -Wno-error=incompatible-pointer-types -Wno-error=implicit-function-declaration -Wno-error=int-conversion -Wno-error=implicit-int -Wno-error=strict-prototypes -Wno-error=date-time -Wno-error=designated-init -Wno-error=return-mismatch -Wno-error=discarded-qualifiers -Wno-error=pointer-sign -Wno-error"

DO_CLONE=0
DO_CLEAN=0
JOBS="${JOBS:-$( (command -v nproc >/dev/null && nproc) || echo 4)}"
# The live S10+ kernel is NOT the stock exynos9820-beyond2lte defconfig: it also
# carries the kbase/UDMABUF/userns/NFC capability fragment (PWNAGE-48000..54000).
# Apply it by default so a CI build reproduces the kernel the phone runs.
FRAGMENT="${NUXEL_KERNEL_FRAGMENT:-${NUXEL_ROOT}/kernel/s10plus/configs/nuxel-drm-kbase.fragment}"
USE_FRAGMENT=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) grep '^#' "$0" | sed -n '2,40p' | sed 's/^# \{0,1\}//'; exit 0 ;;
        --clone) DO_CLONE=1; shift ;;
        --clean) DO_CLEAN=1; shift ;;
        --jobs)  JOBS="$2"; shift 2 ;;
        --cross) CROSS_COMPILE="$2"; shift 2 ;;
        --fragment) FRAGMENT="$2"; shift 2 ;;
        --no-fragment) USE_FRAGMENT=0; shift ;;
        --device) export NUXEL_DEVICE="$2"; shift 2 ;;
        *) echo "Unknown: $1"; exit 1 ;;
    esac
done

# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    echo "ERROR: kernel/s10plus/build-kernel.sh is ONLY for s10plus. Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

KSRC="${NUXEL_ROOT}/kernel/s10plus/.build/src"
KOUT="${NUXEL_ROOT}/kernel/s10plus/.build/out"

# --- GNU host tools + macOS host-tool include fix (ported from kernel/build-kernel.sh)
# The S10+ (Exynos 9820) downstream tree also builds *host* tools on macOS that
# need GNU make, and need <elf.h>/<endian.h>/<asm/types.h> which Apple does not
# ship.  <elf.h>/<endian.h> are vendored in kernel/host-tools/include; the
# generated arm64 uapi wrappers land under $KOUT (out-of-tree O= build).
for _keg in coreutils findutils grep gawk gnu-tar gnu-sed bison flex; do
    if [ -d "/opt/homebrew/opt/${_keg}/libexec/gnubin" ]; then
        PATH="/opt/homebrew/opt/${_keg}/libexec/gnubin:${PATH}"
    elif [ -d "/opt/homebrew/opt/${_keg}/bin" ]; then
        PATH="/opt/homebrew/opt/${_keg}/bin:${PATH}"
    fi
done
export PATH
MAKE="${MAKE:-make}"
if command -v gmake >/dev/null 2>&1; then MAKE="gmake"; fi
HOST_TOOLS_HDR="${NUXEL_ROOT}/kernel/host-tools/include"
HOSTCFLAGS="-I${HOST_TOOLS_HDR}"
# Host tools are linked with the host compiler.  On macOS a bare `ld` is the
# Darwin linker and rejects ELF objects produced by clang/gcc, which breaks
# the genheaders/objtool link steps; point LD at the compiler driver.
export LD="${HOSTCC:-cc}"
if [ "$(uname -s)" = "Darwin" ]; then
    HOSTCFLAGS="${HOSTCFLAGS} -I${KOUT}/arch/arm64/include/generated/uapi"
    HOSTCFLAGS="${HOSTCFLAGS} -I${KSRC}/arch/arm64/include/uapi"
    HOSTCFLAGS="${HOSTCFLAGS} -I${KSRC}/include/uapi"
fi
export HOSTCFLAGS
echo "[nuxel-s10plus-kernel] MAKE: ${MAKE}"
echo "[nuxel-s10plus-kernel] HOSTCFLAGS: ${HOSTCFLAGS}"

# --- toolchain flag probe -------------------------------------------------
# Keep only the DEFAULT_KCFLAGS the selected compiler actually accepts.
# `echo | $(CC) <flag> -c -x c - -o /dev/null` exits non-zero for an unknown
# option, so unsupported relaxations are dropped instead of poisoning the build.
KCFLAGS=""
_CC="${CROSS_COMPILE}gcc"
for _f in ${DEFAULT_KCFLAGS}; do
    if echo | "${_CC}" "${_f}" -c -x c - -o /dev/null >/dev/null 2>&1; then
        KCFLAGS="${KCFLAGS:+${KCFLAGS} }${_f}"
    else
        echo "[nuxel-s10plus-kernel] note: dropping flag unsupported by ${_CC}: ${_f}"
    fi
done

echo "[nuxel-s10plus-kernel] Device: ${DEVICE_KEY} (beyond2lte, Exynos 9820)"
echo "[nuxel-s10plus-kernel] Kernel: ${DOWNSTREAM_REPO##*/}@${DOWNSTREAM_COMMIT:0:12} (Linux 4.14.253 downstream)"
echo "[nuxel-s10plus-kernel] Cross:   ${CROSS_COMPILE:-<native, empty>}"
echo "[nuxel-s10plus-kernel] Defconfig: ${DEFCONFIG}"
echo "[nuxel-s10plus-kernel] KCFLAGS: ${KCFLAGS:-<none>}"
echo "[nuxel-s10plus-kernel] Output:  ${KOUT}"

[[ $DO_CLEAN -eq 1 ]] && { echo "[kernel] Cleaning ${KOUT}"; rm -rf "${KOUT}"; }
mkdir -p "${KOUT}"

# --- clone / fetch ---
if [[ $DO_CLONE -eq 1 || ! -d "${KSRC}/.git" ]]; then
    if [ -d "${KSRC}" ] && [ ! -e "${KSRC}/.git" ] && [ -f "${KSRC}/Makefile" ]; then
        echo "[kernel] Using existing extracted tree at ${KSRC}"
    else
        echo "[kernel] Cloning ${DOWNSTREAM_REPO} (commit ${DOWNSTREAM_COMMIT:0:12})..."
        git clone --filter=blob:none --no-checkout "${DOWNSTREAM_REPO}" "${KSRC}"
        git -C "${KSRC}" checkout "${DOWNSTREAM_COMMIT}"
    fi
fi

# --- apply this repository's kernel patches (idempotent + auditable) --------
# The toolchain README previously claimed this wrapper applied patches, but
# the implementation had no git-apply step.  Keep patch application explicit:
# sorted order, skip documentation-only stubs, detect already-applied patches,
# and allow a per-patch .required sidecar to make a patch failure fatal.
# True when every file a patch creates already exists in the source tree.
patch_targets_present() {
    local patch="$1" f added=0
    while read -r f; do
        [ -n "${f}" ] || continue
        added=1
        [ -e "${KSRC}/${f}" ] || return 1
    done < <(awk '/^diff --git /{path=$4; sub(/^b\//,"",path)} /^new file mode /{print path}' "${patch}")
    [ "${added}" = 1 ]
}

# Patch order across the series is not strictly sequential: some patches touch
# the same files as an earlier one (0007 nfc transport / 0007 class name).
# "git apply --check --cached" sees the staged tree, which the full wrapper
# keeps in the post-series state, so a patch whose content is already staged is
# reported as applied instead of conflicting.
patch_already_in_tree() {
    local patch="$1"
    git -C "${KSRC}" apply --check --cached "${patch}" >/dev/null 2>&1 || return 1
    # A patch that creates files cannot be checked while the file exists on
    # disk, and reverse-checking a modified file fails; the staged check
    # above is the authority for the build tree.
    ! git -C "${KSRC}" apply --check "${patch}" >/dev/null 2>&1 || return 0
}

apply_kernel_patches() {
    local patch_dir="${NUXEL_ROOT}/kernel/s10plus/patches"
    local patch log required
    local -a patches=()
    log="${KOUT}/patch-application.log"
    : > "${log}"
    if [[ ! -d "${patch_dir}" ]]; then
        echo "[kernel-patches] no patch directory: ${patch_dir}" | tee -a "${log}"
        return 0
    fi
    shopt -s nullglob
    patches=("${patch_dir}"/*.patch)
    shopt -u nullglob
    if [[ ${#patches[@]} -eq 0 ]]; then
        echo "[kernel-patches] no *.patch files found" | tee -a "${log}"
        return 0
    fi

    for patch in "${patches[@]}"; do
        required="${patch}.required"
        if grep -qE '^# STUB([[:space:]]|$)' "${patch}" 2>/dev/null; then
            echo "[kernel-patches] SKIP documentation stub: $(basename "${patch}")" | tee -a "${log}"
            continue
        fi

        if git -C "${KSRC}" apply --reverse --check "${patch}" >/dev/null 2>&1; then
            echo "[kernel-patches] ALREADY_APPLIED: $(basename "${patch}")" | tee -a "${log}"
            continue
        fi
        if patch_targets_present "${patch}"; then
            # A patch that creates files cannot be re-applied (git reports
            # "already exists") nor reverse-checked while later hunks of the
            # same series differ; every file it creates is already in the
            # tree, so its content is present.
            echo "[kernel-patches] ALREADY_APPLIED (files present): $(basename "${patch}")" | tee -a "${log}"
            continue
        fi

        if git -C "${KSRC}" apply --check "${patch}" >/dev/null 2>&1; then
            echo "[kernel-patches] APPLY: $(basename "${patch}")" | tee -a "${log}"
            if git -C "${KSRC}" apply "${patch}" >>"${log}" 2>&1 \
                && git -C "${KSRC}" apply --reverse --check "${patch}" >/dev/null 2>&1; then
                echo "[kernel-patches] APPLIED_AND_VERIFIED: $(basename "${patch}")" | tee -a "${log}"
                continue
            fi
            echo "[kernel-patches] ERROR: apply did not verify: $(basename "${patch}")" | tee -a "${log}"
        elif patch_already_in_tree "${patch}"; then
            echo "[kernel-patches] ALREADY_APPLIED (staged tree): $(basename "${patch}")" | tee -a "${log}"
            continue
        else
            echo "[kernel-patches] CONFLICT: $(basename "${patch}")" | tee -a "${log}"
        fi

        if [[ -f "${required}" ]]; then
            echo "[kernel-patches] REQUIRED patch failed; aborting build: $(basename "${patch}")" | tee -a "${log}"
            return 1
        fi
        echo "[kernel-patches] WARN: optional patch not applied; see ${log} and adjacent .README: $(basename "${patch}")" | tee -a "${log}"
    done
    echo "[kernel-patches] summary: ${log}"
}

# The tree has been prepared (patches already applied and verified by an
# earlier run): re-applying the series would conflict on its own edits.
if [ "${NUXEL_SKIP_PATCHES:-0}" = "1" ]; then
    echo "[kernel-patches] NUXEL_SKIP_PATCHES=1 (tree is pre-patched)"
else
    apply_kernel_patches
fi

# --- GCC-13 warning hardening (root-cause fix) ------------------------------
# The downstream 4.14 tree hard-codes -Werror in two places a KCFLAGS
# relaxation cannot reach: per-category `$(call cc-option,-Werror=<diag>)` in
# the top Makefile (specific beats the generic -Wno-error regardless of order)
# and per-directory flags appended after KBUILD_CFLAGS, e.g. bcmdhd's
# `DHDCFLAGS += -Wall -Werror ... -> EXTRA_CFLAGS` (which lands *after* KCFLAGS
# on the cc command line). On CI's GCC 13 that turns ordinary warnings such as
#     block/blk-crypt.c:213: error: function declaration isn't a prototype
#         [-Werror=strict-prototypes]
#     drivers/net/wireless/broadcom/bcmdhd_101_16/wl_android.c:12016: error:
#         the comparison will always evaluate as 'true' ... [-Werror=address]
# into fatal errors. tools/kernel-relax-werror.sh strips those tokens from the
# scratch tree's source Makefiles (idempotent; kbuild-internal scripts/* kept).
bash "${NUXEL_ROOT}/tools/kernel-relax-werror.sh" "${KSRC}"

# --- ABOX Calliope core firmware: build into the kernel ----------------------
# The S10+ ABOX is probed before the rootfs is mounted (Samsung SAR_RD loads the
# ramdisk late), so request_firmware_direct() cannot see /lib/firmware at the
# first abox_enable().  Embedding the four core Calliope blobs as
# CONFIG_EXTRA_FIRMWARE makes the first probe succeed without any userspace PM
# workaround.  The files are the same proprietary blobs already shipped in the
# Nuxel rootfs /vendor/firmware and /lib/firmware; they are never downloaded
# from a third party by the build.
EMBED_FW_DIR="${NUXEL_EMBED_FW_DIR:-${NUXEL_ROOT}/build/out/s10plus/pwnage38000/firmware}"
EMBED_FW_NAMES="calliope_sram.bin calliope_sram_2.bin calliope_dram.bin calliope_dram_2.bin"
if [ -d "$EMBED_FW_DIR" ]; then
    _fw_ok=1
    for _fw in $EMBED_FW_NAMES; do
        [ -r "$EMBED_FW_DIR/$_fw" ] || _fw_ok=0
    done
    if [ "$_fw_ok" = 1 ]; then
        DEFCONFIG_FILE="${KSRC}/arch/arm64/configs/${DEFCONFIG}"
        grep -q '^CONFIG_EXTRA_FIRMWARE=' "$DEFCONFIG_FILE" 2>/dev/null || \
            printf 'CONFIG_EXTRA_FIRMWARE="%s"\n' "$EMBED_FW_NAMES" >> "$DEFCONFIG_FILE"
        grep -q '^CONFIG_EXTRA_FIRMWARE_DIR=' "$DEFCONFIG_FILE" 2>/dev/null || \
            printf 'CONFIG_EXTRA_FIRMWARE_DIR="%s"\n' "$EMBED_FW_DIR" >> "$DEFCONFIG_FILE"
        echo "[nuxel-s10plus-kernel] embedding ABOX Calliope core firmware from $EMBED_FW_DIR"
    else
        echo "[nuxel-s10plus-kernel] WARN: EMBED_FW_DIR exists but is missing core Calliope blobs; not embedding"
    fi
else
    echo "[nuxel-s10plus-kernel] WARN: EMBED_FW_DIR $EMBED_FW_DIR does not exist; not embedding core Calliope blobs"
fi


# A macOS build host uses a case-insensitive filesystem: the kernel tree ships
# pairs such as net/netfilter/xt_MARK.c / xt_mark.c and
# include/uapi/linux/netfilter/xt_MARK.h / xt_mark.h, and only one of each pair
# can exist on disk.  The colliding source is patched to include its ABI
# header through the explicit uapi path (see patch 0022).  Do not fail the
# build on the pair that cannot be materialised.
if [ "$(uname -s)" = "Darwin" ] && [ -x "${NUXEL_ROOT}/tools/kernel-case-collision-fix.sh" ]; then
    bash "${NUXEL_ROOT}/tools/kernel-case-collision-fix.sh" "${KSRC}"
fi

# --- configure ---
cd "${KSRC}"
# CONFIG_LOCALVERSION_AUTO appends "-dirty-<sha>" to the release.  The build
# tree is always a working tree with patches applied, so that suffix changes
# with every edit and makes every other object rebuild (and the release name
# unpredictable).  The pinned commit is the whole source identity, so the
# release stays "4.14.253" for every build of this tree.
"${MAKE}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    HOSTCFLAGS="${HOSTCFLAGS}" KCFLAGS="${KCFLAGS}" "${DEFCONFIG}"

# --- live capability fragment (kbase GPU, UDMABUF, userns, NFC) -------------
# Every setting below was read back from the running handset
# (`zcat /proc/config.gz`); tools/s10plus/verify-kernel-config.py is the
# fail-closed gate that proves the built .config still has them.
if [[ "${USE_FRAGMENT}" = "1" ]]; then
    [ -f "${FRAGMENT}" ] || { echo "[kernel] ERROR: fragment not found: ${FRAGMENT}" >&2; exit 1; }
    echo "[nuxel-s10plus-kernel] applying capability fragment: ${FRAGMENT}"
    while IFS= read -r line; do
        case "${line}" in ''|'#'*) continue ;; esac
        key="${line%%=*}"; val="${line#*=}"
        if [ "${val}" = "n" ]; then
            if grep -q "^${key}=" "${KOUT}/.config"; then
                sed -i.bak "s|^${key}=.*|# ${key} is not set|" "${KOUT}/.config"
            elif ! grep -q "^# ${key} is not set" "${KOUT}/.config"; then
                printf '# %s is not set\n' "${key}" >> "${KOUT}/.config"
            fi
        elif grep -q "^${key}=" "${KOUT}/.config"; then
            sed -i.bak "s|^${key}=.*|${key}=${val}|" "${KOUT}/.config"
        elif grep -q "^# ${key} is not set" "${KOUT}/.config"; then
            sed -i.bak "s|^# ${key} is not set|${key}=${val}|" "${KOUT}/.config"
        else
            printf '%s=%s\n' "${key}" "${val}" >> "${KOUT}/.config"
        fi
    done < "${FRAGMENT}"
    rm -f "${KOUT}/.config.bak"
    "${MAKE}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
        HOSTCFLAGS="${HOSTCFLAGS}" KCFLAGS="${KCFLAGS}" olddefconfig >/dev/null
    echo "[nuxel-s10plus-kernel] capability fragment applied + olddefconfig"
fi

# --- build ---
# Never let a compiler diagnostic race the NFC or USBNET drivers out of the
# final kernel: both are mandatory on this image and each has an independent
# parity gate (tools/s10plus/verify-kernel-nfc.py / verify-kernel-usbnet.py).
echo "[kernel] building mandatory NFC + USBNET driver objects..."
"${MAKE}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    HOSTCFLAGS="${HOSTCFLAGS}" -j"${JOBS}" KCFLAGS="${KCFLAGS}" \
    drivers/nfc/sec_nfc.o drivers/nfc/s3fwrn5/ \
    drivers/usb/gadget/function/f_ncm.o \
    drivers/usb/gadget/function/f_ecm.o \
    drivers/usb/gadget/function/f_eem.o \
    drivers/usb/gadget/function/f_subset.o


echo "[kernel] asm-generic + archprepare (generated uapi headers for host tools)..."
"${MAKE}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    HOSTCFLAGS="${HOSTCFLAGS}" asm-generic archprepare

echo "[kernel] user-namespace source gate..."
python3 "${NUXEL_ROOT}/tools/s10plus/verify-kernel-userns.py" --src "${KSRC}" --config "${KOUT}/.config"

echo "[kernel] Building Image.gz + dtbs (jobs=${JOBS})..."
"${MAKE}" O="${KOUT}" ARCH=arm64 CROSS_COMPILE="${CROSS_COMPILE}" \
    HOSTCFLAGS="${HOSTCFLAGS}" -j"${JOBS}" KCFLAGS="${KCFLAGS}" Image.gz dtbs

echo "[kernel] Done."
if [[ "${USE_FRAGMENT}" = "1" ]]; then
    echo "[kernel] capability parity:"
    if ! python3 "${NUXEL_ROOT}/tools/s10plus/verify-kernel-config.py" \
            --config "${KOUT}/.config" --quiet; then
        echo "[kernel] ERROR: built .config is not the live S10+ capability set" >&2
        exit 1
    fi
fi
ls -lh "${KOUT}/arch/arm64/boot/Image.gz" 2>/dev/null || echo "[kernel] WARN: Image.gz missing"
find "${KOUT}/arch/arm64/boot/dts" -name 'exynos9820-beyond2lte*.dtb' 2>/dev/null || true

if [[ "${USE_FRAGMENT}" = "1" ]]; then
    python3 "${NUXEL_ROOT}/tools/s10plus/verify-kernel-nfc.py" --build "${KOUT}" --quiet
    python3 "${NUXEL_ROOT}/tools/s10plus/verify-kernel-usbnet.py" --build "${KOUT}" --quiet
fi
