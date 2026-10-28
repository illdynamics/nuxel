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
dnf -y install e2fsprogs findutils coreutils file rpm shadow-utils python3 \
    gcc make pkgconf-pkg-config kernel-headers \
    wayland-devel wayland-protocols-devel \
    gtk3-devel webkit2gtk4.1-devel alsa-lib-devel git
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
    python3 phosh phoc stevia stevia-phosh-osk-provider seatd \
    NetworkManager NetworkManager-wifi wpa_supplicant libnl3 libnl3-cli iw wireless-regdb ModemManager geoclue2 geoclue2-demos bluez bluez-deprecated \
    mesa-dri-drivers mesa-libEGL mesa-libgbm libinput \
    gtk3 webkit2gtk4.1 gtk4 libadwaita glib-networking libproxy \
    pipewire wireplumber pipewire-utils alsa-lib mpg123 mpv \
    polkit nftables upower greetd \
    iproute procps-ng kmod e2fsprogs \
    shadow-utils ca-certificates curl
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
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-wl-fb" /nuxel/tools/s10plus/a34/nuxel-wl-fb.c \
    "$B/wlr-screencopy-unstable-v1-protocol.c" \
    $(pkg-config --libs wayland-client)

# A34 screencopy diagnostic (deployed as /usr/local/bin/nuxel-wl-snapshot).
gcc $CFLAGS_COMMON $(pkg-config --cflags wayland-client) \
    -o "$B/nuxel-wl-snapshot" /nuxel/tools/s10plus/a34/nuxel-wl-snapshot.c \
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

# A34 button manager: SYN_REPORT touch translation, power menu, Bixby cancel.
gcc $CFLAGS_COMMON $(pkg-config --cflags alsa) -I /nuxel/tools/s10plus/a34 \
    -o "$B/nuxel-button-manager" \
    /nuxel/tools/s10plus/a34/nuxel-button-manager.c \
    $(pkg-config --libs alsa)

# Current capability-based libinput path shim for the 4.14/udevd-less kernel.
gcc $CFLAGS_COMMON -shared -fPIC -o "$B/libnuxel-libinput-path.so" \
    /nuxel/tools/s10plus/a33/nuxel-libinput-path.c -ldl

# A40/A44 socket-activated Home hardware monitor. The live phone runs this
# collector; a fresh release image must build and install the same source, not
# depend on a previously deployed binary.
gcc -std=c11 -O2 -Wall -Wextra -Werror -o "$B/nuxel-metricsd" \
    /nuxel/services/nuxel-metrics/nuxel-metricsd.c

for _b in nuxel-wl-fb nuxel-wl-snapshot nuxel-pwa-host \
          nuxel-button-manager libnuxel-libinput-path.so nuxel-metricsd; do
  file "$B/$_b" | grep -q 'ARM aarch64' || { echo "ERROR: $_b is not aarch64" >&2; exit 1; }
done
sha256sum "$B"/nuxel-wl-fb "$B"/nuxel-wl-snapshot "$B"/nuxel-pwa-host \
          "$B"/nuxel-button-manager "$B"/libnuxel-libinput-path.so \
          "$B"/nuxel-metricsd \
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
install -Dm0644 /nuxel/services/nuxel-session/systemd/nuxel-boot-sound.service \
    "$STAGE/etc/systemd/system/nuxel-boot-sound.service"
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
ln -sf ../nuxel-boot-sound.service \
    "$STAGE/etc/systemd/system/multi-user.target.wants/nuxel-boot-sound.service"
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
install -m 0755 "$B/nuxel-button-manager"      "$STAGE/usr/lib/nuxel/nuxel-button-manager"
install -m 0755 "$B/libnuxel-libinput-path.so" "$STAGE/usr/lib/nuxel/libnuxel-libinput-path.so"
install -d "$STAGE/usr/local/bin"
install -m 0755 "$B/nuxel-wl-snapshot"         "$STAGE/usr/local/bin/nuxel-wl-snapshot"
# console control for the same configuration the Settings app uses
install -m 0755 /nuxel/tools/s10plus/a32/nuxelctl                     "$STAGE/usr/bin/nuxelctl"
# default device configuration: the S10+ port starts from its own profile, and a
# full rebuild must reproduce what the live deployment installed
install -d "$STAGE/etc/nuxel/display" "$STAGE/etc/nuxel/input"
install -m 0644 /nuxel/configs/nuxel/statusbar-safezones.json "$STAGE/etc/nuxel/display/statusbar-safezones.json"
install -m 0644 /nuxel/configs/nuxel/buttons.json             "$STAGE/etc/nuxel/input/buttons.json"
install -m 0644 /nuxel/configs/nuxel/input/button-fsm.json    "$STAGE/etc/nuxel/input/button-fsm.json"
install -d "$STAGE/etc/nuxel/buttons"
install -m 0644 /nuxel/configs/nuxel/buttons/reboot-gate.json "$STAGE/etc/nuxel/buttons/reboot-gate.json"
install -m 0755 /nuxel/tools/s10plus/a29/nuxel-session.sh            "$STAGE/usr/lib/nuxel/nuxel-session.sh"
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
install -d "$STAGE/etc/pipewire/pipewire.conf.d" \
           "$STAGE/etc/wireplumber/wireplumber.conf.d" \
           "$STAGE/etc/dbus-1/system.d" \
           "$STAGE/etc/geoclue"
install -m 0644 /nuxel/configs/s10plus/pipewire/50-nuxel-s10-alsa.conf \
    "$STAGE/etc/pipewire/pipewire.conf.d/50-nuxel-s10-alsa.conf"
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
