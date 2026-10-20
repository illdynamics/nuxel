# NUXEL A45 — keyboard, caret and penguin/Home repair

**Date:** 2026-10-20 21:19 CEST  
**Phone:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 aarch64, kernel `4.14.253`  
**Compositor:** Phoc 0.54.0, headless backend, pixman renderer, `wayland-0`  
**Branch:** `nuxel/a45-keyboard-home`  
**Commit:** `c3699e2`  
**Verdict:** `SOURCE VERIFIED`, `DEPLOYED VERIFIED`, `INSTRUMENTED LIVE BEHAVIOUR VERIFIED`  
**Owner physical confirmation:** `PENDING` — not claimed.

---

## 1. Root causes found

### Penguin/Home did not restore the launcher

`NuxelHome._backgroundForegroundApp()` returned immediately when the foreground app
had no DOM iframe:

```js
if (!app || !frame) return;
```

That is exactly the native Terminal case: it is a separate top-level WebKit/GTK
surface, not an iframe. The penguin tap ran `nuxel.home()`, Home repainted *under*
the Terminal, and the glass did not change. The host's hardware `home` action
worked because C-side `action_perform("home")` also called `term_close_window()`;
the on-screen penguin did not.

A second race allowed an app that was still loading to reactivate itself after
Home was pressed, because the frame `load` handler unconditionally set `ACTIVE`.

### The keyboard was only an in-page fallback

- `stevia` 0.54.0 and `stevia-phosh-osk-provider` 0.54.0 are installed.
- Phoc exports `zwp_text_input_manager_v3`, `zwp_input_method_manager_v2`,
  `zwlr_layer_shell_v1` and `zwp_virtual_keyboard_manager_v1`.
- No OSK provider was running in the Nuxel session. `nuxel-session.sh` starts the
  web server and `nuxel-pwa-host`; it never starts Stevia.
- The old `touch-keyboard.js` only handled `<input>` and `<textarea>`, not
  contenteditable, had no cursor movement, used no explicit focus promotion, and
  injected no caret styling.
- A controlled live experiment started Stevia manually. It works: Stevia binds
  the input-method protocol and appears on a focused WebKit field. However, it is
  a compositor **keyboard-layer** surface and covers the persistent HTML
  Back/Penguin/Recents strip shown by the launcher. It is therefore not enabled
  by default in this revision; that limitation is recorded below rather than
  shipping a keyboard that removes the navigation dock.

---

## 2. Fix

### Home (penguin) path

- `_backgroundForegroundApp()` now closes a native top-level app through
  `_closeAppSurface()` instead of returning early.
- PWA iframes are hidden and moved to `BACKGROUND`, preserving the session for
  Recents.
- An in-flight iframe is marked `__nuxelBackgrounded`; its `load` handler can no
  longer flip it back to `ACTIVE` and paint over Home.
- `home()` hides the in-page keyboard, closes every overlay/drawer, paints
  Desktop 1, and records `home:complete`.
- Navigation records `NAV tap` / `NAV done` with app state and page, so a tap that
  reaches the dock is distinguishable from a tap that never did.

### Touch keyboard and caret path

- Supports `<input>`, `<textarea>` and contenteditable.
- Uses WebKit's editing command (`execCommand('insertText')` / `delete`) where
  possible, with `setRangeText` fallback; caret and selection remain the engine's
  own.
- Adds real caret visibility (`caret-color`) and text selection to editable
  elements in the launcher and same-origin app iframes. No decorative/fake caret
  element exists.
- Adds Backspace, Space, Enter form submission, Shift, symbols and cursor-left /
  cursor-right.
- Keeps focus on the field while keys are tapped (`pointerdown` is prevented on
  the key panel, and the field is re-focused for every edit).
- Hide Keyboard hides the surface without killing any daemon; Back/Home hide it
  as well.
- Exactly one haptic request is made per accepted key press.
- If a native input-method provider reports `native=1` / `provider=stevia` in
  `keyboard-state`, the HTML fallback disables itself to prevent two keyboards.
- Keyboard layer is `z-index: 250`: above app iframes (`60`) and app bars (`61`),
  below the system navigation dock (`260`).

---

## 3. Files changed

| Source | Deployed path |
|---|---|
| `pwa/nuxel-home/js/app.js` | `/usr/share/nuxel/nuxel-home/js/app.js` |
| `pwa/nuxel-home/js/navigation.js` | `/usr/share/nuxel/nuxel-home/js/navigation.js` |
| `pwa/nuxel-home/js/touch-keyboard.js` | `/usr/share/nuxel/nuxel-home/js/touch-keyboard.js` |
| `pwa/nuxel-home/css/style.css` | `/usr/share/nuxel/nuxel-home/css/style.css` |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/nuxel-home/index.html` |
| `tools/s10plus/a45/test-home-keyboard.js` | offline harness only |

`/usr/share/nuxel/pwa/nuxel-home` is a symlink to `../nuxel-home`, so the same
deployed files are the ones served at
`http://127.0.0.1:8000/pwa/nuxel-home/`.

---

## 4. Tests

| Test | Result |
|---|---|
| `node tools/s10plus/a45/test-home-keyboard.js` | **PASS** — 21/21 checks |
| `node --check` on app.js, navigation.js, touch-keyboard.js | **PASS** |
| `git diff --check` | **PASS** |
| `tools/s10plus/a33/tests/launcher-registry-test.js` | 4 known pre-A45 failures (backgrounded surfaces are retained by design; same failures recorded in A44) |

The offline harness covers native-app Home, PWA Home, in-flight backgrounding,
penguin pointer activation without double-fire, text/backspace/space/arrows,
contenteditable commands, Enter submission, native-provider fallback selection,
and absence of a fake caret.

---

## 5. Live deployment evidence

All five files were staged over the USB console, SHA-256 checked on the target,
installed by same-directory rename, read back, and served again over HTTP. The
served bytes equal the repository and installed bytes.

| File | SHA-256 |
|---|---|
| `index.html` | `86ece237b397398edbb68098fe7a459ee31760b86d23966e51fec2c7bb14d5f9` |
| `css/style.css` | `96461c930d88e00d4e261df5a0a5d4ed3ac170071f1bbe921bba3ea32865f3f4` |
| `js/app.js` | `b4fac45ecb3993aba41505e37cc0324d7e00d7e577e6283c2fc25c8c983056c8` |
| `js/navigation.js` | `71929ad36079f9b35b5e2a0083e064802db09d040ef68263621d9421a28de95a` |
| `js/touch-keyboard.js` | `c80e9cc8203263d3415254dbc1dd4ca119f888e58974a215e3f37358d817683c` |

`nuxel-wayland` and `nuxel-wl-fb` remained **active**. The USB live console was
never restarted. `nuxel-wayland` was restarted twice to load the new launcher
document; the console stayed reachable.

### Live log excerpts (`live-evidence.txt`)

```text
NUXEL_INPUT OSK show tag=INPUT id=search-input rows=5
NUXEL_INPUT OSK show tag=INPUT id=note-title rows=5
NUXEL_INPUT OSK hide
NUXEL_INPUT NAV tap action=back state=ACTIVE page=0
NUXEL_INPUT NAV done action=back state=BACKGROUND page=0
NUXEL_INPUT EVT home:complete state=BACKGROUND page=0
NUXEL_INPUT EVT app:lifecycle id=org.nuxel.Calendar state=BACKGROUND
```

The compositor snapshot `keyboard-above-nav.png` (720×1520) shows the keyboard
rows above the unchanged bottom navigation strip. `native-osk-experiment.png`
records the separate controlled Stevia experiment and the reason it is not the
default: the keyboard layer covered the bottom nav strip.

---

## 6. Rollback

Baseline captured before the first A45 replacement:

```sh
sh /var/lib/nuxel/a45/rollback-20261020T191510Z/rollback.sh
```

The script restores the five pre-A45 files and restarts `nuxel-wayland`; it does
not touch the console, kernel, bootloader, partitions, modem or firmware.

---

## 7. Acceptance matrix

| Feature | Source | Live deployment | Physical verification |
|---|---|---|---|
| Penguin/Home returns to launcher (PWA) | PASS | PASS — `home:complete state=BACKGROUND page=0` | **PENDING** |
| Penguin/Home closes native Terminal | PASS (offline) | Ready | **PENDING** |
| Tap field → keyboard opens | PASS | PASS — `OSK show tag=INPUT …` | **PENDING** |
| Real focused caret | PASS (real caret styling/focus) | Loaded | **PENDING** |
| Typing / Backspace / Space / Enter | PASS (offline) | Loaded | **PENDING** |
| Contenteditable fields | PASS (offline) | Loaded | **PENDING** |
| Keyboard above app content | PASS (z 250 > 60) | PASS (compositor snapshot) | **PENDING** |
| Navigation dock remains visible | PASS | PASS (snapshot) | **PENDING** |
| Hide Keyboard | PASS (source + Back path) | PASS — `OSK hide` | **PENDING** |
| Keyboard haptics | PASS | PASS — `HOST_ACTION haptics-tap` | **PENDING** |
| App switching / focus restoration | PASS | PASS — Calendar ACTIVE → BACKGROUND | **PENDING** |
| Native Stevia input-method OSK | PASS (audited experiment) | Verified working, **not default** | **PENDING** |
| Four-app dock covered by apps | unchanged | unchanged | **PENDING** |
| Rotation with OSK | not changed | not tested | **PENDING** |

### Known limitation

The persistent Back/Penguin/Recents dock is a DOM element inside the launcher
WebKit surface. Stevia is a compositor keyboard-layer surface, which by design
paints above every client surface; enabling it covers the dock. Until the dock
is moved to its own layer-shell surface with an exclusive zone, the compositor
OSK cannot coexist with the current nav strip. The in-page keyboard is therefore
the shipped default, and it stays below the nav dock and above all PWA app
iframes.

---

## 8. 90-second owner test

**“Keyboard and Home test ready. Please test now.”**

1. Open Calendar; tap Event title.
2. Confirm a visible blinking caret inside the field.
3. Type `Nuxel keyboard is alive 123`.
4. Backspace and retype.
5. Tap Hide keyboard; confirm it disappears and Calendar stays put.
6. Tap the field again; confirm the keyboard returns.
7. Tap the penguin/Home button; confirm Desktop 1 appears and Calendar is gone.
8. Open Notes, tap a note title, type, then press penguin/Home.
9. Open Browser, tap the address field, type a URL.
10. Confirm the keyboard is above the app and the Back/Penguin/Recents strip is
    visible below it at all times.
11. Confirm one subtle haptic per key.
12. Open File Explorer and rename a file.
13. Press Home from every app; confirm it always returns to the launcher.
14. Confirm the four-app shortcut dock is not painted over a running app.
