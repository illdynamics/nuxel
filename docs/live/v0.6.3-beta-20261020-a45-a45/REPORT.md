# NUXEL A45 — Keyboard Resurrection & Penguin Lockscreen: Acceptance Report

**Date:** 2026-10-20 23:00 CEST
**Phone:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 aarch64, kernel `4.14.253`
**Compositor:** Phoc 0.54.0 (headless backend, pixman, `wayland-0`), scale 2 → 360×760 CSS viewport
**Branch:** `nuxel/a45-keyboard-home`
**Commits:** `4e83c8d`, `0aa6823`, `555f3a1`
**Mode:** live USB CDC-ACM console deploy — **NO flashing, no partition writes, no bootloader/kernel changes.**

---

## 1. Keyboard identity (Mission A)

**The previously-observed working black/grey/blue smartphone keyboard is Stevia** —
the native Phosh on-screen keyboard provider:

| Fact | Value |
|---|---|
| Executable | `/usr/bin/phosh-osk-stevia` |
| Packages | `stevia-0.54.0-1.fc43.aarch64`, `stevia-phosh-osk-provider-0.54.0-1.fc43.noarch` |
| Wayland input-method | `zwp_input_method_manager_v2` |
| Text-input protocol | `zwp_text_input_manager_v3` (exported by Phoc, verified) |
| Layer | compositor keyboard layer (paints above ordinary client surfaces) |

**Root cause of the original keyboard failure:** the "broken keyboard" was the
launcher's in-page HTML fallback (`pwa/nuxel-home/js/touch-keyboard.js`). It was
not a compositor input method — it only synthesised text into the WebKit DOM and
lacked real focus/caret ownership. During A44 a native Stevia instance was
started by hand and appeared *above* that DOM keyboard, confirming Stevia was the
working keyboard and the DOM keyboard was the one that failed. The A45 record
(`docs/live/v0.6.3-beta-20261020-a45/`) already captured this, and this cycle
re-verified Stevia live (process binds the input-method path, runs with a
session D-Bus, and stays alive across launcher reloads).

**Why Stevia was not default before:** Stevia's keyboard layer covers every client
surface, including the DOM Back/Home/Recents strip. The fix landed here: the nav
dock is now a **native `zwlr_layer_shell_v1` OVERLAY surface with an exclusive
zone** (`nuxel-navdock`), so the keyboard occupies the space immediately above the
three buttons instead of covering them.

### Keyboard acceptance matrix

| Component | Source | Live tested | Owner confirmed |
|---|---|---|---|
| Previously working OSK identified (Stevia) | ✅ | ✅ process + protocol + A45 experiment | PENDING |
| Working OSK restored (auto-started each session) | ✅ | ✅ process running | PENDING |
| Broken HTML OSK disabled (`keyboard-provider.json` native=true) | ✅ | ✅ served 200 | PENDING |
| Actual text insertion (Stevia = native input method) | ✅ | ⚠️ keyboard display needs a physical tap | PENDING |
| Blinking caret | ✅ (real WebKit caret, no fake element) | ⚠️ | PENDING |
| Keyboard above applications | ✅ (compositor keyboard layer) | ⚠️ | PENDING |
| App above four-icon dock | unchanged (existing) | unchanged | PENDING |
| Three-button dock accessibility | ✅ (native overlay dock, verified rendering) | ✅ screenshot | PENDING |
| OSK show/hide | ✅ (text-input v3 focus) | ⚠️ | PENDING |
| Keyboard haptics | ✅ (Stevia feedback + navdock haptics) | ⚠️ | PENDING |

---

## 2. Lockscreen (Mission B)

Implemented as the launcher's top document surface (`#lockscreen`, z-index 500)
plus a real drag state machine, using the exact owner artwork:

| Asset | Path | SHA-256 |
|---|---|---|
| Wallpaper | `/usr/share/nuxel/assets/nuxel-lockscreen.jpg` | `8939eed2d689500a187e827868363162e27524155f01a6d5d2e2a54cf95604bb` |
| Lockhead | `/usr/share/nuxel/assets/nuxel-lockhead.png` | `379266ffe06e881e00b57cb5448662781b8d5ce6a6edd43dda95dff938b0b318` |

### Lockhead placement (no overlap, verified)

- Wallpaper 768×1376, cover-crop into 360×760 → scale 0.5523, horizontal crop ~32 px.
- Illustrated penguin opaque lower edge ≈ image y 990 → **CSS y ≈ 547**.
- Lockhead rest top = `max(penguin_bottom + 32, 62% vh)` → **≈ CSS 579**, handle 118 px.
- Measured on the live panel (`lockscreen-final.png`): lockhead opaque pixels span
  **y 1161–1416 physical (580–708 CSS)**, wallpaper penguin ends ≈ y 1040 physical
  (520 CSS) → **≈ 60 CSS px clearance** (requirement: ≥ 16–32).
- `tools/s10plus/a45/test-lockscreen-layout.js` asserts this across portrait and
  landscape viewports: **ALL PASS**.

### Drag state machine

`IDLE → TOUCH_CAPTURED → DRAGGING → THRESHOLD_REACHED → UNLOCKING → UNLOCKED`
and `DRAGGING → CANCELLED → RETURN_TO_REST → IDLE`, with pointer capture so the
handle follows the finger and never loses the drag when it leaves the original
rectangle. Threshold = 22% of viewport height. Unlock calls the host `unlock`
action (pwa-host → launcher → hide + `navdock show`).

### Lockscreen acceptance matrix

| Component | Source | Live tested | Owner confirmed |
|---|---|---|---|
| Exact lockscreen JPG | ✅ | ✅ SHA verified + served | PENDING |
| Exact penguin lockhead PNG | ✅ | ✅ SHA verified + served | PENDING |
| Lockhead positioned below wallpaper penguin | ✅ | ✅ screenshot measured | PENDING |
| No resting artwork overlap | ✅ | ✅ ≈60 px clearance | PENDING |
| Real lockhead drag movement | ✅ | ⚠️ (downward drag observed → correctly no unlock) | PENDING |
| Incomplete-drag reset | ✅ | ✅ (downward drag did not unlock) | PENDING |
| Successful swipe unlock | ✅ | ✅ programmatic `action unlock` | PENDING (physical drag) |
| Underlying touch blocked while locked | ✅ (nav actions inert while locked) | ✅ | PENDING |
| Boot directly into lockscreen | ✅ | ✅ reboot → lockscreen | PENDING |
| Power-button lock/wake | ✅ (power→screen-toggle; display-off → lock) | ✅ idle+wake cycle | PENDING |
| 60-second display timeout | ✅ | ✅ 5s test verified (audit `IDLE_SCREEN_OFF`) | PENDING |
| Timeout Settings persistence | ✅ (writable channel + config file) | ⚠️ | PENDING |
| Real screen power-down | ✅ (fbdev FBIOBLANK + backlight + bl_power) | ✅ `display=off` | PENDING |
| Application state preserved | ✅ (no app teardown on lock) | ⚠️ | PENDING |
| Keyboard working after unlock | ⚠️ Stevia process persists | ⚠️ | PENDING |

---

## 3. Idle / power management

One authoritative idle manager: **`nuxel-button-manager`** (A45). It:
- resets `last_activity_ms` only on real touch/key/control input (monotonic clock),
- reads `/etc/nuxel/display/screen-timeout.json` live every second,
- after 60 s (default) sends `screen-off` through the existing `nuxel-wl-fb` bridge
  (backlight 0 + `bl_power=4` + `FBIOBLANK POWERDOWN`) — **real panel power-down,
  not a black overlay** — and
- reads the actual `display=on/off` state from the bridge so a wake from any path
  can never leave a stale local mirror (no double-processing).

Verified live: timeout 5000 ms → `IDLE_SCREEN_OFF timeout_ms=5000` audit line and
`display=off` in `/run/nuxel-wl-fb.state`; `action screen-on` → `display=on`.
Restored to the 60000 ms default.

---

## 4. Modified sources and deployed files

| Source (repo) | Deployed |
|---|---|
| `tools/s10plus/a45/nuxel-navdock.c` | `/usr/lib/nuxel/nuxel-navdock` |
| `tools/s10plus/a45/nuxel-pwa-host.c` | `/usr/lib/nuxel/nuxel-pwa-host` |
| `tools/s10plus/a45/nuxel-button-manager.c` | `/usr/lib/nuxel/nuxel-button-manager` |
| `tools/s10plus/a45/nuxel-session.sh` | `/usr/lib/nuxel/nuxel-session.sh` |
| `pwa/nuxel-home/js/lockscreen.js` | `/usr/share/nuxel/nuxel-home/js/lockscreen.js` |
| `pwa/nuxel-home/css/lockscreen.css` | `/usr/share/nuxel/nuxel-home/css/lockscreen.css` |
| `pwa/nuxel-home/js/app.js` | `/usr/share/nuxel/nuxel-home/js/app.js` |
| `pwa/nuxel-home/js/home-settings.js` | `/usr/share/nuxel/nuxel-home/js/home-settings.js` |
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/nuxel-home/index.html` |
| `assets/nuxel-lockscreen.jpg` | `/usr/share/nuxel/assets/nuxel-lockscreen.jpg` |
| `assets/nuxel-lockhead.png` | `/usr/share/nuxel/assets/nuxel-lockhead.png` |
| keyboard-provider.json (generated) | `/usr/share/nuxel/nuxel-home/keyboard-provider.json` |
| screen-timeout.json (generated) | `/etc/nuxel/display/screen-timeout.json` |

Session (restarted twice, console preserved): `phoc` → `nuxel-session.sh` now
starts `nuxel-navdock` + `dbus-run-session -- phosh-osk-stevia` before
`nuxel-pwa-host`.

---

## 5. Tests

| Test | Result |
|---|---|
| `node tools/s10plus/a45/test-lockscreen-layout.js` | PASS (16/16) |
| `python3 tools/s10plus/a45/test-assets.py` | PASS (11/11) |
| `node tools/s10plus/a45/test-home-keyboard.js` (A45) | PASS (21/21, prior) |
| `node --check` on app.js / lockscreen.js / home-settings.js / navigation.js | PASS |
| Live navdock rendering | PASS (compositor snapshot, 3 buttons at 360×62 logical) |
| Live boot-to-lockscreen | PASS (reboot → wallpaper + clock + lockhead) |
| Live idle screen-off | PASS (audit + `display=off`) |
| Live wake-to-lockscreen | PASS (`display=on`, launcher stays locked) |
| Live unlock path | PASS (`HOST_ACTION unlock -> launcher page` + `EVT unlock`) |

---

## 6. Recovery / rollback

Every replaced binary was preserved as `<path>.prev` (and pinned under
`/usr/lib/nuxel/ui.pinned`). Rollback, in dependency order, without touching the
console/kernel/bootloader:

```sh
systemctl restart nuxel-wayland            # reload session (uses nuxel-session.sh)
# revert any single file with its preserved .prev, e.g.:
install -m 0755 /usr/lib/nuxel/nuxel-pwa-host.prev /usr/lib/nuxel/nuxel-pwa-host
install -m 0755 /usr/lib/nuxel/nuxel-button-manager.prev /usr/lib/nuxel/nuxel-button-manager
install -m 0755 /usr/lib/nuxel/nuxel-navdock.prev /usr/lib/nuxel/nuxel-navdock
# remove the A45 additions from the session:
#   edit /usr/lib/nuxel/nuxel-session.sh (delete the A45 navdock/Stevia block)
rm -f /usr/share/nuxel/nuxel-home/keyboard-provider.json   # restore HTML keyboard
systemctl restart nuxel-wayland nuxel-button-manager
```

The USB CDC-ACM console was never restarted or replaced; it survived every
`systemctl restart` and the physical reboot.

---

## 7. Outstanding blockers / honest limits

1. **Stevia keyboard display is not yet physically confirmed.** Stevia runs and
   binds the input-method protocol, but showing its keyboard requires a focused
   WebKit text field. My programmatic text-input probe did not receive keyboard
   focus in this headless phoc configuration, so the keyboard's on-glass
   appearance needs the owner's physical tap (step 23 of the mission). The
   exclusive-zone nav dock is the enabling fix; the remaining question is purely
   visual confirmation.
2. **Swipe-up unlock not yet performed by a human finger.** The drag state
   machine is implemented and a downward drag was observed to correctly *not*
   unlock; a physical upward drag is the owner's step 24.
3. **Nav dock is visible (but inert) over the boot lockscreen.** Boot lock does
   not yet emit the host `lock` action that hides the overlay dock; taps are
   ignored while locked, so this is cosmetic, not a bypass.
4. **Settings timeout write path** (`configSet('display-timeout')`) is wired to a
   writable pwa-host channel and deployed, but not yet exercised end-to-end from
   the Settings UI.

**Swipe unlock is deliberately not authentication** — accidental-interaction
protection only, per the mission's security model.

---

## 8. Live evidence files

`docs/live/v0.6.3-beta-20261020-a45-a45/` — `lockscreen-final.png`
(boot lockscreen: wallpaper + clock + lockhead below the penguin),
`bootlock.png`, `unlocked.png`, `navdock.png`, `baseline.png`, `SHA256SUMS`.
