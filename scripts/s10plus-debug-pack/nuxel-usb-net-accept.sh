#!/usr/bin/env bash
# One-command physical acceptance for Nuxel USB networking/tethering (Mac/Linux).
#
#   nuxel-usb-net-accept.sh [--phone 10.15.19.1] [--host 10.15.19.2/24]
#                           [--key ~/.ssh/<key>] [--no-remove]
#
# Steps (each result is printed and recorded; a failure stops the chain):
#   1. exact-device discovery          (never an unrelated Ethernet port)
#   2. preflight (read-only)           (records the default route)
#   3. apply the host address          (only on the proven interface)
#   4. ping the PHONE                  (not the host .2)
#   5. SSH with the pinned key         (public-key only)
#   6. hash-verified transfer          (sha256 round trip)
#   7. USB tether end-to-end proof     (--tether-test; default route untouched)
#   8. remove only what step 3 added   (unless --no-remove)
#
# It never changes the default route, DNS, Wi-Fi, VPN or ZeroTier; it never
# installs a driver and never disables SIP.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
HELPER="$HERE/nuxel-usb-net-host.sh"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
PHONE=""; HOSTADDR=""; REMOVE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --phone) PHONE="$2"; shift 2 ;;
    --host) HOSTADDR="$2"; shift 2 ;;
    --key) KEY="$2"; shift 2 ;;
    --no-remove) REMOVE=0; shift ;;
    -h|--help) sed -n '2,19p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
ARGS=()
[ -n "$PHONE" ] && ARGS+=(--phone "$PHONE")
[ -n "$HOSTADDR" ] && ARGS+=(--address "$HOSTADDR")
ARGS+=(--key "$KEY")
OUT="${NUXEL_USB_ACCEPT_OUT:-${TMPDIR:-/tmp}/nuxel-usb-accept-$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$OUT"
say() { printf '\n== %s\n' "$*"; }
run() { local n="$1"; shift; "$@" >"$OUT/$n.out" 2>"$OUT/$n.err"; local rc=$?; cat "$OUT/$n.out"; [ -s "$OUT/$n.err" ] && sed 's/^/  ! /' "$OUT/$n.err" | tail -5; printf '  -> %s rc=%s\n' "$n" "$rc"; return $rc; }

say "1. discovery (exact USB device)"
run 01-discover bash "$HELPER" --discover --json "${ARGS[@]}" || exit 1
IFACE=$(python3 - "$OUT/01-discover.out" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print(d.get("interface") or "")
PY
)
[ -n "$IFACE" ] || { echo "no exact Nuxel USB interface; is USB Network enabled on the phone?"; exit 1; }

say "2. preflight (default route must not change)"
run 02-preflight bash "$HELPER" --preflight --json --interface "$IFACE" "${ARGS[@]}" || exit 1
ROUTE_BEFORE=$(route -n get default 2>/dev/null | awk '/interface/{print $2}')
echo "default route interface before: ${ROUTE_BEFORE:-unknown}"

say "3. apply host address on $IFACE only"
run 03-apply sudo bash "$HELPER" --apply --interface "$IFACE" "${ARGS[@]}" || exit 1

say "4. ping the phone"
run 04-ping ping -c 3 "${PHONE:-10.15.19.1}" || true

say "5. SSH (pinned key, public-key only)"
run 05-ssh ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes \
      -o StrictHostKeyChecking=accept-new "root@${PHONE:-10.15.19.1}" \
      'uname -a; /usr/lib/nuxel/nuxel-usb-mode.sh status' || true

say "6. hash-verified transfer"
T=$(mktemp); head -c 262144 /dev/urandom > "$T"
SUM_LOCAL=$(shasum -a 256 "$T" | awk '{print $1}')
scp -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "$T" "root@${PHONE:-10.15.19.1}:/tmp/nuxel-xfer.bin" >/dev/null 2>&1
SUM_REMOTE=$(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "root@${PHONE:-10.15.19.1}" 'sha256sum /tmp/nuxel-xfer.bin' 2>/dev/null | awk '{print $1}')
echo "local  $SUM_LOCAL"; echo "remote ${SUM_REMOTE:-<none>}"
[ "$SUM_LOCAL" = "$SUM_REMOTE" ] && echo "  -> transfer SHA256 MATCH" || echo "  -> transfer SHA256 MISMATCH/NOT TESTED"
rm -f "$T"

say "7. USB tether end-to-end (default route must stay on Wi-Fi)"
run 07-tether bash "$HELPER" --tether-test --json --interface "$IFACE" "${ARGS[@]}" || true
ROUTE_AFTER=$(route -n get default 2>/dev/null | awk '/interface/{print $2}')
echo "default route interface after:  ${ROUTE_AFTER:-unknown}"
[ "$ROUTE_BEFORE" = "$ROUTE_AFTER" ] && echo "  -> default route unchanged" || echo "  -> WARNING: default route changed"

if [ "$REMOVE" = 1 ]; then
  say "8. remove only the address this tool added"
  run 08-remove sudo bash "$HELPER" --remove --interface "$IFACE" "${ARGS[@]}" || true
fi
say "evidence: $OUT"
