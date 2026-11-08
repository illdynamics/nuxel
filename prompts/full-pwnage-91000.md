# FULL-PWNAGE-91000 — Nuxel Deep Systems Audit, Safe Boot/Shutdown Optimization, Compositor Performance, Source Cleanup & Hardware Completion Roadmaps

> **Mission class:** maximum-depth codebase and device audit, evidence-backed performance engineering, careful source cleanup, and seven hardware-completion investigations.
>
> **Primary target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Fedora ARM64 Nuxel, unless the actual checked-out tree and connected device prove another active target.
>
> **Primary objective:** make Nuxel boot and shut down faster, reduce unnecessary service/process work, make the compositor and full visible UI smoother, and remove genuinely obsolete/rejected implementation code without breaking any current functionality. In parallel, produce seven technically complete reports identifying the remaining blockers and the best realistic routes to fully working GPU acceleration, camera, GPS/GNSS, NFC, auto-rotation, fingerprint, mobile networking and colored LEDs.
>
> **Non-negotiable:** DO NOT BREAK ANY SERVICE OR EXISTING FUNCTIONALITY. The hardware reports are research/engineering roadmaps; they do not authorize risky firmware writes, bootloader operations, partition writes, or unapproved kernel flashing.

---

## 0. EXECUTION CONTRACT — THIS IS NOT A SHALLOW REVIEW

You are executing a major systems-engineering mission against the real Nuxel repository and, where safely available, the actual handset. Read this entire file before editing. The companion `pwnage-91000.md` is only the execution kickoff; this file is the complete specification.

### 0.1 Required outcomes

Complete all of the following:

1. Deep-analyze the current repository, installed image/build pipeline, runtime services and connected target to the maximum useful detail. Do not rely on old prompts, README claims or copied reports as proof of current state.
2. Inspect `./SYSTEMD-GRAPH.md` if present. Use its actual boot and shutdown evidence to identify opportunities to shorten boot and shutdown while preserving every required dependency and every existing service behavior. If it is absent or stale, collect fresh evidence and create it before making timing claims.
3. Optimize the current compositor/render/display/input wiring where measurable. Remove redundant work and bad ownership patterns (for example, starting a process only for a second service to disable, stop or override it). Establish one owner for each ongoing responsibility.
4. Find services, scripts, processes, code paths, configuration and packaging entries that are truly unused, superseded or explicitly rejected in earlier Nuxel decisions. Remove genuinely obsolete implementation code and all its active references—not merely mask it at runtime or add another cleanup service—while retaining historical evidence and preserving every real feature.
5. Produce `./GPU-ACCEL-REPORT.md` identifying each still-unaccelerated or partially accelerated graphics/render/media component, the exact blocker, and the best compatible path to finish acceleration.
6. Produce `./REPORT-CAMERA.md`, `./REPORT-GPS.md`, `./REPORT-NFC.md`, `./REPORT-ROTATION.md`, `./REPORT-FINGERPRINT.md`, `./REPORT-MOBILE-NETWORKING.md`, and `./REPORT-LEDS.md`. Each must explain the current blocker, the full hardware-to-userspace chain, what is already implemented, what is missing, the recommended end-state architecture, the actual work required and the risks/dependencies. The target is fully working hardware functionality; do not hide behind vague statements such as “driver needed.”
7. Implement and verify only the safe, evidence-backed boot/compositor/code-cleanup improvements that can be completed without jeopardizing the phone. For hardware subsystems, research, inspect, test harmless existing diagnostics and produce the reports; do not start speculative driver/firmware/TEE work in this mission merely to claim progress.
8. Run the relevant regression/build/package/unit tests and create a clear final report separating physical verification, device-runtime verification, host/offline tests, blocked tests and not-run tests.

### 0.2 Source snapshot facts — starting evidence only, never current truth

The supplied source archive inspected while preparing this prompt was `nuxel-main (12).zip`, with `VERSION` containing `v0.7.7-beta`. The archive did not include a root `SYSTEMD-GRAPH.md`; it did include `docs/s10plus-autonomous-boot-repair/A26-SYSTEMD-BOOT-GRAPH-FIX.md`. This does **not** prove that the user's live checkout lacks `SYSTEMD-GRAPH.md`. Inspect the actual checkout first. If it is absent there too, collect current-device measurements and generate it.

The archive's main device configuration describes:

- Samsung Galaxy S10+ SM-G975F, codename `beyond2lte`, Exynos 9820, Mali-G76 MP12.
- Fedora 43 ARM64 userspace.
- A Samsung downstream Linux 4.14.253 kernel family, with a pinned `Linux4/android_kernel_samsung_exynos9820` source path described in `kernel/s10plus/defconfig` and build scripts. Confirm the exact running kernel, source commit and dirty state before relying on this.
- Phoc/wlroots/Wayland as the compositor/session foundation, a native `nuxel-wl-fb` presenter retaining the DPU20 `/dev/fb0` display path, the Nuxel bridge/PWA host, WebKitGTK and a mixture of native GTK/Flatpak applications.
- A Mali kbase route through `/dev/mali0` and `/dev/udmabuf`, with no `/dev/dri` render node in the historical S10+ GPU evidence.

The archive includes a large number of old mission prompts, compatibility snapshots, device overlays and deployment copies. Some are historical documentation; others may still be build inputs. **Do not decide that a file is unused because it is old, duplicated by name or outside the current-looking directory.** Trace the real build and deployment references.

### 0.3 Important source locations already observed in the archive

Revalidate every path in the current checkout. These are high-value entry points, not a complete file list.

**System/session/compositor/performance**

- `services/nuxel-session/systemd/nuxel-wayland.service`
- `services/nuxel-session/systemd/nuxel-wl-fb.service`
- `services/nuxel-session/systemd/seatd.service`
- `services/nuxel-session/` session scripts and helpers
- `shell/nuxel-shell/`, `shell/nuxel-home-native/`, `shell/nuxel-kiosk/`, `shell/nuxel-phosh-agent/`
- `services/nuxel-bridge/`
- `services/nuxel-performance/` and `services/nuxel-performance/bin/nuxel-perf-tune.sh`
- `tools/s10plus/a45/` native host/navdock/session assets
- `tools/s10plus/a67/` GPU/Mesa/wlroots build, probe and wrapper tooling
- `configs/nuxel/graphics/graphics-profile.json`
- `services/nuxel-metrics/`
- `Makefile`, `images/s10plus/`, `release/s10plus/`, CI and packaging scripts.

**Hardware-specific implementations/configuration**

- Camera: `shell/nuxel-camera-native/`, `shell/nuxel-camera-portal/`, `docs/a52-camera/`, `docs/a53/`, `configs/nuxel/camera/` where present, camera diagnostic tools under `tools/s10plus/`.
- GPS/GNSS: `configs/nuxel/gnss/`, GeoClue configuration, bridge location providers, `tools/s10plus/a33/` diagnostics.
- NFC: `services/nuxel-nfc/`, `configs/nuxel/nfc/`, `kernel/s10plus/patches/0007-sec-nfc-class-name.patch`, device rules and NFC diagnostics.
- Rotation/sensors: `services/nuxel-orientation/`, `configs/nuxel/sensors/`, `tools/s10plus/a33/nuxel-sensors-diag.sh`, the kernel SSP/BBD interfaces and touch calibration integration.
- Fingerprint: `services/nuxel-bridge/src/fingerprint_provider.py`, `configs/nuxel/security/biometric-unlock.json`, kernel/device touch and qbt2000 references, charger/LPM documentation.
- Mobile networking: `configs/nuxel/modem/`, `device/s10plus/deviceinfo`, kernel CP/IPC and Shannon references, `tools/s10plus/a33/nuxel-modem-diag.sh`, NetworkManager/bridge providers.
- LEDs/torch: `configs/nuxel/leds/`, `services/nuxel-bridge/src/led_notification_provider.py`, `services/nuxel-bridge/src/flashlight_provider.py`, `tools/s10plus/a33/nuxel-led-diag.sh`.

### 0.4 Historical hardware findings that need fresh confirmation

Use these as a map of where to look, not as a substitute for current runtime evidence:

- **Graphics:** `docs/beta-finalization/live/PWNAGE-48000-KBASE-GPU-REPORT.md`, `PWNAGE-60000-GPU-MANIFEST.md`, and `docs/beta-finalization/live/GPU-WEBKIT-WSI-DECISION.md` document a Phoc Mali/kbase GPU-rendered route, UDMABUF sharing and a remaining WebKit/GTK Wayland WSI problem. The WSI canary reportedly caused live Phoc crashes and was kept out of the production default. WebKitGTK was explicitly kept on a software fallback at the time. Verify the deployed code and live process before accepting any of those facts as current.
- **Camera:** `docs/a53/CAMERA-PIPELINE-BLOCKERS.md` documents `/dev/video111` as an Exynos FIMC-IS sensor-slot node whose private capabilities did not support standard `VIDIOC_S_FMT`/REQBUFS/QUERYBUF; five sensor devices were reported driver-bound, but no physical frames were proven. The recommended non-destructive direction was a bespoke libcamera pipeline handler using the exact vendor interface, or a carefully scoped standards-based kernel/userspace adaptation. Recheck the real kernel and all nodes.
- **GPS:** `configs/nuxel/gnss/gnss.json` describes a Broadcom BCM4773/BCM47752 BBD/LHD RPC route: `/dev/ttyBCM` is not an NMEA serial port, `/dev/bbd_patch` is the patch loader and `/dev/bbd_control` is a control node. The native protocol reader/firmware/runtime chain was incomplete in the historical baseline. GeoClue IP location must not be confused with GNSS.
- **NFC:** `docs/beta-finalization/live/PWNAGE-65000-NFC-REPORT.md` reports a native daemon, a `/dev/sec-nfc` transport, a firmware file with a verified hash and passing offline ABI/NCI/NDEF tests, but `device_open=false`, `protocol_verified=false` and no physical tag read. It reports NFC OFF by default. The device profile identifies S3NRN82; some historical configuration comments have a conflicting S3FWRN5-family label. Resolve exact silicon/driver identity rather than repeating the stale label.
- **Rotation:** `docs/a69/ROTATION-HARDWARE-BOUNDARY.md` and its PWNAGE-54000/55000 updates describe an LSM6DSO accelerometer/gyro behind a Broadcom BCM47752 SSP sensor hub. The code already tries `ESW:READY` and the accelerometer enable bit, but historical device logs still showed SSP MCU-not-ready, zero raw vectors and no working Android/Bionic LHD runtime. Seven manual/locked orientation modes and compositor/touch mapping already existed. Verify newest service behavior and whether the sensor-hub runtime changed after that report.
- **Fingerprint:** `services/nuxel-bridge/src/fingerprint_provider.py` describes an ultrasonic qbt2000 sensor/driver possibility but refuses enrollment because no verified TEE-backed provider exists. `pwnage-52000.md` discusses charger/LPM gating of touch, qbt2000 fingerprint and Wacom paths. Do not treat a detected device node as an authenticated biometric provider.
- **Cellular:** `device/s10plus/deviceinfo` identifies an integrated Samsung Shannon LTE modem (Cat 20, no 5G) and labels its driver `UNKNOWN_NOT_MM_READY`. `docs/beta-finalization/manual-proof/16-sim-mobile-data.md` describes no upstream ModemManager Shannon plugin/usable CP transport in the tested baseline and expects `NOT_SUPPORTED_ON_DEVICE` or `BLOCKED_FIRMWARE`, with protected EFS/IMEI/calibration paths never touched.
- **LEDs:** `configs/nuxel/leds/leds.json` distinguishes rear flash/torch, a possible front notification LED class that must be enumerated, and “edge lighting” as a display overlay rather than a physical LED. Torch operation is time-bounded, explicit and OFF by default. Verify actual classes/colors on the handset.

All observations above are historical snapshots from the supplied tree (several from October/November 2026). A newer live state can supersede them. Record the source file, capture date, target identity, and evidence tier for every adopted finding.

---

## 1. OPERATING SAFETY AND FUNCTIONALITY PRESERVATION

### 1.1 Repository hygiene

Before changing anything:

1. Record `pwd`, `git status --short --branch`, branch, HEAD, recent commits, `VERSION`, architecture, active device configuration and all uncommitted work. If the archive does not contain `.git`, say so; do not invent a branch or commit.
2. Inspect the current working tree and deployment target. The local source tree, image staging tree, currently installed phone rootfs and any copied deployment tree may differ.
3. Preserve pre-existing user modifications. Never `git reset --hard`, `git clean -xfd`, overwrite an untracked file, stash/drop work, or replace a whole directory as a shortcut.
4. Make an auditable list of changed files and create a reversible snapshot for each system configuration/unit/binary being changed.
5. Do not deploy automatically merely because an image builds. Do not reboot, shut down, power-cycle or restart a critical service until access and recovery paths are verified.

### 1.2 No-service-break invariant

“Faster” does not justify broken behavior. The following must be treated as protected functions and regression-tested where present:

- Boot into a visible, interactive Nuxel session and reliable fallback if the GPU route fails.
- Panel/display output, touch, input coordinate calibration, keyboard/OSK, orientation policy and nav dock.
- Lock/unlock security, screen-off/wake, Home/Back/Recents, launcher/app drawer and PWA lifecycle.
- SSH/Wi-Fi/LAN access, USB/serial Live Console and remote desktop/VNC/RDP where configured.
- NetworkManager profiles, DNS/TLS/browser connectivity, Bluetooth and radio toggles where supported.
- Audio routing, speaker, headset, microphone permissions and haptics.
- Battery/charger mode, thermal management, power key handling and safe shutdown.
- Flatpak isolation, permissions, portals, user namespaces and application launch.
- NFC OFF-by-default safety, camera privacy, fingerprint PIN fallback and LED torch timeout.
- System update, Nuxtore/catalog signing, image build, package installation and rollback.

Before a unit, package, script or code path is modified, identify its consumer(s), dependencies, runtime ownership, health/readiness contract, startup/shutdown ordering, failure mode and rollback. A service being inactive on one boot, absent in a fixture or disabled by default does not prove it is unused.

### 1.3 Prohibited shortcuts

- Do not disable a service merely because it appears late in `systemd-analyze blame`; blame duration is not equivalent to critical-path contribution.
- Do not remove `After=`/`Requires=`/`Wants=` relationships without proving why they exist and exercising both success and failure cases.
- Do not turn `Type=notify` into `Type=simple`, or vice versa, without implementing and testing the actual readiness semantics.
- Do not replace readiness checks with arbitrary `sleep` delays or reduce timeouts so failures are hidden.
- Do not mask or disable a failure-producing service while leaving its callers expecting it.
- Do not create a timer/service that starts a process just to kill it or to undo another unit's startup. Trace and fix the original owner/condition.
- Do not leave the old implementation in the image and add a second wrapper to make it appear removed.
- Do not delete fallback, recovery, diagnostics or rollback code unless there is a tested replacement with the same safety behavior.
- Do not remove historical reports, audit logs or test fixtures simply because they describe obsolete implementation. Retain documentary provenance; clean only dead executable/configuration paths and stale deployment artifacts.
- Do not globally change governors, thermals, CPU affinity, memory pressure, swap, GPU clock, SELinux/AppArmor, sandbox, network manager, initramfs or kernel config without measurements and a proven rollback.
- Do not flash BOOT, SYSTEM, vendor, modem, EFS, persist or any partition. Do not enter Download Mode or alter bootloader/AVB/Knox state.
- Never dump credentials, private keys, Wi-Fi PSKs, SIM identifiers, IMSI/ICCID/IMEI, biometric templates, GPS history or personal media into reports.

### 1.4 Change risk classes

Classify every proposed change:

- **R0 — evidence only:** read-only inspection, tests, profiling, report generation.
- **R1 — isolated source-only optimization:** no runtime behavior or installed system change.
- **R2 — reversible userspace/unit/package change:** requires staged install, health checks and rollback.
- **R3 — kernel/firmware/driver/TEE/boot integration:** report/prototype only in this mission; no handset deployment or flashing.
- **R4 — partition/security/identity/thermal-critical:** prohibited.

Implement R0/R1 and safe R2 only. R3 belongs in hardware reports and isolated non-deployed branches/build artifacts where it is useful. R4 must not be performed.

---

## 2. PHASE ZERO — MAXIMUM-DETAIL CURRENT-STATE AUDIT

Do not begin by editing services. Build an evidence map first.

### 2.1 Establish the target and build provenance

Record:

- Repository root, branch/commit when available, `VERSION`, dirty state and archive/source origin.
- Which device profile is selected (`s10plus`, `g7power`, `google-pixel-10-pro-xl`, or other), actual phone model/codename/SoC/architecture, kernel release/build ID and userspace release.
- Boot ID, uptime, root filesystem, systemd version, initramfs path and boot chain. Never assume the connected device is the S10+ because its files are present.
- Current deployed hashes for compositor, Wayland libraries, presenter, bridge, session manager, hardware providers, units, PWA bundles and relevant configuration. Compare them with the repo and image staging output.
- Actual hardware/software environment: CPU topology/frequency/thermal state, RAM and pressure, storage device/filesystem/free space, GPU driver/device nodes, display refresh/resolution, input devices, network, battery and audio.
- Build toolchain and exact commands required to produce the real rootfs/release image. Locate the canonical packaging route.

No secrets should be printed. Hash configuration files after redacting credential-bearing lines if necessary.

### 2.2 Map code ownership and data flow

Create an audit matrix for all active system responsibilities:

| Responsibility | Source implementation | Runtime process/unit | API/IPC | Dependencies | Readiness signal | Consumers | Build/package inclusion | Evidence |
|---|---|---|---|---|---|---|---|---|

At minimum map:

- PID 1/systemd boot stages, initramfs handoff, storage mount, udev/device setup.
- NetworkManager, Wi-Fi supplicant, DHCP/DNS and firewall.
- Seat/input stack, Phoc/wlroots, Wayland socket, compositor renderer, display/panel driver.
- `nuxel-wl-fb`/frame presenter and every buffer copy/conversion/scale.
- PWA host/WebKit processes, Home/launcher, native GTK apps, Flatpak apps and their portals.
- Nuxel bridge, D-Bus services, session service, nav dock, statusbar, notification service, keyboard, orientation service.
- GPU metrics and performance tuning.
- Audio, camera, NFC, GNSS, fingerprint, modem and LED providers.
- Remote access/Live Console, SSH, XRDP/VNC and USB gadget services.

Follow calls in both directions: who starts a service, who starts its helpers, who opens the resource, who publishes ready, who consumes the state, who stops it, and what happens if it fails.

### 2.3 Duplicate and contradictory implementation search

Search for:

- Duplicate service ownership (same daemon started by systemd and a session script; timer plus watcher; multiple providers claiming the same D-Bus name; parallel pollers doing the same sysfs reads).
- Start-then-stop patterns, race-prevention services that compensate for the wrong owner, transient helper daemons kept alive by repeated polling, stale watchdogs and duplicate fallback paths.
- Multiple copies of the same source compiled/installed from old numbered directories, active package lists, image manifests, release overlays, runtime overrides and local deployment scripts.
- Dead source that is never imported, executed, built, installed, packaged, tested or referenced; stale binaries in rootfs staging; obsolete generated caches and manifests.
- Code that was meant to be removed in previous Nuxel missions but remains in active source, a second copy, generated artifact or package.

Run searches over executable source, systemd files, rootfs builders, packaging manifests, release scripts, PWA registries, initramfs scripts, udev rules, D-Bus activation files, desktop entries and tests. Include case-insensitive variations and dynamic string references; a simple `rg` no-hit is not sufficient proof when paths are assembled at runtime.

### 2.4 Explicit removal ledger

Create a temporary working ledger and include the final version in the final report:

| Candidate | Earlier instruction/decision that rejected it | Current source locations | Runtime/build references | Why obsolete | Replacement owner | Tests required | Decision |
|---|---|---|---|---|---|---|---|

Use only clear evidence to mark an implementation for deletion. If a prior instruction is ambiguous, report the candidate and leave it alone. Do not interpret “we used to do X” as blanket permission to remove unrelated safety code.

For every accepted removal:

1. Remove the obsolete implementation itself.
2. Remove its active callers, unit/install references, package entries, generated copies and build integration.
3. Remove stale configuration that only serves the removed code.
4. Update tests to assert the old path cannot return and the replacement owner remains functional.
5. Update documentation while retaining historical documents and linking them to the superseding implementation/report.
6. Build the image/package and inspect the output to ensure the old executable/configuration is actually absent.

Do not replace a dead process with an equivalent hidden process, a new watchdog or a `Condition...` workaround that merely conceals the duplicate.

### 2.5 Baseline evidence bundle

Save timestamped evidence under a dedicated path such as `diagnostics/pwnage-91000/baseline/`. Capture:

- `systemctl list-units --all`, `systemctl list-unit-files`, `systemd-analyze --version`, `systemd-analyze time`, `systemd-analyze blame`, `systemd-analyze critical-chain`, unit dependency graphs and failed units.
- Active services and processes with elapsed time, CPU, RSS, open descriptors and cgroup membership (avoid exposing private command-line arguments or environment secrets).
- Compositor process environment with secrets redacted, GPU fd/map state, buffer allocation/transport data, display bridge health and renderer identity.
- Frame pacing, input-to-frame latency, scroll/animation smoothness, CPU use per compositor/UI process and memory bandwidth/copy volume when instrumentation permits.
- Network, storage, audio, display, touchscreen, power and hardware provider status.
- Test suite results before changes.

Every output must identify `HOST`, `DEVICE`, `FIXTURE` or `BUILD-IMAGE`; these categories are not interchangeable.

---

## 3. SYSTEMD BOOT AND SHUTDOWN OPTIMIZATION — `./SYSTEMD-GRAPH.md`

### 3.1 Establish whether the graph exists and is current

1. Inspect `./SYSTEMD-GRAPH.md` in the actual checkout and the live phone. Check its capture date, boot ID, kernel/systemd version, device identity, command receipts and whether it matches the currently deployed units.
2. If it is absent, stale, from another device, or based on a different set of units, generate a fresh graph **before** optimizing. Do not infer current timings from a historical prompt.
3. Read `docs/s10plus-autonomous-boot-repair/A26-SYSTEMD-BOOT-GRAPH-FIX.md` as related historical context only; it is not a replacement for fresh graph data.
4. Record limitations: systemd startup plots are boot timelines, not full shutdown timelines. Do not present a boot plot as proof of shutdown performance.

### 3.2 Boot capture

Use supported commands on the phone, where installed:

- `systemd-analyze time`
- `systemd-analyze blame`
- `systemd-analyze critical-chain`
- `systemd-analyze plot > diagnostics/systemd/boot-<boot-id>.svg`
- `systemctl list-units --all`
- `systemctl list-unit-files`
- `systemctl --failed`
- `journalctl -b -o short-monotonic` and targeted unit journals.

Capture the boot ID and monotonic origin. Record firmware, bootloader, kernel, initrd and userspace portions only when the tool exposes them. Add timestamps for meaningful Nuxel milestones (storage usable, udev settled, Wayland socket ready, compositor ready, panel presenter ready, lockscreen visible, first interactive frame, network ready, desktop/app readiness) using existing markers or low-overhead instrumentation. Do not invent milestone values if they are not instrumented.

### 3.3 Shutdown capture

Use real logs only:

- Inspect `journalctl --list-boots`, previous boot journals, final monotonic timestamps, systemd shutdown messages and `systemd-shutdown` logs.
- Identify each slow stop/timeout, filesystem unmount, sync, network teardown, remote session stop, app cleanup and service kill/timeout only when the logs show it.
- If persistent journaling was disabled or the previous shutdown was not captured, mark it `NOT_CAPTURED`. Add a safe next-shutdown capture procedure; do not fabricate stop durations.
- Do not initiate a shutdown/reboot for measurements if it could sever the only recovery/access channel or if a safe route has not been confirmed. A physical shutdown capture must be a controlled operator-supervised test.

Where enough real events exist, generate a separate shutdown timeline SVG (for example, `diagnostics/systemd/shutdown-<boot-id>.svg`) and include raw sanitized journal evidence. Make the limitations explicit.

### 3.4 Correct dependency analysis

For every enabled/active/critical-path service, understand:

- `After=` ordering versus `Wants=`/`Requires=` pull-in semantics.
- `Before=` and `Conflicts=` interactions.
- `Type=simple`, `exec`, `notify`, `oneshot`, `dbus`, `forking` semantics.
- `RemainAfterExit`, `ExecStartPre`, `ExecCondition`, `ExecStartPost`, `ExecStop`, `ExecStopPost`, restart policy, start-limit, timeout and watchdog configuration.
- Device dependencies from udev, mount dependencies, network-online assumptions, D-Bus availability, socket activation and graphical target/session readiness.
- Whether a service provides a true readiness event or merely starts a process that becomes ready later.

Do not add `network-online.target` to every unit. Do not force optional hardware daemons into the critical path. Do not make the session depend on GNSS, NFC, camera, remote desktop, map tiles, Bluetooth scans or other optional features unless the feature's actual contract requires it.

### 3.5 Find safe boot opportunities

Look for measurable improvements such as:

- Expensive optional work incorrectly placed before first usable UI.
- Duplicate device scans/probes done independently by session, bridge, metrics and providers.
- Polling that can become event-driven via udev, D-Bus, systemd path/socket activation or a single shared collector.
- `ExecStartPre` that repeats a test already performed by the owning daemon at startup.
- Helper programs spawned only to query a value already available from an existing provider.
- Long fixed sleeps used instead of a bounded readiness check.
- Services with broad target dependencies despite having no dependency on those targets.
- Expensive telemetry, icon scanning or app registry rebuilding that can safely happen after the lockscreen/launcher first frame.
- Sequential initialization that can be parallelized while preserving the exact dependency graph.
- Excessive `RestartSec`, start-limit behavior or stop timeouts that do not match real recovery semantics.

Only parallelize independent operations. Preserve deterministic readiness ordering and the UI fallback.

### 3.6 Shutdown opportunities

Look for actual stop delays and timeouts, not assumptions:

- Services that wait indefinitely for a child/helper that has already exited.
- Long stop timeouts on processes that have bounded cleanup.
- Duplicate save/flush operations to the same state store.
- Services stopped after a dependency has already disappeared.
- Stop hooks that perform network calls, slow discovery or user-data scans unnecessarily.
- Orphan helper processes that systemd cannot track or terminate cleanly.

Do not reduce graceful shutdown below the time needed to save user data, close database transactions, stop media capture safely, flush filesystem state or leave the panel in a safe state. Never use `KillMode=process` or a weaker kill policy merely to make shutdown look faster.

### 3.7 Systemd deliverable

Create/update `./SYSTEMD-GRAPH.md` containing:

1. Device identity, boot ID, kernel, systemd version, timestamps and evidence provenance.
2. Boot time summary (all available phases).
3. Critical chain plus complete relevant unit graph.
4. A readable service timing table with total duration, critical-chain contribution, state and dependencies.
5. Failed/degraded units and whether each is expected, optional or a real defect.
6. Shutdown timeline/table only where backed by captured evidence; otherwise clearly `NOT_CAPTURED` with a precise capture recipe.
7. The top optimization opportunities ranked by measured impact, risk, dependency confidence and reversibility.
8. Before/after numbers after safe changes, tied to matched boot conditions/boot IDs.
9. A service preservation matrix showing each protected service's before/after state and functional check.
10. Commands/scripts and raw evidence locations so another engineer can reproduce the graph.

Save source data and SVG plots under `diagnostics/systemd/`. Keep credentials, connection secrets and user content out of the artifacts.

---

## 4. COMPOSITOR, RENDERING, INPUT AND UI SMOOTHNESS

### 4.1 Trace the entire frame path

Build a real path diagram of one interactive frame, from input or app update to AMOLED presentation:

`touch/key event → libinput/input owner → Phoc/wlroots event loop → surface commit → renderer/composition → buffer export/transport → nuxel-wl-fb or current panel owner → framebuffer/DSI/DPU → visible scanout`.

Include PWA/WebKit and GTK application paths separately. Identify every copy, scale, color conversion, format conversion, synchronization fence, blocking IPC call, context switch and extra surface. Distinguish:

- GPU rendering;
- GPU composition;
- GPU buffer allocation;
- dma-buf/udmabuf import/export;
- SHM buffer presentation;
- CPU framebuffer copying/scaling;
- hardware display-controller scanout/overlay;
- hardware video decode;
- software image/video decode.

These are separate capabilities. Do not label the complete UI “fully GPU accelerated” merely because the compositor owns a Mali fd or because a surfaceless GL probe can render pixels.

### 4.2 Profile before optimizing

Measure, where supported:

- Frame interval distribution and missed frames (p50/p90/p95/p99), not only average FPS.
- Touch/input event to visible frame latency.
- CPU time per process/thread, context switching and event-loop stalls.
- Buffer dimensions, formats, stride, bytes per frame, actual buffer count and copies per frame.
- Time spent in `phoc`, wlroots renderer, WebKitWebProcess, GTK, `nuxel-wl-fb`, bridge and other session components.
- GPU utilization/clock/memory/context, GPU driver and GL renderer in the actual compositor process.
- CPU cost of software fallback, image decode, compositing, scaling and framebuffer pan/update.
- Thermal state, frequency throttling, memory pressure and storage stalls during representative use.

Test these scenarios: idle Home, app drawer scroll, app open/close, fullscreen app, browser scroll, keyboard open/type, Quick Settings open/close, lock/unlock, notification update, media playback, external display if available. Use a repeated, deterministic visual workload and keep the device thermally comparable.

### 4.3 Audit compositor/session ownership

Inspect current owners and lifecycles for:

- Phoc and its wlroots renderer/environment.
- Wayland startup wrapper and GPU fallback selection.
- `nuxel-wl-fb` framebuffer/panel presentation.
- Native statusbar/navdock/animation layers.
- PWA host and WebKitGTK subprocesses.
- Bridge and any native helper/proxy.
- GPU/metrics collector and performance tuning service.
- Input/calibration/orientation libraries and services.

There must be one authoritative owner per responsibility. A wrapper is acceptable when it makes an actual atomic choice (GPU candidate or known-safe fallback); a service whose sole job is to stop another service after it starts is not acceptable. Remove the root cause of the race instead.

### 4.4 Investigate inefficient wiring

Search for:

- Repeated full-screen buffer copies when damage-region copies or page-flip updates are possible.
- Repeated conversion between ABGR8888/XRGB8888/ARGB8888/RGB formats.
- Unnecessary CPU scaling when source and destination dimensions are identical.
- Duplicate rotation transforms (compositor + presenter + input mapping).
- Double buffering/triple buffering configured in a way that adds latency or causes stale frames.
- Copying through SHM when a safe dma-buf or directly mappable buffer can be shared.
- Excessive full-damage commits and unnecessary redraws of static surfaces.
- Main-loop polling or synchronous bridge HTTP/D-Bus calls that block frame dispatch.
- Repeated registry scans, file/asset stats, icon decode or status polling on every unlock/launcher refresh.
- Two independent event loops that repeatedly publish the same state.
- A status/animation layer kept alive when hidden or inactive.

Do not replace a working display pipeline just to achieve a more elegant diagram. A stable CPU bridge may remain the correct path until a new display ABI is proven.

### 4.5 Optimize safely

Preferred techniques, only when measurements support them:

- Reduce redundant work at the actual source.
- Share cached immutable data and device inventory across readers.
- Use event-driven notification and coalesced state updates.
- Preserve surface/buffer identity for unchanged content.
- Use damage tracking when the panel path supports it.
- Avoid duplicate decode/conversion and preserve source-native formats.
- Move optional probes out of the first-frame/interactive path.
- Bound worker queues and IPC timeouts; avoid unbounded backlog.
- Use a single clock/timestamp strategy (monotonic for intervals).
- Keep GPU fallback deterministic and recoverable.

Do not trade away image quality, touch responsiveness, accessibility, color correctness, screen security or app isolation for a benchmark improvement.

### 4.6 Acceptance

Show measurable baseline and after metrics under comparable conditions. A claimed smoothness improvement needs frame-time/input latency evidence, not visual adjectives. Confirm no regression to panel output, touch, orientation, keyboard, Home/Back, lockscreen, app transitions, WebKit/Flatpak rendering, external displays and fallback startup.

---

## 5. CLEANUP: REMOVE ACTUALLY UNUSED SERVICES AND CODE, NOT JUST HIDE THEM

### 5.1 Define “unused” rigorously

A candidate is removable only if all of these are established:

- It is not started at runtime by systemd, user systemd, D-Bus activation, udev, session scripts, app launch, cron/timers, socket activation or dynamic plugin loading.
- It is not required by the boot/rootfs/release builder, package post-install scripts, generated manifests, OTA/update tooling, rescue image or supported secondary device profile.
- It is not a fallback needed when the preferred implementation fails.
- It is not consumed by a diagnostic, developer workflow, installer, test, migration or rollback procedure that is still supported.
- A supported replacement owns the same public contract and passes equivalent tests.

If any point is unknown, do not delete it. Flag it as `REVIEW_REQUIRED`.

### 5.2 Remove rejected historical implementations

Search earlier Nuxel prompt/report decisions for explicitly rejected strategies and cross-check active code. Examples to investigate, not blindly delete:

- Duplicate/legacy service owners for current navdock/statusbar/animation/session functionality.
- Old compositor launch paths that conflict with the canonical session manager.
- Old device-specific service copies accidentally included in the S10+ image.
- Obsolete PWA bridge providers that have been superseded by a native provider or service.
- Old camera portal APIs that impersonate a standard portal with incompatible methods.
- Deprecated graphics WSI or Mesa builds that are not the selected release artifact.
- Old firmware/driver manifests inconsistent with current device identity.
- Temporary debug scripts or startup hacks installed into production images.

For each, prove the current owner and active package contents. Historical prompts and reports remain useful records and should usually remain in `docs/`.

### 5.3 No “cleanup service” smell

If service B starts only to stop, mask, kill or overwrite process A, investigate why A is started and fix the source owner. Do not keep adding layers such as:

- start old daemon → detect duplicate → kill old daemon;
- start default compositor → service restarts it with custom environment;
- initialize hardware in two services → one races and resets it;
- load default config → late service rewrites it;
- spawn poller → another poller notices and shuts it down.

The proper fix is usually one unit, one owner, one configuration source and an explicit readiness/fallback protocol. Never remove an intentional safety gate without retaining its safety property.

### 5.4 Cleanup test gates

After every removal, run:

- Unit tests and integration tests for the owning subsystem.
- Systemd unit validation and dependency graph checks.
- Rootfs/image build and package manifest checks.
- Runtime unit/DBus activation checks on a staged or test device.
- Search for old binary/config paths in the built image.
- A feature regression matrix proving the replacement still covers all previous behavior.

Do not report “removed” if the old binary or config is still copied from another builder tree or retained in the deployed image.

---

## 6. `./GPU-ACCEL-REPORT.md` — COMPLETE ACCELERATION GAP ANALYSIS

This is a technical report and staged recommendation, not a request to force every application onto an experimental driver.

### 6.1 Required inventory

Inspect the exact running S10+ kernel config, GPU driver, userspace libraries, EGL vendor dispatch, Mesa build, Phoc/wlroots libraries, dma-buf/udmabuf support, `nuxel-wl-fb`, WebKitGTK/GTK runtime, Flatpak GL extensions, video decoder/MFC and camera/ISP path. Confirm installed artifacts against `release/s10plus/gpu/gpu-manifest.json` and checksums where applicable.

Produce a component table with one status per actual layer:

| Layer/component | Current renderer/driver | Allocator/transport | Present path | Hardware evidence | Status | First missing stage | Recommended work |
|---|---|---|---|---|---|---|---|

At minimum cover:

1. Mali-G76 kbase kernel driver and context creation.
2. Mesa GLES/EGL userspace and GLVND vendor selection.
3. Phoc/wlroots rendering and scene composition.
4. dma-buf/UDMABUF allocation/export/import and Wayland buffer protocols.
5. Display/panel scanout via Exynos DPU20 `/dev/fb0` and `nuxel-wl-fb`.
6. CPU copy, scale, rotate, format conversion and presentation costs.
7. WebKitGTK compositing and accelerated backing store.
8. GTK/GSK application rendering.
9. Flatpak graphics ABI/runtime extension and sandbox device exposure.
10. Video decode/encode and Exynos MFC separately from 3D GPU acceleration.
11. Image decode, text rasterization and UI asset paths where acceleration matters.
12. External display and casting/mirroring path if it shares GPU buffers.

### 6.2 Historical S10+ baseline to re-check

Historical evidence reports:

- Mali-G76 MP12 driven by Samsung kbase (`/dev/mali0`), not a standard DRM render node.
- `CONFIG_DRM=y` while `CONFIG_DRM_EXYNOS=n` was retained to avoid the Exynos DRM driver claiming the existing DPU20 fbdev platform path; `CONFIG_UDMABUF=y` added.
- Phoc with a kbase-aware Mesa/wlroots path and GLES2 renderer; Phoc GPU context and `FRAMES_OK` were observed.
- A surfaceless kbase renderer could create real GL content, and UDMABUF-backed output buffers were tested.
- The final display path remained `/dev/fb0`/DPU20, with `nuxel-wl-fb` CPU presentation/copy still a possible limiting stage.
- WebKitGTK/GTK did not have a proven production Wayland EGL/dma-buf path in the last documented baseline. A canary global `zwp_linux_dmabuf_v1` path reportedly crashed live Phoc during screencopy, so production was reverted to the known-safe compositor path and WebKit software fallback.

These are not assumptions to carry forward without measurement. Search current source and check actual phone processes/libraries after recent work.

### 6.3 Recommendation requirements

For each remaining unaccelerated component, give:

- The exact reason (missing kernel API, missing EGL platform, buffer format/modifier mismatch, dma-buf feedback, synchronization fence, sandbox access, toolkit limitation, library ABI, software fallback, crash, lack of evidence, or not applicable).
- Whether the fix is userspace-only, requires Mesa/wlroots/Phoc patching, a kernel ABI change, device-tree/driver work, package/runtime changes or a different architecture.
- The least risky compatible route, alternatives and why they are worse.
- A reproducible isolated proof-of-concept plan with rollback and explicit gates before live enablement.
- Performance/power/thermal tradeoffs and exact tests needed on the phone.
- The reason a generic “install Panfrost” or “set `WEBKIT_DISABLE_COMPOSITING_MODE=0`” is not sufficient if it does not address the actual WSI/export/import/presentation path.

Do not call the compositor fully accelerated if WebKit remains on software or if final panel presentation is CPU-copy-bound. Report partial acceleration precisely. Do not call MFC video decode “GPU acceleration”; report it as a separate hardware media engine with its own status.

### 6.4 Required conclusion

End with a ranked roadmap: immediate safe software/bridge improvements; isolated WebKit/GTK WSI research; safe compositor buffer/presentation improvements; Flatpak/runtime integration; kernel/driver prerequisites; and items that are impossible on the present kernel/ABI without a larger kernel/stack migration. Identify the exact first experiment that will reduce the most uncertainty.

---

## 7. `./REPORT-CAMERA.md` — FULL CAMERA COMPLETION ROADMAP

### 7.1 Enumerate the actual camera system

Identify all rear/front sensor modules and exact variants from runtime kernel logs, DT/DTBO, I2C identities and vendor device information. Do not infer sensor model from a filename or from a generic S10+ specification. Map:

`sensor → I2C/control bus → regulator/clock/reset/GPIO → MIPI CSI → CSI receiver → FIMC-IS ISP/3A/MCU → V4L2 node/private ioctl → DMA buffer → userspace pipeline → PipeWire/portal → Camera app`.

Inspect `/dev/video*`, `/dev/media*`, `/dev/v4l-subdev*`, sysfs drivers, media-controller graph (if any), `VIDIOC_QUERYCAP`, `ENUM_FMT`, `TRY_FMT`, `S_FMT`, `REQBUFS`, `QUERYBUF`, `QBUF`, `DQBUF`, stream-on/off, IRQ/clock/regulator state, firmware/setfile files, IOMMU and DMA heap support. Each ioctl must be run only on an identified harmless capture node with a bounded diagnostic; do not disturb active camera owners.

### 7.2 Existing blocker to verify

The A53 report says `/dev/video111` was an `exynos-fimc-is-30c` slot advertising multi-plane capture plus Samsung private extended pixel format, but standard `VIDIOC_S_FMT` returned `errno=25` and REQBUFS/QUERYBUF failed. It described five sensor devices bound but no standard media graph, no real frame capture, no camera setfile/ISP firmware and no compatible libcamera pipeline handler. Re-run exact diagnostics; identify the first current failing stage.

### 7.3 Best route analysis

Compare at least:

- A dedicated `libcamera` Exynos FIMC-IS pipeline handler speaking the exact private ioctl/control ABI.
- A focused vendor-kernel adaptation exposing standard V4L2/media-controller entities and a maintainable userspace API.
- Reusing a supported upstream/open-source Exynos camera stack if it actually supports this SoC/kernel/ISP.
- A lawful, isolated compatibility runtime for Samsung vendor camera binaries only if licensing, ABI, dependencies, HAL services and security model are understood.

Identify required setfiles, firmware, sensor tuning, calibration, OIS/actuator support, ISP/3A algorithms, formats, buffer allocator and synchronization fences. Determine which sensor modules have usable tuning/firmware and what quality/features would be lost without them.

Do not claim success from a camera node, a test pattern, USB UVC, synthetic source, successful libcamera installation or an app preview window. Physical capture requires changing real scene content and verifying unique timestamped frames from the integrated sensor.

### 7.4 Report roadmap

Include minimum viable rear-primary still/preview first, then focus/exposure/white balance, front camera, additional lenses, video, stabilization/OIS and advanced modes. For every phase state required kernel patch, userspace library/handler, firmware, configuration, portal/API and test. Include build feasibility, license/provenance, owner authorization and risks. Do not write to camera calibration/EEPROM or raw sensor registers during this mission.

---

## 8. `./REPORT-GPS.md` — FULL GNSS COMPLETION ROADMAP

### 8.1 Separate location types

Separate GPS/GNSS fixes from IP geolocation, Wi-Fi location, cached location and manually entered map positions. GeoClue may work through a network source while the GNSS receiver is unavailable; those are different states.

### 8.2 Trace exact Exynos 9820 path

The repository config identifies a Broadcom BCM4773/BCM47752-family integrated path using BBD/LHD RPC, with `/dev/ttyBCM` as packet transport (not NMEA), `/dev/bbd_patch` as patch loader and `/dev/bbd_control` as control interface. Inspect current device tree, driver binding, device nodes, firmware provenance, vendor `/vendor/bin/hw/lhd`/`gpsd`, configs/HIDL dependencies and current rootfs.

Trace:

`GNSS silicon → SPI/serial/SSP transport → kernel driver → BBD patch firmware → LHD/BBD protocol → GNSS daemon/decoder → position provider → GeoClue → permission agent → Maps/consumer`.

### 8.3 Determine the first real blocker

Check for:

- Physical GNSS integration and antenna path for this exact model/board.
- Driver/DT binding and whether a real device node is exposed.
- Valid BBD transport exchange and control path.
- Correct firmware/patch file with exact revision/hash, device match and license/provenance.
- Compatible native or vendor runtime to load the patch and perform BBD/LHD RPC.
- A decoded, timestamped position stream with accuracy and source fields.
- GeoClue provider integration and authorization.

Do not run NMEA parsing against `/dev/ttyBCM` unless live evidence establishes that protocol; repository documentation specifically describes it as a BBD packet transport. Do not claim a location fix from SPI presence, bytes, a network estimate or static coordinates.

### 8.4 Recommended end-state

Compare a lawful native BBD/LHD protocol implementation against an isolated vendor runtime (only if the necessary Bionic/HIDL stack can be safely and legally isolated). Specify how the firmware is sourced and verified. Include cold/warm start, assistance/network requirements, antenna and outdoor tests, power policy, suspend/resume, privacy permission and Geoclue adapter design.

A GNSS PASS requires a fresh receiver-reported coordinate, timestamp and accuracy outdoors, with a credible time-to-first-fix and source. Do not publish private location coordinates in ordinary reports; use redacted/sanitized evidence.

---

## 9. `./REPORT-NFC.md` — FULL NFC COMPLETION ROADMAP

### 9.1 Resolve identity first

The device profile identifies Samsung S3NRN82 at I2C address `0x27`; a historical NFC policy comment labels an S3FWRN5-family controller. Resolve this discrepancy from exact board DT, driver source, chip ID/revision, device logs and firmware header. Do not copy a driver/firmware for a different part based solely on a family name.

### 9.2 Audit the current software

Inspect:

- `kernel/s10plus/configs/live-required.config` and NFC kernel symbols/patches.
- `services/nuxel-nfc/` exact ioctl ABI, transport, NCI framing, NDEF parser, state machine, Unix socket permissions and service unit.
- `/dev/sec-nfc`, sysfs class, I2C binding, IRQ/reset/wake GPIO, regulators, clocks, firmware mode and firmware file hash.
- Bridge/UI APIs, Settings/Quick Settings, permission manager and OFF-by-default behavior.
- Tests in `tests/pwnage65000` and `tools/s10plus/a33/tests/hw-subsystems/`.

### 9.3 Re-check prior baseline

PWNAGE-65000 reported a verified NFC firmware blob (151,852 bytes), `/dev/sec-nfc`, protocol adapter ready, offline ABI/NCI/NDEF tests passing, but `device_open=false`, `protocol_verified=false`, no physical tag read and OFF by default. Confirm the current live device. Do not promote `controller_present` or a fixture selftest into “NFC works.”

### 9.4 Define real completion

Minimum hardware acceptance:

- Controller powers on/off reliably and firmware is accepted by the real device.
- IRQ/polling/receive path functions without stuck wakeups.
- A known physical NDEF tag is detected and read correctly with source/timestamp and bounded scan.
- Repeated scans, suspend/resume, screen lock, app cancellation and daemon restart behave correctly.
- Controller returns OFF and releases the device when requested.

Separately report card emulation/HCE, secure element, payment, access cards, ISO-DEP, MIFARE variants and writing. Never imply these are supported because basic tag reading works. Do not write tags during baseline testing. Payment/eSE work needs a separate security/SE/TEE roadmap.

---

## 10. `./REPORT-ROTATION.md` — FULL ACCELEROMETER/GYROSCOPE/AUTO-ROTATION ROADMAP

### 10.1 Audit existing software first

Inspect `services/nuxel-orientation`, `SensorHubControl`, all seven orientation modes, persisted policy, daemon startup/supervision, compositor transform, touch coordinate remap and input ownership. The repository already has a seven-mode state machine and test suite; do not replace it with a simpler competing rotation daemon.

### 10.2 Trace the S10+ sensor chain

Historical evidence identifies an LSM6DSO accelerometer/gyro behind a Broadcom BCM47752KUB1G SSP sensor hub (`ssp,BCM4773`). The Nuxel owner already attempts `ESW:READY` on `/dev/bbd_control` and setting the accelerometer bit in `/sys/class/sensors/ssp_sensor/enable`, then waits for nonzero `/sys/class/sensors/accelerometer_sensor/raw_data`. Earlier live diagnostics showed MCU-not-ready/timeouts and all-zero vectors despite accepted writes. Vendor `lhd`/sensorhub libraries were found on read-only vendor in one audit, while the Android linker/Bionic runtime needed to execute them was not present in the Nuxel system rootfs.

Revalidate exact MCU identity, nodes, IIO exposure, input events, raw data, gyro data, enable bits, power and logs. Distinguish “driver bound,” “hub powered,” “MCU patched,” “sensor enabled,” “real data streaming,” “orientation calibrated” and “display event applied.”

### 10.3 Best route

Compare:

- A lawful native implementation of the Samsung/Broadcom BBD/SSP handshake and patch protocol.
- A narrowly isolated vendor sensor-hub runtime with required linker/Bionic dependencies, if licensable and safe.
- A direct LSM6DSO driver path, if the physical wiring truly allows host I2C/SPI access outside the SSP and the sensor is not exclusively hub-owned. Prove this from DT and schematics before recommending it; do not simply bind a second driver to an occupied device.
- Any upstream/mainline sensor-hub support, only if it targets the actual silicon/firmware ABI.

The final solution must provide real accelerometer and gyro samples, correct scale/units, timestamps, axis mount matrix, calibration, sensor fusion/hysteresis, orientation policy, Wayland transform and matching touch mapping. Keep manual/locked rotation modes working at all times. Do not produce synthetic gravity data to make Auto appear enabled.

### 10.4 Acceptance

Physical tilt/rotate tests must prove axes change and settle, all supported portrait/landscape modes map correctly, touch coordinates remain aligned, and lock/wake/suspend/resume work. Report acceleration and gyro independently if one is available without the other.

---

## 11. `./REPORT-FINGERPRINT.md` — FULL ULTRASONIC FINGERPRINT ROADMAP

### 11.1 Current software boundary

Inspect `services/nuxel-bridge/src/fingerprint_provider.py`, biometric configuration, Settings/Quick Settings, lockscreen authentication and PIN fallback. The historical provider deliberately refuses enrollment because it has not established an exact-sensor secure provider. `fprintd`/`libfprint` presence alone does not imply qbt2000 support.

### 11.2 Identify the exact part and transport

The S10+ uses an under-display ultrasonic fingerprint sensor historically referred to as qbt2000 in Nuxel notes. Prove exact sensor/vendor/revision, SPI/I2C/secure transport, kernel driver binding, device node, firmware, interrupt and power path. Check charger/LPM gating; do not confuse cold charger mode with normal interactive mode. Do not read or export enrolled templates.

### 11.3 Secure architecture required

A complete design must trace:

`sensor → kernel driver → secure-world/TEE boundary → trusted application/firmware → enrollment/authentication service → OS biometric API/pam/system service → lockscreen authorization`.

Determine whether the exact sensor relies on a Samsung TrustZone trusted application, keymaster/secure storage, vendor daemon, secure clock or OEM-specific HAL. Identify lawful redistributable components and ABI requirements. Explain how to implement or port the missing pieces without bypassing secure boot, TEE, anti-spoof checks or template protection.

### 11.4 No unsafe imitation

Do not expose raw fingerprint images, copy templates into ordinary filesystem storage, implement a fake `fprintd` backend that returns success, or mark a sysfs driver node as authenticated. Do not disable PIN/password fallback. Biometric disable/revoke must remain effective. Do not log biometric material.

### 11.5 Roadmap and acceptance

Give phases for driver enumeration, trusted provider, enrollment, secure template storage, challenge/response authentication, lockscreen integration, retry/rate-limit/lockout policy and recovery. A physical PASS requires real enrollment and repeated genuine authentication using the protected provider, plus fallback and deletion behavior. If the TEE/TA material is unavailable or non-redistributable, explain the exact legal/technical blocker and the realistic owner-supplied/OEM path.

---

## 12. `./REPORT-MOBILE-NETWORKING.md` — FULL SHANNON LTE / CELLULAR ROADMAP

### 12.1 Device-specific boundary

The S10+ profile identifies an integrated Samsung Shannon LTE modem, Cat 20, no 5G. The current device metadata labels the modem driver `UNKNOWN_NOT_MM_READY`. Historical modem diagnostics say no supported ModemManager Shannon plugin/CP path was available, `mmcli -L` found no modem and cellular data was not claimed. Re-run current diagnostics and inspect all actual CP paths.

### 12.2 Map the complete chain

Trace:

`Shannon modem/CP → shared memory/IPC/CPIF/SIPC transport → kernel modem driver/device nodes → modem firmware and boot handshake → userspace protocol/plugin → ModemManager or supported native cellular daemon → NetworkManager bearer → SIM/operator/registration → data interface/APN/DHCP/DNS → calls/SMS/IMS services`.

Determine the exact protocol from the matching Samsung kernel source and board DT. Do not assume QMI, MBIM, PPP or a standard AT tty. Enumerate candidate `/dev/cbd*`, `/dev/umts*`, `/dev/tty*`, `/dev/wwan*`, `rmnet*` and kernel IPC/shared memory endpoints read-only. Correlate with CP boot logs and service architecture.

### 12.3 Full scope must be separated by capability

Report the exact path/blocker for each:

1. SIM presence and safe removal detection.
2. Modem power/state and firmware readiness.
3. Network scan/operator selection/registration/roaming.
4. LTE data bearer/APN and IP routing.
5. SMS send/receive.
6. Voice call control.
7. IMS/VoLTE and carrier provisioning.
8. Emergency calling — discuss required compliance, but do not make or simulate an emergency call.

Do not conflate SIM insertion, signal icons, Wi-Fi connectivity or an AT response with full cellular service.

### 12.4 Security and privacy hard stops

Never read/write EFS, IMEI identity, NV calibration, modem partitions, carrier provisioning or protected persistent regions. Do not unlock, reflash, dump or alter modem firmware. Do not print IMSI, ICCID, IMEI, PIN, PUK, MSISDN or private APN credentials. Do not execute mutating AT commands or raw APDUs. Keep current diagnostic `--yes-at` restrictions if present; expand only with reviewed, read-only allowlists and owner authorization. Do not test-dial emergency numbers.

### 12.5 Recommended route

Determine whether to implement a narrow Shannon CP protocol driver/provider and a ModemManager plugin, a maintained native daemon integrated with NetworkManager, or a legally isolated vendor runtime. State required kernel CP transport, mailbox/shared-memory interfaces, firmware, plugin API, netdev/bearer mechanism, SIM interface, permissions and user UI. Identify whether the work is realistically feasible with public source or requires Samsung/vendor/OEM-only material. Build a staged plan that gets SIM detection and LTE data before attempting IMS/voice if dependencies allow.

A PASS for data requires a real active SIM, registration from modem API, actual bearer/netdev, valid IP route, DNS and HTTPS. A PASS for calls/SMS/IMS requires their own real tests; do not imply them from data connectivity.

---

## 13. `./REPORT-LEDS.md` — FULL LED/FLASH/COLOR ROADMAP

### 13.1 Distinguish hardware from display effects

The S10+ policy file already distinguishes:

- Rear dual-LED flash/torch (potential warm/cool channels controlled by camera/PMIC LED interfaces).
- A possible physical notification LED class, whose existence and color channels must be enumerated rather than assumed.
- “Edge lighting,” which is a curved-AMOLED display animation/overlay, not a dedicated RGB LED.

Inspect actual board variant, parts, DT nodes, PMIC/flash driver, LED class devices, sysfs attributes, triggers, max brightness, flash strobe/current limits and color channel binding. Check `/sys/class/leds`, `/sys/class/led-class` as applicable, driver names and device tree. Verify exact paths live.

### 13.2 Existing implementation

Review `configs/nuxel/leds/leds.json`, notification/flashlight bridge providers, `nuxel-led-diag.sh`, tests and owner procedure. Preserve safety policy: no torch at boot, explicit user action, bounded ON time, forced OFF on exit/failure, thermal/battery constraints.

### 13.3 Color support investigation

Determine whether there is a real multi-color notification LED, separate red/green/blue channels, a multicolor LED class device, a camera flash-only emitter, or no notification LED at all. Inspect whether the controller supports independent current control, color mixing, brightness, blink and hardware triggers. A sysfs file named `led:rgb` is not proof of RGB capability; physically test each color if a real class exists.

If no dedicated colored indicator exists, the accurate fallback is a display-based edge/notification animation; label it as a display effect and never claim a physical LED. Evaluate whether a software display overlay can safely provide the requested color behavior while screen on/off and lockscreen security remain correct.

### 13.4 Acceptance and risks

Report distinct PASS states for rear torch, notification LED, RGB colors, blink, brightness, thermal timeout, forced OFF and screen overlay. Never use the camera flash as a continuous notification lamp without a supported current/thermal policy. Do not write undocumented PMIC registers or flash arbitrary LED firmware.

---

## 14. CROSS-SUBSYSTEM INTEGRATION AND CONFLICT ANALYSIS

The seven hardware domains share resources. Explicitly map cross-dependencies:

- Camera and flashlight may share LED/PMIC controls, clocks or camera power sequencing.
- GNSS and rotation share Broadcom SSP/BBD/LHD components and firmware/protocol infrastructure.
- NFC shares I2C/power/IRQ and system suspend/wake.
- Fingerprint may share secure world, SPI, display/AMOLED, charger/LPM path and lockscreen authentication.
- Mobile networking and GNSS may share modem/antenna/assistance paths but must not be conflated.
- GPU, camera, video decoder and display bridge share memory bandwidth, IOMMU and dma-buf synchronization.
- Compositor and camera/video playback share frame scheduling, decoder queues, thermal headroom and buffer pressure.
- Systemd boot dependencies should not wait for optional radio/camera/sensor features to become ready.

Do not allow one feature's recovery daemon to reset hardware that another feature owns. Define shared-resource ownership and concurrency locks before proposing implementation.

---

## 15. REPORT QUALITY STANDARD — NO GENERIC “NEED A DRIVER” ANSWERS

Each of the seven hardware reports must include these sections:

1. **Executive verdict:** `WORKING`, `PARTIAL`, `BLOCKED_KERNEL`, `BLOCKED_FIRMWARE`, `BLOCKED_VENDOR_RUNTIME`, `BLOCKED_PROTOCOL`, `BLOCKED_SECURITY_PROVIDER`, `NEEDS_OWNER_TEST`, `NOT_SUPPORTED_ON_DEVICE` or another explicitly defined state.
2. **Target identity:** exact model/codename/SoC/chip/module and confidence level.
3. **What already exists:** source paths, package/build inclusions, kernel config, service units, APIs, tests and UI paths.
4. **Latest evidence:** capture date, boot ID, command, result, evidence file and whether it is repo/static, fixture, host, device-runtime or physical.
5. **Full dependency chain:** stage-by-stage table from silicon to user-visible feature.
6. **First failing stage:** exact node, driver, ioctl, protocol request, firmware file, service, ABI or permission where it stops; include raw error (sanitized).
7. **Why prior attempts have not completed the feature:** cite the exact previous report/code/test and explain any new evidence that changes the conclusion.
8. **Best recommended architecture:** one primary recommendation, at least one fallback, and a reasoned comparison.
9. **Required work inventory:** kernel/DT/driver, firmware/provenance, userspace library/daemon, system service, API/portal, UI/permission, packaging and test tasks.
10. **Source/upstream research:** exact project, repository, commit/version, ABI/driver support, patch status and license. Do not cite an unverified branch name or generic web page as proof of support.
11. **Buildability:** can code be built from public sources in the current toolchain? What hardware/firmware is still needed? Does it require a newer kernel, Android/Bionic, HIDL, TEE/TA or proprietary vendor source?
12. **Risks and constraints:** boot, brick, thermals, privacy, safety, licensing, security, calibration and device recovery risks.
13. **Phased roadmap:** smallest first experiment → minimum viable functionality → robust full feature → advanced capabilities.
14. **Acceptance test matrix:** exact physical, runtime and offline checks required to promote each state.
15. **Owner inputs required:** only concrete proprietary files, physical tag/SIM, outdoor test, recovery access or permission that cannot be supplied by the codebase.
16. **Confidence/gaps:** what is proved, inferred, unknown and not yet testable.

Avoid speculative certainty. Put unverified ideas in an “Hypotheses to test” section and rank them. Distinguish a missing firmware artifact from a missing driver, a firmware loader from a usable protocol, a device node from a functioning device, and UI state from actual hardware state.

---

## 16. IMPLEMENTATION SEQUENCE — SAFE IMPROVEMENTS FIRST

### Phase A — complete audit and baseline

- Read the entire prompt.
- Record repository/device identity and dirty state.
- Read `SYSTEMD-GRAPH.md` if available; generate/update it from real evidence if missing/stale.
- Run current tests/build validations before edits.
- Build ownership maps, service graph and removal ledger.
- Capture baseline compositor and GPU data.
- Produce first-pass hardware chain inventories and confirm contradictions between current manifests, deviceinfo and historical docs.

### Phase B — systemd optimization

- Rank opportunities by impact on measured critical path, risk and reversibility.
- Change one dependency/timeout/startup owner at a time.
- Validate `systemd-analyze verify` for every touched unit and check dependency cycles/missing unit references.
- Verify both first boot and failure fallback. Compare boot ID and actual ready milestone timings.
- Make no removal/disable change unless the protected-service matrix passes.

### Phase C — compositor/frame pipeline optimization

- Identify the highest measured frame/input cost first.
- Optimize single-owner initialization, duplicate work, buffer copies/conversions, damage propagation, blocking calls or event polling only where profiling proves the bottleneck.
- Build/test on the host or isolated device staging area before swapping live binaries.
- Keep the current known-good renderer/panel fallback intact.
- Run touch, keyboard, orientation, display, lockscreen, PWA, Flatpak and external-display regression tests.

### Phase D — obsolete code cleanup

- Process the removal ledger by lowest-risk candidate first.
- Remove source, active references, packaging copies, stale config and generated assets together.
- Rebuild image/package and prove stale artifacts are absent.
- Stop immediately and restore the candidate if any owner contract or test fails.

### Phase E — hardware research reports

- Revalidate current hardware with read-only commands first.
- Run existing bounded diagnostics/selftests; do not add new active probes that reset hardware or disrupt a working device.
- Search exact kernel source/DT, firmware provenance, upstream drivers and protocol implementations.
- Create all seven report files with the quality standard above.
- Do not install or deploy experimental firmware/drivers/TEE applications.

### Phase F — final verification

- Re-run unit/integration tests, rootfs build, package manifest verification, unit validation, app launch checks and service state checks.
- Compare before/after boot/compositor metrics.
- Verify systemd unit set and enabled/active states against expected policy.
- Run the protected feature matrix.
- Confirm all reports exist at repository root and the source cleanup is present in the staged image.

---

## 17. REQUIRED AUTOMATED AND DEVICE TESTS

Adapt test names/commands to the actual current Makefile/CI targets; do not invent targets. At minimum test:

### 17.1 Boot/systemd

- Unit syntax and systemd verification for all changed units.
- No dependency cycles, missing units, accidental critical-path pulls of optional hardware or lost target dependencies.
- Required services start and reach readiness.
- Optional service absent/failing does not block login/launcher unless genuinely required.
- Service restart/stop behavior remains correct and no orphan process remains.
- Boot graph contains real evidence and the correct target/boot ID.
- Shutdown measurements are real or marked not captured.

### 17.2 Compositor/UI

- Visible first frame and lockscreen, unlock, Home/app drawer, Back/Recents, Quick Settings and statusbar.
- Touch accuracy and all orientation policies (manual modes always; Auto only if live sensor works).
- Keyboard/OSK opening, bottom nav interactions, external display and mirroring where supported.
- PWA and Flatpak open/close, fullscreen, video playback and lock/unlock app-state retention.
- No GPU fallback regression or increase in Phoc/presenter crash rate.
- Frame timing/input latency under equivalent load and thermal state.

### 17.3 Protected services and hardware integrations

- SSH connection and reconnect, USB/serial Live Console, VNC/RDP if configured.
- Wi-Fi connection, route, DNS and TLS/browser.
- Audio/speaker/headset and microphone mute/permission where available.
- NFC OFF default and bounded scan behavior.
- Flashlight remains OFF by default and timeout still forces it OFF.
- Fingerprint remains fail-closed with PIN fallback.
- Camera privacy/permission remains fail-closed and no fake camera frame.
- Mobile network diagnostics redact all subscriber identifiers and never claim a nonexistent bearer.
- Battery/charger mode and thermal monitoring remain active.

### 17.4 Source cleanup

- Old service/code no longer present in active source/build/deployment output when marked removed.
- Replacement feature remains installed and reachable.
- No references to removed binary paths remain except explicitly preserved historical documentation.
- CI, release image and supported secondary device builds are still valid.

For every test label exactly one: `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_HOST`, `PASS_FIXTURE`, `BLOCKED_HARDWARE`, `NOT_TESTED`, `FAILED` or `ROLLED_BACK`. Never promote an offline test to physical PASS.

---

## 18. FINAL DELIVERABLES

At completion, the repository must contain:

- `SYSTEMD-GRAPH.md`
- `GPU-ACCEL-REPORT.md`
- `REPORT-CAMERA.md`
- `REPORT-GPS.md`
- `REPORT-NFC.md`
- `REPORT-ROTATION.md`
- `REPORT-FINGERPRINT.md`
- `REPORT-MOBILE-NETWORKING.md`
- `REPORT-LEDS.md`
- `diagnostics/pwnage-91000/` with sanitized before/after evidence, test logs, service inventory, ownership/removal ledger, timing captures and benchmark data.
- `diagnostics/systemd/` with SVG graphs and raw evidence supporting `SYSTEMD-GRAPH.md`.
- Updated relevant code/tests/package manifests/build scripts/docs for only the safe changes actually implemented.
- `PWNAGE-91000-REPORT.md` final execution report.

### Final report contents

1. Overall verdict: `FULLY_DONE`, `PARTIAL`, `BLOCKED` or `ROLLED_BACK`.
2. Repository state, commit/branch if available, device identity and running kernel/systemd versions.
3. Boot before/after table with actual measurements, capture boot IDs and the critical-path changes.
4. Shutdown before/after table based on captured evidence; otherwise `NOT_CAPTURED`.
5. Service changes: added/removed/modified/retained, why, dependency tests and runtime state.
6. Compositor/GPU before/after performance metrics and which layer is still CPU-bound/software.
7. Cleanup ledger: exactly what source/config/package artifacts were removed, plus proof that removed code is no longer shipped.
8. One row for each of the seven hardware reports with verdict, first blocker, recommended path, confidence and owner dependency.
9. Full test matrix with exact counts and test labels.
10. Known regressions, limitations, untested physical paths and remaining risks.
11. Rollback instructions for every R2 change, exact backup paths and how to restore the previously working session.

---

## 19. HARD ACCEPTANCE GATES

Do not use `FULLY_DONE` unless all applicable gates pass:

- [ ] The real current codebase, installed system and build pipeline were deeply mapped; no critical path is assumed from old docs alone.
- [ ] `SYSTEMD-GRAPH.md` reflects the current device/units and contains actual boot evidence; shutdown is evidenced or explicitly `NOT_CAPTURED`.
- [ ] Boot/shutdown changes materially improve a measured bottleneck or are deliberately left unchanged where no safe opportunity is proven.
- [ ] No required service was broken, hidden, masked, removed or made unreliable.
- [ ] Compositor changes have reproducible performance evidence and all protected UI/input/display features pass.
- [ ] Duplicate owners and start-then-stop service patterns have been corrected at their source where proven.
- [ ] Obsolete code that was approved for removal is actually removed from active code and image/package output; no new cleanup workaround substitutes for deletion.
- [ ] Existing fallback and recovery routes still work.
- [ ] All seven hardware reports exist and contain exact, source-backed dependency chains, latest evidence, first blocker and a realistic end-state roadmap.
- [ ] No driver, firmware, TEE or protected partition work was falsely represented as completed.
- [ ] All automated tests/builds relevant to touched code pass; device-only gaps are explicitly stated.
- [ ] Rollback is documented and viable.

If something is blocked by lack of a connected handset, missing owner-supplied firmware, licensing, TEE credentials, physical SIM/tag, outdoor GNSS conditions or lack of a safe recovery route, complete every offline analysis/report deliverable and label that part accurately. Do not stop the entire mission because one hardware test is unavailable.

## 20. FINAL DIRECTIVE

Start now. Read this complete prompt, inspect the actual repository and target, and execute the work in the order above. Do not respond with a plan only. Do not invent evidence. Do not break a service to shave seconds off a graph. Do not leave rejected code in the packaged image and call it removed. Do not call any hardware subsystem working until its real physical capability has been demonstrated. Deliver the safe optimizations, all eight reports plus the systemd graph, exact evidence, test results and rollback steps.
