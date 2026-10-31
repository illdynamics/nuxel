# PWNAGE-44000 — NUXEL HOME, HARDWARE CONTROLS, GALLERY & FILE SHARING

**Result:** source implementation + offline regression gate + non-destructive live deployment complete.
**Target:** Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 ARM64, kernel 4.14.253.
**Live host:** `root@192.168.178.167`, key `~/.ssh/wicked_wqn_id_rsa`.
**Base:** `dfd9e76` (`feature/pwnage-43000-final`; the pre-existing dirty tree was preserved, not reset).
**Commit:** `77c3890` — `feat(pwnage-44000): home drag, sticky notes, 15-entry power menu, screenshot, gallery, files and status truth`.

## 1. Implemented

### Home drag/reorder
`pwa/nuxel-home/js/launcher.js`
- One pointer state machine; primary-pointer ownership; secondary contacts cannot cancel/hijack.
- Long-press timer uses stored coordinates (never a stale event object).
- Pointer capture is taken on the stable `#app-grid` during a drag and released on every exit.
- `lostpointercapture`/`pointercancel` roll back the complete layout snapshot.
- Live `elementFromPoint` hit-testing; insertion before/after, empty-grid append, edge-hover page switch.
- Drop outside the grid cancels instead of silently appending.
- `touch-action:none` on app tiles while `#app-grid` keeps native scroll; page swipe remains a separate touch observer.
- Tap-to-launch retains release-target identity (`release over another icon does not launch`).
- New tests: `pwa/nuxel-home/tests/test-launcher-drag.js` plus the existing touchable suite.

### Notes + sticky widget + desktop mapping
- Persisted widget `desktop` is **one-based**; `renderPage(pageIndex)` compares `desktop === pageIndex + 1`. Schema-1 documents migrate losslessly (their values were already the human desktop number).
- Real Notes widget: add/remove, note selection, open-note deep link, clamped body, resize handle, long-press reposition/reorder, all persisted.
- Home Settings caches the panel, uses one set of handlers, refreshes note options after saves, refuses to add a widget with no note, and defaults to desktop 2 when it exists.
- Notes saves are serialized through a revision queue; “Saved” only appears after the write confirms; failed writes keep content and remain dirty; localStorage is an offline cache, not a second source of truth.
- `nuxel:notes-updated` plus the same-origin open-note key synchronize Home widgets and an already-open Notes app.
- Tests: rewritten `test-widgets.js`, new `pwa/nuxel-apps/notes/tests/test-notes-save.js`.

### Performance
- Files: one delegated grid listener; `DocumentFragment` batches of 120; stale render tokens cancel; selection toggles classes only; no per-item listeners.
- Quick Settings: one pull opens, a second/deeper pull expands, timers are panel-owned and stopped on close, stale indicator generations are discarded, expanded strip updates individual cells.
- Home Settings: cached panel/hydration path (no `innerHTML` rebuild on reopen).
- Status bar/QS idle work is display-off gated; continuous location/indicator animations stop while the panel is blank.
- Measured Files 1000-entry synthetic render (linkedom, 20 iterations):
  `p95 59.74 ms -> 34.27 ms` (**42.6% lower p95**); p50 unchanged.
- Live Gallery thumbnail: cold decode **2163 ms**, cached **35 ms** (**98.4% lower** after first frame).

### A34 power menu
- `tools/s10plus/a34/nuxel-button-fsm.h` now matches all **15** configured entries, including Back, Forward, Stop loading and Reload launcher, before the two hard-refused bootloader entries.
- Dispatcher forwards those four verbs to `nuxel-pwa-host`, which already implements `nuxel:action` for them.
- Recovery/Download remain `trigger_allowed=0`, refusal `NO_FLASH_INVARIANT`.
- New `test-a34-power-menu.py` drives the real A34 header and compares JSON/table/action/allowed entry-by-entry. New `test-screenshot-chord.sh` proves the chord suppresses menu/volume classes.
- Live OSD after deployment: `kind power-menu count 15`, ids in configured order. A live Recovery selection produced `MENU_REFUSED id=recovery reason=NO_FLASH_INVARIANT`; the phone stayed in Linux.

### Screenshot
- The rootfs builder now compiles A68 `nuxel-screenshot.c` and installs it at the exact `SHOT_BIN=/usr/lib/nuxel/nuxel-screenshot`.
- Contract verified: `argv[1]` destination PPM, `P6`, Wayland screencopy only, no `/dev/fb0`.
- Host bounds the child (10 s), converts P6 to PNG, atomically publishes in `/home/nuxel/Gallery`, and emits a visible `nuxel:toast` only after the PNG exists.
- Live: `SHOT_OK ... 720x1520`, Gallery PNG 2,514,716 bytes, signature `89504e470d0a1a0a`, owner `nuxel:nuxel`, mode 640, indexed by `storage.media-list`.

### Gallery thumbnails
- `PwaStore.storage_thumbnail()` validates canonical paths, rejects traversal/symlink escape, chooses ffmpeg → mpv → GStreamer, uses argv + shell=False + hard timeouts, writes atomically, and caches by path+size+mtime_ns.
- `POST /api/v1/rpc storage.thumbnail` and `GET /api/v1/storage/thumbnail?path=` serve controlled `image/jpeg`.
- Gallery grid uses `<img loading=lazy decoding=async>`; one shared IntersectionObserver; no `<video>` per cell. Viewer creates at most one on-demand video and keeps the poster plus an honest codec limitation message on error.
- Live endpoint: HTTP 200, 28,111-byte JPEG, 31–38 ms warm.

### Files Send / Bluetooth OBEX
- Send button, selected-path sheet, Bluetooth device list, progress/result and disabled “Coming soon” Wi-Fi Direct/Nearby entries.
- `bluetooth_obex.py` uses BlueZ `org.bluez.obex` ObjectPush1; waits for `Status=complete`; closes sessions; rejects traversal, symlink escape, invalid MACs, >20 files/>512 MB.
- `bluez-obexd` added to the image manifest and installed live; bridge uses the Nuxel session bus for OBEX and the system bus for BlueZ adapters. Live `send-targets` returned the real adapter and zero paired peers (no receiver available for a physical transfer proof).

### Flashlight
- Single owner `flashlight_provider.py`: discovers a writable torch class, writes brightness only from this provider, enforces 60 s max-on, explicit OFF on timeout/exit/toggle, camera marker arbitration, thermal guard, and truthful `NOT_SUPPORTED_ON_DEVICE`/`BLOCKED_CAMERA`/`THERMAL_LIMIT`/`ERROR`.
- QS uses `flashlight.status/toggle`; the hardware path relays through `nuxel-pwa-host` → `/usr/bin/nuxel-flashlight-rpc` → HTTP bridge. No JS writes sysfs.
- Live on `torch-sec1`: `ON` with brightness 15, explicit `OFF` with brightness 0, max-on 60 s, camera/thermal flags false.

### Status + expanded QS
- Top bar now has Location (provider truth), sound mode (normal/vibrate/silent/unknown), and a compact USB glyph labelled `file`/`term`/`chrg` by the canonical precedence, plus a cable-only state.
- Expanded QS strip shows charging vs external power, USB host, active vs selected file transfer, live console active vs armed, and console transports.
- `Full` no longer counts as active charging; the lightning bolt is `Charging`-only and static.
- `system_indicators.get_indicators()` now includes `sound_mode` with `haptics_verified=false`.

## 2. Evidence

Directory: `docs/beta-finalization/live/evidence/pwnage-44000/`

- `offline-tests.log` — complete PWNAGE-44000 gate, all pass.
- `live-baseline.txt` — units, live binary hashes, canonical indicators, flashlight status.
- `live-power-menu.json` — 15-entry live OSD document.
- `live-screenshot.txt` — live PNG metadata.
- `live-thumbnail-timing.txt` — cold/warm timings.
- `files-render-benchmark.json` — 1000-entry before/after render sample.
- `ROLLBACK.md` — exact live rollback.

## 3. Deployment record

- Backup: `/root/pwnage-44000/backup-20261031T054927Z`.
- PWA deployed to `/usr/share/nuxel/nuxel-home` and `/usr/share/nuxel/pwa/nuxel-apps/{files,photos,notes}`.
- Backend deployed to `/usr/lib/nuxel/nuxel-bridge`; helper `/usr/bin/nuxel-flashlight-rpc`; LED policy `/etc/nuxel/leds/leds.json`.
- ARM64 binaries compiled **on the S10+** from the patched sources and installed:
  - `nuxel-pwa-host` `2227030f…94b1`
  - `nuxel-button-manager` `e914612c…5b1e`
  - `nuxel-screenshot` `35b55190…645b`
- `nuxel-http-bridge` and `nuxel-button-manager` restarted; `nuxel-wl-fb` (single `/dev/fb0` owner) untouched.
- Additive Fedora package: `bluez-obexd-5.87+…fc43.aarch64`.
- Final reboot was performed through the existing gated userspace manager (`action reboot-request`), not `systemctl` from JS or a forced reset.
- Post-boot (2026-10-31 06:56:46): button manager, HTTP bridge, web server, wl-fb and PWA host all active; the new PWA host was loaded (hash `2227030f…94b1`); exactly one wl-fb owner; live menu still 15 entries; screenshot action created a second real PNG which Gallery indexed (count 5); flashlight state OFF.

## 4. Remaining owner-dependent checks

- Physical touch proof of long-press drag, sticky-widget resize/move and Notes deep link after reboot.
- A physical Bluetooth transfer needs a second paired OBEX receiver; the provider, UI and honest unavailable/complete states are implemented.
- Visible torch illumination is proven only by the actual LED node changing 0→15→0; the owner should confirm visually during a bounded ON.
- Gallery playback of a codec WebKit cannot decode remains a truthful poster + limitation message.

No mock state was introduced: UNKNOWN, OFF, selected-but-inactive and ACTIVE remain distinct.
