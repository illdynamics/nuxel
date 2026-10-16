#!/bin/bash
# Executed inside docker --platform linux/arm64 fedora:43, not on macOS.
set -Eeuo pipefail
[[ "$(uname -m)" == aarch64 ]] || { echo 'ERROR: expected aarch64 execution' >&2; exit 2; }
NAME="${NUXEL_IMAGE_NAME:?}"
MB="${NUXEL_IMAGE_MB:?}"
[[ "$NAME" != */* && "$NAME" == *.img ]] || { echo 'ERROR: invalid image name' >&2; exit 2; }
OUT="/deliver/$NAME"
[[ ! -e "$OUT" ]] || { echo 'ERROR: existing destination; refusing overwrite' >&2; exit 2; }
STAGE="$(mktemp -d /tmp/nuxel-fedora-stage.XXXXXX)"
cleanup() { rm -rf "$STAGE"; }
trap cleanup EXIT
trap 'rm -f "$OUT" "$OUT.sha256"' ERR
# DNF packages are resolved for Fedora 43/aarch64 by an ARM64 Fedora container.
# A dependency error must abort, rather than emitting a deceptive bare /etc tree.
dnf -y install e2fsprogs findutils coreutils file rpm shadow-utils python3
# Required in the target: real binaries and shared libraries, not .desktop shims.
dnf -y --installroot="$STAGE" --releasever=43 --use-host-config --setopt=install_weak_deps=False install \
    basesystem filesystem setup fedora-release glibc glibc-langpack-en \
    bash coreutils util-linux findutils grep sed gawk \
    systemd systemd-udev systemd-networkd dbus-broker dbus-daemon \
    python3 phosh phoc stevia stevia-phosh-osk-provider \
    NetworkManager ModemManager \
    mesa-dri-drivers mesa-libEGL mesa-libgbm libinput \
    polkit greetd \
    iproute procps-ng kmod e2fsprogs \
    shadow-utils ca-certificates curl
# Keep Nuxel's native phone-specific bits; do not import the G7 Power staging.
install -d "$STAGE/etc/nuxel/device/s10plus" "$STAGE/etc/udev/rules.d" \
    "$STAGE/usr/share/nuxel" "$STAGE/usr/lib/nuxel" "$STAGE/usr/bin" \
    "$STAGE/etc/systemd/system/multi-user.target.wants" "$STAGE/etc/nuxel"
cp -a /nuxel/configs/s10plus/. "$STAGE/etc/nuxel/device/s10plus/"
install -m 0644 /nuxel/device/s10plus/nuxel-beyond2lte.conf "$STAGE/etc/nuxel/nuxel-beyond2lte.conf"
install -m 0644 /nuxel/device/s10plus/90-nuxel-beyond2lte.rules "$STAGE/etc/udev/rules.d/90-nuxel-beyond2lte.rules"
# The launcher is a PWA whose index.html imports `../nuxel-common/bridge.js`
# (pwa/nuxel-common/verify-wiring.js enforces it) and whose application registry
# (pwa/nuxel-home/js/apps.js) addresses the web apps as /pwa/nuxel-apps/... .
# The VM's services/nuxel-web.service therefore serves the REPOSITORY ROOT and the
# launcher URL is /pwa/nuxel-home/index.html.  Staging only pwa/nuxel-home (the
# A25..A29a behaviour) 404'd both the page and the bridge module on the handset
# (measured A29b) and left the WebKit view blank.  So the whole pwa/ tree is
# staged, and the old flat path stays as a symlink for the legacy consumers
# (verify-fedora-phone-rootfs.py checks /usr/share/nuxel/nuxel-home/index.html).
cp -a /nuxel/pwa "$STAGE/usr/share/nuxel/pwa"
ln -sfn pwa/nuxel-home "$STAGE/usr/share/nuxel/nuxel-home"
install -m 0755 /nuxel/tools/s10plus/nuxel-fb-phone-aarch64 "$STAGE/usr/bin/nuxel-fb-phone"
install -m 0644 /nuxel/assets/nuxel-background.png "$STAGE/usr/share/nuxel/nuxel-background.png"
# The launcher stylesheet (css/style.css:60) references
# ../assets/nuxel-background.png RELATIVE TO css/, i.e.
# pwa/nuxel-home/assets/nuxel-background.png.  That per-app copy is git-ignored
# (single-sourced in assets/, normally placed by tools/dedupe-assets.sh) and the
# A25..A29 staging never created it, so the handset rendered with no wallpaper
# (measured: HTTP 404 for that path, A31).  Stage it explicitly for the home PWA
# and for every PWA app, and keep the canonical path for legacy consumers.
for _d in "$STAGE/usr/share/nuxel/pwa/nuxel-home" \
          "$STAGE/usr/share/nuxel/pwa/nuxel-apps/calendar" \
          "$STAGE/usr/share/nuxel/pwa/nuxel-apps/camera-gallery" \
          "$STAGE/usr/share/nuxel/pwa/nuxel-apps/files" \
          "$STAGE/usr/share/nuxel/pwa/nuxel-apps/mail" \
          "$STAGE/usr/share/nuxel/pwa/nuxel-apps/notes"; do
  [ -d "$_d" ] || continue
  install -d "$_d/assets"
  install -m 0644 /nuxel/assets/nuxel-background.png "$_d/assets/nuxel-background.png"
done
# --- A29: the UTM launcher port (Wayland-only; /dev/fb0 output bridge) -------
# The launcher itself is not rebuilt here: pwa/nuxel-home is already staged above
# and the binaries below only carry it (display host + bridge + touch arming).
# See docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/A29-PORT-RECORD.md.
install -d "$STAGE/etc/nuxel" "$STAGE/usr/lib/nuxel"
# A31 is the shipped revision: single-owner framebuffer handoff, boot-animation
# ownership signal for the launcher, capability-aware WebKit permissions, web
# process supervision, and the libinput path shim that gives phoc the real
# touchscreen on a kernel with no VT and no usable udev daemon.
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-touch-arm "$STAGE/usr/lib/nuxel/nuxel-touch-arm"
# A32 is the shipped revision (beta hardware finalizer): explicit XRGB8888 ->
# DECON ABGR_8888 colour conversion in the display bridge, minimum-full-animation
# hand-off gate, screen off/on control FIFO, the launcher host API (settings /
# logical actions / real PTY terminal) with stale-frontend invalidation, and the
# hardware-button manager (power short = display toggle, volume = real ALSA mixer,
# assistant/Bixby key = Nuxel Terminal, remappable in Settings).
for _b in /nuxel/build/out/s10plus/a32/nuxel-wl-fb \
          /nuxel/build/out/s10plus/a32/nuxel-pwa-host \
          /nuxel/build/out/s10plus/a32/nuxel-button-manager \
          /nuxel/build/out/s10plus/a32/libnuxel-libinput-path.so; do
  [ -f "$_b" ] || { echo "ERROR: missing A32 artifact $_b - run tools/s10plus/a32/build-a32.sh (builds on the live UTM VM) before building this image" >&2; exit 1; }
done
install -m 0755 /nuxel/build/out/s10plus/a32/nuxel-wl-fb              "$STAGE/usr/lib/nuxel/nuxel-wl-fb"
install -m 0755 /nuxel/build/out/s10plus/a32/nuxel-pwa-host           "$STAGE/usr/lib/nuxel/nuxel-pwa-host"
install -m 0755 /nuxel/build/out/s10plus/a32/nuxel-button-manager     "$STAGE/usr/lib/nuxel/nuxel-button-manager"
install -m 0755 /nuxel/build/out/s10plus/a32/libnuxel-libinput-path.so "$STAGE/usr/lib/nuxel/libnuxel-libinput-path.so"
# console control for the same configuration the Settings app uses
install -m 0755 /nuxel/tools/s10plus/a32/nuxelctl                     "$STAGE/usr/bin/nuxelctl"
install -m 0644 /nuxel/tools/s10plus/a32/nuxel-button-manager.service \
    "$STAGE/etc/systemd/system/nuxel-button-manager.service"
# default device configuration: the S10+ port starts from its own profile, and a
# full rebuild must reproduce what the live deployment installed
install -d "$STAGE/etc/nuxel/display" "$STAGE/etc/nuxel/input"
install -m 0644 /nuxel/configs/nuxel/statusbar-safezones.json "$STAGE/etc/nuxel/display/statusbar-safezones.json"
install -m 0644 /nuxel/configs/nuxel/buttons.json             "$STAGE/etc/nuxel/input/buttons.json"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-session.sh            "$STAGE/usr/lib/nuxel/nuxel-session.sh"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-wait-wayland          "$STAGE/usr/lib/nuxel/nuxel-wait-wayland"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-launcher-ready-wait.sh "$STAGE/usr/lib/nuxel/nuxel-launcher-ready-wait"
install -m 0644 /nuxel/tools/s10plus/a29/phoc-phone.ini              "$STAGE/etc/nuxel/phoc-phone.ini"
for u in nuxel-touch-arm nuxel-wayland nuxel-wl-fb; do
  install -m 0644 "/nuxel/tools/s10plus/a31/$u.service" "$STAGE/etc/systemd/system/$u.service"
done
install -m 0644 /nuxel/tools/s10plus/a29/nuxel-fallback.service "$STAGE/etc/systemd/system/nuxel-fallback.service"
# The A27 fbdev UI unit must never be a second /dev/fb0 owner on this image:
# /init re-enables it every boot and the initramfs postboot supervisor restarts
# it every 30 s (measured: it took the panel back 9 s after `systemctl stop`).
# The condition makes those starts no-ops while the launcher bridge is installed;
# nuxel-fallback.service still runs /usr/bin/nuxel-ui as the fallback path.
install -Dm0644 /nuxel/tools/s10plus/a29/nuxel-ui-launcher-primary.conf \
    "$STAGE/etc/systemd/system/nuxel-ui.service.d/10-launcher-primary.conf"
# The touchscreen arm is safe to enable on its own (it changes no pixels).
ln -sf ../nuxel-touch-arm.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-touch-arm.service"
# The launcher path is the default screen.  NUXEL_ENABLE_LAUNCHER=0 builds the
# old A27-framebuffer-UI-only image instead.  Verified live on the handset this
# cycle (A29b): NUXEL_HOME_READY for /pwa/nuxel-home/index.html, bridge
# FRAMES_OK ... panel=1440x3040, 217 TOUCH_POINTs delivered from the panel to a
# userspace reader - see UTM-LAUNCHER-PORT/A29-PORT-RECORD.md §6-§8.
if [ "${NUXEL_ENABLE_LAUNCHER:-1}" = "1" ]; then
  for u in nuxel-wayland nuxel-wl-fb nuxel-fallback nuxel-button-manager; do
    ln -sf "../$u.service" "$STAGE/etc/systemd/system/multi-user.target.wants/$u.service"
  done
fi

# A28: the launcher's port record (nuxel-ui.service Documentation= points here)
install -Dm0644 /nuxel/docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/README.md \
    "$STAGE/usr/share/doc/nuxel/UTM-LAUNCHER-PORT.md"
for service in nuxel-bridge nuxel-portal nuxel-notifications; do
  if [[ -d "/nuxel/services/$service/src" ]]; then
    install -d "$STAGE/usr/lib/nuxel/$service"
    cp -a "/nuxel/services/$service/src/." "$STAGE/usr/lib/nuxel/$service/"
  fi
done
install -Dm0644 /nuxel/images/s10plus/nuxel-firstlight.service \
    "$STAGE/etc/systemd/system/nuxel-firstlight.service"
# Diagnostic can run only when the framebuffer node exists; enabling here
# does not enable a graphical Phosh session. It is safe to fail silently.
ln -s ../nuxel-firstlight.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-firstlight.service"
# Fedora systemd is a real OS boot, but needs compatible kernel cgroups,
# SELinux settings, devtmpfs, GPU and input drivers. Do not force Phosh
# autostart when on-device DRM/session support hasn't been established.
ln -sfn /usr/lib/systemd/system/multi-user.target "$STAGE/etc/systemd/system/default.target"
# Fedora /sbin/init is usually a symlink to systemd from the systemd RPM.
# Verify it below, do not fabricate one if the RPM installation omitted it.
[[ -e "$STAGE/sbin/init" ]] || { echo 'ERROR: missing Fedora /sbin/init' >&2; exit 1; }
# User for later phone session; login locked until recovery path established.
chroot "$STAGE" /usr/sbin/useradd -m -s /bin/bash nuxel
mkdir -p "$STAGE/etc/nuxel"
cat > "$STAGE/etc/nuxel/phone-runtime-status" <<'STATUS'
NUXEL_DEVICE=s10plus
NUXEL_CODENAME=beyond2lte
BASE_OS=fedora-43-aarch64
INIT_SYSTEM=systemd
PYTHON3=RPM-installed
PHOSH=RPM-installed
PHOC=RPM-installed
GRAPHICAL_PHONE_SESSION=not-enabled-until-on-device-drm-testing
MOTOROLA_OVERLAY=absent
HARDWARE_BOOT_VERIFIED=false
DISPLAY_DRIVER_VERIFIED=false
STATUS
# No proprietary vendor blobs are silently invented. They require a
# legitimate device-specific source and matching Samsung kernel modules.
[[ ! -e "$STAGE/etc/nuxel/device/g7power" ]] || { echo 'ERROR: g7power overlay included' >&2; exit 1; }
# --- A26: Fedora-on-Linux-4.14 compatibility repairs -------------------------
# Without these the Fedora systemd boot graph NEVER completes on the Exynos 9820
# (measured live; see docs/s10plus-autonomous-boot-repair/A26-SYSTEMD-BOOT-GRAPH-FIX.md):
#   * userdbd/dbus-broker cannot run (sd-event child watching is ENOSYS on 4.14)
#   * nsswitch's "systemd" module turns every user/group lookup into a varlink
#     call that hangs forever when userdbd is absent
#   * systemd-udevd cannot register workers, so it forks unboundedly
# Applied to the STAGING tree, so the shipped image needs no live fix.
bash /nuxel/tools/s10plus/a26/nuxel-rootfs-fixes.sh --root "$STAGE"
python3 /nuxel/tools/s10plus/verify-fedora-phone-rootfs.py --staging "$STAGE"
# Disk size must fit installed runtime before building; fail rather than truncate.
USED_KB="$(du -sk "$STAGE" | awk '{print $1}')"
if (( USED_KB + 512*1024 > MB*1024 )); then
  echo "ERROR: Fedora staging $(($USED_KB/1024)) MiB exceeds ${MB} MiB budget with 512 MiB slack" >&2
  exit 1
fi
truncate -s "${MB}M" "$OUT"
mkfs.ext4 -q -F -L nuxel-beyond2lte -d "$STAGE" "$OUT"
# e2fsck -fn should exit 0 for a correct freshly-made filesystem.
e2fsck -fn "$OUT"
python3 /nuxel/tools/s10plus/verify-fedora-phone-rootfs.py --ext4 "$OUT"
sha256sum "$OUT" > "${OUT}.sha256"
echo "[nuxel] Fedora 43 aarch64 phone rootfs packaged: $OUT"
