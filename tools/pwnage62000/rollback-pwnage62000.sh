#!/bin/sh
# Exact PWNAGE-62000 rollback.  Run as root on the phone:
#   /usr/lib/nuxel/rollback-pwnage62000.sh [/var/backups/nuxel/p62000-<stamp>]
# Restores only files present in the timestamped backup.  It never removes user
# data, SSH keys, authorized_keys, known_hosts, app data or Flatpak state.
set -eu
B="${1:-$(cat /run/nuxel-p62000-backup-dir 2>/dev/null || true)}"
[ -n "$B" ] && [ -d "$B" ] || { echo "rollback: backup directory not found" >&2; exit 2; }
say() { echo "rollback: $*"; }

restore() {
  rel="$1"; dst="/$rel"
  [ -e "$B/$rel" ] || return 0
  tmp="${dst}.p62000.rollback"
  install -m "$(stat -c %a "$B/$rel")" "$B/$rel" "$tmp"
  mv -f "$tmp" "$dst"
  say "restored $dst"
}

for f in \
  usr/lib/nuxel/nuxel-navdock usr/lib/nuxel/nuxel-statusbar \
  usr/lib/nuxel/nuxel-foreign-toplevel usr/lib/nuxel/nuxel-pwa-host \
  usr/lib/nuxel/nuxel-button-manager usr/lib/nuxel/nuxel-session.sh \
  usr/lib/nuxel/nuxel-shell-chrome.sh usr/lib/nuxel/nuxel-security-lock-rpc \
  usr/lib/nuxel/nuxel-wayland-stop.sh usr/lib/nuxel/nuxel-wl-fb-hold.sh \
  usr/lib/nuxel/nuxel-preload-cinema usr/lib/nuxel/nuxel-bridge/system_indicators.py \
  usr/lib/nuxel/stage36000/apply-pwnage36000.sh \
  usr/lib/nuxel/stage36000/nuxel-preload-cinema/nuxel-preload-cinema \
  usr/lib/nuxel/nuxel-audio-stop.sh \
  etc/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf \
  etc/nuxel/boot/preload-cinema.json \
  etc/systemd/system/nuxel-wayland.service \
  usr/share/nuxel/pwa/nuxel-home/manifest.json \
  usr/share/nuxel/nuxel-home/manifest.json \
  etc/systemd/system/nuxel-wayland.service.d/30-fast-stop.conf \
  etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf \
  etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf \
  usr/share/nuxel/pwa/nuxel-home/index.html usr/share/nuxel/pwa/nuxel-home/sw.js \
  usr/share/nuxel/pwa/nuxel-home/js/lockscreen-indicators.js \
  usr/share/nuxel/pwa/nuxel-home/js/gestures.js \
  usr/share/nuxel/pwa/nuxel-home/js/navigation.js \
  usr/share/nuxel/pwa/nuxel-home/js/app.js \
  usr/share/nuxel/pwa/nuxel-home/js/launcher.js usr/share/nuxel/pwa/nuxel-home/js/apps.js \
  usr/share/nuxel/pwa/nuxel-home/css/launcher.css \
  usr/share/nuxel/pwa/nuxel-home/css/style.css \
  usr/share/nuxel/pwa/nuxel-home/css/status-bar.css \
  usr/share/nuxel/nuxel-home/index.html usr/share/nuxel/nuxel-home/sw.js \
  usr/share/nuxel/nuxel-home/js/lockscreen-indicators.js \
  usr/share/nuxel/nuxel-home/js/gestures.js \
  usr/share/nuxel/nuxel-home/js/navigation.js \
  usr/share/nuxel/nuxel-home/js/app.js \
  usr/share/nuxel/nuxel-home/js/launcher.js usr/share/nuxel/nuxel-home/js/apps.js \
  usr/share/nuxel/nuxel-home/css/launcher.css \
  usr/share/nuxel/nuxel-home/css/style.css \
  usr/share/nuxel/nuxel-home/css/status-bar.css; do restore "$f"; done

# Files introduced only by this mission and absent from the backup are removed so
# the old session cannot accidentally execute a half-new helper.
for rel in \
  usr/lib/nuxel/nuxel-shell-chrome.sh usr/lib/nuxel/nuxel-security-lock-rpc \
  usr/lib/nuxel/nuxel-wayland-stop.sh usr/lib/nuxel/nuxel-wl-fb-hold.sh \
  etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf; do
  [ -e "$B/$rel" ] && continue
  [ -e "/$rel" ] && rm -f "/$rel" && say "removed mission-only /$rel"
done

systemctl daemon-reload
systemctl restart nuxel-http-bridge.service 2>/dev/null || true
systemctl restart nuxel-button-manager.service 2>/dev/null || true
systemctl restart nuxel-wayland.service 2>/dev/null || true
say "rollback complete from $B"
say "verify: systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-http-bridge"
