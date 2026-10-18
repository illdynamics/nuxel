# Live S10+ touchscreen repair — 2026-10-18

Verdict: `NEEDS_OWNER_TEST`.

The real USB CDC-ACM console was selected by capability (`18d1:4ee7`, expected
serial) and returned framed SHA-verified receipts. No flash, kernel write,
reboot, modem write, tag, push, or release occurred.

## Evidence

- `evidence/baseline-20261018T1122/`: 41/41 verified frames; normal boot;
  `sec_touchscreen` event2; sec_ts IRQ 431; active Wayland/framebuffer/button/
  touch/seat services; zero failed units.
- On-device bounded capture `owner-20261018T1124`: 18 physical down/up pairs,
  182 sec_ts IRQ events, in-range multitouch coordinates, libinput/compositor
  evidence and 307 WebKit DOM touch events. Machine gate passed.
- The framebuffer bridge reported `FRAMES_OK` at 21 FPS during the live run.
- Post-update `owner-post-appjs-20261018T1138` passed the raw-to-DOM machine
  gate (2 down/up pairs, 33 IRQ events, DOM evidence). Its input was primarily
  swipes, so it could not establish app activation.
- Focused `owner-tile-actions-20261018T1144` passed again with 10 physical
  down/up pairs and in-range coordinates. This is further transport evidence,
  not a substitute for the owner's visible PASS/FAIL statement.

## Repair and rollback

The served `app.js` was stale (`4e7fe…`) while current source was `eea79e…`.
The current source was gzip-staged in individually framed chunks, verified at
`/var/tmp/nuxel-appjs.stage`, then atomically installed as:

`/usr/share/nuxel/pwa/nuxel-home/js/app.js`

The final device SHA is
`eea79efd49ac7c973ab48ada52ed788fcffb2480f2d0471ac886657a3fd77a9a`.
Rollback is retained at
`/usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback-20261018T1138`.
`nuxel-wayland` was restarted and subsequently observed active.

The canonical touch tracer was also installed/read back at `56e16f…`. A later
diagnostic-only tracer update did not install because the console lost its final
response frame; it is not claimed deployed.

## Remaining gate

The event pipeline is proven through DOM, but that does not prove that visible
app launches, Home/Back, Quick Settings, terminal input/close, and redraw are
usable. Record the owner's explicit PASS/FAIL result for that sequence before
promoting this result or publishing a beta.
