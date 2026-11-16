#!/usr/bin/env bash
# PWNAGE-USBNET userspace deploy + rollback for the connected Nuxel S10+.
#
# Ships ONLY userspace (bridge provider, helpers, systemd units, PWA assets).
# It does NOT touch the kernel, boot, DTBO or any other partition: the kernel
# half is the single combined reflash (see PWNAGE-USBNET-REFLASH-MANIFEST.md).
#
#   NUXEL_HOST=root@192.168.178.167 NUXEL_SSH_KEY=~/.ssh/wicked_wqn_id_rsa \
#       ./tools/pwnage_usbnet/deploy-pwnage-usbnet.sh [--rollback]
#
# Every replaced file is backed up as <file>.nuxel-rollback-usbnet-<UTC>.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
MODE=deploy
[ "${1:-}" = "--rollback" ] && MODE=rollback
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=8 "$HOST")

FILES=(
  "services/nuxel-bridge/src/api.py:/usr/lib/nuxel/nuxel-bridge/api.py:0644"
  "services/nuxel-bridge/src/usb_tethering.py:/usr/lib/nuxel/nuxel-bridge/usb_tethering.py:0644"
  "services/nuxel-bridge/src/usb_tether.py:/usr/lib/nuxel/nuxel-bridge/usb_tether.py:0644"
  "services/nuxel-bridge/src/usb_mode.py:/usr/lib/nuxel/nuxel-bridge/usb_mode.py:0644"
  "services/nuxel-bridge/src/tri_link_status.py:/usr/lib/nuxel/nuxel-bridge/tri_link_status.py:0644"
  "services/nuxel-bridge/src/network_manager.py:/usr/lib/nuxel/nuxel-bridge/network_manager.py:0644"
  "services/nuxel-s10/bin/nuxel-usb-mode.sh:/usr/lib/nuxel/nuxel-usb-mode.sh:0755"
  "services/nuxel-s10/bin/nuxel-usb-net-monitor.sh:/usr/lib/nuxel/nuxel-usb-net-monitor.sh:0755"
  "services/nuxel-s10/systemd/nuxel-usb-net-restore.service:/etc/systemd/system/nuxel-usb-net-restore.service:0644"
  "services/nuxel-s10/systemd/nuxel-usb-net-monitor.service:/etc/systemd/system/nuxel-usb-net-monitor.service:0644"
  "pwa/nuxel-home/index.html:/usr/share/nuxel/pwa/nuxel-home/index.html:0644"
  "pwa/nuxel-home/js/qs.js:/usr/share/nuxel/pwa/nuxel-home/js/qs.js:0644"
  "pwa/nuxel-home/js/lockscreen-indicators.js:/usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js:0644"
  "pwa/nuxel-home/css/status-bar.css:/usr/share/nuxel/pwa/nuxel-home/css/status-bar.css:0644"
  "pwa/nuxel-apps/settings/index.html:/usr/share/nuxel/pwa/nuxel-apps/settings/index.html:0644"
  "pwa/nuxel-apps/settings/usb-network-settings.js:/usr/share/nuxel/pwa/nuxel-apps/settings/usb-network-settings.js:0644"
)

if [ "$MODE" = rollback ]; then
  "${SSH[@]}" 'bash -s' <<'REMOTE'
set -uo pipefail
# Return to the safe ACM-only composition FIRST (single owner), then restore
# files.  No other program removes configfs functions.
/usr/lib/nuxel/nuxel-usb-mode.sh off >/dev/null 2>&1 || true
for f in /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/usb_tethering.py \
         /usr/lib/nuxel/nuxel-bridge/usb_tether.py /usr/lib/nuxel/nuxel-bridge/usb_mode.py \
         /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/network_manager.py \
         /usr/lib/nuxel/nuxel-usb-mode.sh /usr/lib/nuxel/nuxel-usb-net-monitor.sh \
         /etc/systemd/system/nuxel-usb-net-restore.service /etc/systemd/system/nuxel-usb-net-monitor.service; do
  last=$(ls -1t "$f".nuxel-rollback-usbnet-* 2>/dev/null | head -1 || true)
  [ -n "$last" ] && cp -a "$last" "$f" && echo "restored $f"
done
systemctl daemon-reload; systemctl restart nuxel-bridge.service || true
echo ROLLBACK_COMPLETE
REMOTE
  exit $?
fi

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
for entry in "${FILES[@]}"; do
  printf '%s\n' "${entry%%:*}" >> "$TMP/list"
done
tar czf "$TMP/usbnet.tar.gz" -C "$ROOT" -T "$TMP/list"
scp -q -i "$KEY" -o BatchMode=yes "$TMP/usbnet.tar.gz" "$HOST:/tmp/usbnet.tar.gz"
"${SSH[@]}" "MODE=$MODE bash -s" <<'REMOTE'
set -euo pipefail
TS=$(date +%Y%m%dT%H%M%S); S=/tmp/usbnet-$TS; mkdir -p "$S"; tar xzf /tmp/usbnet.tar.gz -C "$S"
backup() { [ -e "$1" ] && cp -a "$1" "$1.nuxel-rollback-usbnet-$TS" || true; }
for pair in \
  services/nuxel-bridge/src/api.py:/usr/lib/nuxel/nuxel-bridge/api.py:0644 \
  services/nuxel-bridge/src/usb_tethering.py:/usr/lib/nuxel/nuxel-bridge/usb_tethering.py:0644 \
  services/nuxel-bridge/src/usb_tether.py:/usr/lib/nuxel/nuxel-bridge/usb_tether.py:0644 \
  services/nuxel-bridge/src/usb_mode.py:/usr/lib/nuxel/nuxel-bridge/usb_mode.py:0644 \
  services/nuxel-bridge/src/tri_link_status.py:/usr/lib/nuxel/nuxel-bridge/tri_link_status.py:0644 \
  services/nuxel-bridge/src/network_manager.py:/usr/lib/nuxel/nuxel-bridge/network_manager.py:0644 \
  services/nuxel-s10/bin/nuxel-usb-mode.sh:/usr/lib/nuxel/nuxel-usb-mode.sh:0755 \
  services/nuxel-s10/bin/nuxel-usb-net-monitor.sh:/usr/lib/nuxel/nuxel-usb-net-monitor.sh:0755 \
  services/nuxel-s10/systemd/nuxel-usb-net-restore.service:/etc/systemd/system/nuxel-usb-net-restore.service:0644 \
  services/nuxel-s10/systemd/nuxel-usb-net-monitor.service:/etc/systemd/system/nuxel-usb-net-monitor.service:0644 \
  pwa/nuxel-home/index.html:/usr/share/nuxel/pwa/nuxel-home/index.html:0644 \
  pwa/nuxel-home/js/qs.js:/usr/share/nuxel/pwa/nuxel-home/js/qs.js:0644 \
  pwa/nuxel-home/js/lockscreen-indicators.js:/usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js:0644 \
  pwa/nuxel-home/css/status-bar.css:/usr/share/nuxel/pwa/nuxel-home/css/status-bar.css:0644 \
  pwa/nuxel-apps/settings/index.html:/usr/share/nuxel/pwa/nuxel-apps/settings/index.html:0644 \
  pwa/nuxel-apps/settings/usb-network-settings.js:/usr/share/nuxel/pwa/nuxel-apps/settings/usb-network-settings.js:0644; do
  src=${pair%%:*}; rest=${pair#*:}; dst=${rest%%:*}; mode=${rest#*:}
  install -d "$(dirname "$dst")"; backup "$dst"; install -m "$mode" "$S/$src" "$dst"
done
python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-bridge/usb_tether.py \
  /usr/lib/nuxel/nuxel-bridge/usb_tethering.py /usr/lib/nuxel/nuxel-bridge/usb_mode.py \
  /usr/lib/nuxel/nuxel-bridge/tri_link_status.py /usr/lib/nuxel/nuxel-bridge/network_manager.py
bash -n /usr/lib/nuxel/nuxel-usb-mode.sh /usr/lib/nuxel/nuxel-usb-net-monitor.sh
# The retired second owner must not survive on a live system.
rm -f /usr/lib/nuxel/nuxel-usb-net-helper.sh
systemctl disable nuxel-usb-mode-restore.service >/dev/null 2>&1 || true
systemctl daemon-reload
systemctl enable nuxel-usb-net-monitor.service nuxel-usb-net-restore.service >/dev/null 2>&1 || true
systemctl restart nuxel-usb-net-monitor.service || true
systemctl restart nuxel-bridge.service
/usr/lib/nuxel/nuxel-usb-mode.sh status || true
echo "DEPLOY_COMPLETE TS=$TS"
REMOTE
