# Nuxel Doom engine comparison

Nuxel ships three deliberately separate Doom paths so usability can be
compared honestly. They share the same read-only WAD catalogue but not the same
input or rendering model.

| | Nuxel Doom | Chocolate Doom | UZDoom |
|---|---|---|---|
| Package | `org.nuxel.Doom` | `org.nuxel.Doom.Chocolate` | `org.nuxel.Doom.UZDoom` |
| Engine | Chocolate Doom 3.0 WASM | Chocolate Doom 3.1.1 native | UZDoom 5.0.3 native |
| Maps | Real WAD maps | Real WAD maps | Real WAD maps |
| Rendering | Software renderer inside WebAssembly, canvas presentation | Native software renderer | Software renderer forced on this image |
| Touch HUD | **Yes** (joystick, aim, fire, use, weapons, run, menu) | No (keyboard/gamepad) | No (keyboard/gamepad) |
| Edge-gesture nav | **Yes** (DOM + native strip) | **Yes** (native 14 px strip) | **Yes** (native 14 px strip) |
| Audio | Web Audio, optional | Native SDL/PipeWire path, experimental | Native, music disabled |
| Save state | Engine config in MEMFS for the session; WAD progress via engine save slots | `~/.config/nuxel/doom-native/saves` | `~/.config/nuxel/doom-native/uzdoom.ini`/saves |
| Best for | Phone play with thumbs | Vanilla-faithful comparison | Modern map/detail comparison |

## Nuxel Doom (WASM)

- Entry: `pwa/nuxel-apps/doom/index.html`
- Engine artifacts: `pwa/nuxel-apps/doom/engine/websockets-doom.{js,wasm}`
- Source pin: `cloudflare/doom-wasm` commit
  `65e0d3ae2ffa604155eebd96ed40da6567bd08f4`
- SHA-256:
  - JS `a2909044a9fbc5529f941c8dbf93cc2931927690e0341c737545cf0b9cff23fb`
  - WASM `6366f83a58fe8596ce742a66dbf86871d315862c89c11e65b54935be03c7e6c4`
- WAD source: `/api/v1/doom/wads` + `/api/v1/doom/wad?id=<sha256>`
- Touch mapping: DOM keyboard events delivered to the engine's SDL2 event
  handlers. No external injector, no privileged device access.
- Start options: `PLAY DOOM` (`-warp 1 1` for Doom 1, `-warp 1` for Doom 2)
  and `TITLE SCREEN` (in-game menu).

## Native Chocolate Doom

- Entry: `/usr/lib/nuxel/nuxel-doom-engine chocolate`
- Package source: Fedora 43 `chocolate-doom 3.1.1`
- Install/remove: NuXtore package `org.nuxel.Doom.Chocolate`
- WAD: first IWAD found in `~/doom`, then `/usr/share/doom`
- Input: keyboard or Bluetooth gamepad; this path deliberately does not draw a
  touch HUD over a native surface.
- Chrome: the triple buttons are hidden; swipe up on the 14 px bottom strip to
  reveal Back/Home/Recents.  Recents can kill the app, Home minimises it.
- Config: `~/.config/nuxel/doom-native/chocolate-doom.cfg`
- Saves: `~/.config/nuxel/doom-native/saves`

## Native UZDoom

- Entry: `/usr/lib/nuxel/nuxel-doom-engine uzdoom`
- Engine: UZDoom 5.0.3 (`7910df7102033fd7754a317f3254f24101135926`),
  GPL-3.0-or-later
- Install/remove: NuXtore package `org.nuxel.Doom.UZDoom` — the package ships
  the native aarch64 `uzdoom` binary plus its three required PK3s and licences
  under `pwa/nuxel-apps/doom-uzdoom/engine/`
- Build: native aarch64 from the pinned UZDoom source with
  `tools/s10plus/a33/doom-engines/build-uzdoom.sh`; no x86 AppImage is used
- Rendering: `+vid_renderer 0` (software) because the S10+ vendor kernel has no
  usable `/dev/dri` node. The app is honest about this and does not claim GPU
  acceleration.
- Music is disabled; the S10+ image has no working OPL/MIDI route.
- Config: `~/.config/nuxel/doom-native/uzdoom.ini`

## Why three apps instead of a hidden engine switch?

A single app with hidden engine switching makes failures look like one broken
feature and makes uninstall rules ambiguous. Separate NuXtore packages give
each engine its own install/remove lifecycle, app id, icon and honest status.
Nuxel Doom remains the default because it is the only path designed for thumbs.
