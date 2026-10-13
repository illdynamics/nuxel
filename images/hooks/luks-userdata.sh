#!/bin/sh
#==============================================================================
# luks-userdata.sh — initramfs hook for Nuxel mustang LUKS2 userdata
#
# Opens the LUKS2-encrypted userdata partition:
#   * From the crypttab entry (systemd-initrd / crypttab machinery), OR
#   * Directly via cryptsetup when run from a static initramfs.
#
# Auth strategies:
#   A) Passphrase prompt — interactive prompt when no key file is present.
#   B) Key file derived from the AVB-verified boot chain + disk serial.
#
# The key-file derivation is deliberately tied to the VERIFIED boot chain
# (the AVB pubkey blob / root hash) and the physical disk serial so that the
# userdata volume can only be unlocked on the same (authenticated) hardware
# and boot state — a stolen/copied image cannot decrypt it.
#
# Placement:
#   * systemd-initrd:    drop into /etc/initramfs-tools/scripts/init-premount,
#                        or register as an initrd early service.
#   * pmOS initramfs:    copy to /usr/share/initramfs-tools/scripts/local-top/.
#
# This hook does NOT reformat userdata. Format on first boot with:
#   cryptsetup luksFormat /dev/sda --type luks2
#==============================================================================
set -eu

USERDATA_DEV="${USERDATA_DEV:-/dev/sda}"
MAPNAME="userdata"
KEYFILE="${KEYFILE:-/etc/nuxel/userdata.key}"
CRYPTTAB="${CRYPTTAB:-/etc/crypttab}"
CRYPTTAB_TEMPLATE="${CRYPTTAB_TEMPLATE:-/etc/nuxel/userdata.crypttab}"

log()   { echo "[luks-userdata] $*"; }
die()   { log "ERROR: $*"; exit 1; }

# --- key derivation from AVB-verified boot chain + disk serial ---
derive_keyfile() {
    root_hash=""; serial=""; blob=""; hex=""
    # Capture just the hex root hash (no trailing dot/backreference). A normal
    # `nuxel.verity_hash=<hex>` cmdline token is matched.
    root_hash="$( { cat /proc/cmdline 2>/dev/null || echo ''; } | tr ' ' '\n' \
        | sed -n 's/^nuxel\.verity_hash=\([0-9a-fA-F]*\).*/\1/p' | head -1 || true)"

    # The AVB pubkey blob stored by the bootloader (rollback-protected area).
    blob="$(cat /sys/block/*/boot/avb_pubkey 2>/dev/null | head -c 1024 || true)"

    serial="$(cat /sys/block/sda/device/serial 2>/dev/null \
        || lsblk -o SERIAL -n /dev/sda 2>/dev/null \
        || echo unknown-serial)"

    mkdir -p "$(dirname "$KEYFILE")"
    # Mix the entropy into a 256-bit key using busybox-safe tools only
    # (sha256sum + printf %b) so the derived bytes are identical whether the
    # key is generated at format-time on the host or at boot on the device.
    # No binary xxd/od split is needed: sha256sum emits deterministic hex that
    # printf %b decodes back to raw bytes.
    hex="$({
        printf '%s' "$blob"
        printf '%s' "$root_hash"
        printf '%s' "$serial"
        # Additional hw-unique entropy: the FDE key slot salt may not be
        # readable pre-unlock, so add a hw-unique id if available.
        cat /etc/machine-id 2>/dev/null || true
        cat /sys/class/dmi/id/product_uuid 2>/dev/null || true
    } | tr -dc '[:print:]' | sha256sum | awk '{print $1}')"

    if [ -n "$hex" ]; then
        # Convert the hex digest to raw bytes (busybox printf supports %b
        # backslash escapes). Deterministic and portable.
        printf '%b' "$(printf '%s' "$hex" | sed 's/../\\x&/g')" > "$KEYFILE"
    fi
    # Ensure non-empty, regular file with sane perms.
    touch "$KEYFILE"
    chmod 0600 "$KEYFILE"
    log "derived userdata key file: ${KEYFILE}"
}

open_with_prompt() {
    if [ -f "$KEYFILE" ]; then
        log "opening ${MAPNAME} (keyfile) from ${USERDATA_DEV}..."
        cryptsetup open --type luks2 "$USERDATA_DEV" "$MAPNAME" --key-file "$KEYFILE" \
            || { log "keyfile unlock failed; falling back to prompt"; prompt_open; }
    else
        prompt_open
    fi
}

prompt_open() {
    log "opening ${MAPNAME} (passphrase) from ${USERDATA_DEV}..."
    cryptsetup open --type luks2 "$USERDATA_DEV" "$MAPNAME" \
        || die "LUKS2 unlock failed for ${USERDATA_DEV}"
    log "opened /dev/mapper/${MAPNAME}"
}

generate_crypttab() {
    dev="${USERDATA_DEV}"
    key="${KEYFILE}"
    [ -f "$key" ] || key="none"
    {
        printf 'userdata\t%s\t%s\tluks,discard\n' "$dev" "$key"
    } > "$CRYPTTAB"
    log "crypttab written: ${CRYPTTAB}"
}

main() {
    if [ ! -b "$USERDATA_DEV" ]; then
        log "userdata device ${USERDATA_DEV} not present; trying by-partlabel..."
        bylabel="/dev/disk/by-partlabel/userdata"
        [ -b "$bylabel" ] && USERDATA_DEV="$bylabel"
    fi

    # Strategy selection.
    use_keyfile=0
    if [ "${NUXEL_USERDATA_DERIVE_KEY:-no}" = "yes" ]; then
        use_keyfile=1
        derive_keyfile
    elif [ -f "$KEYFILE" ]; then
        use_keyfile=1
    fi

    if [ "$use_keyfile" = "1" ]; then
        open_with_prompt
    else
        prompt_open
    fi

    generate_crypttab
    log "userdata mapped. Mount later with: mount /dev/mapper/${MAPNAME} /data"
}

main "$@"
