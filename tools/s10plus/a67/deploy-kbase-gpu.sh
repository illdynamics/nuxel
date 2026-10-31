#!/usr/bin/env bash
# Deploy the kbase GPU userspace to a live Nuxel S10+ over Wi-Fi SSH.
#
#   GPU_OUT=build/out/s10plus/kbase-gpu \
#   WLR_OUT=... \
#   bash tools/s10plus/a67/deploy-kbase-gpu.sh [user@host]
#
# Defaults: GPU_OUT=build/out/s10plus/kbase-gpu, WLR_OUT=$GPU_OUT
# The key defaults to ~/.ssh/wicked_wqn_id_rsa.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="${1:-nuxel@192.168.178.167}"
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
GPU_OUT="${GPU_OUT:-$ROOT/build/out/s10plus/kbase-gpu}"
WLR_OUT="${WLR_OUT:-$GPU_OUT}"
TMP=/tmp/nuxel-kbase-deploy.$$
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$HOST")
SCP=(scp -i "$KEY" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null)

for f in "$GPU_OUT/libEGL_mesa.so.0.0.0" "$GPU_OUT/libgallium_dri.so" \
         "$WLR_OUT/libwlroots-0.19.so" "$GPU_OUT/50_mesa.json"; do
  [ -s "$f" ] || { echo "missing build artifact: $f" >&2; exit 2; }
done

"${SSH[@]}" "mkdir -p $TMP"
"${SCP[@]}" "$GPU_OUT/libEGL_mesa.so.0.0.0" "$GPU_OUT/libgallium_dri.so" \
  "$WLR_OUT/libwlroots-0.19.so" "$GPU_OUT/50_mesa.json" \
  "$ROOT/tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh" \
  "$ROOT/tools/s10plus/a29/nuxel-session.sh" \
  "$ROOT/services/nuxel-session/systemd/nuxel-wayland.service" \
  "$HOST:$TMP/" >/dev/null

"${SSH[@]}" "sudo sh -s" <<REMOTE
set -e
B=/var/backups/nuxel/kbase-gpu-\$(date +%Y%m%dT%H%M%S)
mkdir -p "\$B" /usr/lib64/dri
cp -a /usr/lib64/libEGL_mesa.so.0.0.0 "\$B/" 2>/dev/null || true
cp -a /usr/lib64/libwlroots-0.19.so "\$B/" 2>/dev/null || true
cp -a /usr/share/glvnd/egl_vendor.d/50_mesa.json "\$B/" 2>/dev/null || true
cp -a /etc/systemd/system/nuxel-wayland.service "\$B/" 2>/dev/null || true
cp -a /usr/lib/nuxel/nuxel-session.sh "\$B/" 2>/dev/null || true
install -m 0644 $TMP/libEGL_mesa.so.0.0.0 /usr/lib64/libEGL_mesa.so.0.0.0
install -m 0644 $TMP/libgallium_dri.so /usr/lib64/libgallium_dri.so
install -m 0644 $TMP/libwlroots-0.19.so /usr/lib64/libwlroots-0.19.so
install -m 0644 $TMP/50_mesa.json /usr/share/glvnd/egl_vendor.d/50_mesa.json
ln -sf ../libgallium_dri.so /usr/lib64/dri/panfrost_dri.so
ln -sf ../libgallium_dri.so /usr/lib64/dri/exynos_dri.so
install -m 0755 $TMP/nuxel-wayland-gpu-wrapper.sh /usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh
install -m 0755 $TMP/nuxel-session.sh /usr/lib/nuxel/nuxel-session.sh
install -m 0644 $TMP/nuxel-wayland.service /etc/systemd/system/nuxel-wayland.service
systemctl daemon-reload
systemctl restart nuxel-wayland nuxel-wl-fb
rm -rf $TMP
echo "deployed; backup: \$B"
REMOTE
