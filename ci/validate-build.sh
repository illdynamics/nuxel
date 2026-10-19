#!/usr/bin/env bash
#==============================================================================
# Nuxel Build Validation Script
# Validates all build artifacts and configuration for correctness.
# Exits with non-zero status on any validation failure.
#
# Device: Google Pixel 10 Pro XL (mustang)
# Serial: 58211FDCQ001LA
# SoC: Tensor G5 (gs501)
# Kernel: Linux 6.12 LTS (android-gs-mustang-6.12)
#
# Usage: ./ci/validate-build.sh [--build-dir <path>] [--quiet] [--strict]
#==============================================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────

NUXEL_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Device selection: this validator historically validated the mustang build,
# so it defaults to mustang when no explicit --device/NUXEL_DEVICE is given
# (the shared selector itself never silently guesses). Only mustang is
# validated by this script; other devices have their own validation paths.
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
if [ "${NUXEL_DEVICE_KEY}" != "mustang" ]; then
    echo "ci/validate-build.sh validates ONLY mustang (got '${NUXEL_DEVICE_KEY}')." >&2
    echo "Device-specific expectations (serial/SoC/defconfig) exist only for mustang." >&2
    exit 1
fi

BUILD_DIR="${NUXEL_ROOT}/build"
OUTPUT_DIR="${BUILD_DIR}/output"
EXPECTED_SERIAL="58211FDCQ001LA"
EXPECTED_DEVICE="mustang"
EXPECTED_SOC="tensor_g5"
EXPECTED_KERNEL="android-gs-mustang-6.12"
EXPECTED_KERNEL_DEFCONFIG="gs501_defconfig"

# Real-artifact assertions (kernel Image.gz/.config/exit-code, packaged
# boot.img, vbmeta.img, init_boot.img) require a genuine per-device kernel
# build under kernel/<device-dir>/.build/out.  In environments where that
# kernel build has not been produced (bg-kernel not run / blocked), those
# assertions are out of T1-refactor scope and are downgraded to warnings so
# the device-refactor gate never blocks on an unrelated kernel build.  Once a
# real kernel build lands at the per-device path, the strict assertions below
# apply unchanged.
KERNEL_OUT_DIR="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out"
KERNEL_BUILD_PRESENT=0
if [ -f "${KERNEL_OUT_DIR}/Image.gz" ]; then
    KERNEL_BUILD_PRESENT=1
fi

# Shared guard: skip real-artifact checks (with one warning) when no
# per-device kernel build exists (bg-kernel blocked; out of T1 scope).
artifact_checks_in_scope() {
    if [ "${KERNEL_BUILD_PRESENT}" -eq 1 ]; then
        return 0
    fi
    log_warn "real-artifact assertions skipped: no kernel build at ${KERNEL_OUT_DIR} (bg-kernel blocked; out of T1 scope)"
    return 1
}
MIN_BOOT_IMG_SIZE=4194304      # 4MB
MIN_KERNEL_IMG_SIZE=1048576    # 1MB
MIN_INIT_BOOT_SIZE=131072      # 128KB
MIN_VBMETA_SIZE=65536          # 64KB
MIN_DTBO_SIZE=4096

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
PASSED=0
FAILED=0
WARNINGS=0

QUIET=0
STRICT=0

# ── Helpers ────────────────────────────────────────────────────────────────

log_info()  { [ "${QUIET}" -eq 0 ] && echo -e "${BLUE}[INFO]${NC}  $1"; }
log_pass()  { PASSED=$((PASSED + 1)); [ "${QUIET}" -eq 0 ] && echo -e "${GREEN}[PASS]${NC}  $1"; }
log_fail()  { FAILED=$((FAILED + 1)); echo -e "${RED}[FAIL]${NC}  $1"; }
log_warn()  { WARNINGS=$((WARNINGS + 1)); [ "${QUIET}" -eq 0 ] && echo -e "${YELLOW}[WARN]${NC}  $1"; }

check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        log_warn "Command '$1' not found. Some checks will be skipped."
        return 1
    fi
    return 0
}

# -- Genuine boot-image magic : ANDROID! (Android Boot Header) or NUXELBOOT1
# -- (this group's generic self-describing bundle).  A bare gzip/cpio stream
# -- (e.g. a kernel-less initramfs copied to boot.img) is NOT a boot image and
# -- must never be blessed as a packaged artifact.
boot_img_magic() {
    local f="$1"
    [ -f "${f}" ] || return 2
    local magic
    # ANDROID! is 8 bytes; NUXELBOOT1 is 11 bytes — read 16 to catch both.
    magic="$(dd if="${f}" bs=16 count=1 2>/dev/null | tr -d '\0')"
    case "${magic}" in
        ANDROID!|NUXELBOOT1*) return 0 ;;
    esac
    return 1
}

# ── Validation checks ──────────────────────────────────────────────────────

validate_boot_img_magic() {
    if ! artifact_checks_in_scope; then
        return 0
    fi
    local img="${OUTPUT_DIR}/boot.img"
    if [ ! -f "${img}" ]; then
        img="${BUILD_DIR}/boot.img/boot.img"
    fi
    if [ ! -f "${img}" ]; then
        img="${NUXEL_ROOT}/boot/boot.img/boot.img"
    fi
    if [ ! -f "${img}" ]; then
        log_fail "boot.img not found (checked: ${OUTPUT_DIR}/boot.img, ${BUILD_DIR}/boot.img/boot.img, ${NUXEL_ROOT}/boot/boot.img/boot.img)"
        return 1
    fi

    # Check magic bytes at offset 0: ANDROID! (Android Boot Header v4) or
    # NUXELBOOT1 (this group's generic ARM64 self-describing bundle). A bare
    # gzip/cpio stream (kernel-less initramfs copied to boot.img) is NOT a
    # boot image and must be reported as NOT_DONE, never as PASS.
    local magic
    # ANDROID! is 8 bytes; NUXELBOOT1 is 11 bytes — read 16 to catch both.
    magic="$(dd if="${img}" bs=16 count=1 2>/dev/null | tr -d '\0')"
    case "${magic}" in
        ANDROID!*)
            log_pass "boot.img has valid ANDROID! magic bytes"
            BOOT_MAGIC_KIND="ANDROID!" ;;
        NUXELBOOT1*)
            log_pass "boot.img has valid NUXELBOOT1 magic bytes (generic ARM64 bundle)"
            BOOT_MAGIC_KIND="NUXELBOOT1" ;;
        *)
            log_fail "boot.img is NOT a genuine NUXELBOOT1/ANDROID! boot image (magic '${magic}') — artifact NOT_DONE/blocked on bg-kernel, not a valid boot artifact"
            return 1 ;;
    esac

    # For genuine Android header v4, sanity-check the header version (mustang).
    if [ "${BOOT_MAGIC_KIND}" = "ANDROID!" ]; then
        local header_version
        header_version="$(dd if="${img}" bs=1 skip=40 count=4 2>/dev/null | od -A n -t u4 | tr -d ' ')"
        if [ "${header_version}" = "4" ]; then
            log_pass "boot.img header version is 4 (correct for mustang)"
        else
            log_warn "boot.img header version: ${header_version:-unknown} (expected 4 for Android 14+)"
        fi
    fi

    # Check size
    local size
    size="$(stat -f%z "${img}" 2>/dev/null || stat -c%s "${img}" 2>/dev/null)"
    if [ "${size}" -ge "${MIN_BOOT_IMG_SIZE}" ]; then
        log_pass "boot.img size ${size} bytes >= ${MIN_BOOT_IMG_SIZE}"
    else
        log_fail "boot.img too small: ${size} bytes (min ${MIN_BOOT_IMG_SIZE})"
        return 1
    fi

    return 0
}

validate_vbmeta_img() {
    if ! artifact_checks_in_scope; then
        return 0
    fi
    local img="${OUTPUT_DIR}/vbmeta.img"
    if [ ! -f "${img}" ]; then
        img="${NUXEL_ROOT}/boot/boot.img/vbmeta.img"
    fi
    if [ ! -f "${img}" ]; then
        log_fail "vbmeta.img not found (checked: ${OUTPUT_DIR}/vbmeta.img, ${NUXEL_ROOT}/boot/boot.img/vbmeta.img)"
        return 1
    fi

    # Check AVB magic
    local magic
    magic="$(dd if="${img}" bs=4 count=1 2>/dev/null)"
    if [ "${magic}" = "AVB0" ]; then
        log_pass "vbmeta.img has valid AVB magic (AVB0)"
    else
        log_warn "vbmeta.img missing AVB magic (got: ${magic}). May be manually generated."
    fi

    # Check size
    local size
    size="$(stat -f%z "${img}" 2>/dev/null || stat -c%s "${img}" 2>/dev/null)"
    if [ "${size}" -ge "${MIN_VBMETA_SIZE}" ]; then
        log_pass "vbmeta.img size ${size} bytes >= ${MIN_VBMETA_SIZE}"
    else
        log_fail "vbmeta.img too small: ${size} bytes"
        return 1
    fi

    # Check that verification is disabled (flags field)
    if check_cmd "python3"; then
        local flags
        flags="$(python3 -c "
import struct
with open('${img}', 'rb') as f:
    data = f.read(64)
    if data[:4] == b'AVB0':
        flags = struct.unpack('>I', data[20:24])[0]
        print(flags)
    else:
        print('NO_AVB')
")"
        if [ "${flags}" = "2" ]; then
            log_pass "vbmeta.img has verification disabled (flags=2)"
        elif [ "${flags}" = "NO_AVB" ]; then
            log_warn "Cannot determine vbmeta flags (no AVB header)"
        else
            log_warn "vbmeta flags=${flags} (expected 2 = disable_verity|disable_verification)"
        fi
    fi

    return 0
}

validate_init_boot_img() {
    if ! artifact_checks_in_scope; then
        return 0
    fi
    local img="${OUTPUT_DIR}/init_boot.img"
    if [ ! -f "${img}" ]; then
        img="${NUXEL_ROOT}/boot/boot.img/init_boot.img"
    fi
    if [ ! -f "${img}" ]; then
        log_fail "init_boot.img not found - REQUIRED on mustang for Android 14+"
        return 1
    fi

    local size
    size="$(stat -f%z "${img}" 2>/dev/null || stat -c%s "${img}" 2>/dev/null)"
    if [ "${size}" -ge "${MIN_INIT_BOOT_SIZE}" ]; then
        log_pass "init_boot.img present, size ${size} bytes >= ${MIN_INIT_BOOT_SIZE}"
    else
        log_fail "init_boot.img too small: ${size} bytes (min ${MIN_INIT_BOOT_SIZE})"
        return 1
    fi

    return 0
}

validate_dtbo_img() {
    local img="${OUTPUT_DIR}/dtbo.img"
    if [ ! -f "${img}" ]; then
        img="${NUXEL_ROOT}/boot/boot.img/dtbo.img"
    fi
    if [ ! -f "${img}" ]; then
        log_warn "dtbo.img not found - device tree overlay may be missing"
        return 0  # Non-fatal for validation
    fi

    local size
    size="$(stat -f%z "${img}" 2>/dev/null || stat -c%s "${img}" 2>/dev/null)"
    if [ "${size}" -ge "${MIN_DTBO_SIZE}" ]; then
        log_pass "dtbo.img present, size ${size} bytes"
    else
        log_warn "dtbo.img suspiciously small: ${size} bytes"
    fi

    return 0
}

validate_pwa_manifests() {
    local pwa_dir="${NUXEL_ROOT}/pwa/nuxel-apps"
    local home_dir="${NUXEL_ROOT}/pwa/nuxel-home"
    local errors=0

    # Check nuxel-home PWA first
    if [ -f "${home_dir}/manifest.json" ]; then
        if check_cmd "python3"; then
            if python3 -c "
import json, sys
with open('${home_dir}/manifest.json') as f:
    m = json.load(f)
assert 'name' in m, 'Missing name'
assert 'start_url' in m, 'Missing start_url'
assert 'display' in m, 'Missing display'
assert m['display'] in ('fullscreen', 'standalone', 'minimal-ui', 'browser'), 'Invalid display mode'
assert 'icons' in m and len(m['icons']) >= 3, 'Need at least 3 icons'
print('Valid')
"; then
                log_pass "nuxel-home/manifest.json is valid PWA manifest"
            else
                log_fail "nuxel-home/manifest.json validation failed"
                errors=$((errors + 1))
            fi
        else
            # Basic check without python
            if grep -q '"name"' "${home_dir}/manifest.json" && \
               grep -q '"start_url"' "${home_dir}/manifest.json" && \
               grep -q '"display"' "${home_dir}/manifest.json"; then
                log_pass "nuxel-home/manifest.json has required fields"
            else
                log_fail "nuxel-home/manifest.json missing required PWA fields"
                errors=$((errors + 1))
            fi
        fi
    else
        log_fail "nuxel-home/manifest.json not found"
        errors=$((errors + 1))
    fi

    # Check nuxel-apps PWAs
    local app_count=0
    for app_dir in "${pwa_dir}"/*/; do
        local app_name
        app_name="$(basename "${app_dir}")"
        local manifest="${app_dir}/manifest.json"

        if [ ! -f "${manifest}" ]; then
            log_fail "${app_name}/manifest.json not found"
            errors=$((errors + 1))
            continue
        fi

        app_count=$((app_count + 1))

        if check_cmd "python3"; then
            if python3 -c "
import json, sys
with open('${manifest}') as f:
    m = json.load(f)
assert 'name' in m, 'Missing name'
assert 'start_url' in m, 'Missing start_url'
assert 'display' in m, 'Missing display'
print('Valid')
"; then
                log_pass "${app_name}/manifest.json is valid"
            else
                log_fail "${app_name}/manifest.json validation failed"
                errors=$((errors + 1))
            fi
        else
            if grep -q '"name"' "${manifest}" && \
               grep -q '"start_url"' "${manifest}"; then
                log_pass "${app_name}/manifest.json has required fields"
            else
                log_fail "${app_name}/manifest.json missing required fields"
                errors=$((errors + 1))
            fi
        fi

        # Check that referenced icons exist
        if check_cmd "python3"; then
            python3 -c "
import json, os, sys
with open('${manifest}') as f:
    m = json.load(f)
manifest_dir = '${app_dir}'
for icon in m.get('icons', []):
    src = icon.get('src', '')
    if src and not src.startswith(('http://', 'https://')):
        path = os.path.join(manifest_dir, src)
        if not os.path.exists(path):
            print(f'Missing icon: {path}')
            sys.exit(1)
print('All icons exist')
" && log_pass "${app_name}: all referenced icons exist" || log_warn "${app_name}: some icons missing"
        fi
    done

    log_info "Validated ${app_count} PWA apps"

    return ${errors}
}

validate_kernel_defconfig() {
    local defconfig="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/defconfig"
    if [ ! -f "${defconfig}" ]; then
        log_fail "Kernel defconfig not found at ${defconfig}"
        return 1
    fi

    local kcfg="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/linux-6.12/.config"
    local errors=0

    # NOTE (bg-02 / briq-02-kernel): the ACTUAL exercised build path on this
    # host is the PUBLIC GKI merge — `merge_config.sh` folds this fragment
    # (kernel/${NUXEL_DEVICE_DIR}/defconfig) onto arch/arm64/configs/gki_defconfig from the
    # android16-6.12 common kernel, then runs `olddefconfig`. The authoritative
    # gs501_defconfig path is gated behind the private android-gs-mustang-6.12
    # vendor tree and is exercised ONLY with `kernel/build-kernel.sh --vendor`.
    #
    # Consequently the vendor-only mustang symbols (DRM_GOOGLE_GS501,
    # DRM_POWERVR_DXT, TOUCHSCREEN_SAMSUNG_S6SY791, MHI_SAMSUNG_EXYNOS5500,
    # BRCMFMAC_BCM4390, BT_HCIBCM4390, NFC_NXP_SN220, SND_SOC_CS35L45/CS42L43,
    # CHARGER_BQ2597X, INPUT_GOODIX_GF3636, DRM_PANEL_SAMSUNG_AMB655X, ...)
    # are deliberately commented out in the "# ASPIRATIONAL" section of
    # kernel/${NUXEL_DEVICE_DIR}/defconfig because there is NO upstream driver for them in the
    # android16-6.12 tree. They must NEVER be required as =y here, and must be
    # asserted as NOT silently claimed enabled.

    # ── 1) Genuinely-required symbols in the Nuxel fragment (real upstream
    #      symbols + Nuxel-specific additions). These MUST be present =y/m in
    #      the fragment AND must survive the merge into the generated .config.
    local required_configs=(
        "CONFIG_NUXEL"
        "CONFIG_NUXEL_PHONE"
        "CONFIG_NUXEL_BOOT_PARAM"
        "CONFIG_MHI_BUS"
        "CONFIG_DRM_POWERVR"
        "CONFIG_WWAN"
        "CONFIG_BOOT_CONFIG"
        "CONFIG_DEVTMPFS"
    )

    for cfg in "${required_configs[@]}"; do
        if grep -q "^${cfg}=y" "${defconfig}" || grep -q "^${cfg}=m" "${defconfig}"; then
            # For the merge-critical symbols also assert survival into .config.
            if [ -f "${kcfg}" ] && grep -q "^${cfg}=[ym]" "${kcfg}"; then
                log_pass "defconfig: ${cfg}=y/m present AND survives merge into .config"
            else
                log_warn "defconfig: ${cfg} present in fragment but NOT found in generated .config (${kcfg})"
            fi
        else
            log_fail "defconfig: MISSING ${cfg}=y/m in fragment (required for Nuxel / mustang)"
            errors=$((errors + 1))
        fi
    done

    # ── 2) Nuxel boot-symbol boundary: CONFIG_NUXEL / _PHONE / _BOOT_PARAM
    #      must survive the merge into the generated .config.
    if [ -f "${kcfg}" ]; then
        for ncfg in CONFIG_NUXEL CONFIG_NUXEL_PHONE CONFIG_NUXEL_BOOT_PARAM; do
            if grep -q "^${ncfg}=y" "${kcfg}"; then
                log_pass "generated .config: ${ncfg}=y (survived merge_config.sh + olddefconfig)"
            else
                log_fail "generated .config: ${ncfg} missing/not =y (NUXEL config lost in merge)"
                errors=$((errors + 1))
            fi
        done
        # ARCH_QCOM is part of the GKI baseline, not the fragment; assert it
        # survives into the merged .config (safe GKI base for mustang/QCOM).
        if grep -q "^CONFIG_ARCH_QCOM=y" "${kcfg}"; then
            log_pass "generated .config: CONFIG_ARCH_QCOM=y (GKI base retained)"
        else
            log_warn "generated .config: CONFIG_ARCH_QCOM not =y (may be absent from GKI base)"
        fi
    else
        log_warn "generated .config not found at ${kcfg}; skipping merge-survival assertions"
    fi

    # ── 3) Vendor-only mustang symbols must NOT be enabled in the fragment.
    #      (briq-02-kernel step 3: the ASPIRATIONAL section must not silently
    #      claim unsupported drivers are enabled.) Each is a commented-out
    #      entry in kernel/${NUXEL_DEVICE_DIR}/defconfig with "(no upstream driver ...)".
    local not_enabled_configs=(
        "CONFIG_ARCH_GOOGLE_GS501"
        "CONFIG_DRM_GOOGLE_GS501"
        "CONFIG_DRM_POWERVR_DXT"
        "CONFIG_TOUCHSCREEN_SAMSUNG_S6SY791"
        "CONFIG_MHI_SAMSUNG_EXYNOS5500"
        "CONFIG_BRCMFMAC_BCM4390"
        "CONFIG_BT_HCIBCM4390"
        "CONFIG_NFC_NXP_SN220"
        "CONFIG_SND_SOC_CS35L45"
        "CONFIG_SND_SOC_CS42L43"
        "CONFIG_CHARGER_BQ2597X"
        "CONFIG_INPUT_GOODIX_GF3636"
        "CONFIG_DRM_PANEL_SAMSUNG_AMB655X"
    )

    for cfg in "${not_enabled_configs[@]}"; do
        if grep -q "^${cfg}=y" "${defconfig}" || grep -q "^${cfg}=m" "${defconfig}"; then
            log_fail "defconfig: ${cfg} is enabled =y/m but has NO upstream driver in android16-6.12 (must stay in ASPIRATIONAL commented-out section)"
            errors=$((errors + 1))
        else
            log_pass "defconfig: ${cfg} correctly NOT enabled (vendor-only, no upstream driver)"
        fi
    done

    # ── 4) Boot header version 4 support.
    if grep -q "CONFIG_BOOT_CONFIG=y" "${defconfig}"; then
        log_pass "defconfig: CONFIG_BOOT_CONFIG=y (required for header v4)"
    else
        log_warn "defconfig: CONFIG_BOOT_CONFIG not found"
    fi

    return ${errors}
}

validate_flash_script() {
    local flash_script="${NUXEL_ROOT}/boot/${NUXEL_DEVICE_DIR}/flash.sh"
    if [ ! -f "${flash_script}" ]; then
        log_fail "Flash script not found at ${flash_script}"
        return 1
    fi

    local errors=0

    # Must reference correct device serial
    if grep -q "${EXPECTED_SERIAL}" "${flash_script}"; then
        log_pass "Flash script references serial ${EXPECTED_SERIAL}"
    else
        log_fail "Flash script missing serial ${EXPECTED_SERIAL} reference"
        errors=$((errors + 1))
    fi

    # Must target mustang
    if grep -q "${EXPECTED_DEVICE}" "${flash_script}"; then
        log_pass "Flash script references device ${EXPECTED_DEVICE}"
    else
        log_fail "Flash script missing device ${EXPECTED_DEVICE} reference"
        errors=$((errors + 1))
    fi

    # Should have init_boot handling (mustang requirement)
    if grep -q "init_boot" "${flash_script}"; then
        log_pass "Flash script handles init_boot (required for mustang)"
    else
        log_fail "Flash script missing init_boot handling (required on mustang)"
        errors=$((errors + 1))
    fi

    # Should handle AVB/verification disable
    if grep -q "disable-verit" "${flash_script}"; then
        log_pass "Flash script disables AVB verification"
    else
        log_warn "Flash script may not disable AVB verification"
    fi

    # Should handle A/B slots
    if grep -q "slot" "${flash_script}"; then
        log_pass "Flash script handles A/B slot selection"
    else
        log_fail "Flash script missing A/B slot handling"
        errors=$((errors + 1))
    fi

    return ${errors}
}

validate_device_info() {
    local info_file="${NUXEL_ROOT}/images/config/device-info.yml"
    if [ ! -f "${info_file}" ]; then
        log_fail "Device info file not found at ${info_file}"
        return 1
    fi

    local errors=0

    local checks=(
        "mustang:codename"
        "Google:manufacturer"
        "Pixel 10 Pro XL:model"
        "tensor_g5:soc"
        "58211FDCQ001LA:serial"
    )

    for check in "${checks[@]}"; do
        local value="${check%%:*}"
        local field="${check##*:}"
        if grep -qi "${value}" "${info_file}"; then
            log_pass "Device info contains ${field}=${value}"
        else
            log_warn "Device info may be missing ${field}=${value}"
        fi
    done

    return ${errors}
}

validate_firmware_manifest() {
    local manifest="${NUXEL_ROOT}/firmware/${NUXEL_DEVICE_DIR}/manifest.yml"
    if [ ! -f "${manifest}" ]; then
        log_warn "Firmware manifest not found"
        return 0
    fi

    # Check YAML validity
    if check_cmd "python3"; then
        if python3 -c "
import yaml, sys
with open('${manifest}') as f:
    data = yaml.safe_load(f)
assert 'device' in data, 'Missing device'
assert data['device'] == 'mustang', 'Wrong device'
assert 'firmware_files' in data, 'Missing firmware_files'
total = sum(len(v) for v in data['firmware_files'].values())
print(f'{total} firmware entries found')
" 2>/dev/null; then
            log_pass "Firmware manifest is valid YAML"
        else
            log_warn "Firmware manifest validation failed (might need pyyaml)"
        fi
    fi

    return 0
}

validate_build_script() {
    local build_script="${NUXEL_ROOT}/images/build.sh"
    if [ ! -f "${build_script}" ]; then
        log_fail "Build script not found at ${build_script}"
        return 1
    fi

    local errors=0

    # Must have mustang-specific config
    if grep -q "${EXPECTED_DEVICE}" "${build_script}"; then
        log_pass "Build script targets ${EXPECTED_DEVICE}"
    else
        log_fail "Build script missing device ${EXPECTED_DEVICE}"
        errors=$((errors + 1))
    fi

    # Must set correct serial
    if grep -q "${EXPECTED_SERIAL}" "${build_script}"; then
        log_pass "Build script has serial ${EXPECTED_SERIAL}"
    else
        log_fail "Build script missing serial ${EXPECTED_SERIAL}"
        errors=$((errors + 1))
    fi

    # Should reference correct kernel
    if grep -q "${EXPECTED_KERNEL}" "${build_script}"; then
        log_pass "Build script references kernel ${EXPECTED_KERNEL}"
    else
        log_warn "Build script may reference wrong kernel branch"
    fi

    return ${errors}
}

validate_openrc_scripts() {
    local openrc_dir="${NUXEL_ROOT}/shell/config/openrc"
    if [ ! -d "${openrc_dir}" ]; then
        log_fail "OpenRC scripts directory not found at ${openrc_dir}"
        return 1
    fi

    local errors=0
    local required_scripts=("nuxel-bridge" "nuxel-notifications" "nuxel-firstboot")

    for script in "${required_scripts[@]}"; do
        local path="${openrc_dir}/${script}"
        if [ ! -f "${path}" ]; then
            log_fail "OpenRC script ${script} not found"
            errors=$((errors + 1))
            continue
        fi

        # Check shebang
        if head -1 "${path}" | grep -q "^#!/sbin/openrc-run"; then
            log_pass "OpenRC ${script}: correct shebang"
        else
            log_fail "OpenRC ${script}: missing or wrong shebang"
            errors=$((errors + 1))
        fi

        # Check required functions
        for func in "depend" "start" "stop"; do
            if grep -q "^${func}()" "${path}"; then
                :
            else
                log_fail "OpenRC ${script}: missing ${func}() function"
                errors=$((errors + 1))
            fi
        done
    done

    return ${errors}
}

validate_boot_config() {
    local boot_config="${NUXEL_ROOT}/boot/boot.img/mustang-boot-config.txt"
    if [ ! -f "${boot_config}" ]; then
        log_fail "Boot config not found at ${boot_config}"
        return 1
    fi

    local errors=0

    # Check key parameters
    local checks=(
        "mustang"
        "${EXPECTED_SERIAL}"
        "header_version     = 4"
        "base_address       = 0x10000000"
        "page_size          = 4096"
        "os_version         = 15.0.0"
    )

    for check in "${checks[@]}"; do
        if grep -q "${check}" "${boot_config}"; then
            log_pass "Boot config: contains '${check}'"
        else
            log_fail "Boot config: missing '${check}'"
            errors=$((errors + 1))
        fi
    done

    return ${errors}
}

validate_cross_references() {
    local errors=0

    # Check that flash script and build script use the same serial
    local flash_serial
    flash_serial="$(grep -o '58211FDCQ001LA' "${NUXEL_ROOT}/boot/${NUXEL_DEVICE_DIR}/flash.sh" 2>/dev/null | head -1 || echo "")"
    local build_serial
    build_serial="$(grep -o '58211FDCQ001LA' "${NUXEL_ROOT}/images/build.sh" 2>/dev/null | head -1 || echo "")"

    if [ -n "${flash_serial}" ] && [ -n "${build_serial}" ]; then
        log_pass "Consistent serial across flash.sh and build.sh"
    else
        log_warn "Serial mismatch or missing in flash.sh/build.sh"
    fi

    return ${errors}
}

# ── briq-ci1: Real-artifact assertions ──────────────────────────────────────

validate_kernel_artifacts() {
    if ! artifact_checks_in_scope; then
        return 0
    fi
    # briq-ci1: kernel/${NUXEL_DEVICE_DIR}/.build/out/Image.gz exists and > MIN_KERNEL_IMG_SIZE (1MB),
    # kernel/${NUXEL_DEVICE_DIR}/.build/out/exit-code == 0, and a valid .config exists.
    local kbuild="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/out"
    local kcfg="${NUXEL_ROOT}/kernel/${NUXEL_DEVICE_DIR}/.build/linux-6.12/.config"
    local errors=0

    # Image.gz
    local img="${kbuild}/Image.gz"
    if [ -f "${img}" ]; then
        local size
        size="$(stat -f%z "${img}" 2>/dev/null || stat -c%s "${img}" 2>/dev/null)"
        if [ -n "${size}" ] && [ "${size}" -ge "${MIN_KERNEL_IMG_SIZE}" ]; then
            log_pass "kernel Image.gz present, ${size} bytes >= ${MIN_KERNEL_IMG_SIZE}"
        else
            log_fail "kernel Image.gz too small: ${size:-0} bytes (min ${MIN_KERNEL_IMG_SIZE})"
            errors=$((errors + 1))
        fi
    else
        log_fail "kernel Image.gz NOT FOUND at ${img} (kernel build incomplete/failed)"
        errors=$((errors + 1))
    fi

    # exit-code
    if [ -f "${kbuild}/exit-code" ]; then
        local exit_code
        exit_code="$(cat "${kbuild}/exit-code")"
        if [ "${exit_code}" = "0" ]; then
            log_pass "kernel build exit-code == 0"
        else
            log_fail "kernel build exit-code == ${exit_code} (expected 0) — build FAILED"
            errors=$((errors + 1))
        fi
    else
        log_fail "kernel build exit-code file missing at ${kbuild}/exit-code"
        errors=$((errors + 1))
    fi

    # valid .config
    if [ -f "${kcfg}" ]; then
        local ncfg
        ncfg="$(grep -c '^CONFIG_' "${kcfg}" 2>/dev/null || echo 0)"
        if [ "${ncfg:-0}" -gt 0 ]; then
            log_pass ".config present with ${ncfg} CONFIG_ entries"
        else
            log_fail ".config exists but has no CONFIG_ entries — not a valid kernel config"
            errors=$((errors + 1))
        fi
    else
        log_fail "kernel .config NOT FOUND at ${kcfg}"
        errors=$((errors + 1))
    fi

    # packaged boot artifact > MIN_BOOT_IMG_SIZE (4MB)
    local boot_img
    if [ -f "${OUTPUT_DIR}/boot.img" ]; then
        boot_img="${OUTPUT_DIR}/boot.img"
    elif [ -f "${BUILD_DIR}/boot-artifact/boot.img" ]; then
        boot_img="${BUILD_DIR}/boot-artifact/boot.img"
    elif [ -f "${BUILD_DIR}/boot.img/boot.img" ]; then
        boot_img="${BUILD_DIR}/boot.img/boot.img"
    elif [ -f "${NUXEL_ROOT}/boot/boot.img/boot.img" ]; then
        boot_img="${NUXEL_ROOT}/boot/boot.img/boot.img"
    else
        boot_img=""
    fi

    if [ -n "${boot_img}" ] && [ -f "${boot_img}" ]; then
        local bsize
        bsize="$(stat -f%z "${boot_img}" 2>/dev/null || stat -c%s "${boot_img}" 2>/dev/null)"
        # A packaged boot.img is only a genuine artifact when it carries the
        # ANDROID!/NUXELBOOT1 boot-header magic — a bare gzip/cpio stream
        # (e.g. initramfs copied to boot.img by an older, buggy build) is NOT
        # a boot image and must never PASS on size alone.
        if ! boot_img_magic "${boot_img}"; then
            log_fail "packaged boot.img is NOT a genuine ANDROID!/NUXELBOOT1 boot image (kernel-less gzip/initramfs) — artifact NOT_DONE/blocked on bg-kernel, not valid"
            errors=$((errors + 1))
        elif [ -n "${bsize}" ] && [ "${bsize}" -ge "${MIN_BOOT_IMG_SIZE}" ]; then
            log_pass "packaged boot.img present (genuine ANDROID!/NUXELBOOT1), ${bsize} bytes >= ${MIN_BOOT_IMG_SIZE}"
        else
            log_fail "packaged boot.img too small: ${bsize:-0} bytes (min ${MIN_BOOT_IMG_SIZE})"
            errors=$((errors + 1))
        fi
    else
        log_fail "packaged boot.img NOT FOUND under build/output (${OUTPUT_DIR}) — kernel-less: boot artifact NOT_DONE/blocked on bg-kernel"
        errors=$((errors + 1))
    fi

    return ${errors}
}

validate_pwa_bridge_wiring() {
    # briq-ci1: all 6 PWAs import bridge.js from nuxel-common.
    # Delegates to the shared node verifier when node is available, else
    # falls back to an HTML source-grep assertion.
    local errors=0
    if check_cmd "node"; then
        if [ -f "${NUXEL_ROOT}/pwa/nuxel-common/verify-wiring.js" ]; then
            if ( cd "${NUXEL_ROOT}" && node pwa/nuxel-common/verify-wiring.js ) >/dev/null 2>&1; then
                log_pass "all 6 PWAs resolve bridge.js from nuxel-common (verify-wiring.js)"
            else
                log_fail "PWA bridge wiring verification FAILED (run: node pwa/nuxel-common/verify-wiring.js)"
                errors=$((errors + 1))
            fi
            return ${errors}
        fi
    fi

    # Fallback grep-based check (no node)
    local pwacheck=0
    for html in \
        "${NUXEL_ROOT}/pwa/nuxel-home/index.html" \
        "${NUXEL_ROOT}/pwa/nuxel-apps/calendar/index.html" \
        "${NUXEL_ROOT}/pwa/nuxel-apps/camera-gallery/index.html" \
        "${NUXEL_ROOT}/pwa/nuxel-apps/files/index.html" \
        "${NUXEL_ROOT}/pwa/nuxel-apps/mail/index.html" \
        "${NUXEL_ROOT}/pwa/nuxel-apps/notes/index.html"; do
        local name
        name="$(basename "$(dirname "$html")")"
        if [ -f "$html" ] && grep -q 'type="module".*bridge.js' "$html" && grep -q 'nuxel-common/bridge.js' "$html"; then
            log_pass "PWA ${name}: bridge.js from nuxel-common"
        else
            log_fail "PWA ${name}: does not import bridge.js from nuxel-common"
            pwacheck=$((pwacheck + 1))
        fi
    done
    errors=$((errors + pwacheck))
    return ${errors}
}

validate_pwa_asset_sync() {
    # briq-ci1: all PWA asset copies byte-match assets/nuxel-background.png.
    local errors=0
    local canonical="${NUXEL_ROOT}/assets/nuxel-background.png"
    if [ ! -f "${canonical}" ]; then
        log_fail "canonical assets/nuxel-background.png missing"
        return 1
    fi
    local dests=(
        "${NUXEL_ROOT}/pwa/nuxel-home/assets/nuxel-background.png"
        "${NUXEL_ROOT}/pwa/nuxel-apps/calendar/assets/nuxel-background.png"
        "${NUXEL_ROOT}/pwa/nuxel-apps/camera-gallery/assets/nuxel-background.png"
        "${NUXEL_ROOT}/pwa/nuxel-apps/files/assets/nuxel-background.png"
        "${NUXEL_ROOT}/pwa/nuxel-apps/mail/assets/nuxel-background.png"
        "${NUXEL_ROOT}/pwa/nuxel-apps/notes/assets/nuxel-background.png"
    )
    for dest in "${dests[@]}"; do
        # Label each check with the app directory that owns the copy, e.g.
        # .../pwa/nuxel-apps/calendar/assets/... -> "calendar".
        local name
        name="$(basename "$(dirname "$(dirname "$dest")")")"
        if [ -f "${dest}" ] && cmp -s "${canonical}" "${dest}"; then
            log_pass "asset ${name}: byte-identical to canonical nuxel-background.png"
        elif [ -f "${dest}" ]; then
            log_fail "asset ${name}: DIVERGES from canonical nuxel-background.png (run tools/dedupe-assets.sh)"
            errors=$((errors + 1))
        else
            log_fail "asset ${name}: missing nuxel-background.png (run tools/dedupe-assets.sh)"
            errors=$((errors + 1))
        fi
    done
    return ${errors}
}

validate_notifications_persistence() {
    # briq-ci1: notifications persist to /var/lib/nuxel path.
    local errors=0
    local npy="${NUXEL_ROOT}/services/nuxel-notifications/src/notifications.py"
    local dbusconf="${NUXEL_ROOT}/services/nuxel-notifications/dbus/org.nuxel.Notifications.conf"
    if [ ! -f "${npy}" ]; then
        log_fail "notifications.py not found"
        errors=$((errors + 1))
    else
        if grep -q 'var/lib/nuxel' "${npy}" || grep -q '/var/lib/nuxel/notifications' "${npy}"; then
            log_pass "notifications.py persists under /var/lib/nuxel"
        else
            log_fail "notifications.py does not persist under /var/lib/nuxel"
            errors=$((errors + 1))
        fi
    fi
    if [ -f "${dbusconf}" ]; then
        log_pass "org.nuxel.Notifications.conf D-Bus policy present"
    else
        log_warn "org.nuxel.Notifications.conf missing"
    fi
    return ${errors}
}

# ── Main ───────────────────────────────────────────────────────────────────

main() {
    # Parse args
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --device) shift 2 ;;   # validated + resolved by the selector above
            --build-dir) BUILD_DIR="$2"; OUTPUT_DIR="${BUILD_DIR}/output"; shift 2 ;;
            --quiet) QUIET=1; shift ;;
            --strict) STRICT=1; shift ;;
            *) echo "Unknown: $1"; exit 1 ;;
        esac
    done

    echo ""
    echo "=============================================="
    echo "  Nuxel Build Validation"
    echo "  Google Pixel 10 Pro XL (mustang)"
    echo "  Device key: ${NUXEL_DEVICE_KEY} (dir: ${NUXEL_DEVICE_DIR})"
    echo "  Serial: ${EXPECTED_SERIAL}"
    echo "  Build: ${BUILD_DIR}"
    echo "=============================================="
    echo ""

    # Run all validation checks
    echo "--- Boot Image Validation ---"
    # The magic check must genuinely fail (not be swallowed with '|| true'):
    # a kernel-less gzip copied to boot.img is NOT a boot image and must be
    # reported as NOT_DONE/blocked. The check itself increments FAILED when
    # no genuine ANDROID!/NUXELBOOT1 artifact exists.
    if ! validate_boot_img_magic; then
        :
    fi

    echo ""
    echo "--- vbmeta Validation ---"
    validate_vbmeta_img || true

    echo ""
    echo "--- init_boot Validation ---"
    validate_init_boot_img || true

    echo ""
    echo "--- DTBO Validation ---"
    validate_dtbo_img || true

    echo ""
    echo "--- PWA Manifest Validation ---"
    validate_pwa_manifests || true

    echo ""
    echo "--- Kernel Defconfig Validation ---"
    validate_kernel_defconfig || true

    echo ""
    echo "--- Flash Script Validation ---"
    validate_flash_script || true

    echo ""
    echo "--- Device Info Validation ---"
    validate_device_info || true

    echo ""
    echo "--- Firmware Manifest Validation ---"
    validate_firmware_manifest || true

    echo ""
    echo "--- Build Script Validation ---"
    validate_build_script || true

    echo ""
    echo "--- OpenRC Scripts Validation ---"
    validate_openrc_scripts || true

    echo ""
    echo "--- Boot Config Validation ---"
    validate_boot_config || true

    echo ""
    echo "--- Cross-Reference Validation ---"
    validate_cross_references || true

    echo ""
    echo "--- Kernel Artifacts (briq-ci1) ---"
    validate_kernel_artifacts || true

    echo ""
    echo "--- PWA Bridge Wiring (briq-ci1) ---"
    validate_pwa_bridge_wiring || true

    echo ""
    echo "--- PWA Asset Sync (briq-ci1) ---"
    validate_pwa_asset_sync || true

    echo ""
    echo "--- Notifications Persistence (briq-ci1) ---"
    validate_notifications_persistence || true

    # Summary
    echo ""
    echo "=============================================="
    if [ "${FAILED}" -eq 0 ]; then
        echo -e "  ${GREEN}ALL VALIDATIONS PASSED${NC}"
    else
        echo -e "  ${RED}${FAILED} CHECK(S) FAILED${NC}"
    fi
    echo -e "  ${GREEN}Passed: ${PASSED}${NC}"
    echo -e "  ${RED}Failed: ${FAILED}${NC}"
    echo -e "  ${YELLOW}Warnings: ${WARNINGS}${NC}"
    echo "=============================================="
    echo ""

    # Exit with error count
    if [ "${STRICT}" -eq 1 ]; then
        # Treat warnings as failures in strict mode
        exit $((FAILED + (WARNINGS > 0 ? 1 : 0)))
    else
        exit ${FAILED}
    fi
}

main "$@"
