#!/usr/bin/env bash
# Restore every file replaced by deploy-pwnage94000.sh from its newest p94 backup.
set -euo pipefail
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
MAN=$(ls -1t /root/p94/installed-*.list 2>/dev/null | head -1 || true)
if [ -z "$MAN" ]; then echo "no p94 install manifest"; exit 1; fi
echo "using $MAN"
while read -r kind dest; do
  case "$kind" in
    present)
      latest=$(ls -1t "$dest".nuxel-rollback-p94-* 2>/dev/null | head -1 || true)
      if [ -n "$latest" ]; then cp -a "$latest" "$dest"; echo "restored $dest"; else echo "missing backup $dest"; fi ;;
    absent)
      rm -f "$dest"; echo "removed newly-installed $dest" ;;
  esac
done < "$MAN"
dconf update 2>/dev/null || true
python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/api.py || true
sh -n /usr/lib/nuxel/nuxel-session.sh || true
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service
sleep 4
systemctl restart nuxel-wl-fb.service || true
echo ROLLBACK_COMPLETE
REMOTE
