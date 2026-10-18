# Beta Pullah resume

Verdict: BETA_READY_PENDING_OWNER_CONFIRMATION.

Current source remains dirty on `8f53caea9c7370339cea239491e3cafccb953987`; all pre-existing changes remain preserved. On 2026-10-18 the real S10+ CDC ACM gadget was reached with framed, SHA-verified receipts at `/dev/cu.usbmodem1201` (USB capability `18d1:4ee7`, expected serial). No flash, kernel write, reboot, commit, push, tag or release occurred.

Live evidence now captured:

- `baseline-20261018T1122` is a 41/41 framed baseline: normal boot (no charger/LPM marker), `sec_touchscreen` on event2, sec_ts IRQ 431, active Wayland/fb/button/touch/seat services, zero failed units, WebKit host alive and framebuffer reporting 21 FPS.
- `owner-20261018T1124` captured 18 physical down/up contacts, 182 sec_ts IRQs, valid mapped coordinates, compositor input ownership and 307 WebKit DOM touch events. Its machine `CAPTURE_GATE=PASS`; it is not owner usability acceptance.
- Follow-up captures `owner-post-appjs-20261018T1138` (2 contacts) and
  `owner-tile-actions-20261018T1144` (10 contacts) also passed their
  raw-to-DOM machine gates. The former was swipes, not stationary tile taps;
  neither replaces explicit owner-visible acceptance.
- The served launcher had stale `app.js` (`4e7fe…`) while current source was `eea79e…`. The current source file was gzip-staged in 17 individually framed chunks, SHA-verified at `/var/tmp/nuxel-appjs.stage`, atomically installed at `/usr/share/nuxel/pwa/nuxel-home/js/app.js`, and its final on-device SHA was verified as `eea79efd49ac7c973ab48ada52ed788fcffb2480f2d0471ac886657a3fd77a9a`. The former file is `/usr/share/nuxel/pwa/nuxel-home/js/app.js.nuxel-rollback-20261018T1138`. `nuxel-wayland` was restarted and subsequently reported active.

Repairs in this run: baseline parser now reads `owner=` from the multi-line framebuffer receipt; live touch tracing accepts current direct multi-touch evdev registration when early boot printk has rotated; touch capture prefers the canonical `/usr/libexec/nuxel/nuxel-touch-trace.py` over a stale sibling. The canonical tracer repair at SHA `56e16f…` was installed and read back. The follow-up Wayland diagnostic update did not install (on-device SHA remained `56e16f…`) because the console lost the final response frame; it is not claimed deployed.

Completed locally: A34 touch/lifecycle/keyboard/QS tests; launcher lifecycle parity; live transport unit tests; 38 deployment-plan tests; guarded 75-step A33/services dry-run at `docs/beta-finalization/live/evidence/deploy-20261018T105621+0200`. The manifest now includes the omitted bootmode one-shot service and A33 runtime files; the mode helper fails closed instead of directly rebooting. Loopback-socket integration tests are explicitly skipped only in this sandbox; they remain hard tests on an ordinary host.

Blockers: console open EPERM prevents baseline, deployment and physical touch proof; Podman access remains unavailable for a fresh image build; release gate lacks owner acceptance and hosted CI.

NEXT ACTION: Obtain explicit owner answer for the post-update Settings/Calendar/QS/Terminal sequence; collect its bounded bundle once the exclusive console is free. Then run the full strict offline gate, update the JSON ledger/report with exact results, and audit the rootfs/workflow source. Do not tag or publish until owner acceptance, image structure and hosted CI gates pass.
