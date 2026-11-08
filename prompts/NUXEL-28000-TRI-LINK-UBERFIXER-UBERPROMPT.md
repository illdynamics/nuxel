# 🐧 PWNAGE 28000 — NUXEL TRI-LINK CONSOLE UBERFIXER + HOME-UNLOCK FIX

## Mission

Work in the existing Nuxel repository and deliver a real, tested implementation—not just a design document—of a reliable **Tri-Link Console** for the Samsung Galaxy S10+ Exynos 9820 (`SM-G975F`, `beyond2lte`) and correct Nuxel's boot/unlock navigation so that **unlocking the lockscreen always lands on the Home desktop, never inside the Applications window/app drawer**.

The Tri-Link design must expose three distinct console launchers in the Nuxel **Applications window**:

1. **Serial Live Console** — the existing USB serial/Live Console path, retained as the low-level recovery route.
2. **USB SSH Console** — SSH over USB networking, only when the phone's existing kernel, USB gadget/controller, device configuration and host OS support it.
3. **Wi-Fi SSH Console** — SSH over the already-working Wi-Fi network, using the phone's real IP/interface and secure authentication.

All three must have separate, recognizable icons and labels in the Applications window, with truthful status and helpful errors. Do not represent an unavailable transport as connected or working. The three launchers must remain visible even if one transport is unavailable, with a clear unavailable/setup state rather than silently disappearing.

This prompt does not prove the phone has been fixed. Implement, test, and report exactly what the repository tests and physical-device checks establish.

---

## 0. Safety gates — do these first

1. Inspect repository root, current branch, `git status`, recent commits, existing console scripts, application catalog/launcher implementation, lockscreen/unlock path, shell navigation state, service definitions, USB/serial bridge, deployment scripts, and relevant tests before editing.
2. Check whether a previous deployment or another coding agent is actively using the physical S10+ serial port or performing a transaction. In particular, respect the PWNAGE 25000 console/deployment work and any in-progress GPS/map work. **Do not start a competing device deployment, seize the serial port, kill an active transaction, delete a lock, or overwrite uncommitted work.** If an active transaction is present, perform read-only audit only and clearly report the blocker; wait for safe completion before mutating overlapping files or deploying.
3. Keep exactly one owner of the physical serial stream at a time. Do not run serial and a second serial client concurrently. Use independent SSH transports where possible.
4. Preserve the currently bootable Nuxel image, Samsung-derived Linux 4.14 baseline, USB Live Console/recovery path, working Wi-Fi/DNS/TLS/browser, lockscreen artwork and animation, working charging indicator, and other established UI work. Do not flash a kernel, wipe partitions, reset the phone, or make unrelated modem/radio changes as part of this task.
5. Establish a rollback path before deployment: commit or checkpoint changes, retain previous config/service files, stage new files atomically, and record exact rollback commands. Never deploy blindly over a working recovery route.
6. Separate host-side tests from on-device tests. Never claim physical validation if the phone was not actually reachable and tested.

## 1. Audit the actual architecture before changing it

Trace these flows in the current source; do not assume file names or frameworks:

- How the Applications window discovers apps and constructs app icons/entries (`.desktop` files, a manifest, app registry, shell metadata, or another existing mechanism).
- How the current Serial Live Console launcher starts the bridge/client and acquires/releases serial ownership.
- How the phone's Wi-Fi connection and IP address are detected, and how the existing Nuxel bridge/services are discovered over D-Bus or another API.
- Whether an SSH server binary/service is already installed or built into the image, what init/service manager is used, and whether runtime package installation is possible. Do not assume DNF or OpenSSH server is installed on the phone.
- Whether the current kernel exposes USB gadget/configfs and a usable UDC, and whether ECM, RNDIS, or NCM is supported. Inspect the actual kernel config, sysfs/configfs, gadget setup scripts and host compatibility. Do not assume a USB network interface exists just because USB serial works.
- How the lockscreen reports successful unlock and how the shell chooses the initial route/view. Identify whether the Applications window is being restored as a stale route, persisted as the last view, treated as a boot default, or reopened by a startup callback.
- Existing app/window lifecycle, navigation and test patterns. Follow them rather than creating a parallel shell architecture.

Write a short audit summary in the final report, including the actual source paths and root causes found.

## 2. Tri-Link architecture

Implement three transport adapters behind a shared, explicit console-launch interface. Keep the existing code style and architecture wherever feasible; avoid a large rewrite.

### A. Serial Live Console — preserve and register

- Retain the existing, working serial Live Console behavior and its recovery purpose.
- Make it a proper, discoverable Applications-window entry named **Serial Live Console** with its own icon.
- Preserve exclusive serial-port ownership, lock acquisition/release, disconnect detection, cancellation, and useful diagnostics.
- If another process owns the port, show a clear busy/owner state; do not start a second reader/writer or kill the owner automatically.
- A failed new SSH transport must never break serial recovery.

### B. Wi-Fi SSH Console — first practical SSH transport

- Prefer this as the first SSH transport to implement because Nuxel Wi-Fi is already working, but re-verify current state rather than assuming.
- Provide a real SSH session into the phone's shell (a usable Bash session if Bash exists, otherwise clearly report the actual shell). Support file transfer through `scp`/SFTP and `rsync` only when the relevant tools exist; do not claim unsupported utilities are available.
- Detect the active Wi-Fi interface and address dynamically. Do not hardcode a guessed IP, subnet, gateway, username, or interface name. Handle DHCP address changes and Wi-Fi loss gracefully.
- Audit how OpenSSH server or an existing SSH daemon can be supplied by this image. Prefer the existing packaged/service mechanism. If the required server is missing and cannot be safely installed with available tools, implement an honest setup/check path and document the missing dependency; do not fake a successful connection.
- Use key-based authentication by default. Avoid root password login, default/shared credentials, storing private keys on the phone, or weakening system-wide SSH policy. Verify host keys and explain first-use trust; do not silently disable host-key checking.
- Bind to the Wi-Fi/LAN interface only as intended, and apply an appropriate firewall/access policy if the OS has one. Do not expose SSH to the public internet, open router ports, configure port forwarding, or broaden network access without explicit operator intent.
- Show the connection target and state: unavailable, checking, ready, connecting, connected, disconnected, or failed. Display actionable error details without leaking secrets.
- Do not run a privileged command or mutate network configuration merely because the launcher is opened.

### C. USB SSH Console — capability-gated

- Inspect the real Samsung-derived Linux 4.14 kernel, USB controller/UDC, gadget support, device-tree/configuration and host behavior before implementation.
- Check the available gadget mechanisms and configs (including, where relevant, `CONFIG_USB_CONFIGFS`, `CONFIG_USB_CONFIGFS_ECM`, `CONFIG_USB_CONFIGFS_RNDIS`, `CONFIG_USB_CONFIGFS_NCM`, legacy gadget drivers, and an actual UDC). These names are investigation targets, not proof that support exists.
- Select a USB Ethernet gadget mode that is genuinely supported by the phone and the target host operating systems. Consider Fedora and macOS compatibility based on observed support, not guesswork. Do not break the existing USB serial/Live Console or charging/data mode.
- Avoid hardcoded IP addresses or subnets that could collide with an existing network. Choose and validate a safe link-local/private link configuration, and document how the host finds the device. Avoid DHCP conflicts and do not route the phone's Wi-Fi or general internet traffic over USB.
- Establish SSH over the USB network interface only after the interface and route are actually present. USB SSH must be independent of the serial stream; it must not try to open or read the serial port.
- If the current kernel or gadget stack cannot support a safe implementation, keep the USB SSH launcher visible with a truthful “unsupported on this build” diagnostic and a clear report of the missing capability. **Do not flash or rebuild the kernel in this task just to make USB SSH appear to work.**
- Reversible gadget configuration only; preserve USB recovery and normal phone functions. On disconnect, clean up only resources created by this feature and do not disrupt the serial route.

## 3. Three real icons in the Applications window

The Applications window must visibly contain exactly the three intentional console entries described above, using the existing Nuxel app-discovery mechanism:

- **Serial Live Console** — serial/USB serial recovery.
- **USB SSH Console** — SSH over USB networking.
- **Wi-Fi SSH Console** — SSH over Wi-Fi.

Requirements:

- Each is a distinct app entry with its own recognizable icon, title and concise description. Prefer existing Nuxel icon/asset conventions and reuse existing assets where appropriate; do not invent asset paths without checking them.
- Distinguish them visually (for example serial connector, USB/network link, Wi-Fi waves) while matching the current Nuxel styling. If the app catalog supports status indicators, use them; otherwise show status in the launch view.
- All three remain listed even if a transport is unsupported or not configured. The user should be able to open each entry and learn what is missing.
- Clicking each icon launches the corresponding transport's own view/workflow, not the same generic serial console for all three.
- Avoid duplicate icons from multiple manifests, broken `.desktop` entries, missing icon resources, or launch commands that only work from the repository root.
- Check keyboard/touch activation and portrait layout on the S10+.
- If there is a tests/fixture catalog, assert all three identifiers are registered exactly once and each maps to the correct transport handler.

## 4. Fix boot → lockscreen → unlock → Home desktop

**Required user-visible behavior:** after Nuxel boots, the lockscreen appears according to the current design. After a successful unlock, the user lands on the primary **Home desktop**, not inside the Applications window/app drawer.

Trace and fix the root cause, not merely the appearance. Requirements:

1. Identify the canonical Home route/view/state in the current shell. “Home” means the primary desktop/home surface, not the Applications window, app grid, tabs view, or whichever view happened to be open before reboot.
2. On successful unlock after boot, explicitly navigate to that canonical Home state through the shell's supported navigation mechanism. Do not simulate Home by hiding the app drawer while leaving the internal route unchanged.
3. Prevent stale or persisted application-window state from overriding Home during the boot/unlock transition. Inspect state restoration, route persistence, default view, startup handlers, lockscreen callbacks, and race conditions between shell initialization and unlock. Apply the smallest robust fix.
4. Ensure the transition happens only after successful unlock. Failed unlock attempts must not navigate to Home or bypass the lockscreen.
5. Define behavior for cold boot, warm reboot, screen-off/lock timeout, manual lock, app drawer open before locking, and returning from a background app. The explicit requirement is that the first successful unlock following boot ends at Home. Do not unexpectedly terminate apps or erase unrelated user state.
6. Keep the existing lockscreen artwork, lockhead interaction/animation, timeout behavior, bottom navigation and status indicators intact unless a directly related bug must be fixed.
7. Avoid a flash of the Applications window between unlock and Home. Make initialization deterministic and prevent competing startup callbacks from reopening the app drawer.
8. Add unit/integration tests for the navigation state machine and a reproducible manual acceptance procedure on the physical device.

## 5. Shared console UX and reliability

- Each console view must state which transport it is using and its current state.
- Provide clear Start/Connect, Disconnect/Stop and Retry actions where appropriate. Disable impossible actions during transitions.
- Do not show “connected” until the actual session is established and a real command/session check succeeds.
- Handle timeout, auth rejection, host key mismatch, missing service, missing binary, Wi-Fi drop, USB unplug, remote process exit, and permission errors without hanging the shell.
- Bound retries and use cancellation correctly. A cancelled SSH launch must not leave orphaned processes or sockets. Closing a window must not kill unrelated system services.
- Log useful diagnostics with secrets, private key material, passwords, tokens and sensitive command output redacted.
- Use a common transport interface for status/start/stop/diagnostics, but keep serial, USB networking and Wi-Fi SSH mechanisms separate enough that one broken transport cannot take down the others.
- Keep the system single-user/single-device assumptions explicit if the current project has them; do not create an unauthenticated network shell.

## 6. Implementation sequence

1. **Baseline:** inspect status and active deploys/agents; record current behavior and run the most relevant existing tests.
2. **Navigation root cause:** fix and test successful unlock → Home independently, before mixing in transport changes.
3. **Launcher registration:** add the three distinct Applications-window entries and verify each opens its correct screen/adapter.
4. **Serial regression protection:** confirm the current serial console remains operational and exclusive.
5. **Wi-Fi SSH:** audit dependencies and implement the secure, real session path; test authentication, disconnect/reconnect and transfer capabilities that actually exist.
6. **USB SSH:** implement only if supported by the existing hardware/kernel/host combination; otherwise provide a truthful unavailable state and evidence.
7. **Integration:** verify all three icons, status/error handling, lockscreen/home transition, and no conflicts among services or transports.
8. **Device verification:** only when safe and the S10+ is connected. Deploy through the established single-owner workflow; never compete with another active serial transaction.
9. **Report:** summarize changes, tests, real-device evidence, remaining blockers and rollback steps.

## 7. Tests and acceptance criteria

### Automated tests

Add or update tests consistent with the repository's existing framework. At minimum cover:

- All three console app IDs/entries appear exactly once and have unique labels/icons and correct handlers.
- Each launcher selects the intended transport and unsupported transports show truthful diagnostics rather than fake success.
- Serial port lock contention prevents a second owner and preserves the existing session.
- Wi-Fi SSH address/interface discovery is dynamic; missing daemon, failed auth, host-key mismatch, timeout and disconnect are handled safely.
- USB transport refuses to claim readiness when gadget support, UDC, interface, route or SSH endpoint is absent.
- Cleanup removes only resources created by the USB feature and does not disturb serial console operation.
- Successful unlock after cold boot transitions to Home, including when Applications was the prior persisted view.
- Failed unlock does not navigate to Home.
- No transient or race-driven return to the Applications window after Home is selected.
- Existing tests for lockscreen, navigation, Wi-Fi, browser and console continue to pass.

### Physical S10+ acceptance checklist

Record each as PASS / FAIL / BLOCKED with exact evidence:

- [ ] Boot Nuxel; lockscreen appears normally.
- [ ] Unlock; primary Home desktop appears, not the Applications window.
- [ ] Repeat after reboot with Applications window selected before reboot, if that state can be reproduced.
- [ ] Open Applications; see all three console icons, exactly once each.
- [ ] Launch Serial Live Console and verify a real session without a competing serial owner.
- [ ] Launch Wi-Fi SSH and verify a real authenticated shell command returns expected output.
- [ ] Verify SSH host key/authentication behavior and test disconnect/reconnect.
- [ ] Launch USB SSH. If supported, verify a real USB network interface and SSH session; if unsupported, capture exact capability evidence and show the honest unavailable state.
- [ ] Unplug/reconnect USB and confirm no stale connected indicator, orphaned process, broken charging, or broken serial recovery.
- [ ] Verify Wi-Fi, DNS, TLS/browser, lockscreen art/animation, charging indicator and bottom navigation have not regressed.

A host-only mock test is not a physical-device PASS. Clearly label skipped or blocked hardware tests.

## 8. Scope limits and prohibited shortcuts

- No kernel flash, partition wipe, bootloader changes, repartitioning, factory reset or unrelated firmware changes.
- No fake GPS/location data, no unrelated GPS work in this task.
- No weakening SSH host-key validation, no hardcoded/default passwords, no public SSH exposure, no unauthenticated shell.
- No duplicate concurrent serial access, killing active deployment processes, deleting locks to “unstick” a live transaction, or reporting success based only on process exit without verifying the service/session.
- No unrelated redesign of the UI, lockscreen or app system.
- Do not assume `systemd`, DNF, Bash, OpenSSH, `rsync`, a specific interface name, or USB gadget features exist; inspect and report actual availability.

## 9. Final deliverables

Make the code changes and tests. Then provide:

1. Root-cause summary for the unlock-to-Applications bug.
2. Changed file list and concise explanation of each change.
3. The exact three app IDs/labels/icon resources and how the Applications window discovers them.
4. For each transport: implementation status, required components, exact launch behavior, and test evidence.
5. Commands run and results (pass/fail/blocked), including regressions.
6. Physical-device evidence separated from host-only tests.
7. Known limitations, especially any kernel/gadget blockers for USB SSH.
8. Safe deployment and rollback instructions.
9. Confirmation that the serial recovery path remains preserved and no kernel/partition flashing was performed.

**Definition of done:** successful unlock lands on Home; the Applications window displays three distinct, working-or-honestly-unavailable console launchers; serial recovery is preserved; Wi-Fi SSH is a real secure shell if the current image supports it; USB SSH is real only if hardware/kernel support is verified; tests and evidence are reported without exaggeration.

