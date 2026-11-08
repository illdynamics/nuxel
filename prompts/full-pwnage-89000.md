# FULL-PWNAGE-89000.md
# NUXEL BOOT VELOCITY — SYSTEMD DEPENDENCY GRAPH, SAFE PARALLELISM & STARTUP OPTIMIZATION

**Mission:** Reduce the time from power-on to a responsive Nuxel lockscreen/home session by correcting the systemd dependency graph, eliminating unnecessary synchronous startup work, and safely parallelizing independent services. Preserve all existing Nuxel functionality and hardware paths.

**Device target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), ARM64, Nuxel/Fedora-derived userspace. The previously reported kernel was Linux `4.14.253-gf7194c1d15ed-dirty`; this is historical evidence, not an assumption. Discover the actual device, kernel, systemd and userspace versions at execution time.

**Primary evidence supplied by the owner:**

```text
multi-user.target @45.877s
└─nuxel-clockd.service @45.877s
  └─nuxel-soundd.service @4.237s +41.633s
    └─nuxel-audio-session.service @38.923s
      └─basic.target @4.195s
        └─sockets.target @4.194s
          └─systemd-logind-varlink.socket @4.193s +176us
            └─sysinit.target @4.182s
              └─systemd-timesyncd.service @3.897s +285ms
                └─systemd-tmpfiles-setup.service @3.329s +563ms
                  └─systemd-journal-flush.service @3.128s +198ms
                    └─systemd-journald.service @2.491s +635ms
                      └─systemd-journald.socket @2.475s +225us
                        └─system.slice @2.459s
                          └─-.slice @2.459s
```

The owner asks whether all services are unnecessarily dependent on one another and whether startup can be parallelized. The answer is: systemd already starts independent jobs concurrently. The objective is to find artificial ordering constraints and long synchronous initialization paths, not to blindly remove dependencies.

---

## 0. Mission rules and definition of done

This is an implementation task, not a theoretical review. Inspect the real repository and running S10+, identify the measured critical path, change the actual causes, deploy safely, reboot repeatedly, and produce a source-linked engineering report.

### Non-negotiable rules

1. **Do not break the phone to improve a number.** Preserve bootability, lockscreen, touchscreen, physical buttons, sound, alarms/timers, Wi-Fi SSH, Bluetooth, display, Phoc/Wayland, `nuxel-wl-fb`, `/dev/fb0`, Mali/EGL and existing app functionality.
2. **Do not remove a dependency until its contract is understood and an alternative readiness/retry path is implemented and tested.**
3. **Do not make every service `Type=simple` merely to make `systemd-analyze blame` look faster.** A service must be reported ready only when its documented readiness contract is actually satisfied.
4. Do not add arbitrary `sleep` commands, fake readiness, infinite retry loops, unbounded waits, or background forks from `ExecStartPre=`.
5. Do not disable essential services, udev, journald, dbus, logind, networking needed for recovery, audio, or display components just to reduce boot time.
6. Do not weaken security, remove sandboxing, or change service users/capabilities without a demonstrated requirement.
7. Do not alter the kernel, boot image, bootloader, device tree, partition layout, or firmware in this round unless a measured userspace bottleneck proves this is necessary and a separately reviewed recovery plan is available. The expected work is userspace/systemd.
8. Keep a tested rollback path that can be used over Wi-Fi SSH. Never delete the only working backup.
9. Do not assume the previous report's versions, service definitions, paths, host IP or status are still current. Discover and record the actual state.
10. Do not report a performance improvement based solely on `systemd-analyze blame`, a single boot, or a service being marked active earlier.

### Definition of done

- The actual cause(s) of the `nuxel-soundd.service` 41.633-second activation and `nuxel-clockd.service` placement in the critical chain are explained with unit-file, process, journal and timing evidence.
- The boot graph has been deliberately restructured so independent services can initialize concurrently.
- `nuxel-clockd` can start its scheduler without waiting for the entire audio hardware/session stack, while alarm playback remains reliable and cannot be silently lost or duplicated.
- `nuxel-soundd` exposes an honest, fast control-plane readiness state and handles audio hardware/session readiness independently where the code architecture permits it.
- The lockscreen, display session, input, sound, alarms, timers, Wi-Fi SSH, Bluetooth and essential system services all work after repeated cold boots and warm reboots.
- Before/after measurements include boot stages, lockscreen-visible time, usable-input time, target reach times, critical-chain graphs, service timing and resource pressure.
- Any improvement is repeatable across at least 3 measured boots (preferably 5), with median and range reported.
- All modified units pass `systemd-analyze verify`; dependencies are reviewed; no failed essential units or new boot-time errors remain.
- Backups and a precise rollback procedure are documented.

**Performance target:** First measure the real baseline. Aim to materially reduce time-to-lockscreen and userspace target completion; use a 20–30% reduction in the measured userspace-critical portion as an initial stretch objective, not a guarantee. More important than hitting a target is eliminating the 41.6-second soundd critical-path penalty without losing alarm/audio reliability. If kernel, bootloader, display-panel or hardware initialization dominates, report that separately rather than pretending a systemd change can fix it.

---

## 1. Understand the evidence before editing anything

### 1.1 What the supplied graph actually means

The supplied output is from `systemd-analyze critical-chain`. It displays a time-critical activation path for the requested/default target, not a complete diagram of every unit and every relationship.

- `@` is the time the unit became active/started, measured relative to the boot timeline.
- `+` is the time systemd counted the unit as activating.
- The tree is a critical-chain view. It is not proof that every service on the phone starts serially.
- Units with no ordering dependency can start concurrently even if one unit has a `Wants=` or `Requires=` relationship to another. Pull-in and ordering are separate concepts.
- `systemd-analyze blame` is not a causal profiler: a long activation time can include waiting on dependencies. It omits services with `Type=simple` from its activation-time ranking, and it does not show time spent waiting in the job queue.
- `systemd-analyze time` measures the kernel/initrd/userspace phases up to service spawning; this is not necessarily when the UI is fully rendered or interactive.
- The target shown is `multi-user.target`. Determine whether the actual Nuxel UI is tied to `graphical.target`, a custom target, a user session target, or another unit. Do not optimize only the target in the screenshot while leaving the lockscreen path unchanged.

### 1.2 Interpret the current suspicious chain cautiously

The evidence says:

- `multi-user.target` reached at approximately 45.877 s.
- `nuxel-clockd.service` is shown at approximately 45.877 s.
- `nuxel-soundd.service` started around 4.237 s and spent 41.633 s in its activating state.
- `nuxel-audio-session.service` appears underneath soundd and is timestamped around 38.923 s.

This is suspicious but does not, on its own, prove which directive or line of code causes the delay. Possibilities include:

- `nuxel-soundd.service` has `Type=notify`, `Type=dbus`, `Type=forking`, or `Type=oneshot` semantics that keep it activating until a late readiness condition occurs.
- `ExecStartPre=`, `ExecStart=`, or `ExecStartPost=` performs synchronous hardware probing, mixer setup, PipeWire/D-Bus waiting, retries, polling, or sleeps.
- Soundd is ordered after or requires `nuxel-audio-session.service`, while the audio-session itself has a late dependency.
- Soundd starts early but deliberately waits in code for the audio session to become ready.
- A helper script invokes a blocking `systemctl start`, waits on an IPC response, blocks on device enumeration, or has a large timeout.
- A generated unit, drop-in, symlink under a `.wants/`/`.requires/` directory, or implicit dependency changes the effective graph.
- Critical-chain representation and actual process timing are affected by concurrent startup, socket activation or jobs not shown in this view.

**Do not guess.** Establish the exact reason from the effective unit, drop-ins, symlinks, monotonic journal and process traces.

### 1.3 The key systemd semantics to apply correctly

- `Wants=`: pulls a unit into the transaction; by itself it does not order startup. If both units are requested and neither has an ordering edge, they can start together.
- `Requires=`: stronger pull-in/failure relationship; it still does not itself define ordering. Pair with `After=` only when there is a genuine readiness/ordering need.
- `After=` / `Before=`: ordering constraints. These are the directives that can serialize activation when used in a dependency chain.
- `BindsTo=`: lifecycle coupling; only use where a service must not remain active without a specific device/unit.
- `PartOf=`: propagates stop/restart operations; it is not a startup readiness substitute.
- `WantedBy=` in `[Install]` and symlinks into target `.wants/` directories decide what gets pulled into a target. A service being enabled does not mean it must be ordered before every other enabled service.
- `Type=simple`: systemd considers it started very early; it is not a reliable proof that IPC/API initialization has completed.
- `Type=exec`: tracks successful execution setup, but does not prove application-level readiness.
- `Type=notify`: lets a daemon report `READY=1` after its real startup contract is satisfied. Use it only if the daemon reliably sends notification and handles startup failure/timeouts.
- `Type=dbus`: readiness is tied to acquisition of the configured bus name.
- `Type=oneshot`: start completion waits for the command(s) to exit. A long-running initialization script can therefore hold up all ordered dependents.
- `ExecStartPre=` and multiple `ExecStartPre=`/`ExecStartPost=` commands run sequentially. Long checks here are common hidden boot bottlenecks. Do not use them for long-running daemons.
- `DefaultDependencies=yes` should normally remain enabled. Do not add `DefaultDependencies=no` as a generic speed hack.

---

## 2. Connect safely to the physical S10+

Use the real device; do not treat a host-side build as proof of on-device boot performance.

### 2.1 Repository and runtime discovery

- Inspect the current repo at `~/x/nuxel` (or discover the actual worktree if it moved).
- Run `git status --short --branch`, `git log -1 --oneline`, `git diff --stat`, `git diff`, inspect untracked files, and identify any uncommitted PWNAGE-88000 or other work. Do not discard owner changes or overwrite files blindly.
- Identify the current phone address using the repo's live SSH helper if present, e.g. `scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --status`. The old pinned helper address was previously stale, so do not assume it is reachable.
- Connect over Wi-Fi using the existing key path:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  root@<DISCOVERED_PHONE_HOST>
```

- Preserve host-key verification. Never use `StrictHostKeyChecking=no`, never delete `known_hosts` entries to bypass a mismatch, and never print/copy private-key material.
- Verify `id -u` is `0`, capture `hostname`, `uname -a`, `/etc/os-release`, `systemd --version`, `systemctl get-default`, current boot ID and uptime.
- Verify Wi-Fi SSH works both before and after modifications. Keep the network/SSH recovery path available throughout.

### 2.2 Create a recovery point

Before modifying deployed units or scripts:

- Create a timestamped root-owned backup under `/var/backups/nuxel/p89000-<UTC_TIMESTAMP>/`.
- Preserve every changed unit, drop-in, enablement symlink, helper script, configuration file, environment file and binary.
- Record exact ownership, modes, symlink targets and checksums (`sha256sum`).
- Save the effective unit output (`systemctl cat`) and `systemctl show` state before changes.
- Save a copy of the original `systemctl list-dependencies` output and generated boot graphs.
- Ensure the rollback script can restore exact prior files/symlinks, run `systemctl daemon-reload`, and restart only the appropriate services.
- Do not put secrets, cookies, private keys or credentials in the evidence bundle.

---

## 3. Establish a real boot baseline

Do this before changing the graph. Save outputs under the repo, for example:

`docs/pwnage-89000/evidence/<UTC_TIMESTAMP>/baseline/`

At minimum collect:

```bash
systemd-analyze time
systemd-analyze blame --no-pager
systemd-analyze critical-chain --no-pager
systemd-analyze critical-chain graphical.target --no-pager
systemd-analyze critical-chain multi-user.target --no-pager
systemd-analyze critical-chain default.target --no-pager
systemd-analyze plot > boot-before.svg
systemctl get-default
systemctl list-jobs --all
systemctl --failed --no-pager
systemctl list-units --type=service --all --no-pager
systemctl list-dependencies --all --no-pager default.target
systemctl list-dependencies --all --no-pager graphical.target
systemctl list-dependencies --all --no-pager multi-user.target
journalctl -b -o short-monotonic --no-pager
```

If a command is not supported by the phone's systemd build, record that and use a compatible equivalent. Do not let diagnostic collection itself create a material boot delay.

Collect unit-specific state for all Nuxel services and every unit appearing on the critical path:

```bash
systemctl cat nuxel-soundd.service
systemctl cat nuxel-audio-session.service
systemctl cat nuxel-clockd.service
systemctl show nuxel-soundd.service
systemctl show nuxel-audio-session.service
systemctl show nuxel-clockd.service
```

For every important unit, record at least:

- `Id`, `Description`, `LoadState`, `ActiveState`, `SubState`, `Result`
- `Type`, `RemainAfterExit`, `NotifyAccess`, `BusName`
- `ExecCondition`, `ExecStartPre`, `ExecStart`, `ExecStartPost`, `ExecStop`, `ExecStopPost`
- `TimeoutStartUSec`, `TimeoutStopUSec`, `Restart`, `RestartSec`
- `After`, `Before`, `Wants`, `Requires`, `Requisite`, `BindsTo`, `PartOf`, `Conflicts`
- `TriggeredBy`, `Triggers`, `WantedBy`, `RequiredBy`
- `InactiveExitTimestampMonotonic`, `ActiveEnterTimestampMonotonic`, `ExecMainStartTimestampMonotonic`, `ExecMainExitTimestampMonotonic`, `ExecMainPID`, `ExecMainStatus`
- `FragmentPath`, `SourcePath`, `DropInPaths`

The exact set of properties available varies by systemd version. Query supported properties rather than assuming all fields exist.

### 3.1 Measure the user-visible boot separately

`multi-user.target` is not automatically the same thing as a visible, unlocked or interactive Nuxel UI. Create a consistent measurement protocol:

1. Define the start as physical power-button press or another reproducible cold-boot initiation point. Record the measurement method.
2. Define **first visible Nuxel frame** (not a frozen earlier boot frame).
3. Define **lockscreen ready** (correct lockscreen rendered, no zoomed desktop flash, input path ready).
4. Define **first usable interaction** (touch/physical controls respond).
5. Define **home/launcher ready** after unlock.
6. Capture video or timestamped evidence across boots where possible. Do not estimate from memory.

Record kernel/initramfs, userspace, target, lockscreen and interactive timings separately. If `systemd-analyze time` does not expose firmware/bootloader timing on this phone, mark it unavailable rather than inventing a value.

Run at least three baseline boots if feasible; preferably five. Distinguish cold boots from warm reboots. Avoid changing several things between baseline measurements.

### 3.2 Build the actual unit graph

Create a dependency inventory, not merely a list of enabled services.

Use compatible commands such as:

```bash
systemd-analyze dot --order --require > units-before.dot
systemd-analyze dump > systemd-dump-before.txt
systemctl list-dependencies --all --plain default.target
systemctl list-dependencies --all --plain graphical.target
systemctl list-dependencies --all --plain multi-user.target
systemctl list-unit-files --state=enabled --no-pager
```

Render DOT to SVG if Graphviz exists. Otherwise keep the DOT file and create a readable textual table.

For each service, classify:

| Class | Meaning | Example decision |
|---|---|---|
| Boot-critical | Required to get to a safe, visible, interactive lockscreen | Keep on critical path, minimize its work |
| Early independent | Needed early but does not depend on display or audio initialization | Start concurrently with other independent work |
| Readiness consumer | Needs another service's API/device to be ready before it can function | Use exact readiness ordering or retry/activation |
| Background | Useful after the UI is responsive | Move out of the critical path without disabling permanently |
| On-demand | Only needed when a user/app asks for it | Use socket, D-Bus, path or explicit activation where appropriate |
| Optional/deferred | Nonessential work that can wait until idle/charger/unlocked | Timer, idle trigger or session target with resource limits |

Identify every `After=` edge that delays the lockscreen, every slow `Type=oneshot` unit, every long `ExecStartPre=`/`ExecStartPost=`, every `network-online.target` dependency, all device waits, and all service activation loops.

---

## 4. Fix the soundd/audio-session/clockd startup bottleneck

This is the first implementation priority because the supplied evidence places it directly on the target's critical path and reports 41.633 seconds for `nuxel-soundd.service`.

### 4.1 Root-cause the 41.633 seconds

Inspect:

- Effective service definition and every drop-in.
- Enablement symlinks and reverse dependencies.
- All scripts/binaries launched by `ExecStart*`.
- Python/JS/shell startup paths, subprocess waits, D-Bus calls, PipeWire/ALSA discovery, mixer operations, device enumeration, retry loops and timeouts.
- `journalctl -b -u nuxel-soundd.service -o short-monotonic` and equivalent audio-session/clockd logs.
- Whether soundd calls `systemctl start`/`is-active` synchronously or waits for audio-session readiness.
- Whether a helper has a 30/40/45-second connect timeout or multiple retries.
- Whether systemd is waiting for `READY=1`, D-Bus name acquisition, a forking parent or a oneshot process exit.

If evidence does not isolate the delay, add narrowly scoped monotonic instrumentation around startup phases. Use safe process tracing (`strace -ff -ttt -T` or equivalent) only when available and only for a short diagnostic run. Do not leave verbose tracing enabled in production.

Produce a timing breakdown with exact phases, e.g. daemon process launch, config load, socket creation, D-Bus connect, audio-session request, PipeWire connect, ALSA enumeration, mixer setup, route selection, hardware-ready event. Only use phases actually observed in the implementation.

### 4.2 Separate the sound control plane from hardware readiness

Preferred design where the code supports it:

**Fast sound control plane (`nuxel-soundd`)**

- Load minimal configuration and persistent queue/state.
- Create its IPC endpoint/D-Bus interface/socket.
- Initialize event IDs, deduplication and command validation.
- Accept requests even if the physical output device is not yet ready.
- Report its control API ready only once it can reliably accept and queue requests.
- Discover/subscribe to actual audio backend availability asynchronously.
- Publish a distinct audio-output readiness state such as `backend_ready`, `route_ready`, `active_sink`, `last_backend_error`.

**Audio hardware/session initializer (`nuxel-audio-session`)**

- Start independently as soon as its true prerequisites are available.
- Initialize PipeWire/ALSA/session routing without making the control-plane daemon block for the entire hardware discovery process.
- Use device/bus availability events or bounded asynchronous retries instead of a single long synchronous boot barrier.
- Make initialization idempotent and safe on reconnect/device disappearance.
- Expose clear readiness and failure diagnostics.

**Clock scheduler (`nuxel-clockd`)**

- Load and validate schedules, migrate state, arm timers and become ready independently of output hardware.
- Do not wait for full audio route discovery just to calculate alarms.
- On alarm/timer firing, request the sound by stable event/occurrence ID.
- Soundd must accept/queue the cue, start or await audio-session readiness, and play it once a valid output route exists.
- Preserve alarm deadlines and use a carefully defined late-delivery policy. Never silently drop a due alarm because the sound service took longer to boot.

The key architectural rule: **scheduler readiness is not the same as speaker readiness**. The clock must be ready to schedule time-sensitive events early; the audio stack must be ready to render them as soon as possible. Those can be separate states.

### 4.3 Correct systemd dependencies after the API contract is real

Do not blindly apply this example; derive the exact unit graph from implementation. A possible final structure could be:

```ini
# Illustrative only. Adapt to actual service architecture and runtime.
# clockd can be pulled in with soundd, without waiting for soundd hardware init.
[Unit]
Wants=nuxel-soundd.service
# No After=nuxel-soundd.service unless clockd truly requires its control API
# synchronously before clockd can become scheduler-ready.
```

And soundd may pull in audio-session without serializing its own control-plane readiness:

```ini
# Illustrative only. Use only after soundd has a reliable asynchronous backend.
[Unit]
Wants=nuxel-audio-session.service
# Add After= only for a real prerequisite, not merely because soundd uses audio.
```

If soundd needs an IPC endpoint before it can accept a request, consider socket activation or create the socket/control endpoint before audio hardware readiness. Do not create a race where clockd believes soundd is ready but there is no working endpoint to accept the cue.

Potential approaches, in order of preference:

1. Refactor soundd into a fast IPC/control process plus asynchronous backend discovery.
2. Use an activated socket or D-Bus name as the durable request interface, so requests can be accepted/queued while backend startup proceeds.
3. Use a small dedicated audio-session readiness target or event contract, only if it improves clarity.
4. Keep strict `After=` where a caller genuinely cannot work before the dependency is initialized.

Do not use `Type=simple` to fake readiness. If soundd supports systemd notification, use `Type=notify` and send `READY=1` after its control-plane API and queue are truly usable. If it does not, implement and test `sd_notify()` or a compatible datagram implementation. If a `Type=notify` service never sends a valid notification, systemd will wait until timeout and make boot worse. `Type=exec` may be appropriate if only successful process execution is the actual contract, but document that the API may not yet be ready.

### 4.4 Alarm and sound reliability tests

Before and after graph changes, verify:

- Clockd starts before audio hardware readiness and remains functional.
- Alarm/timer schedule loads and persists over reboot.
- An alarm that fires after soundd is ready plays once.
- An alarm that becomes due while the backend is still initializing is queued and plays within a bounded grace period once audio is ready.
- Reconnection/device changes do not replay an already acknowledged alarm.
- Duplicate service restarts do not duplicate audio cues.
- Dismiss/snooze/stop semantics still work.
- Sound settings, separate alarm/timer cues, volume controls, normal system audio and media playback still work.
- Audio route errors are visible in logs and UI rather than swallowed.

Use a non-disruptive test alarm shortly after boot, then remove it. Do not leave persistent test alarms or accidentally wake the owner with repeated test cues.

---

## 5. Parallelize the rest of the boot graph intelligently

The goal is a shallow critical path with real readiness gates, not zero dependencies.

### 5.1 Audit all Nuxel services

Inventory at least all discovered units matching `nuxel-*`, plus related Phoc/Wayland/fb bridge, D-Bus, audio, network, Bluetooth, SSH, prewarming, software/portal and lockscreen services.

For every service, answer:

1. What user-visible or system function does it provide?
2. Is it needed before the lockscreen appears, before unlock, only when an app opens, or only in the background?
3. What exact resource/API does it require?
4. Does it need the dependency to be **active**, or only to have been started / have a socket available?
5. Does it perform slow work synchronously that can be deferred?
6. What is the failure mode if it is not ready at boot?
7. Can it retry asynchronously without losing user operations?

### 5.2 Preserve true boot-critical prerequisites

Do not remove required startup ordering for:

- Root and essential local filesystems.
- udev/device node creation before a service opens a specific device.
- D-Bus before a client that requires a live bus connection (unless socket activation or retry is implemented).
- logind/seat/session setup before services that require a real session/seat.
- input device readiness before the UI is considered interactive.
- framebuffer writer and actual display device initialization before Phoc/Wayland presentation depends on it.
- Phoc/Wayland session readiness before lockscreen clients depend on compositor protocols.
- required user/session environment before per-user graphical services.
- audio backend readiness before a component that directly configures the backend in a non-retryable way.

Avoid adding a blanket order that makes every Nuxel process wait for the display or every UI process wait for audio.

### 5.3 Remove accidental global barriers

Audit specifically for:

- `After=network-online.target` on services that only need networking eventually, or do not need networking at all.
- `Requires=network-online.target` on unrelated phone functions.
- boot services that synchronously wait for Wi-Fi association, DNS or internet access even though local offline startup should work.
- services chained behind `nuxel-soundd` when they only need the sound API at use time.
- services chained behind app-prewarm, Flatpak portal/GVFS, media scanning, software catalog updates or download checks.
- long `ExecStartPre=` and `ExecStartPost=` probes that can run after the service is ready.
- oneshot services that do extensive work but are ordered before the lockscreen.
- duplicate work done by both a service and an application on startup.
- scripts that call `systemctl start` synchronously for another service, then wait without a bounded timeout.

Do not eliminate `network-online.target` from a true consumer that cannot work without configured networking. Instead scope it to the consumer and do not make the rest of the system wait for it. systemd documentation explicitly warns that `network-online.target` may pull in wait-online services and add substantial delays.

### 5.4 Move nonessential work out of the critical path

Potential candidates, only after inspecting actual units and dependencies:

- app prewarming / cache population;
- Flatpak metadata or catalog refresh;
- Software store metadata retrieval;
- optional repository synchronization;
- thumbnail generation / media indexing;
- nonessential logs or diagnostic bundle generation;
- optional update checks;
- background app warming;
- maintenance and cleanup jobs that do not protect boot integrity.

Prefer demand-driven or timer-based activation. If using `systemd.timer`, use an appropriate randomized delay for nonurgent maintenance and avoid launching multiple heavy jobs simultaneously after boot. If using an idle target or graphical-session target, verify that those facilities exist in the actual systemd build.

Do not permanently disable useful capabilities just to move them off the critical path. They must still run at the correct time or when requested.

### 5.5 Consider a small number of Nuxel lifecycle targets

Only introduce custom targets if they simplify and clarify the real graph. Possible conceptual phases:

- `nuxel-core.target`: essential Nuxel control-plane daemons and safe device services.
- `nuxel-session.target`: seat, compositor and lockscreen/user-session readiness.
- `nuxel-background.target`: noncritical background tasks and prewarming.

These are examples, not a requirement to add targets. A new target is not an optimization if it merely creates another ordering barrier. Ensure it uses `Wants=` for optional services and that only actual prerequisites are ordered with `After=`.

Do not use `multi-user.target` and `graphical.target` interchangeably. Discover the active default target, aliases and display/session design. The visible Nuxel lockscreen can have a different readiness point from `multi-user.target`.

---

## 6. Startup code optimization beyond unit files

Changing systemd directives will not solve a daemon that performs slow synchronous initialization internally. Profile the executable and its helpers.

### 6.1 Remove unnecessary synchronous startup work

For each slow daemon:

- Time config parsing, file reads, subprocesses, device discovery, DBus calls, IPC creation and readiness probes separately.
- Avoid spawning a shell for trivial built-in operations where useful, but do not micro-optimize without measurements.
- Cache safe, stable metadata where correctness allows; invalidate when device, configuration or package changes.
- Avoid repeated full scans of `/sys`, `/dev`, Flatpak deployments or app directories on every boot if a device/event or cache index can be used.
- Avoid DNS/network requests during boot unless absolutely required.
- Add bounded deadlines to external calls and continue in a degraded-but-useful mode when the optional subsystem is unavailable.
- Use event-driven notifications (`inotify`, D-Bus signals, device events, PipeWire events, sockets) rather than tight polling or long sleeps.
- If retrying, use bounded exponential backoff with jitter where appropriate, cancellation on shutdown, and a clear maximum policy. Do not sleep inside a systemd startup path for tens of seconds.
- Avoid holding global locks while waiting for hardware or IPC.
- Make all initialization safe to run concurrently where services share caches/configuration. Use atomic writes and narrowly scoped locks; avoid races by design, not by serializing the whole boot.

### 6.2 Be truthful about service readiness

For each daemon, define a documented readiness contract:

- **Process launched:** executable successfully started.
- **Control API ready:** IPC endpoint created and requests can be accepted.
- **Configuration ready:** essential configuration parsed/validated.
- **Hardware ready:** required device/route opened and usable.
- **UI ready:** visible session and input respond.

Do not conflate these states. Use systemd readiness notification only for the readiness level needed by ordered dependents. Publish deeper readiness separately through health status or a D-Bus property/API.

If a service is split into control plane and backend worker, ensure the worker has a watchdog/health path and that queued work survives backend restarts safely.

### 6.3 Avoid readiness deadlocks

Inspect for cycles such as:

- soundd waits for audio-session, while audio-session waits for soundd;
- graphical session waits for a service that itself waits for a session bus/user session;
- service waits for a user app which is only launched after the service becomes active;
- a oneshot calls `systemctl start` on a unit ordered after the oneshot;
- lockscreen waits for a service that waits for lockscreen UI readiness.

Use `systemd-analyze verify`, graph inspection, journal job logs and service startup tracing. Never solve a cycle by removing all ordering constraints. Rebuild the correct acyclic readiness graph.

---

## 7. CPU, memory, I/O and boot smoothness

Parallelism is useful only if it reduces elapsed time without causing CPU contention, memory pressure, flash I/O contention, thermal throttling or UI jank.

### 7.1 Measure actual resource use

During boot and shortly after lockscreen appearance, sample:

- CPU utilization per core / scheduler load;
- memory available, page cache, swap/zram if present, PSI memory/CPU/IO if supported;
- I/O throughput and latency;
- major page faults and process RSS;
- service process counts;
- thermal/CPU frequency and throttling state;
- lockscreen frame stability / input latency where measurable.

Use tools available on the phone (`vmstat`, `pidstat`, `top`, `ps`, `/proc`, PSI files, `systemd-cgtop`, `perf` if available). Do not install heavy instrumentation on the phone solely for a one-off measurement if it creates more overhead than it measures.

### 7.2 Limit background competition

- Prewarm jobs must not compete with lockscreen/Phoc/Wayland/launcher startup.
- Apply modest `CPUWeight=`, `IOWeight=`, `Nice=`, `IOSchedulingClass=` or supported resource controls to noncritical background jobs only after verifying support and actual effect.
- Do not set aggressive global CPU governor or thermal settings as a boot optimization.
- Do not pin all services to one core or force concurrency without checking the Exynos scheduler and big.LITTLE topology.
- Do not launch a burst of all optional services at one timestamp if this saturates storage and slows the UI.
- Use staggered low-priority background activation after lockscreen or idle if measurements show a boot I/O storm.
- Respect memory headroom; a background service that triggers pressure/reclaim can make the phone feel slower even if target time improves.

### 7.3 Keep boot graphics responsive

Preserve the actual framebuffer/Wayland architecture:

`Phoc/Wayland -> nuxel-wl-fb -> sole /dev/fb0 writer -> Samsung display`

Do not add another framebuffer writer, switch to software rendering, disable Mali acceleration, or alter EGL/GBM paths as a side effect of boot optimization. Do not change panel modes or display timing without a separate evidence-based reason.

A boot optimization is not successful if the lockscreen appears sooner but is initially frozen, scaled incorrectly, covered by stale frames, missing input, or followed by a long period of unresponsiveness.

---

## 8. Measure, compare and prove the improvement

### 8.1 Required before/after evidence

Store evidence under:

`docs/pwnage-89000/evidence/<UTC_TIMESTAMP>/`

Include:

- device/version fingerprint;
- repo commit and dirty-worktree state;
- exact backup path;
- all original and modified service unit files and drop-ins;
- unit enablement/symlink changes;
- baseline and final `systemd-analyze time`, `blame`, critical chains and plots;
- dependency graph DOT/SVG before and after;
- monotonic journal excerpts for soundd, audio-session, clockd, display, Phoc, framebuffer bridge, lockscreen, network and SSH;
- service property snapshots;
- boot measurement table (individual boots, median, min/max/range);
- lockscreen video or timestamp evidence;
- test results and failed test details;
- rollback procedure and checksum validation.

### 8.2 Repeatable boot table

Create a table like:

| Metric | Baseline boot 1 | Baseline median | Final boot 1 | Final median | Delta |
|---|---:|---:|---:|---:|---:|
| Kernel/initramfs | | | | | |
| Userspace startup | | | | | |
| `multi-user.target` | | | | | |
| `graphical.target` / actual session target | | | | | |
| First Nuxel frame | | | | | |
| Lock screen ready | | | | | |
| First usable touch | | | | | |
| Home/launcher ready | | | | | |
| soundd control API ready | | | | | |
| audio output route ready | | | | | |
| clockd scheduler ready | | | | | |

Use the same conditions and definitions before and after. State whether the device was cold booted or warm rebooted, whether Wi-Fi was available, and whether the test began after an idle period. Do not compare a cold boot with a warm reboot as though they were identical.

### 8.3 Use the right diagnostics

- `systemd-analyze time`: stage timing, but not full UI readiness.
- `systemd-analyze critical-chain <target>`: critical path for the requested target; check actual UI/session units too.
- `systemd-analyze blame`: clue for long activation state, not a causal ranking.
- `systemd-analyze plot`: visualize start overlap and long activation intervals.
- `systemd-analyze dot`: inspect dependencies/ordering graph.
- `journalctl -b -o short-monotonic`: align process logs with boot timeline.
- `systemctl show`/`cat`: effective unit and timestamps.
- process trace: isolate actual blocking calls if logs are insufficient.

Do not parse human-readable command output in fragile scripts as though it were a stable API. For automation, use D-Bus/systemd properties or carefully version-gated parsing.

---

## 9. Deployment strategy and rollback safety

### Phase A — source changes

1. Make the smallest clear change that removes the measured critical-path cause.
2. Add unit tests for service state/queue/retry behavior where appropriate.
3. Add a graph contract test or a script that checks only intentional dependencies, not hard-coded assumptions that will become stale.
4. Validate every unit file with the phone's `systemd-analyze verify` and the repo's available lint/tests.
5. Inspect generated `systemd-analyze dot` output and verify no cycles or unexpected ordering edges.

### Phase B — stage and deploy

1. Back up every deployed file and symlink.
2. Deploy units and code atomically where possible (write temporary file, fsync if appropriate, rename into place).
3. Run `systemctl daemon-reload` once after the unit set is in place.
4. Do not immediately restart all services at once. Restart in dependency-aware order while SSH remains connected.
5. Verify each service's actual API and health endpoint, not just `ActiveState=active`.
6. Confirm Wi-Fi SSH still works and the phone remains manageable.

### Phase C — controlled reboot

- Before reboot, ensure the backup and rollback helper are accessible locally on the phone and the developer workstation.
- Keep a reliable recovery route. Do not reboot if critical service state is inconsistent or Wi-Fi recovery is lost.
- Run one controlled reboot and inspect the complete journal/boot graph. If stable, run additional boots for measurement.
- If the lockscreen or Wi-Fi SSH fails, use the known recovery route; do not blindly repeat reboots.

### Phase D — rollback

Rollback must restore exact unit files, drop-ins, scripts, configuration and enablement symlinks from the timestamped backup; run daemon-reload; restore original enablement state; and restart/reboot only as appropriate. Verify checksums and the original boot graph. Do not merely copy selected files while leaving changed symlinks or generated configuration behind.

Do not change bootloader/kernel partitions in this task; a systemd rollback should not require TWRP.

---

## 10. Functional regression matrix

Run as much as can be safely automated and physically verify the rest.

### Boot and core session

- Cold boot and warm reboot complete without emergency/rescue mode.
- Correct Nuxel preloading/boot visuals continue to work.
- No frozen first frame, stale desktop zoom flash, black screen or lockscreen race is introduced.
- Lock screen appears correctly, accepts input and unlocks.
- Home, app drawer, tabs, Back and system navigation still function.
- Display orientation and current fixed-rotation behavior are unchanged.
- Phoc/Wayland and the sole `/dev/fb0` writer remain healthy.

### Services and recovery

- No new failed essential units.
- No restart loop or timeout storm.
- Service Settings view (if present) correctly reflects active/failed state.
- systemd manager responds to `systemctl` and D-Bus requests.
- Wi-Fi network and root SSH remain accessible after boot.
- Bluetooth and other services remain functional.

### Audio, clock and alarms

- Soundd control API becomes ready quickly and reports backend status accurately.
- Audio-session eventually reaches hardware-ready state.
- Speaker output and volume cue work.
- Microphone capture remains configured and usable.
- Clockd schedules alarms/timers without waiting for physical audio.
- Alarm and timer sound is delivered even if the cue is requested during backend initialization (within documented policy).
- No lost, duplicate or delayed-by-minutes alarms.
- Dismiss, snooze, timer stop and lockscreen indicators still operate.

### Apps and performance

- Native GTK and Flatpak launch remain functional.
- The earlier Flatpak ~30-second startup stall must not be made worse by boot prewarming or service changes.
- Software/Archive, Firefox, Legcord/Vesktop and other apps still launch as before.
- No memory-pressure spike, swap storm or severe input/frame jank after the lockscreen appears.

---

## 11. Suggested implementation phases

### Phase 0 — Baseline and safety

- Connect over Wi-Fi SSH, establish root, capture baseline, backup.
- Verify target alias and display session readiness path.
- Save all service and graph evidence.

### Phase 1 — Sound bottleneck diagnosis

- Establish why soundd spends 41.633 seconds activating.
- Identify every synchronous wait and actual dependency edge.
- Determine which work is control-plane startup and which is hardware/session initialization.
- Do not edit until this explanation is supported by evidence.

### Phase 2 — Sound/clock readiness redesign

- Make clockd scheduling independent from full audio route readiness.
- Make soundd's request interface ready quickly and reliably.
- Initialize audio-session concurrently or asynchronously.
- Implement durable/idempotent event queueing and bounded retry behavior.
- Preserve alarms and sound under backend unavailability/restart.

### Phase 3 — Whole boot graph audit

- Inventory Nuxel service dependencies.
- Find all accidental `After=` barriers, unnecessary `network-online.target` waits, long oneshots and synchronous start scripts.
- Split essential, session, background and on-demand work.
- Remove only proven unnecessary ordering edges.

### Phase 4 — Startup code and resource optimization

- Move nonessential work out of the lockscreen critical path.
- Reduce scans, waits, shell/process churn and duplicated initialization.
- Throttle background work where required to protect UI responsiveness.

### Phase 5 — Deployment and repeatability

- Verify units, test contracts, deploy, controlled reboot.
- Collect at least three final boots, preferably five.
- Perform functional regression matrix.
- Roll back immediately if the phone loses a core function or boot/recovery reliability.

### Phase 6 — Final engineering report

Write:

`docs/pwnage-89000/evidence/<UTC_TIMESTAMP>/ENGINEERING-REPORT.md`

Include:

1. Executive result and truthful completion status.
2. Device, kernel, Fedora/userspace/systemd versions.
3. Initial user-visible boot measurements and final measurements.
4. Exact cause of the 41.633-second soundd activation.
5. Original and final service dependency graphs.
6. Every modified unit/script/source file and why it changed.
7. Which services now start in parallel and why it is safe.
8. Soundd/clockd/audio-session readiness contract and alarm queue guarantees.
9. Before/after boot timing table and variability.
10. Functional test matrix with PASS/FAIL/NOT TESTED and evidence references.
11. Any remaining bottlenecks and what layer they belong to (bootloader, kernel, filesystem, systemd, service, compositor/UI).
12. Exact backup path and tested rollback commands.
13. A concise final statement distinguishing deployed, automatically tested and physically verified results.

---

## 12. Explicit anti-patterns — do not do these

- Do not remove `After=` from every unit wholesale.
- Do not replace every `Requires=` with `Wants=` without checking whether failure propagation is part of the safety contract.
- Do not remove `Wants=`/`Requires=` as if those directives necessarily serialize startup.
- Do not set all daemons to `Type=simple` to hide initialization delay.
- Do not set `DefaultDependencies=no` globally.
- Do not disable journald, dbus, udev, logind, timesyncd, networking, sound, display or power services without proof they are unnecessary and safe.
- Do not disable `systemd-timesyncd` merely because it appears in this critical chain; first determine whether it is actually delaying the target or just shown in the path.
- Do not force `network-online.target` for services that need only eventual network connectivity.
- Do not add `sleep 1`, `sleep 5` or similar serialization workarounds.
- Do not move alarm scheduler startup into a late graphical session.
- Do not make sound requests fire-and-forget without durable acknowledgement/queue semantics.
- Do not queue alarm sounds indefinitely or replay stale alarms without a defined expiry/idempotency policy.
- Do not use a long foreground hardware discovery loop in `ExecStartPre=`.
- Do not start all optional jobs simultaneously if this saturates memory, storage or CPU.
- Do not force software rendering or change the framebuffer/Mali path.
- Do not treat `multi-user.target` activation as proof that the phone is usable.
- Do not count a faster target timestamp as a win if first usable touch or visible lockscreen becomes slower.
- Do not claim an untested physical reboot succeeded.

---

## 13. Authoritative technical references

Use documentation matching the actual installed systemd version where possible. The phone's installed man pages and effective behavior take precedence over options introduced only in newer systemd releases.

- `systemd.unit(5)` — unit dependencies, `Wants=`, `Requires=`, `After=`, `Before=`, implicit/default dependencies: https://www.freedesktop.org/software/systemd/man/latest/systemd.unit.html
- `systemd.service(5)` — service types, readiness notification, `ExecStartPre=`, `ExecStartPost=`, timeouts: https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html
- `systemd-analyze(1)` — `time`, `blame`, `critical-chain`, `plot`, `dot`, `verify`: https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html
- `systemd.special(7)` — `basic.target`, `multi-user.target`, `graphical.target`, `network-online.target`: https://www.freedesktop.org/software/systemd/man/latest/systemd.special.html
- `sd_notify(3)` — readiness notification protocol: https://www.freedesktop.org/software/systemd/man/latest/sd_notify.html

Useful semantic points:

- `Wants=` and `Requires=` pull units in but do not themselves impose ordering; ordering is controlled separately by `After=`/`Before=`.
- `systemd-analyze critical-chain` is a view of a time-critical path and can mislead because of parallel execution, socket activation, and omitted job/time-out information.
- `systemd-analyze blame` reports activation duration, not causal waiting time or job-queue latency.
- `systemd-analyze time` is not a measure of the fully interactive UI.
- `Type=notify` readiness is useful only when the daemon sends `READY=1` after its real contract is met.

---

# FINAL DIRECTIVE

Execute this full specification against the actual Nuxel repository and actual Samsung S10+ over Wi-Fi SSH. Start with evidence, not assumptions. Identify why soundd takes 41.633 seconds and why clockd is positioned at 45.877 seconds. Then restructure the dependency graph and daemon readiness contracts so independent startup work happens concurrently, without losing any required ordering or functionality.

The desired result is a phone that boots noticeably faster, reaches a usable lockscreen sooner, starts background work without blocking the UI, schedules alarms early, and brings audio online independently. Prove the result with multiple measured boots and physical regression tests. A lower systemd number that hides failures is not success.
