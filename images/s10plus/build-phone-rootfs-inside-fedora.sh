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
cp -a /nuxel/pwa/nuxel-home "$STAGE/usr/share/nuxel/"
install -m 0755 /nuxel/tools/s10plus/nuxel-fb-phone-aarch64 "$STAGE/usr/bin/nuxel-fb-phone"
install -m 0644 /nuxel/assets/nuxel-background.png "$STAGE/usr/share/nuxel/nuxel-background.png"
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
