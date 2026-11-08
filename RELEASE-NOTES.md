# Nuxel Release Notes

This file holds the release-by-release user-facing changes. The full engineering
history remains in [CHANGELOG.md](CHANGELOG.md).

## v0.8.1-beta — direct LAN remote desktop + truthful USB Tri-Link (2026-11-08)

### Direct LAN RDP and VNC

- **XRDP now listens on TCP 13389** (was 3389) and is bound by the privileged
  controller to the current trusted WLAN IPv4 address. TLS 1.2/1.3 only and PAM
  as the local `nuxel` account; separate X11 session; no SSH tunnel.
- **VNC now listens on TCP 15900** (was 5900) and is bound to the same trusted
  WLAN IPv4 address. `enable_auth=true` and `enable_pam=true` are mandatory,
  with per-device TLS and RSA-AES credentials. The old `enable_auth=false`
  production path is gone.
- Bridge/app status now reports the *effective* authentication and encryption
  mode. A listener with authentication disabled is an ERROR, never READY.
- `stop-all` closes both listeners and terminates only managed remote X11
  children; Phoc and the framebuffer bridge are never touched.
- XRDP uses the installed xorgxrdp backend (`autorun=Xorg`). The uninstalled
  Xvnc backend is no longer offered as the default.

### Native mirror vs Android scrcpy

- The former scrcpy app remains honest: official scrcpy is Android/ADB only.
- Native Nuxel is directed to the authenticated VNC mirror on TCP 15900 with a
  copyable direct-LAN endpoint. No fake ADB device is created.

### USB Tri-Link

- USB status is mode-aware: NCM `BLOCKED_KNOWN_PANIC` on the recorded
  4.14.253 kernel, RNDIS `NEEDS_VALIDATION`, ECM absent.
- The device helper is read-only by default, supports `--status`,
  `--preflight`, `--diagnose` and per-mode gating, and refuses every unsafe
  apply. The production `--allow-unsafe-kernel` escape hatch was removed.
- The host helper now supports Linux and macOS discovery/status/preflight and
  never installs a driver or changes the default route.
- `REPORT-USBNET.md` records the exact blocker and next safe step.

### Rolled-up shell and spoof work

- PenguInterface global/per-app spoof profiles, persistence and launch-time
  injection (PWNAGE-91000) are included and deployed.
- PWNAGE-90000 shell reliability fixes (preload playback, restart overlay,
  stale layers, Back/gesture routing, first-paint icons, systemd evidence) are
  included and deployed.

### Verification summary

- Offline: remote-desktop, Tri-Link status/API/console and USB helper suites.
- Live S10+: VNC 15900 offered RFB security types `129` (VeNCrypt) and `5`
  (RSA-AES) with no unauthenticated type; RDP 13389 completed RDP negotiation
  and a TLS 1.3 handshake; both listeners closed on `stop-all`.
- USB physical data-plane: **not run**. Serial ACM remained `acm.usb0` and WLAN
  SSH remained the recovery path throughout.

## What's new in v0.7.7-beta

- **A real WAD engine, not a raycaster.** Nuxel Doom now embeds Chocolate Doom
  3.0 compiled to WebAssembly. It loads Freedoom Phase 1/2/FreeDM or an
  imported IWAD/PWAD, warps straight into a real map, renders the actual
  geometry, textures and status bar, and translates the touch HUD into the
  engine's own keyboard events. The old procedural engine is no longer used.
- **Three engines to compare.** **Nuxel Doom** is the touch-first WASM path.
  **Chocolate Doom** is the native Fedora 3.1.1 port. **UZDoom 5.0.3** is the
  modern GZDoom-lineage comparison path using its software renderer on this
  vendor-kernel phone. All three are separate NuXtore packages and can be
  installed or removed independently.
- **Freedoom is the default content.** No commercial WAD is bundled. The bridge
  exposes a read-only catalogue of allowlisted game-data directories and
  streams WADs by SHA-256 digest; the app never receives a general filesystem
  API and no path is accepted from the client.
- **Global immersive chrome.** Every foreground app, PWA or native, now hides
  the triple buttons and top bar by default. Swipe up from the bottom edge for
  Back/Home/Recents (and Recents to kill), pull down from the top edge for the
  status bar. PWAs use the DOM immersive controller; native apps keep a 14 px
  bottom gesture strip for the dock and a 12 px top strip for the status bar.
  Home and the lockscreen keep their normal chrome.
- **Portrait boot until unlock.** A cold boot always applies the portrait
  orientation before the lockscreen settles. The mode selected before boot is
  recorded by `nuxel-orientationd` and restored by Home only after a successful
  unlock, so rotation becomes available again once the owner is past the
  lockscreen.
- **No Doom keyboard.** The Doom shell has no text input, blurs focus, and asks
  both the host and the compositor to dismiss the OSK at launch, focus, resume
  and exit.
- **Lifecycle safety.** Pause suspends the engine loop, focus loss releases every
  held key, and exiting restores the previous orientation and the normal app
  chrome.

## What's new in v0.7.5-beta

- **Rotation works, and it holds.** The live Phoc session exposes
  `HEADLESS-1` (720x1520), so `wlr-randr` is the only truthful output
  inventory. Transform and scale are now applied as one transaction (0°/180° at
  scale 2, 90°/270° at scale 1 → a real 1520×720 desktop), and the reverse
  90/270 mapping is the physical mapping recovered from the historical config.
  Successful rotations used to revert after 75 s because the "owner
  confirmation" trial ran on the normal path; a `set` now commits only after
  live readback and restores the previous verified transform on failure.
- **Touch follows the rotation.** Phoc feeds raw libinput touch coordinates;
  wlroots rotates the rendered scene and screencopy buffer, not touch. The
  single LD_PRELOADed `libnuxel-libinput-path.so` now applies the measured
  calibration matrix (`0 1 0 / -1 0 1` for transform 270) through
  `libinput_device_config_calibration_set_matrix()`, reads it back, and
  re-applies it from an inotify thread while the screen is idle. `nuxel-wl-fb`
  stays the sole `/dev/fb0` writer and does **not** rotate a second time.
- **GPU acceleration is partial, and measured.** Phoc renders on the vendor
  **Mali-G76** through Mesa panfrost (three `/dev/mali0` contexts, zero llvmpipe
  threads); `zwp_linux_dmabuf_v1` v3 advertises LINEAR formats only and validates
  every buffer before import; WebKit is GPU-rendered (`gpu-rendered-shm-presented`,
  186 `KBASE_IOCTL_JOB_SUBMIT` calls in 3 s) but presents through SHM.
  WebKit DMA-BUF and true zero-copy presentation are `BLOCKED_KERNEL_ABI`
  (`drmMainDevice()` is null, `CONFIG_DRM_VGEM` unset, no `/dev/dri`). Active
  userspace CPU fell from 47.0 % to 27.8–31.3 % of one core; blit 45 ms → 20–38 ms.
- **Triple navigation unblocked.** A stale launcher boot-gate cache discarded
  every Back/Home/Recents request while the authoritative lock state said
  unlocked. The launcher reconciles against `security.status` and replays the
  action only after the provider confirms `locked=false`. Recents also gained
  the missing GET route, a real Close button and left-swipe close.
- **PWNAGE-47000..53000.** GUI tri-link remote desktop (VNC mirrors the Phoc
  session, XRDP is a separate X11 session, scrcpy is Android-only) over
  loopback listeners reached through a pinned-key SSH tunnel; kernel user
  namespaces + the `STATX_MNT_ID` backport + a `bwrap` fd-bind shim make
  Flatpak work; real WDMA1 microphone capture with an enforceable privacy mute;
  NFC kernel/controller/firmware up but `BLOCKED_EXTERNAL_RESOURCE` (no
  userspace NCI reader); Contacts/Messages/Dialer compiled from source into the
  image; Clipper PWA shipped.
- **Release engineering.** The workflow now applies
  `kernel/s10plus/configs/nuxel-drm-kbase.fragment` (DRM core, UDMABUF, Mali
  Bifrost kbase, user namespaces, SECCOMP, NFC) and fails closed via
  `tools/s10plus/verify-kernel-config.py` if the built `.config` is not the
  capability set read back from the phone. The hash-pinned kbase Mesa/wlroots
  set lives in `release/s10plus/gpu/` and must match its `SHA256SUMS`. The exact
  installed BOOT image (`2cbc5085…`, 57,671,680 bytes) and a 5,873-entry
  userspace inventory were re-captured from the handset with
  `tools/release/capture-installed-image.sh`.
- **CI repair.** `gen-navdock-art.py` now resolves its repository root from a
  build copy (the v0.7.4-beta `main` failure was `missing art
  /assets/button-left.png`), the A34 decon contract reads the active A67 bridge,
  the launcher input harness stubs `getElementById`, and the home cache version
  matches its manifest again.

## What's new in v0.7.4-beta

- **Audio is working and owner-confirmed.** The CS35L41 PLL reference was the
  root cause: the device tree says 6.144 MHz, ABOX UAIF1 actually clocks
  1.536 MHz, so the protection DSP never drove the speaker. The fix writes
  `SP_RATE_CTRL=0x1b`, `PLL_CLK_CTRL=0x370`, `AMP_DIG_VOL_CTRL=0x8000` and
  `AMP_OUT_MUTE=0x0` on both amps, and keeps them alive through the driver
  cache (`Digital PCM Volume=817`, `AMP Mute=Unmuted`).
  `nuxel-audio-warmup` powers the DAPM speaker path with an inaudible stream
  before the 366 ms cue, so boot, volume keys and Test Audio all actually play.
  Volume ceiling 100 %, default 50 %.
- **GNSS is almost there.** Real network location works through a new
  per-UID GeoClue agent plus a narrow `CAP_NET_RAW` grant, with a bridge that
  uses the real GeoClue 2.8.2 property API and a PWA shim that never invents
  coordinates, timestamps or accuracy. Satellite GNSS stays
  `BLOCKED_FIRMWARE`; no fix is claimed.
- **GTK and Flatpak apps are almost there.** The GTK4/libadwaita sources
  build; the handset runs the WebKit PWA shell, and modem-dependent flows are
  blocked. Flatpak packages are installed but `CONFIG_USER_NS=n` blocks
  bubblewrap: Firefox/VLC launch the real Fedora RPMs and Signal/Stremio report
  the blocker instead of faking a launch.
- **PWNAGE-44000 Home and hardware.** Reliable long-press drag/reorder with
  pointer-cancel rollback, a real sticky Notes widget, the full 15-entry power
  menu, Power+Volume Down screenshots into Gallery, server-side video
  thumbnails, a Bluetooth Files Send flow, a single-owner flashlight and
  truthful Location/sound/USB status cells. Files p95 improved 42.6 %.
- **`main` is green again.** The Release workflow had failed since the v0.2.1
  merge on the A40 boot-sound contract, a stale launcher assertion, registry
  version drift and a missing CHANGELOG heading. All four are fixed, and the
  rootfs builder now installs the audio warm-up, GeoClue agent, desktop entries
  and Python D-Bus dependencies a fresh image needs.
- **Release tooling.** Launcher cache `v66-v074-release`; whole-repo lockstep
  at `v0.8.0-beta`; registry revision 16 with the Firewall, Permissions, remote-desktop, Clipper and native phone apps.

## What's new in v0.2.1

- **Bluetooth is confirmed working.** The S10+ kernel carries
  `CONFIG_BT_HCIUART`/H4, `btattach -B /dev/ttySAC1 -P h4` creates `hci0`,
  BlueZ reports the BCM4375 controller powered, and a 12-second
  `bluetoothctl scan on` discovers a peer. Settings exposes the real controller,
  rfkill and adapter state plus bounded scan, pair, connect, disconnect, trust,
  remove and known-device listing. Every action reports the actual BlueZ
  readback.
- **Bluetooth overlays tell the truth.** The Quick Settings tile is now
  tri-state (ON/OFF/UNKNOWN), shows discovery and the concrete blocker when no
  adapter exists, and never maps a missing bridge field to OFF. The top status
  bar and lockscreen have proof-only Bluetooth indicators that light only for a
  powered adapter; UNKNOWN and OFF both stay dark.
- **Audio is almost complete.** `nuxel-audio-route.sh` verifies Calliope `MUB0`,
  both CS35L41 DSP1s (`booted=Y running=Y`), `ABOX RDMA1_EN=1`, the full
  RDMA1→SPUS→SIFS1→UAIF1 crossbar, `Left/Right AMP PCM Gain=12`, the 48 kHz
  `alsa_output.hw_0_1` sink and the 25 % volume ceiling. Settings → Sound →
  **Test Audio**, the boot cue and the volume keys share that route and still
  report `audible=unverified` until the owner hears it.
- **Wi-Fi boot and UI state are honest.** NetworkManager remains the only radio
  owner, enables Wi-Fi after a normal boot and verifies the readback. Quick
  Settings separates radio ON from network connected, shows UNKNOWN while the
  bridge starts, and respects a manual OFF for the current session.
- **Feature and overlay documentation is canonical.** The new
  [`docs/features/README.md`](docs/features/README.md) lists each function with
  `WORKING`/`ALMOST`/`PARTIAL`/`BLOCKED` status and its evidence anchor. The
  PWA manifest feature list, README readiness table, Quick Settings, status bar,
  lockscreen, native host and bridge provider now describe the same state.
- **Release tooling.** Launcher cache `v58-p021-bluetooth`; whole-repo lockstep
  at `v0.2.1`.

## What's new in v0.7.3-beta

- **PWNAGE-37000 Butterscotch.** Cold boot fell from 1 min 22.5 s to 58.9 s
  and `multi-user.target` from 1 min 18.1 s to 17.5 s. The ABOX reload no
  longer blocks the UI target, `nuxel-wayland` has a deterministic 8 s stop,
  and Wi-Fi boot no longer serialises behind NetworkManager autoconnect. A
  radio the owner disabled stays disabled.
- **PWNAGE-38000 audio.** The bridge, sound cue and Settings UI now share the
  real PipeWire default sink at 48 kHz (RDMA1 stalls and returns EIO at
  44.1 kHz on this unit). Audio Settings has a real **Test Audio** action that
  plays `nuxel-pow.mp3` and reports `audible=unverified`; the ABOX Calliope
  firmware reload runs at boot with bounded, verified PM cycles.
- **PWNAGE-38000 first light.** The initramfs no longer paints the obsolete A16
  diagnostic frame when the first-light asset is absent, and the repack tool
  ships frame 0 of the real animation, so the first lit frame is the animation.
- **PWNAGE-34000 connection modes.** Lockscreen console-transport and
  file-transfer indicators, the Charging/File Transfer selector and the safe
  USB mode state machine are part of the launcher/bridge sources.
- **Exact installed-image parity.** `release/s10plus/` now holds the BOOT
  partition read back from the handset on 2026-10-30 (`6e998acf…`,
  57,671,680 bytes) and a 4,238-entry userspace inventory. The release tooling
  derives its published hashes from `INSTALLED-IMAGES.json`.
- **Release tooling.** Launcher cache `v56-v073-release`; whole-repo lockstep
  at `v0.7.3-beta`.

## What's new in v0.7.2-beta

- **PWNAGE-31000 preload cinema.** The supplied 1080x1920 clip plays over the
  real lockscreen after wayland/web/display readiness, while startup services
  continue concurrently. A one-shot marker, bounded display/hold timers, a
  fail-open cover and a `FALLBACK` receipt make decode failure safe.
- **PWNAGE-32000 keyboard, navigation and battery.** The intended
  grey/black/white keyboard is restored with haptics; Back/Home/Recents work
  outside the browser; the lower screen band is a valid unlock gesture;
  charger/LPM boots explain the missing touch device; battery 100%→0% flicker
  is debounced.
- **PWNAGE-33000 app resurrection.** Contacts/Messages/Phone launch through
  repaired native registration; Camera/Browser/Weather keep the top bar and
  navigation; Files is a real explorer with CRUD/copy/move/ZIP/upload; Mail has
  settings and compact folder navigation; Gallery browses and plays media;
  Recorder writes a real WAV under the user home; Nuxtore keeps an honest empty
  state; desktop and drawer share canonical icons; standard home folders and
  the console banner are installed.
- **PWNAGE-34000 connection modes.** Back/Home/Tabs rendering is deterministic;
  serial, USB and WLAN consoles have simultaneous live indicators; a
  file-transfer indicator reflects the real mode; the lockscreen offers
  Charging/File Transfer without exposing personal files; the storage state
  machine refuses unsafe raw exports.
- **PWNAGE-35000 Buttersmooth.** Removed idle software-raster filters and
  redundant polling, bounded input/render work, repaired global Back lifecycle,
  shortened the reboot black screen, and made Wi-Fi/quick settings
  readiness-aware.
- **PWNAGE-36000 S10+ fixes.** The ABOX boot-done hard-IRQ panic is patched;
  HCIUART/H4 + `btattach` bring up Bluetooth; RDMA1 audio routing produces
  advancing playback; charger/LPM recovery and early device permissions are
  installed; GPS reports `BLOCKED_FIRMWARE`; boot capture is included.
- **Terminal.** New `nuxel-zsh`: four prompt themes, validated system/per-user
  configuration, `nuxel-theme`, canonical `/etc/banner`, nested/non-interactive
  suppression and rollback. Bash and recovery access remain available.
- **Release tooling.** New `nuxel-preload-cinema` and `nuxel-s10` service
  packages; launcher cache namespace `v54-v072-release`; whole-repo lockstep at
  `v0.7.2-beta`.

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



## Earlier releases

See [CHANGELOG.md](CHANGELOG.md) for the complete v0.1.0 → v0.8.0-beta history
and readiness notes.
