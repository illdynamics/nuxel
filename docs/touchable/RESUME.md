# Operation Touchable resume

Branch: feature/operation-touchable, based on pushed snapshot 9145338.
Current physical trial: tap-repaired-20261018t2314 (runner PID/session managed by
active agent). Wait its full 90 seconds; do not restart the GUI during capture.
Capture lives at /var/tmp/nuxel-tap-repaired-20261018t2314 on the phone and
will be retrieved into docs/touchable/evidence/ of the same trial name.

Nine PWA files deployed with matching destination hashes. Receipt and backups:
docs/touchable/evidence/deploy-taps-20261018/receipt.json and
/var/tmp/nuxel-deploy-taps-20261018/backup/. Confirmed settled framebuffer
FRAMES_OK at 23 FPS, zero failures, display on. No owner acceptance yet.

Key defect: Settings is docked; launcher ignored all dock pointerdown events.
Minimal repair plus pointer-cancel/wrong-target protection passes eight new tests.
Existing newer app.js/style/index/keyboard assets were stale on the phone; they
are now installed, giving apps a Home bar and iframe event observation.

First physical trial recorded 11 contacts with no top-document events because
Calendar was covering Home and iframe instrumentation was absent. Compositor
snapshot shows New Event form and old close glyph overlapping Save. Do not call
that absence proof of dropped events. Raw evidence preserved.

Existing serial push_bytes decode retries deleted their own parts, then emptied
the stage file if a successful receipt was lost. Corrected and exercised by an
executable lost-receipt test. No UI file was changed by the failed staging.

Mac Playwright WebKit installed under build/touchable/browser for synthetic
browser regressions. Five tap/launch/Home cycles pass. Phone ARM64 build container
nuxel-touchable-build is preparing GTK/WebKit headers for the later shared host
routing work. No host binary has been changed yet. Two desktops/global gestures
remain pending the tap trial. No flashing, reboot, framebuffer opens or input grabs.
