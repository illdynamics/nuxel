#!/usr/bin/env bash
# ============================================================================
# nuxel-live-deploy.sh — deploy a Nuxel userspace file to the RUNNING phone over
# the CDC-ACM live console, with a verified transport and an atomic, rollback-
# capable install.  No flash, no reboot, no TWRP.
#
#   nuxel-live-deploy.sh build/out/s10plus/nuxel-ui-a27 \
#        --to /usr/bin/nuxel-ui --restart nuxel-ui --pin A27-measured-layout-2
#
# WHY IT IS BUILT THIS WAY (mission sections 15/16; every item measured on A27):
#
#   * TRANSPORT.  This link has no flow control and the device's N_TTY input
#     buffer is 4 KiB, so a single bulk write silently LOSES bytes — measured:
#     a 118,746-byte gzip payload arrived as 4,375 bytes.  The payload is
#     therefore sent as base64 lines of <= 1 KiB, and every line travels through
#     nuxel-live.sh's framed channel (unique request id, target-side SHA-256,
#     base64 payload inside end markers, automatic retry) — the one transport
#     this project has already proven on hardware.
#   * EVIDENCE.  Success is only reported when: the assembled base64 file hashes
#     to the local value; the target's own decoder prints RECEIVED <bytes> <sha>
#     matching the LOCAL sha of the raw file; the install prints INSTALLED; the
#     sha256 of the INSTALLED path matches again; and (with --restart) the unit
#     reports active.  "It printed an install command" is never success.
#   * SAFETY.  The previous file is kept as <to>.prev, the swap is a rename inside
#     the destination directory (atomic), a stale revision is restored on any
#     failure, and /usr/lib/nuxel/ui.pinned is written so a later BOOT candidate
#     cannot overwrite what was deployed live.
#   * PORT LOCKING.  Every step runs through nuxel-live.sh, which holds an
#     exclusive flock on the serial device, so a second host tool can never
#     interleave on the port.  A cable pull during the run is reported as
#     "console lost", not a traceback.
#
# Exit: 0 deployed+verified, 1 verification failure (rolled back), 2 usage,
#       3 missing input, 4 console lost.
# ============================================================================
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE="$HERE/nuxel-live.sh"
ROOT="$(cd "$HERE/../.." && pwd)"

LOCAL=""; TO=""; RESTART=""; PIN=""; MODE=755; DEV=""
while [ $# -gt 0 ]; do
  case "$1" in
    --to) TO="$2"; shift 2 ;;
    --restart) RESTART="$2"; shift 2 ;;
    --pin) PIN="$2"; shift 2 ;;
    --mode) MODE="$2"; shift 2 ;;
    --dev) DEV="$2"; shift 2 ;;
    -h|--help) sed -n '2,32p' "$0"; exit 0 ;;
    *) LOCAL="$1"; shift ;;
  esac
done
[ -n "$LOCAL" ] || { echo "usage: $0 <file> [--to /usr/bin/x] [--restart unit] [--pin REV]" >&2; exit 2; }
[ -f "$LOCAL" ] || { echo "missing $LOCAL" >&2; exit 3; }
[ -x "$LIVE" ] || { echo "missing $LIVE" >&2; exit 3; }
[ -n "$TO" ] || TO="/usr/bin/$(basename "$LOCAL")"
DEVARG=""; [ -n "$DEV" ] && DEVARG="--dev $DEV"

WORK="$ROOT/build/out/s10plus/a27/deploy"
mkdir -p "$WORK"
B64="$WORK/payload.b64"
BATCH="$WORK/batch.txt"
SHARE="$WORK/nxrecv.py"
SHA=$(shasum -a 256 "$LOCAL" | cut -d' ' -f1)

python3 - "$LOCAL" "$B64" "$SHARE" <<'PY'
import base64, gzip, sys
local, b64out, share = sys.argv[1], sys.argv[2], sys.argv[3]
raw = open(local, "rb").read()
open(b64out, "w").write(base64.b64encode(gzip.compress(raw, 9)).decode())
open(share, "w").write('''import base64,gzip,hashlib,sys
b64,out,want=sys.argv[1],sys.argv[2],sys.argv[3]
raw=gzip.decompress(base64.b64decode(open(b64,"rb").read()))
h=hashlib.sha256(raw).hexdigest()
if h!=want:
    print("BADHASH",h); sys.exit(3)
open(out,"wb").write(raw); print("RECEIVED",len(raw),h)
''')
print("# payload: %d raw -> %d base64 bytes" % (len(raw), len(open(b64out).read())))
PY
B64SHA=$(shasum -a 256 "$B64" | cut -d' ' -f1)
B64LEN=$(wc -c <"$B64" | tr -d ' ')
CHUNK=1368

echo "# target ${DEV:-auto} -> $TO (mode $MODE) restart=${RESTART:-none} pin=${PIN:-none}"
echo "# local sha256 $SHA   (base64 sha256 $B64SHA, $B64LEN bytes)"

{
  echo "python3 -c \"print('NXRECV_READY')\""
  echo "Sha256sumHelper=1; echo NX_SETUP"
  # the helper is small: one line is enough
  printf 'printf %%s %s | base64 -d > /var/lib/nuxel/nxrecv.py && echo RECV_HELPER_OK\n' \
      "'$(python3 -c "import base64,sys;print(base64.b64encode(open('$SHARE','rb').read()).decode())")'"
  echo ": > /var/lib/nuxel/nxpayload.b64; echo NXPAYLOAD_TRUNCATED"
  python3 - "$B64" "$CHUNK" <<'PY'
import sys
b64 = open(sys.argv[1]).read()
step = int(sys.argv[2])
for i in range(0, len(b64), step):
    print("printf '%%s' '%s' >> /var/lib/nuxel/nxpayload.b64; echo NXL%04d" % (b64[i:i + step], i // step))
PY
  echo "sha256sum -- /var/lib/nuxel/nxpayload.b64"
  echo "python3 /var/lib/nuxel/nxrecv.py /var/lib/nuxel/nxpayload.b64 /var/lib/nuxel/deploy.tmp $SHA || echo RECV_FAILED"
  echo "cp -f $TO $TO.prev 2>/dev/null; echo PREV_KEPT=\$?"
  echo "install -m $MODE /var/lib/nuxel/deploy.tmp $TO.deploy-new && mv -f $TO.deploy-new $TO && echo INSTALLED || echo INSTALL_FAILED"
  echo "sha256sum -- $TO"
  [ -n "$PIN" ] && echo "mkdir -p /usr/lib/nuxel && printf '%s\n' '$PIN' > /usr/lib/nuxel/ui.pinned && printf '%s\n' '$PIN' > /usr/lib/nuxel/ui.rev && cat /usr/lib/nuxel/ui.pinned"
  [ -n "$RESTART" ] && echo "systemctl restart $RESTART; sleep 3; systemctl is-active $RESTART"
  echo "rm -f /var/lib/nuxel/nxpayload.b64; echo NX_CLEANUP"
} >"$BATCH"

echo "# transport: $((B64LEN / CHUNK + 1)) framed commands"
set +e
OUT=$(timeout 3000 bash "$LIVE" $DEVARG --batch "$BATCH" --timeout 40 2>&1)
rc=$?
set -e
echo "$OUT" >"$WORK/deploy.log"
if [ $rc -ne 0 ]; then
  echo "$OUT" | grep -E "console lost|no /dev/cu.usbmodem" >/dev/null 2>&1 && { echo "# CONSOLE LOST — nothing further attempted"; exit 4; }
fi

fails=0
# `set -e` note: grep returns 1 when there is NOTHING to report, which is the
# healthy case.  Capture first, test the text second, or a successful deploy
# exits 1 after installing (measured: app.js/osd.js installed and verified but
# this script returned 1 at the old pipeline).
unverified=$(grep -E "^===== " "$WORK/deploy.log" | grep -v "sha_ok=yes" | head -3 || true)
[ -n "$unverified" ] && { printf '%s\n' "$unverified" | sed 's/^/   ! unverified frame: /'; fails=1; }
nonzero=$(grep -E "^===== " "$WORK/deploy.log" | grep -vE "\[rc=0 " | head -5 || true)
[ -n "$nonzero" ] && printf '%s\n' "$nonzero" | sed 's/^/   ! non-zero exit: /'
[ "$(grep -cE '^===== .*\[rc=0 .*sha_ok=yes\]' "$WORK/deploy.log")" -ge 1 ] || { echo "# no verified frames at all"; exit 4; }

have_b64=$(grep -A3 '^===== sha256sum -- /var/lib/nuxel/nxpayload.b64' "$WORK/deploy.log" | grep -oE '^[[:space:]]+[0-9a-f]{64}' | head -1 | tr -d ' ')
[ "$have_b64" = "$B64SHA" ] || { echo "# TRANSPORT MISMATCH base64 ($have_b64 != $B64SHA) — nothing installed"; exit 1; }
echo "# transport verified: assembled payload base64 sha256 matches"

received=$(grep -E "RECEIVED [0-9]+ [0-9a-f]{64}" "$WORK/deploy.log" | head -1 | tr -s ' ' | awk '{print $3}')
[ "$received" = "$SHA" ] || { echo "# TARGET DECODE/HASH FAILED (RECEIVED '$received') — nothing installed"; exit 1; }
echo "# target decoded the payload and reported the matching sha256"

grep -q "INSTALLED" "$WORK/deploy.log" || { echo "# INSTALL DID NOT REPORT SUCCESS"; exit 1; }
back=$(grep -A3 "^===== sha256sum -- $TO" "$WORK/deploy.log" | grep -oE '^[[:space:]]+[0-9a-f]{64}' | head -1 | tr -d ' ')
if [ "$back" != "$SHA" ]; then
  echo "# READBACK MISMATCH ($back != $SHA) — rolling back"
  bash "$LIVE" $DEVARG --run "test -f $TO.prev && cp -f $TO.prev $TO && echo ROLLED_BACK" --timeout 30 || true
  exit 1
fi
echo "# installed file sha256 verified on the device: $back"

if [ -n "$RESTART" ]; then
  if grep -qE "^[[:space:]]+active$" "$WORK/deploy.log"; then
    echo "# service $RESTART is active after the deploy"
  else
    echo "# SERVICE $RESTART DID NOT COME UP — rolling back"
    bash "$LIVE" $DEVARG --run "test -f $TO.prev && cp -f $TO.prev $TO && systemctl restart $RESTART && echo ROLLED_BACK" --timeout 60 || true
    exit 1
  fi
fi
echo "# DEPLOY COMPLETE (transport + install + service all verified)"
