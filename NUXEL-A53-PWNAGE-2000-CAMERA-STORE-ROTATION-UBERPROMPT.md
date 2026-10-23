# 🐧🔥 NUXEL A53 — OPERATION PWNAGE 2000
## Native Camera · Fedora Software Store · Real Flatpak Apps · Five-Mode Orientation · Physical S10+ Acceptance

**Executor:** DeepSeek-v4-pro-thinking, with repository access, Fedora development host as available, and existing authorized USB Live Console access to Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), running the user's CURRENT Fedora ARM64 Nuxel build.

**Mission type:** Implement and deploy working **userspace** functionality wherever supported; perform source-level diagnoses and produce precise next-action blockers when current vendor kernel/ISP/Wayland interfaces prevent real hardware function. Work incrementally and honestly. **Do not flash boot, kernel, recovery, rootfs or partitions. Do not replace the working graphical shell or lockscreen.**

**Primary owner request:**
1. Install a **real native Linux Camera app**; make it launchable from Nuxel Home, not merely listed in a mock app catalogue. Properly integrate the existing A52 Camera/Photos work.
2. Enable **real graphical installation, updating, launching, and removal of native Fedora applications and Flatpak apps**, preferably through **GNOME Software**, with correct privileges, desktop integration and a usable touch interface. Make Nuxel feel like a Linux phone on which software can actually be installed.
3. Fix the unfinished orientation implementation so **all FIVE owner-requested modes** appear in Settings **and** Quick Settings, persist, and work physically: **Auto**, **Auto Portrait**, **Auto Landscape**, **Forced Portrait**, **Forced Landscape**.

**Critical clarification about the last A52 outcome:** The agent reports the **S10+ rear sensor enumerates** but real capture remains **BLOCKED** for rear preview/JPEG/front/video/microphone capture. The Camera PWA, media store, permissions UI and 73+ offline checks were implemented, but **not** a proven camera-to-image pipeline. Do NOT silently convert “native camera installed” into “physical camera is working.” Installing Snapshot is one milestone; obtaining a frame is another.

---

# 0. ENGINEERING CONTRACT — HONEST STATES, NO REGRESSIONS

**Required completion evidence is from the physical S10+, not merely CI or desktop VM.** Preserve:
- Working S10+ boot visuals and TWRP escape route (no reason to enter recovery for A53).
- USB Live Console and recoverability.
- Nuxel Home, dock, Back/Home/Recents, working lockscreen, one good on-screen keyboard and focus handling.
- Existing A52 durable `media_store.py` and Camera/Photos apps; `org.nuxel.Camera` must remain private, not masquerade as a freedesktop portal.
- Wi-Fi and saved credentials as implemented in A51, plus available internet connectivity; don't disturb network configuration while installing packages.
- A50 performance goals and thermal constraints; heavy package metadata refresh or background camera retries must not keep the locked phone hot.
- Current deployment/boot service version and other agents' active files.

Stop for owner confirmation **before a reboot**, a potentially destructive package transaction, a privileged system configuration that could remove recovery, or any change outside ordinary reversible userspace package installation. Do NOT ask permission for every harmless read-only command. The owner specifically requests installation of software and these regular package installations are in scope, subject to a transactional preview/rollback.

**No misleading substitutes:** no fake camera frames, software-store screenshots with nonfunctional buttons, host-desktop success presented as handset success, CSS-only rotation, fake app icons, permissions bypass, disabling Flatpak security, or claiming the kernel camera is fixed merely because a new app opens.

**Statuses per gate:** `PASS_PHYSICAL`, `PASS_OFFLINE_ONLY`, `PARTIAL`, `BLOCKED_HARDWARE`, `BLOCKED_SESSION`, `BLOCKED_KERNEL`, `BLOCKED_NETWORK`, `NOT_TESTED`.

---

# 1. INVESTIGATE THE CURRENT REPO AND PHYSICAL DEVICE FIRST

Use the actual current checkout, not archival v0.6.3-beta assumptions. Find and read: recent A49 orientation work, A50 optimization changes, A51 Wi-Fi/Flatpak work, A52 camera/docs, app registry, Nuxel bridge, current systemd unit files, display-framebuffer bridge (`nuxel-wl-fb` if present), launcher/native-app launch path, XDG desktop session state, Quick Settings code, persisted settings location and kernel logs.

Before modifications capture:

```sh
uname -a
uname -m
cat /etc/fedora-release 2>/dev/null || cat /etc/os-release
id
find /dev/video* /dev/media* /dev/v4l-subdev* 2>/dev/null || true
ls -l /dev/iio:device* 2>/dev/null || true
command -v dnf flatpak gnome-software snapshot wlr-randr monitor-sensor || true
rpm -q snapshot gnome-software flatpak xdg-desktop-portal xdg-desktop-portal-gtk \
      iio-sensor-proxy pipewire wireplumber 2>/dev/null || true
systemctl --user --no-pager --failed 2>/dev/null || true
systemctl --no-pager --failed 2>/dev/null || true
```

Confirm AArch64 package architecture, disk space/inodes, RPM database health, DNS/HTTPS, active Wayland user, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, session bus, `XDG_CURRENT_DESKTOP`, DRM/headless output identity, framebuffer dimensions, whether `/dev/input` transforms are owned by libinput/Phoc/custom code, and persistent file locations. Never display Wi-Fi passwords or user secrets in logs.

Make a dated A53 baseline and rollback archive of the *userspace files that will be edited*. Record git HEAD, running service definitions, source hashes, installed-package manifest, Flatpak remotes and user/system installations. Do not bulk-backup the entire device for a userspace-only mission.

Determine whether the user is connected through Mac or Fedora; use the actual available working serial toolchain. Test recovery from a crashed UI over USB without killing that connection.

---

# 2. CAMERA BACKEND TRIAGE — KNOW THE HARDWARE REALITY

Study the A52 `HARDWARE-BLOCKERS.md`, the provided final gate table and all actual A52 device diagnostics. Preserve the finding: **rear sensor enumerated ≠ real ISP-managed preview frames**.

Re-run noninvasive evidence collection:

```sh
ls -l /dev/video* /dev/media* /dev/v4l-subdev* 2>/dev/null || true
command -v v4l2-ctl && v4l2-ctl --list-devices || true
command -v media-ctl && media-ctl -p -d /dev/media0 || true
command -v cam && cam -l || true
command -v gst-inspect-1.0 && gst-inspect-1.0 pipewiresrc libcamerasrc v4l2src || true
command -v pw-cli && pw-cli ls Node || true
journalctl -k -b --no-pager | grep -Ei 'fimc|isp|camera|sensor|v4l2|media|csi|mipi' | tail -150
```

Only run commands that exist on this image; document each failure. Inspect enumerated media graphs, sensor endpoint links, drivers bound to nodes, sensor probe success, ISP firmware, kernel config and compatible FIMC-IS/libcamera pipeline handlers. On this Exynos, the presence of a `/dev/video*` node does NOT prove that it produces real RGB/YUV frames. **Never substitute unrelated Android binary blobs or flash new firmware to make the UI appear complete.**

Classify whether a native app can receive frames through:
- V4L2 proper capture nodes;
- libcamera camera listing and a real pipeline handler;
- GStreamer `libcamerasrc`, `v4l2src` or PipeWire;
- or whether the missing step is kernel/ISP/firmware/source driver work.

If that underlying step remains blocked, keep camera state honest (`NO_CAMERA_PIPELINE`) but continue with **native app installation** and **software store** work. No infinite sensor polling that heats the locked handset.

---

# 3. INSTALL A REAL NATIVE CAMERA APPLICATION — PREFER GNOME SNAPSHOT

Fedora 43 carries the native Camera app **`snapshot`** (GNOME Snapshot). It is a GTK4/PipeWire camera application, not the Nuxel Camera PWA. The user explicitly asked to install a native application.

On-device package discovery FIRST:

```sh
dnf info snapshot 2>&1 || true
dnf repoquery --available --arch=aarch64 snapshot 2>&1 || true
dnf info pipewire wireplumber gstreamer1-plugin-pipewire 2>&1 || true
```

Determine real RPM package identifiers for all prerequisites from THIS device's enabled repositories; never assume a package exists merely because it exists on a desktop. Inspect sizes and `dnf install --assumeno snapshot` or equivalent dry-run before transaction. Check disk/storage, dependencies and that the DNF transaction will not remove essential Nuxel components.

Install the RPM after review:

```sh
sudo dnf install snapshot
```

Install/repair PipeWire, WirePlumber, GStreamer and libcamera integration **only as supported and justified**. GNOME Snapshot upstream lists PipeWire, WirePlumber, `gstreamer-pipewire`, `gst-plugin-gtk4`, `gst-plugins-bad` and optional libcamera as prerequisites. Verify on the handset; use correct Fedora package names. A Flatpak build of Snapshot is a secondary path if RPM cannot install, and it must be labelled Flatpak rather than native RPM.

Prove the application is really installed:
- `rpm -q snapshot` and actual executable/desktop entry;
- verify `.desktop` `Exec`, icon and app ID;
- launch it through Nuxel's **non-root active Wayland user session**;
- see the actual native GUI and controls, not a WebKit wrapper posing as a native window;
- Back/Home/Recents, portrait/landscape, on-screen keyboard and lockscreen interactions work;
- app exits cleanly and releases camera handles.

**Camera outcome is a separate physical gate:** if no backend camera frames exist, Snapshot may honestly show a No Camera message. Preserve that warning, collect useful logs, and keep the installed app available for subsequent kernel fixes. **Do not claim photo capture PASS.**

If Snapshot cannot run because current Wayland/EGL/GTK/GStreamer support is incomplete, fix reversible session/runtime issues. If infeasible, try a second **genuine native camera app** compatible with ARM64/Wayland, and report exact reasons for failure. Investigate mobile-friendly alternatives only if they are available and safe; do not present a simulated camera app as a native capture implementation.

Integrate Snapshot into Nuxel Home as `Camera (Native)` or with a clear default camera preference. Preserve the A52 custom Camera and Photos apps rather than deleting them. Expose truthful camera availability and a route to sensor diagnostic status.

---

# 4. COMPLETE NATIVE WAYLAND GTK/Qt APPLICATION LAUNCHING

A package manager being installed is **not** enough: Nuxel must let the owner open installed apps from Home and return to them.

Audit actual app launcher/backend and any prior A51 work. Implement one authoritative, **trusted native-app launcher** used by Nuxel Home and Nuxtore/GNOME Software integration. It must:
1. Enumerate XDG desktop entries from user and system application locations, honoring `Hidden`, `NoDisplay`, `TryExec`, desktop environment conditions, priority/overrides and installed executable availability.
2. Parse desktop-file launch fields using a standards-compliant API/GLib helper; never pass untrusted `.desktop` `Exec` strings through `shell=True` or `sh -c`.
3. Run normal apps as the logged-in unprivileged desktop user, using the correct `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, `DBUS_SESSION_BUS_ADDRESS`, `XDG_CURRENT_DESKTOP` and appropriate environment—not as root merely because the USB console is root.
4. Support GTK3, GTK4/libadwaita, Qt/Wayland, and Flatpak-generated `.desktop` launch entries where actual dependencies exist; do not blindly set `GDK_BACKEND=x11` or assume XWayland.
5. Bring up the OSK for text fields; make Back dismiss OSK first, then navigate; Home minimizes/returns Home; Recents tracks native windows without duplicated close handlers.
6. Respect lifecycle and focus when lockscreen/screen off occurs, and stop misidentifying a helper process as the foreground app.
7. Load app icons using XDG icon theme/search paths with sensible fallbacks, correct dimensions and no arbitrary filesystem/network reads from WebKit.
8. Do not grant arbitrary command execution or privilege escalation to a web page or local app. Only trusted launcher requests for validated installed applications may be accepted.
9. Update app list after RPM/Flatpak installs and removals without forcing a compositor restart or phone reboot.
10. Handle fullscreen/minimum size issues on narrow S10+ viewport; scrolling and touch targets remain usable.

Test at least one plain native GTK app and one Flatpak app launched from Nuxel Home. Record PIDs, process UIDs, window type, app ID and actual phone screenshots where authorized.

---

# 5. ENABLE REAL FLATPAK RUNTIME AND SANDBOXING

Do not equate “Flatpak binary installed” with “Flatpak works.” Inspect existing A51 artifacts first: perhaps dependencies/remotes were already deployed.

Check:

```sh
flatpak --version 2>&1 || true
flatpak remotes --show-details 2>&1 || true
flatpak list --columns=application,arch,origin,installation 2>&1 || true
flatpak installations 2>&1 || true
flatpak --supported-arches 2>&1 || true
command -v bwrap || true
zgrep -E 'CONFIG_USER_NS|CONFIG_PID_NS|CONFIG_NET_NS|CONFIG_SECCOMP|CONFIG_SECCOMP_FILTER' /proc/config.gz 2>/dev/null || true
cat /proc/sys/user/max_user_namespaces 2>/dev/null || true
```

Confirm actual namespace, seccomp, mount and bubblewrap feasibility on the current Samsung **4.14 vendor kernel**. Perform a safe, non-privileged sandbox smoke test as the desktop user. **Never disable sandboxing, globally loosen SELinux/security policies, or casually make bubblewrap setuid to claim success.** A kernel feature blocker becomes `BLOCKED_KERNEL` with exact config/errno and a future kernel plan, not a fake PASS.

If safe and supported, install missing `flatpak` and required portal packages through Fedora repos after a transaction preview. Use `flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo` only after working HTTPS/DNS and with appropriate owner control; verify trusted remote metadata. Fedora Flatpak remote is optional and should not silently replace Flathub.

Distinguish system-wide vs per-user Flatpak installations and their permissions. Confirm the logged-in Nuxel graphical user can install, run and remove software as intended. Confirm runtimes can be downloaded and checksummed, and sufficient free storage remains.

Try a small known AArch64-compatible Flatpak through Flathub, **after verifying the app ID and ARM64 remote availability on device**. `org.gnome.Calculator` is a candidate, not a guarantee of compatibility with this firmware/session. Verify:
- downloads completed;
- a real sandbox started;
- `flatpak ps` lists it when running;
- real native graphical window appears;
- keyboard and touch work;
- application integrates into Home and Recents;
- app removal leaves clean results.

Keep Flatpak default security boundaries. Diagnose file chooser, URI opener, camera, settings, notifications, screen capture, secrets and other portal behavior individually rather than forcing a broad `--filesystem=host` or `--device=all` override.

---

# 6. PORTALS, PIPEWIRE, POLKIT, APPSTREAM AND SESSION

Install and configure **`xdg-desktop-portal`** and a compatible backend for the Nuxel Phoc/wlroots session. `xdg-desktop-portal-gtk` typically supports desktop interaction/file chooser, while wlroots-oriented implementations may provide screencast depending on the build; do not assume that a GNOME-only backend is usable under Phoc. Inspect supported interfaces and choose with test evidence.

Tasks:
- Determine which `portals.conf` is selected for `XDG_CURRENT_DESKTOP` on Nuxel and which backends are registered.
- Verify real session D-Bus discovery; portal services are user/session scoped where appropriate.
- Test FileChooser, OpenURI, Settings, and other needed portals from **a sandboxed application**, not just D-Bus introspection.
- Audit A52's private `org.nuxel.Camera`: never advertise it as `org.freedesktop.portal.Camera`. If upstream camera portal APIs are used by Snapshot/Flatpak, deploy them accurately, with correct PipeWire negotiation and denial behavior. No user-space proxy can synthesize absent real sensor frames.
- Ensure `pipewire`, `wireplumber` and gstreamer services are started as correct user, with persistent-but-idle-safe lifecycle.
- Correct polkit auth agent behavior for graphical package installation. Never run GNOME Software itself as root or silently authorize RPM installs from untrusted web content.
- Populate and refresh AppStream metadata using distribution-supported tooling; test actual search results, screenshots, categories and install states.
- Ensure portal or store background services don't spin or hold CPU wakelocks when the screen is off.

---

# 7. INSTALL A GRAPHICAL SOFTWARE STORE — PREFER GNOME SOFTWARE

The user wants a software store able to install **native Fedora RPM applications and Flatpaks** from the phone itself. Start with **GNOME Software** because Fedora 43 packages it, and its 49.x package includes a Flatpak plugin plus PackageKit-based RPM integration. Do **NOT** assume a separately named `gnome-software-plugin-flatpak` Fedora package is needed. Discover actual packages/plugins on-device.

Preparation:

```sh
dnf info gnome-software PackageKit 2>&1 || true
dnf repoquery --available --arch=aarch64 gnome-software PackageKit 2>&1 || true
dnf install --assumeno gnome-software 2>&1 || true
```

Review transaction dependencies, RPM removals, disk footprint and compatibility with lightweight Nuxel stack. Avoid installing all of GNOME Shell/GDM just to obtain an app store; GNOME Software is intended to be an app, not to replace Phoc/Nuxel Home.

Proceed with a non-destructive, approved normal `dnf install gnome-software` transaction after reviewing the dry run. Verify the installed plugin files and PackageKit service, Flatpak plugin and AppStream availability. Fedora 43's GNOME Software 49.4 listing has `libgs_plugin_flatpak.so` and `libgs_plugin_packagekit.so` in the core package; check actual on-device package version and layout.

Required phone-user experience:
- A visible, working **Software** entry in Nuxel Home and app drawer (GNOME Software directly or a clearly branded Nuxel shortcut).
- Search **real** Fedora RPM catalog and **real** Flatpak/Flathub catalog, with source/type visible and accurate available/installed states.
- Tap an app, review name/source/package/perms/storage, install it through correct polkit/PackageKit or Flatpak path.
- Show real transaction progress and final success/failure.
- Launch installed app from store, and separately from Nuxel Home.
- Remove an installed test app through store and see icon disappear from Home.
- Update an installed app or accurately show no updates when none are available.
- No admin-password prompt trapped behind Nuxel keyboard or lockscreen overlay.
- No app store crash when resized/rotated or when network unavailable.
- No forced overnight auto update/download loop causing heat or data consumption.

If GNOME Software is genuinely incompatible with the S10+ session/display/graphics or demands too much memory, **do not silently replace the system GUI**. Build an alternative lightweight native package/store frontend only after documenting why GNOME Software failed, with safe backends (PackageKit/Flatpak) and explicit confirmation for privileged installs. Reuse any existing **Nuxtore** shell only if it becomes a working package manager, not a fake catalogue.

---

# 8. PROVE RPM INSTALLATION THROUGH THE GRAPHICAL STORE

Pick a small native ARM64 GTK application available in Fedora repositories (e.g. Calculator), verifying the actual name via `dnf info`/`repoquery` before the transaction. From the **phone's GNOME Software interface**, not the root USB console:
1. Search app.
2. Open details and identify source Fedora RPM.
3. Install.
4. Authorize through working polkit agent if asked.
5. Launch and interact using touch/keyboard.
6. Return Home and reopen the installed app via app drawer.
7. Check process UID and package name via terminal.
8. Test uninstall from GUI with a disposable test app.

Keep logs with transaction ID, RPM NEVRA, architecture, UI action, process ID and physical verification. Protect all critical Nuxel packages from removal through the store.

If PackageKit backend for Fedora 43 has conflicts with DNF5 or rpmdb locking, identify the exact backend and fix using distro-supported package servicing rather than issuing raw RPM database hacks.

---

# 9. PROVE FLATPAK INSTALLATION THROUGH THE GRAPHICAL STORE

Repeat analogous test for one **verified AArch64 Flatpak**:
1. Search verified app in store with Flathub enabled.
2. Show origin and sandbox permissions.
3. Install real runtime/app.
4. Observe real download progress.
5. Confirm `flatpak list` reports `aarch64` entry.
6. Launch native graphical window on real phone and interact.
7. Close and reopen from Nuxel Home; verify desktop integration.
8. Uninstall safely (or leave approved test app installed at owner preference).

Do not report success from a CLI-only Flatpak install that cannot create a window. If Flatpak is blocked by the 4.14 kernel, record precisely which kernel option/syscall/permission blocks the sandbox, demonstrate that native RPM installation still works, and offer the most minimal safe future remediation (possibly a separate kernel migration mission).

---

# 10. ORIENTATION: ONE REAL FIVE-MODE MANAGER

**Current owner complaint:** Quick Settings/Settings only expose **Portrait** and **Auto**, and auto/rotation does not reliably rotate the whole phone. Earlier A49 requested more modes. Implement these exact **five primary modes**, displayed consistently in Quick Settings **and** Settings:

| UI label | Stable API value | Allowed target orientation |
|---|---|---|
| **Auto** | `auto` | Upright portrait (0°), upside-down portrait (180°), landscape 90°, landscape 270° |
| **Auto Portrait** | `auto_portrait` | Auto-select 0° or 180° only; never landscape |
| **Auto Landscape** | `auto_landscape` | Auto-select 90° or 270° only; never portrait |
| **Forced Portrait** | `portrait` | Fixed normal upright portrait, regardless of sensor |
| **Forced Landscape** | `landscape` | Fixed preferred landscape side (calibrate 90° vs 270°); regardless of sensor |

If previous A49 code already implemented *Forced Reverse Portrait/Reverse Landscape*, preserve them in advanced settings or backwards-compatible APIs as desired; **do not let advanced options displace or hide the five requested core modes**. Do not collapse all auto modes into a single boolean. Current Quick Settings may use a single tile plus a long-press/selection dialog; all five must be discoverable, selectable and truthful.

**Single source of truth:** Implement a stable orientation service/state API with one persisted enum. Connect Settings, Quick Settings, display manager, input transforms, status indicator and lockscreen through it. No competing JS/backend flags, startup races, CSS hacks, or hard-coded transforms for phones other than this target.

---

# 11. AUTO-ROTATION INPUT: ACCELEROMETER, NOT GYRO ASSUMPTIONS

Audit the actual S10+ accelerometer/gyro access path:
- `/sys/bus/iio/devices/`, `/dev/iio:device*`, `iio_info` if present;
- vendor input event nodes with accelerometer capability;
- iio-sensor-proxy / `monitor-sensor` and D-Bus sensor claim API;
- sensor orientation mounting matrix/device tree, scale, channel labels and physical calibration;
- timestamps/update frequencies and whether sensors operate during display on/off.

The **accelerometer/gravity estimate** normally determines static orientation; a gyroscope alone is not sufficient to determine absolute gravity direction. If sensors don't expose actual acceleration data, report a hardware/kernel `BLOCKED_SENSOR` gate, while ensuring **Forced Portrait** and **Forced Landscape** work regardless.

Reconstruct the device-to-screen mapping empirically: place handset upright, upside down, left landscape, right landscape; record actual measured gravity vectors and the display orientation. Detect face-up/face-down and uncertain orientation; **do not rotate randomly when flat**. Respect orientation locks, ignore tilt noise, and don't let handset vibration generate false rotation.

Implement hysteresis, sample smoothing, cooldown and stable dwell time (e.g. 350–650ms calibrated by measurement), with no unbounded event-rate polling, no unnecessary daemon busy loops, and power suspension when lockscreen is off if appropriate. Resume cleanly on wake and apply stored mode.

If IIO is unavailable but a stable vendor accelerometer input API is available, write a bounded adapter that outputs the same normalized orientation events with evidence. **Do not invent accelerometer readings.**

---

# 12. ROTATE THE REAL WAYLAND OUTPUT **AND** THE TOUCH COORDINATES

A50 identified that some historical Nuxel builds used a Phoc **headless** Wayland output + `nuxel-wl-fb` framebuffer presentation to the physical Samsung display. That architecture may still be present. Confirm the CURRENT display path before changing transforms.

The actual goal is **physical, global OS rotation**, including native GTK/Flatpak windows, Home, launcher, keyboard, menus, lockscreen and touch input. It must not be a CSS rotation of the Nuxel Home DOM.

Investigate available Phoc / wlroots output-management protocols, `wlr-randr` or direct compositor APIs, current output scale, logical/physical geometry and whether `phoc.ini` changes require a compositor restart. `wlr-randr --transform` supports normal/90/180/270 where the compositor advertises the output protocol, but **headless or custom framebuffer bridging may require a compatible transform in the presenter**. Never assume command invocation succeeds just because it exits zero; inspect the output and physical panel.

**Exact requirements:**
- Change the compositor output transform through a supported path; preserve active clients without forced restarts.
- If `nuxel-wl-fb` performs panel rotation/scaling, apply the correct corresponding pixel transform exactly once. Avoid double rotation, stretched frames, clipping, incorrectly swapped width/height, tearing, or out-of-bounds framebuffer accesses.
- Update logical width and height, viewport, screen safe areas, dock positions and status bar constraints; landscape UI remains readable and touch-friendly.
- Update touchscreen/libinput coordinate transform or calibrated mapping so tapping a UI element lands on that element in all orientations. Do not only rotate rendered pixels.
- Handle keyboard overlays, drag-to-unlock and edge gestures correctly in each orientation.
- Ensure screenshots and screen mirroring follow the same orientation as the visible phone.
- Retain physical display mode and A50 performance optimizations unless measurement justifies changes. The task is rotation, not a blind resolution overhaul.
- Make mode/state survive reboot; apply saved choice only when output and input devices are ready, not before.

Implement an atomic-ish transition: orient → compositor/presenter ack → touch transform ack → UI resize → announce active orientation; if any stage fails, revert safely to last functional orientation. On startup, never get trapped in an unusable upside-down display with no way to return to portrait. Provide a USB-shell recovery command and safe on-device Reset to Portrait action.

**Examples to investigate, not blindly execute:**

```sh
wlr-randr --help
wlr-randr --dryrun --output ACTUAL_OUTPUT_NAME --transform 90
monitor-sensor
```

The live output identifier must be discovered. A `--dryrun` syntax may vary with installed version; inspect it. `phoc.ini` specifies `rotate`, but file changes alone generally require compositor reinitialization and should not be used for routine live rotation.

---

# 13. COMPLETE QUICK SETTINGS + SETTINGS UI

In **Quick Settings**:
- Orientation tile displays active mode name, not just Auto/Portrait.
- Tap opens the five-choice selector, or use a sensible short-tap cycle plus long-press menu if compatible with the existing UI. All five modes must be reachable from Quick Settings.
- On selection, show progress/ack and current result; errors are displayed clearly and stale mode state is rolled back.
- Keep orientation selector usable in both portrait and landscape without overlapping status panels or lockscreen.

In **Settings > Display > Orientation** (or established Nuxel location):
- The exact five options appear with concise descriptions.
- Current selection is persistent and mirrors Quick Settings immediately.
- Show sensor availability and actual active angle in an optional diagnostics line.
- If accelerometer is not usable, auto choices are visibly disabled with accurate explanation; forced modes must continue working.
- Provide Reset to Portrait and calibration diagnostics.

Preserve the Nuxel-themed visual design and haptic keyboard settings. Do not revive the duplicate blue keyboard or break Back/Home gestures.

---

# 14. POWER, PERFORMANCE, THERMALS, STORAGE AND SECURITY

- Installing GNOME Software may add substantial package/runtime footprint; measure delta in disk use, RAM, cold start latency and battery impact. Don't optimize by disabling necessary security services.
- Camera and sensor services must sleep/stop polling while unused, and release handles after Home/lock/timeout; verify with `/proc`/sysfs counters rather than claiming idle-only temperature values imply safe power use.
- Orientations must not introduce full-screen software redraw loops above display refresh or restart native apps each flip.
- Keep default background update checks conservative/offline-safe; user can opt in to automatic downloads.
- Install native apps under correct owner account, never as root GUI instances.
- Ensure package-manager privileged actions require polkit authorization; restrict bridge verbs to trusted callers; prevent shell injection, malicious `.desktop` execution, untrusted Flatpak privilege overrides, and app-store root escalation.
- If storage is limited, provide accurate capacity/free-space warnings rather than filling persistent Nuxel userdata with Flatpak runtimes.
- Maintain trust boundaries for GNOME Camera access; a custom `org.nuxel.Camera` service must not impersonate the XDG Camera portal.
- No unsafe kernel patching, low-level clock overclocking, SElinux/global security disabling, partition writes or network credential exposure.

---

# 15. TEST MATRIX (OFFLINE AND PHYSICAL)

### Camera installation
- RPM package actually installed and owns a native `.desktop` entry.
- Snapshot appears in Nuxel Home; user can open/close it through native Wayland.
- Correct `NO_CAMERA_PIPELINE` state if kernel still provides no real frames.
- If new hardware pipeline becomes available without kernel flashing, real frame only counts when physical imagery and saved file are verified on S10+.
- No fake success because native GUI starts.

### Software store + apps
- GNOME Software opens from Home, loads real metadata; users can search.
- RPM app install **from GUI** → launch → input → home → reopen → uninstall.
- Flatpak app install **from GUI** → sandbox launch → input → home → reopen → uninstall.
- App catalogue refreshes automatically on install/remove.
- Store respects authentication, signature/checksum and permissions.
- Offline/network-error UI is truthful; no infinite retry or thermal run-away.
- Restart Nuxel Home / user session and verify installed apps persist.
- User-approved reboot: verify RPM/Flatpak app entries, Flatpak portal services and GNOME Software still work.

### Orientation physical acceptance
- Settings shows all five modes and Quick Settings exposes all five.
- Forced Portrait: screen and touch fixed upright when rotating device in hands.
- Forced Landscape: entire graphical session and touch transform landscape.
- Auto: rotates through all four positions with correct screen+touch.
- Auto Portrait: toggles upright/upside-down only, refuses landscape.
- Auto Landscape: toggles left/right landscape only, refuses portrait.
- Face-up on a table holds last stable choice without jitter.
- Native Snapshot, native GTK Calculator, Flatpak app, Camera PWA and Home all resize properly.
- OSK and Back/Home/Recents operate correctly in portrait/landscape.
- Lock/wake preserves configured mode and working penguin unlock gesture.
- User-approved reboot preserves mode; USB recovery route restores normal portrait if anything breaks.

### Physical proof
For each PASS record the exact handset session/process, selected option, screenshot/photo, action outcome, relevant logs, and active transform/sensor measurements. **Do not upgrade offline tests to physical PASS.**

---

# 16. IMPLEMENTATION ORDER & ROLLBACK

Follow this sequence, with a small commit/checkpoint after each milestone:

**M0 — Inventory and safety.** Current repo, USB recovery, package manifest, camera frame gates, session variables, storage, backups.

**M1 — Real native GTK launch path.** Validate a small native Wayland app first so GUI package installation is not blocked by an unfixable launcher.

**M2 — Native Camera (Snapshot).** Install verified Fedora 43 `snapshot`, integrate Home, test real app; report frame blocker honestly.

**M3 — Flatpak prerequisites.** Check kernel namespace/sandbox + D-Bus + portals, install missing pieces safely; fix barriers without dropping sandbox security.

**M4 — GNOME Software.** Install from RPM, integrate Home, load RPM and Flatpak catalogs, test one native and one Flatpak GUI install and removal.

**M5 — Orientation hardware & compositor backend.** Real sensors, transforms, input remapping, recovery, five mode enum.

**M6 — UI integration.** Settings and Quick Settings five-way selector, persisted settings, runtime sync.

**M7 — Physical acceptance and reboot persistence.** Real taps, app launches, rotations, locks, performance, user-approved reboot if needed.

Per milestone record `source diff`, `test log`, `deployment receipt`, `process IDs`, `observed device result`, `rollback instructions`, and `git commit`. Avoid merging unrelated features into one unreviewable commit. Deploy incremental userspace changes over USB. Before restarting the compositor or critical bridge, stage a timed/shell accessible rollback on the existing USB console; do not self-disable recovery.

---

# 17. REPORT REQUIRED

Generate at least:

- `docs/a53/BASELINE-AND-HARDWARE.md`
- `docs/a53/NATIVE-CAMERA-SNAPSHOT.md`
- `docs/a53/CAMERA-PIPELINE-BLOCKERS.md` (if any)
- `docs/a53/NATIVE-APPLICATION-LAUNCHER.md`
- `docs/a53/FLATPAK-SANDBOX-PORTALS.md`
- `docs/a53/GNOME-SOFTWARE-RPM-FLATPAK.md`
- `docs/a53/ORIENTATION-FIVE-MODE-IMPLEMENTATION.md`
- `docs/a53/PHYSICAL-ACCEPTANCE.md`
- `docs/a53/ROLLBACK.md`
- `docs/a53/FINAL-STATUS.md`

Final gate table must clearly separate:

1. Native camera app installed.
2. Native camera app shown on device.
3. Real S10+ camera frame captured (separate hardware gate).
4. GNOME Software installed and displayed.
5. Real RPM app installation/launch/removal from store.
6. Flatpak sandbox supported, or exact kernel blocker.
7. Real Flatpak installation/launch/removal from store.
8. Five modes exposed in Settings.
9. Five modes exposed in Quick Settings.
10. Physical screen and touch orientation correctness.
11. Persistence across session restart/reboot (reboot only with approval).
12. No regressions in Nuxel Home, lockscreen, keyboard, USB console, Wi-Fi, A52 media files, power and thermals.

If a gate is blocked by the Samsung 4.14 kernel, exact firmware/ISP or portal limitations, **say precisely so and still ship the independent working components**. Do not claim that installing GNOME Snapshot cures a nonfunctional Exynos camera ISP. Do not call a UI selector “working rotation” without correct display and touch movement.

## FINAL MISSION DIRECTIVE

**MAKE NUXEL INSTALL REAL SOFTWARE.** Deliver a launchable native Camera app, an actual GNOME Software RPM+Flatpak store with working unprivileged app launching, and five working orientation modes on the physical Galaxy S10+.

**Verify, install, integrate, rotate, test, persist, report. No fake PASS statuses.**

**UNLEASH PENGUIN PWNAGE 2000. 🐧🔥**

---

## MAINTAINER REFERENCES TO CHECK AGAINST THE LIVE MACHINE

- Fedora `snapshot` package: https://packages.fedoraproject.org/pkgs/snapshot/snapshot/
- GNOME Snapshot requirements: https://github.com/GNOME/snapshot
- Fedora `gnome-software` package: https://packages.fedoraproject.org/pkgs/gnome-software/gnome-software/
- Fedora Flatpak usage: https://developer.fedoraproject.org/deployment/flatpak/flatpak-usage.html
- Flatpak user namespace requirements: https://github.com/flatpak/flatpak/wiki/User-namespace-requirements
- XDG Desktop Portal: https://flatpak.github.io/xdg-desktop-portal/docs/
- Phoc display configuration: https://manpages.debian.org/trixie/phoc/phoc.ini.5.en.html
- wlr-randr output transform: https://man.archlinux.org/man/wlr-randr.1.en
- Fedora IIO Sensor Proxy: https://packages.fedoraproject.org/pkgs/iio-sensor-proxy/iio-sensor-proxy/

Use these only as upstream reference; the **phone's real state and source** are authoritative.
