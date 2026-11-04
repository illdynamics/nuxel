#!/usr/bin/env bash
# PWNAGE-64000 — deploy the GNSS inventory/diagnostic fixes over Wi-Fi SSH.
#
# Userspace only.  No kernel/DTB/partition/firmware writes, no GPS rail write,
# no BBD node open, no reboot.  GPS remains power-OFF and policy-OFF.
#
#   NUXEL_HOST=root@<phone> SSH_KEY=~/.ssh/wicked_wqn_id_rsa \
#       tools/s10plus/a64/deploy-pwnage64000.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${NUXEL_HOST:-${1:-}}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
[ -n "$HOST" ] || { echo "refusing to guess a target: set NUXEL_HOST=root@host" >&2; exit 2; }
[ -r "$KEY" ] || { echo "SSH key not readable: $KEY" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes)
R="/tmp/nuxel-p64000.$$"
B="/var/backups/nuxel/p64000-$(date -u +%Y%m%dT%H%M%SZ)"
BRIDGE=/usr/lib/nuxel/nuxel-bridge

echo "== preflight =="
"${SSH[@]}" 'set -e; test "$(uname -m)" = aarch64; command -v python3 >/dev/null; test -d /etc/nuxel/gnss; test -d /usr/lib/nuxel/nuxel-bridge; test -x /usr/local/bin/nuxel-gnss-diag.sh'
echo "target=$HOST backup=$B"

"${SSH[@]}" "set -e; mkdir -p '$R' '$B'
  for f in /etc/nuxel/gnss/gnss.json /usr/local/bin/nuxel-gnss-diag.sh \
           /usr/local/bin/nuxel-gps-status $BRIDGE/gnss_inventory.py \
           $BRIDGE/bridge.py $BRIDGE/hw_providers.py; do
    [ -e \"\$f\" ] && cp -a \"\$f\" '$B/' || true
  done
  ( cd '$B' && sha256sum * > SHA256SUMS )
  echo '$B' > /run/nuxel-p64000-backup-dir"

"${SCP[@]}" "$ROOT/configs/nuxel/gnss/gnss.json" \
  "$ROOT/tools/s10plus/a33/nuxel-gnss-diag.sh" \
  "$ROOT/services/nuxel-s10/bin/nuxel-gps-status" \
  "$ROOT/services/nuxel-bridge/src/gnss_inventory.py" \
  "$ROOT/services/nuxel-bridge/src/bridge.py" \
  "$ROOT/services/nuxel-bridge/src/hw_providers.py" "$HOST:$R/" >/dev/null

echo "== staged import test =="
"${SSH[@]}" "set -e; rm -rf '$R/testtree'; cp -a $BRIDGE '$R/testtree'
  cp '$R/bridge.py' '$R/hw_providers.py' '$R/gnss_inventory.py' '$R/testtree/'
  cd '$R/testtree' && python3 -c 'import bridge, hw_providers, gnss_inventory'"

echo "== install =="
"${SSH[@]}" "set -euo pipefail
  install -m 0644 '$R/gnss.json' /etc/nuxel/gnss/gnss.json
  install -m 0755 '$R/nuxel-gnss-diag.sh' /usr/local/bin/nuxel-gnss-diag.sh
  install -m 0755 '$R/nuxel-gps-status' /usr/local/bin/nuxel-gps-status
  install -m 0644 '$R/gnss_inventory.py' $BRIDGE/gnss_inventory.py
  install -m 0644 '$R/bridge.py' $BRIDGE/bridge.py
  install -m 0644 '$R/hw_providers.py' $BRIDGE/hw_providers.py
  cd $BRIDGE && python3 -c 'import bridge, hw_providers, gnss_inventory'
  systemctl restart nuxel-http-bridge
  sleep 2
  systemctl is-active nuxel-http-bridge
  curl -fsS http://127.0.0.1:8080/api/v1/health >/dev/null
  timeout 30 /usr/local/bin/nuxel-gnss-diag.sh status --json | tail -1
  timeout 20 /usr/local/bin/nuxel-gnss-diag.sh selftest
  rm -rf '$R'"

echo "PASS: PWNAGE-64000 userspace deployed; GPS remains OFF and no BBD node was opened"
echo "backup=$B"
