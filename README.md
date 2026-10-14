# Nuxel Phone OS — Linux on Google Pixel
![Repo Views](https://komarev.com/ghpvc/?username=illdynamics-nuxel&label=Repo+Views&color=blue)

![Nuxel](./nuxel.jpg)

**v0.3.3-alpha** — _Build the bunker first. Add the rave lights later._

A hardened, GrapheneOS-spirited **Linux phone operating system** built from
scratch on a pure Linux substrate. **Zero Android dependencies.** Immutable OS.
**Flatpak-sandboxed app model** (PWA-first for mainstream apps, native GTK4 for
system apps) on a Phosh/GTK4/Wayland shell. Three device bring-ups in progress.

```text
App model:       Flatpak-sandboxed (Bubblewrap) + XDG portals
                   ├─ PWAs        — hardened WebKitGTK, isolated profiles (PWA-first)
                   └─ Native apps — GTK4/libadwaita, C/Python
Shell:           Phosh + phoc (GTK4)
Display:         Wayland only
Packaging:       Flatpak — org.gnome.Platform//46 base + org.nuxel.Platform PWA runtime
Android deps:    ZERO (no AOSP, no APK, no Play Store, no Waydroid, no libhybris)
Explicitly not:  Snap — Flatpak chosen (better portal/permission fit for this model)
No ambient trust.
VM first.
Hardware only after per-device Phase 0 gates pass.
```

---

> **Test hardware (for now).** We're currently testing Nuxel on three devices —
> not because they're the goal, but because we happen to have them lying around
> and they aren't our daily phones: **Motorola Moto G7 Power**, **Samsung Galaxy
> S10 Plus**, and **Google Pixel 10 Pro XL**. The Pixel 10 Pro XL is the target
> device.

## What is Nuxel?

Nuxel is a mobile-first Linux OS built from scratch on a pure Linux substrate.
It borrows the **security mindset** of GrapheneOS without borrowing Android as
the base platform.

| | Nuxel | Android | GrapheneOS |
|---|---|---|---|
| Base | Fedora/GNOME Flatpak runtime (immutable) | AOSP/Linux | AOSP/Linux |
| Kernel | Linux 6.12 LTS | Linux (ACK) | Linux (ACK) |
| Shell | Phosh + GTK4 | SurfaceFlinger | SurfaceFlinger |
| Apps | Flatpak: PWA (WebKitGTK) + native GTK4 | APK | APK |
| Sandbox | 5-layer + Bubblewrap/Flatpak + portals | SELinux | SELinux + hardened |
| Immutable | dm-verity + AVB | dm-verity + AVB | dm-verity + AVB |
| Android deps | **ZERO** | Full AOSP | Full AOSP |

## App Model

Nuxel has **one sandboxed app model** with two app flavours, both delivered and
confined the same way:

| Flavour | Runtime | Used for |
|---|---|---|
| **PWA (PWA-first)** | Hardened **WebKitGTK**, one isolated `WebContext` per app, shipped as a **Flatpak** | Mainstream/user-facing apps: mail, calendar, notes, files, camera, dashboards, social clients |
| **Native GTK4** | **GTK4/libadwaita** (C / Python), Flatpak- or system-confined with AppArmor | Hardware-critical & system apps: dialer, messages, contacts, settings, permissions, sandbox |

**Packaging & sandboxing.** Everything user-installable is a **Flatpak**:
Bubblewrap sandbox (Linux namespaces + seccomp + Landlock + AppArmor + nftables)
that reaches hardware, files, network and devices only through **XDG portals** and
the `nuxel-bridge` capability mediator. The immutable runtime base is
`org.gnome.Platform//46`; PWAs run on the `org.nuxel.Platform` hardened PWA
runtime and are launched with `flatpak run <app-id>` (see `pwa/flatpak/`).

> **Snap is not used.** Nuxel standardises on **Flatpak** — its portal model and
> precise D-Bus/filesystem permissions fit this phone architecture better than
> Snap's interface model, and every app is a Flatpak (there are no Snap
> manifests in this repo). Full detail: [`docs/app-store.md`](docs/app-store.md)
> and [`docs/pwa-model.md`](docs/pwa-model.md).

## Architecture

```text
┌──────────────────────────────────────────────────┐
│  Flatpak-sandboxed apps (Bubblewrap)             │
│  PWA apps        — WebKitGTK, isolated profiles  │
│  Native apps     — GTK4/libadwaita (C/Python)    │
├──────────────────────────────────────────────────┤
│  nuxel-home launcher                             │
│  nuxel-bridge (D-Bus capability mediator)        │
│  nuxel-portal (GTK4 consent dialogs)             │
│  nuxel-notifications (FDO bridge)                │
├──────────────────────────────────────────────────┤
│  Sandbox: namespaces + seccomp + Landlock        │
│          + AppArmor + nftables                   │
├──────────────────────────────────────────────────┤
│  Phosh + phoc compositor (Wayland)               │
├──────────────────────────────────────────────────┤
│  ModemManager | NetworkManager | PipeWire        │
│  GeoClue | xdg-desktop-portal                    │
├──────────────────────────────────────────────────┤
│  Linux 6.12 LTS (per-device defconfig/patches)   │
│  dm-verity system + A/B slots + AVB              │
├──────────────────────────────────────────────────┤
│  Hardware targets (see Multi-Device Targets):    │
│  Google Pixel 10 Pro XL (mustang)                │
│  Samsung Galaxy S10+     (beyond2lte)            │
│  Motorola Moto G7 Power  (ocean)                 │
└──────────────────────────────────────────────────┘
```

## Quick Start

```bash
# Read the quickstart guide
cat prompts/QUICKSTART.md

# Test in UTM VM (Apple Silicon Mac)
bash vm/nuxel-vm-bootstrap.sh
bash vm/phosh-phone-resolution.sh 414x896

# Build images (requires a cross-compiler; the device key is explicit)
NUXEL_DEVICE=mustang bash images/build.sh --quick
NUXEL_DEVICE=g7power bash images/build.sh --quick
NUXEL_DEVICE=s10plus bash images/build.sh --quick

# Flash to hardware (per-device; requires an unlocked device)
NUXEL_DEVICE=mustang bash boot/flash.sh --unlock --wipe

# Bring-up guides
#   Moto G7 Power (SDM632, ocean):  docs/g7power-bringup.md
#   Galaxy S10+   (Exynos 9820):    docs/s10plus-bringup.md
#   Pixel 10 Pro XL (mustang):      docs/pixel10proxl-device-inventory.md
```

## Project Structure

| Directory | Contents |
|---|---|
| `services/` | Core D-Bus services (bridge, portal, notifications) |
| `shell/` | Native GTK4 apps (dialer, messages, contacts, settings, permissions) + `nuxel-sandbox` |
| `pwa/` | Progressive Web Apps + Flatpak manifests (`pwa/flatpak/`) + PWA launcher |
| `boot/` | Shared initramfs + per-device flash/recovery/boot config |
| `images/` | Per-device build orchestration (kernel → rootfs → signing) |
| `kernel/` | Per-device defconfig + patches (mustang, s10plus, g7power) |
| `configs/` | Shared security configs + per-device display/audio/touch |
| `tools/` | Device selection, AVB key generation, image signing, boot-image tooling |
| `vm/` | UTM VM bootstrap, phone resolution, snapshots |
| `docs/` | Architecture, security model, build guide, device setup |
| `phones/` | Per-device documentation bundles (`g7power/`, `s10plus/`, `pixel10proxl/`) |
| `prompts/` | Planning / analysis prompt archive (historical reference) |
| `device/` | Per-device postmarketOS package + deviceinfo |
| `firmware/` | Per-device firmware manifests, install/verify, blobs |
| `ci/` | Build validation |
| `assets/` | Wallpaper + boot animation |

## What's new in v0.3.3-alpha

A **flashing-proven** release: the full Nuxel image set now writes to the Galaxy
S10+ and verifies on the device — the phone reaches the Samsung boot logo. Full
detail in **[CHANGELOG.md](CHANGELOG.md)**.

- **The S10+ full-image flash is proven on hardware.** The merged-DTB boot image
  (`nuxel-beyond2lte-boot.img`) and the Fedora 43 aarch64 phone rootfs
  (`nuxel-beyond2lte-rootfs-fedora-phone.img`) were written to BOOT + USERDATA
  over ADB and read back **byte-for-byte** from the device. Flashing is no longer
  in question; the handset now **bootloops on the Samsung logo**, so the
  remaining work is boot-chain / kernel / root-mount bring-up, not transfer.
- **The S10+ release job builds the real image set.** `.github/workflows/release.yml`
  now builds the merged board-DTB boot image (with an explicit board revision)
  and the Fedora 43 ARM64 phone rootfs in an arm64 container, then verifies both
  with `tools/s10plus/verify-fedora-phone-rootfs.py` — never a skeleton rootfs.
- **A bootloop debug pack ships** (`scripts/s10plus-debug-pack/`): read-only
  ADB/TWRP capture of pstore/last_kmsg, recovery logs, partition maps and an
  offline boot-image/rootfs inspection, for isolating the Samsung-logo loop.
- **Version bump to v0.3.3-alpha** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder.

## What's new in v0.3.2-alpha

A **rootfs-completeness** release: the release CI now builds the *same* rootfs a
local build does. Full detail in **[CHANGELOG.md](CHANGELOG.md)**.

- **Boot splash restored in CI.** `images/mkrootfs.sh` builds the Plymouth boot
  theme through `tools/build-nuxel-boot-theme.sh`, which needs **`ffmpeg`** to
  extract the animation frames. The release workflow never installed it, so the
  (deliberately non-fatal) theme step silently degraded: the published S10+
  rootfs carried ~20 MB of content instead of the ~60 MB a local build produces
  (96 frame PNGs ≈ 50 MB plus the boot-animation MP4 were gone). `ffmpeg` is now
  a required CI build dependency.
- **The artifact gate is fail-closed on the boot splash.**
  `tools/verify-artifacts.sh` now requires the boot-animation MP4 (≥ 1 MB) and
  the generated Plymouth theme (`nuxel.plymouth` + `frame-0001.png`) inside each
  device rootfs image, so a build that silently drops them goes **red** instead
  of shipping a thin image.
- **Version bump to v0.3.2-alpha** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder.

## What's new in v0.3.1-alpha

A correctness release: the bring-up rootfs now actually contains a userspace, and
the artifact gate can no longer pass a near-empty image off as "complete". Full
detail in **[CHANGELOG.md](CHANGELOG.md)**.

- **`images/mkrootfs.sh` actually runs now.** Its userspace steps were defined
  but never called, so every "rootfs" was only the per-device config overlay
  (the S10+ archive shipped a 44 KB, 10-file image). The builder now populates
  the core services, security configs, assets and init files.
- **`tools/verify-artifacts.sh` is fail-closed on content, not just magic.** It
  parses the Android boot header (kernel/ramdisk/dtb must be non-empty) and reads
  the ext4 rootfs with `debugfs` to require the device payload and
  `/usr/bin/nuxel-bridge`. The v0.3.0-alpha S10+ image would now fail the gate.
- **No more 512 MB rootfs.** Rootfs images are sized from real content
  (64 MB floor) instead of the old 512 MB floor.
- **S10+ no longer reports a phantom `INCOMPLETE`** for the mainline-only U-Boot
  artifact; the downstream set (`boot.img` + `rootfs.img`) is complete as
  documented, and `NUXEL_S10PLUS_UBOOT=1` makes U-Boot required for mainline.
- **Version bump to v0.3.1-alpha.**

## What's new in v0.3.0-alpha

A release-pipeline release: the GitHub **Release** workflow is now **fail-closed
and genuinely green** for the two bring-up phones; full detail in
**[CHANGELOG.md](CHANGELOG.md)**.

- **Every build/release step now actually produces its artifact, and a failed
  build can no longer go green.** All `continue-on-error` flags were removed
  from the build matrix, and a new strict gate
  `tools/verify-artifacts.sh` asserts (per device) that the kernel `Image.gz` is
  a real gzip'd **ARM64 Linux Image**, the board DTB is a valid FDT, the boot
  image carries the `ANDROID!` header, the rootfs is `ext4`, and — on G7 Power —
  that `lk2nd.img` exists. The `publish release` job runs only when the whole
  matrix succeeded, so a red run never creates a release.
- **`mustang` (Pixel 10 Pro XL) removed from the workflow** for now — the matrix
  is `g7power` + `s10plus` only.
- **S10+ boot image now builds in CI.** The downstream Exynos 9820 tree ships
  only the SoC base DTB + per-revision `.dtbo` overlays; `images/s10plus/build.sh`
  now merges base + highest-rev overlay into `exynos9820-beyond2lte.dtb` with
  `fdtoverlay` before packing (previously it aborted with "No beyond2lte DTB
  found"). The Nuxel **rootfs** is now produced by the same workflow.
- **G7 Power `lk2nd.img` is now built in CI** (`boot/g7power/lk2nd/build-lk2nd.sh`,
  `msm8916-mainline/lk2nd` → `lk2nd-msm8953`), so the flashed boot chain is
  complete. The shared initramfs is now built by a first-class
  `images/build.sh --initramfs-only` step instead of the old mustang dispatcher.
- **Version bump to v0.3.0-alpha** across `VERSION`, README, docs/design
  headers, the shell apps, the PWA manifest, the device `APKBUILD`s, the VM
  tooling and the OTA builder.

## What's new in v0.2.2-alpha

A small pre-release on top of **v0.2.1-alpha**; full detail in
**[CHANGELOG.md](CHANGELOG.md)**.

- **S10+ kernel build fixed for real in CI.** Forcing `CROSS_COMPILE` and
  dropping the compiler-unsupported KCFLAGS (v0.2.1-alpha) was not enough: on
  the runner's GCC 13 the downstream 4.14 tree still hard-codes `-Werror` in two
  places a `KCFLAGS` relaxation cannot reach — per-category
  `$(call cc-option,-Werror=<diag>)` promotions in the top `Makefile`
  (`block/blk-crypt.c:213: error: function declaration isn't a prototype
  [-Werror=strict-prototypes]`) and per-directory flags that land *after*
  `KBUILD_CFLAGS` (the bcmdhd Wi-Fi driver's `DHDCFLAGS += -Wall -Werror ...`,
  `wl_android.c:12016: error: the comparison will always evaluate as 'true' ...
  [-Werror=address]`). The wrapper now strips those tokens from its scratch tree
  via the new `tools/kernel-relax-werror.sh`, so the build compiles past both.
- **Pixel 10 Pro XL (`mustang`) kernel build fixed.** The
  `0001-nuxel-phone-features.patch` carried a corrupt hunk header
  (`@@ -0,0 +1,108 @@` for a 107-line `drivers/nuxel/nuxel-core.c`), so `git apply`
  failed with `error: corrupt patch` and the build never started. The header is
  corrected and the patch now applies cleanly to the `android16-6.12` GKI tree;
  the mustang dispatcher also gained a `-Wno-error`/`-Wno-error=parentheses`
  KCFLAGS relaxation (the GKI `CONFIG_WERROR=y` dies on
  `fs/fuse/dev.c:458` `[-Werror=parentheses]` under GCC 13).
- **Version bump to v0.3.0-alpha** across `VERSION`, README, docs/design
  headers, the shell apps, the PWA manifest, the device `APKBUILD`s, the VM
  tooling and the OTA builder.

## What's new in v0.2.1-alpha

A small pre-release on top of **v0.2.0**; full detail in
**[CHANGELOG.md](CHANGELOG.md)**.

- **S10+ kernel build fixed.** Three toolchain/tooling issues killed
  `kernel/s10plus/build-kernel.sh` before it produced an `Image.gz`: (1) the
  downstream Samsung Exynos 9820 Makefile hardcodes its internal Android
  toolchain as the default `CROSS_COMPILE` (`.../aarch64-linux-android-`), which
  is not shipped, so `make` reported
  `aarch64-linux-android-gcc: No such file or directory` — the wrapper now always
  passes an explicit `CROSS_COMPILE` (default `aarch64-linux-gnu-`, overridable
  with `--cross` / `$CROSS_COMPILE`) that overrides the tree default; and (2) the
  wrapper's `-Wno-error=return-mismatch` relaxation is a **hard error** on GCC 13
  (which CI uses), because `-Wreturn-mismatch` only exists in GCC >= 14 — and the
  tree appends `$(KCFLAGS)` to `KBUILD_CFLAGS`, so the unknown flag made every
  `cc-option` probe fail and produced the misleading
  `Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not
  supported by compiler` — the wrapper now probes each relaxation against the
  selected compiler and drops unsupported ones; and (3) the downstream Makefile
  compiles with a global `-Werror`, so ordinary warnings (e.g. `-Wformat=` on
  `phys_addr_t` in `arch/arm64/mm/fault.c`) aborted the build — the wrapper now
  appends a bare `-Wno-error` (last, via `KCFLAGS`) to downgrade the tree's
  `-Werror` back to warnings.
- **Version bump to v0.2.1-alpha** across `VERSION`, README, docs/design headers, the
  shell apps, the PWA manifest, the device `APKBUILD`s, the VM tooling and the
  OTA builder.

## What's new in v0.2.0

Everything below landed between **v0.1.0** (the mustang-only scaffold) and this
release. Full detail, per area, is in **[CHANGELOG.md](CHANGELOG.md)**.

- **Three device targets, not one.** `mustang` (Pixel 10 Pro XL) is now joined
  by two active bring-ups: `s10plus` (Samsung Galaxy S10+, Exynos 9820,
  `beyond2lte`) and `g7power` (Motorola Moto G7 Power, SDM632/msm8953, `ocean`).
- **Per-device orchestration + safety gates.** Every device has its own
  `firmware/ kernel/ device/ boot/ configs/ images/` subtree, resolved by
  `tools/nuxel-device-select.sh`. Every build/flash script hard-guards its
  device key and enforces a **Phase 0 inventory gate** so nothing can be built
  or flashed with `PLACEHOLDER`/`UNKNOWN` load addresses or firmware names.
- **G7 Power bring-up advances.** Touchscreen root-caused and fixed (ILI2117 is
  handled by mainline `ili210x` / `CONFIG_TOUCHSCREEN_ILI210X`, *not* a
  nonexistent `CONFIG_TOUCHSCREEN_ILI2117`); an on-device **stock-evidence**
  bundle captured (`phones/g7power/stock-evidence/`); lk2nd boot chain worked
  out — including a QCDT boot-image packer (`tools/build-qcdt-boot.py`) that
  fixes the "lk2nd menu then black screen" packaging bug — plus a two-phase
  fastboot flash flow and an EDL unbrick path; the images are now **flashed to
  the device**, which powers on but still hangs at a black/flashy screen
  (display init not yet resolved).
- **S10+ bring-up scaffolded, boot partition flashed.** Documented Exynos boot
  chain (S-Boot → U-Boot → Linux), the no-fastboot reality (TWRP + Download
  Mode/heimdall), Knox-tripped constraints, anti-cross-flash rules, and a Phase 0
  inventory template; only the **boot partition** is on the device so far
  (heimdall BOOT 100%), with Download Mode balky and a manual flash attempt next.
- **Pixel/mustang prep.** Phase 0 inventory template + build gate and a
  reconciliation of the mustang path against the multi-device layout.
- **Repo hygiene.** Device documentation bundles were consolidated under
  `phones/` (`g7power/`, `s10plus/`, `pixel10proxl/`); the loose planning and
  analysis prompts now live under `prompts/`.
- **Version bump to v0.2.0** across `VERSION`, README, docs/design headers, the
  shell apps (meson + metainfo), the PWA manifest, the device `APKBUILD`s, the
  VM tooling and the OTA builder.

**Readiness at a glance:** a documented scaffold with a **bootable UTM VM
demo** and **built flash images for two of three phones — both partly pushed to
hardware, neither booting Nuxel yet**. **0 of 3 phones have booted a Nuxel-built
image.** The honest
per-area breakdown is the table below; the "what's left" list is in the
changelog.

## Honest Status — v0.3.3-alpha


**S10+ October 14 status — flashing is proven, boot is not.** Read
[S10PLUS-PROGRESS.md](S10PLUS-PROGRESS.md) for area-by-area percentages and
evidence. The **full Nuxel image set** — the merged-DTB boot image plus the
Fedora 43 aarch64 phone rootfs (real Python, systemd, Phosh and Phoc RPM
binaries, built by `images/s10plus/build-phone-rootfs-fedora.sh`) — has been
**written to the handset over ADB and read back byte-for-byte**. The device now
**bootloops on the Samsung logo**: transfer, partition sizing and the storage
handoff are no longer the problem — S-Boot/kernel/root-mount bring-up is. That
is exactly what the new bootloop debug pack (`scripts/s10plus-debug-pack/`)
exists to isolate. No successful hardware boot or Phosh display has been
demonstrated yet. Read
[the final Mac guide](macbook-s10plus-flash-guide-final-full.md) before flashing.


**Nuxel is a design scaffold with three device bring-ups in progress and a bootable UTM VM proving out the architecture. No phone has yet booted a Nuxel-built image.**

| Area | Score | Notes |
|---|---|---|
| Design/docs | 78% | Architecture, security model, PWA spec, three device doc bundles |
| Repo structure | 85% | Clean layout; device doc bundles consolidated under `phones/` |
| PWA apps | 45% | Manifests, SWs, JS exist — need integration testing |
| Flatpak app model | 20% | Manifests + launcher exist (`pwa/flatpak/`, `org.nuxel.Platform`); runtime not built or integration-tested |
| Native GTK apps | 25–35% | C source exists, not proven buildable on aarch64 |
| D-Bus bridge/portal | 30% | Python parses, dev-grade auth, not integration-tested |
| Sandbox/security | 20% | Configs exist, enforcement not wired end-to-end |
| Build system | 58% | Per-device dispatchers + inventory gates; the **fail-closed release CI builds `g7power` + `s10plus`** — the S10+ job now produces the merged board-DTB boot image and the Fedora 43 ARM64 phone rootfs (arm64 container) and gates them with `tools/verify-artifacts.sh` + `tools/s10plus/verify-fedora-phone-rootfs.py`; G7 Power keeps its lk2nd + boot + ext4 chain. Still unproven on hardware |
| Flashable images | 80% | Real, checksummed artifacts for **g7power** (lk2nd + boot + ext4 rootfs) and **s10plus** (merged-DTB boot + Fedora 43 ARM64 phone rootfs). Both are **flashed to hardware**; the **S10+ full image set was read back byte-for-byte** (transfer proven) — **0 of 2 verified booting** |
| Pixel 10 Pro XL (mustang) | 5% | Public mustang Linux is UART/initramfs-level only; no boot artifact built yet |
| Galaxy S10+ (beyond2lte) | 55% | Downstream 4.14 boot image builds with the rev-26 board DTBO merged via `fdtoverlay`; the merged boot image + Fedora 43 ARM64 phone rootfs (Python/systemd/Phosh/Phoc) are **flashed over ADB and read back byte-for-byte** — **flashing proven**. The phone now **bootloops on the Samsung logo**; S-Boot handoff, kernel bring-up and root mount remain unverified |
| Moto G7 Power (ocean) | 40% | Boot + ext4 rootfs images **flashed to hardware** (touch-driver fix, lk2nd/QCDT chainloader); device powers on but hangs at a **black/flashy screen** — not yet booting Nuxel |
| UTM VM | 70% | A genuine **Nuxel UTM bundle exists and boots** — Fedora 43 + Phosh at 720×1440 (live screenshots), Nuxel services + PWA on the desktop, guest SSH + **internet verified working**, and **sound works** via a `virtio-sound-pci` device (`virtio_snd` ALSA card, in-guest playback verified); bundle is a local artifact (`artifacts/vm/`, gitignored, not committed) |

**Overall: ~45–50% MVP scaffold. 2 of 3 phones produce built, checksummed images from a fail-closed CI and both are flashed to hardware; the S10+ full image set is now transfer-proven (byte-for-byte readback) and bootloops on the Samsung logo, while G7 Power hangs at a black screen. 0 of 3 verified booting. The UTM VM demo boots and works (display + network + sound).**

### What this repo IS:
- A well-documented architecture blueprint for a Linux phone OS
- Working PWA shells with service workers and manifests
- Real Python D-Bus services (bridge, portal, notifications)
- Real native GTK4 C app source code
- Flatpak manifests + a PWA launcher (`pwa/flatpak/`, `pwa/launcher/`)
- Complete security configuration files (AppArmor, nftables, hardened_malloc)
- Build/flash/sign/recovery scripts as architectural planning material
- UTM VM testing scripts, plus a **booted UTM VM** (local artifact) running Phosh + the Nuxel service stack at phone resolution

### What this repo HAS now (verified this cycle):
- A **bootable UTM VM** — Fedora 43 + Phosh at 720×1440, Nuxel services + PWA
  live on the desktop, guest SSH reachable and **internet working** (bundle is a
  local, gitignored artifact under `artifacts/vm/`)
- **A green, fail-closed release CI.** The `Release` workflow run for tag
  `v0.3.0-alpha` completed **success** for the `g7power` + `s10plus` matrix (the
  `mustang` job is not in the matrix), including the strict
  `tools/verify-artifacts.sh` gate. Artifacts are reproducible per device and
  shipped with a per-device `sha256sums.txt`; a red run can no longer create a
  release.
- **Working VM audio** — the UTM bundle exposes a `virtio-sound-pci` device
  (`Sound` → `Hardware: virtio-sound-pci` in `config.plist`); the guest binds it
  with `virtio_snd` and enumerates it as ALSA card 0
  (`[SoundCard] virtio-snd — VirtIO SoundCard`). Playback was verified in-guest
  (`aplay` → exit 0, PCM state `RUNNING`, `hw_ptr` advancing), bridged to the
  host through QEMU's audiodev → UTM/CoreAudio. Setup lives in
  `vm/build-vm-image.sh` (device) and `vm/nuxel-vm-bootstrap.sh`
  (`install_audio_virtio`)
- **Built, checksummed, and flashed images for two of three phones**
  — `g7power` (`nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`, `lk2nd.img`,
  sha256-verified against the build manifest) is **flashed to hardware** but so
  far only reaches a black/flashy screen; `s10plus` (`nuxel-beyond2lte-boot.img`
  + the Fedora 43 ARM64 `nuxel-beyond2lte-rootfs-fedora-phone.img`) is **flashed
  over ADB and read back byte-for-byte** and now **bootloops on the Samsung
  logo** — transfer proven, boot not yet

### What this repo IS NOT YET:
- A phone that boots Nuxel on real hardware (no target has booted a Nuxel-built
  image)
- A flashable Pixel ROM (`mustang` has no boot artifact yet)
- A daily-driver phone
- A built Flatpak PWA runtime
- Hardware-validated

### Measured code footprint (accuracy note)

Earlier prose (and `docs/roadmap.md`, `docs/milestones.md`) repeated an inflated
**"~25K lines"** figure for the native core. The verified, reproducible
measurements are far lower but reflect **real, present code**. The full
single-source-of-truth is **[docs/repo-audit.md](docs/repo-audit.md)**; the
headline numbers, re-measured on this cycle, are:

```text
corrected cycle: claimed 25K, actual core ~7.2K
```

```bash
# Pure-Python "true core" across services/ + shell/:
find services/ shell/ -name '*.py' | xargs wc -l
#    => 7,234 lines (services/ 2,863 + shell/ 4,371)

# Python + C (the command the older prose quoted):
find services/ shell/ -name '*.py' -o -name '*.c' | xargs wc -l
#    => 12,246 lines

# Full .py/.c/.js cross-tree total (services + shell + pwa):
find services/ shell/ pwa/ \( -name '*.py' -o -name '*.c' -o -name '*.js' \) | xargs wc -l
#    => 18,036 lines
```

The pure-Python core (bridge, portal, notifications services, the Phosh agent,
firstboot, and the native home in `services/` and `shell/`) is **~7.2K lines**.
Adding the C sources brings Python + C to **12,246** lines. The full
Python + C + JavaScript cross-tree total (which includes the PWA bridge and the
home/launcher JS) is **18,036** lines. The sandbox subsystem is **2,005** lines
(`shell/nuxel-shell/nuxel-sandbox/sandbox.c`, with `sandbox.h` at 256 and
`nftables.sh` at 315), **not** the ~20K previously documented.

**Most "gaps" are already present in the repo, not missing.** In particular:
- **systemd units** — `services/{bridge,portal,notifications}/systemd/*.service`,
  `services/nuxel-web.service`,
  `shell/config/systemd-user/{nuxel-home-native,nuxel-home-kiosk,nuxel-phosh-agent}.service`,
  `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service`,
  `configs/apparmor/systemd/nuxel-apparmor-enforce.service`
- **D-Bus policy configs** —
  `services/{bridge,portal,notifications}/dbus/*.conf` and `configs/dbus/*.conf`
- **OpenRC init scripts** — `shell/config/openrc/{nuxel-bridge,nuxel-portal,nuxel-notifications,nuxel-firstboot}`

These exist as committed files (verified in the audit checklist); what remains
is integration/wiring, not authoring.

### Development path:
1. **Now**: Fix scripts, validate syntax, test PWAs in browser ✅ Done
2. **Next**: Build the Flatpak PWA runtime, boot Phosh in a VM, run bridge/portal locally
3. **Later**: Prove kernel build for the bring-up targets, produce real boot images
4. **Eventually**: Flash to hardware only after bootloader/display/touch/storage/WiFi/modem gates pass

**Build the bunker first. The rave lights come later.**

## Security Model

- **5-layer sandbox**: Linux namespaces → seccomp BPF → Landlock → AppArmor → nftables
- **Flatpak everywhere**: user-installable apps ship as Flatpak bundles (Bubblewrap) — no ambient filesystem/network/device access
- **Portals everywhere**: hardware, files, network and D-Bus access only via `nuxel-bridge` + XDG portals, with explicit user consent
- **Immutable OS**: read-only system partition, dm-verity, atomic A/B updates, rollback
- **Verified boot**: AVB 2.0 chain, user-controlled signing keys, bootloader relock
- **Hardened allocator**: GrapheneOS-style hardened_malloc (zero-on-free, canary, guard slabs)
- **Wayland only**: no X11, no XWayland, per-app surface isolation
- **No Android**: no Waydroid, no Halium, no libhybris, no APK, no AOSP
- **No Snap**: Flatpak is the single app packaging/sandbox format

## Multi-Device Targets

Nuxel supports multiple hardware targets. Select via `NUXEL_DEVICE` or `--device`:

| Key | Device | Codename | Status |
|---|---|---|---|
| `mustang` | Google Pixel 10 Pro XL | mustang | Scaffold — no boot artifact yet |
| `s10plus` | Samsung Galaxy S10+ (Exynos) | beyond2lte | Boot partition flashed only via heimdall (Download Mode flaky); boot unconfirmed |
| `g7power` | Motorola Moto G7 Power (ocean) | ocean | **Flashed to hardware** — powers on but stuck at a black/flashy screen |

Every device-specific **build** artifact lives under a per-device directory
keyed by `NUXEL_DEVICE`: `google-pixel-10-pro-xl/` (mustang), `s10plus/`,
`g7power/` across `firmware/`, `kernel/`, `device/`, `boot/`, `configs/` and
`images/`. `tools/nuxel-device-select.sh` resolves the key (CLI `--device` >
`NUXEL_DEVICE` env > explicit error; aliases `s10plus|beyond2lte`,
`g7power|ocean`) and every per-device script sources it and prints the resolved
key before any work.

Each device's **documentation bundle** (requirements, implementation prompt,
quickstart, go-guide and — for the G7 Power — the on-device stock-evidence
capture) lives under [`phones/`](phones/): `phones/pixel10proxl/`,
`phones/s10plus/` and `phones/g7power/`.

Two of the three targets now have real, checksummed boot artifacts, and **both
have been pushed to hardware — but none has been verified to boot Nuxel**. The
G7 Power (SDM632/msm8953, fastboot + lk2nd + EDL) is further along: its boot
image, writable ext4 rootfs and lk2nd chainloader are **flashed to the device**,
which now powers on but hangs at a black/flashy screen (display init unresolved).
The S10+ (Exynos 9820, no fastboot; TWRP + Download Mode/heimdall) has the
**full image set flashed over ADB** (merged-DTB boot + Fedora 43 ARM64 phone
rootfs), read back byte-for-byte; it now **bootloops on the Samsung logo**, so
the remaining work is boot-chain and root-mount bring-up, not transfer. The
mustang path remains a scaffold with no boot artifact.

See `docs/s10plus-bringup.md` for the S10+ bring-up guide,
`docs/g7power-bringup.md` for the G7 Power bring-up guide, and the per-device
"do it now" checklists at
[`phones/s10plus/s10plus-go-guide.md`](phones/s10plus/s10plus-go-guide.md) and
[`phones/g7power/g7power-go-guide.md`](phones/g7power/g7power-go-guide.md).

## Hardware Targets

**Primary reference target — Google Pixel 10 Pro XL (`mustang`):**

| Spec | Value |
|---|---|
| Device | Google Pixel 10 Pro XL |
| Codename | mustang |
| Serial | 58211FDCQ001LA |
| HW / SKU | MP1.0 / G45RY |
| SoC | Google Tensor G5 (gs501) |
| GPU | Imagination PowerVR DXT-72-2304 |
| Modem | Samsung Exynos 5500 |
| Display | Samsung AMB655X 3120×1440 @120Hz |
| Touch | Samsung S6SY791 |
| WiFi | Broadcom BCM4390 (WiFi 7) |
| Kernel | Linux 6.12 LTS |

The other two bring-up targets are the **Samsung Galaxy S10+** (Exynos 9820,
`beyond2lte`) and the **Motorola Moto G7 Power** (Qualcomm SDM632/msm8953,
`ocean`); their component IDs live in [`docs/hardware-ids.md`](docs/hardware-ids.md).

## Requirements

### For UTM VM testing:
- macOS on Apple Silicon (M1/M2/M3/M4)
- UTM.app
- Fedora/Debian ARM64 ISO

### For building images:
- AArch64 cross-compiler (`aarch64-linux-gnu-gcc`)
- Linux 6.12 kernel source (per-target branch)
- GTK4/libadwaita development libraries
- **Flatpak** + `flatpak-builder` (`org.gnome.Platform//46` runtime base)

### For flashing to hardware:
- The target device with an unlocked bootloader
  (`mustang`/`g7power`: fastboot; `s10plus`: TWRP + Download Mode/heimdall)
- Google/Samsung/Motorola factory image where applicable (for firmware extraction)
- fastboot + adb (plus heimdall for the S10+)
- A completed Phase 0 device inventory for the target (build gates stay closed otherwise)

## Documentation

| Document | Description |
|---|---|
| [CHANGELOG.md](CHANGELOG.md) | Release notes — everything from v0.1.0 to v0.3.3-alpha + readiness |
| [prompts/QUICKSTART.md](prompts/QUICKSTART.md) | Get running in 5 minutes |
| [design/nuxel-linux-phone-design.md](design/nuxel-linux-phone-design.md) | Design bible — the full vision |
| [design/Nuxel Phone OS Project Plan and Architecture.md](design/Nuxel%20Phone%20OS%20Project%20Plan%20and%20Architecture.md) | Technical architecture + component map |
| [docs/architecture.md](docs/architecture.md) | Immutable OS architecture |
| [docs/security-model.md](docs/security-model.md) | Sandbox, mitigations, boot chain |
| [docs/app-store.md](docs/app-store.md) | App distribution model (Flatpak + portals, signed packages) |
| [docs/pwa-model.md](docs/pwa-model.md) | Hardened PWA runtime spec |
| [docs/build-guide.md](docs/build-guide.md) | Full build pipeline |
| [.github/workflows/release.yml](.github/workflows/release.yml) | Tag-triggered build → GitHub Release pipeline |
| [docs/device-setup.md](docs/device-setup.md) | Mustang hardware setup |
| [docs/bootloader-unlock-guide.md](docs/bootloader-unlock-guide.md) | Unlock + relock guide |
| [docs/driver-status.md](docs/driver-status.md) | Hardware driver matrix |
| [docs/hardware-ids.md](docs/hardware-ids.md) | Canonical hardware component IDs (all targets) |
| [docs/milestones.md](docs/milestones.md) | Development progress |
| [docs/roadmap.md](docs/roadmap.md) | Future plans |
| [docs/update-strategy.md](docs/update-strategy.md) | Immutable/atomic update strategy |
| [docs/s10plus-bringup.md](docs/s10plus-bringup.md) | S10+ (Exynos) bring-up guide — boot chain, TWRP/heimdall flash, Phase 0 |
| [docs/s10plus-device-inventory.md](docs/s10plus-device-inventory.md) | S10+ Phase 0 device inventory template + build gate |
| [docs/g7power-bringup.md](docs/g7power-bringup.md) | G7 Power (ocean) bring-up guide — boot chain, two-phase fastboot, dtbo-first rule, EDL unbrick |
| [docs/g7power-device-inventory.md](docs/g7power-device-inventory.md) | G7 Power Phase 0 device inventory template + build gate |
| [docs/pixel10proxl-device-inventory.md](docs/pixel10proxl-device-inventory.md) | Pixel 10 Pro XL Phase 0 device inventory template + build gate |
| [docs/service-graph.md](docs/service-graph.md) | Service dependency graph |
| [docs/repo-audit.md](docs/repo-audit.md) | Measured LOC, file inventory, verified-exists checklist |
| [phones/g7power/g7power-go-guide.md](phones/g7power/g7power-go-guide.md) | G7 Power (ocean) "do it now" flash checklist |
| [phones/s10plus/s10plus-go-guide.md](phones/s10plus/s10plus-go-guide.md) | S10+ (beyond2lte) "do it now" flash checklist |
| [phones/pixel10proxl/pixel10proxl-go-guide.md](phones/pixel10proxl/pixel10proxl-go-guide.md) | Pixel 10 Pro XL (mustang) "do it now" flash checklist |

## Releasing

Build outputs (`build/out/<device>/`) are git-ignored — they are produced by the
scripts in `images/` and `kernel/`, not committed. To publish them on GitHub:

* **Automated (recommended):** push a version tag (`git tag v0.3.3-alpha && git push
  origin v0.3.3-alpha`). [`.github/workflows/release.yml`](.github/workflows/release.yml)
  builds every device on an Ubuntu runner (`make assets`, the shared initramfs,
  each `kernel/<dev>/build-kernel.sh`, then `images/<dev>/build.sh`), packages
  each `build/out/<device>/` directory and creates a GitHub Release with the
  archives + `SHA256SUMS.txt` attached. Devices whose toolchain/kernel source is
  unavailable in CI are skipped without blocking the others.
* **Manually / locally:** run the packager against an existing build tree, then
  upload the archives yourself:

  ```bash
  tools/package-release.sh --version "$(cat VERSION)"   # -> dist/
  ```

  Add `--device g7power` to package a single device, or `--from-assets` to
  (re)generate `SHA256SUMS.txt` + `RELEASE-NOTES.md` over archives already in
  `dist/`.

## License

Nuxel is released under the **MIT License**. See [LICENSE](LICENSE) for the
full text. Maintained by [RikkeTik](https://rikketik.dev).

```text
MIT License

Copyright (c) 2026 RikkeTik (https://rikketik.dev)
```

**Third-party components keep their own licenses** and are *not* covered by the
MIT grant above. This includes, but is not limited to:

| Component | License |
|---|---|
| Linux kernel and patches | GPL-2.0-only |
| `external/avbtool` (AOSP) | MIT |
| `bin/toybox` | 0BSD |

Any file that carries an explicit `SPDX-License-Identifier` or copyright header
is governed by that header, which overrides the project-wide MIT terms for that
file.

## Non-Goals

- No Android app compatibility (no APKs, no Play Store)
- No Waydroid, Halium, or libhybris
- No Snap — Flatpak is the single app packaging/sandbox format
- No KDE or Qt — GTK4/libadwaita only
- No X11 — Wayland only
- No banking/government app compatibility promises
- No daily-driver claim until hardware gates pass

---

_Build the bunker first. Add the rave lights later._

---

<!-- Reconciliation & code-size accuracy owned by the Repo state audit & doc reconciliation build group (briq-01-audit). Single source of truth for all measured counts: docs/repo-audit.md. -->
