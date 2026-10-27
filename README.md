# Nuxel Phone OS — Linux on Google Pixel
![Repo Views](https://komarev.com/ghpvc/?username=illdynamics-nuxel&label=Repo+Views&color=blue)

![Nuxel](./nuxel.jpg)

**v0.7.0-beta** — _Build the bunker first. Add the rave lights later._

> **v0.7.0-beta (2026-10-27).** This release merges the 25000–29000 work:
> the Tri-Link serial/Wi-Fi/USB console entries, the unlock-to-Home repair,
> canonical GPS/Maps state, and first-class Bluetooth, Location, Audio and
> Displays pages backed by real hardware providers. Bluetooth scanning is
> **honestly blocked**, not faked: the BCM4375 HCD is present and verified,
> but the running kernel has `CONFIG_BT_HCIUART` unset, so no HCI transport can
> register `hci0`. GNSS firmware, HDMI/DRM and the MADERA unmute path remain
> documented blockers. A completed GitHub Release is not proof of on-phone
> function; physical audio confirmation is still the owner's test. See
> [`docs/releases/v0.7.0-beta.md`](docs/releases/v0.7.0-beta.md).

> **Samsung S10+ engineering reality.** The active `beyond2lte` port is Fedora
> 43 aarch64 on Samsung Linux 4.14.253. Its launcher is Nuxel Home in WebKitGTK,
> running under headless Phoc and presented through the DECON framebuffer
> screencopy bridge; it is not native DRM/KMS acceleration. A34 captured real
> finger taps opening Mail and Calendar. Sustained touch navigation, the system
> keyboard, cold-boot presentation and Power behavior still require owner
> acceptance for full hardware sign-off in `v0.5.2-beta`; see
> [`docs/beta-finalization/v0.5.2/RELEASE-VERDICT.md`](docs/beta-finalization/v0.5.2/RELEASE-VERDICT.md).

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

## What's new in v0.7.0-beta

- **Tri-Link consoles (25000/26000/28000).** Serial Live Console, Wi-Fi SSH
  Console and USB SSH Console are registered exactly once, launch from the
  Applications drawer, and share one transport-status API. Serial keeps its
  exclusive lock and framed verified transfer; Wi-Fi SSH uses a pinned Ed25519
  host key and public-key auth; USB-NCM reports the measured kernel-panic
  blocker instead of pretending to connect.
- **Unlock → Home.** The A80 state-machine fix removes the stale launcher route
  after a successful unlock and refuses locked deep links.
- **GPS/Maps (27000).** Location exposes provider, permission, searching,
  no-fix, stale-fix and fresh-fix states separately. Maps consumes the same
  canonical provider and never treats a pin or cached coordinate as a fix.
- **Hardware Settings (29000).** Bluetooth, Location, Audio and Displays pages
  read the same authoritative state as Quick Settings. Audio shows the real
  ALSA cards/PCMs and writes the discovered low-volume mixer control; Bluetooth
  shows rfkill/BlueZ/firmware/HCI-transport evidence; Displays reports the
  missing `CONFIG_DRM` layer honestly.
- **Bluetooth correction.** The BCM4375 HCD is now present and SHA-256
  verified, but this kernel has `CONFIG_BT_HCIUART` unset. The provider reports
  `BLOCKED_KERNEL` with that exact evidence; a userspace blob alone cannot
  create `hci0` or make scanning return devices.
- **Release tooling.** The deploy manifest covers all new console/Settings/
  Maps/bridge/diagnostic files, repository-only tests are explicitly named
  non-deployable, and the reboot policy refuses repeated reasons/diagnostics
  before issuing a reboot. Launcher cache namespace: `v48-v070-release`.
- **Whole-repo lockstep at `v0.7.0-beta`** (`VERSION`, APKBUILDs, PWA/bridge
  manifests, systemd pins, shell apps, OTA/VM tooling and docs).

## What's new in v0.6.7-beta

A beta release cut from the exact current repository sources by the GitHub
Actions pipeline. The phone does not need to be connected: the workflow builds,
verifies and packages the merged `main` commit, and the release also carries the
captured installed-phone image and the refreshed installed-userspace inventory.

- **Release gate fixed.** The v0.6.6-beta `main` run was red in
  `tools/s10plus/a45/test-lockscreen-indicators.py`: Ubuntu's GCC rejected
  several `snprintf` indicator paths with `-Werror=format-truncation`. The
  buffers in both `a33` and `a45` host sources are now sized for the worst
  case and the `ind_pid_holds_tty()` result is checked. The same offline
  indicator sequence the workflow runs passes locally under GCC 13 before this
  tag is cut.
- **Transactional Live Console deploy.** `declared_reload` and
  `systemctl restart` run once per deploy group instead of once per file; a
  failed group restores its files and re-applies the coalesced activation plan.
  Large payloads use acknowledged block transfer with bounded retry/rewind and
  fall back to the proven per-frame path. Unit tests:
  `tools/beta/live/tests/test_live_reload_and_transport.py`.
- **A77 USB-detach truth fix.** The PC and Live Console penguins now disappear
  when the cable is unplugged. The measured detach log showed
  `typec/port0/data_role` and the UDC `state` both stay stale on this kernel;
  A77 vetoes the stale `configured` evidence on a non-connected UDC
  `current_speed` (`UNKNOWN`) or on wired VBUS being offline. The bridge and
  the native phone host share the same rules, and the console icon is gated by
  the corrected data link.
- **Release is now GitHub's Latest.** The workflow publishes the beta as a
  normal release with `--latest`, so the sidebar shows the newest version
  instead of v0.6.0-beta. The `-beta` tag and title are preserved.
- **Launcher cache `v46-a77-usb-detach`** with `a77.1` asset cache-busters.
- **Whole-repo lockstep at `v0.6.7-beta`** (`VERSION`, APKBUILDs, PWA/bridge
  manifests, systemd pins, shell apps, OTA/VM tooling and docs).
- **Not hardware verified:** Wi-Fi association/internet, speaker, camera,
  Bluetooth, NFC, GNSS and a fresh-image physical boot still require owner
  testing. See [`docs/releases/v0.6.7-beta.md`](docs/releases/v0.6.7-beta.md).

## What's new in v0.6.5-beta

- **A44 launcher/navigation fixes.** The shortcut dock no longer paints a
  duplicate half-height artwork bar, dock artwork is confined to the
  Back/Home/Recents strip, Home always returns to desktop 1, and pinch/double-tap
  zoom is blocked on the Home document.
- **Live CPU/MEM/GPU/VRAM meters.** The socket-activated `nuxel-metricsd`
  collector accepts cache-busted requests, answers CORS preflight, samples a
  real first CPU delta, and reports Mali allocation bytes against the shared-RAM
  budget instead of a hard-coded N/A.
- **NetworkManager Wi-Fi Settings.** Status, scan, radio control, WPA2/WPA3
  connection activation and disconnect use the existing bridge; no independent
  supplicant is started and credentials never appear in argv.
- **Release flow is PR-only.** A merged PR to `main` builds the S10+ image,
  verifies exact source parity, creates the annotated `v0.6.5-beta` tag and
  publishes a GitHub prerelease. Tag pushes do not trigger the workflow.
- **Whole-repo bump to `v0.6.5-beta`:** `VERSION`, device `APKBUILD`s,
  PWA/bridge manifests, shell apps, services, OTA/VM tooling and release docs.
- **Not hardware verified:** Wi-Fi association/internet, speaker, camera,
  Bluetooth, NFC, GNSS and a fresh-image physical boot still require owner
  testing. See [`docs/releases/v0.6.5-beta.md`](docs/releases/v0.6.5-beta.md).

## What's new in v0.6.1-beta

A patch release on top of the working v0.6.0-beta runtime: it stages haptic
feedback, triple-button support and a live A40 system monitor, keeps the S10+
release image building exactly what ships from repo sources, and bumps every
version string in lockstep to `v0.6.1-beta`.

- **Haptic feedback (A38).** Staged haptic patterns with distinct tap/scroll/long-press
  intensities and durations, a single `nuxel-haptics` writer unit, per-user intensity
  preferences and an on-device Haptics control surface. Intensity is reported honestly and
  falls back to unsupported rather than fabricating an amplitude the motor cannot do.
- **Triple-button support (A38).** Button handling extended beyond the previous two-button
  model so a third button state is wired through the existing input -> UI path, with the
  Bixby/shortcut default action preserved as the Terminal.
- **Live A40 system monitor.** `services/nuxel-metrics` (AArch64 `nuxel-metricsd`) reports
  CPU (`/proc/stat` deltas), RAM (`MemAvailable`), GPU (documented Mali node when exposed)
  and shared GPU memory reported unavailable rather than invented; deployed through the A40
  live payload via a socket-activated service.
- **Whole-repo patch bump to `v0.6.1-beta`.** `VERSION`, device `APKBUILD`s, PWA/bridge
  manifests (`package.json`, `manifest.json` + `pwa_version`, `bridge-version.json` host
  version), bridge/notification/portal services, the OTA builder and VM tooling all move in
  lockstep. The PWA protocol pin (`NUXEL_BRIDGE_VERSION = '1'`) is intentionally unchanged —
  only the host *implementation* version moves.
- **Build method unchanged.** The GitHub Actions `s10plus` job still compiles the current A34
  TOUCHDOWN userspace from repo sources in a Fedora 43 arm64 container, embeds the repo-source
  initramfs in a RAW arm64 kernel Image (never Image.gz) and packs it into the legacy v1 boot.img;
  CI checks out this same tree, so it reproduces exactly what runs on the handset.

**Verified:** nothing new landed on hardware — the honest readiness scores are carried
forward unchanged from v0.6.0-beta. The haptic, triple-button and A40-monitor features land
on the phone through the A40 live payload pending a Milestone A deployment.

## What's new in v0.6.0-beta

**The current S10+ image is reproducible, and the status is now honest about what
works.** The handset boots Nuxel (kernel → embedded initramfs → Fedora 43
systemd → launcher), the **touchscreen works at the hardware/input layer**, and
the remaining interaction gap is that **clicking/navigation in the UI is not yet
signed off**.

- **The release CI builds the exact current userspace.** The S10+ rootfs builder
  now compiles the **A34 TOUCHDOWN** display bridge, PWA host, button manager,
  libinput shim and snapshot tool from repository sources inside the arm64
  container. It no longer copies a developer-only `build/out/s10plus/a32` tree,
  so a clean checkout produces the same runtime the phone is running.
- **The artifact gate knows the current image.** `verify-fedora-phone-rootfs.py`
  fails if any current binary or the current button/reboot-gate configuration is
  missing; the workflow also runs the A34 and A33 touch regression suites.
- **Touch works.** Physical finger contacts reach `sec_touchscreen` → evdev →
  libinput → phoc → WebKit (`pointerdown`/`touchstart`), and the display bridge
  presents frames. Taps are delivered; reliable in-UI clicking is the open item.
- **Sound should work, but is not proven on the phone.** ALSA/UCM configuration
  and diagnostics are present and VM audio is verified, but S10+ audio cannot be
  exercised through the UI until clicking is reliable.
- **Repository cleanup.** Legacy mission/scratch notes, duplicate flash guides,
  the `finish/` trees and all superseded image candidates were removed. Only the
  canonical currently-flashed images remain in the local build tree.
- **Version bump to `v0.6.0-beta`** across the repository.


## What's new in v0.4.0-alpha

**The Galaxy S10+ boots Nuxel.** This release records the first hardware-proven
boot chain on the handset: S-Boot loads the **Nuxel ARM64 kernel**, the
**embedded Nuxel initramfs executes**, the **Fedora 43 ext4 rootfs mounts**,
`switch_root` hands over to **Fedora systemd 258 as PID 1**, systemd's services
execute, the **AMOLED panel shows the Nuxel boot animation** (the original MP4 at
24.00 fps, 0 skipped frames, correct ABGR colour order) and a **live root
console** is available over USB. The **Nuxel phone UI then runs as a real Fedora
userspace process**, commits real framebuffer frames and takes the panel over
from the animation. Full per-step evidence:
[docs/s10plus-autonomous-boot-repair/STATUS.md](docs/s10plus-autonomous-boot-repair/STATUS.md).

- **The boot chain is proven on the SM-G975F, step by step** — kernel handoff,
  initramfs execution, USERDATA discovery, ext4 root mount, systemd PID 1,
  service execution, panel bring-up, animation, live console, UI process and the
  animation→UI handoff. Every line is a hardware marker (`NUXEL_MARKER …`,
  `systemd[1]: systemd 258.11-1.fc43 … arm64`, `FIRST_FRAME_COMMITTED`), not a
  code-level claim. A25 (single-instance UI + console-owned postboot supervisor)
  is flashed to BOOT with a full SHA-256 readback and is awaiting a power cycle.
- **The release CI now builds exactly that image.** S-Boot never populates the
  initrd memory it advertises, so *only a built-in initramfs is ever executed* and
  a gzip kernel payload is executed as code
  ([INITRAMFS-DELIVERY-ROOT-CAUSE.md](docs/s10plus-autonomous-boot-repair/INITRAMFS-DELIVERY-ROOT-CAUSE.md)).
  The S10+ job therefore builds the initramfs **from repo sources**
  (`tools/s10plus/build-a25-initramfs.sh`), **embeds** it in a **raw arm64
  `Image`** (`CONFIG_INITRAMFS_SOURCE`, `images/s10plus/build-a25-boot.sh`) and
  packs it with the merged board DTB as a legacy v1 `boot.img`, gated fail-closed
  by `tools/s10plus/verify-a25-boot.py` (raw kernel, embedded archive identical to
  the built one, pinned systemd payload, partition budget). The legacy
  `Image.gz` + external-ramdisk path is no longer the S10+ deliverable.
- **The honest scoreboard moved accordingly**: build system 58% → 85%, S10+
  bring-up 55% → 85%, flashable images 80% → 90%; overall **~45–50% → ~60%**.
- **Version bump to v0.5.1-alpha** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder.

**Still open, in kind:** no touch event has been exercised yet (every boot so far
was `androidboot.mode=charger`, where no touch device exists), the Fedora boot
graph itself stalls before `multi-user.target` (the UI is started ahead of it and
`bootreport.txt` now instruments the stall), Phosh/Phoc need a DRM/KMS kernel
that this 4.14 tree does not have, and the Moto G7 Power still hangs at a
black/flashy screen.

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

**Readiness at a glance:** the Galaxy S10+ **boots Nuxel on real hardware**,
the display path and **touchscreen input work**, and clicking/navigation is the
remaining interactive gap. The Moto G7 Power is flashed but still hangs at a
black screen; the Pixel 10 Pro XL is still a scaffold. The UTM VM demo boots
(display + network + sound).

## Honest Status — v0.7.0-beta

**S10+ (SM-G975F, beyond2lte) — NUXEL BOOTS AND TOUCH INPUT WORKS.**
S-Boot loads the raw arm64 `Image` with the initramfs embedded, the Fedora 43
ext4 rootfs mounts, `switch_root` hands over to **systemd 258 as PID 1**, the
service graph reaches `running`, and the panel shows the boot animation before
the launcher takes ownership. The **touchscreen produces real finger contact
events** and they are delivered through evdev → libinput → phoc → WebKit.
Unlock → Home, the three Tri-Link console entries and app launching are
physically verified. **Bluetooth scanning cannot work on this kernel**:
`CONFIG_BT_HCIUART` is not set and `bcm43xx_bluetooth` is only the power/rfkill
driver, so even with the verified BCM4375 HCD no `hci0` can register. GNSS has
no firmware/reader, USB-C HDMI needs `CONFIG_DRM` plus a Type-C DP Alt Mode
stack, and the MADERA `HPOUT1 Digital` unmute path wedges in kernel D-state.
**Audio inventory and low-volume control are real; audible output still needs
the owner's physical confirmation.** Camera, radio/modem and the remaining
sensors stay unproven.

**The release ships the exact image installed on the handset.** The workflow
publishes `nuxel-installed-s10plus-boot.img.gz` — the byte-exact A27 BOOT image
read back from the owner's SM-G975F (`48ad61af…`, 51,605,504 bytes) — together
with a hash inventory of the installed userspace and an
`INSTALLED-IMAGES.json` provenance manifest. The separately built
`nuxel-<version>-s10plus.tar.gz` contains the reproducible **A25** source
rebuild and is explicitly labelled as such: it is not byte-identical to the
installed A27 image. See
[`docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md`](docs/a61-penguin-eyes/INSTALLED-IMAGE-RELEASE.md).

| Area | Score | Notes |
|---|---|---|
| Design/docs | 85% | Architecture, security model, PWA spec, three device bundles, plus the A25–A34 hardware evidence set |
| Repo structure | 90% | Legacy scratch trees and duplicate guides removed; canonical images only |
| PWA apps | 55% | Manifests, service workers and launcher integration exist; live app interaction still limited by the clickable gap |
| Flatpak app model | 20% | Manifests + launcher exist (`pwa/flatpak/`, `org.nuxel.Platform`); runtime not built or integration-tested |
| Native GTK apps | 30% | C source exists; not yet proven end-to-end in the phone UI |
| D-Bus bridge/portal | 45% | Bridge/portal/notifications run on the phone with real bus policies; deeper app integration is partial |
| Sandbox/security | 25% | Configs exist; enforcement is not wired end-to-end |
| Build system | 90% | Fail-closed CI builds the A25 boot image and **compiles the current A34 userspace from repo sources**; artifact verification is content-based |
| Flashable images | 90% | S10+ boot + Fedora rootfs and G7 Power lk2nd/boot/rootfs are byte-verified on hardware; S10+ boots |
| Pixel 10 Pro XL (mustang) | 5% | UART/initramfs-level only; no boot artifact yet |
| Galaxy S10+ (beyond2lte) | 90% | **Boots Nuxel; touchscreen works; clickable UI is the remaining gate.** Display, animation, launcher, systemd service graph and single framebuffer owner are proven. Sound is expected but unproven; radio/camera/sensors/Phosh remain open |
| Moto G7 Power (ocean) | 40% | Images flashed (lk2nd + boot + ext4 rootfs); still hangs at a black/flashy screen |
| UTM VM | 70% | Boots Fedora 43 + Phosh at 720×1440 with working network and **audio** (local, gitignored artifact) |

**Overall: ~70% MVP.** One of three phones (S10+) boots a Nuxel-built image,
its display path is live, and its **touchscreen delivers real contacts**; the
phone is not yet a usable interactive device because clicking/navigation is not
signed off. G7 Power still hangs at a black screen; mustang is UART/initramfs
level only. The UTM VM demo boots and works (display, network, sound).

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
- A **bootable S10+** — the Galaxy S10+ runs the Nuxel kernel, embedded
  initramfs, Fedora 43 systemd userspace, the panel animation and the launcher.
  The **touchscreen delivers real finger contacts** through evdev, libinput,
  phoc and WebKit. The open item is reliable **clickable** UI interaction.
- **A reproducible, fail-closed release CI.** The S10+ job builds the A25 boot
  image and compiles the **current A34 TOUCHDOWN** userspace from repo sources
  inside the arm64 container, then runs the A34/A33 touch regression suites and
  the strict `tools/verify-artifacts.sh` content gate. A red build cannot create
  a release.
- **A bootable UTM VM** — Fedora 43 + Phosh at 720×1440, Nuxel services + PWA
  live on the desktop, guest SSH reachable and **internet working**, with
  **verified VM audio** via `virtio-sound-pci` (local, gitignored artifact).
- **Flashed, checksummed images for two of three phones** — `g7power`
  (`lk2nd.img`, `nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`) is flashed but
  still reaches only a black/flashy screen; `s10plus` (`nuxel-beyond2lte-boot.img`
  + the Fedora 43 ARM64 rootfs) is flashed, boots, and its userspace is live.

### What this repo IS NOT YET:
- A fully interactive phone: S10+ clicking/navigation is not yet signed off and
  audio is expected but unproven.
- A flashable Pixel ROM (`mustang` has no boot artifact yet)
- A daily-driver phone
- A built Flatpak PWA runtime
- Hardware-validated across radio, camera, sensors and Phosh

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
| `s10plus` | Samsung Galaxy S10+ (Exynos) | beyond2lte | **Boots Nuxel — touchscreen works; clickable UI pending; sound unproven** |
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

Two of the three targets have real, checksummed boot artifacts, and both are
flashed. The **S10+ (Exynos 9820)** boots Nuxel from the A25 boot image plus the
Fedora 43 ARM64 userspace; its **touchscreen works**, while reliable clicking and
S10+ audio remain open. The **G7 Power (SDM632/msm8953)** has its lk2nd
chainloader, boot image and writable ext4 rootfs flashed, but still hangs at a
black/flashy screen (display init unresolved). The `mustang` path remains a
scaffold with no boot artifact.

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
| [CHANGELOG.md](CHANGELOG.md) | Release notes — everything from v0.1.0 to v0.7.0-beta + readiness |
| [prompts/QUICKSTART.md](prompts/QUICKSTART.md) | Get running in 5 minutes |
| [design/nuxel-linux-phone-design.md](design/nuxel-linux-phone-design.md) | Design bible — the full vision |
| [design/Nuxel Phone OS Project Plan and Architecture.md](design/Nuxel%20Phone%20OS%20Project%20Plan%20and%20Architecture.md) | Technical architecture + component map |
| [docs/architecture.md](docs/architecture.md) | Immutable OS architecture |
| [docs/security-model.md](docs/security-model.md) | Sandbox, mitigations, boot chain |
| [docs/app-store.md](docs/app-store.md) | App distribution model (Flatpak + portals, signed packages) |
| [docs/pwa-model.md](docs/pwa-model.md) | Hardened PWA runtime spec |
| [docs/build-guide.md](docs/build-guide.md) | Full build pipeline |
| [.github/workflows/release.yml](.github/workflows/release.yml) | Merged-PR (`main`) build → auto-tag → GitHub **Latest** release pipeline |
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

* **Automated (recommended):** open a PR against `main`. When the PR is merged,
  [`.github/workflows/release.yml`](.github/workflows/release.yml) runs for the
  merge commit, builds the S10+ image from repo sources, verifies the
  source-to-image parity gates, creates the annotated `v<VERSION>` tag, and
  publishes a GitHub release explicitly marked **Latest** (the `-beta` tag and
  title keep the beta status). The sidebar therefore shows the newest release.
  Tag pushes do not trigger the workflow; `main` is protected, so the release
  route is a merged PR.
  The S10+ build runs `images/s10plus/build-a25-boot.sh` (raw arm64 kernel with
  the repo-source initramfs embedded) plus the Fedora 43 ARM64 phone rootfs,
  which **compiles the current A34 TOUCHDOWN userspace and socket-activated
  metrics daemon from repo sources** inside the arm64 container. It also emits
  the matching hash-manifested live userspace payload.
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
