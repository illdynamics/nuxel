# WEBKIT INPUT TRACE — A34

## The correlated tap

Raw evidence is `evidence/t8-app-launch-raw.txt`. At `2026-10-17T10:13:01Z`:

```
NUXEL_INPUT EVT pointerdown x=155 y=235 tag=DIV id=app-icon app-category-productivity
NUXEL_INPUT EVT touchstart  x=155 y=235 ...
NUXEL_INPUT EVT touchmove   x=155 y=236 ... (3)
NUXEL_INPUT EVT pointerup   x=155 y=236 ...
NUXEL_INPUT EVT app:launch  id=org.nuxel.Mail name=Mail
NUXEL_INPUT EVT touchend    x=155 y=236 ...
```

`app:launch` is dispatched by the launcher's own `js/apps.js` `launchApp()`.
It is not a synthetic event and not a host-side `launch` command; the same
second contains the raw `TOUCH_POINT` records and the IRQ increment.

## What the owner saw

The launcher then created a fullscreen iframe for Mail (`js/app.js` `_openPwa`).
A screenshot at 12:18 local (`evidence/a34/mail-open-physical-tap-1213.png`)
shows the Mail PWA, not the Home grid:

* `#0d1f3c` top bar / folders (6.5% of pixels),
* `#0a1628` body (92.6% of pixels; the mail list is empty in this build),
* dark circular `✕` at top right (the launcher's close button, z-index 10000).

So the physical tap did open the correct application and the framebuffer did
change **without** a Power press. The "whole GUI is frozen" report is explained
by the fullscreen, almost-empty Mail surface: Home is no longer visible and the
only way back is the small `✕`. This is a product/UX defect, not a touch loss.

## Second physical activation (Calendar)

At `10:23:39Z` the same pipeline produced another real activation:

```
NUXEL_INPUT EVT pointerdown x=37 y=154 tag=SPAN id=app-icon ...
NUXEL_INPUT EVT touchstart  x=37 y=154 ...
NUXEL_INPUT EVT pointerup   x=37 y=155 ...
NUXEL_INPUT EVT app:launch  id=org.nuxel.Calendar name=Calendar
```

`evidence/a34/calendar-open-physical-tap-1223.png` is the resulting Calendar
surface. This is an independent second T8 confirmation on a different app.

## Diagnostic limitation

The WebKit user script is injected with `WEBKIT_USER_CONTENT_INJECT_TOP_FRAME`,
so events inside the Mail iframe are not in `/run/nuxel-home.state`. The later
`TOUCH_POINT` records at 10:13:07–09Z / 10:13:54–56Z are consistent with taps
inside Mail and cannot be used as evidence of a top-frame loss.

## T8 / T9

* T7 handler: **PASS** (`app:launch` ran).
* T8 correct action: **PASS for this one tap** (Mail opened and rendered).
* T9 owner confirmation of normal interaction: **PENDING** (Test B).
