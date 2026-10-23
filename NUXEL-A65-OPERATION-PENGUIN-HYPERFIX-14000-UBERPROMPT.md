# 🐧🔥 NUXEL A65 — OPERATION PENGUIN HYPERFIX 14000
## Maximum Cross-Stack Repair: TLS · NetworkManager · Global Navigation · Lockscreen · Rotation · Camera · Foreground Apps · UI

**Primary executor:** `deepseek-v4-pro-thinking` through the user's existing CodeSeeQ (`csft`) client, from the current Fedora laptop's Nuxel checkout.

**Device:** Samsung Galaxy S10+ SM-G975F, beyond2lte, Exynos 9820, independent Nuxel Fedora ARM64 userspace over a legacy Samsung-derived 4.14 kernel, using a mobile Wayland/Phoc-derived compositor architecture, GTK/WebKitGTK hosting, custom Nuxel launcher/bridge/services, and USB Live Console. *Verify the exact current stack; names here are leads, not proof.*

**Mission type:** Repair and **implement** the 15 owner-observed defects below in the **current** checkout and actual live S10+, without restarting earlier 2000–13000 projects or erasing their changes. Keep the handoff actionable, code-oriented and evidence-driven. Never deliver merely a proposed plan when changes can be safely implemented. Every result must be labeled as source-only, offline-tested, deployed, or physically verified.

**Attached owner photographs** in this prompt pack (unaltered originals):
- `evidence/camera-status-a65.jpeg`: Nuxel Camera application, large empty viewfinder, "Camera present", "Live capture: NOT verified", text claiming V4L2 nodes enumerated (68), reference to `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md`, with Refresh status / Open Photos. This photograph **does not establish working real camera capture**. It demonstrates a live application and its current technical diagnostic state; the technical count and pipeline claim must be checked against current logs before repeating as fact.
- `evidence/camera-spinner-a65.jpeg`: second Camera application, title "Camera" and an indefinitely loading spinner, no visible escape/close or operating camera preview. The photo is not a diagnostic of its process implementation.

**Most recent observations provided by owner:** Opening `https://google.nl` offline originally displayed "Temporary failure in name resolution". On connecting Wi-Fi, the error changed to **"TLS support is not available"**. Wi-Fi icon reportedly became green but Settings still says "Authenticating and Associating". Battery works promptly after unlock, yet displays **0% on lockscreen for minutes**. Owner reports the various navigation, foreground, dock, rotation, calculator, camera, and app chrome defects below. Don't downgrade newer working behavior based on older reports.

---

## 0. Non-negotiable rules and rapid triage

1. **Priority P0: maintain escape/recovery**. Verify actual reliable Fedora→phone USB Live Console **before** changing any shell/navigation/lock services. Record console transport, a verified recovery command, persistent backup path and permission to restart specific services. Never risk losing both user navigation and console simultaneously. Current phone is booting: **no boot/kernel/DTB/firmware/partition/TWRP flashes**; no speculative hardware driver or register changes. No factory reset, wiping profiles, or mass Flatpak reinstall.
2. **Stop concurrent device writers.** Coordinate with ongoing A63/A64 12K/13K agents; have exactly ONE live deployment owner at a time. Existing uncommitted work must remain intact; back up first. Source edits may be parallel only if file ownership and merge discipline prevent conflicts; on-phone restarts and deployments serial.
3. Treat available prior mission prompts and source history as references, not something to blindly replay. Read current `git status`, `git log`, relevant implementation files, service definitions, actual deployed hashes, logs and `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md` if present. Discover real paths via `rg`, `find`, package manifests and active process command lines. Record baseline and a per-subsystem rollback plan. Create a dedicated feature branch/checkpoint without trashing the owner's changes.
4. Distinguish **system shell** (global navigation/power/foreground surfaces) from **app-local DOM** (browser top controls, Calculator, custom Camera). Do not patch a native-app foregrounding problem with a CSS `z-index` or implement global Back by injecting a JavaScript listener into only one WebView. Identify the actual compositor/window manager and use its supported capabilities.
5. Do not simulate hardware success, manufacture network states, silently disable TLS verification, accept all certificates, weaken WPA, log Wi-Fi PSKs, or spoof camera frames. Never fake a correct battery %. If a service is unavailable, render honest user-friendly error with recovery and remain escapable.
6. Any command that intentionally kills a process must target only the currently active eligible app. Absolutely exclude PID 1, compositor, shell/launcher, input method, lock manager, network/bridge services, recovery console, and shared WebKit parent processes hosting multiple apps. Before intentional termination, print/verify resolved app ID/PID/cgroup to a sanitized test receipt. Long-Back must be optional and inaccessible at the lockscreen.
7. No blind global rebuild, dependency update, cache wipe, or rollback to old UI. Keep A64's recovered launcher icon scale/grid; preserve latest SnekByte from `./snekbyte.zip`, game persistence, app registry and media store. Avoid regression by precise patches, staged deployment, tests and change receipts.
8. Request owner authorization for reboots and disruptive compositor, lock manager or system service restarts. Prefer minimal service replacement with console live. Protect user data, saved networks, game high scores, browser profiles and installed apps.
9. Generate deliverables under `docs/a65-hyperfix-14000/`: `00-baseline.md`, `01-requirements-matrix.md`, `02-root-causes.md`, `03-source-deployment-map.md`, `04-test-evidence.md`, `05-rollback.md`, `06-final-verdict.md`, `logs/`, `screenshots/`, and a safe deploy/rollback script if appropriate. Do not put secrets in evidence.

### Dependency/implementation order

**Gate A — console + backups + capture live state** → **Gate B — shell ownership/foreground/global navigation** → **Gate C — Wi-Fi truth, DNS/TLS/browser** → **Gate D — screen-off lock, battery source and rotation** → **Gate E — app chrome/Calculator/cameras** → **Gate F — integrated physical acceptance and owner-approved cold reboot**.

If fixing browser TLS is a quick, low-risk install/configuration repair, it may precede shell surgery after baseline. Don't starve easy fixes behind a long camera hardware investigation. Keep each gate independently reversible.

---

## 1. Explicit issue contract: all 15 bugs (do not collapse any)

| ID | Owner-visible defect | Target behavior | Minimum physical verification |
|---|---|---|---|
| A65-01 | Browser formerly DNS failure offline; when Wi-Fi on, `TLS support is not available` for `https://google.nl` | GIO/WebKit has real TLS backend and trusted CA chain, real external HTTPS works; offline DNS error remains honest | Load google.nl and another unrelated HTTPS host in actual Nuxel Browser, navigate/search; retain cert verification |
| A65-02 | Wi-Fi Settings stuck in "Authenticating and Associating" despite likely green/connected icon | State labels strictly reflect real NM device, active connection, DHCP/DNS/reachability; no stuck spinner | Connect, inspect state 100 and IP, UI "Connected", disconnect/reconnect and repeat |
| A65-03 | Screen off does not necessarily lock instantly; user wants configurable delay | Default locks **immediately on screen-off**, configurable lock-after-screen-off interval in Home Settings | Default power-off/on demands unlock; delay option works at boundary times and persists reboot |
| A65-04 | Triple navigation disappears when focusing browser URL/keyboard | Persistent system navigation **above apps/OSK**, with setting to autohide only in apps and edge swipe-to-reveal | Keyboard open, portrait/landscape, several native and PWA apps; controls still usable/revealable |
| A65-05 | Penguin Home button does not return to launcher | Reliable system-level Home from all eligible foreground apps | Repeated taps from Browser/Camera/Settings/SnekByte/native app reach Home |
| A65-06 | Back button no-op; long-Back should kill foreground app | Short Back performs hierarchy: hide keyboard → app Back/previous screen → app exit to Home; long-Back close/terminate **only current eligible app** | Tap and long-press from both PWA and native apps, launcher survives |
| A65-07 | Four bottom launcher favorite icons sit above app content | Favorites dock visible only on Home/launcher; never floats over foreground applications | Open apps with and without keyboard, check dock absent while global triple nav persists |
| A65-08 | Browser top toolbar too wide; buttons offscreen | Compact responsive safe-area aware address/toolbar, actions reachable, never horizontal overflow | S10+ portrait, landscape, OSK open, address entry, tabs, navigation |
| A65-09 | Lockscreen battery falsely starts at 0% for minutes | Current real battery % or honest loading/unknown immediately; same data source as unlocked statusbar | 10 lock/wake cycles and cold startup; no fabricated 0% |
| A65-10 | Only Auto and Forced Portrait available, and Auto doesn't rotate | Seven modes: Force 0/90/180/270; Auto all; Auto portrait; Auto landscape, with working sensor-based auto where hardware exports data | UI seven modes and actual change on physical tilt, touch alignment; report hardware blocker if absent |
| A65-11 | Calculator prematurely evaluates on typing e.g. 9 + 8 | Expression buffer and explicit Equals-to-evaluate; correct editing and precedence | `9 + 8` shows expression until `=`; yields `17` only after Equals |
| A65-12 | First Nuxel Camera shows technical "camera present/capture NOT verified" placeholder | Useful honest camera UI, bounded errors, real preview/photo only if ISP works; never raw debug wall as default | Opens, exits, can access Photos; real capture separately verified or BLOCKED_HARDWARE |
| A65-13 | Second Camera app spinner indefinitely with no escape | Immediate usable shell, bounded camera initialization/failure, global Home/Back/long-Back exits | 10 launches/cancel/fail tests; open without working ISP; all exits functional |
| A65-14 | Launching an app from Applications opens it **behind** current window | New/reopened app becomes active foreground, receives keyboard/touch focus | Test cold launch/second app/relaunch with PWA and native window |
| A65-15 | Redundant top window/app title bar ("Home", app name) wastes room, crops SnekByte fullscreen | Remove redundant **Nuxel shell-owned** per-app top Home/title chrome across apps; preserve system status/navigation, native essential dialogs; full usable SnekByte area | SnekByte fully fits between reserved safe areas, all apps remain accessible, no lost close/escape |

When requirements interact, e.g., A65-04/07/15, design **one** coherent visual/interactive surface hierarchy and verify together, rather than layering three independent fixes.

---

## 2. Gate A — live reality, provenance and regression control

Capture the actual stack from Fedora and separately from S10+; never confuse laptop package results for phone package results. Determine the phone's GUI session user, display server, compositor, output scale/rotation, WebKit host process, launcher app IDs and userspace service units. Record git HEAD, dirty changes, active runtime files/hashes and prior A64 launcher screenshot if available. Note upstream `./snekbyte.zip` latest source (do not unpack or replace unless necessary). Find durable console escape / shell recovery (owned, authenticated). Save exact live copies of candidate shell/CSS/JS/services, excluding secrets and user profiles.

Read-only exploration examples, adapt dynamically:

```sh
uname -a
cat /etc/fedora-release
systemctl --user list-units --type=service --no-pager
systemctl list-units --type=service --no-pager
loginctl list-sessions
ps -eo pid,ppid,comm,args --sort=pid | grep -Ei 'phoc|wayland|webkit|nuxel|snapshot|camera|networkmanager' | head -100
nmcli general status
nmcli device status
ip -br address
ip route
resolvectl status 2>/dev/null || cat /etc/resolv.conf
```

Never assume `resolvectl` or `wlr-randr` exists in a stripped-down rootfs; record missing diagnostics as `TOOL_NOT_INSTALLED`, not system failure. Determine actual real logical viewport + DPI + available output orientation; physical S10+ panel approximately 1440×3040 is not the same as the browser CSS coordinate system.

**Reproduce before modification** each issue with time-correlated logs. For all defects, save baseline status `REPRODUCED/NOT_REPRODUCED/BLOCKED_BY_OTHER`, owner observation vs live observation and exact pathway. Build an app focus/stack trace (surface IDs, PID/desktop IDs, activation timestamps) while tapping Home/Back, app grid, OSK, power, and Camera. If changes originate in stale deployed bundles rather than current Git source, correct deploy pipeline first; do not rewrite the wrong codebase.

---

## 3. A65-01 — make HTTPS/TLS really work (critical, likely small fix)

**Owner's error evolution:** offline DNS resolution failed (expected disconnected case). Connected case: `TLS support is not available` **strongly suggests missing GIO TLS provider** or unable-to-load GIO module in the exact sandbox/namespace/process — NOT proof of defective DNS or an invalid website certificate.

Investigate the *on-device* browser process, UID, environment, runtime and packaging:

- Identify real web technology: GTK 3 or 4? WebKit2GTK 4.0/4.1 vs WebKitGTK 6.0? libsoup2 vs libsoup3? GIO modules library path? Native installed RPM vs Flatpak sandbox? Custom env `GIO_MODULE_DIR`, `GIO_USE_TLS`, `GI_TYPELIB_PATH`, `XDG_DATA_DIRS`, `LD_LIBRARY_PATH`, `SSL_CERT_FILE`, `G_TLS_GNUTLS_PRIORITY` accidentally shadowing/misconfiguring modules? Log only relevant safe vars, never user secrets.
- On **the PHONE**, inspect `rpm -q glib-networking gnutls ca-certificates glib2` (actual Fedora packaging may vary), `rpm -ql glib-networking` if installed, relevant shared object locations/arch, `ldd` missing libs, `rpm -V` packages when applicable. `glib-networking` is Fedora's GIO GnuTLS implementation. Identify whether rootfs composition/installer omitted a dependency or whether an application bundle ships private GLib/GIO with a wrong module directory.
- Directly test GIO under the **same launcher/runtime namespace**, e.g. with Python GI if present:

```python
from gi.repository import Gio
backend = Gio.TlsBackend.get_default()
print(type(backend).__name__, backend.supports_tls())
```

- `supports_tls() == False` strongly indicates no real TLS backend. Determine why it cannot discover/load `libgiognutls.so`; diagnose loader errors, architecture mismatch and sandbox module visibility; only then repair/install needed dependency with reproducible manifest. If test says True but WebKit HTTPS fails, inspect WebKit NetworkProcess child env, libsoup session, proxy, cert database, file permissions and error codes; don't assume one test proves all child processes.
- Separate resolver path: `getent ahosts google.nl`, `resolvectl query google.nl` where present, `ip route`, `curl -Iv https://www.google.nl` *from device* (curl TLS success != WebKit TLS success). Verify UTC/system clock/time sync and actual CA trust; a bad clock would lead to cert validation failure, not necessarily "TLS support is not available".
- Ensure clean HTTP redirect behavior and external HTTPS. Do **not** switch to HTTP, set ignore TLS errors, add `accept-certificate` return True, disable HSTS or bypass validation. If a captive portal is present, offer a visible portal detection route without mislabeling it as globally working internet.
- Repair packaging and image build so `glib-networking`, `gnutls`, CA trust and needed GIO modules survive next image rebuild, do not patch only today's live rootfs. Include package smoke assertion in CI and a **real browser WebKit** check.
- Success: actual browser loads https://www.google.nl and https://example.org, interactive navigation/search, reload and app restart, correct TLS chain; intentionally invalid certificate rejected. Record request error before/after and real loaded page proof.

**Public upstream implementation references:** Fedora package `glib-networking` and GNOME GIO docs `GTlsBackend.supports_tls`, `G_TLS_ERROR_UNAVAILABLE`, `GIO_USE_TLS`. Research as needed using available source docs; never fabricate installed package state.

---

## 4. A65-02 — untangle real Wi-Fi state vs frozen authentication label

Trace `connect UI → Nuxel network bridge → NetworkManager active connection → per-device state/reason → DHCP/IPv6 → resolver/route → link/internet status → UI store/subscriber`, **without ever exposing PSKs**.

Official NetworkManager device states distinguish 50 `CONFIG` (can involve associating), 60 `NEED_AUTH`, 70 `IP_CONFIG`, 100 `ACTIVATED`. If Wi-Fi is in state 100 and phone has assigned route and DNS, UI must not remain in 50/60. However green icon could simply mean `link up` or a cosmetic state, so verify all.

Read-only diagnostics and event traces:

```sh
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,GENERAL.DEVICE device show "$WIFI_IFACE"
nmcli -f GENERAL,IP4,IP6 device show "$WIFI_IFACE"
nmcli connection show --active
nmcli monitor
ip addr show dev "$WIFI_IFACE"
ip route
getent ahosts google.nl
journalctl -b -u NetworkManager -n 180 --no-pager
```

`$WIFI_IFACE` must be discovered on the phone. Avoid logging full saved profiles with credentials. Inspect DBus subscription lifetime, events emitted before listeners subscribe, a stale `ActiveConnection` reference, whether a connect handler awaits a never-resolving secret/activate promise, inconsistent statuses across settings/top bar, loss of events on dialog closure, UI polling only on foreground state, Wi-Fi reconnect races and duplicate NetworkManager activators. Replace ad-hoc labels with a finite state machine mapped to authenticated actual NM states + reason codes; UI must **request initial snapshot on mount/resume**, subscribe to changes, safely handle missed updates/disconnects, and have bounded retries/error hints. Activation API reply = pending, **not** success. Never use an invented access point path such as `/new`.

Define independent statuses: `RADIO_OFF`, `DISCONNECTED`, `CONNECTING`, `AUTH_NEEDED`, `IP_CONFIGURING`, `CONNECTED_LOCAL`, `CONNECTED_INTERNET`, `CAPTIVE_PORTAL`, `ERROR`, `UNKNOWN`. Connectivity check not every frame; avoid background battery drain. The top icon and Settings label must derive from one authoritative state store. Test working connected network while opening/closing Settings; wrong password/rejected AP; real disconnect; airplane toggle; cold reboot autoconnect; multiple APs/reconnect; captive portal if available. Preserve valid known-good connection secrets. If network only becomes `CONNECTED_LOCAL` (no real HTTPS), do not claim full Internet.

---

## 5. A65-04/05/06/07/14/15 — rebuild navigation and app hierarchy as ONE system

**This is the highest-impact cross-app issue.** Determine true compositor and Wayland topology first. WebKit CSS overlays are not global above other clients. Implement a **single authority** for navigation, focus/foreground, app stack and shell chrome; use Wayland layer-shell / compositor-supported panels or the actual supported window-manager mechanisms if available. Validate layer ordering, input regions and reserved exclusive zones; a graphical effect that merely *looks* above an app but cannot receive taps is a failure. Do not assume the window manager allows arbitrary client raise/focus, and do not use `wmctrl/xdotool` as an imagined Wayland solution. Configure/apply activation via supported xdg-activation tokens/surface activation paths where available, with on-phone evidence.

### Surface hierarchy required

1. **System lockscreen** authoritative when locked; cannot be hidden by Home or Back, and should hide/disable unsecured app content until valid unlock. Camera cannot override the locked session or swallow Power events.
2. **System status/header** where intentionally in Nuxel layout, respects camera cutout and orientation.
3. **App client surface** occupies available viewable region, including full-bleed SnekByte and Browser. Remove Nuxel-added redundant per-app chrome `Home | <app name>` across **all** Nuxel-hosted apps, not arbitrary native GTK titlebars required for dialogs/accessibility; if native decorations remain, measure why and negotiate appropriate client/server decoration. Critical functionality must remain reachable through global triple navigation, not removed with header.
4. **Launcher-only favorites** four dock icons; only rendered while launcher/Home is foreground. Disable/hide favorites as soon as app foregrounds. Do not hide **global** Back/Home/Tabs with this logic.
5. **Global bottom triple navigation** Back / penguin Home / Tabs-overview (existing meaning), elevated above eligible app surfaces and normally visible. Reserve height + safe-area/gesture inset; ensure edge gesture region and app content don't collide. When the OSK opens, place bar above keyboard or in a guaranteed visible system layer based on measured actual composition; never leave keys or nav occluded or invisible. In full-screen apps, design content to fill **remaining usable area**, not under controls.

**Home tap:** resolve active app, request suspend/minimize or switch focus to known launcher surface, ensure launcher is visible and gets input. Avoid launching duplicate launcher instance or leaving an invisible full-screen app above it. If already Home, no-op or scroll to Home; must not spawn another instance.

**Short Back precedence:** (i) active input method visible → dismiss keyboard and restore focus; (ii) app-specific navigation goes back within browser history/page stack/dialog; (iii) if no further navigation, gracefully leave foreground app to Home (or previous app if current UX policy); (iv) Home itself stays Home. Support app-local Back through bridge/IPC with receipt and deadline, then system fallback on timeout or nonresponse. Do not let a hung Camera block Back. Test native apps and WebKit PWAs.

**Long Back:** only when an eligible **foreground external app** exists; time threshold measured (for example 700–1100 ms, choose consistent), with pressed/canceled/released state machine. On hold, first request graceful close with bounded timeout, then scoped SIGTERM, then SIGKILL only if necessary and permitted. Target a process/cgroup **owned uniquely by that app**; where multiple PWAs share a WebKit host process, close that app's window/webview instead of killing the entire host/other apps. Guard against PID reuse and stale focus. Exclude compositor, lockscreen, launcher, keyboard, bridge, console, daemon and network services. No long-Back on lockscreen. Provide user affordance/haptic if supported; don't invent haptic hardware.

**Tabs/overview:** preserve functionality already intended by Nuxel; reliably open overview/task switcher. Avoid conflating "Tabs" (browser tabs) with **system** recent-apps (the owner's existing bottom icon may mean launcher tabs). Inspect implementation and owner's established UI; document intended action, do not silently rename or break it.

**Optional autohide:** create persistent Home Settings control `Navigation bar: Always visible (default) / Automatically hide in apps`. The latter only hides while an app is foreground, NEVER while locked or on Home; gesture from lower screen edge reveals the triple buttons, with a visible/temporary affordance and timeout/press behavior. Edge gesture must not trigger accidental scrolling/game swipes or block bottom-of-screen controls. Ensure this policy survives reboot. Test with keyboard shown, SnekByte game, landscape, and app crash.

**Foreground activation:** from Applications screen → app launch → actual surface created → activate/raise app via compositor-approved focus route → input focus confirmed → hide Home/favorites. Reopened running app should focus existing surface, not create a background duplicate. Maintain transient/modal parent relationship. Treat shell `.desktop` / Flatpak / WebKit app registration, `StartupNotify`, activation tokens, focus events, and foreground app registry uniformly with real evidence. When apps close, return to last viable screen or Home and clean up session ownership.

**Top shell chrome:** remove only redundant Nuxel per-app `Home + app title` bar. Preserve site-required input/browser toolbar, safe-area/statusbar and GNOME app-owned controls that are important. In SnekByte, do not zoom/crop/stretch game canvas; compute its viewport after status + nav + keyboard reserves. Canvas/touch controls remain usable; preserve latest `./snekbyte.zip` features, high scores, D-pad, speed, wrap-around and WoNQ mode.

**Integration tests:** exactly one visible persistent nav set, no duplicate overlays, Home/back/long Back/overview from at least Browser, Settings, Photos, Calculator, both Cameras, SnekByte, a native GTK app, and a hung-app simulation. Test when OSK opens, screen rotates, app crashes, and on lockscreen. Record process tree before/after long-Back: launcher and recovery remain alive. A navigation action must work even if active WebView's UI thread is blocked, or clearly document compositor limitation with alternative system escape.

---

## 6. A65-08 — responsive Nuxel Browser top toolbar and keyboard

Measure actual WebKit logical width, CSS safe area, cutout positions and browser root computed styles. Rebuild browser's own top address/controls bar as responsive layout (`min-width: 0`, truncating address field, compact overflow menu, flex/grid breakpoints, correct `box-sizing`, safe-area insets), not `width: 100vw` plus sibling actions exceeding available width. Keep essential Back, Forward, Reload, address, Tabs/menu reachable in portrait; less-used buttons via overflow with clear focus/accessible touch sizes; native keyboard doesn't cover address or global nav. Ensure URL bar focuses OSK; typing doesn't cause nav disappearance/overscroll; navigation handles HTTPS and actual page loads. Test actual phone portrait and landscape and keyboard show/hide. Avoid CSS global `input` rules leaking into launcher/camera.

### Browser acceptance script

1. Open from launcher; browser is actually foreground.
2. Tap address field: OSK opens; bottom global triple nav remains visible or can be edge-revealed per configured mode; address doesn't disappear; toolbar buttons remain reachable.
3. Enter `https://www.google.nl`, submit, verify trusted HTTPS page and title/content. Search terms, tap result, Back returns to prior page, Home returns launcher, restore Browser resumes safely.
4. Open browser tabs and use global task overview separately; no erroneous coupling.
5. Rotate, resize, OSK open/close; no horizontal clipping or inaccessible icons.

---

## 7. A65-03 — screen-off should lock instantly by default, with configurable grace

Inspect actual power key → input event → compositor blank/DPMS/display off → session lock manager → trusted lockscreen → wake cycle. Distinguish **screen off** from `idle`, suspend, display power-down, compositor crash, app-requested prevent-sleep, and manual lock. On any screen-off transition, default policy **immediately enters trusted locked state**, not merely show a wallpaper on wake. It must remain locked after brief display blink or rapid Power tap and across service reinitialization.

Add real persistent Home Settings policy **"Lock after screen turns off"** choices like `Immediately` (default), `5 seconds`, `15 seconds`, `30 seconds`, `1 minute`, `5 minutes` (actual owner may configure more; implement sensible bounded enum with explicit units). Clock starts at confirmed screen-off event, not from last browser touch and not while screen is still on. If user wakes before selected delay, either legitimately resume unlocked under selected policy or re-lock according to explicit user choice; after delay, require swipe unlock. On reboot or settings corruption default to `Immediately`. If service dies during countdown, fail **locked** on recovery; no stale unlocked state. Do not leak app content on lockscreen; do not expose privileged IPC lock toggle to arbitrary webpages. For longer grace intervals, expose clear UI copy that this is less private than immediate lock.

Preserve existing upward draggable penguin padlock lockscreen art: `./assets/nuxel-lockscreen.jpg`, `./assets/nuxel-lockhead.png` where those resources remain current; drag gesture should remain 10/10 functional and must not rely solely on hiding a WebKit DOM layer. Verify power/wake immediately, wake at 4/6 sec for 5-sec setting and at 15/16 sec for 15-sec; switch back to instant and reboot test. Set default without silently replacing prior saved explicit owner choice if existing setting already exists and owner has chosen it.

---

## 8. A65-09 — lockscreen 0% battery initialization race

Trace `kernel power_supply` → authoritative battery collector/service → bridge DBus/event stream → Home/statusbar → **lockscreen-specific WebView/IPC**. Owner says statusbar meters work instantly after unlock; compare lockscreen subscriber timing and data source. Likely stale `0` placeholder / missing initial snapshot / suspended subscriber / out-of-order event, **not necessarily** real battery hardware failure. Measure, don't assume.

- Inspect real sysfs battery percent path(s), e.g. discovery under `/sys/class/power_supply/*/capacity`, actual validity, service messages and timestamps. Distinguish charging status and multiple power supplies; phone may have legacy vendor representation.
- On lockscreen **before unlock** asynchronously request authoritative last fresh value and subscribe; on boot before first valid read show `—%` or small spinner, **never synthetic 0%**. If collector returns a real zero with valid source, display it; do not suppress legitimate near-empty condition.
- Eliminate duplicated battery sources between topbar and lockscreen, fix startup/readiness ordering and stale bridge event dropping. Use monotonic timestamps, last-known-valid with age cap, generation IDs after service restart, no excessive polling. Keep accessibility label truthful. Acceptance: fresh boot and ten lock/wake cycles; initial valid % in bounded time matching sysfs + statusbar, or honest unavailable when source fails.

---

## 9. A65-10 — make seven orientation modes real, not a Settings mock

Current quick settings reportedly only offers **Auto** and **Forced Portrait**, and Auto does not rotate. Review current orientation policy service, quick-settings renderer, saved preferences, compositor output transform, device sensor discovery (IIO/accelerometer, input events, sensor proxies), udev permissions, logind device access, and touch calibration. Don't hardcode accelerometer axis orientation or a generic Pixel mapping: **beyond2lte** mounting and coordinate transformations may differ from common phones.

Seven modes required (labels may be localized but semantics must match):

1. **Force Portrait (0°)**
2. **Force Landscape (90°)**
3. **Force Inverted Portrait (180°)**
4. **Force Inverted Landscape (270°)**
5. **Auto — All Orientations**
6. **Auto — Portrait Only** (0/180)
7. **Auto — Landscape Only** (90/270)

One shared persisted policy state store for Home Settings and Quick Settings; all seven accessible (compact submenu/secondary sheet is fine; don't cram unreadable labels into quick tile). Quick tile must show active mode and current applied physical transform. Read actual hardware orientation events (IIO, libinput, `iio-sensor-proxy` if genuinely installed and compatible), debounce and hysteresis, avoid jitter, honor initial unknown orientation and fallback, allow touch coordinate transform; avoid rotating locked/unlocking surfaces inconsistently. Inspect `phoc`/wlroots output transform API available and whether older framebuffer bridge offers transform; don't take guesses that blind touch input.

Required instrumentation: current mode, raw sensor vector/event timestamp, mapped device orientation, compositor transform, visual orientation, touch mapping. If no accelerometer events at all due to vendor driver, **report exact missing interface** and maintain working manual four forced modes; do NOT mark Auto PASS. No reboot just to try random vendor drivers. Test all four forced positions (return to portrait at end), auto physical tilt 10x and keyboard/bottom nav in each; persistence after reboot.

---

## 10. A65-11 — Calculator evaluates ONLY on Equals

Inspect current Calculator framework (PWA, GTK, CLI bridge, or native). Separate input buffer from result, represent expression explicitly, and compute only on Equals or accessible equivalent Enter/`=`. Tapping `9`, `+`, `8` must show **`9 + 8`** (or appropriate visible expression), never show `17` until `=` pressed. Handle consecutive operators, negative numbers, floating decimals, backspace, clear (`C`/`AC`), repeated Equals (choose consistent behavior), division by zero with non-crashing error, precedence (`2+3×4 = 14` if calculator is expression-style, or explicitly test documented sequential calculator design), and precision formatting. Avoid unsafe `eval` and arbitrary JS/Python evaluation of input; use constrained parser/existing arithmetic library. Test tap and physical keyboard flows, app relaunch, locale decimal separator where supported, input responsiveness, no accidental Home/Back intercept. Unit test includes intermediate display states, not only final arithmetic.

---

## 11. A65-12/13 — TWO camera apps, two different failures

### First app (Nuxel Camera, photo `camera-status-a65.jpeg`)

Already has a functional shell and says "Camera present" with "Live capture: NOT verified"; it also exposes raw debug details claiming 68 V4L2 nodes and a missing standard capture interface. Don't "fix" this by changing the verdict to `WORKING` or by adding fake frames. Verify current real media topology, loaded driver/module, camera sensor detection and permissions **read-only**; note distinction between many `/dev/video*` nodes and a coherent libcamera/GStreamer capture pipeline. Preserve media store/Photos integration, functioning buttons, and real Back/Home/Close.

Improve UX: concise top-level status and a reliable **Retry camera** action; move verbose FIMC-IS topology and logs to a collapsible **Technical diagnostics** panel, with link to `docs/a52-camera/MEDIA-PIPELINE-ANALYSIS.md` only if available. If ISP pipeline unavailable, show "Camera hardware detected, but live preview is not available on this kernel" plus safe user next steps; save nothing unless real frames actually arrive. No endless spinner, no misleading Capture button. Preserve actual still/video support if future pipeline works; prove real frames for CAPTURE_PASS.

### Second Camera app (photo `camera-spinner-a65.jpeg`)

Find exact launch mapping: native GNOME Snapshot vs another camera PWA/Flatpak/GTK application vs user-installed app; the photo title alone cannot identify the implementation. Map icon → `.desktop`/PWA registry → PID/cgroup/window → PipeWire/GStreamer/portal/media init → GUI spinner → exit path. Distinguish app still responsive but hardware enumeration blocked, WebKit JS thread blocked, portal permission timeout, stale IPC, GPU render issue, native app stuck on camera request, and unresponsive compositor focus.

Implement immediate window with clear `Close`, `Retry` and `Camera unavailable` after **bounded** initialization timeout (choose ~5–8 seconds if appropriate). Do not block UI thread waiting on libcamera/pipewire/portal, even if driver call is hung. Cancellation must release resources and leave any shared capture stack sane. **Global Home/Back/long-Back must work during spinner and without app-specific cooperation**, while preserving the running launcher and other apps. Native GNOME Snapshot must stay unmodified third-party package if possible; implement shell-level escape and fix missing dependencies/portal only where demonstrably needed. Never rewrite vendor camera or flash kernel as part of this UI mission.

Perform 10 runs of each app: from Home and Applications, connect/disconnect Wi-Fi (camera unrelated), orientation changes, lock/wake while camera open, Home, Back, long-Back, re-open. Classify real preview as `PASS_PHYSICAL_CAPTURE`, `BLOCKED_HARDWARE`, or `NOT_TESTED`; camera **app usability** as independent test and do not conflate the two.

---

## 12. Cross-feature integration: no regressions from the earlier 13K UI rescue

- Restored A64 launcher grid/icons remain correct dimensions with real image labels. Home favorites only when Home is active. No oversized icons, telemetry spill, giant dark circle, duplicate navigation, or nav overlay covering launcher icons.
- Preserve Nuxel style wallpaper, blue/pixel icons, lockscreen penguin drag, all SnekByte newest-game features, high scores, app list, Nuxtore/Flatpak, USB debugging and live console.
- App registry stable: selecting app makes actual foreground with focus; returning via Home must not spawn duplicate container or leave stale overlay in focus stack.
- Native apps not special-cased into bypassing navigation; noninteractive camera spinner cannot consume all input.
- WebKit view uses trusted HTTPS, proper keyboard/OSK, responsive toolbar, no stale CSS references; nuke only **targeted** stale assets with data-preserving reload, never all browser storage.
- Navigation policy persists, screen lock delay persists, orientation modes persist; conflicting UI settings merged in one source of truth, not two unrelated toggles.
- Deep sleep/power events must not leave laptop-side daemon as an implicit requirement. Phone must work standalone after cold boot.

---

## 13. Mandatory physical test matrix (document BEFORE/AFTER)

**Set up** console, active device logs, an owner-observed test run and a complete read-only baseline. Use meaningful per-test IDs.

| Test | Steps | Expected |
|---|---|---|
| 01 HTTPS | Wi-Fi on → Nuxel Browser → google.nl and example.org → search/result | Real trusted HTTPS HTML, no TLS-unavailable; cert errors still rejected |
| 02 offline | Wi-Fi off → visit page | Honest offline/DNS error; no crash |
| 03 Wi-Fi state | Known AP connect → Settings Wi-Fi pane open → close/reopen | NM 100, address/route, UI Connected; no stale authenticating |
| 04 reconnect | Disable/re-enable radio; reconnect; owner-approved reboot | Saved network reconnects, browser works |
| 05 keyboard/nav | Browser URL focus and OSK | Back/Home/Tabs available on top; OSK doesn't cover bar |
| 06 Home | Browser, Settings, Photos, Calculator, SnekByte, both Cameras, GTK app | Penguin returns real launcher each time |
| 07 Back | OSK, deep browser history, empty history, native app, hung app | Dismiss → go back → leave app in proper order |
| 08 Long-Back | On foreground Camera/Browser/GTK/SnekByte | Target closes, shell and all other apps remain alive |
| 09 nav policy | Enable autohide → app → bottom-edge swipe | Triple bar reveals, clickable; Home remains persistent on launcher |
| 10 favorites | App open/foreground, OSK | Four Home favorites never on app, nav remains |
| 11 app focus | Applications → open already-running Browser/native app | Foreground and receives input, no orphan window |
| 12 titlebar | SnekByte + every Nuxel app type | No redundant shell Home/title bar; proper content geometry |
| 13 screen lock | Power off → immediate Power on | Locked by default; penguin drag works |
| 14 lock-delay | Set 5s → wake at 4s, later at >5s; reboot | Precisely documented behavior, persistent and fail-closed |
| 15 battery | Cold boot and 10 locks/unlocks | Valid real % or unknown; no false 0% |
| 16 rotation | Four forced modes + three auto modes | All offered; manual works; auto tilt if sensor exposed; aligned touch |
| 17 calculator | `9 + 8`, inspect before `=` then press `=`; `2+3×4` | Before equals unchanged, after proper result; no `eval` |
| 18 first Camera | Launch, retry, technical details, exit, Photos | Responsive, truthful capture availability |
| 19 second Camera | Launch 10×; wait timeout; Back/Home/long-Back | No trap; loading bounded; app scoped closure |
| 20 cross-app stress | Browser typing → Home → SnekByte → Camera → lock/wake → rotate → Home | No menu z-order corruption, navigation loss, touch mismatch |
| 21 cold boot | Owner-approved cold reboot, repeat core tests | Startup order fixed, settings stable, no regression |

Run portrait tests with measured logical resolution and landscape, keyboard visible and hidden, Wi-Fi online/offline, screen locked/unlocked. Take photographs/screenshots from physical S10+, match version hashes and annotate. A mock or desktop preview cannot substitute for phone testing; explicitly mark `PASS_OFFLINE_ONLY` where physical tests are unavailable.

**Defect statuses:** `PASS_PHYSICAL`, `PASS_OFFLINE_ONLY`, `BLOCKED_HARDWARE`, `BLOCKED_ENVIRONMENT`, `FAILED`, `NOT_TESTED`, `DEFERRED_WITH_OWNER_APPROVAL`. Evidence required: log path, timestamp, test command/gesture, actual result, linked code change and deployment hash.

---

## 14. Final engineering outputs and acceptance gates

### Implementation discipline

For each ID A65-01..A65-15, record cause hypothesis then observed proof, exact source module(s), minimal patch and rollback, automated assertion, live file hash, physical test and regression score. Where multiple issues share one root cause (e.g. app windows layered behind shell, Home/Back not reaching native apps, favorites overlay, missing global nav while OSK), prefer **one robust compositor/shell fix**, not fragmented CSS hacks.

Use code-level architecture guides and typed API contracts where applicable, document a state machine for Navigation/AppManager, Network state, DisplayLock policy, Screen Orientation and Camera readiness. Serialize mutable transitions; avoid stale async event/completion races with generation IDs and monotonic timers. Real process and device operation receipts include start/success/failure, exit code and timestamp.

### Deliverable files in `docs/a65-hyperfix-14000/`

1. `00-baseline.md` — current source and physical device truth, preservation/console status.
2. `01-requirements-matrix.md` — all 15 owner issues mapped to reproduction, files, acceptance and status.
3. `02-root-causes.md` — evidence-based hypotheses, proof, upstream dependency links, root cause per fix.
4. `03-source-deployment-map.md` — edited source files, built assets, on-device paths/checksums, process owner and services.
5. `04-test-evidence.md` — reproducible unit/integration and actual S10+ test results.
6. `05-rollback.md` — exact device backup paths, service recovery, revert commands, rescue console.
7. `06-final-verdict.md` — per-issue `PASS_PHYSICAL/...` matrix; camera hardware vs app usability separated.
8. `screenshots/` — owner photos preserved as reference, after-fix physical screenshots, camera diagnostics; protect private data.
9. `logs/` — sanitized network, TLS, lock/wake, orientation, app focus and shell traces.

### Absolute stop conditions

- If USB Live Console is unreliable, STOP risky shell/lock/compositor changes and fix recovery first.
- If an operation risks losing only remaining phone access, do not execute; stage code and ask for owner-guided recovery plan.
- If the phone fails to boot or a critical app unexpectedly traps all input after deployment, roll back **only the affected change** using verified backup and report exact outcome.
- If camera preview requires unavailable vendor ISP support, mark capture BLOCKED_HARDWARE while still completing responsive app and global-escape functionality.
- If auto-rotation sensors are unavailable, don't guess working sensor; provide reliable manual transforms and precise hardware blocker.

### Definition of done

A65 is **not complete** until the phone genuinely browses HTTPS with valid TLS, Wi-Fi labels track real NetworkManager state, Home/Back/long Back/global triple nav work even with OSK and two cameras, launcher favorites stay on Home, selected apps appear in front, per-app redundant header is gone without damaging SnekByte, screen-off locking follows owner-selectable policy, battery shows truthful fresh value, all seven rotation modes can be selected and tested honestly, Calculator waits for Equals, and both Camera apps are escapable. Output truthful remaining hardware blockers and reboot/rollback evidence.

**DO THE WORK. DO NOT TURN THIS INTO ANOTHER NEVER-ENDING DISCOVERY LOOP.** Fix the small high-confidence issues quickly, verify, then move to broader window-manager refactors. Progress issue-by-issue with git checkpoints, keep the USB rescue path alive, and don't call anything working until the actual S10+ proves it.

# 🐧 PENGUIN HYPERFIX 14000 — THE SHELL OWNS THE PHONE, NOT THE SPINNER.

