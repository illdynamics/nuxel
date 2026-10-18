#!/bin/sh
# nuxel-usb-input-audit — READ-ONLY audit of USB host/device role and HID input.
# It never writes a role, never unbinds a driver, never touches a partition.
# Output is JSONL so one run can be archived and compared between boots.
#
#   nuxel-usb-input-audit.sh [--seconds N]
#
# The decisive question on the S10+ single port is whether a Type-C attach makes
# the DWC3 port a HOST (xHCI binds, USB devices enumerate, HID creates an evdev
# node) or remains a DEVICE (the live console gadget).  This script records the
# actual sysfs state instead of inferring it from "USB exists".
set -u
SECS=1
[ "${1:-}" = "--seconds" ] && SECS="${2:-1}"
now() { date -u +%Y-%m-%dT%H:%M:%SZ; }
jstr() { printf '%s' "$1" | tr -d '"\\\r\n' ; }
json() { printf '{"ts":"%s","kind":"%s","name":"%s","value":"%s"}\n' "$(now)" "$1" "$(jstr "$2")" "$(jstr "$3")"; }

json audit start "seconds=$SECS"
for f in /sys/class/typec/port*/data_role /sys/class/typec/port*/power_role /sys/class/typec/port*/port_type \
         /sys/class/typec/port*/preferred_role /sys/class/typec/port*/vconn_source; do
  [ -r "$f" ] && json typec "$(basename "$(dirname "$f")")/$(basename "$f")" "$(cat "$f" 2>/dev/null)"
done
for f in /sys/class/power_supply/otg/online /sys/class/power_supply/usb/online; do
  [ -r "$f" ] && json power "$f" "$(cat "$f" 2>/dev/null)"
done
for u in /sys/class/udc/*; do
  [ -e "$u" ] || continue
  json udc "$(basename "$u")" "state=$(cat "$u/state" 2>/dev/null)"
done
json gadget UDC "$(cat /sys/kernel/config/usb_gadget/*/UDC 2>/dev/null | tr '\n' ' ')"
# xHCI is only useful if a USB host controller is actually bound to a device.
json xhci bound_devices "$(ls -1 /sys/bus/platform/drivers/xhci-hcd 2>/dev/null | grep -v '^bind$\|^unbind$\|^uevent$\|^module$\|^drivers$\|^driver_override$' | tr '\n' ' ')"
json xhci driver "$(readlink -f /sys/bus/platform/drivers/xhci-hcd 2>/dev/null)"
# Every enumerated USB device (root hubs are included only if a host exists).
for d in /sys/bus/usb/devices/*; do
  [ -r "$d/idVendor" ] || continue
  json usb "$(basename "$d")" "vid=$(cat "$d/idVendor") pid=$(cat "$d/idProduct") product=$(cat "$d/product" 2>/dev/null) driver=$(basename "$(readlink -f "$d/driver" 2>/dev/null)")"
done
# HID input devices and whether they expose key/rel/abs events.
for e in /dev/input/event*; do
  [ -e "$e" ] || continue
  name=$(cat "/sys/class/input/$(basename "$e")/device/name" 2>/dev/null)
  case "$name" in *keyboard*|*Keyboard*|*mouse*|*Mouse*|*HID*|*hid*) json hid "$e" "name=$name";; esac
done
json audit done "seconds=$SECS"
