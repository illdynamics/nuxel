# SOURCE PATCHES — A34

All changes are userspace. No kernel, bootloader, partition or device-tree write
was made.

## 1. `tools/s10plus/a34/nuxel-wl-fb.c`

Derived from the deployed A33 source. Adds:

* `BL_POWER` path and `bl_power_write()`.
* `display_set(0, ...)`: brightness 0 **and** `bl_power=4` (FB_BLANK_POWERDOWN).
* `display_set(1, ...)`: `bl_power=0`, `FBIOBLANK(UNBLANK)`, then restore
  brightness.
* `display_publish()` includes `actual_brightness` and `bl_power`.

Measured result: OFF `bl_power=4`, ON `bl_power=0`; one FIFO cycle wakes.

## 2. `tools/s10plus/a34/nuxel-button-manager.c`

Copied from A33 with the A34 SYN_REPORT touch fix:

* DOWN/UP/MOVE are emitted on `SYN_REPORT` after the position axes, not on
  `ABS_MT_TRACKING_ID`.
* Pending flags survive a read boundary.
* This removes the measured spurious `source=touch action=back` on a centre tap.

Deployed SHA-256: `6bdc66424fdaa31a71dcbdec58d00ed87df682b0fbb8ef9826db4d5a34bc5e6d` (first A34 build), then `dd027b9687ba397b808041b1fbc6651989de1117a58c2cff09d66f169f7465fc` after the Bixby cancellation below.

## 2a. Power menu Cancel

`nuxel-button-fsm.h` (A33 and A34 copies) and
`configs/nuxel/input/button-fsm.json` now carry an explicit **Cancel** entry as
entry 0, action `menu-close`. This is the safe initial selection and satisfies
the owner's requested menu shape. `--menu-dump` reports `MENU_COUNT 11`.
The A33 button-FSM test (`tools/s10plus/a33/tests/test-button-fsm.py`) passes
with 0 failures; the two menu-navigation fixtures were shifted by one position.

## 2b. `tools/s10plus/a34/nuxel-button-fsm.h`

A Power press now clears a pending deferred Bixby short press
(`bixby_double_deferring`) when Bixby is not held. This is the exact mechanism
that produced the previous boot's `source=tick action=open-terminal` after a
Power interaction. The deterministic trace
`tests/power-cancels-bixby.trace` reproduces the old A33 output
(`screen-toggle` **and** `open-terminal`) and asserts the A34 output contains
only `screen-toggle`. Test: `tools/s10plus/a34/tests/test-fsm-power-bixby.sh`
(PASS).

## 3. `pwa/nuxel-home/js/status-bar.js`

A34 wires the Quick Settings pull-down that the existing `qs.js` already
listened for (`gesture:qs`) but nothing dispatched. It handles pointer and
passive touch events on `#status-bar`, with a 24 px vertical threshold and an
80 px skew limit, and shares state so a browser emitting both pointer and touch
cannot open the panel twice.

Version triple updated consistently:

* `status-bar.js` `StatusBar.VERSION = 0.4.3-a34`
* `manifest.json` `nuxel.pwa_version = 0.4.3-a34`, `cache_version = v7-a34`
* `sw.js` `CACHE_VERSION = v7-a34`

## 3b. `pwa/nuxel-home/js/app.js`

Two input-integration fixes, no layout change:

* `_closeOverlays()` now removes `.pwa-frame` / `.pwa-close-btn`, so a `home`
  action closes an app surface instead of only search/QS.
* The `nuxel:action` handler is registered on **window** as well as document.
  `nuxel-pwa-host` dispatches `window.dispatchEvent(...)`; a window-target event
  does not bubble down to document, which is why the host's `home` action was
  previously a no-op. Measured: launch Mail → host `action home` → screenshot
  changes from the Mail frame (295 unique colours) back to Home (23,547).
* The button manager translates the launcher's `back` gesture to the host
  `home` action because the launcher has no back stack and pwa-host has no
  `back` handler. This is a translation of an existing gesture, not a new UI.

## 4. Diagnostics

* `tools/s10plus/a34/nuxel-wl-snapshot.c` — one-shot wlr-screencopy client;
  writes PPM, never opens `/dev/fb0`.
* `tools/s10plus/a34/nuxel-usb-input-audit.sh` — read-only USB/Type-C/HID audit.
* `tools/s10plus/a34/nuxel-display-frame-trace.sh` — frame-counter/hash sampler.
* `tools/s10plus/a34/nuxel-button-trace.sh` — bounded read-only key/MT capture.
* `tools/s10plus/a34/tests/test-fsm-power-bixby.sh` + trace — deterministic
  regression for the deferred-Bixby-to-Terminal path.
* `tools/s10plus/a34/tests/test-qs-gesture.js` — loads the real status-bar.js in
  a fake DOM and proves one vertical pull fires `gesture:qs` once, while a short
  tap or diagonal drag does not.
* Existing `nuxel-touch-trace` (A33) and `nuxel-touch-capture.sh` retained; no
  duplicate touch tracer was created.

## 5. Not changed

No launcher redesign, no compositor replacement, no second framebuffer owner,
no `dnf upgrade`, no flash, no raw partition write, no device-tree rewrite.
