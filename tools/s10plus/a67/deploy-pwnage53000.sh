#!/usr/bin/env bash
# Deploy the PWNAGE-53000 GPU/EGL/DMA-BUF userspace set to the live S10+.
#
#   STAGE=/path/to/stage tools/s10plus/a67/deploy-pwnage53000.sh [root@host]
#
# STAGE must contain:
#   libEGL_mesa.so.0.0.0   kbase Mesa with EGL_PLATFORM_WAYLAND (Wayland WSI)
#   libgallium_dri.so      matching panfrost/kbase gallium
#   libwlroots-0.19.so     0.19.3 + surfaceless + LINEAR-only dmabuf patches
#   nuxel-wl-fb            adaptive-pacing bridge build
#   nuxel-graphics-profile profile helper (schema 2)
#   graphics-profile.json  schema 2 policy
#   egl-kbase.json         glvnd vendor file pointing at the absolute path
#
# It writes a timestamped, hash-verified backup under /var/backups/nuxel and
# never touches /dev/fb0, kbase, BOOT or any partition.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-root@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
STAGE="${STAGE:-$ROOT/build/out/s10plus/pwnage53000}"
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new "$HOST")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=accept-new)

for f in libEGL_mesa.so.0.0.0 libgallium_dri.so libwlroots-0.19.so \
         nuxel-wl-fb nuxel-graphics-profile graphics-profile.json egl-kbase.json; do
  [ -s "$STAGE/$f" ] || { echo "missing $STAGE/$f" >&2; exit 2; }
done

TMP=/tmp/pwnage53000-deploy.$$
"${SSH[@]}" "mkdir -p $TMP"
"${SCP[@]}" "$STAGE"/{libEGL_mesa.so.0.0.0,libgallium_dri.so,libwlroots-0.19.so,nuxel-wl-fb,nuxel-graphics-profile,graphics-profile.json,egl-kbase.json} "$HOST:$TMP/" >/dev/null
"${SCP[@]}" "$ROOT/services/nuxel-session/systemd/nuxel-wayland.service.d/50-kbase-egl.conf" "$HOST:$TMP/" >/dev/null

"${SSH[@]}" "bash -s" <<REMOTE
set -euo pipefail
B=/var/backups/nuxel/p53000-\$(date +%Y%m%dT%H%M%S)
mkdir -p "\$B"
readlink /usr/lib64/libEGL_mesa.so.0 > "\$B/libEGL_mesa.so.0.target" 2>/dev/null || true
for f in /usr/lib64/libEGL_mesa.so.0.0.0 /usr/lib64/libgallium_dri.so \
         /usr/lib64/libwlroots-0.19.so /usr/lib/nuxel/nuxel-wl-fb \
         /usr/lib/nuxel/nuxel-graphics-profile \
         /etc/nuxel/graphics/graphics-profile.json \
         /etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf; do
  [ -e "\$f" ] && cp -a "\$f" "\$B/" || true
done
(cd "\$B" && sha256sum * > SHA256SUMS)
echo "\$B" > /run/nuxel-p53000-backup-dir

install -m 0644 $TMP/libEGL_mesa.so.0.0.0 /usr/lib64/libEGL_mesa.so.0.0.0
install -m 0755 $TMP/libgallium_dri.so   /usr/lib64/libgallium_dri.so
install -m 0644 $TMP/libwlroots-0.19.so  /usr/lib64/libwlroots-0.19.so
install -m 0755 $TMP/nuxel-wl-fb         /usr/lib/nuxel/nuxel-wl-fb
install -m 0755 $TMP/nuxel-graphics-profile /usr/lib/nuxel/nuxel-graphics-profile
install -Dm0644 $TMP/graphics-profile.json /etc/nuxel/graphics/graphics-profile.json
install -Dm0644 $TMP/egl-kbase.json /etc/nuxel/egl-kbase.json
install -d -m 0755 /etc/systemd/system/nuxel-wayland.service.d
install -m 0644 $TMP/50-kbase-egl.conf /etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf
ln -sfn libEGL_mesa.so.0.0.0 /usr/lib64/libEGL_mesa.so.0
ln -sfn ../libgallium_dri.so /usr/lib64/dri/panfrost_dri.so
ln -sfn ../libgallium_dri.so /usr/lib64/dri/exynos_dri.so
systemctl daemon-reload
systemctl restart nuxel-wayland nuxel-wl-fb
rm -rf $TMP
echo "backup=\$B"
REMOTE

sleep 6
"${SSH[@]}" 'systemctl is-active nuxel-wayland nuxel-wl-fb; cat /run/nuxel-wl-fb.state'
