# NUXEL 25000 — Liver Than Live Console++ — final report

Date: 2026-10-27 (host Europe/Amsterdam). Host: `dextronux`.
Target: Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820.
Baseline: Samsung-derived Linux **4.14.253** (unchanged; no kernel/bootloader/
modem/partition write was performed).

## 0. Prior transaction and incident resolution

The reported `a75-bridge-version-restore-apply` run was **not active** at triage:

- no `nuxel-live-deploy` / `bridge.py` host process;
- no process held `/dev/ttyACM0` (checked `/proc/*/fd`);
- `--lock-status` reported the shared flock free;
- the last related journal was
  `/tmp/nxl-apply-groups12/a75-bridge-version-restore-groups12/transaction.jsonl`,
  ending `finished`, exit 0, `DEPLOYED_UNVERIFIED` at 2026-10-26 22:31:50.

The earlier 5.5-minute observation was the old frame path: 92,944 bytes in
364.292 s (969 parts, ~255 B/s), not a live lock owner. A stale advisory sidecar
from a later read-only command was correctly classified as “NOT currently
locked … advisory/stale”; the flock, not the sidecar, remained authoritative.

## 1. Root causes found and fixed

1. **Per-file reload execution.** Reload/restart declarations were previously
   embedded in each file's install script. `install_script()` now installs only
   one file. `transaction_activation_plan()` coalesces the whole transaction:
   identical actions once, one `daemon-reload`, each service once, and services
   already named in a declared reload are not restarted again. Only an exact
   leading `systemctl daemon-reload &&|;` prefix is split; the remainder keeps
   its original shell text.
2. **Serial round-trip bottleneck.** The old frame path spends one verified
   round trip per 128-char base64 part. `block_push_bytes()` now sends bounded
   bursts (8 lines, ≤3072 bytes) in one write, then one uniquely framed
   cumulative-length ACK. The old path remains the fallback.
3. **Partial artifact could be promoted before verification.** Both
   `push_bytes()` and `block_push_bytes()` previously decoded and `mv`'d into
   place before the final hash check. They now decode to
   `<target>.nuxel-decode`, verify SHA-256, and only then atomically promote.
4. **Unsafe rollback baseline.** The first apply exposed that a long-lived
   `.nuxel-rollback` may be older than the bytes present at the start of this
   run. Each run now captures `<target>.nuxel-rollback.pre-<op-id>`; strict
   rollback prefers it, verifies the recorded previous hash, and never
   substitutes a stale historical baseline. If any restore is unverified,
   services are not restarted on a mixed file set and the verdict is
   `NEEDS_RECOVERY`.
5. **Invalid group-3 health check.** `grep -c PATTERN file1 file2` prints
   `file:count`, not literal `2`, so it could never pass. The check now uses
   single-file `grep -q` plus `systemctl show -p Environment` for both running
   services and both version files.
6. **Lock/status defects.** The shared `/tmp` lock is root-owned `0644`.
   `_flock` now opens it read-only without truncation or symlink following when
   write-open is denied; flock still excludes peers. Status is tri-state
   (`held`/`free`/`absent`/`unknown`), a dead sidecar PID is not treated as a
   stale lock while the flock is held, and an unreadable lock fails closed.
7. **Journal field collision.** The reporter overwrote a file-level `target`
   with the console target. It now preserves the file target and records the
   console separately as `console`.

## 2. Changed files

- `tools/beta/live/nuxel_live.py`
  — transaction activation planner, block protocol, verified promotion, resume,
    per-transaction backup support, lock probe/flock hardening, state machine.
- `tools/beta/live/nuxel-live-deploy.py`
  — transaction staging/activation/rollback, journal/status, operator progress,
    cancellation/reconnect handling, strict recovery/exit codes.
- `tools/beta/live/nuxel-live-bench.py` (new)
  — non-activating transfer benchmark; writes only under `/var/tmp`, verifies
    the hash, removes its artifacts.
- `tools/beta/live/a75-bridge-version-restore-manifest.json`
  — bounded health checks; 0.6.7 version pin; valid group-3 check.
- `tools/beta/live/tests/test_live_lib.py`
  — normalized service expectation.
- `tools/beta/live/tests/test_live_reload_and_transport.py`
  — 24 new deterministic cases (79 total across both suites).
- `scripts/s10plus-debug-pack/nuxel-live.sh`
  — release the shared lock through `release_console_lock()` so the advisory
    owner sidecar is cleared as well as the kernel flock.
- `docs/beta-finalization/live/TRANSACTION-RELOAD-AND-BLOCK-TRANSPORT.md`
  — operator guide, protocol, recovery and incident notes.
- This report.

## 3. Tests (exact command and result)

```text
python3 -m pytest tools/beta/live/tests/test_live_lib.py \
                 tools/beta/live/tests/test_live_reload_and_transport.py -q

79 passed in 94.02s
```

Also:

```text
python3 -m py_compile tools/beta/live/nuxel_live.py \
  tools/beta/live/nuxel-live-deploy.py tools/beta/live/nuxel-live-bench.py
# ALL_COMPILE_OK
git diff --check
# clean
```

Coverage includes: five identical reload declarations → one action; duplicate
services across groups; one transaction-level daemon-reload; unchanged/no-op
deploys with no restart; malformed reload preflight; block corruption, missing
ACK, retry exhaustion, disconnect, wrong hash, resume and wrong-prefix discard;
empty/binary/Unicode/shell-metacharacter payloads; partial-promotion prevention;
per-transaction vs stale rollback backup; lock contention, read-only/root-owned
lock, symlink, dead sidecar; cancellation; restart/health failure rollback;
failed rollback → recovery; journal target integrity and status.

## 4. Transfer measurements

Representative file: `services/nuxel-bridge/src/bridge.py`, 92,944 bytes,
SHA-256 `03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca`.

Benchmark command (writes only `/var/tmp`, never activates):

```bash
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-bench.py \
  --dev /dev/ttyACM0 --mode block --json
```

| Path | Duration | Throughput | Blocks / parts | Retries | Hash |
|---|---:|---:|---:|---:|---|
| prior frame path (2026-10-26) | 364.292 s | 255.1 B/s | 969 parts | 0 | OK |
| block 4 lines / 2048 B | 16.269 s | 5,712.8 B/s | 82 blocks / 82 ACKs | 0 | OK |
| block 8 lines / 3072 B, run 1 | 11.568 s | 8,034.6 B/s | 55 / 55 | 0 | OK |
| block 8 lines / 3072 B, run 2 | 11.540 s | 8,054.4 B/s | 55 / 55 | 0 | OK |
| block 8 lines / 3072 B, run 3 | 11.601 s | 8,012.0 B/s | 55 / 55 | 0 | OK |
| same, wicked+dialout (not root) | 11.630 s | 7,991.6 B/s | 55 / 55 | 0 | OK |

Result: ~31× throughput and 969 → 55 acknowledged round trips, with 0 retries
and exact device SHA-256 in every run. This is a measured result, not a claim.

## 5. Physical device work actually performed

### Preflight (read-only)

- `/dev/ttyACM0`, reachable; boot ID
  `96f40ab6-e1ea-4952-af24-6f7efae499d2`; kernel `4.14.253`.
- `nuxel-bridge.service` and `nuxel-http-bridge.service`: active.
- 454 MB free on `/`; all required `.nuxel-rollback` files present.
- Dry-run: 0 violations, 7 steps, 1 transaction daemon-reload, 2 planned
  bridge/http restarts (via the declared reload).

### First apply (failed safely, then recovered)

`evidence/a75-bridge-version-restore-n25000/`: installed four changed 0.6.7
assets, ran **1 daemon-reload + 1 declared reload (2 restarts)**, then the
invalid group-3 health check failed. Rollback restored the old long-lived
backups, which did not match the pre-transaction hashes, so strict verification
returned **NEEDS_RECOVERY** and deliberately did not restart services on the
mixed file set. No false success was reported. Boot ID stayed unchanged.

### Recovery apply (succeeded)

`evidence/a75-bridge-version-restore-recover-n25000/`:

- 4 changed files, 7,551 bytes, frame path 12.383 s (609.8 B/s, 81 parts,
  0 retries) because those files were below the 8 KiB block threshold;
- **1 daemon-reload, 1 declared reload, 2 service restarts, 3 health checks**;
- verdict `DEPLOYED_UNVERIFIED` (no human-visible observation claimed), exit 0.

### Post-deploy verification

- Boot ID unchanged: `96f40ab6-e1ea-4952-af24-6f7efae499d2`.
- Source/target hashes match exactly:
  - `bridge.py 03d1349444cbba752a9e9b0690a40756b177c25b1c9d235276fda1a2e29fafca`
  - `api.py 1752beb415f73b0d686d94b44fd791625f6ee7ae2dd9df20d56d62500dbd9079`
  - `nuxel-bridge.service 67ce1cea694617887d65142f35e110a705aabc31eef76430915b14f1327399a0`
  - `nuxel-http-bridge.service 97944ab8d75261cf335468efae2bb76cac4da4a84c7607b615fddc59b59e5def`
  - `/etc/nuxel/bridge-version.json` and the `/usr/share/...` copy:
    `4d9710dd847789380761c118185c84d5593ed9c829f4a852402780f5ec3876de`
  - `bridge.js 1b409e04facb7f185c7bdbf810082251fd802246444c2ca3d94f7c9877b0b75e`
- Both services active; `systemctl show -p Environment` reports
  `NUXEL_BRIDGE_VERSION=0.6.7-beta` for both.
- D-Bus Ping: `status=ok`, `version=0.6.7-beta`, `bridge_version=1`.
- HTTP `/api/v1/health`: `200`.
- Per-transaction backups contain the pre-recovery bytes; the long-lived
  `.nuxel-rollback` baselines were preserved unchanged.
- Lock released after every run; a final `nuxel-live.sh` command now clears
  both the flock and the advisory sidecar (`no recorded owner … free`).

### No-op idempotence (3/3)

`a75-noop-n25000-1`, `-2`, `-3`: each ~2.2 s, **0 changed files, 0 bytes,
0 reloads, 0 restarts, 3 health checks**, boot ID unchanged, lock released.
This is the repeated safe no-op requirement.

### Physical tests NOT performed

- No cable pull/disconnect was forced (mission safety rule). The console stayed
  connected through the bridge restarts (`reconnects: []`); reconnect and
  disconnect handling are covered by deterministic fake-transport tests, not a
  physical unplug.
- No physical Ctrl-C was used during a transfer; cancellation is covered by the
  block-boundary cancellation test. Remote commands already handed to the device
  are explicitly documented as possibly continuing.
- No kernel, bootloader, modem, partition or unrelated image was written.

## 6. Evidence locations

- Prior completed transaction:
  `/tmp/nxl-apply-groups12/a75-bridge-version-restore-groups12/`
- Failed first NUXEL-25000 apply:
  `docs/beta-finalization/live/evidence/a75-bridge-version-restore-n25000/`
- Successful recovery:
  `docs/beta-finalization/live/evidence/a75-bridge-version-restore-recover-n25000/`
- No-op cycles:
  `docs/beta-finalization/live/evidence/a75-noop-n25000-{1,2,3}/`
- Benchmarks: `/tmp/nxl25000-bench-*.json`
- Device read-only captures: `/tmp/nxl25000-{preflight,postfailure,postdeploy,final}-device.txt`

## 7. Remaining risks / operator notes

- The long-lived `.nuxel-rollback` files are historical (0.6.1/0.4.0) and should
  not be used as the rollback route for a newer transaction. Use the
  `.nuxel-rollback.pre-<op-id>` copy recorded in the evidence/journal.
- The block path was physically benchmarked on the 92,944-byte bridge payload;
  the recovery deploy’s small files correctly used the frame path. Resume was
  tested offline, not by a physical mid-transfer unplug.
- `--transaction-status` is read-only and is the first command to run when a
  deploy is interrupted.
- The lock file remains root-owned from earlier runs. Unprivileged operators in
  `dialout` can acquire it read-only; otherwise use `sudo`.

## 8. Exact safe next command

Read-only status (never opens the serial port):

```bash
python3 tools/beta/live/nuxel-live-deploy.py \
  --transaction-status docs/beta-finalization/live/evidence/a75-bridge-version-restore-recover-n25000 \
  --json
```

A further no-op verification, if desired:

```bash
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-noop-next --dev /dev/ttyACM0 --apply \
  --timeout 30 --lock-wait 30 --reconnect-timeout 180
```
