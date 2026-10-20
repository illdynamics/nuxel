# NUXEL R37 — VPN and private networking
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r37-vpn-private-networking`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Implement VPN/private-networking support through NetworkManager/WireGuard/OpenVPN with correct routes, DNS-leak prevention, key storage, status, and a kill switch scoped to the selected profile. The branch must preserve USB/local recovery and not globally hijack networking.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nftables/nuxel-vpn-killswitch.nft`, `configs/networkmanager/98-nuxel-dns.conf`, `configs/nuxel/security/remote-access.json`, `configs/networkmanager/README.md`, `tools/s10plus/a33/nuxel-vpn-tor.sh`, `tools/s10plus/a33/security-tests/test-vpn-tor.sh`, `tools/s10plus/a33/security-fixtures/net-mocks/wg`, and `pwa/nuxel-home/js/qs.js`. Configs and mocks exist; a real tunnel and kill switch are not proven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns VPN profile lifecycle, route/DNS policy, kill-switch rules, key/credential handling, status, and failure recovery. Does not own the Tor branch or generic firewall UI. No plaintext private keys in Git and no kill switch that locks out local recovery.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Define supported VPN types and their NetworkManager integration; do not invent a custom tunnel protocol.
2. Implement profile import/create with safe key storage/permissions and redacted logs.
3. Verify route/DNS behavior: traffic uses the tunnel, DNS does not leak, and local/USB recovery routes remain reachable.
4. Implement a kill switch as a scoped nftables transaction with atomic apply and rollback.
5. Handle tunnel disconnect, auth failure, server timeout, DNS failure, and route conflict.
6. Show real connection state and the protected/unprotected scope in the UI.
7. Test with mock `wg`/NetworkManager fixtures plus one owner-approved real profile if available.

## Failure modes and diagnostics
- Watch for DNS leaking through a non-tunnel interface, kill-switch rules surviving a profile removal, route metrics overriding the tunnel, and private keys in world-readable paths. Test from a known DNS/route baseline.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. A configured tunnel actually carries traffic and reports real state, or is explicitly NOT TESTED.
2. DNS queries do not bypass the tunnel when the kill switch is active.
3. The kill switch allows the documented USB/local recovery path.
4. Tunnel failure leaves a clear disconnected/protected state and no silent leak.
5. Private keys are stored with restrictive permissions and absent from logs/repo.
6. Route/interface conflict and auth timeout produce actionable errors.
7. The VPN does not globally break Wi-Fi, cellular, or local management.

## Hardware, privilege and rollback safety
No unauthenticated remote tunnel or credential scraping. Do not change radio firmware or flash. A kill switch must have a timed rollback/watchdog to avoid locking out the owner.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r37-vpn-private-networking`, with tests and docs for this component only.
- `docs/component-reports/r37.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the real VPN profile cannot be tested safely; keep it NOT TESTED and prove the mock routing/firewall logic separately. Do not claim privacy from a UI toggle.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
