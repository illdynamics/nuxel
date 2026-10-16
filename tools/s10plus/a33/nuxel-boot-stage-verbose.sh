#!/bin/sh
# nuxel-boot-stage-verbose.sh — the EARLY BOOT STAGE half of the one-time
# Bixby-hold verbose-boot override (briq-02b).
#
# STATUS: IMPLEMENTED, NOT DEPLOYED.  This fragment belongs in the initramfs
# (BOOT partition) and installing it requires a BOOT partition write, which this
# mission forbids (NO FLASHING of any kind).  It is kept here, ready, so the next
# BOOT update can adopt it; until then nuxel-verbose-boot reports the override as
# BOOT_UPDATE_REQUIRED with this exact reason.  Nothing fakes the override behind
# a cosmetic switch.
#
# WHAT IT DOES (design, for the future BOOT update)
#   1. Waits for the gpio_keys input device and reads the Bixby/assistant key
#      (keycode 703 on /dev/input/eventN "gpio_keys" - the same key the A32
#      button manager uses).  The event node is discovered by NAME, never by a
#      hard-coded eventN (the touch pipeline's rule, applied here too).
#   2. If the key is HELD when the boot stage reaches the animation decision
#      point, it drops the one-time request /run/nuxel/boot-verbose-once and
#      publishes the capability receipt /run/nuxel/boot-stage-capabilities with
#      `bixby-hold-override=1` so the userspace consumer is allowed to honour it.
#   3. It never persists anything: the override applies to THAT BOOT ONLY, which
#      is the whole point of a recovery aid ("one-time").
#
# INSERTION POINT (documented, not applied): boot/initramfs/init.sh, immediately
# before the `nuxel_start_animation` call, i.e. after the rootfs is mounted and
# before the MP4 player takes the framebuffer.
set -eu

STATEDIR="${NUXEL_STATE_DIR:-/run/nuxel}"
HOLD_MS="${NUXEL_BIXBY_HOLD_MS:-1200}"
CAPS="${STATEDIR}/boot-stage-capabilities"
ONCE="${STATEDIR}/boot-verbose-once"

mkdir -p "$STATEDIR" 2>/dev/null || true

# --- 1. find the key device by NAME (never a hard-coded eventN) ---------------
find_key_device() {
    for dev in /sys/class/input/event*; do
        [ -r "${dev}/device/name" ] || continue
        name="$(cat "${dev}/device/name" 2>/dev/null)" || continue
        case "$name" in
            *gpio_keys*|*gpio-keys*) basename "$dev"; return 0 ;;
        esac
    done
    return 1
}

KEYDEV="$(find_key_device || true)"
if [ -n "${KEYDEV}" ]; then
    printf 'bixby-key-device=%s\n' "${KEYDEV}" >> "$CAPS" 2>/dev/null || true
else
    printf 'bixby-key-device=none\n' >> "$CAPS" 2>/dev/null || true
    exit 0
fi

# --- 2. is the Bixby/assistant key (703) held? -------------------------------
# /sys/class/input/eventN/device/key ... this shell cannot decode key bitmaps, so
# the authoritative reader is a small helper that returns 0 when the key is held
# for at least HOLD_MS.  If the helper is not in the initramfs the override is
# reported as unavailable rather than guessed.
HELPER=/opt/nuxel/nuxel-key-hold
if [ ! -x "${HELPER}" ]; then
    printf 'bixby-hold-override=0\n' >> "$CAPS" 2>/dev/null || true
    printf 'bixby-hold-override-reason=key-hold-helper-absent\n' >> "$CAPS" 2>/dev/null || true
    exit 0
fi
if "${HELPER}" --device="/dev/input/${KEYDEV}" --keycode=703 --hold-ms="${HOLD_MS}"; then
    printf 'bixby-hold-override=1\n' >> "$CAPS" 2>/dev/null || true
    : > "$ONCE" 2>/dev/null || true
    printf 'NUXEL_VERBOSE_BOOT_OVERRIDE_REQUESTED=1\n' >> /dev/kmsg 2>/dev/null || true
else
    printf 'bixby-hold-override=1\n' >> "$CAPS" 2>/dev/null || true
fi
exit 0
