# NUXEL R38 — Tor privacy tools
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r38-tor-privacy-tools`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Integrate Tor as an explicit, opt-in privacy tool with correct SOCKS/DNS behavior, bridge policy, app routing, and limitations. This branch must prove that traffic is routed, not merely that `tor` is running, and must not globally hijack NetworkManager or other apps' networking.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/nuxel/security/tor/torrc`, `configs/networkmanager/resolved-conf.d/nuxel-privacy.conf`, `configs/networkmanager/nuxel-stubby.yml`, `configs/nuxel/security/privacy-config.json`, `tools/s10plus/a33/nuxel-vpn-tor.sh`, `tools/s10plus/a33/security-tests/test-vpn-tor.sh`, and the Tor-related Quick Settings icons. A daemon/config may exist, but routing and leak prevention are unproven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns Tor service/config, SOCKS/DNS isolation, bridge configuration, opt-in app routing, and status/limitations. Does not own VPN profiles or global DNS hijacking. No hidden enforcement and no claim of anonymity from a process being active.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Validate the torrc and probe SOCKS/control ports without exposing them to the network.
2. Implement explicit opt-in routing for selected apps/browser contexts; do not silently redirect all traffic.
3. Verify DNS resolution path and test for leaks outside the Tor proxy.
4. Support bridge configuration without embedding private bridge lines in the repository.
5. Handle bootstrap failure, no network, blocked bridges, and a stale/cached status.
6. Expose clear status: DISABLED, BOOTSTRAPPING, READY, FAILED, and which apps are routed.
7. Document limitations (non-Tor traffic, UDP, local network, app leaks) and test a non-routed app remains non-routed.

## Failure modes and diagnostics
- Watch for DNS resolving through the local resolver, WebRTC/QUIC/UDP bypass, a browser profile that ignores the proxy, and a control port exposed on all interfaces. Verify with a leak test, not a log line.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. Tor status is derived from bootstrap/control output and real route tests.
2. An opted-in client uses SOCKS and a DNS leak test cannot resolve outside the proxy path.
3. Apps not opted in remain on their normal route; routing is not global by surprise.
4. A bootstrap/bridge failure produces FAILED with a reason.
5. Bridges/passwords are not committed to Git.
6. The UI does not promise anonymity or hide limitations.
7. The real routed-traffic test is labeled separately from daemon-active state.

## Hardware, privilege and rollback safety
No illegal or abusive use; preserve privacy and safety. Do not globally intercept all traffic or expose control ports. No flash/kernel changes.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r38-tor-privacy-tools`, with tests and docs for this component only.
- `docs/component-reports/r38.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the only implementation path is a global transparent proxy that would break recovery networking. Report the limitation and keep routing opt-in.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
