# 🐧⚡ NUXEL A75 / 24000 — OPERATION SMOOTH PENGUIN: PERFORMANCE + MOTION + USB + NETWORK/RADIO RESTORATION

## MAKE EVERY INTERACTION FEEL ALIVE. RESTORE WI-FI / BLUETOOTH / LOCATION. UNPLUG USB WITHOUT PANIC.

**Target device:** Samsung Galaxy S10+ **SM-G975F / `beyond2lte` / Exynos 9820**, running the existing Fedora-based ARM64 Nuxel userspace, Phoc/Wayland/WebKitGTK/PWA shell and known-good downstream Linux 4.14 kernel. Confirm the live reality; these labels are expected target context, not proof of the current runtime.

**Mission:** A measured, reversible performance-and-motion pass across the currently deployed Nuxel experience, a definitive repair for the USB-disconnect defect, and restoration of the currently broken Wi-Fi / Bluetooth / Location Quick Settings path. The owner reports that Wi-Fi now fails with the same or similar D-Bus “no service provider provides Nuxel bridge” error as Bluetooth and GPS/Location, and Bluetooth and Location still cannot be turned on. Treat that wording as an approximate symptom until the exact runtime error is captured. Repair the shared bridge/provider path if evidence confirms it, then verify each real backend independently. After computer USB disconnect, PC and Live Console icons must clear and the phone must not hang or reboot.

**Personality:** Keep Nuxel's distinctive custom penguin / wonky identity. The UI should feel playful, tactile, intentional and polished—not like a pile of generic transitions. Motion should communicate state, not obstruct work. Performance means low touch-to-visible-feedback latency, stable frame pacing, quick app transitions, reliable input and safe idle behavior—not merely a high FPS number in a config file.

**Execution order:** inventory → safe recovery and exact deployed-state capture → baseline → USB detach root-cause capture → D-Bus bridge/provider and Wi-Fi/Bluetooth/Location root-cause capture → restore real network/radio operations → motion audit → measure critical path → small reversible optimizations → asset optimization where justified → automated tests → staged deploy → physical acceptance → before/after report.

**Recommended agent:** strongest coding/reasoning agent available (GPT-5.6 Sol High / DeepSeek V4 Pro Thinking or equivalent). A capable Flash model may do an initial inventory, but do not let it guess at kernel/USB races or claim physical verification without evidence.

---

# 0. OWNER'S EXACT REQUIREMENTS — NON-NEGOTIABLE CONTRACT

The owner asks for the whole phone to feel smoother and more responsive, for all meaningful movements to be animated, and for all three lockscreen status penguins to animate: charging, PC connected, and Live Console active. The owner reports that the indicators otherwise activate correctly for their respective events, but after the computer USB cable is disconnected the PC and Live Console icons stay visible; earlier unplug attempts also caused a hang and reboot. Treat the stale icons and detach crash as linked symptoms to investigate, but do not assume one bug necessarily causes the other.

## 0.1 Final behavior

1. **Every meaningful UI transition has intentional motion**: press/active feedback, app open/close, home/desktop movement, app drawer, Quick Settings, popovers/modals, lock/unlock, navigation, tab/task switching, loading/empty/error states and indicator state transitions. Avoid animating every pixel of continuous scrolling or adding delay where direct manipulation should remain immediate.
2. Motion is coherent: consistent durations, easing, direction, interruption behavior and layering. Transitions must be interruptible and must not trap touch input or leave surfaces in a half-open state.
3. The charging, PC-connected and Live Console penguins each have a distinct, lightweight, state-appropriate animation. Their existing correct position, size, transparency, artwork, spacing, visibility rules and identity must be preserved unless a measured, documented correction is essential.
4. **USB state is truthful and independent:** charging/power state is not the same thing as USB host/data connectivity; a USB gadget being configured/addressed, a console daemon existing, or `ttyGS0` existing is not proof that a computer is currently connected.
5. On physical computer disconnect, the PC-connected icon goes OFF and the Live Console icon goes OFF promptly when the host transport/session is no longer actually connected/usable. This transition must be idempotent, race-safe and reflected in backend state and UI state—not just hidden with CSS.
6. Charging remains on only according to the existing authoritative power/charging semantics. Disconnecting the PC data cable should not falsify charging state; a wall charger should not light the PC icon; the icon logic must not conflate charging with a live data link.
7. **Unplugging must never hang or reboot Nuxel.** No kernel panic, watchdog reset, service cascade, compositor freeze, systemd restart storm or userspace-initiated reboot as a normal result of USB detach.
8. Preserve the known-good launcher, lockscreen/lockhead, Home/Back/Recents, SnekByte, app lifecycle, battery, keyboard, and any already-working functions. **Wi-Fi is currently reported broken; Bluetooth and Location/GPS toggles are also reported unable to turn on. Restore these explicitly instead of treating them as working or merely preserving the broken behavior.** Preserve DNS/TLS/browser behavior as a regression target and avoid replacing the installed network stack without evidence.
9. Make performance gains with evidence. Optimize bottlenecks that measurements identify; do not blindly lower quality, remove visual identity, or claim GPU acceleration when the live stack is software rendered.
10. Keep the current working Linux 4.14 kernel, boot chain, bootloader, partitions and recovery arrangement. This mission is **userspace/UI/asset/service-level** unless investigation proves otherwise and the owner explicitly authorizes a separate hardware/kernel project. No flashing as part of this mission.

## 0.2 Done means

- Same boot ID before and after physical unplug; uptime continues; the UI and system remain responsive.
- PC and Live Console icons turn off correctly after real host disconnect, and reappear on the correct subsequent connection/session.
- Charging icon follows its actual power state independently.
- Wi-Fi Quick Settings no longer fails with the reported D-Bus/provider error; actual scanning, connection, IP configuration, DNS and TLS work using the existing supported stack.
- Bluetooth and Location toggles invoke real backend operations through a correctly registered bridge/provider; each reports truthful hardware/service limitations instead of a generic missing-provider error.
- All important transitions have visible, polished motion without stutter, delayed controls, animation lockups, high idle CPU or overheating.
- Before/after measurements, test output, deployed file hashes, rollback steps and honest hardware test statuses are delivered.

A source diff, mocked test, or a successful reboot after the incident is **not** proof that the physical unplug defect is fixed.

---

# 1. SAFETY FIRST — PROTECT THE PHONE AND ITS WORKING FEATURES

1. Identify the actual checkout, branch, commit, dirty changes, current deploy mechanism, running Nuxel version, device identity and active session. Compare repo files to deployed files and running executables. Do not assume the repository matches the phone.
2. Inspect the latest A74 / 23000 USB-unplug fix attempt and its deployed state first. The accompanying `REFERENCE-A74-USB-UNPLUG-PWNAGE-23000.md` is historical context, not truth about the current state. Keep any valid improvements and do not overwrite them with an older ZIP.
3. Establish a recovery route **other than the USB cable being tested**, if possible (verified Wi-Fi/SSH, another serial/console route, or owner-controlled recovery). Do not physically unplug the only access path until a safe evidence/recovery plan is agreed. If no independent path exists, complete offline diagnostics and request the owner's supervised unplug test rather than pretending it was performed.
4. Capture current `git status`, branch/HEAD, changed files, SHA-256 hashes of important deployed files/binaries, current boot ID, uptime, kernel release, process/service state, indicator endpoint/state and USB/gadget/console state. Make narrow backups and a rollback script before deployment.
5. Never run `reboot`, `poweroff`, or equivalent as a USB detach response or as a service retry strategy. Never mask the defect by leaving stale icons visible, suppressing disconnect events, permanently binding the gadget, disabling Live Console without permission, or hiding the actual state.
6. Do not disable watchdogs, thermal protections, panic evidence, journaling, SELinux/AppArmor, or power management to improve a benchmark. Do not set a permanent max CPU frequency or force unsupported graphics modes.
7. No concurrent agents should deploy to the same physical phone. Do not restart the only recovery/access service while relying on it. Restart only the smallest relevant service and only after the rollback route is ready. Network service restarts can sever SSH/remote access; preserve a second recovery route and warn the owner before any operation likely to drop the current link.
8. Do not mass-upgrade packages, replace the kernel, flash boot/system partitions, alter the bootloader, or perform risky display-driver experiments. The target's legacy kernel and software presentation pipeline may constrain performance; document those constraints rather than breaking boot.
9. Preserve privacy in diagnostics: do not dump credentials, tokens, Wi-Fi secrets, private user files or arbitrary console contents. Use bounded logs and rotate them.
10. If any change makes the display blank, unlock broken, touch misaligned, console inaccessible or device hotter at idle, roll back the smallest change immediately. Do not leave a broken test build on the phone to collect more numbers.

---

# 2. RECONNAISSANCE — CURRENT REPO AND DEVICE ARE THE SOURCE OF TRUTH

Before edits, inspect the current tree and runtime. Use search tools to discover actual files; these paths are leads from earlier work, not guaranteed current paths:

- `pwa/nuxel-home/` and its current JS/CSS/HTML/assets
- `pwa/nuxel-home/js/launcher.js`, `app.js`, `qs.js` and other current UI controllers
- lockscreen/lockhead code and CSS; battery/indicator rendering components
- `services/nuxel-bridge/src/system_indicators.py`
- `services/nuxel-bridge/` service/unit/API and any indicator cache or polling loop
- all current Nuxel D-Bus bridge/provider registration, object/interface definitions, activation descriptors, systemd units, policy files and frontend call sites for Wi-Fi, Bluetooth and Location/GPS
- `services/nuxel-console/`, USB gadget setup, systemd units/drop-ins, udev rules and host/session monitoring
- any `nuxel-wl-fb` / framebuffer bridge / Phoc configuration / display presentation code that is actually deployed
- image assets under `assets/`, PWA assets and generated/copied installation assets
- build, packaging, install, deployment and rollback scripts
- tests for indicators, USB, lockscreen, navigation, animations, asset manifests and performance.

Run `git status --short`, inspect diffs and search the entire repo for:

- USB attach/detach, UDC/gadget bind/unbind, `ttyGS0`, Type-C/data-role, host/session state, uevents/netlink, sysfs power-supply state, console leases and stale PID files;
- `systemctl reboot`, `reboot`, `poweroff`, `Restart=`, `OnFailure=`, watchdogs, stop/restart scripts and teardown callbacks;
- icon state cache, API polling, WebSocket/SSE/event updates, stale frontend state, event listeners that are never removed, timers that continue after detach;
- CSS `transition`, `animation`, `@keyframes`, transform/opacity, `filter`, `backdrop-filter`, box shadows, `will-change`, forced layout reads (`offsetWidth`, `getBoundingClientRect`), large DOM updates, synchronous loops and long-running event handlers;
- images larger than their rendered dimensions, duplicate assets, high-resolution PNGs, GIFs, unnecessary base64, unused fonts, large JS/CSS and repeated decoding.

Create a concise inventory table:

`behavior | source path | deployed path | runtime owner | state source | current measured cost | proposed fix | test | rollback`.

Do not perform blind repository-wide rewrites. First identify the actual critical path and the exact files used by the live phone.

---

# 3. USB DETACH: REPAIR STATE TRUTH AND STABILITY BEFORE COSMETIC POLISH

Treat this as a P0 reliability issue. Capture evidence before changing logic. The previous A74 mission provides a detailed investigation approach; re-use it and extend it as needed.

## 3.1 Capture one controlled failure safely

If the failure can be reproduced with an independent recovery path, collect durable, bounded evidence on the phone before/during/after the event. Do not rely only on a USB stream that disappears at the moment of failure.

Record:

- `/proc/sys/kernel/random/boot_id`, uptime, kernel release, timestamp and battery/power state before and after;
- kernel journal/dmesg tail, watchdog/OOM/coredump evidence, reboot reason and `/sys/fs/pstore`/ramoops if present; inspect after reboot before cleanup;
- console daemon PID, cgroup, open TTY/file descriptors, exit status, service restart counters, recent systemd journal and any disconnect-triggered jobs;
- UDC/gadget binding, USB controller state, Type-C/data role if available, power-supply state, actual host/session state and `ttyGS0` availability;
- current backend indicator payload/API response and frontend indicator classes/state;
- timestamped detach event, service state transitions and whether Wi-Fi remains reachable during the alleged hang.

Determine whether the failure is a kernel panic/oops, watchdog stall, userspace reboot request, console I/O teardown race, service dependency/restart cascade, compositor/UI-only hang, power/PMIC issue or another evidenced class. Do not assert a root cause from a plausible story alone.

## 3.2 Required state model: never collapse three different truths

Implement or repair a clear state model using the current architecture:

- `power_present` / charging state: from the authoritative power-supply interface already used by Nuxel. Keep current correct behavior.
- `usb_host_connected` / PC data connection: from the strongest actual detach-capable signal the installed stack exposes. A configured gadget, bound UDC, controller `addressed` state, existing daemon or present `ttyGS0` alone is not enough to prove the host is still present.
- `console_transport_active` / Live Console: true only while the relevant console transport/session is actually open and usable according to the project's real semantics. A daemon being installed/running or a stale lease does not by itself prove the physical host remains connected.

Do not assume a particular sysfs path or USB gadget implementation. Inspect the current kernel, sysfs, configfs, udev/uevent and daemon behavior on the actual device. If no single authoritative event exists, use a small state machine that combines available evidence, with explicit stale-state expiration and safe transitions. Explain the evidence and limitations.

Suggested states (adapt to actual APIs):

`DISCONNECTED` → `HOST_CONNECTED` → `CONSOLE_ACTIVE`; on detach → `DETACHING` → close the transport/session idempotently → `DISCONNECTED`. Charging/power state is tracked on a separate axis and must not be forced OFF just because the host data link disappeared if external power remains present.

## 3.3 Detach event requirements

- Handle disconnect once or multiple times safely; duplicate uevents/callbacks must be harmless.
- Close/flush/cancel console transport operations without blocking the event loop indefinitely.
- Handle EOF, HUP, POLLERR, EIO, ENODEV, EPIPE, ECONNRESET, missing sysfs attributes, stale PID/lease and service exit without treating an ordinary disconnect as a fatal OS failure.
- Bound waits and retries. No busy-spin, unbounded retry, repeated systemd restarts or reboot fallback.
- Do not run slow synchronous filesystem writes or service orchestration inside a critical callback. Queue bounded cleanup work and return promptly.
- Clear backend PC and Live Console state immediately after authoritative disconnect confirmation, then publish the updated state through the real bridge/API/event mechanism. Frontend must consume it and remove `active`/visible state rather than retaining old cached values.
- Use event-driven state updates where feasible; if polling is necessary, choose a bounded sensible interval, handle missing data, and avoid multiplying timers across app reopen/reconnect cycles.
- Keep console daemon lifecycle separate from host session lifecycle if the architecture requires it. Do not kill a healthy daemon just to hide an icon; do not leave a false active session either.
- Log concise, rate-limited transitions (`USB_HOST_CONNECTED`, `USB_HOST_DETACHED`, `CONSOLE_TRANSPORT_CLOSED`, `INDICATOR_STATE_PUBLISHED`, `DETACH_CLEANUP_FAILED`) with timestamps and reasons, but never console payloads or secrets.
- If the original reboot cause remains unproven, clearly label it unresolved and do not claim complete physical stability. Add the best safe instrumentation, test the evidenced portions, and request the owner for a controlled hardware test.

## 3.4 Required indicator acceptance matrix

| Physical condition | Charging penguin | PC-connected penguin | Live Console penguin |
|---|---|---|---|
| Phone on battery, no computer | OFF unless existing power semantics truly say charging | OFF | OFF |
| Wall charger / power-only supply, no data host | Correct actual charging state | OFF | OFF |
| Computer cable connected, host/data link established | Reflect actual charging state, not cable assumption | ON | OFF until the real console session is active |
| Computer connected + Live Console transport actually active | Reflect actual charging state | ON | ON |
| Computer physically disconnected, phone remains on battery | OFF if no charging source remains | **OFF promptly** | **OFF promptly** |
| Computer data disconnect while a separate external power source remains | Reflect actual independent power state | **OFF promptly** | **OFF promptly** |
| Reconnect computer after prior clean detach | Correct current charging state | ON only after confirmed host connection | ON only when console session becomes genuinely active |
| Console daemon exists but no computer host is present | Independent charging state | OFF | OFF |

The frontend may animate a short exit (e.g. fade/scale of roughly 120–220 ms), but the semantic state must switch to OFF immediately. An exit animation is not permission to leave a stale active state in the backend, accessibility tree, hit testing or future re-render. Avoid long grace periods that make the icons appear stuck.

## 3.5 Regression tests for detach and reconnect

Add realistic tests, using the project's conventions, for:

- detach while console is idle, reading, writing, blocked, and shutting down;
- duplicate detach, detach+attach races, rapid reconnect and concurrent callbacks;
- EOF/HUP/POLLERR/EIO/ENODEV/EPIPE/ECONNRESET and missing device nodes/sysfs attributes;
- stale leases/PID files, PID reuse safety, zombie cleanup and service restart limits;
- charging-only versus data-connected states; host connected but console not active; daemon present but host absent;
- backend state changes actually reach the UI; stale cached state is invalidated;
- no reboot/poweroff call occurs on normal disconnect;
- repeated detach/reconnect does not increase service restart counters without reason, memory use or active timers;
- charging icon and all three icon animations/positions remain correct.

At least one acceptance check must compare boot ID and uptime before/after a physical unplug. A unit test cannot substitute for it.

---

# 3.6 P0 NETWORK + RADIO RESTORATION — FIX THE SHARED D-BUS / NUXEL-BRIDGE FAILURE

The owner reports a new critical regression: **Wi-Fi is broken too**. Its Quick Settings action returns the same or similar D-Bus error that Bluetooth and GPS/Location show, approximately “no service provider provides Nuxel bridge.” The exact wording is uncertain and must be captured from the running system. Bluetooth and Location still cannot be enabled. Do not guess that this is a Wi-Fi radio failure or fix three UI buttons separately before checking whether they all depend on a missing or misregistered bridge/provider.

Treat this as a P0 service/API integration issue. It may be a missing D-Bus owner, wrong bus (system vs session), wrong service/interface/object path, stale frontend/backend version mismatch, absent activation descriptor, failed Python import/venv, systemd dependency/order failure, permission/policy denial, or a genuinely unavailable device/backend. Prove which case applies before editing.

## 3.6.1 Capture the exact error and current architecture first

1. Reproduce one failed Wi-Fi toggle safely and capture the exact UI message, timestamp, D-Bus error name/message, called method, destination service name, object path, interface, and whether the request reaches the bridge. Repeat separately for Bluetooth and Location. Redact SSIDs, passwords, tokens and location history.
2. Inspect the current deployed frontend call sites and bridge implementation. Search all current files for “Nuxel bridge”, “service provider”, D-Bus service names, object paths, interface names, method names, Quick Settings handlers, and Wi-Fi/Bluetooth/location provider dispatch. Treat the user's quoted error as approximate, not a literal guaranteed string.
3. Compare repository files with the actual deployed files, service unit, D-Bus activation descriptor, Python environment/module imports and running process command line. Check for version skew where the UI expects an API that the deployed bridge does not export, or the bridge exports an interface under a different name.
4. Inspect both system and session bus intentionally. Use the installed tooling available on the phone (for example `busctl`, `gdbus`, `dbus-send`, `systemctl`, journal queries, and the project's own diagnostics) to identify bus ownership, service activation, object introspection, method signatures and permission failures. Do not assume every tool is installed; do not install a second daemon just to get a diagnostic command.
5. Inspect the actual service unit and activation wiring: `BusName=`, `Type=dbus`, `ExecStart`, `Environment`, working directory, Python interpreter/venv, import path, `DBusActivatable`/service descriptor where used, dependencies, ordering, restart policy, timeout, user/group, policy files and ownership. Confirm that the declared bus name exactly matches the name acquired by the live process and the destination used by the UI.
6. Check service logs from boot and from the exact toggle attempt: import errors, name-acquisition failures, unknown object/interface/method, timeout/no reply, access denied, service activation failure, missing dependency, method signature mismatch, and unexpected process exit. Distinguish these error classes rather than replacing them all with a generic message.
7. Inspect the service/provider lifecycle and readiness contract. A process being `active` is not enough if it never acquired its bus name or does not export the required objects. A successful ping is not enough if the actual method is missing.
8. Save current service files, configuration and network state before edits. Never print saved Wi-Fi passwords or dump secrets. Avoid `nmcli connection show --show-secrets` or equivalent secret-revealing commands.

## 3.6.2 Repair the actual provider contract — no fake buttons

- Choose the provider and bus model already used by the current repository and installed system. Do not invent a new bus name, interface or object path. Make the frontend, bridge implementation, D-Bus activation/service configuration and service unit agree exactly.
- If a shared Nuxel bridge is meant to expose Wi-Fi, Bluetooth and Location methods, ensure it actually acquires its expected name, exports the expected object/interface, registers every intended method with correct signatures, starts reliably, and returns structured errors. If the project deliberately uses separate providers, repair each actual provider rather than forcing a fake shared provider.
- Fix the true cause: incorrect D-Bus destination; mismatched service name; missing activation descriptor; wrong system/session bus; broken unit ordering; bad executable/venv/import path; service exits before name acquisition; policy permissions; stale client cache; method/object mismatch; or an absent backend. Only change the cause that the evidence supports.
- Add a readiness check that verifies the expected bus name and required object/interface/methods are present, not just that the unit process exists. Make it bounded and non-blocking for the UI. Surface an actionable, accurate error if a real backend is missing.
- Ensure UI calls have finite timeouts and cannot block the main thread indefinitely. The UI must not claim “enabled” until the backend confirms its actual state. On error, restore the switch to the real reported state and show a useful diagnostic without hiding the underlying failure.
- Ensure bridge restart/disconnect/reconnect does not leave stale proxy objects or cached “provider missing” state. Reconnect to the service safely and refresh provider introspection/state. Avoid tight retry loops and service restart storms.
- Add structured, rate-limited logs for request, provider resolution, backend call, response and failure class. Never log Wi-Fi credentials, arbitrary console data, private location history or tokens.

## 3.6.3 Restore Wi-Fi using the existing supported stack

1. Identify the actual installed Wi-Fi manager/backend from the running device, not from assumptions: NetworkManager, wpa_supplicant, iwd, a project-specific daemon, or another evidenced implementation. Determine which service owns the radio and which API the bridge should call.
2. Inspect whether the adapter exists and is enabled; check rfkill/soft block, driver/module state, firmware load status, interface presence, supplicant/manager state, D-Bus ownership and scan/connect method availability. Read relevant logs. Do not assume a D-Bus provider error means the kernel driver is broken, and do not assume a visible interface proves the bridge works.
3. Fix Quick Settings scan/enable/disable/connect/disconnect through the existing backend. Preserve saved connections and permissions. Do not delete profiles, wipe credentials, reset all networking, install a competing network manager, or replace working config unless the evidence proves it necessary and a rollback exists.
4. Verify actual scan results, connect to an owner-approved known network without printing credentials, obtain an address/route, resolve DNS, complete HTTPS/TLS, and load the existing browser. Verify that a failed connection is reported accurately and does not wedge the UI.
5. Ensure the toggle reflects the actual radio/manager state after service restart, screen lock/unlock, app reopen and a second toggle. The UI must not optimistically remain ON after the backend rejects the operation.
6. If Wi-Fi was working before this regression, compare current deployed bridge/unit/config with the last known-good version and isolate the regression. Prefer a narrow rollback of the offending change over a full stack replacement.

## 3.6.4 Bluetooth — actual controller, service and state

- Trace Quick Settings request through the actual bridge to the installed Bluetooth service and adapter API. Inspect whether BlueZ/`bluetoothd` or the project's supported alternative exists and owns the adapter; verify D-Bus registration, adapter object, controller enumeration, rfkill block, firmware/driver state, permissions and service readiness.
- If the adapter is soft-blocked, unblock it only after confirming that this is the intended user toggle and safe. Do not bypass hardware/airplane-mode policy. If BlueZ is absent, establish whether it is intended and available for the actual Fedora ARM64 userspace before installing it; no blind package installs or internet assumptions.
- Toggle must invoke a real backend action and then read back controller `Powered`/equivalent state. Report “hardware/driver/firmware unavailable” separately from “bridge/provider unavailable” and “permission denied.” Do not animate a successful ON state when the controller did not turn on.
- Test enable, disable, repeated toggles, service restart and state refresh. If the physical controller cannot be enabled because a driver/firmware/kernel facility is missing, document the exact evidence and mark hardware support blocked rather than faking a pass.

## 3.6.5 Location / GPS — separate location policy from GNSS fix

- Determine what the existing Location tile is designed to control: a location-service/provider enable flag, privacy permission, geolocation service, GNSS receiver, or a combination. Inspect actual code and runtime. Do not equate “Location enabled” with “GPS fix acquired.”
- Trace the action through the real D-Bus/bridge/provider and identify the intended service, object/interface/method and readiness requirements. Fix provider resolution if shared with the Wi-Fi/BT failure; then separately check location backend availability, permission/policy, device node, driver/firmware, GNSS daemon/provider and service logs as applicable.
- Do not invent a GPS device, fabricate coordinates, or report a fix without real GNSS/provider evidence. A location privacy/service toggle may legitimately turn ON even when no satellite fix exists; show fix status separately if the UI supports it.
- If GNSS is not supported by the current hardware/kernel/userspace, the tile must state the exact supported limitation and remain truthful. Do not mark the entire bridge/provider repaired merely because a UI switch changes color.
- Test enable/disable and persistence/readback. Test a real fix only if the device has a supported receiver/provider and test conditions allow it; otherwise label the fix test `BLOCKED_HARDWARE` or `NOT_TESTED`.

## 3.6.6 Network/radio regression matrix

| ID | Test | Required result |
|---|---|---|
| N1 | Query bridge readiness after boot | Correct expected bus name, object, interface and methods are present; no false ready state |
| N2 | Invoke Wi-Fi toggle once | No generic “no service provider provides Nuxel bridge” error; real backend request and readback occur |
| N3 | Scan for networks | Real scan result or precise backend error; UI remains responsive |
| N4 | Connect to an owner-approved saved/known network | Connection succeeds without exposing credentials; IP/route state is valid |
| N5 | DNS, HTTPS/TLS and browser smoke test | Name resolution and secure web access work after changes |
| N6 | Disable/enable Wi-Fi and repeat | Actual state matches UI; no stale provider cache, hang or restart storm |
| N7 | Toggle Bluetooth ON/OFF | Real adapter state read back; accurate distinction between provider failure and unsupported hardware |
| N8 | Toggle Location ON/OFF | Real location-service/policy state read back; no fabricated GNSS fix |
| N9 | Restart/reconnect bridge under safe conditions | Provider becomes ready; clients recover; no endless retries or stale state |
| N10 | Trigger a missing-backend/error case in tests | UI gives truthful actionable error and remains responsive |
| N11 | Lock/unlock, reopen Quick Settings and use other apps | Network/radio controls remain correct; no regression to navigation or animation |
| N12 | Run Wi-Fi/BT/Location tests alongside USB state tests | No coupling that falsely changes charging/PC/console indicator state |

## 3.6.7 Required network/radio deliverables

Create `docs/performance/A75/` or follow the existing repository convention and include:

- `02B-DBUS-BRIDGE-PROVIDER-ROOT-CAUSE.md`: exact observed error, bus type, destination name, owner, object path/interface/method, unit/activation wiring, root cause and proof.
- `02C-WIFI-RESTORATION.md`: backend found, state before/after, scan/connect/IP/DNS/TLS/browser evidence, safe config changes and rollback.
- `02D-BLUETOOTH-LOCATION-STATUS.md`: actual controller/provider/services, enable/readback results, firmware/driver/hardware blockers and truthful support status.
- Tests covering D-Bus service unavailable, unknown name/object/interface/method, activation failure, permission denial, timeout, provider restart and stale frontend proxy/cache.

No UI-only workaround qualifies. If the bridge is genuinely absent, implement or repair the intended provider with correct project conventions and deployment wiring. If the provider is present but the device backend is absent, fix the provider contract and report the separate hardware limitation honestly.

---

# 4. BASELINE FIRST — MEASURE RESPONSIVENESS, FRAME PACING, CPU AND MEMORY

Create a dedicated mission evidence folder, preferably `docs/performance/A75/` (adapt to repo conventions). Do not assume older A50 measurements describe today's build. Include timestamp, device identity, commit, deployed hashes, renderer/backend, actual output sizes, battery/charging state, brightness, orientation, network state and thermal starting conditions.

Collect an unchanged baseline before optimization:

### 4.1 Interaction scenarios

Use repeated, comparable actions (ideally 10 repetitions where practical); report median and p95, not only best-case times.

- lockscreen wake and lockhead drag/unlock;
- tap response: physical touch → first visible pressed feedback;
- Home / Back / Recents button feedback and completed action;
- desktop swipe left/right, app drawer open/close and app-grid scroll;
- Quick Settings open/close and toggle interaction;
- app open cold/warm, return Home, switch app, close/minimize app;
- keyboard show/hide, typing response and focus changes;
- dialog/modal/popup open and dismiss;
- indicator activation and USB-detach-to-icons-off latency;
- repeated animation/gesture interruptions (start a transition then reverse or tap another control);
- normal multi-minute use and locked screen-off idle.

### 4.2 Rendering and process metrics

Measure what is actually available; mark unavailable metrics as `UNAVAILABLE`, never invent zero values.

- actual frame rate and frame interval distribution; dropped/duplicate/long frames; distinguish compositor FPS from the physical panel and from the framebuffer bridge;
- CPU per-process and total, event-loop stalls, memory/RSS/PSS if available, WebKit process count, memory pressure, swap, I/O waits, service restart counts;
- frame stages if a bridge exists: capture, buffer conversion/upscale, copy/blit, framebuffer commit and sleep/wait separately;
- screen logical size, compositor/headless size, framebuffer size, pixel format, stride and refresh modes as actually configured;
- CSS/JS performance traces: long tasks, style/layout/paint, image decode, repeated layout, event listener duplication, DOM size and animation frame cost;
- thermal/battery trend, screen-off CPU activity and wake responsiveness;
- indicator detach timing: physical/host event → backend state change → API/event publish → frontend state → icon invisible.

If the installed stack is the historical Phoc/Pixman/headless + software framebuffer bridge, inspect the full pipeline. Old evidence cited roughly 23–28 FPS and 34–43 ms blit time on a previous build, but **do not assume these numbers remain current**. Do not change output dimensions until actual active modes and costs are verified.

Deliver `A75-BASELINE.md`, machine-readable `A75-BASELINE.json`/CSV where feasible, and raw traces/logs that contain no secrets.

---

# 5. MOTION SYSTEM — ANIMATE ALL MEANINGFUL MOVEMENTS WITHOUT MAKING IT SLOW

Audit the full UI and define a consistent motion system rather than sprinkling random animations everywhere. Keep Nuxel's existing visual language and artwork. Motion should confirm touch immediately, communicate spatial relationships and make transitions feel alive, but never delay input or reduce legibility.

## 5.1 Motion tokens and timing rules

Create or reuse shared CSS variables / JS constants in the current theme, e.g.:

- very short feedback: about **70–120 ms**;
- small state transition: about **120–180 ms**;
- standard panel/card/modal transition: about **160–240 ms**;
- larger desktop/app transition: about **180–280 ms**, only if measurements and the interaction feel support it;
- spring/bounce accent: subtle and brief; no prolonged elastic overshoot that makes a phone feel sluggish.

These are starting ranges, not arbitrary requirements. Match the existing design and measure. Use a small coherent easing set (quick-out for feedback, smooth standard ease for panel movement, restrained spring-like effect only for playful accents). Avoid giant stagger chains and anything that blocks a second input until the first animation finishes.

Use CSS custom properties such as `--motion-fast`, `--motion-state`, `--motion-panel`, `--ease-out`, `--ease-standard`, if compatible with the current style system. Document the tokens in one place. Do not scatter slightly different timings across dozens of selectors.

## 5.2 Movement audit — all of these must have deliberate behavior

Inspect and implement the right motion for every surface that exists in the current build. Do not add features that do not exist merely to check a box.

1. **Tap/press feedback:** buttons, dock icons, app icons, tiles, Quick Settings switches, menu rows and keyboard keys. Provide immediate pressed/active feedback (small scale, opacity, tint or existing tactile response) within the first visual frame where possible. Release must restore state smoothly even if the pointer exits.
2. **Navigation strip:** Back, penguin Home and Tabs/Recents buttons. Give press feedback and animate resulting navigation consistently. Preserve current semantics, hit targets and lockscreen hiding rules. Never delay the action until the animation ends.
3. **Desktop/home:** left/right desktop movement, desktop indicator/page state, home restoration, app minimize/foreground transitions, dock reveal/hide, app drawer open/close and icon-grid transitions. Keep gesture tracking direct and responsive; animate settling after gesture release, not a lagging proxy.
4. **App lifecycle:** opening, minimizing, restoring, switching, closing and loading. Avoid fake app-window movement if the actual app is an iframe or a separate Wayland surface; choose a transition compatible with the real architecture. Ensure focus and pointer input transfer at the correct time.
5. **Quick Settings and notification surfaces:** top swipe-down panel, expansion/collapse, toggle state, tiles, subpanels and dismiss. Animate transform/opacity and background changes without expensive full-screen blur. Make gesture progress track the finger if current architecture supports it. A backend operation may finish asynchronously; keep the UI truthful and interactive.
6. **Dialogs, context menus, popovers and power menu:** enter/exit motion, correct z-order, safe hit testing, backdrop only if affordable, and escape/back dismissal behavior. No invisible overlay should capture touches after closing.
7. **Lockscreen:** lockhead drag response, subtle idle/wiggle if already intended, unlock handoff, battery presentation and status indicators. Keep unlock geometry accurate and motion independent of backend call completion. No navigation controls on the lockscreen if current design intentionally hides them.
8. **Keyboard:** show/hide, key press, shift/caps state, suggestion row if present and focus transitions. Typing must never wait for a decorative animation; do not animate each key in a way that drops input or burns CPU.
9. **Lists, scrolling and overscroll:** preserve native/direct scroll performance; add only subtle feedback where the current UI supports it. Do not put JavaScript in the scroll hot path, animate `top/left/height` per scroll frame, or disable inertia to create the illusion of control.
10. **Switches and sliders:** immediate visual feedback, smooth thumb/track movement, actual state update and error rollback if the backend rejects a change. Do not animate to a fake success state.
11. **Loading/empty/error/success states:** short purposeful entrance/exit or progress indication. Respect reduced-motion preference; avoid permanent spinning indicators for operations that are not really running.
12. **Battery and system status:** battery fill/percentage updates should be subtle and not animate stale readings; charging animation only while the true charging state is active. Avoid animation restarts on every poll if the state did not change.
13. **Three penguin status icons:** see the dedicated section below; each must have its own motion and actual state binding.
14. **Orientation/layout changes:** animate only properties that remain geometrically correct during rotation. Never animate touch coordinates separately from the content, and do not hide a broken rotation behind a crossfade.
15. **Browser/WebKit UI:** browser top bar, tabs, toolbar reveal/hide and page transitions only if the current UI owns those elements. Do not try to animate remote web content or interfere with WebKit's native scrolling.
16. **Focus/hover/selection:** keyboard focus and active selection should remain visible. On touch-first hardware, hover must not become a sticky pseudo-state.
17. **System notifications / temporary toasts:** animate in/out quickly, dismiss deterministically, avoid overlapping the nav strip and do not accumulate timers after app switches.

Create an audit table mapping each real UI movement to the implementation and test. Any movement intentionally left unanimated must have a reason (e.g. direct manipulation, readability, expensive surface or native compositor behavior).

## 5.3 Animation engineering constraints

- Prefer compositor-friendly `transform` and `opacity` for simple transitions. Animate `height`, `width`, `top`, `left`, large `box-shadow`, blur/filter and gradients only when necessary and measured to be affordable.
- Avoid layout thrashing: do not interleave DOM writes and layout reads; batch reads, then writes. Replace forced `offsetWidth` transition resets with a safer state-driven approach if the current behavior causes measurable jank; don't remove them blindly if they solve a real transition issue.
- Use `requestAnimationFrame` for JS-driven visual updates, with at most one outstanding callback per component. Cancel frames on destroy/hidden state and do not create a new loop on every pointer move.
- Clean up event listeners, observers, animation frames, intervals, timeouts and subscriptions when a component is hidden/destroyed or the app changes. Repeated open/close must not multiply listeners or background loops.
- Avoid animating huge full-screen layers simultaneously, excessive DOM shadows, full-screen `backdrop-filter`, expensive CSS filters or continuous repaint of static content.
- Keep stable layer composition; add `will-change` only to elements that truly animate, only near the transition, and remove it afterwards. Do not apply `will-change: transform` to every element permanently.
- Use `prefers-reduced-motion: reduce` or the project's equivalent setting. Reduced motion should shorten/disable nonessential movement while preserving immediate state feedback and all functionality. Ensure the app still works if this media query is unsupported.
- Handle interruption, cancellation, pointer cancel, page visibility changes and fast repeated taps. Animation promises must not leave state locks set if cancelled.
- Do not animate from `display:none`; use correct entry/exit structure. Remove hidden elements from hit testing/accessibility when fully dismissed.
- Respect user preference / battery mode if Nuxel has one. If no motion setting exists, do not invent a large settings subsystem; implement a safe OS/browser preference fallback and document it.
- Avoid heavy JS animation libraries unless one is already installed and compatible. Prefer the smallest native CSS/JS implementation.
- Do not use infinite animation for all icons or all surfaces. Continuous motion is reserved for meaningful active states and should stop when the device is locked/screen-off or the relevant feature is inactive.

## 5.4 The three lockscreen penguins — individual, animated, state-correct

Target assets historically referenced (verify exact current files before editing):

- `./assets/nuxel-charging.png`
- `./assets/nuxel-connected-pc.png`
- `./assets/nuxel-live-console-active.png`

Earlier work reported that positions/sizes were corrected and the charging indicator already behaves correctly. **Preserve the deployed positions, sizing, artwork, transparent margins, clipping and spacing.** Do not regress A70/A71/A73/A74 work or recreate these icons from scratch.

Required motion language (adapt to existing design):

- **Charging penguin:** a gentle, smooth bob/pulse or tiny charging spark/glow, active only while the authoritative charging condition is active. Avoid a large jump, strobing, color flashing or restarting the animation on every backend poll. On charging stop, transition out quickly and remove from visible state.
- **PC-connected penguin:** subtle side-to-side sway, tiny bounce or restrained two-frame “connected” wiggle while a real host/data connection is established. Keep it visually calmer than a warning. Stop/exit when host connectivity is lost.
- **Live Console penguin:** distinct, subtle terminal/activity pulse or tiny rhythmic wiggle only while the real console transport/session is active. Do not animate it merely because the console daemon exists. Stop immediately when session state becomes inactive; any short exit fade must not delay the semantic OFF state.

Use separate CSS classes/state flags for `charging`, `pc-connected`, and `live-console-active`; never a shared “USB active” class that lights all three. Ensure state classes are derived from authoritative backend values. Use accessible labels/alt text where the UI currently supports them.

Performance rules for the icons:

- Keep motion low-cost (`transform`/`opacity` preferred). Avoid continuous full-resolution image filters or layout-affecting keyframes.
- Avoid duplicate image decoding and huge intrinsic image dimensions where unnecessary; preserve transparent PNG if it is the best compatible source. If optimizing assets, retain alpha and crisp pixel edges.
- Do not reload the image or reset its animation on every indicator poll; update only on state transitions.
- Stop decorative motion while hidden, offscreen or screen-off; restart smoothly on visible/wake without a long first-frame stall.
- Make sure CSS selectors do not accidentally leave `.active`, `.visible`, `aria-hidden`, pointer events or animation classes behind after detach.
- Confirm actual visible artwork dimensions, not just the PNG canvas dimensions; transparent margins may make an icon appear small. However, positions/sizes are already working—do not “fix” them unless visual evidence shows a regression.

### Required visible-state timing

On a real host disconnect, backend state becomes disconnected immediately after reliable detach confirmation; the PC and Live Console elements are marked inactive/hidden in the UI without waiting for a long animation or polling timeout. A short fade/scale exit may run, but the semantic state and hit testing must already be off. If the event source is unavailable or transient, expose the real uncertainty rather than leaving a false active icon indefinitely.

---

# 6. PERFORMANCE BOOSTER — PROFILE THE ENTIRE PATH, THEN FIX THE BIGGEST COSTS

Do not assume all slowness is CSS. Trace touch → event handler → state update → JS/layout/paint → compositor → screen/framebuffer presentation. If an app is slow because a system call or backend blocks the UI thread, prettier CSS will not solve it.

## 6.1 Input-to-visible feedback

- Ensure taps and pointer-down events get immediate local feedback before slower backend work, without falsely reporting that a system operation succeeded.
- Move noncritical work off synchronous input handlers; debounce only noisy nonessential operations, not direct touch or USB detach state changes.
- Ensure no synchronous file/network calls, blocking subprocesses, long loops or full asset decoding happen in a touch handler.
- For long tasks, chunk work and yield appropriately. Avoid introducing timers that add latency to the actual action.
- Keep touch targets, pointer capture, swipe thresholds and gesture cancellation correct. Performance changes must not cause missed or duplicated taps.

## 6.2 JavaScript and DOM

- Profile current JS before rewriting. Reduce repeated selector queries in hot paths, redundant JSON parsing, needless state re-renders, full-screen DOM rebuilds, large synchronous loops and duplicate subscriptions.
- Cache stable references where safe; invalidate them correctly when nodes are replaced.
- Use event delegation for repeated elements where it reduces listener count without breaking event semantics.
- Coalesce multiple visual state updates into one frame. Avoid state churn when the value has not changed.
- Use passive listeners only for events that truly do not call `preventDefault`; do not make swipe gestures passive if that breaks intended capture.
- Prevent repeated fetches/polls when state is unchanged; handle errors and disconnects cleanly. Avoid multiplying intervals on screen re-entry.
- Inspect app iframe/WebKit lifecycle and avoid destroying/recreating an app for every Home/Back transition if the architecture intends it to remain warm. Balance fast resume with memory bounds and correct app state.
- Keep code understandable and testable; do not minify source as a substitute for performance engineering.

## 6.3 CSS, layout and paint

- Find expensive style recalculations and forced layouts using supported WebKit tooling or lightweight instrumentation.
- Prefer transform/opacity for transitions; reserve geometry changes for layout transitions that genuinely require them.
- Avoid large blur/backdrop effects over moving backgrounds if they cause repaint storms; preserve the visual concept using cheaper translucent surfaces when evidence supports it.
- Avoid unbounded shadows, animated filters, large masks/clip-path recalculation and excessive overlapping layers.
- Use containment/content-visibility only if the deployed WebKitGTK supports the relevant feature and the UI semantics remain correct. Feature-detect or use a safe fallback.
- Respect correct z-order, keyboard focus, click-through and lockscreen touch geometry.

## 6.4 Image and asset optimization — safe, reversible and visual-quality aware

Inventory all UI assets and report original size, rendered dimensions, file size, alpha/transparency, format, loading path and usage. Prioritize oversized assets that load during boot, lockscreen, launcher, app switching and animations.

- Preserve original assets in version control or a dedicated backup folder and record hashes. Never overwrite the only copy of a beloved penguin or background.
- For opaque photographs/backgrounds, test a supported modern lossy format (WebP/AVIF only if the deployed WebKitGTK version truly supports it) at high quality and compare visual fidelity. For transparency and sharp pixel art, use lossless PNG optimization or a verified alpha-preserving WebP only if supported and visually identical enough.
- **Never convert transparent PNGs to JPEG.** Preserve alpha edges, pixel-art crispness, and correct color profile. Be careful with palette conversion, premultiplied alpha and gamma shifts.
- Do not assume AVIF/WebP is supported merely because the desktop browser supports it; test the exact device's WebKitGTK. Keep PNG/JPEG fallback assets where needed.
- Resize only assets whose intrinsic pixel dimensions are materially larger than the maximum displayed size and whose future scaling requirements are understood. Keep high-resolution sources if they are used in a zoom, rotation or splash sequence.
- Optimize PNG with lossless tooling (e.g. `oxipng`, `optipng`, `pngquant` only for a separately approved lossy palette tradeoff) when available; verify resulting transparency and pixel edges. Use deterministic tool flags and document versions.
- Use responsive `srcset`/sizes or separate assets only if the current WebKitGTK/PWA architecture supports them and actual memory/load time improves. Avoid serving many variants unnecessarily.
- Lazy-load noncritical offscreen images and defer noncritical modules, but eagerly load the lockscreen, first Home frame, nav icons and essential system status assets so they never pop in late.
- Preload only genuinely critical fonts/images; excessive preload competes with first paint and wastes memory.
- Avoid embedding large image base64 blobs in JS/CSS if external files improve caching and startup; preserve offline behavior and path resolution.
- Deduplicate repeated assets only when packaging/runtime paths support shared use and caching is real. Avoid symlink tricks that break installation.
- Compare source and optimized output side-by-side, and measure cold/warm startup, memory and paint cost. Reject any optimization that blurs important text/artwork, damages transparency, changes expected dimensions, or does not produce a meaningful benefit.
- Add an asset audit report with before/after bytes and the visual/compatibility check used.

## 6.5 Framebuffer / compositor / display bridge (only if confirmed in live stack)

If the current phone still uses a software-rendered Phoc/Pixman/headless output and a separate `nuxel-wl-fb` screencopy-to-framebuffer bridge, measure each stage separately. Do not assume that old configuration is active.

- Identify the single authorized writer to `/dev/fb0`; never run a second bridge or competing display service.
- Reuse capture buffers and conversion buffers if safe; avoid allocating/freeing a full frame every frame.
- Check stride, pixel format, alpha handling, alignment, endianness and source/destination dimensions. Preserve correct pixels before optimizing copies.
- Avoid needless full-frame conversion/upscale when buffers or format can be reused; investigate damage/partial updates only if the real compositor/screencopy API and bridge support it correctly.
- Use bounded, frame-paced scheduling; avoid busy-spin and repeated copies of an unchanged frame. Sleep/yield while no new frame is available.
- Compare 30/45/60 frame caps only if the actual output path supports them. Stable 30 FPS may feel better than unstable 60; do not promise a target the pipeline cannot deliver.
- Do not change native panel resolution, framebuffer mode, Phoc output size or scale without a controlled A/B test, exact rollback and owner approval if the screen may blank. Distinguish logical CSS pixels, compositor pixels, framebuffer pixels and physical panel pixels.
- Do not claim Panfrost/Mali hardware acceleration unless the actual renderer/driver and rendered path prove it. Mesa alone does not guarantee usable GPU acceleration on the legacy vendor kernel.
- Never start a second framebuffer writer, replace the known-good bridge with an old historical binary, or change kernel/DTB/boot configuration in this mission.

## 6.6 App lifecycle, startup and memory

- Measure cold vs warm app launch and return-to-home separately.
- Defer noncritical startup tasks until after first interactive Home; do not delay battery, touch, network or USB state correctness.
- Cache only assets/data that are safe and bounded; add eviction/cleanup. Avoid caching giant images or app DOMs without a memory budget.
- Repeatedly open/switch/close apps and observe RSS, process count, WebKit workers, listeners and timers. Memory should plateau, not climb without bound.
- Do not kill/recreate essential services on each UI transition. Do not keep all heavyweight apps alive if memory pressure makes the phone less responsive.
- Keep network/browser functionality and offline UI behavior working.

## 6.7 Power, thermals and idle

- Profile locked screen-off CPU, timers, compositor/bridge activity and animation loops.
- Stop nonessential animation and frame polling when the display is off or UI is hidden; resume without stale state after wake.
- Never use infinite high-frequency polls, max-governor pinning, disabled thermal controls or watchdog suppression.
- Use a short, controlled screen-on interactive soak and screen-off locked soak; compare comparable starting conditions. If measurements are unavailable, report that instead of claiming improved battery life.

---

# 7. IMPLEMENTATION STRATEGY — SMALL PATCHES, EVIDENCE, ROLLBACK

Make changes in risk order, not all at once:

1. **State correctness + instrumentation:** capture USB detach evidence; fix authoritative USB state and add regression tests.
2. **D-Bus/provider root cause:** capture the exact Wi-Fi/BT/Location error and reconcile UI, bridge, D-Bus names/interfaces, units and deployed versions.
3. **Restore real Wi-Fi operations:** verify scan, connection, IP, DNS, TLS and browser before cosmetic work.
4. **Restore Bluetooth and Location controls truthfully:** enable real backend operations where supported; report driver/firmware/hardware blockers precisely.
5. **Baseline and profiling:** create repeatable performance scripts and record unchanged numbers.
6. **Motion tokens + missing transitions:** add shared tokens and improve high-visibility interactions; verify each group.
7. **Three icon animations + stale-state clearing:** bind animation to actual state and keep it low-cost.
8. **Measured JS/CSS hot-path fixes and asset optimization:** one category at a time, visual checks included.
9. **Display/bridge optimizations:** only after measurements establish a bottleneck and rollback is ready.
10. **Integrated regression:** navigation, lock/unlock, Wi-Fi/DNS/TLS/browser, Bluetooth, Location, USB detach/reconnect, app lifecycle and thermal checks.

Use an isolated branch/worktree if possible. Keep each logical change small enough to revert independently. Do not change a CSS animation, USB state model, image formats and display bridge all at once; otherwise a regression cannot be attributed.

For each optimization, record:

`hypothesis | baseline evidence | minimal patch | tests | measured delta | visual check | power/thermal impact | keep/reject | rollback`.

No unmeasured “cleanup refactor” is allowed to piggyback on this mission. Avoid renaming/reformatting unrelated files or replacing project conventions.

---

# 8. TESTS — AUTOMATED, DEVICE-RUNTIME AND PHYSICAL MUST BE DISTINCT

## 8.1 Automated tests

Run the project's actual test/build/lint commands after discovery. Add targeted tests for:

- USB state transitions, idempotent detach, host vs console vs charging separation, stale-state invalidation, no reboot command and reconnect;
- frontend receives backend OFF state and removes stale classes; animation does not delay semantic OFF;
- each icon has its own active condition and distinct animation; no icon becomes active from an unrelated state;
- animation cancellation/reversal, rapid repeated taps, pointercancel, hidden tab, app destroy/reopen and reduced-motion preference;
- listener/timer/requestAnimationFrame cleanup and no duplicate subscription on repeated mount;
- app navigation and z-order after transition; no invisible overlay captures touch;
- asset paths, formats, alpha, dimensions and fallback compatibility;
- JS unit tests or instrumentation for no long synchronous work in input handlers;
- benchmark scripts are bounded and exit without background processes;
- service restart/teardown handling does not reboot the OS on a simulated disconnect;
- D-Bus bridge readiness checks bus name, object, interface and methods rather than only systemd process state;
- D-Bus missing name/object/interface/method, activation failure, wrong bus, permission denial, timeout and service restart paths are handled truthfully;
- Wi-Fi toggle/scan/connect/disconnect use the real installed backend and read back actual state;
- Bluetooth enable/disable and Location enable/disable call the actual supported providers and never report fake success;
- GNSS fix status is kept separate from a Location service/policy toggle.

Do not mock every backend function to always return the desired state. Test error paths and stale data. Record exact test commands, counts and failures.

## 8.2 Device-runtime tests without physical cable movement

If possible, verify the live service/API/UI and animation behavior while connected; measure current indicator payload, animation frames, CSS computed styles, CPU and memory. Mark these as `PASS_DEVICE_RUNTIME`, not physical detach proof.

## 8.3 Physical unplug / reconnect acceptance matrix

Before physical test, ensure an independent recovery path or owner-supervised test plan. Capture boot ID and uptime immediately before and after each unplug. Stop after one crash; preserve evidence and do not repeat blindly.

| ID | Action | Required result |
|---|---|---|
| U1 | Boot Nuxel without computer cable | No false PC/Live Console icons; no stale session; normal UI |
| U2 | Connect PC data cable | PC icon appears only after real host/data connection |
| U3 | Start actual Live Console session | Live Console icon appears only when transport/session is truly active |
| U4 | Disconnect PC cable while console is active | PC and Live Console icons turn off promptly; no hang/reboot; same boot ID; uptime continues; UI responsive |
| U5 | Reconnect PC and resume console | Both states return only after their real prerequisites; no manual reboot needed |
| U6 | Repeat attach/detach at least 5 times after first safe pass | No stale icons, crash, service storm, zombie process or delay growth |
| U7 | Use wall charger/power-only source | Charging indicator correct; PC/Live Console off |
| U8 | Remove PC data while separate power remains, if physically supported | PC/Live Console off; charging state remains accurate |
| U9 | Disconnect while console is idle and while output is active | Both cases safe and responsive |
| U10 | Immediately use Home/Back/Recents and open browser after detach | Controls work, Wi-Fi/DNS/TLS/browser remain intact |
| U11 | Lock/unlock and observe all three icons | Positions/sizes correct; distinct animation; state truthful; no controls visible on lockscreen contrary to current design |
| U12 | Repeated home swipes, app opens, Quick Settings and keyboard cycles | Motion feels consistent; no stuck half-transitions, missed input or memory growth |
| U13 | Screen-on interactive soak and screen-off locked soak | No excessive heat, busy-loop, runaway CPU or wake regression |
| N1 | Toggle Wi-Fi from Quick Settings | Real bridge/backend response; no missing-provider error; UI state follows backend |
| N2 | Scan/connect to an approved known Wi-Fi network | Real scan and connection; valid IP/route; DNS and HTTPS/TLS/browser work |
| N3 | Disable/re-enable Wi-Fi and reopen Quick Settings | State remains correct; no stale bridge proxy or stuck switch |
| N4 | Toggle Bluetooth ON/OFF | Real adapter state if supported; exact blocker reported otherwise |
| N5 | Toggle Location ON/OFF | Real location-service/policy state if supported; no fabricated GPS fix |
| N6 | Restart/reconnect bridge safely | Bus name/object/interface readiness verified; clients recover without restart storm |

Each test must be labelled one of `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_OFFLINE_ONLY`, `BLOCKED_HARDWARE`, `NOT_TESTED`, `FAILED`. Do not upgrade a mocked/offline test to physical pass.

## 8.4 Performance acceptance criteria

Use the baseline to define meaningful improvement. Prefer:

- lower touch-to-first-visible-feedback median and p95 on important controls;
- fewer long frames and better p95/p99 frame interval, not just average FPS;
- lower or stable CPU/memory during equivalent UI work;
- no increase in locked screen-off CPU/temperature;
- faster or equal app readiness with no loss of app state;
- no visual degradation in penguins, lockscreen, text, transparency or layout;
- no input dead time while transitions are running;
- USB detach-to-icons-off measured and bounded by the actual event/update path, normally well under one second where the available kernel/event path supports it. Report real timing; do not invent a guarantee if the hardware event is delayed.

If the legacy software compositor or kernel is the dominant ceiling, make the best safe measured improvements and clearly state what remains limited by architecture. Do not fake 60 FPS or claim unsupported GPU use.

---

# 9. BUILD, DEPLOY, AND ROLLBACK

1. Build/test on the host using the project's established workflow. Confirm ARM64 architecture and target ABI for device binaries.
2. Save the pre-change deployed file and SHA-256 for every changed live file/binary/config/unit. Keep a rollback script with exact restore commands and service restart order.
3. Deploy only the smallest coherent subset, preferably one layer at a time. Do not overwrite the whole rootfs or install an old full drop-in ZIP.
4. Verify deployed hashes, process command lines, service ownership and API/UI behavior after each stage.
5. Restart only the necessary UI/service process and only if the recovery path remains available. Warn the owner before a potentially screen-disrupting change.
6. After motion changes, check first Home frame, lockscreen, touch alignment, app switching and reduced-motion behavior immediately. If the UI becomes inaccessible, roll back immediately.
7. After USB service changes, do not test by pulling the only connection without a prepared independent path. On the first hang/reboot, stop, preserve pstore and journal evidence, and fix the evidenced cause before another trial.
8. After asset changes, compare image dimensions, alpha, color, load timing and visual result on the device—not only in a desktop viewer.
9. Do not automatically reboot to “see if it works.” If a reboot is needed for a service or asset reload, explain why and ask for approval when it risks access or recovery.
10. Keep performance experiments and diagnostics opt-in, bounded and removable. Production should not ship with verbose tracing, an inspector port or background profiling loops enabled.

---

# 10. REQUIRED DELIVERABLES

Create `docs/performance/A75/` (or follow existing repo convention) and deliver:

1. `00-CURRENT-STATE-AND-DEPLOYED-HASHES.md` — current commit, dirty files, device/runtime identity, active renderer/bridge, service owners, deployed file hashes and recovery path.
2. `01-BASELINE.md` plus `A75-BASELINE.json`/CSV and relevant bounded traces — timings, FPS/frame intervals, CPU/memory/thermal and test conditions.
3. `02-USB-DETACH-ROOT-CAUSE.md` — exact observed event path, evidence, failure classification, hypothesis/falsification, fix and any uncertainty.
4. `02B-DBUS-BRIDGE-PROVIDER-ROOT-CAUSE.md`, `02C-WIFI-RESTORATION.md`, `02D-BLUETOOTH-LOCATION-STATUS.md` — exact D-Bus/provider diagnosis, real Wi-Fi end-to-end results, and Bluetooth/Location backend state or evidenced hardware blockers.
5. `03-USB-STATE-MODEL-AND-INDICATORS.md` — source of charging, PC host state and console transport state; event flow to backend/UI; measured detach-to-off latency.
6. `04-MOTION-AUDIT.md` — every actual UI surface, its transition, duration/easing, state behavior, reduced-motion behavior and test; explain any deliberately unanimated direct-manipulation path.
7. `05-THREE-PENGUIN-ANIMATION-AND-STATE.md` — asset identity, positions/sizes preserved, separate animation/state classes, stop conditions and visual acceptance.
8. `06-PERFORMANCE-ROOT-CAUSES.md` — measured top bottlenecks in touch/JS/layout/paint/compositor/bridge/assets/app lifecycle.
9. `07-ASSET-OPTIMIZATION-REPORT.md` — original vs optimized formats, dimensions, bytes saved, compatibility proof, alpha/visual checks, and rollback mapping.
10. `08-BEFORE-AFTER-BENCHMARKS.md` and raw machine-readable data — p50/p95, frame pacing, CPU/memory/thermal and USB state timings; keep/reject decision for each experiment.
11. `09-TEST-RESULTS.md` — automated tests, runtime checks, physical test matrix, exact status labels and logs/evidence locations.
12. `10-ROLLBACK.md` plus executable rollback helper — restore all changed live files/assets and restart only required services safely.
13. `A75-SUMMARY.md` — concise owner-facing summary, improvements actually measured, remaining limitations, physical test status and next safe step.
14. Tests/benchmark tooling used, with bounded duration, clean exit and no background processes left behind.

If a deliverable cannot be produced, explain why; do not fabricate evidence or create empty documents that imply a test ran.

---

# 11. FINAL REPORT — FACTS, NOT VIBES

Finish with a table containing each item and one of `PASS`, `PARTIAL`, `BLOCKED`, `NOT_TESTED`, `FAILED`:

- PC icon clears on real USB detach;
- Live Console icon clears on real USB detach;
- charging icon remains independent and correct;
- physical unplug does not hang or reboot the same boot;
- D-Bus bridge/provider bus name, object, interface and required methods verified ready;
- Wi-Fi toggle, scan, connect, IP/route, DNS, TLS and browser end-to-end;
- Bluetooth actual enable/disable/readback or precise hardware blocker;
- Location service/policy enable/disable/readback and separate GNSS-fix status;
- reconnect and console session recover;
- all three penguins have distinct state-bound animations;
- key UI movement audit completed;
- lockscreen/lockhead and touch alignment preserved;
- Home/Back/Recents, app drawer, Quick Settings, keyboard and browser preserved;
- image/asset changes have visual and device compatibility evidence;
- median/p95 touch feedback and frame pacing before/after;
- CPU/memory/thermal/screen-off behavior before/after;
- exact tests run and their results;
- deployed commit/hash and rollback availability;
- physical verification status.

Network/radio status must additionally be summarized separately as `WIFI_RESTORED`, `WIFI_NOT_RESTORED`, `BLUETOOTH_VERIFIED`, `BLUETOOTH_BLOCKED_HARDWARE`, `LOCATION_SERVICE_VERIFIED`, `GNSS_BLOCKED_HARDWARE`, `DBUS_PROVIDER_FIXED_NOT_DEVICE_VERIFIED`, or `DBUS_PROVIDER_UNRESOLVED`, using only labels supported by evidence. Do not mark Bluetooth/GNSS blocked by hardware unless the actual device evidence proves that; do not mark them working just because D-Bus calls stop erroring.

Overall verdict must be one of:

- `VERIFIED_ON_DEVICE` — physical unplug/reconnect and key UI/performance tests passed;
- `IMPROVED_BUT_LIMITED` — measurable improvements, with a clear remaining hardware/software ceiling;
- `USB_FIX_NOT_PHYSICALLY_VERIFIED` — code/tests improved but no physical detach proof;
- `NO_MEASURABLE_GAIN` — no credible performance improvement;
- `BLOCKED` — unsafe or unavailable test path;
- `ROLLED_BACK` — candidate caused a regression and known-good state was restored.

Do not say “all movements are animated” unless the audit covers the actual UI. Do not say “smooth 60 FPS” because a setting says 60. Do not say “GPU accelerated” unless the active rendering path proves it. Do not say “USB fixed” if the PC and Live Console icons were only hidden with CSS, the phone rebooted, or no physical detach was tested.

## FINAL DIRECTIVE 🐧💥

Go wonky—but engineer like the phone has to survive in someone's pocket. Make every important transition feel deliberate, make the three lockscreen penguins dance only when their real states are true, make Nuxel react instantly, trim waste only where measurement proves it matters, and make unplugging a computer boring. **Smooth penguin, honest pixels, truthful USB state, zero surprise reboot.**
