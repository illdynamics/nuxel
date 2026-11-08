# PWNAGE-90000 — Final Engineering Report

**Status: PARTIAL.** All thirteen P90 workstreams have source, integration and
host-test changes; P90-02 (preload motion) and P90-12 (systemd evidence) are
hardware-verified on the connected S10+. The remaining hardware checks need
physical touch/unlock/launch input from the operator and are marked **NOT RUN**
rather than assumed.

- **Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`, Exynos 9820,
  Fedora Linux 43, kernel `4.14.253-gf7194c1d15ed-dirty`, systemd 258.
- **Device Nuxel build:** `v0.7.9-beta` installed; repository `VERSION` is
  `v0.8.0-beta`. No version bump or release/push was performed.
- **Final clean boot:** `5ab43e24-41c6-45c9-9f92-50d10ca58a8b`
  (`systemd-analyze time`: 3.430 s kernel + 12.713 s userspace = **16.143 s**).
- **Deployment:** rebuilt natively on the phone (aarch64), staged with
  `.nuxel-rollback-p90-20261108T095310` backups.

---

## 1. Root causes

### P90-01 — “Restart accepted” on the next boot
**Confirmed source issue:** the outgoing power surface wrote an acceptance
verdict (`e.label + ' accepted'`, then `accepted by systemd`) into `#menu-result`
and kept the full-screen `.nuxel-reboot-overlay` alive. The bounded framebuffer
hold (`nuxel-wl-fb` ExecStop) can legitimately preserve the last outgoing frame,
so any text/overlay still painted at shutdown can appear at the start of the
next boot.

**Fix:** reboot is now rendered only as a request (“requested; waiting for the
backend verdict”), never as completion. The overlay is neutral black, and
`pagehide` / `beforeunload` / `visibilitychange:hidden` destroy both the overlay
and the result line. No notification or storage entry is created.

### P90-02 — preload MP4 froze after ~1 s
**Confirmed root cause (hardware):** the mpv clock ran to EOF (6.3 s), but the
compositor presented exactly one frame. `zwlr_foreign_toplevel` lock enforcement
(`watch-lock`) re-ran every second and re-maximized/activated the fullscreen Home
lockscreen, which made phoc treat the preload surface as not visible and stop
sending it frame callbacks. This is the “moves briefly, then freezes” symptom.

**Evidence:** with the old watcher, 30 composited screencopy samples produced
**1 distinct frame / 0 changes**. With the watcher edge-triggered and the
preload surface exempted, the same clip produced **15 consecutive distinct
frames** on the live session and again on a cold boot. `wl-fb` blits rose from
39 to 122; the controller recorded `clock_advances=48/50`,
`stall_count=0`, `eof_at_s=6.324–6.396`, `first_frame_s=0.042–0.167`.

### P90-03 — first-unlock icon paint
**Confirmed source issues:** visible desktop/dock images used
`loading="lazy"`, `fetchpriority="low"`; the grid was rebuilt via `innerHTML`
on every render; the service worker forced `cache:'no-store'` for built-in
versioned icons; the fallback glyph was hidden until an error.

**Fix:** immutable/versioned icons are cache-first and precached
(`v080-p90000`), visible desktop/dock icons are eager/high-priority, a correct
fallback glyph paints immediately, and the grid/dock reconcile keyed nodes so
decoded `<img>` nodes survive re-renders. Drawer icons stay lazy.

### P90-04 — Flatpak redraw/reinit on lock/unlock
**Confirmed source issue:** `enforce_locked()` issued
`unset_fullscreen`/`unset_maximize`/`set_minimized` to every non-Home toplevel
on every 1 s policy tick, even while already locked. That is a repeated
visibility/configure churn source for GTK/Electron/Flatpak apps.

**Fix:** enforcement is edge-triggered (lock transition, late non-Home
activation, or a meaningful state change). Requests are only sent when the
window state actually calls for them, and the trusted preload overlay is
exempt. Hardware check: `/run/nuxel/lock-enforcement.state` mtime stayed
unchanged across 5 s while locked (no repeated enforcement).

### P90-05 — Flatpak time-to-first-frame
The bridge already returns a launch job promptly and runs a bounded background
verifier. This pass adds explicit stage timing (`request_to_provider_lookup`,
`provider_lookup_to_exec`, `systemd_run_accept`,
`request_to_launch_accepted`) and preserves the existing installed-app and
metadata caches. **No security policy was weakened.** Real tap→first-frame
measurement was not possible because the device remained locked and native
launches are correctly refused while locked. No percentage is claimed.

### P90-06 — dark-blue rectangle after Reload launcher
**Confirmed source issues:** reload had no lifecycle marker, so the new
document could re-enter boot-splash/preload-cover paths; transient power/toast
layers were not synchronously retired; pointer/gesture state from the old
document could survive.

**Fix:** `reloadLauncher()` sets a one-shot sessionStorage marker, closes
overlays/QS/recents/drawer, removes reboot/toast/splash nodes, hides the preload
cover, resets immersive chrome and pointer lock, then reloads. The new document
consumes the marker and starts clean without replaying boot chrome.

### P90-07 — invisible input interceptor after Back
**Confirmed source issue:** “Back at root” called
`gracefulCloseForeground()`, which asks the compositor to close the app and
waits; unknown native apps were reported as `at_root:true` immediately. That
left an incoming close/transition racing the Home drawer.

**Fix:** only a confirmed root backgrounds the app (process/document preserved)
through one `_returnToHome()` transition that dismisses the keyboard, clears
pointer capture/lock, closes transient overlays, resets immersive chrome and
makes Home touchable. Unknown capability now returns `unsupported` and keeps
the app foreground with a subtle notice.

### P90-08/09/10 — top gesture state machine
**Confirmed source issue:** PWA `immersive.js` only toggled a boolean status
bar and had no compact→expanded stage; `qs.js` explicitly treated expanded+up
as inert; the native statusbar’s second pull had no Quick Settings route.

**Fix:** one explicit contract:
`HIDDEN → COMPACT_BAR → EXPANDED_QUICK_SETTINGS`, with upward swipe closing
compact or expanded. The Quick Settings controller remains the single shade
owner; PWA top-edge and native statusbar both route the second pull to it
(`pwa-host action quick-settings`). Pointer/touch duplicates are de-duplicated.

### P90-11 — bottom gesture while OSK is open
**Confirmed source issue:** the navdock strip was mapped before the OSK and
could end up below the keyboard overlay.

**Fix:** when OSK visibility changes, the thin transparent strip is re-mapped so
it is the last overlay at the physical bottom edge. It does not clear keyboard
focus and does not paint over the keyboard.

### P90-12 — systemd report
**Delivered:** `tools/diagnostics/nuxel-systemd-graph.py`, root
`SYSTEMD-GRAPH.md`, `diagnostics/systemd/SYSTEMD-BOOT.svg`, raw boot/blame/
critical-chain/unit/boot-list artifacts, checksummed `collector-metadata.json`,
and a real previous-boot shutdown timeline. No timing was fabricated. The
shutdown parser explicitly excludes boot-time service restarts and anchors on
the final manager handoff.

### P90-13 — universal Back
**Confirmed source issue:** `_native_back_action()` returned
`handled:false, at_root:true` for every native app without an adapter. Absence
of an adapter was treated as proof of root.

**Fix:** typed result contract
`handled | at_root | unsupported | failed | pending`, correlated request IDs,
and a verified adapter registry. PWA apps get a documented
`NuxelBackProtocol` (`pwa/nuxel-common/back.js`) with an explicit
`at_root` declaration. Short Back never closes/kills; long-Back remains the
distinct terminate gesture; Home stays immediate.

---

## 2. Implementation (changed files)

### PWA / UI
- `pwa/nuxel-apps/settings/power-menu.js`, `power-menu.css` — transient restart
  state, neutral overlay, pagehide cleanup.
- `pwa/nuxel-home/js/app.js` — reload lifecycle, preload-cover boot/reload
  split, typed Back/Home transitions, Quick Settings entry points, visible-icon
  warm decode.
- `pwa/nuxel-home/js/qs.js`, `immersive.js`, `status-bar.js` — two-stage top
  gesture contract and upward dismissal.
- `pwa/nuxel-home/js/apps.js`, `launcher.js`, `css/launcher.css` — stable icon
  nodes, eager visible priority, immediate fallback, keyed grid reconciliation.
- `pwa/nuxel-home/sw.js`, `manifest.json` — cache namespace `v080-p90000`,
  cache-first immutable icons, install-time critical icon precache.
- `pwa/nuxel-common/back.js` — new PWA Back protocol helper.

### Native (AArch64, rebuilt on device)
- `tools/s10plus/a59/nuxel-foreign-toplevel.c` — edge-triggered lock
  enforcement, preload-surface exemption, conditional restack requests.
- `tools/s10plus/a45/nuxel-statusbar.c` — second-pull `quick-settings` route,
  upward dismiss.
- `tools/s10plus/a45/nuxel-navdock.c` — OSK visibility remap.
- `tools/s10plus/a45/nuxel-pwa-host.c` — `quick-settings[-close]` host action.

### Bridge / preload / packaging / tests
- `services/nuxel-bridge/src/api.py` — typed Back result, adapter registry,
  correlated request/session echo.
- `services/nuxel-preload-cinema/nuxel-preload-cinema` — clock/pause/EOF
  sampling, stall watchdog/nudge, first-frame receipt fields.
- `tools/diagnostics/nuxel-systemd-graph.py` + `SYSTEMD-GRAPH.md` +
  `diagnostics/systemd/`.
- `tools/pwnage90000/deploy-pwnage90000.sh`,
  `tools/pwnage90000/rollback-pwnage90000.sh`.
- `tools/s10plus/a43/package-live.py`, `verify-live.py`,
  `tools/s10plus/verify-fedora-phone-rootfs.py` — package/verify `back.js` and
  changed PWA assets.
- `tests/pwnage90000/test_pwnage90000.py` — 21 regressions.
- Updated stale contract checks in `tests/pwnage49000` and
  `tests/pwnage54000` to the new confirmed-root semantics.

---

## 3. Validation

### Host tests (2026-11-08)

**Baseline before edits:** the pwnage80000/81000/82000/84000/85000/89000 subset
reported **63 passed, 1 failed**; the failure was already the Vesktop static
marker check. This confirms the one remaining failure is pre-existing.

After the changes (short basetemp avoids the pre-existing macOS Unix-socket
path limit):

```sh
python3 -m pytest \
  tests/pwnage90000/test_pwnage90000.py tests/pwnage31000 tests/pwnage49000 \
  tests/pwnage62000 tests/pwnage63000 tests/pwnage80000 tests/pwnage81000 \
  tests/pwnage82000 tests/pwnage85000 tests/pwnage89000 \
  --basetemp=/tmp/p90safe -q
```

**Result: 160 passed, 4 skipped, 1 failed.** The single failure is the
pre-existing `test_vesktop_uses_visible_software_compositing_fallback`
(`target_id == "dev.vencord.Vesktop"` marker absent); it fails on the unmodified
baseline too and is unrelated to this mission.

Additional script gates:

- `tests/pwnage54000/test_orientation_ui.py`: **0 failing checks.**
- `tests/pwnage54000/test_app_contracts.py`: **1 failing check**
  (`clock plays the owner alarm asset`); pre-existing and unrelated (clock app
  untouched).
- `tests/pwnage90000/test_release_assets.py`: **0 failures.**
- `python3 -m py_compile` on the changed bridge/collector/preload modules: OK.
- `node --check` on every changed JS module plus the new helper: OK.
- The 45-test preload suite passes with a short basetemp; without it, pytest’s
  long `/private/var/.../pytest-of-...` path exceeds the 104-byte macOS socket
  limit and the fake IPC bind fails (host harness limitation, not a code
  regression).

### Device checks

- Native clients compiled natively on the S10+ and report `AArch64` in
  `readelf -h`; installed hashes match the build output.
- `systemd-analyze verify` on the wayland/display/bridge/web units: only
  pre-existing warnings (`RestartMaxDelaySec` without `RestartSteps`, `@dbus`
  syscall group on this kernel, executable `nuxel-bootmode-oneshot.service`).
- `/run/nuxel/lock-enforcement.state` mtime unchanged across 5 s while locked.
- `POST /api/v1/apps/back` returned the typed contract:
  `{"status":"at_root","at_root":true,"handled":false,"method":"home",
  "request_id":"p90-probe","session":7,...}`.
- Served PWA: `const CACHE_VERSION = 'v080-p90000'`; manifest
  `cache_version = v080-p90000`.
- One owner each for pwa-host, navdock, statusbar, lock watch, OSD and the shell
  chrome supervisor.
- Host action `reload-launcher` was executed on the live device; the post-reload
  UI audit reported `powerMenus:0`, `frames:0`, `iframes:0`, `preload-ready`,
  no boot splash, and the lock still enforced. Evidence:
  `docs/pwnage-90000/evidence/final/reload-ui-state.txt`.
- Native top-bar action routing was verified end-to-end:
  `HOST_ACTION quick-settings -> launcher page` and
  `HOST_ACTION quick-settings-close -> launcher page` (same evidence file).

---

## 4. Hardware verification matrix

| P90 | Check | Result |
|---|---|---|
| 01 | Restart from Settings → next boot shows no outgoing overlay | **NOT RUN** — requires operator tap. Offline lifecycle tests pass; cold-boot capture contains no outgoing menu surface. |
| 02 | Full ~6.016 s preload motion | **PASS (S10+)** — 15 consecutive distinct composited frames; `clock_advances=48`, `stall_count=0`, EOF 6.32–6.40 s. |
| 03 | First unlocked frame paints all desktop/dock icons | **NOT RUN** — device remained locked; no operator unlock. Host/static tests pass. |
| 04 | Ten lock/unlock cycles preserve Flatpak PID/state | **NOT RUN** — device remained locked. The repeated-restack source is fixed and the lock receipt is stable over 5 s. |
| 05 | Flatpak tap→first-frame baseline/after | **NOT RUN** — launches are correctly refused while locked. Stage instrumentation added. |
| 06 | Reload launcher without blue rectangle | **PARTIAL** — the real host `reload-launcher` action was verified with a clean overlay audit; the Settings touch gesture ×10 is **NOT RUN** (operator input). |
| 07 | App → one Back → drawer immediately | **NOT RUN** — requires touch. Offline Back/drawer contract tests pass. |
| 08/09/10 | Fullscreen top pull / second pull / up dismiss | **PARTIAL** — the native `quick-settings` route was delivered end-to-end; the physical two-pull/up-swipe sequence is **NOT RUN** (touchscreen input). State-machine tests pass. |
| 11 | Bottom swipe with OSK visible | **NOT RUN** — requires touchscreen + keyboard input. Native remap compiled and installed. |
| 12 | Real boot + shutdown evidence | **PASS (S10+)** — see `SYSTEMD-GRAPH.md`. |
| 13 | App-first Back on installed PWA/native/Flatpak apps | **PARTIAL** — typed endpoint verified; in-app adapter coverage listed below; GTP+ absent. |

No boot/kernel/modem partition was flashed. No push, merge, PR or release was
performed.

---

## 5. Performance (measured, not estimated)

| Metric | Baseline | After |
|---|---|---|
| Preload composited frame changes (30-sample live capture) | **0** (1 distinct frame) | **15** |
| Preload `wl-fb` blits during clip | 39 | 122 |
| Preload clock advances | clock to EOF, no frame callbacks | 42–48 advances |
| Preload stall count | n/a (frozen) | 0 |
| Clean boot total | 17.585 s (3.486 kernel + 14.099 userspace) | **16.143 s** (3.430 + 12.713) |
| Lock enforcement restacks while already locked | once per second | 0 over the 5 s sample |

Boot values are single clean-boot observations; some run-to-run variance is
expected. No icon first-paint or Flatpak TTFF number is reported because those
hardware sequences could not be run without unlocking the device.

---

## 6. Systemd graph

- Report: `SYSTEMD-GRAPH.md`
- Boot graph: `diagnostics/systemd/SYSTEMD-BOOT.svg`
- Shutdown timeline (event-derived): `diagnostics/systemd/SYSTEMD-SHUTDOWN.svg`
- Raw: `boot-systemd-analyze.txt`, `boot-blame.txt`,
  `boot-critical-chain.txt`, `boot-units.tsv`, `boot-list-units.txt`,
  `boot-failed.txt`, `boots.txt`, `shutdown-journal-summary.txt`
- Metadata/checksums: `diagnostics/systemd/collector-metadata.json`
- Collector: `tools/diagnostics/nuxel-systemd-graph.py`

The shutdown timeline is **CAPTURED** from the real previous-boot journal
(manager handoff at 114.299 s, last journaled stop at 115.924 s, 1.625 s
observed window). The collector notes that journald itself stops during
handoff, so the journaled window is a lower bound.

---

## 7. Back adapter coverage (live inventory, 2026-11-08)

| Installed app | Adapter | Result model |
|---|---|---|
| `org.mozilla.firefox` | Alt+Left explicit shortcut | handled / delivered, not state-verified |
| `com.stremio.Stremio` | Alt+Left explicit shortcut | handled / delivered, not state-verified |
| `org.videolan.VLC` | Escape explicit shortcut | handled / delivered, not state-verified |
| `org.nuxel.BrowserNative` | app-owned browser state FIFO | handled or confirmed at_root |
| `org.gnome.FileRoller`, `Loupe`, `Papers` | Alt+Left explicit shortcut | handled / delivered |
| `app.legcord.Legcord` | none | **unsupported** — stays foreground |
| `com.github.IsmaelMartinez.teams_for_linux` | none | **unsupported** |
| `com.rtosta.zapzap` | none | **unsupported** |
| `dev.vencord.Vesktop` | none | **unsupported** |
| `io.mpv.Mpv` | none | **unsupported** |
| `org.ferdium.Ferdium` | none | **unsupported** |
| `org.gnome.TextEditor` | none | **unsupported** |
| `org.signal.Signal` | none | **unsupported** |
| `org.telegram.desktop` | none | **unsupported** |

**GTP+ discovery:** no installed Flatpak, desktop file, or app-registry entry
on the S10+ matched `GTP+`/`GPT+` on 2026-11-08. The installed app list contains
Legcord, Portal for Teams, ZapZap, Stremio, Vesktop, mpv, Ferdium, Text Editor,
Firefox, Signal, Telegram and VLC. No ID was invented; the generic truthful
Flatpak contract is implemented instead.

---

## 8. Risks and limitations

1. **Hardware UI sequences not run.** Touch gestures, unlock cycles, icon first
   paint, Reload launcher and tap-to-launch Flatpak TTFF require physical input
   and/or an authenticated unlock. They are reported as NOT RUN.
2. **Back adapters that inject a shortcut prove delivery, not history depth.**
   They return `verified:false`; only app-owned state (browser FIFO) can return
   `at_root`.
3. **Shutdown window is journaled only.** Journald stops during final handoff;
   the measured 1.625 s window is what the journal recorded, not a fabricated
   total.
4. **Pre-existing host test issues.** One Vesktop static check and one clock
   asset static check fail on the baseline; the macOS pytest socket-path limit
   requires a short `--basetemp`. Neither is caused by this mission.
5. **Installed Nuxel version remains v0.7.9-beta** while the checkout is
   v0.8.0-beta. Files were deployed individually; no version bump or release
   was performed.

---

## 9. Rollback

All replaced files have an in-place backup:
`<path>.nuxel-rollback-p90-20261108T095310`.

Fast rollback on the phone:

```sh
./tools/pwnage90000/rollback-pwnage90000.sh
# or, if operating from the device:
bash /path/to/rollback-pwnage90000.sh
```

The script restores the newest `.nuxel-rollback-p90-*` copy for every native
binary, the preload controller, the bridge API, the PWA JS/CSS/SW/manifest and
the power-menu assets, then restarts `nuxel-bridge`, `nuxel-http-bridge`,
`nuxel-wayland` and `nuxel-wl-fb`.

Rebuild/redeploy:

```sh
NUXEL_HOST=root@192.168.178.167 \
NUXEL_SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  ./tools/pwnage90000/deploy-pwnage90000.sh
```

No partition, bootloader, kernel or modem image was modified, so no flash
rollback is required.
