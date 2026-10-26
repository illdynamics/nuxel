# Live Console — transactional reload + block transport (NUXEL-25000)

This documents the NUXEL-25000 changes to `tools/beta/live/`. Nothing here was
validated on the phone; see the run report for what is unit-tested vs physical.

## What changed

1. **`declared_reload` is now coalesced at the group boundary.**
   - `nuxel_live.normalize_reload()`, `coalesce_reload_actions()` and
     `group_reload_plan()` turn a multi-file group's repeated reload/restart
     declarations into a deterministic plan.
   - `nuxel_live.install_script()` now ONLY stages, hash-verifies and
     atomically installs one file. It no longer runs `systemctl restart`,
     `systemctl is-active`, `systemctl daemon-reload` or `declared_reload` per
     file.
   - `nuxel-live-deploy.run_group_activation()` runs each group's coalesced
     restarts and reloads once, then runs the group health check once.
   - `nuxel-live-deploy.run_group_rollback()` restores the whole group and then
     runs the coalesced rollback actions.

2. **Faster, acknowledged bulk transfer.**
   - `nuxel_live.block_push_bytes()` writes bounded blocks of base64 lines
     (380-char lines, 24 lines per block) as a raw burst and acknowledges at
     each block boundary with a cumulative `wc -c` receipt. It rewinds to the
     last verified boundary and retries a bounded number of times before
     failing.
   - The deploy tool uses it for payloads >= 8 KiB and falls back to the
     proven `push_bytes()` frame-per-chunk path if block streaming is
     unsupported or raises `ConsoleLost`.
   - The old `push_bytes()` path is unchanged and remains the fallback.

3. **Lock ownership is unchanged and preserved.**
   - The serial lock is still one exclusive `flock` on the shared `/tmp` inode,
     held for the whole deploy. Stale-lock recovery is still the kernel's job
     (a dead process releases its flock); no code unlinks a lock file.

## Operator commands

Generate a plan/dry-run (no device write):

```bash
python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-bridge-version-restore-plan
```

Inspect the coalesced plan before applying:

```bash
cat docs/beta-finalization/live/evidence/<name>/activation-plan.json
cat docs/beta-finalization/live/evidence/<name>/scripts/000-activate.sh
```

Apply only after the prior transaction is resolved, preflight/dry-run pass,
backups exist and recovery is available:

```bash
python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-bridge-version-restore-apply \
  --apply --timeout 40 --lock-wait 40 --reconnect-timeout 180
```

## Cancellation and troubleshooting

- **Ctrl-C stops the local waiter only.** The remote install/reload may
  continue, because the device shell was already told to run it. Do not assume
  the transaction was cancelled; re-run in dry-run mode and check hashes before
  deciding to roll back.
- **A quiet but valid operation is not a stall.** Progress is acknowledged at
  block boundaries; do not kill a slow transfer automatically.
- **If the console drops** (`OSError: Device not configured`), the deploy tool
  reopens the port, re-probes and resumes. Already-installed files skip
  themselves; the rollback copy is never overwritten on resume.
- **Lock contention:** the error names the lock and device. Wait for the owner
  to finish; never remove the lock file by hand.
- **Rollback:** each target keeps `<target>.nuxel-rollback`. The tool restores
  it on failure; `docs/performance/A75/rollback-a75-bridge.sh` is the manual
  A75 rollback helper.

## Tests

```bash
cd tools/beta/live/tests
python3 -m unittest test_live_reload_and_transport
python3 -m unittest test_live_lib
python3 -m unittest test_live_deploy_plan   # 4 pre-existing coverage failures
```
