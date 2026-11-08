#!/usr/bin/env bash
# Reproducible PWNAGE-90000 build + stage for the connected Nuxel S10+.
# It builds the four native clients natively on the phone, backs up every
# replaced file as <name>.nuxel-rollback-p90-<UTC timestamp>, installs the PWA
# and Python owners, then restarts the bridge and the single wayland session.
#
#   NUXEL_HOST=root@192.168.178.167 NUXEL_SSH_KEY=~/.ssh/wicked_wqn_id_rsa \
#       ./tools/pwnage90000/deploy-pwnage90000.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${NUXEL_HOST:-root@192.168.178.167}"
KEY="${NUXEL_SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
tar czf "$TMP/pwa.tar.gz" -C "$ROOT" \
  pwa/nuxel-home/js/app.js pwa/nuxel-home/js/qs.js pwa/nuxel-home/js/immersive.js \
  pwa/nuxel-home/js/status-bar.js pwa/nuxel-home/js/apps.js pwa/nuxel-home/js/launcher.js \
  pwa/nuxel-home/sw.js pwa/nuxel-home/manifest.json pwa/nuxel-home/css/launcher.css \
  pwa/nuxel-common/back.js pwa/nuxel-apps/settings/power-menu.js \
  pwa/nuxel-apps/settings/power-menu.css
tar czf "$TMP/py.tar.gz" -C "$ROOT" \
  services/nuxel-bridge/src/api.py services/nuxel-preload-cinema/nuxel-preload-cinema

"${SSH[@]}" 'rm -rf /root/p90/src /root/p90/gen /root/p90/out /tmp/p90stage; mkdir -p /root/p90/src /root/p90/gen /root/p90/out /tmp/p90stage'
"${SCP[@]}" "$ROOT/tools/s10plus/a45/nuxel-navdock.c" \
  "$ROOT/tools/s10plus/a45/nuxel-statusbar.c" \
  "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" \
  "$ROOT/tools/s10plus/a45/navdock-art.h" \
  "$ROOT/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml" \
  "$ROOT/tools/s10plus/a45/xdg-shell.xml" \
  "$ROOT/tools/s10plus/a59/nuxel-foreign-toplevel.c" "$HOST:/root/p90/src/" >/dev/null
"${SCP[@]}" "$TMP/pwa.tar.gz" "$TMP/py.tar.gz" "$HOST:/tmp/" >/dev/null

"${SSH[@]}" 'bash -s' <<'REMOTE'
set -euo pipefail
cd /root/p90
wayland-scanner client-header src/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-client-protocol.h
wayland-scanner private-code  src/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-protocol.c
wayland-scanner client-header src/xdg-shell.xml gen/xdg-shell-client-protocol.h
wayland-scanner private-code  src/xdg-shell.xml gen/xdg-shell-protocol.c
CF="-O2 -Wall -Wextra -Wno-unused-parameter -Igen -Isrc"
gcc $CF -o out/nuxel-navdock src/nuxel-navdock.c gen/wlr-layer-shell-unstable-v1-protocol.c gen/xdg-shell-protocol.c $(pkg-config --cflags --libs wayland-client) -lm
gcc $CF -o out/nuxel-statusbar src/nuxel-statusbar.c gen/wlr-layer-shell-unstable-v1-protocol.c gen/xdg-shell-protocol.c $(pkg-config --cflags --libs wayland-client pangocairo cairo) -lm
gcc -O2 -Wall -Wextra -o out/nuxel-foreign-toplevel src/nuxel-foreign-toplevel.c -ldl
gcc $CF -o out/nuxel-pwa-host src/nuxel-pwa-host.c $(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil -lz
cd /tmp/p90stage; tar xzf /tmp/pwa.tar.gz; tar xzf /tmp/py.tar.gz
TS=$(date +%Y%m%dT%H%M%S)
backup() { if [ -e "$1" ]; then cp -a "$1" "$1.nuxel-rollback-p90-$TS"; fi; return 0; }
for base in /usr/share/nuxel/pwa /usr/share/nuxel; do
  for f in js/app.js js/qs.js js/immersive.js js/status-bar.js js/apps.js js/launcher.js sw.js manifest.json css/launcher.css; do
    dest="$base/nuxel-home/$f"; [ -d "$(dirname "$dest")" ] || continue
    backup "$dest"; install -m 0644 "/tmp/p90stage/pwa/nuxel-home/$f" "$dest"
  done
  if [ -d "$base/nuxel-common" ]; then
    backup "$base/nuxel-common/back.js"; install -m 0644 /tmp/p90stage/pwa/nuxel-common/back.js "$base/nuxel-common/back.js"
  fi
  for f in power-menu.js power-menu.css; do
    dest="$base/nuxel-apps/settings/$f"; [ -d "$(dirname "$dest")" ] || continue
    backup "$dest"; install -m 0644 "/tmp/p90stage/pwa/nuxel-apps/settings/$f" "$dest"
  done
done
backup /usr/lib/nuxel/nuxel-bridge/api.py; install -m 0644 /tmp/p90stage/services/nuxel-bridge/src/api.py /usr/lib/nuxel/nuxel-bridge/api.py
backup /usr/lib/nuxel/nuxel-preload-cinema; install -m 0755 /tmp/p90stage/services/nuxel-preload-cinema/nuxel-preload-cinema /usr/lib/nuxel/nuxel-preload-cinema
for b in nuxel-navdock nuxel-statusbar nuxel-foreign-toplevel nuxel-pwa-host; do
  backup "/usr/lib/nuxel/$b"; install -m 0755 "/root/p90/out/$b" "/usr/lib/nuxel/$b"
done
python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/api.py /usr/lib/nuxel/nuxel-preload-cinema
systemctl restart nuxel-bridge.service nuxel-http-bridge.service
systemctl restart nuxel-wayland.service
sleep 3
systemctl restart nuxel-wl-fb.service || true
echo "DEPLOY_COMPLETE TS=$TS"
REMOTE
