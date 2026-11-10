#!/usr/bin/env bash
# PWNAGE-94000 reproducible build + safe deploy to the connected Nuxel S10+.
# Userspace only: no boot, recovery, kernel, modem or firmware writes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

tar czf "$TMP/src.tar.gz" -C "$ROOT" \
  pwa/nuxel-home/index.html pwa/nuxel-home/sw.js pwa/nuxel-home/manifest.json \
  pwa/nuxel-home/css/status-bar.css pwa/nuxel-home/css/style.css \
  pwa/nuxel-home/js/app.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/js/status-bar.js \
  pwa/nuxel-home/js/qs.js pwa/nuxel-home/js/immersive.js pwa/nuxel-home/js/topbar-machine.js \
  pwa/nuxel-home/js/bridge.js pwa/nuxel-home/js/gestures.js pwa/nuxel-home/js/navigation.js \
  pwa/nuxel-apps/doom/index.html pwa/nuxel-apps/doom/js/doom.js \
  services/nuxel-bridge/src/api.py \
  tools/s10plus/a45/nuxel-session.sh tools/s10plus/a45/nuxel-pwa-host.c \
  tools/s10plus/a45/nuxel-statusbar.c tools/s10plus/a45/nuxel-navdock.c \
  tools/s10plus/a45/navdock-art.h tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml \
  tools/s10plus/a45/xdg-shell.xml \
  tools/s10plus/a59/nuxel-foreign-toplevel.c \
  tools/s10plus/a33/doom-engines/nuxel-doom-engine tools/s10plus/a33/nuxel-crispy-doom \
  configs/nuxel/gtk/gtk-3.0-settings.ini configs/nuxel/gtk/gtk-4.0-settings.ini \
  configs/nuxel/dconf/profile-user configs/nuxel/dconf/db/site.d/00-nuxel-dark \
  configs/nuxel/flatpak/global-override

"${SSH[@]}" 'rm -rf /root/p94 /tmp/p94stage; mkdir -p /root/p94/out /tmp/p94stage'
"${SCP[@]}" "$TMP/src.tar.gz" "$HOST:/tmp/p94src.tar.gz" >/dev/null

"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd /tmp/p94stage
tar xzf /tmp/p94src.tar.gz
mkdir -p /root/p94/out /root/p94/gen
ST=/tmp/p94stage
wayland-scanner client-header "$ST/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml" /root/p94/gen/wlr-layer-shell-unstable-v1-client-protocol.h
wayland-scanner private-code "$ST/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml" /root/p94/gen/wlr-layer-shell-unstable-v1-protocol.c
wayland-scanner client-header "$ST/tools/s10plus/a45/xdg-shell.xml" /root/p94/gen/xdg-shell-client-protocol.h
wayland-scanner private-code "$ST/tools/s10plus/a45/xdg-shell.xml" /root/p94/gen/xdg-shell-protocol.c
echo "== build native (aarch64 on device) =="
gcc -O2 -Wall -Wextra -o /root/p94/out/nuxel-foreign-toplevel \
  "$ST/tools/s10plus/a59/nuxel-foreign-toplevel.c" -ldl
gcc -O2 -Wall -Wextra -Wno-unused-parameter -I/root/p94/gen -I"$ST/tools/s10plus/a45" \
  -o /root/p94/out/nuxel-navdock "$ST/tools/s10plus/a45/nuxel-navdock.c" \
  /root/p94/gen/wlr-layer-shell-unstable-v1-protocol.c /root/p94/gen/xdg-shell-protocol.c -lwayland-client
gcc -O2 -Wall -Wextra -Wno-unused-parameter -I/root/p94/gen \
  -o /root/p94/out/nuxel-statusbar "$ST/tools/s10plus/a45/nuxel-statusbar.c" \
  /root/p94/gen/wlr-layer-shell-unstable-v1-protocol.c /root/p94/gen/xdg-shell-protocol.c \
  $(pkg-config --cflags --libs pangocairo cairo wayland-client)
gcc -O2 -Wall -Wextra -Wno-unused-parameter -I/root/p94/gen \
  -o /root/p94/out/nuxel-pwa-host "$ST/tools/s10plus/a45/nuxel-pwa-host.c" \
  $(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil -lz
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 /root/p94/out/nuxel-foreign-toplevel list >/dev/null

TS=$(date +%Y%m%dT%H%M%S)
MAN=/root/p94/installed-$TS.list
backup() {
  dest="$1"
  if [ -e "$dest" ]; then
    cp -a "$dest" "$dest.nuxel-rollback-p94-$TS"
    printf 'present %s\n' "$dest" >> "$MAN"
  else
    printf 'absent %s\n' "$dest" >> "$MAN"
  fi
}
install_file() {
  src="$1"; dest="$2"; mode="$3"
  [ -f "$src" ] || { echo "missing source $src" >&2; exit 1; }
  mkdir -p "$(dirname "$dest")"
  backup "$dest"
  install -m "$mode" "$src" "$dest"
}
install_optional() {
  src="$1"; dest="$2"; mode="$3"
  [ -f "$src" ] || return 0
  install_file "$src" "$dest" "$mode"
}

PWAFILES="index.html sw.js manifest.json css/status-bar.css css/style.css \
 js/app.js js/apps.js js/status-bar.js js/qs.js js/immersive.js js/topbar-machine.js \
 js/bridge.js js/gestures.js js/navigation.js"
for base in /usr/share/nuxel/pwa /usr/share/nuxel; do
  [ -d "$base/nuxel-home" ] || continue
  for f in $PWAFILES; do
    install_file "$ST/pwa/nuxel-home/$f" "$base/nuxel-home/$f" 0644
  done
done
for base in /usr/share/nuxel/pwa/nuxel-apps/doom /usr/share/nuxel/nuxel-apps/doom; do
  [ -d "$base" ] || continue
  install_file "$ST/pwa/nuxel-apps/doom/index.html" "$base/index.html" 0644
  install_file "$ST/pwa/nuxel-apps/doom/js/doom.js" "$base/js/doom.js" 0644
done
install_file "$ST/services/nuxel-bridge/src/api.py" /usr/lib/nuxel/nuxel-bridge/api.py 0644
install_file "$ST/tools/s10plus/a45/nuxel-session.sh" /usr/lib/nuxel/nuxel-session.sh 0755
install_file /root/p94/out/nuxel-foreign-toplevel /usr/lib/nuxel/nuxel-foreign-toplevel 0755
install_file /root/p94/out/nuxel-navdock /usr/lib/nuxel/nuxel-navdock 0755
install_file /root/p94/out/nuxel-statusbar /usr/lib/nuxel/nuxel-statusbar 0755
install_file /root/p94/out/nuxel-pwa-host /usr/lib/nuxel/nuxel-pwa-host 0755
install_file "$ST/tools/s10plus/a33/doom-engines/nuxel-doom-engine" /usr/lib/nuxel/nuxel-doom-engine 0755
install_file "$ST/tools/s10plus/a33/nuxel-crispy-doom" /usr/lib/nuxel/nuxel-crispy-doom 0755
# Canonical dark-theme defaults (system-wide, user db still wins).
install_file "$ST/configs/nuxel/gtk/gtk-3.0-settings.ini" /etc/gtk-3.0/settings.ini 0644
install_file "$ST/configs/nuxel/gtk/gtk-4.0-settings.ini" /etc/gtk-4.0/settings.ini 0644
install_file "$ST/configs/nuxel/dconf/profile-user" /etc/dconf/profile/user 0644
install_file "$ST/configs/nuxel/dconf/db/site.d/00-nuxel-dark" /etc/dconf/db/site.d/00-nuxel-dark 0644
mkdir -p /var/lib/flatpak/overrides
backup /etc/dconf/db/site
install_file "$ST/configs/nuxel/flatpak/global-override" /var/lib/flatpak/overrides/global 0644
dconf update 2>/dev/null || true

python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/api.py
sh -n /usr/lib/nuxel/nuxel-session.sh
sh -n /usr/lib/nuxel/nuxel-doom-engine
sh -n /usr/lib/nuxel/nuxel-crispy-doom
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 /usr/lib/nuxel/nuxel-foreign-toplevel list >/dev/null

# Drop the launcher's WebKit page/SW caches so the new state machine is loaded
# deterministically after the session restart.  localStorage is preserved.
for d in /root/.local/share/nuxel-pwa-host/serviceworkers /root/.cache/nuxel-pwa-host/WebKitCache /root/.cache/nuxel-pwa-host/CacheStorage; do
  [ -e "$d" ] && rm -rf "$d"
done

systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service
sleep 4
systemctl restart nuxel-wl-fb.service || true
sleep 2
# Ensure the standard document portal is live after the session restart.
if [ -S /run/user/1000/bus ] && ! pgrep -u nuxel -f '^/usr/libexec/xdg-document-portal$' >/dev/null 2>&1; then
  nohup runuser -u nuxel -- env XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus \
    /usr/libexec/xdg-document-portal </dev/null >/run/nuxel-document-portal.log 2>&1 &
  i=0; while [ "$i" -lt 50 ]; do grep -q ' /run/user/1000/doc ' /proc/mounts && break; i=$((i+1)); sleep 0.1; done
fi
echo "MANIFEST=$MAN"
echo "DEPLOY_COMPLETE TS=$TS"
REMOTE
