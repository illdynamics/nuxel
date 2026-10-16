# NUXEL BETA — RELEASE ROLLBACK INSTRUCTIONS

**briq:** `briq-09c-release-deliverables` · **companion:** [`REBOOT-ROLLBACK.md`](REBOOT-ROLLBACK.md) (the discipline and the reboot policy) · [`../testing/TEST-STRATEGY.md`](../testing/TEST-STRATEGY.md)

This document is the operator-facing answer to one question: **"this release
change broke something — how do I get back?"** It covers the repository itself,
the userspace components, the service definitions, the launcher and the runtime
configuration. It never covers flashing a partition, because no Nuxel release
step flashes one.

> **The one rule.** Nothing in a Nuxel release may leave the phone in a state that
> cannot be undone from the live USB console. If a change would remove that
> console or the local recovery route, it is not deployable in this form.

---

## 1. Repository-level rollback (the release deliverables)

Everything in this briQ is repository data and tooling. Rolling it back is a
plain revert — nothing on the phone changes, because nothing here is enabled as a
unit or called from a boot path.

```bash
cd /path/to/nuxel
git log --oneline -- docs/beta-finalization tools/beta CHANGELOG.md VERSION
git revert <commit>                     # one commit
git revert <oldest>^..<newest>          # a whole briQ (oldest first)
```

What a revert restores, per deliverable:

| Deliverable | Effect of `git revert` |
|---|---|
| `CHANGELOG.md` | the previous release notes; no runtime effect |
| `VERSION` | the previous version identifier (see §1.1) |
| `docs/beta-finalization/**` | the previous reports/manifests; no runtime effect |
| `tools/beta/run-all-tests.sh`, `soak.sh`, `soak_lib.py`, `suite-coverage.py` | the previous release gate |
| `tools/beta/rollback.sh`, `reboot-policy.sh`, `health-check.sh`, `release_lib.py` | the previous deploy/rollback tooling |
| `tools/beta/validate-capability-manifest.py` | the previous manifest validator |

### 1.1 The version identifier

`VERSION` is the canonical identifier and is bumped in lockstep with the release
notes. If a version bump itself must be undone, revert the commit that contains it
and confirm the tree is consistent:

```bash
cat VERSION
grep -n "^## \[" CHANGELOG.md | head -3     # the newest entry must match VERSION
tools/beta/run-all-tests.sh --only '^U-release-tools-selftest$'
```

The suite `U-release-tools-selftest` fails if `VERSION` carries no beta line, if
`CHANGELOG.md` has no coherent entry for it, or if the release deliverable set is
incomplete — so a half-done version rollback is caught immediately.

### 1.2 Verifying a repository rollback

```bash
tools/beta/run-all-tests.sh                     # the offline gate: expect exit 0
tools/beta/run-all-tests.sh --strict            # the raw verdict (no cross-group allowances)
tools/beta/validate-capability-manifest.py \
    --manifest docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json \
    --schema   docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.schema.json \
    --workqueue docs/beta-finalization/workqueue
```

---

## 2. Userspace / runtime rollback (the phone)

The mechanism is `tools/beta/rollback.sh`; the discipline and its failure
behaviour are documented in [`REBOOT-ROLLBACK.md`](REBOOT-ROLLBACK.md) §2. The
short version:

```bash
# 1. what is deployed, and what is the baseline?
tools/beta/rollback.sh list
tools/beta/rollback.sh status

# 2. does the live tree still match the recorded baseline?
tools/beta/rollback.sh verify

# 3. restore (files + only the affected service), then prove it is healthy
tools/beta/rollback.sh rollback --briq <briq-id>
tools/beta/health-check.sh
```

Baselines live on the phone at
**`/var/lib/nuxel/rollback/<briq-id>/baseline-<stamp>/`** (copies + hashes +
`baseline.json` + `history.jsonl`), and the corresponding deploy manifest and
hashes are committed under `docs/beta-finalization/live/` so the recorded state is
reproducible without the phone.

### Component map

| Component | Baseline path (on phone) | Rollback = restore + restart | Notes |
|---|---|---|---|
| Launcher PWA | `/home/nuxel/nuxel/pwa/nuxel-home/**` | `nuxel-pwa` (or the session unit) | the **legacy framebuffer frontend stays available** as a non-competing fallback (`nuxel-ui-fallback.service`), so a bad launcher upgrade cannot brick the UI |
| Launcher native fallback | `/usr/local/bin/nuxel-ui*`, `nuxel-ui-fallback.service` | `nuxel-ui-fallback` | the A32 recovery route |
| Display bridge | `/usr/local/bin/nuxel-wl-fb` | `nuxel-wl-fb` | the single framebuffer writer; restarting it re-takes the panel |
| PWA host | `/usr/local/bin/nuxel-pwa-host` | `nuxel-wayland` | |
| Button manager | `/usr/local/bin/nuxel-button-manager`, `/etc/nuxel/button.json` | `nuxel-button-manager` | a `.prev-a32` copy is kept on the phone |
| Touch shim | `/usr/lib/nuxel/libnuxel-libinput-path.so` | `nuxel-wayland` | shim removal is a file restore |
| Settings documents | `/etc/nuxel/**` | the reader re-reads | atomic write; a bad document is replaced by its baseline |
| Service definitions | `/etc/systemd/system/nuxel-*.service` | `daemon-reload` + that one unit | |
| CLI | `/usr/local/bin/nuxelctl` | nothing (no daemon) | |
| Whole userspace | the tree capture | `tools/nuxel-rollback-home.sh` | native home ⇄ PWA kiosk route preserved |

### Time-bounded auto-rollback (security / network changes)

A firewall or VPN change can cut the only reachable session. `rollback.sh install`
therefore runs every such change **with a declared `health_check` and a bounded
step timeout**: if the declared check does not succeed, the baseline is restored
automatically and the run reports `ROLLED_BACK` (exit 3). The firewall surfaces
additionally ship a fail-closed console guard
(`configs/nftables/nuxel-console-guard.nft`) so a rule set cannot silently drop
the live console.

**Emergency path if the console is unreachable:** do not power-cycle repeatedly.
`tools/beta/reboot-policy.sh check` refuses to authorise another reboot until the
previous one has returned (`not_recovered`), and
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` describes the physical
recovery route. Recovering the console is the first action; rebooting is a last
resort.

---

## 3. What must never be "rolled back" by deleting things

The following are **not** cleanup targets and no Nuxel tool removes them:
`/var/lib/nuxel/rollback/**` (the way back), `/etc/nuxel/**` user settings,
saved Wi-Fi profiles, authenticator secrets, user documents, app data,
`/var/lib/nuxel/fb-owner` and the boot receipts, journals inside the configured
retention window. `cleanup` explicitly excludes credentials, app data,
authenticator secrets, boot images, firmware and unapproved user files, and it
never runs `rm -rf` on an unknown path.

---

## 4. Rollback of the beta itself

Reverting the *whole* beta candidate means reverting to the last A32-verified
state:

```bash
git log --oneline | grep -m1 "A32 BETA HARDWARE FINALIZER"   # the last hardware-verified commit
git diff --stat <a32-commit>..HEAD -- pwa/ shell/ services/ configs/ tools/
git revert <a32-commit>..HEAD --no-commit                    # inspect before committing
```

Then redeploy the preserved A32 userspace (`tools/beta/rollback.sh rollback`,
`tools/nuxel-rollback-home.sh`) and confirm with
`tools/beta/regression-guard.sh` (the A32 baseline register) plus
`tools/beta/health-check.sh`. The A32 successes that must survive any rollback are
enumerated as hash pins and behavioural invariants in
`docs/beta-finalization/baseline-protection.json` and
`docs/beta-finalization/BASELINE-PROTECTION.md`.

---

## 5. Evidence for this document

| Artefact | Contents |
|---|---|
| `docs/beta-finalization/release/evidence/rollback-selftest.txt` | `rollback.sh selftest` |
| `docs/beta-finalization/release/evidence/reboot-policy-selftest.txt` | `reboot-policy.sh selftest` |
| `docs/beta-finalization/release/evidence/run-all-tests-transcript-*.txt` | the release gate run that includes the mocked-failure scenarios |
| `tools/beta/tests/test-rollback-reboot.sh` | 22 scenarios: auto-rollback on an un-completable install and on a failing health check, refusal of raw-block and missing-source manifests, a clean install reporting `DEPLOYED_UNVERIFIED`, restore after mutation, `--briq` isolation, every policy refusal, and the inert dry run |

*This document and its tooling are `OFFLINE_TESTED`. The first live rehearsal
(rollback + reboot + reconnect) belongs to `briq-10c` and will be recorded in the
live evidence tree.*
