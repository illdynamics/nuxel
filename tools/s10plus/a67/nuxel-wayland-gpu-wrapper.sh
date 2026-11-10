#!/bin/sh
# Nuxel phone Wayland session launcher with a safe GPU-first policy.
#
# The S10+ vendor kernel has no DRM node.  Mesa panfrost drives the Mali-G76
# through ARM kbase (/dev/mali0) on an EGL surfaceless display, and wlroots is
# patched (wlroots-kbase-surfaceless.patch) to accept that when MESA_KBASE_NODE
# is set.  wlroots then uses the UDMABUF allocator for GPU-renderable output
# buffers, which the Nuxel kernel provides through the backported CONFIG_UDMABUF.
#
# If that path fails on a live boot, the wrapper leaves /run/nuxel-gpu-fallback
# and systemd's next attempt runs the proven pixman path.  /run is per-boot, so
# the device re-tries GPU acceleration on the next boot instead of staying
# permanently downgraded.
set -u
FALLBACK=/run/nuxel-gpu-fallback

export XDG_RUNTIME_DIR=/run/nuxel-wayland
export XDG_SESSION_TYPE=wayland
# Nuxel cyan cursor theme (installed under /usr/share/icons/nuxel).
export XCURSOR_THEME=nuxel
export XCURSOR_SIZE=32
export WLR_BACKENDS=headless,libinput
export WLR_HEADLESS_OUTPUTS=1
export LIBSEAT_BACKEND=noop
export WLR_LIBINPUT_NO_DEVICES=1
export LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so

# Local GPU nodes: /dev/mali0 is normally 0666, /dev/udmabuf is created 0600
# by the misc driver.  User-session apps (the PWA host) need the latter for
# DMA-BUF allocations when they opt into GL.
for node in /dev/mali0 /dev/udmabuf; do
  [ -e "$node" ] && chmod 0666 "$node" 2>/dev/null || true
done

if [ -e "$FALLBACK" ]; then
  export NUXEL_GPU=0
  export WLR_RENDERER=pixman
  echo "nuxel-wayland: GPU fallback marker present; using pixman" >&2
else
  export NUXEL_GPU=1
  export WLR_RENDERER=gles2
  export MESA_LOADER_DRIVER_OVERRIDE=panfrost
  export MESA_KBASE_NODE=/dev/mali0
  export LIBGL_DRIVERS_PATH=/usr/lib64/dri
  # panfrost shader cache is optional; keep the renderer deterministic so a
  # stale cache cannot take the UI down before the fallback is armed.
  export MESA_SHADER_CACHE_DISABLE=1
  # PWNAGE-60000: prove the kbase EGL path BEFORE handing the panel session to
  # phoc.  The helper runs the bounded probe and records a per-boot cache.  A
  # failure arms the same marker the old crash path used, so this boot runs the
  # proven pixman compositor and every app gets software-safe from the helper.
  # /run is a tmpfs: a later boot retries the GPU.
  if [ -x /usr/lib/nuxel/nuxel-graphics-profile ]; then
    if ! timeout 8 /usr/lib/nuxel/nuxel-graphics-profile probe          >/run/nuxel-gpu-boot-probe.json 2>&1; then
      : > "$FALLBACK"
      export NUXEL_GPU=0
      export WLR_RENDERER=pixman
      echo "nuxel-wayland: kbase EGL boot probe failed; using pixman" >&2
    fi
  fi
fi

/usr/sbin/phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini \
  -E /usr/lib/nuxel/nuxel-session.sh
rc=$?

if [ "$rc" -ne 0 ] && [ ! -e "$FALLBACK" ]; then
  : > "$FALLBACK"
  echo "nuxel-wayland: GPU phoc exited rc=$rc; next start uses pixman" >&2
fi
exit "$rc"
