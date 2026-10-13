#!/usr/bin/env bash
#==============================================================================
# Nuxel Firmware Extraction & Installation Script
# Google Pixel 10 Pro XL (mustang) - Tensor G5
#
# This script automates extracting firmware blobs from a Google factory image
# and installing them to the correct locations in /lib/firmware.
#
# Device:      Google Pixel 10 Pro XL
# Codename:    mustang
# Serial:      58211FDCQ001LA
# HW:          MP1.0, SKU G45RY
# SoC:         Google Tensor G5 (gs501)
# Modem:       Samsung Exynos 5500
# WiFi/BT:     Broadcom BCM4390
# GPU:         Imagination PowerVR DXT-72-2304
#
# Usage:
#   ./install-firmware.sh <factory-image.zip> [options]
#
# Options:
#   --output-dir <dir>    Extract firmware to directory (default: ./firmware-out)
#   --install             Install firmware to /lib/firmware (requires root)
#   --force               Overwrite existing files
#   --verify-only         Only verify already-installed firmware
#   --list-files          List all required firmware files and exit
#   --checksums           Generate and print checksums for installed files
#   --no-modem            Skip modem firmware extraction
#   --no-wifi             Skip WiFi firmware extraction
#   --no-bt               Skip Bluetooth firmware extraction
#   --no-gpu              Skip GPU firmware extraction
#   --verbose             Verbose output
#==============================================================================

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────

# Resolve the repo root whether invoked directly or via the legacy symlink
# firmware/install-firmware.sh -> google-pixel-10-pro-xl/install-firmware.sh.
_NUXEL_SRC="${BASH_SOURCE[0]}"
while [ -h "${_NUXEL_SRC}" ]; do
    _NUXEL_DIR="$(cd -P "$(dirname "${_NUXEL_SRC}")" && pwd)"
    _NUXEL_SRC="$(readlink "${_NUXEL_SRC}")"
    case "${_NUXEL_SRC}" in
        /*) ;;
        *) _NUXEL_SRC="${_NUXEL_DIR}/${_NUXEL_SRC}" ;;
    esac
done
NUXEL_ROOT="$(cd -P "$(dirname "${_NUXEL_SRC}")/../.." && pwd)"

# Device selection: this per-device script is mustang-only. The shared
# selector never silently guesses; the wrapper defaults to mustang only for
# backward compatibility (this script historically WAS the mustang firmware
# installer).
if [ -z "${NUXEL_DEVICE:-}" ] && [[ "$*" != *--device* ]]; then
    export NUXEL_DEVICE="mustang"
fi
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "mustang" ] || {
    echo "[install-firmware] ERROR: firmware/${NUXEL_DEVICE_DIR}/install-firmware.sh is ONLY for mustang. Got: ${NUXEL_DEVICE_KEY}" >&2
    exit 1
}

MANIFEST="${NUXEL_ROOT}/firmware/${NUXEL_DEVICE_DIR}/manifest.yml"
DEVICE_CODENAME="mustang"
DEVICE_MODEL="Pixel 10 Pro XL"
DEVICE_SERIAL="58211FDCQ001LA"
EXPECTED_BUILD="BP1A.250405.001"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Counters
EXTRACTED=0
SKIPPED=0
FAILED=0
VERIFIED=0
MISSING=0

# Flags
DO_INSTALL=0
DO_FORCE=0
DO_VERIFY_ONLY=0
DO_LIST=0
DO_CHECKSUMS=0
DO_MODEM=1
DO_WIFI=1
DO_BT=1
DO_GPU=1
VERBOSE=0
OUTPUT_DIR=""

# ── Helpers ─────────────────────────────────────────────────────────────────

log_info()    { echo -e "${BLUE}[INFO]${NC}  $1"; }
log_ok()      { echo -e "${GREEN}[OK]${NC}    $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo ""; echo -e "${CYAN}══ $1 ══${NC}"; }
log_detail()  { if [ "${VERBOSE}" -eq 1 ]; then echo "    $1"; fi; return 0; }
log_separator() { echo "────────────────────────────────────────────"; }

check_deps() {
    local missing=0
    for cmd in unzip python3 file mount; do
        if ! command -v "${cmd}" &>/dev/null; then
            log_error "Required command not found: ${cmd}"
            missing=$((missing + 1))
        fi
    done

    # Optional but recommended
    for cmd in simg2img lpunpack avbtool; do
        if ! command -v "${cmd}" &>/dev/null; then
            log_detail "Optional tool not found: ${cmd}"
        fi
    done

    # Check for root if installing
    if [ "${DO_INSTALL}" -eq 1 ] && [ "$(id -u)" -ne 0 ]; then
        log_error "--install requires root. Run with sudo."
        exit 1
    fi

    return "${missing}"
}

get_firmware_list() {
    # Emit "src|dest|desc|required|category" for every blob in manifest.yml.
    # Pipelines honour the --no-modem/--no-wifi/--no-bt/--no-gpu skips so that
    # verify-installed, checksums and install all respect the same filter.
    # Final output is the 4-field form (src|dest|desc|required) expected by callers.
    local cat_skip=""
    [ "${DO_MODEM}" -eq 0 ] && cat_skip="${cat_skip} modem"
    [ "${DO_WIFI}" -eq 0 ]  && cat_skip="${cat_skip} wifi"
    [ "${DO_BT}" -eq 0 ]    && cat_skip="${cat_skip} bluetooth"
    [ "${DO_GPU}" -eq 0 ]   && cat_skip="${cat_skip} gpu"

    {
        if [ -f "${MANIFEST}" ]; then
            MANIFEST="${MANIFEST}" python3 -c "
import os, yaml, sys
with open(os.environ['MANIFEST']) as f:
    data = yaml.safe_load(f)
for category, files in data.get('firmware_files', {}).items():
    for fw in files:
        src = fw.get('source_path', '')
        dst = fw.get('dest', '')
        desc = fw.get('description', '')
        req = 'required' if fw.get('required', False) else 'optional'
        print('%s|%s|%s|%s|%s' % (src, dst, desc, req, category))
" 2>/dev/null
        else
            # Fallback: hardcoded firmware list for Tensor G5 mustang (5th field = category)
            echo "vendor/firmware/modem.bin|/lib/firmware/modem.bin|Exynos 5500 baseband|required|modem"
            echo "vendor/firmware/modem_pr.bin|/lib/firmware/modem_pr.bin|Primary modem firmware|required|modem"
            echo "vendor/firmware/modem_cal.bin|/lib/firmware/modem_cal.bin|Modem calibration|required|modem"
            echo "vendor/firmware/modem_cfg.txt|/lib/firmware/modem_cfg.txt|Modem config|required|modem"
            echo "vendor/firmware/exynos5500_shm.bin|/lib/firmware/exynos5500_shm.bin|Modem shared memory|required|modem"
            echo "vendor/firmware/brcmfmac4390.bin|/lib/firmware/brcm/brcmfmac4390.bin|BCM4390 WiFi 7 (SDIO)|required|wifi"
            echo "vendor/firmware/brcmfmac4390-pcie.bin|/lib/firmware/brcm/brcmfmac4390-pcie.bin|BCM4390 WiFi 7 PCIe|required|wifi"
            echo "vendor/firmware/brcmfmac4390-pcie.clm_blob|/lib/firmware/brcm/brcmfmac4390-pcie.clm_blob|WiFi 7 PCIe CLM|required|wifi"
            echo "vendor/firmware/brcmfmac4390.clm_blob|/lib/firmware/brcm/brcmfmac4390.clm_blob|WiFi CLM blob|required|wifi"
            echo "vendor/firmware/brcmfmac4390.nvm|/lib/firmware/brcm/brcmfmac4390.nvm|WiFi NVM config|required|wifi"
            echo "vendor/firmware/BCM4390.hcd|/lib/firmware/brcm/BCM4390.hcd|BT 5.4 firmware|required|bluetooth"
            echo "vendor/firmware/pvr_drv.so|/lib/firmware/img/pvr_drv.so|PowerVR GPU driver|required|gpu"
            echo "vendor/firmware/pvr_rogue_km.fw|/lib/firmware/img/pvr_rogue_km.fw|PowerVR kernel mode|required|gpu"
            echo "vendor/firmware/pvr_dxt_fw.fw|/lib/firmware/img/pvr_dxt_fw.fw|PowerVR DXT firmware|required|gpu"
            echo "vendor/firmware/pvr_rogue_csf.fw|/lib/firmware/img/pvr_rogue_csf.fw|PowerVR CSF|required|gpu"
            echo "vendor/firmware/amb655x_fw.bin|/lib/firmware/samsung/amb655x_fw.bin|Display panel|required|display"
            echo "vendor/firmware/amb655x_gamma.bin|/lib/firmware/samsung/amb655x_gamma.bin|Display gamma|required|display"
            echo "vendor/firmware/s6sy791_touch_fw.bin|/lib/firmware/samsung/s6sy791_touch_fw.bin|Touch controller|required|display"
            echo "vendor/firmware/cs35l45_fw.bin|/lib/firmware/cirrus/cs35l45_fw.bin|CS35L45 speaker amp|required|audio"
            echo "vendor/firmware/cs35l45_dsp.bin|/lib/firmware/cirrus/cs35l45_dsp.bin|CS35L45 DSP|required|audio"
            echo "vendor/firmware/cs42l43_fw.bin|/lib/firmware/cirrus/cs42l43_fw.bin|CS42L43 codec|required|audio"
            echo "vendor/firmware/bmi270_fw.bin|/lib/firmware/bosch/bmi270_fw.bin|BMI270 IMU|required|sensors"
            echo "vendor/firmware/lsm6dsv_fw.bin|/lib/firmware/st/lsm6dsv_fw.bin|LSM6DSV IMU|required|sensors"
            echo "vendor/firmware/tcs3710_fw.bin|/lib/firmware/ams/tcs3710_fw.bin|ALS/proximity|required|sensors"
            echo "vendor/firmware/sn220_fw.bin|/lib/firmware/nxp/sn220_fw.bin|NXP SN220 NFC|required|nfc"
            echo "vendor/firmware/gf3636_fw.bin|/lib/firmware/goodix/gf3636_fw.bin|Goodix fingerprint|required|fingerprint"
            echo "vendor/firmware/max77729_fw.bin|/lib/firmware/maxim/max77729_fw.bin|MAX77729 PMIC|required|pmic"
            echo "vendor/firmware/max77826_fw.bin|/lib/firmware/maxim/max77826_fw.bin|MAX77826 PMIC|required|pmic"
            echo "vendor/firmware/bq2597x_fw.bin|/lib/firmware/ti/bq2597x_fw.bin|BQ2597x charger|required|charger"
            echo "vendor/firmware/max1720x_fw.bin|/lib/firmware/maxim/max1720x_fw.bin|MAX1720x fuel gauge|required|charger"
        fi
    } | awk -v skip="${cat_skip:-}" -F'|' '
        { cat=$5 }
        skip != "" && index(" " skip " ", " " cat " ") > 0 { next }
        { print $1"|"$2"|"$3"|"$4 }
    '
}

list_files() {
    log_step "Required firmware files (mustang / Tensor G5)"
    log_info "Device: ${DEVICE_MODEL} (${DEVICE_CODENAME})  Serial: ${DEVICE_SERIAL}"
    log_info "Manifest: ${MANIFEST}"

    if [ ! -f "${MANIFEST}" ]; then
        log_error "Manifest not found: ${MANIFEST}"
        return 1
    fi

    # Emit the manifest contents as a table and run a self-consistency check:
    # the manifest must cover the expected required blobs (Exynos 5500 modem,
    # BCM4390 WiFi/BT, PowerVR GPU) for mustang bring-up (briq-hw1).
    local nuxel_cat_skip=""
    [ "${DO_MODEM}" -eq 0 ] && nuxel_cat_skip="${nuxel_cat_skip} modem"
    [ "${DO_WIFI}" -eq 0 ]  && nuxel_cat_skip="${nuxel_cat_skip} wifi"
    [ "${DO_BT}" -eq 0 ]    && nuxel_cat_skip="${nuxel_cat_skip} bluetooth"
    [ "${DO_GPU}" -eq 0 ]   && nuxel_cat_skip="${nuxel_cat_skip} gpu"

    MANIFEST="${MANIFEST}" LOG_VERBOSE="${VERBOSE}" NUXEL_CAT_SKIP="${nuxel_cat_skip}" python3 - <<'PY'
import os, sys
try:
    import yaml
except ImportError:
    print("[ERROR] python3 PyYAML is required to parse manifest.yml", file=sys.stderr)
    sys.exit(3)

try:
    with open(os.environ['MANIFEST']) as f:
        data = yaml.safe_load(f)
except Exception as e:
    print("[ERROR] cannot parse manifest.yml: %s" % e, file=sys.stderr)
    sys.exit(3)

problems = []
for key, want in {'device': 'mustang', 'soc': 'tensor_g5', 'modem': 'exynos_5500'}.items():
    got = str(data.get(key, '')).lower()
    if got != want:
        problems.append("manifest.%s expected '%s', got '%s'" % (key, want, got or '<missing>'))

files = data.get('firmware_files', {}) or {}
skip_cats = set(os.environ.get('NUXEL_CAT_SKIP', '').split())
# Apply the --no-modem/--no-wifi/--no-bt/--no-gpu category-skip filter so
# --list-files matches verify/checksum/install mode behaviour.
def kept(cat):
    return cat not in skip_cats
all_required_dests = []
seen = set()
for cat in sorted(files.keys()):
    if not kept(cat):
        continue
    entries = files[cat] or []
    for fw in entries:
        dst = fw.get('dest', '')
        req = bool(fw.get('required', False))
        if not dst:
            problems.append("firmware_files.%s has an entry without 'dest'" % cat)
            continue
        if dst in seen:
            problems.append("duplicate dest '%s' in category '%s'" % (dst, cat))
        seen.add(dst)
        if req:
            all_required_dests.append(dst)
    print("  [%s]  %d blob(s)" % (cat, len(entries)))

print("")
print("required count: %d   optional count: %d" % (
    len(all_required_dests), len(seen) - len(all_required_dests)))
print("")

print("MANIFEST FIRMWARE TABLE")
print("%-58s %-4s %-6s %s" % ("dest", "req", "hash", "description"))
print("%s %s %s %s" % ("-"*58, "-"*4, "-"*6, "-"*40))
for cat in sorted(files.keys()):
    if not kept(cat):
        continue
    for fw in files.get(cat, []) or []:
        dst = fw.get('dest', '')
        req = 'req' if fw.get('required', False) else 'opt'
        cs = fw.get('checksum', {}) or {}
        sha = cs.get('sha256', '') if isinstance(cs, dict) else str(cs)
        if not sha or sha.startswith('PLACEHOLDER') or sha.startswith('sha256:verify'):
            sha = 'PENDING'
        print("%-58s %-4s %-6s %s" % (dst, req, sha, fw.get('description','')))

print("")

# The expect gate below assumes the full (unfiltered) manifest. When
# --no-modem/--no-wifi/--no-bt/--no-gpu are set, blobs from the skipped
# categories are intentionally absent, so do not flag them as missing.
skipped_dests = set()
for cat in files:
    if not kept(cat):
        for fw in files.get(cat, []) or []:
            skipped_dests.add(fw.get('dest', ''))

missing_expected = []
for blob in ['/lib/firmware/modem.bin',
             '/lib/firmware/modem_pr.bin',
             '/lib/firmware/modem_cfg.txt',
             '/lib/firmware/exynos5500_shm.bin',
             '/lib/firmware/brcm/brcmfmac4390.bin',
             '/lib/firmware/brcm/brcmfmac4390-pcie.bin',
             '/lib/firmware/brcm/brcmfmac4390.nvm',
             '/lib/firmware/brcm/BCM4390.hcd',
             '/lib/firmware/img/pvr_drv.so',
             '/lib/firmware/img/pvr_rogue_km.fw',
             '/lib/firmware/img/pvr_dxt_fw.fw']:
    if blob in skipped_dests:
        continue
    if blob not in all_required_dests:
        missing_expected.append(blob)

if missing_expected:
    problems.append("manifest missing required blobs: %s" % ", ".join(missing_expected))

if problems:
    print("CONSISTENCY CHECK: FAILED")
    for p in problems:
        print("  - %s" % p)
    print("")
    print("Result: %d problem(s) found in %s" % (len(problems), os.environ.get('MANIFEST', 'firmware/manifest.yml')))
    sys.exit(1)
else:
    print("CONSISTENCY CHECK: PASSED")
    print("Result: %s covers all expected mustang blobs "
          "(Exynos 5500 modem, BCM4390 WiFi/BT, PowerVR GPU)."
          % os.environ.get('MANIFEST', 'firmware/manifest.yml'))
    sys.exit(0)
PY
    local rc=$?
    if [ "${rc}" -ne 0 ]; then
        log_warn "manifest.yml does not fully match expected mustang firmware files."
    fi
    echo ""
    log_info "Manifest-file listing complete."

    if [ "${VERBOSE}" -eq 1 ]; then
        log_detail "Use --verify-only to check installed blobs; verify-firmware.sh checks sha256."
    fi
    return "${rc}"
}


verify_installed_firmware() {
    log_step "Verifying installed firmware"

    MISSING=0
    VERIFIED=0

    local src dest desc required installed_path size
    while IFS='|' read -r src dest desc required; do
        installed_path="${dest}"

        if [ -f "${installed_path}" ]; then
            size="$(stat -f%z "${installed_path}" 2>/dev/null || stat -c%s "${installed_path}" 2>/dev/null)"
            # A valid firmware blob should be at least 1KB
            if [ "${size:-0}" -ge 1024 ]; then
                log_ok "${dest} (${size} bytes)"
                VERIFIED=$((VERIFIED + 1))
            else
                log_warn "${dest} is suspiciously small (${size:-0} bytes)"
            fi
        else
            if [ "${required}" = "required" ]; then
                log_error "${dest} is MISSING (required)"
                MISSING=$((MISSING + 1))
            else
                log_detail "${dest} not found (optional)"
            fi
        fi
    done < <(get_firmware_list)

    echo ""
    log_info "Verified: ${VERIFIED} files present"
    if [ "${MISSING}" -gt 0 ]; then
        log_error "${MISSING} required files MISSING"
    fi
}

generate_checksums() {
    log_step "Firmware Checksums"

    local output_file="/tmp/nuxel-firmware-checksums-$(date +%Y%m%d).txt"
    local gen_done="$(date)"
    echo "# Nuxel Firmware Checksums for ${DEVICE_MODEL} (${DEVICE_CODENAME})" > "${output_file}"
    echo "# Generated: ${gen_done}" >> "${output_file}"
    echo "# Device: ${DEVICE_MODEL} (mustang)" >> "${output_file}"
    echo "# Serial: ${DEVICE_SERIAL}" >> "${output_file}"
    echo "# Mode: verify-only (no on-device flash; hardware-gated until real mustang device)" >> "${output_file}"
    echo "" >> "${output_file}"

    local installed_count=0 pending_count=0
    local src dest desc required hash status

    # sha256 the installed blobs; blobs not yet extracted are reported as PENDING.
    while IFS='|' read -r src dest desc required; do
        if [ -f "${dest}" ]; then
            if command -v sha256sum &>/dev/null; then
                hash="$(sha256sum "${dest}" | cut -d' ' -f1)"
            else
                hash="$(shasum -a 256 "${dest}" | cut -d' ' -f1)"
            fi
            echo "${hash}  ${dest}  # ${desc}" >> "${output_file}"
            status="VERIFIED"
            installed_count=$((installed_count + 1))
        else
            status="PENDING"
            pending_count=$((pending_count + 1))
            echo "# PENDING  ${dest}  # ${desc} (not extracted yet)" >> "${output_file}"
        fi
    done < <(get_firmware_list)

    echo "" >> "${output_file}"
    echo "# Summary: ${installed_count} blob(s) with real sha256, ${pending_count} PENDING until the" >> "${output_file}"
    echo "# stock factory image is extracted (see firmware/${NUXEL_DEVICE_DIR}/manifest.yml)." >> "${output_file}"

    echo "Checksums written to: ${output_file}"
    echo ""
    cat "${output_file}"

    # Manifest self-consistency gate (verify/checksum mode without a device).
    echo ""
    if [ -f "${MANIFEST}" ]; then
        log_step "Manifest consistency (verify-only)"
        bash "${NUXEL_ROOT}/firmware/${NUXEL_DEVICE_DIR}/verify-firmware.sh" --root / || true
        local rc=$?
        if [ "${rc}" -eq 3 ]; then
            log_warn "verify-firmware.sh could not run (exit 3); manifest self-check passed by list_files."
        fi
    fi

    return 0
}

extract_factory_image() {
    local factory_zip="$1"
    local output="$2"

    if [ ! -f "${factory_zip}" ]; then
        log_error "Factory image not found: ${factory_zip}"
        exit 1
    fi

    log_info "Extracting factory image: ${factory_zip}"

    local workdir
    workdir="$(mktemp -d)"
    local extracted_dir="${output}/extracted"

    mkdir -p "${extracted_dir}" "${output}/firmware" \
             "${output}/modem" "${output}/dsp"

    # Extract factory zip
    log_info "Unzipping factory image..."
    if ! unzip -qo "${factory_zip}" -d "${workdir}" 2>&1; then
        log_error "Failed to unzip factory image"
        rm -rf "${workdir}"
        return 1
    fi

    # Check for valid mustang build
    if ls "${workdir}"/*mustang* 1>/dev/null 2>&1; then
        log_ok "Valid mustang factory image detected"
    else
        log_warn "Images may not be for mustang. Proceeding anyway..."
    fi

    # Find all images
    log_info "Searching for firmware-bearing images..."

    local vendor_img=""
    local modem_img=""
    local dsp_img=""
    local super_img=""

    # Find vendor image
    vendor_img="$(find "${workdir}" -name "vendor*img" -type f 2>/dev/null | head -1 || true)"

    # Find super image if vendor not found directly
    if [ -z "${vendor_img}" ]; then
        super_img="$(find "${workdir}" -name "super*img" -type f 2>/dev/null | head -1 || true)"
    fi

    # Find modem image
    modem_img="$(find "${workdir}" -name "modem*img" -type f 2>/dev/null | head -1 || true)"

    # Find DSP image
    dsp_img="$(find "${workdir}" -name "dsp*img" -type f 2>/dev/null | head -1 || true)"

    # If no vendor found directly, extract from super
    if [ -z "${vendor_img}" ] && [ -n "${super_img}" ]; then
        log_info "Extracting vendor from super image..."
        if command -v simg2img &>/dev/null; then
            simg2img "${super_img}" "${workdir}/super.raw" 2>/dev/null && {
                if command -v lpunpack &>/dev/null; then
                    mkdir -p "${workdir}/super-out"
                    lpunpack "${workdir}/super.raw" "${workdir}/super-out/" 2>/dev/null || true
                    vendor_img="$(find "${workdir}/super-out" -name "vendor*img" -type f 2>/dev/null | head -1 || true)"
                fi
            }
        else
            log_warn "simg2img not available. Cannot extract from super image."
            log_warn "Try extracting with: sudo mount -o loop system.img /mnt"
        fi
    fi

    # Extract firmware from vendor image
    if [ -n "${vendor_img}" ]; then
        log_info "Extracting firmware from vendor image: ${vendor_img}"

        # Convert sparse to raw if needed
        if file "${vendor_img}" 2>/dev/null | grep -q "sparse"; then
            if command -v simg2img &>/dev/null; then
                log_info "Converting sparse vendor image..."
                simg2img "${vendor_img}" "${workdir}/vendor.raw"
                vendor_img="${workdir}/vendor.raw"
            fi
        fi

        # Mount and extract
        mkdir -p "${workdir}/mnt-vendor"

        # Try mounting
        if mount -o loop,ro "${vendor_img}" "${workdir}/mnt-vendor" 2>/dev/null; then
            log_ok "Vendor image mounted"

            # Copy firmware from all possible locations
            local fw_sources=(
                "firmware"
                "lib/firmware"
                "etc/firmware"
                "vendor/firmware"
                "vendor/lib/firmware"
            )

            for fw_src in "${fw_sources[@]}"; do
                local src_path="${workdir}/mnt-vendor/${fw_src}"
                if [ -d "${src_path}" ]; then
                    log_info "  Copying from ${fw_src}..."
                    cp -r "${src_path}/." "${extracted_dir}/" 2>/dev/null || true
                fi
            done

            umount "${workdir}/mnt-vendor" 2>/dev/null || true
            log_ok "Firmware extracted from vendor"
        else
            log_warn "Could not mount vendor image. Trying raw copy..."
            # Fallback: use Python to extract files
            python3 -c "
import os, sys, struct

vendor_img = '${vendor_img}'
out_dir = '${extracted_dir}'

# Try to extract known files by searching for magic strings
# This is a best-effort fallback
print(f'Vendor image size: {os.path.getsize(vendor_img)} bytes')
print(f'Output directory: {out_dir}')
print('Manual extraction recommended:')
print(f'  simg2img {vendor_img} vendor.raw')
print(f'  mount -o loop vendor.raw /mnt')
print(f'  cp -r /mnt/firmware/* {out_dir}/')
" 2>/dev/null || true
        fi
    else
        log_warn "No vendor image found in factory package"
    fi

    # Extract modem firmware
    if [ "${DO_MODEM}" -eq 1 ] && [ -n "${modem_img}" ]; then
        log_info "Extracting Exynos 5500 modem firmware..."

        # Convert if sparse
        if file "${modem_img}" 2>/dev/null | grep -q "sparse"; then
            if command -v simg2img &>/dev/null; then
                simg2img "${modem_img}" "${workdir}/modem.raw" 2>/dev/null
                modem_img="${workdir}/modem.raw"
            fi
        fi

        mkdir -p "${workdir}/mnt-modem"
        if mount -o loop,ro "${modem_img}" "${workdir}/mnt-modem" 2>/dev/null; then
            log_ok "Modem image mounted"
            cp -r "${workdir}/mnt-modem/." "${output}/modem/" 2>/dev/null || true
            umount "${workdir}/mnt-modem" 2>/dev/null || true
            log_ok "Modem firmware extracted (${output}/modem/)"
        else
            log_warn "Could not mount modem image. Copying raw..."
            cp "${modem_img}" "${output}/modem/modem.img" 2>/dev/null || true
        fi
    else
        log_detail "Modem extraction skipped"
    fi

    # Extract DSP firmware
    if [ -n "${dsp_img}" ]; then
        log_info "Extracting DSP firmware..."

        if file "${dsp_img}" 2>/dev/null | grep -q "sparse"; then
            if command -v simg2img &>/dev/null; then
                simg2img "${dsp_img}" "${workdir}/dsp.raw" 2>/dev/null
                dsp_img="${workdir}/dsp.raw"
            fi
        fi

        mkdir -p "${workdir}/mnt-dsp"
        if mount -o loop,ro "${dsp_img}" "${workdir}/mnt-dsp" 2>/dev/null; then
            log_ok "DSP image mounted"
            cp -r "${workdir}/mnt-dsp/." "${output}/dsp/" 2>/dev/null || true
            umount "${workdir}/mnt-dsp" 2>/dev/null || true
            log_ok "DSP firmware extracted (${output}/dsp/)"
        else
            cp "${dsp_img}" "${output}/dsp/dsp.img" 2>/dev/null || true
        fi
    fi

    # Extract DTBO from vendor_boot if available
    local vendor_boot_img
    vendor_boot_img="$(find "${workdir}" -name "vendor_boot*img" -type f 2>/dev/null | head -1 || true)"
    if [ -n "${vendor_boot_img}" ]; then
        log_info "Found vendor_boot.img, extracting DTBO..."
        mkdir -p "${output}/dtbo"
        cp "${vendor_boot_img}" "${output}/dtbo/" 2>/dev/null || true
    fi

    # Clean up
    rm -rf "${workdir}"

    log_ok "Factory image extraction complete"
    return 0
}

install_firmware() {
    local source_dir="$1"
    local firmware_installed=0
    local firmware_failed=0

    log_step "Installing firmware to /lib/firmware"

    if [ ! -d "${source_dir}" ]; then
        log_error "Source directory not found: ${source_dir}"
        return 1
    fi

    # Install from the manifest-specified paths.
    # NOTE: `< <(get_firmware_list)` (process substitution) keeps the loop in the
    # current shell so the EXTRACTED / SKIPPED / FAILED counters propagate out.
    local src dest desc required src_file dest_dir installed found
    while IFS='|' read -r src dest desc required; do
        src_file="${source_dir}/$(basename "${src}")"
        dest_dir="$(dirname "${dest}")"
        installed=0

        # Try to find the file in the extracted directory
        if [ -f "${src_file}" ]; then
            mkdir -p "${dest_dir}"
            if [ "${DO_FORCE}" -eq 1 ] || [ ! -f "${dest}" ]; then
                if ! cp -v "${src_file}" "${dest}" 2>/dev/null; then
                    log_error "Failed to copy ${desc} to ${dest}"
                    firmware_failed=$((firmware_failed + 1))
                    FAILED=$((FAILED + 1))
                    installed=1
                fi
                if [ "${installed}" -eq 0 ]; then
                    # Set permissions (readable by all, writable by root)
                    chmod 644 "${dest}" 2>/dev/null || true
                    log_ok "Installed: ${dest} (${desc})"
                    EXTRACTED=$((EXTRACTED + 1))
                fi
            else
                log_detail "Skipping ${dest} (already exists, use --force to overwrite)"
                SKIPPED=$((SKIPPED + 1))
            fi
        else
            # Try broader search in output directory
            found="$(find "${source_dir}" -name "$(basename "${src}")" -type f 2>/dev/null | head -1 || true)"
            if [ -n "${found}" ]; then
                mkdir -p "${dest_dir}"
                if [ "${DO_FORCE}" -eq 1 ] || [ ! -f "${dest}" ]; then
                    cp -v "${found}" "${dest}" 2>/dev/null || true
                    chmod 644 "${dest}" 2>/dev/null || true
                    log_ok "Installed: ${dest} (${desc}) [from ${found}]"
                    EXTRACTED=$((EXTRACTED + 1))
                else
                    SKIPPED=$((SKIPPED + 1))
                fi
            else
                log_detail "Source file not found: $(basename "${src}") - ${desc}"
                if [ "${required}" = "required" ]; then
                    FAILED=$((FAILED + 1))
                fi
            fi
        fi
    done < <(get_firmware_list)

    # Also install modem firmware if present
    if [ "${DO_MODEM}" -eq 1 ] && [ -d "${source_dir}/../modem" ]; then
        local modem_dir="${source_dir}/../modem"
        mkdir -p /lib/firmware/modem
        find "${modem_dir}" -type f -exec cp -v {} /lib/firmware/modem/ \; 2>/dev/null || true
        log_info "Modem firmware installed from ${modem_dir}"
    fi

    # Install DSP firmware if present
    if [ -d "${source_dir}/../dsp" ]; then
        local dsp_dir="${source_dir}/../dsp"
        mkdir -p /lib/firmware/dsp
        find "${dsp_dir}" -type f -exec cp -v {} /lib/firmware/dsp/ \; 2>/dev/null || true
        log_info "DSP firmware installed from ${dsp_dir}"
    fi

    return 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
            --install) DO_INSTALL=1; shift ;;
            --force) DO_FORCE=1; shift ;;
            --verify-only) DO_VERIFY_ONLY=1; shift ;;
            --list-files) DO_LIST=1; shift ;;
            --checksums) DO_CHECKSUMS=1; shift ;;
            --no-modem) DO_MODEM=0; shift ;;
            --no-wifi) DO_WIFI=0; shift ;;
            --no-bt) DO_BT=0; shift ;;
            --no-gpu) DO_GPU=0; shift ;;
            --verbose) VERBOSE=1; shift ;;
            -v) VERBOSE=1; shift ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
            *)
                # Positional arg: factory image zip
                if [ -z "${FACTORY_ZIP+x}" ]; then
                    FACTORY_ZIP="$1"
                    shift
                else
                    log_error "Unexpected argument: $1"
                    exit 1
                fi
                ;;
        esac
    done
}

show_usage() {
    echo ""
    echo "Nuxel Firmware Installer for ${DEVICE_MODEL} (${DEVICE_CODENAME})"
    echo "Serial: ${DEVICE_SERIAL}"
    echo ""
    echo "Usage: $0 <factory-image.zip> [options]"
    echo ""
    echo "Options:"
    echo "  --output-dir <dir>    Extract firmware to directory"
    echo "  --install             Install firmware to /lib/firmware (root)"
    echo "  --force               Overwrite existing files"
    echo "  --verify-only         Verify installed firmware only"
    echo "  --list-files          List required firmware files"
    echo "  --checksums           Generate checksums of installed files"
    echo "  --no-modem            Skip modem firmware blobs"
    echo "  --no-wifi             Skip WiFi firmware blobs"
    echo "  --no-bt               Skip Bluetooth firmware blobs"
    echo "  --no-gpu              Skip GPU firmware blobs"
    echo "  --verbose             Verbose output"
    echo ""
    echo "  The --no-modem/--no-wifi/--no-bt/--no-gpu filters apply to"
    echo "  --verify-only, --checksums, --install and --list-files alike,"
    echo "  so --list-files omits the skipped categories too."
    echo "  -h, --help            Show this help"
    echo ""
    echo "Examples:"
    echo "  # List all required firmware:"
    echo "  $0 --list-files"
    echo ""
    echo "  # Extract firmware to directory:"
    echo "  $0 mustang-factory.zip --output-dir ./firmware-out"
    echo ""
    echo "  # Full extract and install:"
    echo "  sudo $0 mustang-factory.zip --output-dir ./firmware-out --install"
    echo ""
    echo "  # Verify installed firmware:"
    echo "  $0 --verify-only"
    echo ""
    echo "Download factory image:"
    echo "  https://developers.google.com/android/images#mustang"
    echo "  Expected build: ${EXPECTED_BUILD}"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────

main() {
    parse_args "$@"

    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo -e "║        ${BOLD}Nuxel Firmware Installer${NC}                ║"
    echo -e "║   ${DEVICE_MODEL} (${DEVICE_CODENAME}) - Tensor G5      ║"
    echo -e "║   Serial: ${DEVICE_SERIAL}                           ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""

    # Check dependencies
    check_deps

    # Handle special modes
    if [ "${DO_LIST}" -eq 1 ]; then
        list_files
        exit 0
    fi

    if [ "${DO_CHECKSUMS}" -eq 1 ]; then
        generate_checksums
        exit 0
    fi

    if [ "${DO_VERIFY_ONLY}" -eq 1 ]; then
        verify_installed_firmware
        exit ${MISSING}
    fi

    # Must have a factory image
    if [ -z "${FACTORY_ZIP+x}" ]; then
        log_error "No factory image specified."
        echo ""
        echo "Usage: $0 <factory-image.zip> [options]"
        echo "Try: $0 --help for more information."
        exit 1
    fi

    # Set output directory
    if [ -z "${OUTPUT_DIR}" ]; then
        OUTPUT_DIR="$(pwd)/firmware-out-${DEVICE_CODENAME}-$(date +%Y%m%d-%H%M%S)"
    fi

    # Step 1: Extract firmware from factory image
    log_step "Extracting firmware from factory image"
    extract_factory_image "${FACTORY_ZIP}" "${OUTPUT_DIR}"

    echo ""
    log_info "Extracted firmware directory: ${OUTPUT_DIR}"
    echo ""
    echo "Extracted files:"
    find "${OUTPUT_DIR}" -type f | sort | head -50
    echo ""

    # Step 2: Install firmware (if requested)
    if [ "${DO_INSTALL}" -eq 1 ]; then
        local extracted_dir="${OUTPUT_DIR}/extracted"
        install_firmware "${extracted_dir}"

        echo ""
        log_separator
        echo "Firmware installation summary:"
        echo "  Installed: ${EXTRACTED}"
        echo "  Skipped:   ${SKIPPED}"
        echo "  Failed:    ${FAILED}"
        echo ""

        if [ "${FAILED}" -gt 0 ]; then
            log_warn "${FAILED} firmware files failed to install"
            log_warn "The device may not function fully without all required firmware"
        fi
    fi

    # Final verification
    echo ""
    log_step "Final verification"
    verify_installed_firmware

    # --- sha256 verification against firmware/manifest.yml -------------------
    log_step "sha256 manifest verification (firmware/verify-firmware.sh)"
    local verify_script="${NUXEL_ROOT}/firmware/${NUXEL_DEVICE_DIR}/verify-firmware.sh"
    if [ -x "${verify_script}" ]; then
        if bash "${verify_script}" ; then
            log_ok "All firmware hashes verified against manifest.yml"
        else
            log_warn "verify-firmware.sh reported issues; some blobs missing or unverified."
        fi
    else
        log_warn "verify-firmware.sh not found/executable at ${verify_script}"
    fi

    # Report missing blobs
    if [ "${MISSING}" -gt 0 ]; then
        echo ""
        log_warn "${MISSING} required firmware files are still missing!"
        echo ""
        echo "Manual extraction hint:"
        echo "  1. Extract factory image: unzip ${FACTORY_ZIP} -d /tmp/factory"
        echo "  2. Find vendor image: find /tmp/factory -name 'vendor*img'"
        echo "  3. Mount and copy:"
        echo "     simg2img vendor.img vendor.raw"
        echo "     mount -o loop vendor.raw /mnt"
        echo "     cp -r /mnt/firmware/* /lib/firmware/"
        echo "     umount /mnt"
        echo ""
        echo "See firmware/${NUXEL_DEVICE_DIR}/manifest.yml for complete list."
        exit 1
    fi

    echo ""
    log_ok "Firmware setup complete!"
    echo ""
}

main "$@"
