# 🐧⚡ NUXEL A74 / 23000 — OPERATION USB UNPLUG PWNAGE

## REMOVE THE PC CABLE. NOT THE ENTIRE OPERATING SYSTEM.

**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820. Existing Nuxel Fedora ARM64 userspace and known-good downstream Linux 4.14 kernel.  
**Execution:** Work in the owner's CURRENT repository and against the CURRENT deployed phone. Use the strongest available coding/reasoning model.  
**Mission type:** Crash/root-cause investigation, narrow repair, safe deployment, and physical unplug/replug verification.

## 0. Exact owner report and non-negotiable acceptance contract

The owner reports that **all USB/charging/PC/Live Console penguin indicators now work properly**, but **when the USB cable connecting the phone to the computer is physically disconnected, the phone hangs and reboots**.

Treat this as a newly exposed, high-priority stability regression. Do not assume the icon code itself causes the reboot; prove the causal path with evidence. Do not assume it is software-only; distinguish userspace crash/reboot, kernel panic/oops/watchdog, power/PMIC/battery behavior, and a UI-only hang with the system still running.

### Required final behavior

1. While connected to the computer, the expected PC-connected and Live Console states work exactly as they do now.
2. On physical PC-cable detach, the connection state changes cleanly; the PC and Live Console indicators become OFF according to the established semantics; the phone remains running and responsive.
3. **No hang, kernel panic, watchdog reboot, userspace-triggered reboot, compositor restart loop, or forced restart is permitted as a normal consequence of USB detach.**
4. Reconnecting the computer works normally and restores the expected indicators and console functionality.
5. Repeated unplug/replug cycles do not accumulate stale sessions, zombie processes, blocked I/O, memory leaks, or restart loops.
6. Charging indicator behavior, its artwork/animation/position/size, PC indicator behavior, Live Console indicator behavior, Quick Settings Bluetooth and Location functionality, Wi-Fi, DNS/TLS, browser, lockscreen, launcher/navigation, Camera and SnekByte must not regress.
7. Preserve the existing Linux 4.14 kernel baseline. Do not flash a kernel, bootloader, DTB, modem firmware, or partitions as part of this task.

**Definition of done:** the physical detach test passes and evidence shows that the same boot continues across detach. A unit test or a source-only patch is not enough to claim the physical bug is fixed.

---

## 1. Safety rules — read before touching the phone

- First establish how the agent currently reaches the device: USB Live Console, SSH over Wi-Fi, another network path, or a combination. **Do not pull the only access cable without an owner-approved test plan and a way to recover evidence.**
- Do not restart/stop the only working console, bridge, network, compositor, or gadget service while depending on it as the only recovery path.
- Before changing anything, capture `git status`, branch/HEAD, diffs, installed file hashes, boot ID, uptime, kernel release, service state and available recovery method. Make a branch/worktree and narrow backups of only the files/units you change.
- Never run `reboot`, `poweroff`, `systemctl reboot`, or a destructive USB reset from an unplug handler as a “recovery” for a disconnected console. Never convert normal disconnect into reboot.
- Do not hide the symptom by disabling kernel panic evidence, disabling the watchdog, suppressing USB detach, pinning the UI in a stale connected state, or leaving the console gadget stuck bound forever. Do not add arbitrary sleep loops to mask a race.
- Do not run multiple agents that can write to or deploy to the phone simultaneously.
- Do not mass-upgrade packages or change kernel/boot configuration before the evidence points to that layer. Any systemd unit, udev rule, gadget script or privileged service change needs a rollback path.
- Do not expose secrets, Wi-Fi credentials, tokens, full user data or precise location in logs. Redact identifiers where feasible.
- If a physical test cannot safely be performed, implement diagnostics and host-side tests, label hardware validation `NOT_TESTED`, and ask the owner for the exact next physical step. Do not claim success.

## 2. Source and deployment reconnaissance (historical leads only)

The archive available during prompt preparation, `nuxel-main (4)(1).zip`, contains useful historical leads, but the live checkout/deployment may be newer. Re-inspect current HEAD and deployed bytes before editing. Likely relevant paths include:

- `services/nuxel-console/systemd/nuxel-console.service`
- `services/nuxel-console/README.md`
- `services/nuxel-bridge/src/system_indicators.py`
- `services/nuxel-bridge/systemd/nuxel-bridge.service`
- `tools/s10plus/a17/nuxel-usb-monitor.py`
- `tools/s10plus/a17/usb-watch.sh`
- `tools/s10plus/a17/nuxel-console.c`
- `tools/s10plus/a18/`, `tools/s10plus/a19/`, `tools/s10plus/a24-nuxel-console.c`, and `tools/s10plus/a33/nuxel-console.c`
- USB/gadget setup scripts, systemd units/drop-ins, udev rules, console lease/session files, service watchdogs, startup scripts, deployment scripts and any code reacting to UDC or power-supply changes.

These are search leads, not proof of cause. Search the current repo for all USB detach/attach handling, gadget bind/unbind operations, `ttyGS0`, `nuxel-console`, session leases, `Restart=`, `OnFailure=`, reboot/poweroff commands, watchdog handling, `panic`, `oom`, `systemctl`, udev rules, netlink/uevent consumers and teardown callbacks. Also inspect generated or installed copies: the crashing behavior may come from a deployed file that differs from Git.

Produce a repo-to-device mapping for every relevant file/unit:

`repo path | deployed path | source SHA-256 | deployed SHA-256 | owning service/process | reload/restart method | rollback method`

Do not blindly deploy an old ZIP over the working phone.

---

## 3. Capture the failure before attempting a repair

### 3.1 Record a clean baseline

Before the next owner-approved detach test, capture to a **durable local phone directory** (for example a dated folder under `/var/lib/nuxel/diagnostics/usb-unplug/`, after checking filesystem capacity and permissions):

- timestamp, boot ID (`/proc/sys/kernel/random/boot_id`), uptime, boot time and kernel release;
- `uname -a`, kernel command line, available `/sys/fs/pstore` and ramoops contents, `last -x` if available, previous-boot journal availability, and whether journald is persistent;
- `dmesg`/kernel journal tail and relevant kernel config/sysctl values, including panic-on-oops, panic timeout, watchdog and reboot reason sources **read-only first**;
- battery voltage/current/capacity/status, external power-supply state, USB controller and UDC state, gadget UDC binding, configfs and/or Android USB state, relevant Type-C/data-role state if exposed, and console TTY state;
- service state, main PID, cgroup, restart counters, `NRestarts`, recent journal for console, bridge, gadget setup, USB monitor, systemd-udevd, network, compositor/session and any watchdog service;
- current indicator JSON/API result and current console transport/session state;
- process tree and file descriptors for console-related processes, without dumping unrelated user data.

Capture a short rolling log immediately before, during and after detach. Use bounded, rate-limited logs. Avoid a high-frequency poller that itself causes CPU, storage or power problems. If journald is volatile, create a small, bounded durable evidence mechanism or a narrowly scoped diagnostic service/script that appends timestamped state snapshots to local storage and rotates them. Do not rely on the host receiving logs over the very USB cable being removed.

Check `pstore`/ramoops **after reboot** before any cleanup. Preserve crash evidence; do not clear it automatically.

### 3.2 Perform one controlled detach, with independent evidence

Only after an alternate recovery path is confirmed, have the owner disconnect the PC cable. The diagnostic should write a marker immediately before the expected event, then collect available evidence without requiring the USB console. Wi-Fi/SSH may be used if verified stable. Record:

- exact timestamp of physical disconnect (owner observation or host-side USB event);
- last UDC/gadget/Type-C/power-supply states before detach and first states after detach;
- whether the `nuxel-console` process exits, blocks, crashes, or remains alive;
- service restart events, signals, exit codes, coredumps, kernel messages, watchdog reports, OOM events, systemd jobs and reboot requests;
- last boot ID and uptime before disconnect, and boot ID/uptime after the device returns;
- whether only the UI hangs or the whole system stops responding (test network reachability and a safe remote health probe where possible).

**Do not run an uncontrolled series of unplug tests until the first failure has been captured.** If the phone immediately reboots and logs are unavailable, use the next boot to recover pstore/previous-boot records, then add better bounded logging before retrying.

### 3.3 Determine which failure class is actually happening

Classify with evidence; more than one may apply:

- **Kernel panic/oops:** pstore/ramoops, panic trace, kernel log tail, watchdog reason, or reboot reason supports it.
- **Watchdog reset / kernel stall:** watchdog/lockup trace, missed heartbeat, scheduler stall, or hardware reset evidence supports it.
- **Userspace-initiated reboot:** audit/journal/process evidence identifies the caller, unit, script, D-Bus request, or `systemctl` invocation.
- **Console teardown race:** detach causes concurrent close/unbind/session cleanup, blocked I/O, double-close/use-after-free, lock inversion, SIGPIPE/EPIPE/IO errors treated as fatal, or a teardown callback restarting/shutting down a broader service.
- **Systemd/udev restart loop:** a disconnect-triggered unit repeatedly restarts, pulls in a target, or fires an `OnFailure`/`ExecStopPost`/`BindsTo`/`PartOf`/`Requires` relationship with unintended consequences.
- **Power/PMIC/battery issue:** measured battery voltage/current/power-supply transitions or reset-reason evidence correlates with detach. Remember that removing USB input should normally transition to battery operation; do not assume a power issue without evidence.
- **UI-only hang:** device remains reachable, boot ID and uptime continue, services/kernel progress, but Wayland/PWA/bridge locks up. Fix the real blocking path, not the icon.
- **Unknown:** retain the evidence, improve instrumentation and do not guess.

Do not label a reset a “kernel panic” merely because the phone reboots. Use `PASS`/`FAIL` labels only for what the evidence establishes.

---

## 4. Investigate the full USB detach lifecycle

Trace the actual path from the hardware event through the kernel and userspace. Draw a concise sequence diagram in the report:

`physical detach → kernel/UDC/Type-C/power event → uevent/netlink/sysfs observer → gadget/session handling → nuxel-console → bridge/indicator refresh → UI`

For each transition, record which process owns it, whether it runs synchronously in an event callback, and whether it can block, unbind a gadget, close a descriptor, wait for a child, restart a service or invoke a reboot.

### Specific failure patterns to test

1. **Blocking read/write on `ttyGS0`:** a console worker waits forever after carrier/device disappearance; shutdown waits for the worker and blocks systemd or the session. Ensure I/O handles disconnect/error non-fatally and all waits have correct cancellation/timeouts.
2. **Close/unbind race:** two event paths both close a descriptor, free session state, unbind configfs, or remove the same lease. Make teardown idempotent and serialize ownership.
3. **Detach incorrectly treated as fatal:** `EIO`, `ENODEV`, `EPIPE`, `ECONNRESET`, `POLLHUP`, `POLLERR`, zero-length read, HUP/EOF or a missing TTY is converted into a fatal assertion, broad service shutdown or reboot. A normal disconnect should be an expected state transition.
4. **Restart storm:** systemd `Restart=always/on-failure`, watchdog wrappers, shell loops or udev rules repeatedly respawn console/gadget setup during detach. Inspect `RestartSec`, start limits, unit dependencies and `NRestarts`.
5. **Wrong service coupling:** console session is tied to `default.target`, graphical session, network target or system power target using `BindsTo`, `PartOf`, `Conflicts`, `OnFailure`, `ExecStopPost` or an overly broad dependency. A USB transport loss must not stop/restart the OS or core graphical session.
6. **Re-entrant gadget reconfiguration:** multiple services unbind/rebind the UDC at once, or an indicator/monitor callback changes gadget state when it should only read it. Keep monitoring/read-only status code separate from gadget ownership.
7. **Deadlock / lock inversion:** one thread holds a session/TTY/gadget mutex while waiting for an event that needs the same lock; shutdown waits for worker join while worker is blocked on disconnected I/O.
8. **Unsafe child-process cleanup:** kill a process group or PID that has been reused, terminate a parent/systemd process, or kill all processes holding the TTY. Use exact process ownership, pidfd/identity checks where supported, and bounded graceful shutdown.
9. **Power-supply event mishandling:** detach changes `online` to 0 and an observer wrongly treats this as low battery, critical power, or system shutdown. Keep charger state distinct from battery health and USB data-link state.
10. **Kernel / vendor USB path:** if evidence points to a 4.14 downstream driver or UDC crash, collect the trace and identify the exact driver/callback. Do not attempt a kernel replacement as the first response. Make a narrowly scoped userspace mitigation only if it is safe and honest, and document the kernel-level blocker.
11. **Watchdog / hardware reset:** do not disable the watchdog as a workaround. Determine why the heartbeat is missed; fix the stall or provide a clearly documented, minimal mitigation only with evidence and rollback.
12. **Logging and storage:** ensure the diagnostic mechanism cannot block the event path, fill storage, or keep a synchronous disk write inside a critical USB callback. Event handlers should queue bounded work and return promptly.

### Required design properties for the repaired path

- Detach is idempotent and safe to receive more than once.
- USB data disconnect changes transport/session state; it does **not** imply poweroff/reboot or failure of the whole OS.
- Console daemon/service lifetime is distinct from one attached host session. Do not terminate the daemon merely to hide an indicator; do not leave a fake active session either.
- Stop/close operations have bounded timeouts, cancellation and error handling appropriate to the actual APIs used.
- The service can restart/reconnect cleanly after a disconnect, with no duplicate readers/writers or stale lease/PID state.
- Indicator code remains a consumer of authoritative state, not an owner of USB gadget configuration.
- Avoid hidden state: report the last transition, reason, source and timestamp for the console transport/session where safe.
- Do not introduce an endless busy loop, excessive polling, or unbounded journald output.

---

## 5. Implement a minimal, evidence-led fix

After the first useful evidence capture:

1. Write a short root-cause hypothesis ranked by evidence and explicitly state what would falsify each hypothesis.
2. Add a regression test reproducing the observed failure class. If the actual kernel event cannot be reproduced in a host test, add realistic fault-injection tests for disconnect/HUP/EIO/ENODEV, partial teardown, duplicate detach, rapid detach/reconnect, and service restart races.
3. Patch the narrowest layer responsible. Prefer correcting the detach/session lifecycle over changing the whole service architecture.
4. Keep diagnostics behind a flag or bounded service if they are not intended for permanent production operation.
5. Add clear, rate-limited logs: `USB_HOST_DETACHED`, `CONSOLE_TRANSPORT_CLOSED`, `CONSOLE_SESSION_STOPPED`, `GADGET_STATE_CHANGED`, `RECOVERY_RETRY`, with timestamp/reason. Do not log credentials or arbitrary terminal payloads.
6. Preserve the distinction between USB power/charging, USB data connection, console service availability, and a host-connected console session. Do not tie all indicators to one boolean.
7. Inspect whether the deployed process is running an old Python module/binary, a stale systemd unit, a cached script or a generated copy. Deploy the intended artifact and prove its hash and runtime owner.
8. Re-run targeted tests, broader service tests, static checks and boot/service validation. Review the complete diff for accidental unrelated changes.

### Do not use these fake fixes

- Suppress the PC/Live Console indicator or keep it stale so no detach work runs.
- Disable the USB Live Console entirely without owner approval and without a replacement recovery path.
- Prevent all USB gadget state changes or permanently keep the UDC bound if that breaks future reconnection.
- Add `sleep 5` / `sleep 30` as the only fix for a race.
- Disable kernel panic reporting, watchdogs, OOM evidence or journaling.
- Add a reboot command after disconnect or use reboot as a retry strategy.
- Claim a physical pass from mocks or from the phone merely booting again.
- Modify charging indicator layout, icon artwork, animation or sizing; the owner says those now work.

---

## 6. Test plan

### 6.1 Automated/host-side tests

At minimum add tests for:

- normal detach event and clean console transport shutdown;
- duplicate detach events and concurrent detach callbacks;
- disconnect while a read is blocked, while a write is pending, while a lease exists, and during service shutdown;
- `POLLHUP`/`POLLERR`, EOF, `EIO`, `ENODEV`, `EPIPE`, `ECONNRESET`, missing TTY and missing sysfs attributes;
- unplug/reconnect rapidly and multiple times;
- stale PID/lease, PID reuse protection and zombie process cleanup;
- console daemon present but host absent; host present but console session not yet ready; host reconnect after prior disconnect;
- power-only charger attach/detach, data cable attach/detach and charging status transitions;
- systemd service exit/restart behavior, start limits, and no dependency that reboots/stops the OS;
- diagnostic logger disk full/unavailable, permission failure, and logger process failure without crashing the event path;
- indicator state remains correct and no unrelated icon CSS/layout/animation changes occur.

Use real project test conventions and hardware-faithful fixtures. Do not simply mock every signal to return the desired state.

### 6.2 Physical acceptance matrix

After safe deployment and confirmation of an alternate recovery path, execute on the actual SM-G975F. Capture timestamps, boot ID, uptime and evidence before/after each action.

| Test | Action | Expected result |
|---|---|---|
| P1 | Boot with no PC cable | Nuxel boots; no stale PC connection; expected current console indicator semantics preserved; no reboot loop |
| P2 | Connect PC data cable | PC + Live Console indicators and console work as intended |
| P3 | Disconnect PC cable while console is active | Indicators transition correctly; **no hang or reboot**; UI and OS remain responsive; boot ID unchanged and uptime continues |
| P4 | Reconnect PC cable | Data transport/console recover; no manual reboot needed |
| P5 | Repeat P2–P4 at least 5 cycles | No crash/reboot, restart storm, zombie process, stale lease or increasing delay |
| P6 | Use wall charger/power-only connection | Charging state behaves correctly; PC icon remains OFF; no reboot on charger removal while battery is healthy |
| P7 | Detach while console is idle/unused | No system-wide failure |
| P8 | Detach during an ordinary terminal command or output stream | Command/stream receives a handled disconnect; shell/UI/OS remain alive |
| P9 | Wi-Fi + HTTPS browser after detach | Network/browser continue working if Wi-Fi was already connected |
| P10 | Lock/unlock, navigation, battery and all three penguins after repeated cycles | No regression in current working UI/indicator behavior |
| P11 | Reboot normally after all tests | Normal boot; no stale USB session; no reboot loop |

For every physical test record one of: `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_OFFLINE_ONLY`, `BLOCKED_HARDWARE`, `NOT_TESTED`, `FAILED`. A physical unplug pass requires boot ID unchanged across the test, uptime continuing, and responsive system evidence; a mere successful post-reboot boot is a failure for this requirement.

### 6.3 Do not risk the phone to satisfy a test count

If the first controlled unplug reproduces a hard reboot and the evidence is insufficient, stop repeating it. Retrieve the evidence, improve the instrumentation or repair the evidenced cause, then ask the owner before another test. If the phone loses the only access channel, use the documented recovery path and do not make claims about unobserved runtime behavior.

---

## 7. Deployment and rollback

Before deployment:

- list every file/unit changed and why;
- preserve the previous working versions and checksums;
- confirm which process owns the console and how the agent will recover if USB drops;
- use a staged install and only restart the minimum service necessary;
- do not restart or stop the only access service until alternate access is confirmed;
- have a tested rollback command or script ready before touching live files;
- ensure the service manager will not trigger an unintended system target transition during a restart.

After deployment:

- verify installed hashes against the intended build;
- verify service active state, PID, restart counter and relevant log output;
- verify USB connected state and indicators before unplug;
- run the controlled physical acceptance matrix;
- retrieve device-local evidence after the test and inspect pstore/previous boot if any reset occurred;
- compare final `git diff`, run project tests, and confirm no unrelated files changed.

Rollback must restore only the changed files/units and their prior enabled/active state, without resetting the whole repository or overwriting newer unrelated work. If a reboot happens unexpectedly during deployment, stop further mutation until the cause is understood.

---

## 8. Required evidence and deliverables

Create `docs/a74/` and commit/report the following:

1. `PREFLIGHT-AND-RECOVERY.md` — revision, deployment hashes, access path, backups, recovery route and rollback.
2. `CRASH-CLASSIFICATION.md` — what happened on detach, evidence sources, boot IDs, timestamps, previous-boot/pstore data, and the reason it is classified as panic/watchdog/userspace/power/UI hang/unknown.
3. `USB-DETACH-SEQUENCE.md` — real event path and sequence diagram, owning process/unit at each step, blocking/teardown risks.
4. `ROOT-CAUSE-AND-FIX.md` — evidence-backed root cause, alternative hypotheses ruled in/out, exact code/unit changes and why they are minimal.
5. `TEST-MATRIX.md` — automated and physical results, test commands, timestamps, status labels, log paths and any limitations.
6. `REPO-VS-DEPLOYED.md` — hashes and runtime ownership for all relevant deployed artifacts.
7. `ROLLBACK.md` — tested rollback commands and the service recovery procedure.
8. `FINAL-STATUS.md` — concise outcome, what is fixed, what is still blocked, and explicit physical proof.

Also add regression tests to the repository in the established test locations. Keep large or sensitive raw logs outside version control; commit a redacted summary and references to local evidence paths.

## 9. Final response format

Return:

- **Root cause:** one evidence-backed sentence, or `NOT YET PROVEN`.
- **Classification:** kernel panic / watchdog / userspace reboot / console teardown race / service dependency / power reset / UI-only hang / unknown.
- **Fix:** exact files and behavioral change.
- **Tests:** automated counts plus physical detach/reconnect count.
- **Continuity proof:** before/after boot IDs and uptime; redact device identifiers as appropriate.
- **Regressions:** Wi-Fi/browser, charging, PC, Live Console, Bluetooth/Location toggles, lockscreen/navigation, and relevant apps.
- **Deployment and rollback:** hashes, service actions, exact recovery path.
- **Limitations:** anything not physically tested or not proven.

No unsupported “fixed!” claim. If the real failure is not captured, say so and state the next safe diagnostic action.

---

## MISSION COMPLETE WHEN

**Unplugging the PC cable is a boring, recoverable USB transport event—not a system crash.** The phone stays on the same boot, remains responsive, all three penguin indicators retain their now-correct behavior, the console can reconnect cleanly, and the physical test evidence proves it. 🐧🔌💪
