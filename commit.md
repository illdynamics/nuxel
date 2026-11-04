dev headers on macOS); the release CI builds it.

**Two things still open**
1. `services/nuxel-performance/` and `configs/nuxel/performance/journald.conf` are committed as source but **not wired into** `images/s10plus/build-phone-rootfs-inside-fedora.sh`, so they won't land in the image yet.
2. The idle-wakeup reductions have not been measured on the physical handset.

Want me to add the rootfs install wiring (service enablement + journald drop-in) as a follow-up PR?
Merged via **[PR #27](https://github.com/illdynamics/nuxel/pull/27)**.

**What happened**
- Found uncommitted work on the already-merged `fix/kernel-parity-gate-invocation` branch, with `main` 6 commits ahead.    
- Branched `perf/idle-wakeup-reduction` from current `origin/main`, staged all 11 modified + 3 untracked paths (22 files, +319/−49), and committed as `794c879`.
- Opened, verified `MERGEABLE`/`CLEAN`, and merged with a merge commit `4140450`. `main` release workflow ran and succeeded; build/publish jobs skipped because `VERSION` is unchanged from the already-tagged `v0.7.6-beta`.
- Cleaned up the temporary baseline worktree; local `main` is now up to date.

**Verification**
- Affected suites (`pwnage37000/49000/46000/50000/52000`): 180 passed, 8 failed.
- Same suites on untouched `origin/main`: 179 passed, 9 failed — the 8 failures pre-exist; this branch also fixes the stale `test_cache_version_bumped` assertion.
- `sh -n` on the new perf script and `py_compile` on `nuxel-orientationd` pass. The C host wasn't compiled locally (no GTK dev headers on macOS); the release CI builds it.

**Two things still open**
1. `services/nuxel-performance/` and `configs/nuxel/performance/journald.conf` are committed as source but **not wired into** `images/s10plus/build-phone-rootfs-inside-fedora.sh`, so they won't land in the image yet.
2. The idle-wakeup reductions have not been measured on the physical handset.

Want me to add the rootfs install wiring (service enablement + journald drop-in) as a follow-up PR?
tokens used
1,341,321
[codeseeq] stopping owned bridge process (pid=3669)

## PWNAGE-58000 follow-up (shipped with this branch)

- **Wired into the rootfs builder:** `nuxel-perf-tune.service`, its script, the
  journald drop-in at `/etc/systemd/journald.conf.d/50-nuxel-performance.conf`,
  and the `multi-user.target.wants` enablement. A fresh image now contains the
  change that `794c879` committed as source only.
- **Verifier contracts:** `tools/s10plus/verify-fedora-phone-rootfs.py` now
  requires the exact installed paths and byte parity for all four assets, and
  `tools/s10plus/a33/verify-service-graph.py` tracks the new unit.
- **Prompts:** `full-pwnage-58000.md` (full measurement/deployment brief) and
  `pwnage-58000.md` (kickstarter) were added at the repository root.
- **Tests:** `tests/pwnage58000/` guards the builder wiring, unit safety,
  journald bounds, tuning-script scope and prompt honesty. Registered as
  `U-pwnage58000-idle-truth` in `tools/beta/run-all-tests.sh`.
- **Still open:** the physical handset measurement itself. PWNAGE-58000 must
  produce the real baseline/candidate evidence; no battery or wakeup reduction
  is claimed by this branch.
