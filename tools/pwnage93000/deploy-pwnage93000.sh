#!/usr/bin/env bash
# PWNAGE-93000 reproducible build + safe deploy for the connected Nuxel S10+.
# Every replaced file is backed up as <name>.nuxel-rollback-p93-<UTC>.
# Native helper is built natively on the phone; PWA/bridge/daemon files are
# installed from this working tree.  No boot/recovery/kernel/firmware writes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar czf "$TMP/pwa.tar.gz" -C "$ROOT" \
  pwa/nuxel-home/index.html pwa/nuxel-home/manifest.json pwa/nuxel-home/sw.js \
  pwa/nuxel-home/css/status-bar.css \
  pwa/nuxel-home/js/app.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/js/status-bar.js \
  pwa/nuxel-home/js/qs.js pwa/nuxel-home/js/bridge.js \
  pwa/nuxel-common/app-registry.json
tar czf "$TMP/py.tar.gz" -C "$ROOT" \
  services/nuxel-notifications/src/notifications.py \
  services/nuxel-bridge/src/api.py \
  tools/s10plus/a45/nuxel-session.sh \
  tools/s10plus/a45/nuxel-pwa-host.c \
  tools/s10plus/a59/nuxel-foreign-toplevel.c

"${SSH[@]}" 'rm -rf /root/p93 /tmp/p93stage; mkdir -p /root/p93/out /tmp/p93stage'
"${SCP[@]}" "$TMP/pwa.tar.gz" "$TMP/py.tar.gz" "$HOST:/tmp/" >/dev/null

"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd /tmp/p93stage
tar xzf /tmp/pwa.tar.gz
tar xzf /tmp/py.tar.gz
mkdir -p /root/p93/out
# Build only the toplevel helper that changed (native ARM64 on the phone).
gcc -O2 -Wall -Wextra -o /root/p93/out/nuxel-foreign-toplevel \
    tools/s10plus/a59/nuxel-foreign-toplevel.c -ldl
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
  /root/p93/out/nuxel-foreign-toplevel list >/dev/null
gcc -O2 -Wall -Wextra -Wno-unused-parameter -I/usr/include \
  -o /root/p93/out/nuxel-pwa-host tools/s10plus/a45/nuxel-pwa-host.c \
  $(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil -lz

TS=$(date +%Y%m%dT%H%M%S)
backup() { if [ -e "$1" ]; then cp -a "$1" "$1.nuxel-rollback-p93-$TS"; fi; return 0; }
install_file() {
  src="$1"; dest="$2"; mode="$3"
  [ -d "$(dirname "$dest")" ] || return 0
  backup "$dest"
  install -m "$mode" "$src" "$dest"
}

for base in /usr/share/nuxel/pwa /usr/share/nuxel; do
  [ -d "$base/nuxel-home" ] || continue
  for f in index.html manifest.json sw.js css/status-bar.css \
           js/app.js js/apps.js js/status-bar.js js/qs.js js/bridge.js; do
    install_file "/tmp/p93stage/pwa/nuxel-home/$f" "$base/nuxel-home/$f" 0644
  done
done
# Canonical registry consumed by the bridge and by Home after refresh.
if [ -d /etc/nuxel/app-registry ]; then
  install_file /tmp/p93stage/pwa/nuxel-common/app-registry.json \
    /etc/nuxel/app-registry/app_registry.json 0644
fi
for base in /usr/share/nuxel/pwa/nuxel-common /usr/share/nuxel/nuxel-common; do
  install_file /tmp/p93stage/pwa/nuxel-common/app-registry.json \
    "$base/app-registry.json" 0644
done

install_file /tmp/p93stage/services/nuxel-notifications/src/notifications.py \
  /usr/lib/nuxel/nuxel-notifications/notifications.py 0644
install_file /tmp/p93stage/services/nuxel-bridge/src/api.py \
  /usr/lib/nuxel/nuxel-bridge/api.py 0644
install_file /tmp/p93stage/tools/s10plus/a45/nuxel-session.sh \
  /usr/lib/nuxel/nuxel-session.sh 0755
install_file /root/p93/out/nuxel-foreign-toplevel \
  /usr/lib/nuxel/nuxel-foreign-toplevel 0755
install_file /root/p93/out/nuxel-pwa-host \
  /usr/lib/nuxel/nuxel-pwa-host 0755

python3 -m py_compile /usr/lib/nuxel/nuxel-notifications/notifications.py \
  /usr/lib/nuxel/nuxel-bridge/api.py
sh -n /usr/lib/nuxel/nuxel-session.sh
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
  /usr/lib/nuxel/nuxel-foreign-toplevel list >/dev/null

systemctl restart nuxel-notifications.service
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
# The session script is read by nuxel-wayland; restarting it applies the PWA,
# relays, and all session-owned native helpers together.
systemctl restart nuxel-wayland.service
sleep 3
systemctl restart nuxel-wl-fb.service || true
sleep 2
echo "DEPLOY_COMPLETE TS=$TS"
REMOTE
