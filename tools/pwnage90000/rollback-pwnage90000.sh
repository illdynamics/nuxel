#!/usr/bin/env bash
# Roll back the PWNAGE-90000 native/PWA/Python deploy using the in-place
# .nuxel-rollback-p90-<timestamp> copies created by the deploy step.
#
#   NUXEL_HOST=root@192.168.178.167 NUXEL_SSH_KEY=~/.ssh/wicked_wqn_id_rsa \
#       ./tools/pwnage90000/rollback-pwnage90000.sh
set -euo pipefail
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
restore() {
  target="$1"
  latest=$(ls -1t "$target".nuxel-rollback-p90-* 2>/dev/null | head -1 || true)
  if [ -n "$latest" ] && [ -e "$latest" ]; then
    cp -a "$latest" "$target"
    echo "RESTORED $target <- $latest"
  else
    echo "NO_BACKUP $target"
  fi
}
for b in nuxel-navdock nuxel-statusbar nuxel-foreign-toplevel nuxel-pwa-host; do
  restore "/usr/lib/nuxel/$b"
done
restore /usr/lib/nuxel/nuxel-preload-cinema
restore /usr/lib/nuxel/nuxel-bridge/api.py
for base in /usr/share/nuxel/pwa /usr/share/nuxel; do
  for f in js/app.js js/qs.js js/immersive.js js/status-bar.js js/apps.js js/launcher.js \
           sw.js manifest.json css/launcher.css; do
    restore "$base/nuxel-home/$f"
  done
  restore "$base/nuxel-common/back.js"
  restore "$base/nuxel-apps/settings/power-menu.js" 2>/dev/null || true
  restore "$base/nuxel-apps/settings/power-menu.css" 2>/dev/null || true
done
systemctl restart nuxel-bridge.service nuxel-http-bridge.service || true
systemctl restart nuxel-wayland.service || true
sleep 2
systemctl restart nuxel-wl-fb.service || true
echo "ROLLBACK_COMPLETE"
REMOTE
