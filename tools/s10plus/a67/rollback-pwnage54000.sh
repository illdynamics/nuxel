#!/usr/bin/env bash
# Restore the pre-PWNAGE-54000 userspace files from the deploy backup.
#   tools/s10plus/a67/rollback-pwnage54000.sh [root@host] [/var/backups/nuxel/p54000-...]
set -euo pipefail
HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
B="${2:-}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
"${SSH[@]}" "B='$B' bash -s" <<'REMOTE'
set -euo pipefail
B="${B:-$(cat /run/nuxel-p54000-backup-dir 2>/dev/null || true)}"
[ -n "$B" ] && [ -d "$B" ] || { echo "no backup dir (pass one)" >&2; exit 2; }
echo "restoring userspace from $B"
[ -d "$B/nuxel_orientation" ] && rm -rf /usr/libexec/nuxel/nuxel_orientation && cp -a "$B/nuxel_orientation" /usr/libexec/nuxel/nuxel_orientation
[ -f "$B/nuxel-orientationd" ] && install -m 0755 "$B/nuxel-orientationd" /usr/libexec/nuxel/nuxel-orientationd
[ -f "$B/orientation.json" ] && install -m 0644 "$B/orientation.json" /etc/nuxel/orientation/orientation.json
[ -f "$B/nuxel-navdock" ] && install -m 0755 "$B/nuxel-navdock" /usr/lib/nuxel/nuxel-navdock
[ -f "$B/nuxel-foreign-toplevel" ] && install -m 0755 "$B/nuxel-foreign-toplevel" /usr/lib/nuxel/nuxel-foreign-toplevel
[ -f "$B/nuxel-pwa-host" ] && install -m 0755 "$B/nuxel-pwa-host" /usr/lib/nuxel/nuxel-pwa-host
[ -f "$B/libnuxel-libinput-path.so" ] && install -m 0755 "$B/libnuxel-libinput-path.so" /usr/lib/nuxel/libnuxel-libinput-path.so
[ -f "$B/portal.py" ] && install -m 0755 "$B/portal.py" /usr/lib/nuxel/nuxel-portal/portal.py
[ -f "$B/nuxel-portal.service" ] && install -m 0644 "$B/nuxel-portal.service" /etc/systemd/system/nuxel-portal.service
[ -f "$B/pwa-home.tgz" ] && tar -C /usr/share/nuxel -xzf "$B/pwa-home.tgz"
[ -f "$B/pwa-recorder.tgz" ] && tar -C /usr/share/nuxel -xzf "$B/pwa-recorder.tgz"
[ -f "$B/assets.tgz" ] && tar -C /usr/share/nuxel/assets -xzf "$B/assets.tgz"
# The pre-deploy presenter is the fallback copy made by the deploy script.
if [ -x /usr/lib/nuxel/nuxel-wl-fb.p54000-prev ]; then
  install -m 0755 /usr/lib/nuxel/nuxel-wl-fb.p54000-prev /usr/lib/nuxel/nuxel-wl-fb
fi
systemctl daemon-reload
systemctl restart nuxel-orientationd
systemctl restart nuxel-portal
systemctl restart nuxel-wayland
sleep 4
systemctl is-active nuxel-orientationd nuxel-wayland nuxel-wl-fb
cat /run/nuxel-wl-fb-orientation 2>/dev/null || true
REMOTE
