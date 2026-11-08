#!/bin/sh
# Deploy the A76 opt-in text-input-v1 shim, keyboard setting and Settings UI.
# Usage: tools/s10plus/a76/deploy-a76.sh [root@host]
set -eu

HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
STAGE="/var/tmp/nuxel-a76-$$"
TS=$(date -u +%Y%m%dT%H%M%SZ)

SSH="ssh -i $KEY -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 $HOST"
SCP="scp -i $KEY -o IdentitiesOnly=yes"

$SSH "id -u | grep -qx 0; mkdir -p '$STAGE'"
$SCP "$ROOT/tools/s10plus/a76/phoc-text-input-v1.patch" \
     "$ROOT/tools/s10plus/a76/a76-build-phoc-text-input-v1.sh" \
     "$ROOT/tools/s10plus/a33/nuxel-keyboard-apply.sh" \
     "$ROOT/configs/nuxel/keyboard/keyboard.json" \
     "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" \
     "$ROOT/tools/s10plus/a45/nuxel-session.sh" \
     "$ROOT/pwa/nuxel-apps/settings/index.html" \
     "$ROOT/pwa/nuxel-apps/settings/settings-model.js" \
     "$ROOT/pwa/nuxel-apps/settings/keyboard-settings.js" \
     "$HOST:$STAGE/"

$SSH "STAGE='$STAGE' TS='$TS' sh -s" <<'REMOTE'
set -eu

B="/var/backups/nuxel/a76-$TS"
mkdir -p "$B"
backup() {
  if [ -e "$1" ]; then
    mkdir -p "$B/$(dirname "${1#/}")"
    cp -a "$1" "$B/${1#/}"
  fi
}

echo "== backing up affected files =="
for f in \
  /usr/sbin/phoc /usr/bin/phoc \
  /usr/lib/nuxel/nuxel-session.sh \
  /usr/lib/nuxel/nuxel-pwa-host \
  /usr/local/bin/nuxel-keyboard-apply.sh \
  /usr/libexec/nuxel/nuxel-keyboard-apply \
  /etc/nuxel/keyboard/keyboard.json \
  /usr/share/nuxel/pwa/nuxel-apps/settings/index.html \
  /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js; do
  backup "$f"
done

echo "== building nuxel-pwa-host =="
cd "$STAGE"
gcc -O2 -Wall -Wextra -Wno-unused-parameter \
  -o nuxel-pwa-host "$STAGE/nuxel-pwa-host.c" \
  $(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil
readelf -h nuxel-pwa-host | grep -q 'AArch64'
sha256sum nuxel-pwa-host

echo "== installing keyboard applier, document and session =="
install -m 0755 "$STAGE/nuxel-keyboard-apply.sh" /usr/local/bin/nuxel-keyboard-apply.sh
install -d /usr/libexec/nuxel
install -m 0755 "$STAGE/nuxel-keyboard-apply.sh" /usr/libexec/nuxel/nuxel-keyboard-apply
install -d /etc/nuxel/keyboard
install -m 0644 "$STAGE/keyboard.json" /etc/nuxel/keyboard/keyboard.json
install -m 0755 "$STAGE/nuxel-session.sh" /usr/lib/nuxel/nuxel-session.sh
install -m 0755 "$STAGE/nuxel-pwa-host" /usr/lib/nuxel/nuxel-pwa-host

echo "== installing Settings UI =="
install -d /usr/share/nuxel/pwa/nuxel-apps/settings
install -m 0644 "$STAGE/index.html" /usr/share/nuxel/pwa/nuxel-apps/settings/index.html
install -m 0644 "$STAGE/settings-model.js" /usr/share/nuxel/pwa/nuxel-apps/settings/settings-model.js
install -m 0644 "$STAGE/keyboard-settings.js" /usr/share/nuxel/pwa/nuxel-apps/settings/keyboard-settings.js

echo "== building and installing phoc + shim =="
install -m 0755 "$STAGE/a76-build-phoc-text-input-v1.sh" /usr/lib/nuxel/a76-build-phoc-text-input-v1.sh
install -m 0644 "$STAGE/phoc-text-input-v1.patch" /usr/lib/nuxel/phoc-text-input-v1.patch
/usr/lib/nuxel/a76-build-phoc-text-input-v1.sh

echo "== ensuring the keyboard apply path unit is active =="
systemctl daemon-reload
systemctl enable --now nuxel-keyboard-apply.path 2>/dev/null || true
systemctl start nuxel-keyboard-apply.service 2>/dev/null || \
  /usr/local/bin/nuxel-keyboard-apply.sh apply

echo "== enabling the v1 shim for Caprine =="
/usr/local/bin/nuxel-keyboard-apply.sh set keyboard.text_input_v1 true

echo "== live checks =="
sleep 2
printf 'phoc shim string: '; strings /usr/sbin/phoc | grep -m1 'nuxel-text-input-v1.enabled' || true
printf 'marker: '; cat /run/nuxel-text-input-v1.enabled 2>/dev/null || echo '(missing)'
grep -E '^(text_input|keyboard\.text_input_v1)=' /run/nuxel-keyboard.state 2>/dev/null || true
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 wayland-info 2>/dev/null | grep -E 'zwp_text_input_manager_v[13]' || true
systemctl is-active nuxel-wayland
echo "backup: $B"
REMOTE

echo "deployed to $HOST"
