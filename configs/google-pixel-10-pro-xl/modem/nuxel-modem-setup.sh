#!/usr/bin/env bash
#==============================================================================
# Nuxel modem bring-up — Samsung Exynos 5500 (mustang, Pixel 10 Pro XL)
#
# Checks that ModemManager can see the modem, keys it, sets the operating mode,
# and provides fallback diagnostics when the modem does not enumerate.
#
# IMPORTANT (see docs/driver-status.md): the mainline ModemManager has **no**
# dedicated "exynos5500" plugin. Detection relies on the generic MHI/PCIe port
# + ModemManager's platform-independant "Samsung" handling only when firmware and
# the MHI bus are correctly up. Most diagnostics below assume the Exynos 5500
# enumerates as a PCIe/MHI device (vendor 0x144d Samsung).
#
# Usage:
#   sudo configs/modem/nuxel-modem-setup.sh [--key <hex>] [--mode <op>] [-v]
#
# Notes:
#   * On the VM (no modem) this script prints a clear "no modem" diagnostic and
#     exits 3 so run scripts can treat it as expected-absent.
#   * The modem key below is a PLACEHOLDER. Replace with the real per-device
#     Exynos 5500 key obtained from the carrier / vendor. Sensitive.
#==============================================================================

set -uo pipefail

NUXEL_KEY="${NUXEL_EXYNOS5500_KEY:-}"
MODE="${NUXEL_MODEM_MODE:-5g}"          # 5g | 4g | cat-m | airplane
VERBOSE=0

log()  { echo "[nuxel-modem] $*"; }
warn() { echo "[nuxel-modem][warn] $*" >&2; }
err()  { echo "[nuxel-modem][error] $*" >&2; }

USAGE="Usage: $0 [--key <hex>] [--mode 5g|4g|cat-m|airplane] [-v]"

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --key) NUXEL_KEY="$2"; shift 2 ;;
            --mode) MODE="$2"; shift 2 ;;
            -v|--verbose) VERBOSE=1; shift ;;
            -h|--help) echo "$USAGE"; exit 0 ;;
            *) err "Unknown option: $1"; echo "$USAGE"; exit 1 ;;
        esac
    done
}

# --- capability checks -------------------------------------------------------
require_mm() {
    if command -v mmcli >/dev/null 2>&1 && command -v ModemManager >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# --- primary: ModemManager present --------------------------------------------
mm_path() {
    # Return the first available modem object path, else empty.
    mmcli --list-modems 2>/dev/null | grep -oE '/org/freedesktop/ModemManager1/Modem/[0-9]+' | head -1
}

run_mm_setup() {
    local path
    path="$(mm_path)"
    if [ -z "$path" ]; then
        err "No modem enumerated via ModemManager (device = ${MODEM_PATH:-unknown})."
        return 1
    fi
    log "Using modem ${path}"

    # Get current state / firmware validity.
    if [ "${VERBOSE}" -eq 1 ]; then
        mmcli -m "$path" --command 'ATI'
    fi

    # 1. Key the modem if a key was supplied.
    if [ -n "$NUXEL_KEY" ]; then
        log "Keying Exynos 5500 modem..."
        # AT command sent as ModemManager generic +CPIN? / +CIEV; the vendor
        # "EXYNOS5500=KEY=" is delivered via a technology-specific AT escape.
        if ! mmcli -m "$path" --command "AT+EXYNOS5500=KEY=${NUXEL_KEY}"; then
            warn "AT+EXYNOS5500 key rejected — check firmware/operating mode."
        else
            log "Modem keyed successfully."
        fi
    else
        warn "No modem key supplied (--key). Enabling default registration may fail."
    fi

    # 2. Set operating mode (radio stack).
    case "$MODE" in
        airplane) mmcli -m "$path" --3gpp-set-airplane-mode 1 ;;
        cat-m)    mmcli -m "$path" --3gpp-set-cat-m 1 || warn "cat-m scheduling unsupported by this firmware" ;;
        4g)       mmcli -m "$path" --3gpp-set-allowed-modes 2g,3g,4g,5g ;;
        *)        mmcli -m "$path" --3gpp-set-allowed-modes 2g,3g,4g,5g ;;
    esac

    # 3. Enable radio if not airplane.
    if [ "$MODE" != "airplane" ]; then
        mmcli -m "$path" --enable || warn "modem --enable failed" 
    fi

    mmcli -m "$path" --command 'AT+COPS=0'
    log "Operating mode set to '${MODE}'."
    return 0
}

# --- fallback diagnostics ------------------------------------------------------
diagnose_pcie() {
    log "Rolling PCIe/MHI diagnostic for Exynos 5500..."
    if [ -e /sys/bus/pci/devices/0000:00:00.0 ]; then
        lspci -nnk 2>/dev/null | grep -iA3 'exynos\|144d:0a80' || \
            err "No Exynos 5500 PCIe device found (vendor 0x144d). Is firmware loaded?"
    else
        err "No PCIe sysfs tree — MHI bus not up."
    fi
    if [ -e /sys/firmware ]; then
        log "/sys/firmware present; modem may rely on vendor rambag blob."
    fi
    return 1
}

main() {
    parse_args "$@"
    log "Nuxel Exynos 5500 modem setup (mode=${MODE})"

    if require_mm; then
        if run_mm_setup; then
            log "Modem bring-up complete."
            return 0
        fi
        log "MM present but modem not enumerating — running diagnostics."
    else
        warn "ModemManager not installed. Cannot drive the modem from this image."
        warn "Install ModemManager on mustang before Phase-2 voice/data bring-up."
    fi

    diagnose_pcie
    warn "Modem not usable yet. Expected on VM (no modem) and until firmware+key are"
    warn "available on hardware. See configs/modem/exynos5500-people.md and"
    warn "docs/driver-status.md."
    return 3
}

main "$@"
