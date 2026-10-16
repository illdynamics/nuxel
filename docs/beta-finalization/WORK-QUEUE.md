# Nuxel beta finalization — authoritative work queue (briq-00c)

**Access tier:** repository-only (no phone, no VM needed to read or update this queue).
**Compiled:** 2026-10-16 16:12:26+0200 (Europe/Amsterdam) — real host clock, nothing here is a fabricated timestamp.
**Machine view (source of truth):** `docs/beta-finalization/workqueue/<stable-id>.json` — one file per task.
**Human view (this file):** a rendered snapshot; if the two ever disagree, the JSON wins and this
file is regenerated from it.
**Tool:** `tools/beta/workqueue.py` (stdlib only, no network, never writes to `.qq`).
**Tests:** `tools/beta/tests/test_workqueue.py` — 27 assertions, all passing (OFFLINE_TESTED).

Mission section 4 requires a persistent, dependency-aware, resumable work queue with per-task
stable id, priority, component, current implementation state, dependencies, evidence, intended
changes, tests, risk level, rollback method and final verdict.  This is that queue.

---

## 1. Why one file per task (and why append-only)

Eleven build groups are writing into this tree at the same time.  A single shared
`WORK-QUEUE.json` would be a guaranteed merge conflict and a lost-update race.  So:

* **one file per task**, `workqueue/<stable-id>.json`, named after the task id;
* each file holds an **append-only `revisions` array** — `set-state` never edits a previous
  revision, it appends a new one with `revision: N+1`, `at` (real clock) and `by`;
* writes are **atomic** (`mkstemp` + `os.replace`) so a parallel reader sees either the old
  or the new file, never a torn one;
* writers take a short **advisory lock** (`<id>.json.lock`, `O_CREAT|O_EXCL`) so two processes
  can never interleave on the same task;
* the effective record is always the **last** revision;
* **mistakes are corrected by appending, never by rewriting.**  bg-00 did exactly that: the
  first revisions carried approximate evidence timestamps, and a later revision records the
  real re-verification window and says which values it supersedes.

That gives resumability for free: after a crash, restart or a new cycle, the queue is simply
read back off disk, and every task's audit trail is intact.

```jsonc
{
  "schema_version": 1,
  "id": "briq-00c-workqueue-ledger",
  "revisions": [
    { "revision": 1, "at": "…", "by": "construqtor/bg-00-preflight",
      "title": "…", "component": "bg-00-preflight", "priority": 0, "state": "pending",
      "dependencies": ["briq-00a-repo-preflight"], "evidence": [], "intended_changes": […],
      "tests": […], "risk": "low", "rollback": "…", "verdict": null },
    { "revision": 2, "at": "…", "by": "construqtor/bg-00-preflight",
      "state": "implemented", "verdict": "OFFLINE_TESTED", "note": "…" }
  ]
}
```

## 2. Record schema

| Field | Type | Meaning |
|-------|------|---------|
| `id` | string | stable id, also the file name; `^[a-z0-9][a-z0-9._-]*$` |
| `title` | string | the briQ title |
| `component` | string | owning build group (`bg-01-touch-pipeline`, …) |
| `component_title` | string | human-readable group name (seeded tasks) |
| `priority` | int 0–8 | mission band; **0 = repository foundation** that must exist before band 1 |
| `state` | enum | `pending` · `in_progress` · `implemented` · `blocked` · `deferred` · `reverted` |
| `dependencies` | [id] | must exist, may not self-reference, must be acyclic |
| `evidence` | [obj] | `{kind, path, command, result, at}` — see the verdict table |
| `intended_changes` | [string] | what the briQ is supposed to change (seeded from the plan's expected files) |
| `tests` | [string] | how the change is/was tested |
| `risk` | enum | `low` · `medium` · `high` |
| `rollback` | string | required, non-empty — how to undo the task |
| `verdict` | enum \| null | **exactly** the mission vocabulary below; `null` = no verdict recorded yet |
| `offline_ceiling` | enum \| null | highest verdict reachable **without the handset**; beats optimism |
| `owner_action` | string | the step the phone owner must perform (owner-test tasks only) |
| `expected_files` | [string] | delivered paths, as declared in the plan |
| `note` | string | free-text rationale, required when a recorded verdict changes |

`verify-schema` fails on: unknown vocabulary token, unknown/self/duplicate/cyclic dependency,
missing rollback, malformed evidence, out-of-range priority, an `id` that disagrees with the file
name, and an unreadable state file.  `--strict` additionally demands a final verdict on every task.

## 3. Verdict vocabulary, and the evidence each one demands

The vocabulary is closed.  `verify-schema` rejects anything outside it, whether passed on the CLI
or hand-written into a file.

| Verdict | Means | Evidence the validator requires |
|---------|-------|---------------------------------|
| `VERIFIED_ON_S10PLUS` | observed working **on the physical SM-G975F** | **at least one `kind:"on_device"` entry with a real command and a captured result/`at`** — otherwise refused |
| `VERIFIED_IN_VM_ONLY` | proven in the UTM Fedora 43 guest only | ≥1 `kind:"vm"` entry |
| `OFFLINE_TESTED` | executed on the build host (unit test, build, static analysis) | `kind:"offline"` entries |
| `DEPLOYED_UNVERIFIED` | staged/deployed to the phone but not yet exercised | ≥1 `kind:"on_device"` entry |
| `IMPLEMENTED_NOT_DEPLOYED` | code/config exists and is committed, nothing deployed | `kind:"offline"`/`"observation"` |
| `BLOCKED_KERNEL` | needs a kernel patch/rebuild that is **not deployed** | blocker described in `note` |
| `BLOCKED_FIRMWARE` | needs firmware/blobs not obtainable non-destructively | as above |
| `BLOCKED_HARDWARE` | the silicon/board cannot do this | as above |
| `BLOCKED_EXTERNAL_RESOURCE` | no phone console / no VM / no owner / missing input archive | as above |
| `NEEDS_OWNER_TEST` | implemented + instrumented, a human must act on the device | `owner_action` filled in |
| `FAILED` | attempted, did not work | failure evidence |
| `DEFERRED` | deliberately out of this beta | `note` |
| `NOT_SUPPORTED_ON_DEVICE` | will never work on this hardware, by design | `note` |

The hard rule from the mission, encoded in `validate_record()`:

> **a passing unit test never yields `VERIFIED_ON_S10PLUS`.**

There is no flag, override or bypass in the tool: an on-device verdict without an on-device
capture is rejected with exit code 1.  Evidence kinds are `offline`, `vm`, `on_device`,
`owner_instruction`, `observation` and `doc`; `observation` (e.g. "the file exists") is
deliberately *not* proof and can never satisfy an on-device or VM gate.

## 4. Priority bands

| Band | Build group(s) |
|------|----------------|
| 0 (foundation) | `bg-00-preflight` — preflight, archive discovery, this ledger, baseline protection |
| 1 | `bg-01-touch-pipeline` — touchscreen and reliable interactive input |
| 2 | `bg-02-boot-animation-launcher` — boot stability, animation handoff, launcher parity |
| 3 | `bg-03-connectivity-time-audio-buttons` — Wi-Fi, time/RTC, audio, headphones, buttons |
| 4 | `bg-04-userspace-completion` — Fedora userspace, services, application infrastructure |
| 5 | `bg-05-security-permissions` — permissions, firewall, VPN/Tor, security audit |
| 6 | `bg-06-core-phone-apps` — core apps, phone apps, settings, keyboard |
| 7 | `bg-07-specialty-apps`, `bg-08-hardware-subsystems` — store/power-user apps; power, sensors, owner kits |
| 8 | `bg-09-integration-release`, `bg-12-reports` — soak/rollback/release deliverables; the two reports |

The two evidence channels that gate everything else are scheduled alongside bands 1–2 because they
*produce* verification rather than consume it: `bg-10-live-phone` (serialized live deployment,
band 1) and `bg-11-vm-parity` (band 2).

## 5. Current ledger state (measured at compile time)

| Metric | Value |
|--------|-------|
| Tasks | **54** (one per briQ in the plan, bg-00 … bg-12) |
| Dependencies | validated acyclic; referential integrity enforced |
| `implemented` / `in_progress` / `pending` | 4 / 29 / 21 |
| Verdicts recorded | 4 — all `OFFLINE_TESTED` (bg-00's four briQs) · no verdict yet: 50 |
| `VERIFIED_ON_S10PLUS` claims | **0** — nothing has been proven on the handset yet |
| Evidence entries | 93 |
| Schedulable now (all deps resolved) | 18 tasks: `00a-repo-preflight` · `00b-archive-discovery` · `00c-workqueue-ledger` · `00d-baseline-protection` · `01a-pipeline-trace-tool` · `01b-libinput-path-shim` · `10a-live-reachability-preflight` · `02a-readiness-handoff` · `02b-verbose-boot-setting` · `02c-fb-colour-conversion` · `02d-launcher-parity` · `02e-safe-zones-statusbar` · `03a-wifi` · `03b-time-rtc-timesync` · `03c-audio-speaker` · `03e-buttons-gestures` · `04a-fedora-packages` · `09a-test-strategy-soak` |
| Marked owner-only (`offline_ceiling = NEEDS_OWNER_TEST`) | 12: `01d-touch-owner-test` · `10b-live-deploy-userspace` · `02a-readiness-handoff` · `03d-headphones-usbc` · `08b-vibration-haptics` · `08c-flashlight-led` · `08d-bluetooth` · `08e-nfc` · `08f-gps-gnss` · `08g-sensors` · `08h-camera` · `08i-sim-microsd-modem` |

`in_progress` was seeded from **observed file presence**: 29 of the 54 tasks already have at
least one of their expected files in the tree (the eleven parallel groups are mid-flight).  Presence
is **not** a verdict — it is recorded as an `observation` evidence entry and nothing more.

## 6. The task ledger

Columns: task id, priority band, component, state, verdict, evidence count, dependencies.
Ids are shown without the `briq-` prefix.

| id | pri | component | state | verdict | ev | depends on |
|----|----:|-----------|-------|---------|--:|------------|
| `00a-repo-preflight` | 0 | bg-00-preflight | implemented | OFFLINE_TESTED | 3 | — |
| `00b-archive-discovery` | 0 | bg-00-preflight | implemented | OFFLINE_TESTED | 3 | 00a-repo-preflight |
| `00c-workqueue-ledger` | 0 | bg-00-preflight | implemented | OFFLINE_TESTED | 5 | 00a-repo-preflight, 00b-archive-discovery |
| `00d-baseline-protection` | 0 | bg-00-preflight | implemented | OFFLINE_TESTED | 6 | 00a-repo-preflight |
| `01a-pipeline-trace-tool` | 1 | bg-01-touch-pipeline | in_progress | — | 1 | — |
| `01b-libinput-path-shim` | 1 | bg-01-touch-pipeline | in_progress | — | 3 | — |
| `01c-chargermode-bootmode` | 1 | bg-01-touch-pipeline | in_progress | — | 1 | 01a-pipeline-trace-tool |
| `01d-touch-owner-test` | 1 | bg-01-touch-pipeline | pending | — | 0 | 01a-pipeline-trace-tool |
| `10a-live-reachability-preflight` | 1 | bg-10-live-phone | pending | — | 0 | 00a-repo-preflight |
| `10b-live-deploy-userspace` | 1 | bg-10-live-phone | pending | — | 0 | 10a-live-reachability-preflight, 01b-libinput-path-shim, 02a-readiness-handoff, 09b-reboot-rollback-policy |
| `10c-live-reboot-and-verify` | 1 | bg-10-live-phone | pending | — | 0 | 10b-live-deploy-userspace, 01a-pipeline-trace-tool, 03c-audio-speaker |
| `02a-readiness-handoff` | 2 | bg-02-boot-animation-launcher | in_progress | — | 2 | — |
| `02b-verbose-boot-setting` | 2 | bg-02-boot-animation-launcher | in_progress | — | 3 | — |
| `02c-fb-colour-conversion` | 2 | bg-02-boot-animation-launcher | in_progress | — | 2 | 00d-baseline-protection |
| `02d-launcher-parity` | 2 | bg-02-boot-animation-launcher | in_progress | — | 6 | 00d-baseline-protection |
| `02e-safe-zones-statusbar` | 2 | bg-02-boot-animation-launcher | in_progress | — | 2 | 00d-baseline-protection |
| `11a-vm-launcher-parity` | 2 | bg-11-vm-parity | pending | — | 0 | 02d-launcher-parity, 02e-safe-zones-statusbar, 06b-missing-core-apps |
| `11b-vm-services-verify` | 2 | bg-11-vm-parity | in_progress | — | 1 | 04b-service-definitions, 04c-app-infrastructure |
| `03a-wifi` | 3 | bg-03-connectivity-time-audio-buttons | in_progress | — | 3 | 00c-workqueue-ledger |
| `03b-time-rtc-timesync` | 3 | bg-03-connectivity-time-audio-buttons | in_progress | — | 3 | 00c-workqueue-ledger |
| `03c-audio-speaker` | 3 | bg-03-connectivity-time-audio-buttons | in_progress | — | 3 | 00c-workqueue-ledger |
| `03d-headphones-usbc` | 3 | bg-03-connectivity-time-audio-buttons | pending | — | 0 | 03c-audio-speaker |
| `03e-buttons-gestures` | 3 | bg-03-connectivity-time-audio-buttons | pending | — | 0 | 00d-baseline-protection |
| `04a-fedora-packages` | 4 | bg-04-userspace-completion | in_progress | — | 3 | 00c-workqueue-ledger |
| `04b-service-definitions` | 4 | bg-04-userspace-completion | in_progress | — | 3 | 04a-fedora-packages |
| `04c-app-infrastructure` | 4 | bg-04-userspace-completion | in_progress | — | 4 | 04b-service-definitions |
| `05a-permission-manager` | 5 | bg-05-security-permissions | in_progress | — | 3 | 04c-app-infrastructure |
| `05b-firewall-app` | 5 | bg-05-security-permissions | in_progress | — | 2 | 04b-service-definitions |
| `05c-vpn-tor-remote` | 5 | bg-05-security-permissions | in_progress | — | 1 | 05b-firewall-app |
| `05d-security-auditor` | 5 | bg-05-security-permissions | pending | — | 0 | 05a-permission-manager |
| `06a-core-app-inventory` | 6 | bg-06-core-phone-apps | pending | — | 0 | 04c-app-infrastructure |
| `06b-missing-core-apps` | 6 | bg-06-core-phone-apps | in_progress | — | 10 | 06a-core-app-inventory |
| `06c-phone-apps` | 6 | bg-06-core-phone-apps | in_progress | — | 4 | 06a-core-app-inventory |
| `06d-settings-and-keyboard` | 6 | bg-06-core-phone-apps | in_progress | — | 3 | 06b-missing-core-apps |
| `07a-nuxtore` | 7 | bg-07-specialty-apps | in_progress | — | 1 | 06a-core-app-inventory |
| `07b-devmgmt-cleanup-root` | 7 | bg-07-specialty-apps | in_progress | — | 3 | 06a-core-app-inventory |
| `07c-media-authenticator-downloader` | 7 | bg-07-specialty-apps | in_progress | — | 3 | 06a-core-app-inventory |
| `07d-snekbyte` | 7 | bg-07-specialty-apps | in_progress | — | 1 | 00b-archive-discovery, 06a-core-app-inventory |
| `07e-live-console-app` | 7 | bg-07-specialty-apps | in_progress | — | 1 | 04c-app-infrastructure |
| `07f-penguinterface` | 7 | bg-07-specialty-apps | in_progress | — | 1 | 06a-core-app-inventory |
| `08a-power-management` | 7 | bg-08-hardware-subsystems | in_progress | — | 1 | 03e-buttons-gestures |
| `08b-vibration-haptics` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08c-flashlight-led` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08d-bluetooth` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08e-nfc` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08f-gps-gnss` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08g-sensors` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08h-camera` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `08i-sim-microsd-modem` | 7 | bg-08-hardware-subsystems | pending | — | 0 | 08a-power-management |
| `09a-test-strategy-soak` | 8 | bg-09-integration-release | pending | — | 0 | 00c-workqueue-ledger |
| `09b-reboot-rollback-policy` | 8 | bg-09-integration-release | pending | — | 0 | 09a-test-strategy-soak |
| `09c-release-deliverables` | 8 | bg-09-integration-release | in_progress | — | 2 | 09b-reboot-rollback-policy |
| `12a-engineering-report` | 8 | bg-12-reports | pending | — | 0 | 00d-baseline-protection, 09c-release-deliverables, 10c-live-reboot-and-verify, 11a-vm-launcher-parity, 11b-vm-services-verify |
| `12b-manual-proof-checklist` | 8 | bg-12-reports | pending | — | 0 | 01d-touch-owner-test, 09c-release-deliverables, 10c-live-reboot-and-verify, 11a-vm-launcher-parity, 11b-vm-services-verify |

## 7. Using the queue

```bash
# everything (human-readable, sorted by priority band)
python3 tools/beta/workqueue.py list

# machine-readable / filtered
python3 tools/beta/workqueue.py list --json --group bg-01-touch-pipeline
python3 tools/beta/workqueue.py list --ready              # deps resolved, nothing blocking
python3 tools/beta/workqueue.py list --verdict BLOCKED_EXTERNAL_RESOURCE

# one task, or its full audit trail
python3 tools/beta/workqueue.py show briq-01a-pipeline-trace-tool
python3 tools/beta/workqueue.py show briq-00c-workqueue-ledger --history

# record progress: this APPENDS a revision (state, verdict, evidence, tests, risk, rollback)
python3 tools/beta/workqueue.py set-state briq-03a-wifi --state implemented \
    --verdict OFFLINE_TESTED \
    --evidence '{"kind":"offline","path":"tools/s10plus/a33/nuxel-wifi-diag.sh","command":"bash …","result":"…"}'

# add a task that is not in the plan (new work discovered mid-run)
python3 tools/beta/workqueue.py add --id bg-00-extra-example --title "…" --component bg-00-preflight \
    --priority 0 --dep briq-00a-repo-preflight --risk low

# validation: vocabulary + dependencies + evidence gates
python3 tools/beta/workqueue.py verify-schema            # exits 1 when invalid
python3 tools/beta/workqueue.py verify-schema --strict   # also: every task needs a verdict
python3 tools/beta/workqueue.py verify-schema --json

# self-test
python3 tools/beta/tests/test_workqueue.py
```

Global flags (`--root`, `--by`) go **before** the subcommand:
`python3 tools/beta/workqueue.py --by "construqtor/bg-03" set-state briq-03a-wifi …`.

A task is **ready** when it exists, every dependency exists, and every dependency has a recorded
verdict that is not one of `FAILED`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `BLOCKED_HARDWARE`,
`BLOCKED_EXTERNAL_RESOURCE`.  `DEFERRED` and `NOT_SUPPORTED_ON_DEVICE` count as resolved
(they are terminal decisions, not open work).

## 8. What this ledger does **not** claim

* It is not evidence that a feature works.  A task's verdict describes the *evidence recorded for
  that task*, nothing more.
* Removing a blocker requires a **new revision with evidence**, not editing an old one.
* `VERIFIED_ON_S10PLUS` is unreachable from this repository alone.  With no phone console
  (see `docs/beta-finalization/preflight/ENVIRONMENT.md` §6) every on-device verdict stays
  `BLOCKED_EXTERNAL_RESOURCE` or `NEEDS_OWNER_TEST` until a real capture exists.  The validator
  refuses the verdict either way — there is no "trust me" path.
* The ledger is written by hand/CLI, so its honesty is a discipline, not a proof.  The validator
  enforces the vocabulary, the dependency graph and the evidence *shape*; the guard in
  `tools/beta/regression-guard.sh` enforces the A32 baseline.  A recorded `at` is only as good as
  the clock it was read from — where a value was later found to be approximate, bg-00 corrected it
  by appending a revision that names the real measurement window.

## 9. Invariants that apply to every task in this queue (verbatim)

NO FLASHING of any kind - no writes to raw partition block devices or to
BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/VBMETA/radio/modem/EFS/SEC_EFS/calibration/IMEI/PIT or
partition metadata; no Heimdall/Odin/wrappers, no Download Mode, no TWRP, no new kernel installed
to the physical phone.  Recovery/Download-Mode power-menu entries may be implemented and
offline-tested but MUST NOT be triggered.  NEVER create/edit/build anything under
/Users/wicked/x/nuxel/.qq or RUN_ROOT - QonQrete metadata is read-only; NEVER write receipt JSON
or pipeline metadata into the project workspace.  Do not regress the A32 baseline.  Do not start
over: no new launcher, no replacing Fedora, no recreating existing functionality.  Never claim
untested hardware works; a passing unit test never yields VERIFIED_ON_S10PLUS.  Reboots are
allowed but must return to Nuxel with a known-working userspace rollback path; no blind repeat
reboots.  After three same-mode failures, change diagnostic strategy.

## 10. Verdicts for this briQ

| Item | Verdict |
|------|---------|
| `tools/beta/workqueue.py` (list/show/add/set-state/verify-schema/seed) | **OFFLINE_TESTED** |
| 54 per-task append-only state files seeded from the plan, schema-valid, acyclic | **OFFLINE_TESTED** |
| Append-only semantics, atomic writes, per-task lock | **OFFLINE_TESTED** (the self-test caught and drove out a shallow-copy defect that rewrote history) |
| Closed verdict vocabulary + dependency acyclicity enforcement | **OFFLINE_TESTED** |
| On-device evidence gate on `VERIFIED_ON_S10PLUS` | **OFFLINE_TESTED** |
| `docs/beta-finalization/WORK-QUEUE.md` | **IMPLEMENTED_NOT_DEPLOYED** (documentation; nothing to deploy) |
| Any task in the ledger reaching `VERIFIED_ON_S10PLUS` | **BLOCKED_EXTERNAL_RESOURCE** (no live console this run) |
| Owner-only tasks (finger / ear / SIM / outdoors / tags) | **NEEDS_OWNER_TEST** |
| Ledger entries for the other eleven groups (state/verdict as they report) | maintained by those groups; seeded here as `pending`/`in_progress` from observed file presence only |
