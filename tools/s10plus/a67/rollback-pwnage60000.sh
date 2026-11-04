#!/usr/bin/env bash
# Restore the pre-PWNAGE-60000 userspace graphics set from a hash-verified
# backup.  Never touches /dev/fb0, kbase, BOOT, firmware or a partition.
#
#   tools/s10plus/a67/rollback-pwnage60000.sh [root@10.20.30.16] [backup-dir]
set -euo pipefail
HOST="${1:-root@10.20.30.16}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
BACKUP="${2:-}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")

"${SSH[@]}" "BACKUP='$BACKUP' bash -s" <<'REMOTE'
set -euo pipefail
B="${BACKUP:-$(cat /run/nuxel-p60000-backup-dir 2>/dev/null || true)}"
[ -n "$B" ] && [ -d "$B" ] || { echo "no backup dir (pass one)" >&2; exit 2; }
echo "restoring from $B"
( cd "$B" && sha256sum -c SHA256SUMS 2>&1 | tail -20 ) || true

restore_one() { # backup basename, destination, mode
  local base="$1" dst="$2" mode="$3" tmp
  [ -e "$B/$base" ] || return 0
  tmp="${dst}.nuxel-rollback.$$"
  install -m "$mode" "$B/$base" "$tmp"
  mv -f "$tmp" "$dst"
  command -v restorecon >/dev/null 2>&1 && restorecon -F "$dst" 2>/dev/null || true
}

restore_one libEGL_mesa.so.0.0.0 /usr/lib64/libEGL_mesa.so.0.0.0 0644
restore_one libgallium_dri.so /usr/lib64/libgallium_dri.so 0755
restore_one libwlroots-0.19.so /usr/lib64/libwlroots-0.19.so 0644
restore_one nuxel-wl-fb /usr/lib/nuxel/nuxel-wl-fb 0755
restore_one nuxel-graphics-profile /usr/lib/nuxel/nuxel-graphics-profile 0755
restore_one nuxel-kbase-egl-probe /usr/lib/nuxel/nuxel-kbase-egl-probe 0755
restore_one nuxel-gpu-status /usr/lib/nuxel/nuxel-gpu-status 0755
restore_one nuxel-wayland-gpu-wrapper.sh /usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh 0755
restore_one nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh 0755
restore_one graphics-profile.json /etc/nuxel/graphics/graphics-profile.json 0644
restore_one egl-kbase.json /etc/nuxel/egl-kbase.json 0644
restore_one 50_mesa.json /usr/share/glvnd/egl_vendor.d/50_mesa.json 0644
restore_one gpu-manifest.json /usr/share/nuxel/gpu-manifest.json 0644
restore_one api.py /usr/lib/nuxel/nuxel-bridge/api.py 0644

# Remove files that did not exist before the deployment.
if [ -f "$B/missing.list" ]; then
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    case "$f" in
      /usr/lib/nuxel/nuxel-gpu-status|/usr/lib/nuxel/nuxel-kbase-egl-probe|/usr/share/nuxel/gpu-manifest.json)
        rm -f "$f" ;;
    esac
  done < "$B/missing.list"
fi

for l in libEGL_mesa.so.0 panfrost_dri.so exynos_dri.so; do
  t="$B/$l.target"
  [ -s "$t" ] || continue
  case "$l" in
    libEGL_mesa.so.0) ln -sfn "$(cat "$t")" "/usr/lib64/$l" ;;
    panfrost_dri.so|exynos_dri.so) ln -sfn "$(cat "$t")" "/usr/lib64/dri/$l" ;;
  esac
done

# Restore the pre-deploy profile exactly; remove the per-boot cache/marker so
# the restored policy is re-evaluated instead of inheriting a newer result.
rm -f /run/nuxel/graphics-gpu-probe.json /run/nuxel-gpu-fallback
systemctl restart nuxel-wayland nuxel-wl-fb
systemctl restart nuxel-bridge 2>/dev/null || true

for i in $(seq 1 45); do
  state=$(cat /run/nuxel-wl-fb.state 2>/dev/null || true)
  active=$(systemctl is-active nuxel-wayland nuxel-wl-fb 2>/dev/null | tr '\n' ' ')
  if [ "$active" = "active active " ] && printf '%s' "$state" | grep -q FRAMES_OK; then
    echo "$state"
    echo "ROLLBACK_OK backup=$B"
    exit 0
  fi
  sleep 1
done
echo "ROLLBACK_HEALTH_TIMEOUT state=${state:-none} active=${active:-none}" >&2
exit 1
REMOTE
