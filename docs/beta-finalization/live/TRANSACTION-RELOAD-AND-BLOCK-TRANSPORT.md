# Live Console — transactional reload + acknowledged block transport (NUXEL-25000)

This is the operator guide for the NUXEL-25000 changes in `tools/beta/live/`.
It covers the transaction boundary, the block protocol, lock/status commands,
cancellation, rollback and the measured transfer result.

## 1. Transaction boundary

A deploy run is one transaction:

1. validate the whole manifest and guard every path;
2. acquire the shared console flock;
3. record boot id, previous hashes and a JSONL journal;
4. stage, hash-verify and atomically install **every selected file**, capturing
   the bytes actually present at the start of this run in
   `<target>.nuxel-rollback.pre-<op-id>` (the long-lived `.nuxel-rollback`
   baseline is preserved separately and created only when absent);
5. build one coalesced activation plan;
6. run one `daemon-reload` (if any unit visibility changed), declared reload
   actions, and each affected service restart **once**;
7. run each group health check;
8. commit, or restore every changed target and re-run the coalesced rollback.

`nuxel_live.transaction_activation_plan()` implements step 5. It:

- normalizes whitespace/separators only for deduplication, never rewrites the
  executed command;
- deduplicates identical declared actions across the whole transaction;
- splits **only** an exact leading `systemctl daemon-reload &&`/`;` prefix so
  several unit-file groups share one daemon-reload (the remainder is preserved
  verbatim);
- deduplicates service names (including `unit` vs `unit.service`);
- removes a service from the independent restart list when an explicit
  `systemctl restart|try-restart|reload-or-restart` in a declared action already
  names it.

`install_script()` only stages, verifies and installs one file. It never runs a
service restart, health check or declared reload. Consequently five files in a
group (or a transaction) cannot restart `nuxel-bridge` five times.

An unchanged target is detected by its device hash and skipped. A no-op re-run
therefore performs zero writes, zero reloads and zero restarts; it still runs
the non-mutating group health checks and reports `no_op: true`.

## 2. Block transfer protocol

The fast path is `nuxel_live.block_push_bytes()`:

- 380 base64 chars per line (the measured safe console line size);
- 8 lines per burst, additionally capped at 3072 payload bytes, under the
  4 KiB N_TTY input ring;
- each burst is **one** `Console.send()` call, which loops over partial writes;
- each burst ends with a uniquely framed acknowledgement:
  `@@AB<rid>:<block>:<cumulative-length>@@`;
- a missing/short/wrong ACK rewinds to the last verified block boundary and
  retries with a finite budget (default 5);
- the completed base64 file is length-checked, decoded to
  `<target>.nuxel-decode`, SHA-256-verified, and only then atomically moved into
  place. A partial or corrupt file can never become the staged artifact;
- same-target + same-expected-SHA part files may resume only after the existing
  prefix's device-side SHA-256 matches the host's expected prefix. A wrong or
  oversized prefix is discarded, never appended;
- on a transport failure the deploy tool removes the block part and falls back
  to the proven frame-per-128-char `push_bytes()` path.

The old frame path remains the fallback. It now also verifies the decoded temp
file before promotion and reports acknowledged part progress.

### Measured result (physical S10+, 2026-10-27)

Representative file: `services/nuxel-bridge/src/bridge.py`, 92,944 bytes,
SHA-256 `03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca`.

| Path | Duration | Throughput | Round trips / parts | Retries | Hash |
|---|---:|---:|---:|---:|---|
| prior frame path (2026-10-26) | 364.292 s | 255.1 B/s | 969 | 0 | OK |
| block, 8 lines / 3072 B (3 runs) | 11.540–11.601 s | 8012–8054 B/s | 55 blocks, 55 ACKs | 0 | OK |
| block under wicked+dialout | 11.630 s | 7991.6 B/s | 55 blocks, 55 ACKs | 0 | OK |

This is ~31× the measured frame throughput and 969 → 55 acknowledged round
trips. The numbers are from the benchmark below, not inferred.

The recovery deploy (4 small changed files, 7,551 bytes total) used the frame
path because each file was below 8 KiB: 12.383 s, 609.8 B/s, 81 parts, 0 retries.
It executed **1 daemon-reload, 1 declared reload, 2 service restarts and 3
health checks**. Three subsequent no-op deploys each took ~2.2 s with 0 bytes,
0 reloads and 0 restarts.

## 3. Lock ownership and status

All tools use one shared inode: `/tmp/nuxel-live.<sanitised-dev>.lock`
(overridable with `NUXEL_LIVE_LOCK`). The flock covers the whole serialized
transaction. The lock file is never deleted to "recover" it.

- `_flock` uses `O_NOFOLLOW|O_CLOEXEC`, never truncates, and falls back to a
  read-only open of the **same inode** when another user owns a protected
  `/tmp` lock. Linux supports `flock(LOCK_EX)` on that read-only fd.
- The owner sidecar (`<lock>.owner.json`) records pid, process start ticks, host,
  operation id and acquisition time. It is advisory; the flock is authoritative.
- A dead recorded pid with a still-held flock is reported as **locked**, not
  stale.
- An unreadable lock is `UNKNOWN`, not "free" (fail closed).
- A symlink lock fails closed.
- `nuxel-live.sh` releases through `release_console_lock()`, clearing its own
  advisory sidecar as well as the flock.

Non-mutating host status:

```bash
python3 tools/beta/live/nuxel-live-deploy.py --lock-status --dev /dev/ttyACM0
python3 tools/beta/live/nuxel-live-deploy.py --transaction-status <evidence-dir>
```

`--transaction-status` reports `COMPLETE`, `ACTIVE`, `INCOMPLETE` or
`NEEDS_RECOVERY`, the last journal event, changed targets, lock state and a
concrete next action. It never opens the serial port.

## 4. Commands

Plan/dry-run (no device write):

```bash
python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-plan
```

Apply only after the prior transaction is resolved, the diff is reviewed, the
dry-run passes and a rollback route exists:

```bash
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-bridge-version-restore-n25000 \
  --dev /dev/ttyACM0 --apply --timeout 30 --lock-wait 30 \
  --reconnect-timeout 180 \
  --operation-id a75-bridge-version-restore-n25000
```

Benchmark the same file without activating anything (writes only under
`/var/tmp`, verifies the hash, removes its artifacts):

```bash
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-bench.py \
  --dev /dev/ttyACM0 --mode block --json
```

Use `--mode frame` for the conservative path, or `--mode both` for a paired
measurement. `--block-lines`, `--block-bytes`, `--chunk` and `--no-resume` are
available for bounded tuning.

## 5. Cancellation

`Ctrl-C` is cooperative:

- it sets a cancellation flag checked at chunk/block/step boundaries;
- the physical lock is not released mid-frame;
- an in-flight block is not promoted;
- the tool restores every changed target, runs the coalesced rollback actions
  and reports `CANCELLED` (exit 130) or `NEEDS_RECOVERY` (exit 6);
- a remote command already handed to the device may still finish. The tool
  never claims a remote cancel it cannot prove.

Do not pull the USB cable as a cancellation mechanism.

## 6. Failure and rollback

- A failed stage leaves the active target unchanged and triggers transaction
  rollback.
- A restart or health-check failure triggers strict rollback.
- Strict rollback restores the **per-transaction** backup
  `<target>.nuxel-rollback.pre-<op-id>`, verifies the recorded previous hash (or
  proves a newly-created file absent), then runs the coalesced rollback
  reload/restart plan and health checks. It never substitutes a stale historical
  `.nuxel-rollback` baseline for the bytes this transaction actually saw.
- If any file restore cannot be verified, services are **not** restarted on a
  mixed file set; the verdict is `NEEDS_RECOVERY` (exit 6).
- Exit codes: 2 validation/CLI, 3 console unavailable, 4 plan violation,
  5 failed but rolled back, 6 recovery required, 130 cancelled.

The install script preserves the first `.nuxel-rollback` copy across re-runs.
The manual A75 rollback helper remains
`docs/performance/A75/rollback-a75-bridge.sh`.

## 7. Tests

```bash
python3 -m pytest tools/beta/live/tests/test_live_lib.py \
                 tools/beta/live/tests/test_live_reload_and_transport.py -q
```

79 deterministic tests pass. They cover: five identical reload declarations →
one action; transaction-level
daemon-reload/restart dedupe; unit-file split; unchanged/no-op deploys; malformed
reload preflight; block framing, corruption, disconnect, retry exhaustion, wrong
hash, resume and wrong-prefix discard; empty/binary/Unicode/shell-metacharacter
payloads; partial-promotion prevention; per-transaction backup vs stale baseline;
lock contention, read-only/root-owned lock, symlink and dead-sidecar handling;
cancellation; restart/health failure rollback; failed rollback → recovery;
journal field integrity and journal status.

Offline tests are not device evidence. Physical results are recorded in
`NUXEL-25000-CONSOLE-REPORT.md`.

## 8. Incident and recovery note (2026-10-27)

The first NUXEL-25000 apply staged and installed all four changed 0.6.7 assets,
daemon-reloaded and restarted both bridge services, then failed its group-3
health check. The check used `grep -c PATTERN file1 file2`, which prints
`file:count` lines rather than the literal count, so it could never pass.

Rollback then restored the long-lived `.nuxel-rollback` files, which were older
than the bytes present before the transaction; strict verification correctly
reported `NEEDS_RECOVERY` and deliberately did not restart services on the mixed
file set. The running services still reported 0.6.7 while disk held 0.6.1/0.4.0
assets.

Recovery changes:

- the group-3 health check now uses single-file `grep -q` checks plus
  `systemctl show -p Environment` for both running services;
- every transaction captures its own pre-change backup and rollback prefers it;
- the recovery deploy completed 0.6.7, and three no-op cycles confirmed the
  final state.

The failed transaction remains in
`evidence/a75-bridge-version-restore-n25000/` as evidence; successful recovery
is in `evidence/a75-bridge-version-restore-recover-n25000/`.
