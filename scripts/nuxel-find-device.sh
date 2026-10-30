#!/usr/bin/env bash
# nuxel-find-device.sh — locate the Nuxel S10+ on the current /24 LAN and print
# a ready-to-run SSH command.  PWNAGE-37000 companion debug tool.
#
#   scripts/nuxel-find-device.sh                # full discovery (serial first, then nmap)
#   scripts/nuxel-find-device.sh --serial-only  # only the USB-serial IP probe
#   scripts/nuxel-find-device.sh --lan-only     # only the nmap/ARP scan
#   scripts/nuxel-find-device.sh --ping-ip 10.17.239.166
#
# Strategy (in this order, never silently falling back between transports):
#   1. USB serial console  — read the WLAN IP directly from the phone over the
#      CDC-ACM gadget (fastest and authoritative; no guessing).
#   2. nmap / ARP          — scan the current /24 (derived from the default
#      route interface) and match the Nuxel hardware address or its vendor
#      prefixes.  Requires nmap; if it is absent the ARP fallback is used.
#
# SAFETY: this script NEVER opens /dev/fb0 and never writes to the phone.
# It only reads the serial console and sends harmless read-only commands.

set -uo pipefail

KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH_USER="${NUXEL_SSH_USER:-root}"
# The S10+ wlan0 address is not manufacturer-stable across images: Fedora's
# NetworkManager may randomise the locally-administered MAC on each network.
# The authoritative value is read from the phone over USB serial and cached
# here (or supplied with NUXEL_HW_MAC).  The old a2:24:64:59:32:f1 default is
# kept only as one more candidate, never as the sole identity.
MAC_CACHE="${NUXEL_MAC_CACHE:-$HOME/.cache/nuxel/wlan0.mac}"
NUXEL_MAC="${NUXEL_HW_MAC:-}"
if [ -z "$NUXEL_MAC" ] && [ -f "$MAC_CACHE" ]; then
  NUXEL_MAC="$(tr -d '[:space:]' < "$MAC_CACHE")"
fi
# Known historical addresses / Broadcom-Samsung OUI prefixes.  They are
# candidates only; --lan-only reports every match rather than assuming one.
NUXEL_MAC_PREFIXES=("a2:24:64" "a4:5e:60" "e8:6f:38" "d0:39:57" "78:bd:bc" "96:42:b9")
LEGACY_MACS=("a2:24:64:59:32:f1")

SERIAL_ONLY=0; LAN_ONLY=0; PING_IP=""
while [ $# -gt 0 ]; do
  case "$1" in
    --serial-only) SERIAL_ONLY=1; shift ;;
    --lan-only) LAN_ONLY=1; shift ;;
    --ping-ip) PING_IP="$2"; shift 2 ;;
    -h|--help) sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

log() { printf '%s\n' "$*" >&2; }

# ---------------------------------------------------------------------------
# USB serial IP probe (embedded, self-contained).  Uses the same CDC-ACM
# framing/ANSI-filter approach as the existing nuxel-live/console tools.
# ---------------------------------------------------------------------------
serial_discover_dev() {
  local n
  for n in /dev/cu.usbmodem* /dev/ttyACM*; do
    [ -e "$n" ] && { printf '%s\n' "$n"; return 0; }
  done
  return 1
}

serial_ip() {
  local dev="$1" py
  py="$(command -v python3 || command -v python)"
  [ -n "$py" ] || { log "!! python3 required for serial probe"; return 1; }
  "$py" - "$dev" <<'PY'
import os, sys, termios, time, select, re
dev = sys.argv[1]
try:
    fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
except OSError as e:
    print("!! cannot open %s: %s" % (dev, e))
    sys.exit(1)
a = termios.tcgetattr(fd)
a[0] = a[1] = 0
a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
a[3] = 0
a[4] = a[5] = 9600
termios.tcsetattr(fd, termios.TCSANOW, a)
termios.tcflush(fd, termios.TCIOFLUSH)
def drain(secs):
    out = b""
    t0 = time.time()
    while time.time() - t0 < secs:
        r, _, _ = select.select([fd], [], [], 0.2)
        if r:
            try:
                c = os.read(fd, 65536)
            except OSError:
                break
            if c:
                out += c
    return out
drain(0.2)
begin = "NXLB_%d" % int(time.time() * 1000)
end = "NXLE_%d" % int(time.time() * 1000)
os.write(fd, ("echo %s\r" % begin).encode())
time.sleep(0.25)
os.write(fd, b"ip -4 addr show wlan0; cat /sys/class/net/wlan0/address\r")
time.sleep(1.4)
os.write(fd, ("echo %s\r" % end).encode())
time.sleep(0.4)
data = drain(1.5).decode("utf-8", "replace")
os.close(fd)
bi = data.find(begin)
ei = data.find(end, bi + len(begin))
chunk = data[bi + len(begin):ei] if bi != -1 and ei != -1 else data
chunk = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", chunk)
ips = re.findall(r"inet\s+(\d+\.\d+\.\d+\.\d+)/", chunk)
if not ips:
    print("!! serial console reachable but no wlan0 IPv4 line found")
    sys.exit(1)
macs = re.findall(r"(?<![0-9a-fA-F:])((?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2})(?![0-9a-fA-F:])", chunk)
print(ips[0] + "\t" + (macs[0].lower() if macs else ""))
PY
}

# ---------------------------------------------------------------------------
# Current /24 LAN from the default route interface.
# ---------------------------------------------------------------------------
lan_prefix() {
  local def dev ip
  def="$(route -n get default 2>/dev/null | awk '/interface:/{print $2; exit}')"
  dev="${def:-en0}"
  ip="$(ipconfig getifaddr "$dev" 2>/dev/null)"
  if [ -n "$ip" ]; then
    printf '%s\t%s\n' "$(printf '%s' "$ip" | awk -F. '{printf "%s.%s.%s.0/24", $1, $2, $3}')" "$dev"
  else
    printf '\t%s\n' "$dev"
  fi
}

# ---------------------------------------------------------------------------
# nmap/ARP discovery of the current /24.
# ---------------------------------------------------------------------------
lan_discover() {
  local prefix="$1" ip nmap_out mac line cand
  nmap_out=""
  if command -v nmap >/dev/null 2>&1; then
    log "# nmap -sn ${prefix} (may take a few seconds) ..."
    nmap_out="$(nmap -sn -T4 --max-retries 1 "$prefix" 2>/dev/null || true)"
  fi
  # Parse nmap "Nmap scan report for <ip>" + "MAC Address: ..." pairs.
  ip=""
  while IFS= read -r line; do
    case "$line" in
      *"Nmap scan report for "*) ip="${line##*for }" ;;
      *"MAC Address: "*)
        mac="$(printf '%s' "$line" | sed -n 's/.*MAC Address: \([0-9A-Fa-f:]*\).*/\1/p' | tr 'A-F' 'a-f')"
        [ -n "$ip" ] || continue
        for cand in "$NUXEL_MAC" "${LEGACY_MACS[@]}" "${NUXEL_MAC_PREFIXES[@]}"; do
          [ -n "$cand" ] || continue;
          cand="$(printf '%s' "$cand" | tr 'A-F' 'a-f')"
          if [ "${mac#${cand}}" != "$mac" ]; then
            printf '%s\t%s\n' "$ip" "$mac"
            break
          fi
        done
        ;;
    esac
  done <<< "$nmap_out"
  # ARP fallback (also catches an already-active peer without a fresh nmap run).
  if command -v arp >/dev/null 2>&1; then
    arp -a 2>/dev/null | while IFS= read -r line; do
      mac="$(printf '%s' "$line" | grep -oE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' | head -1 | tr 'A-F' 'a-f')"
      ip="$(printf '%s' "$line" | grep -oE '\(([0-9]{1,3}\.){3}[0-9]{1,3}\)' | head -1 | tr -d '()')"
      [ -n "$ip" ] && [ -n "$mac" ] || continue
      for cand in "$NUXEL_MAC" "${LEGACY_MACS[@]}" "${NUXEL_MAC_PREFIXES[@]}"; do
        cand="$(printf '%s' "$cand" | tr 'A-F' 'a-f')"
        if [ "${mac#${cand}}" != "$mac" ]; then
          printf '%s\t%s\n' "$ip" "$mac"
          break
        fi
      done
    done
  fi
}

# ---------------------------------------------------------------------------
main() {
  [ -n "$PING_IP" ] && { log "# ping check: $PING_IP"; ping -c 1 -t 2 "$PING_IP" >/dev/null 2>&1 && log "reachable: $PING_IP" || log "unreachable: $PING_IP"; exit 0; }

  local serial_ip="" serial_mac=""
  if [ "$LAN_ONLY" -ne 1 ]; then
    local dev found_serial
    if dev="$(serial_discover_dev)"; then
      log "# USB serial console: $dev"
      found_serial="$(serial_ip "$dev")"
      if [ -n "$found_serial" ]; then
        serial_ip="${found_serial%%$'\t'*}"
        serial_mac="${found_serial#*$'\t'}"
        [ "$serial_mac" = "$found_serial" ] && serial_mac=""
        log "# WLAN IP from serial: $serial_ip"
        if [ -n "$serial_mac" ]; then
          log "# WLAN hardware address from serial: $serial_mac"
          NUXEL_MAC="$serial_mac"
          mkdir -p "$(dirname "$MAC_CACHE")" 2>/dev/null || true
          printf '%s\n' "$serial_mac" > "$MAC_CACHE" 2>/dev/null || true
        fi
      fi
    else
      log "# no USB serial console (cu.usbmodem*/ttyACM*) present"
    fi
  fi

  if [ "$SERIAL_ONLY" -eq 1 ]; then
    if [ -n "$serial_ip" ]; then
      printf '%s\n' "$serial_ip"
      log "ssh -i $KEY ${SSH_USER}@${serial_ip}"
      return 0
    fi
    log "!! no serial IP discovered"
    return 1
  fi

  local lan_info prefix lan_iface found ip mac
  lan_info="$(lan_prefix)"
  prefix="${lan_info%%$'\t'*}"
  lan_iface="${lan_info#*$'\t'}"
  [ -n "$prefix" ] && prefix="${prefix:-$(lan_prefix | cut -f1)}"
  log "# current LAN: $prefix  (interface ${lan_iface:-en0})"
  found=""
  while IFS=$'\t' read -r ip mac; do
    [ -n "$ip" ] || continue
    log "# LAN match: $ip  ($mac)"
    printf '%s\n' "$ip"
    found="$ip"
  done < <(lan_discover "$prefix")

  # Serial IP is authoritative; prefer it when the LAN scan is inconclusive.
  if [ -n "$serial_ip" ] && [ -z "$found" ]; then
    printf '%s\n' "$serial_ip"
    found="$serial_ip"
  fi

  if [ -z "$found" ]; then
    log "!! no Nuxel device matched in $prefix"
    log "   (serial IP: ${serial_ip:-none}, MAC target: ${NUXEL_MAC:-unknown})"
    log "   connect USB once (or set NUXEL_HW_MAC=xx:xx:...) so the current"
    log "   hardware address can be learned for future --lan-only scans."
    return 1
  fi

  log "ssh -i $KEY ${SSH_USER}@${found}"
  return 0
}

main
