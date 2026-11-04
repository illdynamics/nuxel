# Doom on Nuxel: touch-first launcher and fullscreen fit

> **v0.7.6-beta:** the primary Doom experience is now the original **Nuxel
> Doom** app (`org.nuxel.Doom`) documented in
> [`games/doom.md`](games/doom.md). This page remains the record of the
> optional Crispy Doom launcher path that the in-app **CLASSIC ENGINE** button
> can start when that Flatpak is installed.

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
