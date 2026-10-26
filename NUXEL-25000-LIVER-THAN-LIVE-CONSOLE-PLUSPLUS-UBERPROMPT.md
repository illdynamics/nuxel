# 🐧 NUXEL 25000 — LIVER THAN LIVE CONSOLE++
## Operation: Mature Console, Faster Transport, Transactional Deployments, No Self-Inflicted Lockouts

**Mission ID:** NUXEL-25000  
**Target:** Nuxel on Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820.  
**Primary outcome:** Make the existing USB Live Console a mature, observable, resilient, faster development/deployment interface while preserving the known-good recovery path and the currently bootable phone.  
**Non-goal:** This is not permission to blindly rewrite the console, wipe the phone, or flash a new kernel.

---

## 0. Incident context and mandatory first action

The operator supplied this incident evidence:

- Source hashes reportedly match expected values.
- A subtle `declared_reload` issue exists for group 3: the install script executes the declaration per file. If five files each declare the same reload, it may run `systemctl daemon-reload` and restart services five times.
- A deploy was started using:

```bash
python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/a75-bridge-version-restore-manifest.json \
  --name a75-bridge-version-restore-apply \
  --apply \
  --timeout 40 \
  --lock-wait 40 \
  --reconnect-timeout 180
```

- The deployment was reported still running after about 5.5 minutes.
- `services/nuxel-bridge/src/bridge.py` was described as approximately 92 KB; a prior transfer was estimated at around 964 base64 parts.
- The actual transport may batch multiple lines per write. Do not assume one round trip per part until code and telemetry prove it.
- The deployment tool appears to hold the serialized console lock for the whole run. Other `nuxel-live.sh` commands may block while it owns the lock.
- The supplied log ends before the final outcome. We do not know whether that deployment succeeded, failed, rolled back, timed out, or remains active.

### First: establish state safely

Before editing deployment code, acquiring/releasing locks, restarting services, or deploying:

1. Inspect the current repository, `git status`, relevant scripts/manifests/tests, logs and the current deploy journal.
2. Determine whether the prior `a75-bridge-version-restore-apply` process is still active or has completed. Use host-side process/status inspection that does not contend for the serial console.
3. If it is active, **do not launch a second deploy, kill it, remove its lock, or issue another serial command**. Establish actual progress and let it finish unless concrete evidence proves it is deadlocked or destructive.
4. If completed, collect the final result, rollback result, source/device hashes, bridge service state, console reconnect state and phone boot ID before planning another mutation.
5. Never call a lock stale based only on age. Verify its owner/process identity and operation ID. Never remove an active lock as a shortcut.
6. Preserve the known-good deployed artifacts and physical recovery route.
7. If the phone is unavailable, perform repository analysis and tests only, clearly marking physical tests as **not run**. Never claim the device is fixed without device evidence.

The first deliverable is a short baseline report: confirmed facts, hypotheses, unknowns, process/lock status, and the next safe step. Do not start a new deployment while the previous transaction is ambiguous.

---

## 1. Mission objectives and priorities

### P0 — Correct transaction behavior
- Coalesce duplicate `declared_reload` actions across a deployment group/transaction.
- Install and verify all relevant files before restarting services.
- Run `systemctl daemon-reload` only when required, and restart each affected service at most once per transaction unless a documented dependency requires otherwise.
- Apply the same coalescing rules during rollback.
- Never report success if a required reload, restart or health check failed.

### P0 — Reliable, faster transport
- Trace the real host-to-phone transport and measure throughput, payload size, block size, round trips, ACK frequency, retry count, and time spent in transfer versus install/restart/reconnect.
- Replace avoidable per-chunk round trips with bounded, acknowledged block transfers if supported by the current protocol.
- Add robust framing, end-to-end integrity checks, bounded retries and safe resume at verified boundaries where feasible.
- Keep a single owner for the physical serial/USB stream. Do not parallelize writes to one raw serial connection unless explicit framing/multiplexing is implemented and tested.

### P1 — Operator-grade console UX
- Explicit state/progress, useful errors, logs and final summaries.
- Show confirmed bytes/blocks, files completed, elapsed time, measured throughput, retries and last meaningful progress.
- Distinguish slow progress from a stall. Do not kill a quiet but valid operation automatically.
- Define safe Ctrl-C/cancellation behavior and clearly distinguish stopping the local waiter from cancelling a remote transaction.

### P1 — Predictable deployment and recovery
- Preflight, dry-run, stage, verify, activate, health-check, commit or rollback.
- Journal every important transaction transition.
- Preserve a known-good version and report exactly what is active after failure.
- Make lock ownership, wait behavior, stale-lock recovery and helper lock re-entrancy well-defined.

---

## 2. Inspect the actual implementation before editing

Confirm actual paths and current call chains; do not assume line numbers or behavior. Inspect at least:

- `tools/beta/live/nuxel-live-deploy.py`
- `tools/beta/live/a75-bridge-version-restore-manifest.json`
- install-script generation and every use of `declared_reload`
- `nuxel-live.sh` and the transport it invokes
- `nuxel_live.py`, including `push_bytes` and block/chunk verification
- `nuxel-push.py`, if present
- serial-console lock acquisition/release and stale-lock logic
- bridge service units, restart/activation logic and health checks
- manifest schema, hash verification, backups, rollback and deploy journals
- tests/fixtures for transport, service restart and live deployment.

Trace this end-to-end:

`CLI → manifest validation → plan → lock → preflight → transfer/stage → integrity verification → activation → declared reload → service health → commit/rollback → lock release → final report`.

Read complete relevant functions and their call sites. Do not rewrite the entire console just because a local fix is easier to understand as a rewrite. Prefer narrow, backward-compatible changes with tests.

---

## 3. Fix `declared_reload` at the transaction boundary

### Required behavior

1. Determine the manifest's intended semantics for `declared_reload`. Do not infer from one call site alone.
2. Collect all declared actions during preflight.
3. Normalize and deduplicate only semantically identical actions. Preserve ordering and dependencies; do not use fragile shell-string rewriting to erase differences.
4. Finish installing and verifying the complete group before reload/restart.
5. If systemd unit files changed, execute one `daemon-reload` for the transaction.
6. Restart each affected service once in deterministic dependency order.
7. If no relevant file changed, skip unnecessary restart/reload work when the manifest semantics permit it.
8. Record planned and executed actions explicitly, with counts in the final report.
9. If reload/restart fails, do not commit. Enter the defined recovery path and verify the resulting state.
10. Apply the same coalescing behavior to rollback.
11. Preserve existing manifests and hash expectations. If a schema migration is truly necessary, make it backward-compatible and document it.
12. Dry-run must show the same action plan the actual deploy will execute.

### Required tests

- Five files with the same reload declaration execute one normalized action, not five.
- Multiple distinct services each restart once in deterministic order.
- Changed unit file: one `daemon-reload`; unchanged units: no unnecessary reload.
- An unchanged payload does not cause needless rewrite/restart where safe hash-based skipping is supported.
- A malformed action fails during preflight before target mutation.
- Failure before activation leaves active files unchanged.
- Activation/health failure triggers recovery and a truthful final status.
- Rollback reloads/restarts are coalesced.
- Re-running an already successful manifest is idempotent and avoids needless restarts.

---

## 4. Speed up transfer safely: measure first

The `92 KB / 964 parts` observation is useful but not a benchmark. First establish whether the tool writes each part individually or batches many parts per transport write.

Instrument:
- source size and SHA-256;
- encoded payload size;
- actual bytes per transport write;
- number of writes/round trips;
- block size and acknowledgement frequency;
- block latency, throughput and retries;
- time spent transferring, verifying, installing, restarting, reconnecting and health-checking.

### Preferred transport improvements

1. **Bounded block writes:** batch multiple chunks per write, using measured safe limits for the actual transport and device buffers.
2. **Acknowledgement at block boundaries:** sequence number or unambiguous offset, expected length and integrity check. Never treat silence as success.
3. **Explicit framing:** prevent echoed commands, shell output, prompts or partial lines from being mistaken for payload/ACKs.
4. **End-to-end integrity:** verify reconstructed target byte length and cryptographic hash before activation.
5. **Safe staging:** write into a transaction-specific temporary file, close/flush, verify, set expected permissions, then atomically promote where supported.
6. **Bounded retries:** retry transient errors with a finite retry budget and backoff; report the exact block and failure when exhausted.
7. **Resume only when safe:** resume at a verified block boundary only when transaction ID, destination identity, expected hash and offset match. Otherwise discard the incomplete temporary artifact and start over.
8. **Avoid excessive shell overhead:** use a carefully framed streaming receiver if supported instead of hundreds of separate shell commands. Do not pass giant base64 blobs as command-line arguments.
9. **Bound memory:** stream the file rather than retaining many full copies in memory.
10. **Fallback:** if the target shell or transport cannot safely support block streaming, keep the reliable existing method as a fallback. Do not replace a proven path with an untested protocol.

### Serialization rule

The physical serial/USB connection is an ordered byte stream. Do not issue concurrent writes from multiple processes. Parallel CPU-only local work (hashing, manifest planning) is fine; writes and protocol commands to the same stream must have one owner unless a real multiplexing protocol exists and has tests.

### Performance acceptance

Benchmark the same representative file before and after under comparable conditions. Report measured bytes/sec, write/round-trip count, retries and duration. Demonstrate real improvement without invented speedup claims. Verify the target hash exactly matches the expected hash. Test disconnect, corrupted block, delayed/missing ACK, retry exhaustion, wrong hash and resume. Progress reporting itself must not materially slow transfers.

---

## 5. Lock ownership, waiting and cancellation

The transport lock may need to cover a complete transfer to prevent interleaving; do not shorten it unsafely just to make it look efficient.

- Establish one clear owner for the physical transport lock. Helpers must not accidentally reacquire a non-reentrant lock held by their caller.
- Record owner PID, host/process identity where appropriate, operation ID, acquisition time and purpose.
- Release locks on all normal/error paths (`finally` or equivalent).
- Handle crashes through validated stale-lock recovery. Do not remove locks based only on age.
- Bound lock waits and report the known owner and operation ID.
- If a deploy waits, display elapsed time and owner details when available.
- Provide a local status view that does not touch the locked serial stream, if the journal/status files support it.
- Do not automatically launch another deploy when the first seems slow.
- Ctrl-C must have defined semantics: cooperative cancellation at a safe boundary if supported; otherwise explain that the remote transaction may continue. Never claim it was cancelled merely because local polling stopped.
- Never release the physical lock between raw writes if another process could corrupt the active protocol stream.

Test two callers contending for the lock, timeout behavior, crash recovery, live-lock protection, helper re-entrancy, and cancellation at preparation/transfer/activation/reconnect stages.

---

## 6. Mature Live Console UX

Improve the existing CLI/interface rather than building a disconnected replacement. Use an explicit state machine or the project's equivalent:

`DISCONNECTED`, `CONNECTING`, `CONNECTED_IDLE`, `COMMAND_RUNNING`, `TRANSFER_PREPARING`, `TRANSFER_RUNNING`, `TRANSFER_VERIFYING`, `DEPLOY_STAGING`, `DEPLOY_ACTIVATING`, `SERVICE_RESTARTING`, `RECONNECTING`, `HEALTH_CHECK`, `ROLLING_BACK`, `SUCCEEDED`, `FAILED`, `CANCELLED`, `NEEDS_RECOVERY`.

Validate transitions. A failed reconnect must not display `CONNECTED`; failed health checks must not display `SUCCEEDED`.

For long operations show:
- operation ID and target;
- current phase/step;
- file count and acknowledged byte/block progress;
- elapsed time and measured throughput;
- retries and last successful acknowledgement;
- time since last actual progress;
- last useful device output;
- service/reconnect status when known.

Use an in-place progress line where supported and periodic summaries for redirected/non-interactive logs. Do not print every tiny chunk by default. Offer verbose diagnostics with secrets redacted. Progress must reflect acknowledged work, not merely data queued on the host.

Use consistent exit codes for validation, transport, device, rollback and ambiguous recovery failures. Logs should be structured (JSONL or the project's current format) and include timestamp, operation ID, step, target, elapsed time, attempt, acknowledged bytes, error category and recovery action. Never log Wi-Fi credentials, tokens, private keys or other secrets.

---

## 7. Bridge restart and reconnect must not cut off recovery

Establish which component owns the physical serial stream and which component provides the bridge/API; do not assume they are the same.

- Stage and verify all files and save rollback metadata before restart.
- Restart `nuxel-bridge` only after the transaction is ready and only once.
- Plan for expected connection loss during restart.
- Use bounded reconnect retries and a real health check, not merely “process exists.”
- Distinguish expected bridge disconnect/reconnect from an actual phone reboot.
- Record boot ID before and after; a service restart must not be reported as a phone reboot.
- If reconnect fails, do not enter an unbounded restart loop. Stop after the retry budget and provide a recovery path.
- Verify the deployed bridge version/hash and health endpoint/method after reconnect.
- Keep USB Live Console/recovery available. Do not flash the kernel, bootloader, modem or unrelated partitions.

---

## 8. Transaction journal, atomic activation and rollback

Implement or strengthen this transaction sequence:

1. Validate manifest schema and paths.
2. Reject path traversal and unexpected symlinks.
3. Verify source hashes, permissions, capacity and required device capabilities.
4. Produce a deterministic dry-run plan with coalesced reload actions.
5. Acquire the transport lock.
6. Create a journal and record current active versions/hashes.
7. Stage changed files in temporary locations.
8. Verify every staged file's byte count and hash.
9. Prepare activation and rollback metadata.
10. Activate atomically where supported.
11. Run the coalesced reload/restart plan.
12. Reconnect and run service/functional health checks.
13. Commit only after all required checks pass.
14. Otherwise restore known-good artifacts, coalesce rollback actions, verify recovery and report the final state.
15. Release the lock and write a final report.

Journal states should distinguish at least: `planned`, `staging`, `staged`, `verified`, `activating`, `activated`, `health_check`, `committed`, `rolling_back`, `rolled_back`, `recovery_required`.

Never infer commit because a command was sent. Record acknowledgements and postconditions. Keep source hashes separate from target hashes; never rewrite expected manifest hashes to force success. Do not activate a file whose target hash fails verification.

Inject failures at each transaction boundary, including host process exit. After restart, the tool must be able to inspect the journal and determine whether to resume, roll back or require operator action.

---

## 9. Required tests before a real-device deployment

Use deterministic fake transports and mocked service actions for normal CI.

### Reload/manifest
- Five identical declarations → one action.
- Multiple distinct services → once each in deterministic order.
- Unit file changed → one `daemon-reload`.
- No relevant change → no unnecessary restart.
- Malformed declaration → fail preflight before mutation.
- Reload/restart failure → no false commit.
- Rollback actions coalesced.
- Dry-run plan equals executed action plan.

### Transfer
- Large file, binary content, Unicode, shell metacharacters and empty file if allowed.
- Exact block ordering/framing.
- Partial/corrupt block, missing/delayed ACK, duplicate ACK and retry.
- Disconnect mid-transfer.
- Wrong expected hash.
- Resume only at verified boundary and reject wrong transaction ID.
- Temporary file never activates before full hash verification.
- Payload is never executed as shell code.

### Lock/cancellation
- Two callers contend.
- Wait timeout includes actionable owner information.
- Process exits while holding lock.
- Live lock is not classified stale.
- Nested helper behavior does not deadlock.
- Ctrl-C at each phase has documented behavior.
- No second writer interleaves with active transfer.

### Failure injection/regression
- Staging failure, disk full, service restart failure, bridge drops/returns, bridge never returns, unexpected device reboot, unhealthy service, rollback failure, host exit at each stage.
- Existing tests still run; do not weaken assertions just to pass.
- Report exact commands and outcomes.

---

## 10. Safe device validation

Only test the phone if it is safely reachable and the previous transaction has been resolved.

Before deploy:
- confirm target identity;
- record boot ID, kernel version, bridge service state, console status and current hashes;
- confirm free space for staged files and backup;
- ensure physical recovery remains available;
- ensure no prior deploy is active.

After deploy:
- verify source/target hashes and intended bridge version;
- verify service health and console commands end-to-end;
- verify reconnect after the planned bridge restart;
- verify boot ID did not change unexpectedly;
- run at least three safe deploy/no-op cycles if practical;
- compare transfer duration, round trips and service downtime;
- verify a multi-file group does not trigger repeated restarts;
- verify locks are released after success and failure.

Do not yank the cable during an active write or activation. Do not use a USB disconnect as a cancellation mechanism.

If device access is unavailable, label hardware tests **NOT RUN**. Do not imply physical success based on unit tests.

---

## 11. Scope boundaries

Do not:
- flash a kernel, bootloader, modem or unrelated partition;
- wipe/reset the phone or erase user data;
- remove Wi-Fi profiles or change unrelated radio settings;
- weaken filesystem, D-Bus, service or integrity protections;
- disable hashes, rollback or health checks;
- kill a possibly active deployment because it is slow;
- remove a lock while its owner may still be active;
- run multiple deployment agents against the same phone;
- introduce a new protocol without a tested fallback;
- rewrite unrelated Wi-Fi/Bluetooth/GPS/UI code as collateral.

Keep compatibility with the existing Fedora-based ARM64 userspace and Samsung-derived Linux 4.14 baseline.

---

## 12. Required deliverables

Make actual reviewable repository changes and tests, not just a plan. Deliver:

1. Root-cause report: confirmed facts, hypotheses and evidence.
2. Fix for transaction-level `declared_reload` coalescing.
3. Transport reliability/performance improvement with measured before/after results.
4. Lock ownership, status and recovery improvements where needed.
5. Mature progress/state/logging/cancellation behavior.
6. Transaction journal, activation and rollback improvements where needed.
7. Documentation for normal commands, cancellation, troubleshooting and recovery.
8. Test report with exact commands and results.
9. Device report with target identity, boot IDs, hashes, service health and physical checks—or an explicit statement that device validation was unavailable.
10. Diff summary and changed file list.
11. One exact safe next command after the previous transaction is resolved.

If an existing mechanism already solves a requirement, do not duplicate it: cite the implementation and test it. If an optimization is unsafe or unsupported, retain the fallback and explain the limitation.

---

## 13. Execution phases

**A — Triage:** identify active deploy, lock owner, journal and device/service state. No new deploy.

**B — Baseline:** trace `declared_reload`; trace transfer path; run existing tests and non-mutating benchmark.

**C — Design:** choose the smallest safe transaction boundary and transfer improvement; document restart/reconnect behavior.

**D — Implement:** add tests for reload coalescing, framing, hashes and lock behavior, then implement.

**E — Local verification:** run relevant tests, lint/type checks and failure-injection tests using fake transport.

**F — Device deployment:** only when the previous transaction is resolved, preflight and dry-run pass, diff is reviewed, backups exist and recovery is available.

**G — Verify:** hashes, service health, reconnect, boot ID, repeated no-op cycles, measured speed and lock cleanup.

**H — Report:** list what changed, measured gains, tests run, physical tests run/not run, remaining risks and the next safe action.

Do not stop after writing a plan if safe repository changes can be made. Do not rush into device deployment while the prior transaction's state is ambiguous.

---

## 14. Definition of DONE

- [ ] Prior deployment is safely resolved or explicitly reported as still active.
- [ ] One owner at a time controls the physical serial stream.
- [ ] Identical `declared_reload` actions are coalesced per transaction.
- [ ] The five-file case does not restart `nuxel-bridge` five times.
- [ ] Failed restart/health checks cannot be reported as success.
- [ ] Transfer speed and round trips are measured before and after.
- [ ] Target hashes match before activation; partial files never become active.
- [ ] Lock contention, stale-lock recovery and cancellation have tests.
- [ ] Progress reflects acknowledged work and distinguishes slow from stalled.
- [ ] Reconnect and rollback paths are tested.
- [ ] Relevant existing regression tests pass or failures are explained.
- [ ] Boot ID remains stable through an intended service restart test.
- [ ] Repeated safe deploy/no-op cycles pass if hardware access permits.
- [ ] Recovery path remains usable; no unrelated partition/kernel changes occurred.
- [ ] Final report clearly separates unit-test evidence from physical-device evidence.

## Final operator principle

Make Live Console feel like a proper engineering instrument: predictable, observable, quick when the transport allows it, honest when the device is slow, and recoverable when anything goes wrong.

**Speed without integrity is corruption. Parallelism without transport framing is a race. A restart without recovery is self-lockout. A progress bar without acknowledgements is theatre.**

🐧 **NUXEL 25000: LIVER THAN LIVE — fewer pointless restarts, fewer serial round trips, zero fake success, and no penguin left behind.**
