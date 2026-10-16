# NUXEL BETA — AUTONOMOUS REBOOT POLICY & PER-COMPONENT ROLLBACK

**briq:** `briq-09b-reboot-rollback-policy` (depends on `briq-09a`)
**Tools:** `tools/beta/reboot-policy.sh` · `tools/beta/rollback.sh` · `tools/beta/health-check.sh` · `tools/beta/release_lib.py`
**Tests:** `tools/beta/tests/test-rollback-reboot.sh` (22 mocked-failure scenarios) · `tools/beta/tests/test-release-tools.sh`
**Companion:** [`../testing/TEST-STRATEGY.md`](../testing/TEST-STRATEGY.md) · [`ROLLBACK.md`](ROLLBACK.md) · [`DEVICE-CAPABILITY-MANIFEST.md`](DEVICE-CAPABILITY-MANIFEST.md)

---

## 1. The two rules that this document exists to enforce

1. **A reboot is allowed; a blind reboot is not.** Every reboot states a reason
   *and* a diagnostic that differs from the previous one, and the previous reboot
   must have returned to Nuxel before another is permitted.
2. **No change is deployed without a recorded, testable way back.** Record the
   previous hash → stage → verify → atomic install → restart the smallest
   affected service → health-check → roll back on failure.

Both are implemented, both are tested under mocked failure, and both are inert
until invoked. **No script in this repository ever flashes a partition, writes to
a block device, enters Download Mode/TWRP, or reboots the phone on its own
initiative.**

---

## 2. Rollback discipline (applies to *every* deployed component)

`tools/beta/rollback.sh` implements the seven-step discipline in this exact order:

| Step | Action | Failure behaviour |
|---|---|---|
| 1 | **Record the previous hash** of every tracked target and copy it aside (`capture`) | a target that does not exist is recorded as `kind: "absent"` — never invented |
| 2 | **Stage** the new file next to its target (`<target>.nuxel-staged`) | a stage failure stops the run **before** anything live is touched |
| 3 | **Verify** the staged bytes against the manifest's `source_sha256` | a mismatch stops the run; nothing is installed |
| 4 | **Atomic install** (`mv -f staged target`) — a half-written file can never be live | — |
| 5 | **Restart only the smallest affected service** (`systemctl restart <one unit>`, `daemon-reload` only if a unit file changed) | a non-zero restart is reported; the health gate decides |
| 6 | **Health check** (`tools/beta/health-check.sh`) | UNHEALTHY → **automatic rollback**, exit 3 |
| 7 | **Per-group `health_check` commands** from the manifest | a failing declared check → **automatic rollback**, exit 3 |

On any failure the tool restores the recorded baseline (files *and* the affected
service) and reports `ROLLED_BACK`; **the phone is never left in the failed
state**. Exit codes: `0` ok · `2` usage/guard · `3` auto-rolled-back (state
restored) · `4` manifest violations (nothing was written) · `5` unhealthy after a
manual rollback.

```bash
tools/beta/rollback.sh capture --briq briq-03a-wifi --label pre-wifi \
    --paths /etc/NetworkManager/conf.d/20-nuxel-wifi.conf \
            /usr/local/bin/nuxel-wifi-diag.sh
tools/beta/rollback.sh status
tools/beta/rollback.sh install --briq briq-03a-wifi \
    --manifest build/deploy-manifest.json --dry-run          # plan only
tools/beta/rollback.sh install --briq briq-03a-wifi \
    --manifest build/deploy-manifest.json                    # real, health-gated
tools/beta/rollback.sh rollback --briq briq-03a-wifi          # restore "latest"
tools/beta/rollback.sh verify                                  # compare live vs baseline
```

### Backup location

* On the phone: **`/var/lib/nuxel/rollback/<briq-id>/baseline-<stamp>/`**
  (files under `files/`, hashes and provenance in `baseline.json`, history in
  `history.jsonl`, the current pointer in `path`).
* In the repository: the deploy manifests, the recorded hashes and the dry-run /
  rehearsal transcripts live under `docs/beta-finalization/release/evidence/`
  and the live group's `docs/beta-finalization/live/` evidence tree, so a rebuild
  can reproduce the recorded state without the phone.
* `--briq <id>` isolates each task's baseline. The id is validated (no `/`, `.`
  or `..`) and recorded inside `baseline.json` as provenance, so two tasks can
  never overwrite each other's "previous good" copy.

### Per-component coverage

| Component | Baseline | Rollback route |
|---|---|---|
| PWA launcher (`/home/nuxel/nuxel/pwa/nuxel-home/**`) | `capture` records `index.html`, `js/*`, `sw.js`, `manifest.json` | `rollback` restores the previous build; the **working fallback frontend is preserved** (`nuxel-ui-fallback.service` / native home) so a bad launcher upgrade cannot brick the UI |
| Display bridge (`/usr/local/bin/nuxel-wl-fb`) | hash + copy | restore + restart `nuxel-wl-fb` only |
| PWA host (`nuxel-pwa-host`) | hash + copy | restore + restart the session unit |
| Button manager (`nuxel-button-manager` + `/etc/nuxel/button.json`) | hash + copy (a `.prev-a32` copy already exists on the phone) | restore + restart `nuxel-button-manager` only |
| Settings documents (`/etc/nuxel/**`) | hash + copy | restore the document; the reader re-reads without a restart where possible |
| systemd units | hash + copy | restore + `daemon-reload` + restart that one unit |
| CLI (`nuxelctl`) | hash + copy | restore; no service restart |
| Whole userspace | the tree capture (`--tree`) | `tools/nuxel-rollback-home.sh` keeps the native-home → PWA-kiosk route working; `rollback.sh rollback` restores the previous userspace build wholesale |
| **Live Console manager** | policy + service state | **local owner recovery is preserved**: the manager's disable switch is locally reversible, and the console's own disable path never removes the local takeover route |

### Time-bounded auto-rollback for security / network changes

Security and networking changes can cut the only reachable session (the USB
console). The rule is therefore explicit:

* The firewall/VPN/Tor surfaces ship a **fail-closed console guard**
  (`configs/nftables/nuxel-console-guard.nft` + the guard hand-off in the
  firewall tool) that permits the existing console session, so applying a rule
  set cannot silently kill the debug path.
* Every firewall/network deploy runs under `rollback.sh install` with a
  **time-bounded auto-rollback**: the declared `health_check` must succeed within
  the step timeout or the baseline is restored and the run reports `ROLLED_BACK`.
  A network change that cannot prove the console still answers is reverted.
* Never run two clients against a dangerous device node at once; never deploy a
  firewall and a VPN kill-switch in the same step.

### Manifest safety

`release_lib.parse_manifest()` refuses, before anything is written:

* any target under `/dev/block/*`, `/dev/sd*`, `/dev/mmcblk*`, `/dev/nvme*`,
  `/dev/mapper/*` (raw block);
* any path under `.qq/` or `.codeseeq/` (QonQrete metadata);
* a group declared `blocked_kernel`/`blocked_firmware`/`blocked_hardware`
  (its files must not be deployed);
* a source that does not exist (the hash cannot be computed);
* an install step whose desired effect is a flash operation.

`health_check` commands containing `heimdall`, `fastboot`, `dd … of=/dev/…` or
`mkfs*` are refused outright.

### Protecting user settings from later upgrades

User state (settings documents, saved networks, authenticator secrets,
bookmarks) is baselined by the same capture and is **never cleaned or replaced by
an upgrade** — `cleanup` excludes credentials, app data and authenticator
secrets; a settings upgrade merges into the existing document (atomic
read-modify-write) rather than overwriting it.

---

## 3. The autonomous reboot policy

`tools/beta/reboot-policy.sh` encodes the mission's reboot checklist and its hard
rules. A normal OS reboot into Nuxel is **authorized when justified after the
safety checks**; it is never automatic.

### 3.1 Pre-reboot checklist (`reboot-policy.sh pre [--run]`)

| # | Check | Why |
|---|---|---|
| 1 | live console working and answering framed commands | it is the only way back |
| 2 | progress saved (work queue + evidence written) | a lost session must not lose the run |
| 3 | logs flushed (`systemd-journald` + evidence files) | post-mortem evidence |
| 4 | `systemd` ready (`is-system-running` not `starting`) | do not reboot a half-built boot |
| 5 | no active package transaction (`dnf`/`rpm`/`flatpak` lock free) | a reboot mid-transaction damages the rootfs |
| 6 | known-working services preserved (baseline captured, rollback `status` known-good) | a way back exists |
| 7 | bounded reconnect strategy recorded (timeout + retry plan, not "wait forever") | the next attempt is bounded |

`post` re-runs the read-only half against the new boot and records whether the
phone actually returned to Nuxel.

### 3.2 The refusal rules (mechanically enforced)

`release_lib.policy_verdict()` refuses a reboot when any of these holds:

| Code | Refusal | Rule |
|---|---|---|
| `incomplete` | no stated reason, or no stated diagnostic | a reboot needs both |
| `blind_repeat` | the diagnostic is identical to the previous reboot's | change the evidence channel, not the power state |
| `reason_repeat` | the reason repeats the previous reboot's | same reason = same hypothesis = same result |
| `not_recovered` | the previous reboot never returned to Nuxel | recover the console and finish the post-checklist first |
| `no_rollback` | no known-good userspace rollback after the last reboot | never reboot into an unrecoverable state |
| `budget_exhausted` | 3 reboots already used this cycle | `POLICY["max_reboots"] = 3` |
| `three_same_mode_failures` | the same diagnostic **mode** failed three times | **three strikes: change the diagnostic strategy** — do not re-litigate a closed issue |

The three-strikes guard is mode-scoped: a *different* mode (say `usb-console`
after three `touch-irq` failures) is still allowed, which is exactly the
"three identical attempts → change diagnostic strategy" rule.

### 3.3 The hard rules (never violated by any tool in this repository)

* **Never another reboot merely because the previous one has not reconnected.**
  A missing reconnect is a *diagnostic* problem; another power cycle destroys the
  evidence and may worsen the state.
* **If the live console is lost, stop blind reboots and document.** The policy
  refuses (`not_recovered`) and the run records the blocked state.
* **Never reboot into recovery or Download Mode.** No Samsung magic reboot
  string is guessed, ever. The power menu entries exist as **offline-tested UI**
  only; `reboot-policy.sh` issues nothing but the normal OS reboot command, and
  only after `--execute --confirm` **and** a positive console-reachability check
  **and** not a dry run.
* No flashing, no raw block writes, no bootloader tools, no TWRP, no
  repartitioning — enforced statically by the `L1-no-flash-invariants` suite.

```bash
tools/beta/reboot-policy.sh status
tools/beta/reboot-policy.sh check  --reason "Wi-Fi association after config change" \
                                   --diagnostic "iw dev wlan0 link + NetworkManager state"
tools/beta/reboot-policy.sh pre    --run             # read-only probes
tools/beta/reboot-policy.sh reboot --reason "…" --diagnostic "…" --execute --confirm
tools/beta/reboot-policy.sh post
```

In a repository-only run (no owner, no console) the `reboot` command **prints the
exact command and exits 3 with `BLOCKED_EXTERNAL_RESOURCE`**. It never reboots by
itself.

---

## 4. Health gate

`tools/beta/health-check.sh` is the post-deploy/post-rollback gate:

* **on device** (`--root /`): every Nuxel stack unit active, `systemctl --failed`
  empty, the framebuffer-owner record present with a live PID, and the launcher
  answering `200` on `127.0.0.1:8000`;
* **offline** (`--root DIR`): the same checks against a recorded/fixture tree,
  verdict capped at `OFFLINE_TESTED` and explicitly advisory.

Exit `0` HEALTHY · `1` UNHEALTHY · `2` usage/guard. It refuses to run against a
QonQrete root. It is a **service** gate: it never claims that any hardware works
(see the manual proof checklist for those).

---

## 5. Evidence (mocked failure, dry runs, rehearsals)

| Artefact | What it shows |
|---|---|
| `tools/beta/tests/test-rollback-reboot.sh` (22 scenarios, all PASS) | the rollback really triggers: an un-completable install auto-rolls-back with the previous bytes byte-identical; a failing `health_check` auto-rolls-back; a raw-block target and a missing source are refused with nothing written; a clean install reports `DEPLOYED_UNVERIFIED`; `rollback` restores a mutated file; `--briq` isolates the baseline; the policy refuses no-reason, blind-repeat, reason-repeat, non-returned, budget-exhausted and three-same-mode-failures; the reboot command is inert without `--execute --confirm` + a reachable console, and the dry run issues nothing (proved with a `reboot` shim that must stay untouched) |
| `docs/beta-finalization/release/evidence/rollback-selftest.txt` | the tool's own sandboxed self-test |
| `docs/beta-finalization/release/evidence/reboot-policy-selftest.txt` | the policy self-test (1 : reason+diagnostic, blind repeat, non-return, budget, three-strikes) |
| `docs/beta-finalization/release/evidence/reboot-policy-dryrun.txt` | a dry-run transcript up to the reachability gate |
| `docs/beta-finalization/release/evidence/health-check-offline.txt` | the offline health tier on a fixture tree |
| `docs/beta-finalization/live/` (bg-10) | the live rehearsal once `briq-10c` runs with this tooling — that is the first `VERIFIED_ON_S10PLUS` for the policy |

Verdict for this briQ: **`OFFLINE_TESTED`** (tools, discipline and policy proven
offline under mocked failure). The live rehearsal verdict belongs to `briq-10c`.

---

## 6. Rollback of this briQ

`git revert` the commits touching `tools/beta/**` and
`docs/beta-finalization/release/**`. The scripts are inert until invoked: they
change no device state, they are not enabled as systemd units, and no boot path
calls them. Nothing on the phone changes if this briQ is reverted.
