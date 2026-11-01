#!/bin/sh
# Bounded kbase Wayland-WSI canary.
#
# Starts a SECOND headless Phoc on its own socket, using the patched wlroots
# (linux-dmabuf v3) and the experimental Mesa Wayland build.  It never touches
# the live session, /dev/fb0 or the main Wayland socket.  This is the only
# supported way to test the buffer-sharing path until the main compositor's
# linux-dmabuf crash is fixed.
set -eu
RT=/run/nuxel-wsi-canary
LOG=/run/nuxel-wsi-canary.log
STAGE=/usr/local/lib/nuxel-gpu
PROBE=${PROBE:-/usr/local/bin/nuxel-wayland-egl-probe}
mkdir -p "$RT"
chmod 700 "$RT"
rm -f "$RT/wayland-0" "$RT/wayland-0.lock"
[ -x "$STAGE/libwlroots-0.19.so" ] || { echo "missing $STAGE/libwlroots-0.19.so" >&2; exit 2; }
[ -x "$STAGE/libgallium_dri.so" ] || { echo "missing $STAGE/libgallium_dri.so" >&2; exit 2; }
# The experimental driver is loaded from the staging dir; the system default
# stays on the proven surfaceless build.
XDG_RUNTIME_DIR="$RT" \
MESA_KBASE_NODE=/dev/mali0 MESA_LOADER_DRIVER_OVERRIDE=panfrost \
LIBGL_DRIVERS_PATH="$STAGE/dri" \
__EGL_VENDOR_LIBRARY_FILENAMES="$STAGE/50_mesa.json" \
LD_LIBRARY_PATH="$STAGE" \
WLR_BACKENDS=headless,libinput WLR_HEADLESS_OUTPUTS=1 \
LIBSEAT_BACKEND=noop WLR_LIBINPUT_NO_DEVICES=1 WLR_RENDERER=gles2 \
MESA_SHADER_CACHE_DISABLE=1 \
/usr/sbin/phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E "/bin/sleep 90" \
  >"$LOG" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT INT TERM
i=0
while [ ! -S "$RT/wayland-0" ] && [ "$i" -lt 80 ]; do i=$((i+1)); sleep 0.1; done
[ -S "$RT/wayland-0" ] || { echo "canary compositor socket did not appear" >&2; tail -20 "$LOG" >&2; exit 3; }
XDG_RUNTIME_DIR="$RT" WAYLAND_DISPLAY=wayland-0 \
MESA_KBASE_NODE=/dev/mali0 MESA_LOADER_DRIVER_OVERRIDE=panfrost \
LIBGL_DRIVERS_PATH="$STAGE/dri" \
__EGL_VENDOR_LIBRARY_FILENAMES="$STAGE/50_mesa.json" \
LD_LIBRARY_PATH="$STAGE" NUXEL_KBASE_WSI=1 \
timeout 25 "$PROBE" 2
RC=$?
kill "$PID" 2>/dev/null || true
trap - EXIT INT TERM
echo "{\"canary\":\"$([ "$RC" -eq 0 ] && echo PASS || echo FAIL)\",\"exit_code\":$RC}"
exit "$RC"
