# Chocolate Doom WebAssembly engine provenance

Nuxel Doom runs a real Chocolate Doom engine inside the app, not a lookalike
raycaster. The engine is the **Cloudflare WebSockets Doom** build of Chocolate
Doom, compiled to WebAssembly.

| Field | Value |
|---|---|
| Upstream source | <https://github.com/cloudflare/doom-wasm> |
| Pinned source commit | `65e0d3ae2ffa604155eebd96ed40da6567bd08f4` |
| Upstream base | Chocolate Doom 3.0.0 (GPL-2.0-or-later) |
| Artifact origin | Official Cloudflare demo, <https://silentspacemarine.com/> |
| Local files | `websockets-doom.js`, `websockets-doom.wasm` |
| SHA-256 (JS) | `a2909044a9fbc5529f941c8dbf93cc2931927690e0341c737545cf0b9cff23fb` |
| SHA-256 (WASM) | `6366f83a58fe8596ce742a66dbf86871d315862c89c11e65b54935be03c7e6c4` |
| Licence | GNU GPL v2 or later; see `COPYING.md` |

The WebAssembly binary is unmodified. Nuxel supplies its own HTML shell, WAD
catalogue, launcher, touch HUD and persistence. No WAD or commercial game asset
is bundled in this repository; Freedoom or a user-imported WAD is loaded at
runtime from the read-only bridge endpoint.
