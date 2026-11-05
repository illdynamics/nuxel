#!/usr/bin/env bash
# PWNAGE-80000 userspace deployment.  No kernel, partition, bootloader or
# networking change is performed.  Target host is discovered by the operator;
# this script never guesses one.
#
#   SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
#     tools/pwnage80000/deploy-pwnage80000.sh root@<DISCOVERED_NUXEL_HOST> --restart
#
# The key path can be overridden with SSH_KEY.  Host-key verification is kept
# on; there is deliberately no StrictHostKeyChecking=no escape hatch.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HOST="${1:?usage: $0 root@HOST [--restart]}"
shift || true
RESTART=0
for a in "$@"; do
  case "$a" in
    --restart) RESTART=1 ;;
    *) echo "unknown argument: $a" >&2; exit 2 ;;
  esac
done
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
[ -r "$KEY" ] || { echo "SSH key not readable: $KEY" >&2; exit 2; }
SSH=(ssh -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes "$HOST")
SCP=(scp -i "$KEY" -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes)
STAGE=/var/tmp/pwnage80000-stage
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/var/backups/nuxel/p80000-$STAMP"

echo "[p80000] verifying root on $HOST"
"${SSH[@]}" 'test "$(id -u)" = 0' || { echo "remote shell is not root" >&2; exit 2; }

echo "[p80000] staging source"
"${SSH[@]}" "rm -rf '$STAGE' && mkdir -p '$STAGE' '$BACKUP'"
tar -C "$ROOT" -cf - \
  pwa/nuxel-home pwa/nuxel-common pwa/nuxel-apps \
  configs/nuxel/policy/zoom.json \
  configs/nuxel/buttons/reboot-gate.json \
  configs/nuxel/power/power-menu.json \
  configs/nuxel/input/button-fsm.json \
  services/nuxel-s10/systemd/system.conf.d/50-nuxel-bounded-stop.conf \
  services/nuxel-session/systemd/nuxel-boot-sound.service.d/99-p80000-fast-stop.conf \
  tools/s10plus/a45/nuxel-pwa-host.c \
  tools/s10plus/a45/nuxel-osd.c \
  tools/s10plus/a45/nuxel-button-manager.c \
  tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml \
  tools/s10plus/a45/xdg-shell.xml \
  tools/s10plus/a34/nuxel-button-fsm.h \
  | "${SSH[@]}" "tar -C '$STAGE' -xf -"

echo "[p80000] backing up deployed userspace"
"${SSH[@]}" "set -e
for f in /usr/lib/nuxel/nuxel-pwa-host /usr/lib/nuxel/nuxel-osd /usr/lib/nuxel/nuxel-button-manager \
         /etc/nuxel/policy/zoom.json /etc/nuxel/buttons/reboot-gate.json \
         /etc/nuxel/power/power-menu.json /etc/nuxel/input/button-fsm.json; do
  [ -e \"\$f\" ] || continue
  install -D -m 0644 \"\$f\" '$BACKUP/files'\${f}
done
if [ -d /usr/share/nuxel/pwa ]; then
  tar -C /usr/share/nuxel -czf '$BACKUP/pwa.tgz' pwa
fi
[ -d /usr/share/nuxel/runtime ] && cp -a /usr/share/nuxel/runtime '$BACKUP/runtime' || true
find '$BACKUP' -type f -printf '%p %s bytes\n' | sort > '$BACKUP/MANIFEST.txt'"

echo "[p80000] building on target (native aarch64)"
"${SSH[@]}" "set -e
cd '$STAGE'
mkdir -p gen
wayland-scanner client-header tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-client-protocol.h
wayland-scanner private-code tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-protocol.c
wayland-scanner client-header tools/s10plus/a45/xdg-shell.xml gen/xdg-shell-client-protocol.h
wayland-scanner private-code tools/s10plus/a45/xdg-shell.xml gen/xdg-shell-protocol.c
CF='-O2 -Wall -Wextra -Wno-unused-parameter -I gen'
gcc \$CF -o nuxel-osd tools/s10plus/a45/nuxel-osd.c gen/wlr-layer-shell-unstable-v1-protocol.c gen/xdg-shell-protocol.c \$(pkg-config --cflags --libs wayland-client cairo pangocairo)
gcc \$CF -o nuxel-pwa-host tools/s10plus/a45/nuxel-pwa-host.c \$(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil
gcc -std=gnu11 -O2 -Wall -Wextra -I tools/s10plus/a34 -o nuxel-button-manager tools/s10plus/a45/nuxel-button-manager.c \$(pkg-config --cflags --libs alsa)
for b in nuxel-osd nuxel-pwa-host nuxel-button-manager; do readelf -h \$b | grep -q AArch64; done
sha256sum nuxel-osd nuxel-pwa-host nuxel-button-manager | tee '$STAGE/BUILT-SHA256SUMS'"

echo "[p80000] installing atomically"
"${SSH[@]}" "set -e
cd '$STAGE'
install_atomic() { src=\$1; dst=\$2; mode=\$3; tmp=\${dst}.p80000.new; install -m \"\$mode\" \"\$src\" \"\$tmp\"; mv -f \"\$tmp\" \"\$dst\"; }
install -d -m 0755 /usr/lib/nuxel /usr/share/nuxel/pwa /usr/share/nuxel/runtime /etc/nuxel/policy
install_atomic nuxel-osd /usr/lib/nuxel/nuxel-osd 0755
install_atomic nuxel-pwa-host /usr/lib/nuxel/nuxel-pwa-host 0755
install_atomic nuxel-button-manager /usr/lib/nuxel/nuxel-button-manager 0755
# PWA payload: overwrite the active trees, then remove the retired standalone
# Chocolate Doom launcher (the internal engine runtime remains available).
cp -a pwa/nuxel-home/. /usr/share/nuxel/pwa/nuxel-home/
cp -a pwa/nuxel-common/. /usr/share/nuxel/pwa/nuxel-common/
cp -a pwa/nuxel-apps/. /usr/share/nuxel/pwa/nuxel-apps/
rm -rf /usr/share/nuxel/pwa/nuxel-apps/doom-chocolate /usr/share/nuxel/nuxel-apps/doom-chocolate
install -m 0644 configs/nuxel/policy/zoom.json /etc/nuxel/policy/zoom.json
install -m 0644 configs/nuxel/policy/zoom.json /usr/share/nuxel/runtime/zoom-policy.json
install -m 0644 configs/nuxel/buttons/reboot-gate.json /etc/nuxel/buttons/reboot-gate.json
install -m 0644 configs/nuxel/power/power-menu.json /etc/nuxel/power/power-menu.json
install -m 0644 configs/nuxel/input/button-fsm.json /etc/nuxel/input/button-fsm.json
install -d -m 0755 /etc/systemd/system.conf.d
install -m 0644 services/nuxel-s10/systemd/system.conf.d/50-nuxel-bounded-stop.conf /etc/systemd/system.conf.d/50-nuxel-bounded-stop.conf
install -d -m 0755 /etc/systemd/system/nuxel-boot-sound.service.d
install -m 0644 services/nuxel-session/systemd/nuxel-boot-sound.service.d/99-p80000-fast-stop.conf /etc/systemd/system/nuxel-boot-sound.service.d/99-p80000-fast-stop.conf
systemctl daemon-reload
sha256sum /usr/lib/nuxel/nuxel-osd /usr/lib/nuxel/nuxel-pwa-host /usr/lib/nuxel/nuxel-button-manager \
          /usr/share/nuxel/pwa/nuxel-home/js/app.js /usr/share/nuxel/pwa/nuxel-common/zoom-policy.js \
          | tee '$STAGE/INSTALLED-SHA256SUMS'"

if [ "$RESTART" = 1 ]; then
  echo "[p80000] restarting userspace (Wayland + buttons + OSD)"
  "${SSH[@]}" 'systemctl reset-failed nuxel-button-manager.service 2>/dev/null || true
systemctl restart nuxel-button-manager.service
systemctl restart nuxel-wayland.service
for i in $(seq 1 30); do
  systemctl is-active --quiet nuxel-wayland.service && \
  systemctl is-active --quiet nuxel-wl-fb.service && \
  systemctl is-active --quiet nuxel-button-manager.service && break
  sleep 1
done
systemctl --no-pager --failed | head -20
systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-button-manager nuxel-web nuxel-http-bridge
cat /run/nuxel-wl-fb.state 2>/dev/null || true'
fi

echo "[p80000] installed; backups: $BACKUP"
