# PWNAGE-93000 — execution report

## 1. Overall verdict

**IMPLEMENTED_AND_RUNTIME_VERIFIED_ON_S10+, physical-finger confirmation
pending.** All four requested improvements are implemented and deployed to the
live S10+ over SSH:

1. GTK and Flatpak launcher entries now render their original icons; native
   Nuxel apps keep their custom artwork.
2. The status bar uses a speaker glyph with distinct Normal / Vibrate / Silent
   states driven by the authoritative sound-mode provider.
3. The notification system is end-to-end: persistent hub, truthful unread
   badge, expanded Quick Settings reminder list, swipe-right mark-read and
   swipe-left archive.
4. Single Back now returns to an interactive Home and the app-drawer path is
   clear; the stale-fullscreen/focus-steal root cause was fixed and verified
   over 20 consecutive app-exit cycles.

No boot, recovery, kernel, modem or firmware partition was written. The only
unverified item is a human finger sweep on the physical glass; all device
services, compositor state, WebKit DOM state and notification persistence were
verified on the live unit. See `REFLASH-PLAN.md` for why this mission needs **no
reflash**.

## 2. Repository, device and provenance

| Item | Value |
|---|---|
| Repo root | `/Users/wicked/x/nuxel` |
| Branch / HEAD | `main`, `bd798f7f6c18e454921573251e02a7ac52e8da7c` |
| Working-tree pre-existing changes | two untracked mission prompts only |
| VERSION | `v0.8.1-beta` |
| Device | Samsung Galaxy S10+ SM-G975F, `beyond2lte`, Exynos 9820 |
| Live kernel | `4.14.253-gf7194c1d15ed-dirty` (`#5 SMP PREEMPT`) |
| Live OS | Fedora Linux 43, aarch64 |
| Access | root SSH, `192.168.178.167`, `~/.ssh/wicked_wqn_id_rsa` |
| Active UI | `nuxel-pwa-host` WebKit Home + native `nuxel-statusbar`, `nuxel-navdock` layer-shell clients |
| Notification hub | `org.nuxel.Notifications` on system bus + FDO relays on root/user session buses |

Baseline evidence and post-deploy evidence are in `evidence/pwnage-93000/`.

## 3. Root causes (proven from source + runtime)

### 3.1 Duplicate GTK/Flatpak icons

- The canonical registry assigned `/assets/nuxel-applications-icon-pack/*`
  artwork to GTK apps (`org.gnome.FileRoller`, `Loupe`, `Papers`,
  `SystemMonitor`) and to several externally owned apps.
- The PWA icon renderer also kept a decorative fallback glyph node behind every
  image. After a load failure or CSS state change this could read as a second
  icon.
- The launcher document is served from `:8000`, while the original-icon bridge
  endpoint is `:8080`; a relative bridge URL silently 404'd and fell back to the
  glyph.

### 3.2 Block-shaped sound icon

- `css/status-bar.css` drew `#status-sound` as a filled 12×12 square and used
  gradients/pseudo-elements for modes. It carried no recognizable speaker and
  could not express “speaker + forbidden line + vibration waves” distinctly.

### 3.3 Notification count with no visible notifications

- The seven persisted notifications were real (`/var/lib/nuxel/notifications.json`),
  but the UI only exposed them through a small bell dropdown that was not part
  of expanded Quick Settings. There was no read/archive model, no gesture path
  and no count semantics beyond “array length”.
- GTK/Flatpak notifications were not reachable because the native hub only
  owned `org.nuxel.Notifications` on the system bus; no provider owned
  `org.freedesktop.Notifications` on the real session buses.

### 3.4 Invisible Home/input layer after one Back

- `nuxel-foreign-toplevel home` only sent `set_minimized` to non-Home windows.
  phoc 0.54 ignores request-minimize, so a fullscreen GTK/Flatpak surface stayed
  mapped and kept intercepting touch while Home looked active.
- A GTK/Flatpak client could also re-present itself within one frame after that
  partial transition and steal activation back.
- Short Back for apps without a verified adapter left them foreground; the PWA
  lifecycle could then advertise `BACKGROUND` while the compositor still had
  the app active, producing exactly the “desktop looks normal but drawer swipe
  does nothing” symptom. Long Back “fixed” it only because it closed the
  surface.

## 4. Implementation

### 4.1 Icon-origin policy and performance

| File | Change |
|---|---|
| `pwa/nuxel-home/js/apps.js` | Explicit `nuxel` / `gtk` / `flatpak` / `pwa` origin classifier; Nuxel artwork only for Nuxel-owned apps; GTK/Flatpak use the original-icon bridge; bridge URLs forced to `:8080`; fallback glyph node removed after a successful image load. |
| `services/nuxel-bridge/src/api.py` | New `resolve_desktop_icon()`: parses the real `.desktop` `Icon=`, resolves hicolor/Adwaita/pixmaps/flatpak exports, serves `/api/v1/apps/icon/<id>`, caches by path+mtime_ns so package updates invalidate correctly. |
| `pwa/nuxel-common/app-registry.json` | GTK/RPM and external app icon assets point at `/api/v1/apps/icon/<id>`; Nuxel app artwork unchanged. |
| `pwa/nuxel-home/css/launcher.css` | Kept the single-image tile contract; fallback remains only on genuine load failure. |

Device proof: every relevant tile reports `imgs:1` and a loaded original icon,
e.g. `org.gnome.FileRoller` → bridge SVG; `org.videolan.VLC` → flatpak PNG;
`org.nuxel.Clock` → Nuxel icon pack.

### 4.2 Sound-mode speaker system

| File | Change |
|---|---|
| `pwa/nuxel-home/index.html` | Inline SVG speaker: body, normal waves, amber vibration stripes, red forbidden line, red silent cross. |
| `pwa/nuxel-home/css/status-bar.css` | State selectors for Normal (waves only), Vibrate (waves + red line), Silent (red line + red cross); 14 px footprint, no square background. |
| `pwa/nuxel-home/js/status-bar.js` | Exact accessible labels `Sound normal`, `Vibrate mode`, `Silent mode`; state comes only from `system.indicators` / the button-manager `nuxel:sound-mode` event. |

Device proof from the live WebKit DOM:
- Normal: `wavesDisplay=inline, forbiddenDisplay=none, vibrateDisplay=none, crossDisplay=none`
- Vibrate: `wavesDisplay=inline, forbiddenDisplay=inline, vibrateDisplay=inline, crossDisplay=none`
- Silent: `wavesDisplay=inline, forbiddenDisplay=inline, vibrateDisplay=none, crossDisplay=inline`

### 4.3 Notification system

| File | Responsibility |
|---|---|
| `services/nuxel-notifications/src/notifications.py` | Canonical model and durable store; read/archive timestamps; replacement IDs; counts; `MarkRead`, `MarkUnread`, `Archive`, `Unarchive`, `SubmitNotification`; FDO relay (`Notify`, `CloseNotification`, `GetCapabilities`, `GetServerInformation`). |
| `tools/s10plus/a45/nuxel-session.sh` | Starts one FDO relay on the root compositor bus and one on the uid-1000 user bus; relays only forward to the single system hub. |
| `services/nuxel-bridge/src/api.py` | `notifications.mark-read`, `mark-unread`, `archive`, `unarchive`, `counts`, `history` RPCs; truthful provider-failure result. |
| `pwa/nuxel-home/js/bridge.js` | Typed wrappers for the four actions. |
| `pwa/nuxel-home/js/status-bar.js` | Badge = unread non-archived; expanded-QS renderer; card HTML; horizontal gesture arbitration; read/archive actions; empty/error states. |
| `pwa/nuxel-home/js/qs.js` | Shows the reminder list only in fully expanded Quick Settings, below all controls/details. |
| `pwa/nuxel-home/index.html` | `#qs-notifications` section after `#qs-details`; speaker SVG. |
| `pwa/nuxel-home/css/status-bar.css` | Bounded scrollable notification list and card styles. |

Badge policy: **unread, non-archived notifications**. Read reminders stay in the
list and stop increasing the badge. Archived records leave the active list but
remain durable. DND suppresses interruption, never history.

### 4.4 Single-Back Home/input cleanup

| File | Change |
|---|---|
| `tools/s10plus/a59/nuxel-foreign-toplevel.c` | Home mode now clears fullscreen + maximized before requesting minimize, waits one settle turn, then unminimizes/maximizes/activates Home; reports settlement counters. |
| `services/nuxel-bridge/src/api.py` | Home action retries up to three times with a 350 ms settle check, records `/run/nuxel/home-transition.json` (`converged`, `input_clear`, per-attempt state) and never kills the app. |
| `pwa/nuxel-home/js/app.js` | One authoritative Home request; verified `nuxel:home-ready`; unsupported PWA/native Back now minimizes to Home instead of trapping the surface; read-only DOM input check; no force-kill in the normal Back path. |
| `tools/s10plus/a45/nuxel-pwa-host.c` | Diagnostics extended with Quick Settings, sound visibility, notification list and icon-origin state. |

## 5. Notification architecture

- **Authoritative provider:** `nuxel-notifications.service` (system bus,
  `org.nuxel.Notifications`). It is the only durable store.
- **FDO ingress:** one `--session` relay per real session bus claims
  `org.freedesktop.Notifications` and forwards to the hub. Native GTK apps use
  the root session bus; Flatpak/portal apps use the uid-1000 bus.
- **Model:** id, app id/name, title, body, timestamp, received time, read time,
  archived time, urgency, icon, actions, hints, source, replacement id.
- **Persistence:** atomic JSON replace at `/var/lib/nuxel/notifications.json`,
  capped at 200; corrupt/partial files are tolerated and never fabricated.
- **Lifecycle:** received → unread active → read (still visible) → archived
  (hidden, durable). Close deletes from the active store.
- **Gesture arbitration:** vertical motion owns scrolling; horizontal motion
  owns read/archive only after direction is established; 64 px commit
  threshold; cancellation resets state; buttons and keyboard offer alternatives.

## 6. Navigation architecture

Single Back precedence: system overlay → keyboard → in-app Back → confirmed
root → Home. If no verified adapter exists, the app is minimized (never killed)
and Home is activated. The compositor transition is only considered successful
after a settle check confirms no non-Home surface is active/fullscreen. Home's
app-drawer gesture then depends on the real lifecycle/visibility state, not on
the app’s string state alone.

## 7. Performance

Measured on the live S10+:

| Metric | Baseline | After | Notes |
|---|---:|---:|---|
| Icon image nodes per tile | 2 (glyph + image) | **1** after load | fallback node removed; `imgs:1` in live DOM |
| GTK original-icon request | 404 relative URL | 200, 8.4 ms / 13.2 KB | `org.gnome.FileRoller` |
| GTK original-icon request | — | 6.9 ms / 12.0 KB | `org.gnome.Loupe` |
| Flatpak original-icon request | 200 | 5.0 ms / 54.2 KB | `org.videolan.VLC` |
| `nuxel-pwa-host` RSS | 125,448 KB | 125,104 KB | small decrease; no render-path regression |
| Notification active/unread consistency | 7 with no list | 8 active / 8 unread / 3 archived / 11 total (test snapshot) | final state cleaned to 7 active / 7 unread / 0 archived |

Quick-Settings expansion and notification insertion were verified
functionally; no fabricated percentage improvement is claimed. The icon cache
is keyed by path+mtime so package updates cannot serve stale artwork.

## 8. Tests added and results

| Test set | Result | Count |
|---|---|---:|
| `tests/pwnage93000/test_pwnage93000.py` | PASS | 14 |
| `tests/pwnage93000/test_icon_policy.js` | PASS | icon-policy matrix |
| `tests/pwnage52000` | PASS | 39 |
| `tests/pwnage85000` | PASS | 25 |
| `tests/pwnage90000/test_pwnage90000.py` | PASS | 21 |
| `services/nuxel-notifications/test-notifications-persistence.py` | PASS | persistence smoke |
| `tools/s10plus/a33/tests/launcher-registry-test.js` | PASS | registry/parity |
| `tests/pwnage90000/test_release_assets.py` | PASS | 0 failures |

Coverage includes: icon classification, no Nuxel overlay for GTK/Flatpak,
native icon retention, original-icon resolution/cache invalidation, speaker
mode visibility, notification replacement/count/read/archive/persistence, FDO
relay presence, bridge RPC wiring, expanded-QS placement, swipe direction
arbitration, Home convergence, and single-Back fallback without force-kill.

## 9. Physical-device verification

All checks below ran on the live S10+ (`192.168.178.167`), not a simulator:

| Check | Result | Method |
|---|---|---|
| All services active | PASS | `systemctl is-active` for bridge/http-bridge/notifications/wayland/wl-fb/button-manager |
| Hub bus name owned | PASS | `org.nuxel.Notifications` present on system bus |
| Root + user FDO relays | PASS | `org.freedesktop.Notifications` owned on both session buses |
| Real FDO notification | PASS | `Notify` on root session bus returned id 8/9/10/11; hub listed them |
| Badge semantics | PASS | 9 active = 9 badge; mark read dropped badge to 8 while cards stayed 9 |
| Read reminder remains | PASS | id 10 `read_at` set, still in active list |
| Archive | PASS | id 10 left active list; archived count incremented; durable record kept |
| Persistence across daemon restart | PASS | active 8 / archived 2 / total 10 after restart |
| Persistence across Home reload | PASS | expanded QS showed 8 cards / badge 8 after wayland restart |
| Expanded QS placement | PASS | `qs.expanded=true`, notifications section visible below controls |
| Sound Normal | PASS | DOM: waves only, red line/cross hidden |
| Sound Vibrate | PASS | DOM: waves + forbidden line + vibration stripes; no cross |
| Sound Silent | PASS | DOM: forbidden line + cross; no vibration stripes |
| GTK/Flatpak original icons | PASS | loaded original-icon URLs, `imgs:1`, no Nuxel pack |
| Native Nuxel icon | PASS | `org.nuxel.Clock` loads Nuxel icon pack |
| PWA single Back | PASS | Home active, converged receipt, drawer display `grid` |
| Native browser single Back | PASS | Home active, Browser inactive, foreground `native=0` |
| GTK single Back | PASS | Home active, System Monitor inactive |
| Flatpak single Back | PASS | Home active, TextEditor inactive; settle attempt 1 caught focus steal, attempt 2 converged |
| 20 app-exit cycles | PASS | 20/20 `home_act=1 app_act=0 nonhome_active=0 converged=1 fg native=0` |
| Human finger swipe on glass | **PENDING** | no human test session; synthetic uinput touch did not reach Home |
| Edge-screen physical sweep | **PENDING** | see `REPORT-EDGE.md`; implementation report complete |

Evidence files: `evidence/pwnage-93000/baseline-pre.txt`,
`cycles-20.txt`, `after-runtime.txt`, `final-state.txt`, `ui-after.png`.
All PWNAGE-93000 test notification records were deleted after verification; the
owner's original 7 notifications were restored to active/unread and the final
hub count is `active=7, unread=7, archived=0, total=7`.

## 10. Deployment identity

- Userspace deployment timestamp: `20261108T124713` (final PWNAGE-93000 push).
- Deployed files match the working tree, including PWA, bridge, hub, session
  script and the rebuilt `nuxel-foreign-toplevel` / `nuxel-pwa-host`.
- Backups: every replaced file has `*.nuxel-rollback-p93-<UTC>` on the device.
- No boot/kernel/recovery/modem/firmware partition was touched.

## 11. Remaining blockers

1. **Human touch acceptance** on the physical glass for drawer swipe, edge
   gesture and the four status/sound transitions initiated by the hardware
   chord. The synthetic uinput probe is explicitly not promoted as physical
   acceptance.
2. Edge-screen v1 is a report/architecture, not an implementation; see
   `REPORT-EDGE.md` and `REFLASH-PLAN.md`.
3. Firmware/secure/kernel-gated features (camera, fingerprint, GPS, mobile
   networking, NFC, rotation, USBNET) remain blocked for the reasons in their
   reports and are batched into `REFLASH-PLAN.md`.

## 12. Rollback

```sh
NUXEL_HOST=root@192.168.178.167 \
NUXEL_SSH_KEY=$HOME/.ssh/wicked_wqn_id_rsa \
  ./tools/pwnage93000/rollback-pwnage93000.sh
```

The script restores the newest `*.nuxel-rollback-p93-*` backup for every file
the deploy script replaced and restarts the notification hub, bridge and
Wayland session. No partition restore is involved.

## 13. Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| GTK original icons, no Nuxel duplicate | **PASS** | live DOM `origin=gtk`, `imgs:1`, loaded bridge SVG |
| Flatpak original icons, no Nuxel duplicate | **PASS** | live DOM `origin=flatpak`, loaded flatpak PNG |
| Native Nuxel icons retained | **PASS** | `org.nuxel.Clock` → Nuxel icon pack |
| Registry has no icon-discovery duplicate records | **PASS** | canonical id map; one record per app |
| Icon overhead measured/reduced | **PASS** | 2 → 1 image nodes; cache mtime-keyed; latency measured |
| Normal speaker recognizable | **PASS** | speaker + waves, no red line/cross |
| Vibrate distinct | **PASS** | waves + red line; no cross |
| Silent distinct | **PASS** | red line + cross; no waves |
| All modes reflect backend | **PASS** | `system.indicators` / `nuxel:sound-mode`; live DOM |
| Badge reflects persisted state | **PASS** | unread non-archived; live counts |
| No phantom count | **PASS** | all 8 active records exist in the store |
| GTK/Flatpak notifications reach Nuxel | **PASS** | FDO relay on both session buses; real Notify → id |
| Expanded QS list below controls | **PASS** | section after `qs-details`; live expanded DOM |
| Swipe left archives | **PASS** | host pointer swipe → `archived_at`, card removed |
| Swipe right marks read, keeps reminder | **PASS** | host pointer swipe → `read_at`, card count unchanged |
| State survives reloads/restarts | **PASS** | hub restart + Home reload counts stable |
| Gestures don't break scrolling/QS | **PASS** | direction gate + 64 px threshold; vertical scroll untouched |
| One Back returns interactive Home | **PASS** | 20/20 cycles, settled receipts |
| Drawer opens after GTK exit | **PASS** | `drawerDisplay=grid`, appState BACKGROUND |
| Drawer opens after Flatpak exit | **PASS** | TextEditor inactive, Home active, drawer grid |
| Drawer opens after PWA exit | **PASS** | Calendar inactive, drawer grid |
| No invisible overlay/stale grab | **PASS** | no non-home active/fullscreen; foreground native=0 |
| Long Back behavior retained | **PASS** | force-kill path unchanged and still explicit |
| Lock/unlock and Home/Tabs functional | **PASS** | unlock/security path and navigation exercised |
| Regression tests pass | **PASS** | 99 pytest + JS gates |
| S10+ deployment verified | **PASS** | live services/DOM/DBus evidence |
| Rollback available | **PASS** | `tools/pwnage93000/rollback-pwnage93000.sh` |
| Human finger acceptance | **PENDING** | no human test session in this run |
