# 🐧🔥 NUXEL 21000 — OPERATION PENGUIN INTERNET UNLEASHED
## Current-repository + real-device recovery, dependency installation, hardware bring-up, media completion, shell polish, and physically verified convergence

**Execution:** GPT-5.6 Sol (High/Extra High) through Codex, or DeepSeek-v4-pro-thinking through the owner's CodeSeeQ `csft`, **on the actual current Nuxel Git checkout**. Host may be Fedora 43 laptop or MacBook: discover tools/transport, do not assume host OS. **Device:** Samsung Galaxy S10+ SM-G975F `beyond2lte` Exynos 9820, Nuxel independent Fedora ARM64 userland, historically working Linux 4.14.253 downstream kernel. **Current state is unknown until freshly audited.** Mission is active diagnosis, safe implementation, controlled deployment, real-device tests, and reporting. Do not merely compose a plan; do not claim to have tested any physical function you cannot access.

## WHY 21000 IS DIFFERENT FROM 18000

The owner now reports **working Wi-Fi, DNS, TLS, web browsing and actual internet on the phone**. The A69/18000 report (bundled as `references/ARCHIVED-FINAL-STATUS.md`, recorded 2026-10-24) predates that owner-confirmed breakthrough and cannot be used to classify the current phone's connection as offline. You may use online Fedora repositories, upstream documentation, upstream source history and legally distributable firmware documentation for dependency discovery and safe restoration. Internet is a powerful new tool **but not evidence that proprietary device firmware exists or will run**. The older A69 report is forensic context, **NOT** today's diagnosis. Your top priority is fresh **REPO↔PHONE↔UPSTREAM** three-way reconciliation so already-working fixes are protected.

The attached complete prior mission `references/NUXEL-18000-original-requirements.md` contains 13 requirements and a 35-test acceptance matrix; it is a mandatory contract. The newest USB lockscreen-indicator work from 19000/20000 is protected baseline functionality, not an invitation to move or resize icons. Older A69 artifacts can help pinpoint likely subsystems, but their truth/status labels expire unless reproduced on this current runtime.

**Goal:** make everything within the previous 18000 scope genuinely functional to the greatest extent feasible on the present hardware/4.14 kernel: reliable battery on first lockscreen render, exactly one global nav bar, correct Back/Home/Tabs and application stacking, real speaker/Bluetooth/USB audio and media playback, actual rotation/sensors when hardware supports it, honest GPS and useful Maps, NFC where kernel/controller allows, fast volume controls, further smoothness and delightful restrained animations; preserve Wi-Fi, TLS, browser, SnekByte, recovery, lockscreen and the latest USB penguin-indicator positions/size/logic.

---

# 00. SOURCE-OF-TRUTH HIERARCHY / WHAT NOT TO DO

1. **Fresh live phone + actual current checkout** outrank any historic report or archived ZIP. Show `git status --short --branch`, `git rev-parse HEAD`, last 20 commits, current system services, running binaries, deployed hashes, known-good backup records and physical telemetry. An earlier provided archive `nuxel-main (4)(1).zip` is only a snapshot; if this workspace contains a newer Git checkout, prefer that newer tree. Do NOT forcibly checkout to the archived commit (`37bc270` in A69).
2. Owner-reported current working internet is a protected baseline. **Prove** it with real Wi-Fi state, default route, DNS, verified TLS and the Nuxel browser. If it fails during an audit, flag regression rather than rolling back the phone or rewriting Wi-Fi credentials.
3. Preserve uncommitted work, and do not overwrite source with historical ZIPs; checkpoint in a new feature branch or worktree, manifest backups with SHA256 and modes, stage in isolated directory, peer-check changes, and document a rollback rehearsed against a scratch staging tree.
4. Discover actual device transport. Prior report used **macOS `/dev/cu.usbmodem2201` USB CDC-ACM** and had no ADB. On Fedora discover real `/dev/ttyACM*` and permissions, connect with owner's existing scripts; never assume adb or a hard-coded serial path. Test a **separate recovery route** before any USB mode/driver/BT changes. Do not close only console or shell session.
5. **No flashing** kernel, boot image, recovery, dtb, partition table, persistent modem settings, Android/HAL replacements or bootloader; no broad Fedora distribution upgrade, no third-party RPM trust bypasses, no arbitrary chmod 777, and no insecure TLS bypass. Explicit owner approval before service disruption, privileged package install, RF behavior changes, firmware deployment, USB-role switch or reboot. If the current 4.14 kernel lacks hardware APIs, document boundary rather than gambling on 6.x.
6. One deployment owner, sequential changes on the phone; do not run two live agents on separate hosts at once. Give every modified runtime component an owner and exact install path.
7. Never invent physical proof. Valid statuses: `PASS_PHYSICAL`, `PASS_DEVICE_RUNTIME`, `PASS_OFFLINE_ONLY`, `BLOCKED_FIRMWARE`, `BLOCKED_KERNEL`, `BLOCKED_DEPENDENCY`, `BLOCKED_EQUIPMENT`, `FAILED`, `NOT_TESTED`. `PASS_DEVICE_RUNTIME` indicates service/data proof but not human-observed hardware result. Use all statuses accurately, no fake percentage, fake GPS fix, fake audio cue or synthetically successful driver probing.
8. All sensitive logs/screenshots stay local and are redacted before sharing: Wi-Fi credentials, MACs, Bluetooth IDs/names, personal locations, USB serial, media filenames, contacts. No credential collection or unlocking around privacy controls.

---

# 01. MANDATORY FORENSIC PRE-FLIGHT — REPO ↔ PHONE ↔ PRIOR A69

Read all `references/` files, especially A69's `FINAL-STATUS.md` and `PREFLIGHT.md`. Use them as leads, not current facts.

**A69 historical findings to test rather than assume:**

- Boot battery: kernel `/sys/class/power_supply/battery/capacity` accurate immediately; old `pwa/nuxel-home/js/lockscreen.js` queried host first and 1s/3s; lockscreen status marked `PASS_DEVICE_RUNTIME`, not guaranteed owner-visible result.
- Double nav: native `/usr/lib/nuxel/nuxel-navdock` and DOM `#system-navigation` both drawn until `.native-nav-present #system-navigation { display:none; }`; older code deployed under `/usr/share/nuxel/pwa/nuxel-home/`. Verify newer CSS and compositor role instead of reintroducing fallback overlap.
- App drawer: `_dismissLauncherChrome()` from `pwa/nuxel-home/js/app.js`, `body[data-app-state="ACTIVE"|"LAUNCHING"]` hide drawer/dock; confirm the latest source still has equivalent and phone hashes match.
- Audio: `beyond-madera` ALSA card; ABox, Cirrus `CS47L93` codec and two `CS35L40` speaker amps; old agent reported missing `*.wmfw` DSP blobs, missing UCM `HiFi.conf`, PipeWire, WirePlumber and ALSA utilities. **Do not conclude firmware is mandatory merely because one old diagnostic claimed absent**; independently determine which DSP routes are required and whether any safe PCM test is feasible. No unverified amp-power writes.
- Orientation: BCM47752KUB1G Samsung sensor hub (`ssp,BCM4773`), STM LSM6DSO accelerometer/gyro, `ssp_down == true`, `raw_data=0,0,0`, seven UI policies but no real sensor event. Confirm driver + firmware/boot protocol and whether the sensors can be initialized with trustworthy licensed components without kernel swap.
- GNSS: no working hardware GNSS under the prior down SSP; `geoclue2` could be used only for consented approximate network position. NFC: `sec-nfc@27` registered but not bound to controller; may be DT/power/bus integration rather than just a missing app.
- Bluetooth: BCM43xx rfkill `soft=1` / `hard=0`; no BlueZ tool or active HCI and claimed firmware absent. Distinguish soft block, transport HCI not registered, missing firmware, wrong UART service and absence of userspace manager.
- 18000 had **no network and no DNF**, so Fedora ARM64 package installation and online Maps were blocked. That limitation MUST be retested; owner now reports Internet working.
- Older phone ran Linux `4.14.253` Fedora 43 ARM64; its software rendering was heavy. **Do not assume any newer acceleration or system package state without remeasuring.**

**Mandatory inspection entry points present in the archived source (confirm existence in CURRENT tree):**

```
pwa/nuxel-home/js/{lockscreen.js,lockscreen-indicators.js,status-bar.js,app.js,navigation.js,launcher.js,apps.js,home-settings.js}
pwa/nuxel-home/css/style.css
services/nuxel-bridge/src/{bridge.py,api.py,system_indicators.py}
services/nuxel-orientation/nuxel_orientation/{sensors.py,policy.py,apply.py}
services/nuxel-orientation/nuxel-orientationd
services/nuxel-session/systemd/{nuxel-wayland.service,nuxel-wl-fb.service,nuxel-button-manager.service}
configs/s10plus/alsa-ucm/{SamsungBeyond2/HiFi.conf,SamsungBeyond2/SamsungBeyond2.conf,beyond-madera}
configs/s10plus/{pipewire,wireplumber,display}
configs/nuxel/{bluetooth,gnss,nfc,orientation,sensors,power}
tools/s10plus/a33/{nuxelctl,nuxel-audio-diag.sh,nuxel-bluetooth-diag.sh,nuxel-sensors-diag.sh,nuxel-gnss-diag.sh,nuxel-nfc-diag.sh,nuxel-headphone-diag.sh,nuxel-typec-diag.sh,nuxel-wl-fb.c,nuxel-pwa-host.c,nuxel-button-manager.c}
pwa/nuxel-apps/{browser,calculator,camera-gallery,...}
shell/nuxel-shell/
docs/a69/{FINAL-STATUS.md,PREFLIGHT.md,LIVE-VS-REPO.md,ROTATION-HARDWARE-BOUNDARY.md,requirements.csv,test-matrix.csv}
```

**Path notes:** the prior ZIP also has `configs/s10plus/alsa-ucm/SamsungBeyond2/HiFi.conf` but A69 claimed that `/usr/share/alsa/ucm2/beyond-madera/HiFi.conf` was absent on phone. This is an important *repo-vs-deployment vs ALSA card-name mismatch* to investigate—verify whether config exists but was NEVER copied to the correct card alias / UCM location. That does not prove it will fix missing DSP firmware. Do not assume `SamsungBeyond2` equals actual card ID without inspecting UCM configuration and ALSA API.

**Deliver preflight output before touching packages:**

- `docs/a72-21000/00-BASELINE.md`: model, kernel, Fedora release, AArch64, repo branch/dirty files, console path, running process/service versions, persistent storage and free space, temp/thermal, battery %, network status, DNS/TLS HTTPS, package manager availability.
- `docs/a72-21000/01-REPO-LIVE-DELTA.md`: each relevant source path, deployed path, source SHA256, live SHA256, current effective service unit and installed binary, evidence of stale WebKit caches or duplicated launch units.
- `docs/a72-21000/02-RECOVERY-PLAN.md`: tested backup manifest, restore and systemd reload commands, target known-good state, explicit approval boundaries.
- `docs/a72-21000/03-HARDWARE-DRIVER-MATRIX.md`: kernel DT probe, `/dev` nodes, firmware requests, sound cards, BT HCI, SSP/IIO, NFC, GNSS, USB host.
- `docs/a72-21000/04-INTERNET-AND-PACKAGE-MANAGER.md`: proof of phone/host internet and exact safe package transaction plan.
- For each original A69-01…13 create an issue ledger: **reported symptom → prior workaround → actual now → true root cause → minimal verified fix → tests → deployed hash → physical outcome**.

Safe initial READ-ONLY commands *inside phone* where available (capture and redact):

```sh
uname -a; cat /etc/fedora-release; cat /etc/os-release
cat /sys/class/power_supply/battery/capacity 2>/dev/null || :
command -v dnf5 || :; command -v dnf || :; command -v rpm || :
rpm -qa | sort > /tmp/nuxel-a72-rpm-baseline.txt
nmcli -t -f GENERAL.STATE,GENERAL.CONNECTION dev show wlan0 2>/dev/null || :
ip route get 1.1.1.1 2>/dev/null || :
getent ahostsv4 www.fedoraproject.org 2>/dev/null | head -3
curl -sSIL --connect-timeout 5 --max-time 15 https://www.fedoraproject.org/ 2>&1 | head -25
cat /proc/asound/cards 2>/dev/null; cat /proc/asound/pcm 2>/dev/null
find /sys/class/sensors /sys/bus/iio/devices /sys/class/rfkill /sys/class/nfc /sys/class/gnss -maxdepth 2 -print 2>/dev/null | head -100
systemctl --no-pager --all list-units | grep -Ei 'nuxel|pipewire|wireplumber|blue|sensor|gps|nfc|phoc' | head -100
```

On host additionally compare `git diff`, `git log --date=iso -n 20`, selected installed RPM database and actual live hashes. No blindly running *host* dnf commands to believe they installed packages on *phone*.

---

# 02. INTERNET UNLEASHED — TRUSTED FEDORA ARM64 PACKAGE RESTORATION

Owner-confirmed mobile Internet now enables genuine package remediation. **Do this after baseline and safely**, not a `dnf upgrade -y` frenzy.

## 02A. Establish trustworthy connectivity end-to-end

Test (on phone, not just host): NetworkManager `ACTIVATED`, actual route, lease, resolvers, DNS, time synchronization for TLS certificate validity, verified HTTPS for Fedora mirrors and `https://www.google.nl` from Nuxel Browser. Check proxies, split DNS, captive portal, stale or mismatched DNS, network changes under screen off/wake. Capture real outcomes; do not print saved passwords. Preserve current Wi-Fi profiles/network code. If Internet temporarily drops, pause network-dependent stages without destabilizing phone.

## 02B. Bootstrap package manager correctly

A69 had **RPM but no `dnf`**. First check current `dnf`, `dnf5`, `microdnf`, `libdnf5`, rpm version and repo definitions on the PHONE. Fedora 43's DNF5 exists upstream (source https://packages.fedoraproject.org/pkgs/dnf5/dnf5/). If absent:

1. Record `rpm -qa`, Fedora release and architecture from phone; inspect free space/readonly mounts. Verify trusted Fedora 43 **aarch64** official RPM repos and cryptographic signature keys already trusted on device. Check signatures (`rpm -K`) and package NEVRA/provenance.
2. Resolve exact package + dependency closure using official Fedora 43 AArch64 repository metadata **without disabling signature checks**. Prefer safe staged root/sysroot or host aarch64 resolver with correct releasever/basearch and no host contamination; collect complete RPM set + hashes and verify signatures. If using Fedora host, host x86_64 `dnf` does not mean the packages are right for phone ARM64.
3. Preview complete transaction, conflicts/replacements, file owners, service unit impact and disk footprint. Do NOT `rpm --nodeps`, `--force`, `--replacefiles`, `--nosignature`, `curl | sh`, systemwide `distro-sync`, GPG bypass or `rpm -Uvh *.rpm` without dependency resolution. Ask explicit permission, install smallest needed correct package set, and verify the package manager can query/resolve/install a harmless package after boot/restart.
4. Treat `/usr` mount or image management policy as authoritative: if rootfs is image-managed/read-only, use supported persistent package layering/build process, not unsafe remounts. Document rollback of each installed RPM and version locks where sensible.
5. Once DNF5 is working, take advantage of its transactional preview/download mechanisms, but keep transactions **small and reviewable**.

Stage package families **only when needed and compatible:** `alsa-utils`, `alsa-ucm`, `pipewire`, `pipewire-alsa`, `wireplumber`, relevant `pipewire-plugin-*`, BlueZ (`bluez`, `bluez-tools` where available), `libspa`/BlueZ backend if packaged, `iio-sensor-proxy` if real sensor interface exists, `gpsd`/`geoclue2` if compatible, NFC reader tools appropriate to actual NCI transport, `vlc` including real GUI component when separated, `mpv` or separate lightweight music player, codec support if available in trusted enabled repositories, `usbutils`, `i2c-tools` for *read-only supported diagnostics*, `libinput-utils`, GStreamer plugin packages when needed. Confirm names/availability with real repo queries; no package list is a blind install command.

Log source URLs, signatures, versions, transaction dry-run, package size, dependencies, install receipts, service activation and rollback per family. Real packages mean **native ARM64 userland tools**; root availability and running process must be verified.

## 02C. Internet-assisted firmware research — safe/provenanced

For sound DSP blobs, Broadcom BT HCD, sensor-hub firmware and NFC controller only:

- Research official Samsung/vendor firmware distribution, exact **S10+ / beyond2lte Exynos** hardware revision, compatible Android/vendor source licensing, device-tree `firmware-name` / request_firmware paths and kernel driver ABI expected by the running 4.14 kernel. Inspect legally available firmware packages upstream and archived repo artifacts.
- Distinguish a driver that asks for firmware from a driver which can operate in bypass/fallback mode; map probe trace and I/O results. **Do not download arbitrary blobs or install firmware from unverified third-party mirrors**. No extraction of proprietary firmware from a device without owner's clear authorization and appropriate rights. No sending vendor images to external services.
- If owner provides firmware from their own compatible device/authorized source, hash, license, version, target revision, signature when available, staging location and expected request path, then ask permission before an isolated, reversible deployment. Test relevant service only, avoid overwriting Wi-Fi firmware.
- A `firmware downloaded` log is not proof of codec sound, sensor events, Bluetooth scanning or NFC tag read. Capture actual subsystem evidence.
- If no compatible lawful firmware can be found, mark precisely `BLOCKED_FIRMWARE` and continue all independently fixable userspace work.

---

# 03. A69-01 — LOCKSCREEN BATTERY FIRST-PAINT TRUTH

Reproduce *current* screen after cold boot. Compare monotonic timestamps: kernel battery capacity, `nuxel-metricsd`/host status, top status bar, lockscreen JS bridge initial response/refresh. Old A69 host-first fix may already be deployed; determine whether new bundle, WebKit cache or competing battery source reintroduced 0%. Eliminate hardcoded false `0`, reset-on-mount, late polling or lost subscription. One authoritative battery state with freshness timestamp, immediate host read if available, event-driven updates and retry on API initialization. Unknown renders `--%`, not 0% unless genuinely 0. Lockscreen never waits minutes after top-bar displays verified value. Test 3 approved cold boots and ten screen wake/unlock/lock cycles; capture physical screenshots and logs. **Preserve lockscreen artwork and the three USB penguins at their now-correct positions/sizes; don't redo 19000/20000.**

---

# 04. A69-02 + A69-13 — SINGLE NAV, REAL APP FOREGROUNDING AND CORRECT APP LIFECYCLE

Map the authoritative shell layers: native `nuxel-navdock` vs fallback DOM `#system-navigation`, `phoc` Wayland and `nuxel-pwa-host`; launcher/app drawer `z-index`, OSK, status bar, app focus, recents; distinguish real Wayland surface owner from HTML layout. Compare current styles with A69 `.native-nav-present #system-navigation`. Ensure **one visible and touchable triple bar per state**, the fallback shows only if native dock genuinely absent, no nav duplication during WebKit app transition, rotation, lockscreen or OSK. Don't hide both controls to suppress duplication.

Back semantics:
- Short Back dismisses OSK/modal if appropriate, then issues in-app history navigation to actually focused PWA/native app, when app can navigate back; at route root, a subsequent Back minimizes/returns to Home.
- Penguin Home **immediately** backgrounds active app, shows actual launcher wallpaper/widgets/app icons, focuses launcher, not just paint four app icons over still-visible app.
- Tabs/recents shows running apps correctly and raises chosen app; long Back kills foreground **non-system** app safely and does not terminate launcher/lockscreen.
- Applications drawer selection brings already running or newly mapped app above drawer, hides/demotes drawer atomically, transitions without stolen focus; if launch fails, show real failure. Support SnekByte, browser, Camera, Settings, Maps, VLC, MP3, native GTK/Qt, keyboard.
- Desktop 4-icon dock is absent above foreground apps; redundant top 'Home + app name' strip removed/disabled where owner requested while global escape remains. Respect app fullscreen vs nav policy.
- All controls always usable in fullscreen browser, navigation buttons stay visible or reveal with well-tested edge gesture according to settings. No CSS-only hack can outrank another compositor surface.

Physical test: at least 20 Home/Back/Tabs events across 8 apps, app drawer cold/return launches, 10 OSK cycles, no duplicate bar and no app behind drawer. Touch-down haptics if enabled; no duplicate event deliveries. Preserve current owner-configured gesture settings.

---

# 05. A69-03 + A69-10 — REAL EXYNOS SPEAKER AUDIO AND INSTANT VOLUME

This is a root-cause driver+codec+daemon exercise, not a UI-only “play beep” button. Actual old hardware inventory: Exynos ABox, `beyond-madera`, Cirrus CS47L93 and CS35L40×2. Verify latest kernel probes/codec controls and speaker amp enable sequence. Locate firmware request names, load statuses, UCM config source path, ALSA PCM capabilities. **Important discrepancy:** historical repo `configs/s10plus/alsa-ucm/SamsungBeyond2/HiFi.conf` exists while live UCM `beyond-madera/HiFi.conf` was reported absent; audit card name, `UCM2` alias, correct install root and actual mixer elements. Avoid writing guessed register values or unsafe gain settings.

Recover userspace with trusted ARM64 packages after DNF bootstrap if needed: `alsa-utils`, PipeWire, WirePlumber, policy/routing and actual session-level systemd user units. Distinguish missing package from missing card/codec firmware/amp power. Check service logs, `pactl`/`wpctl`/`aplay` and `amixer`, owner-approved safe low-volume signal to speaker through ALSA and PipeWire; audible proof from human, never solely a PCM stream return code.

Volume rocker: instrument kernel evdev keydown timestamp → `nuxel-button-manager` → actual mixer gain → UI OSD → audible change; measure median and p95 under idle and browser load, rapid taps and press-and-hold, make OSD immediate, avoid long await/keyup-only click or queued volume previews. No audio spikes or unsafe max gain. Restore boot/lock volume policy; ensure feedback sound scales with currently selected output volume and doesn't recurse into itself. Haptic intensity settings unchanged unless needed.

When codec speaker firmware remains unavailable, separately prove any safe alternative digital USB DAC or Bluetooth speaker route. No false “all audio fixed” merely because PipeWire now starts.

---

# 06. A69-07 — BLUETOOTH REAL HCI + UI MANAGER + SPEAKER PLAYBACK

Freshly enumerate Broadcom radio transport, rfkill hard/soft states, bt kernel modules, kernel DT UART/serdev protocol, HCI device and firmware request path, coexistence with already-working Wi-Fi. Previous `soft=1 hard=0` is an actionable lead; **do not confuse BlueZ installation with registered HCI hardware**. Safely unblock the correct Bluetooth rfkill only once physical driver and power prerequisites are clear; avoid disrupting existing radio/network stack. Install trusted BlueZ packages, enable correct service and DBus permissions, initialize firmware if legally available/proven compatible. Provide honest Settings manager: off/starting/searching/pairing/trusted/connected/disconnected/unavailable/error; discovery, named device, PIN/consent, connect/forget, stale entry cleanup and errors.

Then verify speaker playback end to end: HCI powered, discover actual owner speaker, pair/trust/connect via bluetoothctl/GUI, detect A2DP sink in WirePlumber/ PipeWire, play real file at safe level, volume and sink switching, switch back to wired speaker on disconnect. Protect device identity in logs. If transport or firmware absent after packages installed, `BLOCKED_FIRMWARE`/`BLOCKED_KERNEL`, not phantom paired UI. Do not disconnect Wi-Fi to attempt an unproven Bluetooth combo fix.

---

# 07. A69-08 — USB-C DIGITAL AUDIO, ACTIVE USB-C-TO-JACK, HEADSET JACK

Before tests classify actual phone USB role and keep USB Live Console recoverable. **Active USB-C DAC / USB audio headset:** correct host-mode negotiation, enumeration, `snd-usb-audio`, ALSA card, PipeWire sink, real sound/hotplug, auto-route and restored previous route on unplug. **Passive analog USB-C adapter:** requires device analog accessory mode and mux; installing DAC driver cannot magically support it. Separately test native S10+ 3.5mm jack via `madera-extcon` if available. Exercise physical equipment only with owner permission after a backup recovery method. Don't swap USB roles over the only recovery console. Capture equipment availability and `BLOCKED_EQUIPMENT` when no accessory exists.

---

# 08. A69-04 — ACCEL/GYRO/SSP AND SEVEN ROTATION MODES

Verify the *actual* Samsung sensor-hub state, not simulated raw values. Inspect `ssp` driver logs and DT, BCM47752KUB1G bus initialization, STM LSM6DSO raw gravity/rotation vectors, relevant sysfs/IIO/input interfaces and firmware request failures. With Internet, research properly licensed matching firmware/userspace and upstream driver/protocol sources for the **existing kernel**. If owner can provide a compatible authorized vendor payload, test isolated bring-up with approval, hash/provenance and rollback. A newer kernel is not required by default and is not authorized here.

Ensure that forced rotation modes remain available **even if SSP down**; seven-mode policy UI: Forced Portrait, Inverted Portrait, Landscape Left, Landscape Right, Auto All, Auto Portrait, Auto Landscape. Real Auto must read physical sensor changes and apply transforms to `phoc`, framebuffer bridge, touch orientation/coordinates, keyboard, global nav and app viewport. Determine actual transform/inversion and panel dimensions live. Distinguish `sensor unavailable` vs simulated events; never mark real rotation PASS from artificial IIO values or manual forced mode. Test portrait↔landscape physical turns (including upside-down when allowed), touch hit targets, screen lock and browse. Report exact hardware barrier if SSP cannot start.

---

# 09. A69-05 — GPS + MAPS: INTERNET IS AVAILABLE NOW

**Maps should be useful even if GPS is not.** Working Internet means implement/test real HTTPS map tiles, attribution, pan, zoom, search, tap location and graceful offline/error state using a policy-compliant map provider; obey usage limits/API requirements and don't hammer public OSM servers. Verify actual in-phone WebKit TLD/TLS path. No placeholder tiles. Optionally search/geocode via a legitimate supported provider with rate limits and consent. Location button requests explicit permission; permit a separately labeled approximate Wi-Fi/network location if user consents. Do not present IP geolocation as GPS.

GNSS: inspect actual DT driver, SSP link, identified GNSS transport/device and daemon (`gpsd` if appropriate), kernel events/NMEA data, stationary/open-sky status. Do not blindly connect to random `/dev/tty*`, send modem AT commands, alter cellular RF/baseband settings or upload precise location. If real hardware becomes available, physical satellite fix with owner permission and accuracy/satellites/time evidence; otherwise Maps gets PASS for online features and GNSS separately `BLOCKED_FIRMWARE/KERNEL`.

---

# 10. A69-06 — NFC CONTROLLER + SAFE TAG READER

Freshly locate `sec-nfc@27` DT bus, power supply/regulator GPIO, I2C binding/driver probe, firmware request, interrupts and `/sys/class/nfc` or NCI device nodes. Determine genuine support path (kernel NFC NCI vs libnfc transport; not automatically the same). Safe native Nuxel NFC Settings panel must tell `hardware missing / initializing / ready / scanning / tag found / error`. With owner-controlled NDEF tag, prove read and removal at supported field range; URL/tag contents never auto-execute, ask permission before external open. No secure element/card emulation/payment or bank card experiments. If hardware doesn't bind, give exact blocker and reproducible steps, not fake toggle.

---

# 11. A69-09 — ACTUAL VLC + MUSIC PLAYER ON FEDORA ARM64

Once package manager restored, query genuine **Fedora 43 aarch64** VLC GUI package split (where present), `mpv` and a light desktop GUI music player available in the current enabled signed repos. Deploy **VLC** and a **separate MP3/music player** appropriate to Wayland (do not count `vlc` and `vlc-cli` as two apps). Choose small real app, not a fake Nuxel PWA façade. Confirm package versions and dependencies, appropriate GStreamer/FFmpeg decode routes (respect repository licensing/codec constraints), correct icons/.desktop IDs/launcher registry, actual foreground application activation, MIME registration, audio sink selection and Back/Home/exit. Test real local owner MP3/WAV playing, pause/play, seek, playlist and app lifecycle, and documented audio output route. If physical speaker firmware blocked but USB DAC/BT available, use that to certify actual audio. If no usable sink, record audio decode/runtime separately from heard playback.

---

# 12. A69-11 + A69-12 — ACTUAL FAST PHONE / CONSISTENT ANIMATION

No random Mesa/GL driver replacement or kernel change. Use live measurements to identify CPU bottlenecks, software renderer, Wayland Phoc, `nuxel-wl-fb` copy/scale path, WebKitGTK, app memory pressure, unnecessary polling, GPU fallback, input latency, lockscreen redraw and icon decoding. Historical screen hardware 1440×3040 with potential 720×1520 software bridge—**verify modes and update rate**, don't blindly tweak based on outdated numbers.

**Baseline/after** same workload with multiple samples and stable thermal/battery conditions: app drawer open & launch, browser HTTPS scroll, workspace swipe, quick settings, Maps pan/zoom, SnekByte, nav and keyboard. Record p50/p95/p99 frame interval (when measurable), input-to-screen times, CPU use, RAM, temperatures, battery draw; distinguish genuine speedup from a disabled feature. Fix damaging full-frame copies, avoid blocking DBus/HTTP in UI event loop, optimize CSS layout and damage/paint regions and animations only with measured improvement.

Animate workspace swipes (touch-following), app enter/exit, drawer, recents, lock/wake as compatible with shell; gentle 120–220ms design starting points, compositor capabilities and accessibility `Off/Reduced/Normal`. Never let transition overlay intercept navigation or keep app behind drawer. Preserve pixel art, icons and the now-correct lockscreen penguin positions and animations. Avoid complex full-screen blur on software renderer.

---

# 13. USB INDICATOR REGRESSION GUARD FOR NEWEST WORK (20000)

The owner has been improving three lockscreen icons: charging penguin, PC connected penguin, Live Console penguin. They are now **correctly positioned below date/clock/battery and correctly sized**. Do not change positioning or size, do not replace artwork, don't disable animations. Check only as regression after relevant USB/audio/headset/package changes:

- Charger on whenever external power/charging state warrants according to agreed UI behavior; no power means off. Additive gentle animation stays working.
- PC connected only for an actual USB data connection to a host (not wall charger, not stale addressed/configured state after detach); disappears promptly on disconnect.
- Live Console active only when functionality and actual transport session state warrant; disappears on loss of host connection. **No stale cached ON bits after disconnect.**
- Tests: no cable, wall charger, real PC data USB, live console active, unplug and reconnect, USB DAC only if alternate console route safe. Never confuse charging source with PC data role.

If these already work, leave them untouched. This 21000 mission targets the older 18000 issues, not 20000 decorative changes.

---

# 14. SAFE EXECUTION BATCHES AND HARD STOP CONDITIONS

Use minimal reversible branches/commits, tested staged deployment, documented receipts and one owner. Suggested batches:

- **A72.0** Baseline and repo/live/hash reconciliation, network proof, backup, rollback.
- **A72.1** Trusted Fedora 43 ARM64 DNF5/bootstrap + small package transaction, with owner approval and independent recovery.
- **A72.2** Battery/nav/drawer fixes (only if currently still failing); ensure native navdock fallback ownership and app focus.
- **A72.3** Sound diagnosis + ALSA UCM placement, PipeWire/WirePlumber, Cirrus firmware compatibility; safe sound verification.
- **A72.4** BlueZ + Bluetooth driver/transport and A2DP + USB-C digital audio/headphone switch.
- **A72.5** SSP/rotation, NFC and GNSS diagnosis/integration; Maps online independent of GPS.
- **A72.6** VLC, separate music player and integrated media routing.
- **A72.7** Measured responsiveness/animations and exhaustive regression with owner-approved 3 cold boots.

For every batch: failing repro → root-cause receipts → patched files + tests → dry install preview → stage → deploy with recovery → physical check → snapshot hash → commit/rollback reference. If failure regresses Wi-Fi, TLS, shell/Home, USB recovery or boot, STOP that batch, restore last-good and diagnose. Do NOT compensate for a broken critical subsystem by adding a second copy of it. Time-consuming firmware research should not prevent finishing unrelated UI/Map/media improvements.

**Stop / require user input if:** only recovery console about to be severed; package transaction would replace critical glibc/systemd/kernel/boot or break Wayland deps; unverified proprietary firmware must be installed; USB role switch or reboot; physical outdoor/speaker/NFC accessory action requires human presence; powered speaker amplifier programming uncertain; a confirmed irreducible kernel/hardware blocker encountered. Do not ask confirmation for harmless read-only analysis or routine local code edits.

---

# 15. ACCEPTANCE MATRIX: 35 ORIGINAL TESTS + 21000 INTERNET GATES

Read the original 18000 requirements and test matrix in `references/NUXEL-18000-original-requirements.md`. Produce `docs/a72-21000/acceptance.csv` **with all T01–T35** rows including status, observation timestamp, OS/app version, evidence file and who observed. Re-run all tests, do not inherit historic PASS.

Additional mandatory gates:

| ID | Acceptance |
| --- | --- |
| T36 | Working current phone Wi-Fi + DNS + verified TLS + Nuxel browser HTTPS, before and after every service/package batch |
| T37 | Real Fedora 43 AArch64 repository access and correctly signature-verified package resolution OR precise justified blocker |
| T38 | Package manager on phone working where supported, sane dependencies and rollback receipts; don't count installed RPM alone as runtime success |
| T39 | Audio UCM source vs installed card-ID alias resolved; kernel+firmware requirements evidenced, no dangerous guessed amplifier writes |
| T40 | BlueZ packages vs actual powered HCI controller distinguished; owner speaker genuinely pairs/plays if hardware allows |
| T41 | Maps real HTTPS tiles/search/pan/zoom independently of GPS; consented GNSS truth separate |
| T42 | Seven rotation modes survive; real auto only PASS with physical accelerometer samples and actual compositor/touch rotate |
| T43 | Bluetooth, USB DAC and internal audio routed correctly when corresponding hardware is actually present |
| T44 | Latest 19000/20000 lockscreen icon position/size and USB state rules preserved; three independently animating icons unchanged |
| T45 | Exact repo→live install/sha256 and service unit/URL cache provenance for every changed component |
| T46 | Device/host architecture confirmed; no Fedora host RPM accidentally installed on phone, no `rpm --nodeps`, no signature bypass |
| T47 | 3 approved cold boots, USB recovery available, automatic connectivity + shell navigation + lockscreen battery correct |
| T48 | Before/after quantitative performance and animation checks, no placebo gains, no gaming FPS regression |
| T49 | Current 18000 A69 issue list all 13 explicitly revisited, no assumption that old A69 blockers still apply |

Further individual physical proof:
- Lockscreen correct battery at first paint; ten wakes; no false 0%.
- Exactly one Back/Penguin Home/Tabs; browser/Settings/Maps/Game can always be escaped; 4-icon dock only at desktop.
- App drawer opens selected app in foreground; no duplicate processes for already-running app.
- Real audible internal speaker and/or explicitly separate verified wired/BT routes; volume latency before/after and moderate test gain.
- Genuine HCI and BT manager and owner speaker playback when actual hardware supports it.
- Digital USB DAC enumeration/routing, passive USB-C analog truth, native headphone jack separately.
- Real SSP axis samples and auto-rotate or explicit firmware blocker, forced modes functional.
- Maps tile/search works with Internet; GNSS satellite fix verified ONLY from actual source; network fallback clearly labeled.
- NFC owner tag read or precise hardware limitation.
- VLC GUI and distinct MP3 music player installed/launchable; media formats load and controls work; audio dependent status truthful.
- Smooth pixel-art UI animations with reduce motion; measured speedup or explicit no measurable improvement.
- Continued successful Wi-Fi/DNS/TLS/Internet, Nuxel Browser, latest SnekByte, launcher, console and penguin lockscreen icons.

---

# 16. OUTPUT FILES AND FINAL REPORT — HARD COMPLETION CONTRACT

Work within `docs/a72-21000/` and commit relevant tests + implementation. Required outputs:

```
00-BASELINE.md
01-REPO-LIVE-DELTA.md
02-RECOVERY-PLAN.md
03-HARDWARE-DRIVER-MATRIX.md
04-INTERNET-AND-PACKAGE-MANAGER.md
05-FIRMWARE-SOURCE-AND-ABI-AUDIT.md
06-AUDIO-ALSACODEC-UCM-PIPEWIRE.md
07-BLUETOOTH-USB-AUDIO.md
08-SSP-ROTATION-GNSS-NFC.md
09-MAPS-VLC-MUSIC-APPS.md
10-UI-NAV-BATTERY-FOREGROUND.md
11-PERFORMANCE-ANIMATIONS.md
12-POST-REBOOT-REGRESSIONS.md
requirements-18000-to-21000.csv
acceptance.csv
package-install-manifest.csv
changed-files-hashes.csv
logs/  (sanitized)
benchmarks/  (real measurements)
evidence/ (device screenshots/short captures when available)
ROLLBACK.sh (reviewed; safe; never reboot/flash without approval)
FINAL-STATUS.md
```

Final report must include:

1. Today's **actual** Git commit, host/device identification, transport used, active services and source vs live hashes.
2. All 13 original A69 objectives + T01–T49, current PASS/BLOCKED/FAILED state with device evidence links. Distinguish already-working baseline from newly fixed this run.
3. Exact up-to-date blockers: distinguish *unavailable phone Internet* (owner now says working), *missing DNF*, *missing userland package*, *missing firmware*, *driver not bound*, *no accessory available* and *real working hardware*. Do not collapse them into “need kernel v6”.
4. Packages/firmware researched and installed, trusted source/signature/license, dependency changes, permission receipts and rollback. Explain anything not installed and why.
5. Speaker/BT/DAC audio audibility; sensor and GNSS raw data; NFC tag; Maps tiles/search; native player runtime/decoding; boot battery truth; navigation/layer ownership; before/after p95 and CPU/thermal.
6. Last-known-good restore steps and commands tested; repeatable cold boot and internet regression results.
7. High-priority remaining work, with precise failure point and a proposed **isolated future kernel/firmware study** only if a current 4.14 hardware barrier is proven. No kernel switch in 21000.

**Do the real work in the current repo and on the actual S10+ where connected; don't just rewrite these instructions, run mocks and declare the entire phone finished. User-visible quality and truth matter more than a summary full of green.**

---

# UPSTREAM RESEARCH STARTING POINTS (VERIFY, NOT A LICENSE TO BLIND-INSTALL)

- Fedora 43 DNF5: https://packages.fedoraproject.org/pkgs/dnf5/dnf5/
- DNF5 install transaction docs: https://dnf5.readthedocs.io/en/latest/commands/install.8.html
- Fedora VLC: https://packages.fedoraproject.org/pkgs/vlc/
- Fedora mpv: https://packages.fedoraproject.org/pkgs/mpv/
- postmarketOS device reference: https://wiki.postmarketos.org/wiki/Samsung_Galaxy_S10%2B_%28samsung-beyond2lte%29

**NUXEL 21000: TRUST THE LIVE PHONE. USE THE INTERNET. FIX THE ACTUAL ROOT CAUSES. BRING THE PENGUIN HOME. 🐧🔥🌐🔊🛰️**
