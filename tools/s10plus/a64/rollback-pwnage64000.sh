#!/usr/bin/env bash
# PWNAGE-64000 — restore the pre-deploy GNSS userspace files.
# Userspace only; never touches kernel, partitions, firmware or the GPS rail.
set -euo pipefail
HOST="${NUXEL_HOST:-${1:-}}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
B="${2:-}"
[ -n "$HOST" ] || { echo "set NUXEL_HOST=root@host [backup-dir]" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
if [ -z "$B" ]; then
  B="$("${SSH[@]}" 'cat /run/nuxel-p64000-backup-dir 2>/dev/null || true')"
fi
[ -n "$B" ] || { echo "no backup dir recorded" >&2; exit 2; }
"${SSH[@]}" "set -euo pipefail
  test -d '$B'
  ( cd '$B' && sha256sum -c SHA256SUMS --quiet )
  for f in gnss.json nuxel-gnss-diag.sh nuxel-gps-status; do
    [ -e '$B/'\$f ] || continue
    case \$f in
      gnss.json) install -m 0644 '$B/'\$f /etc/nuxel/gnss/gnss.json ;;
      *) install -m 0755 '$B/'\$f /usr/local/bin/\$f ;;
    esac
  done
  for f in gnss_inventory.py bridge.py hw_providers.py; do
    [ -e '$B/'\$f ] && install -m 0644 '$B/'\$f /usr/lib/nuxel/nuxel-bridge/\$f || true
  done
  systemctl restart nuxel-http-bridge || true
  sleep 2
  systemctl is-active nuxel-http-bridge || true
  echo ROLLBACK_OK"
