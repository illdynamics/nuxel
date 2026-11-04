#!/usr/bin/env bash
# Deploy the PWNAGE-65000 NFC userspace service over Wi-Fi SSH.
# Userspace only: no partition, firmware, bootloader or controller write.
# NFC stays default-OFF after deployment.
#
#   NUXEL_HOST=root@<verified-phone> SSH_KEY=~/.ssh/wicked_wqn_id_rsa \
#       tools/s10plus/a65/deploy-pwnage65000.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${NUXEL_HOST:-${1:-}}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
[ -n "$HOST" ] || { echo "refusing to guess a target: set NUXEL_HOST=root@host" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes)
R=/tmp/nuxel-p65000.$$
B="/var/backups/nuxel/p65000-$(date -u +%Y%m%dT%H%M%SZ)"

echo "== preflight =="
"${SSH[@]}" 'test "$(uname -m)" = aarch64; command -v python3 >/dev/null; test -c /dev/sec-nfc; test -f /lib/firmware/nfc/sec_s3nrn82_firmware.bin'
echo "target=$HOST backup=$B"

"${SSH[@]}" "set -e; mkdir -p '$R/nuxel_nfc' '$B'
  cp -a /usr/lib/nuxel/nuxel-nfc '$B/' 2>/dev/null || true
  cp -a /usr/lib/nuxel/nuxel-bridge/nfc_provider.py '$B/' 2>/dev/null || true
  cp -a /etc/systemd/system/nuxel-nfcd.service '$B/' 2>/dev/null || true
  cp -a /etc/udev/rules.d/90-nuxel-nfc.rules '$B/' 2>/dev/null || true
  echo '$B' > /run/nuxel-p65000-backup-dir"
"${SCP[@]}" "$ROOT"/services/nuxel-nfc/nuxel_nfc/*.py "$HOST:$R/nuxel_nfc/" >/dev/null
"${SCP[@]}" "$ROOT/services/nuxel-nfc/nuxel-nfc" "$ROOT/services/nuxel-nfc/systemd/nuxel-nfcd.service" \
           "$ROOT/services/nuxel-nfc/90-nuxel-nfc.rules" "$ROOT/services/nuxel-bridge/src/nfc_provider.py" "$HOST:$R/" >/dev/null

"${SSH[@]}" "set -euo pipefail
  install -d -m 0755 /usr/lib/nuxel/nuxel-nfc/nuxel_nfc /usr/libexec/nuxel
  install -m 0644 $R/nuxel_nfc/*.py /usr/lib/nuxel/nuxel-nfc/nuxel_nfc/
  install -m 0755 $R/nuxel-nfc /usr/libexec/nuxel/nuxel-nfc
  ln -sfn /usr/libexec/nuxel/nuxel-nfc /usr/bin/nuxel-nfc
  install -m 0644 $R/nuxel-nfcd.service /etc/systemd/system/nuxel-nfcd.service
  install -m 0644 $R/90-nuxel-nfc.rules /etc/udev/rules.d/90-nuxel-nfc.rules
  install -m 0644 $R/nfc_provider.py /usr/lib/nuxel/nuxel-bridge/nfc_provider.py
  systemctl daemon-reload
  systemctl enable nuxel-nfcd.service
  systemctl restart nuxel-nfcd.service
  systemctl restart nuxel-http-bridge.service
  rm -rf $R
  systemctl is-active nuxel-nfcd.service nuxel-http-bridge.service
  /usr/libexec/nuxel/nuxel-nfc selftest
  /usr/libexec/nuxel/nuxel-nfc status | head -40
"
echo "backup=$B"
echo "NFC remains OFF. Owner physical tag test: nuxel-nfc scan --timeout 10"
