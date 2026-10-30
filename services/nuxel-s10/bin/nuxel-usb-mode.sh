#!/bin/sh
# Nuxel USB connection-mode helper (PWNAGE-34000).
#
# Safe userspace-only mode switch.  It NEVER:
#   * writes a block device, flashes a partition or touches the bootloader;
#   * exports a mounted live root or home filesystem as raw USB mass storage;
#   * stops the initramfs USB CDC-ACM console (the recovery route).
#
# For Charging it records the safe charging state and returns success.
# For File Transfer it probes for a genuinely supported transfer endpoint and
# only reports success if that endpoint actually activated.  Without a supported
# MTP/FFS stack it records the exact blocker and returns failure, so the UI can
# never show the file-transfer icon for an unsupported mode.
set -u
umask 022

MODE="${1:-}"
STATE=/run/nuxel/usb-mode.state
LOG=/var/lib/nuxel/usb-mode.log
mkdir -p /run/nuxel /var/lib/nuxel 2>/dev/null || true

say() { echo "$(date -u +%FT%TZ) nuxel-usb-mode: $*" >>"$LOG" 2>/dev/null || true; }
write_state() {
    # JSON is hand-rolled here because jq is not guaranteed on the handset.
    printf '{"mode":"%s","active":%s,"endpoint_state":"%s","source":"%s","error":%s}\n' \
        "$1" "$2" "$3" "$4" "$5" >"$STATE.new" 2>/dev/null || return 1
    mv -f "$STATE.new" "$STATE" 2>/dev/null || { cat "$STATE.new" >"$STATE"; rm -f "$STATE.new"; }
}

json_err() {
    if [ "$1" = "null" ]; then
        printf 'null'
    else
        printf '"%s"' "$(printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g')"
    fi
}

charging_mode() {
    say "charging: recording safe charging state (console untouched)"
    write_state charging false inactive charging-mode null
    say "charging: state recorded rc=$?"
    exit 0
}

file_transfer_mode() {
    say "file_transfer: probing for a supported endpoint"
    # A supported MTP responder must exist AND the kernel must expose a usable
    # configfs MTP function.  We never invent a capability.
    have_mtp=0
    for b in umtprd mtp-server jmtpfs; do
        if command -v "$b" >/dev/null 2>&1; then have_mtp=1; say "file_transfer: found responder $b"; break; fi
    done

    have_ffs_mtp=0
    cfg=/sys/kernel/config/usb_gadget
    if [ -d "$cfg" ]; then
        for g in "$cfg"/*/functions; do
            [ -d "$g" ] || continue
            for f in "$g"/*; do
                case "$(basename "$f")" in
                    ffs.mtp*|mtp.*|mtp.usb*) have_ffs_mtp=1; say "file_transfer: found gadget function $(basename "$f")";;
                esac
            done
        done
    fi

    if [ "$have_mtp" -eq 0 ]; then
        err="unsupported: no MTP responder installed (umtprd/mtp-server/jmtpfs absent)"
        say "file_transfer: $err"
        write_state file_transfer false unsupported "unsupported:no-mtp-responder" "$(json_err "$err")"
        exit 1
    fi
    if [ "$have_ffs_mtp" -eq 0 ]; then
        err="unsupported: kernel exposes no configfs MTP function on this boot"
        say "file_transfer: $err"
        write_state file_transfer false unsupported "unsupported:no-ffs-mtp-function" "$(json_err "$err")"
        exit 1
    fi

    # A supported endpoint exists.  Starting/configuring it is deliberately left
    # to the dedicated integration helper (NUXEL_USB_MODE_IMPLEMENTATION); this
    # script refuses to guess a gadget layout that could conflict with the
    # console.  It records the truth: the endpoint was NOT activated here.
    err="endpoint detected but activation helper is not configured; file transfer was not activated"
    say "file_transfer: $err"
    write_state file_transfer false not_activated "detected:activation-not-configured" "$(json_err "$err")"
    exit 1
}

case "$MODE" in
    charging) charging_mode ;;
    file_transfer|file-transfer) file_transfer_mode ;;
    *)
        say "refusing unknown mode: ${MODE:-<empty>}"
        write_state charging false inactive "refused:unknown-mode" '"unknown mode"'
        exit 2
        ;;
esac
