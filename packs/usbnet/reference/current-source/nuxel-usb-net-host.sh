#!/usr/bin/env bash
# nuxel-usb-net-host.sh — host side of the Nuxel USB network link.
#
#   nuxel-usb-net-host.sh --status [--json]
#   nuxel-usb-net-host.sh --discover [--json]
#   nuxel-usb-net-host.sh --preflight [--json]
#   sudo nuxel-usb-net-host.sh --apply [--interface IFACE] [--address 10.15.19.1/24]
#   sudo nuxel-usb-net-host.sh --remove [--interface IFACE] [--address 10.15.19.1/24]
#   nuxel-usb-net-host.sh --diagnose [--json]
#
# It discovers the Nuxel gadget by VID:PID 18d1:4ee7, configures ONLY the USB
# interface address and never changes the default route, Wi-Fi, DNS or VPN.
# macOS requires a host driver that actually exposes a network interface; this
# script NEVER installs a driver and refuses to guess when none is present.
set -euo pipefail

VID="${NUXEL_USB_VID:-18d1}"
PID="${NUXEL_USB_PID:-4ee7}"
IFACE=""
ADDR="10.15.19.1/24"
CIDR="10.15.19.0/24"
MODE="auto"
ACTION=status
JSON=0

usage() { sed -n '2,18p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --status) ACTION=status; shift ;;
    --discover) ACTION=discover; shift ;;
    --preflight) ACTION=preflight; shift ;;
    --apply) ACTION=apply; shift ;;
    --remove) ACTION=remove; shift ;;
    --diagnose) ACTION=diagnose; shift ;;
    --interface) IFACE="$2"; shift 2 ;;
    --address) ADDR="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --json) JSON=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

OS="$(uname -s)"
EXIT=0
STATUS="UNKNOWN"
DETAIL=""
DEVICE=""
DRIVER=""

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip("\n")))' <<<"$1"; }

discover_linux() {
  local d vid pid
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

discover_macos() {
  # 1. Prove the USB gadget is present (VID/PID) with system_profiler.
  local sp
  sp="$(system_profiler SPUSBDataType -json 2>/dev/null || true)"
  if ! grep -qi "\"vendor_id\"[[:space:]]*:[[:space:]]*\"0x${VID}\"" <<<"$sp" &&
     ! grep -qi "\"vendor_id\"[[:space:]]*:[[:space:]]*\"${VID}\"" <<<"$sp"; then
    return 1
  fi
  if ! grep -qi "\"product_id\"[[:space:]]*:[[:space:]]*\"0x${PID}\"" <<<"$sp" &&
     ! grep -qi "\"product_id\"[[:space:]]*:[[:space:]]*\"${PID}\"" <<<"$sp"; then
    return 1
  fi
  # 2. Find a USB/Ethernet hardware port.  NCM shows as an Ethernet port on
  #    supported macOS releases; RNDIS needs a userspace driver that creates
  #    one.  Never invent an interface.
  local list ifc port
  list="$(networksetup -listallhardwareports 2>/dev/null || true)"
  while read -r ifc; do
    [ -n "$ifc" ] || continue
    [ -d "/sys/class/net/$ifc" ] && continue
    if ifconfig "$ifc" 2>/dev/null | grep -qiE 'ether|inet'; then
      printf '%s\n' "$ifc"
      return 0
    fi
  done < <(awk '/Hardware Port:/{port=$0} /Device:/{if (tolower(port) ~ /usb|ncm|rndis|ethernet/) print $2}' <<<"$list")
  return 1
}

if [ -z "$IFACE" ]; then
  case "$OS" in
    Linux) IFACE="$(discover_linux || true)" ;;
    Darwin) IFACE="$(discover_macos || true)" ;;
  esac
fi

if [ -z "$IFACE" ]; then
  STATUS="NO_USB_NETWORK_INTERFACE"
  if [ "$OS" = Darwin ]; then
    DETAIL="No macOS USB network interface for VID $VID PID $PID. NCM may need native support; RNDIS needs a reviewed userspace driver (for example ReRNDIS/TetherKit). This tool does not install drivers or change SIP."
  else
    DETAIL="No Linux interface belongs to Nuxel VID $VID PID $PID. The phone currently exposes CDC-ACM serial only."
  fi
  EXIT=3
elif [ ! -d "/sys/class/net/$IFACE" ] && [ "$OS" = Linux ]; then
  STATUS="INTERFACE_NOT_FOUND"
  DETAIL="interface $IFACE does not exist"
  EXIT=3
else
  STATUS="INTERFACE_FOUND"
  DETAIL="USB network interface $IFACE detected"
fi

[ -n "$IFACE" ] && DEVICE="$IFACE"

default_route() {
  case "$OS" in
    Linux) ip -4 route show default 2>/dev/null || true ;;
    Darwin) route -n get default 2>/dev/null | awk '/gateway|interface/{print}' || true ;;
  esac
}

interface_state() {
  [ -n "$IFACE" ] || return 0
  case "$OS" in
    Linux)
      ip -br link show dev "$IFACE" 2>/dev/null || true
      ip -4 -o addr show dev "$IFACE" 2>/dev/null || true
      ;;
    Darwin)
      ifconfig "$IFACE" 2>/dev/null || true
      ;;
  esac
}

emit() {
  if [ "$JSON" = 1 ]; then
    printf '{"status":%s,"detail":%s,"os":%s,"mode":%s,"interface":%s,"address":%s,"cidr":%s,"default_route":%s}\n' \
      "$(json_escape "$STATUS")" "$(json_escape "$DETAIL")" "$(json_escape "$OS")" \
      "$(json_escape "$MODE")" "$(json_escape "$IFACE")" "$(json_escape "$ADDR")" \
      "$(json_escape "$CIDR")" "$(json_escape "$(default_route)")"
  else
    echo "# status: $STATUS"
    echo "# detail: $DETAIL"
    echo "# os: $OS  mode: $MODE  interface: ${IFACE:-none}  address: $ADDR"
    echo "# default route (must remain unchanged):"
    default_route | sed 's/^/#   /'
    interface_state | sed 's/^/#   /'
  fi
}

case "$ACTION" in
  status|discover)
    emit
    exit "$EXIT"
    ;;
  preflight)
    if [ -z "$IFACE" ]; then
      emit
      exit 3
    fi
    DETAIL="would configure $IFACE with $ADDR, add no default route, and leave Wi-Fi/VPN/DNS untouched"
    emit
    exit 0
    ;;
  diagnose)
    DETAIL="$DETAIL; ssh probe: $( (ssh -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=no "nuxel@${ADDR%%/*}" true >/dev/null 2>&1 && echo ok) || echo not-attempted )"
    emit
    exit "$EXIT"
    ;;
  apply)
    [ -n "$IFACE" ] || { emit; exit 3; }
    if [ "$OS" = Darwin ]; then
      sudo ifconfig "$IFACE" inet "${ADDR%%/*}" netmask 255.255.255.0 up
    else
      if ip -4 -o addr show dev "$IFACE" | grep -q "inet ${ADDR%%/*}/"; then
        echo "# $ADDR already present on $IFACE (idempotent)" >&2
      else
        sudo ip addr add "$ADDR" dev "$IFACE"
      fi
      sudo ip link set "$IFACE" up
    fi
    STATUS="APPLIED"
    DETAIL="configured $IFACE only; default route untouched"
    emit
    ;;
  remove)
    [ -n "$IFACE" ] || { emit; exit 3; }
    if [ "$OS" = Darwin ]; then
      sudo ifconfig "$IFACE" inet "${ADDR%%/*}" -alias 2>/dev/null || true
    else
      sudo ip addr del "$ADDR" dev "$IFACE" 2>/dev/null || true
    fi
    STATUS="REMOVED"
    DETAIL="removed only the address this tool owns; default route untouched"
    emit
    ;;
  *) usage; exit 2 ;;
esac
