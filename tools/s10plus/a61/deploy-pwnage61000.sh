#!/usr/bin/env bash
# PWNAGE-61000 — install the read-only MFC diagnostic and truthful player policy.
#
# Userspace only.  This does NOT install mfc_fw.bin, does NOT install the
# experimental decoder helper, does NOT open /dev/video*, and does NOT touch
# the kernel/BOOT/DTB/partitions.  Hardware decode remains blocked until the
# owner approves the patched kernel + verified firmware.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${NUXEL_HOST:-${1:-}}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
[ -n "$HOST" ] || { echo "set NUXEL_HOST=root@host" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes)
R="/tmp/nuxel-p61000.$$"
B="/var/backups/nuxel/p61000-$(date -u +%Y%m%dT%H%M%SZ)"

"${SSH[@]}" 'set -e; test "$(uname -m)" = aarch64; command -v python3 >/dev/null'
"${SSH[@]}" "set -e; mkdir -p '$R' '$B'
  cp -a /usr/local/sbin/nuxel-mfc-diag '$B/' 2>/dev/null || true
  cp -a /usr/local/bin/nuxel-mfc-play '$B/' 2>/dev/null || true
  echo '$B' > /run/nuxel-p61000-backup-dir"
"${SCP[@]}" "$ROOT/tools/s10plus/a61/nuxel-mfc-diag" "$ROOT/tools/s10plus/a61/nuxel-mfc-play" \
  "$ROOT/tools/s10plus/a61/mfc-status.schema.json" "$HOST:$R/" >/dev/null
"${SSH[@]}" "set -euo pipefail
  install -d -m 0755 /usr/local/sbin /usr/local/bin /usr/share/nuxel/mfc
  install -m 0755 '$R/nuxel-mfc-diag' /usr/local/sbin/nuxel-mfc-diag
  install -m 0755 '$R/nuxel-mfc-play' /usr/local/bin/nuxel-mfc-play
  install -m 0644 '$R/mfc-status.schema.json' /usr/share/nuxel/mfc/mfc-status.schema.json
  /usr/local/sbin/nuxel-mfc-diag --self-test
  timeout 30 /usr/local/sbin/nuxel-mfc-diag --status --json
  rm -rf '$R'"
echo "backup=$B"
echo "MFC hardware decode NOT enabled: firmware/kernel path unchanged and no /dev/video* opened"
