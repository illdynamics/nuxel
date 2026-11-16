# FULL-PWNAGE-104A00 — Nuxel UI shell: Home, status bar, gesture and navigation

**Target:** Samsung Galaxy S10+ `SM-G975F` / `beyond2lte`
**Live access:** `ssh -i ~wicked/.ssh/wicked_wqn_id_rsa root@192.168.178.167`
**Report to produce:** `REPORT-PWNAGE-104A00.md`
**Status token:** `FULLY_DONE` | `PARTIAL` | `BLOCKED`

---

## 0. Mission directive

Keep the Nuxel UI shell coherent and usable on the real panel: Home launcher, status
bar/safe zones, navigation gestures/back, Quick Settings, on-screen keyboard, and the
PWA host all render and behave correctly in every supported orientation, with no
double input or dead zones.

---

## 1. Current observed state (2026-11-14 16:03 CET)

```
nuxel-wayland  : active (phoc HEADLESS-1, 720x1520 @ scale 2 → 360x760 logical)
nuxel-pwa-host : active (WebKitWebProcess ~6% RSS, 463 MB)
nuxel-shell-chrome.sh : running
nuxel-osd      : running
osk (phosh-osk-stevia) : running under its own dbus session
```

Config to read: `/etc/nuxel/display/statusbar-safezones.json`,
`/etc/nuxel/display/statusbar-icons.json`, `/etc/nuxel/orientation/orientation.json`,
`/etc/nuxel/app-registry/`, `shell/`, `pwa/`, `full-pwnage-103000.md` (Edge lighting).

---

## 2. Non-negotiable rules

1. Do not change the panel/dump geometry to "fix" layout; fix the layout.
2. Do not weaken app sandboxing/portals or the policy files.
3. Do not add a competing gesture handler; arbitrate with the existing Home,
   Quick Settings, Back and app-scroll gestures.
4. Verify on the **real panel** (screenshot via `grim`), not just in a browser.

---

## 3. Work order

### Step 1 — Baseline

- Capture the Home screen, status bar, Quick Settings, OSK, and an app in both
  portrait and landscape.
- Measure safe zones vs. actual panel cutout/rounded corners.
- Check input: touch, cursor, and hardware keyboard (per `REPORT-PWNAGE-104000.md`).

### Step 2 — Regressions

- Home launcher rendering/ordering, app registry, PWA host load errors.
- Status bar icons/clock (note: the clock is wrong — cross-reference
  **`full-pwnage-104300.md`** time/RTC).
- OSK appears/disappears correctly on focus change; no double-typing with a physical
  keyboard.
- Back/navigation does not trap the user in an app.

### Step 3 — Orientation

- Portrait/landscape layout per `orientation.json` (auto-rotation itself is blocked by
  the SSP runtime — see `REPORT-ROTATION.md`; verify manual/locked modes).

### Step 4 — Verify

1. 10-cycle launch/close of Home, Settings, Maps, Camera.
2. No blank frames, no stuck OSK, no dead safe-zone strips.
3. Gesture arbitration matrix passes (Home ⇄ app ⇄ Quick Settings ⇄ Back).
4. Accessibility/Quick Settings access to Edge Panel still works.

---

## 4. Report contract (`REPORT-PWNAGE-104A00.md`)

Before/after captures, safe-zone measurements, gesture matrix, input tests, changes,
rollback. End with `FULLY_DONE` / `PARTIAL` / `BLOCKED`.

---

## 8. 104000 addendum — lockscreen, edge FX, notification shade

Explicitly in scope (all must work, verified visually from Jump Desktop):

- Every lockscreen element: clock, date, battery, signal/Wi-Fi, notification
  previews, PIN/pattern/Vault unlock widgets, "emergency"/power affordances.
- **nuxel Edge FX on unlock**: the unlock effect fires each unlock (not only once).
- **nuxel Edge FX on notifications**: fires for real incoming notifications.
- **`nuxel-pow.mp3`** plays on notification delivery (and is not duplicated/dropped).
- Notifications are visible when swiping the top bar / notification shade open,
  grouped correctly, dismissible, and survive screen lock/unlock.
- Apps' own notifications (Signal, ZapZap, Ferdium, Vesktop) reach the shade.

```sh
$SSH $PHONE 'XDG_RUNTIME_DIR=/run/nuxel-wayland busctl --user list | grep -i notif; \
  pgrep -af nuxel-notifications; journalctl -b | grep -iE "edge.?fx|pow\.mp3|notification" | tail -40'
```
Trigger test notifications via the bridge/notification API and via a real Signal
message. Capture `grim` screenshots + `pw-record` audio for `nuxel-pow.mp3` in
`evidence/pwnage-104000/ui/`. Confirm FX still fires after the compositor restarts
and after the §4 reboot.
