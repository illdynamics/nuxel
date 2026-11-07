# Nuxel Doom engine comparison

Nuxel exposes exactly one user-facing Doom package: **Nuxel Doom** from NuXtore.
It contains a complete Chocolate Doom 3.0 WebAssembly engine, the touch HUD,
WAD catalogue, import flow and legal notices. There is no separate Chocolate
Doom app entry and no separate engine installation step.

The image may additionally contain Fedora's native Chocolate Doom 3.1.1 as an
optional internal comparison runtime. Nuxel Doom opens it directly through the
bridge when it is present; it is not a NuXtore prerequisite, never appears as a
second app/package, and its absence does not affect the bundled WASM engine.
The UZDoom and Crispy Doom comparison paths were removed at the owner's request.

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

## Native Chocolate Doom (optional internal comparison)

- Entry: `/usr/lib/nuxel/nuxel-doom-engine chocolate`
- Package source: Fedora 43 `chocolate-doom 3.1.1`, when the image provides it
- Install/remove: not a NuXtore app; Nuxel Doom calls this target directly
- WAD: first IWAD found in `~/doom`, then `/usr/share/doom`
- Input: keyboard or Bluetooth gamepad; this path deliberately does not draw a
  touch HUD over a native surface.
- Chrome: the triple buttons are hidden; swipe up on the 14 px bottom strip to
  reveal Back/Home/Recents.  Recents can kill the app, Home minimises it.
- Config: `~/.config/nuxel/doom-native/chocolate-doom.cfg`
- Saves: `~/.config/nuxel/doom-native/saves`

## Why one package with an internal optional comparison runtime?

A single app with hidden engine switching makes failures look like one broken
feature. A second user-facing package makes users install the engine twice and
creates two icons for the same game. Nuxel Doom owns the complete bundled engine
and exposes the native runtime only as an optional comparison inside the app.
