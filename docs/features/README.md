# Nuxel feature status

Canonical, human-readable feature list for the current repository state
(`v0.2.1`, 2026-10-30). It describes what the code and the physical Galaxy S10+
actually do, not what is merely planned.

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
| Audio playback | `ALMOST` | ABOX Calliope `MUB0`, both CS35L41 DSP1s running, RDMA1 enabled, gain 12/12, 48 kHz default sink and advancing `hw_ptr`. `pw-play`/boot cue/Test Audio return success. Physical audibility is not yet owner-confirmed. |
| Audio volume | `WORKING` | Hardware keys and UI share the PipeWire default sink; absolute 5 % steps, 25 % safety ceiling, OSD and throttled preview cue. |
| Boot sound | `ALMOST` | One gated POW per boot after UI ownership and route readiness. Same audibility caveat as playback. |
| Microphone capture | `NOT STARTED` | Capture devices enumerate, but no real recording/WAV acceptance has been performed. |
| Wired headset | `NOT STARTED` | Jack detection exists; route and audibility are unverified. |
| USB-C audio | `NOT STARTED` | No DAC/accessory test; USB role conflicts with the console gadget remain. |
| Camera | `BLOCKED` | No usable V4L2 capture node; UI reports the blocker instead of showing fake frames. |
| GNSS | `BLOCKED` | BCM4773 SPI rail responds, but the Broadcom BBD/LHD userspace is absent. Network/IP location is labelled separately. |
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
| Native GTK4 apps | `PARTIAL` | Dialer/Messages/Contacts/Settings sources exist; hardware-dependent flows are limited by modem and audio confirmation. |
| Notes | `WORKING` | File-backed notes, title/body editing and store persistence; used as the audio-confirmation surface. |
| Mail/Calendar/Files | `WORKING` | File-backed persistence, folder/attachment handling, file explorer with CRUD/copy/move/ZIP/upload. |
| Media/Gallery/Recorder | `PARTIAL` | Media playback and Gallery work; Recorder writes a real WAV; microphone/speaker acceptance is open. |
| Browser | `WORKING` | Real HTTPS browser with system chrome/navigation; fullscreen/native-layer edge cases remain owner checks. |
| Camera app | `BLOCKED` | Honest hardware status; capture backend deferred. |
| Maps/Location UI | `PARTIAL` | Real provider state and privacy policy; satellite fix blocked, network location depends on GeoClue. |
| Weather/Clock/Calculator | `WORKING` | Functional PWAs with offline states. |
| SnekByte | `WORKING` | Bundled offline game with touch controls and system navigation. |
| Settings | `WORKING` | Display/safe zones, status bar, Wi-Fi, Bluetooth, audio, location, input, buttons, theme/haptics, power, developer and About. |
| Nuxtore | `PARTIAL` | Honest store/empty state and local verification; install backend is incomplete. |
| Flatpak app model | `PARTIAL` | Manifests and sandbox configuration exist; no built runtime or end-to-end sandbox acceptance. |
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
- `CHANGELOG.md` / `docs/releases/v0.2.1.md` — what changed in this release.
- `docs/s10plus-live-fixes-20261028.md` — Bluetooth and RDMA1 first hardware proof.
- `docs/beta-finalization/live/PWNAGE-40000-REPORT.md` — audio persistence and readiness evidence.
- `docs/beta-finalization/live/PWNAGE-39000-TODO.md` — Wi-Fi, Bluetooth and overlay state.
- `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.md` — evidence-gated subsystem verdicts.
