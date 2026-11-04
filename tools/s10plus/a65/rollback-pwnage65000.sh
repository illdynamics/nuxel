#!/usr/bin/env bash
# Revert PWNAGE-65000 userspace only.  Never touches partitions or firmware.
set -euo pipefail
HOST="${NUXEL_HOST:-${1:-}}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
[ -n "$HOST" ] || { echo "set NUXEL_HOST=root@host" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
"${SSH[@]}" 'set -euo pipefail
  systemctl disable --now nuxel-nfcd.service 2>/dev/null || true
  rm -f /etc/systemd/system/nuxel-nfcd.service /etc/udev/rules.d/90-nuxel-nfc.rules
  rm -f /usr/bin/nuxel-nfc
  rm -rf /usr/libexec/nuxel/nuxel-nfc /usr/lib/nuxel/nuxel-nfc
  systemctl daemon-reload
  systemctl restart nuxel-http-bridge.service || true
  echo "PWNAGE-65000 userspace reverted; NFC device untouched and OFF"'
