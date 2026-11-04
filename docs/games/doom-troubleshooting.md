# Nuxel Doom troubleshooting

## The game is not in Nuxel Home

1. Open **NuXtore → Available** and install `org.nuxel.Doom`.
2. If NuXtore shows **Install** but the launcher does not update, pull Home
   away and back, or reopen Home. Installation registers the app through the
   canonical app registry; it is not a localStorage-only flag.
3. If NuXtore refuses the package, run the offline verifier from a development
   checkout:

```sh
python3 pwa/nuxel-apps/nuxtore/tools/nuxtore-verify.py --require-signature --confirm-unsigned org.example.UnsignedDemo
```

A digest or signature failure is a hard failure and must not be bypassed.

## Remove did nothing

NuxTore Remove calls the Bridge `apps.unregister` verb. The app icon disappears
from Home after the next registry refresh. User settings and progress are
intentionally preserved. If the icon remains, check that the registry refresh
succeeded:

```sh
curl -s http://127.0.0.1:8080/api/v1/apps/registry | python3 -m json.tool | \
  grep -n 'org.nuxel.Doom'
```

No output after Remove is the expected result.

## The system keyboard opens

Nuxel Doom has no `<input>` or `<textarea>` elements. If a keyboard still
appears, it belongs to the previous app or the host's text-input focus:

1. Tap the Doom game area once.
2. Press the revealed **MENU** button.
3. If necessary, return Home and reopen Doom.

The shell calls `dismissKeyboard()` and the host `dismiss-keyboard` action on
start, focus, resume and exit.

## Triple buttons are missing

That is intentional in a foreground PWA. **Swipe up from the bottom edge** of
the screen. The Back/Home/Recents strip appears for a few seconds. On the
lockscreen it stays hidden by design.

If the strip does not appear:

- make sure the swipe starts within roughly 34 px of the bottom edge;
- swipe upward at least 42 px;
- check that the lockscreen is not active;
- on the handset, confirm the native dock is alive with the normal launcher
  diagnostics.

## The top bar is missing

Doom enters real fullscreen mode when gameplay starts. Pull down from the top
edge to reveal the top bar. It hides again automatically.

## Display stayed in landscape

Doom asks the orientation service for landscape only while it is starting and
restores the previous mode when leaving the campaign, exiting, or receiving a
page-hide event. If a crash leaves the session in landscape, use Quick Settings
to select the wanted rotation. Do not issue arbitrary `wlr-randr` commands.

## No sound

Nuxel Doom uses the browser Web Audio path inside the host. Check:

1. the **SOUND** toggle in Doom settings;
2. the system volume;
3. the PipeWire output route in Settings;
4. that the host audio service is running.

The optional Classic Engine button follows the separately documented Crispy
Doom audio path.

## Low frame rate

The renderer is intentionally 320×180. If the panel feels slow:

- close other foreground apps;
- avoid maximum brightness and performance-heavy background work;
- verify the GPU path is healthy with the normal Nuxel performance tools;
- remember that the framebuffer presenter still performs a CPU scanout copy.

Nuxel Doom does not force llvmpipe and does not assume a working DRM/KMS path.

## A touch stays stuck after switching apps

This is a bug. The shell calls `releaseAllInput()` on blur, visibility change,
pause, cancellation and page hide. Capture a diagnostic trace and report the
exact transition (Home, Recents, lock, notification shade, rotation). Do not
work around it with a global input injector.
