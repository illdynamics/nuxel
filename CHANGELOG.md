## A39 — Smart dock / Home settings (2026-10-19)

- Default dock artwork now uses `assets/nuxel-bottom-bar2.png`; `Home Settings → Dock Background` switches BG1 JPEG / BG2 PNG instantly and persists across restarts. Both images are copied byte-for-byte to the PWA webroot and included in deployment checks.
- Added layout lock, independently assigned Home desktop pages (two by default), Home returning to primary page, drawer Add to Home interactions, 4-position stationary dock and fixed wallpaper, slim inert scrollbar indicators, and live battery display styles.
- Preserved A37 asset/haptics handling. Strengthened userspace manifest and included a separate hash-manifested A39 payload. Speaker output remains an on-device ALSA/UCM diagnostic blocker, not a tested success.

# Changelog

All notable changes to the Nuxel Phone OS repository are documented here.

The canonical version lives in [`VERSION`](VERSION) and is bumped in lockstep
across the shell apps, the PWA manifest, the device `APKBUILD`s, the VM tooling
and the OTA builder (see *Versioning* below).

## [v0.2.1] - 2026-10-30 - *Feature truth, confirmed Bluetooth and near-complete audio*

- **Bluetooth is confirmed working on the S10+.** `CONFIG_BT_HCIUART`/H4 plus
  `btattach -B /dev/ttySAC1 -P h4 -S 115200` register `hci0`; BlueZ reports the
  BCM4375 controller (`43:75:B1:00:1F:AC`) powered, and a 12-second
  `bluetoothctl scan on` discovers a peer. Settings exposes the real controller,
  rfkill, adapter and discovery state and supports bounded scan, list, pair,
  connect, disconnect, trust and remove; every action reports the actual BlueZ
  result. A specific headset/keyboard profile remains an owner check.
- **Bluetooth overlays are tri-state and truthful.** Quick Settings no longer
  defaults to OFF: `powered=true` shows ON, an explicit BlueZ false shows OFF,
  and a missing/unreadable provider field stays UNKNOWN. The tile names
  discovery and the concrete blocker when no adapter exists. The status bar and
  lockscreen add proof-only Bluetooth glyphs that light only for a powered
  adapter. The obsolete Settings paragraph claiming `CONFIG_BT_HCIUART` is not
  set has been removed.
- **Audio is almost complete.** The complete route is verified live: ABOX
  Calliope `MUB0`, both CS35L41 DSP1 protection images running, `ABOX RDMA1_EN=1`,
  the RDMA1→SPUS→SIFS1→UAIF1 crossbar, `Left/Right AMP PCM Gain=12/12`, the
  48 kHz `alsa_output.hw_0_1` default sink and an advancing `hw_ptr`. `pw-play`,
  the boot cue and Settings → Sound → Test Audio succeed. Physical audibility is
  still not owner-confirmed, so the API continues to report
  `audible=unverified`.
- **Wi-Fi boot/UI truth.** NetworkManager enables Wi-Fi after a normal boot and
  the helper verifies the readback; saved profiles autoconnect; a manual OFF is
  respected for the current session. Quick Settings separates radio ON from
  network connected, renders CHECKING/UNKNOWN while the bridge starts, and never
  converts a missing field to OFF.
- **Canonical feature documentation.** New `docs/features/README.md` records
  each function as `WORKING`, `ALMOST`, `PARTIAL`, `BLOCKED` or `NOT STARTED`
  with evidence anchors. The README readiness table, PWA manifest feature list,
  capability manifest and overlays now describe the same state.
- **Overlay/application limits documented honestly.** Camera capture, GNSS,
  cellular modem, external display and microphone/headset/USB-C audio remain
  blocked or unstarted; the UI reports the concrete blocker instead of a
  placeholder success.
- **Whole-repo lockstep bump to `v0.2.1`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, service/version pins, shell apps, OTA/VM
  tooling and documentation. Launcher cache: `v58-p021-bluetooth`.
- **Verification:** Wi-Fi/Bluetooth Quick Settings mapper, status-bar and
  lockscreen indicator suites; system-indicator payload tests; PWNAGE-37000
  Bluetooth/audio and PWNAGE-40000 audio persistence suites; capability-manifest
  validation; and the A43 source-contract version lockstep.

## [v0.7.3-beta] - 2026-10-30 - *Release: PWNAGE-37000/38000 boot, Wi-Fi, audio and exact image parity*

- **PWNAGE-37000 Butterscotch.** Cold boot dropped from 1 min 22.5 s to
  58.9 s and `multi-user.target` from 1 min 18.1 s to 17.5 s: the ABOX
  firmware-reload unit no longer blocks the UI target, `nuxel-wayland` stops
  deterministically in 8 s instead of ~46 s in `final-sigterm`, and
  `nuxel-wifi.service` no longer serialises behind NetworkManager autoconnect.
  With the radio disabled by the owner, the boot script leaves it disabled.
- **PWNAGE-38000 audio.** The bridge, sound cue and Settings UI now share the
  real PipeWire default sink, and the S10+ static sink plus graph clock run at
  48 kHz — RDMA1 returns EIO and stalls `hw_ptr` at 44.1 kHz on this unit. The
  new Audio Settings **Test Audio** action plays `nuxel-pow.mp3` at a bounded
  volume and reports `audible=unverified` honestly. The ABOX Calliope
  core-firmware reload runs at boot with bounded, verified PM cycles.
- **PWNAGE-38000 first light.** `boot/initramfs/init.sh` never paints the A16
  diagnostic splash when the first-light asset is absent, and
  `tools/s10plus/a27/repack-splashfix.sh` packs the animation's frame 0 back
  into the ramdisk, so the first lit frame is the real boot animation.
- **PWNAGE-34000 connection modes.** Lockscreen transport/file-transfer
  indicators, the Charging/File Transfer selector and the safe USB state
  machine ship in the launcher and bridge.
- **Exact installed-image parity.** `release/s10plus/` was re-captured from the
  live handset on 2026-10-30: the boot image is the complete BOOT partition
  (`6e998acf…`, 57,671,680 bytes) and the userspace inventory covers 4,238
  entries. `tools/release/verify-installed-image.py` gates the release on those
  bytes; `tools/package-release.sh` now derives the published hashes from the
  manifest instead of hard-coding the retired A27 capture.
- **Whole-repo lockstep bump to `v0.7.3-beta`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, service/version pins, shell apps, OTA/VM
  tooling and documentation. Launcher cache: `v56-v073-release`.
- **Verification:** the preload-cinema, connection-mode, PWNAGE-37000/38000,
  A69/A72/A80 pytest suites, the lockscreen/keyboard/indicator JS suites, the
  touch and A40 gates pass locally (the `/proc`-dependent preload tests are
  Linux-only and were run with a Linux-compatible temp path). The GitHub
  workflow rebuilds the S10+ image set from this merged commit and publishes
  the captured phone bytes alongside it.

## [v0.7.2-beta] - 2026-10-28 - *Release: PWNAGE-31000..36000 UI reliability + S10+ hardware fixes*

- **PWNAGE-31000 preload cinema.** The supplied 1080x1920 clip plays over the
  real lockscreen only after the wayland/web/display readiness gates pass.
  Startup services continue concurrently; a one-shot marker, a bounded
  `max_display`/`hard_timeout`, a 15 s fail-open cover and a `FALLBACK` receipt
  prevent a decoder failure, stale state or a later boot from blocking unlock.
- **PWNAGE-32000 keyboard, navigation and battery.** The intended
  grey/black/white keyboard is restored, including haptics and contenteditable
  fields; Back/Home/Recents work outside the browser; the lower screen band is
  a valid unlock surface; charger/LPM boots explain the missing touch device;
  battery 100%→0% flicker is debounced in both lockscreen and status bar.
- **PWNAGE-33000 app resurrection.** Contacts, Messages and Phone now launch
  through repaired native registration. Camera/Browser/Weather keep the system
  top bar and navigation. Files has a real breadcrumbed explorer with CRUD,
  copy/move, ZIP and upload; Mail gains settings and compact folder navigation;
  Photos is Gallery with playback; Recorder writes a 16-bit PCM WAV under the
  user home; Nuxtore keeps the empty-store state; desktop/drawer icons share
  one canonical set; the standard home folders and canonical console banner are
  installed.
- **PWNAGE-34000 connection modes.** The dock/navigation icons render through a
  deterministic path; serial, USB and WLAN consoles each show a live indicator;
  a file-transfer indicator reflects the real mode; the lockscreen
  Charging/File Transfer selector is usable without unlocking; the storage
  state machine refuses unsafe raw exports and preserves recovery transports.
- **PWNAGE-35000 Buttersmooth.** Idle lockscreen filters and redundant polling
  are removed, input/render work is bounded, global Back now follows app
  lifecycle before returning Home, reboot is bounded, and Wi-Fi startup,
  autoconnect and quick-settings actions use readiness-aware ordering.
- **PWNAGE-36000 S10+ reflash fixes.** The ABOX boot-done hard-IRQ panic is
  patched (`kernel/s10plus/patches/0004-nuxel-abox-boot-done-and-bt-hciuart.patch`).
  HCIUART/H4 plus `btattach` create `hci0` and pass a peer scan; RDMA1 audio
  routing produces advancing playback; charger/LPM recovery and early device
  permissions are installed; GPS remains `BLOCKED_FIRMWARE`; boot capture
  tooling is included.
- **Terminal.** New `nuxel-zsh` package with four prompt themes, validated
  system/per-user configuration, `nuxel-theme`, the canonical `/etc/banner`,
  nested/non-interactive suppression and rollback. Bash and recovery access are
  preserved; the default shell changes only with `--set-shell`.
- **Whole-repo lockstep bump to `v0.7.2-beta`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, service/version pins, shell apps, OTA/VM
  tooling, release provenance and documentation. Launcher cache namespace:
  `v54-v072-release`.
- **Verification:** the PWNAGE-31000/33000 pytest suites, the zsh suite, the
  lockscreen/keyboard/navigation JS suites, the S10 hardware-fix checks and
  `tools/beta/run-all-tests.sh` were run locally. The GitHub release workflow
  rebuilds the S10+ image set from this exact merged commit. Physical
  touch/haptic/microphone and laptop-side file-transfer acceptance remain the
  owner's tests.

## [v0.7.1-beta] - 2026-10-27 - *Release: PWNAGE-30000 application suite + live USB deployment*

- **PWNAGE-30000 application suite.** Calendar, Clock, Contacts, Files, Mail,
  Notes, Weather, Gallery, Recorder and Nuxtore now have real, durable flows.
  Calendar/Notes/Contacts use an in-process, atomic file-backed store instead of
  the non-existent `CaldavList`/`StorageListDir`/`MailImapList` D-Bus methods;
  Files is a traversal-safe browser with CRUD, copy/move, ZIP and upload;
  Clock tabs switch; Weather uses live Open-Meteo; Gallery seeds real PNGs;
  Recorder writes a real 16-bit PCM WAV; Mail performs TLS-only IMAP/SMTP
  discovery and connection tests without storing passwords.
- **Shared theme, haptics and widgets.** New `pwa/nuxel-common/theme.css`,
  `theme.js` and `haptics.js` provide Nuxel Grove (default) / Test Theme,
  immediate same-origin theme propagation and the haptics FIFO client.
  `pwa/nuxel-home/js/widgets.js` adds a per-desktop widget registry and the
  Notes widget; the desktop-2 isolation test covers it.
- **Live USB deployment completed on the connected S10+.** The framed/
  acknowledged Live Console transport staged 43 files into
  `/usr/share/nuxel` and `/usr/lib/nuxel`, verified every target by SHA-256,
  installed atomically and re-ran the coalesced service restarts and health
  checks. A second 18-file pass pinned `v0.7.1-beta`, updated the bridge/
  notification/portal units and applied the PWA server ownership fix. Installed
  bytes match the repository; no partition or kernel flash was performed.
- **PWA server ownership race fixed.** `nuxel-web.service` is the single owner
  of `127.0.0.1:8000`. The launcher session's development fallback now binds
  `127.0.0.1:8001`, and `nuxel-wayland.service` is ordered after
  `nuxel-web.service`. A `nuxel-web` restart can no longer fail with
  `OSError: [Errno 98] Address already in use` because the session fallback
  already holds the port.
- **Launcher cache `v49-v071-release`** with `a81` cache-busters for the theme,
  haptics, widgets, launcher, home-settings, touch-keyboard, status-bar and
  `app.js` assets.
- **Whole-repo lockstep bump to `v0.7.1-beta`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, services and systemd environment pins,
  shell apps, OTA/VM tooling, captured-image provenance and release docs.
- **Verification:** the PWNAGE-30000 pytest suite, the core-app suite, the
  theme/haptics/widgets/WAV JS tests, the live-tool offline subset and
  `tools/verify-pwa-assets.sh` were run locally; the deploy transaction
  recorded 43/43 changed files with zero rollbacks and two passing health
  checks. The full repository-wide gate still reports the pre-existing
  infrastructure-group failures documented in the release notes. Physical
  touch-driven app acceptance remains the owner's test.

## [v0.7.0-beta] - 2026-10-27 - *Release: Tri-Link consoles, real hardware providers, GPS/Maps truth*

- **25000 — Live Console++.** The serial Live Console keeps its exclusive lock,
  framed command transport, verified output and recovery path while the
  launcher gains the indicator truth that a real USB data link is required.
- **26000 — Tri-Link.** Adds explicit `serial`, `wlan`, `usb` and `auto`
  transports, pinned Ed25519 host-key verification, public-key SSH, SHA-256
  verified put/get, exit-code preservation and a cross-transport deployment
  guard. Wi-Fi SSH is physically verified; USB-NCM remains an honest
  `BLOCKED_KERNEL_PANIC` (teardown panics this 4.14.253 kernel).
- **27000 — GPS/GNSS truth.** Location keeps distinct provider-unavailable,
  disabled, searching, no-fix, stale-fix and fresh-fix states. Maps consumes
  the canonical location provider; pins and cached coordinates are never
  presented as a GNSS fix.
- **28000 — Tri-Link UI.** The Applications drawer registers
  `org.nuxel.LiveConsole`, `org.nuxel.USBSSHConsole` and
  `org.nuxel.WiFiSSHConsole` exactly once, with real launch handlers and the
  unlock-to-Home state-machine fix.
- **29000 — hardware providers.** Settings gains Bluetooth, Location/GPS,
  Audio and Displays pages backed by the same authoritative providers as Quick
  Settings. Audio uses the real ALSA inventory and a numid-based low-volume
  mixer control (`HPOUT1 Digital Volume`) so status returns in <0.1 s instead
  of hanging in the MADERA name-based sget path; Bluetooth power uses `rfkill`
  + `bluetooth.service`; Displays reports the missing DRM layer instead of
  inventing a monitor.
- **Corrected Bluetooth blocker.** The owner-supplied BCM4375 HCD is present
  and checksum-verified, but the running 4.14.253 kernel was built with
  `CONFIG_BT_HCIUART` **not set**. `bcm43xx_bluetooth` is only the power/rfkill
  driver, so no HCI transport can register `hci0`; scanning cannot return
  devices until a scoped kernel rebuild. The provider now reports
  `BLOCKED_KERNEL` with that exact evidence, not a stale firmware-only error.
- **Remaining hardware blockers, stated plainly:** GNSS firmware/reader is
  absent; the MADERA `HPOUT1 Digital` unmute path wedges in kernel D-state;
  USB-C HDMI needs `CONFIG_DRM` + a Type-C DP Alt Mode stack. No fake device,
  fix, monitor or audible-sound claim is made.
- **Release/tooling fixes.** The live-deploy plan now covers every new console,
  Settings, Maps, bridge-provider and diagnostics file and explicitly names
  repository-only tests/backups plus image-managed orientation/metrics sources.
  The reboot policy now refuses repeated reasons/diagnostics **before** issuing
  a reboot, and its offline evidence-directory/thread handling was repaired.
- **Whole-repo lockstep bump to `v0.7.0-beta`** across `VERSION`, APKBUILDs,
  PWA/bridge manifests, service/version pins, shell apps, OTA/VM tooling,
  launcher cache namespace (`v48-v070-release`) and release docs.
- **Verification:** `tests/` 56 passed; `tools/beta/live/tests` 187 passed;
  the bridge hardware/app suites, A34 touch suite, A40 launcher suite, A45
  lockscreen/unlock tests and the packages/registry checks were run locally.
  The GitHub workflow rebuilds the S10+ image set from this same commit.

## [v0.6.7-beta] - 2026-10-26 - *Release: green release gate + transactional Live Console deploy*

- **The red release gate from the last `main` run is fixed.** The
  v0.6.6-beta run failed in
  `tools/s10plus/a45/test-lockscreen-indicators.py`: GCC's
  `-Werror=format-truncation` rejected `ind_pid_holds_tty()` and the indicator
  path buffers in BOTH native host copies. The paths are now sized for the
  worst case (root + a 255-byte dirent + the `/state`/`/online` suffix) and
  truncation is checked before use. Both `a33` and `a45` sources compile clean
  under `-Wall -Wextra -Werror`; the release-gate compile no longer depends on
  the host compiler's warning heuristics.
- **A77 USB-detach truth ships in this release.** After a real cable pull the
  cyan PC penguin and the amber Live Console penguin now clear. The measured
  detach log shows this kernel leaves `typec/port0/data_role` and the UDC
  `state` stale at `host [device]` / `configured`, so A77 adds two independent
  detach signals to both truth providers: a non-connected UDC
  `current_speed` (`UNKNOWN`) and wired VBUS `online=0`. Wireless charging is
  excluded; absent signals stay neutral. `live_console.active` follows the
  corrected data link; the console daemon is never killed to hide the icon.
- **Live Console deploys are transactional.** `declared_reload` and
  `systemctl restart` now run once per deploy group instead of once per file;
  a failed group rolls its files back and re-runs the coalesced activation
  plan. Large payloads use an acknowledged block transfer with a bounded
  retry/rewind and the proven frame-per-chunk path as fallback. Offline
  coverage is in `tools/beta/live/tests/test_live_reload_and_transport.py`;
  the protocol is documented in
  `docs/beta-finalization/live/TRANSACTION-RELOAD-AND-BLOCK-TRANSPORT.md`.
- **Release visibility.** The workflow still publishes the beta as GitHub's
  **Latest** release (`--latest`), which is what puts it in the repository
  sidebar; the tag and title keep the `-beta` suffix.
- **Whole-repo lockstep bump to `v0.6.7-beta`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, services and systemd `Environment=` pins,
  shell apps, OTA/VM tooling and release docs.
- **Release status:** all offline gates that the release workflow runs were
  executed locally before the tag; the workflow then builds the S10+ image set
  from the merged commit and publishes it. Hardware acceptance remains
  pending (see `docs/releases/v0.6.7-beta.md`).

## [v0.6.6-beta] - 2026-10-26 - *Unreleased: release workflow failed; superseded by v0.6.7-beta*

- **Ghost PC / Live Console penguins fixed.** After connecting to a PC and
  physically unplugging, the cyan PC penguin and the amber Live Console penguin
  now clear. Root cause proven from the phone's own detach log: on this
  SM-G975F 4.14.253 kernel `typec/port0/data_role` stays `host [device]` and
  `udc/10c00000.dwc3/state` stays `configured` after a real cable pull, so the
  A73/A74 Type-C veto could never fire. A77 adds two independent, safe detach
  signals to both truth providers: a readable non-connected UDC
  `current_speed` (`UNKNOWN`) and wired VBUS `online=0`. Wireless charging is
  excluded; absent signals stay neutral. Charging remains independent.
- **Live Console follows the corrected data link.** `live_console.active` is
  gated by `usb_data.pc_connected`, so one detach clears both icons in the same
  read; the console daemon is never killed to hide the icon. The indicator API
  now also reports `usb_data.vbus_present` and `usb_data.udc_speeds`.
- **Launcher cache `v46-a77-usb-detach`** with `a77.1` cache-busters, because
  `js/lockscreen-indicators.js`, `index.html`, the manifest and `sw.js` all
  changed. A v44 cache must not survive this release.
- **Release visibility fixed.** The release workflow now publishes the built
  beta as a normal release and explicitly marks it **Latest**, instead of
  publishing only a prerelease. Prereleases cannot be GitHub's "Latest
  release", which is why the sidebar still showed v0.6.0-beta while v0.6.3 and
  v0.6.5 were visible only on the Releases page. The tag/title still carry the
  `-beta` suffix and the notes state the beta status.
- **Whole-repo lockstep bump to `v0.6.6-beta`** across `VERSION`, device
  `APKBUILD`s, PWA/bridge manifests, services and systemd `Environment=` pins,
  shell apps, OTA/VM tooling, the animated-home `metainfo.xml` and release docs.
- **Installed-phone capture refreshed.** `release/s10plus/` now carries the
  SHA-256 inventory of the userspace actually running after the A77 live
  deployment (2,959 entries) plus the re-verified byte-exact installed BOOT
  image. The workflow publishes these with the CI-built image set.

## [v0.6.5-beta] - 2026-10-26 - *Released: A76 whole-repo lockstep + green release gate*

- Whole-repo lockstep bump to `v0.6.5-beta`: the `VERSION` file already said
  `v0.6.5-beta`, but the device `APKBUILD`s, PWA/bridge manifests, bridge,
  portal and notifications hosts, systemd `Environment=` pins, shell apps,
  OTA/VM tooling and Home `metainfo.xml` were still pinned to `0.6.3-beta`.
  `pwa/nuxel-common/bridge-version.json` `host_version` now agrees with the
  installed `NUXEL_BRIDGE_VERSION` pins, which `verify-app-registry.py` checks.
- Release gate repair — the reason every `main` release run went red:
  `tools/s10plus/a43/test-a43-source.py` and
  `tools/s10plus/a34/tests/test-qs-gesture.js` hard-coded `0.6.3-beta`, so the
  A43 source contract failed the moment `VERSION` moved. Both now derive the
  expected version from `VERSION`, so a future bump cannot break CI again.
  `tools/s10plus/a34/test-decon-presentation-contract.py` also asserted a
  pre-A65 brace layout; it now asserts the real invariant (every *changed*
  frame is committed) instead of one historical `else {` arrangement.
- Launcher cache advanced to `v44-a76-lockstep` (`sw.js` + manifest
  `nuxel.cache_version`) because `home-settings.js`, `status-bar.js` and
  `bridge.js` changed; a v43 cache must not survive this release.
- Radio/privacy truth: the PWA bridge no longer answers
  `permissions.request`, `network.wifi-*`, `bluetooth.*` or `location.*` with
  the development mock-success fallback — an unavailable provider now returns
  an explicit `offline` error. The bridge also bounds `RequestScan` to 5 s so a
  recovering radio cannot block the shared D-Bus handler, and grant loading
  ignores malformed/boolean/policy files instead of crashing at startup.
- Release path unchanged: the workflow builds `s10plus` on the merged `main`
  commit, verifies every gate, creates the annotated `v0.6.5-beta` tag and
  publishes the prerelease, including the captured installed-phone boot image.

## [v0.6.5-beta] - 2026-10-23 - *Operation Penguin Hyperfix 14000 (interim, unreleased)*

- A65-01: installed glib-networking (GnuTLS GIO backend) on the S10+ and added it
  to the Fedora rootfs build + essential-package manifest, so WebKitGTK/libpsoup3
  now performs real HTTPS with certificate verification (google.nl/example.org
  load; badssl rejected). Root cause: package was missing -> `GDummyTlsBackend`.
- A65-11: Calculator no longer evaluates while typing; result updates only on Equals.
- A65-08/15: native browser toolbar made compact/responsive and the redundant GTK
  titlebar removed; native camera made undecorated.
- A65-12/13: Camera PWA and native camera show concise status, a Retry action and a
  collapsible Technical diagnostics panel; native camera gained an explicit Close.
- A65-02/09: verified Wi-Fi and battery reporting are truthful end-to-end (live
  NM state 100/connectivity 4; battery 100%/Full) and deployed bytes match repo.
- A65-10: seven rotation modes remain selectable; sensor auto-rotation is
  BLOCKED_HARDWARE (BCM4773 exposes no IIO accelerometer channels on this kernel).
- Documentation and rollback runbook under `docs/a65-hyperfix-14000/`.

## [v0.6.4-beta] - 2026-10-23 - *Penguin launcher resurrection*

- Emergency UI-only repair: restored the on-device `launcher.css` bytes
  (`9d56a005…`, 12764 B) after the A63 partial deploy left it 0-byte, which
  broke the Home grid, app-icon scaling, status bar and bottom dock. No
  kernel/partition changes, no reboot, no factory reset.
- Hot-reloaded the WebKit launcher over the USB Live Console via the
  `/run/nuxel-pwa-host.cmd` control FIFO and recovered the blanked panel
  backlight (`bl_power` 4 -> 0).
- Added the A64 safety baseline, visual diagnosis, change map, test receipts,
  physical pass matrix and rollback runbook under
  `docs/a64-launcher-resurrection/`.

## [v0.6.3-beta] — 2026-10-23 — *Release ships the exact installed S10+ image*

- The GitHub release now publishes `nuxel-installed-s10plus-boot.img.gz`, the
  byte-exact A27 BOOT image read back from the owner's SM-G975F
  (`48ad61afa91b6fe50278443ecae0695724f706a80de383e0acb021d030620cea`,
  51,605,504 bytes), plus a hash inventory of the installed userspace and
  `INSTALLED-IMAGES.json` provenance.
- `tools/release/verify-installed-image.py` gates publication on the gzip
  stream, v1 `ANDROID!` header, raw arm64 kernel, load addresses and
  kernel/ramdisk hashes. The CI-built A25 image remains in the device archive
  but is explicitly labelled a source rebuild, not the installed image.
- Fixed the Fedora `-Werror=unused-result` build failure in
  `services/nuxel-metrics/nuxel-metricsd.c` that turned the previous `main`
  release run red.
- Aligned the A40 offline gates with the shipped sources (Back long-press
  threshold, display-off/lockscreen pause, backgrounded-app polling) and made
  the Home PWA cache version match `sw.js` (`v33-a59-rescue`).
- Marked the committed Toybox interpreter and asset tools executable so a clean
  checkout can build the shared initramfs.

## [v0.6.3-beta] — 2026-10-20 — *S10+ connectivity UI and beta release wiring*

- Restored the background layer's visibility for the four-shortcut dock and fixed
  responsive artwork sizing while preserving BG1/BG2 selection (BG2 default).
- Home gesture threshold and compositor-friendly shade/drawer/page transitions;
  prevent WebKit gesture zoom on the Home document, not on browser webpages.
- NetworkManager-backed Settings tab: Wi-Fi status, scan, radio power, D-Bus
  connection activation, and disconnect. No separate supplicant is launched;
  credentials are passed to NetworkManager and never written to command argv.
- Existing Nuxel Browser remains a WebKit page viewer with external navigation
  opt-in; websites that forbid iframe embedding still require a native top-level
  WebKit browser integration. No physical HTTPS browsing is claimed.
- Release workflow builds verified Fedora ARM64 S10+ artifacts on a main-branch
  VERSION bump or explicit version tag, and attempts annotated tag plus GitHub
  prerelease publication after the full artifact gate passes.
- **Not hardware verified:** actual Broadcom Wi-Fi association/internet, speaker,
  camera, Bluetooth, NFC, GNSS or S10+ image boot. `final.md` tasks are tracked
  as independent evidence gates, not all declared production-complete.

## [v0.6.1-beta] — 2026-10-20 — *haptic feedback, triple-button support and live A40 system monitor; whole-repo patch bump*

- **Whole-repo version bump to `v0.6.1-beta`.** `VERSION`, the device `APKBUILD`s
  (s10plus, g7power, google-pixel-10-pro-xl), PWA/bridge manifests
  (`package.json`, `manifest.json` + `pwa_version`, `bridge-version.json` host
  version), shell apps (Home metainfo / About Phone strings), bridge/notification/portal
  services, the OTA builder and VM tooling all move in lockstep. The PWA protocol pin
  (`NUXEL_BRIDGE_VERSION = '1'`) is intentionally left unchanged — only the host
  *implementation* version moves; historical changelog entries are preserved untouched.
- **Haptic feedback (A38).** Staged haptic patterns with distinct tap/scroll/long-press
  intensities and durations, a single `nuxel-haptics` writer unit, per-user intensity
  preferences and an on-device Haptics control surface. Intensity is reported honestly
  and falls back to unsupported rather than fabricating an amplitude the motor cannot do.
- **Triple-button support (A38).** Button handling extended beyond the previous two-button
  model so a third button state is wired through the existing input -> UI path, with the
  Bixby/shortcut default action preserved as the Terminal.
- **Live A40 system monitor.** `services/nuxel-metrics` (AArch64 `nuxel-metricsd`) reports
  CPU (`/proc/stat` deltas), RAM (`MemAvailable`), GPU (documented Mali node when exposed)
  and shared GPU memory that is reported unavailable rather than invented. Deployed via the
  socket-activated metrics service through the A40 live payload; device values remain
  UNVERIFIED on the phone until a Milestone A live deployment completes.
- **S10+ release image unchanged in build method.** The GitHub Actions `s10plus` job still
  compiles the current A34 TOUCHDOWN userspace from repo sources inside a Fedora 43 arm64
  container, embeds the repo-source initramfs in a RAW arm64 kernel Image (never Image.gz —
  S-Boot executes a gzip payload as code) and packs it into the legacy v1 boot.img with the
  merged board DTB. CI checks out this same source tree, so it reproduces exactly what ships.
- **Documentation sync.** README changelog headers, "What's new" section, release-tag link and
  CHANGELOG all reflect `v0.6.1-beta`; readiness percentages are carried forward from v0.6.0-beta
  unchanged (no new hardware verification landed in this patch — see honesty note below).

**Honesty about what is verified.** The haptic patterns, triple-button wiring and the A40
monitor are software staged in this release but have **not yet been exercised on physical
hardware**; they land on the phone through the A40 live payload pending a Milestone A
deployment. The CI build reproduces the committed sources bit-for-bit; nothing about the boot
chain, initramfs embedding or A34 userspace compile changed in this patch.

---

## [v0.6.0-beta] — 2026-10-19 — *touchscreen works: v0.5.2-beta live on the handset, image built exactly as shipped*

- **Touchscreen works.** The Operation Touchable A34 TOUCHDOWN pass (A34 Wayland
  framebuffer `bl_power=4` screen-off path + decon/frame-commit contract tests)
  that landed in v0.5.2-beta is the current, working state: real finger contacts
  reach evdev -> libinput -> phoc -> WebKit and taps are delivered. This release
  ships that exact runtime — no silent rollback to an older userspace.
- **The S10+ release image now builds exactly what runs on the phone.** The GitHub
  Actions `s10plus` job compiles the current A34 TOUCHDOWN userspace from repo
  sources inside a Fedora 43 arm64 container (`nuxel-wl-fb`, `nuxel-button-manager`,
  `nuxel-pwa-host`, libinput shim, `nuxel-wl-snapshot`) and embeds the repo-source
  initramfs in a RAW arm64 kernel Image (never Image.gz — S-Boot executes a gzip
  payload as code), packed into the legacy v1 boot.img with the merged board DTB.
  No developer-only `build/out/s10plus/a32` tree is copied; CI reproduces the
  handset bit-for-bit.
- **Whole-repo version bump to `v0.6.0-beta`.** `VERSION`, the device `APKBUILD`s
  (s10plus, g7power, google-pixel-10-pro-xl), PWA/bridge manifests
  (`package.json`, `manifest.json` + `pwa_version`/`cache_version`,
  `bridge-version.json` host version), shell apps (`meson.build`, Home metainfo,
  About Phone strings), bridge/notification/portal services, the OTA builder and
  VM tooling all move in lockstep. The PWA protocol pin (`NUXEL_BRIDGE_VERSION =
  '1'`) is intentionally left unchanged — only the host *implementation* version
  moves; historical changelog entries are preserved untouched.

---

## [v0.5.2-beta] — 2026-10-18 — *interaction and reproducible release candidate*

- Added explicit launcher application lifecycle states and common surface cleanup;
  failed PWA loads remain visible and escapable.
- Repaired Terminal Shift, symbols and Backspace history behavior while retaining
  the real PTY host bridge and `term_close_window()` lifecycle.
- Staged the existing Stevia keyboard configuration/applier/user units into the
  S10+ Fedora image and made the rootfs verifier gate current launcher/Terminal
  assets.
- Normalized release tags to exactly one leading `v`, rejected tag/`VERSION`
  mismatches, and pinned build, packaging and release creation to one source SHA.
- Added the v0.5.2 finalization evidence set. The A34 real-finger app launches
  remain proven; the longer owner navigation/keyboard sequence is explicitly
  still `NEEDS_OWNER_TEST` because this session could not open the USB console.

## [v0.5.1-alpha] — 2026-10-18 — *current-state cleanup + reproducible A34 image*

**The S10+ image chain is now reproducible from a clean checkout.** The release
workflow used to copy `build/out/s10plus/a32/*` binaries that only existed on a
developer machine, so a fresh CI run could not build the userspace the handset is
actually running. The Fedora 43 arm64 rootfs builder now compiles the **current
A34 TOUCHDOWN userspace from repository sources inside the container**:

- `nuxel-wl-fb` (A34 display bridge, `bl_power=4` screen-off path),
- `nuxel-button-manager` (A34 `SYN_REPORT` touch translation, 11-entry power
  menu with **Cancel first**, deferred Bixby cancelled by Power),
- `nuxel-pwa-host` (current terminal-surface close + host-action fixes),
- `libnuxel-libinput-path.so` (capability-based shim for the 4.14/udevd-less
  kernel), and
- `nuxel-wl-snapshot` (current screencopy diagnostic).

`tools/s10plus/verify-fedora-phone-rootfs.py` now rejects an image that lacks any
of those binaries or the current `button-fsm.json` / `reboot-gate.json` configs,
and the workflow runs the A34 and A33 touch regression suites before packaging.

**Current hardware truth on the S10+ (SM-G975F):**

- Nuxel boots: S-Boot -> raw arm64 `Image` with embedded initramfs -> Fedora 43
  ext4 rootfs -> systemd 258 PID 1 -> service graph `running`.
- The display path works: boot animation, Wayland screencopy bridge, launcher,
  single framebuffer owner.
- **The touchscreen works**: real finger contacts reach evdev, libinput, phoc and
  WebKit (`pointerdown`/`touchstart`). Touch coordinates and gestures are
  delivered.
- **Clickable interaction is still not signed off.** Taps are delivered, but
  reliable in-UI clicking/navigation is the remaining open owner test.
- **Sound should work but is not proven on the handset.** The ALSA/UCM routing
  and diagnostics are present and VM audio is proven, but the phone's audio
  cannot be exercised through the UI until clicking works reliably.

**Repository cleanup.** Removed the legacy top-level mission notes and scratch
captures (`yolo*.md`, `task*.md`, `35b.ms`, `ad.md`, `fb.md`, `heim*.md`,
`.ocean.dtb/.dts`, `report-workspace-context.md`), the obsolete `finish/` and
`finish2/` trees, the duplicate/stale flash guides, and the superseded
`S10PLUS-*` progress notes. Only the canonical currently-flashed image set is
kept under `build/out/` locally (S10+ BOOT + rootfs, G7 Power lk2nd + BOOT +
rootfs); all older candidate images and kernel build trees were deleted.

**Version bump to `v0.5.1-alpha`** across `VERSION`, the device `APKBUILD`s,
PWA/bridge manifests, services, shell apps, VM tooling, current docs and the OTA
builder.

---

## [v0.5.0-beta-rc1] — 2026-10-17 — *live service-graph repair + device evidence (task2 continued)*

**Version still unchanged:** same rationale as above; this pass repairs the live service graph and
timekeeping rather than adding feature surface.

* **Service graph brought to `systemctl is-system-running` = `running` with 0 failed units.** The
  hardened units for `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-notifications` and `nuxel-portal`
  depended on identities/directories that had never been provisioned on the device.
  - Added idempotent `tools/s10plus/a33/nuxel-provision-services.sh` (users `nuxel-bridge`,
    `nuxel-notifications`; dirs `/var/lib/nuxel/permissions`, `/var/log/nuxel`).
  - Installed `python3-dbus`, `python3-gobject`, `python3-gobject-base`, `python3-cairo` on the
    phone (aarch64 Fedora 43 RPMs, verified over the console, `rpm -i`).
  - `services/nuxel-bridge/src/bridge.py`: replaced the non-existent `dbus.service.property` with a
    real `org.freedesktop.DBus.Properties` Get/GetAll implementation.
  - `org.nuxel.Bridge.conf`: removed the invalid `<limit name="log_level">info</limit>` that made
    dbus-daemon reject the whole policy file; added `nuxel-bridge` own-name policy. Added
    `nuxel-notifications` own-name policy to `org.nuxel.Notifications.conf`.
  - `nuxel-http-bridge.service` runs as root: the Samsung 4.14 vendor `ncm` module denies
    AF_INET/AF_INET6 socket creation to non-root UIDs (kernel limitation, documented).
* **Time/RTC repaired.** Device clock was ~1 month behind (`Sep 15`); set to real time
  (`date -s`), `hwclock -w -u`, timezone `Europe/Amsterdam` via `/etc/localtime`.
* **Reboot defect found + fixed.** `systemctl reboot` hung on logind D-Bus activation (boot_id
  unchanged). Default `--reboot-cmd` in `nuxel-live-reboot-verify.py` is now
  `systemctl reboot --force` (still a normal, non-recovery reboot).
* **Touch pipeline diagnosed.** `sec_touchscreen` (event2) -> phoc/libinput (phoc holds
  event2/event4) all present on a non-charger boot; real-finger proof remains `NEEDS_OWNER_TEST`.
* **Bounded soak sample** (two samples, 60 s apart): no reboot, 0 failed units, single fb owner,
  launcher 200, no unbounded RSS/CPU growth (preliminary, not the 8 h tier).
* Evidence: `docs/beta-finalization/live/{BASELINE-CAPTURE.md,DEPLOYMENTS.md}` and
  `docs/beta-finalization/live/evidence/{baseline,deploy,reboot-verify}-20261017T*`.

---

## [v0.5.0-beta-rc1] — 2026-10-16 — *live deployment cycle (task2)*

**Version unchanged on purpose:** this cycle does not add a new feature surface, it moves what was
already written onto the physical handset. The identifier stays `v0.5.0-beta-rc1` (no silent
renumber); the release engineering that justifies `-rc1` is unchanged, and the Beta verdict is still
`BETA_CANDIDATE_PENDING_HARDWARE_PROOF`.

**Landed on the phone (S10+ `beyond2lte`, from host `dextronux`):**

* **Root fix.** The deploy plan now resolves onto `/usr/share/nuxel` — the root the handset actually
  serves — instead of `/home/nuxel/nuxel`, which does not exist on the device. 440/624 targets were
  pointed at a tree nothing reads; that was why earlier passes produced "no difference on my phone".
  Manifest gains a `target_root_map`; `nuxel_live.build_deploy_plan` applies it before guarding.
* **Applied** the 16-group / 624-step plan (5 runs): launcher + safe zones (22/22), PWA app suite +
  shared runtime + registry (400/400), configs / a33 tools / services / native-shell sources /
  touch+buttons / audio+network (185/185), a33 runtime + session units + boot animation + packages
  (64/64, 4/4 health checks), animation handoff (2/2). Files hash-verified on-device; the served
  launcher hash equals the repository and 25 apps answer `HTTP 200`.
* **Boot mode.** Two normal OS reboots cleared the LPM/charger-mode boot and armed the touchscreen
  (`sec_touchscreen`, `INPUT_PROP_DIRECT`, `sec_ts` IRQ 431, all units active, 0 failed). A recurrence
  was traced to an 11.6 s hardware POWER-key hold; the offline bootmode guard stays `BLOCKED_KERNEL`.
* **Persistence.** The deployed userspace survived a reboot (served launcher hash unchanged).

**Live-tooling fixes (each blocked the deploy):** CRLF frame normalisation; sysfs hex `idVendor`
parsing (Linux console discovery found zero nodes); `MAX_WRAPPER_LEN` raised 480→3800 after measuring
the real tty limit; `chunk_size_for` now returns the largest fitting chunk; `install_script` no longer
reverts every successful install via a stray trailing rollback; group health checks run once per group
rather than inside every file's install; the flash-tool guard no longer matches `pit` inside base64;
`push_bytes` writes idempotent per-chunk part files and verifies the staged hash on-device; the deploy
plan validates `--only` against the full manifest; the apply loop auto-reconnects the console and skips
already-current files (resumable).

**Honest gaps recorded, not hidden:** human touch/audio/button/radio acceptance is `NEEDS_OWNER_TEST`;
`nuxel-portal`/`nuxel-bridge` are deployed but not enabled; the device clock is wrong
(`2026-09-15` vs the real `2026-10-16`); `flatpak` is still absent so NuXtore has no backend.

**New artefacts:** `docs/beta-finalization/live/BASELINE-CAPTURE.md`,
`docs/beta-finalization/live/DEPLOYMENTS.md`, evidence bundles under
`docs/beta-finalization/live/evidence/{baseline,deploy,reboot-verify}-*`.

---

## [v0.5.0-beta-rc1] — 2026-10-16

**Theme:** the alpha hardware bring-up becomes a *maintainable* beta candidate.
The device truth is now recorded per subsystem instead of asserted, the whole
programme runs through a resumable on-disk work queue, and the release gate has a
real test hierarchy, a bounded soak, a reboot policy and a rollback discipline
behind it.

> **This is a beta CANDIDATE (`-rc1`), not a beta release.** The identifier is
> justified because the *release engineering* (queue, gate, soak, rollback,
> capability manifest) now exists and is offline-tested — and because the
> hardware story is honest rather than finished: the phone boots Fedora 43 with
> systemd, the launcher runs on the panel through the Wayland→framebuffer
> bridge, the live console is proven, and the separate subsystems say plainly
> which of them are still unproven. Per-subsystem status is **not** in this file:
> it lives in [`docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md`](docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md)
> (machine-readable twin `.json`, cross-checked against the work queue by
> `tools/beta/validate-capability-manifest.py`). Words like "working" in this
> changelog mean "exists in the repository and passed its offline suite" unless a
> live capture is cited.

### Added — release engineering (this cycle's deliverable, `bg-09`)

- **`tools/beta/run-all-tests.sh` — the release gate.** One command runs every
  offline suite plus the A32 baseline regression guard, prints a per-suite table
  (`ID / TIER / STATUS / OWNER / CHECKS / SECS`) and exits non-zero on any hard
  failure. `CHECKS` is the number of PASS-shaped assertion lines the suite
  printed (a floor, never a coverage claim). `--list`, `--only REGEX`, `--strict`,
  `--external`, `--json -` (pure JSON on stdout, transcript on stderr), `--quiet`.
  The machine summary carries `gate` **and** `raw_gate`, `counts`, every
  `failures[]` entry attributed to its owning group, and `allowances_applied[]`.
- **`docs/beta-finalization/testing/TEST-STRATEGY.md`** — the L1–L6 hierarchy
  (static → unit → integration → UTM VM → live phone → owner physical),
  what each tier may claim, the hardware truth table that constrains those
  claims, and the rule that a metric the phone could not produce is reported
  unproven rather than assumed healthy.
- **`docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`** + the extended
  harness. The soak is bounded (default ≤ 30 min for an autonomous run, 8 h on
  the device tier) and now measures, in addition to stability: **disk headroom,
  swap pressure, WebKit subprocess count and memory, Phoc CPU/RSS, the
  framebuffer bridge's CPU and commit volume, leftover animation processes,
  runnable-process count and the input-node inventory** — alongside the existing
  reboot / failed-unit / launcher-availability / single-framebuffer-owner /
  stack-CPU / RSS-growth / service-restart / thermal findings. Unreachable
  console ⇒ `BLOCKED_EXTERNAL_RESOURCE`, never a fabricated sample.
- **`tools/beta/rollback.sh`** — record previous hash → stage → verify sha256 →
  atomic install → restart only the smallest affected service → health-check →
  **automatic rollback** on failure. Per-task baselines under
  `/var/lib/nuxel/rollback/<briq-id>/` via the new `--briq` switch.
- **`tools/beta/reboot-policy.sh`** — the pre/post reboot checklist (live console,
  progress saved, logs flushed, systemd ready, no package transaction, known-good
  rollback, bounded reconnect) plus mechanical refusals: no reason, blind repeat,
  repeated reason, previous reboot never returned, no known-good rollback,
  3-reboot budget, and the mode-scoped **three-same-mode-failures** guard. It
  never reboots on its own initiative.
- **`docs/beta-finalization/release/REBOOT-ROLLBACK.md`** and **`ROLLBACK.md`** —
  the discipline, the component map, the backup paths and the rollback routes,
  including the time-bounded auto-rollback rule for security/network changes that
  could cut the only reachable console.
- **`docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.{md,json,schema.json}`**
  and **`tools/beta/validate-capability-manifest.py`** — 41 subsystem entries,
  each naming the work-queue record that authorises it; the validator rejects any
  verdict stronger than the record's (schema validation **and** cross-check).
- **`tools/beta/tests/test-rollback-reboot.sh`** — 22 mocked-failure scenarios
  that prove the rollback really triggers and the reboot path is inert.

### Changed

- **`VERSION`** → `v0.5.0-beta-rc1`, in lockstep with this entry.
- **`tools/beta/soak.sh` / `soak_lib.py`** — the probe emits a second short line
  (`SOAK2`) for the resource/performance metrics, and two sample families are now
  explicitly separated: *gated* (decides the verdict) and *recorded* (warns).
- **`tools/beta/run-all-tests.sh`** — the JSON emitter no longer writes invalid
  JSON for a suite that never ran (`"rc": -` → `null`), the external tier is
  reported as `EXTERNAL`/`BLOCKED_EXTERNAL_RESOURCE` instead of the meaningless
  `EXTERNAL_EXTERNAL`, and cross-group allowances are now **evidence-derived**:
  an entry is honoured only while its owning group still has an unfinished record
  in the work queue, so it stops working by itself when that group lands.
- Legacy alpha-cycle gates (`tools/s10plus/a27/*`) are precondition-gated with a
  `probe:` prerequisite: a missing alpha build artefact or host tool is a loud
  `SKIP` that names the missing piece, never a silent pass and never a fake
  failure.

### Fixed

- **Invalid machine-readable summary** (`"rc": -` for a suite that never ran)
  made `summary.json` unparseable whenever any suite was skipped. Fixed and
  covered by the release-tooling self-test.
- **`tools/beta/tests/test-release-tools.sh`** had a stray `from release_lib
  import` line that made the `release_lib.py` unit block die with a SyntaxError;
  the block now runs.
- **The release-tool self-test asserted the wrong stream**: with `--json -` the
  gate now keeps stdout pure JSON and moves the human transcript to stderr, and
  the test captures the two streams separately.

### Preserved from A32 (do not start over)

The A32 hardware-proven baseline is unchanged and still guarded, as hash pins and
behavioural invariants in `docs/beta-finalization/baseline-protection.json` plus
`tools/beta/regression-guard.sh` (passing in the release gate): Fedora 43 ARM64 +
Samsung Linux 4.14.253 with systemd PID1 and the USB CDC-ACM console, the DECON
framebuffer at 1440×3040, the XRGB8888→Samsung ABGR8888 screencopy translation,
Phoc headless + the Wayland→framebuffer bridge, the original MP4 boot animation
with a single framebuffer owner and receipt-driven handoff, the WebKitGTK Nuxel
Home PWA as the authoritative launcher, the A32 button manager, and the ten-zone
status-bar safe areas.

### Still open / not claimed (see the capability manifest for the full matrix)

- **No subsystem in this release is `VERIFIED_ON_S10PLUS` by this cycle.** The
  live preflight was read-only; the manifest caps every entry at its recorded
  offline/vendor ceiling, and no entry in it claims live verification from this run.
- The touch controller is present but **deliberately not initialised** while
  `androidboot.mode=charger` sets `lpcharge=1` (`sec_ts_init: Do not load driver
  due to : lpm 1`); touch is `BLOCKED_KERNEL` on the boot mode until a normal
  boot is performed, and the finger test is `NEEDS_OWNER_TEST`.
- Wi-Fi enumerates (`brcmfmac`, `wlan0`/`wlan1`, unblocked, **down**) but
  association/DHCP/DNS/reconnect are unproven; Bluetooth is soft-blocked;
  ModemManager reports `No modems were found` despite the Shannon `rmnet*`
  interfaces; `pipewire`, `wireplumber`, `alsa-utils` and `flatpak` are **not
  installed** on the phone.
- There is **no exposed battery-backed RTC** (`timedatectl`: *RTC time: n/a*); the
  device clock reads ~31 days behind the host and that already breaks RPM
  signature verification (`signature is not alive`). Time is therefore reported
  with its uncertainty rather than as a precise value.
- The 8 h device soak, the UTM tiers and every physical acceptance item are
  registered but **not executed** here: the soak and the VM tiers are
  `BLOCKED_EXTERNAL_RESOURCE`, and the physical items are `NEEDS_OWNER_TEST` in
  `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`.
- The release gate is **RED** at the time of this entry for two suites owned by
  another build group (`U-baseline-a32-suite` and `U-boot-s10plus-gates`, both
  needing alpha-cycle build artefacts that the beta build host cannot produce:
  the aarch64 bridge binary and the A5 boot fixture). They are attributed in
  `build/reports/beta-tests/summary.json` as `failures[]`; nothing here hides
  them, and `--strict` reports the raw verdict.

---

---

## [v0.4.0-alpha] — 2026-10-15

**Theme:** the Galaxy S10+ **boots Nuxel** — and the release CI now builds the
exact image that runs on the handset. The earlier "bootloops on the Samsung logo"
status is **superseded**.

### Proven on hardware (SM-G975F), each step with a device marker

| Step | Evidence |
|---|---|
| S-Boot loads and executes the Nuxel ARM64 kernel | S-Boot record + `linux_banner` in the ram console |
| Embedded Nuxel initramfs executes | `NUXEL_MARKER INITRAMFS_EXECUTED` |
| Nuxel `/init` runs, USERDATA discovered | `USERDATA_FALLBACK /dev/sda31`, `USERDATA_DISCOVERED` |
| Fedora ext4 rootfs mounts | `ROOTFS_MOUNTED /dev/sda31 ext4` |
| `switch_root` → Fedora systemd 258 PID 1 | `systemd[1]: systemd 258.11-1.fc43 … arm64` |
| systemd builds its unit graph / services execute / cgroup2 / journald | `Reached target basic.target` (A15); A18 spawn-failure fix |
| Stable boot without spontaneous reset | A15 ran 1892 s (operator reset only) |
| Nuxel renders on the AMOLED panel; spinning penguin | A16 first light on the DECON fbdev path |
| Original MP4 boot animation, 24.00 fps, 0 skipped frames | A21/A22 measurements |
| Panel colour order | ABGR_8888 proven from the driver commit path (A23) |
| Interactive live root console over USB | A21 acceptance suite; A24/A25 disconnect survival (HUP-proof, respawning supervisor) |
| Fedora userspace UI process + real framebuffer commit | A24 `UI_STARTED`, `FIRST_FRAME_COMMITTED fbio_pan rc=0` |
| Animation → UI handoff | A24 `ANIMATION_STOP_SIGNALLED`, `PHONE_UI_READY` |
| A25 (single-instance UI + console-owned postboot supervisor) | flashed to BOOT with full 51,718,144-byte SHA-256 readback PASS; boot is the next observation |

### Added

- **`tools/s10plus/build-a25-initramfs.sh`** — builds the A25 initramfs **from
  repo sources** (no local candidate base): freestanding aarch64 binaries
  (`nuxel-ui`, `nuxel-anim-player`, `nuxel-fb-phone`, `nuxel-syscall-probe`),
  static-glibc binaries (`nuxel-console`, `nuxel-hwprobe`, `nuxel-verify`), toybox
  + applets, `/init`, the systemd units, the post-boot supervisor and the pinned
  `libsystemd-shared`. Every member is re-extracted and hash-compared before the
  script reports success.
- **`tools/s10plus/mkinitramfs-cpio.py`** — deterministic newc packer used by the
  builder (works on macOS and Linux; no host `cpio`).
- **`images/s10plus/build-a25-boot.sh`** — the A25 BOOT image pipeline: build the
  initramfs → merge the board DTB (`fdtoverlay`) → **rebuild the kernel with
  `CONFIG_INITRAMFS_SOURCE`** → pack a legacy v1 `boot.img` with the **raw arm64
  `Image`** → gate the result.
- **`tools/s10plus/verify-a25-boot.py`** — fail-closed verifier: container
  structure (delegated to `verify-boot-image.py`, including the partition budget),
  raw (non-gzip) arm64 Image, the initramfs really embedded, the embedded archive
  identical member-by-member to the built one, the pinned systemd payload, and the
  ramdisk copy carrying the same archive.
- **`boot/s10plus/payload/libsystemd-shared-258.11-1.fc43.so`** (+ provenance
  README) — the kernel-4.14 `pidfd_spawn`/`pidref` patched library `/init` installs
  into the Fedora rootfs, SHA-256 pinned (`848149cf…`) by both the payload README
  and `boot/initramfs/init.sh`.

### Changed

- **`.github/workflows/release.yml`**: the S10+ job now builds the A25 image
  (`images/s10plus/build-a25-boot.sh`) instead of the legacy
  `--boot-images-only` `Image.gz` + external-ramdisk boot image; the shared
  initramfs step is now g7power-only; the Fedora 43 ARM64 phone rootfs step is
  unchanged.
- **`tools/verify-artifacts.sh`**: the s10plus branch no longer requires
  `Image.gz`; it requires the A25 contract (`Image-A25` + `initramfs-A25.cpio` +
  `nuxel-beyond2lte-boot.img`) through `tools/s10plus/verify-a25-boot.py`.
- **Docs/README status + scoreboard** updated to the proven state: build system
  58% → 85%, S10+ bring-up 55% → 85%, flashable images 80% → 90%, overall
  ~45–50% → ~60%.
- **Version bump to v0.4.0-alpha** across `VERSION`, README/design/docs, the flash
  guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling and the
  OTA builder.

### Still open (unchanged in kind)

- Touch input: every boot so far was `androidboot.mode=charger` (no touch device).
- Human-visible confirmation of the UI and of the animation colours.
- The Fedora boot graph stalls before `multi-user.target`; `bootreport.txt` now
  instruments which job stalls.
- Phosh/Phoc need DRM/KMS — this 4.14 vendor tree has `# CONFIG_DRM is not set`.
- Moto G7 Power still hangs at a black/flashy screen.

---

## [v0.3.3-alpha] — 2026-10-14

**Theme:** flashing is **proven** on the Galaxy S10+ — the full Nuxel image set
now writes to the handset and verifies on the device. The phone reaches the
Samsung logo and **bootloops**; boot-chain bring-up is the remaining work.

The S10+ **full image set** — the merged-DTB boot image
(`nuxel-beyond2lte-boot.img`) and the Fedora 43 aarch64 phone rootfs
(`nuxel-beyond2lte-rootfs-fedora-phone.img`, real Python / systemd / Phosh /
Phoc RPM binaries) — was written to **BOOT + USERDATA over ADB** and **read back
byte-for-byte** from the device. So flashing/transfer, partition sizing and the
storage handoff are no longer open questions: the device now **bootloops on the
Samsung logo**, which points at S-Boot handoff, kernel bring-up or the root
mount (systemd/init) rather than the flash.

### Added

- **S10+ bootloop debug pack** (`scripts/s10plus-debug-pack/`): a standalone,
  **read-only** observability toolkit (no `adb push`, `dd of=`, `flash`,
  `reboot`, `remount`, `mount`, `wipe` or `setprop`). It captures pstore /
  `/proc/last_kmsg`, TWRP recovery logs, partition/mount maps and an offline
  Android-boot-image + Fedora-rootfs inspection, produces an evidence-based
  `TRIAGE.md`, and ships an opt-in, best-effort redacted share bundle. See
  `docs/BOOTLOOP-DECISION-TREE.md`.
- **`images/s10plus/build.sh --boot-images-only`**: packs the S10+ boot image(s)
  and per-artifact checksums without invoking the (intentionally disabled)
  legacy shared rootfs bake, so the real Fedora rootfs can be built separately.

### Changed

- **The S10+ release job now builds the real image set.**
  `.github/workflows/release.yml` builds the merged board-DTB boot image (with an
  explicit board revision, `NUXEL_S10PLUS_BOARD_REV`) and the Fedora 43 ARM64
  phone rootfs via `images/s10plus/build-phone-rootfs-fedora.sh` in an arm64
  container, instead of the retired `images/s10plus/build.sh --device s10plus`
  path (which now fails closed rather than emit a skeleton/"incorrect-runtime"
  rootfs). Only the `s10plus` job changed; `g7power` is untouched.
- **`tools/verify-artifacts.sh` verifies the S10+ image set for what it is**:
  the merged board DTB, the `ANDROID!` boot image, and the Fedora ARM64 phone
  rootfs (via `tools/s10plus/verify-fedora-phone-rootfs.py --ext4`) — not the
  Plymouth-boot-splash payload that the legacy shared rootfs carried.

### Docs / version

- README status: **S10+ 38% → 55%**, **Flashable images 65% → 80%**, overall
  **~40–45% → ~45–50%**; S10+ row now states flashing is proven and the device
  bootloops on the Samsung logo. `S10PLUS-PROGRESS.md` updated to match.
- **Version bump to v0.3.3-alpha** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests + meson, the
  services, the VM tooling and the OTA builder.

---

## [v0.3.2-alpha] — 2026-10-13

**Theme:** make the release CI build the **same complete rootfs** a local build
does — the boot splash is no longer silently dropped.

Reported symptom: the S10+ rootfs published by CI still held only ~20 MB of
content while a local build's staging tree was ~60 MB. Root cause:
`images/mkrootfs.sh` builds the Plymouth boot theme through
`tools/build-nuxel-boot-theme.sh`, which needs **`ffmpeg`** to extract the
animation frames. `.github/workflows/release.yml` never installed `ffmpeg`, and
that step is deliberately non-fatal, so it logged a warning and continued — the
rootfs shipped without the ~50 MB frame sequence (96 PNGs) and the
`nuxel.plymouth` / `nuxel.script` descriptors. `tools/verify-artifacts.sh`
passed because it never checked for the theme.

Verified against the artifacts: a local rootfs image carries 96 `frame-*.png`
files (99 PNG signatures incl. wallpapers) and a `plymouth/` payload; the
v0.3.1-alpha CI image carried 2 PNGs (wallpapers only) and no `plymouth` payload
at all — i.e. 19.9 MB of non-zero inode data vs ~88 MB locally.

### Fixed

- **CI installs `ffmpeg`.** The Release workflow build dependencies now include
  `ffmpeg`, so `images/mkrootfs.sh` -> `tools/build-nuxel-boot-theme.sh`
  produces the Plymouth theme (96 PNG frames + `nuxel.plymouth` / `nuxel.script`)
  in CI exactly as it does on a dev box. This closes the local-vs-CI rootfs gap.
- **`tools/verify-artifacts.sh` is fail-closed on the boot splash.** For both
  `g7power` and `s10plus` it now requires, inside the ext4 rootfs:
  - `/usr/share/nuxel/boot/nuxel-boot-animation.mp4` (size-checked via `debugfs`,
    must be >= 1 MB), and
  - the generated Plymouth theme
    (`/usr/share/plymouth/themes/nuxel/nuxel.plymouth` + `frame-0001.png`).

  A rootfs that silently lost its theme — the exact v0.3.1-alpha CI failure — is
  now a hard failure instead of a green build.
- **Version bump to `v0.3.2-alpha`** across `VERSION`, README/design/docs, the
  flash guides, the device `APKBUILD`s, the shell/PWA manifests, the VM tooling
  and the OTA builder. The device `APKBUILD`s and shell/PWA `meson.build`s, which
  the previous bump left at `0.3.0-alpha`, are now in lockstep.

### Notes

- No hardware/boot status changed: still **0 of 3 phones verified booting**.
- The G7 Power rootfs gains the boot splash in CI too (same shared builder), so
  both bring-up phones now ship the full userspace + theme.

---

## [v0.3.1-alpha] — 2026-10-13

**Theme:** make the bring-up rootfs **actually contain a userspace**, and make
the artifact gate stop a near-empty image from ever being published as
"complete".

Reported symptom: the S10+ release archive was only ~21 MB (a 22 MB boot image
plus a 26 MB rootfs holding a **44 KB / 10-file** overlay), while a local build's
rootfs was ~60 MB+. Root cause: `images/mkrootfs.sh` declared every userspace
step but **never called them** — the script was a no-op that exited 0, so every
"rootfs" was only the per-device config overlay.

### Fixed

- **`images/mkrootfs.sh` now actually builds the userspace.** Added the missing
  driver (`main`): clean -> Flatpak/fallback base -> core services -> native apps
  -> security configs -> assets -> Plymouth theme -> directory/permission setup
  -> optional dm-verity image -> summary. Previously none of these ran, so
  `/usr/bin/nuxel-bridge`, `/etc/nuxel/paths.conf`, the AppArmor/nftables/sysctl
  configs and the boot theme were absent from every rootfs image.
- **`tools/verify-artifacts.sh` is now genuinely fail-closed.** It no longer
  accepts an image on a magic number alone:
  - boot images must carry a real kernel + ramdisk + device tree (Android v1
    header sizes must be non-zero) — an empty/placeholder header fails;
  - rootfs images must contain the expected payload (per-device config plus the
    Nuxel userspace core `/usr/bin/nuxel-bridge`), verified by reading the ext4
    contents with `debugfs` — the 44 KB S10+ image that shipped in
    v0.3.0-alpha is now a hard failure;
  - `NUXEL_S10PLUS_UBOOT=1` makes `u-boot-beyond2lte.img` a required artifact.
- **Rootfs images are sized from real content.** The 512 MB minimum floor in
  both device builders, combined with a `resize2fs -M` that cannot always shrink
  a many-small-file filesystem, produced a **512 MB** G7 Power rootfs in CI. The
  floor is now 64 MB and the image is sized from the staging tree (content + 25%
  + slack).
- **The S10+ build no longer reports a phantom `INCOMPLETE`.** U-Boot is a
  mainline-stretch artifact; the supported Phase-1 downstream/heimdall set is
  `boot.img` + `rootfs.img`, exactly as the flash guide documents. U-Boot is
  built when present and only fails the build when explicitly required
  (`NUXEL_S10PLUS_UBOOT=1`).
- **Version bump to `v0.3.1-alpha`** across `VERSION`, README/design/docs, the
  flash guides, PWA/shell manifests, VM tooling and the OTA builder.

### Notes

- **There is no `userdata.img`** by design in Phase 1: the rootfs image *is* the
  userdata payload (G7 Power: shared `userdata`; S10+: `SYSTEM`/`userdata`), so
  the archive ships `nuxel-*-rootfs.img`, not a separate `userdata.img`.
- **`lk2nd` is G7 Power-only** (`msm8953`). The S10+ is Exynos and never uses
  `lk2nd`; its chain is stock `S-Boot` -> (optional `u-boot-beyond2lte.img`) ->
  `nuxel-beyond2lte-boot.img`.
- Device-proprietary vendor blobs (`firmware/*/blobs/vendor-*`) remain
  **unshippable** (gitignored): CI builds the rootfs from repo sources only, so a
  CI image is smaller than a local one that has pulled those blobs. The gate
  verifies the repo-provided payload, not the non-redistributable firmware.

---

## [v0.3.0-alpha] — 2026-10-13

**Theme:** make the release pipeline **fail-closed and genuinely green** for the
two bring-up phones (**G7 Power** `g7power`/ocean and **Galaxy S10+**
`s10plus`/beyond2lte). Every build/release step for both phones now actually
produces its artifact, and the workflow can no longer report success when a
kernel / initramfs / boot image / rootfs is missing or invalid.

### Changed

- **`mustang` (Google Pixel 10 Pro XL) removed from the release workflow** for
  now. The build matrix is `g7power` + `s10plus` only; the `prepare` job filters
  any other device key out (with a warning) and fails if nothing supported is
  requested. `images/build.sh` still refuses non-mustang devices except in the
  new initramfs-only mode.
- **Per-device `sha256sums.txt` in every release archive.**
  `images/g7power/build.sh` and `images/s10plus/build.sh` now emit
  `sha256sums.txt` alongside the images, so the flash guides can verify each
  flashed artifact (`nuxel-ocean-boot.img`, `nuxel-ocean-rootfs.img`, `lk2nd.img`
  / `nuxel-beyond2lte-boot.img`, `nuxel-beyond2lte-rootfs.img`) before writing
  it to the device.
- **Version bump to `v0.3.0-alpha`** across `VERSION`, README/design/docs,
  APKBUILDs, PWA/shell manifests, services and the OTA builder.

### Fixed

- **Release workflow no longer goes green on a failed build.** All
  `continue-on-error: true` flags were removed from the build matrix, the
  "Package device artifact" step is no longer `if: always()` + best-effort, the
  upload step uses `if-no-files-found: error`, and the `publish release` job now
  runs only when the whole build matrix succeeded (`if: needs.build.result ==
  'success'`). A device whose kernel/images fail leaves the run **red** and no
  GitHub Release is created.
- **New strict artifact gate `tools/verify-artifacts.sh`.** After the image
  build, CI verifies (per device) that the kernel `Image.gz` is a real
  gzip-compressed **ARM64 Linux Image** (`0x644d5241`), that the board DTB is a
  valid FDT (`0xd00dfeed`), that the boot image carries the `ANDROID!` header,
  that the rootfs is `ext4` (`0x53EF` superblock magic), and — on G7 Power —
  that `lk2nd.img` is present. Any miss fails the job with `::error::`.
- **S10+ boot image now builds in CI.** The downstream Exynos 9820 tree ships
  only the SoC base DTB (`dts/exynos/exynos9820.dtb`) plus per-revision overlays
  (`dts/samsung/exynos9820-beyond2lte_eur_open_<rev>.dtbo`); the previous build
  looked for a board `.dtb` that is never produced, so `images/s10plus/build.sh`
  aborted with "No beyond2lte DTB found". It now merges base + highest-revision
  overlay into `exynos9820-beyond2lte.dtb` with `fdtoverlay`
  (`device-tree-compiler`) before packing, matching the previously-built local
  artifact byte-for-byte (376101 bytes, rev 26).
- **Shared initramfs is now a first-class step.** `images/build.sh` gained
  `--initramfs-only`, which assembles the device-agnostic initramfs, mirrors it
  to `build/boot-artifact/` and exits 0 — instead of the old "mustang dispatcher"
  invocation that exited 3 whenever the (now-removed) mustang kernel was absent.
- **G7 Power `lk2nd.img` is now built in CI.** New
  `boot/g7power/lk2nd/build-lk2nd.sh` clones `msm8916-mainline/lk2nd` and builds
  `lk2nd-msm8953` with the `arm-none-eabi` toolchain, producing the
  `lk2nd.img` that `images/g7power/build.sh` copies into the release. Without it
  the G7 Power artifact set was silently incomplete.

### Notes

- `g7power` kernel build time varies with runner speed (~25–47 min for the full
  mainline `msm8953` tree: `Image.gz` + `dtbs` + `modules`); both bounds are
  normal. The `s10plus` downstream 4.14 kernel builds in ~15 min.

## [v0.2.2-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.1-alpha — make the **S10+** and the
**Pixel 10 Pro XL (`mustang`)** kernel builds actually produce an `Image.gz` in
CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI).** v0.2.1-alpha forced `CROSS_COMPILE` and dropped
  compiler-unsupported KCFLAGS, but the build still failed on the runner's GCC 13
  because the downstream 4.14 Exynos 9820 tree hard-codes `-Werror` in two places
  a `KCFLAGS` relaxation cannot reach:
  - **per-category promotions** in the top `Makefile`
    (`KBUILD_CFLAGS += $(call cc-option,-Werror=strict-prototypes)` and friends,
    `Makefile:935-947`). GCC's "the more specific option wins, independently of
    order" rule means the generic `-Wno-error` appended via KCFLAGS does **not**
    downgrade them, so the build died on
    `block/blk-crypt.c:213: error: function declaration isn't a prototype
    [-Werror=strict-prototypes]`;
  - **per-directory flags appended after `KBUILD_CFLAGS`** on the cc command
    line — the bcmdhd Wi-Fi driver's
    `DHDCFLAGS += -Wall -Werror -Wstrict-prototypes` → `EXTRA_CFLAGS` →
    `ccflags-y`. That re-enables a general `-Werror`, so the build died on
    `drivers/net/wireless/broadcom/bcmdhd_101_16/wl_android.c:12016: error: the
    comparison will always evaluate as ‘true’ … [-Werror=address]`
    (`cc1: all warnings being treated as errors`).

  `kernel/s10plus/build-kernel.sh` now runs the new
  `tools/kernel-relax-werror.sh`, which strips the `-Werror` /
  `-Werror=<diag>` / `-Werror-<diag>` tokens (and whole
  `$(call cc-option,-Werror=...)` expressions) from the scratch tree's **source**
  Makefiles — leaving `-Wno-error…` untouched and avoiding the kbuild-internal
  `scripts/Makefile.*` feature-probe helpers. `DEFAULT_KCFLAGS` also gains
  `-Wno-error=strict-prototypes`, `-Wno-error=date-time` and
  `-Wno-error=designated-init` (each still probed against the selected compiler
  and dropped if unsupported). Idempotent; the tree is a throwaway clone.
- **Pixel 10 Pro XL (`mustang`) kernel build — patch.** The committed
  `kernel/google-pixel-10-pro-xl/patches/0001-nuxel-phone-features.patch`
  declared `@@ -0,0 +1,108 @@` for a hunk that adds only 107 lines
  (`drivers/nuxel/nuxel-core.c`), so `git apply --check` failed
  (`error: corrupt patch`) and `kernel/build-kernel.sh` aborted with
  `error: patch not applied and does not apply` before it ever configured or
  built. The hunk header is corrected to `@@ -0,0 +1,107 @@`; the patch now applies
  cleanly to the `android16-6.12` GKI common tree.
- **Pixel 10 Pro XL (`mustang`) compiler-diagnostics relaxation.**
  `kernel/build-kernel.sh` now neutralises the GKI tree's global
  `CONFIG_WERROR=y` (which lands in `KBUILD_CPPFLAGS` via
  `scripts/Makefile.extrawarn`) with a probe-checked
  `DEFAULT_KCFLAGS="-Wno-error=parentheses -Wno-error"` — KCFLAGS is appended to
  `KBUILD_CFLAGS`, i.e. *after* the `-Werror`, so it wins — fixing e.g.
  `fs/fuse/dev.c:458: … [-Werror=parentheses]`. It also runs
  `tools/kernel-relax-werror.sh` to strip the per-directory `-Werror`
  (`arch/arm64/kernel/vdso32`, aic7xxx, lpfc). The generated asm/uapi headers are
  now produced before `archprepare` (`make asm-generic archprepare`) so the
  host-tool gate builds on a pristine tree.

### Added

- `tools/kernel-relax-werror.sh` — idempotent helper that strips hard-coded
  `-Werror` from a kernel source tree's Makefiles (used by the `mustang` and
  S10+ kernel dispatchers).

### Changed

- **Repository-wide version bump v0.2.1-alpha → v0.2.2-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.2-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`) and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.2-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.2-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.1-alpha] — 2026-10-13

**Theme:** pre-release fix on top of v0.2.0 — make the **S10+ kernel build**
succeed in CI. No other behaviour changes; the readiness picture is unchanged.

### Fixed

- **S10+ kernel build (CI / any non-Samsung host).**
  `kernel/s10plus/build-kernel.sh` never overrode the downstream Samsung tree's
  hardcoded toolchain. The Exynos 9820 `Makefile` line 316 sets

  ```
  CROSS_COMPILE ?= $(srctree)/toolchain/gcc-cfp/gcc-cfp-jopp-only/aarch64-linux-android-4.9/bin/aarch64-linux-android-
  ```

  a tree-internal Android GCC that is **not** shipped with the source. A bare
  `make` therefore failed before compiling anything:

  ```
  make[1]: .../aarch64-linux-android-gcc: No such file or directory
  Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not supported by compiler
  make[1]: *** [Makefile:1267: prepare-compiler-check] Error 1
  ```

  which cascaded into `[nuxel-s10plus-build][error] Kernel image not found:
  .../arch/arm64/boot/Image.gz` and an empty `build/out/s10plus/` (the GitHub
  Actions job logged the kernel step as exit 2 and packaged nothing). The
  wrapper now sets `CROSS_COMPILE` (default `aarch64-linux-gnu-`, matching the
  `gcc-aarch64-linux-gnu` package CI installs) and passes it on **every** `make`
  invocation, so the command-line assignment overrides the tree's `?=` default.
  `--cross <prefix>` is now honoured (previously accepted and silently ignored),
  and `--cross ''`/`CROSS_COMPILE=` yields a native aarch64 host build.
- **S10+ kernel build, second toolchain bug: version-specific `KCFLAGS`.**
  With the toolchain path fixed, the build still died at the same
  `prepare-compiler-check` — but no longer because of a missing compiler.
  `DEFAULT_KCFLAGS` contained `-Wno-error=return-mismatch`, and `-Wno-error=<x>`
  is a **hard error** when the compiler has no `-W<x>` (GCC 13 does not know
  `-Wreturn-mismatch`; it is GCC >= 14). The downstream tree appends `$(KCFLAGS)`
  to `KBUILD_CFLAGS` (`Makefile:963`), so the unknown flag made **every**
  `cc-option` probe fail — producing the misleading
  `Cannot use CONFIG_CC_STACKPROTECTOR_STRONG: -fstack-protector-strong not
  supported by compiler`. The wrapper now probes each relaxation flag against the
  selected compiler (`echo | $(CC) <flag> -c -x c - -o /dev/null`) and keeps only
  the supported ones: GCC 13 drops `-Wno-error=return-mismatch`; GCC 15 keeps it.
  Verified against GCC 13.4 (probe fails before, passes after) and GCC 15.2.

- **S10+ kernel build, third issue: the tree's global `-Werror`.** With the
  probe flag fixed the kernel finally compiled (`CC arch/arm64/...`), then died
  on a real warning promoted to an error:
  `arch/arm64/mm/fault.c: ... error: format '%lx' expects argument of type
  'long unsigned int', but argument 5 has type 'phys_addr_t' ... [-Werror=format=]`.
  The downstream Makefile compiles with a global `-Werror` (`Makefile:428`), so
  any `-Wall` warning is fatal. `DEFAULT_KCFLAGS` now ends with a bare
  `-Wno-error`; because `$(KCFLAGS)` is appended **last** to `KBUILD_CFLAGS`
  (`Makefile:963`), it downgrades the tree's `-Werror` (and its earlier
  `-Werror=<...>` set) back to warnings - while the specific
  `-Wno-error=<diag>` relaxations still cover GCC 14+ default-errors.

### Changed

- **Repository-wide version bump v0.2.0 → v0.2.1-alpha** in: `VERSION`,
  `README.md`, `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with a
  new 0.2.1-alpha release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`), and the OTA builder (`images/build-ota.sh`).
- `README.md` gains a short *What's new in v0.2.1-alpha* section.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.1-alpha`.
- Historical run logs (under `vm/logs/`) and the point-in-time VM recon report
  (`vm/utm-state-report.md`) are left untouched as record.

---

## [v0.2.0] — 2026-10-13

**Theme:** from a single mustang-only scaffold to a **three-target bring-up
repository**, with per-device orchestration, safety gates, consolidated device
docs, and a repository-wide version bump.

> ⛔ **Readiness headline (unchanged in spirit from v0.1.0):** Nuxel is still a
> **design scaffold + code prototype**. It is **not** a flashable phone OS. No
> target has booted Nuxel from a Nuxel-built image, and there is **no verified
> flashable artifact set** for any device.

### Added

- **Multi-device support with explicit selection.** `tools/nuxel-device-select.sh`
  resolves a device key (`--device` > `NUXEL_DEVICE` env > explicit error;
  aliases `s10plus|beyond2lte`, `g7power|ocean`) and every per-device script
  sources it and prints the resolved key before doing any work.
- **Per-device subtrees** for `firmware/`, `kernel/`, `device/`, `boot/`,
  `configs/` and `images/` for all three targets (`google-pixel-10-pro-xl`
  / mustang, `s10plus`, `g7power`).
- **Phase 0 device-inventory templates + build gates:**
  - `docs/g7power-device-inventory.md`
  - `docs/s10plus-device-inventory.md`
  - `docs/pixel10proxl-device-inventory.md`

  Every build/flash/firmware script refuses to run while load addresses or
  firmware filenames are still `PLACEHOLDER`/`UNKNOWN`.
- **G7 Power (Motorola Moto G7 Power, SDM632/msm8953, `ocean`) bring-up:**
  - On-device **stock-evidence** capture bundle —
    `phones/g7power/stock-evidence/` (partitions, props, dmesg, input devices,
    i2c, USB, firmware sysfs, vendor modules, etc.).
  - lk2nd chainloader docs and artifact — `boot/g7power/lk2nd/`.
  - QCDT boot-image packer `tools/build-qcdt-boot.py` (lk2nd-format DT table).
  - Boot-image cmdline patcher `tools/patch-boot-cmdline.py`.
  - Two-phase fastboot flash flow (`boot/g7power/flash.sh`), recovery
    (`boot/g7power/recovery.sh`), boot packer (`boot/g7power/pack-boot-v1.sh`),
    boot config (`boot/g7power/boot-config.txt`).
  - EDL (Qualcomm 9008) unbrick path documented.
  - Bring-up guide: `docs/g7power-bringup.md`; "do it now" checklist:
    `phones/g7power/g7power-go-guide.md`.
- **S10+ (Samsung Galaxy S10+, Exynos 9820, `beyond2lte`) bring-up:**
  - Exynos boot chain docs (S-Boot → U-Boot → Linux), the **no-fastboot**
    reality (TWRP + Download Mode / heimdall), Knox-tripped constraints,
    protected-partition list and anti-cross-flash rules.
  - Flash tooling: `boot/s10plus/flash.sh`, `flash-heimdall.sh`,
    `uboot-chainload.sh`, `pack-boot-v1.sh`, `recovery.sh`,
    `boot/s10plus/boot-config.txt`.
  - Firmware staging: `firmware/s10plus/` (`fetch-vendor-blobs.sh`,
    `gen-manifest.py`, `install-firmware.sh`, `verify-firmware.sh`, vendor
    firmware blob trees).
  - Bring-up guide: `docs/s10plus-bringup.md`; "do it now" checklist:
    `phones/s10plus/s10plus-go-guide.md`.
- **Pixel 10 Pro XL (mustang) prep:** Phase 0 inventory template + gate
  (`docs/pixel10proxl-device-inventory.md`) and reconciliation against the
  multi-device layout.
- **[`CHANGELOG.md`](CHANGELOG.md)** (this file).

### Changed

- **Repository-wide version bump v0.1.0 → v0.2.0** in: `VERSION`, `README.md`,
  `docs/*.md` and `design/*.md` headers, the shell apps
  (`shell/nuxel-shell`, `shell/nuxel-home-native` — meson project version,
  `__init__`, runtime banner, settings About label and AppStream metainfo with
  a new 0.2.0 release entry), the PWA manifest
  (`pwa/nuxel-home/manifest.json` `bridge_version`), the device `APKBUILD`s
  (`pkgver=0.2.0`), the VM tooling (`vm/deploy-vm-manifest.txt`,
  `vm/nuxel-vm-snapshot.sh`, `vm/utm-state-report.md`), and the OTA builder
  (`images/build-ota.sh`).
- **README** rewritten around the multi-device reality: a new
  *What's new in v0.2.0* section, a restructured *Project Structure* table
  (`phones/`, `prompts/`), an updated *Honest Status* table (per-target rows,
  per-area scores), corrected documentation links, and per-device "go-guide"
  links.
- Documentation cross-references updated to the new `phones/` layout.

### Fixed

- **G7 Power touchscreen.** Root-caused the "no touch driver" dead end: the
  controller (ILI2117) is handled by mainline **`ili210x`**
  (`CONFIG_TOUCHSCREEN_ILI210X`, OF match `ilitek,ili2117`); the config had
  requested the **nonexistent** `CONFIG_TOUCHSCREEN_ILI2117`, so no driver was
  ever built. Config fixed and kernel rebuilt
  (`kernel/g7power/defconfig`, `configs/g7power/libinput/`).
- **G7 Power lk2nd black-screen packaging bug.** The payload boot image's DT
  region must be an lk2nd-format QCDT v3 table (12-byte header, 40-byte
  entries) — a raw FDT or a 20-byte Qualcomm header fails validation. Fixed via
  `tools/build-qcdt-boot.py` (DTB bytes unchanged; only packaging corrected).

### Moved / reorganised

- Device **documentation bundles** consolidated under [`phones/`](phones/):
  - `g7power/` → `phones/g7power/`
  - `s10plus/` → `phones/s10plus/`
  - `pixel10proxl/` → `phones/pixel10proxl/`
- Loose planning / analysis prompts consolidated under `prompts/`.
- All in-repo references (docs, scripts, APKBUILDs, config READMEs) updated to
  the new paths.

### Versioning

- Canonical version file: [`VERSION`](VERSION) = `v0.2.0`.
- The historical provenance lines that describe an analysis *of the v0.1.0
  tree* (e.g. "Based on: Deep analysis of Nuxel v0.1.0 repo") are intentionally
  left at v0.1.0; run logs under `vm/logs/` are left untouched as historical
  record.

### Readiness assessment — v0.2.0

| Area | Score | Notes |
|---|---|---|
| Design/docs | 78% | Architecture, security model, PWA spec, three device doc bundles |
| Repo structure | 85% | Clean layout; device doc bundles consolidated under `phones/` |
| PWA apps | 45% | Manifests, SWs, JS exist — need integration testing |
| Native GTK apps | 25–35% | C source exists, not proven buildable on aarch64 |
| D-Bus bridge/portal | 30% | Python parses, dev-grade auth, not integration-tested |
| Sandbox/security | 20% | Configs exist, enforcement not wired end-to-end |
| Build system | 20% | Per-device dispatchers + inventory gates; still unproven on hardware |
| Flashable images | 0% | No verified boot artifact set produced |
| Pixel 10 Pro XL (mustang) | 5% | Public mustang Linux is UART/initramfs-level only |
| Galaxy S10+ (beyond2lte) | 10% | Bring-up: device package, gates, docs — no boot yet |
| Moto G7 Power (ocean) | 15% | Bring-up: touchscreen-driver fix, stock evidence, lk2nd/QCDT tooling |
| UTM VM | 25% | Scripts/docs exist, no VM image artifact produced |

**Overall: ~30–35% MVP scaffold. 0% verified flashable OS. ~40–45% patchable VM demo.**

### Still not done (honest gaps)

- **No target has booted a Nuxel-built image.** 0% verified flashable.
- **Phase 0 inventories are empty templates** — load addresses, firmware
  filenames and checksums remain `PLACEHOLDER`/`UNKNOWN` until filled from the
  physical devices. Every build/flash gate therefore stays closed.
- **Sandbox enforcement is not wired end-to-end** (namespaces + seccomp +
  Landlock + AppArmor + nftables configs exist; enforcement is not proven).
- **Native GTK4 apps are unproven on aarch64.**
- **No VM image artifact** is produced by the bootstrap (scripts/docs only).
- **Modem, camera and sensors are deferred** on both bring-up targets.

### Next (v0.3.0 candidates)

1. Fill the G7 Power and S10+ Phase 0 inventories from the real devices.
2. Produce real kernel + lk2nd + boot/rootfs images and attempt first boot.
3. Build a bootable UTM VM image artifact and run Phosh + bridge/portal.
4. Prove the sandbox enforces (namespaces/seccomp/Landlock/AppArmor/nftables)
   in an integration test.

---

## [v0.1.0] — 2026-05-10

**Baseline release: mustang-only design scaffold + code prototype.**

- Architecture blueprint, security model and PWA runtime specification.
- PWA shells (home, mail, calendar, notes, files, camera) with manifests and
  service workers.
- Python D-Bus services (bridge, portal, notifications) and native GTK4 C app
  source.
- Security configuration files (AppArmor, nftables, hardened_malloc).
- Build / flash / sign / recovery scripts as architectural planning material.
- UTM VM testing scripts for early validation.

Status at v0.1.0: ~25–30% MVP scaffold, **0% verified flashable**, ~35–45%
patchable VM demo. See [`docs/repo-audit.md`](docs/repo-audit.md) for the
measured code footprint and [`docs/milestones.md`](docs/milestones.md) for the
programme view.
