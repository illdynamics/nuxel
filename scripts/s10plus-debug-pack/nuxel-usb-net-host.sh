#!/usr/bin/env bash
# nuxel-usb-net-host.sh — host side of the opt-in USB NCM link.
#
#   nuxel-usb-net-host.sh --status
#   sudo nuxel-usb-net-host.sh --apply [--interface usb0] [--address 10.15.19.1/24]
#   sudo nuxel-usb-net-host.sh --remove
#
# It discovers the Nuxel gadget by VID:PID 18d1:4ee7, adds ONLY the USB-link
# address and never changes the default route.  On macOS this script reports
# that the interface must be configured with ifconfig/networksetup; it does not
# pretend a Linux sysfs probe works there.
set -euo pipefail

VID="${NUXEL_USB_VID:-18d1}"
PID="${NUXEL_USB_PID:-4ee7}"
IFACE=""
ADDR="10.15.19.1/24"
ACTION=status

usage() { sed -n '2,14p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --status) ACTION=status; shift ;;
    --apply) ACTION=apply; shift ;;
    --remove) ACTION=remove; shift ;;
    --interface) IFACE="$2"; shift 2 ;;
    --address) ADDR="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

if [ "$(uname -s)" = Darwin ]; then
  echo "# macOS: use 'networksetup -listallhardwareports' and 'ifconfig'." >&2
  echo "# macOS NCM support was NOT verified by this tool; refusing to guess." >&2
  exit 3
fi

discover() {
  local d i vid pid
  for d in /sys/class/net/*; do
    [ -e "$d/device/idVendor" ] || continue
    vid="$(cat "$d/device/idVendor" 2>/dev/null || true)"
    pid="$(cat "$d/device/idProduct" 2>/dev/null || true)"
    vid="${vid#0x}"; pid="${pid#0x}"
    if [ "$vid" = "$VID" ] && [ "$pid" = "$PID" ]; then
      basename "$d"
      return 0
    fi
  done
  return 1
}

[ -n "$IFACE" ] || IFACE="$(discover || true)"
if [ -z "$IFACE" ]; then
  echo "!! no Nuxel USB network interface (VID $VID PID $PID) on this host" >&2
  echo "!! the phone currently exposes only CDC-ACM serial; see nuxel-usb-net.py" >&2
  exit 3
fi
if [ ! -d "/sys/class/net/$IFACE" ]; then
  echo "!! interface $IFACE does not exist" >&2
  exit 3
fi

show() {
  echo "# interface: $IFACE"
  ip -br link show dev "$IFACE" 2>/dev/null || true
  ip -4 -o addr show dev "$IFACE" 2>/dev/null || true
  ip -4 route show | grep -E "(^| )10\.15\.19\.0/24( |$)" || true
}

case "$ACTION" in
  status)
    show
    ;;
  apply)
    if ip -4 -o addr show | grep -q "10\.15\.19\."; then
      echo "# $ADDR already present (idempotent)"
    else
      sudo ip addr add "$ADDR" dev "$IFACE"
    fi
    sudo ip link set "$IFACE" up
    show
    echo "# default route unchanged:"
    ip -4 route show default
    ;;
  remove)
    sudo ip addr del "$ADDR" dev "$IFACE" 2>/dev/null || true
    show
    ;;
esac
