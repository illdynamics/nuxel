# PWNAGE-84000 — Operation Daily Penguin

**Kickstarter / execution prompt**  
**Full specification:** `full-pwnage-84000.md`  
**Target:** Nuxel on Samsung Galaxy S10+ (`SM-G975F`, `beyond2lte`, Exynos 9820)  
**Primary transport:** Wi-Fi SSH, authenticated with the existing key `~wicked/.ssh/wicked_wqn_id_rsa`  
**Execution posture:** inspect first, implement end-to-end, verify on the physical phone, preserve working systems.

---

## Mission

Read `full-pwnage-84000.md` completely and execute it as the authoritative implementation specification. This is not a request for another plan, a mock-up, or a list of suggestions. Work in the current Nuxel repository, connect to the running phone over Wi-Fi SSH as **root** using the supplied private-key path, diagnose the live state, implement the fixes, deploy them safely, and prove each result on the actual S10+.

The full prompt covers:

1. Replace Doom's current one-stick-plus-look-surface arrangement with two matched, circular, analog-style virtual joysticks: left for movement and right for aiming/turning. Preserve correct engine input, multitouch, fire controls and the working Doom audio.
2. Move alarm and timer execution out of the Clock web page into a durable system service. Add proper Stop controls, configurable snooze (default 9 minutes, with snooze-disable support), separate alarm/timer sounds, lockscreen penguin indicators, alarm swipe-right-to-dismiss / swipe-left-to-snooze, and timer-penguin tap-to-stop.
3. Remove the visible horizontal scrollbar from Settings while keeping Settings tabs horizontally touch-scrollable.
4. Diagnose and materially reduce native GTK and Flatpak cold/warm launch latency, using measurements rather than disabling security or hiding startup delays.
5. Make Downloader a real `yt-dlp` front end with MP3/MP4 presets, selectable Chrome/Firefox/Nuxel cookie sources, real progress and completion, and secure handling of browser cookies.
6. Make Notes reliably save real files under `~/Notes`, show a gallery-style preview, and integrate note-to-event / note-to-alarm workflows with Calendar and Clock.
7. Rebuild desktop layout around one collision-aware grid so widgets and app icons can coexist, be moved, resized, removed and transferred between desktops by edge-dragging. Ensure per-widget desktop ownership is real.
8. Add a Calendar widget and event-to-alarm / notification shortcuts.
9. Diagnose the S10+ capture route and make microphone recordings contain intelligible voice; expose actual microphone gain and optional noise suppression in Sound Settings.
10. Make the Adwaita dark preference apply consistently to native GTK 3, GTK 4/libadwaita and Flatpak apps, including Software and Archive.
11. Fix Software app keyboard lifecycle: no surprise keyboard on launch, swipe-up reveals Back/Home/Tabs, swipe-down dismisses the keyboard.
12. Package and integrate **ARM64-native** Legcord and Vesktop, ensure both launch correctly in the real Nuxel session, and leave authentication ready for the owner to complete manually.

## Mandatory live-device connection

Work from the checked-out Nuxel repository. Use its existing Tri-Link SSH helper and strict host-key handling; do not invent an IP or weaken SSH security.

```bash
cd ~/x/nuxel
KEY=~wicked/.ssh/wicked_wqn_id_rsa
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --status --user root --key "$KEY"
```

Use the helper's discovered/configured Wi-Fi host. If the phone host is not configured, resolve it through the repository's documented Nuxel WLAN discovery and ask no one to repeat already-known information. Do not silently fall back to USB or serial. Once the host is known, open the root console through the same helper:

```bash
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host "$PHONE_WLAN_HOST" \
  --user root --key "$KEY" --shell
```

Confirm `id -u` is `0`, record `uname -a`, `/etc/os-release`, active display/session processes, service status, package versions and current deployment IDs before changing anything. Keep the helper's pinned `known_hosts` behavior. If the key or host-key verification fails, diagnose it; never use `StrictHostKeyChecking=no`, never delete a pinned key to make a connection pass, and never expose private-key contents.

If the helper is unable to connect, report the exact failure and continue with repository-side work and tests that do not require the phone. Do not pretend that live deployment or physical verification happened.

## Non-negotiable execution rules

- Read the entire full prompt before editing. Inspect the live phone and source tree before deciding implementation details.
- Do not stop after diagnosis. Implement the working path, tests, deployment and physical verification.
- Preserve the current working Nuxel boot, Phoc/Wayland/framebuffer path, Mali acceleration, audio playback, touch routing, networking, Flatpak sandboxing and app lifecycle.
- No kernel/bootloader/partition flashing for these userspace issues. Change kernel configuration only if live evidence proves a required kernel interface is missing; then stop before any flash and provide a separate exact, reversible kernel procedure.
- Do not replace real operations with fake progress, static success labels, sample audio, generated “voice” or mock state.
- Never run a GUI app as root. Root owns the system bridge/services; GUI processes and browser-profile access run as the actual Nuxel session user.
- Never place passwords, session tokens, browser-cookie contents, Discord tokens, private keys or MFA codes in source, prompts, command arguments, logs, evidence artifacts or test fixtures. The owner must type credentials into the official client UI.
- Do not bypass DRM, paywalls, login controls, rate limits or access restrictions in Downloader. Preserve its existing rights/consent gate.
- Use current official ARM64 release artifacts for Legcord/Vesktop, verify checksums/signatures where published, and never install x86_64 binaries on this ARM64 phone.
- Every persistent change needs a backup/rollback path and a recorded before/after state. Prefer atomic file replacement and narrow systemd drop-ins over broad rewrites.
- When hardware does not expose a control or capability, report the exact probe and provide a truthful unavailable state. Do not display a fake slider or claim noise cancellation / suspend wake / microphone gain is active without evidence.

## Required finish line

The task is complete only when the full prompt's acceptance checklist passes on the physical phone: Doom has two true thumb joysticks and sound still works; alarm/timer are independent persistent system events with the requested lockscreen controls and sound behavior; widgets and icons share a collision-free draggable/resizable desktop grid; Notes are actually on disk in `~/Notes`; Calendar reminders schedule and fire; mic captures intelligible voice; the selected dark mode reaches Software and Archive; app launches are measurably improved; Downloader performs real yt-dlp jobs; Software keyboard gestures work; and both ARM64 chat clients launch and reach their login UI. If manual authentication is needed, stop at the login screen and let the owner sign in—do not use or store a supplied password.

Read and follow `full-pwnage-84000.md` now. Do the work in this session, test every change, collect evidence, and finish with a concise engineering report: root causes, files changed, packages installed, live commands run, test results, performance before/after, known limitations and rollback instructions.
