#!/bin/sh
# Nuxel beyond2lte hardware bring-up PID 1. NOT the complete Nuxel desktop.
# Invoked by initramfs switch_root after the verified USERDATA ext4 is mounted.
# Deliberately remains alive even when panel/USB firmware fails to initialize.
export PATH=/bin:/sbin:/usr/bin:/usr/sbin

[ -d /proc ] || mkdir -p /proc
[ -d /sys ] || mkdir -p /sys
[ -d /dev ] || mkdir -p /dev
[ -e /proc/cmdline ] || mount -t proc proc /proc 2>/dev/null || true
[ -d /sys/class ] || mount -t sysfs sysfs /sys 2>/dev/null || true
[ -e /dev/null ] || mount -t devtmpfs devtmpfs /dev 2>/dev/null || true
mkdir -p /run /tmp /dev/pts /sys/kernel/config
mount -t devpts devpts /dev/pts 2>/dev/null || true
mount -t configfs configfs /sys/kernel/config 2>/dev/null || true

log() {
    printf 'nuxel-s10plus: %s\n' "$*" >/dev/console 2>/dev/null || true
    printf '<6>nuxel-s10plus: %s\n' "$*" >/dev/kmsg 2>/dev/null || true
    [ -c /dev/ttyGS0 ] && printf 'nuxel-s10plus: %s\r\n' "$*" > /dev/ttyGS0 2>/dev/null || true
}
log 'Phase-1 ARM64 bring-up init started (not full desktop)'
log "cmdline: $(cat /proc/cmdline 2>/dev/null)"
log "kernel: $(uname -r 2>/dev/null || echo unknown)"

# Optional early USB-ACM diagnostic console. Gadget availability depends on
# compiled-in USB controller and configfs modules; failure is not boot fatal.
setup_acm() {
    [ -d /sys/kernel/config/usb_gadget ] || return 1
    [ -d /sys/class/udc ] || return 1
    udc="$(ls /sys/class/udc 2>/dev/null | head -n 1)"
    [ -n "$udc" ] || return 1
    G=/sys/kernel/config/usb_gadget/nuxel
    mkdir -p "$G" "$G/strings/0x409" "$G/configs/c.1/strings/0x409" "$G/functions/acm.usb0" 2>/dev/null || return 1
    printf '0x1d6b\n' >"$G/idVendor" 2>/dev/null || return 1
    printf '0x0104\n' >"$G/idProduct" 2>/dev/null || return 1
    printf 'Nuxel\n' >"$G/strings/0x409/manufacturer" 2>/dev/null || true
    printf 'S10+ diagnostics\n' >"$G/strings/0x409/product" 2>/dev/null || true
    printf 'nuxel-beyond2lte\n' >"$G/strings/0x409/serialnumber" 2>/dev/null || true
    printf 'ACM console\n' >"$G/configs/c.1/strings/0x409/configuration" 2>/dev/null || true
    ln -sf "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0" 2>/dev/null || return 1
    printf '%s\n' "$udc" >"$G/UDC" 2>/dev/null || return 1
}
setup_acm && log 'USB ACM gadget bound' || log 'USB ACM unavailable (not a fatal error)'

# Early Nuxel phone first-light screen; this is an explicitly diagnostic
# framebuffer UI, not Phosh. It uses a static ARM64 binary with no libc.
# We cannot make the Samsung panel driver appear from userland. If the kernel
# exposes no /dev/fb0, record a precise failure instead of claiming success.
fb_attempt=0
fb_ok=0
while [ "$fb_attempt" -lt 20 ]; do
    if [ -c /dev/fb0 ] || [ -c /dev/graphics/fb0 ]; then
        if [ -x /usr/bin/nuxel-fb-phone ]; then
            /usr/bin/nuxel-fb-phone > /run/nuxel-fb-status 2>&1 && fb_ok=1
        fi
        break
    fi
    fb_attempt=$((fb_attempt+1))
    sleep 1
done
if [ "$fb_ok" -eq 1 ]; then
    log 'first-light framebuffer write completed; actual panel visibility unverified'
else
    log 'first-light display unavailable: no driver, unsupported mode or framebuffer write failure'
    cat /run/nuxel-fb-status >/dev/console 2>/dev/null || true
fi

# This small diagnostic filesystem does NOT have Python/OpenRC/Phosh installed.
# Full phone UI needs build-phone-rootfs-fedora.sh and verified driver support.
if [ ! -x /usr/bin/python3 ] || [ ! -x /sbin/openrc-init ]; then
    log 'minimal bring-up root: no full Python/OpenRC/Phosh runtime'
fi
printf '%s\n' 'nuxel-s10plus-bringup-init-reached' > /run/nuxel-bringup-status 2>/dev/null || true

# Security: a passwordless root serial shell is NOT automatically exposed.
# Only an explicit nuxel.debug=1 on the kernel cmdline unlocks it.
case " $(cat /proc/cmdline 2>/dev/null) " in
    *' nuxel.debug=1 '*)
        if [ -c /dev/ttyGS0 ]; then
            log 'DEBUG MODE: unauthenticated USB root shell enabled by cmdline'
            (while :; do /bin/sh -i </dev/ttyGS0 >/dev/ttyGS0 2>&1; sleep 1; done) &
        fi ;;
    *) log 'USB root shell disabled (pass nuxel.debug=1 for explicit debug mode)' ;;
esac

log 'PID 1 alive; awaiting hardware bring-up diagnostics'
while :; do sleep 30; done
