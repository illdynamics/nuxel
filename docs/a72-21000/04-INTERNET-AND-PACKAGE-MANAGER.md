# NUXEL A72 / 21000 — 04-INTERNET-AND-PACKAGE-MANAGER

## 04A. Internet proof (phone-side, measured live)
- wlan0 `connected` (NetworkManager state 100), SSID `Nuxel Ziggo5501109`, 192.168.178.167/24.
- default route via 192.168.178.1; DNS 62.179.104.196 / 213.46.228.196 (+ v6).
- TLS-verified: `curl -sSIL https://www.fedoraproject.org/` → `HTTP/2 302`, HSTS present.
- Fedora 43 aarch64 GA + updates repomd.xml both `HTTP 200` from the phone.

## 04B. Package-manager bootstrap (designed, pending owner approval)
Phone has rpm 6.0.2 but no dnf5 and none of the dnf5 shared libs. Authoritative
resolution was done with a native aarch64 `registry.fedoraproject.org/fedora:43`
container (`dnf5 install --installroot=... --setopt=install_weak_deps=False`
dry-run + install into a throwaway staging rootfs), NOT a host x86 dnf.

### Minimal verified transaction (NEW packages only)
Subtracting the phone's existing 463 packages from the resolved 91-package
closure yields exactly 13 NEW packages, 4.1 MiB total, all Fedora 43 aarch64,
all GPG-signed (gpgcheck=1, repo_gpgcheck handled by rpmkeys -K):

| name | NEVRA | sha256 |
|---|---|---|
| coreutils-single | 9.7-10.fc43.aarch64 | b7c658ac… |
| dnf5 | 5.2.18.0-5.fc43.aarch64 | f31dafa5… |
| fmt | 11.2.0-3.fc43.aarch64 | 7714af6d… |
| glibc-minimal-langpack | 2.42-17.fc43.aarch64 | 56c8dcca… |
| libdnf5 | 5.2.18.0-5.fc43.aarch64 | d39c6523… |
| libdnf5-cli | 5.2.18.0-5.fc43.aarch64 | aa79e51c… |
| libmodulemd | 2.15.3-1.fc43.aarch64 | 79bcb0e8… |
| librepo | 1.20.0-4.fc43.aarch64 | 6dc3f5fe… |
| libsolv | 0.7.40-1.fc43.aarch64 | b4d62301… |
| libyaml | 0.2.5-17.fc43.aarch64 | 5ec796dd… |
| sdbus-cpp | 2.1.0-3.fc43.aarch64 | 3a96e33f… |
| systemd-standalone-sysusers | 258.11-1.fc43.aarch64 | d404bad1… |
| zchunk-libs | 1.5.4-1.fc43.aarch64 | 27f079cf… |

Full URLs: docs/a72-21000/package-install-manifest.csv (sha256 + exact
dl.fedoraproject.org URL for each). No --nodeps, no --force, no --nosignature,
no --replacefiles, no systemwide `distro-sync`, no broad upgrade.

### ABI compatibility check (no base-library upgrades required)
- dnf5/libdnf5 require `librpm.so.10`, `librpmio.so.10`, `libsolv.so.1`,
  `librepo.so.0`, `libmodulemd.so.2`, `libfmt.so.11`, `libsdbus-c++.so.2`,
  `libsqlite3.so.0`, `libcrypto.so.3(OPENSSL_3.0.0)`, `libcurl.so.4`.
- Phone already provides: librpm.so.10.7.1, librpmio.so.10.7.1 (rpm-6.0.2-1,
  SAME as repo), libsqlite3.so.3.50.2 (same), libcurl.so.4.8.0 (>=7.52),
  libzstd.so.1.5.7, systemd-libs-258.11 (the pinned 4.14-compatible NEVRA),
  glibc-2.42-17 (same). No glibc/systemd/rpm/python3 upgrade is part of the
  bootstrap — it is purely additive.

### Plan
1. Take versioned backup (03). 2. Download the 13 RPMs ON THE PHONE via curl from
dl.fedoraproject.org (exact URLs), verify sha256 + `rpmkeys -K`. 3. `rpm --test
-Uvh <13 rpms>` preview. 4. `rpm -Uvh` install. 5. Verify `dnf5 --version`,
`rpm -q` each, re-verify internet + shell + USB console. Rollback: `rpm -e` the
13 packages in reverse order (receipts in package-install-manifest.csv).

## 04C. Staged package-family plan (post-dnf5, each a separate approved transaction)
Sizes below are the FRESH-rootfs full closure via aarch64 container; on the phone
the already-installed base is subtracted, so real "new package" counts are smaller.

| family | packages | size | purpose |
|---|---|---|---|
| dnf5 bootstrap | 13 | 4.1 MiB | package manager (this plan) |
| alsa-utils + alsa-ucm | ~66 | 29 MiB | aplay/amixer/alsaucm diagnostics |
| pipewire + pipewire-alsa + wireplumber | ~104 | 42 MiB | audio server/routing |
| bluez (+bluez-tools) | ~70 | 33 MiB | Bluetooth stack |
| vlc (Qt GUI) | heavy (Qt6/ffmpeg chain) | large | media player (mandatory) |
| mpv | ~353 | 211 MiB | lighter media player |

Note: `vlc` GUI pulls Qt6 + a large codec chain; per the mission's "avoid gratuitous
packages", media install will be sized to the smallest set that provides a real
GUI player + a separate music player, installed only after the audio server and
with owner approval. No package family is installed without the dnf5 bootstrap first.
