# Nuxel — Prompt for P11: Durable evidence and truthful checkpoint

> **Purpose of this file.** This Markdown is a *prompt for a future implementation session*, authored by the prompt-factory. It is **not** an implementation, and it must not be executed as one. The future agent that consumes it owns the work: audit, implement, test, commit `docs/component-reports/p11.md`, and finish with a clean worktree on its checked-out feature branch (`nuxel/p11-durable-evidence-checkpoint`).
>
> In this file, lines prefixed **`[AUDITED]`** are facts I verified by reading the repository read-only during prompt authoring. Lines prefixed **`[INSPECT]`** are things the future agent must confirm in its own checkout (paths, versions, or live device state can differ). Treat `[INSPECT]` as required first steps, not assumptions.

---

## 0. Agent mission (this branch ONLY)

You are the Nuxel Fedora ARM64 phone OS engineering agent, working in a dedicated Git feature branch (`nuxel/p11-durable-evidence-checkpoint`). Implement **only component P11: Durable evidence and truthful checkpoint** in this existing repository. This file is the complete scope for the current run; do **not** implement the other screenshot items or sibling components in this branch. Reuse actual Nuxel architecture and existing services instead of creating parallel or fake substitutes.

**Target platform:** Samsung Galaxy S10+ `SM-G975F` / Exynos 9820, Nuxel Fedora ARM64 **without Android framework dependencies**. A MacBook host may build/test; the live phone **may not be connected**. Do **not** assume a hardware verification that did not happen — see §9.

### Component-specific implementation contract
1. Define an **append-only evidence format** for commands, hashes, versions and observed outcomes.
2. Persist a **resumable checkpoint/state** for tests and component progress.
3. Record hardware results as **`NOT_TESTED`**, distinct from `PASS`.
4. Test **interrupted-run recovery** and **evidence integrity**.

---

## 1. What "durable evidence" means here (do not over-build)

Nuxel already has a mature, committed convention for exactly this. Your job is to **extend the existing vocabulary**, not invent a new one. Match it precisely.

`[AUDITED]` The authoritative precedent is in `tools/beta/`, and its closed verdict/evidence vocabulary:
- `tools/beta/workqueue.py` — append-only queue records; history grows, the previous revision is **never rewritten**; records are keyed by `<suite-id>|<owning group>|<reason + committed evidence path>|<expiry YYYY-MM-DD>`. The verdicts are a **closed set**: `PASS`, `FAIL`, `BLOCKED_EXTERNAL_RESOURCE`, and terminal states including `VERIFIED_ON_S10PLUS on PASS`, `VERIFIED_IN_VM_ONLY`, `OFFLINE_TESTED`. A verdict change requires a note (the reason is evidence).
- `tools/beta/soak_lib.py` — **resumable** evaluation: it writes per-sample NDJSON to an output file and re-reads it; `--checkpoint` drives periodic durable snapshots (`checkpoint_s=1800` default) so a run can be resumed mid-way rather than restarted.
- `tools/beta/rollback.sh`, `tools/beta/regression-guard.sh`, `tools/beta/run-all-tests.sh` — fail-closed gates; evidence-derived allowance registers; CI-friendly `::error::` reporting.
- `tools/verify-artifacts.sh` (+ `tools/s10plus/verify-a25-boot.py`, `tools/s10plus/verify-fedora-phone-rootfs.py`) — the repo's **FAIL-CLOSED** verification pattern: non-empty files, structural validity (boot image header sizes > 0, ext4 magic + real payload), and byte-identical archive checks. This is the template for "prove it is what it claims" integrity checking.
- `docs/verification-report.md` — the honest reporting vocabulary in prose: **`NOT VERIFIED HERE`** when a value cannot be produced in-sandbox, never fabricating a PASS; every claimed PASS is backed by a quoted, committed artifact.

### The verdict vocabulary you must extend (closed set)
Reuse and extend this exact closed set — do not introduce free-form statuses:
- `PASS` / `FAIL` — offline/host behaviour of the evidence + checkpoint machinery itself.
- `NOT_TESTED` — hardware touched by P11 that was **not** exercised on a live device in this run. This is a first-class, required outcome; it is **not** a gap to hide and **not** equivalent to `PASS`.
- `BLOCKED_EXTERNAL_RESOURCE` — an external dependency (e.g. the phone not connected) blocks verification of one item while the rest proceeds.
- Terminal device states (already defined in `soak_lib.coalesce_plan["terminal_states"]`): `VERIFIED_ON_S10PLUS on PASS`, `VERIFIED_IN_VM_ONLY`, `OFFLINE_TESTED`.

**Rule:** every P11 item ends as exactly one of these, never omitted. Omitting an item is a failure; marking it `NOT_TESTED` with the reason is correct and complete for this run.

---

## 2. Required behaviour — precise scope

### 2.1 Append-only evidence format
Implement a durable evidence log that records, per event:
- **command** executed (canonical, normalized form),
- **hashes** of relevant inputs/outputs (sha256 — the repo already uses sha256 for artifact provenance; see `verify-artifacts.sh` "asserts the A5 base's documented sha256"),
- **versions** observed (read `VERSION`, which is currently `v0.6.0-beta`; also pin kernel/userspace versions where relevant — `[INSPECT]` confirm the exact values in your checkout),
- **observed outcome**, expressed only with the closed verdict set above,
- a monotonic **sequence number / append token** proving append-only ordering,
- an **integrity pointer** chaining each record to the previous (a hash-chain so tampering is detectable — see §2.4).

Constraints that follow directly from the repo:
- The log is **append-only**: writing a new record never mutates or rewrites existing lines. Model it on `workqueue.py`'s "history grows; the previous revision is never rewritten" invariant.
- Records must be machine-parseable (NDJSON, one compact JSON object per line) so they compose with the soak replay path (`soak_lib` reads NDJSON samples). This keeps P11 evidence consumable by existing tooling rather than a parallel format.
- The log lives somewhere that is **committed to git as source** but whose *live runtime* instance is clearly distinguished from committed history. `[AUDITED]` `.gitignore` ignores `*.log`/`trace.log`; the repo's durable evidence (the authoritative record) is the **committed** copy under a stable, versioned path, while ephemeral per-run logs are git-ignored. Match this: commit a canonical, deterministic evidence store; never rely on a transient file for truth.

### 2.2 Resumable checkpoint / state
Implement resumable progress so an interrupted run continues rather than restarts:
- Persist a small **checkpoint** document (JSON) that records completion state at each durable boundary — which events are recorded, the current chain height, and the last verified sequence number. Model on `soak_lib`'s per-sample NDJSON + `--checkpoint` resume pattern.
- On start-up, the tool must detect an existing checkpoint and **resume**: it skips already-recorded/verified work and continues from the last durable boundary. It must never duplicate a record or rewind history.
- Checkpoint writes must be atomic (write-temp-then-rename) so a crash mid-write cannot corrupt prior state — this is the same fail-closed discipline as `verify-artifacts.sh`.

### 2.3 Hardware NOT_TESTED distinct from PASS
Where P11 touches the phone, record it honestly:
- If no live device was exercised in this run, the item's verdict is **`NOT_TESTED`** with a one-line reason (e.g. "phone not connected on host"). This must be structurally different from `PASS` — a downstream reader rendering the report must never confuse them.
- `VERIFIED_ON_S10PLUS on PASS` may only be recorded when backed by an **on-device evidence path** (the same rule `workqueue.py` enforces: "VERIFIED_ON_S10PLUS is REFUSED without an on-device evidence path"). A passing host unit test can never produce it.
- `[INSPECT]` Confirm the exact live-console and service paths below before citing them as deployed-vs-not-deployed facts in your report.

### 2.4 Evidence integrity (hash-chain) + interrupted-run recovery
Integrity is a first-class feature, not an afterthought:
- Each record carries a `prev` pointer = hash of the previous full record; the chain root is defined by convention. A verifier recomputes hashes top-to-bottom and **fails loudly** on any mismatch (fail-closed like `verify-artifacts.sh`).
- Implement recovery from a partially-written tail: an interrupted append that left a truncated final line must not be treated as valid, and resumption must skip it deterministically rather than re-executing the command.

---

## 3. Repository integration points (reuse, do not duplicate)

`[AUDITED]` Reuse these real things instead of building parallel substitutes:
- **Single-owner lock pattern** — `services/nuxel-console/bin/nuxel-console-free` + `services/nuxel-console/systemd/nuxel-console.service`. The console guards the debug port with an `flock(LOCK_EX|LOCK_NB)` on `$NUXEL_CONSOLE_LOCK` (default `/run/nuxel-console.lock`) and exits non-zero if anyone holds it. This is the repo's canonical "prove you are not a second owner" primitive — reuse it for any concurrency guard your checkpoint machinery needs, rather than inventing a new locking scheme.
- **systemd unit convention** — units carry elaborate `[Unit]` comment blocks explaining *why* each directive exists and what is deliberately **not** applied (e.g. `nuxel-console.service` explains why `ProtectSystem=strict`/`PrivateDevices=yes` are intentionally omitted). If P11 adds a service or unit, follow this exact documentation style: every hardening choice is recorded with its reason, not just listed.
- **CI gate integration** — wire the new evidence/checkpoint checks into `tools/beta/run-all-tests.sh` / `ci/validate-build.sh` following that script's existing PASS/FAIL + exit-code + `::error::` conventions. `[INSPECT]` confirm whether P11 checks belong in the CI rootfs build path or the offline `run-all-tests.sh` suite.
- **Honest reporting** — mirror `docs/verification-report.md`: quote committed artifacts for every PASS, mark `NOT VERIFIED HERE` where a value cannot be produced from this sandbox, never fabricate.

---

## 4. Implementation steps (smallest coherent plan)

1. **Audit (do not skip).** Read `tools/beta/workqueue.py`, `soak_lib.py`, `verify-artifacts.sh`, `nuxel-console-free`, and one systemd unit's comment block. Confirm the closed verdict set, the sha256 provenance convention, the flock lock path, and that `docs/component-reports/` does not yet exist (`[AUDITED]` it is absent — P11 creates its first report). Record findings as the "existing behaviour" section of your report.
2. **Add the evidence + checkpoint tooling.** Implement a single well-tested module/script under an appropriate existing location (e.g. `tools/beta/`, matching precedent) exposing: `record` (append), `verify-chain` (integrity), `checkpoint-save`, `checkpoint-restore`, and a CLI that resumes from any existing checkpoint. Use sha256, NDJSON lines, monotonic sequence numbers, and `prev` hash-chaining.
3. **Wire into the test harness.** Add tests to `tools/beta/tests/` (matching the style of `test_workqueue.py`: hermetic, throw-away dirs under `$TMPDIR`, driving the real CLI in a subprocess). Do not add an un-wired parallel suite.
4. **Integrate the gate** (`[INSPECT]` confirm target) so evidence integrity and resume behaviour are asserted by CI/offline runs, fail-closed.
5. **Report.** Write `docs/component-reports/p11.md` (see §8). Commit only P11's code/tests/docs/report on this branch.

---

## 5. Tests — must exercise real behaviour and failure paths

Model test style on `tools/beta/tests/test_workqueue.py`. Every requirement in §2 needs a **real** failing path, not just a static reference:

- **Append-only:** run `record` twice; assert the first line is byte-for-byte unchanged and a new monotonic sequence number was issued.
- **Integrity — happy path:** build a chain of N records; `verify-chain` returns PASS and reports the correct root hash.
- **Integrity — tamper detection:** flip one character in record *k*; assert `verify-chain` FAILs at exactly that height with a clear message (fail-closed).
- **Interrupted tail recovery:** write a valid chain of N records then append a **truncated** final line; resume must skip the truncated line deterministically and re-verifying still yields PASS over the first N — it must not crash or accept the garbage.
- **Checkpoint resume:** run to a durable boundary, "crash" (kill), start again against the same store; assert it resumes from the last checkpoint, does **not** duplicate records, and continues appending with correct sequence numbers.
- **NOT_TESTED ≠ PASS:** a check that would require a live device reports `NOT_TESTED` in the sandbox host path — assert the verdict value is literally `NOT_TESTED`, structurally distinct from `PASS`.
- **Version/hash honesty:** an event recorded without its real hash/version must fail verification, proving the format cannot silently drop provenance.

All tests run on the MacBook host with no device connected; they prove the machinery that *produces and verifies* truthful evidence works, including its honest NOT_TESTED handling. They do **not** claim to have verified hardware.

---

## 6. Build / test / lint for AArch64 native code

`[AUDITED]` The S10+ target is ARM64; a MacBook host builds cross-platform Python/shell but may not compile the small C pieces natively.
- For pure-Python/Shell evidence tooling: run on the host directly (`python3`, `bash`).
- For any AArch64-native code (e.g. anything touching the console's C probe in `tools/s10plus/a34/`): **cross-build or clearly document the precise toolchain restriction.** Do not claim native ARM64 execution on host that does not run it. `[INSPECT]` whether P11 introduces any AArch64 component; if it does, either cross-compile (document the exact `aarch64-*` toolchain + flags) or mark that specific compile step `NOT_TESTED` with the restriction stated.

---

## 7. Acceptance gates
- Every item in §2 is **implemented** or explicitly marked `BLOCKED`/`NOT_TESTED` with concrete evidence — never omitted.
- Tests exercise real behaviour and failure paths (§5), not static references.
- Hardware-touching items distinguish *mock/host-tested* from *live-deployed* and *owner-confirmed*.
- No dangerous hardware operation (flashing, bootloader/partition write, kernel replacement, unsafe amplifier/LED setting) is performed — P11 only reads evidence state and verifies integrity.
- If a critical external dependency blocks verification, produce the smallest safe implementation + a precise blocker report, then stop; do not let missing hardware proof stall unrelated queue items.

---

## 8. Report — `docs/component-reports/p11.md`

Create this file (P11's first component report). Structure it to mirror the honesty of `docs/verification-report.md`:
- **Honesty statement:** what was produced, and explicitly which parts could only be verified on-host vs. a live S10+.
- **Code paths changed** with reasons (extend §3 integration points; justify any new systemd directive using the documented-style).
- **Commands / receipts:** example `record`/`verify-chain` invocations and their real output, plus the integrity root hash of the committed sample store.
- **Verdicts per item:** `PASS` / `FAIL` / `BLOCKED` / `NOT_TESTED`, each with evidence (quoted artifact or test id).
- **Device deployment status:** state clearly whether anything was deployed to a live phone this run (`[INSPECT]` confirm — the live S10+ may be offline; if so, mark deployment `NOT VERIFIED HERE`).
- **Unresolved issues** and **safe rollback instructions** (model on `tools/beta/rollback.sh`: what to revert, how to restore the prior evidence store / checkpoint, how to disable a new unit without breaking the single-owner console).

---

## 9. Hardware verification — honest boundaries

`[AUDITED]` The live S10+ is the deployment target but **may not be connected** to this host during your run.
- Distinguish three states everywhere: `OFFLINE_TESTED` (host/tests), `NOT VERIFIED HERE` / `NOT_TESTED` (could not run on device this cycle), and `VERIFIED_ON_S10PLUS on PASS` (only with a real on-device evidence path).
- Never pass off mock/host tests as physical checks, and never invent an owner-confirmed result. If you cannot reach the phone, record `NOT_TESTED`/`NOT VERIFIED HERE` — that is correct and complete for this run.

---

## 10. Hard boundaries for THIS component's run
- Implement **only** P11; do not touch unrelated screenshot items or sibling components.
- Reuse existing Nuxel architecture (see §3); no parallel/fake substitutes.
- Preserve working launcher navigation, haptics, custom icon assets, Home layouts and USB recovery — P11 must not regress them.
- Keep dangerous hardware operations forbidden; P11 only records/verifies evidence.
- Commit **only** this component's code, tests, documentation and report on the checked-out branch. Do not merge into main, switch branches, add secrets, or generate unrelated features. Check `git status` and finish with a clean worktree.

---

## 11. Start here (checklist)
1. Read §3 sources; confirm closed verdict set, sha256 convention, flock path, and that `docs/component-reports/` is absent (`[INSPECT]`).
2. Implement the evidence + checkpoint tooling (§2.1–2.4), reusing `soak_lib`/`workqueue`/`verify-artifacts.sh` patterns.
3. Add failure-path tests (§5) under `tools/beta/tests/`.
4. Wire the gate (`[INSPECT]` target).
5. Write `docs/component-reports/p11.md` (§8); commit only P11; clean worktree.

**COMPONENT P11 ONLY.**
