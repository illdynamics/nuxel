# FULL PWNAGE-85000 — BUTTERSMOOTH PENGUIN
## Flatpak launch latency elimination, system-wide responsiveness, and lightweight Nuxel motion design

**Mission ID:** PWNAGE-85000  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820  
**OS:** Nuxel / Fedora 43 ARM64  
**Known recent kernel from owner report:** Linux 4.14.253 aarch64 (must re-verify live)  
**Primary transport:** Wi-Fi SSH to the Nuxel root console  
**Priority:** P0 Flatpak launch stall; P1 whole-device responsiveness; P2 restrained smooth transitions  
**Execution mode:** inspect → measure → isolate → implement → deploy → physically verify → document/rollback

---

# 0. Mission statement and non-negotiable outcome

Nuxel already works substantially well on the Galaxy S10+. This mission is not a rewrite, a benchmark vanity pass, or permission to destabilize the phone in pursuit of a theoretical FPS number. The objective is to remove the remaining major application-startup delay, improve the responsiveness of the complete phone, and make its interactions feel polished and fluid using small, efficient effects.

The owner has specifically reported that native GTK and Flatpak applications still feel slow. The latest PWNAGE-84000 engineering report contains a critical measurement:

- Native GTK application spawn: approximately **0.48 seconds**.
- Flatpak sandbox initialization: approximately **30.7 seconds**, reproduced three times, with the delay described as occurring in the post-context / D-Bus-proxy phase.
- An `nuxel-app-prewarm` service was enabled, but the underlying Flatpak delay was **not resolved**.

Treat those as owner-supplied recent evidence. Reproduce them on the live phone. Do not reinterpret “spawn” as “first frame” and do not claim the 30.7 seconds is explained until a trace identifies the exact wait. The mission must separately measure:

1. launcher-to-process spawn;
2. process spawn-to-sandbox-ready;
3. sandbox-ready-to-app-process;
4. app-process-to-Wayland surface mapped;
5. surface mapped-to-first presented frame;
6. first frame-to-first accepted input.

A second, separate concern is the rendering policy applied to Flatpak apps. In the supplied repository snapshot, `services/nuxel-bridge/src/flatpak_provider.py` constructs every non-Doom Flatpak launch with these environment settings:

```text
LIBGL_ALWAYS_SOFTWARE=1
GALLIUM_DRIVER=llvmpipe
MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
GSK_RENDERER=cairo
GDK_BACKEND=wayland
MOZ_ENABLE_WAYLAND=1
```

This is a strong candidate for poor **runtime rendering performance** after an app has launched. It does not, by itself, prove the cause of the 30.7-second sandbox delay. The settings may have been added because the deployed host/Flatpak graphics combination cannot reliably present a surface otherwise. Verify current source, live provider, actual session environment and deployed hashes before changing any of them. The correct end state is an evidence-based, per-app renderer policy, not a blanket switch from one untested renderer to another.

The phone's historic A50 performance record also describes Phoc running with Pixman, WebKit software rendering, an fbdev presentation bridge, and no `/dev/dri` device. A50 recorded a 74–79 ms average cost for a changed full frame in that earlier deployment, with damage-based presentation skipping and screen-off capture-stop already present. Those are **historical measurements from October 2026**, not guaranteed measurements of the current November 6 live deployment. Re-probe the running phone before drawing any current conclusion. Preserve all valuable deployed improvements.

The user-visible target is simple: Flatpak apps should open in a reasonable time, app switching and common interactions should feel immediate, the phone should remain cool and responsive, and transitions should look polished without consuming disproportionate CPU, memory or battery.

This mission is complete only after it has made real, safely deployed improvements and supplied reproducible evidence. An excellent audit with no implementation is not completion unless a concrete safety blocker makes implementation impossible.

# 1. Required Wi-Fi SSH connection and device authority

The owner explicitly requires connecting over Wi-Fi SSH and accessing the Nuxel root console with:

```text
~wicked/.ssh/wicked_wqn_id_rsa
```

Use the key; do not request or embed a password. The connection must use:

```bash
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=10 \
  root@<DISCOVERED_WIFI_HOST>
```

## 1.1 Discover the current Wi-Fi address; do not trust stale helper state

Use the current repository helper and inspect its output before connecting. Historical evidence says a helper-pinned host `10.20.30.16` was stale/unreachable during PWNAGE-84000, and the owner supplied `192.168.178.167`, which worked then. Neither IP is guaranteed current.

Use the repo's current S10+ debug-pack Wi-Fi status operation, for example:

```bash
scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport wlan --status
```

Verify helper syntax and behavior from the repository before execution. If the helper exposes a real current WLAN address, use it. If it still reports stale data, obtain the phone's current WLAN IP through an existing trusted project mechanism or the owner-supplied last-known address only after reachability/identity checks. Do not scan unrelated networks or guess credentials.

## 1.2 SSH trust and root verification

- Keep normal host-key verification enabled.
- Do not use `StrictHostKeyChecking=no`.
- Do not delete or overwrite `known_hosts` entries to make a connection succeed.
- If a host key differs, stop and investigate; do not silently accept a changed device identity.
- Use `IdentitiesOnly=yes` so the specified key is the only offered identity.
- Verify `id -u` is `0`, `id -un`, `hostname`, kernel, architecture, model and root filesystem before doing anything mutating.
- Verify the phone is in normal boot, not recovery/TWRP.
- Do not copy, display, log, upload or change permissions on the private key. Do not embed secrets in shell history, scripts, systemd units, environment dumps or evidence.

## 1.3 If Wi-Fi access fails

Do not fall back to USB, TWRP, a guessed IP or a different privilege path without owner authorization. Record the reason and use repository-side analysis until Wi-Fi SSH is restored. Do not claim on-device verification if no live connection was made.

# 2. Current-state facts and historical evidence to preserve

These are starting clues, not substitutes for live inspection.

## 2.1 Latest owner-provided PWNAGE-84000 result (November 6, 2026)

The owner reports that the phone was reached at `root@192.168.178.167` using the specified identity key with `IdentitiesOnly=yes`; root UID was confirmed. The running platform was:

- Samsung Galaxy S10+ SM-G975F;
- Fedora 43 ARM64;
- Linux `4.14.253-gf7194c1d15ed-dirty`;
- Phoc/Wayland with `nuxel-wl-fb` and `/dev/fb0` still intact;
- Mali/EGL stack deliberately left untouched.

PWNAGE-84000 reports these relevant components and results:

- `nuxel-soundd`, `nuxel-soundctl`, PipeWire 1.4.11;
- sound cue response approximately 17.99 ms in one measurement and 19.68 ms for alarm E2E;
- native GTK spawn approximately 0.48 s;
- Flatpak sandbox initialization approximately 30.7 s, measured three times;
- `nuxel-app-prewarm` enabled;
- Legcord 1.3.1 and Vesktop 1.6.8 installed as `aarch64` Flatpak refs;
- all 37 tests reported passing (21 pytest + 16 desktop layout JavaScript tests).

This is the latest supplied report. Verify the current state now: packages, exact app IDs, Flatpak installation scope, remotes, runtime versions, app refs, systemd unit status, process ownership, session bus, environment, provider code and current hashes. Do not assume that deployment or package state has not changed since the report.

## 2.2 Repository findings from the supplied `nuxel-main (12).zip`

The attached repository snapshot is dated November 4 and therefore predates the latest PWNAGE-84000 deployment. Its architecture is useful, but it is not the sole source of truth for the current phone.

Relevant files observed in that snapshot:

- `services/nuxel-bridge/src/flatpak_provider.py`
- `services/nuxel-performance/bin/nuxel-perf-tune.sh`
- `services/nuxel-performance/systemd/nuxel-perf-tune.service`
- `configs/nuxel/portals.conf`
- `pwa/flatpak/nuxel-launcher.sh`
- `pwa/flatpak/README.md`
- `pwa/nuxel-home/js/launcher.js`
- `tests/pwnage37000/test_butterscotch_perf.py`
- `docs/performance/A50/`
- `docs/beta-finalization/testing/SOAK-AND-PERFORMANCE.md`
- `docs/beta-finalization/live/PWNAGE-51000-PERF.md`

The repository Flatpak provider's user-launch wrapper uses a systemd transient unit to run as `nuxel` with `HOME`, `XDG_RUNTIME_DIR`, user D-Bus address, `XDG_CURRENT_DESKTOP=Nuxel`, `WAYLAND_DISPLAY=wayland-0`, and `XDG_DATA_DIRS` set explicitly. Preserve the security intent: the root HTTP bridge must not accidentally run GUI applications as root or with an incomplete user environment. Verify that the live user UID/GID, runtime directory and session bus actually match these configured paths.

The repository provider also calls `is_installed()` from `launch_argv()`. In that snapshot, `is_installed()` rebuilds its answer by calling `installed_ids()` → `list_installed()` → Flatpak list for system and user scope, then parses desktop files and resolves icon paths. Determine whether this scan is on the live UI's launch critical path and measure it. It may add avoidable pre-launch latency, even if it does not explain the reported 30-second sandbox phase. A cache or indexed registry may be appropriate, but it must remain coherent after install, update, uninstall and remote changes.

The historic portal configuration selects the GTK portal backend for supported interfaces and intentionally does not advertise unsupported ScreenCast behavior. Do not replace portal routing wholesale or pretend the wlr portal works if its PipeWire socket/ownership setup does not. Inspect the live service and portal readiness files and maintain truthful capabilities.

## 2.3 Historical A50 display-performance facts

A50's October 22 historical live inventory documented:

- S10+ AMOLED panel 1440×3040;
- Phoc headless output 720×1520 with scale 2;
- `nuxel-wl-fb` as sole `/dev/fb0` writer;
- a CPU Pixman render path and software WebKit settings at that point in time;
- no `/dev/dri`, `/sys/class/drm`, GBM or EGL DRM node in that specific build;
- a changed-frame bridge cost of 74–79 ms and roughly 13 FPS theoretical ceiling for full-screen continuously changing content;
- damage-based presentation skip for most unchanged frames;
- screen-off `capture=stopped` behavior and approximately 0.1% bridge CPU use during display sleep.

A50 explicitly warned that the deployed `nuxel-wl-fb` binary was newer than committed source, with damage skipping and screen-off capture-stop not represented by the stale source. Rebuilding from old A34 source would risk regression. This mission must re-check the current binary and source relation. Do not replace an unknown newer binary with a stale build.

Historical A50 suggested that NEON optimization of the bridge hot loop, removing software backdrop blur, right-sizing oversized artwork and a carefully controlled resolution A/B could help—but no experiment was promoted in that investigation. Do not assume any of those historical recommendations have been implemented or remain safe. Re-evaluate from current evidence.

## 2.4 Current services to protect

The recent owner report says the following classes of components were working after PWNAGE-84000. Verify exact current names and state before deployment:

- `nuxel-clockd` and its scheduler/persistence;
- `nuxel-soundd` and sound routing;
- Nuxel bridge/API;
- microphone route service and gain setting;
- `nuxel-app-prewarm`;
- Phoc/Wayland and `nuxel-wl-fb`;
- PipeWire/WirePlumber/audio services;
- Wi-Fi/network access.

A performance pass must not break the clock, alarms, timer, audio, microphone, display sleep/wake, orientation, launcher, widgets, touch, camera work in progress, or user files.

# 3. Performance engineering principles

1. Measure first. Every optimization must target a measured delay, CPU hotspot, memory problem, I/O wait, wakeup source or frame bottleneck.
2. Distinguish latency categories. Process spawn is not window-ready; window-ready is not first presented frame; first frame is not first interactive response.
3. Separate startup from rendering. Fixing a 30-second launch stall does not prove that a Flatpak app will render smoothly afterwards.
4. Preserve sandboxing. Performance cannot be purchased by disabling Flatpak/bwrap isolation or granting broad filesystem/device access.
5. Preserve user/session identity. GUI applications must run as the real graphical user with the actual user D-Bus and Wayland session.
6. Optimize critical paths, not convenience functions. App launch should not synchronously refresh every remote, enumerate every package, scan all icons, query unrelated providers or wait for optional services.
7. Keep the phone cool and battery-safe. A benchmark that improves by running the CPU at maximum frequency or keeping large processes resident is not a valid default improvement.
8. Favor bounded caches over hidden always-on workloads. Cache the information that materially shortens a critical path; invalidate it correctly; measure its RAM and idle cost.
9. Avoid architecture rewrites. The existing framebuffer owner, compositor, display and user-space service architecture is valuable and must be preserved unless a proven issue demands a carefully staged change.
10. Make a single controlled change at a time, then compare under similar conditions.
11. Never fabricate FPS, timing, power, temperature, memory or GPU-acceleration claims.
12. A visual effect that produces stutter is not polish. The owner values a buttersmooth, responsive interface over glow, blur or elaborate motion.

# 4. Phase 0 — baseline, identity, backup and current deployment map

Before changes, create a timestamped campaign directory:

```text
docs/pwnage-85000/evidence/<UTC_TIMESTAMP>/
```

Recommended subdirectories:

```text
baseline/
traces/
flatpak/
process/
frames/
thermal/
experiments/
deployment/
rollback/
```

Record:

- repository root, branch, commit, dirty status and untracked files;
- current local source hashes for every file to be changed;
- live device model, board, kernel, architecture, Fedora release and boot mode;
- live hashes, size, mtime and ownership of deployed services/binaries;
- exact systemd units and drop-ins for Phoc, Wayland, `nuxel-wl-fb`, launcher, bridge, portal, PipeWire, clock, sound, microphone, prewarm and performance tuning;
- Flatpak version, architecture, installations, remotes, installed apps, runtimes and app refs;
- exact app IDs and Flatpak install scope for at least one small GTK Flatpak, Vesktop/Legcord if available, and another representative app;
- user UID/GID/home, runtime directory, session bus socket, Wayland socket and process tree;
- current CPU frequency policy, governors, thermal interfaces, memory, zram/swap, storage free space and mount options (read-only inspection first);
- current `nuxel-wl-fb` status and framebuffer owner;
- current Phoc renderer/backend and WebKit/GTK rendering environment;
- current active theme and motion preference.

Back up all live files and units that may be modified. Back up configuration and relevant user state before modifying Flatpak overrides or per-app renderer settings. Do not copy private tokens, cookies or unrelated personal information into evidence.

## 4.1 Read-only system baseline

Use bounded read-only commands, adapted to what is actually installed:

```bash
uname -a
cat /etc/os-release
id
getent passwd nuxel
systemctl --failed
systemctl list-units --type=service --state=running
systemd-analyze time
systemd-analyze blame
systemd-analyze critical-chain
free -h
cat /proc/meminfo
cat /proc/pressure/cpu /proc/pressure/memory /proc/pressure/io 2>/dev/null
cat /proc/loadavg
cat /proc/stat
cat /proc/uptime
findmnt
lsblk -o NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,ROTA
```

Do not treat every command as universally available; mark missing tools `UNAVAILABLE`. `systemd-analyze blame` is useful but not a definitive causal graph: it measures unit initialization durations and can be misleading where one service is delayed by another dependency. Use `critical-chain`, journal timestamps and per-unit `ExecMainStartTimestampMonotonic`/`ActiveEnterTimestampMonotonic` when available to locate actual critical-path waits.

Collect the current display pipeline truth:

```bash
ps -ef | grep -E 'phoc|nuxel-wl-fb|nuxel-pwa-host|WebKit|mali|pipewire'
cat /run/nuxel-wl-fb.state 2>/dev/null
ls -l /dev/fb* /dev/dri/* /dev/mali* 2>/dev/null
ls -l /run/nuxel-wayland /run/user/* 2>/dev/null
```

Inspect current `phoc` process environment through a privacy-safe selected environment dump, not an indiscriminate dump of every process environment. In particular verify `WLR_BACKENDS`, `WLR_RENDERER`, `LIBGL_ALWAYS_SOFTWARE`, `WEBKIT_DISABLE_COMPOSITING_MODE`, `GSK_RENDERER`, `GDK_BACKEND`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`, `XDG_CURRENT_DESKTOP` and `XDG_DATA_DIRS`.

Do not infer GPU availability from the presence of `/dev/mali0` alone. Distinguish Mali kbase device access, vendor EGL implementation, Wayland EGL support, Mesa/GBM support, DRM render-node support and the ability of a given Flatpak runtime to load a compatible graphics driver.

# 5. Phase 1 — reproduce and decompose the Flatpak 30.7-second delay

This is the highest-priority issue. A repeatable 30-second wait usually indicates a bounded timeout, service activation wait, IPC timeout, proxy negotiation, filesystem operation or other blocking path—not a reason to add another generic prewarm daemon. Identify the exact wait.

## 5.1 Representative application matrix

Select apps that are already installed and known to work or at least launch. Do not download new runtimes simply to create a benchmark matrix. Use the following where currently present:

- one lightweight GTK application (e.g. a simple utility);
- Archive/File Roller if present as a Flatpak;
- one GTK4/libadwaita Flatpak if installed;
- Vesktop and Legcord as Electron/Chromium-based Flatpaks, but do not mix their first-run setup/login work with GTK timings;
- Crispy Doom only as a separate special case because its wrapper and graphics workaround differ;
- one native GTK app for comparison;
- one Nuxel PWA for comparison.

The app list and app IDs must come from live `flatpak list`/`flatpak info`, not guessed names. Record app ID, version, branch, architecture, runtime, origin, installation scope, sandbox permissions and renderer environment.

## 5.2 Timing model

For every launch, capture monotonic timestamps for as many of these events as possible:

| Marker | Definition |
|---|---|
| T0 | Physical/automation-confirmed app activation or launch button event |
| T1 | Bridge/API receives launch request |
| T2 | App ID validation/installed-state lookup completes |
| T3 | systemd transient unit requested |
| T4 | transient unit begins execution |
| T5 | Flatpak CLI process begins |
| T6 | bwrap process starts and namespace setup begins |
| T7 | D-Bus proxy process starts and/or sandbox bus becomes available |
| T8 | Flatpak command enters the app runtime |
| T9 | target application process begins |
| T10 | target Wayland surface is created/mapped/configured |
| T11 | first frame is presented to the compositor/output path |
| T12 | first meaningful user input is accepted and handled |

Not every boundary can be observed on this build. If one cannot be instrumented, say so and triangulate with process timestamps, unit logs, journal, `strace`, D-Bus monitoring or narrowly scoped instrumentation. Do not label an event as T11 if it is only a process start.

Measure at least five launches per app where feasible. Keep separate:

- first launch after boot;
- cold app launch after the app was fully closed;
- warm launch after runtime/page caches are naturally warm;
- relaunch after terminating the app but retaining system/runtime caches.

Do not clear Linux page cache, delete Flatpak caches, remove runtime data or invalidate indexes as a “cold start” shortcut. Do not benchmark while a package transaction, update, remote refresh or large download is running. Record Wi-Fi state and charging state, and keep thermals comparable.

Report median, p95, min/max and sample count. A single sample is diagnostic, not a benchmark.

## 5.3 Flatpak diagnostics

Use only tools that exist on the phone. Relevant commands include:

```bash
flatpak --version
flatpak list --app --columns=application,name,version,branch,arch,origin,installation,runtime
flatpak info <APP_ID>
flatpak info --show-permissions <APP_ID>
flatpak override --user --show <APP_ID>
flatpak override --user --show
flatpak override --system --show <APP_ID>
flatpak override --system --show
flatpak run --verbose <APP_ID>
```

Choose the correct installation scope (`--user` or `--system`) based on live state. Do not assume default scope. Review the output before sharing; remove usernames, private paths, tokens and app-private data from any externally shared evidence.

For a selected app, inspect the effective runtime environment from inside the sandbox, if supported by the installed Flatpak version:

```bash
flatpak run --command=env <APP_ID>
```

or a controlled diagnostic shell:

```bash
flatpak run --command=sh <APP_ID>
```

Use the exact command syntax exposed by the installed `flatpak --help`; some debug options vary by Flatpak version. Do not add unsupported `--verbose` or debug flags blindly. When useful, use `strace -ff -ttT` around the launch command to attribute long blocking syscalls or child processes. Use `perf`/`perf trace` only if available and if sampling overhead is low enough. Do not install a huge tracing stack on the phone merely for this task.

Inspect:

- bwrap/Flatpak child process tree and exact executable arguments;
- `/proc/<pid>/stat`, `/proc/<pid>/status`, `/proc/<pid>/wchan`, `/proc/<pid>/io` for selected live processes;
- D-Bus session socket existence, permissions, ownership and responsiveness;
- name-owner and activation time for `org.freedesktop.portal.Desktop`, GTK portal backend and any other service the app requests;
- whether the actual app launch blocks on a portal call or only later requests a portal;
- D-Bus proxy startup/exit/logs and exact configured socket paths;
- namespace creation and bwrap stderr;
- runtime and extension mount/lookup latency;
- file access or shared-library scans that block;
- systemd transient unit job queue and execution start;
- `systemd-run` command latency separately from Flatpak command latency;
- SELinux/AppArmor denial logs, without disabling either framework;
- DNS/network/remotes only if the trace proves launch is contacting a remote. An app launch should not synchronously refresh Flathub.

### D-Bus and portal checks

The historic `configs/nuxel/portals.conf` maps selected interfaces to GTK and intentionally leaves unsupported screen-capture capabilities unadvertised. Inspect actual live portal units, D-Bus activation files, config precedence and backend process health. Do not replace the portal map with a broad default merely to hide a timeout.

Verify the real session identity:

- resolve UID/GID/home via passwd and active graphical session;
- verify `/run/user/<UID>` exists and has correct ownership/mode;
- verify the session bus socket exists and is owned by the session user;
- verify `DBUS_SESSION_BUS_ADDRESS` points to that exact socket;
- verify `WAYLAND_DISPLAY` points to an actual socket in the same runtime/session;
- verify `XDG_RUNTIME_DIR` matches the user runtime directory;
- verify the process is running as `nuxel`, not root;
- verify supplementary groups are only those necessary (the provider currently includes audio for app launches; confirm whether each group is needed).

A missing/incorrect user bus or a portal activation deadlock could plausibly create a fixed timeout. Prove it before changing session startup. Do not create a second session bus as an ad hoc fix. Do not use a root-owned user bus path or export another user's session socket.

### systemd-run checks

The source provider in the attached snapshot uses transient systemd units with `--uid=nuxel --gid=nuxel` for user-scope Flatpak jobs and a separate root transaction path for system changes. Inspect the live version. Measure:

1. direct `systemd-run` overhead for a harmless no-op as the `nuxel` user;
2. transient unit queued → start timestamps;
3. time from unit process start to Flatpak CLI start;
4. unit properties and environment actually applied;
5. user manager availability and system manager load;
6. whether synchronous waiting or `--pipe` holds the launch RPC/UI unnecessarily.

Preserve privilege separation. GUI launch must be under the real session user; Flatpak installation transactions may legitimately require system scope/root but must not run the GUI as root. Never replace this with `sudo -u`, `runuser`, an unrestricted shell, or inherited root environment without verifying the bridge's security model and `NoNewPrivileges` constraints.

## 5.4 Inspect the bridge/provider launch critical path

Audit the current live and repository versions of:

- `services/nuxel-bridge/src/flatpak_provider.py`;
- `app_manager.py` and native launch provider;
- `software_provider.py` and Software app refresh flow;
- Bridge HTTP/RPC endpoint dispatch;
- PWA app launcher / app registry / desktop entry parser;
- app-prewarm service and unit;
- any service that enumerates installed apps, icons, runtimes or remotes.

Investigate specific code paths:

**Installed-state lookup:** the supplied provider's `launch_argv()` calls `is_installed()`, which calls `installed_ids()`, which calls `list_installed()`, which enumerates both system and user apps. The enumeration reads desktop metadata and searches icon directories. Determine if every tap performs this scan. If so, introduce a bounded, atomic cache keyed by app ID/scope and a small deployment fingerprint (e.g. installed refs/mtime or update event). Refresh asynchronously after install/update/uninstall and at controlled startup/idle points. Keep a cheap correctness check so deleted apps do not launch as if installed. Do not let stale cache produce success for a removed app.

**App catalogue:** separate app launch from Software catalogue discovery, remote search and icon resolution. Launch must not wait for Flathub, AppStream, remote list, full icon scans or package transaction status. Serve last-known local installed state immediately; refresh catalogue work in the background with visible state and bounded retry/backoff.

**Bridge response:** ensure an app launch request does not block waiting for the application to finish initialization. Return a job/launch token promptly once the process is accepted, then emit state updates. Keep request IDs, failure status and logs. The user should get a responsive UI while the real app appears. Do not fake “launched” before confirming the process/window lifecycle.

**Timeouts:** replace unexplained 30-second waits with explicit, bounded timeouts where safe. A timeout should fail promptly with the actual phase and error, not be globally reduced so far that legitimate first-run runtime initialization is killed. Use separate timeouts for service activation, Flatpak sandbox setup, app startup and package transactions.

**IPC:** inspect synchronous HTTP/D-Bus calls on the launch path. Do not call unrelated providers (Bluetooth, location, battery, audio, etc.) merely to open an application. Use cached status for decorations and refresh independently.

## 5.5 Find the exact root cause; likely classes, not assumptions

Evaluate and either prove or eliminate:

- D-Bus proxy activation or session bus address mismatch;
- portal backend activation timeout or a backend waiting for PipeWire/user session state;
- incorrect XDG runtime directory ownership/path;
- systemd transient unit dispatch or manager queue latency;
- Flatpak install-scope mismatch causing metadata lookup/lock contention;
- bwrap namespace setup or user namespace configuration issue;
- mount/overlay/permission setup cost;
- stale/missing runtime extensions or corrupt deployment metadata;
- fontconfig/GIO/MIME/theme cache stalls;
- library loader searching many nonexistent paths;
- app manager full inventory scan or icon traversal;
- app launch waiting on remote catalogue/network/DNS;
- first-run app initialization (Electron cache, GTK settings, WebKit process pool) being mistaken for sandbox startup;
- SELinux/AppArmor policy denial and repeated retry;
- systemd-run `--wait`/`--pipe` lifetime semantics unnecessarily tying up the bridge/UI;
- a post-context DBus call with a fixed 25–30 second timeout;
- prewarm unit competing for CPU/IO or leaving background processes resident.

The report describes the problem as a fixed 30.7-second stall in the post-context / D-Bus-proxy phase. Treat that as a valuable clue, not a guaranteed diagnosis. A trace must show the actual process/syscall/IPC boundary and wait duration.

# 6. Phase 2 — correct Flatpak renderer policy and post-launch performance

The attached repository snapshot's `flatpak_provider.py` applies software-rendering variables to all non-Crispy-Doom Flatpak launches. Do not assume that policy is still live; diff current repository source against deployed provider and inspect the actual environment inside real app processes.

## 6.1 Build an app-by-app capability matrix

For every selected app record:

| Field | Required value |
|---|---|
| App ID, version, branch | Live Flatpak metadata |
| Architecture/runtime | Actual aarch64 runtime/extension |
| Launch scope | System or user installation |
| Backend | Wayland or other actually used backend |
| GDK/GTK renderer | Effective in-process value |
| Mesa/Gallium flags | Effective value, if any |
| EGL vendor/version | Actual runtime if app exposes it |
| GPU device access | Actual file and permission; do not infer |
| CPU renderer | llvmpipe/softpipe/Cairo/etc. if proven |
| First frame and input | Measured latency |
| CPU/RSS | At 1, 3 and 10 seconds after frame where available |
| Stability | Window, input, scrolling, notifications, suspend/resume |

## 6.2 Distinguish host Mali from Flatpak runtime graphics

The phone's Mali-G76/Exynos 9820 environment is not automatically interchangeable with a generic Mesa/DRM desktop. The historic platform had Mali kbase/EGL but no standard DRM render node in the A50 capture. Re-probe the live system and verify:

- `/dev/mali0` and group/permissions;
- vendor EGL libraries and loader path;
- EGL Wayland platform support;
- GBM and DRM availability separately;
- whether a Flatpak runtime can load an ABI-compatible graphics stack;
- whether the installed runtime bundles Mesa drivers or tries to use host extension drivers;
- whether its sandbox can access the necessary device without broad grants;
- whether Phoc is actually compositing with Pixman or another backend;
- whether WebKitGTK/GTK app rendering has its own software-only override.

Do not say “GPU accelerated” merely because an EGL context initializes. Verify that the app's drawing path, compositor composition, and presentation stage are accelerated as claimed. A Mali vendor EGL context, llvmpipe runtime, and Phoc Pixman compositor are different pieces of the pipeline.

## 6.3 Controlled renderer experiments

For a representative app, test these configurations only when supported by the actual installed runtime:

1. Current deployed environment, unchanged (control).
2. Remove only the global `GSK_RENDERER=cairo` override for a GTK4 app and let GTK choose its supported default.
3. Remove only forced Mesa software variables where the runtime has a valid driver path and no crash/blank-window risk.
4. Use app-specific Wayland backend settings only where app supports Wayland.
5. Retain explicit software fallback for apps that fail to present correctly without it.

One variable per experiment. Store the exact environment and result. Run each app for a short but meaningful touch/scroll test, not just launch success. Watch logs for graphics-driver errors, surface failures, black windows, flicker or compositor instability. If no compatible Flatpak GPU path exists on this kernel/userspace combination, report it honestly and optimize the software path rather than forcing a broken hardware path.

## 6.4 Per-app policy design

If the current global software forcing is proven unnecessary for some apps, replace it with a small, explicit renderer policy:

- `auto`: do not inject unnecessary rendering overrides; let the app/runtime choose its supported default;
- `verified-hardware`: only for an app that passed device testing on the actual graphics stack;
- `software-fallback`: only for apps that require the tested software path;
- optional `known-good-wayland` flag if necessary to select Wayland explicitly.

The default must be conservative and validated. Do not infer support from app toolkit alone. Add clear diagnostics that report the chosen policy and why. Provide a straightforward rollback to the previous global software environment if the new policy causes a regression.

Do not add `--device=dri` when `/dev/dri` is absent; do not grant all devices; do not expose `/dev/mali0` to every sandbox without a proven, least-privilege, ABI-compatible design. Do not inject host libraries into all Flatpaks. Do not use `LD_PRELOAD` hacks as a blanket workaround.

# 7. Phase 3 — prewarm, caching and app lifecycle

PWNAGE-84000 enabled `nuxel-app-prewarm`. Inspect its deployed unit, executable, trigger, targets, startup time, resident processes, memory footprint, idle wakeups and logs. The November 4 ZIP snapshot may not contain the final PWNAGE-84000 version; inspect the live phone and current repository independently.

## 7.1 Distinguish useful warming from waste

Possible useful behavior:

- parse and cache app registry / desktop entry metadata;
- refresh Flatpak installed-ref index after transactions;
- validate portal/session readiness once and publish a truthful readiness state;
- perform small, bounded fontconfig/GIO cache verification or rebuild only when stale;
- warm a small, explicitly selected runtime component if measurement proves a large launch improvement and memory is abundant.

Potentially harmful behavior:

- launching hidden GUI app instances;
- keeping many WebKit/Electron renderer processes resident;
- keeping large Flatpak runtimes mapped without a measurable benefit;
- repeated Flatpak list/remote calls in a loop;
- periodic polling of inactive apps;
- starting a second D-Bus/portal session;
- holding files, audio devices or display resources open;
- preventing screen-off idle or keeping CPU cores awake.

Do not assume `prewarm` is good because the name sounds helpful. Quantify:

- RSS/PSS or RSS if PSS unavailable;
- CPU seconds and wakeups per minute;
- battery/thermal delta over a reasonable idle observation;
- first-launch improvement;
- cold-start regression after a reboot;
- impact under memory pressure.

Use lazy metadata caching first. Prefer a bounded cache that exits/clears under memory pressure. Keep the prewarm unit only if a measured benefit materially outweighs resource cost. It must not be required for correctness or normal app launch.

## 7.2 Cache invalidation and correctness

- Cache installed app IDs, scope, version/ref, desktop name/icon and launch policy.
- Invalidate/update after install, uninstall, update, remote change, app ref change and deployment switch.
- Use atomic writes and a schema/version number.
- Use a bounded TTL fallback if transaction events are missed.
- Do not run remote network discovery as a prerequisite for launching an installed app.
- If the cache is absent/corrupt, rebuild once in the background and use a safe minimal lookup for the requested app.
- A removed app must never remain launchable because of stale cache.
- A new app should become visible after confirmed install without requiring a reboot.

# 8. Phase 4 — whole-device latency and smoothness campaign

Do a controlled baseline and post-change run on the same phone with comparable battery, charging, Wi-Fi, thermal state, screen brightness and app state. Use as little instrumentation overhead as possible.

## 8.1 User-perceived interaction set

Measure and physically check:

1. cold boot to lockscreen visible;
2. unlock to responsive Home;
3. Home to app drawer visible;
4. app drawer scroll and app tap;
5. app launch to first visible frame and input-ready state;
6. app close/minimize back to Home;
7. desktop switch in both directions;
8. Quick Settings open/close and toggles;
9. Settings navigation and scroll;
10. keyboard open, first key response and dismiss;
11. Notes/Calendar/Clock/PWA launch;
12. native GTK launch;
13. Flatpak launch;
14. return from a heavy app to Home;
15. lockscreen and display-off transition;
16. screen wake and first interactive frame.

Record p50/p95, longest pause, dropped/missed frame count or best available proxy, and whether touch input is accepted during animations. Use a physical finger check when the interaction cannot be reliably automated. Do not use synthetic input results as proof of glass-to-photon latency.

## 8.2 Rendering / frame pacing

Inspect the actual Phoc and `nuxel-wl-fb` state and source/binary match first. Use existing telemetry if present:

- `/run/nuxel-wl-fb.state` and current FRAMES_OK counters;
- blit/compose timing;
- capture rate and presented frame counts;
- `present_skipped`/damage skip counters;
- panel commit failures;
- CPU use for Phoc, WebKitWebProcess, PWA host, `nuxel-wl-fb`;
- per-process faults/context switches where available;
- touch/input and frame timestamps.

Capture short repeatable intervals for static lockscreen, simple menu animation, app drawer scrolling, desktop switching and an actual Flatpak app. Use p50/p95/p99 frame intervals if the telemetry supports it. Record sample count and measurement limitations.

The October A50 baseline of 74–79 ms per changed frame is a historical reference, not a current acceptance result. If similar costs remain, decompose the path rather than raising a target FPS cap. In a software framebuffer architecture, a claimed 60 FPS animation target may be physically unrealistic. It is acceptable to use a lower but consistent animation cadence if it feels smooth and does not overload the device. Prioritize stable cadence, fast input acknowledgement and avoiding long stalls over theoretical FPS claims.

### Preserve the sole framebuffer owner

- Confirm exactly one process owns `/dev/fb0` writes.
- Do not let a second renderer, screenshot helper or benchmark write to fb0.
- Keep `nuxel-wl-fb` damage-driven skip and screen-off capture-stop behavior.
- Preserve current output resolution/scale unless a separately approved A/B proves a net benefit and readability remains acceptable.
- Do not deploy stale bridge source over a newer live binary.
- If optimizing `nuxel-wl-fb`, first recover exact deployed source/build provenance. If that cannot be established, do not replace it.

## 8.3 WebKit and PWA efficiency

Inspect and profile:

- `nuxel-pwa-host` and WebKitWebProcess counts;
- process reuse policy and process-pool configuration;
- app first-load vs warm-load times;
- WebKit compositing environment and process launch time;
- duplicate bridge requests or synchronous network calls during launch;
- large DOM trees and expensive CSS in Home, app drawer, Settings, widgets and status panels;
- long tasks and forced synchronous layouts;
- expensive event handlers on pointer/touch move;
- repeated DOM reconstruction where a cached render is safe;
- full-resolution PNGs that are being downscaled every frame;
- unnecessary animation timers when panels are hidden or screen is off;
- repeated API polling by hidden PWAs.

Do not disable WebKit security, process isolation, sandboxing, JavaScript security or required origin behavior. Do not reduce image quality blindly. Preserve artwork originals, optimize losslessly where possible and size only duplicate runtime assets to their actual display use. Keep color profiles, alpha and crisp edges. Never replace pixel art with blurry resampling.

## 8.4 Native GTK / libadwaita performance

The owner report's approximately 0.48-second GTK number is process spawn, not necessarily first interactive frame. Re-measure separately for at least two native GTK applications. Investigate:

- first library load and dynamic linker cache;
- fontconfig cache validity;
- GIO module and MIME cache state;
- GTK theme/icon theme lookup;
- portal settings and user D-Bus activation;
- session environment propagation;
- GTK4 renderer selection (`GSK_RENDERER`) and actual renderer availability;
- app cold-start vs warm-start behavior.

Do not globally force `GTK_THEME=Adwaita-dark` or `GSK_RENDERER=cairo` just to make the app consistent. Keep theme and renderer settings separate. Fix stale/invalid caches only if proven. Avoid running `gtk-update-icon-cache`, `fc-cache`, `glib-compile-schemas` or other cache builders on every boot; build only when inputs changed.

## 8.5 Systemd / service critical path

Use `systemd-analyze time`, `blame`, `critical-chain`, journals and monotonic timestamps. Determine which units gate the first interactive desktop and which can start after Home. Apply only dependency changes that preserve required readiness ordering.

Candidates for defer/lazy start only if proven noncritical:

- nonessential diagnostics;
- remote/catal og refresh;
- app metadata/icon refresh;
- optional background indexing;
- prewarm work;
- delayed firmware reloads that existing prompts already moved off the initial boot path.

Do not move a required unit later if it causes blank UI, missing touch/audio/network, broken alarms or delayed user input. Prefer systemd timers/path activation/on-demand activation with bounded work and proper dependencies. Keep timeouts specific to the relevant unit; do not shrink global manager timeouts.

## 8.6 CPU, memory, I/O and thermal investigation

Capture:

- per-core frequency policy and actual frequency where exposed;
- CPU idle states and run queue;
- per-process CPU, RSS, faults, context switches;
- memory availability, reclaim, page cache, PSI, zram/swap;
- block-device queue/latency and filesystem free space;
- top system wakeup sources if available;
- battery/charger state and credible temperature sensors.

Do not overclock. Do not disable thermal throttling, thermal zones, watchdogs, battery protections, CPU idle states or kernel safety controls. Do not force the `performance` governor globally. Do not change schedutil, cpuset, uclamp, task affinity, scheduler priorities, `vm.swappiness`, zram, writeback settings, I/O scheduler or dirty ratios without a measured causal problem, a one-change A/B, a thermal/idle check and an exact rollback. The existing `nuxel-perf-tune.sh` historically adjusts flash I/O scheduler and writeback/swappiness settings; inspect whether it is active and whether those settings help the current workload. Do not assume its comments prove benefit.

A sustained UI animation should not hold big cores at high frequency after the animation finishes. Hidden app panels and stopped timers should be idle. Screen-off should return to low-power state without a polling loop.

# 9. Phase 5 — lightweight motion design (beautiful, crisp, cheap)

The owner specifically requests smooth effects and transitions, but not resource-heavy effects. Implement a small motion language and apply it consistently across Nuxel's shell and apps.

## 9.1 Design goals

- Responsive, subtle, polished and intentional.
- Short enough that the UI never feels slower because it is animating.
- Crisp 8-bit/pixel-art visual identity remains intact.
- No giant glow, blur, frosted glass or oversized shadow effects.
- Interactions must remain tappable and cancelable throughout transitions.
- Animation must not block navigation or input processing.
- Motion preference must be respected.

## 9.2 Suggested motion tokens

Treat these as initial candidates, then test and tune on hardware:

| Token | Initial duration | Use |
|---|---:|---|
| `--motion-press` | 80–100 ms | Button/card press feedback |
| `--motion-fast` | 120–150 ms | Tiny menus, tooltips, state chips |
| `--motion-standard` | 160–190 ms | Panels, dialogs, app content transitions |
| `--motion-navigation` | 180–220 ms | Drawer, desktop/workspace transitions |
| `--motion-emphasis` | ≤240 ms | Rare important state changes only |

Use a restrained ease such as `cubic-bezier(0.2, 0.8, 0.2, 1)` for entry and a slightly faster ease for exit. Avoid long overshoot/bounce/spring effects. Avoid an animation continuing after the user has already navigated away.

## 9.3 Good initial effect patterns

Use these only where the relevant element is small and the test shows no repaint storm:

- App/surface entry: opacity 0→1 and very small scale 0.985→1 over approximately 160–190 ms.
- App/surface exit: opacity 1→0 and scale 1→0.99 over approximately 110–150 ms.
- Panel/menu: opacity with translateY of approximately 4–8 CSS px over 130–170 ms.
- Desktop switch: restrained 10–16 CSS px directional slide with opacity over 180–220 ms; do not animate the entire native output if that causes a full-screen repaint storm.
- Button tap: scale 1→0.98→1 over 80–100 ms, with no large shadow interpolation.
- Widget placement: short opacity/translate snap confirmation after the drop; do not continuously animate grid coordinates.
- Keyboard reveal/hide: transform/opacity only if keyboard layout and touch geometry remain correct; never delay key acceptance until the effect completes.
- Progress indicator: one small, low-frequency, determinate or indeterminate indicator, not several full-screen animated elements.

These are visual starting points, not guarantees that CSS transforms are GPU accelerated. Nuxel's graphics stack may still repaint through software. Measure each category on the actual runtime.

## 9.4 Explicitly avoid

- `backdrop-filter: blur()` and `-webkit-backdrop-filter`;
- large animated blur, filter, drop-shadow or glow effects;
- animating `width`, `height`, `top`, `left`, `margin`, `padding`, flex/grid geometry or border width;
- animating large shadows or large gradients;
- full-screen translucent overlay animation when a small panel can be animated;
- perpetual background motion, parallax, starfields or particle systems;
- unnecessary JavaScript `requestAnimationFrame` loops;
- heavy spring physics libraries for simple transitions;
- large GIF/APNG/video assets for UI motion;
- blanket `will-change: transform, opacity` on every hidden panel or every widget;
- `translateZ(0)` everywhere as a magical GPU fix;
- duplicated timers/animation loops left running while hidden;
- any transition that causes missed taps, touch lockout, scroll interception or delayed app launch.

`transform` and `opacity` are generally preferable to geometry-changing CSS properties, but the runtime may not composite them on a hardware GPU. Do not claim off-main-thread or GPU animation without profiling. Use `will-change` only on a specific element immediately before a brief animation and remove it when finished, and only if measured beneficial.

## 9.5 Reduced motion and performance preference

Respect `prefers-reduced-motion` and any existing Nuxel motion/accessibility preference. Add a clear user-facing control if there is no existing setting:

- **Full (subtle)** — default: short transitions described above;
- **Reduced** — only essential opacity/state feedback, minimal duration;
- **Off** — near-instant state changes; no decorative motion.

Optionally provide a **Performance mode** that reduces nonessential animations and expensive effects while preserving essential feedback. Do not conflate reduced motion with lower screen resolution, a renderer change or disabling accessibility feedback.

Persist the preference in the existing settings model. Ensure the preference is applied to PWA CSS, native GTK/libadwaita where supported and Flatpak apps via supported settings integration. Do not globally force environment variables to all toolkits.

## 9.6 Tests

Extend or preserve the repository's `test_butterscotch_perf.py` style checks. The supplied test currently asserts no backdrop blur, no persistent `will-change` on hidden panels, local small nav artwork, no duplicate quick-settings provider calls and small blur radii. Do not weaken this contract to make an animation test pass. Add tests for:

- duration token upper bounds;
- allowed properties for core shell transitions;
- no layout-property animation in critical Home CSS;
- reduced-motion override actually disables/reduces effects;
- hidden panels do not keep running timers;
- transition cancellation on rapid repeated taps/navigation;
- touch and scrolling remain functional during transition;
- no blanket permanent `will-change` declarations;
- no CSS backdrop blur reintroduced by inline JS or dynamically generated CSS.

Do not attempt to ban every use of `filter` blindly if some non-animated static icon use is safe; focus on expensive animated render-path effects and the current no-blur contract.

# 10. Phase 6 — efficient assets and front-end critical path

Inspect large images used in the shell, dock, status, navigation and app drawer. Historical A50 recorded several nav images around 1.0–1.14 MB and dock artwork around 0.9 MB, but current assets must be measured. Create a report of:

- image dimensions and file sizes;
- actual on-screen display dimensions;
- decode/paint frequency;
- whether an asset is repeatedly scaled;
- whether the same file is decoded/copied more than once;
- whether any asset is animated or unnecessarily full-screen.

Optimization rules:

- Keep source originals and provenance.
- Preserve transparency, alpha, colour profile, sharp edges and intended pixel-art look.
- Prefer SVG for simple vector artwork and lossless PNG/WebP where appropriate and supported by the actual WebKit/GTK runtime.
- Do not convert icons to lossy JPEG.
- Do not reduce quality or resolution below actual use requirements.
- Create device-sized derivatives only as separate generated assets and compare visually on the phone.
- Avoid huge CSS background images for tiny elements.
- Lazy-load off-screen gallery/catalogue imagery while keeping critical Home icons immediately available.
- Avoid synchronous decode of large noncritical images during launcher startup.
- Pre-size image slots to prevent layout jumps.

Reduce launch critical-path work:

- do not enumerate remote apps or decode all artwork before Home is responsive;
- lazy-load nonessential Settings sections;
- avoid repeated DOM rebuilds on every tab switch where safe;
- coalesce duplicate status requests;
- do not run hardware probes on every screen open;
- keep event handlers small and avoid long synchronous loops;
- move non-UI work to bounded native async jobs where an existing service pattern supports it;
- prevent hidden pages from polling or animating needlessly.

# 11. Phase 7 — boot and service startup optimization

The repository already contains PWNAGE-51000 evidence that moving a noncritical ABOX firmware reload off the boot-critical path reduced measured boot time substantially in that earlier build. Re-check current boot graph; do not reapply old changes blindly.

Measure:

- kernel time;
- initrd time if available;
- userspace time;
- multi-user target;
- Phoc/Wayland start;
- framebuffer owner readiness;
- PWA host ready;
- lockscreen/Home first visible frame;
- first usable input.

Use systemd dependency graph and journal timestamps. Identify any long-running service that is ordered before the first interactive frame unnecessarily. Defer optional work only when safe and observable. Keep required display, touch, session bus, audio routing, clock/alarm service and input infrastructure available when expected.

Avoid:

- `DefaultTimeoutStartSec` global reduction;
- killing services that appear slow but are required;
- changing systemd target topology without proof;
- replacing a healthy session daemon with a shell script background process;
- turning off service restart/recovery policies;
- masking units to make `systemctl --failed` look clean.

# 12. Phase 8 — benchmark and regression framework

Create or extend a reproducible campaign harness under a suitable `tools/perf/pwnage85000/` path. Reuse existing perf tools and telemetry rather than creating a permanent heavy profiler daemon.

The harness should:

- support baseline and candidate snapshots;
- use monotonic clocks;
- include sample count, p50, p95, min/max and optional p99;
- return structured JSON and Markdown;
- mark unavailable counters as `UNAVAILABLE`, never zero;
- mark interrupted runs as `INCOMPLETE`;
- mark safety-blocked tests as `BLOCKED`;
- detect missing timestamps and inconsistent samples;
- record charging/battery/thermal and Wi-Fi conditions;
- avoid clearing page cache or changing the governor;
- stop sampling after a bounded interval;
- write to evidence directory, not application data directories;
- avoid capturing passwords, cookies, tokens, browser history or private files.

## 12.1 Core performance table

Produce before/after values for:

| Metric | Baseline | Candidate | Acceptance |
|---|---:|---:|---|
| Flatpak lightweight app launch → first frame, warm p50/p95 | Measure | Measure | Aim p50 ≤5 s and materially reduced p95 |
| Flatpak cold first launch → first frame | Measure | Measure | Separate from warm; no hidden 30 s timeout |
| Flatpak first input accepted | Measure | Measure | No unresponsive post-frame interval |
| Native GTK launch → first frame | Measure | Measure | No regression; improve if proven |
| PWA launch → first frame | Measure | Measure | No regression |
| App registry lookup | Measure | Measure | Remove full scan from critical path if present |
| Boot → interactive Home | Measure | Measure | Improve only with verified safe deferral |
| App drawer open | Measure | Measure | Stable, no jank/touch loss |
| Desktop switch | Measure | Measure | Stable and bounded motion |
| Scroll frame intervals | Measure | Measure | Fewer long stalls; no input regressions |
| CPU idle use, screen-on | Measure | Measure | No new permanent background load |
| CPU idle use, screen-off | Measure | Measure | No regressions / no polling loop |
| Memory available / pressure | Measure | Measure | Maintain headroom; no OOM |
| App-prewarm RSS and CPU | Measure | Measure | Benefit must outweigh cost |
| Thermal/battery trend | Measure | Measure | No adverse trend |

## 12.2 Flatpak acceptance gate

The reported ~30.7-second delay must be explained and addressed. Target for a lightweight representative app:

- warm launch-to-first-interactive-frame **≤5 seconds** where the measured app/runtime/device path permits;
- if a hardware/runtime floor prevents that target, achieve at least 70% reduction in the unexplained delay, identify the remaining measured segment and provide the evidence;
- no 25–30 second unexplained timeout remains hidden;
- no app is reported ready before its actual window/first frame;
- no security sandbox weakening;
- app runs as the intended user, with working Wayland input and user D-Bus;
- portal integration remains correct for supported features;
- no theme regression.

A different heavy Electron app may have a larger startup floor. Report it separately; do not let that app mask the basic runtime launch result.

## 12.3 System acceptance gate

- common Home/shell interactions feel faster or at least no slower;
- no new long-frame stalls;
- no regression in touch handling, display updates, screen sleep or wake;
- no extra background CPU loop;
- no OOM/reclaim thrash under app switching;
- no excessive residual process count after apps close;
- no thermal or battery regression;
- native GTK, PWA and Flatpak app launches all remain functional;
- no crash or black window in selected apps.

# 13. Phase 9 — implementation order and experiment discipline

Execute in this order. Do not implement all candidates in one giant patch.

## E0 — baseline / no-change control

- Reconnect over Wi-Fi SSH.
- Capture current state and hashes.
- Reproduce Flatpak 30.7 seconds.
- Capture per-phase timing.
- Measure native GTK/PWA baseline.
- Capture current renderer environment and UI frame data.
- Preserve the evidence before moving on.

## E1 — remove avoidable launch-path inventory work

If the live provider enumerates system/user Flatpak apps and resolves icons on every launch, implement a coherent installed-ref cache. Prove it shortens T0–T3. Ensure install/update/uninstall invalidation. Add unit tests for stale cache, missing app, newly installed app, transaction races and corrupt cache. This change must not affect the actual Flatpak runtime or sandbox.

## E2 — diagnose/fix exact D-Bus / systemd / bwrap wait

Make the smallest change that removes the proved wait. Examples only if evidence supports them:

- fix wrong user-bus or runtime-dir path/ownership;
- correct portal activation/session readiness;
- remove duplicate portal/session-bus activation;
- fix transient unit environment or unnecessary manager queue wait;
- prevent an app launch from waiting on an unrelated portal call;
- correct Flatpak system/user installation selection;
- remove a stale broken override that triggers an actual timeout.

Do not change portal backend routing, environment or services on speculation. Test all supported portal behaviors that the phone uses after a change.

## E3 — per-app renderer policy

Measure current forced llvmpipe/Cairo path. Introduce per-app verified policy only where evidence proves the alternative works. Retain software fallback where required. Add diagnostics and tests. Compare launch-to-first-frame and scrolling/render CPU separately.

## E4 — prewarm/caching decision

Compare with and without prewarm under similar conditions. Preserve only proven benefit. Implement metadata/cache-first approach. Check memory pressure and idle power.

## E5 — UI/render-path optimization

Profile Home, drawer, Settings, panels, widgets and app switching. Remove only proven expensive work. Maintain layout/touch correctness. Optimize assets losslessly and visually verify on device.

## E6 — measured service/boot tuning

Defer only safe noncritical work, based on systemd timing and critical path. Reboot only if needed and only after recovery/rollback is verified. The mission's default is no reboot unless a config/service change explicitly requires it and the live evidence says it is safe.

## E7 — motion language

Add short, subtle, transform/opacity-focused effects. Run reduced-motion tests. Measure CPU/frame pacing during animations. Tune or remove any effect that causes jank. Do not put decorative animation ahead of launch latency.

## E8 — complete regression and soak

- Re-run all targeted tests.
- Run the broader relevant repository test suite.
- Run actual Flatpak launch matrix.
- Verify app close and relaunch.
- Verify app switch / Home / desktop transitions.
- Check native GTK and PWA launches.
- Verify screen-off / wake / idle.
- Verify sound/alarm/clock services remain active.
- Run a bounded 15–30 minute soak with representative light use if safe; monitor thermal and memory trend.
- Ensure no service failure, crash loop or unexpected background process.

# 14. Security, stability and do-not-do list

This mission does not authorize weakening the Nuxel security model.

**Never do these as a performance shortcut:**

- `flatpak run --no-sandbox` or equivalent;
- disable user namespaces, mount namespaces, PID namespaces or seccomp;
- mark bubblewrap setuid or add ambient capabilities as a launch hack;
- `flatpak override --filesystem=host`;
- `flatpak override --device=all`;
- expose all of `/dev`, `/proc`, `/sys`, home or root to every app;
- run GUI apps as root;
- disable AppArmor, SELinux, polkit or D-Bus authentication globally;
- turn off sandbox process isolation;
- clear all Flatpak overrides without an audit;
- blindly set global `GTK_THEME`, `GSK_RENDERER`, `LIBGL_ALWAYS_SOFTWARE` or Mesa variables;
- make llvmpipe the only renderer on all apps without measuring;
- assume `/dev/mali0` implies the Flatpak runtime can use Mali EGL;
- fake GPU acceleration by reading renderer strings without confirming the active drawing path;
- keep all apps prewarmed or leave hidden GUI processes running;
- globally set max CPU frequency or disable thermal controls;
- overclock, undervolt or change kernel/bootloader/DTB/initramfs;
- replace the working `nuxel-wl-fb` binary using a stale source tree;
- run two framebuffer writers;
- change panel resolution/scale without a real readability/touch A/B;
- add a heavy animation framework or permanently promote every UI node to a compositor layer;
- optimize a benchmark while degrading touch, audio, alarms, Wi-Fi or idle battery.

# 15. Tests to add/update

At minimum, cover:

## Flatpak provider

- `launch_argv()` does not run a full package inventory on every launch if a verified cache exists.
- Cache miss rebuilds once and handles timeout/failure cleanly.
- install/uninstall/update invalidates cache.
- app ID validation remains strict.
- app removed between cache and launch returns a truthful failure.
- app architecture and scope selection remain correct.
- app launch executes under the real `nuxel` UID/GID and expected session environment.
- no shell injection or `shell=True` is introduced.
- timeout phase is reported distinctly.
- system-scope install transactions remain separate from user-scope GUI launch.
- renderer policy is app-specific and defaults to a tested safe mode.
- no broad sandbox grants appear in manifests or overrides.

## Services / startup

- prewarm only starts a bounded, intentional job;
- no hidden application process is retained by default;
- service has a timeout, resource limits appropriate to its work and clear logging;
- noncritical refreshes do not gate app launch or Home readiness;
- screen-off stops nonessential polling/timers.

## UI/motion

- all core transition durations are within budget;
- no core transition animates geometry/layout properties;
- no backdrop blur;
- hidden panels do not retain `will-change`;
- reduced-motion preference actually reduces motion;
- performance mode disables nonessential effects;
- repeated fast taps cancel/reconcile transitions without input lock;
- no gesture/touch regression;
- app drawer and desktop switch remain correctly aligned;
- no panel steals touch while transitioning out.

## Regression

Run all relevant existing suites, including the existing Butterscotch performance guard (`tests/pwnage37000/test_butterscotch_perf.py` or its current renamed successor), launcher/desktop layout tests, Flatpak provider tests, app manager tests and service tests. Update obsolete assertions only when the underlying intended contract has actually changed; do not simply weaken them.

# 16. Deployment plan and rollback

## 16.1 Before deployment

- Confirm Wi-Fi SSH still works in a second terminal or reconnection path if feasible.
- Confirm host key and root access.
- Create timestamped backup of every changed file, directory and unit.
- Record SHA-256 of pre-change live binaries/config/source.
- Preserve user Flatpak overrides, system Flatpak overrides and installation metadata.
- Preserve Flatpak app data and runtime refs; do not remove/reinstall apps as an optimization shortcut.
- Prepare a script or exact commands to restore prior provider, session config, service units, UI assets and settings.
- Ensure rollback does not depend on the changed bridge or app UI being functional.

## 16.2 Deploy incrementally

- Deploy one logical experiment at a time.
- Validate file owner, mode, syntax, imports and service-unit verification before restart.
- Restart only the smallest affected service.
- Avoid restarting Phoc/Wayland or `nuxel-wl-fb` unless absolutely required by the change and explicitly planned.
- Do not reboot just to make a test pass.
- After each deployment, check `systemctl --failed`, process tree, logs, window presentation and Wi-Fi SSH survival.

## 16.3 Rollback conditions

Rollback the experiment immediately if any of these occur:

- Flatpak sandbox fails or becomes less isolated;
- app starts as root or wrong user;
- display black screen, Phoc crash, framebuffer owner violation or `decon_pan_failed` appears;
- touch or keyboard input is lost;
- app window appears but is unresponsive;
- audio/clock/alarm/microphone services regress;
- memory pressure/OOM rises materially;
- screen-off CPU use/wakeups increase unexpectedly;
- temperature or battery drain materially worsens;
- more than one representative app regresses without a documented app-specific exception.

Keep the existing PWNAGE-84000 backup and prior rollback points intact. Create a new independent PWNAGE-85000 backup; do not overwrite the PWNAGE-84000 restore point.

# 17. Required evidence and final engineering report

Write:

```text
docs/pwnage-85000/evidence/<UTC_TIMESTAMP>/ENGINEERING-REPORT.md
```

Also create, as appropriate:

```text
BASELINE.md
FLATPAK-TIMELINE.md
FLATPAK-APP-MATRIX.md
RENDERER-POLICY.md
WHOLE-DEVICE-PERFORMANCE.md
ANIMATION-PROFILE.md
THERMAL-IDLE-REPORT.md
ROLLBACK.md
baseline.json
candidate.json
flatpak-launches.csv
SHA256SUMS
```

The report must contain:

1. Connection and root verification (never the private key content).
2. Actual phone/kernel/OS identity and current repo commit.
3. Pre-change service, process and deployment map.
4. Exact reproduction of the ~30.7-second stall or a clear reason it could not be reproduced.
5. Timestamped phase-by-phase Flatpak launch trace.
6. Proven root cause, competing hypotheses ruled out, and exact code/config fix.
7. Renderer policy experiments per app, including failures and safe fallback.
8. Before/after first frame and first input p50/p95.
9. Native GTK and PWA before/after results.
10. App-prewarm benefit/resource accounting and keep/remove decision.
11. Boot/systemd and whole-device latency changes.
12. CPU/memory/I/O/frame/thermal/idle measurements.
13. Motion effects added and reduced-motion behavior.
14. Automated test results and physical touch/visual acceptance.
15. All modified paths, deployed hashes, units restarted and package/runtime changes.
16. Exact backup path and tested rollback method.
17. Remaining limitations, honestly labeled `NOT_TESTED`, `BLOCKED`, `REGRESSION` or `NEEDS_OWNER_TEST`.

A file existing or a unit being `active` is not proof that its feature works. The report must distinguish:

- `IMPLEMENTED` — source exists;
- `DEPLOYED` — expected version is on the phone;
- `AUTOMATED_TESTED` — deterministic tests pass;
- `VERIFIED_ON_DEVICE` — real app/window/input behavior was confirmed;
- `NEEDS_OWNER_TEST` — requires owner interaction/visual judgement;
- `BLOCKED` — specific dependency or safety reason prevents a test.

# 18. Physical acceptance checklist

Perform real touch verification for the following with the owner available or by an existing trusted input/display validation workflow. Do not invent owner interaction.

- [ ] A lightweight Flatpak app appears quickly, receives input immediately and closes cleanly.
- [ ] A second GTK Flatpak app starts without the unexplained 30-second delay.
- [ ] Vesktop and Legcord still open if installed; login state is untouched.
- [ ] Native GTK app opens promptly and dark appearance remains correct.
- [ ] PWA launches and Home/app drawer remain responsive.
- [ ] App drawer opens, scrolls and launches deliberately tapped apps.
- [ ] Desktop switch effect is smooth, short and does not swallow touch.
- [ ] Quick Settings and Settings open/close without lag.
- [ ] Keyboard opens and dismisses normally; keys remain responsive during transitions.
- [ ] Widget movement/resizing remains correct.
- [ ] No large blur/glow or excessive effect has been introduced.
- [ ] Reduced-motion and performance settings work.
- [ ] Repeated app open/close does not leak processes or memory.
- [ ] Lock screen and screen-off idle remain low-activity.
- [ ] Wake from screen-off is responsive.
- [ ] Sound, microphone, Clock alarms and timer remain functional.
- [ ] Wi-Fi SSH remains connected or reconnectable.
- [ ] No new failed systemd units or crash loops.

# 19. External references and how to use them

Use these references as technical guidance and check the exact behavior against the versions installed on Nuxel. They do not replace local tracing.

- **Flathub troubleshooting:** <https://docs.flathub.org/docs/for-users/troubleshooting/> — recommends collecting terminal launch output, Flatpak version/app info, app permissions and user/system overrides before changing them. It warns against broad filesystem grants as a generic remedy.
- **Bubblewrap:** <https://github.com/containers/bubblewrap> — describes mount/user/IPC/PID namespaces and the sandbox's filesystem boundary. Preserve the namespace model; do not remove it to improve speed.
- **systemd-analyze:** <https://freedesktop.org/software/systemd/man/latest/systemd-analyze.html> — use `time`, `blame`, `critical-chain` and `plot` appropriately. `blame` alone does not establish a causal dependency wait.
- **CSS performance:** <https://developer.mozilla.org/en-US/docs/Web/Performance/Guides/Animation_performance_and_frame_rate> and <https://developer.mozilla.org/en-US/docs/Learn_web_development/Extensions/Performance/CSS> — prefer properties that avoid repeated layout; `transform`/`opacity` can be efficient, but animation cost depends on the rendering stack. Respect reduced motion and avoid unnecessary layers.
- **Phoc:** <https://manpages.debian.org/experimental/phoc/phoc.1.en.html> — environment/debug options are version-sensitive. Check the installed Phoc/wlroots version and build before using any flag; do not paste current upstream variables into this older/possibly vendor-patched stack blindly.

# 20. Definition of done

PWNAGE-85000 is complete only when all of the following are true:

1. The unexplained Flatpak delay has a trace-backed root cause and a deployed fix, or a narrowly identified external blocker with a tested mitigation.
2. At least one lightweight representative Flatpak app shows a substantial measured launch-to-first-frame improvement; target warm first-interactive-frame ≤5 seconds where feasible, otherwise ≥70% reduction in the unexplained delay with evidence.
3. A second app confirms the fix is not a one-app accident.
4. Sandboxing, user identity, D-Bus, portal behavior and app permissions remain correct.
5. The global forced-software policy has been audited and replaced with a verified per-app policy only where safe; no unsupported GPU claim is made.
6. Prewarm is justified by measured benefit and cost, or removed/reduced in favor of efficient metadata caching.
7. Whole-device interaction metrics are improved or documented as hardware-limited without regressions.
8. New transitions are subtle, consistent, low-cost, touch-safe and accessible through reduced-motion settings.
9. The phone stays stable, thermally safe, responsive, and functional across existing core services.
10. Evidence, hashes, tests, physical verification and rollback are all documented.

**Final instruction:** this is a full engineering execution mission. Connect over Wi-Fi SSH with the specified key, inspect the live device and repository, find the real 30-second Flatpak wait, fix it, optimize the broader phone based on measured bottlenecks, add restrained Nuxel motion, deploy safely, test on the actual S10+, and write the complete evidence report. Do not stop after diagnosis, do not substitute generic prewarming for a root-cause fix, do not weaken sandboxing, and do not trade battery, thermals or reliability for a synthetic performance number.
