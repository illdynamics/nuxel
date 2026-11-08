# 🐧🌐 NUXEL A51 — OPERATION WI-FI TO WEB
## Fix persistent Wi-Fi, complete native GTK/Qt/Wayland and Flatpak compatibility, and make Ladybird the preferred real browser on the Samsung Galaxy S10+

**Executor:** DeepSeek-v4-pro-thinking (preferred). Use the actual *current* Nuxel checkout and real phone, not an old ZIP as the deployed truth.

**Hardware:** Samsung Galaxy S10+ **SM-G975F**, Exynos 9820, `beyond2lte`, Fedora ARM64 Nuxel; Samsung vendor Linux **4.14.x** unless the actual installed kernel says otherwise. Development: Fedora laptop is convenient for native Linux builds; MacBook may remain the proven USB-console host. **Target binaries must be AArch64, not x86-64.**

**Owner's exact current error:**

```text
org.freedesktop.NetworkManager.Device.SpecificObjectNotFound:
The access point /new was not in the scan list.
```

**Already observed:** Wi-Fi scans work and the Nuxel UI lists real networks. The user can select an SSID, enter a password, and press Connect, but activation fails. Do not redo Wi-Fi bring-up from scratch or pretend the scanner is broken.

**Definition of success:** On the *physical S10+*, the owner can select their wireless network, enter the password once, connect, obtain a real route/DNS, load HTTPS through a graphical native browser, reboot when authorized, reconnect automatically without reentering the password, and launch an installed native app through Nuxel Home. Establish a functioning Flatpak environment if the kernel's isolation primitives permit it. **Try seriously to build/install/run Ladybird for Linux AArch64** and make it the preferred Nuxel browser if and only if it passes physical acceptance; if upstream/platform limitations prevent that, deliver a functional GTK/WebKitGTK browser and an exact evidence-backed Ladybird continuation plan. No pretend Ladybird skin or mislabeled WebKit view.

**NON-GOALS:** No bootloader/partition flashes, kernel replacement, recovery changes, Android/Magisk, unrelated display-stack rewrites, altered boot artwork, or replacement of the working penguin lockscreen / OSK. No network passwords in commits, build logs, shell history, browser state dumps, photos, or support artifacts. No disabling Flatpak sandbox security merely to claim success.

---

## I. CONFIRMED ROOT-CAUSE LEAD FROM HISTORICAL SOURCE — VERIFY AGAINST LIVE CHECKOUT

In the previously examined `nuxel-v0.6.3-beta-FULL-dropin.zip`, `services/nuxel-bridge/src/bridge.py` contains:

```python
mgr.AddAndActivateConnection(
    dbus.Dictionary(profile, signature='sa{sv}'),
    path,
    '/new',
)
```

Its Wi-Fi scan routine already returns an `ap_path` for each discovered access point:

```python
{'ssid': ssid, 'strength': strength,
 'security': security, 'ap_path': str(ap_path)}
```

`'/new'` is **not** a valid placeholder for a scanned access point. NetworkManager's `AddAndActivateConnection(a{sa{sv}}, o device, o specific_object)` expects the actual **D-Bus object path** of the selected Wi-Fi AP. For `ActivateConnection`, the documented path `/` can allow automatic AP selection; **do not replace `/new` with `/` blindly for `AddAndActivateConnection` without confirming API semantics and profile completeness**. The correct default here is to select/re-resolve an actual AP object from the current Wi-Fi device scan list.

**Authoritative reference:** https://networkmanager.pages.freedesktop.org/NetworkManager/NetworkManager/gdbus-org.freedesktop.NetworkManager.html

Do not treat this historical implementation as proof that the current live build is unchanged. Trace source → built/deployed file → running process → D-Bus request → error. Identify and patch the real active implementation. If another implementation is live, follow its actual code path.

---

## II. HARD PHASE GATES

Complete these **in order**; each phase has observable PASS evidence. A downstream failure must not discard an upstream success.

| Gate | Completion evidence | Must survive reboot? |
|---|---|---|
| **G1 — Wi-Fi** | User-selected WPA2/WPA3 network associates, DHCP, DNS and HTTPS work | **Yes** |
| **G2 — GUI** | A genuine AArch64 native Wayland GTK or Qt app opens, responds to touch/keyboard, and exits | Yes |
| **G3 — Flatpak** | A Flatpak AArch64 app installs, sandbox starts, window and portals work, and launcher integration works | Yes |
| **G4 — Ladybird** | A genuine Ladybird binary with its own engine launches and loads HTTPS on S10+ | Yes, if feasible |
| **G5 — browser fallback** | If G4 blocked, a real WebKitGTK browser works over Wi-Fi and is launchable from Home | **Yes** |

**Do not abandon G1–G3 to spend all available effort fighting upstream Ladybird compiler/toolchain/graphics problems.** Deliver all gates that device evidence genuinely supports and a precise blocker report for the others.

---

## III. PREFLIGHT: SAFE BACKUP AND LIVE-SYSTEM INVENTORY

1. Capture `git status`, branch, commit, key runtime versions, any concurrent A50 performance changes, and whether the actual Nuxel source is mounted read-only / live; use a separate worktree if another agent operates in the same checkout. Don't overwrite A50 work or previous boot-logo patches.
2. Confirm owner-controlled phone identity and USB recovery channel. Test a harmless command and record the method of return/recovery.
3. Record phone architecture (`uname -m`), `uname -r`, Fedora release, storage (`df -h`), RAM, live display/server environment (`WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, session user and bus), available repositories, `rpm -q` status for `NetworkManager`, `flatpak`, `webkit2gtk*`, Qt runtime, D-Bus packages.
4. Capture `nmcli -g GENERAL.STATE,GENERAL.CONNECTION device show <actual-wifi-interface>`; `nmcli device status`; `nmcli -f GENERAL,IP4,IP6 device show`; `nmcli -f IN-USE,SSID,BSSID,FREQ,SIGNAL,SECURITY device wifi list` with redaction where appropriate. Commands are examples: find actual interface; avoid assuming `wlan0`.
5. Inspect systemd NetworkManager unit, permission/polkit model, settings paths, bridge unit/service user, Wi-Fi frontend JS, settings UI, Quick Settings, and existing Nuxel app launch path. Record whether a second daemon or frontend is rewriting Wi-Fi state.
6. Back up *files about to be changed*, NetworkManager configuration files, affected user profiles, launcher manifests, and bridge service units to an off-device location with SHA-256. **Do not export readable PSKs** to publicly shared logs; encrypt credential-bearing backups, lock down permissions, and scrub secrets from diagnostic bundles.
7. Establish reversible userspace deployment. Preserve the working live USB-console service and the graphical session. No partition write or kernel replacement.

Create `A51-PREFLIGHT.md` and `A51-ROLLBACK.md` before modifying services.

---

## IV. ROOT CAUSE — TRACE THE REAL CONNECT BUTTON, THEN REPAIR NETWORKMANAGER D-BUS

### A. Trace one end-to-end request

Follow: `Nuxel Wi-Fi list` → selected scan object/SSID/BSSID/security/AP path → password prompt → frontend bridge request → backend `connect_wifi` → chosen device D-Bus path → chosen AP D-Bus path → `AddAndActivateConnection` / `ActivateConnection` → active connection state. Trace receipt IDs and redacted errors. Identify any change in AP path between list and selection.

The historical bridge signature accepted only `(ssid, password, security)` and discarded the selected `ap_path`. Fix the contract **without blindly trusting a frontend-supplied D-Bus path**. Return enough metadata to the UI for a stable selection; server-side verify the selected AP is **currently listed on the same Wi-Fi device**. SSID can contain arbitrary bytes and duplicate SSIDs are normal; where possible prefer verified BSSID / AP object identity rather than assuming the display name uniquely identifies one AP. Hidden networks require a separate explicit path; never fabricate AP IDs.

### B. Correct semantics

- Obtain actual Wi-Fi device object path from NetworkManager; do not assume interface name or platform path.
- Query `org.freedesktop.NetworkManager.Device.Wireless` (including `GetAccessPoints()` and potentially `GetAllAccessPoints()` as supported) and AP properties. Read SSID as **bytes**; compare carefully with user-selected network. Validate object paths using D-Bus types.
- For a new selected Wi-Fi AP call `AddAndActivateConnection` with the **actual verified AP object path** and correct D-Bus `a{sa{sv}}` profile structure. The method's returned settings/active paths must be captured; activation is async.
- For an existing saved connection use the saved settings-connection object path with `ActivateConnection`, selecting a suitable AP or `/` where supported. Avoid creating a duplicate connection profile each time the user taps Connect.
- On stale AP path: refresh scan results / re-find matching SSID+BSSID, retry **at most once or a small bounded number**, and return a human-readable stale-scan error if the AP genuinely disappeared. Do not loop indefinitely or connect to a different SSID without user consent.
- Send a deliberate `disconnect` via NetworkManager without deleting the saved profile. Support explicit **Forget network** separately.
- Honor WPA2-Personal, WPA3-SAE, and supported mixed WPA2/WPA3 policies as reported by the **actual RSN information**, not merely a guessed security badge. Do not silently downgrade from user-requested security. Enterprise/EAP and WEP should explicitly report unsupported until implemented securely; do not pretend any password works.
- Preserve radio enable/disable and existing Quick Settings behavior; no `rfkill unblock all` as a broad fix. Handle missing AP, invalid PSK, timeout, DHCP failure, DNS failure, captive portal and disabled radio with distinct UI messages.
- Password prompt must allow the Nuxel native keyboard, show/hide password if already supported, and never leak credentials into URL query params, shell command arguments or bridge logs. Check NetworkManager secret flags / secret-agent design. Do not call `nmcli` with plaintext password in a visible process argument or shell history.
- Use typed D-Bus variants consistently. Compare with `nmcli`/libnm only as *diagnostic* independent validation, not as a lasting fragile command-string workaround if an existing D-Bus backend is appropriate.
- Eliminate the literal `/new` path **from all executable Wi-Fi activation call sites** and protect against its regression with a unit test.

### C. Lifecycle: no optimistic false success

Do not return `connected` immediately after `AddAndActivateConnection`. Distinguish:

`SCANNING → PASSWORD_REQUIRED → ASSOCIATING → AUTHENTICATING → IP_CONFIGURING → CONNECTED_LOCAL → INTERNET_VERIFIED`

With failure transitions and explicit captive-portal / internet-unavailable states. Use NetworkManager properties, state-change signals, bounded timeouts, and active connection object state; handle stale signals and cancellation with an operation ID. Display association + IP acquisition progress in the frontend without freezing touch controls. A locally connected network may have no internet; display that truthfully.

---

## V. PERSISTENT WIFI PROFILES AND USER PREFERENCES

This is *not complete* when the user can connect once. NetworkManager must save a durable connection profile (through its settings service) and autoconnect on normal boot **without another prompt**.

Implement and test:

- Saved SSID/BSSID/security policy and stored secret through the supported NetworkManager secret/profile facility (privileged files readable only by appropriate principals). **Never cache plain Wi-Fi passwords in Nuxel frontend localStorage or unencrypted application JSON.**
- `connection.autoconnect=true` by default for successfully joined user networks; allow user disable per network.
- Default `autoconnect-priority` policy sensible for multiple known networks, without an overly aggressive retry loop.
- Reuse saved profiles after reconnect; don't create `Nuxel <SSID>`, `Nuxel <SSID> 2`, `...3` duplicates.
- Persistent remembered/available network UI after Nuxel bridge restart, graphical session restart, and approved cold reboot.
- Saved networks list: SSID, currently connected, auto-connect on/off, manual Connect, Disconnect, Forget, signal, security, and human-readable status. Avoid exposing PSKs to frontend.
- Wireless switch state persistence, loss-of-AP recovery, Wi-Fi roaming when an SSID has multiple APs, wrong-password correction, and device wake/resume reconnect.
- DNS and time synchronization required for HTTPS certificates; do not disable TLS verification to make browsing appear successful.
- Keep default route and DNS authoritative; avoid manually writing `/etc/resolv.conf` if NetworkManager or systemd-resolved manages it.
- Handle profiles owned by different Unix/system contexts, polkit and service permissions. Do not make the entire bridge root-accessible from arbitrary web pages just to manage Wi-Fi.

If Nuxel creates a separate settings UI model, make it a **view of actual NetworkManager state**, not an independent fiction that diverges at boot.

---

## VI. VERIFY REAL INTERNET CONNECTIVITY — NOT JUST A GREEN ICON

On the physical phone, after owner enters the password in Nuxel UI:

1. Confirm link association, BSSID, driver state and correct device NM active state. Do not log the user's private SSID/BSSID unnecessarily in the final public report.
2. Confirm valid IPv4 and/or IPv6 lease/address, default route and DNS resolver.
3. Resolve a public hostname with system DNS (`getent ahosts example.org` or available equivalent).
4. Make an HTTPS request with standard TLS verification, e.g. `curl -I --max-time 15 https://example.org` (network behavior may vary; try a second known-safe endpoint if needed).
5. Distinguish DHCP vs route vs DNS vs TLS/certificate/time vs captive portal.
6. Test an actual web page in a graphical native browser, not just terminal `curl`.
7. Disconnect, reconnect via saved profile without password; turn Wi-Fi off/on; lock/wake; restart bridge; on **owner-approved reboot** validate autoconnect and repeat HTTPS test.
8. Check USB console remains available when Wi-Fi fails, avoiding a network-dependent recovery path.

Produce state-transition tests, unit tests mocking AP selection, and live D-Bus evidence. Never print the user's PSK in screenshots or CI logs.

---

## VII. NATIVE LINUX APPLICATION COMPATIBILITY (WAYLAND/GTK/QT/WEBKITGTK)

**Two independent surfaces:** Nuxel PWA apps using WebKitGTK and **native Linux GUI programs**. Do not conflate them. A browser like Ladybird has its own engine/UI; it is not a WebKitGTK embedded page.

Inspect the running Phoc compositor and session user. Prove that a separate AArch64 GUI application can run via Wayland **on the physical display**, with correct screen scaling and touch/OSK, not just in a headless nested session. Determine if GTK3/GTK4 applications and Qt6 Wayland apps can start. Check `libwayland-client`, `qt6-qtwayland`, WebKitGTK runtime versions, fontconfig, `xdg-open`, graphical app environment, D-Bus session bus, clipboard, TLS CA bundle, and Mesa/EGL or honest software-rendering fallback.

Make a reusable **Nuxel native-app launcher** running as the correct user, with the correct `XDG_RUNTIME_DIR`, `WAYLAND_DISPLAY`, `DBUS_SESSION_BUS_ADDRESS`, locale, scaling and PATH. **Do not globally export an unsafe `QT_QPA_PLATFORM` or hardcode root's runtime directory.** Use conditional per-app Qt Wayland environment if needed; don't unconditionally disable application sandboxes/GPU isolation. One launcher must not hijack existing Nuxel Home or triple-button behavior.

Integrate FreeDesktop `.desktop` manifests and installed app metadata into the existing launcher/registry without duplicate stale entries. Install and launch a small known ARM64 GTK native test app (choose after querying available Fedora packages). Verify:

- Appears in app drawer / Nuxtore installed list (as appropriate).
- Opens on the visible phone, receives touch, text via *working grey/black/blue native OSK*, and can close.
- Short Back dismisses keyboard first; Home returns Home; long Back closes only the current foreground application where Nuxel explicitly supports that behavior.
- No app window renders under an invisible always-on-top overlay; bottom four home shortcuts are not rendered over full-screen apps.
- App remains launchable following authorized reboot; no reliance on `adb shell` or stale root environment.
- Browser, PDF, file URL and application-link dispatch respect MIME types and user-selected defaults without allowing arbitrary webpage code to execute privileged commands.

For WebKitGTK apps: verify actual network access, JavaScript, TLS, cookies/storage, local navigation, session isolation, link handling and platform integration. Fix specific blockers rather than rewriting everything as a new PWA. Preserve the working lockscreen/keyboard.

---

## VIII. ENABLE REAL FLATPAK, IF AND ONLY IF SANDBOX PRIMITIVES WORK

**Historical finding:** `docs/beta-finalization/live/procedures/nuxtore-and-flatpak.md` in the earlier Nuxel archive explicitly states Flatpak was **not installed** on the then-current handset, although manifests exist under `pwa/flatpak/` for an experimental `org.nuxel.Platform` and Nuxel PWA applications. Recheck against current phone. Do not claim Flatpak is already deployed because manifest JSON files exist.

### A. Install safely

- First verify real Wi-Fi/DNS/HTTPS and Fedora architecture/release/repository signature trust.
- Check capacity and RAM; Flatpak runtimes can be large. Avoid filling rootfs or userdata.
- Use Fedora's package manager to install official `flatpak` and appropriate `xdg-desktop-portal` implementation *only after viewing the exact planned transaction*. Keep kernel, firmware, bootloader, critical display stack and security units excluded from unexpected upgrades.
- Add the verified Flathub remote from the official canonical URL **only after checking transport and GPG trust**; preserve stock Fedora repository settings and provenance.
- Choose user vs system installation deliberately; keep it consistent with the Nuxel graphical session; no global root-owned app installs that the normal session can't launch.
- Verify Flatpak architecture: `flatpak --default-arch` should map to `aarch64` or correct Flathub triplet. A manifest for `x86_64` is not usable on the phone.

### B. Kernel sandbox capability gate (CRITICAL)

Samsung's old 4.14 kernel may have restrictions on user namespaces, mount namespaces, seccomp, overlay filesystems and bubblewrap. Run **non-destructive** real tests of:

- `CONFIG_USER_NS`, user namespace availability and policy;
- unprivileged namespace creation and mount namespace support;
- bubblewrap startup and its needed syscall / seccomp behavior;
- Flatpak sandbox as the target ordinary user (not merely `flatpak --version` as root);
- GLib/GIO D-Bus session and XDG portals (`org.freedesktop.portal.Desktop`), `xdg-desktop-portal` backend availability under Phoc; document features that need compositor-specific implementation.

**Never disable seccomp, mount isolation, namespace restrictions, SELinux or system security policy just to label Flatpak functional.** If a safe supported configuration is available, document precisely; otherwise declare `FLATPAK_SANDBOX_BLOCKED_BY_KERNEL` with actual logs. Do not secretly switch to `--no-sandbox`, `--filesystem=host`, or privileged launch. Native RPM/browser fallback still must work.

### C. Flatpak execution and UI

- Install a small *real* published AArch64 GUI Flatpak chosen from actual remote metadata (do not assume every app has ARM64 builds).
- Verify `flatpak run <real-app-id>` starts inside sandbox, displays on phone, uses touch/keyboard, and can be exited.
- Validate TLS/network if the app uses networking; document portal capability gaps (file chooser, URI open, notifications, screenshots, settings, secrets).
- Support manifest lifecycle, remote/user scope, desktop launcher registration, icons, application updates, and uninstall through normal tools.
- Update Nuxtore realistically: display native RPM apps, installed Flatpaks, or existing verified Nuxel bundles as **distinct** types; no fake install buttons claiming software deployed when no package was actually installed. Keep application signatures/GPG trust provenance intact.
- Do not make the custom `org.nuxel.Platform` WebKit runtime a mandatory prerequisite for launching **unrelated** third-party Flatpaks.

Reference: https://docs.flatpak.org/ and https://flatpak.org/setup/Fedora .

---

## IX. LADYBIRD — PREFERRED NATIVE BROWSER; ACTUAL AARCH64 FEASIBILITY FIRST

**Upstream:** https://github.com/LadybirdBrowser/ladybird

**Official build guide:** https://github.com/LadybirdBrowser/ladybird/blob/master/Documentation/BuildInstructionsLadybird.md

**Status caveat, October 2026:** The official README still identifies Ladybird as a **pre-alpha developer browser**. Current upstream build instructions specify **Qt 6.10+** (check exact pinned commit), CMake **3.30+**, C++23, Rust, nasm and a platform-specific Qt frontend. Requirements change: consult exact commit's docs, not a historical guide. A successful Linux x86_64 build does **not** imply AArch64 support or usable S10+ GPU driver support. Don't claim it is generally release-ready.

### A. Feasibility and traceable build

1. Check whether official Ladybird releases / Flathub publish an **actual Linux AArch64 build**. Use it only if provenance and checksum/signature are verified. Do not assume there is one.
2. If no suitable binary, inspect the upstream repo at a pinned commit; audit host and target requirements, any x86-specific assembly/nasm dependencies, vcpkg target triplets, Qt library versions, LLVM/GCC versions, Rust target, CMake, Skia, rendering backend and build scripts. Look for documented AArch64 support or open issues.
3. Prefer development on the Fedora laptop with sufficient CPU/RAM/disk. It is **x86_64**, so either cross-compile properly with an AArch64 sysroot/toolchain, use a genuine AArch64 build host, or, only if practical, build carefully on the phone. Never copy the laptop's x86_64 Ladybird binary onto the phone expecting it to run.
4. Pin source revision and dependencies; avoid installing experimental C++/Qt development stacks wholesale onto the fragile phone. Build in isolated staging; package only required compatible runtime libraries and support files. Inspect licensing and use official code only.
5. Produce exact `file`, `readelf -h`, ABI and shared-library audit; confirm `AArch64`, compatible glibc, Qt Wayland plugin, SSL/certificates, font assets and required subprocess binaries. All Ladybird subprocess executables must also be AArch64.
6. If build genuinely succeeds, install an isolated, reversible Nuxel Ladybird package with a `.desktop` file, correct launcher and icon; do not overwrite Nuxel's existing Browser until it passes live testing.
7. If a critical dependency (e.g. unsupported AArch64 assembler, incompatible Qt, missing EGL, inaccessible Wayland feature, unavailable memory) blocks progress, investigate a bounded documented workaround—not arbitrary vendor-driver patches or unsafe process sandbox bypasses. Emit exact blocker, upstream issue link if known, and reproducible build logs. Continue to Section X so real browsing is delivered.

### B. On-phone acceptance for actual Ladybird

Verify on S10+:

- Ladybird own window shown through Phoc/Wayland (not a WebKitGTK wrapper pretending to be Ladybird).
- HTTPS loads e.g. `https://example.org` with valid TLS; browse a second real standards-oriented site.
- Tap address bar; **native OSK actually types**; Enter navigates; Back/Home/close respond; no focus trap.
- Scrolling, viewport scaling, painting and touch targets are usable on the tall screen; note limitations rather than rewriting upstream engine.
- 2+ tabs if stable, page back/forward, text selection, bookmarks if available in this version.
- Network errors/certificate failures handled honestly; no insecure TLS bypass.
- Browser recovers or fails cleanly; does not cause thermal runaway, lockups, or destroy Nuxel graphics/session.
- Application profile files stored under user-owned location; service restart/authorized reboot keeps the launcher and default browser behavior.

Only after tests pass make it the preferred native browser in Nuxel. Explicitly label its developer/pre-alpha nature, and preserve a reliable browser fallback for normal internet testing.

---

## X. GUARANTEED PRACTICAL BROWSER PATH WHEN LADYBIRD IS BLOCKED

**Do not invent a false guarantee of Ladybird success.** The purpose of this phase is to deliver the user's most important outcome—open a real website through real working Wi-Fi—**even if Ladybird needs further ARM64 engineering**.

1. Check Fedora AArch64 availability of `epiphany` (GNOME Web), a conventional GTK/WebKitGTK browser, or another maintained compatible native browser supported by installed kernel, GTK/Wayland and libraries. Confirm the actual package identity from configured repositories instead of guessing.
2. Install the chosen signed RPM or a validated Flatpak if G3 passes. Prefer RPM if Flatpak kernel isolation is blocked.
3. Launch under the normal Nuxel user Wayland session through the native-app launcher; keep hardware safety, CA/TLS verification and system keyboard integration intact.
4. Prove real URL loading over the **newly connected Wi-Fi**, scrolling, link clicks, keyboard input, Back, Home, and closing the browser. Use a second site and follow redirects.
5. Register it in Nuxel Home and the Browser shortcut. Set default only with deliberate owner preference; keep Ladybird listed as `Experimental` if partially deployable, and ensure the fallback remains launchable.
6. If even Epiphany/WebKitGTK cannot render because of compositor / graphics problems, identify the first broken layer and fix the smallest supported issue. A WebKit view inside a launcher is **not by itself** equivalent to a separately installable native browser; provide genuine application/window lifecycle.

Preserve current WebKitGTK Nuxel PWA functionality. It is fine for Ladybird (Qt) and native GTK apps to coexist.

---

## XI. NUXEL UX AND STATE CONTRACTS

### Wi-Fi Settings

- List detected APs with actual strength and security; allow selecting duplicates explicitly if needed.
- Connecting spinner with phases, timeout/cancel, errors mapped to backend state.
- Accurate connected marker, IP/Internet verified signal, optional captive-portal notification.
- Saved networks screen with auto-join toggle, connect/disconnect/forget, secure password change.
- Wi-Fi Quick Settings tile reflects actual NetworkManager state, not stale localStorage.
- Back dismisses password keyboard first, then popup; Penguin Home returns Home without killing NetworkManager; lockscreen never exposes the OSK.
- Never disclose Wi-Fi credentials to ordinary web pages or unrelated apps; narrow bridge API and permissions.

### Application management

- Apps installed from RPM, Flatpak or native hand-built packages appear in correct categories without replacing Nuxel PWA registry with a second independent registry.
- Distinguish app IDs, display names, Exec quoting, icons, MIME types, system vs user scope, Flatpak sandbox and native apps.
- No untrusted `.desktop` command injection or direct execution of names supplied from a webpage. Nuxel launcher must validate trusted app metadata and run under limited normal user identity.
- Define browser preference selection, default browser handling and reasonable error fallback.

---

## XII. TEST MATRIX — AUTOMATED + REAL HANDSET

### Unit / integration (host or isolated test service)

- Reject the literal `/new` sentinel in `specific_object` for new Wi-Fi AP activation.
- Choose real AP path tied to Wi-Fi device; stale path triggers bounded refresh; duplicate SSIDs and SSID byte handling.
- Correct DBus typed `a{sa{sv}}` mapping for WPA2/WPA3/open profiles; reject unsafe/incomplete profiles.
- Connection completion only on appropriate NM state transitions, not method return.
- Authentication failure shows retryable UI but doesn't print PSK.
- Existing profile activation doesn't duplicate saved profiles.
- Autoconnect flag and secret ownership persist through bridge/process restarts.
- Back, Home, keyboard and launcher integration remain functional.
- App metadata and `.desktop` validation prevent arbitrary execution.
- Flatpak non-sandboxed failure is reported, never silently treated as pass.
- Native AArch64 executable architecture validated; `libLadybird`/processes distinguished from WebKitGTK fallback.

### Physical S10+ (required, not simulated)

1. Unlock phone; scan; select home SSID; type PSK via real working on-screen keyboard.
2. Press Connect → successful authentication, valid DHCP/route/DNS, Internet verified.
3. Browse HTTPS from native GUI. Open two sites and tap/scroll/type.
4. Turn Wi-Fi off then on → remembered AP reconnects without new password.
5. Disconnect then reconnect; check user preference and saved profile survived service restart.
6. Try an incorrect password **on a dedicated test network or only with owner approval**; verify clear error without leaking password and success after correction.
7. Launch GTK test app; verify correct input, Back, Penguin Home, foreground lifecycle.
8. Attempt Flatpak install/run as unprivileged GUI user; verify isolation with actual evidence.
9. Attempt Ladybird build/install/run and record true PASS/BLOCKED. If blocked, launch WebKitGTK fallback and browse normally.
10. Reboot **only with owner approval after a verified recovery route**; confirm saved Wi-Fi autoconnect, default browser, installed app registry, GTK/Qt session env, and no orphaned daemons.
11. Reconfirm Nuxel Home, lockscreen, working native keyboard, resource monitors and USB console remain functional.
12. Observe CPU/RAM, FPS, idle watts/thermals where measurable. Browsing must not leave a runaway CPU loop when the screen is locked/off.

A screenshot showing the network list is *not* proof of Wi-Fi connectivity. `curl` alone is *not* proof of graphical browser integration. Seeing a Flatpak version number is *not* proof the sandbox runs. A desktop icon is *not* proof Ladybird works.

---

## XIII. DEPLOYMENT, ROLLBACK AND NO-REGRESSION

- Work in small reversible commits: (1) NetworkManager bridge, (2) persistent profiles/UI, (3) GUI launcher, (4) Flatpak setup, (5) browser integration and Ladybird experiment.
- Run targeted tests after each change, then deploy over proven live USB console.
- Back up prior service files/packages and profile metadata before replacing. Beware secrets in backups.
- Restart only affected userspace components; keep compositor/recovery alive if possible.
- Inspect current Nuxel compatibility with A50 performance work; don't disable graphics optimizations as an unexplained fix.
- Snapshot `dnf` transaction IDs and new packages; provide supported rollback path. Do not blindly revert all DNF transactions since earlier missions.
- Preserve saved user Wi-Fi profiles during normal Nuxel upgrades, but if rollback is needed restore them safely without disclosing PSKs.
- No kernel upgrades, partition writes, firmware flashing or USB gadget removal. Stop if a package transaction proposes unexpected critical changes.
- If device connectivity is temporarily lost, use the working USB console to recover; don't rely on the very Wi-Fi being repaired.

---

## XIV. REQUIRED DELIVERABLES

Produce the following in a dedicated `docs/a51-wifi-to-web/` folder or equivalent established project conventions:

1. `PREFLIGHT-AND-ROOT-CAUSE.md`: active source path, actual bad call, NetworkManager device/AP mapping and redacted trace.
2. `NETWORKMANAGER-FIX.md`: exact diff, typed signatures, AP selection, profile reuse, error model, secret handling.
3. `WIFI-PERSISTENCE-TEST.md`: user-entered network connection, service restart, owner-approved reboot results and saved profile state without secrets.
4. `NATIVE-GUI-COMPATIBILITY.md`: actual Phoc/Wayland, GTK/Qt/WebKitGTK, launcher, input integration and physical tests.
5. `FLATPAK-ARM64-READINESS.md`: installation provenance, actual sandbox/portal test verdict, old-kernel restrictions and remediation if blocked.
6. `LADYBIRD-AARCH64-BUILD.md`: pinned git commit, official requirements, host/target toolchains, build logs, architecture, binary deps, live Qt/Wayland result or precise blockers and continuation plan.
7. `BROWSER-ACCEPTANCE.md`: chosen default browser, actual URL and TLS/keyboard/touch tests, fallback if necessary.
8. `A51-ROLLBACK.md`: per-change rollback and recovery instructions with receipts.
9. Source commits and focused tests; never commit owner Wi-Fi secrets.

Summarize final status as **PASS / PARTIAL / BLOCKED / FAIL** separately for G1–G5, with actual console/log evidence and owner-observable proof. Don't claim that Ladybird was shipped if only a build was attempted. Don't claim persistent Wi-Fi without a reboot test.

---

## XV. EXECUTION PRIORITY AND FINAL DIRECTIVE

**Do not stop after saying “the Wi-Fi path should be fixed.”** Implement, deploy, physically verify and make saved preferences persist, then enable normal Linux graphical applications and sandboxed Flatpaks where supported. Pursue *real* Ladybird on ARM64 as the owner's first choice, without inventing compatibility. Deliver a usable WebKitGTK browser fallback if needed so the owner can actually browse the web at the end.

**Minimum non-negotiable result:** On the S10+, press Connect, obtain internet, open a real graphical browser, navigate HTTPS and reboot back into the same saved Wi-Fi setup.

**Stretch result:** Genuine Ladybird launches from Nuxel Home, renders HTTPS via its own engine, uses the phone's touch/OSK, and remains usable over the newly working Wi-Fi.

**GO GET THE PENGUIN ONLINE. 🐧🌐🔥**
