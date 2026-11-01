#!/bin/sh
# PWNAGE-53000 live acceptance: proves each stage independently.
# Run on the phone as root.  It never writes /dev/fb0 and never restarts Phoc.
set -u
OUT="${OUT:-/tmp/pwnage53000-live}"
mkdir -p "$OUT"
FAIL=0
say() { printf '%s\n' "$*"; }
ck() { if [ "$1" = 0 ]; then say "PASS $2"; else say "FAIL $2"; FAIL=1; fi; }

RT=/run/nuxel-wayland
export XDG_RUNTIME_DIR=$RT WAYLAND_DISPLAY=wayland-0
BASE="MESA_KBASE_NODE=/dev/mali0 MESA_LOADER_DRIVER_OVERRIDE=panfrost LIBGL_DRIVERS_PATH=/usr/lib64/dri __EGL_VENDOR_LIBRARY_FILENAMES=/etc/nuxel/egl-kbase.json"

P=$(pgrep -n phoc); [ -n "$P" ]
grep -q libgallium_dri /proc/$P/maps; ck $? "0 phoc loads kbase Mesa"
[ "$(ls -l /proc/$P/fd | grep -c mali0)" -ge 3 ]; ck $? "0 phoc holds >=3 /dev/mali0 fds"

env $BASE timeout 15 /usr/local/bin/nuxel-kbase-egl-probe >$OUT/egl-surfaceless.log 2>&1
grep -q 'GL_RENDERER=Mali-G76' $OUT/egl-surfaceless.log; ck $? "1 EGL surfaceless renders on Mali"

env $BASE timeout 20 /usr/lib/nuxel/nuxel-egl-wayland-probe >$OUT/egl-wayland.log 2>&1
grep -q '^PASS' $OUT/egl-wayland.log; ck $? "2 EGL_PLATFORM_WAYLAND window surface + swap + destroy"

env $BASE GDK_BACKEND=wayland GDK_GL=gles timeout 20 /usr/lib/nuxel/nuxel-gtk3-gl-probe >$OUT/gtk3.log 2>&1
grep -q '"gtk3_gl":"PASS"' $OUT/gtk3.log; ck $? "3 GTK3 GtkGLArea renders on Mali"

wayland-info 2>/dev/null | grep -q zwp_linux_dmabuf_v1; ck $? "4 linux-dmabuf global present"
FMT=$(wayland-info 2>/dev/null | sed -n '/zwp_linux_dmabuf_v1/,/^interface:/p')
echo "$FMT" > $OUT/dmabuf-formats.txt
echo "$FMT" | grep -q "AB24'; 0x0000000000000000 = LINEAR"; ck $? "4 AB24 LINEAR advertised"
echo "$FMT" | grep -q "ARM_BLOCK_SIZE"; [ $? -ne 0 ]; ck $? "4 no unproven ARM tiled modifiers"

timeout 60 /usr/local/bin/nuxel-dmabuf-negative 10 valid >$OUT/dmabuf-valid.log 2>&1
grep -q PASS $OUT/dmabuf-valid.log; ck $? "5 valid linear DMA-BUF import x10"
timeout 30 /usr/local/bin/nuxel-dmabuf-negative 10 mod >$OUT/dmabuf-bad-mod.log 2>&1
grep -q PASS $OUT/dmabuf-bad-mod.log; ck $? "5 unsupported modifier safe"
timeout 30 /usr/local/bin/nuxel-dmabuf-negative 1 kill-client >$OUT/dmabuf-bad-offset.log 2>&1
ck $? "5 malformed offset disconnects only the client"
P2=$(pgrep -n phoc); [ "$P" = "$P2" ]; ck $? "5 Phoc PID unchanged after malformed input"

# WebKit GPU-rendered-SHM probe (diagnostic page, isolated env)
env $BASE GDK_BACKEND=wayland GDK_GL=gles NUXEL_KBASE_WSI=1 \
  WEBKIT_FORCE_COMPOSITING_MODE=1 NUXEL_HOME_URL=file:///usr/share/nuxel/pwnage53000/index.html \
  timeout 20 /usr/lib/nuxel/nuxel-pwa-host >$OUT/webkit.log 2>&1 &
sleep 6
H=""; for p in $(pgrep -x nuxel-pwa-host); do
  tr '\0' '\n' </proc/$p/environ 2>/dev/null | grep -q pwnage53000 && H=$p && break
done
W=""; for p in $(pgrep -f WebKitWebProcess); do
  [ "$(awk '{print $4}' /proc/$p/stat 2>/dev/null)" = "$H" ] && W=$p && break
done
[ -n "$W" ]; ck $? "6 WebKit web process found"
[ "$(ls -l /proc/$W/fd 2>/dev/null | grep -c mali0)" -ge 1 ]; ck $? "6 WebKit web process holds kbase"
[ "$(ps -L -p $W -o comm= 2>/dev/null | grep -c eadedCompositor)" -ge 1 ]; ck $? "6 ThreadedCompositor active"
timeout 3 strace -f -e trace=ioctl -p $W -o $OUT/webkit-ioctl.txt 2>/dev/null
grep -q "_IOC(_IOC_WRITE, 0x80, 0x2" $OUT/webkit-ioctl.txt; ck $? "6 KBASE_IOCTL_JOB_SUBMIT observed"
say "info WebKit dmabuf fds=$(ls -l /proc/$W/fd 2>/dev/null | grep -cE 'udmabuf|dmabuf') (0 = SHM presentation)"
kill $H 2>/dev/null

STATE=$(cat /run/nuxel-wl-fb.state 2>/dev/null)
echo "$STATE" > $OUT/fb-state.txt
echo "$STATE" | grep -q FRAMES_OK; ck $? "7 FRAMES_OK"
echo "$STATE" | grep -q "decon_pan_failed=0"; ck $? "7 decon_pan_failed=0"
[ "$(cat /sys/class/graphics/fb0/virtual_size)" = "1440,6080" ]; ck $? "7 /dev/fb0 1440x6080"
[ "$(fuser /dev/fb0 2>/dev/null | wc -w)" -eq 1 ]; ck $? "7 exactly one /dev/fb0 writer"
[ ! -e /run/nuxel-gpu-fallback ]; ck $? "7 no GPU fallback marker"

say "RESULT=$([ $FAIL -eq 0 ] && echo PASS || echo FAIL)"
exit $FAIL
