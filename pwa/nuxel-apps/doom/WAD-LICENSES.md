# Nuxel Doom WAD licensing and import policy

Nuxel Doom bundles **no commercial DOOM IWAD or commercial sprite/audio asset**.
The engine is Chocolate Doom 3.0 compiled to WebAssembly (GPL-2.0-or-later), and
Nuxel supplies only the launcher, touch HUD and WAD catalogue. This document is
shipped inside the Nuxel Doom NuXtore package so the policy travels with the
app.

## Default free content

The base Fedora/Nuxel image installs the `freedoom`, `freedoom2` and
`freedoom-freedm` packages. Their WADs live under `/usr/share/doom/`:

- `freedoom1.wad` — Freedoom: Phase 1
- `freedoom2.wad` — Freedoom: Phase 2
- `freedm.wad` — FreeDM

Freedoom is a free, freely redistributable project (BSD-style licence; see
`/usr/share/licenses/freedoom*` on the device). It is the default content
because it is legal to redistribute and does not require the owner's commercial
DOOM IWAD. NuXtore's Nuxel Doom package declares the Freedoom OS package and the
read-only WAD roots as requirements; it does not claim to bundle a commercial
IWAD.

## User-imported WADs

The owner may import a WAD they legally obtained (for example an original
`DOOM.WAD`/`DOOM2.WAD` they purchased). The import flow:

1. Requires an explicit "I own the rights to this WAD" acknowledgement.
2. Accepts only a plain `.wad` filename and validates the IWAD/PWAD directory.
3. Stores the file privately under `/home/nuxel/doom/imported/`, addressed by
   SHA-256, with no upload path.
4. Never bundles, mirrors or redistributes the imported file in the Nuxel image
   or NuXtore catalog.

Freedoom and user-imported WADs are shown in the in-app catalogue with their
IWAD/PWAD tags. Nuxel Doom does not substitute simplified pixel-art graphics for
the engine's real WAD rendering.
