#!/bin/sh
#==============================================================================
# verity-setup.sh — initramfs hook for Nuxel mustang
#
# Opens the dm-verity protected root device. The root hash is taken from the
# kernel cmdline parameter `nuxel.verity_hash=<hex>`. When the hash is present
# this hook regenerates /etc/veritytab from images/config/verity.conf (which is
# usually baked into the initramfs at /etc/nuxel/verity.conf) and lets the
# initramfs init bring the verified device online.
#
# Placement in the pmOS/systemd initramfs:
#   * systemd-initrd: install into /usr/lib/initramfs-tools/hooks or the
#     systemd-initrd early-cpio; call from an early initrd service.
#   * pmOS/initramfs-tools: copy to /usr/share/initramfs-tools/hooks and drop
#     a script in scripts/local-top/ that sources this file.
#
# This file is also kept runnable as a standalone helper for debugging.
#==============================================================================
set -eu

# Configuration source (baked into initramfs at build time).
VERITY_CONF="${VERITY_CONF:-/etc/nuxel/verity.conf}"
VERITYTAB="/etc/veritytab"
SLOT=0

log()   { echo "[verity-setup] $*"; }
die()   { log "ERROR: $*"; exit 1; }

# Parse a simple KEY=VALUE config into positional variables.
nv_get() { # nv_get <var>
    awk -F= -v k="$1" '$1==k{sub(/^[^=]*=/,""); print; exit}' "$VERITY_CONF"
}

# Get current active slot (a/b) if the bootloader exposes it, else 0.
detect_slot() {
    # postmarketOS/U-Boot sets `boot_slot` (or androidboot.slot) in env/cmdline.
    s=""
    s="$( (cat /proc/cmdline 2>/dev/null || echo '') | tr ' ' '\n' \
        | sed -n 's/^androidboot\.slot=\([0-9a-f]\).*/\1/p' | head -1)"
    case "$s" in
        a) SLOT=0 ;;
        b) SLOT=1 ;;
        [01]) SLOT="$s" ;;
        *) SLOT=0; log "active slot unknown; assuming _a" ;;
    esac
}

apply_config() {
    [ -r "$VERITY_CONF" ] || die "missing ${VERITY_CONF}"
    VERITY_NAME="$(nv_get verity_device_name || echo verityroot)"
    DATA_DEV="$(nv_get verity_data_device || echo /dev/disk/by-partlabel/system_a)"
    HASH_DEV="$(nv_get verity_hash_device || echo /dev/disk/by-partlabel/hash_a)"
    ROOT_HASH="$(nv_get verity_root_hash || true)"
    ON_CORRUPT="$(nv_get verity_on_corruption || echo restart)"
    FEC_DEV="$(nv_get verity_fec_device || true)"
    EXTRA_ARGS="$(nv_get verity_extra_args || true)"
}

# Refresh data/hash device names to the active slot when using per-slot
# partitions (system_a/system_b + hash_a/hash_b).
apply_slot_to_devices() {
    suffix="a"
    [ "$SLOT" = "1" ] && suffix="b"
    DATA_DEV="$(printf '%s' "$DATA_DEV" | sed "s/_a$/_${suffix}/")"
    HASH_DEV="$(printf '%s' "$HASH_DEV" | sed "s/_a$/_${suffix}/")"
    log "active slot -> ${suffix}: DATA=${DATA_DEV} HASH=${HASH_DEV}"
}

write_veritytab() {
    # Regenerate the veritytab every boot from the freshly-selected slot and
    # root hash. We do NOT bail early here: after a slot flip or a changed
    # `nuxel.verity_hash=` cmdline we must not keep a stale mapping. (Only
    # skip if it already matches the current slot/hash to avoid needless
    # churn is handled by the caller comparing ROOT_HASH; otherwise rewrite.)
    line="${VERITY_NAME} ${DATA_DEV} ${HASH_DEV} ${ROOT_HASH}"
    # Append the on-corruption strategy to the VMC option field. veritysetup
    # accepts "restart_on_corruption" / "panic_on_corruption" as modern
    # chained options; map restart->restart_on_corruption.
    case "$ON_CORRUPT" in
        panic)            line="${line} panic_on_corruption" ;;
        restart|*)        line="${line} restart_on_corruption" ;;
    esac
    [ -n "$FEC_DEV" ] && line="${line} ${FEC_DEV}"
    [ -n "$EXTRA_ARGS" ] && line="${line} ${EXTRA_ARGS}"

    printf '%s\n' "$line" > "$VERITYTAB"
    log "veritytab written: ${VERITYTAB}"
    log "  ${line}"
}

get_cmdline_hash() {
    { cat /proc/cmdline 2>/dev/null || echo ''; } | tr ' ' '\n' \
        | sed -n 's/^nuxel\.verity_hash=\([0-9a-fA-F]*\).*/\1/p' | head -1
}

main() {
    apply_config
    detect_slot
    apply_slot_to_devices

    cmd_hash=""
    cmd_hash="$(get_cmdline_hash)"
    if [ -n "$cmd_hash" ]; then
        ROOT_HASH="$cmd_hash"
        log "using kernel-cmdline verity root hash (root of trust from bootloader)"
    else
        log "WARNING: no nuxel.verity_hash= in cmdline; falling back to baked-in hash"
        [ -n "${ROOT_HASH}" ] && [ "${ROOT_HASH}" != "@@ROOT_HASH@@" ] \
            || die "no verity root hash available (set nuxel.verity_hash= or bake one in)"
    fi

    write_veritytab
    log "dm-verity root mapping prepared. Continue boot."

    # When run under initramfs-tools style boot, systemd/dm-init consumes
    # veritytab automatically. For raw static initramfs, perform the mapping
    # directly here:
    if [ "${VERITY_SETUP_RUNNING:-no}" = "1" ]; then
        log "performing direct veritysetup open..."
        # --no-superblock is a legal *CLI* flag for the veritysetup command,
        # so it belongs here (and in VERITY_CLI_FLAGS), NOT in the veritytab
        # options field (which holds veritysetup option words).
        veritysetup open "${DATA_DEV}" "${VERITY_NAME}" "${HASH_DEV}" \
            "${ROOT_HASH}" ${EXTRA_ARGS} --no-superblock \
            || die "veritysetup open failed"
        log "opened /dev/mapper/${VERITY_NAME}"
    fi
}

main "$@"
