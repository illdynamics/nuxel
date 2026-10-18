# Test results

Before patches: ten relevant strict repository suites PASS, 0 failures, in 61 s.
Includes A33 touch/boot/userspace, A34, registry, PWA bridge, activation,
console ownership, wiring, assets. See `evidence/tests-before/summary.json`.

New launcher regression initially reproduced five failures; patched code passes
eight checks. Lost USB decode-receipt executable test passes. Existing live
library: 31 tests pass. Existing capture integrity: four tests pass.

Real browser, synthetic input: Mac Playwright WebKit 27.2, viewport 360x760,
DPR 2. Five sequential app tap/close cycles pass, plus keyboard activation,
surface cleanup, changed rendered pixels and no uncaught JS errors. Test backend
is deliberately unavailable at the same origin to exercise offline fallback.
This does not count as physical S10+ acceptance.

Physical trial 1 completed 90.002821 s, 11 contacts, no captured top-level DOM.
Outcome remains unaccepted. See APP-CLICKABILITY.md for the iframe observer gap.
