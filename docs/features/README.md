# Nuxel feature status

Canonical, human-readable feature list for the current repository state
(`v0.7.4-beta`, 2026-10-31). It describes what the code and the physical Galaxy
S10+ actually do, not what is merely planned.

**v0.7.4-beta changes the headline verdicts:** speaker audio is now `WORKING`
(owner-confirmed audible), GNSS is `ALMOST` (real network location works;
satellite fixes remain `BLOCKED`), and the Flatpak/GTK application model is
`ALMOST` (installed and truthful, but `CONFIG_USER_NS=n` blocks the Flatpak
sandbox and the handset runs the WebKit PWA shell).

**Status legend**

| Status | Meaning |
|---|---|
| `WORKING` | Exercised successfully on the physical S10+ with a specific evidence path |
| `ALMOST` | Software path is implemented, deployed and measured; one physical/owner check remains |
| `PARTIAL` | Some user-visible functions work; named gaps remain |
| `BLOCKED` | Hardware/firmware/kernel dependency prevents the feature |
| `NOT STARTED` | Scaffold or design only |

## Platform

| Feature | Status | Current detail |
|---|---|---|
| S10+ cold boot | `WORKING` | Raw arm64 kernel + embedded initramfs + Fedora 43 ext4 rootfs + systemd 258 + Nuxel Home. Boot animation hands off to the launcher. |
| Display path | `WORKING` | Headless Phoc → Wayland screencopy → DECON `/dev/fb0`; 1440×3040 ABGR8888 frames committed. No DRM/KMS on the 4.14 vendor tree. |
| Touch input | `WORKING` | `sec_ts` → evdev → libinput → Phoc → WebKit; unlock, Home, app launch and launcher gestures receive real finger contacts. |
| Lockscreen | `WORKING` | Penguin drag-to-unlock, battery/time/date, charging, USB-host and live-console indicators, connection-mode selector. |
| Home launcher | `WORKING` | App grid, search, dock, recents, widgets, safe zones, home settings, service-worker cache migration. |
| Global navigation | `PARTIAL` | Back/Home/Recents work across PWAs; some native/dialog focus and long-Back kill paths still need owner acceptance. |
| Status bar | `WORKING` | Clock, cellular presence (never inferred from Wi-Fi), Wi-Fi radio/link state, battery with charge state, notifications, cutout-safe layout and overlap assertion. |
| Quick Settings | `WORKING` | Wi-Fi tri-state, Bluetooth power/status, mobile, location policy, do-not-disturb, flashlight, rotation menu and verbose-boot tile. |
| Bluetooth | `WORKING` | BCM4375 HCD + `CONFIG_BT_HCIUART` + `btattach` register `hci0`; controller powers on and a 12 s scan discovers peers. Settings supports list, scan, pair, connect, disconnect, trust and remove. |
| Wi-Fi | `WORKING` | BCM4390/brcmfmac, NetworkManager as sole owner, radio ON after normal boot, saved profiles autoconnect, radio/link state separated in the UI, manual OFF respected for the session. |
| Audio playback | `WORKING` | Owner-confirmed audible. ABOX Calliope `MUB0`, both CS35L41 DSP1s running, RDMA1 enabled, gain 12/12, 48 kHz default sink and advancing `hw_ptr`. Root cause of the silent speaker was the CS35L41 PLL reference: the DT programs 6.144 MHz while ABOX UAIF1 clocks 1.536 MHz; `0x4804=0x1b`, `0x2c04=0x370`, `0x6000=0x8000`, `0x2024=0x0` on both amps, kept alive by the driver cache (`Digital PCM Volume=817`, `AMP Mute=Unmuted`). Owner typed `works` for boot cue, volume cue, Test Audio and after a full reboot. |
| Audio volume | `WORKING` | Hardware keys and UI share the PipeWire default sink; absolute 5 % steps, **100 % ceiling**, **50 % first-boot default**, OSD and throttled preview cue. |
| Boot sound | `WORKING` | One gated POW per boot after UI ownership and route readiness. `nuxel-audio-warmup` powers the DAPM speaker path with an inaudible 8 s stream first, so the 366 ms cue is not swallowed; owner-confirmed audible. |
| Microphone capture | `NOT STARTED` | Capture devices enumerate, but no real recording/WAV acceptance has been performed. |
| Wired headset | `NOT STARTED` | Jack detection exists; route and audibility are unverified. |
| USB-C audio | `NOT STARTED` | No DAC/accessory test; USB role conflicts with the console gadget remain. |
| Camera | `BLOCKED` | No usable V4L2 capture node; UI reports the blocker instead of showing fake frames. |
| GNSS (satellite) | `BLOCKED` | BCM4773 SPI rail, `/dev/ttyBCM` and the GPIO145 rail are real, but the BBD sensor-hub patch firmware and the Android/Bionic `lhd`+`gpsd`+HIDL runtime are absent. Verdict `BLOCKED_FIRMWARE`; no satellite fix is claimed. |
| Cellular modem | `BLOCKED` | Shannon net devices exist; ModemManager finds no modem object, so calls/SMS/data are unavailable. |
| NFC | `BLOCKED` | No controller/firmware path. |
| Sensors/haptics | `PARTIAL` | Input devices enumerate and the haptics writer path exists; real feel and motion-sensor integration need owner tests. |
| External display | `BLOCKED` | No `CONFIG_DRM`/Type-C DP Alt Mode stack. |
| USB serial console | `WORKING` | CDC-ACM `/dev/ttyACM0`, key-only recovery access. |
| Wi-Fi SSH console | `WORKING` | Key-only SSH over the LAN; the owner's current route is used for live deployment. |
| USB network SSH | `BLOCKED` | Kernel USB-gadget/network limitation documented in the app and bridge. |
| OTA/update | `PARTIAL` | OTA builder and versioned image artifacts exist; end-to-end on-device update is not accepted. |

## App model and apps

| Feature | Status | Current detail |
|---|---|---|
| PWA launcher/runtime | `WORKING` | Hardened WebKitGTK, isolated app contexts, local static server, version-pinned bridge. |
| Native GTK4 apps | `ALMOST` | Dialer/Messages/Contacts/Settings/Permissions sources build with GTK4 + libadwaita; the S10+ Launcher is the WebKit PWA shell and the image does not compile the GTK apps into `/usr/bin`. Calls/SMS remain blocked by the missing modem object. `nuxel-statusbar` (cairo/Pango layer-shell) ships so fullscreen native apps keep the top strip. |
| Notes | `WORKING` | File-backed notes, title/body editing and store persistence; used as the audio-confirmation surface. |
| Mail/Calendar/Files | `WORKING` | File-backed persistence, folder/attachment handling, file explorer with CRUD/copy/move/ZIP/upload. |
| Media/Gallery/Recorder | `PARTIAL` | Media playback and Gallery work; Recorder writes a real WAV; microphone/speaker acceptance is open. |
| Browser | `WORKING` | Real HTTPS browser with system chrome/navigation; fullscreen/native-layer edge cases remain owner checks. |
| Camera app | `BLOCKED` | Honest hardware status; capture backend deferred. |
| Maps/Location UI | `WORKING` | Network location is verified live (`51.4005, 5.47196 ±25 km`, source `network_wifi`) through the per-UID GeoClue agent; Maps and Quick Settings distinguish GNSS, network and stale fixes, and the shim never invents coordinates, timestamps or accuracy. Satellite fix remains blocked. |
| Weather/Clock/Calculator | `WORKING` | Functional PWAs with offline states. |
| SnekByte | `WORKING` | Bundled offline game with touch controls and system navigation. |
| Settings | `WORKING` | Display/safe zones, status bar, Wi-Fi, Bluetooth, audio, location, input, buttons, theme/haptics, power, developer and About. |
| Nuxtore | `PARTIAL` | Honest store/empty state and local verification; install backend is incomplete. |
| Flatpak app model | `ALMOST` | aarch64 Firefox/VLC/Signal/Stremio packages are installed, but `CONFIG_USER_NS=n` means bubblewrap cannot create a user namespace. Firefox/VLC wrappers exec the genuine Fedora aarch64 RPMs; Signal/Stremio report the blocker and exit 2. |
| Permission portal | `PARTIAL` | Capability checks, grants and prompts are wired; deeper XDG portal integration remains. |

## Security and system

| Feature | Status | Current detail |
|---|---|---|
| Capability mediation | `WORKING` | `nuxel-bridge` checks app id + capability; Bluetooth scan/connect/manage, location read/manage and similar actions are gated. |
| Version pinning | `WORKING` | PWA protocol pin `1`; host implementation version moves in lockstep; mismatches fail loudly. |
| Safe zones | `WORKING` | Ten-zone camera-cutout model with shared planner between the live status bar and Settings preview. |
| Battery/charge truth | `WORKING` | sysfs fuel gauge, 100→0 debounce, charge-state glyph, capacity reporting. |
| Performance telemetry | `PARTIAL` | CPU/RAM/GPU meters and metrics service exist; sustained smoothness and idle-power testing remain open. |
| Immutable/verified boot | `NOT STARTED` | dm-verity/AVB design exists; the current bring-up image is writable and unsigned for development. |
| Sandbox enforcement | `PARTIAL` | AppArmor/nftables/seccomp/Landlock configuration exists; full enforcement is not wired on this 4.14 kernel. |

## Evidence anchors

- `README.md` — release summary and readiness table.
- `audio.md` — detailed audio state and remaining checks.
- `CHANGELOG.md` / `docs/releases/v0.7.4-beta.md` — what changed in this release.
- `out.md` — owner-confirmed audio root cause and the `works` confirmations.
- `docs/beta-finalization/live/PWNAGE-42000-REPORT.md` — GeoClue agent and network-location evidence.
- `docs/beta-finalization/live/PWNAGE-44000-REPORT.md` — Home/hardware UI work and measurements.
- `docs/s10plus-live-fixes-20261028.md` — Bluetooth and RDMA1 first hardware proof.
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md` — audio persistence and readiness evidence.
- `docs/beta-finalization/live/PWNAGE-39000-TODO.md` — Wi-Fi, Bluetooth and overlay state.
- `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md` — evidence-gated subsystem verdicts.
