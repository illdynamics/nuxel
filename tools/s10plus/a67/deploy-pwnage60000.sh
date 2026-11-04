#!/usr/bin/env bash
# PWNAGE-60000 atomic live deployment over Wi-Fi SSH.
#
#   tools/s10plus/a67/deploy-pwnage60000.sh [root@10.20.30.16] [--no-rollback]
#
# Installs only userspace graphics/policy/diagnostic files, builds the two
# small probes on the target, keeps a hash-verified backup, restarts the
# minimum services, verifies one /dev/fb0 writer and real WebKit GPU mappings,
# and automatically restores the backup if the display health check fails.
# Never writes BOOT, firmware, a partition or /dev/mali0.  Never creates a DRM
# node.  The single framebuffer writer contract is preserved.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
HOST="root@10.20.30.16"
ROLLBACK=1
for a in "$@"; do
  case "$a" in
    --no-rollback) ROLLBACK=0 ;;
    root@*|*@*) HOST="$a" ;;
    *) echo "unknown argument: $a" >&2; exit 2 ;;
  esac
done
KEY="${SSH_KEY:-$HOME/.ssh/wicked_wqn_id_rsa}"
SSH=(ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=10 "$HOST")
SCP=(scp -i "$KEY" -o BatchMode=yes)
R=/tmp/nuxel-p60000.$$
B=/var/backups/nuxel/p60000-$(date -u +%Y%m%dT%H%M%SZ)
E=/root/pwnage-60000/deploy-$(date -u +%Y%m%dT%H%M%SZ)
LOCAL_E="$ROOT/evidence/pwnage-60000/deploy/$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$LOCAL_E"

echo "== preflight =="
"${SSH[@]}" "set -e
  test \"\$(uname -m)\" = aarch64
  test -e /dev/fb0
  command -v gcc >/dev/null
  command -v wayland-scanner >/dev/null
  command -v python3 >/dev/null
  test -e /dev/mali0
  echo \"target=\$(uname -n) kernel=\$(uname -r)\""

echo "== stage sources =="
"${SSH[@]}" "mkdir -p '$R' '$B' '$E'"
"${SCP[@]}" \
  "$ROOT/tools/s10plus/a45/nuxel-graphics-profile" \
  "$ROOT/configs/nuxel/graphics/graphics-profile.json" \
  "$ROOT/tools/s10plus/a67/nuxel-gpu-status" \
  "$ROOT/tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh" \
  "$ROOT/tools/s10plus/a45/nuxel-session.sh" \
  "$ROOT/tools/s10plus/a67/nuxel-wl-fb.c" \
  "$ROOT/tools/s10plus/a67/nuxel-kbase-egl-probe.c" \
  "$ROOT/tools/s10plus/a67/nuxel-drm-main-device-probe.c" \
  "$ROOT/tools/s10plus/a67/nuxel-gtk4-gsk-probe.c" \
  "$ROOT/tools/s10plus/a33/nuxel-handoff-logic.h" \
  "$ROOT/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml" \
  "$ROOT/release/s10plus/gpu/gpu-manifest.json" \
  "$ROOT/release/s10plus/gpu/SHA256SUMS" \
  "$ROOT/release/s10plus/gpu/libEGL_mesa.so.0.0.0" \
  "$ROOT/release/s10plus/gpu/libgallium_dri.so" \
  "$ROOT/release/s10plus/gpu/libwlroots-0.19.so" \
  "$ROOT/release/s10plus/gpu/egl-kbase.json" \
  "$ROOT/release/s10plus/gpu/50_mesa.json" \
  "$ROOT/tools/s10plus/a67/nuxel-gpu-image-verify.sh" \
  "$ROOT/services/nuxel-bridge/src/api.py" \
  "$ROOT/services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh" \
  "$HOST:$R/" >/dev/null

echo "== build, backup, install and health-check on target =="
set +e
"${SSH[@]}" "R='$R' B='$B' E='$E' bash -s" <<'REMOTE'
set -euo pipefail
exec > >(tee -a "$E/deploy.log") 2>&1
say() { echo "[$(date -u +%FT%TZ)] $*"; }

say "== backup =="
: > "$B/existing.list"; : > "$B/missing.list"
for f in \
  /usr/lib64/libEGL_mesa.so.0.0.0 /usr/lib64/libgallium_dri.so \
  /usr/lib64/libwlroots-0.19.so /usr/lib/nuxel/nuxel-wl-fb \
  /usr/lib/nuxel/nuxel-graphics-profile /usr/lib/nuxel/nuxel-kbase-egl-probe \
  /usr/lib/nuxel/nuxel-gpu-status /usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh \
  /usr/lib/nuxel/nuxel-session.sh \
  /etc/nuxel/graphics/graphics-profile.json /etc/nuxel/egl-kbase.json \
  /usr/share/glvnd/egl_vendor.d/50_mesa.json /usr/share/nuxel/gpu-manifest.json \
  /usr/lib/nuxel/nuxel-bridge/api.py; do
  if [ -e "$f" ]; then
    cp -a "$f" "$B/" 2>/dev/null || true
    echo "$f" >> "$B/existing.list"
  else
    echo "$f" >> "$B/missing.list"
  fi
done
for l in /usr/lib64/libEGL_mesa.so.0 /usr/lib64/dri/panfrost_dri.so /usr/lib64/dri/exynos_dri.so; do
  [ -L "$l" ] && readlink "$l" > "$B/$(basename "$l").target" || true
done
( cd "$B" && sha256sum * > SHA256SUMS 2>/dev/null || true )
echo "$B" > /run/nuxel-p60000-backup-dir
cp -a /run/nuxel-wl-fb.state "$E/before-state.txt" 2>/dev/null || true
systemctl is-active nuxel-wayland nuxel-wl-fb > "$E/before-active.txt" 2>&1 || true
say "backup=$B"

say "== build probes and bridge =="
cd "$R"
wayland-scanner client-header wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-client-protocol.h
wayland-scanner private-code wlr-screencopy-unstable-v1.xml wlr-screencopy-unstable-v1-protocol.c
gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 -I. \
  $(pkg-config --cflags wayland-client) -o nuxel-wl-fb \
  nuxel-wl-fb.c wlr-screencopy-unstable-v1-protocol.c \
  $(pkg-config --libs wayland-client)
gcc -O2 -Wall -Wextra -std=gnu11 -o nuxel-kbase-egl-probe \
  nuxel-kbase-egl-probe.c $(pkg-config --cflags --libs egl glesv2)
gcc -O2 -Wall -Wextra -I/usr/include/libdrm -o nuxel-drm-main-device-probe \
  nuxel-drm-main-device-probe.c -ldrm 2>/dev/null || true
if pkg-config --exists gtk4; then
  gcc -O2 -Wall -Wextra $(pkg-config --cflags gtk4) -o nuxel-gtk4-gsk-probe \
    nuxel-gtk4-gsk-probe.c $(pkg-config --libs gtk4)
fi
python3 -m py_compile api.py nuxel-graphics-profile nuxel-gpu-status
./nuxel-wl-fb --damage-selftest | tee "$E/damage-selftest.txt"
./nuxel-wl-fb --colour-selftest | tee "$E/colour-selftest.txt"
timeout 8 env MESA_KBASE_NODE=/dev/mali0 MESA_LOADER_DRIVER_OVERRIDE=panfrost \
  LIBGL_DRIVERS_PATH=/usr/lib64/dri \
  __EGL_VENDOR_LIBRARY_FILENAMES="$R/egl-kbase.json" \
  ./nuxel-kbase-egl-probe | tee "$E/egl-probe.txt"
if [ -x ./nuxel-drm-main-device-probe ]; then
  ./nuxel-drm-main-device-probe | tee "$E/drm-main-device-probe.txt" || true
fi
sha256sum nuxel-wl-fb nuxel-kbase-egl-probe nuxel-drm-main-device-probe 2>/dev/null > "$E/built-sha256.txt" || true

say "== install =="
put() { # src dst mode
  local src="$1" dst="$2" mode="$3" tmp
  tmp="${dst}.nuxel-new.$$"
  install -m "$mode" "$src" "$tmp"
  mv -f "$tmp" "$dst"
  command -v restorecon >/dev/null 2>&1 && restorecon -F "$dst" 2>/dev/null || true
}
put "$R/nuxel-wl-fb" /usr/lib/nuxel/nuxel-wl-fb 0755
put "$R/nuxel-kbase-egl-probe" /usr/lib/nuxel/nuxel-kbase-egl-probe 0755
put "$R/nuxel-graphics-profile" /usr/lib/nuxel/nuxel-graphics-profile 0755
put "$R/nuxel-gpu-status" /usr/lib/nuxel/nuxel-gpu-status 0755
[ -x "$R/nuxel-gtk4-gsk-probe" ] && put "$R/nuxel-gtk4-gsk-probe" /usr/lib/nuxel/nuxel-gtk4-gsk-probe 0755 || true
put "$R/nuxel-wayland-gpu-wrapper.sh" /usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh 0755
put "$R/nuxel-session.sh" /usr/lib/nuxel/nuxel-session.sh 0755
put "$R/graphics-profile.json" /etc/nuxel/graphics/graphics-profile.json 0644
put "$R/egl-kbase.json" /etc/nuxel/egl-kbase.json 0644
put "$R/50_mesa.json" /usr/share/glvnd/egl_vendor.d/50_mesa.json 0644
install -Dm0644 "$R/gpu-manifest.json" /usr/share/nuxel/gpu-manifest.json
install -Dm0644 "$R/SHA256SUMS" /usr/share/nuxel/gpu-SHA256SUMS
# The boot-time PWN36000 bootstrap must not revert this session file.  Patch
# its "newer deployed wins" guard and stage the same current session so either
# path yields identical content.
if [ -d /usr/lib/nuxel/stage36000 ]; then
  put "$R/nuxel-apply-pwnage36000.sh" /usr/lib/nuxel/stage36000/apply-pwnage36000.sh 0755
  install -Dm0755 "$R/nuxel-session.sh" /usr/lib/nuxel/stage36000/session/nuxel-session.sh
fi
ln -sfn libEGL_mesa.so.0.0.0 /usr/lib64/libEGL_mesa.so.0
ln -sfn ../libgallium_dri.so /usr/lib64/dri/panfrost_dri.so
ln -sfn ../libgallium_dri.so /usr/lib64/dri/exynos_dri.so

# Fail closed: verify the live tree against the same release manifest used by
# image builds.  This catches a stale helper/config or a reset GLVND symlink.
bash "$R/nuxel-gpu-image-verify.sh" / --manifest "$R/gpu-manifest.json" \
  | tee "$E/image-verify.txt"

# Policy validation BEFORE touching the live session.
NUXEL_GRAPHICS_PROFILE=/etc/nuxel/graphics/graphics-profile.json \
  /usr/lib/nuxel/nuxel-graphics-profile validate | tee "$E/profile-validate.json"
rm -f /run/nuxel-gpu-fallback /run/nuxel/graphics-gpu-probe.json
/usr/lib/nuxel/nuxel-graphics-profile probe --refresh | tee "$E/profile-probe.json"

say "== restart compositor + bridge =="
systemctl restart nuxel-wayland nuxel-wl-fb

health() {
  local i state writers active
  for i in $(seq 1 45); do
    active=$(systemctl is-active nuxel-wayland nuxel-wl-fb 2>/dev/null | tr '\n' ' ')
    state=$(cat /run/nuxel-wl-fb.state 2>/dev/null || true)
    writers=$(python3 - <<'PY'
import os
n=0
for e in os.listdir('/proc'):
    if not e.isdigit(): continue
    try:
        for f in os.listdir('/proc/%s/fd' % e):
            try:
                if os.readlink('/proc/%s/fd/%s' % (e,f)) == '/dev/fb0': n+=1
            except OSError: pass
    except OSError: pass
print(n)
PY
)
    if [ "$active" = "active active " ] && printf '%s' "$state" | grep -q FRAMES_OK && [ "$writers" = "1" ]; then
      echo "$state" > "$E/after-state.txt"
      echo "writers=$writers" >> "$E/after-state.txt"
      return 0
    fi
    sleep 1
  done
  echo "HEALTH_TIMEOUT active=$active writers=$writers state=$state" | tee "$E/health-failure.txt"
  return 1
}
health

# Prove the production WebKit process is on Mali and presents through SHM.
webkit_health() {
  local i pid maps env
  for i in $(seq 1 45); do
    pid=$(pgrep -f WebKitWebProcess | head -1 || true)
    if [ -n "$pid" ]; then
      maps=$(grep -c 'libgallium' /proc/$pid/maps 2>/dev/null || true)
      env=$(tr '\0' '\n' < /proc/$pid/environ 2>/dev/null || true)
      if [ "${maps:-0}" -gt 0 ] && echo "$env" | grep -q 'WEBKIT_DISABLE_COMPOSITING_MODE=0'; then
        echo "pid=$pid gallium_maps=$maps" > "$E/webkit-gpu.txt"
        echo "$env" | grep -E 'WEBKIT_|NUXEL_|MESA_|LIBGL_' >> "$E/webkit-gpu.txt" || true
        ls -l /proc/$pid/fd 2>/dev/null | grep -E 'mali0|udmabuf|dmabuf' >> "$E/webkit-gpu.txt" || true
        return 0
      fi
    fi
    sleep 1
  done
  echo "WEBKIT_GPU_NOT_OBSERVED pid=${pid:-none}" | tee "$E/webkit-gpu-failure.txt"
  return 1
}
webkit_health || WEBKIT_RC=$?

say "== install bridge API and restart =="
put "$R/api.py" /usr/lib/nuxel/nuxel-bridge/api.py 0644
systemctl restart nuxel-bridge
sleep 2
systemctl is-active nuxel-bridge > "$E/bridge-active.txt" 2>&1 || true
if ! systemctl is-active --quiet nuxel-bridge; then
  echo "BRIDGE_FAILED" | tee "$E/bridge-failure.txt"
  exit 4
fi

say "== read-only media/external caches =="
timeout 40 /usr/local/sbin/nuxel-cast-diag.sh status --json > /run/nuxel/cast-status.json 2>/dev/null || true
timeout 25 /usr/local/sbin/nuxel-typec-diag.sh status --json > /run/nuxel/typec-status.json 2>/dev/null || true

say "== status (deep probe populates GTK3/GTK4 caches) =="
/usr/lib/nuxel/nuxel-gpu-status --deep --json > "$E/status-deep.json" 2>&1 || true
/usr/lib/nuxel/nuxel-gpu-status --json --no-probe > "$E/status.json" 2>&1 || true
/usr/lib/nuxel/nuxel-gpu-status --no-probe > "$E/status.txt" 2>&1 || true
sha256sum /usr/lib/nuxel/nuxel-wl-fb /usr/lib/nuxel/nuxel-kbase-egl-probe \
  /usr/lib/nuxel/nuxel-graphics-profile /usr/lib/nuxel/nuxel-gpu-status \
  /usr/lib/nuxel/nuxel-bridge/api.py > "$E/installed-sha256.txt"
echo "$B" > "$E/backup-dir.txt"
say "DEPLOY_OK backup=$B evidence=$E"
exit ${WEBKIT_RC:-0}
REMOTE
RC=$?
set -e

echo "== collect evidence =="
"${SCP[@]}" -r "$HOST:$E" "$LOCAL_E/" >/dev/null 2>&1 || true
"${SSH[@]}" 'echo "== final status =="; cat /run/nuxel-wl-fb.state; echo; systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-bridge' > "$LOCAL_E/final-status.txt" 2>&1 || true

if [ "$RC" -ne 0 ]; then
  echo "deployment health check failed rc=$RC" >&2
  if [ "$ROLLBACK" = 1 ]; then
    echo "== automatic rollback ==" >&2
    "$ROOT/tools/s10plus/a67/rollback-pwnage60000.sh" "$HOST" || true
  fi
  exit "$RC"
fi
echo "PWNAGE-60000 deploy: PASS"
echo "backup: $B"
echo "evidence: $LOCAL_E"
