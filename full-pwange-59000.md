# FULL PWNAGE 59000
## Nuxel S10+ display pipeline, launcher geometry, independent app drawer, Settings responsiveness, and a working Fedora Software centre

**Mission type:** implementation, repair, profiling, regression coverage, and on-device verification  
**Target device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820 / universal9820)  
**Target userspace:** Nuxel Fedora ARM64 phone image; the current build tree is Fedora 43-oriented, but always verify the installed target release before writing repository configuration  
**Primary source tree:** this repository, especially `tools/s10plus/`, `images/s10plus/`, `services/`, and `pwa/`  
**Required output:** working code changes, tests, device evidence, rollback instructions, and a concise completion report

---

# 0. Your assignment

You are not being asked for an architecture proposal or a list of suggestions. You are being asked to **inspect, implement, test, and document** a complete repair of the following Nuxel phone experience:

1. Establish the real live display pipeline and find the best safe way to reduce rendering work without damaging the S10+ panel geometry, text quality, touch mapping, rotation, or boot/recovery reliability.
2. Fix desktop/home grid settings so the advertised desktop columns and rows are what the phone actually renders. The user currently sees three desktop app columns even though Home Settings says four columns and five rows.
3. Give the app drawer its **own independent columns and rows settings**. Changing the drawer must not change the desktop grid, desktop icon size, per-app icon size, dock, page capacity, or desktop layout. Changing the desktop must not change the drawer.
4. Expose these settings coherently in both the existing Home Settings UI and the main Settings app. There must be one source of truth; the two screens must stay synchronized.
5. Make Settings feel immediate. Do not perform every hardware, location, graphics, and developer probe just because the Settings app opened. Load the data for the selected tab, reuse it, and stop background polling when the user leaves a tab or the app is hidden.
6. Repair the Software app so that searches return actual packages from configured official Fedora repositories, package metadata is available, and installing/removing packages is safe and usable. Do not confuse this app with NuXtore, which is a separate Nuxel bundle/catalog feature.
7. Add meaningful automated tests and collect actual on-device measurements. No fabricated performance claims and no “looks fixed on my desktop” acceptance.

**Implement this in the repository.** Make the appropriate source, image-builder, test, and documentation changes. Do not stop after producing a plan. If a required physical test cannot be performed from your current environment, implement all safe code-side work, provide a precise device-side test/deploy script or command set, and mark only the unperformed physical acceptance items as unverified.

The end state should feel like a responsive phone UI, not a desktop stack that happens to fit on a phone.

---

# 1. Verified repository truth — start here

These findings are based on the source tree and its existing engineering notes. They are a starting point for investigation, not permission to assume the phone currently has the same live state. Capture the actual device state before changing anything.

## 1.1 The S10+ has several different “resolutions”

The project has at least four resolution layers. Keep them separate in code, logs, tests, documentation, and your report.

| Layer | Known S10+ portrait value | Meaning |
|---|---:|---|
| Physical AMOLED / framebuffer scanout | `1440×3040` | The phone panel. It remains the physical output target. |
| Phoc headless output / compositor buffer | `720×1520` | The current source-buffer mode in the shipped phone configuration. |
| Phoc logical / Wayland / CSS viewport | `360×760` | The application coordinate space when the output scale is 2. |
| Framebuffer bridge output | `1440×3040` | The bridge converts/upscales the compositor image for the physical framebuffer. |

The active phone configuration in `tools/s10plus/a29/phoc-phone.ini` currently specifies:

```ini
[output:HEADLESS-1]
mode = 720x1520
scale = 2
```

The image builder installs this to `/etc/nuxel/phoc-phone.ini`. The active Wayland service in `services/nuxel-session/systemd/nuxel-wayland.service` starts Phoc with that configuration. The normal logical phone viewport is therefore `360×760` in portrait. Do not describe the phone as “rendering at 1440×3040” without qualifying which layer you mean.

The S10+ display notes in `docs/performance/A50/02-DISPLAY-RESOLUTION-AND-RENDERING-TRUTH.md` record `/dev/fb0` at 1440×3040, 32 bits per pixel, stride 5760 bytes, with a virtual Y size of 6080 for double buffering. The live device must be queried again; documentation is not a substitute for runtime evidence.

## 1.2 The framebuffer bridge is the real scanout boundary

The active bridge source is `tools/s10plus/a67/nuxel-wl-fb.c`. The S10+ builder compiles and installs this source as `/usr/lib/nuxel/nuxel-wl-fb`.

Important implementation facts to verify against the current checked-out source:

- The current optimized fast path handles exact 2× horizontal and vertical enlargement. The A67 source contains an NEON-oriented row expansion path for the established `720×1520` to `1440×3040` mapping.
- The general integer enlargement path can map an integer-sized compositor image to the physical framebuffer using an X coordinate map and a reusable row buffer, and can repeat rows vertically. This suggests that `360×760` to `1440×3040` (4× in each dimension) is technically representable by the generic path.
- The generic 4× path is not the same as the existing optimized 2× path. Measure it. If it becomes the preferred profile, consider a correctly tested 4× fast path; do not assume it will be faster simply because the input buffer has fewer pixels.
- The bridge still has to write the physical framebuffer. A smaller compositor buffer does **not** make the final 1440×3040 panel disappear. The fixed scanout/conversion/present work may dominate.
- Preserve damage tracking, unchanged-frame skipping, colour conversion, framebuffer stride handling, and single-writer ownership. Do not replace the bridge with an uncontrolled second framebuffer process.

The older A50 performance baseline in `docs/performance/A50/A50-BASELINE.json` and associated reports is dated 2026-10-22 and describes an earlier measurement state. It reports high CPU use and slow changed-frame blits, but those numbers are **historical**, not confirmed current A67 performance. Do not repeat them as current measurements. Take a fresh baseline from the exact build/device being tested.

## 1.3 Why the two resolutions suggested by the user are not the right S10+ modes

The S10+ portrait panel ratio is `1440:3040`, or approximately `9:19`.

- `720×1280` and `1080×1920` are `9:16` modes. They do not preserve the phone panel’s aspect ratio. They require cropping, stretching, letterboxing, or a different layout. Do not silently introduce one of those effects.
- `1080×1920` contains approximately 2.074 million source pixels, versus approximately 1.094 million for `720×1520`. It is about 89.5% more pixels than the current compositor buffer. It is not a performance-downscale from the current mode.
- `720×1280` contains fewer pixels than the current compositor buffer, but the aspect ratio is wrong and it is not a faithful full-panel S10+ mode.
- `360×760` preserves the portrait aspect ratio and has the same 360×760 logical dimensions at scale 1. It has one quarter of the pixel count of 720×1520, theoretically reducing compositor raster work by 75%. However, it removes the current 2× supersampling and the general bridge path may be slower per output pixel than the current NEON 2× implementation. Text and edge quality may be worse.
- `540×1140` also preserves the aspect ratio, but scale 1.5 is fractional. The orientation code and integer output scale assumptions must be checked before treating it as a valid Phoc profile. Do not introduce fractional scale casually.

**Default policy:** keep `720×1520`, scale 2, as the safe fallback until a complete on-device A/B test proves another mode better. The first low-resolution experiment should be `360×760`, scale 1, in portrait, because it preserves the current logical coordinate dimensions. It is an experiment, not a guaranteed default.

## 1.4 Rotation is a hard constraint, not an afterthought

Inspect `services/nuxel-orientation/nuxel_orientation/apply.py` and its tests. The current policy uses portrait scale 2 and landscape scale 1. Existing comments describe the `720×1520` mode producing a 360×760 portrait logical viewport and a 1520×720 landscape logical viewport after the intended transform/scale arrangement.

If the portrait mode is changed to `360×760`, scale 1, do not assume landscape continues to expose 1520×720 logical coordinates. It may instead expose 760×360. That would change app layout and touch mapping in landscape. Work out how the selected physical mode, transform, integer scale, and logical viewport interact for every supported rotation.

You must preserve all supported portrait/landscape orientations and their touch calibration. If no safe per-orientation solution exists, keep the current mode as default and report the lower-resolution profile as an unpromoted experiment. A benchmark that works only in portrait is not a complete display fix.

## 1.5 Current graphics strategy is deliberately conservative

Inspect `configs/nuxel/graphics/graphics-profile.json`, `tools/s10plus/a45/nuxel-graphics-profile`, the S10+ session startup, and the actual process environment.

The current graphics profile defines a conservative software-safe path. The repository also documents a `gpu-rendered-shm-presented` experimental route and unavailable/unsupported DMA-BUF or fully accelerated paths on the present WebKit/DRM stack. The source notes mention WebKit 2.54.1, missing `drmMainDevice` / `CONFIG_DRM_VGEM` conditions, and no normal `/dev/dri` route in the recorded environment. Verify the exact live kernel and runtime rather than treating those older observations as immutable truth.

Do not flip every GL/Mali variable, disable the software fallback, or claim hardware composition because a process can create an EGL context. A valid GPU experiment must prove the actual UI process is using the intended renderer, the frame is presented correctly, it survives screen sleep/wake and rotation, and there are no silent fallbacks or visual corruptions.

## 1.6 Launcher and app drawer currently share geometry

Primary implementation:

- `pwa/nuxel-home/js/launcher.js`
- `pwa/nuxel-home/js/home-settings.js`
- `pwa/nuxel-home/js/layout-model.js`
- `pwa/nuxel-home/css/launcher.css`
- `pwa/nuxel-home/index.html`
- `pwa/nuxel-home/sw.js`

The current launcher defaults include `gridColumns: 4` and `gridRows: 5`. `_applyLayout()` sets the `--home-columns` CSS variable and calculates desktop capacity from the columns × rows. The desktop app grid uses `.app-list`.

The drawer container is created with both `app-list` and `drawer-list` classes. The generic `.app-list` CSS uses `--home-columns`, so the drawer inherits desktop geometry. It does not have a truly independent grid configuration. That is a confirmed coupling defect.

Home Settings currently exposes home/desktop grid rows and columns, but no independent drawer dimensions. The user reports seeing three desktop columns while the screen says four columns and five rows. The current source’s default and normal CSS suggest four, so **do not claim the exact cause of the three-column live display without observing it**. Investigate localStorage migration, stale service worker/cache, computed styles, media overrides, actual viewport dimensions, and the currently deployed build. There is a separate three-column system-navigation rule in shared styling; do not mistake it for the desktop app grid.

The launcher persists layout data under `nuxel.launcherLayout` and app ordering under `nuxel.appOrder`; app sizes are separate. `_applyLayout()` currently clamps the home grid. `updateHomeSettings()` validates settings but does not safely repack all existing page assignments when grid capacity changes. Fix this without losing apps, folders, order, or desktop selection.

The dock has its own variable/setting and must remain independent. Per-app and general icon sizing are also separate and must not be changed by a columns/rows update.

## 1.7 Settings starts too much work too early

Primary implementation:

- `pwa/nuxel-apps/settings/index.html`
- `pwa/nuxel-apps/settings/settings.js`
- `pwa/nuxel-apps/settings/hardware-settings.js`
- `pwa/nuxel-apps/settings/location-maps.js`
- `pwa/nuxel-apps/settings/pwange45000-settings.js`
- `pwa/nuxel-apps/settings/driver-diagnostics.js`
- `pwa/nuxel-apps/settings/graphics-diagnostics.js`
- supporting bridge and settings modules in the same directory

There are many tabs. The current Settings startup path performs work that belongs to hidden tabs. Source-level findings include:

- `loadRotation()` runs on initial load.
- Startup configuration loads are chained serially (`loadZonesDoc()`, `loadButtons()`, `loadBoot()`, haptics document/render work), so one slow call can delay later initialization.
- Developer status refreshes multiple bridge state keys, duplicates at least one read, and has a 15-second timer even when the user is not looking at Developer settings.
- Hardware settings boot eagerly retries bridge readiness and starts Bluetooth, device, display, and audio refreshes even when their tabs are not active.
- Location/maps binding eagerly renders/refreshes location before the user opens that tab; its interval must also respect app visibility.
- Power data is loaded eagerly and again when the Power tab is selected.
- A hidden tab does not mean its JavaScript modules or eager bridge operations are inactive.

The first Settings screen should appear without waiting for Bluetooth, GPS, display enumeration, audio controls, diagnostic probes, developer status, or Software metadata.

## 1.8 Software is a custom GTK application backed by PackageKit

Relevant files:

- `services/nuxel-software/nuxel-software` — custom GTK application.
- `services/nuxel-bridge/src/software_provider.py` — Software/bridge status reporting.
- `pwa/nuxel-apps/settings/pwange45000-settings.js` — Settings Software status panel.
- `pwa/nuxel-common/app-registry.json` — application identity and native executable.
- `images/s10plus/build-phone-rootfs-inside-fedora.sh` — installs native Software app and packages.
- `images/s10plus/packages-manifest.json` — declared packages.
- `tools/s10plus/a33/verify-packages.py` — repository URL policy used by the builder.

The application registry maps the Software app to `/usr/lib/nuxel/nuxel-software`, described as Fedora RPM via `pkcon` and polkit. NuXtore is a separate offline Nuxel app-bundle catalog. Keep those roles separate.

Confirmed risks in the current custom GTK app:

- `_run()` uses synchronous `subprocess.run()` from GTK UI callbacks. A repository refresh or package search can block the UI for a long time.
- Search is run on `SearchEntry.activate` rather than a debounced asynchronous request.
- Output parsing assumes semicolon-separated rows with a fixed field shape. Ordinary `pkcon` output may be human-readable/status text or a different structure. This can cause a false empty result list.
- Package IDs are split at a dot, potentially corrupting RPM PackageKit identifiers.
- Exit status, stderr, metadata freshness, no repositories, backend not running, and genuine no-results conditions are not represented distinctly enough.
- Install/remove operations must also not block the GTK main loop.

The image builder creates temporary build-time DNF repository configuration under `/tmp/nuxel-repos` for build operations. That does **not** prove that the resulting phone root filesystem has working persistent `/etc/yum.repos.d/*.repo` files. Check the actual rootfs and actual device.

`tools/s10plus/a33/verify-packages.py` contains the repository’s official Fedora 43 AArch64 Fedora release and updates URLs. The source currently uses the standard official release/updates channels. The image manifest includes PackageKit-related components, Fedora release support, GNOME Software-related dependencies, and AppStream pieces; verify the actual files and services installed in the target.

The current bridge `software_provider.py` checks for some native package tools but may report native package support ready without proving `pkcon`, PackageKit’s D-Bus service, enabled repositories, or usable metadata. Make health reporting truthful without triggering a costly metadata refresh on every status call.

---

# 2. Safety and change-control rules — mandatory

This task is userspace/display/UI/software-store work. Do not turn it into an experimental kernel flashing exercise.

1. **No bootloader, partition, recovery, modem, firmware, or kernel flashing.** Do not use Odin, Heimdall, fastboot, raw `dd` to block devices, or repartitioning commands. Do not modify DTBs, boot images, vendor firmware, or recovery partitions as part of this task.
2. Do not change the physical panel mode to pretend a lower-resolution mode is a panel-native mode. Keep the framebuffer geometry at the actual device-reported 1440×3040 unless live hardware evidence proves otherwise.
3. Do not set `720×1280` or `1080×1920` as the S10+ display mode. They have the wrong panel aspect ratio.
4. Do not disable package signature checking, GPG verification, polkit, SELinux, sandboxing, or system security to make a feature appear to work. Never use `gpgcheck=0`, `--nogpgcheck`, or an equivalent trust bypass.
5. Do not install a second process that writes `/dev/fb0`. Preserve one authoritative framebuffer bridge and its systemd lifecycle.
6. Do not alter touch calibration/mapping without verifying the full rotation matrix and all touch corners on the physical phone.
7. Do not change icon size when fixing grid dimensions. Columns/rows and icon scale are distinct controls.
8. Do not make NuXtore impersonate Fedora Software or present a local-only catalog as a working online package repository.
9. Do not install third-party RPM repositories as a shortcut. Start with official Fedora release and updates only. Add no RPM Fusion, COPR, random mirrors, or untrusted repositories in this task.
10. Do not run a full repository refresh on each keystroke or every time Settings opens.
11. Do not perform a real package install/remove as an unannounced test. The UI must retain an explicit confirmation step for every package transaction. Use mocked tests and read-only real search/metadata checks unless the device owner explicitly authorizes a test installation.
12. Make a backup of each modified device-side config before deployment. Keep a known-good display config and rollback command available over SSH before testing a new display mode.
13. Keep SSH/LAN/ZeroTier administration reachable. Do not replace working network, login, or shell configuration as part of this task.
14. Avoid unrelated UI redesigns, broad dependency replacement, framework rewrites, or unbounded refactors. Fix the real faults with the smallest maintainable architecture.
15. Report every test as `PASS`, `FAIL`, `NOT RUN`, or `BLOCKED`. Never label unperformed physical work as passed.

If deployment is available, use the existing Nuxel deploy/debug workflow and transport chosen by the owner. Do not assume USB or Wi-Fi is available without checking. Prefer a reversible staged deployment over overwriting a working root filesystem.

---

# 3. Phase A — establish an exact, reproducible baseline

Before changing code, capture the repository and phone state. Save evidence in a new directory such as:

```text
docs/pwnage59000/evidence/<UTC-or-local-timestamp>/
```

Do not put secrets, Wi-Fi passwords, private keys, access tokens, or personal data into committed evidence. Redact them from logs.

## 3.1 Source/build identity

Record:

- Git commit, branch, dirty-tree state, and diff summary.
- Nuxel image/release version from the rootfs and app manifests.
- S10+ builder revision and hashes of the active display configuration, bridge binary, bridge source, orientation policy, graphics profile, launcher JS/CSS, Settings JS, and Software executable.
- Fedora release and architecture from the target, not only from the build host.
- Current service files and relevant systemd drop-ins.

## 3.2 Live display inventory

On the actual S10+ collect, where supported:

```sh
uname -a
cat /etc/os-release
rpm -E '%{fedora} %{_arch}' 2>/dev/null || true
cat /etc/nuxel/phoc-phone.ini
wlr-randr --json 2>/dev/null || wlr-randr 2>/dev/null || true
fbset -i 2>/dev/null || true
cat /sys/class/graphics/fb0/virtual_size 2>/dev/null || true
cat /sys/class/graphics/fb0/bits_per_pixel 2>/dev/null || true
cat /sys/class/graphics/fb0/stride 2>/dev/null || true
cat /run/nuxel-wl-fb.state 2>/dev/null || true
cat /run/nuxel-wl-fb.orientation 2>/dev/null || true
systemctl status nuxel-wayland.service --no-pager 2>/dev/null || true
systemctl status nuxel-wl-fb.service --no-pager 2>/dev/null || true
ps -eo pid,comm,args | grep -E 'phoc|nuxel-wl-fb|nuxel-home|WebKit|webkit' | grep -v grep || true
```

Use the appropriate available commands if a particular utility is absent. Capture actual framebuffer dimensions/stride via the bridge’s own verified status/diagnostic interface or ioctl if the kernel exports them. Do not invent a `stride` sysfs file if none exists.

Also record:

- Phoc output mode, scale, transform, refresh rate, and logical dimensions.
- bridge input and panel output dimensions, source format, destination format, stride, scale factor, damage behaviour, present-skip counters, and error state.
- orientation service state and current transform.
- touch input device identity, calibration/matrix, and mapped output.
- current thermal status and available CPU frequency/governor information, using non-invasive read-only sources.
- memory pressure and whether the UI is swapping or under reclaim pressure.

**Important:** distinguish the actual active config from the source template. Prove the path from source file → image-builder install → installed file → running service command line.

## 3.3 Live graphics inventory

Record the current `nuxel-graphics-profile status` / `check` output if those commands exist in this build, the effective environment of the compositor and app/WebKit process, Mali/EGL availability, DRM nodes, loaded drivers, and any fallback reason. Inspect the *actual app process*, not only the shell’s environment.

Do not assume that an EGL library being installed proves the UI is GPU-rendered. Establish whether GTK/WebKit selects the renderer and whether the bridge still copies through system memory.

## 3.4 Live launcher evidence

On the device, before editing:

1. Open Home Settings and record displayed desktop columns/rows.
2. Count actual desktop columns and rows on the rendered home page.
3. Open app drawer and count its columns and displayed rows.
4. Capture portrait screenshots and, if supported, landscape screenshots.
5. Read the actual `nuxel.launcherLayout`, `nuxel.appOrder`, and app-size keys (redact app metadata if necessary).
6. Record current service-worker controller, cache version, script URLs, manifest version, and app asset hashes.
7. From the actual rendered desktop and drawer elements, record `getComputedStyle(...).gridTemplateColumns`, CSS custom properties, element dimensions, icon dimensions, and viewport size.

Inspect whether old localStorage values, old SW clients, a deployed old asset bundle, a CSS override, or a viewport/media rule explains why the user sees three columns while the settings screen says four. Repair the actual cause; do not just change the displayed number.

## 3.5 Live Settings evidence

Measure from Settings icon tap/open to:

- the first stable visible Settings frame;
- the first usable control;
- the first selected-tab data being usable;
- switching between already visited tabs;
- first opening expensive tabs such as Bluetooth, Location, Graphics, Software, and Developer.

Record bridge request count and timing during initial launch. Use DevTools/remote inspector if available, otherwise add a temporary, opt-in diagnostic logger that can be removed or kept disabled by default.

## 3.6 Live Software/repository evidence

On the target inspect:

```sh
rpm -E '%{fedora}'
rpm -E '%{_arch}'
command -v dnf dnf5 pkcon rpm appstreamcli 2>/dev/null || true
pkcon backend-details 2>&1 || true
pkcon get-roles 2>&1 || true
dnf repolist --enabled 2>&1 || dnf5 repolist --enabled 2>&1 || true
ls -la /etc/yum.repos.d/ 2>/dev/null || true
systemctl status packagekit.service --no-pager 2>/dev/null || true
systemctl status packagekit-offline-update.service --no-pager 2>/dev/null || true
```

Also inspect D-Bus activation and PackageKit service units as appropriate. Check repo files and ownership, enabled state, release URL, architecture, GPG key references, `gpgcheck`, and metadata availability. Use read-only commands for search/metadata proof. A service may be D-Bus activated rather than permanently running; report that accurately.

Do not assume a standard systemd service must be active all the time. Test the actual PackageKit transaction path.

---

# 4. Phase B — display pipeline, resolution experiments, and smoothness

## 4.1 Preserve the known-good baseline

Keep a pristine copy of the working phone config and known-good binary/config hashes. The default safe profile must continue to be:

```ini
[output:HEADLESS-1]
mode = 720x1520
scale = 2
```

unless all acceptance checks below prove a better alternative on the actual phone. Do not change the physical framebuffer panel mode to match a compositor experiment.

The configuration should be explicit, documented, and traceable. Do not leave several conflicting display configs or duplicate orientation overrides where it is unclear which one wins.

## 4.2 Implement a controlled profile experiment

Add a clear, reversible way to select display profiles for **testing**. Use the project’s existing configuration conventions. At minimum distinguish:

- `safe-720x1520-s2` — current default and fallback;
- `candidate-360x760-s1` — portrait low-pixel-count experiment;
- any additional profile only if proven supported by Phoc, the bridge, the orientation service, and the physical output.

Do not expose an experimental profile as a normal user toggle until it has passed all physical acceptance checks. A config file or explicit root-only engineering command is sufficient for A/B work.

A profile must describe both compositor mode and scale. Validate inputs strictly. Reject arbitrary strings, unsupported ratios, zero/negative scales, or modes that do not map to the panel. Prefer a small allow-list for the S10+ over an arbitrary resolution API.

## 4.3 Test the 360×760 / scale-1 candidate honestly

This is the most interesting first experiment because it preserves the 360×760 portrait logical viewport while reducing the compositor buffer to 25% of the current pixel count.

However, prove all of the following:

- Phoc actually accepts the mode and exposes the intended 360×760 logical output.
- The bridge recognizes 360×760 input and produces an exact 1440×3040 panel image.
- The general 4× upscale path is correct, has no row-stride or colour-order corruption, and does not exceed the current bridge latency.
- Text and fine line quality remain acceptable. Compare small text, icon edges, thin strokes, anti-aliasing, keyboard glyphs, and subpixel/high-contrast content against the current 2× mode.
- Touch coordinates map to the correct locations at all four corners, edges, and center.
- Home, app drawer, Settings, keyboard, browser, dialogs, video, and any app using fixed physical/logical assumptions remain correctly laid out.
- Landscape and all supported rotations maintain the project’s intended logical dimensions, with no squashing, unexpected zoom, off-screen touch mapping, or incorrect status/navigation bars.
- Screen-off, screen-on, suspend/resume, lock screen, unlock, charger connect/disconnect, orientation change, and Wi-Fi SSH access still work.
- The display bridge has one owner and returns to the safe profile cleanly after an intentional test failure or service restart.

Because the current orientation policy uses different portrait and landscape scales, you must solve the logical-size issue explicitly. If landscape cannot retain its intended logical layout using the candidate, keep it as a portrait-only experiment and do not promote it to the global default. A portrait-only improvement is not a complete all-orientations replacement.

## 4.4 Do not force 540×1140 unless fractional scale support is proven

`540×1140` preserves the panel aspect ratio and is a useful theoretical middle point, but a 1.5 scale is not established as supported by the current Phoc/orientation/bridge path. Test support explicitly before adding it. Never fake 1.5 by rounding different components independently.

## 4.5 Profile A/B method

Run both modes under the same controlled conditions:

- same phone, OS build, brightness, battery/charger condition, network, temperature range, and app set;
- same scripted interaction sequence and same duration;
- cold and warm app launch cases;
- idle/locked screen and changed-frame animation cases;
- home swipes, drawer open/close/scroll, Settings first open/tab changes, keyboard open/type/close, and a representative app/web view;
- repeated trials, not a single favourable sample.

Collect at minimum:

- bridge `blit_avg_ms`, p50/p90/p95 (add these if existing telemetry does not expose them), frames/presents per second, skipped unchanged frames, full/partial damage rows, and failures;
- compositor, bridge, and WebKit/GTK CPU time and peak memory;
- interaction latency and visible frame stability;
- temperature/throttling indicators;
- battery drain only when a repeatable measurement is possible;
- screenshots for image-quality comparison.

Benchmark the complete path. A smaller compositor buffer is not automatically faster if the generic 4× expansion path costs more CPU or if the fixed framebuffer write dominates.

Use a documented script or test harness that labels the active profile in every sample. Make the results reproducible and keep raw CSV/JSON plus a summary under `docs/pwnage59000/evidence/`.

**Promotion rule:** do not change the shipped default solely because pixel count is lower. Require a repeatable, meaningful improvement (target at least 20% improvement in the relevant p95 render/present or UI-interaction metric, unless the measured bottleneck makes another justified threshold more appropriate), no visible quality regression that matters on a phone, no touch/orientation regression, and no reliability regression. State clearly which metric improved. If results are neutral or mixed, retain the current default.

## 4.6 Improve the bridge only where profiling justifies it

Inspect `tools/s10plus/a67/nuxel-wl-fb.c` and the corresponding build/install rules.

Potential areas to measure and consider:

- optimize the actual selected integer scale path (especially 4× if the 360×760 experiment is successful);
- avoid per-frame allocation and unnecessary format conversions;
- retain aligned buffers and safe stride calculations;
- ensure vectorized code handles row tails and non-multiple widths safely;
- use the existing optimized 2× path as the bit-exact reference;
- retain correct XRGB/ABGR/BGRA handling for the actual framebuffer format;
- preserve damage-region copies and skip unchanged frames;
- avoid redundant copies between screencopy buffers, staging buffers, and framebuffer rows;
- avoid waking the bridge or WebKit needlessly when the display is off/locked and unchanged;
- maintain atomic/consistent status reporting for orientation and current mode.

For any new SIMD path, add a scalar reference implementation and tests that compare every output pixel against it across:

- smallest and normal dimensions;
- odd/even dimensions where supported;
- padded source and destination strides;
- row boundaries and final partial tiles;
- each supported integer factor;
- black, white, primary colours, gradients, alpha/XRGB edge cases, and random pixel data.

Use sanitizers or valgrind on host builds where practical. Do not make undefined alignment assumptions. Benchmark in both synthetic tests and the real phone bridge.

Do not claim direct scanout, zero-copy, DMA-BUF, or GPU composition unless proven end-to-end. The current architecture is a compositor buffer → bridge → framebuffer presentation path.

## 4.7 Graphics-profile correctness and legacy contract

Run and repair `tests/pwnage50000/test_graphics_profile.py` without weakening it. In the current checkout, the test run surfaced three failures:

1. Legacy schema-v1 `webkitgtk.mode = "accelerated"` is not translated into the expected WebKit environment by `env_for()` because the profile-selection path reads the newer profile/default-profile shape.
2. An invalid legacy mode such as `gl; rm -rf /` is not rejected/fallen back closed with a clear `NUXEL_GRAPHICS_FALLBACK_REASON`.
3. `env_for("gtk4")` inherits WebKit software environment variables, violating the requirement that GTK4 renderer selection be independent of WebKit.

Fix the compatibility/normalization layer, input validation, fallback reason, and per-toolkit environment composition. Preserve strict allow-listed values and safe defaults. Do not solve a failing test by deleting it, skipping it, or relaxing security validation.

Add tests proving:

- schema-v1 and schema-v2 inputs map to the intended effective profile;
- invalid values fail closed and cannot inject environment variables or commands;
- GTK4 settings do not leak into WebKit and WebKit settings do not contaminate GTK4;
- software-safe fallback is deterministic;
- renderer availability is not inferred merely from installed library files;
- status output reports why a profile was rejected or fell back.

Only enable a GPU-rendered SHM profile after live testing proves the target WebKit process is using it and the bridge presents it correctly. Do not advertise DMA-BUF as available when the current device/kernel path does not support it.

---

# 5. Phase C — separate desktop grid from app drawer geometry

## 5.1 Define four independent layout settings

The authoritative launcher settings must distinguish:

```js
{
  gridColumns: 4,   // desktop/home app grid columns
  gridRows: 5,      // desktop/home app grid rows
  drawerColumns: 4, // app-drawer columns only
  drawerRows: 5     // app-drawer visible row density only
}
```

Keep existing settings and migration behaviour. The values above are sensible defaults, not permission to overwrite a user’s existing preferences.

The following must remain independent:

- desktop columns and rows;
- app drawer columns and visible row density;
- dock columns/layout;
- desktop icon size and per-app icon size;
- desktop count and home-page assignments;
- app ordering and folders.

Changing any one of these must not mutate the others.

## 5.2 Specify drawer row semantics clearly

`drawerColumns` controls how many icon/app tiles are shown across the drawer.

`drawerRows` controls the drawer’s visible vertical density/row sizing within its viewport. The drawer must continue to expose **all installed/registered apps through vertical scrolling**. Do not turn the app drawer into a paginated subset that hides apps after `drawerRows × drawerColumns`.

The row setting can control grid auto-row sizing or the number of comfortable rows visible at once, as appropriate to the actual drawer design. Choose one clear model, document it in the UI/help text, and ensure it behaves in both portrait and landscape. It must not accidentally constrain the desktop’s `appsPerPage`.

Use bounded, validated values. A reasonable initial range to consider is 3–6 drawer columns and 3–8 drawer visible rows, but inspect actual screen sizes and choose sensible limits. The desktop can retain its current 3–6 columns and 4–7 rows unless device evidence justifies changing them. Reject malformed localStorage values safely.

## 5.3 Give the drawer independent CSS variables and selectors

Introduce independent variables such as:

```css
--home-columns: 4;
--home-rows: 5;
--drawer-columns: 4;
--drawer-rows: 5;
```

Do not use a shared `.app-list` rule that forces the drawer to inherit `--home-columns`. Prefer explicit selectors with clear ownership, for example:

```css
/* Desktop/home only */
.home-screen .app-list:not(.drawer-list) { ... }

/* App drawer only */
#drawer-list.drawer-list { ... }
```

Adapt those selectors to the actual DOM. The important requirement is that the drawer rule wins for the drawer and the home rule wins for the desktop, without a cascade accident.

Set `--home-columns` from `gridColumns` and `--drawer-columns` from `drawerColumns` independently. Do not derive drawer geometry from the desktop variable. `drawerRows` must have a real visible effect, not just be saved and displayed in the setting control.

Do not let this work alter `--app-icon-size`, app-specific sizes, dock icon sizing, or touch target dimensions unless a separate usability issue is demonstrated and addressed explicitly.

## 5.4 Fix the desktop’s four-column/five-row mismatch

Do not assume the current mismatch is a CSS bug until you inspect the live phone. Trace the complete chain:

1. Settings screen input value.
2. `launcher.settings` in memory.
3. `localStorage['nuxel.launcherLayout']` persisted value.
4. `_applyLayout()` and CSS custom properties.
5. actual desktop grid element and computed style.
6. active CSS bundle, media rules, and service-worker version.
7. app tiles visible and their measured rectangles.

Potential causes to evaluate include stale localStorage, a legacy settings migration, CSS specificity, wrong DOM selector, an older deployed JS/CSS bundle, an active SW serving old assets, a container width/side padding issue, or an incorrect page assignment. Fix the actual root cause.

Add a lightweight diagnostic mode or test helper that reports the four values above and the actual computed CSS grid counts. Avoid permanent noisy logs in the normal UI.

## 5.5 Repack desktop assignments safely when capacity changes

When `gridColumns` or `gridRows` changes, update page capacity and re-evaluate current assignments. The current code’s settings update path does not fully normalize `pageAssignments` when capacity changes; fix this.

Requirements:

- preserve all app IDs and folder IDs;
- preserve user-specified order as far as possible;
- preserve current desktop/page when possible;
- do not drop apps that no longer fit;
- do not silently create more desktops than `desktopCount` without a clear policy;
- if the new capacity requires multiple pages, distribute items deterministically and visibly;
- preserve pinned/dock entries according to their existing semantics;
- keep hidden/system app policy unchanged;
- make shrinking and expanding grids deterministic and idempotent;
- if an update is rejected, leave both in-memory and persisted state unchanged;
- migrate older layout records without loss.

Use or extend `pwa/nuxel-home/js/layout-model.js` as the pure layout/packing authority. Unit-test it independently of the DOM. Do not duplicate layout algorithms in the Settings iframe.

## 5.6 Add controls in both Settings surfaces

The user asked for the controls in Home Settings and in the main Settings app. Implement both.

### Existing Home Settings overlay

Retain the existing desktop/home grid section and add a clearly separate App Drawer section containing:

- drawer columns control;
- drawer visible rows/density control;
- concise help stating that all apps remain scrollable and these values do not affect the desktop.

Ensure the desktop controls remain labelled “Home/Desktop grid” and drawer controls are labelled “App drawer grid” or equivalent.

### Main Settings app

Add a dedicated “Home & App Drawer” tab/section in `pwa/nuxel-apps/settings/index.html` and its existing Settings navigation model. It should show the same four controls, grouped into “Home screen” and “App drawer”. Keep the visual conventions of the current Settings app; do not create a second settings architecture.

### One source of truth

Home Settings and the Settings PWA run in distinct document contexts. Inspect how the Settings PWA is embedded (the current design uses an iframe) and use a deliberate same-origin integration. The launcher exposes a global `window.launcher`; if that remains the intended API, use a narrow, validated public method rather than allowing the iframe to mutate random internal fields.

A suitable approach is a documented launcher settings API that:

- returns a copy of the validated settings;
- performs one atomic update through `updateHomeSettings()`;
- publishes a namespaced `nuxel:launcher-settings-changed` event with a safe settings snapshot;
- allows both Home Settings and the Settings iframe to subscribe and refresh their controls;
- handles iframe teardown/reload and same-origin access errors gracefully.

Alternatively, use a shared, versioned settings module/API if that fits the existing architecture better. Do not create two independent localStorage records that can drift. Keep `nuxel.launcherLayout` as the canonical persistence location unless there is a well-supported reason to migrate it.

Settings controls must reflect external changes immediately. Prevent event loops by distinguishing user-originated updates from state reflection. Validate at the authoritative launcher boundary even if the UI already constrains its inputs.

## 5.7 Drawer behaviour and polish

- All apps remain discoverable and scrollable.
- Opening/closing and scrolling remain smooth; no full registry re-render on each slider tick.
- Changing drawer columns/rows updates layout without changing app icon source/size.
- The drawer must not inherit desktop page capacity or desktop assignments.
- App search/filter behaviour remains correct.
- Keyboard and touch scrolling work.
- Empty-state, large-app-count, and small-viewport cases are tested.
- Rotation preserves settings and sensible layout.

## 5.8 Service worker and release versioning

Inspect `pwa/nuxel-home/sw.js`, `manifest.json`, asset query versions, and `tools/s10plus/a33/tests/launcher-registry-test.js`.

After changing served assets:

- bump the home PWA cache version using the repository’s versioning convention;
- keep manifest cache version, SW cache version, and status-bar/app version invariants synchronized as required by the existing registry test;
- update HTML asset URLs/version query strings consistently;
- ensure the old cache is retired without deleting unrelated app data/localStorage;
- confirm a running client updates and reloads predictably;
- do not solve caching by indiscriminately clearing all browser storage or app preferences.

Add a migration test for existing `nuxel.launcherLayout` records and a test proving a stale service-worker cache cannot keep the old drawer/home CSS active after the supported update process.

---

# 6. Phase D — make the Settings app fast by doing less work

## 6.1 Establish first paint before backend work

The Settings shell and the initially visible tab should render immediately from static UI and cached/local values. No Bluetooth discovery, display enumeration, GPS lookup, audio enumeration, graphics diagnostics, PackageKit metadata refresh, or developer polling should be required just to show Settings.

Use a clear lifecycle:

1. Parse DOM and bind lightweight event handlers.
2. Determine which tab is initially active.
3. Render the shell and tab navigation.
4. Load the initial tab’s essential data only.
5. On first visit to another tab, lazily initialize and load that tab.
6. Cache successful results with a documented lifetime where appropriate.
7. Allow an explicit refresh that bypasses cached data.

Do not block initial rendering on optional data. Render progressive loading/error states per tab.

## 6.2 One loader per tab, with in-flight deduplication

Create or adapt a small tab lifecycle/loader registry. Each tab should have:

- a lightweight `bind()` phase that registers handlers once;
- an `init/load()` phase invoked when the tab first becomes active;
- a `refresh()` operation for explicit user refresh;
- an in-flight promise so double-clicks do not start duplicate backend work;
- a loaded/last-updated marker;
- cancellation or a monotonically increasing request token so stale results do not overwrite newer state;
- a proper error state that can be retried.

Keep module responsibilities clear. Do not create a giant Settings controller with every hardware detail embedded in it.

## 6.3 Move eager work to the tab that owns it

Review the existing startup and move each operation to its actual tab:

| Current work | Correct ownership / lazy trigger |
|---|---|
| `loadRotation()` | Screen/display tab, or only if required for a visible global indicator |
| zones document and screen geometry | Screen tab |
| button, boot, and haptics config | Buttons / navigation / haptics tab |
| Bluetooth status and device scan | Bluetooth tab |
| display enumeration | Displays tab |
| audio device enumeration | Sound tab |
| maps rendering and location refresh | Location tab |
| power detail/status | Power tab |
| notifications, NFC, fingerprint, security | Their own tabs |
| Software provider/metadata status | Software tab; status check must be lightweight |
| graphics diagnostics | Graphics tab |
| driver diagnostics | Diagnostics tab |
| multiple `status.read` developer probes | Developer tab only |

Initialise the initially selected tab only. If the existing navigation model has nested sections, preserve its semantics.

## 6.4 Eliminate unnecessary polling

- No developer timer while Developer is not active.
- No location timer while Location is not active.
- No polling while `document.hidden` is true.
- Stop timers and abort/cancel requests on tab switch, `visibilitychange`, app close/unload, and iframe disposal.
- Restart them only when the owning tab is active and the document visible.
- Do not poll a setting just to animate a value that does not change.
- Prefer a documented manual refresh or a modest, justified interval. The existing unconditional 15-second developer refresh should be removed or scoped to the active Developer tab.
- Deduplicate duplicate state reads, including touch-arm reads in the current developer refresh sequence.

Use one timer per feature, not one timer for every visit or event. Prevent timers from multiplying after switching tabs repeatedly.

## 6.5 Parallelize independent requests, not all requests

The current serial startup promise chain makes unrelated work wait behind earlier operations. Once a tab is active, run independent requests in parallel and render each section as its result arrives. Use sensible timeouts and cancellation.

Do not start all tabs in parallel. The optimization is to load the selected tab’s independent requests in parallel, not to create a thundering herd across the entire device.

## 6.6 Prevent main-thread and DOM churn

- Keep all expensive bridge and subprocess operations out of synchronous UI callbacks.
- Do not rebuild large DOM trees for every status tick or range-slider change.
- Debounce text search and other high-frequency input.
- Batch visual updates with `requestAnimationFrame` where useful.
- Avoid repeated style reads/writes that cause layout thrashing.
- Check hidden-panel rendering and expensive maps/graphics previews.
- Avoid adding broad blur/backdrop effects to the phone UI as a “polish” step.
- Keep transitions short and compositing-friendly; do not animate layout-heavy properties unnecessarily.
- Make loading spinners, progress, timeout, and error feedback clear rather than freezing the UI.

## 6.7 Instrument the improvement

Add opt-in performance marks or a diagnostic mode for:

- Settings shell DOM ready;
- first stable Settings frame / shell interactive;
- first tab data complete;
- tab switch start and completion;
- bridge request count and latency per tab;
- JS long tasks or slow handlers where available;
- active polling/timer count.

Capture a before/after comparison on the same device. A meaningful goal is that the Settings shell and first usable controls appear without waiting for unrelated services; target sub-500ms shell interaction where the phone is not already heavily loaded, and report the real median/p95 rather than hiding slower cases. First-load hardware tabs may take longer, but the navigation must stay responsive and show progress.

Add tests that assert hidden tabs do not trigger their probes at initial load and that timers stop when the user switches away or hides the document.

---

# 7. Phase E — repair Software search, Fedora repositories, and installation

## 7.1 Keep the product identity clear

The native **Software** app is the graphical front end for the device’s Fedora RPM package system. It should search enabled RPM repositories and install/remove packages using PackageKit/DNF dependency resolution and polkit.

**NuXtore** is the separate Nuxel app-bundle/offline catalog. Do not merge the two catalogs, claim NuXtore contains Fedora packages, or show a fake remote list when no bundle source exists.

Keep the app registry entry, desktop file, executable path, package ownership, and Settings status consistent. Investigate the stale `shell/config/org.gnome.Software.desktop` entry (`Exec=gnome-software`) versus the installed custom `nuxel-software` launcher. Ensure the user’s Software icon resolves to the intended custom app and that no duplicate/stale desktop entry can launch an absent or unintended binary.

## 7.2 Configure official Fedora repositories in the target rootfs

The existing build script uses a temporary `/tmp/nuxel-repos` directory for build-time DNF operations. Do not assume those temporary repo files are copied into the phone image.

The repository’s `tools/s10plus/a33/verify-packages.py` defines the project’s expected official Fedora 43 AArch64 channels:

- Fedora release / Everything for the target Fedora release and architecture;
- Fedora updates / Everything updates for that same release and architecture.

For Fedora 43 AArch64, the known canonical locations in this repository are equivalent to:

```text
https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Everything/aarch64/os
https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64
```

Do not hard-code Fedora 43 blindly if the actual target is a different release. Determine the installed release and architecture, then keep the target repo files, builder repo URLs, and package verifier constants consistent. Prefer Fedora’s own `fedora-release` / `fedora-repos` package-owned files if they correctly configure the target. If they are missing or wrong, add a controlled image-builder step to install/repair the standard official release and updates repo files in the target rootfs.

Requirements:

- enable the official Fedora release and updates repositories;
- use the correct `$releasever` and `$basearch` or explicitly verified values;
- `gpgcheck=1` (and repo metadata verification where supported);
- use the official Fedora signing key packaged/imported through Fedora’s trusted mechanism;
- ensure the expected signing key is installed and its fingerprint/ownership is trusted;
- preserve TLS certificate validation;
- do not disable GPG verification to work around a bad repo/key;
- do not add third-party repositories as part of this repair;
- do not duplicate repo IDs or leave stale mirror URLs;
- make the rootfs verifier assert that the files exist, are enabled, use the expected official hosts, and keep signature checking enabled.

Use the repository’s existing repo constants as the source of truth where possible; avoid subtly diverging the image builder and `verify-packages.py`.

The image builder should make the target image usable after first boot. If metadata must be refreshed on first boot, do this as a bounded, visible one-time job with progress and failure state—not every time the Software app is opened. Do not block the graphical session or initial boot indefinitely on network availability.

## 7.3 Verify PackageKit end to end

Check actual target packages and services:

- `pkcon` client exists and is executable;
- PackageKit D-Bus service/backend exists and can activate;
- the DNF backend is installed/selected and functional;
- polkit is installed and the intended user interaction is available;
- repo files are enabled and valid;
- AppStream data and metadata are available or can be refreshed;
- metadata freshness is known;
- search and package detail roles are supported;
- package transaction roles are supported;
- package IDs returned by PackageKit are preserved exactly.

Do not require the PackageKit daemon to sit running permanently if the intended Fedora setup is D-Bus activation. Test a real read-only transaction or query from the actual app user context.

Check whether `appstreamcli` is present and which refresh/cache commands the installed version actually supports. Do not copy a command from a different AppStream release without checking its `--help`.

## 7.4 Make search asynchronous and robust

Refactor `services/nuxel-software/nuxel-software` so GTK never waits synchronously on repository search, refresh, install, remove, or package detail operations.

Use a worker thread / Gio asynchronous API / PackageKit D-Bus async transaction, whichever is the cleanest fit for the installed dependencies. If using Python threads, update GTK widgets only through `GLib.idle_add` or the approved main-context mechanism. Handle the window closing while work is still in flight.

Search requirements:

- run after a short debounce (roughly 250–400ms) or Enter, not on every raw keystroke with no control;
- cancel prior work when possible and always discard stale results using a monotonically increasing request ID;
- query available packages from enabled repos, not only installed software;
- make search case-insensitive and useful for package name and summary/description according to supported backend roles;
- support an empty query as a well-defined state (e.g., curated/trending or explain “type to search”), not an accidental full-repository flood;
- retain package name, exact PackageKit package ID, version, architecture, repository, summary, and installed/available status as distinct fields;
- do not split package IDs at the first dot or otherwise rewrite them;
- sort/rank results deterministically and avoid duplicate architectures/versions crowding the UI;
- provide loading, no results, metadata updating, no network, repo unavailable, PackageKit unavailable, permission required, and backend error states distinctly;
- preserve the stderr, exit code, and useful backend error message for diagnostics while presenting user-friendly copy;
- provide a Retry / Refresh metadata action where appropriate.

The existing semicolon-output parser is not reliable until proven against the installed `pkcon` version. Inspect `pkcon --help` and the exact installed version. Prefer the PackageKit D-Bus API and typed package objects if feasible. If a CLI interface is retained, use a documented machine-readable/plain mode only after verifying that the target version supports it, add fixtures from actual output variants, force a known locale for parser stability, and handle warnings/progress text separately from package rows. Never assume an output option exists.

Do not parse output by splitting a display line on arbitrary whitespace if package summary fields can contain spaces. Keep package IDs intact.

## 7.5 Safe install and remove operations

- Use PackageKit transactions so DNF resolves dependencies, conflicts, scriptlets, and package signatures.
- Keep polkit authorization/confirmation intact.
- Show package name, version, and a clear install/remove confirmation before starting.
- Show transaction progress and actionable failure reasons.
- Disable duplicate transaction actions while one is active, but keep navigation responsive.
- On success, refresh the affected package state and update the installed badge.
- Never build shell command strings with user input; use structured API arguments or argument arrays.
- Validate package IDs and use the exact selected ID returned by PackageKit.
- Do not run `rpm -i` or `dnf -y` from a GUI shell string as a shortcut.
- Do not perform an install automatically just to test the app.

## 7.6 Refresh strategy and first-run experience

Separate the following states:

1. Repositories configured and enabled.
2. PackageKit backend available.
3. Metadata present.
4. Metadata freshness known.
5. Search transaction running.

On first boot or first Software launch, if metadata is absent/stale, provide a visible “Updating software information” state and start a bounded refresh in the background. Do not refresh on every search. If no network exists, show that the local metadata is unavailable and offer retry; do not show a falsely empty repository as “No software found”.

A manual refresh button must refresh metadata once and then re-run the current query. Prevent simultaneous duplicate refreshes. Make progress and timeout behaviour clear.

## 7.7 Fix Software status reporting

Update `services/nuxel-bridge/src/software_provider.py` so “ready” means the appropriate package-management path is genuinely usable. At minimum report separately:

- RPM database/tool present;
- DNF/DNF5 backend available;
- `pkcon` present;
- PackageKit D-Bus service/backend can activate/respond;
- official repositories present and enabled;
- GPG verification configuration safe;
- AppStream data/metadata state;
- last refresh / metadata freshness when available;
- Flatpak status as a separate optional capability.

Do not initiate a full repo refresh for a simple status read. Status should be bounded and quick. Use actual runtime checks instead of claiming a kernel config option is missing/present based on an old comment. The existing user-namespace probe may use `unshare`; report the runtime outcome accurately.

Do not weaken Flatpak sandboxing, user namespaces, bubblewrap, or portal requirements to make the app look more capable. If Flatpak is unavailable, say why and keep the Fedora RPM search/install path working.

Settings’ Software tab should distinguish “PackageKit ready”, “repositories missing”, “metadata needs refresh”, “network unavailable”, and “backend unavailable”. It must not say the native store is ready just because `rpm` and `dnf` executables exist.

## 7.8 Keep image contents and launchers consistent

Update the S10+ rootfs builder and package verifier so a freshly built image contains:

- the intended custom Software executable;
- the intended desktop entry and app-registry path;
- PackageKit client and correct DNF backend;
- Fedora release/repository package and correct official release/updates repo files;
- polkit agent suitable for the existing session;
- AppStream support/data required by the Software UI;
- any required D-Bus activation/service files.

Remove or stop installing conflicting stale desktop launchers only after proving no other code depends on them. Verify that only the intended Software app entry appears in the launcher.

---

# 8. Phase F — regression tests and verification

Add a new test group:

```text
tests/pwnage59000/
```

Tests must exercise behaviour, not merely assert that a filename contains a string. Prefer pure-function tests for layout/packing, repo policy, parser logic, settings lifecycle, and profile resolution; add source-contract checks only where runtime integration is not easily testable.

## 8.1 Display tests

- allowed S10+ profiles and aspect ratios;
- reject 720×1280 and 1080×1920 as S10+ full-panel profile candidates;
- safe fallback remains 720×1520 scale 2;
- candidate 360×760 scale 1 derives the intended portrait logical size;
- orientation transformations/scales remain correct or candidate is explicitly disabled for unhandled poses;
- bridge scaling factor and buffer dimensions are checked without integer overflow;
- scalar and SIMD bridge output are pixel-identical for test vectors;
- row stride and damage-region edge cases;
- no second framebuffer writer/service is introduced;
- diagnostics state the actual active mode, scale, transform, buffer, and panel dimensions.

If C tests exist or can be built on the host, add them. If bridge behaviour can only be validated on target, provide a deterministic on-device harness and mark that part `NOT RUN` on a host-only environment.

## 8.2 Launcher tests

- defaults and legacy migration;
- independent home and drawer values;
- updating `gridColumns` never changes `drawerColumns` and vice versa;
- updating home rows/columns never changes icon sizes, dock settings, or drawer dimensions;
- updating drawer rows/columns never changes desktop capacity or page assignments;
- drawer scrolls through all apps beyond visible rows;
- CSS variable separation and actual drawer selector;
- settings changes from either Home Settings or main Settings update the same canonical state;
- iframe teardown/reload does not leave stale listeners;
- deterministic desktop repack without data loss;
- shrinking/expanding grids maintains valid page indices and desktop count;
- a 4×5 desktop actually computes to four columns/five rows on the tested viewport;
- service-worker cache/version migration.

Add JS tests using the project’s available Node/test infrastructure. Do not introduce a large new framework for a small pure layout function.

## 8.3 Settings performance tests

- initial Settings load does not call Bluetooth, display, audio, GPS, graphics diagnostics, PackageKit, or Developer probes unless the initially selected tab requires them;
- each tab initializes once on first activation;
- concurrent activation shares an in-flight load;
- switching away stops polling;
- `document.hidden` stops polling;
- returning to the tab restarts only its allowed polling;
- explicit refresh bypasses cache;
- stale asynchronous responses do not overwrite newer state;
- a failing hidden service does not block first paint;
- listener/timer counts do not grow after repeated tab switches.

## 8.4 Software and repository tests

- repo policy uses official Fedora release and updates only;
- repo release/architecture matches actual configured target;
- GPG verification must be enabled;
- reject insecure repo configuration, unknown hosts, duplicate IDs, and wrong architecture;
- package parser handles verified real output fixtures, status/progress lines, empty results, localized messages, errors, and summaries with spaces;
- package IDs remain byte-for-byte unchanged;
- stale search responses are discarded;
- search is asynchronous/debounced;
- failed refresh is not represented as empty search results;
- install/remove preserve exact package IDs and confirmation semantics;
- GTK widgets are only updated on the main loop;
- destroying the window while work is running does not cause callbacks against destroyed widgets;
- provider health distinguishes binaries, service, repos, metadata, and Flatpak separately;
- NuXtore and RPM Software remain distinct.

Use mocks for transactions in tests. Do not make CI depend on a live Fedora mirror or network. Add an opt-in integration test for the actual phone.

## 8.5 Existing tests that must stay green

The current audit ran:

```sh
pytest -q \
  tests/pwnage50000/test_drawer_gesture_guard.py \
  tests/pwnage50000/test_graphics_profile.py \
  tests/pwnage52000/test_settings_dom.py \
  tests/pwnage58000/test_pwnage58000.py
```

Current observed result: **3 failed, 17 passed**. The three failures are the graphics-profile compatibility/environment-isolation issues listed in section 4.7. The drawer gesture guard, Settings DOM, and PWNAGE-58000 contract tests passed in this run.

Fix those three failures; do not weaken them. Then run the broader relevant suite, including the new PWNAGE-59000 tests. Report the exact command and full pass/fail/skip summary.

At minimum run relevant commands such as:

```sh
pytest -q tests/pwnage50000 tests/pwnage52000 tests/pwnage54000 tests/pwnage58000 tests/pwnage59000
node tools/s10plus/a33/tests/launcher-registry-test.js
python -m compileall -q services/nuxel-bridge services/nuxel-orientation
python -m py_compile services/nuxel-software/nuxel-software
bash -n images/s10plus/build-phone-rootfs-inside-fedora.sh
```

For JS files, use the repository’s supported syntax checker or `node --check` on standalone files where module syntax permits. For C bridge changes, compile using the same flags/toolchain as the S10+ image builder, and run host unit tests/sanitizers when practical. Do not mark a command as passed if it was not executed.

Run the actual rootfs verifier on a staging rootfs or built image. Extend it to check the target repo files, Software launch target, PackageKit components, and graphics/display config installation where appropriate.

---

# 9. Physical-device acceptance matrix

A source-level pass is not the same as a working phone. Test on the actual SM-G975F whenever device access is available.

## 9.1 Display and interaction

| Test | Required result |
|---|---|
| Cold boot | Correct portrait display, no black screen/hang, lock screen usable |
| Normal home | No cropping/stretching; stable 4-column desktop when configured 4 |
| App drawer | Independent columns/rows, all apps scrollable |
| Settings | Shell appears quickly; selected tab loads progressively |
| Keyboard | Correct scale, visible keys, accurate touch mapping |
| Touch corners | All four corners and center map correctly |
| Rotation | All supported orientations have correct layout and touch mapping |
| Lock/unlock | No broken bridge or stale frame after unlock |
| Screen off/on | Bridge and compositor recover without duplicate writer |
| Brightness | Full usable panel; no unexpected partial image |
| Wi-Fi SSH | Remains reachable during/after display tests |
| Charger/USB indicators | Existing indicator logic remains functional |
| Long UI session | No accumulating timers, memory leak, or performance collapse |

## 9.2 Launcher/Home/Settings

- Set desktop to 4 columns × 5 rows and verify four actual desktop columns and five desktop rows where content fills them.
- Set drawer to a different geometry (e.g. 5 columns × 6 visible rows) and verify the drawer changes while the desktop remains 4×5.
- Change desktop back to 3×4 and verify drawer stays at 5×6.
- Change drawer and desktop settings from the main Settings app, then open Home Settings; both must show identical values.
- Reverse the process and check synchronization.
- Reboot and verify settings persist.
- Install/register a test app through the normal Nuxel app registry path if available and confirm it appears in the drawer and obeys the expected desktop pin/order model.
- Verify icon size and dock are unchanged throughout.
- Test enough app registrations to exceed one drawer viewport; scroll all the way to the final app.

## 9.3 Settings performance

Run the same interaction sequence before and after. Record median and p95 timing. Verify that the initial Settings opening does not start unrelated device probes. Open each hardware tab once and ensure it loads and reports true state. Switch between tabs rapidly and inspect logs for duplicated requests or callbacks after the tab closes.

## 9.4 Software

After official repo configuration is verified:

- open Software;
- wait for initial metadata state if necessary;
- search for at least two known package names expected in the target Fedora repository set (verify availability from the live repo, do not hard-code a package as guaranteed if it has been retired);
- verify that result names, summaries, versions, repo names, and exact IDs are present;
- search for a deliberately nonsense term and observe a genuine no-results state;
- test offline/no-backend error states where safely possible;
- test metadata refresh once and ensure it is not repeated on every search;
- verify install confirmation and polkit flow without actually installing unless explicitly authorized;
- if an owner-authorized install test is performed, record package/version, transaction logs, and a safe cleanup procedure.

---

# 10. Deployment, rollback, and fail-safe behaviour

## 10.1 Display experiment rollback

Before deploying an experimental mode:

1. Back up `/etc/nuxel/phoc-phone.ini`, orientation configuration, and any changed bridge/session file with timestamps and hashes.
2. Save the known-good 720×1520 scale-2 config in a protected rollback location.
3. Prepare a tested command/script to restore it and restart the relevant services.
4. Verify the bridge’s single-writer lifecycle before restart.
5. Keep SSH alive and have a remote rollback route independent of the phone UI.
6. Test the rollback path before running a long experiment.

If the experimental mode produces a blank panel, wrong touch mapping, broken rotation, or bridge failure, restore the safe mode immediately. Do not keep an unusable profile active to collect more data.

## 10.2 Software repository rollback

Back up existing repo files and package-manager config before modifying them. New repo configuration must be limited to known official Fedora files and be easy to restore. Never delete the RPM database or wipe DNF caches as a generic fix. If metadata refresh fails, keep the repo definitions and show a clear error; do not disable signature checking.

## 10.3 PWA/storage rollback

Preserve launcher localStorage data. Implement migrations as copy/validate/commit operations. If an invalid layout migration is detected, recover the old value and use safe defaults without deleting app order or icon-size preferences. Keep SW cache cleanup limited to Nuxel Home cache names.

## 10.4 Release/build integration

Ensure the S10+ image builder installs all newly required files and executable permissions. Confirm that the service points at the built/installed binary, not a developer checkout. Include any required dependencies in the appropriate package manifest. Keep the deployment process compatible with the user’s existing S10+ workflow and current SSH debugging approach.

---

# 11. Required deliverables

At completion, provide all of the following:

1. **Implementation diff** covering display/profile correctness, launcher layout, Settings lifecycle, Software/backend/repositories, image builder, verifiers, and tests as needed.
2. **A root-cause report** for the three-column desktop discrepancy, based on the live DOM/settings/cache evidence. If the phone was unavailable, state exactly what source-level causes were fixed and what remains unverified.
3. **A resolution recommendation** that names the actual default mode, scale, logical dimensions, and physical panel dimensions. Include A/B measurements for every tested candidate. Do not promote an untested mode.
4. **A launcher settings matrix** demonstrating home columns/rows and drawer columns/rows are independent, and that icon sizes/dock are unaffected.
5. **Settings performance measurements** before and after, including startup and tab timings, request counts, and timer behaviour.
6. **Software repository proof**: target Fedora release/architecture, enabled repo IDs and official URLs, GPG verification state, PackageKit backend state, metadata state, and real search results (read-only).
7. **Test report** with exact commands, pass/fail/skip/not-run results, including the previously failing graphics-profile tests.
8. **Device deployment instructions** using the repo’s existing Nuxel workflow, with transport stated explicitly and no invented host/IP.
9. **Rollback commands** for the display config, Software repo config, and PWA migration/cache version if needed.
10. **Files changed and why**, concise enough for the owner to review.

Do not claim “super smooth”, “GPU accelerated”, “90% faster”, “all packages searchable”, or “fully fixed” without the measurements and device evidence that support the exact claim.

---

# 12. Definition of done

This task is complete only when all applicable items below are true:

- [ ] The active physical panel dimensions are measured and distinguished from compositor/logical dimensions.
- [ ] `720×1280` and `1080×1920` are not used as S10+ full-panel modes.
- [ ] The safe `720×1520` scale-2 fallback remains available and documented.
- [ ] The `360×760` scale-1 candidate has been tested honestly, including bridge quality/performance, orientation, and touch; it is promoted only if it passes.
- [ ] The bridge remains a single framebuffer writer and all scale/stride paths are tested.
- [ ] Graphics profile legacy schema behaviour and GTK4/WebKit isolation tests pass.
- [ ] Desktop/home grid settings produce the actual specified desktop grid.
- [ ] Drawer columns and rows are independent of desktop columns and rows.
- [ ] Drawer rows have a visible, documented effect while all apps remain scrollable.
- [ ] Both Home Settings and the main Settings app control the same authoritative settings and stay synchronized.
- [ ] Changing grid dimensions does not alter icon size, app-specific size, dock, or lose apps/folders/order.
- [ ] Settings initial view performs no hidden-tab hardware/location/developer/software probes.
- [ ] Tab work is lazy, deduplicated, cancellable/stale-safe, and polling stops when hidden/inactive.
- [ ] Settings responsiveness has before/after measurements from a real device, or is explicitly marked unverified if device access was unavailable.
- [ ] Official Fedora release and updates repositories are configured in the target image/device with GPG checking enabled.
- [ ] PackageKit can query available software from the current target context.
- [ ] Software search is asynchronous, correctly parses supported backend results, and can distinguish backend/metadata/network/no-results states.
- [ ] Install/remove use safe PackageKit transactions with explicit confirmation and polkit.
- [ ] NuXtore remains separate from Fedora Software.
- [ ] Rootfs/image verification and relevant regression tests pass.
- [ ] Rollback instructions exist and are practical.
- [ ] The final report is honest about any missing physical test.

---

# 13. Suggested execution order

Work in this order to minimise risk and keep the changes reviewable:

1. **Baseline first:** capture current repo/test state and live phone state.
2. **Fix deterministic tests and graphics-profile correctness:** repair the three known failures and ensure conservative fallback behaviour.
3. **Fix launcher model and CSS separation:** implement the pure settings/migration/repacking logic first, then CSS and Home Settings.
4. **Add the main Settings controls:** connect them to the same launcher API and test cross-surface synchronisation.
5. **Fix Settings lifecycle:** make the shell fast, lazy-load per tab, and scope timers.
6. **Repair Software repository/image configuration:** ensure the target image contains official repos and PackageKit prerequisites.
7. **Refactor Software UI/backend:** asynchronous search/refresh/install/remove with robust PackageKit results and status.
8. **Run host tests and build/image verification.**
9. **Deploy non-display UI/software changes and verify them on the phone.**
10. **Run display A/B tests last**, because display-mode experiments can make the phone harder to operate. Preserve the known-good profile and SSH rollback.
11. **Produce evidence and the final completion report.**

Do not interleave a risky resolution change with an unverified launcher or PackageKit deployment. Keep each phase independently reversible.

---

# 14. Final instruction to the agent

Be rigorous and practical. Follow the code path that is actually built and launched on the S10+, not an abandoned prototype, duplicate config, old backup, or design mock-up. When two files appear to configure the same feature, trace which one the image builder installs and which one the running service reads.

Fix root causes. Do not hide symptoms by changing labels, hard-coding a fake four-column display, clearing all user preferences, disabling security, or making the entire app drawer a fixed page. Do not turn off useful diagnostics just to make Settings appear faster; make them lazy and scoped.

The key performance question is **where the frame time is spent**: the compositor, WebKit/GTK, framebuffer bridge, fixed physical scanout, or main-thread JavaScript/GTK blocking. Measure each layer. The key layout question is **which setting owns which geometry**. The key Software question is **whether the target Fedora repositories, PackageKit transaction backend, and metadata are actually present and healthy**.

The owner wants a phone that is visibly and measurably smoother, with a configurable home screen and app drawer, and a Software app that can genuinely find and install Fedora packages. Deliver that result without sacrificing the S10+ display, touch, rotation, security, or the ability to recover the phone remotely.

