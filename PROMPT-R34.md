# NUXEL R34 — Firewall application
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r34-firewall-application`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make the firewall application reflect and control the real nftables/firewalld policy, including ingress/egress, zones, per-app rules, VPN kill switch interaction, and USB recovery exceptions. The branch must show actual policy, not an unbacked toggle, and must never lock the owner out of the phone.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nftables/nuxel-firewall-config.json`, `configs/nftables/nuxel-app-firewall.nft`, `configs/nftables/nuxel-app-firewall-cgroupv2.nft`, `configs/nftables/nuxel-vpn-killswitch.nft`, `configs/nftables/nuxel-console-guard.nft`, `configs/nftables/systemd/nuxel-firewall.service`, `tools/s10plus/a33/nuxel-firewall.sh`, and `tools/s10plus/a33/security-tests/test-firewall.sh`. The policy files exist; effective rules and user-facing state must be queried from the running system.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns effective-rule inspection, app/zone policy, change transactions, rollback, and firewall UI state. Does not own VPN protocol setup itself, but must coordinate the kill switch. No default deny that cuts the USB/console recovery path without an explicit override.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Read the effective nftables ruleset and map it to the intended zone/app policy; record differences.
2. Define safe default profiles and an explicit recovery allowance for the USB console/local path.
3. Implement add/remove rules as a validated transaction with syntax check, atomic reload, and rollback on failure.
4. Integrate cgroupv2 app matching and verify an app's egress is actually blocked/allowed.
5. Coordinate VPN kill-switch rules so disabling/removing a VPN cannot leave the phone without recovery connectivity.
6. Test malformed policy, nft reload failure, concurrent change, and a rule that would block all management access.
7. Expose real counters/state in the app rather than a stale enabled flag.

## Failure modes and diagnostics
- Watch for firewalld and raw nftables managing the same tables, a default-drop rule applied before the SSH/USB exception, cgroup paths changing after app restart, and counters not updating due to a missing hook. Use a test listener on localhost for behavior checks.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. The firewall UI reflects the effective ruleset, not just the config file.
2. App/zone rules produce observed allow/deny behavior for a test listener.
3. A failed rule transaction rolls back and leaves connectivity intact.
4. The USB/local recovery path remains allowed unless the owner explicitly overrides it with a documented recovery plan.
5. VPN kill-switch interaction is defined and tested for disconnect/failure.
6. Malformed or conflicting rules are rejected before apply.
7. No toggle can report ENABLED while the firewall service is inactive or rules failed to load.

## Hardware, privilege and rollback safety
Do not lock out the USB console or the only remote management path. Rule changes need a timed rollback/watchdog. No flash/partition changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r34-firewall-application`, with tests and docs for this component only.
- `docs/component-reports/r34.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the current ruleset cannot be inspected or if a change cannot be atomically rolled back. Report the exact table/chain uncertainty.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
