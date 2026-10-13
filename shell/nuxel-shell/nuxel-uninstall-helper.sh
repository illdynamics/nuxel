#!/usr/bin/env bash
# =============================================================================
# nuxel-uninstall-helper.sh
# Complete app uninstall with full data wipe for Nuxel OS.
#
# Usage:
#   sudo ./nuxel-uninstall-helper.sh <app-id>
#
# Safety:
#   - Requires root (data wipe touches system-owned directories)
#   - Dry-run mode: ./nuxel-uninstall-helper.sh --dry-run <app-id>
#   - Confirms before destructive actions
#   - Rejects dangerous app_ids (empty, path-traversal, or system paths)
#
# What it wipes:
#   1. Flatpak installation (if app was Flatpak-based)
#   2. App data directory (/var/app/<app-id>/)
#   3. Permission grants (/var/lib/nuxel/permissions/<safe-id>.json)
#   4. .desktop entry and icon caches
#   5. Cgroup if exists (under /sys/fs/cgroup/nuxel/<safe-id>/)
#   6. nftables rules for the app
#   7. Logs the uninstall action
#
# Returns 0 on successful uninstall, 1 on failure.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${GREEN}[INFO]${NC}    $*"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC}    $*"; }
log_error()   { echo -e "${RED}[ERROR]${NC}   $*"; }
log_step()    { echo -e "${BLUE}[STEP]${NC}    $*"; }
log_dryrun()  { echo -e "${CYAN}[DRY-RUN]${NC} $*"; }

# ── Configuration ──────────────────────────────────────────────────────────

NUXEL_APP_DIR="${NUXEL_APP_DIR:-/var/app}"
NUXEL_PERMISSIONS_DIR="${NUXEL_PERMISSIONS_DIR:-/var/lib/nuxel/permissions}"
NUXEL_LOG_DIR="${NUXEL_LOG_DIR:-/var/log/nuxel}"
NUXEL_CGROUP_BASE="${NUXEL_CGROUP_BASE:-/sys/fs/cgroup/nuxel}"
UNINSTALL_LOG="${NUXEL_LOG_DIR}/uninstall.log"
DRY_RUN=false

# ── Argument Parsing ───────────────────────────────────────────────────────

usage() {
    echo ""
    echo "Nuxel App Uninstall Helper — Full data wipe"
    echo ""
    echo "Usage:"
    echo "  $0 [--dry-run] <app-id>"
    echo ""
    echo "Arguments:"
    echo "  <app-id>   Application identifier (e.g., org.nuxel.Calendar)"
    echo ""
    echo "Options:"
    echo "  --dry-run  Show what would be deleted without actually deleting"
    echo ""
    echo "Examples:"
    echo "  sudo $0 org.nuxel.Calendar"
    echo "  sudo $0 --dry-run org.nuxel.Mail"
    echo ""
    exit 0
}

if [ $# -eq 0 ]; then
    usage
fi

if [ "${1:-}" = "--dry-run" ]; then
    DRY_RUN=true
    shift
fi

if [ $# -lt 1 ] || [ -z "${1:-}" ]; then
    log_error "Missing app-id argument"
    usage
fi

APP_ID="$1"
SAFE_ID="${APP_ID//\//_}"
SAFE_ID="${SAFE_ID//\.\./_}"

# ── Safety Checks ──────────────────────────────────────────────────────────

safety_check() {
    # Check 1: Must run as root
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root (sudo)"
        echo "  Permissions, cgroups, and nftables operations require root."
        exit 1
    fi

    # Check 2: App ID is not empty
    if [ -z "${APP_ID}" ]; then
        log_error "App ID cannot be empty"
        exit 1
    fi

    # Check 3: No path traversal
    if echo "${APP_ID}" | grep -q '\.\.'; then
        log_error "App ID contains path traversal sequence: ${APP_ID}"
        exit 1
    fi

    # Check 4: No absolute paths
    if echo "${APP_ID}" | grep -q '^/'; then
        log_error "App ID looks like an absolute path: ${APP_ID}"
        exit 1
    fi

    # Check 5: Reject known system app_ids that must not be uninstalled
    local SYSTEM_APPS=(
        "org.nuxel.settings"
        "org.nuxel.Home"
        "org.nuxel.dialer"
        "org.nuxel.firstboot"
        "org.nuxel.shell"
    )
    for sys_app in "${SYSTEM_APPS[@]}"; do
        if [ "${APP_ID}" = "${sys_app}" ]; then
            log_error "Refusing to uninstall system app: ${APP_ID}"
            echo "  System apps are required for Nuxel OS operation."
            echo "  To remove this app, rebuild the system image without it."
            exit 1
        fi
    done

    # Check 6: SAFE_ID is not "/", "*", or empty
    if [ -z "${SAFE_ID}" ] || [ "${SAFE_ID}" = "/" ] || [ "${SAFE_ID}" = "*" ]; then
        log_error "Invalid SAFE_ID derived from app_id: ${SAFE_ID}"
        exit 1
    fi

    log_info "Safety checks passed for app: ${APP_ID}"
}

confirm_uninstall() {
    echo ""
    echo "┌────────────────────────────────────────────────────────────┐"
    echo "│                   ⚠  CONFIRM UNINSTALL                     │"
    echo "├────────────────────────────────────────────────────────────┤"
    echo "│"
    echo "│  App:       ${APP_ID}"
    echo "│  Data dir:  ${NUXEL_APP_DIR}/${SAFE_ID}/"
    echo "│  Perms:     ${NUXEL_PERMISSIONS_DIR}/${SAFE_ID}.json"
    echo "│"
    echo "│  THIS WILL PERMANENTLY DELETE:"
    echo "│    • App installation (Flatpak)"
    echo "│    • App data directory"
    echo "│    • All permission grants"
    echo "│    • Desktop entries and icons"
    echo "│    • Network rules and cgroup"
    echo "│"
    echo "└────────────────────────────────────────────────────────────┘"
    echo ""

    if [ "${DRY_RUN}" = true ]; then
        log_warn "DRY RUN: Would prompt for confirmation here"
        return 0
    fi

    read -r -p "Are you sure you want to uninstall '${APP_ID}'? [y/N] " response
    case "${response}" in
        [yY]|[yY][eE][sS])
            log_info "Confirmation received. Proceeding with uninstall..."
            return 0
            ;;
        *)
            log_info "Uninstall cancelled by user"
            exit 0
            ;;
    esac
}

# ── Uninstall Steps ────────────────────────────────────────────────────────

uninstall_flatpak() {
    log_step "Step 1: Removing Flatpak installation..."

    if command -v flatpak &>/dev/null; then
        if flatpak info "${APP_ID}" &>/dev/null 2>&1; then
            if [ "${DRY_RUN}" = true ]; then
                log_dryrun "flatpak uninstall --delete-data ${APP_ID}"
                log_dryrun "flatpak uninstall --unused"
            else
                log_info "Removing Flatpak app: ${APP_ID}"
                flatpak uninstall --delete-data --noninteractive "${APP_ID}" 2>&1 || {
                    log_warn "Flatpak uninstall reported issues (may already be partially removed)"
                }
                # Clean up unused runtimes
                flatpak uninstall --unused --noninteractive 2>/dev/null || true
                log_info "Flatpak app removed"
            fi
        else
            log_info "Flatpak app '${APP_ID}' not found. Skipping."
        fi
    else
        log_info "Flatpak not installed. Skipping Flatpak cleanup."
    fi
}

remove_app_data() {
    local APP_DATA_DIR="${NUXEL_APP_DIR}/${SAFE_ID}"

    log_step "Step 2: Removing app data directory..."

    if [ -d "${APP_DATA_DIR}" ]; then
        if [ "${DRY_RUN}" = true ]; then
            log_dryrun "rm -rf ${APP_DATA_DIR}/"
        else
            log_info "Removing app data: ${APP_DATA_DIR}"
            rm -rf "${APP_DATA_DIR}"
            log_info "App data directory removed"
        fi
    else
        log_info "App data directory not found: ${APP_DATA_DIR}. Skipping."
    fi
}

remove_permissions() {
    local PERMS_FILE="${NUXEL_PERMISSIONS_DIR}/${SAFE_ID}.json"

    log_step "Step 3: Removing permission grants..."

    if [ -f "${PERMS_FILE}" ]; then
        if [ "${DRY_RUN}" = true ]; then
            log_dryrun "rm -f ${PERMS_FILE}"
        else
            log_info "Removing permissions file: ${PERMS_FILE}"
            rm -f "${PERMS_FILE}"
            log_info "Permission grants removed"
        fi
    else
        log_info "Permissions file not found: ${PERMS_FILE}. Skipping."
    fi

    # Also remove any legacy permission files
    local LEGACY_PERMS
    LEGACY_PERMS=$(find "${NUXEL_PERMISSIONS_DIR}" -name "${SAFE_ID}*" -type f 2>/dev/null || true)
    if [ -n "${LEGACY_PERMS}" ]; then
        if [ "${DRY_RUN}" = true ]; then
            echo "${LEGACY_PERMS}" | while read -r f; do
                log_dryrun "rm -f ${f}"
            done
        else
            echo "${LEGACY_PERMS}" | while read -r f; do
                rm -f "${f}"
                log_info "Removed legacy permission file: ${f}"
            done
        fi
    fi
}

remove_desktop_entries() {
    log_step "Step 4: Removing desktop entries and icon cache..."

    local XDG_DIRS=(
        "/usr/share/applications"
        "/usr/local/share/applications"
        "${HOME}/.local/share/applications"
        "/var/lib/flatpak/exports/share/applications"
    )

    # Remove .desktop files matching the app
    for dir in "${XDG_DIRS[@]}"; do
        if [ -d "${dir}" ]; then
            # Match app_id.desktop or any variant with app_id in name
            local DESKTOP_FILES
            DESKTOP_FILES=$(find "${dir}" -name "${APP_ID}*.desktop" -type f 2>/dev/null || true)
            if [ -n "${DESKTOP_FILES}" ]; then
                echo "${DESKTOP_FILES}" | while read -r f; do
                    if [ "${DRY_RUN}" = true ]; then
                        log_dryrun "rm ${f}"
                    else
                        rm -f "${f}"
                        log_info "Removed desktop entry: ${f}"
                    fi
                done
            fi

            # Also match by app name in .desktop files
            local GREP_FILES
            GREP_FILES=$(grep -rl "exec.*${APP_ID}" "${dir}" 2>/dev/null || true)
            if [ -n "${GREP_FILES}" ]; then
                echo "${GREP_FILES}" | while read -r f; do
                    if [ "${DRY_RUN}" = true ]; then
                        log_dryrun "rm ${f} (matched by Exec line)"
                    else
                        rm -f "${f}"
                        log_info "Removed desktop entry (matched by Exec): ${f}"
                    fi
                done
            fi
        fi
    done

    # Clean icon cache
    if [ "${DRY_RUN}" = false ]; then
        if command -v gtk-update-icon-cache &>/dev/null; then
            for icondir in /usr/share/icons/hicolor /usr/share/icons/Adwaita; do
                if [ -d "${icondir}" ]; then
                    gtk-update-icon-cache -f -t "${icondir}" 2>/dev/null || true
                fi
            done
        fi

        # Update desktop database
        if command -v update-desktop-database &>/dev/null; then
            for dir in "${XDG_DIRS[@]}"; do
                if [ -d "${dir}" ]; then
                    update-desktop-database -q "${dir}" 2>/dev/null || true
                fi
            done
        fi

        log_info "Desktop entry cache updated"
    else
        log_dryrun "gtk-update-icon-cache (for icon themes)"
        log_dryrun "update-desktop-database (for desktop dirs)"
    fi
}

remove_cgroup() {
    local CGROUP_PATH="${NUXEL_CGROUP_BASE}/${SAFE_ID}"

    log_step "Step 5: Removing cgroup..."

    if [ -d "${CGROUP_PATH}" ]; then
        if [ "${DRY_RUN}" = true ]; then
            log_dryrun "rmdir ${CGROUP_PATH} (cgroup v2)"
        else
            log_info "Removing cgroup: ${CGROUP_PATH}"

            # Kill any remaining processes in the cgroup
            if [ -f "${CGROUP_PATH}/cgroup.procs" ]; then
                local PIDS
                PIDS=$(cat "${CGROUP_PATH}/cgroup.procs" 2>/dev/null || true)
                if [ -n "${PIDS}" ]; then
                    log_warn "Killing remaining processes in cgroup: ${PIDS}"
                    echo "${PIDS}" | while read -r pid; do
                        kill -15 "${pid}" 2>/dev/null || true
                    done
                    sleep 1
                    # Force kill if still alive
                    echo "${PIDS}" | while read -r pid; do
                        kill -9 "${pid}" 2>/dev/null || true
                    done
                fi
            fi

            # Remove cgroup directory
            rmdir "${CGROUP_PATH}" 2>/dev/null || {
                log_warn "Could not remove cgroup directory (may need to migrate processes first)"
                # Try writing to cgroup.kill first
                if [ -f "${CGROUP_PATH}/cgroup.kill" ]; then
                    echo 1 > "${CGROUP_PATH}/cgroup.kill" 2>/dev/null || true
                    sleep 1
                    rmdir "${CGROUP_PATH}" 2>/dev/null || true
                fi
            }

            if [ -d "${CGROUP_PATH}" ]; then
                log_warn "Cgroup directory still exists after removal attempt"
            else
                log_info "Cgroup removed"
            fi
        fi
    else
        log_info "Cgroup not found: ${CGROUP_PATH}. Skipping."
    fi
}

remove_nftables_rules() {
    log_step "Step 6: Removing nftables rules..."

    if command -v nft &>/dev/null; then
        # Check if app-specific chains exist in the nuxel-apps table
        local APP_CHAIN_INPUT="nuxel-app-input-${SAFE_ID}"
        local APP_CHAIN_OUTPUT="nuxel-app-output-${SAFE_ID}"

        if [ "${DRY_RUN}" = true ]; then
            log_dryrun "nft delete chain inet nuxel-apps ${APP_CHAIN_INPUT} (if exists)"
            log_dryrun "nft delete chain inet nuxel-apps ${APP_CHAIN_OUTPUT} (if exists)"
        else
            # Remove app-specific chains
            for chain in "${APP_CHAIN_INPUT}" "${APP_CHAIN_OUTPUT}"; do
                if nft list chain inet nuxel-apps "${chain}" &>/dev/null 2>&1; then
                    # Flush rules first
                    nft flush chain inet nuxel-apps "${chain}" 2>/dev/null || true
                    # Delete the chain
                    nft delete chain inet nuxel-apps "${chain}" 2>/dev/null || {
                        log_warn "Could not delete nftables chain: ${chain}"
                    }
                    log_info "Removed nftables chain: ${chain}"
                fi
            done

            # Also check for any rules in the base chain that reference this app
            # (for apps that were added via direct rule insertion)
            if nft list chain inet nuxel-apps app-output &>/dev/null 2>&1; then
                nft -a list chain inet nuxel-apps app-output 2>/dev/null | \
                    grep -i "${SAFE_ID}" | \
                    sed 's/.*handle //' | \
                    while read -r handle; do
                        if [ -n "${handle}" ] && [ "${handle}" -gt 0 ] 2>/dev/null; then
                            nft delete rule inet nuxel-apps app-output handle "${handle}" 2>/dev/null || true
                            log_info "Removed nftables rule handle ${handle} for ${SAFE_ID}"
                        fi
                    done || true
            fi
        fi
    else
        log_info "nftables not installed. Skipping."
    fi
}

log_uninstall() {
    log_step "Step 7: Logging uninstall action..."

    mkdir -p "${NUXEL_LOG_DIR}"

    local TIMESTAMP
    TIMESTAMP=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    local LOG_ENTRY="[${TIMESTAMP}] UNINSTALL: app_id=${APP_ID} safe_id=${SAFE_ID} status=${1} user=${SUDO_USER:-${USER}}"

    if [ "${DRY_RUN}" = true ]; then
        log_dryrun "Append to ${UNINSTALL_LOG}: ${LOG_ENTRY}"
    else
        echo "${LOG_ENTRY}" >> "${UNINSTALL_LOG}"
        log_info "Uninstall logged to ${UNINSTALL_LOG}"
    fi
}

# ── Post-Uninstall Verification ────────────────────────────────────────────

verify_cleanup() {
    log_step "Verifying cleanup..."

    local ISSUES=0

    # Check app data
    if [ -d "${NUXEL_APP_DIR}/${SAFE_ID}" ]; then
        log_warn "App data directory still exists: ${NUXEL_APP_DIR}/${SAFE_ID}"
        ISSUES=$((ISSUES + 1))
    fi

    # Check permissions
    if [ -f "${NUXEL_PERMISSIONS_DIR}/${SAFE_ID}.json" ]; then
        log_warn "Permissions file still exists: ${NUXEL_PERMISSIONS_DIR}/${SAFE_ID}.json"
        ISSUES=$((ISSUES + 1))
    fi

    # Check cgroup
    if [ -d "${NUXEL_CGROUP_BASE}/${SAFE_ID}" ]; then
        log_warn "Cgroup still exists: ${NUXEL_CGROUP_BASE}/${SAFE_ID}"
        ISSUES=$((ISSUES + 1))
    fi

    if [ "${ISSUES}" -eq 0 ]; then
        log_info "All traces of '${APP_ID}' have been removed"
        return 0
    else
        log_warn "${ISSUES} cleanup issue(s) remain"
        return 1
    fi
}

# ── Main ───────────────────────────────────────────────────────────────────

main() {
    echo ""
    echo "=============================================="
    echo "  Nuxel App Uninstall Helper"
    echo "=============================================="
    echo ""

    safety_check

    echo "  App ID:       ${APP_ID}"
    echo "  Safe ID:      ${SAFE_ID}"
    echo "  Dry run:      ${DRY_RUN}"
    echo ""

    if [ "${DRY_RUN}" = false ]; then
        confirm_uninstall
    fi

    echo ""
    if [ "${DRY_RUN}" = true ]; then
        log_warn "DRY RUN MODE — No changes will be made"
        echo ""
    fi

    uninstall_flatpak
    echo ""

    remove_app_data
    echo ""

    remove_permissions
    echo ""

    remove_desktop_entries
    echo ""

    remove_cgroup
    echo ""

    remove_nftables_rules
    echo ""

    if [ "${DRY_RUN}" = false ]; then
        log_uninstall "success"
        echo ""

        log_info "Running post-uninstall verification..."
        verify_cleanup
        local RESULT=$?
        echo ""

        if [ "${RESULT}" -eq 0 ]; then
            echo "=============================================="
            echo -e "${GREEN}  Uninstall complete: ${APP_ID}${NC}"
            echo "=============================================="
        else
            echo "=============================================="
            echo -e "${YELLOW}  Uninstall finished with warnings: ${APP_ID}${NC}"
            echo "=============================================="
        fi

        return "${RESULT}"
    else
        log_info "Dry run complete. No changes were made."
        return 0
    fi
}

main "$@"
