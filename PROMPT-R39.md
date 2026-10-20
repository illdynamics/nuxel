# NUXEL R39 — Remote access and device connect
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r39-remote-access-device-connect`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make remote access and device-connect features authenticated, deliberate, and revocable. This branch owns SSH/mDNS/Zerotier/USB-link discovery, pairing, key handling, firewall exposure, file transfer, and recovery, and must never expose an unauthenticated control listener.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/security/remote-access.json`, `configs/nftables/nuxel-console-guard.nft`, `scripts/nuxel-adb-flash-pack/scripts/01-discover.sh`, `scripts/nuxel-adb-flash-pack/scripts/04-verify.sh`, `services/nuxel-console/`, `tools/s10plus/a33/nuxel-console.c`, and `pwa/nuxel-home/js/qs.js`. Discovery/flash-pack scripts exist; remote-access policy and actual listeners must be verified.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns remote-access policy/UI, pairing/keys, listener exposure, transfer authorization, and revocation. Does not own VPN/Tor or the base USB console. No default-on SSH with weak credentials and no unauthenticated control endpoint.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Inventory all listening services and map each to an explicit remote-access policy decision.
2. Audit SSH host/user keys, password auth, root login, and authorized_keys; default to key-only and disabled unless enabled by the owner.
3. Implement pairing/consent for device connect and file transfer with a visible confirmation and revocable grant.
4. Verify firewall rules expose only the intended interface/port and keep local/USB recovery accessible.
5. Implement revocation that removes keys/rules/grants and confirms no listener remains.
6. Test discovery, wrong key, expired/revoked grant, unauthorized transfer, and service restart.
7. Document the exact recovery path if remote access is misconfigured.

## Failure modes and diagnostics
- Watch for SSH enabled by a package default, mDNS advertising more than intended, firewall exceptions wider than the service, and keys stored world-readable. Verify listeners with `ss`, not only unit state.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Every listening port has an owner policy and a firewall decision.
2. Remote access is off or key-only by default; no weak/default credential path exists.
3. Pairing/consent is explicit, visible, and revocable.
4. Revocation removes the grant/key/rule and the listener no longer accepts it.
5. Only the intended interface is exposed; local/USB recovery remains reachable.
6. Unauthorized/expired attempts fail closed.
7. A misconfiguration recovery procedure is tested or clearly marked NOT TESTED.

## Hardware, privilege and rollback safety
Do not turn on remote access for convenience during testing without a scoped firewall and revocation plan. No unauthenticated control listener. Preserve USB console recovery.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r39-remote-access-device-connect`, with tests and docs for this component only.
- `docs/component-reports/r39.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if remote access cannot be scoped or revoked safely. Report the exact listener/rule and keep the feature disabled.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
