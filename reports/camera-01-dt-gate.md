# Camera Prompt 01 gate qualification — LIVE addendum (2026-11-22)

This adds the live-device qualification to the prior offline ZIP audit, without
rewriting the earlier BLOCK status.

## Live evidence now established (read-only)

- Live FDT SHA-256: `761df64ac4417f6dd5bbb468eeb6dc2305cbf45f8541d3639d5a50ca2ffc7cad`
  (full hash; matches the previously reported `761df64a` prefix).
- Board revision 26, DTBO selection index 9 (from `/proc/cmdline`).
- Model `BEYOND2LTE EUR OPEN 26` on Exynos9820; product SM-G975F.

## Gate qualification outcome

- Offline synthetic suite: 51/51 PASS (`test-camera-offline-gates.py`).
- Historical A5/A25 boot gates: SKIP-PREREQ (exit 3) — correctly not counted as pass.
- Real (live-image) golden no-op: **BLOCKED** — owner-signed manifest, private
  current BOOT/DTB/DTBO images and trusted signing key are absent from this host.

The revised GPIO overlap exception remains hash-pinned (no Samsung pin waiver), and
the separate-DTB/DTBO path remains evidence-bound. Both were source-reviewed; neither
was bypassed. The real merged-FDT `camera-dt-gate.py --merged --golden-merged ...`
run could not be executed because no private golden merged FDT copy is present on the
host (only the live `/sys/firmware/fdt` on-device, which was hash-verified but not
pulled into an immutable off-device file in this session).

No on-device writes, reboots, STREAMON, or recovery entries occurred.
