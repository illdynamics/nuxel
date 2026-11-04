# Doom on Nuxel: touch-first launcher and fullscreen fit

> **v0.7.7-beta:** the primary Doom experience is **Nuxel Doom**
> (`org.nuxel.Doom`), a real Chocolate Doom WebAssembly WAD engine documented
> in [`games/doom.md`](games/doom.md). This page remains the record of the
> older GTK/Crispy launcher path. The in-app engine comparison now exposes
> native **Chocolate Doom** and **UZDoom** packages; see
> [`games/doom-engines.md`](games/doom-engines.md).

The installed Flathub **Crispy Doom** (`io.github.fabiangreffrath.Doom`) is still
the game source.  The Nuxel launcher is the "Linux Doom Launcher" option: a
small Python + GTK4 frontend that lists WADs as large touch targets and starts
Crispy Doom fullscreen on the current Phoc output.

## What is installed on the handset

| Path | Purpose |
|---|---|
| `/usr/lib/nuxel/nuxel-doom-launcher` | GTK4 touch WAD picker |
| `/usr/lib/nuxel/nuxel-crispy-doom` | Crispy Doom with Nuxel's host SDL2/PipeWire environment |
| `/usr/lib/nuxel/nuxel-flatpak-doom` | Entry point: no arguments -> launcher; game switches -> Crispy Doom |
| `/usr/share/applications/org.nuxel.DoomLauncher.desktop` | Desktop entry for the same launcher |

`nuxel-bridge`'s Flatpak provider already points
`io.github.fabiangreffrath.Doom` at `/usr/lib/nuxel/nuxel-flatpak-doom`, so the
existing Crispy Doom icon in Nuxel Home now opens the touch launcher instead of
dropping straight into a 360x225 window.

## Use

1. Tap **Crispy Doom** in Nuxel Home.
2. Tap a WAD tile (currently `~/doom/freedoom1.wad`).
3. Crispy Doom starts fullscreen; the launcher hides and returns when the game
   exits.

The launcher searches `~/doom`, `~/Downloads`, `~/Documents`, the Crispy Doom
data directory, and the common system Doom directories.  **Add WAD** remembers
extra files.  A PWAD is loaded with `-file` on top of the first available IWAD.

## Screen controls

- **Fullscreen** — default on; uses the current logical output (720x1520 or
  1520x720 on this handset).
- **Keep 4:3** — off by default so the game uses the whole phone screen; turn it
  on for the classic aspect ratio.
- **Sound (experimental)** — off by default.  The old host sdl2-compat audio
  path invalidated the SDL renderer; leave it off unless testing.
- **Setup** — opens `crispy-doom-setup` with the same environment.

WAD selection is touch-first.  In-game movement/fire still uses Crispy Doom's
normal keyboard or gamepad input; the launcher does not pretend a touch surface
is a gamepad.

## Reinstall

```sh
sudo tools/s10plus/a33/nuxel-doom-launcher-install.sh
```

## Home route and persistence

The Flatpak id stays `io.github.fabiangreffrath.Doom`, but the bridge's
`FlatpakProvider.launch_argv()` resolves that one id to
`/usr/lib/nuxel/nuxel-flatpak-doom`.  Home therefore opens the touch launcher
from the normal **Crispy Doom** tile; no separate special-case entry is needed.

The launcher, the two wrappers and the provider change are deployed by
`tools/beta/live/nuxel-doom-launcher-manifest.json` (userspace only, SHA-256
verified, `.nuxel-rollback` kept).  They survive reboot.

## Verified on the handset (2026-11-04)

- Home's `POST /api/v1/apps/exec` for `io.github.fabiangreffrath.Doom`
  returned `argv: ["/usr/lib/nuxel/nuxel-flatpak-doom"]` and started the
  launcher.
- The launcher rendered fullscreen at the current logical 1520×720 landscape
  output and listed `Freedoom: Phase 1` as a large `▶ PLAY` tile.
- Tapping the tile path starts the Flathub `crispy-doom` binary through the
  host SDL2 stack with `-iwad /home/nuxel/doom/freedoom1.wad -fullscreen`; the
  engine reached `P_SetupLevel: E1M6` and presented a fullscreen frame.
- Sound remains off by default: the host `sdl2-compat`/ALSA path reports
  `installation of hardware parameter failed` and does not currently produce
  audio.  The **Sound (experimental)** switch is the opt-in test path.
- In-game touch movement/fire is **not** part of this launcher.  Crispy Doom
  still needs a Bluetooth gamepad or keyboard for gameplay; this page covers
  the touch-first WAD selection and fullscreen presentation only.

## After the reboot (2026-11-04)

The reboot verifier's automatic framebuffer and :8000 checks fired before the
session settled and reported false negatives.  A manual recheck after boot
found: `systemctl is-system-running = running`, 0 failed units; the seven
session units active; exactly one `/dev/fb0` owner (`nuxel-wl-fb`); Home HTTP
200; bridge ping 200; and all four launcher hashes unchanged.  The Crispy Doom
Flatpak and `~/doom/freedoom1.wad` were still present.  The handset was left at
the lock screen, so the launch endpoint correctly returned HTTP 423
`session_locked` until the owner unlocks and taps **Crispy Doom**.
