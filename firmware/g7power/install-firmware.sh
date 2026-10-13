#!/usr/bin/env bash
# =============================================================================
# Nuxel G7 Power Firmware Installer / Extractor — Motorola Moto G7 Power (ocean)
#
# Sources blobs for firmware/g7power/manifest.yml from a physical G7 Power that
# is running stock Android (USB debugging) or a recovery with adb, verifies
# installed blobs, and installs them into a rootfs staging area. This script
# is g7power-only: it never reads or installs mustang/s10plus paths and never
# reads another device's manifest.
#
# Flash method: fastboot + lk2nd (no fastbootd/vendor_boot/init_boot/vbmeta).
# Acquisition: adb pull. This script never dd's or fastboot-flashes any
# partition and never touches the protected partitions:
#   modemst1 modemst2 fsg fsc ddr persist misc
#
# Usage:
#   NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --list-files
#   firmware/g7power/install-firmware.sh --device g7power --list-files
#   NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --verify-only
#   NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --checksums
#   NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --adb-pull
#   NUXEL_DEVICE=g7power firmware/g7power/install-firmware.sh --install \
#       [--rootfs-staging build/out/rootfs] [--force-pending]
#
# Modes:
#   --list-files    Print the full G7 Power manifest; install nothing.
#   --verify-only   Verify installed blobs; UNKNOWN checksums report
#                   "pending" and exit 0 (not an error).
#   --checksums     Print sha256 of every blob under blobs/.
#   --adb-pull      Pull vendor blobs from the connected device into blobs/
#                   (identity-checked: ro.product.device must be ocean), then
#                   cross-reference the manifest found vs missing. This is the
#                   acquisition step that fills the UNKNOWN values — never gated.
#   --install       Copy blobs from blobs/ into the rootfs staging area.
#                   Refuses while required checksums are UNKNOWN unless
#                   --force-pending is passed.
#   --help          Print this help and exit (runs offline).
#
# Guard: NUXEL_DEVICE must resolve to g7power (or pass --device g7power).
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
# Inventory gate (Phase 0) — see docs/g7power-device-inventory.md
# Blocks real install operations until the operator has filled the critical
# fields from the physical device. Never blocks --help / --list-files /
# --verify-only / --checksums / --adb-pull (adb-pull is the acquisition step
# that FILLS the unknowns). Exact gate text from the T8 briQ spec.
# ---------------------------------------------------------------------------
_check_g7power_inventory() { local inv="${NUXEL_ROOT}/docs/g7power-device-inventory.md"; [ -f "${inv}" ] || { echo "ERROR: docs/g7power-device-inventory.md missing — run Phase 0 inventory first."; exit 1; }; if grep -qE "KERNEL_ADDR:.*PLACEHOLDER|RAMDISK_ADDR:.*PLACEHOLDER|TAGS_ADDR:.*PLACEHOLDER|WIFI_FW_FILENAMES:.*UNKNOWN" "${inv}"; then echo "ERROR: G7 Power device inventory incomplete."; echo "       Run Phase 0 commands in docs/g7power-device-inventory.md"; echo "       Fill at minimum: KERNEL_ADDR, RAMDISK_ADDR, WIFI_FW_FILENAMES"; exit 1; fi; }

# ---------------------------------------------------------------------------
# Protected-partition guard (safety invariant 4). The G7 Power firmware
# installer must NEVER treat modemst1 modemst2 fsg fsc ddr persist misc as
# firmware targets: they hold per-unit IMEI/MAC/radio calibration and are
# irreplaceable. We print the denylist and scan every parsed manifest entry
# (source/dest/checksum fields) for a forbidden partition reference.
# ---------------------------------------------------------------------------
protected_partition_guard() {
    local protected="modemst1 modemst2 fsg fsc ddr persist misc"
    log "Protected partitions (NEVER firmware targets): ${protected}"
    local bad=0 cat src dst req cs _desc field
    while IFS=$'\t' read -r cat src dst req cs _desc; do
        [ -n "$src" ] || continue
        for field in "$src" "$dst" "$cs"; do
            if printf '%s\n' "$field" | grep -qwE 'modemst1|modemst2|fsg|fsc|ddr|persist|misc'; then
                err "protected partition referenced as a firmware target: '${field}'"
                bad=1
            fi
        done
    done < <(manifest_tsv)
    if [ "${bad}" -ne 0 ]; then
        err "Manifest lists a protected partition as a firmware target — refusing to continue."
        exit 3
    fi
    log "Protected-partition guard: OK — no manifest entry targets modemst1 modemst2 fsg fsc ddr persist misc."
}

# ---------------------------------------------------------------------------
# Manifest flattening: emit tab-separated lines
#   category<TAB>source<TAB>dest<TAB>required<TAB>checksum<TAB>description
# Requires python3 + PyYAML (same dependency as the s10plus installer).
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
# adb-pull layout: vendor-firmware/, vendor-firmware-mnt/, vendor-modules/,
# vendor-etc-firmware/). Returns 1 when the source prefix is not pulled.
blob_path_for_source() {
    local src="$1" base="" rel=""
    case "$src" in
        vendor/firmware_mnt/*)  base="vendor-firmware-mnt"; rel="${src#vendor/firmware_mnt/}" ;;
        vendor/firmware/*)      base="vendor-firmware"; rel="${src#vendor/firmware/}" ;;
        vendor/lib/modules/*)   base="vendor-modules"; rel="${src#vendor/lib/modules/}" ;;
        vendor/etc/firmware/*)  base="vendor-etc-firmware"; rel="${src#vendor/etc/firmware/}" ;;
        *) return 1 ;;
    esac
    printf '%s/%s/%s' "${BLOBS_DIR}" "${base}" "${rel}"
}

list_files() {
    log "G7 Power firmware manifest (firmware/g7power/manifest.yml)"
    log "device: g7power | codename: ocean | soc: sdm632 (msm8953 family)"
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
        warn "blobs/ does not exist yet — run --adb-pull on the G7 Power first."
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

adb_pull() {
    command -v adb >/dev/null 2>&1 || { err "adb not found — install android-tools/adb first."; exit 1; }
    if ! adb devices | grep -q "device$"; then
        err "No ADB device found. Is the G7 Power in Android (USB debugging) or a recovery with adb?"
        exit 1
    fi
    local adb_device dev_prop
    adb_device="$(adb get-serialno 2>/dev/null | tr -d '\r')"
    dev_prop="$(adb shell getprop ro.product.device 2>/dev/null | tr -d '\r')"
    log "Connected: serialno='${adb_device}' ro.product.device='${dev_prop}'"
    [ "${dev_prop}" = "ocean" ] || {
        err "Identity check failed: ro.product.device must be 'ocean', got '${dev_prop}'."
        err "REFUSING to pull from a different device."
        exit 1
    }
    log "Identity verified: ocean (serialno '${adb_device}')."

    mkdir -p "${BLOBS_DIR}"/{vendor-firmware,vendor-firmware-mnt,vendor-modules,vendor-etc-firmware}
    log "Pulling /vendor/firmware → blobs/vendor-firmware/ ..."
    adb pull /vendor/firmware "${BLOBS_DIR}/vendor-firmware/" || warn "pull of /vendor/firmware reported issues"
    log "Pulling /vendor/firmware_mnt → blobs/vendor-firmware-mnt/ ..."
    adb pull /vendor/firmware_mnt "${BLOBS_DIR}/vendor-firmware-mnt/" || warn "pull of /vendor/firmware_mnt reported issues"
    log "Pulling /vendor/lib/modules → blobs/vendor-modules/ ..."
    adb pull /vendor/lib/modules "${BLOBS_DIR}/vendor-modules/" || warn "pull of /vendor/lib/modules reported issues"
    log "Pulling /vendor/etc/firmware → blobs/vendor-etc-firmware/ ..."
    adb pull /vendor/etc/firmware "${BLOBS_DIR}/vendor-etc-firmware/" || warn "pull of /vendor/etc/firmware reported issues"

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
            warn "SKIP     ${src} (source prefix not pulled; e.g. vendor/etc — pull manually if needed)"
        fi
    done < <(manifest_tsv)
    log "adb-pull cross-reference: ${found} found, ${missing} missing."
    log "Now fill firmware/g7power/manifest.yml checksums from sha256 of blobs/ (--checksums)."
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
                err "MISSING  ${src} — required blob not found under blobs/ (run --adb-pull)"
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
        err "Fill real checksums in firmware/g7power/manifest.yml (Phase 0) or pass --force-pending."
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
        --adb-pull) DO_PULL=1; shift ;;
        --install) DO_INSTALL=1; shift ;;
        --force-pending) FORCE_PENDING=1; shift ;;
        --rootfs-staging) STAGING="$2"; shift 2 ;;
        --verbose|-v) VERBOSE=1; shift ;;
        *) err "Unknown option: $1"; usage; exit 1 ;;
    esac
done

# Device guard — g7power only. Explicit selection required (env or --device).
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" "$@"
[ "${NUXEL_DEVICE_KEY}" = "g7power" ] || {
    err "This script is ONLY for the Motorola Moto G7 Power (g7power). Got: ${NUXEL_DEVICE_KEY}"
    exit 1
}

[ -f "${MANIFEST}" ] || { err "Manifest not found: ${MANIFEST}"; exit 3; }
command -v python3 >/dev/null 2>&1 || { err "python3 required to parse the manifest"; exit 3; }

# Fail closed: every mode below consumes the manifest through a process
# substitution whose python3 exit status is masked, so an unparseable YAML
# would otherwise be read as an empty manifest and every mode would silently
# "succeed". Validate the manifest up front and abort (exit 3) on parse error.
if ! python3 -c 'import yaml,sys; yaml.safe_load(open(sys.argv[1], encoding="utf-8"))' "${MANIFEST}"; then
    err "Manifest parse error (python3/PyYAML): ${MANIFEST} — refusing to run any mode."
    exit 3
fi

# Protected partitions are NEVER firmware targets — print + enforce the
# denylist before any mode runs (safety invariant 4).
protected_partition_guard

# The inventory gate guards ONLY the real install path. --adb-pull is the
# acquisition step that FILLS the unknowns, so it stays unblocked.
if [ "${DO_INSTALL}" -eq 1 ]; then
    _check_g7power_inventory
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
    adb_pull
fi
if [ "${DO_INSTALL}" -eq 1 ]; then
    install_blobs
fi

if [ "${DO_LIST}${DO_VERIFY}${DO_CHECKSUMS}${DO_PULL}${DO_INSTALL}" = "00000" ]; then
    warn "No mode selected. Use --help to see available modes."
    exit 1
fi
