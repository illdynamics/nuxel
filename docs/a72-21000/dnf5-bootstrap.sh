#!/bin/sh
# NUXEL A72/21000 — dnf5 bootstrap. Downloads 13 Fedora 43 aarch64 RPMs ON THE
# PHONE over HTTPS, verifies sha256 + GPG (rpmkeys -K), previews with rpm --test,
# then installs with plain rpm -U. NO --nodeps/--force/--nosignature/--replacefiles.
# Review before running. Idempotent: already-installed packages are skipped.
set -eu
STAGE=/var/lib/nuxel/a72-rpms
KEY=/etc/pki/rpm-gpg/RPM-GPG-KEY-fedora-43-primary
mkdir -p "$STAGE"; cd "$STAGE"

dl() { # dl NAME URL SHA256
  n="$1"; u="$2"; s="$3"
  f="${u##*/}"
  if [ -f "$f" ]; then
    if echo "$s  $f" | sha256sum -c - >/dev/null 2>&1; then echo "[$n] cached+verified"; return 0; fi
  fi
  echo "[$n] downloading $f"
  curl -sSL --connect-timeout 10 --max-time 180 -o "$f.tmp" "$u"
  echo "$s  $f.tmp" | sha256sum -c -
  mv "$f.tmp" "$f"
  echo "[$n] sha256 OK"
}

dl coreutils-single https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/c/coreutils-single-9.7-10.fc43.aarch64.rpm b7c658ac604a7c96f588c649501617172987350e7eade0d78c0d14a6cf0562a7
dl dnf5 https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/d/dnf5-5.2.18.0-5.fc43.aarch64.rpm f31dafa5ecea71518c7eedd67d2ae3edee4f7dd387908628d98d4a930af34740
dl fmt https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os/Packages/f/fmt-11.2.0-3.fc43.aarch64.rpm 7714af6d843c104380c17efaec5d332c9ec2fe5e7c4b67dde0842d2c617f0857
dl glibc-minimal-langpack https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/g/glibc-minimal-langpack-2.42-17.fc43.aarch64.rpm 56c8dcca50a5bf78a19fc317109af92de5052fa0df8aa53ea3a744566920afb6
dl libdnf5 https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/l/libdnf5-5.2.18.0-5.fc43.aarch64.rpm d39c652346dea5a81f1a42b4ebd12466bb30eb06a529093f9021bed791b2fe35
dl libdnf5-cli https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/l/libdnf5-cli-5.2.18.0-5.fc43.aarch64.rpm aa79e51c45c62a11738206989118a90888b6afbd2f02bf897aa727123bea9718
dl libmodulemd https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/l/libmodulemd-2.15.3-1.fc43.aarch64.rpm 79bcb0e827bbcbb7abc10daf7d65a41e0eec30ffb9faaef72b2b379a2f80ef89
dl librepo https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os/Packages/l/librepo-1.20.0-4.fc43.aarch64.rpm 6dc3f5fe62a3ab514ed654014d70c6122968607f7429a0a84fba3d2783712d8c
dl libsolv https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/l/libsolv-0.7.40-1.fc43.aarch64.rpm b4d6230162febf512ba4aa754482cd29267ed6a75a1803183d453a48fd32739d
dl libyaml https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os/Packages/l/libyaml-0.2.5-17.fc43.aarch64.rpm 5ec796dde746e2f84e6879ed26b7c07f79706cb32ca9f836e7cd71ed71f9961a
dl sdbus-cpp https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os/Packages/s/sdbus-cpp-2.1.0-3.fc43.aarch64.rpm 3a96e33f6705f4f48e7d4e1b5ddfb5324d0eef35ef363426cb964cad0f3b8985
dl systemd-standalone-sysusers https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/s/systemd-standalone-sysusers-258.11-1.fc43.aarch64.rpm d404bad16245a9ad6ea11274fc35c86318e43058cf06294892dec0b2985dfe49
dl zchunk-libs https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/Packages/z/zchunk-libs-1.5.4-1.fc43.aarch64.rpm 27f079cf330f39121de0ea7d4d0d12d607548d84916ac91ff82066606c985549

# Import the Fedora 43 key if not already imported (non-destructive).
rpm --import "$KEY" 2>/dev/null || true

echo "== GPG verification (rpmkeys -K) =="
for f in *.rpm; do rpmkeys -K "$f"; done

# Build the install list: skip anything already installed at a satisfying version.
INSTALL=""
for f in *.rpm; do
  n="${f%%-[0-9]*}"; n="${n%%-[0-9]*}"
  # rpm -q --whatprovides is noisy; use rpm -q on the package name derived from file
  pkgname=$(rpm -qp --qf '%{NAME}' "$f" 2>/dev/null || true)
  if [ -n "$pkgname" ] && rpm -q "$pkgname" >/dev/null 2>&1; then
    echo "skip already-installed: $pkgname"
  else
    INSTALL="$INSTALL $f"
  fi
done

echo "== transaction preview =="
# shellcheck disable=SC2086
rpm --test -Uvh $INSTALL

echo "== install =="
# shellcheck disable=SC2086
rpm -Uvh $INSTALL

echo "== verify =="
dnf5 --version | head -6
rpm -q dnf5 libdnf5 libdnf5-cli libsolv librepo libmodulemd fmt sdbus-cpp libyaml zchunk-libs coreutils-single glibc-minimal-langpack systemd-standalone-sysusers
echo "== DONE =="
