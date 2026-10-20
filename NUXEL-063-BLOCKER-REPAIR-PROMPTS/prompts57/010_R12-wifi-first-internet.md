# NUXEL R12 — Internet — Wi-Fi first
STATUS: IMPLEMENTATION PROMPT ONLY — NOT EXECUTED
BRANCH: `nuxel/r12-wifi-first-internet`
BASE EVIDENCE SNAPSHOT: `e2aaf66951570a8e86211cb8b48060e6cd6773dd` (`v0.6.0-beta`)

## Mission
Make Wi-Fi the first working internet path on the S10+ with truthful end-to-end state. This branch owns chipset/driver/firmware discovery, NetworkManager policy, scan/join/DHCP/DNS/captive-portal handling, reconnect after suspend/reboot, and UI status, and must never report online from a toggle or interface flag alone.

This file is a future implementation brief, not an instruction to execute now. A future agent may modify this branch only after the repository owner explicitly authorizes execution. Do not merge, deploy, flash, reboot the phone, or start another branch's component as part of this work.

## Repo-grounded current state
Observed owners: `configs/networkmanager/10-nuxel-s10plus-wifi.conf`, `configs/networkmanager/wpa_supplicant-s10plus.conf`, `configs/networkmanager/nuxel-network-settings.spec.json`, `configs/networkmanager/nuxel-s10plus-wifi.nmconnection.example`, `tools/s10plus/a33/nuxel-wifi-diag.sh`, `tools/s10plus/a33/tests/test-wifi-diag.py`, `pwa/nuxel-home/js/status-bar.js`, and `pwa/nuxel-apps/settings/wifi-settings.js`. Capability manifests currently default the radio to `BLOCKED_FIRMWARE`; a BCM4375-class device is expected but real association is not proven.

Use `SOURCE VERIFIED`, `BUILT`, `VM VERIFIED`, `LIVE-DEVICE DEPLOYED`, `OWNER-VERIFIED`, `BLOCKED`, and `NOT TESTED` as separate labels. A file existing, a unit being active, a mock returning PASS, or a command exiting 0 is not proof of physical hardware behaviour.

## Precise component boundaries
Owns Wi-Fi enumeration, firmware/driver diagnostics, NetworkManager/wpa policy, network state reporting, and the Wi-Fi settings surface. Does not own cellular fallback or Bluetooth. No credential storage in Git and no guessed firmware filename as truth.

Stay inside this boundary. Do not silently alter unrelated launcher, compositor, boot, radio, security, or release behaviour. If a cited path is absent at execution time, record **“Not found—locate or add the smallest appropriate module”** and prove why; never invent a path, symbol, device node, or observed hardware result.

## Implementation work packages
1. Enumerate the real Wi-Fi PCI/SDIO device, driver binding, firmware/NVRAM paths, rfkill state, and interface name; report the first missing stage.
2. Verify NetworkManager owns the interface and that `wpa_supplicant`/`iwd` is not competing for it.
3. Test scan, association, DHCP lease, DNS resolution, captive-portal detection, and a real HTTPS fetch; record each stage separately.
4. Verify reconnect after link loss, suspend/resume where supported, and one ordinary reboot under the reboot policy.
5. Audit the status-bar/Quick Settings state so it follows NetworkManager events and does not render duplicate Wi-Fi icons.
6. Exercise wrong password, AP unavailable, DHCP failure, DNS failure, and captive portal as distinct negative cases.
7. Redact SSIDs/passwords and avoid storing credentials in the repository or logs.

## Failure modes and diagnostics
- Likely blockers: missing BCM4375 HCD/NVRAM firmware, wrong driver (do not transplant Pixel BCM4390 instructions), rfkill block, NetworkManager policy conflict, regulatory domain, and power-save dropping the link. Verify with `dmesg`, `/sys/class/net`, `/proc/asound`-style real sources, not config prose.
- Preserve the first failing layer, exact command, stderr, timestamp, versions, and owning service/module. Do not blur missing hardware, missing firmware, missing kernel support, bad permissions, stale cache, and an actual code regression into one failure.

## Verification and acceptance
A future agent must report every item below with its evidence class and exact command or inspection:
1. `nuxel-wifi-diag.sh status` identifies the real interface/driver/firmware and first failing stage.
2. Association yields a non-empty IPv4 address, default route, working DNS, and a successful HTTPS request.
3. The UI shows the same state as NetworkManager and does not show online from an interface flag alone.
4. Reconnect works after link loss and, if tested, after suspend/reboot.
5. Wrong password/AP absent/DHCP/DNS failures each produce a distinct actionable error.
6. No Wi-Fi credential or personal SSID is committed to Git.
7. The report labels source/tooling tests separately from the physical association and owner-visible result.

## Hardware, privilege and rollback safety
Do not install random firmware blobs or change radio calibration/partitions. Preserve the USB console and avoid killing the only network path remotely. Firmware changes require explicit owner approval and rollback.
Before a live-device step, capture boot mode, target model/variant, deployed hashes, service state, and a tested userspace rollback. Preserve the USB console and the existing 25% speaker-volume cap. Never surprise-flash, write bootloader/partitions, replace the kernel, change radio firmware, or strobe an LED/torch without explicit owner approval. A missing phone or missing owner observation remains `NOT TESTED` or `BLOCKED`.

## Deliverables
- A narrowly scoped implementation on `nuxel/r12-wifi-first-internet`, with tests and docs for this component only.
- `docs/component-reports/r12.md` containing: commit/tree state, changed files, observed pre-state, commands and exit codes, hashes, evidence-class matrix, owner test steps/results, rollback receipt, and unresolved blockers.
- A concise handoff stating exactly what is SOURCE VERIFIED, BUILT, DEPLOYED, OWNER-VERIFIED, BLOCKED, and NOT TESTED.

## Stop conditions / known blockers
Stop if the radio does not enumerate or firmware is absent; report BLOCKED_FIRMWARE with the exact missing path. Never claim internet access from a successful toggle or scan.
Stop rather than guessing if target identity, privilege, firmware/driver support, rollback availability, or physical safety cannot be established. A failed protected assertion must be triaged as stale versus regression with evidence; never convert it to a skip. This prompt authorizes no implementation, deployment, reboot, or release.
