# 🐧 PWNAGE 26000 — NUXEL TRI-LINK CONSOLE REVOLUTION

## Mission

Upgrade Nuxel's development and recovery access by building a second-generation SSH console alongside the existing serial Live Console. Deliver three distinct access paths:

1. **Live Console — Serial:** existing low-level recovery and boot diagnostics.
2. **Live Console 2 — USB Network + SSH:** a real interactive shell and file transfer over USB Ethernet, where the existing kernel and hardware support it.
3. **Live Console 3 — WLAN + SSH:** a real interactive shell and file transfer over the phone's existing Wi-Fi connection.

The goal is a robust, maintainable Tri-Link architecture—not three names for the same fragile connection.

**Target:** Samsung Galaxy S10+ SM-G975F / beyond2lte, Exynos 9820, current Samsung-derived Linux 4.14 kernel, running Nuxel's Fedora-based ARM64 userspace.

**Repository:** `github.com/illdynamics/nuxel`

## PHASE 0 — Protect existing work

Before modifying anything:

- Inspect the repository, current branch, dirty working tree, existing console scripts, bridge code, deployment scripts, systemd units, package manifests, tests and documentation.
- Determine the actual status of PWNAGE 25000 and any deployment or agent currently operating on the physical phone.
- If a deployment is active or its status is ambiguous, perform read-only inspection only. Do not start another deployment, kill an unclear process, remove a lock or seize the serial port. Wait for operator confirmation before conflicting mutations.
- Preserve all user modifications and the existing serial recovery route.
- Maintain a single owner for the physical serial stream. Never let two processes or agents write to it concurrently.
- Keep the current kernel. Do not flash a kernel, repartition, wipe user data or modify unrelated Wi-Fi, browser, lockscreen, GPS, modem, charging or UI functionality.
- Record the baseline and create reversible backups before changing device configuration.
- Never report a test as passed unless it was actually run.

## PHASE 1 — Audit the current capabilities

Produce a capability report before implementation.

Inspect:

- Existing serial-console launcher, serial transport protocol, locking and deployment workflow.
- Whether an SSH server is already available: OpenSSH, Dropbear, BusyBox or another implementation.
- Available package manager, installed packages, init/service manager, network utilities, firewall configuration and account model. Do not assume DNF, systemd or any specific command exists.
- Wi-Fi interface, assigned IP address, routes and current connectivity.
- USB controller, gadget framework, available USB functions and relevant kernel configuration.
- Existing support for `CONFIG_USB_CONFIGFS`, CDC ECM, RNDIS, NCM or other network gadget modes, using real system evidence.
- Host compatibility on the available Fedora laptop and Mac.
- Existing tests and the actual state of PWNAGE 25000's deployment and transaction improvements.

For each link, report `AVAILABLE`, `UNAVAILABLE` or `UNKNOWN`, with supporting evidence. Do not assume that a USB cable automatically provides an IP network.

## PHASE 2 — Build WLAN SSH first

Wi-Fi has been reported working, making WLAN SSH the first practical route to implement.

### SSH service

- Reuse existing Nuxel account and service conventions where possible.
- Provision a suitable SSH server through a supported and reversible mechanism.
- If installation is impossible, explain the actual blocker instead of downloading unverified binaries or inventing a package manager.
- Use public-key authentication. Keep private keys on the development host.
- Do not enable root password login, blank passwords or unrestricted guest access.
- Preserve a stable SSH host key and display its fingerprint for verification.
- Never silently accept a changed host key or disable host-key checking.
- Restrict access to the intended local WLAN and existing firewall policy. Do not expose SSH to the public Internet.
- Keep SSH failures from blocking boot or breaking Wi-Fi.

### Host-side launcher

Implement a launcher following the repository's actual naming conventions. The proposed interface is:

`./nuxel-live-ssh.sh --transport wlan`

The launcher must:

1. Discover the phone's address or accept an explicit, validated target; never guess an IP.
2. Verify the SSH host key.
3. Authenticate with the configured account and key.
4. Open a genuine interactive Bash shell where Bash is installed, or clearly report the available shell.
5. Preserve terminal allocation, terminal resizing, signals, exit status and error output.
6. Distinguish Wi-Fi failure, missing route, timeout, refused connection, authentication failure and host-key mismatch.
7. Support secure file transfer through SFTP or `scp`; support `rsync` only if both endpoints have it.
8. Provide bounded retries and clean cancellation.
9. Never silently switch to serial or USB and misrepresent which transport is active.

### WLAN acceptance tests

On the actual development host and phone:

- Establish an authenticated interactive shell over Wi-Fi.
- Run harmless diagnostic commands and verify that non-zero command exit status is preserved.
- Transfer a test file to a staging directory and back, comparing SHA-256 hashes where available.
- Verify that an unauthorized key is rejected.
- Confirm host-key mismatch produces a clear warning.
- Verify that root/password login has not been enabled.
- Restart or stop the SSH service and confirm that connection status is reported accurately.
- Verify that serial recovery remains available independently.

A ping, open port, service file or unit test does not prove WLAN SSH is operational.

## PHASE 3 — Build USB Network + SSH

Only proceed after auditing the existing Samsung-derived Linux 4.14 kernel and USB gadget stack.

### Capability requirements

Determine which USB networking mode is actually supported and compatible with the available host. Evaluate ECM, RNDIS, NCM or another mode only where evidence supports it.

Check whether the phone's existing USB configuration can expose networking while preserving the current serial function. Identify conflicts with other gadget functions and host-specific behavior.

### Implementation requirements

- Treat USB Ethernet as an independent network interface and SSH as a service operating over that interface.
- Preserve the existing serial function.
- Do not assume macOS and Fedora support identical gadget modes.
- Select addresses only after checking for route and subnet conflicts.
- Avoid changing the host's default route or disrupting the phone's WLAN connectivity.
- Restrict SSH access on the USB interface appropriately.
- Make configuration idempotent, observable, reversible and limited to resources owned by this feature.
- If kernel support is missing, document the exact missing capability and evidence. Do not flash or rebuild the kernel in this mission.

### USB acceptance tests

- Confirm both phone and host detect the USB network interface.
- Verify non-conflicting addresses and the intended route.
- Disable phone Wi-Fi and establish a real interactive SSH shell over USB.
- Transfer a representative file in both directions and verify its hash.
- Confirm that serial remains available.
- Test disconnect and reconnect behavior.
- Record which host operating systems were actually tested.

If the existing kernel cannot safely support USB networking alongside serial, report the blocker honestly. Do not fake a third working link.

## PHASE 4 — Create the Tri-Link transport manager

Once WLAN SSH works and USB networking has been verified or explicitly marked blocked, implement a thin transport-selection layer.

Desired interface, adapted to project conventions:

- `./nuxel-live.sh` — existing serial recovery console.
- `./nuxel-live-ssh.sh --transport wlan` — WLAN SSH.
- `./nuxel-live-ssh.sh --transport usb` — USB-network SSH.
- `./nuxel-live-ssh.sh --transport auto` — explicit discovery and selection.

These are proposed interfaces, not claims that these scripts already exist.

Requirements:

- Keep serial, USB networking and WLAN as separate transport adapters.
- `auto` must show discovery results and the selected transport before connecting.
- Never silently switch transports when doing so could confuse debugging or deploy to the wrong endpoint.
- Report transport, target, account and connection state without exposing secrets.
- Distinguish SSH service restarts, bridge restarts, Wi-Fi loss, USB re-enumeration and actual phone reboots.
- Preserve command exit codes, stderr, path quoting and cancellation behavior.
- Reuse proven shared deployment logic where practical, but do not duplicate the low-level serial protocol inside SSH code.
- SSH should not depend on `nuxel-bridge` being healthy if a separately managed SSH service is practical.
- Avoid holding a serial lock during SSH operations.
- Refuse conflicting deployments rather than allowing two transport paths to mutate the same transaction concurrently.

## PHASE 5 — Integrate with deployment safely

Inspect the real PWNAGE 25000 implementation before integrating. Determine whether its changes are present, complete, active or still in progress.

Reuse existing transaction, validation, service-reload, rollback and progress-reporting mechanisms where proven.

- Stage files before activation.
- Verify staged content before replacing live files.
- Use checksums where available.
- Restart each affected service at most once per transaction, not once per file.
- Do not restart unrelated services.
- Report failures and rollback outcomes explicitly.
- Never deploy concurrently through serial and SSH to the same target transaction.
- Preserve recovery access throughout the deployment.

Do not assume PWNAGE 25000 is complete just because its prompt exists.

## PHASE 6 — Tests and failure handling

Add automated tests for:

- Explicit transport selection and `auto` reporting.
- Missing SSH client or server.
- Authentication failure and host-key mismatch.
- WLAN route loss, connection refusal and timeout.
- Missing or unsupported USB gadget networking.
- Interrupted transfers, hash mismatch and safe staging cleanup.
- Remote command quoting and exit-code preservation.
- Serial lock contention and prevention of concurrent serial writers.
- Existing deployment conflicts.
- Service restart versus actual reboot detection.
- Bounded retry, cancellation and reconnect behavior.
- Rollback and preservation of configuration.
- Preservation of the serial recovery path.

Run the relevant existing tests, lint and packaging checks. Do not delete failing tests or weaken acceptance criteria to get a green result.

Keep unit tests, host integration tests and physical-device tests separate in the report.

## PHASE 7 — Recovery procedure

Before device mutations:

1. Record original configuration and file hashes.
2. Save reversible backups.
3. Verify that the existing serial recovery route is available.
4. Apply one small change at a time.
5. Test immediately after each change.
6. Roll back the last change if it breaks access.

If SSH fails, use the established serial recovery route only when no other process owns it. Do not launch competing serial sessions.

## REQUIRED FINAL REPORT

Report:

1. Exact files changed and behavior implemented.
2. WLAN SSH status: `PASS`, `FAIL`, `BLOCKED` or `NOT RUN`, with evidence.
3. USB-network SSH status and the actual kernel/host compatibility evidence.
4. Whether USB SSH succeeded with phone Wi-Fi disabled.
5. Serial-console status before and after changes.
6. Transfer integrity and deployment/rollback test results.
7. Exact test commands and pass/fail counts.
8. Known limitations and security implications.
9. Manual device steps, only if necessary.
10. Exact rollback instructions.

Do not claim Tri-Link is complete unless all three links have passed their real-device acceptance tests. If USB is unsupported, state that serial plus WLAN SSH works only if verified, and that the third link remains incomplete.

## DEFINITION OF DONE

- Serial remains a dependable recovery route.
- WLAN SSH provides a verified interactive shell and safe file transfer, or its blocker is proven.
- USB-network SSH works independently of Wi-Fi, or its kernel/hardware blocker is precisely documented without flashing the kernel.
- Transport selection is explicit, diagnostics are useful and deployment is protected against concurrency.
- Tests and physical-device evidence are reported honestly.
- Recovery and rollback instructions are complete.

**Priority:** protect serial → prove WLAN SSH → audit and implement USB networking → unify transports → test failure recovery.

🐧 **Serial for survival. USB for speed. WLAN for freedom. Three links, one Nuxel.**
