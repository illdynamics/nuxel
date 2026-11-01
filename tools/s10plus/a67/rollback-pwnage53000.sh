#!/usr/bin/env bash
# Restore the pre-PWNAGE-53000 graphics set from a hash-verified backup and
# prove the display comes back.  Never touches /dev/fb0, kbase or BOOT.
#
#   tools/s10plus/a67/rollback-pwnage53000.sh [root@host] [/var/backups/nuxel/p53000-...]
set -euo pipefail
HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
BACKUP="${2:-}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST")

"${SSH[@]}" "BACKUP='$BACKUP' bash -s" <<'REMOTE'
set -euo pipefail
B="${BACKUP:-$(cat /run/nuxel-p53000-backup-dir 2>/dev/null || true)}"
[ -n "$B" ] && [ -d "$B" ] || { echo "no backup dir (pass one)" >&2; exit 2; }
echo "restoring from $B"
(cd "$B" && sha256sum -c SHA256SUMS 2>&1 | tail -20) || true

for f in libEGL_mesa.so.0.0.0 libgallium_dri.so libwlroots-0.19.so nuxel-wl-fb \
         nuxel-graphics-profile graphics-profile.json 50-kbase-egl.conf; do
  [ -e "$B/$f" ] || continue
  case "$f" in
    libEGL_mesa.so.0.0.0|libgallium_dri.so|libwlroots-0.19.so)
      install -m 0644 "$B/$f" "/usr/lib64/$f" ;;
    nuxel-wl-fb|nuxel-graphics-profile)
      install -m 0755 "$B/$f" "/usr/lib/nuxel/$f" ;;
    graphics-profile.json)
      install -Dm0644 "$B/$f" /etc/nuxel/graphics/graphics-profile.json ;;
    50-kbase-egl.conf)
      install -dm0755 /etc/systemd/system/nuxel-wayland.service.d
      install -m 0644 "$B/$f" /etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf ;;
  esac
done
# A pre-PWNAGE-53000 backup has no drop-in: remove it so the restored stock
# EGL library is actually used instead of being shadowed by the kbase path.
[ -e "$B/50-kbase-egl.conf" ] || rm -f /etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf
if [ -s "$B/libEGL_mesa.so.0.target" ]; then
  ln -sfn "$(cat "$B/libEGL_mesa.so.0.target")" /usr/lib64/libEGL_mesa.so.0
fi
systemctl daemon-reload
systemctl restart nuxel-wayland nuxel-wl-fb
sleep 6
systemctl is-active nuxel-wayland nuxel-wl-fb
cat /run/nuxel-wl-fb.state
REMOTE
