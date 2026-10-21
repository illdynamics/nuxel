# NUXEL A49 — Phase 0 baseline + recovery

## Baseline facts (recorded before any change)

* `git status`: clean working tree.
* Branch: `nuxel/bootscreens-orientation-big-screen`, HEAD `9229908`
  ("bootscreens fixed"), tracking `origin/nuxel/bootscreens-orientation-big-screen`.
* Lineage: `main` → v0.6.3-beta → bootscreens work. No WIP to preserve beyond
  this; no commits were reset or rewritten (only new commits appended).

## Device (from archived evidence, NOT a live probe this session)

* Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, vendor Linux
  4.14.253, Fedora 43 ARM64, Phoc/Phosh/Wayland, WebKitGTK.
* The A32/A33 evidence shows the panel is S6E3HA9 (3040x1440, portrait scanout
  1440x3040), the hub input devices are `grip_sensor`/`ssp_context`/`hall`, and
  Wi-Fi is vendor `bcmdhd`. None of this was re-probed live in this session.

## Scope of this mission (files touched)

Only userspace/config/WebKit JS. **No** boot, recovery, kernel, device-tree,
boot partition, Type-C mux/PMIC, or initramfs changes. See the commit list in
FINAL-REPORT.md. SHA-256 of every new/changed file is in git and reproduced in
the commit "4 commits" record; request `git diff --name-only 9229908..HEAD` and
`shasum -a 256` to re-verify.

## Recovery

* Repository rollback: `git reset --hard 9229908` (host only).
* The orientation daemon writes only `/var/lib/nuxel/orientation/state.json`;
  delete that file to return to the `portrait` default.
* No service was installed/enabled on any device this session; nothing to
  uninstall. A future staged deploy must use the A49 manifest and
  `tools/s10plus/a33/nuxel-rollback-home.sh`, and must never touch boot chain.

## PASS / PARTIAL / BLOCKED ledger (this session)

| Area | Ledger | Evidence |
|---|---|---|
| Phase 0 baseline | PASS (repo) | clean tree at 9229908 |
| Phase 1 sensor bring-up | PARTIAL | adapters + diag implemented; readings UNVERIFIED |
| Phase 2 seven modes | PASS (offline) | 39 pytest tests |
| Phase 3 compositor/touch | BLOCKED | Phoc transform+calibration need the device |
| Phase 4 QS/Settings/persistence | PARTIAL | implemented+offline-tested; device deploy unproven |
| Phase 5 USB-C/HDMI | PARTIAL | read-only probe; physical output UNVERIFIED |
| Phase 6 wireless cast | PARTIAL | read-only probe; real pipeline UNVERIFIED |
| Phase 7 keyboard haptics | PARTIAL | settings+schema+route; felt buzz UNVERIFIED |
| Phase 8 resource/privacy/power | PARTIAL | no regression surface; no device measurement |
| Phase 9 tests | PASS (offline) | 46 new tests, 0 failures |
| Phase 10 staged deploy | NOT RUN | no live device console |
| Phase 11 owner acceptance | NOT RUN | requires owner + phone |

Pre-existing (unrelated) failing test noted: `nuxel-keyboard-apply.sh` selftest
reports `3/23 checks passed` (its own applier fixture verdicts) — present before
this mission and outside its scope; recorded here for transparency.
