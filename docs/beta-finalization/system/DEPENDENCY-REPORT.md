# Nuxel S10+ — Fedora 43 ARM64 Dependency Report

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04a-fedora-packages`
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), Fedora 43
aarch64 userspace on Samsung Linux **4.14.253**, systemd PID 1.
**Verdict:** `OFFLINE_TESTED` — the manifest resolved **and its rpm dependencies
resolved** against **real Fedora 43 aarch64 repository metadata** (two
repositories, 93 991 distinct NEVRAs; revision 2 of `briq-04a-fedora-packages`).
No package version in `images/s10plus/packages-manifest.json` is guessed, and
every one of the 1220 rpm requirements of the 50 essential packages is either
resolved to a package/capability in that metadata, or explicitly recorded as
not-decidable-from-`primary.xml` (file requirements). Unresolved: **0**.

## 1. What was verified, and how

| Step | Mechanism | Result |
|---|---|---|
| Repo metadata located | `repomd.xml` → `primary.xml.zst` fetched from `dl.fedoraproject.org` | 200 OK |
| GA repository | `releases/43/Everything/aarch64/os` | 68 135 aarch64/noarch NEVRAs |
| Updates repository | `updates/43/Everything/aarch64` | 25 856 aarch64/noarch NEVRAs |
| Essential package list | 50 packages across 11 groups | **all resolve** |
| systemd pin | `systemd-258.11-1.fc43.aarch64` | **exact match in updates** |
| systemd subpackages | `systemd-udev`, `systemd-networkd` must equal the pinned systemd version-release | aligned at `258.11-1.fc43` |
| 4.14 patch cross-check | carried `boot/s10plus/payload/libsystemd-shared-*.so` version must equal the resolved systemd version-release | **match** (`258.11-1.fc43`) |
| Requirement classifier | every `Requires` of every essential package, classified by rpm shape | 95 package / 1062 capability / 11 rich / 52 file |
| Dependency resolution | each requirement matched against the repository's package names **and** its real `rpm:provides` entries; the needed set is global across BOTH repositories | **0 unresolved** |
| rpm RICH dependencies | boolean `(A or B)`, `(A if B)`, `(A if B else C)` evaluated tri-state; never guessed | 10 resolved, 1 not-decidable-from-primary |
| Manifest schema | `--validate-manifest` against the embedded JSON schema (stdlib validator; no `jsonschema` dependency exists on a Fedora 43 ARM64 image) | valid (rc 0) |
| Manifest self-check | `--emit-manifest` refuses to write a manifest that does not validate | enforced |
| Offline re-verification | `--offline` against the cached metadata | `resolved` |
| No metadata source | `--offline` with an empty cache | `BLOCKED_EXTERNAL_RESOURCE` (rc 3) |

Reproduce exactly:

```sh
python3 tools/s10plus/a33/verify-packages.py                 # network, real metadata
python3 tools/s10plus/a33/verify-packages.py --offline       # cache only, reproducible
python3 tools/s10plus/a33/verify-packages.py --ga-only       # MUST fail on the systemd pin
python3 tools/s10plus/a33/verify-packages.py --validate-manifest   # JSON-schema the manifest
python3 tools/s10plus/a33/verify-packages.py --emit-manifest # regenerate the manifest
python3 tools/s10plus/a33/tests/test-packages-manifest.py     # the whole guarantee, offline
```

There is **no `--skip-unavailable`**. An essential package that does not exist
for aarch64 is a hard failure, not a warning — a missing package is either fixed
in the manifest or would have aborted the real `dnf` install (the builder runs
`set -Eeuo pipefail`).

### 1.1 Provenance of the metadata every NEVRA comes from

A version is only evidence if the artifact it was read from is named. The
verifier now records the chain of custody for each repository in the report
(`metadata_provenance[]`) and in the manifest
(`source.metadata_provenance[]`), and re-derives it on every run. Values below
are from the live `dl.fedoraproject.org` fetch of **2026-10-16** (the cache
under `build/pkgmeta/` holds bit-identical copies, verified by
`tests/test-packages-manifest.py`):

| Repository | `repomd.xml` sha256 | primary payload | compressed sha256 | NEVRAs |
|---|---|---|---|---|
| `releases/43/Everything/aarch64/os` (GA) | `6431612747d987257399969298151d19cfe87ed26322be6987e7b00cd0ae66a2` | `a29dc3fc…-primary.xml.zst` (14 837 955 B) | `a29dc3fcc86b6e10fab525e6de0b97e851b5e4e7fc3691d40d72efe6757a733d` | 68 135 |
| `updates/43/Everything/aarch64` | `0a1fda3e791e0d0b61940d075fd4a503031419a54848ae84a22871f90beec7af` | `7ca220d0…-primary.xml.zst` (5 594 019 B) | `7ca220d0970a83663d177d49f88307ab4cea8151b9d67cd36e337a0bf2af89dc` | 25 856 |

Decompressed primary sha256: GA
`02d247f25e10add65533a4e76462fe390ebf2b77fcc4e60fe53c2c172ce2d680`, updates
`a3505a4b18b100c7b9ada971cef70d2dadf010ff8a9efefb01f5a07a79f48fbd`. Together:
**93 991 distinct aarch64/noarch NEVRAs**, re-derivable from the recorded artifacts
by anyone with the URLs and a sha256 tool. The `updates` repository moves by
design, so the numbers in this table are the ones resolved by the run recorded
in `images/s10plus/packages-manifest.json` (`source.metadata_provenance[]` is
the machine-readable copy of this table).

Re-derive the same package set from the recorded artifacts:

```sh
# network: fetch the current metadata and re-resolve (fails on any pin drift)
python3 tools/s10plus/a33/verify-packages.py --report build/pkgmeta/report.json
# offline: resolve from the cache and diff its hashes against the manifest
python3 tools/s10plus/a33/verify-packages.py --offline --quiet
python3 tools/s10plus/a33/tests/test-packages-manifest.py   # provenance + pin + builder checks
```

Drift policy: the `updates` repository moves by design. `test-packages-manifest.py`
reports a `updates` hash change as `INFO metadata drifted`, a **GA** hash change
as a failure, and any change that breaks the `systemd` pin as `FAILED`
regardless — the pin is what the carried 4.14 `libsystemd-shared` patch is
compiled against (§3.1).

## 2. Fail-loud findings (these changed the build)

Three real problems were found by resolving against actual metadata. All three
would have broken or silently degraded the shipped image:

### 2.1 `basesystem` does not exist in Fedora 43 — REMOVED from the install line

`<name>basesystem</name>` occurs **0 times** in the GA metadata and 0 times in
the updates metadata. The package was retired; `filesystem` + `setup` are the
real base. The previous rootfs builder listed `basesystem` in its `dnf install`
line, which would have failed the whole build with
`Error: Unable to find a match: basesystem`. **Action taken:** the install line
now uses `filesystem setup` and the manifest records it.

### 2.2 `stevia` / `stevia-phosh-osk-provider` exist ONLY in `updates`

The phosh on-screen keyboard packages (`stevia`, `stevia-phosh-osk-provider`)
are absent from the GA repository entirely and present in `updates` at
`0.54.0-1.fc43`. `phosh`/`phoc` in GA are `0.49.0-1.fc43`; `updates` carries
`0.54.0-1.fc43`. **Action taken:** the builder now enables the Fedora 43
`updates` repository (`--releasever=43`, `--setopt` repos) instead of resolving
against GA alone. Without this the build aborts on `stevia`.

### 2.3 The carried 4.14 `libsystemd` patch REQUIRES `systemd-258.11-1.fc43` from `updates`

This is the most important dependency in the whole phone.

* The GA repository ships `systemd-258-1.fc43.aarch64`.
* The carried patched library is
  `boot/s10plus/payload/libsystemd-shared-258.11-1.fc43.so` — i.e. the
  **updates** build `systemd-258.11-1.fc43.aarch64`.
* The initramfs installs that file over
  `/usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so` at boot
  (`tools/s10plus/a17/edit-init-a17.py`), and the systemd binaries locate the
  shared library by a SONAME that contains the **version-release**. If DNF
  resolves `systemd-258-1.fc43` (GA), the rootfs binary and the patched library
  do not line up: the two 4.14 source edits (see §3) would not be the code that
  actually runs, and every unit start would go back to
  `Failed to spawn executor: Function not implemented`
  (`docs/s10plus-autonomous-boot-repair/SYSTEMD-COMPATIBILITY.md`).

**Action taken:** `systemd` is pinned in the manifest and in the builder to
`systemd-258.11-1.fc43`, `systemd-udev`/`systemd-networkd` are required to be
the *same version-release*, and the builder refuses to build if the pin cannot
be satisfied. `--ga-only` is kept in the verifier precisely so the failure mode
is demonstrable:

```
[verify-packages] verdict=FAILED ... pin_mismatches=[{
  "package": "systemd", "expected": "systemd-258.11-1.fc43.aarch64",
  "available": ["systemd-258-1.fc43.aarch64"]}]
```

## 3. Protected compatibility items (do not regress)

### 3.1 `libsystemd-shared` kernel-4.14 patch

| Item | Value |
|---|---|
| Carried artifact | `boot/s10plus/payload/libsystemd-shared-258.11-1.fc43.so` |
| Base NEVRA | `systemd-258.11-1.fc43.aarch64` (updates) |
| Source edits | `src/basic/process-util.c` — fall back to `posix_spawn()` when glibc's `pidfd_spawn()` returns `ENOSYS`; `src/basic/pidref.c` — `pidref_set_pid()` degrades to a PID-only `PidRef` on `ENOSYS`/`EOPNOTSUPP`/`ENOTTY` |
| Builder | `tools/s10plus/a17/build-systemd4.sh` + `tools/s10plus/a17/nuxel-systemd-edit.py` |
| Installed by | `tools/s10plus/a17/edit-init-a17.py` (initramfs, over `/usr/lib64/systemd/`) |
| Why | Linux 4.14 has neither `pidfd_open()` (5.3) nor `waitid(P_PIDFD)` (5.4) |
| Constraint | the `systemd` RPM must stay `258.11-1.fc43`; if it moves, the patch must be rebuilt against the new NEVRA and the payload filename updated |

Still queued (documented, not a regression): the third source edit — teaching
`sd-event`'s child watcher to degrade to `waitid()` — which would let
`systemd-userdbd`, `dbus-broker` and `systemd-udevd` be un-masked. Until then
§3.2 is the shipped configuration.

### 3.2 A26 rootfs fixes (4.14 containment)

`tools/s10plus/a26/nuxel-rootfs-fixes.sh` runs on the staging tree inside the
image build (never on a phone) and applies four idempotent changes:

1. `authselect/nsswitch.conf`: drop the `systemd` varlink NSS module for
   passwd/shadow/group/gshadow (otherwise every lookup blocks forever).
2. Mask `systemd-userdbd.{service,socket}` (cannot run without pidfd child
   watching).
3. System bus → `dbus-daemon.service` (`dbus-broker-launch` dies `ENOSYS` in
   `launcher_fork`).
4. Mask `systemd-udevd` + its three sockets and set `udev_log=err` (udevd
   cannot register worker objects and forks unboundedly); devtmpfs supplies
   every node Nuxel needs.

Both items are recorded in `images/s10plus/packages-manifest.json` under
`protected_compat_items`, and `verify-packages.py` re-checks §3.1 on every run.

## 4. Verified package set

Generated directly from the repository metadata by
`python3 tools/s10plus/a33/verify-packages.py --emit-manifest`. Machine-readable
source of truth: `images/s10plus/packages-manifest.json` (`groups[].packages[]`
each carry `name` + `nevra`).

### base — Fedora base OS, init, 4.14-compatible service manager

| Package | Verified NEVRA |
|---|---|
| filesystem | `filesystem-3.18-50.fc43.aarch64` |
| setup | `setup-2.15.0-26.fc43.noarch` |
| fedora-release | `fedora-release-43-27.noarch` |
| glibc | `glibc-2.42-17.fc43.aarch64` |
| glibc-langpack-en | `glibc-langpack-en-2.42-17.fc43.aarch64` |
| bash | `bash-5.3.0-2.fc43.aarch64` |
| coreutils | `coreutils-9.7-10.fc43.aarch64` |
| util-linux | `util-linux-2.41.5-1.fc43.aarch64` |
| findutils | `findutils-1:4.10.0-6.fc43.aarch64` |
| grep | `grep-3.12-2.fc43.aarch64` |
| sed | `sed-4.9-5.fc43.aarch64` |
| gawk | `gawk-5.3.2-2.fc43.aarch64` |
| shadow-utils | `shadow-utils-2:4.18.0-3.fc43.aarch64` |
| procps-ng | `procps-ng-4.0.4-7.fc43.1.aarch64` |
| kmod | `kmod-34.2-2.fc43.aarch64` |
| e2fsprogs | `e2fsprogs-1.47.3-2.fc43.aarch64` |
| ca-certificates | `ca-certificates-2026.2.90_v9.0.317-1.fc43.noarch` |
| curl | `curl-8.15.0-10.fc43.aarch64` |
| **systemd (PINNED)** | **`systemd-258.11-1.fc43.aarch64`** |
| systemd-udev | `systemd-udev-258.11-1.fc43.aarch64` |
| systemd-networkd | `systemd-networkd-258.11-1.fc43.aarch64` |

### dbus / python

| Package | Verified NEVRA |
|---|---|
| dbus-daemon | `dbus-daemon-1:1.16.2-1.fc43.aarch64` |
| dbus-broker | `dbus-broker-37-2.fc43.aarch64` |
| python3 | `python3-3.14.8-1.fc43.aarch64` |

`dbus-broker` is installed but **not** used as the system bus on this kernel —
see §3.2 item 3. It is kept so the alternative remains one `systemctl` away.

### graphics / session (Wayland → framebuffer path)

| Package | Verified NEVRA |
|---|---|
| mesa-dri-drivers | `mesa-dri-drivers-25.3.6-3.fc43.aarch64` |
| mesa-libEGL | `mesa-libEGL-25.3.6-3.fc43.aarch64` |
| mesa-libgbm | `mesa-libgbm-25.3.6-3.fc43.aarch64` |
| libinput | `libinput-1.30.3-1.fc43.aarch64` |
| seatd | `seatd-0.9.3-1.fc43.aarch64` |
| phoc | `phoc-0.54.0-1.fc43.aarch64` |
| phosh | `phosh-0.54.0-1.fc43.aarch64` |
| stevia | `stevia-0.54.0-1.fc43.aarch64` |
| stevia-phosh-osk-provider | `stevia-phosh-osk-provider-0.54.0-1.fc43.noarch` |
| greetd | `greetd-0.10.3-6.fc43.aarch64` |

`seatd` was **missing** from the previous builder's install line even though
`services/nuxel-session/systemd/seatd.service` (carried from A31) requires
`/usr/bin/seatd`. Added.

### webkit (the launcher surface)

| Package | Verified NEVRA |
|---|---|
| gtk3 | `gtk3-3.24.52-1.fc43.aarch64` |
| webkit2gtk4.1 | `webkit2gtk4.1-2.52.5-1.fc43.aarch64` |
| gtk4 | `gtk4-4.20.4-1.fc43.aarch64` |
| libadwaita | `libadwaita-1.8.8-1.fc43.aarch64` |

`nuxel-pwa-host` (`tools/s10plus/a32/nuxel-pwa-host.c`) includes
`<gtk/gtk.h>` + `<webkit2/webkit2.h>` and links `webkit2gtk-4.1`, so the
`webkit2gtk4.1`, `gtk3` and `alsa-lib` **runtime** packages are mandatory in the
image. They were previously installed only in the VM build environment, not in
the phone rootfs — the host binary would have failed to load. Added.
`gtk4`/`libadwaita` are required by the Phosh consent agent
(`shell/nuxel-phosh-agent`).

### network / connectors

| Package | Verified NEVRA |
|---|---|
| NetworkManager | `NetworkManager-1:1.54.3-3.fc43.aarch64` |
| NetworkManager-wifi | `NetworkManager-wifi-1:1.54.3-3.fc43.aarch64` |
| ModemManager | `ModemManager-1.24.2-1.fc43.aarch64` |
| iproute | `iproute-6.14.0-2.fc43.aarch64` |
| geoclue2 | `geoclue2-2.8.2-1.fc43.aarch64` |
| bluez | `bluez-5.87+1.git8750129efca8-1.fc43.aarch64` |

`geoclue2` is the D-Bus service the bridge's `GeoClueConnector` connects to;
`bluez` is the Bluetooth owner-test subject for Priority 7b. Wi-Fi bring-up and
the Shannon/modem honesty work are owned by Priority 3 and Priority 7b; this
report only guarantees the packages exist for aarch64.

### audio / security / power

| Package | Verified NEVRA |
|---|---|
| pipewire | `pipewire-1.4.11-1.fc43.aarch64` |
| wireplumber | `wireplumber-0.5.14-1.fc43.aarch64` |
| alsa-lib | `alsa-lib-1.2.16.1-1.fc43.aarch64` |
| polkit | `polkit-126-6.fc43.2.aarch64` |
| nftables | `nftables-1:1.1.3-6.fc43.1.aarch64` |
| upower | `upower-1.91.3-2.fc43.aarch64` |

## 5. Honest limitations

* **Package existence is not hardware function.** Every NEVRA above is verified
  to exist for aarch64; none of it is evidence that the S10+ Wi-Fi, modem,
  speaker, camera or GNSS works. A registered driver is not proof of working
  hardware, and this report makes no such claim.
* **The repository is a live target.** `updates` moves. The manifest records the
  NEVRAs resolved on 2026-10-16T14:01Z and the builder re-verifies at build
  time; drift in an unpinned package is reported (WARN + recorded), drift in the
  pinned `systemd` is a build failure.
* **The metadata cache lives under `build/pkgmeta/`** (git-ignored,
  regenerable). Nothing is written to `.qq` or the QonQrete run root.
* **Package-set completeness is asserted, not proven by installation.** The
  full `dnf --installroot` run requires an aarch64 Fedora container (Docker/
  Podman Desktop) and is executed by
  `images/s10plus/build-phone-rootfs-fedora.sh`. This cycle verified metadata
  resolution + the install-list correctness offline; the container install is
  not run here.
* **Unresolved / unavailable packages: none.** 50/50 essential packages
  resolved. `basesystem` was removed from the list because it no longer exists
  in Fedora 43 (documented in §2.1) — that is a removal of a non-existent
  package, not a hidden `--skip-unavailable`.

## 6. Evidence index (reproduce everything offline)

| Claim | Command | Result |
|---|---|---|
| essential packages resolve against real Fedora 43 aarch64 metadata | `python3 tools/s10plus/a33/verify-packages.py` | `resolved` (rc 0), 50/50 |
| the systemd pin is load-bearing (GA alone fails) | `python3 tools/s10plus/a33/verify-packages.py --ga-only` | `FAILED`, names the systemd pin |
| no metadata source ⇒ no invented versions | `python3 tools/s10plus/a33/verify-packages.py --offline --cache-dir /tmp/empty` | `BLOCKED_EXTERNAL_RESOURCE` (rc 3) |
| provenance + builder install-line + pin, all offline | `python3 tools/s10plus/a33/tests/test-packages-manifest.py` | all assertions pass |
| all of Priority 4 in one command | `bash tools/s10plus/a33/tests/run-userspace-tests.sh` | `OFFLINE_TESTED` (10/10) |

The machine-readable results are written to `build/pkgmeta/` (git-ignored build
scratch, never to `.qq`/RUN_ROOT).
