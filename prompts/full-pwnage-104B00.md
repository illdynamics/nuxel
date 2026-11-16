# FULL-PWNAGE-104B00 — Applications: Flatpak/GTK startup speed + ZapZap, Signal, Ferdium, Vesktop voice

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104B00.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Every installed app must **start quickly and work**, and the four messenger
clients — **ZapZap, Signal, Ferdium, Vesktop** — must all be able to **record a
voice message using the phone microphone**. Verify each app one by one; no app is
"working" because a desktop file exists.

## 1. Baseline on the live phone

```sh
$SSH $PHONE 'XDG_RUNTIME_DIR=/run/nuxel-wayland flatpak list --app --columns=application,version 2>&1 | head -60'
$SSH $PHONE 'rpm -qa | grep -Ei "zapzap|signal|ferdium|vesktop|discord" '
$SSH $PHONE 'ls /usr/share/applications /var/lib/flatpak/exports/share/applications 2>/dev/null | head -80'
$SSH $PHONE 'XDG_RUNTIME_DIR=/run/nuxel-wayland wpctl status'
```
Note: pipewire/wireplumber run inside `nuxel-audio-session.service` with
`XDG_RUNTIME_DIR=/run/nuxel-wayland`. Mic is source **S10+ microphone (WDMA1)**.

## 2. Known risk areas

- Flatpak `--socket=pulseaudio` / PipeWire relay (`nuxel-flatpak-pulse-relay.py`)
  missing or misconfigured → apps see no input device or silent capture.
- XDG portals (`nuxel/portals.conf`, camera/mic portal) blocking capture.
- WebRTC clients (Signal, Vesktop, ZapZap WebView, Ferdium) need a working
  `pipewire` audio server + a **loopback/echo-cancel-free** default source.
- Slow first launch: cold Flatpak runtime + no page cache + Wayland GPU missing
  (`/dev/dri` absent today — see 104700).

## 3. Work order

1. **Launch matrix** — for each app measure cold-start time and confirm a visible
   window (screenshot via `grim` to `evidence/pwnage-104000/apps/<app>-launch.png`):
   ```sh
   time $SSH $PHONE 'XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 flatpak run <id> &'
   ```
   Target: warm start ≤ 5 s, cold ≤ 15 s on this hardware. Find the real cost
   before optimizing (I/O, font cache, GPU, portal round-trips).
2. **Mic for each messenger**: set default source, record a 5 s voice message in
   the app UI, save the app's own file + a parallel `pw-record` capture, and
   verify both contain audio (non-silent RMS via `sox --i`/`ffmpeg volumedetect`).
   Watch `journalctl` and `pw-top` while recording.
3. **Permissions**: mic portal/permission must be granted through the Nuxel
   permission manager (see 104C00), not by globally weakening sandboxing.
4. Fix startup performance: preload/pre-warm runtimes, fontconfig cache,
   `nuxel-preloading-screen.mp4` gesture while Flatpaks warm, and ensure GPU
   acceleration works (104700) so WebKit/CEF/Electron apps render smoothly.

## 4. Acceptance

| App | Starts | Window | Mic voice msg | Notes |
|---|---|---|---|---|
| ZapZap | | | | |
| Signal | | | | |
| Ferdium | | | | |
| Vesktop | | | | |
| GTK core apps (Files, Settings, Text Editor, Terminal) | | | n/a | |
| Other installed Flatpaks | | | | |

Plus: no app crashes on start, no blank window, audio/video playback works, and all
pass again after the §4 reboot of `full-pwnage-104000.md`.
