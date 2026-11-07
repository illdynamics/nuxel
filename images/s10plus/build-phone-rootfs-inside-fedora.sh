#!/bin/bash
# Executed inside docker --platform linux/arm64 fedora:43, not on macOS.
set -Eeuo pipefail
# PWNAGE-60000: release images require the pinned kbase GPU set.  A developer
# image may opt into a software fallback explicitly with NUXEL_REQUIRE_KBASE=0.
GPU_REQUIRED="${NUXEL_REQUIRE_KBASE:-0}"
[ "${NUXEL_RELEASE:-0}" = "1" ] && GPU_REQUIRED=1
GPU_MANIFEST="${NUXEL_GPU_MANIFEST:-/nuxel/release/s10plus/gpu/gpu-manifest.json}"
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
# PWNAGE-54000: nuxel-contacts / nuxel-messages / nuxel-dialer are compiled
# from repo sources into the image and need the GTK4 + libadwaita headers.
dnf -y install e2fsprogs findutils coreutils file rpm shadow-utils acl python3 python3-pillow \
    gcc make pkgconf-pkg-config kernel-headers \
    wayland-devel wayland-protocols-devel \
    gtk3-devel webkit2gtk4.1-devel alsa-lib-devel git openssl \
    gtk4-devel libadwaita-devel
# --- BOTH Fedora 43 aarch64 repositories are REQUIRED (briq-04a) --------------
# The GA "Everything" repo alone is NOT enough and the failure is not cosmetic:
#   * `stevia` / `stevia-phosh-osk-provider` (the phosh on-screen keyboard) do
#     not exist in GA at all, so `dnf install stevia` aborts the whole build;
#   * `systemd-258.11-1.fc43` -- the exact NEVRA the carried kernel-4.14
#     libsystemd-shared patch was built from -- is in `updates` only (GA has
#     `systemd-258-1.fc43`).  Resolving GA's systemd silently drops the 4.14
#     spawn fix, and every unit start goes back to ENOSYS.
# `phosh`/`phoc` are also 0.49.0 in GA and 0.54.0 in updates.
# Explicit, reproducible repo definitions (no dependence on whatever the
# fedora:43 container image happens to ship, and no reliance on container repo
# ids).  DNF reads these through --setopt=reposdir= below.
REPODIR=/tmp/nuxel-repos
mkdir -p "$REPODIR"
GPGKEY=""
for cand in /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-43-primary \
            /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-43 \
            /etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-aarch64; do
  [ -f "$cand" ] && { GPGKEY="$cand"; break; }
done
if [ -n "$GPGKEY" ]; then
  rpm --import "$GPGKEY"
  GPGCHECK=1
else
  echo 'ERROR: Fedora 43 signing key missing; refusing unsigned RPM installation' >&2
  exit 1
fi
for spec in "fedora|$GPGKEY|1" "updates|$GPGKEY|1"; do
  rid="${spec%%|*}"; rest="${spec#*|}"; key="${rest%%|*}"
  case "$rid" in
    fedora)  url='https://dl.fedoraproject.org/pub/fedora/linux/releases/$releasever/Everything/$basearch/os' ;;
    updates) url='https://dl.fedoraproject.org/pub/fedora/linux/updates/$releasever/Everything/$basearch' ;;
  esac
  {
    printf '[%s]\n' "$rid"
    printf 'name=Fedora 43 aarch64 (%s)\n' "$rid"
    printf 'baseurl=%s\n' "$url"
    printf 'enabled=1\n'
    printf 'metadata_expire=6h\n'
    printf 'gpgcheck=%s\n' "$GPGCHECK"
    printf 'repo_gpgcheck=0\n'
    if [ -n "$key" ]; then printf 'gpgkey=file://%s\n' "$key"; fi
  } > "$REPODIR/nuxel-$rid.repo"
done
# Verify the essential package list against REAL repo metadata before installing
# anything.  No --skip-unavailable: a package that does not exist must be seen.
python3 /nuxel/tools/s10plus/a33/verify-packages.py --quiet --report /tmp/nuxel-packages-report.json \
  || { echo 'ERROR: Fedora 43 essential package manifest did not resolve - see /tmp/nuxel-packages-report.json' >&2; exit 1; }
# Required in the target: real binaries and shared libraries, not .desktop shims.
# `basesystem` was RETIRED in Fedora 43 (0 occurrences in GA and updates); the
# real base is `filesystem` + `setup`.  webkit2gtk4.1/gtk3/alsa-lib are the
# RUNTIME libraries nuxel-pwa-host and nuxel-button-manager are linked against;
# seatd is required by services/nuxel-session/systemd/seatd.service.
# NetworkManager-wifi provides the Wi-Fi device plugin; without it NM creates
# wlan0 as a generic unmanaged device even when the BCM/DHD driver and firmware
# have registered a radio. wpa_supplicant is the configured backend and requires
# Fedora's split libnl3 + libnl3-cli runtime; iw and wireless-regdb provide
# truthful scan/regulatory diagnostics and its required regulatory database.
dnf -y --installroot="$STAGE" --releasever=43 --use-host-config \
    --setopt=reposdir="$REPODIR" --setopt=install_weak_deps=False --setopt=tsflags=nodocs install \
    filesystem setup fedora-release glibc glibc-langpack-en \
    bash coreutils util-linux findutils grep sed gawk \
    systemd-258.11-1.fc43 systemd-udev systemd-networkd dbus-broker dbus-daemon \
    python3 python3-dbus python3-gobject phosh phoc stevia stevia-phosh-osk-provider seatd \
    NetworkManager NetworkManager-wifi wpa_supplicant libnl3 libnl3-cli iw wireless-regdb ModemManager geoclue2 geoclue2-demos bluez bluez-deprecated bluez-obexd \
    mesa-dri-drivers mesa-libEGL mesa-libgbm libinput \
    gtk3 webkit2gtk4.1 gtk4 libadwaita glib-networking libproxy \
    pipewire wireplumber pipewire-utils alsa-lib mpg123 mpv \
    polkit nftables upower greetd \
    wlr-randr xrandr \
    iproute procps-ng kmod e2fsprogs acl \
    shadow-utils ca-certificates curl \
    wayvnc wayland-utils xrdp xorgxrdp xorg-x11-server-Xorg xorg-x11-server-Xwayland wtype \
    openbox xterm firefox android-tools openssl \
    gnome-software PackageKit PackageKit-command-not-found lxpolkit xfce-polkit appstream \
    xdg-desktop-portal-gtk xdg-desktop-portal-wlr \
    chocolate-doom freedoom freedoom2 freedoom-freedm
# PWNAGE-47000 BOOT SAFETY: Nuxel runs systemd PID 1 and the initramfs live
# console from a kernel_t context.  The graphical remote-access packages
# (xrdp/xorgxrdp/tigervnc-selinux) pull in selinux-policy-targeted as a weak
# dependency; when that policy is loaded in enforcing mode, PID 1 cannot exec
# journald/udevd and the phone loops on the boot animation forever (measured on
# 2026-10-31).  Nuxel is documented as "SELinux not enabled by default", so pin
# the shipped image to disabled after the package transaction.  This is a
# rootfs configuration file, not a kernel argument; no bootloader change.
install -d "$STAGE/etc/selinux"
printf 'SELINUX=permissive\nSELINUXTYPE=targeted\n' > "$STAGE/etc/selinux/config"
chmod 0644 "$STAGE/etc/selinux/config"
grep -qx 'SELINUX=permissive' "$STAGE/etc/selinux/config" || {
  echo 'ERROR: SELinux guard failed to disable policy loading' >&2
  exit 1
}
# A newly installed policy must never be able to turn enforcement back on via a
# preset/autorelabel path.  The config above is authoritative for systemd.
rm -f "$STAGE/.autorelabel" 2>/dev/null || true

# The pinned systemd must be what actually landed, or the carried 4.14
# libsystemd-shared patch and the installed binaries do not line up.
INSTALLED_SYSTEMD="$(rpm --root "$STAGE" -q systemd)"
case "$INSTALLED_SYSTEMD" in
  systemd-258.11-1.fc43*) echo "[nuxel] systemd pin OK: $INSTALLED_SYSTEMD" ;;
  *) echo "ERROR: installed $INSTALLED_SYSTEMD, expected systemd-258.11-1.fc43 (carried 4.14 libsystemd patch)" >&2; exit 1 ;;
esac
# PWNAGE-31000: the pre-lockscreen controller invokes mpv by absolute path.  It
# must exist in a freshly built image, not only on a handset where a previous
# live session installed it.  The image is built with weak deps disabled, so
# this is the same lean FFmpeg-free chain measured on the phone (A72).
test -x "$STAGE/usr/bin/mpv" || {
  echo "ERROR: mpv is absent from the built rootfs; preload cinema cannot decode the supplied H.264 clip" >&2
  exit 1
}
# --- current S10+ userspace binaries (A34 TOUCHDOWN) -----------------------
# Build the exact binaries the handset runs from the repository sources *inside
# this arm64 container*.  Earlier builders copied build/out/s10plus/a32/*,
# which only exists on a developer machine; a clean CI checkout has none, and
# those A32 binaries are not the current A34 display/button code.  Everything
# below is compiled natively for aarch64 here, so the release image is
# reproducible from a fresh clone.
B=/tmp/nuxel-current-userspace
mkdir -p "$B"
# The A34 display bridge includes the shared A33 handoff decision header.  Keep
# this repo source path explicit: the clean CI checkout must compile the same
# bridge that is staged onto the handset, without depending on a developer's
# generated include tree.
CFLAGS_COMMON="-O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 -I$B -I/nuxel/tools/s10plus/a33"
wayland-scanner client-header \
    /nuxel/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml \
    "$B/wlr-screencopy-unstable-v1-client-protocol.h"
wayland-scanner private-code \
    /nuxel/tools/s10plus/a29/wlr-screencopy-unstable-v1.xml \
    "$B/wlr-screencopy-unstable-v1-protocol.c"

# A35-patched A34 bridge: frame-by-frame DECON PAN commits, real AMOLED blank,
# automatic first-frame presentation at boot, and current handoff/colour path.
# PWNAGE-53000: A67 bridge (adaptive idle capture + NEON 2x blit) is the
# active source.  The A34 file is kept for history only.
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-wl-fb" /nuxel/tools/s10plus/a67/nuxel-wl-fb.c \
    "$B/wlr-screencopy-unstable-v1-protocol.c" \
    $(pkg-config --libs wayland-client)

# A34 screencopy diagnostic (deployed as /usr/local/bin/nuxel-wl-snapshot).
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-wl-snapshot" /nuxel/tools/s10plus/a34/nuxel-wl-snapshot.c \
    "$B/wlr-screencopy-unstable-v1-protocol.c" \
    $(pkg-config --libs wayland-client)

# PWNAGE-44000: the A45 PWA host executes SHOT_BIN=/usr/lib/nuxel/nuxel-screenshot
# with one argument (destination PPM).  The A68 helper has exactly that contract
# and bounded screencopy waits, so compile it from source and install it at the
# path the host actually uses.  It is a Wayland screencopy client, never a
# framebuffer writer.
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-screenshot" /nuxel/tools/s10plus/a68/nuxel-screenshot.c \
    "$B/wlr-screencopy-unstable-v1-protocol.c" \
    $(pkg-config --libs wayland-client)

# A45 PWA host: the current terminal-window close + host-action fixes, the
# lockscreen/navdock actions, and the lockhead indicator reader (sysfs + /proc,
# with an event-driven uevent refresh).  The source is deliberately compiled from
# tools/s10plus/a45 so the image and the live deployment cannot drift.
gcc $CFLAGS_COMMON $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) \
    -I /nuxel/tools/s10plus/a45 -I /nuxel/tools/s10plus/a33 -o "$B/nuxel-pwa-host" \
    /nuxel/tools/s10plus/a45/nuxel-pwa-host.c \
    $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) -lutil

# PWNAGE-54000: the three GTK4/libadwaita phone apps are built from the
# repository source, not copied from a developer machine.  They share the
# dependency-free nuxel-phone-data layer and are installed into the image.
mkdir -p "$B/native-apps"
for _app in nuxel-contacts nuxel-messages nuxel-dialer; do
  gcc -O2 -Wall -Wextra -Wno-unused-parameter -std=gnu11 \
      $(pkg-config --cflags gtk4 libadwaita-1) \
      -I /nuxel/shell/nuxel-shell/nuxel-phone-data \
      -o "$B/native-apps/$_app" \
      "/nuxel/shell/nuxel-shell/$_app/main.c" \
      /nuxel/shell/nuxel-shell/nuxel-phone-data/nuxel-phone-data.c \
      $(pkg-config --libs gtk4 libadwaita-1)
  test -x "$B/native-apps/$_app" || { echo "ERROR: native app $_app missing" >&2; exit 1; }
done

# PWNAGE-43000/50000: persistent nav dock + native OSD + foreign-toplevel
# controller.  All are built from the same sources the handset runs.
cp -a /nuxel/tools/s10plus/a45 "$B/a45"
NUXEL_NAVDOCK_SKIP_FALLBACK=1 python3 "$B/a45/gen-navdock-art.py"
wayland-scanner client-header \
    /nuxel/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml \
    "$B/wlr-layer-shell-unstable-v1-client-protocol.h"
wayland-scanner private-code \
    /nuxel/tools/s10plus/a45/wlr-layer-shell-unstable-v1.xml \
    "$B/wlr-layer-shell-unstable-v1-protocol.c"
wayland-scanner client-header /nuxel/tools/s10plus/a45/xdg-shell.xml "$B/xdg-shell-client-protocol.h"
wayland-scanner private-code  /nuxel/tools/s10plus/a45/xdg-shell.xml "$B/xdg-shell-protocol.c"
gcc $CFLAGS_COMMON -I "$B/a45" $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-navdock" "$B/a45/nuxel-navdock.c" \
    "$B/wlr-layer-shell-unstable-v1-protocol.c" "$B/xdg-shell-protocol.c" \
    $(pkg-config --libs wayland-client)
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client cairo pangocairo) \
    -o "$B/nuxel-statusbar" /nuxel/tools/s10plus/a45/nuxel-statusbar.c \
    "$B/wlr-layer-shell-unstable-v1-protocol.c" "$B/xdg-shell-protocol.c" \
    $(pkg-config --libs wayland-client cairo pangocairo)
# Native OSD survives a fullscreen native toplevel.  Reads the same
# /usr/share/nuxel/runtime/osd.json the PWA OSD used.
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client cairo pangocairo) \
    -o "$B/nuxel-osd" /nuxel/tools/s10plus/a45/nuxel-osd.c \
    "$B/wlr-layer-shell-unstable-v1-protocol.c" "$B/xdg-shell-protocol.c" \
    $(pkg-config --libs wayland-client cairo pangocairo)
gcc $CFLAGS_COMMON -o "$B/nuxel-foreign-toplevel" /nuxel/tools/s10plus/a59/nuxel-foreign-toplevel.c -ldl

# PWNAGE-50000 graphics probes.  They are diagnostics only and are built when
# the image build has the development headers; absence is not a boot failure.
if pkg-config --exists egl glesv2 wayland-client wayland-egl; then
  gcc $CFLAGS_COMMON -o "$B/nuxel-wayland-egl-probe" \
      /nuxel/tools/s10plus/a67/nuxel-wayland-egl-probe.c \
      $(pkg-config --cflags --libs egl glesv2 wayland-client wayland-egl) || true
fi
if ! gcc $CFLAGS_COMMON -o "$B/nuxel-kbase-egl-probe" \
    /nuxel/tools/s10plus/a67/nuxel-kbase-egl-probe.c \
    $(pkg-config --cflags --libs egl glesv2); then
  [ "$GPU_REQUIRED" = 1 ] && { echo "ERROR: required kbase EGL probe failed to build" >&2; exit 1; }
  rm -f "$B/nuxel-kbase-egl-probe"
fi
if pkg-config --exists gtk+-3.0 epoxy; then
  gcc $CFLAGS_COMMON $(pkg-config --cflags gtk+-3.0 epoxy) \
      -o "$B/nuxel-gtk3-gl-probe" /nuxel/tools/s10plus/a67/nuxel-gtk3-gl-probe.c \
      $(pkg-config --libs gtk+-3.0 epoxy) || true
fi
if pkg-config --exists gtk4; then
  gcc $CFLAGS_COMMON $(pkg-config --cflags gtk4) \
      -o "$B/nuxel-gtk4-gsk-probe" /nuxel/tools/s10plus/a67/nuxel-gtk4-gsk-probe.c \
      $(pkg-config --libs gtk4) || true
fi
if pkg-config --exists gtk+-3.0 webkit2gtk-4.1; then
  gcc $CFLAGS_COMMON $(pkg-config --cflags gtk+-3.0 webkit2gtk-4.1) \
      -o "$B/nuxel-webkit-probe" /nuxel/tools/s10plus/a67/nuxel-webkit-probe.c \
      $(pkg-config --libs gtk+-3.0 webkit2gtk-4.1) || true
fi

# A45 button manager: SYN_REPORT touch translation, power menu, Bixby cancel,
# PipeWire absolute volume steps and the central-sound cue fast path.  The
# shared FSM header remains in a34; compiling the old a34 source here silently
# dropped all owner-facing volume fixes from fresh images.
gcc $CFLAGS_COMMON $(pkg-config --cflags alsa) -I /nuxel/tools/s10plus/a34 \
    -o "$B/nuxel-button-manager" \
    /nuxel/tools/s10plus/a45/nuxel-button-manager.c \
    $(pkg-config --libs alsa)

# Minimal-latency soundd client (C, not the slower Python fallback).  The
# volume key path and clock scheduler both depend on this exact binary.
gcc -O2 -Wall -Wextra -Werror -std=gnu11 \
    -o "$B/nuxel-soundctl" /nuxel/services/nuxel-sound/nuxel-soundctl.c

# Current capability-based libinput path shim for the 4.14/udevd-less kernel.
gcc $CFLAGS_COMMON -shared -fPIC -o "$B/libnuxel-libinput-path.so" \
    /nuxel/tools/s10plus/a33/nuxel-libinput-path.c -ldl

# A40/A44 socket-activated Home hardware monitor. The live phone runs this
# collector; a fresh release image must build and install the same source, not
# depend on a previously deployed binary.
gcc -std=c11 -O2 -Wall -Wextra -Werror -o "$B/nuxel-metricsd" \
    /nuxel/services/nuxel-metrics/nuxel-metricsd.c

for _b in nuxel-wl-fb nuxel-wl-snapshot nuxel-screenshot nuxel-pwa-host \
          nuxel-button-manager nuxel-soundctl libnuxel-libinput-path.so \
          nuxel-metricsd nuxel-navdock nuxel-statusbar nuxel-osd \
          nuxel-foreign-toplevel; do
  file "$B/$_b" | grep -q 'ARM aarch64' || { echo "ERROR: $_b is not aarch64" >&2; exit 1; }
done
sha256sum "$B"/nuxel-wl-fb "$B"/nuxel-wl-snapshot "$B"/nuxel-screenshot "$B"/nuxel-pwa-host \
          "$B"/nuxel-button-manager "$B"/nuxel-soundctl \
          "$B"/libnuxel-libinput-path.so "$B"/nuxel-metricsd "$B"/nuxel-navdock \
          "$B"/nuxel-statusbar "$B"/nuxel-osd "$B"/nuxel-foreign-toplevel \
  | tee /tmp/nuxel-current-userspace.sha256

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
# Root-relative /assets URLs used by launcher icons, Quick Settings and
# navigation images must exist in the STATIC WEBROOT, not just in the repo.
# Also stage the owner's real MP3 audio cues (no synthetic substitutes).
install -d "$STAGE/usr/share/nuxel/assets" "$STAGE/usr/share/nuxel/boot" \
    "$STAGE/usr/share/nuxel/preload"
cp -a /nuxel/assets/. "$STAGE/usr/share/nuxel/assets/"
# Native application artwork used by Home (Firefox/VLC/GNOME apps) is part of
# the runtime asset tree, not a build-only input.
if [ -d /nuxel/assets/native-app-icons ]; then
  cp -a /nuxel/assets/native-app-icons "$STAGE/usr/share/nuxel/assets/"
fi
# PWNAGE-31000: the supplied pre-lockscreen clip is a runtime asset, not an
# initramfs or boot-partition payload.  It is installed only when the owner has
# supplied it; the controller's missing-asset path is the safe fallback.
if [ -s /nuxel/assets/nuxel-preloading-screen.mp4 ]; then
  install -m 0644 /nuxel/assets/nuxel-preloading-screen.mp4 \
    "$STAGE/usr/share/nuxel/preload/nuxel-preloading-screen.mp4"
  # The asset also arrived via the broad assets/ copy into the static webroot;
  # the preload clip is a boot asset, not a PWA asset.  Remove that duplicate so
  # the image carries one verified copy (7.3 MB, not 14.6 MB).
  rm -f "$STAGE/usr/share/nuxel/assets/nuxel-preloading-screen.mp4"
  _preload_sha="$(sha256sum "$STAGE/usr/share/nuxel/preload/nuxel-preloading-screen.mp4" | cut -d' ' -f1)"
  _preload_want="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("asset_sha256") or "")' \
    /nuxel/configs/nuxel/boot/preload-cinema.json)"
  if [ -n "$_preload_want" ] && [ "$_preload_sha" != "$_preload_want" ]; then
    echo "ERROR: nuxel-preloading-screen.mp4 sha256 $_preload_sha != configured $_preload_want" >&2
    exit 1
  fi
  printf '%s  %s\n' "$_preload_sha" nuxel-preloading-screen.mp4 \
    > "$STAGE/usr/share/nuxel/preload/nuxel-preloading-screen.mp4.sha256"
  echo "[nuxel] preload cinema asset sha256 OK: $_preload_sha"
else
  echo "[nuxel] WARN assets/nuxel-preloading-screen.mp4 absent: preload cinema will fall back to lockscreen" >&2
fi
for _cue in nuxel-boot-audio.mp3 nuxel-pow.mp3; do
  test -s "$STAGE/usr/share/nuxel/assets/$_cue" || { echo "ERROR: missing cue $_cue" >&2; exit 1; }
done
install -Dm0755 /nuxel/tools/s10plus/a33/nuxel-sound-cue.py \
    "$STAGE/usr/libexec/nuxel/nuxel-sound-cue"
install -Dm0755 /nuxel/services/nuxel-sound/nuxel-soundd.py \
    "$STAGE/usr/libexec/nuxel/nuxel-soundd"
install -Dm0755 "$B/nuxel-soundctl" "$STAGE/usr/libexec/nuxel/nuxel-soundctl"
install -Dm0755 /nuxel/services/nuxel-sound/install-sound-library.sh \
    "$STAGE/usr/libexec/nuxel/install-sound-library"
install -Dm0755 /nuxel/services/nuxel-clock/nuxel-clockd.py \
    "$STAGE/usr/libexec/nuxel/nuxel-clockd"
install -Dm0644 /nuxel/services/nuxel-sound/nuxel-soundd.service \
    "$STAGE/etc/systemd/system/nuxel-soundd.service"
install -Dm0644 /nuxel/services/nuxel-clock/nuxel-clockd.service \
    "$STAGE/etc/systemd/system/nuxel-clockd.service"
install -Dm0644 /nuxel/services/nuxel-session/systemd/nuxel-boot-sound.service \
    "$STAGE/etc/systemd/system/nuxel-boot-sound.service"
ln -sf ../nuxel-soundd.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-soundd.service"
ln -sf ../nuxel-clockd.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-clockd.service"
# A40/A44 metrics daemon + socket activation. This is the same collector the
# live userspace reports through /metrics; without it a fresh image would lose
# the CPU/MEM/GPU/VRAM meters.
install -Dm0755 "$B/nuxel-metricsd" "$STAGE/usr/lib/nuxel/nuxel-metricsd"
install -Dm0644 /nuxel/services/nuxel-metrics/nuxel-metrics.service \
    "$STAGE/etc/systemd/system/nuxel-metrics.service"
install -Dm0644 /nuxel/services/nuxel-metrics/nuxel-metrics.socket \
    "$STAGE/etc/systemd/system/nuxel-metrics.socket"
install -d "$STAGE/etc/systemd/system/sockets.target.wants"
ln -sf ../nuxel-metrics.socket \
    "$STAGE/etc/systemd/system/sockets.target.wants/nuxel-metrics.socket"
# PWNAGE-58000: the idle/wakeup tuning that was committed in 794c879 is now
# part of the shipped image, not just the repository.  Three separate pieces:
#   1. the one-shot nuxel-perf-tune.service (I/O scheduler + dirty writeback +
#      swappiness; userspace-only and reversible on the next boot);
#   2. the journald drop-in that bounds the vendor kernel's driver-log volume on
#      a phone-sized rootfs;
#   3. a multi-user.target wants symlink so a fresh image actually enables 1.
# The build text itself is the boot-graph contract: verify-service-graph.py
# asserts the install and enablement lines, and verify-fedora-phone-rootfs.py
# proves the packaged bytes match these exact repository sources.
install -d "$STAGE/etc/systemd/journald.conf.d"
install -m 0755 /nuxel/services/nuxel-performance/bin/nuxel-perf-tune.sh \
    "$STAGE/usr/lib/nuxel/nuxel-perf-tune.sh"
install -m 0644 /nuxel/services/nuxel-performance/systemd/nuxel-perf-tune.service \
    "$STAGE/etc/systemd/system/nuxel-perf-tune.service"
install -m 0644 /nuxel/configs/nuxel/performance/journald.conf \
    "$STAGE/etc/systemd/journald.conf.d/50-nuxel-performance.conf"
ln -sf ../nuxel-perf-tune.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-perf-tune.service"
# Package the already-existing haptics implementation and preferences. Do NOT
# enable an additional vibrator owner automatically: the older haptics bridge
# may already own the device on live phones. Physical owner test is required.
install -Dm0644 /nuxel/configs/nuxel/haptics/settings.json \
    "$STAGE/etc/nuxel/haptics/settings.json"
install -Dm0755 /nuxel/services/nuxel-haptics/nuxel-hapticsd.py \
    "$STAGE/usr/lib/nuxel/nuxel-hapticsd.py"
install -Dm0644 /nuxel/services/nuxel-haptics/nuxel-haptics.service \
    "$STAGE/etc/systemd/system/nuxel-haptics.service"
install -Dm0755 /nuxel/services/nuxel-haptics/nuxel-haptics-sleep \
    "$STAGE/usr/libexec/nuxel/nuxel-haptics-sleep"
# PWNAGE-89000: the boot cue is triggered by nuxel-boot-sound.path only
# after /run/nuxel-audio-route.ready exists.  It must not be a direct boot want.
install -d "$STAGE/etc/systemd/system/paths.target.wants"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-boot-sound.path \
    "$STAGE/etc/systemd/system/nuxel-boot-sound.path"
ln -sf ../nuxel-boot-sound.path \
    "$STAGE/etc/systemd/system/paths.target.wants/nuxel-boot-sound.path"
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
# A34 is the shipped revision (TOUCHDOWN): the A35-patched A34 display
# bridge (per-frame PAN + powerdown), the A34 button manager (SYN_REPORT touch translation,
# 11-entry power menu with Cancel first, deferred Bixby cancelled by Power) and
# the current PWA host (terminal surface close + host action fixes).  All were
# built from repository sources above, not copied from a developer's build tree.
install -m 0755 "$B/nuxel-wl-fb"               "$STAGE/usr/lib/nuxel/nuxel-wl-fb"
install -m 0755 "$B/nuxel-pwa-host"            "$STAGE/usr/lib/nuxel/nuxel-pwa-host"
for _app in nuxel-contacts nuxel-messages nuxel-dialer; do
  install -m 0755 "$B/native-apps/$_app" "$STAGE/usr/bin/$_app"
done
install -m 0755 "$B/nuxel-button-manager"      "$STAGE/usr/lib/nuxel/nuxel-button-manager"
install -m 0755 "$B/libnuxel-libinput-path.so" "$STAGE/usr/lib/nuxel/libnuxel-libinput-path.so"
install -d "$STAGE/usr/local/bin"
install -m 0755 "$B/nuxel-wl-snapshot"         "$STAGE/usr/local/bin/nuxel-wl-snapshot"
install -m 0755 "$B/nuxel-screenshot"          "$STAGE/usr/lib/nuxel/nuxel-screenshot"
# console control for the same configuration the Settings app uses
install -m 0755 /nuxel/tools/s10plus/a32/nuxelctl                     "$STAGE/usr/bin/nuxelctl"
# --- PWNAGE-46000: one orientation owner + policy + presenter contract ------
# Bridge, Settings and Quick Settings all exec /usr/libexec/nuxel/nuxel-orientationd.
# Install the daemon and its importable package together, at the exact path the
# Bridge uses.  A clean image must never silently omit this feature again.
install -d "$STAGE/usr/libexec/nuxel/nuxel_orientation"            "$STAGE/etc/nuxel/orientation"            "$STAGE/var/lib/nuxel/orientation"
install -m 0755 /nuxel/services/nuxel-orientation/nuxel-orientationd     "$STAGE/usr/libexec/nuxel/nuxel-orientationd"
for _of in __init__.py policy.py sensors.py apply.py; do
  install -m 0644 "/nuxel/services/nuxel-orientation/nuxel_orientation/$_of"       "$STAGE/usr/libexec/nuxel/nuxel_orientation/$_of"
done
install -m 0644 /nuxel/configs/nuxel/orientation/orientation.json     "$STAGE/etc/nuxel/orientation/orientation.json"
install -m 0644 /nuxel/configs/nuxel/orientation/orientation.schema.json     "$STAGE/etc/nuxel/orientation/orientation.schema.json"
install -m 0644 /nuxel/services/nuxel-orientation/systemd/nuxel-orientationd.service     "$STAGE/etc/systemd/system/nuxel-orientationd.service"
install -Dm0644 /nuxel/docs/beta-finalization/live/PWNAGE-46000-TODO.md     "$STAGE/usr/share/doc/nuxel/PWNAGE-46000.md"
install -m 0755 /nuxel/tools/pwnage46000/rotation-notes.py \
    "$STAGE/usr/local/bin/nuxel-rotation-notes"
install -m 0755 /nuxel/services/nuxel-remote-desktop/bin/nuxel-orientation-remote-sync \
    "$STAGE/usr/libexec/nuxel/nuxel-orientation-remote-sync"
# The service imports `nuxel_orientation` from its own directory.  Prove the
# installed copy is importable now, not after boot.
PYTHONPATH="$STAGE/usr/libexec/nuxel" python3 -c     'from nuxel_orientation.policy import SEVEN_MODES, MODE_ORDER; assert len(MODE_ORDER)==7 and len(SEVEN_MODES)==7'
test -x "$STAGE/usr/libexec/nuxel/nuxel-orientationd" || {
  echo "ERROR: orientation daemon missing from rootfs" >&2; exit 1; }
test -f "$STAGE/etc/nuxel/orientation/orientation.json" || {
  echo "ERROR: orientation config missing from rootfs" >&2; exit 1; }
test -f "$STAGE/etc/systemd/system/nuxel-orientationd.service" || {
  echo "ERROR: orientation service unit missing from rootfs" >&2; exit 1; }
# wlr-randr is the actual transform backend used by apply.py.  A rootfs with the
# daemon but without this executable reports "applied: false" forever.
test -x "$STAGE/usr/bin/wlr-randr" || {
  echo "ERROR: wlr-randr missing from rootfs (orientation transform backend)" >&2; exit 1; }
test -x "$STAGE/usr/libexec/nuxel/nuxel-orientation-remote-sync" || {
  echo "ERROR: orientation remote sync helper missing from rootfs" >&2; exit 1; }
for _app in nuxel-contacts nuxel-messages nuxel-dialer; do
  test -x "$STAGE/usr/bin/$_app" || {
    echo "ERROR: native phone app $_app missing from rootfs" >&2; exit 1; }
done
test -f "$STAGE/usr/share/nuxel/pwa/nuxel-apps/clipper/index.html" || {
  echo "ERROR: Clipper app missing from rootfs" >&2; exit 1; }
test -x "$STAGE/usr/bin/xrandr" || {
  echo "ERROR: xrandr missing from rootfs (XRDP geometry probe)" >&2; exit 1; }
# default device configuration: the S10+ port starts from its own profile, and a
# full rebuild must reproduce what the live deployment installed
install -d "$STAGE/etc/nuxel/display" "$STAGE/etc/nuxel/input"
install -m 0644 /nuxel/configs/nuxel/statusbar-safezones.json "$STAGE/etc/nuxel/display/statusbar-safezones.json"
# PWNAGE-52000: UI-only icon visibility.  Never clobber the owner's document on
# a rootfs refresh; the default is installed only when the file is absent.
if [ ! -e "$STAGE/etc/nuxel/display/statusbar-icons.json" ]; then
  install -m 0644 /nuxel/configs/nuxel/display/statusbar-icons.json "$STAGE/etc/nuxel/display/statusbar-icons.json"
fi
install -m 0644 /nuxel/configs/nuxel/buttons.json             "$STAGE/etc/nuxel/input/buttons.json"
install -m 0644 /nuxel/configs/nuxel/input/button-fsm.json    "$STAGE/etc/nuxel/input/button-fsm.json"
install -d "$STAGE/etc/nuxel/buttons" "$STAGE/etc/nuxel/leds" "$STAGE/var/cache/nuxel/thumbnails"
install -m 0644 /nuxel/configs/nuxel/buttons/reboot-gate.json "$STAGE/etc/nuxel/buttons/reboot-gate.json"
install -m 0644 /nuxel/configs/nuxel/leds/leds.json          "$STAGE/etc/nuxel/leds/leds.json"
# PWNAGE-45000: hardware/provider policy + diagnostics + explicit MTP share root.
install -d "$STAGE/etc/nuxel/notifications" "$STAGE/etc/nuxel/nfc" \
           "$STAGE/etc/nuxel/security" "$STAGE/var/lib/nuxel/security" \
           "$STAGE/var/lib/nuxel/notifications" "$STAGE/var/lib/nuxel/leds" \
           "$STAGE/home/nuxel/Shared/Downloads" "$STAGE/home/nuxel/Shared/Pictures" \
           "$STAGE/home/nuxel/Shared/Documents" "$STAGE/home/nuxel/Shared/Music" \
           "$STAGE/home/nuxel/Shared/Videos"
chmod 0700 "$STAGE/var/lib/nuxel/security"
chown -R 1000:1000 "$STAGE/home/nuxel/Shared"
install -d "$STAGE/usr/share/doc/nuxel"
# The notification daemon runs as nuxel-notifications and must be able to
# replace its canonical history file in /var/lib/nuxel without broad writes.
chgrp nuxel-notifications "$STAGE/var/lib/nuxel" 2>/dev/null || true
# 0771 = traverse for the bridge even if a future image tool drops POSIX ACLs;
# the directory is not listable by other users and its children stay 0700/0770.
chmod 0771 "$STAGE/var/lib/nuxel"
install -m 0644 /nuxel/configs/nuxel/notifications/dnd.json "$STAGE/etc/nuxel/notifications/dnd.json"
install -m 0644 /nuxel/configs/nuxel/notifications/README.md "$STAGE/usr/share/doc/nuxel/notifications-policy.md" 2>/dev/null || true
install -m 0644 /nuxel/configs/nuxel/nfc/nfc.json "$STAGE/etc/nuxel/nfc/nfc.json"
install -m 0644 /nuxel/configs/nuxel/nfc/README.md "$STAGE/usr/share/doc/nuxel/nfc.md" 2>/dev/null || true

# PWNAGE-65000: one root-owned NFC service owns /dev/sec-nfc.  It stays
# default-OFF and does not open the controller until an explicit enable/scan.
install -d "$STAGE/usr/lib/nuxel/nuxel-nfc/nuxel_nfc" "$STAGE/usr/libexec/nuxel" \
           "$STAGE/etc/udev/rules.d"
install -m 0644 /nuxel/services/nuxel-nfc/nuxel_nfc/*.py \
    "$STAGE/usr/lib/nuxel/nuxel-nfc/nuxel_nfc/"
install -m 0755 /nuxel/services/nuxel-nfc/nuxel-nfc "$STAGE/usr/libexec/nuxel/nuxel-nfc"
ln -sfn /usr/libexec/nuxel/nuxel-nfc "$STAGE/usr/bin/nuxel-nfc"
install -m 0644 /nuxel/services/nuxel-nfc/systemd/nuxel-nfcd.service \
    "$STAGE/etc/systemd/system/nuxel-nfcd.service"
install -m 0644 /nuxel/services/nuxel-nfc/90-nuxel-nfc.rules \
    "$STAGE/etc/udev/rules.d/90-nuxel-nfc.rules"
ln -sf ../nuxel-nfcd.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-nfcd.service"
test -f "$STAGE/usr/lib/nuxel/nuxel-nfc/nuxel_nfc/daemon.py" || {
  echo 'ERROR: nuxel NFC service missing from staged rootfs' >&2; exit 1; }
# Read-only hardware diagnostics used by Settings > Mobile network / Camera /
# Sensors / NFC / GNSS and the LED pages.  A page whose tool is absent would
# either lie or fail with ENOENT; ship the complete allowlisted set.
install -d "$STAGE/etc/nuxel/modem" "$STAGE/etc/nuxel/camera" \
           "$STAGE/etc/nuxel/sensors" "$STAGE/etc/nuxel/gnss"
for _diag in nfc led modem camera sensors gnss power wifi bluetooth; do
  install -m 0755 "/nuxel/tools/s10plus/a33/nuxel-${_diag}-diag.sh" \
      "$STAGE/usr/local/bin/nuxel-${_diag}-diag.sh"
done
install -m 0644 /nuxel/configs/nuxel/modem/modem.json "$STAGE/etc/nuxel/modem/modem.json"
install -m 0644 /nuxel/configs/nuxel/camera/camera.json "$STAGE/etc/nuxel/camera/camera.json"
# PWNAGE-52000 system privacy gates (never clobber an owner choice).
if [ ! -e "$STAGE/etc/nuxel/security/biometric-unlock.json" ]; then
  install -Dm0644 /nuxel/configs/nuxel/security/biometric-unlock.json "$STAGE/etc/nuxel/security/biometric-unlock.json"
fi
for _priv in camera microphone; do
  if [ ! -e "$STAGE/etc/nuxel/privacy/$_priv.json" ]; then
    install -Dm0644 "/nuxel/configs/nuxel/privacy/$_priv.json" "$STAGE/etc/nuxel/privacy/$_priv.json"
  fi
done
install -m 0644 /nuxel/configs/nuxel/sensors/sensors.json "$STAGE/etc/nuxel/sensors/sensors.json"
install -m 0644 /nuxel/configs/nuxel/gnss/gnss.json "$STAGE/etc/nuxel/gnss/gnss.json"
install -m 0755 /nuxel/tools/s10plus/a45/nuxel-session.sh            "$STAGE/usr/lib/nuxel/nuxel-session.sh"
install -m 0755 /nuxel/tools/s10plus/a67/nuxel-wayland-gpu-wrapper.sh "$STAGE/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh"
# The session hook is only useful if the guard binary is actually installed.
# A clean image previously relied on a previously-provisioned handset copy.
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-gstreamer-guard.sh     "$STAGE/usr/lib/nuxel/nuxel-gstreamer-guard.sh"

# --- PWNAGE-61000: MFC diagnostics and truthful decoder policy -------------
# Installed read-only/inventory-first.  Nothing here starts at boot, login,
# package install or Settings render, and nothing opens /dev/video* by default.
# The helper is optional: a software-only image remains valid without it.
install -d "$STAGE/usr/lib/nuxel" "$STAGE/usr/share/nuxel" "$STAGE/etc/nuxel/mfc"
install -m 0755 /nuxel/tools/s10plus/a61/nuxel-mfc-diag     "$STAGE/usr/lib/nuxel/nuxel-mfc-diag"
install -m 0755 /nuxel/tools/s10plus/a61/nuxel-mfc-play     "$STAGE/usr/lib/nuxel/nuxel-mfc-play"
install -m 0755 /nuxel/tools/s10plus/a61/nuxel-mfc-safety-receipt.py     "$STAGE/usr/lib/nuxel/nuxel-mfc-safety-receipt.py"
install -m 0644 /nuxel/tools/s10plus/a61/mfc-status.schema.json     "$STAGE/usr/share/nuxel/mfc-status.schema.json"
install -m 0644 /nuxel/tools/s10plus/a61/mfc-safety-receipt.template.json     "$STAGE/etc/nuxel/mfc/safety-receipt.template.json"
# The decode helper is a real aarch64 binary, never a shell wrapper around an
# unsafe generic player.  Prefer a prebuilt artifact; otherwise cross-compile
# from the repository source when a toolchain is available.
_mfc_decode_bin="${NUXEL_MFC_DECODE_BIN:-/nuxel/build/pwnage61000/nuxel-mfc-decode}"
if [ ! -x "$_mfc_decode_bin" ] && [ -f /nuxel/tools/s10plus/a61/nuxel-mfc-decode.c ]; then
  if [ "$(uname -m)" = "aarch64" ] && command -v cc >/dev/null 2>&1; then
    cc -O2 -Wall -Wextra -Wno-unused-parameter -Wno-format-truncation       -o /tmp/nuxel-mfc-decode /nuxel/tools/s10plus/a61/nuxel-mfc-decode.c       && _mfc_decode_bin=/tmp/nuxel-mfc-decode
  elif command -v aarch64-linux-gnu-gcc >/dev/null 2>&1; then
    aarch64-linux-gnu-gcc -O2 -Wall -Wextra -Wno-unused-parameter -Wno-format-truncation       -o /tmp/nuxel-mfc-decode /nuxel/tools/s10plus/a61/nuxel-mfc-decode.c       && _mfc_decode_bin=/tmp/nuxel-mfc-decode
  fi
fi
if [ -x "$_mfc_decode_bin" ]; then
  install -m 0755 "$_mfc_decode_bin" "$STAGE/usr/lib/nuxel/nuxel-mfc-decode"
else
  echo "[nuxel] NOTE: nuxel-mfc-decode not built; software-only image remains valid" >&2
fi
# PWNAGE-60000: the PWN36000 boot bootstrap used to overwrite a newer deployed
# session on every boot.  Ship the guarded bootstrap and the same session in
# the stage so a cold boot cannot revert the production graphics policy.
if [ -d "$STAGE/usr/lib/nuxel/stage36000" ]; then
  install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh \
      "$STAGE/usr/lib/nuxel/stage36000/apply-pwnage36000.sh"
  install -Dm0755 /nuxel/tools/s10plus/a45/nuxel-session.sh \
      "$STAGE/usr/lib/nuxel/stage36000/session/nuxel-session.sh"
fi
install -m 0755 /nuxel/tools/s10plus/a67/nuxel-gpu-status             "$STAGE/usr/lib/nuxel/nuxel-gpu-status"
# v0.7.7-beta: native Doom engine comparison entry point (Chocolate/UZDoom/
# Crispy).  Nuxel Doom itself is the WebAssembly engine inside the PWA.
install -m 0755 /nuxel/tools/s10plus/a33/doom-engines/nuxel-doom-engine "$STAGE/usr/lib/nuxel/nuxel-doom-engine"
install -Dm0644 /nuxel/configs/nuxel/portals.conf                      "$STAGE/etc/xdg-desktop-portal/portals.conf"
install -Dm0755 /nuxel/tools/s10plus/a45/nuxel-graphics-profile \
    "$STAGE/usr/lib/nuxel/nuxel-graphics-profile"
install -Dm0644 /nuxel/configs/nuxel/graphics/graphics-profile.json \
    "$STAGE/etc/nuxel/graphics/graphics-profile.json"
if [ -x "$B/nuxel-wayland-egl-probe" ]; then
  install -m 0755 "$B/nuxel-wayland-egl-probe" "$STAGE/usr/lib/nuxel/nuxel-wayland-egl-probe"
fi
if [ -x "$B/nuxel-kbase-egl-probe" ]; then
  install -m 0755 "$B/nuxel-kbase-egl-probe" "$STAGE/usr/lib/nuxel/nuxel-kbase-egl-probe"
fi
for _probe in nuxel-gtk3-gl-probe nuxel-gtk4-gsk-probe nuxel-webkit-probe; do
  if [ -x "$B/$_probe" ]; then
    install -m 0755 "$B/$_probe" "$STAGE/usr/lib/nuxel/$_probe"
  fi
done
if [ -x "$B/nuxel-kbase-egl-probe" ]; then
  install -m 0755 "$B/nuxel-kbase-egl-probe" "$STAGE/usr/lib/nuxel/nuxel-kbase-egl-probe"
elif [ "$GPU_REQUIRED" = 1 ]; then
  echo "ERROR: required kbase EGL probe is missing at $B/nuxel-kbase-egl-probe" >&2
  exit 1
fi

# PWNAGE-51000/53000: the S10+ GPU baseline is the vendor kbase Mali-G76 path,
# NOT a DRM render node.  Install the exact kbase Mesa/wlroots set that runs on
# the handset.  The canonical, hash-pinned copy lives in release/s10plus/gpu
# (recorded from the physical phone); build/out/s10plus/kbase-gpu is only a
# developer rebuild and is used when the canonical copy is absent.
KBASE_GPU=/nuxel/release/s10plus/gpu
if [ "$GPU_REQUIRED" = 1 ]; then
  # Release builds must use the canonical, manifest-pinned set.  Never silently
  # fall back to a developer tree or to stock Mesa/llvmpipe.
  [ -f "$GPU_MANIFEST" ] || { echo "ERROR: GPU manifest missing: $GPU_MANIFEST" >&2; exit 1; }
  [ -f "$KBASE_GPU/SHA256SUMS" ] || { echo "ERROR: $KBASE_GPU/SHA256SUMS missing" >&2; exit 1; }
  ( cd "$KBASE_GPU" && sha256sum -c SHA256SUMS --quiet ) || {
    echo "ERROR: release GPU assets failed SHA-256 verification in $KBASE_GPU" >&2; exit 1; }
else
  [ -f "$KBASE_GPU/libEGL_mesa.so.0.0.0" ] || KBASE_GPU=/nuxel/build/out/s10plus/kbase-gpu/lib
fi
if [ -f "$KBASE_GPU/libEGL_mesa.so.0.0.0" ] && \
   [ -f "$KBASE_GPU/libgallium_dri.so" ] && \
   [ -f "$KBASE_GPU/libwlroots-0.19.so" ]; then
  install -m 0644 "$KBASE_GPU/libEGL_mesa.so.0.0.0" "$STAGE/usr/lib64/libEGL_mesa.so.0.0.0"
  install -m 0755 "$KBASE_GPU/libgallium_dri.so"   "$STAGE/usr/lib64/libgallium_dri.so"
  install -m 0644 "$KBASE_GPU/libwlroots-0.19.so"   "$STAGE/usr/lib64/libwlroots-0.19.so"
  # glvnd vendor file: the canonical dir carries the phone's 50_mesa.json
  # content; the developer tree keeps it one level up.  Never ship a missing
  # file silently - glvnd would then pick the stock (llvmpipe) library.
  for _json in "$KBASE_GPU/50_mesa.json" "$KBASE_GPU/../50_mesa.json"; do
    [ -f "$_json" ] && break
  done
  [ -f "$_json" ] || { echo "ERROR: 50_mesa.json not found under $KBASE_GPU" >&2; exit 1; }
  install -m 0644 "$_json" "$STAGE/usr/share/glvnd/egl_vendor.d/50_mesa.json"
  # PWNAGE-53000/60000: pin the kbase EGL build by absolute path so a Mesa
  # package update cannot silently reset the glvnd symlink to the stock library.
  install -d -m 0755 "$STAGE/etc/nuxel"
  if [ "$GPU_REQUIRED" = 1 ] && [ -f "$KBASE_GPU/egl-kbase.json" ]; then
    install -m 0644 "$KBASE_GPU/egl-kbase.json" "$STAGE/etc/nuxel/egl-kbase.json"
    install -m 0755 "$KBASE_GPU/nuxel-graphics-profile" "$STAGE/usr/lib/nuxel/nuxel-graphics-profile"
    install -Dm0644 "$KBASE_GPU/graphics-profile.json" "$STAGE/etc/nuxel/graphics/graphics-profile.json"
    install -m 0755 "$KBASE_GPU/nuxel-gpu-status" "$STAGE/usr/lib/nuxel/nuxel-gpu-status"
    install -m 0755 "$KBASE_GPU/nuxel-wayland-gpu-wrapper.sh" "$STAGE/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh"
    install -m 0755 "$KBASE_GPU/nuxel-session.sh" "$STAGE/usr/lib/nuxel/nuxel-session.sh"
  else
    printf '{\n  "file_format_version": "1.0.0",\n  "ICD": { "library_path": "/usr/lib64/libEGL_mesa.so.0.0.0" }\n}\n' \
        > "$STAGE/etc/nuxel/egl-kbase.json"
  fi
  ln -sfn libEGL_mesa.so.0.0.0 "$STAGE/usr/lib64/libEGL_mesa.so.0"
  ln -sfn ../libgallium_dri.so "$STAGE/usr/lib64/dri/panfrost_dri.so"
  ln -sfn ../libgallium_dri.so "$STAGE/usr/lib64/dri/exynos_dri.so"
  if [ -f "$GPU_MANIFEST" ]; then
    install -Dm0644 "$GPU_MANIFEST" "$STAGE/usr/share/nuxel/gpu-manifest.json"
    install -Dm0644 "$(dirname "$GPU_MANIFEST")/SHA256SUMS" "$STAGE/usr/share/nuxel/gpu-SHA256SUMS"
  fi
  echo "[nuxel-rootfs] kbase GPU userspace installed (Mali-G76 / Panfrost)"
elif [ "$GPU_REQUIRED" = 1 ]; then
  echo "ERROR: kbase GPU userspace missing at $KBASE_GPU" >&2
  exit 1
else
  echo "WARNING: kbase GPU userspace absent at $KBASE_GPU; image will use software GL" >&2
fi
# Desktop entries for the installed native applications.  pwa/nuxel-common/
# app-registry.json names these files, so a launcher entry can never point at a
# desktop file that the image does not ship.
install -d "$STAGE/usr/share/applications"
for _desk in org.mozilla.firefox org.videolan.VLC org.signal.Signal com.stremio.Stremio \
             org.gnome.FileRoller org.gnome.Loupe org.gnome.Papers org.gnome.SystemMonitor \
             nuxel-software; do
  install -m 0644 "/nuxel/shell/config/$_desk.desktop" "$STAGE/usr/share/applications/$_desk.desktop"
done
install -m 0755 "$B/nuxel-navdock"            "$STAGE/usr/lib/nuxel/nuxel-navdock"
# PWNAGE-62000: the native top bar is now part of the real shell.  It hides on
# Home and while locked, and is shown only over a non-Home native/Flatpak
# toplevel, so it never duplicates Home's DOM bar.
install -m 0755 "$B/nuxel-statusbar"          "$STAGE/usr/lib/nuxel/nuxel-statusbar"
install -m 0755 "$B/nuxel-osd"                "$STAGE/usr/lib/nuxel/nuxel-osd"
install -m 0755 "$B/nuxel-foreign-toplevel"   "$STAGE/usr/lib/nuxel/nuxel-foreign-toplevel"
install -m 0755 /nuxel/tools/s10plus/a45/nuxel-shell-chrome.sh "$STAGE/usr/lib/nuxel/nuxel-shell-chrome.sh"
install -m 0755 /nuxel/tools/s10plus/a45/nuxel-security-lock-rpc "$STAGE/usr/lib/nuxel/nuxel-security-lock-rpc"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-focus-app.sh "$STAGE/usr/lib/nuxel/nuxel-focus-app.sh"
# PWNAGE-40000 pre-play amplifier/DAPM warm-up.  It starts an inaudible 8 s
# stream, repairs the CS35L41 driver cache and waits for DAPM SPEAKER=On so the
# 366 ms boot/volume cue is not swallowed by a cold speaker path.  The raw I2C
# register writer (/usr/local/bin/nuxel-cs35.py) is device-only and deliberately
# absent from a fresh image; the helper degrades to the driver-cache path and
# logs that the raw patch was not applied.
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-audio-warmup "$STAGE/usr/lib/nuxel/nuxel-audio-warmup"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-cs35l41-apply.sh "$STAGE/usr/lib/nuxel/nuxel-cs35l41-apply.sh"
install -m 0644 /nuxel/assets/nuxel-silence-8s.wav "$STAGE/usr/share/nuxel/assets/nuxel-silence-8s.wav"
install -d "$STAGE/etc/systemd/system/nuxel-boot-sound.service.d"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-boot-sound.service.d/20-warmup-keepalive.conf \
    "$STAGE/etc/systemd/system/nuxel-boot-sound.service.d/20-warmup-keepalive.conf"
# PWNAGE-43000 standalone audio + ABOX reload + Wi-Fi/charger policy
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-audio-session.sh "$STAGE/usr/lib/nuxel/nuxel-audio-session.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-abox-firmware-reload.sh "$STAGE/usr/lib/nuxel/nuxel-abox-firmware-reload.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-abox-firmware-reload-boot.sh "$STAGE/usr/lib/nuxel/nuxel-abox-firmware-reload-boot.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-audio-route.sh "$STAGE/usr/lib/nuxel/nuxel-audio-route.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-mic-route.sh "$STAGE/usr/lib/nuxel/nuxel-mic-route.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-wifi-up.sh "$STAGE/usr/lib/nuxel/nuxel-wifi-up.sh"
# Durable interface ON/OFF intent shared by Settings, Quick Settings and the
# boot restore.  Bluetooth/NFC/GNSS default OFF; Wi-Fi keeps NetworkManager as
# its owner and is not re-enabled when the owner persisted it OFF.
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-interface-state "$STAGE/usr/lib/nuxel/nuxel-interface-state"
install -Dm0644 /nuxel/docs/interface-state.md "$STAGE/usr/share/doc/nuxel/interface-state.md"
ln -sfn /usr/lib/nuxel/nuxel-interface-state "$STAGE/usr/local/bin/nuxel-interface-state"
# PWNAGE-52000: the existing boot-mode guard classifies charger/LPM and
# publishes /run/nuxel-bootmode.{state,json}.  It never reboots by itself
# (allow_reboot=false); the one-shot fallback below consumes its state.
install -Dm0755 /nuxel/tools/s10plus/a33/nuxel-bootmode-guard.py "$STAGE/usr/libexec/nuxel/nuxel-bootmode-guard.py"
install -Dm0644 /nuxel/configs/nuxel/touch/nuxel-bootmode-guard.service "$STAGE/etc/systemd/system/nuxel-bootmode-guard.service"
install -Dm0644 /nuxel/configs/nuxel/bootmode/bootmode-guard.json "$STAGE/etc/nuxel/bootmode/bootmode-guard.json"
install -Dm0644 /nuxel/configs/nuxel/touch/bootmode-guard.json "$STAGE/etc/nuxel/touch/bootmode-guard.json"
ln -sf ../nuxel-bootmode-guard.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-bootmode-guard.service"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-charger-mode-recovery.sh "$STAGE/usr/lib/nuxel/nuxel-charger-mode-recovery.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-device-permissions.sh "$STAGE/usr/lib/nuxel/nuxel-device-permissions.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-usb-mode.sh "$STAGE/usr/lib/nuxel/nuxel-usb-mode.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-mtp-server "$STAGE/usr/lib/nuxel/nuxel-mtp-server"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-vlc-fallback "$STAGE/usr/lib/nuxel/nuxel-vlc-fallback"
install -m 0755 /nuxel/services/nuxel-software/nuxel-software "$STAGE/usr/lib/nuxel/nuxel-software"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-gps-status "$STAGE/usr/local/bin/nuxel-gps-status"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-audio-status "$STAGE/usr/local/bin/nuxel-audio-status"
for _w in firefox vlc signal stremio; do
  install -m 0755 "/nuxel/services/nuxel-s10/bin/nuxel-flatpak-$_w" "$STAGE/usr/lib/nuxel/nuxel-flatpak-$_w"
done
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-audio-session.service "$STAGE/etc/systemd/system/nuxel-audio-session.service"
install -d -m 0755 "$STAGE/etc/systemd/system/nuxel-audio-session.service.d"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-audio-session.service.d/10-stop-bound.conf "$STAGE/etc/systemd/system/nuxel-audio-session.service.d/10-stop-bound.conf"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-audio-stop.sh "$STAGE/usr/lib/nuxel/nuxel-audio-stop.sh"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-abox-firmware-reload.service "$STAGE/etc/systemd/system/nuxel-abox-firmware-reload.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-audio-route.service "$STAGE/etc/systemd/system/nuxel-audio-route.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-audio-route-retry.service "$STAGE/etc/systemd/system/nuxel-audio-route-retry.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-audio-route.timer "$STAGE/etc/systemd/system/nuxel-audio-route.timer"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-mic-route.service "$STAGE/etc/systemd/system/nuxel-mic-route.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-mic-route.path "$STAGE/etc/systemd/system/nuxel-mic-route.path"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wifi.service "$STAGE/etc/systemd/system/nuxel-wifi.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-bluetooth.service "$STAGE/etc/systemd/system/nuxel-bluetooth.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-interface-state.service "$STAGE/etc/systemd/system/nuxel-interface-state.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-charger-mode-recovery.service "$STAGE/etc/systemd/system/nuxel-charger-mode-recovery.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-device-permissions.service "$STAGE/etc/systemd/system/nuxel-device-permissions.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-mtp.service "$STAGE/etc/systemd/system/nuxel-mtp.service"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-usb-mode-monitor.service "$STAGE/etc/systemd/system/nuxel-usb-mode-monitor.service"

install -d -m 0755 "$STAGE/etc/systemd/system/nuxel-wl-fb.service.d"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wl-fb.service.d/15-idle-fps.conf "$STAGE/etc/systemd/system/nuxel-wl-fb.service.d/15-idle-fps.conf"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wl-fb.service.d/25-reboot-hold.conf "$STAGE/etc/systemd/system/nuxel-wl-fb.service.d/25-reboot-hold.conf"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-wl-fb-hold.sh "$STAGE/usr/lib/nuxel/nuxel-wl-fb-hold.sh"
install -m 0755 /nuxel/services/nuxel-s10/bin/nuxel-wayland-stop.sh "$STAGE/usr/lib/nuxel/nuxel-wayland-stop.sh"
# PWNAGE-42000: GeoClue2 queues Manager.GetClient until an agent is registered
# for the calling UID.  The agent must run in its own process (the bridge's
# single-threaded D-Bus loop deadlocks on the callback), as the same UID.
install -d "$STAGE/etc/systemd/system/geoclue.service.d"
install -m 0644 /nuxel/services/nuxel-s10/systemd/geoclue.service.d/10-nuxel-network.conf \
    "$STAGE/etc/systemd/system/geoclue.service.d/10-nuxel-network.conf"
install -m 0644 /nuxel/services/nuxel-bridge/systemd/nuxel-geoclue-agent.service \
    "$STAGE/etc/systemd/system/nuxel-geoclue-agent.service"
install -d "$STAGE/etc/systemd/system/nuxel-abox-firmware-reload.service.d" \
           "$STAGE/etc/systemd/system/nuxel-wl-fb.service.d"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-abox-firmware-reload.service.d/10-boot-priority.conf \
    "$STAGE/etc/systemd/system/nuxel-abox-firmware-reload.service.d/10-boot-priority.conf"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wl-fb.service.d/10-display-priority.conf \
    "$STAGE/etc/systemd/system/nuxel-wl-fb.service.d/10-display-priority.conf"
for _svc in nuxel-boot-sound nuxel-bridge nuxel-button-manager nuxel-http-bridge nuxel-touch-arm nuxel-web nuxel-wl-fb; do
  install -d "$STAGE/etc/systemd/system/$_svc.service.d"
  install -m 0644 "/nuxel/services/nuxel-s10/systemd/fast-stop/$_svc.service.d.conf" \
      "$STAGE/etc/systemd/system/$_svc.service.d/20-fast-stop.conf"
done
# PWNAGE-89000: soundd owns the audio-session pull-in; audio-route is a
# Wayland-session background task; microphone capture is event-driven by
# nuxel-mic-route.path after the applied-route receipt.  None of these belong
# in multi-user.target.wants.
install -d "$STAGE/etc/systemd/system/nuxel-wayland.service.wants" \
           "$STAGE/etc/systemd/system/paths.target.wants" \
           "$STAGE/etc/systemd/system/timers.target.wants"
ln -sf ../nuxel-audio-route.service "$STAGE/etc/systemd/system/nuxel-wayland.service.wants/nuxel-audio-route.service"
ln -sf ../nuxel-mic-route.path "$STAGE/etc/systemd/system/paths.target.wants/nuxel-mic-route.path"
ln -sf ../nuxel-audio-route.timer "$STAGE/etc/systemd/system/timers.target.wants/nuxel-audio-route.timer"
ln -sf ../nuxel-wifi.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-wifi.service"
ln -sf ../nuxel-interface-state.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-interface-state.service"
# Bluetooth is OFF on a fresh boot.  Remove the package/older-image autostart
# links so the radio is not powered before nuxel-interface-state restores the
# owner's persisted choice.  The D-Bus alias remains, so an explicit ON can
# still start BlueZ.
rm -f "$STAGE/etc/systemd/system/bluetooth.target.wants/bluetooth.service" \
      "$STAGE/etc/systemd/system/bluetooth.target.wants/nuxel-bluetooth.service" \
      "$STAGE/etc/systemd/system/multi-user.target.wants/bluetooth.service" \
      "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-bluetooth.service" \
      "$STAGE/etc/systemd/system/dbus-org.bluez.service"
ln -sf ../nuxel-charger-mode-recovery.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-charger-mode-recovery.service"
ln -sf ../nuxel-device-permissions.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-device-permissions.service"
ln -sf ../nuxel-usb-mode-monitor.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-usb-mode-monitor.service"
ln -sf ../nuxel-geoclue-agent.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-geoclue-agent.service"
# PWNAGE-36000: S10+ audio/geoclue runtime configuration.
#   * static PipeWire ALSA sink on RDMA1 (hw:0,1, 44.1 kHz): the image has no
#     udev daemon, so WirePlumber's api.alsa.enum.udev monitor cannot enumerate
#     beyond-madera and would fall back to Dummy Output;
#   * WirePlumber video-capture disabled: the Samsung MFC V4L2 open blocks in
#     request_firmware/mfc_load_firmware and wedges the audio session manager;
#   * /etc/asound.conf points ALSA direct consumers at RDMA1 as well;
#   * geoclue runs WiFi/IP sources, with modem-GPS explicitly disabled (there is
#     no modem-GPS source on this device and leaving it enabled makes geoclue
#     treat it as the exclusive provider);
#   * the udev rules are a fallback; nuxel-session.sh also re-applies /dev/snd
#     group/mode every boot because this image does not run udev.
# PWNAGE-52000: bwrap 0.12's --ro-bind-fd/--bind-fd path resolution fails on
# the Samsung 4.14 kernel (it closes the source fd before resolving it, seen as
# "Can't find source path /proc/self/fd/N").  Flatpak 1.16 uses those options for
# every /usr and /app bind.  Install a transparent shim that rewrites them to
# the fd's real path; the real binary stays alongside it.
install -d "$STAGE/usr/libexec"
if [ -x "$STAGE/usr/bin/bwrap" ]; then
    install -m 0755 "$STAGE/usr/bin/bwrap" "$STAGE/usr/libexec/bwrap.real"
    install -m 0755 /nuxel/tools/s10plus/nuxel-bwrap-compat.py "$STAGE/usr/bin/bwrap"
fi
install -d "$STAGE/etc/pipewire/pipewire.conf.d" \
           "$STAGE/etc/wireplumber/wireplumber.conf.d" \
           "$STAGE/etc/dbus-1/system.d" \
           "$STAGE/etc/geoclue"
install -m 0644 /nuxel/configs/s10plus/pipewire/50-nuxel-s10-alsa.conf \
    "$STAGE/etc/pipewire/pipewire.conf.d/50-nuxel-s10-alsa.conf"
# PWNAGE-52000: static capture source for the built-in mics (WDMA1) plus the
# vendor-derived UAIF0 -> NSRC0 -> SIFM0/WDMA1 route.  Without this the privacy
# provider correctly reports UNSUPPORTED_NO_CAPTURE_SOURCE.
install -m 0644 /nuxel/configs/s10plus/pipewire/51-nuxel-s10-mic.conf \
    "$STAGE/etc/pipewire/pipewire.conf.d/51-nuxel-s10-mic.conf"
install -m 0644 /nuxel/configs/s10plus/wireplumber/99-nuxel-no-v4l2.conf \
    "$STAGE/etc/wireplumber/wireplumber.conf.d/99-nuxel-no-v4l2.conf"
install -m 0644 /nuxel/configs/s10plus/alsa/asound.conf "$STAGE/etc/asound.conf"
install -m 0644 /nuxel/configs/s10plus/geoclue/geoclue.conf "$STAGE/etc/geoclue/geoclue.conf"
install -m 0644 /nuxel/configs/nuxel/gnss/99-geoclue-nuxel.conf \
    "$STAGE/etc/dbus-1/system.d/99-geoclue-nuxel.conf"
install -m 0644 /nuxel/configs/s10plus/udev/90-nuxel-audio.rules \
    "$STAGE/etc/udev/rules.d/90-nuxel-audio.rules"
install -m 0644 /nuxel/configs/s10plus/udev/90-nuxel-bluetooth.rules \
    "$STAGE/etc/udev/rules.d/90-nuxel-bluetooth.rules"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-wait-wayland          "$STAGE/usr/lib/nuxel/nuxel-wait-wayland"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-launcher-ready-wait.sh "$STAGE/usr/lib/nuxel/nuxel-launcher-ready-wait"
install -m 0644 /nuxel/tools/s10plus/a29/phoc-phone.ini              "$STAGE/etc/nuxel/phoc-phone.ini"
# --- canonical service graph (briq-04b) --------------------------------------
# The units are installed from services/**, the ONE canonical repository source,
# NOT from the A29/A31/A32 tool directories they were measured in.  Provenance is
# checked by tools/s10plus/a33/verify-service-graph.py (it fails if a canonical
# unit loses an Environment=/ExecStart= line the shipped revision carried).
# Explicit, one line per unit: the boot graph must be readable and verifiable
# from this script (verify-service-graph.py proves install AND enablement textually).
install -m 0644 /nuxel/services/nuxel-session/systemd/seatd.service                "$STAGE/etc/systemd/system/seatd.service"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-touch-arm.service      "$STAGE/etc/systemd/system/nuxel-touch-arm.service"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-wayland.service        "$STAGE/etc/systemd/system/nuxel-wayland.service"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-wl-fb.service          "$STAGE/etc/systemd/system/nuxel-wl-fb.service"
install -d -m 0755 "$STAGE/etc/systemd/system/nuxel-wayland.service.d"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-wayland.service.d/50-kbase-egl.conf \
    "$STAGE/etc/systemd/system/nuxel-wayland.service.d/50-kbase-egl.conf"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wayland.service.d/30-fast-stop.conf \
    "$STAGE/etc/systemd/system/nuxel-wayland.service.d/30-fast-stop.conf"
install -m 0644 /nuxel/services/nuxel-s10/systemd/nuxel-wayland.service.d/40-bounded-stop.conf \
    "$STAGE/etc/systemd/system/nuxel-wayland.service.d/40-bounded-stop.conf"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-fallback.service       "$STAGE/etc/systemd/system/nuxel-fallback.service"
install -m 0644 /nuxel/services/nuxel-session/systemd/nuxel-button-manager.service "$STAGE/etc/systemd/system/nuxel-button-manager.service"
install -m 0644 /nuxel/services/nuxel-animation/systemd/nuxel-animation.service \
    "$STAGE/etc/systemd/system/nuxel-animation.service"
install -m 0755 /nuxel/services/nuxel-animation/bin/nuxel-animation-claim \
    "$STAGE/usr/lib/nuxel/nuxel-animation-claim"
# --- live console (briq-04b): INSTALLED, DELIBERATELY NOT ENABLED -------------
# The console has exactly ONE owner. On this image that owner is the initramfs
# instance of /opt/nuxel/nuxel-console, which binds the CDC-ACM gadget and holds
# /run/nuxel-console.lock before systemd exists (boot/initramfs/init.sh).
# The unit + its flock probe are installed so the declaration is reproducible
# from the repository, but NO multi-user.target.wants symlink is created:
#   * ConditionPathExists=/usr/bin/nuxel-console (absent: the console ships in
#     the initramfs) and ExecCondition=nuxel-console-free (proves the port is
#     free) already make a start impossible while the initramfs owner runs;
#   * enabling it would put a second console on the same tty the moment the
#     rootfs binary is ever added, which desynchronises the framed protocol.
# services/nuxel-console/test-console-ownership.py asserts BOTH facts, and
# verify-service-graph.py fails the build if an enablement line appears here.
install -m 0644 /nuxel/services/nuxel-console/systemd/nuxel-console.service \
    "$STAGE/etc/systemd/system/nuxel-console.service"
install -m 0755 /nuxel/services/nuxel-console/bin/nuxel-console-free \
    "$STAGE/usr/lib/nuxel/nuxel-console-free"
# NOT ENABLED ON PURPOSE - see above. No `ln -sf ../nuxel-console.service`.
# nuxel-animation may only become the panel owner on an image WITHOUT the launcher
# bridge (ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb + the claim helper), so
# enabling it cannot regress the A32 single framebuffer owner invariant.
ln -sf ../nuxel-animation.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-animation.service"
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
  # seatd is the backend session provider the libinput backend needs (A31).
  # One explicit symlink per unit (verify-service-graph.py reads these lines).
  ln -sf ../seatd.service                "$STAGE/etc/systemd/system/multi-user.target.wants/seatd.service"
  ln -sf ../nuxel-orientationd.service   "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-orientationd.service"
  ln -sf ../nuxel-wayland.service        "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-wayland.service"
  ln -sf ../nuxel-wl-fb.service          "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-wl-fb.service"
  ln -sf ../nuxel-fallback.service       "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-fallback.service"
  ln -sf ../nuxel-button-manager.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-button-manager.service"
  # PWNAGE-31000: bounded, fail-open pre-lockscreen video.  This unit is enabled
  # only on launcher images; it observes nuxel-wayland + nuxel-wl-fb and never
  # owns the framebuffer or starts an application service.
  install -d "$STAGE/etc/nuxel/boot"
  install -m 0755 /nuxel/services/nuxel-preload-cinema/nuxel-preload-cinema \
    "$STAGE/usr/lib/nuxel/nuxel-preload-cinema"
  install -m 0644 /nuxel/configs/nuxel/boot/preload-cinema.json \
    "$STAGE/etc/nuxel/boot/preload-cinema.json"
  install -m 0644 /nuxel/services/nuxel-preload-cinema/nuxel-preload-cinema.service \
    "$STAGE/etc/systemd/system/nuxel-preload-cinema.service"
  install -Dm0644 /nuxel/docs/pwnage-31000/IMPLEMENTATION.md \
    "$STAGE/usr/share/nuxel/doc/PWNAGE-31000.md"
  ln -sf ../nuxel-preload-cinema.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-preload-cinema.service"
fi

# A28: the launcher's port record (nuxel-ui.service Documentation= points here)
install -Dm0644 /nuxel/docs/s10plus-autonomous-boot-repair/UTM-LAUNCHER-PORT/README.md \
    "$STAGE/usr/share/doc/nuxel/UTM-LAUNCHER-PORT.md"
# --- bridge / portal / notifications: code, shims, units, policies ----------
for service in nuxel-bridge nuxel-portal nuxel-notifications; do
  [[ -d "/nuxel/services/$service/src" ]] || { echo "ERROR: services/$service/src missing" >&2; exit 1; }
  install -d "$STAGE/usr/lib/nuxel/$service"
  cp -a "/nuxel/services/$service/src/." "$STAGE/usr/lib/nuxel/$service/"
  for shim in "/nuxel/services/$service/bin/"*; do
    [ -f "$shim" ] || continue
    install -m 0755 "$shim" "$STAGE/usr/bin/$(basename "$shim")"
  done
done
# Units installed explicitly (not by glob) so the canonical set is greppable and
# verify-service-graph.py can prove install + enablement from the script text.
install -m 0644 /nuxel/services/nuxel-bridge/systemd/nuxel-bridge.service             "$STAGE/etc/systemd/system/nuxel-bridge.service"
install -m 0644 /nuxel/services/nuxel-bridge/systemd/nuxel-http-bridge.service        "$STAGE/etc/systemd/system/nuxel-http-bridge.service"
# PWNAGE-47000 GUI remote access: separate provider, on-demand services and
# loopback-only listeners.  Nothing here is enabled at boot.
install -d "$STAGE/usr/local/libexec/nuxel" "$STAGE/etc/nuxel/remote-desktop/vnc" \
         "$STAGE/etc/nuxel/remote-desktop/xrdp" "$STAGE/var/lib/nuxel/remote-desktop" \
         "$STAGE/usr/share/nuxel/remote-desktop"
install -m 0755 /nuxel/services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl \
    "$STAGE/usr/local/libexec/nuxel/nuxel-remote-desktop-ctl"
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/wayvnc.conf.example \
    "$STAGE/etc/nuxel/remote-desktop/vnc/wayvnc.conf"
install -m 0644 /nuxel/services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service \
    "$STAGE/etc/systemd/system/nuxel-remote-vnc.service"
# XRDP is a SEPARATE X11 session.  The account has no sudo, no root login and
# no access to the active Wayland runtime socket.
# Create gid 3003 before any supplementary-group lookup.  The Android 4.14
# paranoid-network policy requires it for AF_INET sockets, and both the
# restricted remote account and the interactive nuxel account use it.
chroot "$STAGE" /usr/sbin/groupadd -f -g 3003 inet
chroot "$STAGE" /usr/sbin/useradd --create-home --shell /bin/bash nuxel-remote 2>/dev/null || true
chroot "$STAGE" /usr/sbin/usermod -aG inet nuxel-remote
# PWNAGE-47000: every image gets its own strong RDP password for the
# restricted account.  The value is never echoed by this script; it is written
# only to a root-only 0600 file inside the image so the owner can read it once.
install -d -m 0700 "$STAGE/etc/nuxel/remote-desktop/xrdp"
_rdpw="$(openssl rand -hex 14)"
[ "${#_rdpw}" -eq 28 ] || { echo 'ERROR: RDP credential generation failed' >&2; exit 1; }
printf 'nuxel-remote:%s\n' "$_rdpw" | chroot "$STAGE" /usr/sbin/chpasswd
( umask 077; printf '%s\n' "$_rdpw" > "$STAGE/etc/nuxel/remote-desktop/xrdp/credential" )
chmod 0600 "$STAGE/etc/nuxel/remote-desktop/xrdp/credential"
chown 0:0 "$STAGE/etc/nuxel/remote-desktop/xrdp/credential"
unset _rdpw
[ -s "$STAGE/etc/nuxel/remote-desktop/xrdp/credential" ] || {
  echo 'ERROR: RDP credential file missing' >&2; exit 1; }
install -d "$STAGE/home/nuxel-remote/.config/openbox" "$STAGE/home/nuxel-remote/.mozilla/firefox/xrdp"
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/xrdp.ini \
    "$STAGE/etc/xrdp/xrdp.ini"
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/sesman.ini \
    "$STAGE/etc/xrdp/sesman.ini"
# RDP is restricted to the local nuxel account (uid 1000). The legacy
# nuxel-remote account must not authenticate over RDP.
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/xrdp-sesman.pam \
    "$STAGE/etc/pam.d/xrdp-sesman"
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/xorg.conf \
    "$STAGE/etc/xrdp/xorg-nuxel.conf"
install -m 0755 /nuxel/services/nuxel-remote-desktop/bin/nuxel-xrdp-session \
    "$STAGE/usr/local/bin/nuxel-xrdp-session"
install -m 0644 /nuxel/services/nuxel-remote-desktop/config/launcher.html \
    "$STAGE/usr/share/nuxel/remote-desktop/launcher.html"
# Generate per-image TLS material for xrdp.  Never ship a shared key.
openssl req -x509 -newkey rsa:2048 -nodes -days 825 -subj '/CN=nuxel-remote-desktop' \
    -addext 'subjectAltName=DNS:nuxel,DNS:localhost,IP:127.0.0.1' \
    -keyout "$STAGE/etc/xrdp/nuxel-key.pem" -out "$STAGE/etc/xrdp/nuxel-cert.pem" >/dev/null 2>&1
chmod 0640 "$STAGE/etc/xrdp/nuxel-key.pem" "$STAGE/etc/xrdp/nuxel-cert.pem"
chgrp xrdp "$STAGE/etc/xrdp/nuxel-key.pem" "$STAGE/etc/xrdp/nuxel-cert.pem" 2>/dev/null || true
# Clean-rootfs assertions: the supported binaries, unit and configs must exist.
for _rd in /usr/bin/wayvnc /usr/bin/wayvncctl /usr/bin/xrdp /usr/libexec/Xorg \
           /usr/bin/openbox /usr/bin/firefox /usr/local/bin/nuxel-xrdp-session \
           /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl \
           /etc/systemd/system/nuxel-remote-vnc.service \
           /etc/nuxel/remote-desktop/vnc/wayvnc.conf \
           /etc/xrdp/xrdp.ini \
           /etc/xrdp/sesman.ini /etc/xrdp/xorg-nuxel.conf; do
  [ -e "$STAGE$_rd" ] || { echo "ERROR: remote-desktop missing $_rd" >&2; exit 1; }
done
# The remote services are activation-driven; do NOT create boot wants.
install -m 0644 /nuxel/services/nuxel-bridge/polkit/50-nuxel-bridge-network.rules     "$STAGE/etc/polkit-1/rules.d/50-nuxel-bridge-network.rules"
install -m 0644 /nuxel/services/nuxel-portal/systemd/nuxel-portal.service             "$STAGE/etc/systemd/system/nuxel-portal.service"
install -m 0644 /nuxel/services/nuxel-notifications/systemd/nuxel-notifications.service "$STAGE/etc/systemd/system/nuxel-notifications.service"
# The static PWA server that serves the launcher tree on :8000.
install -m 0755 /nuxel/services/nuxel-web/bin/nuxel-web "$STAGE/usr/bin/nuxel-web"
# The static server itself (briq-04c rev 2): explicit MIME types, ETag +
# Last-Modified revalidation, Service-Worker-Allowed for service-worker scripts,
# a cache policy per asset class and threaded serving. The shim resolves it from
# /usr/lib/nuxel first, so this path is what the phone uses.
install -m 0755 /nuxel/services/nuxel-web/bin/nuxel-web-server.py \
    "$STAGE/usr/lib/nuxel/nuxel-web-server.py"
install -m 0644 /nuxel/services/nuxel-web.service "$STAGE/etc/systemd/system/nuxel-web.service"
# System users the units run as (systemd-sysusers would do this at boot, but
# this kernel masks the units that consume it, so create them in the image).
for u in nuxel-bridge nuxel-portal nuxel-notifications; do
  chroot "$STAGE" /usr/sbin/useradd --system --no-create-home --home-dir /       --shell /usr/sbin/nologin "$u" 2>/dev/null || true
done
# The notification daemon must replace its canonical history file.  Grant only
# its group write on /var/lib/nuxel (the bridge remains root and owns policy).
# The chgrp above can be a no-op when the build host does not know the target
# group name; the authoritative numeric assignment happens AFTER the service
# users are created below.
chgrp nuxel-notifications "$STAGE/var/lib/nuxel" 2>/dev/null || true
chmod 0770 "$STAGE/var/lib/nuxel"
chroot "$STAGE" /usr/sbin/groupadd --system seat 2>/dev/null || true
# D-Bus system policies: configs/dbus/ is the canonical combined directory.
install -d "$STAGE/etc/dbus-1/system.d"
for conf in /nuxel/configs/dbus/*.conf; do
  [ -f "$conf" ] || continue
  install -m 0644 "$conf" "$STAGE/etc/dbus-1/system.d/$(basename "$conf")"
done
# The canonical application registry is a runtime file, so the shell, the bridge
# and the PWA all resolve the same source of truth (briq-04c).
install -d "$STAGE/etc/nuxel/app-registry"
install -m 0644 /nuxel/pwa/nuxel-common/app-registry.json \
    "$STAGE/etc/nuxel/app-registry/app_registry.json"
install -m 0644 /nuxel/pwa/nuxel-common/bridge-version.json \
    "$STAGE/etc/nuxel/bridge-version.json"
# Virtual keyboard contract: Stevia is installed above, while this applier and
# its user units connect the Settings document to the active Phoc/Phosh session.
# These files were previously tested in-tree but omitted from the phone image.
install -Dm0644 /nuxel/configs/nuxel/keyboard/keyboard.json \
    "$STAGE/etc/nuxel/keyboard/keyboard.json"
install -Dm0644 /nuxel/configs/nuxel/keyboard/keyboard.schema.json \
    "$STAGE/usr/share/nuxel/schemas/keyboard.schema.json"
install -Dm0644 /nuxel/configs/nuxel/keyboard/README.md \
    "$STAGE/usr/share/doc/nuxel/keyboard/README.md"
install -Dm0755 /nuxel/tools/s10plus/a33/nuxel-keyboard-apply.sh \
    "$STAGE/usr/libexec/nuxel/nuxel-keyboard-apply"
install -Dm0644 /nuxel/configs/nuxel/keyboard/nuxel-keyboard-apply.service \
    "$STAGE/usr/lib/systemd/user/nuxel-keyboard-apply.service"
install -Dm0644 /nuxel/configs/nuxel/keyboard/nuxel-keyboard-apply.path \
    "$STAGE/usr/lib/systemd/user/nuxel-keyboard-apply.path"
install -d "$STAGE/etc/systemd/user/default.target.wants"
ln -sf /usr/lib/systemd/user/nuxel-keyboard-apply.path \
    "$STAGE/etc/systemd/user/default.target.wants/nuxel-keyboard-apply.path"
# docroot override for nuxel-web (the shim also probes the default locations)
printf 'NUXEL_WEBROOT=/usr/share/nuxel\nNUXEL_WEB_PORT=8000\nNUXEL_WEB_BIND=127.0.0.1\n' \
    > "$STAGE/etc/nuxel/web.conf"
# enablement: the boot graph must be reproducible from the repository
ln -sf ../nuxel-notifications.service "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-notifications.service"
ln -sf ../nuxel-portal.service        "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-portal.service"
ln -sf ../nuxel-bridge.service        "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-bridge.service"
ln -sf ../nuxel-http-bridge.service   "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-http-bridge.service"
# BlueZ OBEX Object Push (Files -> Send) is D-Bus activated from
# /usr/share/dbus-1/services/org.bluez.obex.service (Fedora ships the unit in
# /usr/lib/systemd/user/).  No system-unit symlink is created; the bridge's
# session-bus address is configured in nuxel-http-bridge.service.
ln -sf ../nuxel-web.service           "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-web.service"
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
# PWNAGE-42000 ROOT CAUSE: /var/lib/nuxel is 0770 root:nuxel-notifications so
# the notification hub can replace its history file.  nuxel-bridge is not in
# that group, and without directory execute permission it could not read the
# persisted Location policy or any capability grant.  The bridge therefore
# silently reported Location OFF and CAPABILITY_DENIED.  Resolve the target
# users' numeric IDs from the staged passwd/group files (never from the macOS
# build host), then grant the bridge exactly:
#   /var/lib/nuxel               r-x  (traverse only)
#   /var/lib/nuxel/permissions   rwx  (read grants, persist its own policy)
# The notification hub keeps its group-write path; nothing becomes world-readable.
install -d -m 0770 "$STAGE/var/lib/nuxel/permissions"
NUXEL_UID="$(awk -F: '$1=="nuxel"{print $3; exit}' "$STAGE/etc/passwd")"
NUXEL_GID="$(awk -F: '$1=="nuxel"{print $4; exit}' "$STAGE/etc/passwd")"
[ -n "$NUXEL_UID" ] && [ -n "$NUXEL_GID" ] || {
  echo 'ERROR: nuxel interactive identity missing from staged passwd' >&2; exit 1; }
chown "$NUXEL_UID:$NUXEL_GID" "$STAGE/var/lib/nuxel/permissions"
chmod 0770 "$STAGE/var/lib/nuxel/permissions"
NUXEL_BRIDGE_UID="$(awk -F: '$1=="nuxel-bridge"{print $3; exit}' "$STAGE/etc/passwd")"
NUXEL_BRIDGE_GID="$(awk -F: '$1=="nuxel-bridge"{print $4; exit}' "$STAGE/etc/passwd")"
NUXEL_NOTIFY_GID="$(awk -F: '$1=="nuxel-notifications"{print $3; exit}' "$STAGE/etc/group")"
[ -n "$NUXEL_BRIDGE_UID" ] && [ -n "$NUXEL_BRIDGE_GID" ] || {
  echo 'ERROR: nuxel-bridge identity missing from staged passwd' >&2; exit 1; }
[ -n "$NUXEL_NOTIFY_GID" ] || {
  echo 'ERROR: nuxel-notifications group missing from staged group' >&2; exit 1; }
chown 0:"$NUXEL_NOTIFY_GID" "$STAGE/var/lib/nuxel"
chmod 0771 "$STAGE/var/lib/nuxel"
setfacl -m "u:${NUXEL_BRIDGE_UID}:r-x" "$STAGE/var/lib/nuxel"
setfacl -m "u:${NUXEL_UID}:r-x" "$STAGE/var/lib/nuxel"
setfacl -m "u:${NUXEL_BRIDGE_UID}:rwx" "$STAGE/var/lib/nuxel/permissions"
# Prove the exact access path the bridge needs.  If the build host kernel has no
# ACL support this fails the build instead of shipping a silently broken policy.
getfacl -p "$STAGE/var/lib/nuxel" "$STAGE/var/lib/nuxel/permissions"
# PWNAGE-47000: this Android-derived 4.14 kernel is built with
# CONFIG_ANDROID_PARANOID_NETWORK=y.  A non-root process may only create an
# AF_INET socket when its supplementary groups include gid 3003 ("inet").
# Without this, unprivileged sshd sessions cannot open local port forwards and
# the GUI remote-access apps can never reach the loopback-bound servers.
# Direct /etc/group edit: groupadd/usermod in this kernel-less chroot can
# disagree through the NSS userdb path and abort a clean image build.  The
# resulting file is the authoritative source for sshd's supplementary groups.
python3 - "$STAGE/etc/group" <<'PYGROUP'
import sys
path = sys.argv[1]
entries = open(path).read().splitlines()
found = False
out = []
for line in entries:
    parts = line.split(":")
    if parts and parts[0] == "inet":
        found = True
        while len(parts) < 4:
            parts.append("")
        parts[2] = "3003"
        members = [m for m in parts[3].split(",") if m and m != "nuxel"]
        members.append("nuxel")
        parts[3] = ",".join(members)
        line = ":".join(parts)
    out.append(line)
if not found:
    out.append("inet:x:3003:nuxel")
with open(path, "w") as fh:
    fh.write("\n".join(out) + "\n")
PYGROUP
grep -q '^inet:x:3003:.*nuxel' "$STAGE/etc/group" || {
  echo 'ERROR: could not add nuxel to gid 3003 (inet)' >&2; exit 1;
}
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
USERSERVICE_REVISION=A34-touchdown
TOUCHSCREEN=requires-current-image-physical-test
CLICKABLE=not-yet-owner-verified
VIRTUAL_KEYBOARD=stevia-installed-owner-test-pending
AUDIO=unverified-no-touchscreen-interaction
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

# PWNAGE-60000 FINAL GATE: verify the generated tree after every package and
# asset transaction.  This catches a DNF transaction resetting the GLVND vendor
# file or a missing probe before the image can be published.
if [ "$GPU_REQUIRED" = 1 ]; then
  /nuxel/tools/s10plus/a67/nuxel-gpu-image-verify.sh "$STAGE" --manifest "$GPU_MANIFEST" || {
    echo "ERROR: GPU image verification failed; refusing to publish this image" >&2
    exit 1
  }
fi
