#!/bin/bash
# PWNAGE-62000 Wi-Fi SSH deployment.  Stages, backs up, builds on the target,
# installs atomically and runs health checks.  It never reboots automatically.
#
#   tools/pwnage62000/deploy-pwnage62000.sh [root@10.20.30.16]
#
# Key: $SSH_KEY (default ~/.ssh/wicked_wqn_id_rsa).  known_hosts is enforced.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="${1:-root@10.20.30.16}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
STAGE="/tmp/pwnage62000-$STAMP"
BACKUP="/var/backups/nuxel/p62000-$STAMP"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes -o ConnectTimeout=10 "$TARGET")
SCP=(scp -q -i "$KEY" -o BatchMode=yes -o StrictHostKeyChecking=yes)

echo "[p62000] target=$TARGET stamp=$STAMP"
"${SSH[@]}" "set -e; test \"\$(uname -m)\" = aarch64; grep -q '^ID=fedora' /etc/os-release; test -e /usr/lib/nuxel/nuxel-pwa-host; echo TARGET_OK"

"${SSH[@]}" "set -e; mkdir -p '$STAGE/src' '$STAGE/bin' '$STAGE/pwa' '$BACKUP'; echo '$BACKUP' > /run/nuxel-p62000-backup-dir"

echo "[p62000] backing up existing targets"
"${SSH[@]}" "set -e
backup_one() {
  src=\$1
  [ -e \"\$src\" ] || return 0
  rel=\${src#/}
  mkdir -p \"$BACKUP/\$(dirname \"\$rel\")\"
  cp -a \"\$src\" \"$BACKUP/\$rel\"
}
for f in \
  /usr/lib/nuxel/nuxel-navdock /usr/lib/nuxel/nuxel-statusbar \
  /usr/lib/nuxel/nuxel-foreign-toplevel /usr/lib/nuxel/nuxel-pwa-host \
  /usr/lib/nuxel/nuxel-button-manager /usr/lib/nuxel/nuxel-session.sh \
  /usr/lib/nuxel/nuxel-shell-chrome.sh /usr/lib/nuxel/nuxel-security-lock-rpc \
  /usr/lib/nuxel/nuxel-wayland-stop.sh /usr/lib/nuxel/nuxel-wl-fb-hold.sh \
  /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-bridge/system_indicators.py \
  /usr/lib/nuxel/stage36000/apply-pwnage36000.sh \
  /usr/lib/nuxel/stage36000/nuxel-preload-cinema/nuxel-preload-cinema \
  /usr/lib/nuxel/nuxel-audio-stop.sh \
  /etc/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf \
  /etc/nuxel/boot/preload-cinema.json \
  /etc/systemd/system/nuxel-wayland.service \
  /usr/share/nuxel/pwa/nuxel-home/manifest.json \
  /usr/share/nuxel/nuxel-home/manifest.json \
  /etc/systemd/system/nuxel-wayland.service.d/30-fast-stop.conf \
  /etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf \
  /etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf \
  /usr/share/nuxel/pwa/nuxel-home/index.html \
  /usr/share/nuxel/pwa/nuxel-home/sw.js \
  /usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js \
  /usr/share/nuxel/pwa/nuxel-home/js/gestures.js \
  /usr/share/nuxel/pwa/nuxel-home/js/navigation.js \
  /usr/share/nuxel/pwa/nuxel-home/js/launcher.js \
  /usr/share/nuxel/pwa/nuxel-home/js/apps.js \
  /usr/share/nuxel/pwa/nuxel-home/js/app.js \
  /usr/share/nuxel/pwa/nuxel-home/css/launcher.css \
  /usr/share/nuxel/pwa/nuxel-home/css/style.css \
  /usr/share/nuxel/pwa/nuxel-home/css/status-bar.css \
  /usr/share/nuxel/nuxel-home/index.html \
  /usr/share/nuxel/nuxel-home/sw.js \
  /usr/share/nuxel/nuxel-home/js/lockscreen-indicators.js \
  /usr/share/nuxel/nuxel-home/js/gestures.js \
  /usr/share/nuxel/nuxel-home/js/navigation.js \
  /usr/share/nuxel/nuxel-home/js/launcher.js \
  /usr/share/nuxel/nuxel-home/js/apps.js \
  /usr/share/nuxel/nuxel-home/js/app.js \
  /usr/share/nuxel/nuxel-home/css/launcher.css \
  /usr/share/nuxel/nuxel-home/css/style.css \
  /usr/share/nuxel/nuxel-home/css/status-bar.css; do backup_one \"\$f\"; done
find '$BACKUP' -type f ! -name 'SHA256SUMS*' -print0 | sort -z | xargs -0 sha256sum > '/tmp/p62000-backup-sums.$$'
mv -f '/tmp/p62000-backup-sums.$$' '$BACKUP/SHA256SUMS'
"

echo "[p62000] staging sources"
"${SCP[@]}" \
  "$ROOT/tools/s10plus/a45/nuxel-navdock.c" \
  "$ROOT/tools/s10plus/a45/nuxel-statusbar.c" \
  "$ROOT/tools/s10plus/a45/nuxel-pwa-host.c" \
  "$ROOT/tools/s10plus/a45/nuxel-button-manager.c" \
  "$ROOT/tools/s10plus/a45/navdock-art.h" \
  "$ROOT/tools/s10plus/a33/nuxel-button-fsm.h" \
  "$ROOT/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml" \
  "$ROOT/tools/s10plus/a45/xdg-shell.xml" \
  "$ROOT/tools/s10plus/a59/nuxel-foreign-toplevel.c" \
  "$TARGET:$STAGE/src/"
"${SCP[@]}" \
  "$ROOT/tools/s10plus/a45/nuxel-session.sh" \
  "$ROOT/tools/s10plus/a45/nuxel-shell-chrome.sh" \
  "$ROOT/tools/s10plus/a45/nuxel-security-lock-rpc" \
  "$ROOT/services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh" \
  "$ROOT/services/nuxel-s10/bin/nuxel-audio-stop.sh" \
  "$ROOT/services/nuxel-s10/bin/nuxel-wayland-stop.sh" \
  "$ROOT/services/nuxel-s10/bin/nuxel-wl-fb-hold.sh" \
  "$ROOT/services/nuxel-preload-cinema/nuxel-preload-cinema" \
  "$ROOT/tools/pwnage62000/rollback-pwnage62000.sh" \
  "$TARGET:$STAGE/bin/"
"${SCP[@]}" \
  "$ROOT/services/nuxel-bridge/src/system_indicators.py" \
  "$ROOT/configs/nuxel/boot/preload-cinema.json" \
  "$TARGET:$STAGE/"
# PWNAGE-72000: the Home manifest and the canonical wayland unit are part of
# the deployed 62000 surface.  Stage them explicitly so a run cannot leave the
# live Home manifest as the Clipper manifest or the unit stale.
"${SCP[@]}" \
  "$ROOT/pwa/nuxel-home/manifest.json" \
  "$ROOT/tools/s10plus/a31/nuxel-wayland.service" \
  "$TARGET:$STAGE/"
"${SCP[@]}" \
  "$ROOT/pwa/nuxel-home/index.html" \
  "$ROOT/pwa/nuxel-home/sw.js" \
  "$ROOT/pwa/nuxel-home/js/lockscreen-indicators.js" \
  "$ROOT/pwa/nuxel-home/js/gestures.js" \
  "$ROOT/pwa/nuxel-home/js/navigation.js" \
  "$ROOT/pwa/nuxel-home/js/launcher.js" \
  "$ROOT/pwa/nuxel-home/js/apps.js" \
  "$ROOT/pwa/nuxel-home/js/app.js" \
  "$ROOT/pwa/nuxel-home/css/launcher.css" \
  "$ROOT/pwa/nuxel-home/css/style.css" \
  "$ROOT/pwa/nuxel-home/css/status-bar.css" \
  "$TARGET:$STAGE/pwa/"
"${SCP[@]}" \
  "$ROOT/services/nuxel-s10/systemd/nuxel-wayland.service.d/30-fast-stop.conf" \
  "$ROOT/services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf" \
  "$ROOT/services/nuxel-s10/systemd/nuxel-wl-fb.service.d/25-reboot-hold.conf" \
  "$TARGET:$STAGE/"
"${SCP[@]}" "$ROOT/services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf" "$TARGET:$STAGE/10-audio-stop-bound.conf"

echo "[p62000] building AArch64 components on target"
"${SSH[@]}" "set -e
cd '$STAGE'
mkdir -p gen
wayland-scanner client-header src/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-client-protocol.h
wayland-scanner private-code src/wlr-layer-shell-unstable-v1.xml gen/wlr-layer-shell-unstable-v1-protocol.c
wayland-scanner client-header src/xdg-shell.xml gen/xdg-shell-client-protocol.h
wayland-scanner private-code src/xdg-shell.xml gen/xdg-shell-protocol.c
CF='-O2 -Wall -Wextra -Wno-unused-parameter -I gen -I src'
gcc \$CF -o bin/nuxel-navdock src/nuxel-navdock.c gen/wlr-layer-shell-unstable-v1-protocol.c gen/xdg-shell-protocol.c \$(pkg-config --cflags --libs wayland-client)
gcc \$CF -o bin/nuxel-statusbar src/nuxel-statusbar.c gen/wlr-layer-shell-unstable-v1-protocol.c gen/xdg-shell-protocol.c \$(pkg-config --cflags --libs wayland-client cairo pangocairo)
gcc \$CF -o bin/nuxel-foreign-toplevel src/nuxel-foreign-toplevel.c -ldl
gcc \$CF -o bin/nuxel-pwa-host src/nuxel-pwa-host.c \$(pkg-config --cflags --libs gtk+-3.0 webkit2gtk-4.1) -lutil
gcc \$CF -o bin/nuxel-button-manager src/nuxel-button-manager.c \$(pkg-config --cflags --libs alsa)
for b in nuxel-navdock nuxel-statusbar nuxel-foreign-toplevel nuxel-pwa-host nuxel-button-manager; do
  readelf -h \"bin/\$b\" | grep -q AArch64 || { echo \"NOT AARCH64: \$b\" >&2; exit 1; }
done
python3 -m py_compile bin/nuxel-preload-cinema bin/nuxel-security-lock-rpc
find bin -maxdepth 1 -type f -print0 | sort -z | xargs -0 sha256sum > bin/SHA256SUMS
"

echo "[p62000] installing atomically"
"${SSH[@]}" "set -e
install_atomic() { src=\$1; dst=\$2; mode=\$3; tmp=\${dst}.p62000.new; install -m \"\$mode\" \"\$src\" \"\$tmp\"; mv -f \"\$tmp\" \"\$dst\"; }
install -d -m 0755 /usr/lib/nuxel /usr/lib/nuxel/nuxel-bridge /etc/systemd/system/nuxel-wayland.service.d /etc/systemd/system/nuxel-wl-fb.service.d /etc/nuxel/boot
install_atomic '$STAGE/bin/nuxel-navdock' /usr/lib/nuxel/nuxel-navdock 0755
install_atomic '$STAGE/bin/nuxel-statusbar' /usr/lib/nuxel/nuxel-statusbar 0755
install_atomic '$STAGE/bin/nuxel-foreign-toplevel' /usr/lib/nuxel/nuxel-foreign-toplevel 0755
install_atomic '$STAGE/bin/nuxel-pwa-host' /usr/lib/nuxel/nuxel-pwa-host 0755
install_atomic '$STAGE/bin/nuxel-button-manager' /usr/lib/nuxel/nuxel-button-manager 0755
install_atomic '$STAGE/bin/nuxel-session.sh' /usr/lib/nuxel/nuxel-session.sh 0755
install_atomic '$STAGE/bin/nuxel-shell-chrome.sh' /usr/lib/nuxel/nuxel-shell-chrome.sh 0755
install_atomic '$STAGE/bin/nuxel-security-lock-rpc' /usr/lib/nuxel/nuxel-security-lock-rpc 0755
# The early-boot bootstrap must guard (not overwrite) the deployed controller;
# keep both copies identical so either policy path carries the same code.
install -d -m 0755 /usr/lib/nuxel/stage36000/nuxel-preload-cinema
install_atomic '$STAGE/bin/nuxel-apply-pwnage36000.sh' /usr/lib/nuxel/stage36000/apply-pwnage36000.sh 0755
install_atomic '$STAGE/bin/nuxel-preload-cinema' /usr/lib/nuxel/stage36000/nuxel-preload-cinema/nuxel-preload-cinema 0755
install_atomic '$STAGE/bin/nuxel-audio-stop.sh' /usr/lib/nuxel/nuxel-audio-stop.sh 0755
install -d -m 0755 /etc/systemd/system/nuxel-audio-session.service.d
install_atomic '$STAGE/10-audio-stop-bound.conf' /etc/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf 0644
install_atomic '$STAGE/bin/nuxel-wayland-stop.sh' /usr/lib/nuxel/nuxel-wayland-stop.sh 0755
install_atomic '$STAGE/bin/nuxel-wl-fb-hold.sh' /usr/lib/nuxel/nuxel-wl-fb-hold.sh 0755
install_atomic '$STAGE/bin/rollback-pwnage62000.sh' /usr/lib/nuxel/rollback-pwnage62000.sh 0755
install_atomic '$STAGE/bin/nuxel-preload-cinema' /usr/lib/nuxel/nuxel-preload-cinema 0755
install_atomic '$STAGE/system_indicators.py' /usr/lib/nuxel/nuxel-bridge/system_indicators.py 0644
install_atomic '$STAGE/preload-cinema.json' /etc/nuxel/boot/preload-cinema.json 0644
install_atomic '$STAGE/30-fast-stop.conf' /etc/systemd/system/nuxel-wayland.service.d/30-fast-stop.conf 0644
install_atomic '$STAGE/40-bounded-stop.conf' /etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf 0644
install_atomic '$STAGE/25-reboot-hold.conf' /etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf 0644
for d in /usr/share/nuxel/pwa/nuxel-home /usr/share/nuxel/nuxel-home; do
  [ -d \"\$d\" ] || continue
  install -d \"\$d/js\" \"\$d/css\"
  install_atomic '$STAGE/manifest.json' \"\$d/manifest.json\" 0644
  install_atomic '$STAGE/pwa/index.html' \"\$d/index.html\" 0644
  install_atomic '$STAGE/pwa/sw.js' \"\$d/sw.js\" 0644
  install_atomic '$STAGE/pwa/lockscreen-indicators.js' \"\$d/js/lockscreen-indicators.js\" 0644
  install_atomic '$STAGE/pwa/gestures.js' \"\$d/js/gestures.js\" 0644
  install_atomic '$STAGE/pwa/navigation.js' \"\$d/js/navigation.js\" 0644
  install_atomic '$STAGE/pwa/launcher.js' \"\$d/js/launcher.js\" 0644
  install_atomic '$STAGE/pwa/apps.js' \"\$d/js/apps.js\" 0644
  install_atomic '$STAGE/pwa/app.js' \"\$d/js/app.js\" 0644
  install_atomic '$STAGE/pwa/launcher.css' \"\$d/css/launcher.css\" 0644
  install_atomic '$STAGE/pwa/style.css' \"\$d/css/style.css\" 0644
  install_atomic '$STAGE/pwa/status-bar.css' \"\$d/css/status-bar.css\" 0644
done
install_atomic '$STAGE/nuxel-wayland.service' /etc/systemd/system/nuxel-wayland.service 0644
python3 -m py_compile /usr/lib/nuxel/nuxel-bridge/system_indicators.py /usr/lib/nuxel/nuxel-preload-cinema /usr/lib/nuxel/nuxel-security-lock-rpc
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/nuxel-wayland.service /etc/systemd/system/nuxel-wl-fb.service >/tmp/p62000-verify.log 2>&1 || { cat /tmp/p62000-verify.log; exit 1; }
"

echo "[p62000] restarting affected services"
"${SSH[@]}" "set -e
systemctl restart nuxel-http-bridge.service
systemctl restart nuxel-button-manager.service
# Restarts the compositor session once so the new navdock/statusbar/lock
# watcher and PWA assets are active. SSH is independent of this unit.
systemctl restart nuxel-wayland.service
# The old wl-fb may still look active for a moment after the compositor socket
# is replaced.  Restart it explicitly so it reconnects to the new session, then
# wait for both a real frame receipt and the supervised chrome state files.
systemctl restart nuxel-wl-fb.service
for i in \$(seq 1 40); do
  grep -q FRAMES_OK /run/nuxel-wl-fb.state 2>/dev/null && \
    [ -f /run/nuxel-navdock.json ] && [ -f /run/nuxel-statusbar.state ] && break
  sleep 0.5
done
sleep 1
"

echo "[p62000] health checks"
"${SSH[@]}" "set -e
unit_ok=1
for u in nuxel-wayland nuxel-wl-fb nuxel-http-bridge nuxel-button-manager; do
  systemctl is-active --quiet \$u.service || { echo \"INACTIVE \$u\"; unit_ok=0; }
done
test \"\$unit_ok\" = 1
test \"\$(systemctl show nuxel-wayland.service -p TimeoutStopUSec --value)\" = '2s'
test \"\$(systemctl show nuxel-audio-session.service -p TimeoutStopUSec --value)\" = '2s'
grep -q 'presentation-grace-expired' /usr/lib/nuxel/nuxel-preload-cinema
test -x /usr/lib/nuxel/nuxel-audio-stop.sh
test -x /usr/lib/nuxel/nuxel-statusbar
test -x /usr/lib/nuxel/nuxel-shell-chrome.sh
test -x /usr/lib/nuxel/nuxel-security-lock-rpc
test -f /run/nuxel/security/lock-state.json
export XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0
/usr/lib/nuxel/nuxel-foreign-toplevel list 2>/dev/null | grep -q 'app_id=nuxel-pwa-host'
for d in /usr/share/nuxel/pwa/nuxel-home /usr/share/nuxel/nuxel-home; do
  [ -d \"\$d\" ] || continue
  grep -q 'app.js?v=p62000' \"\$d/index.html\"
  grep -q 'touchstart' \"\$d/js/gestures.js\"
done
grep -qx 'ExecStart=/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh' /etc/systemd/system/nuxel-wayland.service
python3 - <<'PY'
import json, os
for p in ('/usr/share/nuxel/pwa/nuxel-home/manifest.json',
          '/usr/share/nuxel/nuxel-home/manifest.json'):
    if not os.path.exists(p):
        continue
    d = json.load(open(p))
    assert d.get('name') == 'Nuxel Home', (p, d.get('name'))
    n = d.get('nuxel') or {}
    assert n.get('registry_version') == 12, (p, n.get('registry_version'))
    ids = set(n.get('apps_in_registry') or [])
    assert {'org.nuxel.Clipper', 'org.nuxel.Vault'} <= ids, p
print('HEALTH manifest/unit parity OK')
PY
python3 - <<'PY'
import sys
sys.path.insert(0, '/usr/lib/nuxel/nuxel-bridge')
import system_indicators as s
d = s.get_indicators()
w = d['console_transports']['wlan']
print('HEALTH indicators live=%s serial=%s wlan_active=%s wlan_sessions=%s' % (
    d['live_console']['active'], d['console_transports']['serial']['active'],
    w['active'], w['sessions']))
assert w['active'] is False or w['sessions'] >= 1
PY
cat > /run/nuxel-p62000-deploy.json <<JSON
{\"schema_version\":1,\"mission\":\"PWNAGE-62000\",\"deployed_at\":\"\$(date -u +%FT%TZ)\",\"backup\":\"$BACKUP\",\"stage\":\"$STAGE\",\"statusbar\":true,\"navdock\":true,\"lock_watch\":true}
JSON
mkdir -p /var/lib/nuxel/diagnostics
cp /run/nuxel-p62000-deploy.json /var/lib/nuxel/diagnostics/pwnage62000-deploy.json
echo DEPLOY_OK backup=$BACKUP
"

echo "[p62000] done. Backup: $BACKUP"
echo "[p62000] rollback: /usr/lib/nuxel/rollback-pwnage62000.sh $BACKUP"
