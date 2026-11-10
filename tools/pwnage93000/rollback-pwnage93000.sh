#!/usr/bin/env bash
# Restore every file replaced by deploy-pwnage93000.sh from its newest .p93 backup.
set -euo pipefail
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
restore() {
  dest="$1"
  latest=$(ls -1t "$dest".nuxel-rollback-p93-* 2>/dev/null | head -1 || true)
  if [ -n "$latest" ]; then
    cp -a "$latest" "$dest"
    echo "restored $dest <- $latest"
  else
    echo "no p93 backup for $dest (left untouched)"
  fi
}
for base in /usr/share/nuxel/pwa /usr/share/nuxel; do
  [ -d "$base/nuxel-home" ] || continue
  for f in index.html manifest.json sw.js css/status-bar.css \
           js/app.js js/apps.js js/status-bar.js js/qs.js js/bridge.js; do
    restore "$base/nuxel-home/$f"
  done
done
restore /etc/nuxel/app-registry/app_registry.json
restore /usr/share/nuxel/pwa/nuxel-common/app-registry.json
restore /usr/share/nuxel/nuxel-common/app-registry.json
restore /usr/lib/nuxel/nuxel-notifications/notifications.py
restore /usr/lib/nuxel/nuxel-bridge/api.py
restore /usr/lib/nuxel/nuxel-session.sh
restore /usr/lib/nuxel/nuxel-foreign-toplevel
restore /usr/lib/nuxel/nuxel-pwa-host
systemctl restart nuxel-notifications.service
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service
sleep 2
systemctl restart nuxel-wl-fb.service || true
echo ROLLBACK_COMPLETE
REMOTE
