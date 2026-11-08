# PWNAGE 26000 — MINI KICKSTARTER 🐧

Implement Nuxel Tri-Link Console Revolution in this repository.

First perform a read-only audit of the repository, device capabilities and current PWNAGE 25000/deployment state. If another agent or deployment is active, do not mutate the phone or contend for serial. Preserve the existing serial Live Console as the recovery route.

**First: WLAN SSH.** Audit the actual userspace and provision a supported SSH server. Implement key-based authentication, host-key verification, a real interactive shell, useful connection diagnostics and verified file transfer over Nuxel's existing Wi-Fi. Do not enable root password login or public Internet exposure.

**Second: USB-network SSH.** Audit the Samsung Galaxy S10+ SM-G975F / beyond2lte's current Samsung-derived Linux 4.14 kernel, gadget configuration, USB controller and actual Fedora/macOS host compatibility. Implement a compatible USB Ethernet mode only if it can coexist safely with serial. Test SSH with phone Wi-Fi disabled. Do not flash or rebuild the kernel as part of this task.

**Third: Tri-Link manager.** Add explicit serial, USB and WLAN transport selection plus a clearly reported `auto` mode. Keep transport adapters separate, preserve exit codes, support safe verified transfers, and prevent concurrent serial writers or conflicting deployments. Inspect PWNAGE 25000's real state and reuse proven transaction/reload/rollback code rather than duplicating it.

Add automated tests for authentication, host-key mismatch, network loss, missing USB capabilities, transfers/checksums, exit codes, locks, deployment conflicts, reconnect and rollback. Run relevant project tests.

Report exact files changed, test commands/results, real-device evidence, blockers and rollback instructions. Clearly distinguish unit tests from physical Samsung Galaxy S10+ tests. Never claim a transport works without actually verifying it.

Read `NUXEL-26000-TRI-LINK-CONSOLE-REVOLUTION-UBERPROMPT.md` for the complete specification.

Launch:
`csft "$(cat ./pwnage-26000.md)"`

Or:
`codex --model gpt-5.6-sol -c 'model_reasoning_effort="high"' --sandbox workspace-write "$(cat ./pwnage-26000.md)"`
