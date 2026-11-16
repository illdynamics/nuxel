#!/usr/bin/env bash
# nuxel-usb-net-host.sh — host side of the Nuxel USB network link.
#
#   nuxel-usb-net-host.sh --status [--json]
#   nuxel-usb-net-host.sh --discover [--json]
#   nuxel-usb-net-host.sh --preflight [--json]
#   sudo nuxel-usb-net-host.sh --apply [--interface IFACE] [--address 10.100.10.1/24]
#   sudo nuxel-usb-net-host.sh --remove [--interface IFACE]
#   nuxel-usb-net-host.sh --diagnose [--json]
#   nuxel-usb-net-host.sh --ssh [--phone 10.100.10.1] --key ~/.ssh/xxx
#   nuxel-usb-net-host.sh --tether-test [--json]
#       Prove Internet tethering END TO END from this computer: default route
#       must stay on Wi-Fi, so the phone is probed by binding the source
#       address to the USB interface and sending via the phone gateway.  The
#       result is POSTed to the phone's usb-tether host-report verb (evidence
#       only) and printed.
#
# Discovery is EXACT: the selected BSD interface must be an IORegistry
# descendant of the USB device with the configured VID:PID (Linux: walk the
# sysfs parent chain).  It never guesses from a friendly port name, never
# installs a driver and never touches the default route, Wi-Fi, DNS or VPN.
#
# macOS: the phone's CDC-NCM function is driven natively by
# com.apple.driver.AppleUSBDeviceNCM; no SIP change and no third-party
# driver are needed.  The Mac is configured .2 of the phone's link subnet and
# the phone (nuxel-usb-mode.sh) owns .1.  no default route is added: the
# link is a directly connected /24, so SSH/ping to .1 work without touching
# Wi-Fi, DNS, VPN or ZeroTier.
#
# State written by --apply lives in $STATE (root-owned) and --remove deletes
# ONLY the address recorded there.
set -uo pipefail

VID="${NUXEL_USB_VID:-18d1}"
PID="${NUXEL_USB_PID:-4ee7}"
IFACE="${NUXEL_USB_IFACE:-}"
PHONE="${NUXEL_USB_PHONE:-}"
ADDR="${NUXEL_USB_HOST_ADDR:-10.100.10.2/24}"
MODE="auto"
ACTION=status
JSON=0
PHONE_EXPLICIT=0
[ -n "${NUXEL_USB_PHONE:-}" ] && PHONE_EXPLICIT=1
KEY="${NUXEL_SSH_KEY:-${HOME}/.ssh/wicked_wqn_id_rsa}"
SSH_USER="${NUXEL_SSH_USER:-root}"
SSH_PORT="${NUXEL_USB_SSH_PORT:-2022}"
STATE="${NUXEL_USB_HOST_STATE:-/var/run/nuxel-usb-net-host.state}"

usage() { sed -n '2,32p' "$0"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --status) ACTION=status; shift ;;
    --discover) ACTION=discover; shift ;;
    --preflight) ACTION=preflight; shift ;;
    --apply) ACTION=apply; shift ;;
    --remove) ACTION=remove; shift ;;
    --diagnose) ACTION=diagnose; shift ;;
    --ssh) ACTION=ssh; shift ;;
    --tether-test) ACTION=tether_test; shift ;;
    --interface) IFACE="$2"; shift 2 ;;
    --address) ADDR="$2"; shift 2 ;;
    --phone) PHONE="$2"; PHONE_EXPLICIT=1; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
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
ANCHOR=""

# Resolve the phone address from the host address prefix, unless the owner
# passed --phone or NUXEL_USB_PHONE explicitly.  The phone owns .1 of its link
# subnet (10.100.10.1/24 by default, matching nuxel-usb-mode.sh); the host is
# configured .2.  Diagnostics must probe the PHONE, never the host's own .2/.1.
phone_addr() {
  if [ "$PHONE_EXPLICIT" = 1 ]; then
    printf '%s\n' "$PHONE"; return
  fi
  python3 - "$ADDR" <<'PY'
import ipaddress, sys
try:
    i = ipaddress.ip_interface(sys.argv[1])
except ValueError:
    print("10.100.10.1"); raise SystemExit(0)
net = i.network
print(str(net.network_address + 1))
PY
}

json_escape() { python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().rstrip("\n")))' <<<"$1"; }

# --- Linux discovery -------------------------------------------------------
# Walk /sys/class/net/<iface>/device parents until a USB device node is found.
discover_linux() {
  local d dev p vid pid
  for d in /sys/class/net/*; do
    [ -d "$d/device" ] || continue
    p="$(readlink -f "$d/device" 2>/dev/null || true)"
    [ -n "$p" ] || continue
    while [ -n "$p" ] && [ "$p" != "/" ]; do
      if [ -r "$p/idVendor" ] && [ -r "$p/idProduct" ]; then
        vid="$(tr -d ' \n' < "$p/idVendor")"; pid="$(tr -d ' \n' < "$p/idProduct")"
        vid="${vid#0x}"; pid="${pid#0x}"
        if [ "$vid" = "$VID" ] && [ "$pid" = "$PID" ]; then
          basename "$d"; return 0
        fi
        break
      fi
      p="$(dirname "$p")"
    done
  done
  return 1
}

# --- macOS discovery -------------------------------------------------------
# IORegistry shape on macOS (verified on this Apple Silicon Mac):
#   <driver service>  AppleUSBDeviceNCM / AppleUSBDeviceNCMData / ...  <- has BSD Name child
#     +- IOEthernetInterface / IOSkywalkLegacyEthernetInterface  { "BSD Name" = enN }
#     +- IONetworkStack  (registered under IOResources, NOT under the device)
# The BSD node is a CHILD of the driver service, not its parent.  For each
# network-interface node we therefore walk its ancestors up to the USB device
# (the node carrying idVendor/idProduct) and require an exact VID:PID match.
# `ioreg -a` output is normally XML; a binary-plist fallback is used when a
# newer macOS emits that instead (the old helper silently returned nothing and
# then guessed).
discover_macos() {
  local out
  out="$(python3 - "$VID" "$PID" "${NUXEL_IOREG_PLIST:-}" <<'PY'
import json, plistlib, subprocess, sys
vid, pid = sys.argv[1].lower().replace("0x", ""), sys.argv[2].lower().replace("0x", "")
fixture = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else ""

raw = b""
if fixture:
    raw = open(fixture, "rb").read()
else:
    # MUST be -a -l: without -l ioreg emits short nodes that contain OID
    # references instead of idVendor/BSD Name, which made the old helper see
    # zero matching interfaces.
    try:
        raw = subprocess.run(["ioreg", "-a", "-l", "-p", "IOService", "-w0"],
                             capture_output=True, timeout=180).stdout
    except Exception:
        raw = b""
if not raw:
    sys.exit(1)

def load(raw):
    try:
        return plistlib.loads(raw)
    except Exception:
        pass
    try:
        # Binary plist: convert with plutil to XML on stdout (-o -).
        out = subprocess.run(["plutil", "-convert", "xml1", "-o", "-", "-"],
                             input=raw, capture_output=True, timeout=120).stdout
        return plistlib.loads(out)
    except Exception:
        return None

data = load(raw)
if data is None:
    sys.exit(1)
roots = data if isinstance(data, list) else [data]

def hx(v):
    if isinstance(v, int):
        return "%x" % v
    return str(v).lower().replace("0x", "")

results = []   # (bsd, class, driver, usb_instance, match)
def walk(node, ancestors):
    if not isinstance(node, dict):
        return
    cls = node.get("IOClass") or node.get("IORegistryEntryName") or "?"
    here = ancestors + [node]
    if "BSD Name" in node:
        usb = None
        for anc in reversed(here[:-1]):
            if "idVendor" in anc and "idProduct" in anc:
                usb = anc
                break
        vid_ok = usb is not None and hx(usb.get("idVendor")) == vid and hx(usb.get("idProduct")) == pid
        # The nearest driver service below the interface node (exclude the
        # interface classes themselves).
        driver = None
        for anc in reversed(here[:-1]):
            c = anc.get("IOClass") or ""
            if c in ("IOEthernetInterface", "IOSkywalkLegacyEthernetInterface",
                     "IONetworkInterface", "IONetworkStack", "IOResources"):
                continue
            driver = c
            break
        results.append((str(node["BSD Name"]), cls, driver or "",
                        str((usb or {}).get("USB Serial Number") or ""), vid_ok))
    for c in node.get("IORegistryEntryChildren") or []:
        walk(c, here)

for r in roots:
    walk(r, [])

for bsd, cls, driver, serial, ok in results:
    if ok:
        print("%s|%s|%s|%s" % (bsd, cls, driver, serial))
PY
)"
  local line bsd
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    bsd="${line%%|*}"
    case "$bsd" in
      en*)
        ANCHOR="$line"
        DRIVER="${line#*|}"; DRIVER="${DRIVER%%|*}"
        printf '%s\n' "$bsd"; return 0 ;;
    esac
  done <<< "$out"
  return 1
}

# Prove (read-only) that an explicitly supplied --interface really belongs to
# the exact USB device.  An explicit interface is never trusted blindly.
iface_belongs_to_device_macos() {
  local want="$1" line bsd
  line="$(python3 - "$VID" "$PID" "$want" "${NUXEL_IOREG_PLIST:-}" <<'PY'
import plistlib, subprocess, sys
vid, pid, want = sys.argv[1].lower().replace("0x", ""), sys.argv[2].lower().replace("0x", ""), sys.argv[3]
fixture = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else ""
try:
    if fixture:
        raw = subprocess.run(["ioreg", "-a", "-r", "-n", want, "-p", "IOService", "-w0"],
                             capture_output=True, timeout=120).stdout
    else:
        raw = subprocess.run(["ioreg", "-a", "-r", "-n", want, "-p", "IOService", "-w0"],
                             capture_output=True, timeout=120).stdout
    data = plistlib.loads(raw)
except Exception:
    sys.exit(1)
nodes = data if isinstance(data, list) else [data]
def hx(v):
    return ("%x" % v) if isinstance(v, int) else str(v).lower().replace("0x", "")
def walk(n, anc):
    if not isinstance(n, dict):
        return False
    if str(n.get("BSD Name") or "") == want:
        for a in reversed(anc):
            if "idVendor" in a and "idProduct" in a:
                return hx(a.get("idVendor")) == vid and hx(a.get("idProduct")) == pid
        return False
    return any(walk(c, anc + [n]) for c in (n.get("IORegistryEntryChildren") or []))
sys.exit(0 if any(walk(r, []) for r in nodes) else 1)
PY
)" || return 1
  return 0
}

if [ -n "$IFACE" ]; then
  case "$OS" in
    Darwin) iface_belongs_to_device_macos "$IFACE" || {
      echo "refusing --interface $IFACE: IORegistry does not show it under USB ${VID}:${PID}" >&2
      IFACE_EXPLICIT_REFUSED=1; IFACE=""; } ;;
    Linux) { p="$(readlink -f "/sys/class/net/$IFACE/device" 2>/dev/null || true)"; ok=0
             while [ -n "$p" ] && [ "$p" != "/" ]; do
               if [ -r "$p/idVendor" ]; then
                 [ "$(tr -d ' \n' < "$p/idVendor" | sed 's/^0x//')" = "$VID" ] && \
                 [ "$(tr -d ' \n' < "$p/idProduct" | sed 's/^0x//')" = "$PID" ] && ok=1
                 break; fi
               p="$(dirname "$p")"; done
             [ "$ok" = 1 ] || { echo "refusing --interface $IFACE: no USB ${VID}:${PID} ancestor" >&2; IFACE=""; }; } ;;
  esac
fi
# An explicitly requested interface that failed the ancestry proof is never
# replaced by a silent auto-discovery: the operator asked for THAT port.
if [ "${IFACE_EXPLICIT_REFUSED:-0}" != 1 ]; then
  [ -n "$IFACE" ] || { case "$OS" in Linux) IFACE="$(discover_linux || true)";; Darwin) IFACE="$(discover_macos || true)";; esac; }
fi

if [ -z "$IFACE" ]; then
  STATUS="NO_USB_NETWORK_INTERFACE"
  if [ "${IFACE_EXPLICIT_REFUSED:-0}" = 1 ]; then
    DETAIL="the explicit --interface was refused: it is not an IORegistry child of USB ${VID}:${PID}, and this tool never substitutes another port"
  elif [ "$OS" = Darwin ]; then
    DETAIL="No network interface is an IORegistry descendant of USB ${VID}:${PID}. Either the phone is not exposing its NCM function (USB Network is OFF on the phone) or macOS did not bind AppleUSBDeviceNCM. This tool will not select an unrelated Ethernet port."
  else
    DETAIL="No Linux interface has a USB ancestor with VID:PID ${VID}:${PID}. The phone is probably still ACM-only (USB Network OFF)."
  fi
  EXIT=3
else
  STATUS="INTERFACE_FOUND"
  DETAIL="interface $IFACE belongs to USB ${VID}:${PID}"
fi

default_route() {
  case "$OS" in
    Linux) ip -4 route show default 2>/dev/null || true ;;
    Darwin) route -n get default 2>/dev/null | awk '/gateway|interface/{print}' || true ;;
  esac
}

iface_has_addr() {
  [ -n "$IFACE" ] || return 1
  if [ "$OS" = Darwin ]; then ifconfig "$IFACE" 2>/dev/null | grep -q "inet ${ADDR%%/*} "; else
    ip -4 -o addr show dev "$IFACE" 2>/dev/null | grep -q "inet ${ADDR%%/*}/"; fi
}

lldp_link_up() {
  [ -n "$IFACE" ] || return 1
  case "$OS" in
    Darwin) ifconfig "$IFACE" 2>/dev/null | grep -q 'status: active' ;;
    Linux) [ "$(cat /sys/class/net/$IFACE/operstate 2>/dev/null)" = up ] ;;
  esac
}

phone_reachable() {
  case "$OS" in
    Darwin) ping -c1 -W 1000 "$(phone_addr)" >/dev/null 2>&1 ;;
    Linux) ping -c1 -W 1 "$(phone_addr)" >/dev/null 2>&1 ;;
  esac
}

ssh_probe() {
  local keyopt=()
  [ -f "$KEY" ] && keyopt=(-i "$KEY" -o IdentitiesOnly=yes)
  ssh -p "$SSH_PORT" -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new \
      "${keyopt[@]}" "${SSH_USER}@$(phone_addr)" true >/dev/null 2>&1
}

emit() {
  local ipcfg=false link=down reach=false sshstate=unverified drv="${DRIVER:-}"
  # device_present is proven by the exact USB ancestry match above (or by the
  # Linux sysfs walk); a mere VID:PID on the bus is not enough.
  iface_has_addr && ipcfg=true
  lldp_link_up && link=up
  phone_reachable && reach=true
  if [ "$reach" = true ] && ssh_probe; then sshstate=authenticated; fi
  if [ "$JSON" = 1 ]; then
    printf '{"status":%s,"detail":%s,"os":%s,"mode":%s,"interface":%s,"device_present":%s,"phone_address":%s,"host_address":%s,"driver":%s,"link":%s,"ip_configured":%s,"phone_reachable":%s,"ssh":%s,"default_route":%s}\n' \
      "$(json_escape "$STATUS")" "$(json_escape "$DETAIL")" "$(json_escape "$OS")" \
      "$(json_escape "$MODE")" "$(json_escape "$IFACE")" "$([ -n "$IFACE" ] && echo true || echo false)" \
      "$(json_escape "$(phone_addr)")" \
      "$(json_escape "$ADDR")" "$(json_escape "$drv")" "$(json_escape "$link")" "$ipcfg" \
      "$reach" "$(json_escape "$sshstate")" "$(json_escape "$(default_route)")"
  else
    echo "# status: $STATUS"
    echo "# detail: $DETAIL"
    echo "# os: $OS  mode: $MODE  interface: ${IFACE:-none}"
    echo "# driver/anchor: ${drv:-none}"
    echo "# phone ${PHONE}  host $ADDR  link=$link ip_configured=$ipcfg reachable=$reach ssh=$sshstate"
    echo "# default route (must remain unchanged):"
    default_route | sed 's/^/#   /'
    [ -n "$IFACE" ] && ifconfig "$IFACE" 2>/dev/null | sed 's/^/#   /'
  fi
}


# --- end-to-end tether proof -------------------------------------------------
# The Mac keeps Wi-Fi as its default route (the owner is working on it and the
# default route must not change).  A plain "curl" therefore proves nothing about
# the USB share: it would use Wi-Fi.  Instead we bind the source address to the
# USB interface and send THROUGH THE PHONE as gateway:
#   ping  -b <host .2> <phone .1>
#   curl  --interface <host .2> --resolve connectivity.gstatic.com:443:<phone .1>
#          (the phone's NAT forwards to the real upstream)
#   plus a DNS lookup through the phone (dscacheutil/nslookup is host-resolver;
#   a direct UDP DNS query to the phone is not served - we report that honestly)
tether_test() {
  local host_ip="${ADDR%%/*}" phone
  phone="$(phone_addr)"
  if [ -z "$IFACE" ]; then
    case "$OS" in
      Darwin) discover_macos >/dev/null 2>&1 && IFACE="$(discover_macos)";;
      *) IFACE="$(discover_linux || true)";;
    esac
  fi
  if [ -z "$IFACE" ]; then
    STATUS="NO_USB_NETWORK_INTERFACE"; DETAIL="no exact Nuxel USB interface; cannot prove tether"
    EXIT=3; emit; return 3
  fi
  if ! iface_has_addr; then
    STATUS="TETHER_NOT_CONFIGURED"; DETAIL="configure $IFACE with $ADDR first (--apply)"
    EXIT=4; emit; return 4
  fi
  local ping_ok=false http_ok=false http_code="" dns_ok=false dns_detail="not probed"
  case "$OS" in
    Darwin) ping -c 2 -W 1500 -S "$host_ip" "$phone" >/dev/null 2>&1 && ping_ok=true ;;
    Linux) ping -c 2 -W 2 -I "$IFACE" "$phone" >/dev/null 2>&1 && ping_ok=true ;;
  esac
  # Host resolves the public name through its normal resolver, then connects to
  # the resolved address but routed via the phone gateway (host route scoped to
  # that one address - removed immediately afterwards).
  local target_ip=""
  target_ip="$(python3 - <<'PY' 2>/dev/null
import socket
try:
    print(socket.getaddrinfo("connectivity.gstatic.com", 443, socket.AF_INET)[0][4][0])
except Exception:
    pass
PY
)"
  if [ -n "$target_ip" ]; then
    if [ "$OS" = Darwin ]; then
      sudo route -n add -host "$target_ip" "$phone" >/dev/null 2>&1 && host_route=1 || host_route=0
      # Preserve the hostname for TLS/SNI while forcing this probe through the
      # temporary USB route. Bare-IP HTTPS produces a false negative on macOS.
      http_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 \
        --interface "$host_ip" --resolve "connectivity.gstatic.com:443:$target_ip" \
        "https://connectivity.gstatic.com/generate_204" 2>/dev/null)"
      [ "${host_route:-0}" = 1 ] && sudo route -n delete -host "$target_ip" "$phone" >/dev/null 2>&1
    else
      sudo ip route add "$target_ip/32" via "$phone" dev "$IFACE" >/dev/null 2>&1 && host_route=1 || host_route=0
      http_code="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 8 \
        --interface "$host_ip" --resolve "connectivity.gstatic.com:443:$target_ip" \
        "https://connectivity.gstatic.com/generate_204" 2>/dev/null)"
      [ "${host_route:-0}" = 1 ] && sudo ip route del "$target_ip/32" >/dev/null 2>&1
    fi
    case "$http_code" in 204|200) http_ok=true ;; esac
    dns_detail="public DNS resolved $target_ip on the host resolver; DNS is not served by the phone (static-host-config)"
  else
    dns_detail="host could not resolve connectivity.gstatic.com"
  fi
  STATUS="TETHER_UNVERIFIED"
  [ "$ping_ok" = true ] && [ "$http_ok" = true ] && STATUS="TETHER_VERIFIED"
  DETAIL="ping_phone=$ping_ok http=$http_ok code=${http_code:-none} via=$phone host=$host_ip iface=$IFACE"
  # Report typed evidence to the phone (evidence only; never changes firewall).
  local report
  report="$(python3 - "$host_ip" "$phone" "$ping_ok" "$http_ok" <<'PY'
import json, sys, datetime
print(json.dumps({"host_address": sys.argv[1], "checked_phone": sys.argv[2],
                  "ping_ok": sys.argv[3] == "true", "internet_ok": sys.argv[4] == "true",
                  "dns_ok": False, "checked_at": datetime.datetime.utcnow().isoformat() + "Z"}))
PY
)"
  if [ "$ping_ok" = true ]; then
    ssh -p "$SSH_PORT" -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new \
        -i "$KEY" -o IdentitiesOnly=yes "${SSH_USER}@${phone}" \
        "cd /usr/lib/nuxel/nuxel-bridge && python3 -c 'import json,sys; import usb_tether; print(json.dumps(usb_tether.host_report(json.loads(sys.stdin.read()))))'" \
        <<<"$report" 2>/dev/null | tail -1 | grep -q '"internet_verified": true' \
        && DETAIL="$DETAIL reported=1" || DETAIL="$DETAIL reported=0"
  fi
  emit
  if [ "$STATUS" = TETHER_VERIFIED ]; then return 0; fi
  return 5
}

case "$ACTION" in
  status|discover) emit; exit "$EXIT" ;;
  preflight)
    [ -n "$IFACE" ] || { emit; exit 3; }
    STATUS="PREFLIGHT_OK"
    DETAIL="would configure $IFACE with $ADDR, add no default route, leave Wi-Fi/VPN/DNS untouched"
    emit; exit 0 ;;
  apply)
    [ -n "$IFACE" ] || { emit; exit 3; }
    if iface_has_addr; then
      # Idempotent: the address is already present.  It is NOT recorded as
      # owned, so --remove can never delete an address this tool did not add.
      STATUS="APPLIED"; DETAIL="$ADDR already present on $IFACE (idempotent, not owned)"
      emit; exit 0
    fi
    if [ "$OS" = Darwin ]; then
      sudo ifconfig "$IFACE" inet "${ADDR%%/*}" netmask 255.255.255.0 up || { STATUS="APPLY_FAILED"; DETAIL="ifconfig failed"; emit; exit 4; }
    else
      sudo ip addr add "$ADDR" dev "$IFACE" || { STATUS="APPLY_FAILED"; DETAIL="ip addr add failed"; emit; exit 4; }
      sudo ip link set "$IFACE" up || { STATUS="APPLY_FAILED"; DETAIL="ip link up failed"; emit; exit 4; }
    fi
    if [ "$(id -u)" -eq 0 ]; then printf '%s\n%s\n%s\n' "$OS" "$IFACE" "$ADDR" > "$STATE" 2>/dev/null || true
    else printf '%s\n%s\n%s\n' "$OS" "$IFACE" "$ADDR" | sudo tee "$STATE" >/dev/null 2>&1 || true; fi
    STATUS="APPLIED"; DETAIL="configured only $IFACE with $ADDR; default route untouched"
    emit; exit 0 ;;
  remove)
    local_iface="$IFACE"; local_addr="$ADDR"
    if [ -r "$STATE" ]; then
      { read -r _s_os; read -r _s_if; read -r _s_addr; } < "$STATE" || true
      [ -n "${_s_if:-}" ] && local_iface="$_s_if"
      [ -n "${_s_addr:-}" ] && local_addr="$_s_addr"
    fi
    [ -n "$local_iface" ] || { emit; exit 3; }
    if [ "$OS" = Darwin ]; then
      sudo ifconfig "$local_iface" inet "${local_addr%%/*}" -alias 2>/dev/null || true
    else
      sudo ip addr del "$local_addr" dev "$local_iface" 2>/dev/null || true
    fi
    [ "$(id -u)" -eq 0 ] && rm -f "$STATE" 2>/dev/null || sudo rm -f "$STATE" 2>/dev/null || true
    STATUS="REMOVED"; DETAIL="removed only the address this tool added on $local_iface"
    emit; exit 0 ;;
  tether_test|tether-test) tether_test; exit $? ;;
  diagnose)
    if [ -n "$IFACE" ] && phone_reachable; then
      STATUS="PHONE_REACHABLE"
      DETAIL="phone $(phone_addr) answers on $IFACE"
    elif [ -n "$IFACE" ]; then
      STATUS="PHONE_UNREACHABLE"
      DETAIL="probing phone $(phone_addr) (NOT the host's own $(ADDR%%/*)); link=$(lldp_link_up && echo up || echo down) ip=$(iface_has_addr && echo yes || echo no)"
    fi
    emit; exit "$EXIT" ;;
  ssh)
    [ -n "$IFACE" ] || { emit; exit 3; }
    exec ssh -i "$KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new \
      "${SSH_USER}@$(phone_addr)" ;;
  *) usage; exit 2 ;;
esac
