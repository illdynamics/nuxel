# Nuxel Doom troubleshooting

## Nuxel Doom is not in Home

1. Open **NuXtore → Available** and install `org.nuxel.Doom`.
2. Pull Home away and back, or reopen Home.
3. Verify the catalogue offline:

```sh
python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py --require-signature --confirm-unsigned org.example.UnsignedDemo
```

A digest or signature failure is a hard failure; do not bypass it.

## “NO WAD FOUND”

The bridge catalogue is empty or unreachable. Check:

```sh
curl -s http://127.0.0.1:8080/api/v1/doom/wads | python3 -m json.tool
```

The catalogue scans only `/home/nuxel/doom`, `~/Downloads`, `~/Documents` and
the system Doom directories. Freedoom is installed by the image. To add a WAD,
copy it into `~/doom` and press **SCAN AGAIN**.

## The game starts but the map is black

- Confirm the selected file is an **IWAD**, not a resource PWAD such as
  `prboom.wad`. A PWAD needs an IWAD base; the app loads the first available
  IWAD automatically.
- Try **PLAY DOOM** rather than the title screen; `-warp` skips the menu.
- Check the browser console for `WAD fetch failed` or an engine abort. A 404
  from `/api/v1/doom/wad?id=...` means the catalogue cache and the file changed
  between scan and launch; press **SCAN AGAIN**.

## The WebAssembly engine fails to initialise

- The app needs `engine/websockets-doom.wasm` (about 2.2 MB). Confirm the file
  exists under `/usr/share/nuxel/pwa/nuxel-apps/doom/engine/`.
- Clear the old service worker cache by reopening the app after an OS update.
- The engine needs WebGL/SwiftShader-backed canvas presentation. If the host's
  WebKit GPU path is broken, Nuxel Doom reports the error instead of showing a
  blank screen.

## The system keyboard opens

Nuxel Doom has no `<input>` or `<textarea>` elements. If a keyboard appears it
belongs to a previous app or the compositor's stale text-input focus. The shell
blurs the active field and calls both the host and compositor dismiss actions
on launch, focus, resume and exit. Tap the game once and press **MENU**; if it
persists, return Home and reopen Doom.

## Triple buttons are missing

That is the global foreground-app contract. **Swipe up from the bottom edge**
within about 34 px of the bottom, moving at least 42 px upward. In a PWA the
DOM dock appears; in a native app `nuxel-navdock` keeps a 14 px gesture strip
mapped and expands to the full dock. Both hide again after a few seconds.
Home and the lockscreen never enter this mode.

## The top bar is missing

It is hidden in every foreground app now. **Pull down from the top edge** to
reveal it. It hides again automatically.

## Display stayed in landscape

A cold boot forces portrait through the lockscreen and restores the mode
selected before boot only after unlock. Doom then requests landscape while
the engine is active and restores the previous mode on pause/exit/page-hide.
If a crash leaves the session rotated, use Quick Settings. Do not issue
arbitrary `wlr-randr` commands.

## No sound

The WebAssembly engine uses Web Audio and starts audio after the first tap.
Check the **SOUND** toggle, system volume and the PipeWire output route. If the
host route is not ready the engine continues silently; the UI does not fake
audio.

## Low frame rate

Nuxel Doom renders at 640×400 inside WebAssembly and presents through the
browser canvas. If it feels slow:

- close other foreground apps;
- lower the display scale in Quick Settings;
- use the native Chocolate Doom comparison engine with a gamepad if the browser
  canvas path is the bottleneck;
- remember the framebuffer presenter still performs a CPU scanout copy.

## A touch stays stuck after switching apps

This is a bug. `releaseAllInput()` runs on blur, visibility change, pause,
cancellation and page hide, and emits key-up for every held key. Capture a
diagnostic trace and report the exact transition. Do not work around it with a
global input injector.

## Native Chocolate Doom / UZDoom does not start

- These are optional comparison engines; Nuxel Doom itself does not need them.
- Native Chocolate Doom must be installed (`chocolate-doom` RPM) and launched
  through `/usr/lib/nuxel/nuxel-doom-engine chocolate`.
- UZDoom is only available if the UZDoom package binary is present. The wrapper
  reports `UZDoom is not installed on this image` instead of pretending it ran.
- The native path uses keyboard/gamepad input; it does not draw the Nuxel touch
  HUD over a native surface.
