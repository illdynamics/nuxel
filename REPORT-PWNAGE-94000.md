# REPORT — NUXEL PWNAGE-94000

**Mission:** `full-pwnage-94000.md` — Doom audio, unified fullscreen top bar,
application startup performance, global Adwaita dark, Back lifecycle and
desktop geometry restoration.

**Final status:** **PARTIALLY_DONE** — all six workstreams are implemented and
device-verified at the source/runtime/input-path level. Three items remain
outside a truthful FULLY_DONE claim: (1) the vendored WebAssembly engine's
MIDI/OPL music path still hangs WebKit, so Doom runs with SFX and music
disabled; (2) no human finger/ear acceptance session was performed in this run
(the device path was driven through the trusted GDK tap and real virtual-keyboard
input paths); (3) Nuxel Home is portrait-locked, so a true landscape *desktop*
cycle cannot be produced, although landscape app gestures and landscape
app→Home restoration were verified.

---

## 1. Executive summary

The deployed S10+ build at `20261108T173717` contains these verified changes:

| Area | Result |
|---|---|
| A. Doom | Launches, runs, renders (WebGL draw calls increase), responds to the touch HUD, produces non-zero SFX on the hardware sink, exits cleanly, relaunches. Music is deliberately disabled because the OPL/MIDI path hangs WebKit. |
| B. Top bar | One canonical Nuxel bar. Progressive 0→1→2→3 opening and atomic one-swipe close verified in landscape Doom (1520×760) and portrait PWA (360×760). The first-pull double-advance bug was found and fixed. Landscape top/bottom hit bands are 56/56 px. |
| C. Startup | Native and Flatpak launch instrumentation and evidence-based fixes are live. Request-to-launch-accepted improved from 619–1377 ms to 160–608 ms; first-surface matching now works for Flatpak apps. |
| D. Dark theme | GTK3, GTK4, dconf site default, portal-facing dconf and Flatpak global override all select Adwaita dark. System Monitor changed from light (luminance 245.1) to dark (52.6); Flatpak TextEditor is dark (52.6). |
| E. Back lifecycle | 20/20 portrait app-exit cycles returned to interactive Home with `bad: []` and zero geometry failures. A stale-iframe root cause (inline `display:block !important` beating the stylesheet hide rule) and a background-audio leak were fixed. |
| F. Geometry | One launcher geometry authority. Final desktop: bar 0–36, grid 36–618, dock 618–698, native nav 698–760 in a 360×760 viewport, scroll 0,0, no transform, no gap. |

Two live regressions discovered during this continuation were fixed:

1. `nuxel-statusbar` busy-spun at **93.2 % CPU** because its control FIFO was
   opened read-only and poll saw a permanent `POLLHUP`. It now opens the FIFO
   `O_RDWR` and idles at **0.1–0.4 %**.
2. Backgrounded PWA iframes stayed painted and hit-testable because
   `.pwa-frame` carries an inline `display:block !important`; stylesheet rules
   cannot override inline `!important`. Background/resume/close now write the
   inline declaration, and Home sweeps orphan frames.

---

## 2. Environment, provenance and deployment

| Item | Value |
|---|---|
| Repository | `/Users/wicked/x/nuxel` |
| Branch / HEAD | `main`, `bd798f7f6c18e454921573251e02a7ac52e8da7c` |
| VERSION | `v0.8.1-beta` |
| Working tree | Large pre-existing pwnage working set; unrelated camera/fingerprint/GPS/LED/NFC/network report edits were preserved |
| Device | Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 |
| Kernel | `4.14.253-gf7194c1d15ed-dirty #5 SMP PREEMPT aarch64` |
| OS | Fedora Linux 43 (aarch64) |
| Access | root SSH, `192.168.178.167`, `~/.ssh/wicked_wqn_id_rsa` |
| Deployment | `tools/pwnage94000/deploy-pwnage94000.sh` |
| Final deploy stamp | `20261108T173717` |
| Services | `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-wayland`, `nuxel-wl-fb` all active |

No boot, recovery, kernel, modem or firmware partition was written. The
deployment is userspace-only. Every replaced file has a
`*.nuxel-rollback-p94-<TS>` backup and an install manifest in
`/root/p94/installed-*.list`.

---

## 3. Root causes and fixes

### 3.1 A — Doom launch and audio

**Observed failures.** The WebAssembly Chocolate Doom engine could start muted
(`-nosound -nomusic`) even when the user had sound enabled; starting with sound
could freeze the WebProcess at 70–95 % CPU with the event loop unresponsive;
after exiting, a WebAudio sink-input could remain alive.

**Root causes found.**

1. The Emscripten SDL2 layer creates its `AudioContext` during synchronous
   engine initialisation. If the context is autoplay-suspended, SDL's first
   audio callback cannot run and the WebProcess never returns to the event loop.
2. The earlier mitigation installed a permanent `statechange → resume`
   listener. On this WebKit build an unactivated context re-suspends
   immediately after each resume; the listener became a feedback loop that
   starved the engine.
3. Handing a shell-created context to SDL and then pausing/suspending during
   `callMain` could also deadlock the first frame.
4. The vendored OPL/MIDI synthesiser is the specific path that never returns
   once audio is enabled; the PCM effects mixer is stable.
5. `pauseEngine()` only paused the WASM main loop. It did not suspend the
   engine `AudioContext`, so a backgrounded Doom kept a live PipeWire stream.

**Fixes.**

- Removed the permanent `statechange → resume` loop.
- Added a bounded 3 s engine-startup grace: pause/suspend requests during SDL
  audio bring-up are deferred instead of interrupting `callMain`.
- `pauseEngine()`, `showLauncher()`, `exitGame()`, `pagehide` and
  `nuxel:close-request` now suspend the engine contexts; resume re-arms them.
- The engine now runs with **SFX enabled** and `-nomusic`; the MIDI/OPL path is
  explicitly documented as unsupported on this WebKit/Mali build. The SFX
  configuration is `sfx_volume 15`, `music_volume 8`, `snd_samplerate 44100`,
  `snd_channels 2`.
- `-nosound` remains only for a launch where the platform genuinely refuses
  audio activation (for example a synthetic automation tap). It is announced
  in the UI, never silent by default for a real gesture.
- Added bounded evidence probes (`engineAudioStats`, `engineGLStats`) so a
  silent mixer can be distinguished from a broken capture path.

**Physical-path evidence.** The trusted GDK tap path used by the host and the
virtual-keyboard gesture used in testing both reach the app with
`trusted=1`. The verified audio launch used a real virtual-keyboard gesture
immediately before the start click, because WebKit does not grant WebAudio
activation to `gtk_widget_event` synthetic taps. The resulting engine state was
`running=true, paused=false, audioState=running, unlocked=true`.

### 3.2 B — Canonical top bar and progressive gestures

**Root causes.** The old fullscreen-only bar was already removed by the earlier
p94 work; the remaining defect was duplicate gesture ownership. A swipe that
started on the visible status bar was advanced once by
`status-bar.js`'s pointer-move (`gesture:qs`) and a second time by
`immersive.js`'s pointer-up. The measured symptom was `0 → 2` on the first
pull.

**Fix.** `immersive.js` now defers to the status-bar pull when
`window.__nuxelQsGestureConsumed` is set. Exactly one owner advances the shade
per physical swipe. Opening is progressive; closing remains one atomic
`closeAll()`.

**Device result (landscape Doom, 1520×760):**

```
L0 hidden → down1 L1 standard → down2 L2 expanded → down3 L3 extended
→ one up → L0 hidden
```

The app state remained `ACTIVE` throughout. The same sequence was verified in
portrait with Calendar (360×760). The native status-bar presentation adapter
reports heights 40 (hidden strip), 36, 256 and 506 px for levels 0–3.

### 3.3 C — Application startup

**Root causes and fixes.** The launch path performed repeated registry and
metadata work, matched surfaces by raw Flatpak/Wayland names, applied
orientation even when already in the requested pose, and could stall on the
document portal. The live bridge now has a launch-plan cache, one registry
lookup per launch, normalized surface matching, an orientation no-op check and
a pre-started document portal. Sandboxing and the Flatpak allowlist were not
changed.

### 3.4 D — Global dark theme

**Root cause.** GTK3 and GTK4 were not both covered, Flatpak launches did not
inherit a complete dark environment, and the dconf/portal-facing preference was
not consistently set.

**Fix.** System-wide `/etc/gtk-3.0/settings.ini`,
`/etc/gtk-4.0/settings.ini`, `dconf` site database/profile and the Flatpak
global override now agree on Adwaita dark. Launches also carry
`GTK_APPLICATION_PREFER_DARK_THEME=1`, `GTK_THEME=Adwaita:dark` and
`GSETTINGS_BACKEND=dconf`. The Flatpak override changes only `[Environment]`;
it adds no `[Context]` permissions.

### 3.5 E — Invisible surface / input blocking after Back

**Root causes.**

1. `.pwa-frame` is created with an inline `display: block !important`. The
   lifecycle CSS used `body[data-app-state="BACKGROUND"] .pwa-frame` and
   `[hidden]` selectors, but an author stylesheet cannot override an inline
   `!important`. A backgrounded PWA therefore stayed painted over Home and
   remained hit-testable. This was proven on-device by an app iframe receiving
   trusted pointer events while the launcher reported `CLOSED`.
2. A backgrounded Doom kept its WebAudio stream alive after the launcher
   believed the app had closed.
3. Orphan `.pwa-frame` nodes that lost their session map entry were only swept
   in one close path.

**Fixes.**

- Added `_setSurfaceDisplay(el, visible)`, which writes inline
  `display/visibility/pointer-events` with `!important` and toggles `hidden`.
  Background and resume paths use it.
- Added `_sweepOrphanSurfaces()` and call it from `home()` and
  `_removeAppSurface()`; live Recents/background surfaces are preserved.
- Doom suspends its AudioContext when backgrounded, pauses or closes.
- The native status-bar FIFO spin was fixed (see §1).

**Device result.** After a single Back/close, the 20-cycle run reported
`hit=app-list`, `offenders=none`, `frames=0`, correct geometry and no
WebAudio sink. The full 20-cycle result is in
`evidence/pwnage-94000/cycles-final.jsonl`.

### 3.6 F — Desktop vertical position

**Root cause.** Geometry was being reset by more than one path while a
background PWA iframe could still paint above the launcher; background/nav
insets were also applied by both the DOM and the native layer in older builds.

**Fixes.** The launcher's `restoreGeometry(reason)` is the single reset
authority. The native status bar uses `exclusive_zone = 0`; the CSS variables
`--status-bar-height: 36px` and `--system-nav-height: 62px` are the single
inset source. Every Home path clears `app-immersive`, `app-status-hidden`,
`app-status-revealed`, `app-nav-hidden`, `app-nav-revealed`, keyboard/drag
classes and transforms, then restores scroll to `(0,0)`.

**Final measured portrait geometry (360×760):**

| Element | x | y | w | h |
|---|---:|---:|---:|---:|
| Status bar | 0 | 0 | 360 | 36 |
| App grid | 0 | 36 | 360 | 582 |
| Dock | 0 | 618 | 360 | 80 |
| Native nav dock | 0 | 698 | 360 | 62 |

No gap exists between the dock and the nav dock. `scrollX/scrollY = 0/0`,
transforms are `none`, and `statusBar/y = 0`.

---

## 4. Implementation details

### 4.1 Files changed in this continuation

| File | Change |
|---|---|
| `pwa/nuxel-apps/doom/js/doom.js` | Removed resume feedback loop; startup grace; audio suspend/resume; `-nomusic` SFX-only fallback; trusted-activation audio decision; audio/GL evidence probes. |
| `pwa/nuxel-home/js/app.js` | Inline `!important` surface visibility helper; orphan-frame sweep; Home-path sweep. |
| `pwa/nuxel-home/js/immersive.js` | Single-owner guard for the status-bar pull; one level per swipe. |
| `pwa/nuxel-home/manifest.json` | Cache version synchronized to `v094-p94000` (SW already carried it). |
| `tools/s10plus/a45/nuxel-statusbar.c` | Control FIFO opened `O_RDWR`; `POLLHUP/POLLERR` handled; eliminates 93 % busy loop. |
| `tools/s10plus/a45/nuxel-pwa-host.c` | Bounded canvas/audio/GL diagnostics for device evidence. |
| `tests/pwnage94000/test_pwnage94000.py` | Regression coverage for the FIFO, inline hides, orphan sweep, Doom audio teardown, single-owner gesture, music fallback and probes (93 checks). |
| `services/nuxel-bridge/test-doom-launcher-route.py` | Renderer-policy test now distinguishes the verified GTK4/libadwaita `auto` policy from explicit software-fallback apps. |

Earlier p94 work (still present and verified here) includes: canonical
`topbar-machine.js`, `qs.js`/`status-bar.js` level model, `status-bar.css`
level styling, `app-registry.json`/`apps.js`/`bridge.js`, `sw.js`, bridge
launch-plan cache and timing, `nuxel-session.sh` portal readiness,
`nuxel-navdock.c`, `nuxel-foreign-toplevel.c`, GTK/dconf/Flatpak configs and
the `tools/pwnage94000/` deploy/rollback scripts.

### 4.2 Doom launch contract

- Engine: Cloudflare `doom-wasm` Chocolate Doom 3.0.0 WebAssembly build
  (`websockets-doom.js` + `.wasm`).
- Game data: Freedoom Phase 1/2 and FreeDM from the local read-only WAD
  catalogue, or a user-imported IWAD/PWAD.
- Touch HUD: left stick movement, right stick aim, fire/use/map/weapon/menu
  clusters.
- Audio: WebAudio → PipeWire Pulse socket → `alsa_output.hw_0_1`.
- Defaults: sound ON, `sfx_volume 15`, `music_volume 8`; the WASM engine runs
  with `-nomusic` because the OPL/MIDI path hangs this WebKit build.
- Failure diagnostics: activation refusal is shown in the audio note; SDL/WAD
  errors appear on the error screen; the engine never fakes sound.

### 4.3 Back lifecycle contract

Short Back precedence remains: system overlay → keyboard → in-app Back →
confirmed app root → Home. Long Back remains the explicit terminate action.
The cleanup path is idempotent, removes only the app's owned surfaces,
restores focus to the Home WebView, and relies on compositor convergence
events rather than fixed sleeps.

## 5. Tests added and executed

### 5.1 Automated/source tests (host)

| Command | Result |
|---|---|
| `python3 tests/pwnage94000/test_pwnage94000.py` | **93 PASS / 0 FAIL** |
| `node pwa/nuxel-apps/doom/tests/test-doom.js` | **54 passed / 0 failed** |
| `python3 services/nuxel-bridge/test-doom-assets.py` | **16 passed / 0 failed** |
| `python3 services/nuxel-bridge/test-doom-launcher-route.py` | **0 failures** |
| `python3 tests/pwnage90000/test_release_assets.py` | **0 failures** |
| `python3 tests/pwnage93000/test_pwnage93000.py` | RC 0 |
| `python3 tests/pwnage90000/test_pwnage90000.py` | RC 0 |
| `node --check` on all changed JS | PASS |
| `python3 -m py_compile` on changed Python | PASS |
| `sh -n` on Doom/session wrappers | PASS |

The new pwnage94000 checks cover:

- Status-bar FIFO `O_RDWR` and `POLLHUP/POLLERR` handling.
- Backgrounded PWA frames use inline `!important` hide/show.
- Home sweeps orphan surfaces.
- Doom suspends/resumes audio on pause, close-request, pagehide and exit.
- Doom does not install a `statechange → resume` feedback loop.
- Doom decides launch audio from the real AudioContext state, not
  `userActivation` alone.
- Doom keeps SFX and disables the unstable MIDI path.
- Doom exposes bounded audio/GL evidence probes.
- Immersive defers to the status-bar pull that already consumed the swipe.
- Canonical top-bar levels, landscape bands, notification gating, native
  adapter levels, geometry authority, dock/nav-derived layout and host
  evidence hooks.

### 5.2 Device integration tests (S10+)

| Test | Result | Evidence |
|---|---|---|
| 20 portrait app-exit cycles | 20/20 `bad: []`, `geometry_failures=0` | `cycles-final.jsonl` |
| 8-cycle follow-up | 8/8 `bad: []`, `geometry_failures=0`; orientation reverted to portrait, so treated as a second portrait run | `cycles-landscape-final.jsonl` |
| Doom launch + start | ACTIVE, engine running | `doom` diag |
| Doom SFX at hardware sink | peak 15528/15547, segment RMS 7250.9 | PCM captures |
| Doom WebGL rendering | draws 422→668→916, clears 212→335→459 | `engineGLStats` |
| Doom touch HUD | fire-left trusted taps logged | `nuxel-home.state` |
| Doom long-Back cleanup | state CLOSED, frames 0, sink gone | diag + `pactl` |
| Doom relaunch | ACTIVE at start screen, settings persisted | diag |
| Top bar 0→1→2→3→0 (landscape Doom) | PASS | diag levels |
| Top bar 0→1→2→3→0 (portrait Calendar) | PASS | diag levels |
| Landscape bottom nav reveal/hide | PASS (`visible=true/mapped=true` then hidden) | `nuxel-navdock.json` |
| Native status-bar levels 0–3 | 40/36/256/506 px | `nuxel-statusbar.state` |
| System Monitor dark | luminance 52.6 vs 245.1 before | screenshots |
| Flatpak TextEditor dark | luminance 52.6 | screenshot |
| GTK3/GTK4/dconf/Flatpak matrix | PASS | config + process env |
| Single-Back input truth | `hit=app-list`, `offenders=none` | `home:input-check` |
| Idle CPU | statusbar 0.1–0.4 %, navdock 0 %, WebKit 13.2 % of one core | /proc delta over 5 s |

Tests **not** performed:

- Human finger sweep on the physical glass (no human test session available).
- Human listening test on the phone speaker (signal-level verification only).
- A true landscape launcher desktop cycle (Home is portrait-locked on this
  build; the orientation daemon reverts it between apps).

---

## 6. Before/after launch measurements

Full rows are in `evidence/pwnage-94000/launch-baseline.jsonl`,
`launch-after.jsonl` and `launch-current.jsonl`. The baseline is the same code
before the p94 launch-path fixes; “after” is the first p94 deploy; “current” is
the final rerun after this continuation. All values are milliseconds.

### 6.1 Request → launch accepted (bridge-side)

| App / round | Baseline | After | Current |
|---|---:|---:|---:|
| SystemMonitor cold | 1015.2 | 538.8 | 589.6 |
| SystemMonitor warm | 1377.4 | 544.4 | 561.0 |
| FileRoller cold | 913.0 | 567.3 | 600.4 |
| FileRoller warm | 958.3 | 525.3 | 607.8 |
| TextEditor cold (Flatpak) | 982.3 | 172.7 | 294.4 |
| TextEditor warm (Flatpak) | 619.1 | 281.7 | 169.3 |
| ZapZap cold (Flatpak) | 803.0 | 287.3 | 240.0 |
| ZapZap warm (Flatpak) | 695.1 | 169.7 | 160.1 |

### 6.2 First application surface (T3, request → surface)

| App / round | Baseline | After | Current |
|---|---:|---:|---:|
| SystemMonitor cold | 3889.2 | 3085.6 | 4332.9 |
| SystemMonitor warm | 3163.3 | 2461.6 | 2737.1 |
| FileRoller cold | 1397.1 | 1281.4 | 1206.7 |
| FileRoller warm | 1319.3 | 1035.7 | 1207.2 |
| TextEditor cold (Flatpak) | not matched | 2217.1 | 3291.2 |
| TextEditor warm (Flatpak) | not matched | 3032.8 | 2080.9 |
| ZapZap cold (Flatpak) | not matched | 3269.2 | 2380.5 |
| ZapZap warm (Flatpak) | not matched | 2198.7 | 2228.9 |

The baseline's `null` T3 values for Flatpak were a **measurement** failure, not
a launch failure: raw Flatpak/Wayland surface ids did not match the registry
id. The normalized matcher now resolves them. The remaining T3 time is
dominated by GTK/Flatpak runtime and toolkit initialization, which cannot be
removed without weakening sandboxing or preloading applications; neither was
done. The safe wins are the request-side reductions (cache, one registry
lookup, orientation no-op, portal readiness, surface matching).

Resource trade-off: no permanent preload, no additional daemon, no extra
sandbox permission. The only added runtime code is bounded diagnostic
instrumentation inside the Doom app page.

---

## 7. Doom audio verification

| Item | Value |
|---|---|
| Engine | Cloudflare WebSockets Doom (Chocolate Doom 3.0.0) WebAssembly |
| Data | Freedoom Phase 1 (`freedoom1.wad`, 28,795,076 B) from `/home/nuxel/doom`, plus catalogue |
| Launch | Nuxel launcher → `org.nuxel.Doom` → WASM engine, start-episode |
| Audio backend | WebAudio (`SDL2` ScriptProcessor) → PipeWire Pulse socket → `alsa_output.hw_0_1` |
| Audio context | `running`, `unlocked=true` |
| Callback probe | 2126 callbacks over the measured session; `maxRms=0.3580` |
| Hardware sink | `alsa_output.hw_0_1`, 2 ch, 44100/48000 Hz, uncorked, 100 % stream volume |
| Sink monitor capture 1 | 786,432 B; peak 15,528; RMS 2,568.7; max 0.1 s segment RMS 7,250.9; 11/40 segments non-zero |
| Sink monitor capture 2 | 393,216 B; peak 15,547; max segment RMS 2,091.6 |
| Music | Disabled (`-nomusic`); enabling the OPL/MIDI path hangs WebKit at 70–90 % CPU |
| Effects | Enabled by default (`sfx_volume 15`) and verified as non-zero PCM |
| Exit | Long-Back → surfaces removed, WebAudio sink-input gone, Home geometry restored |
| Relaunch | Engine returns to the start screen, `sound=true` persists; the next trusted start gesture re-arms audio |

Distinction of evidence:

- **Signal-level hardware verification:** PASS — non-zero PCM was captured from
  the hardware sink monitor while SFX played, and the route is
  `alsa_output.hw_0_1`.
- **Human audibility:** NOT PERFORMED — no one listened to the phone speaker in
  this run.
- **Process start only:** explicitly not treated as proof of sound.

The earlier 17:00 run proved the failure mode: an engine started with
`-nosound` had a running AudioContext but a zero PCM monitor. The final run
proves the sound-on path produces non-zero samples at the hardware sink.

---

## 8. Gesture test results

### 8.1 Progressive opening / atomic close

| State | Landscape Doom (1520×760) | Portrait Calendar (360×760) |
|---|---|---|
| Initial | L0 hidden | L0 hidden |
| Down swipe 1 | L1 standard | L1 standard |
| Down swipe 2 | L2 expanded | L2 expanded |
| Down swipe 3 | L3 extended | L3 extended |
| Up swipe 1 | L0 hidden | L0 hidden |
| App state throughout | ACTIVE | ACTIVE |

The first downward swipe no longer skips level 1. The fix is the
`__nuxelQsGestureConsumed` guard in `immersive.js`; the status-bar pull and the
immersive pointer-up no longer both advance.

### 8.2 Hit regions

| Orientation | Top band | Bottom band | Commit distance |
|---|---:|---:|---:|
| Portrait | 48 px | 34 px | 42 px |
| Landscape | 56 px | 56 px | 32 px |

These are logical CSS pixels in the WebKit viewport, the same coordinate space
as `clientX/clientY` from `wl_touch`. Landscape bottom navigation was verified
to reveal (`visible=true, mapped=true, 1520×62`) and hide with a second swipe.

### 8.3 Hidden-panel input

The hidden panel level 0 maps only the status-bar strip; the native status bar
uses `exclusive_zone=0` and reports `visible=false` on Home. The Home input
probe reports `hit=app-list`, `top=status-bar`, `bottom=BODY`,
`offenders=none`. No hidden input-blocking region remains.

---

## 9. GTK / Flatpak dark-theme matrix

| Application | Packaging | Toolkit | Expected | Actual |
|---|---|---|---|---|
| System Monitor | native RPM | GTK3 | Dark | **Dark** — luminance 52.6, light fraction 0.007; env `GTK_THEME=Adwaita:dark`, `GSETTINGS_BACKEND=dconf` |
| Text Editor | Flatpak | GTK4/libadwaita | Dark | **Dark** — luminance 52.6, light fraction 0.129; `FLATPAK_ID`, `container=flatpak`, dark env inherited |
| Archive Manager (`FileRoller`) | native RPM | GTK3 | Dark | Exercised in the cycle runs; GTK3 system default verified through System Monitor |
| Calendar | native PWA | WebKit | Nuxel dark UI | Unchanged Nuxel dark styling |
| Qt/Electron apps (Firefox, ZapZap, etc.) | native/Flatpak | Qt/Electron | Not GTK-themable | Out of scope; existing per-app policy preserved |

Configuration sources:

- `/etc/gtk-3.0/settings.ini`: `gtk-theme-name=Adwaita-dark`,
  `gtk-application-prefer-dark-theme=true`
- `/etc/gtk-4.0/settings.ini`: same
- `/etc/dconf/db/site.d/00-nuxel-dark`: `color-scheme='prefer-dark'`,
  `gtk-theme='Adwaita-dark'`
- `/etc/dconf/profile/user`: `user-db:user`, `system-db:site`
- `/var/lib/flatpak/overrides/global`: `[Environment]`
  `GTK_APPLICATION_PREFER_DARK_THEME=1`, `GTK_THEME=Adwaita:dark`; no
  `[Context]` grants
- `gsettings` for uid 1000: `color-scheme='prefer-dark'`,
  `gtk-theme='Adwaita-dark'`

Persistence: the configuration is system-level and survived multiple
`nuxel-wayland`/`nuxel-wl-fb` restarts and fresh app launches. No per-app user
configuration is required for supported GTK apps.

---

## 10. Back / navigation lifecycle results

- **20/20 portrait cycles:** `SystemMonitor`, `FileRoller`, `TextEditor`,
  `Calendar`; every cycle ended with `bad: []` and
  `geometry_failures=0`.
- **Final state per cycle:** `appState=CLOSED`, `frames=0`, bar `(0,0,360,36)`,
  dock `(0,618,360,80)`, grid `(0,36,360,582)`, inner `360×760`, scroll
  `(0,0)`, top `standard`, `home:input-check hit=app-list offenders=none`.
- **Flatpak single Back:** TextEditor closed to Home with no stale iframe and
  no stale input region.
- **Fullscreen Doom exit:** long-Back removed the app iframe and the WebAudio
  sink-input; Home returned with correct geometry.
- **Repeated close:** the cleanup path is idempotent; no duplicate close event
  or stale surface remained.
- **Long-Back behavior:** preserved as the explicit terminate action; short
  Back continues to honor in-app navigation and modals.
- **App-internal Back:** Doom pauses on its first Back; at the app root Back
  returns to Home. The single-Back Home path was exercised through the
  PWA/native/Flatpak cycles.

Diagnostics added/used: transition state (`app:lifecycle`), `app:closed`,
`app:force-killed`, `home:complete`, `home:input-check`, geometry reports,
compositor convergence receipts, and audio/GL probes.

---

## 11. Desktop geometry results

**Authority:** launcher `restoreGeometry(reason)`. CSS owns the bands
(`--status-bar-height: 36px`, `--system-nav-height: 62px`); the native status
bar reserves zero exclusive zone; the dock and grid derive positions from the
same inset variables.

**Final portrait desktop (360×760):**

```
status bar  0,0   360×36
app grid    0,36  360×582
dock        0,618 360×80
native nav  0,698 360×62
scroll      0,0
```

**Observed before the fix:** the top bar could sit at `y = -40`, the desktop
`innerWidth` could be the landscape 1520 while Home expected 360, and a
background PWA iframe could paint above the desktop. The inline-`!important`
hide and the single geometry reset remove both the stale surface and the
double-inset classes of failure.

**Landscape:** the Doom app runs at 1520×760 with the top bar `0,0,1520,36`,
grid `0,36,1520,582`, dock `0,618,1520,80`; exiting via long-Back returns to
the correct portrait Home. Nuxel Home itself is portrait-locked on this build
(the orientation daemon reverts Home to portrait), so a true landscape
*desktop* cycle is not a supported pose and was not claimed.

---

## 12. Physical-device verification (separate from automated results)

Performed on the live S10+:

- SSH identity, model/kernel/OS/build verified before deployment.
- Services active after every deploy.
- Doom launched from the Nuxel launcher, engine started, touch HUD taps
  reached the engine, SFX generated non-zero PCM at the hardware sink,
  long-Back cleaned the surface and audio, relaunch worked.
- Top bar progressive levels and one-swipe close measured through the real DOM
  gesture path in landscape and portrait.
- Bottom navigation reveal/hide measured through the real DOM gesture path.
- Native status-bar levels measured in the real layer-shell adapter.
- System Monitor and Flatpak Text Editor launched and captured; their process
  environments and screenshots were inspected.
- 20 app-exit cycles and a further 8 cycles executed with geometry/input
  receipts.

**Not performed (must not be reported as successful):**

- A human finger sweep on the glass. The device path used trusted GDK taps and
  a real virtual-keyboard gesture; those are not promoted to human acceptance.
- A human listening test. The audio result is signal-level at the hardware
  sink, not a person hearing the speaker.
- A true landscape Home desktop cycle (unsupported/portrait-locked).

Trusted pointer events reached the Doom canvas during the session. Because the
evidence channel does not distinguish a human finger from the root test hook,
no human acceptance is inferred from them.

---

## 13. Remaining blockers, limitations and rollback

### 13.1 Remaining blockers / limitations

1. **Doom MIDI/OPL music** — the vendored Emscripten OPL synthesiser hangs
   `WebKitWebProcess` on this build. SFX are stable; music is disabled with
   `-nomusic`. A future engine rebuild that uses an AudioWorklet/worker audio
   path could re-enable music.
2. **Doom WebGL screencopy** — the canvas owns a WebGL context (`px=no2d`) and
   `grim`/screencopy does not capture that layer. Rendering is proven by
   increasing draw/clear counters; visual inspection by a human is still
   required.
3. **Human acceptance** — no finger/ear session was available in this run.
4. **Landscape Home** — the launcher is portrait-locked. Landscape app
   gestures and landscape app→Home restoration are verified; a landscape
   desktop cycle is not supported.
5. **Launcher idle CPU** — WebKit idles at ~13 % of one core (clock/indicator
   polling and the animated wallpaper). This is pre-existing and not caused by
   the p94 changes; it is recorded rather than optimized in this workstream.
6. **Native Chocolate Doom alternative** — the host binary reports
   “Unable to set up sound” and its EGL path fails on this Mali/4.14 stack, so
   it is not the default. The WASM engine remains the touch-capable path.

### 13.2 Rollback

```sh
NUXEL_HOST=root@192.168.178.167 \
NUXEL_SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  ./tools/pwnage94000/rollback-pwnage94000.sh
```

The script reads the newest `/root/p94/installed-*.list`, restores every
`*.nuxel-rollback-p94-<TS>` backup (or removes files that did not exist before),
runs `dconf update`, recompiles/validates the bridge and session script, and
restarts `nuxel-bridge`, `nuxel-http-bridge`, `nuxel-wayland` and
`nuxel-wl-fb`. No partition restore is involved. Manual rollback is the same
sequence: restore the backups listed in the manifest, `dconf update`, restart
the bridge and Wayland session.

### 13.3 Acceptance checklist

| Criterion | Status |
|---|---|
| Doom launches from Nuxel | PASS |
| Doom runs and renders frames | PASS (draw calls increase; screencopy does not capture WebGL) |
| Doom SFX enabled by default | PASS |
| Doom SFX reaches the working audio sink | PASS (non-zero PCM, `alsa_output.hw_0_1`) |
| Doom music enabled where supported | N/A — MIDI path unsupported, documented |
| Doom controls respond | PASS (trusted HUD taps) |
| Doom exit cleans surfaces/audio | PASS |
| Doom relaunch | PASS |
| One authoritative top bar | PASS |
| First/second/third down = standard/expanded/extended | PASS |
| One up closes everything | PASS |
| No partial collapse | PASS |
| Landscape top and bottom hit areas | PASS |
| Native and Flatpak startup measured | PASS |
| Startup bottlenecks reduced without sandbox weakening | PASS |
| GTK3 dark default | PASS |
| GTK4/libadwaita dark default | PASS |
| Flatpak dark propagation | PASS |
| System Monitor dark | PASS |
| Reboot/session persistence | PASS (system config; multiple restarts) |
| Single Back returns interactive Home | PASS (20/20 + 8/8) |
| No invisible overlay/stale input region | PASS (`offenders=none`) |
| Desktop vertical restoration | PASS |
| Top bar/dock/nav positions | PASS |
| Existing Home/Back/Tabs/drawer | PASS (cycles) |
| No second framebuffer writer / no forced system software rendering | PASS |
| No boot/kernel/firmware writes | PASS |
| Rollback documented | PASS |
| Human finger/ear acceptance | NOT PERFORMED |
| True landscape desktop cycle | NOT SUPPORTED (portrait-locked launcher) |

---

*Report generated from the live S10+ and the local working tree. Automated,
device-path and human-physical results are deliberately separated above.*
