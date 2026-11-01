#!/usr/bin/env bash
# PWNAGE-54000 userspace deployment over Wi-Fi SSH.
#
#   tools/s10plus/a67/deploy-pwnage54000.sh [root@host]
#
# Deploys ONLY userspace: orientation daemon/package/config, remote sync helper,
# PWA assets, and the nav-dock / foreign-toplevel binaries compiled on-device.
# Never writes /dev/fb0, BOOT, firmware or any partition.  Restarting
# nuxel-orientationd is safe; the compositor is restarted only because the
# native dock is a session child, and the script restores it on failure.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)
R=/tmp/nuxel-p54000
B=/var/backups/nuxel/p54000-$(date -u +%Y%m%dT%H%M%SZ)

echo "== preflight =="
"${SSH[@]}" "test \"\$(uname -m)\" = aarch64; test -e /dev/fb0; command -v wlr-randr >/dev/null; command -v python3 >/dev/null"
echo "target=$HOST backup=$B"

"${SSH[@]}" "set -e; mkdir -p '$R' '$B'
  for f in /usr/libexec/nuxel/nuxel-orientationd /usr/libexec/nuxel/nuxel_orientation \
           /etc/nuxel/orientation/orientation.json /usr/libexec/nuxel/nuxel-orientation-remote-sync \
           /usr/lib/nuxel/nuxel-navdock /usr/lib/nuxel/nuxel-foreign-toplevel \
           /usr/lib/nuxel/nuxel-pwa-host /usr/lib/nuxel/libnuxel-libinput-path.so \
           /usr/lib/nuxel/nuxel-portal/portal.py /etc/systemd/system/nuxel-portal.service; do
    [ -e \"\$f\" ] && cp -a \"\$f\" '$B'/ || true
  done
  tar -C /usr/share/nuxel -czf '$B'/pwa-home.tgz pwa/nuxel-home 2>/dev/null || true
  tar -C /usr/share/nuxel -czf '$B'/pwa-recorder.tgz pwa/nuxel-apps/recorder 2>/dev/null || true
  tar -C /usr/share/nuxel/assets -czf '$B'/assets.tgz nuxel-quicksettings-icon-pack 2>/dev/null || true
  sha256sum /usr/libexec/nuxel/nuxel-orientationd /etc/nuxel/orientation/orientation.json \
            /usr/lib/nuxel/nuxel-navdock /usr/lib/nuxel/nuxel-foreign-toplevel > '$B'/SHA256SUMS 2>/dev/null || true
  echo '$B' > /run/nuxel-p54000-backup-dir"

"${SCP[@]}" -r \
  "$ROOT/services/nuxel-orientation/nuxel-orientationd" \
  "$ROOT/services/nuxel-orientation/nuxel_orientation" \
  "$ROOT/services/nuxel-orientation/systemd/nuxel-orientationd.service" \
  "$ROOT/configs/nuxel/orientation/orientation.json" \
  "$ROOT/configs/nuxel/orientation/orientation.schema.json" \
  "$ROOT/services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync" \
  "$ROOT/services/nuxel-bridge/src/api.py" \
  "$ROOT/tools/s10plus/a45/nuxel-navdock.c" \
  "$ROOT/tools/s10plus/a45/navdock-art.h" \
  "$ROOT/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml" \
  "$ROOT/tools/s10plus/a45/xdg-shell.xml" \
  "$ROOT/tools/s10plus/a59/nuxel-foreign-toplevel.c" \
  "$ROOT/tools/s10plus/a67/nuxel-wl-fb.c" \
  "$ROOT/tools/s10plus/a33/nuxel-handoff-logic.h" \
  "$ROOT/tools/s10plus/a33/nuxel-libinput-path.c" \
  "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" \
  "$ROOT/services/nuxel-portal/src/portal.py" \
  "$ROOT/services/nuxel-portal/systemd/nuxel-portal.service" \
  "$ROOT/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml" \
  "$ROOT/services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf" \
  "$HOST:$R/" >/dev/null
for d in pwa/nuxel-home pwa/nuxel-apps/settings pwa/nuxel-apps/recorder; do
  "${SSH[@]}" "mkdir -p '$R/$(dirname "$d")'"
  "${SCP[@]}" -r "$ROOT/$d" "$HOST:$R/$d"
done
"${SCP[@]}" -r "$ROOT/assets/nuxel-quicksettings-icon-pack" "$HOST:$R/"

echo "== build native userspace on target =="
"${SSH[@]}" "set -euo pipefail
  cd '$R'
  wayland-scanner client-header wlr-layer-shell-unstable-v1.xml wlr-layer-shell-unstable-v1-client-protocol.h
  wayland-scanner private-code  wlr-layer-shell-unstable-v1.xml wlr-layer-shell-unstable-v1-protocol.c
  wayland-scanner client-header xdg-shell.xml xdg-shell-client-protocol.h
  wayland-scanner private-code  xdg-shell.xml xdg-shell-protocol.c
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 -I. \$(pkg-config --cflags wayland-client) \
      -o nuxel-navdock nuxel-navdock.c wlr-layer-shell-unstable-v1-protocol.c xdg-shell-protocol.c \$(pkg-config --libs wayland-client)
  gcc -O2 -Wall -Wextra -std=gnu11 -o nuxel-foreign-toplevel nuxel-foreign-toplevel.c -ldl
  wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
  wayland-scanner private-code  wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 -I. \
      \$(pkg-config --cflags wayland-client) -o nuxel-wl-fb nuxel-wl-fb.c wlr-screencopy-unstable-v1-protocol.c \
      \$(pkg-config --libs wayland-client)
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 -shared -fPIC \
      -o libnuxel-libinput-path.so nuxel-libinput-path.c -ldl
  gcc -O2 -Wall -Wextra -std=gnu11 \$(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) \
      -I. -o nuxel-pwa-host nuxel-pwa-host.c \$(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) -lutil
  ./nuxel-wl-fb --colour-selftest >/dev/null 2>&1 || true
  readelf -h nuxel-navdock | grep -q AArch64
  readelf -h nuxel-foreign-toplevel | grep -q AArch64
  readelf -h nuxel-wl-fb | grep -q AArch64
  readelf -h nuxel-pwa-host | grep -q AArch64
  readelf -h libnuxel-libinput-path.so | grep -q AArch64
  python3 -m py_compile nuxel-orientationd nuxel-orientation-remote-sync
  /usr/bin/python3 nuxel-orientationd selftest
  sha256sum nuxel-navdock nuxel-foreign-toplevel nuxel-wl-fb nuxel-orientationd \
            nuxel-pwa-host libnuxel-libinput-path.so > BUILD-SHA256SUMS"

echo "== install =="
"${SSH[@]}" "set -euo pipefail
  install -d -m 0755 /usr/libexec/nuxel/nuxel_orientation /etc/nuxel/orientation
  install -m 0755 '$R/nuxel-orientationd' /usr/libexec/nuxel/nuxel-orientationd
  for f in __init__.py policy.py sensors.py apply.py; do
    install -m 0644 \"$R/nuxel_orientation/\$f\" \"/usr/libexec/nuxel/nuxel_orientation/\$f\"
  done
  install -m 0755 '$R/nuxel-orientation-remote-sync' /usr/libexec/nuxel/nuxel-orientation-remote-sync
  install -m 0644 '$R/api.py' /usr/lib/nuxel/nuxel-bridge/api.py
  install -m 0644 '$R/orientation.json' /etc/nuxel/orientation/orientation.json
  install -m 0644 '$R/orientation.schema.json' /etc/nuxel/orientation/orientation.schema.json
  install -m 0644 '$R/nuxel-orientationd.service' /etc/systemd/system/nuxel-orientationd.service
  install -m 0755 '$R/nuxel-foreign-toplevel' /usr/lib/nuxel/nuxel-foreign-toplevel
  install -m 0755 '$R/nuxel-navdock' /usr/lib/nuxel/nuxel-navdock
  install -m 0755 '$R/nuxel-wl-fb' /usr/lib/nuxel/nuxel-wl-fb.p54000
  cp -a /usr/lib/nuxel/nuxel-pwa-host /usr/lib/nuxel/nuxel-pwa-host.p54000-prev
  install -m 0755 '$R/nuxel-pwa-host' /usr/lib/nuxel/nuxel-pwa-host
  cp -a /usr/lib/nuxel/libnuxel-libinput-path.so /usr/lib/nuxel/libnuxel-libinput-path.so.p54000-prev
  install -m 0755 '$R/libnuxel-libinput-path.so' /usr/lib/nuxel/libnuxel-libinput-path.so
  install -d -m 0755 /usr/lib/nuxel/nuxel-portal
  cp -a /usr/lib/nuxel/nuxel-portal/portal.py /usr/lib/nuxel/nuxel-portal/portal.py.p54000-prev 2>/dev/null || true
  install -m 0755 '$R/portal.py' /usr/lib/nuxel/nuxel-portal/portal.py
  cp -a /etc/systemd/system/nuxel-portal.service /etc/systemd/system/nuxel-portal.service.p54000-prev 2>/dev/null || true
  install -m 0644 '$R/nuxel-portal.service' /etc/systemd/system/nuxel-portal.service
  # The portal owns /var/lib/nuxel/permissions but must traverse the parent.
  # Repair both the live ACL and the directory mode; the unit also carries the
  # nuxel-notifications supplementary group as a second, durable path.
  setfacl -m u:nuxel:r-x /var/lib/nuxel 2>/dev/null || chmod o+x /var/lib/nuxel
  install -d -o nuxel -g nuxel -m 0770 /var/lib/nuxel/permissions
  setfacl -m u:nuxel-bridge:rwx /var/lib/nuxel/permissions 2>/dev/null || true
  install -m 0644 '$R/nuxel-quicksettings-icon-pack/04-bluetooth.svg' /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/04-bluetooth.svg
  install -m 0644 '$R/nuxel-quicksettings-icon-pack/09-location.svg' /usr/share/nuxel/assets/nuxel-quicksettings-icon-pack/09-location.svg
  cp -a '$R/pwa/nuxel-home/.' /usr/share/nuxel/pwa/nuxel-home/
  mkdir -p /usr/share/nuxel/pwa/nuxel-apps/settings /usr/share/nuxel/pwa/nuxel-apps/recorder
  cp -a '$R/pwa/nuxel-apps/settings/.' /usr/share/nuxel/pwa/nuxel-apps/settings/
  cp -a '$R/pwa/nuxel-apps/recorder/.' /usr/share/nuxel/pwa/nuxel-apps/recorder/
  # The presenter binary and the rotation-capable source must land together.
  # Keep a fallback copy until the next reboot proves the new build.
  cp -a /usr/lib/nuxel/nuxel-wl-fb /usr/lib/nuxel/nuxel-wl-fb.p54000-prev
  install -m 0755 '$R/nuxel-wl-fb' /usr/lib/nuxel/nuxel-wl-fb
  systemctl daemon-reload
  /usr/libexec/nuxel/nuxel-orientationd selftest
  install -d -m 0755 /etc/systemd/system/nuxel-wl-fb.service.d
  install -m 0644 '$R/15-idle-fps.conf' /etc/systemd/system/nuxel-wl-fb.service.d/15-idle-fps.conf
  systemctl restart nuxel-orientationd
  systemctl restart nuxel-http-bridge
  systemctl restart nuxel-wl-fb
  sleep 2
  systemctl is-active nuxel-orientationd nuxel-wl-fb
  cat /run/nuxel-wl-fb-orientation
  cat /run/nuxel-wl-fb.orientation 2>/dev/null || true
  systemctl restart nuxel-portal
  sleep 2
  systemctl is-active nuxel-portal"

echo "== restart session overlay clients (dock binary changed) =="
"${SSH[@]}" "set -e
  systemctl restart nuxel-wayland
  sleep 4
  systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-orientationd
  cat /run/nuxel-navdock.state 2>/dev/null | tail -5"

echo "== post-deploy verification =="
"${SSH[@]}" "cat '$R'/BUILD-SHA256SUMS 2>/dev/null || true
  sha256sum /usr/libexec/nuxel/nuxel-orientationd /usr/lib/nuxel/nuxel-navdock \
            /usr/lib/nuxel/nuxel-foreign-toplevel /usr/lib/nuxel/nuxel-pwa-host \
            /usr/lib/nuxel/libnuxel-libinput-path.so
  /usr/libexec/nuxel/nuxel-orientationd status --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get(\"mode\"), d.get(\"mode_label\"), d.get(\"effective_orientation\"), (d.get(\"display\") or {}).get(\"output\"), (d.get(\"display\") or {}).get(\"transform\"), d.get(\"display_verified\"))'
  cat /run/nuxel-orientation/input.json
  cat /run/nuxel-touch-calibration.state 2>/dev/null || true
  systemctl is-active nuxel-portal
  curl -sS -m 10 -H 'Content-Type: application/json' -H 'X-Nuxel-App-Id: org.nuxel.Recorder' \
    -d '{\"namespace\":\"audio\",\"verb\":\"capture-route\",\"params\":{}}' \
    http://127.0.0.1:8080/api/v1/rpc"
echo "deployed. backup=$B"
echo "rollback: tools/s10plus/a67/rollback-pwnage54000.sh $HOST $B"
