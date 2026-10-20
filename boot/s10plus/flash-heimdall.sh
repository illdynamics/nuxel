#!/usr/bin/env bash
# =============================================================================
# Nuxel Heimdall flash wrapper — Samsung Galaxy S10+ (beyond2lte, Exynos 9820)
#
# This is the ONLY sanctioned way to flash the S10+ from this repo. It uses the
# instrumented Heimdall fork (external/heimdall-nuxel) which:
#   * never treats a missing Odin end-session acknowledgement as success,
#   * refuses to write to a device unless this wrapper enables it,
#   * classifies the end-session failure (timeout / USB disconnect / malformed
#     packet / rejected command / delayed ack / still-in-Download-Mode),
#   * verifies the phone actually left Download Mode before reporting success.
#
# Flash targets are restricted to BOOT and USERDATA. PIT, DTB, DTBO, RECOVERY,
# EFS and every bootloader partition are never targeted. Repartitioning is not
# supported by this wrapper.
#
# Usage:
#   bash boot/s10plus/flash-heimdall.sh --device s10plus \
#       --pit-text docs/s10plus-device-pit-2026-10-14.txt \
#       --board-rev 26 --image-overlay "BEYOND2LTE EUR OPEN 26" \
#       --verified-block-bytes 4096 \
#       --boot  build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
#       --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
#
# Options:
#   --device s10plus             REQUIRED (any other key is refused)
#   --boot <img>                 v1 boot.img to flash to BOOT
#   --rootfs <img>               rootfs image to flash to USERDATA (DESTRUCTIVE)
#   --pit-text <file>            text from heimdall print-pit (preflight)
#   --board-rev <rev>            independently verified phone board revision
#   --image-overlay <string>     board overlay string embedded in the image
#   --verified-block-bytes <n>   independently verified byte unit (512/4096/8192)
#   --allow-unverified-board     proceed even if capacity/board rev are unverified
#   --session-timeout <ms>       bounded end-session timeout (50..600000)
#   --no-reboot                  leave the phone in Download Mode after flashing
#   --no-presence-check          skip the "did it leave Download Mode" probe
#   --use-stock-heimdall         use the stock binary (loses classification)
#   --dry-run                    print what would run; write nothing
#   --force                      skip the interactive confirmation
#   --i-accept-risk              additionally required together with --force
#   --help                       this help
#
# Safety: Knox is already tripped. Never attempt to re-lock or restore Knox.
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PROTECTED_PARTITIONS="efs efsg persist param up_param steady keystorage carrier cp_debug misc bootloader bootloader2 recovery dtb dtbo pit md5hdr vbmeta"

DEVICE_KEY=""; BOOT_IMG=""; ROOTFS_IMG=""; PIT_TEXT=""
BOARD_REV=""; IMAGE_OVERLAY=""; VERIFIED_BLOCK_BYTES=""
DRY_RUN=0; FORCE=0; ACCEPT_RISK=0; NO_REBOOT=0; NO_PRESENCE=0; USE_STOCK=0
ALLOW_UNVERIFIED=0; SESSION_TIMEOUT=""

log()  { echo "[s10plus-heimdall] $*"; }
err()  { echo "[s10plus-heimdall][error] $*" >&2; }
hint() { echo "[s10plus-heimdall][next] $*" >&2; }

usage() { sed -n '2,54p' "$0" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --device) DEVICE_KEY="$2"; shift 2 ;;
        --boot) BOOT_IMG="$2"; shift 2 ;;
        --rootfs) ROOTFS_IMG="$2"; shift 2 ;;
        --pit-text) PIT_TEXT="$2"; shift 2 ;;
        --board-rev) BOARD_REV="$2"; shift 2 ;;
        --image-overlay) IMAGE_OVERLAY="$2"; shift 2 ;;
        --verified-block-bytes) VERIFIED_BLOCK_BYTES="$2"; shift 2 ;;
        --session-timeout) SESSION_TIMEOUT="$2"; shift 2 ;;
        --allow-unverified-board) ALLOW_UNVERIFIED=1; shift ;;
        --no-reboot) NO_REBOOT=1; shift ;;
        --no-presence-check) NO_PRESENCE=1; shift ;;
        --use-stock-heimdall) USE_STOCK=1; shift ;;
        --dry-run) DRY_RUN=1; shift ;;
        --force) FORCE=1; shift ;;
        --i-accept-risk) ACCEPT_RISK=1; shift ;;
        *) err "unknown option: $1"; usage; exit 1 ;;
    esac
done

[ "${DEVICE_KEY}" = "s10plus" ] || { err "--device s10plus is required (got '${DEVICE_KEY}')."; exit 1; }
# shellcheck source=tools/nuxel-device-select.sh
source "${NUXEL_ROOT}/tools/nuxel-device-select.sh" --device "${DEVICE_KEY}"
[ "${NUXEL_DEVICE_KEY}" = "s10plus" ] || { err "device key mismatch"; exit 1; }

[ -n "${BOOT_IMG}" ] || [ -n "${ROOTFS_IMG}" ] || { err "give at least --boot or --rootfs"; exit 1; }
[ -z "${BOOT_IMG}" ]   || [ -f "${BOOT_IMG}" ]   || { err "boot image not found: ${BOOT_IMG}"; exit 1; }
[ -z "${ROOTFS_IMG}" ] || [ -f "${ROOTFS_IMG}" ] || { err "rootfs image not found: ${ROOTFS_IMG}"; exit 1; }

# ---------------------------------------------------------------------------
# Locate the instrumented fork first. The stock binary cannot classify the
# end-session failure and cannot enforce the write gate.
# ---------------------------------------------------------------------------
HEIMDALL=""
FORK="${NUXEL_HEIMDALL_BIN:-${NUXEL_ROOT}/build/heimdall-nuxel/out/heimdall-nuxel}"
IS_FORK=0

if [ "${USE_STOCK}" -eq 0 ] && [ -x "${FORK}" ]; then
    HEIMDALL="${FORK}"; IS_FORK=1
elif [ "${USE_STOCK}" -eq 0 ]; then
    for cand in heimdall-flash /opt/homebrew/bin/heimdall-flash heimdall; do
        if command -v "${cand}" >/dev/null 2>&1; then
            HEIMDALL="${cand}"; break
        fi
    done
    if [ -n "${HEIMDALL}" ]; then
        err "instrumented fork not found at: ${FORK}"
        err "refusing to fall back to the stock binary automatically."
        err "build it first:  external/heimdall-nuxel/scripts/build-and-test.sh"
        err "or pass --use-stock-heimdall to accept losing failure classification."
        exit 1
    fi
else
    for cand in heimdall-flash /opt/homebrew/bin/heimdall-flash heimdall; do
        if command -v "${cand}" >/dev/null 2>&1; then
            HEIMDALL="${cand}"; break
        fi
    done
fi

[ -n "${HEIMDALL}" ] || { err "no heimdall binary found"; exit 1; }
if [ "${IS_FORK}" -eq 0 ]; then
    err "WARNING: using a non-instrumented Heimdall. End-session failures will not"
    err "         be classified and the write gate is NOT enforced by the binary."
fi
log "heimdall: ${HEIMDALL} ($("${HEIMDALL}" version 2>/dev/null | head -1))"

# ---------------------------------------------------------------------------
# Preflight: BOOT/USERDATA capacity and board revision are checked SEPARATELY.
# ---------------------------------------------------------------------------
if [ -n "${PIT_TEXT}" ]; then
    [ -f "${PIT_TEXT}" ] || { err "PIT text not found: ${PIT_TEXT}"; exit 1; }
    PIT_CMD=(python3 "${NUXEL_ROOT}/tools/s10plus/check-device-pit.py" "${PIT_TEXT}")
    [ -z "${BOOT_IMG}" ] || PIT_CMD+=(--boot "${BOOT_IMG}")
    [ -z "${ROOTFS_IMG}" ] || PIT_CMD+=(--rootfs "${ROOTFS_IMG}")
    [ -z "${VERIFIED_BLOCK_BYTES}" ] || PIT_CMD+=(--verified-block-bytes "${VERIFIED_BLOCK_BYTES}")
    [ -z "${BOARD_REV}" ] || PIT_CMD+=(--board-rev "${BOARD_REV}")
    [ -z "${IMAGE_OVERLAY}" ] || PIT_CMD+=(--image-overlay "${IMAGE_OVERLAY}")

    set +e
    "${PIT_CMD[@]}"
    PIT_RC=$?
    set -e

    if [ "${PIT_RC}" -ne 0 ]; then
        err "PIT preflight verdict: NOT VERIFIED (exit ${PIT_RC})"
        if [ "${ALLOW_UNVERIFIED}" -eq 0 ]; then
            err "refusing to flash. Pass --allow-unverified-board only if you truly accept it."
            exit 1
        fi
        err "--allow-unverified-board given: continuing with an unverified board/capacity."
    fi
else
    err "WARNING: --pit-text not set. Capacity and structure were not checked."
    if [ "${ALLOW_UNVERIFIED}" -eq 0 ] && [ "${DRY_RUN}" -eq 0 ]; then
        err "refusing to flash without --pit-text (use --allow-unverified-board to override)."
        exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Build the heimdall command.
# ---------------------------------------------------------------------------
ARGS=(flash)
[ -z "${BOOT_IMG}" ]   || ARGS+=(--BOOT "${BOOT_IMG}")
[ -z "${ROOTFS_IMG}" ] || ARGS+=(--USERDATA "${ROOTFS_IMG}")
[ "$NO_REBOOT" -eq 0 ] || ARGS+=(--no-reboot)
[ "$NO_PRESENCE" -eq 0 ] || ARGS+=(--no-nuxel-presence-check)
if [ "${IS_FORK}" -eq 1 ]; then
    ARGS+=(--nuxel-trace-packets --usb-log-level debug --verbose)
    [ -z "${SESSION_TIMEOUT}" ] || ARGS+=(--nuxel-session-timeout "${SESSION_TIMEOUT}")
fi

log "Put the S10+ in Download Mode: Vol Down + Bixby + Power (hold)."
log "Command: ${HEIMDALL} ${ARGS[*]}"

if [ "${DRY_RUN}" -eq 1 ]; then
    log "[dry-run] not flashing."
    exit 0
fi

# Non-destructive presence probe before any confirmation.
"${HEIMDALL}" detect || { err "no Download-Mode device detected"; exit 1; }

if [ "${FORCE}" -eq 0 ]; then
    err "This overwrites BOOT and/or USERDATA on a real phone. That is destructive."
    printf 'Type FLASH (all caps) to continue: '
    read -r answer
    [ "${answer}" = "FLASH" ] || { err "aborted"; exit 1; }
else
    [ "${ACCEPT_RISK}" -eq 1 ] || { err "--force also requires --i-accept-risk"; exit 1; }
fi

LOG_DIR="${NUXEL_ROOT}/build/logs/s10plus"
mkdir -p "${LOG_DIR}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_LOG="${LOG_DIR}/heimdall-nuxel-${STAMP}.log"
log "logging to ${RUN_LOG}"

# Only now is the instrumented binary allowed to write to the device.
export NUXEL_ALLOW_DEVICE_WRITE=1

set +e
"${HEIMDALL}" "${ARGS[@]}" 2>&1 | tee "${RUN_LOG}"
RC=${PIPESTATUS[0]}
set -e

RESULT="$(grep -a 'NUXEL_SESSION_RESULT=' "${RUN_LOG}" | tail -1 | cut -d= -f2 || true)"
FAILURE_CLASS="$(grep -a 'NUXEL_FAILURE_CLASS=' "${RUN_LOG}" | tail -1 | cut -d= -f2 || true)"
INTERNAL_RC="$(grep -a 'NUXEL_EXIT_CODE=' "${RUN_LOG}" | tail -1 | cut -d= -f2 || true)"

log "heimdall exit=${RC} session_result='${RESULT:-unknown}' failure_class='${FAILURE_CLASS:-unknown}' internal_rc='${INTERNAL_RC:-unknown}'"

case "${RESULT}" in
    ok_acknowledged|ok_delayed_ack)
        if [ "${RC}" -ne 0 ]; then
            err "Contradiction: session reported '${RESULT}' but heimdall exited ${RC}."
            exit 5
        fi
        log "End-session handshake acknowledged AND the phone left Download Mode."
        log "That still does NOT prove the flashed image boots. Collect a kernel/boot log next."
        exit 0
        ;;
    timeout)
        err "TIMEOUT: the phone never sent the end-session acknowledgement."
        hint "Distinguish host-side timing from a device problem: retry once from a native"
        hint "USB port with --session-timeout 20000 and compare the [nuxel] packet trace."
        hint "A capture of a *successful* Odin flash of the same device is the missing evidence."
        exit 5 ;;
    usb_disconnect)
        err "USB DISCONNECT during the session. Check cable/port (no hub), then re-detect."
        hint "Do not reflash blindly; confirm whether the phone left Download Mode first."
        exit 5 ;;
    malformed_packet)
        err "MALFORMED PACKET: the reply was not a well-formed 8-byte control response."
        hint "Capture the raw [nuxel] RX hex lines and compare with an Odin USB capture."
        exit 5 ;;
    rejected_command)
        err "REJECTED COMMAND: the phone replied with an unexpected response type."
        hint "This is the protocol-mismatch class. It needs an Odin USB capture to resolve."
        exit 5 ;;
    reboot_timeout|reboot_disconnect)
        err "REBOOT step unconfirmed: the phone did not positively acknowledge the reboot."
        hint "The flash may or may not have committed. Inspect the phone before retrying."
        exit 5 ;;
    still_in_download_mode)
        err "STILL IN DOWNLOAD MODE: the transfer completed but the phone did not leave."
        hint "This is the classic S10+ symptom. Treat the flash as NOT committed."
        hint "Check board revision/DTBO match and S-Boot verification before any retry."
        exit 5 ;;
    ""|unknown)
        err "FLASH NOT CONFIRMED (exit=${RC}). See ${RUN_LOG}"
        if [ "${IS_FORK}" -eq 0 ]; then
            err "Stock Heimdall cannot classify the failure; build the fork for a real verdict."
        fi
        exit 5 ;;
    *)
        err "Unexpected session result '${RESULT}'. FLASH NOT CONFIRMED."
        exit 5 ;;
esac
