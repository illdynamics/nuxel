#!/usr/bin/env bash
# PWNAGE-54000 userspace-only deployment over Wi-Fi SSH.
#
#   tools/s10plus/a67/deploy-pwnage54000-apps.sh [nuxel@PHONE_IP]
#
# Scope: orientation daemon/config, Bridge launch/file-listing fixes, PWA
# assets (Home/QS/Settings/Files/Browser/Calendar/Clock/Clipper), the three
# native phone apps, pwa-host log cap and the alarm/Pengu assets.
#
# It NEVER writes /dev/fb0, kernel, firmware, boot or any partition.
# Rollback instructions are printed at the end and saved on the device.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-nuxel@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
TS="$(date -u +%Y%m%dT%H%M%SZ)"
R="/tmp/nuxel-p54000-apps-$TS"
B="/var/backups/nuxel/p54000-apps-$TS"

echo "== preflight =="
"${SSH[@]}" "set -e; test \"\$(uname -m)\" = aarch64; test -e /dev/fb0; command -v wlr-randr >/dev/null; command -v gcc >/dev/null; pkg-config --exists gtk4 libadwaita-1; command -v wayland-scanner >/dev/null; command -v curl >/dev/null"
echo "target=$HOST backup=$B"

echo "== backup =="
"${SSH[@]}" "set -e; sudo mkdir -p '$B'
  for f in /usr/libexec/nuxel/nuxel-orientationd /usr/libexec/nuxel/nuxel_orientation \
           /etc/nuxel/orientation /usr/lib/nuxel/nuxel-bridge/api.py \
           /usr/lib/nuxel/nuxel-bridge/pwa_store.py /usr/lib/nuxel/nuxel-pwa-host \
           /usr/libexec/nuxel/nuxel-orientation-remote-sync \
           /usr/bin/nuxel-contacts /usr/bin/nuxel-messages /usr/bin/nuxel-dialer \
           /etc/nuxel/app-registry/app_registry.json; do
    [ -e \"\$f\" ] && sudo cp -a \"\$f\" '$B'/ || true
  done
  sudo tar -C /usr/share/nuxel -czf '$B/pwa.tgz' pwa/nuxel-home pwa/nuxel-common \
       pwa/nuxel-apps/settings pwa/nuxel-apps/files pwa/nuxel-apps/browser \
       pwa/nuxel-apps/calendar pwa/nuxel-apps/clock pwa/nuxel-apps/clipper \
       assets/nuxel-alarm.mp3 assets/nuxel-app-penguinterface.png 2>/dev/null || true
  sudo cp -a /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json '$B/native-app_registry.json' 2>/dev/null || true
  echo '$B' | sudo tee /run/nuxel-p54000-apps-backup-dir >/dev/null"

echo "== stage =="
"${SSH[@]}" "mkdir -p '$R'"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP"/{orient,config,bridge,tools,shell/nuxel-shell/nuxel-phone-data,pwa,assets}
cp "$ROOT/services/nuxel-orientation/nuxel-orientationd" "$TMP/orient/"
cp -a "$ROOT/services/nuxel-orientation/nuxel_orientation" "$TMP/orient/"
cp "$ROOT/configs/nuxel/orientation/orientation.json" "$ROOT/configs/nuxel/orientation/orientation.schema.json" "$TMP/config/"
cp "$ROOT/services/nuxel-bridge/src/api.py" "$ROOT/services/nuxel-bridge/src/pwa_store.py" "$TMP/bridge/"
cp "$ROOT/services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync" "$TMP/tools/"
cp "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" "$TMP/tools/"
cp "$ROOT/shell/nuxel-shell/nuxel-contacts/main.c" "$TMP/shell/nuxel-contacts.c"
cp "$ROOT/shell/nuxel-shell/nuxel-messages/main.c" "$TMP/shell/nuxel-messages.c"
cp "$ROOT/shell/nuxel-shell/nuxel-dialer/main.c" "$TMP/shell/nuxel-dialer.c"
cp "$ROOT/shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c" "$ROOT/shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.h" "$TMP/shell/nuxel-shell/nuxel-phone-data/"
cp -a "$ROOT/pwa/nuxel-home" "$ROOT/pwa/nuxel-common" "$TMP/pwa/"
for a in settings files browser calendar clock clipper; do cp -a "$ROOT/pwa/nuxel-apps/$a" "$TMP/pwa/"; done
cp "$ROOT/assets/nuxel-alarm.mp3" "$ROOT/assets/nuxel-app-penguinterface.png" "$TMP/assets/"
cp "$ROOT/pwa/nuxel-common/app-registry.json" "$TMP/app_registry.json"
cp "$ROOT/shell/nuxel-home-native/nuxel_home/app_registry.json" "$TMP/app_registry.native.json"
tar czf "$TMP/payload.tgz" -C "$TMP" .
"${SSH[@]}" "tar xzf - -C '$R'" < "$TMP/payload.tgz"

echo "== build on target =="
"${SSH[@]}" "set -euo pipefail; cd '$R'
  CFLAGS='-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11'
  for app in nuxel-contacts nuxel-messages nuxel-dialer; do
    gcc \$CFLAGS \$(pkg-config --cflags gtk4 libadwaita-1) \
        -I shell/nuxel-shell/nuxel-phone-data \
        -o shell/\$app shell/\$app.c shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c \
        \$(pkg-config --libs gtk4 libadwaita-1)
  done
  gcc \$CFLAGS \$(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) -Itools \
      -o tools/nuxel-pwa-host tools/nuxel-pwa-host.c \
      \$(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) -lutil
  python3 -m py_compile orient/nuxel-orientationd orient/nuxel_orientation/*.py \
      bridge/api.py bridge/pwa_store.py tools/nuxel-orientation-remote-sync
  /usr/bin/python3 orient/nuxel-orientationd selftest"

echo "== install =="
"${SSH[@]}" "set -euo pipefail; cd '$R'
  sudo install -d -m 0755 /usr/libexec/nuxel/nuxel_orientation /etc/nuxel/orientation \
       /usr/lib/nuxel/nuxel-bridge /usr/share/nuxel/pwa/nuxel-apps
  sudo install -m 0755 orient/nuxel-orientationd /usr/libexec/nuxel/nuxel-orientationd
  for f in __init__.py policy.py sensors.py apply.py; do
    sudo install -m 0644 orient/nuxel_orientation/\$f /usr/libexec/nuxel/nuxel_orientation/\$f
  done
  sudo install -m 0644 config/orientation.json /etc/nuxel/orientation/orientation.json
  sudo install -m 0644 config/orientation.schema.json /etc/nuxel/orientation/orientation.schema.json
  sudo install -m 0644 bridge/api.py /usr/lib/nuxel/nuxel-bridge/api.py
  sudo install -m 0644 bridge/pwa_store.py /usr/lib/nuxel/nuxel-bridge/pwa_store.py
  sudo install -m 0755 tools/nuxel-orientation-remote-sync /usr/libexec/nuxel/nuxel-orientation-remote-sync
  sudo install -m 0755 tools/nuxel-pwa-host /usr/lib/nuxel/nuxel-pwa-host
  for app in nuxel-contacts nuxel-messages nuxel-dialer; do
    sudo install -m 0755 shell/\$app /usr/bin/\$app
  done
  sudo cp -a pwa/nuxel-home/. /usr/share/nuxel/pwa/nuxel-home/
  sudo cp -a pwa/nuxel-common/. /usr/share/nuxel/pwa/nuxel-common/
  for a in settings files browser calendar clock clipper; do
    sudo mkdir -p /usr/share/nuxel/pwa/nuxel-apps/\$a
    sudo cp -a pwa/\$a/. /usr/share/nuxel/pwa/nuxel-apps/\$a/
  done
  sudo install -m 0644 assets/nuxel-alarm.mp3 /usr/share/nuxel/assets/nuxel-alarm.mp3
  sudo install -m 0644 assets/nuxel-app-penguinterface.png /usr/share/nuxel/assets/nuxel-app-penguinterface.png
  sudo install -m 0644 app_registry.json /etc/nuxel/app-registry/app_registry.json
  sudo install -m 0644 app_registry.native.json /usr/lib/nuxel/nuxel-home-native/nuxel_home/app_registry.json
  sudo systemctl daemon-reload
  sudo systemctl restart nuxel-orientationd nuxel-http-bridge nuxel-bridge
  sleep 2
  systemctl is-active nuxel-orientationd nuxel-http-bridge nuxel-bridge
  sudo /usr/libexec/nuxel/nuxel-orientationd selftest
  sudo /usr/libexec/nuxel/nuxel-orientationd sensor --json | head -40 || true"

echo
echo "== post-deploy checks =="
"${SSH[@]}" "sudo /usr/libexec/nuxel/nuxel-orientationd status --json | \
  python3 -c 'import sys,json;d=json.load(sys.stdin);print(\"mode\",d[\"mode\"],d[\"mode_label\"],\"effective\",d[\"effective_orientation\"],\"applied\",d[\"applied\"]);print(\"display\",d[\"display\"][\"output\"],d[\"display\"][\"transform\"],d[\"display\"][\"logical_width\"],\"x\",d[\"display\"][\"logical_height\"]);print(\"sensor\",d[\"sensor\"][\"available\"],d[\"sensor\"].get(\"hub\",{}).get(\"auto_blocked_reason\"))'"

cat <<EOF

Deployment complete. Backup: $B
Restart the launcher only when convenient (it reloads the new PWA assets):
  ssh -i $KEY $HOST 'sudo systemctl restart nuxel-wayland'
  # If a PWA still serves a cached bundle, bump/reload Home once; sw.js is v82.

Rollback (userspace only):
  ssh -i $KEY $HOST 'sudo bash -c "
    B=\$(cat /run/nuxel-p54000-apps-backup-dir)
    sudo install -m 0755 \$B/nuxel-orientationd /usr/libexec/nuxel/nuxel-orientationd
    sudo cp -a \$B/nuxel_orientation/. /usr/libexec/nuxel/nuxel_orientation/
    sudo cp -a \$B/orientation/. /etc/nuxel/orientation/
    sudo install -m 0644 \$B/api.py /usr/lib/nuxel/nuxel-bridge/api.py
    sudo install -m 0644 \$B/pwa_store.py /usr/lib/nuxel/nuxel-bridge/pwa_store.py
    sudo install -m 0755 \$B/nuxel-pwa-host /usr/lib/nuxel/nuxel-pwa-host
    sudo install -m 0755 \$B/nuxel-contacts /usr/bin/nuxel-contacts
    sudo install -m 0755 \$B/nuxel-messages /usr/bin/nuxel-messages
    sudo install -m 0755 \$B/nuxel-dialer /usr/bin/nuxel-dialer
    sudo tar -C /usr/share/nuxel -xzf \$B/pwa.tgz
    sudo systemctl restart nuxel-orientationd nuxel-http-bridge nuxel-bridge
  "'
