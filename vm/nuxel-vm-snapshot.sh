#!/usr/bin/env bash
# =============================================================================
# nuxel-vm-snapshot.sh
# UTM VM Snapshot Manager — create, list, restore, and delete snapshots
# for the Nuxel development VM on Apple Silicon.
#
# Usage:
#   ./nuxel-vm-snapshot.sh create "My Snapshot" "Optional description"
#   ./nuxel-vm-snapshot.sh list
#   ./nuxel-vm-snapshot.sh restore <snapshot-name>
#   ./nuxel-vm-snapshot.sh delete <snapshot-name>
#
# The script manages UTM snapshots via the `osascript` AppleScript interface
# to UTM's GUI, as well as via direct QEMU snapshot files for headless use.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_step()  { echo -e "${BLUE}[STEP]${NC}  $*"; }

VM_NAME="${VM_NAME:-Nuxel}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-${HOME}/Library/Containers/com.utmapp.UTM/Data/Documents/${VM_NAME}.utm/}"

# ── Detect macOS vs In-VM ─────────────────────────────────────────────────

is_macos() {
    [[ "$(uname -s)" == "Darwin" ]]
}

# ── AppleScript Helpers (macOS Host) ──────────────────────────────────────

utm_applescript() {
    local SCRIPT="$1"
    osascript -e "tell application \"UTM\" to ${SCRIPT}"
}

get_vm_id() {
    utm_applescript "id of virtual machine named \"${VM_NAME}\"" 2>/dev/null || echo ""
}

vm_is_running() {
    local STATE
    STATE=$(utm_applescript "status of virtual machine named \"${VM_NAME}\"" 2>/dev/null || echo "stopped")
    [[ "${STATE}" == "started" ]]
}

create_snapshot_utm() {
    local NAME="$1"
    local DESC="${2:-}"

    log_step "Creating UTM snapshot: ${NAME}"

    if ! vm_is_running; then
        log_warn "VM '${VM_NAME}' is not running. Snapshots require running state."
        log_info "Starting VM to take snapshot..."
        utm_applescript "start virtual machine named \"${VM_NAME}\""
        sleep 5
    fi

    # UTM's AppleScript API doesn't expose snapshot creation directly,
    # so we use the QEMU monitor fallback or manual path.

    local SNAPSHOT_PATH="${SNAPSHOT_DIR}/Snapshots/${NAME}"
    mkdir -p "${SNAPSHOT_PATH}"

    # Save snapshot metadata
    cat > "${SNAPSHOT_PATH}/metadata.json" << 'METADATA'
{
    "name": "SNAPSHOT_NAME",
    "description": "SNAPSHOT_DESC",
    "created_at": "SNAPSHOT_DATE",
    "vm_name": "VM_NAME",
    "tool": "nuxel-vm-snapshot.sh",
    "nuxel_version": "0.3.2-alpha"
}
METADATA
    sed -i '' "s/SNAPSHOT_NAME/${NAME}/g" "${SNAPSHOT_PATH}/metadata.json"
    sed -i '' "s/SNAPSHOT_DESC/${DESC:-Snapshot created by nuxel-vm-snapshot.sh}/g" "${SNAPSHOT_PATH}/metadata.json"
    sed -i '' "s/SNAPSHOT_DATE/$(date -u +%Y-%m-%dT%H:%M:%SZ)/g" "${SNAPSHOT_PATH}/metadata.json"
    sed -i '' "s/VM_NAME/${VM_NAME}/g" "${SNAPSHOT_PATH}/metadata.json"

    # Try QEMU monitor snapshot if VM is running
    if command -v qemu-img &>/dev/null && [ -f "${SNAPSHOT_DIR}/Images/disk-0.qcow2" ]; then
        log_info "Creating QEMU snapshot via qemu-img..."
        qemu-img snapshot -c "${NAME}" "${SNAPSHOT_DIR}/Images/disk-0.qcow2" 2>/dev/null && {
            log_info "QEMU snapshot created in disk image"
            return 0
        }
    fi

    log_info "Snapshot metadata saved to ${SNAPSHOT_PATH}"
    echo ""
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  Manual step required:                       │"
    echo "  │                                             │"
    echo "  │  To complete the snapshot in UTM:            │"
    echo "  │  1. Open UTM                                │"
    echo "  │  2. Select VM -> Manage -> Take Snapshot     │"
    echo "  │  3. Name: ${NAME}               │"
    echo "  │  4. Click OK                                │"
    echo "  └─────────────────────────────────────────────┘"
}

list_snapshots_utm() {
    log_step "Listing UTM snapshots..."

    if [ -d "${SNAPSHOT_DIR}/Snapshots" ]; then
        echo ""
        printf "  %-30s %-25s %s\n" "NAME" "CREATED" "DESCRIPTION"
        printf "  %-30s %-25s %s\n" "----" "-------" "-----------"
        for SNAPDIR in "${SNAPSHOT_DIR}/Snapshots"/*/; do
            if [ -f "${SNAPDIR}/metadata.json" ]; then
                local NAME DESC DATE
                NAME=$(python3 -c "import json; print(json.load(open('${SNAPDIR}/metadata.json')).get('name','unknown'))" 2>/dev/null || basename "${SNAPDIR}")
                DESC=$(python3 -c "import json; print(json.load(open('${SNAPDIR}/metadata.json')).get('description',''))" 2>/dev/null || echo "")
                DATE=$(python3 -c "import json; print(json.load(open('${SNAPDIR}/metadata.json')).get('created_at',''))" 2>/dev/null || echo "")
                printf "  %-30s %-25s %s\n" "${NAME}" "${DATE}" "${DESC}"
            else
                printf "  %-30s %-25s %s\n" "$(basename "${SNAPDIR}")" "" ""
            fi
        done
    fi

    # Also list QEMU snapshots
    if command -v qemu-img &>/dev/null && [ -f "${SNAPSHOT_DIR}/Images/disk-0.qcow2" ]; then
        echo ""
        log_info "QEMU disk snapshots:"
        qemu-img snapshot -l "${SNAPSHOT_DIR}/Images/disk-0.qcow2" 2>/dev/null || echo "  No QEMU snapshots found"
    fi

    # List via UTM AppleScript
    if is_macos; then
        echo ""
        log_info "UTM VM list:"
        utm_applescript "name of every virtual machine" 2>/dev/null | tr ',' '\n' | sed 's/^/  /' || true
    fi
}

restore_snapshot_utm() {
    local NAME="$1"

    log_step "Restoring snapshot: ${NAME}"

    # Check if VM is running
    if vm_is_running; then
        log_warn "VM '${VM_NAME}' is running. Stopping..."
        utm_applescript "stop virtual machine named \"${VM_NAME}\"" || true
        sleep 3
    fi

    # Try QEMU snapshot restore first
    if command -v qemu-img &>/dev/null && [ -f "${SNAPSHOT_DIR}/Images/disk-0.qcow2" ]; then
        log_info "Restoring QEMU snapshot..."
        qemu-img snapshot -a "${NAME}" "${SNAPSHOT_DIR}/Images/disk-0.qcow2" 2>/dev/null && {
            log_info "QEMU snapshot restored"
            log_info "Start the VM in UTM to verify"
            return 0
        }
    fi

    echo ""
    echo "  ┌─────────────────────────────────────────────┐"
    echo "  │  Manual step required:                       │"
    echo "  │                                             │"
    echo "  │  To restore snapshot in UTM:                 │"
    echo "  │  1. Open UTM                                │"
    echo "  │  2. Select VM                               │"
    echo "  │  3. Manage -> Restore Snapshot               │"
    echo "  │  4. Select: ${NAME}                 │"
    echo "  │  5. Click Restore                           │"
    echo "  └─────────────────────────────────────────────┘"
}

delete_snapshot_utm() {
    local NAME="$1"

    log_step "Deleting snapshot: ${NAME}"

    # Remove metadata directory
    local SNAPDIR="${SNAPSHOT_DIR}/Snapshots/${NAME}"
    if [ -d "${SNAPDIR}" ]; then
        rm -rf "${SNAPDIR}"
        log_info "Removed snapshot metadata: ${SNAPDIR}"
    fi

    # Remove QEMU snapshot
    if command -v qemu-img &>/dev/null && [ -f "${SNAPSHOT_DIR}/Images/disk-0.qcow2" ]; then
        qemu-img snapshot -d "${NAME}" "${SNAPSHOT_DIR}/Images/disk-0.qcow2" 2>/dev/null && {
            log_info "QEMU snapshot removed from disk image"
            return 0
        }
    fi

    log_info "Snapshot '${NAME}' deleted"
}

# ── In-VM Helpers (for running inside the guest) ──────────────────────────

create_snapshot_inguest() {
    local NAME="$1"
    local DESC="${2:-}"

    log_step "Creating system-state snapshot marker: ${NAME}"

    local MARKER_DIR="/var/lib/nuxel/snapshots"
    mkdir -p "${MARKER_DIR}"

    cat > "${MARKER_DIR}/${NAME}.json" << JSONEOF
{
    "name": "${NAME}",
    "description": "${DESC:-}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "kernel": "$(uname -r)",
    "nuxel_version": "0.3.2-alpha",
    "type": "guest-marker"
}
JSONEOF

    # Save package state
    if command -v rpm &>/dev/null; then
        rpm -qa --queryformat '%{NAME}-%{VERSION}-%{RELEASE}.%{ARCH}\n' > "${MARKER_DIR}/${NAME}-packages.txt"
    elif command -v dpkg &>/dev/null; then
        dpkg --get-selections > "${MARKER_DIR}/${NAME}-packages.txt"
    fi

    # Save service states
    systemctl list-units --type=service --all --no-legend > "${MARKER_DIR}/${NAME}-services.txt" 2>/dev/null || true

    # Save config state
    cp -r /etc/nuxel "${MARKER_DIR}/${NAME}-etc-nuxel" 2>/dev/null || true
    cp -r /var/lib/nuxel "${MARKER_DIR}/${NAME}-var-lib-nuxel" 2>/dev/null || true

    log_info "System state snapshot saved to ${MARKER_DIR}/${NAME}.json"
    log_info "Use this marker to verify rollback behavior during update testing"
}

list_snapshots_inguest() {
    local MARKER_DIR="/var/lib/nuxel/snapshots"
    if [ -d "${MARKER_DIR}" ]; then
        echo ""
        printf "  %-30s %-25s %s\n" "NAME" "CREATED" "DESCRIPTION"
        printf "  %-30s %-25s %s\n" "----" "-------" "-----------"
        for FILE in "${MARKER_DIR}"/*.json; do
            if [ -f "${FILE}" ]; then
                python3 -c "
import json, sys
d = json.load(open('${FILE}'))
print(f\"  {d.get('name','?'):30s} {d.get('created_at','?'):25s} {d.get('description','')}\")
" 2>/dev/null || echo "  $(basename "${FILE}" .json)"
            fi
        done
    else
        log_info "No snapshots found"
    fi
}

restore_snapshot_inguest() {
    local NAME="$1"
    log_warn "In-guest snapshot restore is a state marker only."
    log_info "To restore: revert the UTM VM to a previous snapshot."
    log_info "The marker file /var/lib/nuxel/snapshots/${NAME}.json describes"
    log_info "the expected state for verification after restore."
}

delete_snapshot_inguest() {
    local NAME="$1"
    local MARKER_DIR="/var/lib/nuxel/snapshots"
    rm -f "${MARKER_DIR}/${NAME}.json"
    rm -f "${MARKER_DIR}/${NAME}-packages.txt"
    rm -f "${MARKER_DIR}/${NAME}-services.txt"
    rm -rf "${MARKER_DIR}/${NAME}-etc-nuxel"
    rm -rf "${MARKER_DIR}/${NAME}-var-lib-nuxel"
    log_info "Snapshot '${NAME}' deleted"
}

# ── Main ──────────────────────────────────────────────────────────────────

main() {
    local COMMAND="${1:-}"
    shift 2>/dev/null || true

    case "${COMMAND}" in
        create)
            local NAME="${1:-}"
            local DESC="${2:-}"
            if [ -z "${NAME}" ]; then
                log_error "Usage: $0 create <name> [description]"
                exit 1
            fi
            if is_macos; then
                create_snapshot_utm "${NAME}" "${DESC}"
            else
                create_snapshot_inguest "${NAME}" "${DESC}"
            fi
            ;;
        list)
            if is_macos; then
                list_snapshots_utm
            else
                list_snapshots_inguest
            fi
            ;;
        restore)
            local NAME="${1:-}"
            if [ -z "${NAME}" ]; then
                log_error "Usage: $0 restore <snapshot-name>"
                exit 1
            fi
            if is_macos; then
                restore_snapshot_utm "${NAME}"
            else
                restore_snapshot_inguest "${NAME}"
            fi
            ;;
        delete)
            local NAME="${1:-}"
            if [ -z "${NAME}" ]; then
                log_error "Usage: $0 delete <snapshot-name>"
                exit 1
            fi
            if is_macos; then
                delete_snapshot_utm "${NAME}"
            else
                delete_snapshot_inguest "${NAME}"
            fi
            ;;
        *)
            echo ""
            echo "Nuxel VM Snapshot Manager"
            echo ""
            echo "Usage:"
            echo "  $0 create <name> [description]   Create a new snapshot"
            echo "  $0 list                           List all snapshots"
            echo "  $0 restore <name>                 Restore a snapshot"
            echo "  $0 delete <name>                  Delete a snapshot"
            echo ""
            echo "Examples:"
            echo "  $0 create baseline \"Clean install with Phosh\""
            echo "  $0 create after-update \"After atomic update test\""
            echo "  $0 list"
            echo "  $0 restore baseline"
            echo ""
            echo "On macOS host: Manages UTM VM snapshots."
            echo "Inside guest:  Creates state markers for update/rollback testing."
            echo ""
            ;;
    esac
}

main "$@"
