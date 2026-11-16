# PWNAGE-103000 — Nuxel LED / Torch / Edge Lighting / Edge Screen

**Verdict: `PARTIAL`** — all userspace software work is implemented, tested and
deployed to the live S10+; physical owner checks (torch visibility, edge-effect
visibility on glass, finger-swipe ergonomics) remain **NEEDS_OWNER_PHYSICAL_TEST**.

| Item | Value |
|---|---|
| Target | Samsung Galaxy S10+ `SM-G975F`, `beyond2lte`, Exynos 9820 |
| SSH | `root@192.168.178.167` with `~wicked/.ssh/wicked_wqn_id_rsa`, host-key verification on (no `StrictHostKeyChecking=no`) |
| Device verified | `Linux 4.14.253-gf7194c1d15ed-dirty … aarch64`, `uid=0`, board `BEYOND2LTE EUR OPEN 26`, live `2026-11-12T10:35+01:00` |
| Reflash | **none** — no partition, kernel, boot image or DT touched |
| Backups | `/root/nuxel-backup-103000-20261112T093450Z/` (+ local source snapshot) |
| Manifest | `evidence/pwnage103000/deploy-manifest.json`; FX follow-up `evidence/pwnage103000/fx-fix-deploy-manifest.json` |
| Rollback | `evidence/pwnage103000/rollback.sh`; FX follow-up `evidence/pwnage103000/fx-fix-rollback.sh` |
| Live evidence | `evidence/pwnage103000/device/` (final state: `final-live-state.txt`, render: `render-final/evidence.json`); FX follow-up live proof: `device/fx-fix-live/` |

---

## 1. Implementation summary

### Torch (real rear flash only)
* Single owner unchanged: `services/nuxel-bridge/src/flashlight_provider.py`.
  No new LED writer; the UI/edge code contains no `/sys` or `/dev/fb` path.
* **Fixed policy bug:** the provider silently capped `max_on_ms` at 300 s while
  the shipped policy says `600000`. It now enforces `min(600 s, policy)` and never
  more than the policy. Live status reports `max_on_seconds = 600.0`.
* **OFF on init:** provider construction re-reads the LED and writes 0 when it is
  non-zero (a crashed previous process can no longer leave the torch burning).
* ON/OFF are read back; a failed write or non-zero readback is `ERROR` with
  `last_error`, never a fake ON. Timeout is a provider-side `threading.Timer`
  (survives client disconnects; one timer per session).
* `status()` now exposes `remaining_seconds`, `session`, `on_count`, `last_error`.
* `leds-sec1` is never adopted (no source/physical evidence of a notification
  role). No notification, boot, animation or edge path can turn the torch on.

### Notification → Edge Lighting (AMOLED display overlay)
* **One controller:** new `services/nuxel-bridge/src/edge_lighting_provider.py`.
  It is the only owner of Edge Lighting policy state and never writes an LED.
* **One event source:** the HTTP bridge subscribes to
  `org.nuxel.Notifications.NotificationAdded` on the system bus (the canonical
  hub, no second notification store). The watch owns a dedicated GLib loop
  (the HTTP server has none; sharing the default loop silently dropped callbacks —
  measured and fixed).
* Storage per existing unit design: read-only shipped default
  `/etc/nuxel/edge-lighting/edge-lighting.json` (Wave/theme/1800 ms), mutable user
  document `/var/lib/nuxel/edge-lighting/settings.json` (the unit is
  `ProtectSystem=full`/strict writes; this directory is persistent and survives
  reboot and service restarts — verified live).
* Bounded journal `/var/lib/nuxel/edge-lighting/events.jsonl` (rotates), read by
  Home through `GET /api/v1/edge-lighting/events?since=N`. Entries carry
  **app id + category + effect settings only** — never summary, body, contact or
  even app display name (a hub `app_name` is usually the sender label). The
  renderer resolves names from the canonical registry.
* Policy: enabled, effect, colour mode/value, width, transparency, duration,
  `screen_on` only, DND, reduced motion, reduced-motion style, per-app allow/block
  (validated against the canonical registry). Dedupe per notification record
  (`DEDUP_WINDOW_MS=1500`) and coalescing of a different record inside 700 ms.
* Truthful capability: `screen_off` and `always` are reported
  `NOT_SUPPORTED_BY_CURRENT_DISPLAY_STACK` (no edge-only low-power render path);
  they are disabled in the UI, not faked.
* `preview` returns presentation metadata only, is never journaled as a
  notification, and cannot be used to inject a real event (`event` RPC verb is
  refused for PWAs).

### Effects (all eight, original code)
`basic`, `wave`, `bubble`, `multicolor`, `heart`, `fireworks`, `eclipse`, `echo`
in `pwa/nuxel-home/js/edge-lighting.js` + `css/edge-lighting.css`. Wave is the
persisted default; the colour resolves from the live `--nx-accent` token
(fallback `#63f0bd`). Only transform/opacity animate, ≤5 particles per side,
`will-change` only while running, one cancellable lifecycle, pointer-events none,
reduced motion = short static pulse. Each effect was rendered in real WebKit on
the device (DOM evidence in `evidence/pwnage103000/device/evidence.json`).

### Edge Panel
* Opened by a deliberate inward swipe from either curved side (30 px band,
  ≥42 px inward, 1.5× dominance) through the **existing** gesture owner
  (`js/gestures.js`) + pure recognizer `js/edge-panel-gesture.js`; no second
  document-level pointer/touch listener. Accessible entries: Quick Settings
  “Edge” tile and the Edge FX app.
* Apps come from `appRegistry.getAllApps()` (55 real apps on device), notifications
  from the canonical `statusBar` state, hidden while locked; launching uses the
  canonical `launchApp()`. Closes on outside tap, Back/Escape, orientation,
  blur, display sleep, Quick Settings opening or explicit close.
* Left/right, portrait/landscape, arbitration with drawer/QS/top-edge/bottom
  dock/scrolls: covered by the recognizer test matrix (all pass).

### Edge FX app (installable / uninstallable)
`pwa/nuxel-apps/edge-fx/` — canonical PWA (`nuxel-edge-fx`): on/off, eight effect
tiles with previews, theme/preset/custom colour, width, transparency, duration,
DND, reduced motion, screen-state honesty, source allowlist from the real
registry, “Open left/right” panel buttons, and **Uninstall / Install (reinstall)**
via the existing `apps` RPC. Live test: register → `installed_and_launchable`
(registry_version 20), unregister → `staged_not_registered` (21), re-register (22).
Settings/documents are preserved on uninstall. Also reachable from Settings →
Notifications → Edge lighting (status, preview, on/off, Open Edge FX/panel).


---

## 1a. Edge FX follow-up — Preview + Allow all apps (live fixed)

The owner reported that the Edge FX app's **Preview selected** button did
nothing and that **Allow all apps** did not work. Both were reproduced and
fixed against the live S10+ and verified in the real app iframe.

### Root causes (measured, not guessed)

1. **Preview was hidden/unreachable.** `body.edge-panel-open
   #nuxel-edge-lighting { visibility:hidden }` hid the whole overlay whenever a
   panel/QS flag remained set, and the Edge FX full-screen app frame sits above
   Home's overlay. The app also called `parent.NuxelEdgeLighting.preview()`
   without an acknowledgement, so a suppressed preview looked like a no-op.
2. **First save raced the bridge module.** `edge-fx.js` is a classic script;
   `bridge.js` is an ES module loaded after it. The first tap often saw
   `window.NuxelBridge === undefined`, and the old code refused with
   "Bridge unavailable" instead of waiting.
3. **Home read a legacy settings shape.** The edge engine called the shared
   `NuxelBridge.get('/edge-lighting')`; that client already prefixes
   `/api/v1`, so the request became `/api/v1/edge-lighting/edge-lighting` and
   the first settings read fell back to a legacy unauthenticated document
   without `source_mode`. The UI then used the old ambiguous all-apps logic.
4. **All-apps state was ambiguous in the UI.** `allowed_apps: []` means "all
   apps" in the provider contract, but the Edge FX list rendered every app as
   checked. There was no explicit persisted `all` vs `allowlist` mode, so the
   list could not show what "Allow all" did. Re-rendering also captured a stale
   allowlist closure, and unchecking one row from All apps saved the other 47
   apps as an allowlist.

### Fixes

* **Preview bridge:** Edge FX posts `nuxel:edge-lighting-preview` to Home with
  a request id; Home validates source/origin, runs the one presentation
  controller (bounded, no notification state change), and acknowledges with
  `nuxel:edge-lighting-preview-result`. The direct parent call remains a
  fallback only. Preview gives the overlay an explicit visible/top-layer state
  and clears it when the bounded lifecycle ends. A master-off setting does not
  silently swallow a preview; a sleeping display still refuses it.
* **Bridge readiness:** Edge FX and the Home engine both wait for the shared
  bridge singleton before their first status/save call.
* **Correct settings fetch:** the Home engine strips the already-present
  `/api/v1` prefix before handing the endpoint to `NuxelBridge.get()`.
* **Explicit source mode:** added persisted `source_mode: "all" | "allowlist"`
  to the provider schema and shipped default, with backward-compatible
  migration (non-empty legacy allowlist → allowlist; empty → all). `all`
  ignores a stale allowlist. Edge FX reads the list from the authoritative
  returned config, not a stale closure, and shows an explicit "All apps" state.
  From All apps: checking a row selects only that app; unchecking a row selects
  every app except it. Per-app edits persist `allowlist`.
* Cache/manifest bumped to `v097-p103000`; Edge FX asset query bumped to
  `p103000b`.

### Live verification (real Home document + real Edge FX iframe, headless WebKit on device)

`evidence/pwnage103000/device/fx-fix-live/`:

* **Preview selected — `PASS_DEVICE_RUNTIME`:** clicking the actual Preview
  button made `#nuxel-edge-lighting.active` true with computed
  `visibility: visible`, `z-index: 240` above the app frame, 2 edge bands and
  the expected particles; Home's `lastPreview.ok` was true. After the bounded
  duration it automatically returned to inactive/hidden. One overlay root only.
* **All eight effects through the app frame — `PASS_DEVICE_RUNTIME`:**
  basic, wave, bubble, multicolor, heart, fireworks, eclipse, echo all
  activated and were visible with the correct particle budgets (2 bands each;
  0/6/8/0/6/10/4/6 particles). `effects-live.json`.
* **Allow all apps — `PASS_DEVICE_RUNTIME`:** start at All apps (0 of 48
  checked) → select one app (1 of 48, summary "1 of 48 apps") → tap **Allow all
  apps** → 0 of 48 checked, summary "All apps", provider
  `allowed_apps: []`, `source_mode: "all"`. `allowall-live.txt`.
* Deployed artifacts byte-identical to the repository
  (`installed-sha256.txt`); `nuxel-http-bridge`, `nuxel-web`,
  `nuxel-notifications`, `nuxel-wl-fb`, `nuxel-wayland` active; torch still
  `OFF`, `max_on_seconds 600`; no reboot, no reflash.

### Follow-up tests

`tests/pwnage103000/test_edge_fx_fixes.py` (added to `run-all.sh`) covers the
preview acknowledgement path, origin/source validation, overlay visibility and
top-layer cleanup, bridge readiness, `/api/v1` endpoint handling, explicit
source mode, authoritative re-render, the all-apps checkbox semantics and
cache version lockstep. Provider tests now cover `source_mode`, legacy
migration and `all` ignoring a stale allowlist. Full gate:

```
sh tests/pwnage103000/run-all.sh   -> PWNAGE-103000 GATE: PASS
```

**Physical checks still outstanding:** the owner must confirm the preview is
visible on the curved glass and that finger taps on the real app trigger it;
synthetic in-iframe clicks prove delivery and rendering, not glass visibility.
That keeps the overall mission verdict **PARTIAL**.

### FX follow-up deployment / rollback

* Backup: `/root/nuxel-backup-103000-fxfix-20261112T103651Z/` (prior
  Home JS/CSS, whole Edge FX bundle, user settings, provider, shipped default;
  `SHA256SUMS`).
* Manifest: `evidence/pwnage103000/fx-fix-deploy-manifest.json`.
* Rollback:
  `scp evidence/pwnage103000/fx-fix-rollback.sh root@192.168.178.167:/tmp/ &&
  ssh root@192.168.178.167 'sh /tmp/fx-fix-rollback.sh'`.
  It restores only the four PWA files, provider, default and Edge FX bundle,
  restarts only `nuxel-http-bridge`, and preserves
  `/var/lib/nuxel/edge-lighting` user settings. `RESTORE_V096=1` also restores
  the prior cache marker.

---

## 1b. Edge FX follow-up #2 — Preview + Allow all apps (live re-verified, deployed)

The owner reported again that **Preview selected** and **Allow all apps** did not
work. Both were reproduced against the deployed app on the live S10+ and fixed;
the fix is deployed (`v098-p103000`) and verified on the real `:8000` document.

### Root causes (measured live, not inferred)

1. **Effect tiles never saved.** `renderEffects()` called `previewEffect(eff)` and
   nothing else, so tapping Heart/Fireworks/etc. only previewed; the persisted
   effect never changed (reproduced: tapped `heart`, provider stayed `fireworks`).
2. **Preview ignored the app's own controls.** Home rendered the preview from its
   stale settings copy, so the chosen colour/width/duration were not what lit the
   edge.
3. **Allow all persisted but Home kept the old policy.** The provider accepted
   `source_mode=all` (`HTTP 200`, `settings.json` written) while Home's engine
   still held `allowlist → ["nuxel-dialer"]`; the app then re-rendered from its
   own local flag. The owner's exact live state
   (`source_mode: "allowlist"`, `allowed_apps: ["nuxel-dialer"]`) was reproduced.
4. **Overlay could be clipped/invisible.** `.edge-root` used `contain: strict`
   (paint containment), clipping particles and masks to a 13 px slab.
5. **Mock replies looked real.** The shared bridge client returns `{mock:true}`
   when its RPC cannot run; the app treated that as a provider answer, so a failed
   call was reported as "provider refused the change".
6. **A suppressed preview reported success**, so "nothing visible" looked like it
   worked.

### Fixes (repository)

* `pwa/nuxel-apps/edge-fx/edge-fx.js`
  * Effect tile: persists the selection *first* (so a suppressed preview can never
    block saving), then previews; `?fixture=1` is presentation-only and never writes.
  * `previewSettings()` sends colour/width/transparency/duration to Home; Home
    accepts them as a **presentation-only** override.
  * Every successful save posts `nuxel:edge-lighting-resync` with the provider's
    document, so Home's engine adopts the authoritative config immediately.
  * Allow all: serialized save, read-back via `status`, and success is only shown
    when the provider really reports `all` — otherwise the exact state is named.
  * `save()` is serialized and every failure names its cause and label.
  * `{mock:true}` replies are never accepted (falls back to the bootstrap-token RPC).
  * Uninstall/reinstall: no button left disabled after a failure, a blocked
    confirm dialog is not consent, and the post-uninstall text is consistent.
* `pwa/nuxel-home/js/edge-lighting.js`
  * `preview(effect, {settings})` honours the app's presentation settings.
  * Handles `nuxel:edge-lighting-resync` and exposes `api.syncConfig(config)`.
  * A preview that was not rendered returns `ok:false` with
    `display-asleep` / `edge-lighting-off` / `reduced-motion-suppressed`.
* `pwa/nuxel-home/css/edge-lighting.css`
  * Removed root paint containment; the layer and sides no longer clip particles.
* `sw.js` + `manifest.json` → `v098-p103000`; `index.html` and the Edge FX asset
  queries bumped in lockstep (`edge-lighting.js?v=p103000b`,
  `edge-fx.{js,css}?v=p103000c`).
* `tests/pwnage103000/test_edge_fx_fixes.py` extended for all of the above.

### Live verification (`PASS_DEVICE_RUNTIME`, deployed `:8000` tree)

* **Preview:** `active:true`, `visibility:visible`, `z-index:240`,
  `overflow:visible`, custom colour `#ff8fab` applied, both sides present; the
  bounded 1800 ms lifecycle then returns to `hidden`. Message:
  "Previewing Echo — no notification was created or changed."
* **All eight effects** through the real app: tile → persisted == previewed for
  basic, wave, bubble, multicolor, heart, fireworks, eclipse, echo; 2–12 nodes.
* **Allow all apps:** from the reproduced `allowlist → [nuxel-dialer]` state,
  the button leaves provider **and** Home at `all` / `[]`, summary "All apps";
  repeatable (checked twice) and a per-app edit switches back to a 1-app allowlist.
* **Real notification:** id 92 (`org.nuxel.Mail`) under `all` produced one bounded
  journal entry (`seq 6`, `effect echo`); message body never journaled; notification
  then closed through the hub.
* **Install lifecycle:** real buttons → `Installed (installed_and_launchable)` →
  `Uninstalled` (absent from the registry) → `Installed` (registry v28).
* **Health:** `nuxel-web`, `nuxel-http-bridge`, `nuxel-notifications`,
  `nuxel-wl-fb`, `nuxel-wayland`, `nuxel-bridge` active; torch `OFF`,
  `max_on_seconds 600`; no reboot, no reflash, no partition write.
* Gate: `sh tests/pwnage103000/run-all.sh` → **PASS**; `verify-wiring.js` → all six
  PWA surfaces OK. Rollback dry-run restored all eight files byte-identical to the
  backup.

**Still `NEEDS_OWNER_PHYSICAL_TEST`:** actual visibility on the curved glass and a
finger tap on the real screen. Everything above is DOM/rendering evidence inside
the device's WebKit, not a human observation. Because the phone was locked
(display-off) at deploy time, the running launcher reloads the new bundle on the
next unlock (no force-reload while locked).

**Deployment:** backup `/root/nuxel-backup-103000-fxfix2-20261112T120614Z/`,
manifest `evidence/pwnage103000/fx-fix2-deploy-manifest.json`, rollback
`evidence/pwnage103000/fx-fix2-rollback.sh`, evidence
`evidence/pwnage103000/device/fx-fix2-live/`.

---

## 2. Evidence tiers

| Evidence | Tier |
|---|---|
| Device model/root/kernel/SSH target verified | `PASS_DEVICE_RUNTIME` |
| Torch class discovery, OFF-by-default, readback, timeout, error cleanup, policy ceiling | `PASS_BUILD_TEST` + live `GET /api/v1/system/flashlight` (`OFF`, `max_on_seconds 600`) |
| Torch physical light | `NEEDS_OWNER_PHYSICAL_TEST` |
| `rear_torch` capability | `PASS_DEVICE_RUNTIME` |
| `notification_led` / `rgb_notification_led` | `NOT_SUPPORTED_ON_DEVICE` (only `torch-sec1`, `leds-sec1` exist; no notification/RGB class) |
| `leds-sec1` role | left unassigned; not advertised as RGB/notification |
| Edge Lighting provider, policy, persistence, dedupe, DND, allowlist, journal privacy | `PASS_BUILD_TEST` + live device (`/var/lib/nuxel/edge-lighting/settings.json` survives `nuxel-http-bridge` restart) |
| Real notification → one event | `PASS_DEVICE_RUNTIME` (hub `SubmitNotification` → `NotificationAdded` → journal entry; DND suppresses; no private text) |
| Eight effects render both sides in WebKit (zero JS errors) | `PASS_UI_RENDER` (`evidence/pwnage103000/device/render-final/evidence.json`) |
| Effect visibility on the curved glass | `NEEDS_OWNER_PHYSICAL_TEST` |
| Edge Panel opens left+right with 55 registry apps, closes | `PASS_UI_RENDER` + `PASS_DEVICE_RUNTIME` (`device/render-final/evidence.json`, `device/panel-probe.txt`) |
| Finger-swipe ergonomics in both orientations | `NEEDS_OWNER_PHYSICAL_TEST` |
| Screen-off / Always lighting | `NOT_SUPPORTED_BY_CURRENT_DISPLAY_STACK` |
| Edge FX install/uninstall | `PASS_DEVICE_RUNTIME` (`device/edge-fx-install.txt`) |
| Service-worker cache v096-p103000 shipped | `PASS_BUILD_TEST` (HTTP 200 on the new assets; v096 bump in sw.js + manifest) |
| New modules loaded by the **live Home WebView** | `PASS_DEVICE_RUNTIME` — the production `WebKitWebProcess` (parent `nuxel-pwa-host`) was observed polling `GET /api/v1/edge-lighting/events?since=…` every 2 s (118+ polls, log evidence `device/live-ui-runtime.txt` and `live-event.txt`). The launcher document itself was loaded before the deploy, so a clean owner-visible reload (`action reload-launcher` → `app.reloadLauncher()`) is still required for the new QS tiles/gestures to appear; the reload was **not forced** because the device was locked at mission end (reload is correctly blocked while locked). |
| Touch controller tuning | not attempted (no measured need); controller policy unchanged |

---

## 3. Tests (all pass)

```
sh tests/pwnage103000/run-all.sh
  test_edge_lighting_js.py          ALL PASS   (registry, defaults, colour, scene budgets, CSS)
  test_edge_panel_gesture.py        ALL PASS   (25+ cases: sides, landscape, vertical/diagonal/outward,
                                                top-edge/bottom-dock/owned surfaces, cancel, 1-swipe=1-open, 20 cycles/side)
  test_edge_lighting_provider.py    ALL PASS   (defaults+persistence, event ingest, privacy, dedupe/coalesce,
                                                DND, allow/block, disabled, preview, journal rotation, migration)
  test_pwnage103000_contract.py     ALL PASS   (one notification source, one gesture owner, no fb/LED writer,
                                                routes/watch, SW cache, Edge FX app, registry, Settings wiring)
  test_torch_safety.py              ALL PASS   (600 s ceiling, OFF on init/exit, timeout, ERROR cleanup,
                                                rapid toggles, thermal/camera blocks, leds-sec1 not adopted)
  baseline pwnage44000/45000/50000/85000/93000  PASS
PWNAGE-103000 GATE: PASS
```
Also: `tools/s10plus/a33/verify-app-registry.py` → `problems=0` (verdict
`OFFLINE_TESTED_WITH_DEFERRALS`, the one deferral is the pre-existing `privacy`
app), `pwa/nuxel-common/verify-wiring.js` → `ALL 6 PWA SURFACES OK`, and
`python3 -m py_compile` on all touched bridge modules.

Device-side render harness: `/usr/local/bin/nuxel-edge-render.py` →
`PASS_UI_RENDER_EFFECTS` with **all four checks true**: engine+recognizer loaded,
all 8 effects rendered on both sides (bands + the per-effect particle counts
0/4/3/2/5/3/0/3 per side), zero JS errors, and the Edge Panel opening left and
right with 55 canonical apps and the Notifications tab, then closing. Evidence:
`evidence/pwnage103000/device/render-final/evidence.json`,
`evidence/pwnage103000/device/edge-render.log`, plus the standalone probe
`device/panel-probe.txt`. (One harness run early in the session reported the
panel step false because the offscreen WebKit host can delay async evaluate
callbacks after a long effects loop; with the final files the same harness passes.
The rendered DOM/state is proven — physical visibility on the glass is not.)

**Baseline failures (pre-existing, unrelated, not touched):**
`tests/pwnage54000/test_app_contracts.py` → “clock plays the owner alarm asset”
fails (the clock app already lacked `assets/nuxel-alarm.mp3` before this mission;
`pwa/nuxel-apps/clock` is unmodified).

---

## 4. Live verification (device)

* Services after deploy: `nuxel-web`, `nuxel-http-bridge`, `nuxel-bridge`,
  `nuxel-notifications`, `nuxel-wl-fb`, `nuxel-wayland` all **active**; no crash
  loop, no traceback in `journalctl -u nuxel-http-bridge`.
* Bridge startup log:
  `edge-lighting: watching org.nuxel.Notifications.NotificationAdded`,
  `effect=wave enabled=True settings=/var/lib/nuxel/edge-lighting/settings.json screen_modes=['screen_on']`.
* Torch: `state=OFF on=false supported=true led_path=/sys/class/camera/flash/rear_flash
  max_on_seconds=600 reason="provider init: explicit OFF"`; `torch-sec1=0`, `leds-sec1=0`.
* LED capability report (`/usr/local/bin/nuxel-led-diag.sh edge`):
  LEDs enumerated `leds-sec1`, `torch-sec1`; `notification_led=NOT_SUPPORTED_ON_DEVICE`;
  `home_runtime.loaded=true`, 8 effects, default `wave`.
* Edge Lighting: default `wave` / `theme` / 1800 ms / medium / screen_on, persisted;
  changing to `eclipse`, restarting `nuxel-http-bridge`, and re-reading returns
  `eclipse` from `/var/lib/nuxel/edge-lighting/settings.json` (then restored to `wave`).
* Real event: notification id 86 (`org.nuxel.Mail`) → one journal entry
  `{seq, record_id, app_id, effect:"wave", duration_ms:1800}`; a second notification
  inside the coalesce window was folded; DND on → no entry; DND restored off.
  `grep PRIVATE /var/lib/nuxel/edge-lighting/events.jsonl` → 0 hits.
* Edge FX registry: installed (registry_version 20) → uninstalled → `staged_not_registered`
  → reinstalled (22, `installed_and_launchable`).
* The six notifications used for verification were removed through the hub's own
  `CloseNotification` after the tests; no owner records, messages or settings were
  modified, and no private notification contents are stored in any artifact.
* All deployed files byte-identical to the repository (`sha256` compared).

**Truth correction (read-only finding):** `/sys/class/camera/flash/rear_flash` is
**not** a torch-state readback. Its `show` returns the constant
`S2MPB02_TORCH_OUT_I_MAX-1` (`15`) from `kernel/.../drivers/leds/leds-s2mpb02.c`.
A value of `15` therefore does not mean the flash is on; `torch-sec1/brightness`
is the state node. The provider still reads back after writes (for the LED-class
fallback path) and reports the write result honestly.

---

## 5. Files created / modified

Created: `services/nuxel-bridge/src/edge_lighting_provider.py`,
`configs/nuxel/edge-lighting/edge-lighting.json`,
`pwa/nuxel-home/js/edge-lighting.js`, `pwa/nuxel-home/js/edge-panel-gesture.js`,
`pwa/nuxel-home/css/edge-lighting.css`, `pwa/nuxel-apps/edge-fx/{index.html,
manifest.json,app.json,edge-fx.js,edge-fx.css,e2e/e2e.html}`,
`pwa/nuxel-apps/settings/edge-lighting-settings.js`,
`tools/s10plus/a33/edge-runtime/{edge-runtime-render.py,nuxel-edge-runtime-probe.py,nuxel-edge-runtime-probe.sh}`,
`tests/pwnage103000/*`.
Modified: `services/nuxel-bridge/src/{api.py,flashlight_provider.py}`,
`pwa/nuxel-home/{index.html,sw.js,manifest.json,js/gestures.js,js/qs.js,js/apps.js}`,
`pwa/nuxel-common/{bridge.js,app-registry.json}`,
`pwa/nuxel-apps/settings/index.html`,
`shell/nuxel-home-native/nuxel_home/app_registry.json` (mirror sync),
`tools/s10plus/a33/nuxel-led-diag.sh` (`edge` report; `nuxel-led-diag.sh status` unchanged).
Reason for each: see `deploy-manifest.json` (`reason` field).

---

## 6. Owner acceptance steps still required (`NEEDS_OWNER_PHYSICAL_TEST`)

1. **Torch:** Quick Settings → Flash on, look at the rear flash, then off; confirm
   the light is visible and turns off. (Torch is OFF today; no ON test was run
   autonomously because the owner's phone was untouched/unobserved at the time.)
2. **Edge Lighting on glass:** open Edge FX, tap each of the eight tiles; confirm
   the effect is visible along the curved edges and that Wave is selected by
   default with the theme accent. Then trigger a real notification (e.g. send a
   mail/reminder) and confirm exactly one bounded animation.
3. **Edge Panel ergonomics:** from Home, swipe inward from the left curved edge,
   then the right; repeat in landscape; confirm vertical scrolling near the edge,
   top-edge Quick Settings, bottom drawer and dock taps still work; close with
   outside tap, Back and an outward swipe.
4. **Reload for the new UI:** the running Home document was loaded before this
   deploy. From an unlocked session use **Settings → Apps → Edge FX**, or reload
   the launcher once; the new “Edge” / “Edge light” Quick Settings tiles and the
   side-swipe panel then appear (the Edge Lighting engine itself is already live in
   the running WebView, as its 2 s event polls show).
5. **Screen off:** confirm the expected honest behaviour — Edge Lighting does not
   animate while the panel is off (documented limitation, not a secret).

## 7. Rollback

```sh
scp evidence/pwnage103000/rollback.sh root@192.168.178.167:/tmp/
ssh root@192.168.178.167 'sh /tmp/rollback.sh'
```
It restores `/usr/lib/nuxel/nuxel-bridge/{api.py,flashlight_provider.py}` and the
pre-mission `/usr/share/nuxel/pwa/{nuxel-home,nuxel-common/bridge.js,
nuxel-common/app-registry.json,nuxel-apps/settings}` from
`/root/nuxel-backup-103000-20261112T093450Z/`, removes the additive Edge FX bundle,
Edge Lighting default and provider module, restarts only `nuxel-http-bridge`, and
keeps user Edge Lighting settings/journal under `/var/lib/nuxel/edge-lighting`.
No partitions, kernel, boot or DT are involved.
