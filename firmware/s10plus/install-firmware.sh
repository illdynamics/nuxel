#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ Firmware Installer / Extractor — Samsung Galaxy S10+ (beyond2lte)
#
# Sources blobs for firmware/s10plus/manifest.yml from a physical S10+ that is
# already in TWRP, verifies installed blobs, and installs them into a rootfs
# staging area. This script is S10+-only: it never reads or installs mustang
# paths and never reads the mustang manifest.
#
# Flash method: TWRP adb pull (acquisition) + rootfs staging copy (install).
# The S10+ (Exynos) has NO Android-bootloader-mode flashing — only TWRP (adb)
# and Download Mode (Odin/heimdall). This script never dd's any partition and
# never touches the protected partitions:
#   efs efsg persist param up_param steady keystorage carrier cp_debug misc
#
# Usage:
#   NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --list-files
#   firmware/s10plus/install-firmware.sh --device s10plus --list-files
#   NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --verify-only
#   NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --checksums
#   NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --twrp-pull
#   NUXEL_DEVICE=s10plus firmware/s10plus/install-firmware.sh --install \
#       [--rootfs-staging build/out/rootfs] [--force-pending]
#
# Modes:
#   --list-files    Print the full S10+ manifest; install nothing.
#   --verify-only   Verify installed blobs; UNKNOWN checksums report
#                   "pending" and exit 0 (not an error).
#   --checksums     Print sha256 of every blob under blobs/.
#   --twrp-pull     Pull vendor blobs from the TWRP-connected device into
#                   blobs/ (identity-checked), then cross-reference the
#                   manifest found vs missing. This is the acquisition step
#                   that fills the UNKNOWN values — never gated.
#   --install       Copy blobs from blobs/ into the rootfs staging area.
#                   Refuses while required checksums are UNKNOWN unless
#                   --force-pending is passed.
#   --help          Print this help and exit (runs offline).
#
# Guard: NUXEL_DEVICE must resolve to s10plus (or pass --device s10plus).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MANIFEST="${SCRIPT_DIR}/manifest.yml"
BLOBS_DIR="${SCRIPT_DIR}/blobs"
STAGING="${ROOTFS_STAGING:-${NUXEL_ROOT}/build/out/rootfs}"

DO_LIST=0
DO_VERIFY=0
DO_CHECKSUMS=0
DO_PULL=0
DO_INSTALL=0
FORCE_PENDING=0
# VERBOSE adds per-file diagnostics in install_blobs (accepted via --verbose).
VERBOSE=0

log()  { echo "[nuxel-fw] $*"; }
warn() { echo "[nuxel-fw][warn] $*" >&2; }
err()  { echo "[nuxel-fw][error] $*" >&2; }

usage() {
    sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
}

# ---------------------------------------------------------------------------
# Inventory gate (Phase 0) — see docs/s10plus-device-inventory.md
# Blocks real install operations until the operator has filled the critical
# fields from the physical device. Never blocks --help / --list-files /
# --verify-only / --checksums / --twrp-pull.
# ---------------------------------------------------------------------------
_check_s10plus_inventory() {
    local inventory="${NUXEL_ROOT}/docs/s10plus-device-inventory.md"
    # Fail closed: a missing/unreadable inventory must never disarm the
    # Phase-0 gate — the grep below would otherwise pass vacuously.
    [[ -f "${inventory}" ]] || {
        echo "ERROR: ${inventory} missing — run Phase 0 inventory first."
        exit 1
    }
    # Check if UNKNOWN placeholders are still present in critical fields
    if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAME:.*UNKNOWN" "${inventory}" 2>/dev/null; then
        echo "ERROR: S10+ device inventory is incomplete."
        echo "       Run Phase 0 collection commands in docs/s10plus-device-inventory.md"
        echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, TAGS_ADDR, WIFI_FW_FILENAME"
        echo "       Then re-run this script."
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Manifest flattening: emit tab-separated lines
#   category<TAB>source<TAB>dest<TAB>required<TAB>checksum<TAB>description
# Requires python3 + PyYAML (same dependency as the mustang verifier).
# ---------------------------------------------------------------------------
manifest_tsv() {
    MANIFEST="$MANIFEST" python3 <<'PY'
import os, sys
try:
    import yaml
except Exception as exc:  # pragma: no cover
    sys.stderr.write("nuxel-fw: PyYAML is required: %s\n" % exc)
    sys.exit(3)
try:
    doc = yaml.safe_load(open(os.environ["MANIFEST"], encoding="utf-8"))
except Exception as exc:
    sys.stderr.write("nuxel-fw: manifest parse error: %s\n" % exc)
    sys.exit(3)
for cat, entries in (doc or {}).get("firmware_files", {}).items():
    for fw in entries or []:
        if not isinstance(fw, dict):
            continue
        src = str(fw.get("source_path", ""))
        dst = str(fw.get("dest", ""))
        req = "true" if fw.get("required") else "false"
        cs = fw.get("checksum", "")
        if isinstance(cs, dict):
            cs = str(cs.get("sha256", ""))
        desc = str(fw.get("description", ""))
        print("\t".join([cat, src, dst, req, cs, desc]))
PY
}

is_pending_checksum() {
    local v="$1"
    case "$v" in
        ""|UNKNOWN*|PLACEHOLDER*|TBD*|sha256:verify*) return 0 ;;
        *) return 1 ;;
    esac
}

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" 2>/dev/null | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" 2>/dev/null | awk '{print $1}'
    else
        return 1
    fi
}

# Map a manifest source_path onto a blob path under blobs/ (mirrors the
# twrp-pull layout: vendor-firmware/, vendor-modules/, vendor-etc-firmware/,
# system-lib64/). Returns 1 when the source prefix is not pulled.
blob_path_for_source() {
    local src="$1" base="" rel=""
    case "$src" in
        vendor/firmware/*)  base="vendor-firmware"; rel="${src#vendor/firmware/}" ;;
        vendor/lib/modules/*) base="vendor-modules"; rel="${src#vendor/lib/modules/}" ;;
        vendor/etc/firmware/*) base="vendor-etc-firmware"; rel="${src#vendor/etc/firmware/}" ;;
        vendor/lib64/*)     base="system-lib64"; rel="${src#vendor/lib64/}" ;;
        *) return 1 ;;
    esac
    printf '%s/%s/%s' "${BLOBS_DIR}" "${base}" "${rel}"
}

list_files() {
    log "S10+ firmware manifest (firmware/s10plus/manifest.yml)"
    log "device: s10plus | codename: beyond2lte | soc: exynos9820"
    local cat src dst req cs _desc
    while IFS=$'\t' read -r cat src dst req cs _desc; do
        [ -n "$src" ] || continue
        printf '  [%s] required=%s\n      source: %s\n      dest:   %s\n      sha256: %s\n' \
            "${cat}" "${req}" "${src}" "${dst}" "${cs}"
    done < <(manifest_tsv)
    log "All checksums are UNKNOWN until Phase 0 inventory is collected."
}

verify_only() {
    local pass=0 pending=0 missing=0 mismatch=0 advisory=0
    local cat src dst req cs _desc root_full
    while IFS=$'\t' read -r cat src dst req cs _desc; do
        [ -n "$src" ] || continue
        if [ "${req}" = "false" ]; then
            advisory=$((advisory+1))
            continue
        fi
        if is_pending_checksum "$cs"; then
            log "PENDING  ${src} (checksum UNKNOWN — collect in Phase 0)"
            pending=$((pending+1))
            continue
        fi
        root_full="${STAGING%/}${dst}"
        if [ ! -f "${root_full}" ]; then
            warn "MISSING  ${dst}"
            missing=$((missing+1))
            continue
        fi
        local actual
        actual="$(sha256_of "${root_full}")" || { err "cannot hash ${root_full}"; mismatch=$((mismatch+1)); continue; }
        if [ "$actual" = "$cs" ]; then
            log "OK       ${dst}"
            pass=$((pass+1))
        else
            err "MISMATCH ${dst}: expected ${cs}, got ${actual}"
            mismatch=$((mismatch+1))
        fi
    done < <(manifest_tsv)
    log "verify-only summary: ${pass} verified, ${pending} pending (UNKNOWN checksums), ${missing} missing, ${mismatch} mismatch, ${advisory} advisory."
    # UNKNOWN checksums are pending (exit 0); a required blob that carries a
    # REAL checksum but is missing or mismatched is a hard failure.
    [ "${mismatch}" -eq 0 ] && [ "${missing}" -eq 0 ]
}

checksums() {
    if [ ! -d "${BLOBS_DIR}" ]; then
        warn "blobs/ does not exist yet — run --twrp-pull on the S10+ first."
        return 0
    fi
    local n=0
    # Hash only pulled firmware blobs; skip this repo's own metadata files.
    while IFS= read -r -d '' f; do
        local base
        base="$(basename "$f")"
        case "$base" in
            .gitkeep|README.md) continue ;;
        esac
        local sum
        sum="$(sha256_of "$f")" || { err "cannot hash $f"; return 1; }
        printf '%s  %s\n' "$sum" "${f#${BLOBS_DIR}/}"
        n=$((n+1))
    done < <(find "${BLOBS_DIR}" -type f -print0 | sort -z)
    log "${n} blob(s) checksummed."
}

twrp_pull() {
    command -v adb >/dev/null 2>&1 || { err "adb not found — install android-tools/adb first."; exit 1; }
    if ! adb devices | grep -q "device$"; then
        err "No ADB device found. Is the S10+ in TWRP with USB debugging enabled?"
        exit 1
    fi
    local dev name
    dev="$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')"
    name="$(adb shell getprop ro.product.name 2>/dev/null | tr -d '\r')"
    log "Connected: device='${dev}' name='${name}'"
    [ "${dev}" = "beyond2lte" ] || {
        err "Identity check failed: ro.product.device must be beyond2lte, got '${dev}'."
        err "REFUSING to pull from a different device."
        exit 1
    }
    local name_regex="${NUXEL_S10PLUS_NAME_REGEX:-^beyond2lte}"
    if ! printf '%s' "${name}" | grep -qE "${name_regex}"; then
        err "Identity check failed: ro.product.name '${name}' does not match '${name_regex}'."
        err "Expected beyond2ltexx (or the operator's regional variant)."
        exit 1
    fi
    log "Identity verified: ${dev} / ${name}."

    mkdir -p "${BLOBS_DIR}"/{vendor-firmware,vendor-modules,vendor-etc-firmware,system-lib64}
    log "Pulling /vendor/firmware → blobs/vendor-firmware/ ..."
    adb pull /vendor/firmware "${BLOBS_DIR}/vendor-firmware/" || warn "pull of /vendor/firmware reported issues"
    log "Pulling /vendor/lib/modules → blobs/vendor-modules/ ..."
    adb pull /vendor/lib/modules "${BLOBS_DIR}/vendor-modules/" || warn "pull of /vendor/lib/modules reported issues"
    log "Pulling /vendor/etc/firmware → blobs/vendor-etc-firmware/ ..."
    adb pull /vendor/etc/firmware "${BLOBS_DIR}/vendor-etc-firmware/" || warn "pull of /vendor/etc/firmware reported issues"
    log "Pulling /system/lib64 → blobs/system-lib64/ ..."
    adb pull /system/lib64 "${BLOBS_DIR}/system-lib64/" || warn "pull of /system/lib64 reported issues"

    log "Cross-referencing manifest vs pulled blobs..."
    local cat src dst req cs _desc blob found=0 missing=0
    while IFS=$'\t' read -r cat src dst req cs _desc; do
        [ -n "$src" ] || continue
        case "$src" in
            PLACEHOLDER*|UNKNOWN*) continue ;;   # nothing to look for yet
        esac
        blob="$(blob_path_for_source "$src" || true)"
        if [ -n "$blob" ]; then
            if compgen -G "${blob}" >/dev/null 2>&1; then
                log "FOUND    ${src}"
                found=$((found+1))
            else
                warn "MISSING  ${src}"
                missing=$((missing+1))
            fi
        else
            warn "SKIP     ${src} (source prefix not pulled; e.g. vendor/lib64 — pull manually if needed)"
        fi
    done < <(manifest_tsv)
    log "twrp-pull cross-reference: ${found} found, ${missing} missing."
    log "Now fill firmware/s10plus/manifest.yml checksums from sha256 of blobs/ (--checksums)."
}

install_blobs() {
    local pending=0
    local cat src dst req cs _desc blob target
    while IFS=$'\t' read -r cat src dst req cs _desc; do
        [ -n "$src" ] || continue
        case "$dst" in
            "DO NOT INSTALL"*) log "SKIP     ${src} (${dst})"; continue ;;
        esac
        case "$src" in
            PLACEHOLDER*|UNKNOWN*) log "SKIP     ${src} (no real source path yet)"; continue ;;
        esac
        if [ "${req}" = "true" ] && is_pending_checksum "$cs" && [ "${FORCE_PENDING}" -eq 0 ]; then
            warn "PENDING  ${src} — required blob with UNKNOWN checksum (refusing install)"
            pending=$((pending+1))
            continue
        fi
        blob="$(blob_path_for_source "$src" || true)"
        if [ -z "$blob" ] || ! compgen -G "${blob}" >/dev/null 2>&1; then
            if [ "${req}" = "true" ] && [ "${FORCE_PENDING}" -eq 0 ]; then
                err "MISSING  ${src} — required blob not found under blobs/ (run --twrp-pull)"
                pending=$((pending+1))
            else
                warn "SKIP     ${src} — blob not present (optional or forced pending)"
            fi
            continue
        fi
        # dest may be a directory (trailing '/') or an exact file path
        case "${dst}" in
            */) target="${STAGING%/}${dst}$(basename "$(compgen -G "${blob}" | head -1)")" ;;
            *)  target="${STAGING%/}${dst}" ;;
        esac
        mkdir -p "$(dirname "${target}")"
        if [ "${VERBOSE}" -eq 1 ]; then
            log "verbose: ${src} -> ${target}"
        fi
        cp -v "$(compgen -G "${blob}" | head -1)" "${target}" | sed 's/^/INSTALL /'
    done < <(manifest_tsv)
    if [ "${pending}" -gt 0 ]; then
        err "install aborted: ${pending} required blob(s) have UNKNOWN checksums or are missing."
        err "Fill real checksums in firmware/s10plus/manifest.yml (Phase 0) or pass --force-pending."
        exit 1
    fi
    log "Install complete (staging: ${STAGING})."
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --device) [ -n "${2:-}" ] || { err "--device requires a value"; exit 1; }
            # shellcheck disable=SC2034 # consumed by tools/nuxel-device-select.sh via env
            NUXEL_DEVICE="$2"; shift 2 ;;
        --list-files) DO_LIST=1; shift ;;
        --verify-only) DO_VERIFY=1; shift ;;
        --checksums) DO_CHECKSUMS=1; shift ;;
        --twrp-pull) DO_PULL=1; shift ;;
        --install) DO_INSTALL=1; shift ;;
        --force-pending) FORCE_PENDING=1; shift ;;
        --rootfs-staging) STAGING="$2"; shift 2 ;;
        --verbose|-v) VERBOSE=1; shift ;;
        *) err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Device guard — S10+ only. Explicit selection required (env or --device).
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || {
    err "This script is ONLY for the Samsung Galaxy S10+ (s10plus). Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

[ -f "${MANIFEST}" ] || { err "Manifest not found: ${MANIFEST}"; exit 3; }
command -v python3 >/dev/null 2>&1 || { err "python3 required to parse the manifest"; exit 3; }

# The inventory gate guards ONLY the real install path. --twrp-pull is the
# acquisition step that FILLS the unknowns, so it stays unblocked.
if [ "${DO_INSTALL}" -eq 1 ]; then
    _check_s10plus_inventory
fi

if [ "${DO_LIST}" -eq 1 ]; then
    list_files
fi
if [ "${DO_VERIFY}" -eq 1 ]; then
    verify_only
fi
if [ "${DO_CHECKSUMS}" -eq 1 ]; then
    checksums
fi
if [ "${DO_PULL}" -eq 1 ]; then
    twrp_pull
fi
if [ "${DO_INSTALL}" -eq 1 ]; then
    install_blobs
fi

if [ "${DO_LIST}${DO_VERIFY}${DO_CHECKSUMS}${DO_PULL}${DO_INSTALL}" = "00000" ]; then
    warn "No mode selected. Use --help to see available modes."
    exit 1
fi
