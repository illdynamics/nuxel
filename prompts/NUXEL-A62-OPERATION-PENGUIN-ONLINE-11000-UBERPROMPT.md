# 🐧🌐🔥 NUXEL A62 — OPERATION PENGUIN ONLINE 11000
## Ultimate Galaxy S10+ Wi-Fi Association / Authentication / Internet / Browser Repair Mission

**Executor:** Codex, preferably `gpt-5.6-sol` with high reasoning, in the **current** Nuxel checkout.

**Target:** Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Nuxel Fedora ARM64 userspace with Samsung-derived Linux 4.14 hardware stack, custom Nuxel Home, native/WebKitGTK applications and a USB Live Console.

**Owner-visible bugs:**
- Scanning discovers actual SSIDs; selecting a network and entering the password never completes. The UI is stuck at **“Authenticating and associating”**. Earlier versions stalled at **“Associating DHCP...”** and previously failed with `org.freedesktop.NetworkManager.Device.SpecificObjectNotFound: the access point /new was not in the scan list`.
- Nuxel's Browser cannot yet reliably browse the external internet. A browser window/icon or a local HTML page does not constitute working web access.
- The owner wants **real internet browsing**, preferably a repaired/custom Nuxel Browser plus **Firefox, Chromium** and optionally **Ladybird** where technically compatible.

## Absolute outcome

**On the actual S10+**: scan → select SSID → enter correct password → associate/authenticate → obtain network configuration → resolve DNS → load HTTPS → open Nuxel Browser → navigate to `https://www.google.nl` → enter a search and follow results → close/reopen → reboot → reconnect automatically → browse again. Never declare success from mocks, an installed binary, a spinner, or an HTTP response on the development laptop.

**Priority:** Wi-Fi connectivity and stability FIRST, working Nuxel WebKitGTK browser SECOND, additional browsers THIRD. Finish and physically verify the first two before expensive Ladybird work.

---

## Non-negotiable safety and ownership rules

1. Work against the **actual current repository and deployed live S10+ revision**, not a remembered v0.6.x snapshot. Inspect branch, dirty files, active services, installed Python/JS, package versions and all running Wi-Fi controllers before proposing changes.
2. Preserve the functioning penguin lockscreen/unlock, three-button navigation, keyboard, SnekByte, docks, graphics, sensors, camera work, and USB Live Console. Do not casually restart the compositor or destroy a functioning connection to the device.
3. **No kernel, DTB, bootloader, partition, recovery, firmware or rootfs image flashing.** Do not bypass authentication, browser sandboxing, WPA security, SELinux/AppArmor or networking permissions as a “fix.” Do not overclock.
4. Obtain the owner's approval before a reboot, disruptive service restart, modification of live device networking or broad software installation where the established workflow requires approval. Maintain an independent USB recovery route; network changes must not strand the console.
5. NEVER collect, print, commit or log Wi-Fi passwords, PSKs, private keys, cookies, tokens, saved-browser secrets or raw system connection profiles. Sanitize diagnostic traces before retaining/sharing. Avoid `nmcli --show-secrets` and avoid logging D-Bus payloads that include secrets. Store profiles only in standard protected NetworkManager storage.
6. Back up target source/config files before changing them, record rollback commands, and edit in focused commits. Unit/offline tests are supplementary; physical S10+ acceptance is mandatory.
7. Keep documentation and UI honest: `CONNECTED` only after NetworkManager activation and verified network configuration; `INTERNET_OK` only after DNS+HTTPS. Do not silently generate synthetic Wi-Fi states or pretend a localhost page is external internet.
8. If a supported feature is genuinely blocked by vendor kernel/driver/firmware or ARM64 graphics, deliver full diagnosis and the best safe usable subset. Never manufacture green hardware statuses.

---

# PHASE 0 — Freeze state, identify provenance, preserve rollback

Produce `docs/a62-wifi-browser/00-baseline.md` containing:

- git HEAD, branch, dirty changes and active staging work; do not destroy in-progress A60/A61 changes.
- Running Nuxel services, device identifiers (sanitized), installed Bridge sources, compiled/installed JS bundles, WebKit host, current browser packaging, network config sources, NetworkManager version, wpa_supplicant/iwd versions, Fedora release and kernel.
- NetworkManager unit state, Wi-Fi driver/module, firmware file/version if visible, interface name, radio/soft block/hard block, regulatory state, managed/unmanaged state, MAC randomization policies, Wi-Fi chipset identity from actual evidence.
- Whether phone is connected over stable recovery USB and whether the operator has an alternate communications channel.
- The current issue as observed on physical phone: exact start time, selected SSID (redacted for exported logs), activation changes, UI progression and terminal failure or timeout.
- Baseline `nmcli` and kernel facts with sensitive data redacted; separate host and phone information clearly.
- Known-good and known-bad Git revisions if available; compare old `/new` regression and more recent failures.

Sample read-only diagnostics, adapt interface/service names to **this** device:

```sh
uname -a
cat /etc/fedora-release
systemctl is-active NetworkManager
nmcli general status
nmcli device status
nmcli radio all
nmcli -f IN-USE,SSID,BSSID,FREQ,SIGNAL,SECURITY,DEVICE device wifi list
nmcli connection show
ip -br link
ip -br addr
ip route
rfkill list
journalctl -b -u NetworkManager --no-pager -n 250
```

Use `iw dev`, `iw phy`, `ethtool -i <actual-interface>` and `lsmod` **when available**; vendor-kernel drivers may report partially. Never assume an interface called `wlan0` or a specific Broadcom chip. Avoid copying private profiles/secrets into documentation.

### Reality check
A stale UI saying *“Authenticating and associating”* may mean the network is truly failing or that the backend completed and the UI stopped receiving state events. Investigate both before changing either.

---

# PHASE 1 — Wi-Fi state-machine forensic investigation (CRITICAL)

Trace the complete chain with correlated timestamps and correlation IDs:

**Nuxel UI Connect tap → selected scan entry/SSID/BSSID/AP object path → Nuxel bridge request → NetworkManager device/profile object → supplicant association → WPA authentication/4-way handshake → NetworkManager activation → IPv4/IPv6 config → DNS → reachability check → UI terminal state**.

Precisely distinguish:

| Stage | Evidence | Examples of failure to distinguish |
|---|---|---|
| Scan | SSID/BSSID/channel/RSSI, AP object | stale or missing AP |
| Association | `iw ... link`, NM device state and logs | incompatible band/channel, AP rejection, timeout |
| WPA authentication | supplicant state and NM reason codes | wrong PSK, unsupported WPA3/PMF, stale credentials |
| Activation | NM `ActiveConnection` transitions | bridge returns too early, missing event handler |
| DHCP/IP | address, gateway, lease logs | DHCP refused/timed out after association |
| DNS | resolver and domain response | wrong DNS, stale resolv.conf |
| TLS/web | real remote HTTPS response | clock/certificate/proxy/captive portal |

Do **not** treat the textual stage “Associating DHCP...” as a real NetworkManager state; it may be an incorrect aggregated label. Collect the device's **actual** `NMDeviceState` and **state reason**, `ActiveConnection` state, and supplicant/driver indicators. An API call returning successfully means activation began—not necessarily that authentication and IP config succeeded.

Never swallow D-Bus exceptions or translate every failure into `AUTHENTICATING`. Map exact codes to actionable localized user-visible messages and a bounded retry option. Use event subscriptions rather than busy polling, but include timeout/cancellation and state reconciliation when signals are missed.

For diagnostics, temporarily raise NetworkManager logging only to appropriate supported domains and restore original levels after collection. Keep logs free of passwords and ephemeral credentials.

---

# PHASE 2 — Fix actual NetworkManager D-Bus activation and AP selection

Inspect the **current** source, especially historical path `services/nuxel-bridge/src/bridge.py`, scan-to-connect flow, frontend selection persistence, and auth settings. Previous versions used an invalid literal `'/new'` in `AddAndActivateConnection`.

### Strict D-Bus rules

NetworkManager's `AddAndActivateConnection` accepts:

```
AddAndActivateConnection(a{sa{sv}} connection, o device, o specific_object)
```

For Wi-Fi, `specific_object` must identify a real **current access-point object path belonging to the target device**, sourced from its scan list. Never invent `/new`. For operations that explicitly support automatic AP selection, use the documented neutral path **`/`**, not `/new`, and do not use it indiscriminately when creating an AP-dependent new connection. Verify method-specific semantics from installed NetworkManager's D-Bus introspection/API version.

### Specific repair requirements

- Use actual scanned `ap_path` and device D-Bus object path, with correct `dbus.ObjectPath` types and correct nested `a{sa{sv}}` profile signature.
- Revalidate selected AP still exists immediately before activation; handle disappearing/stale paths with a short explicit rescan and re-selection rather than looping forever.
- Match BSSID/SSID bytes correctly, including escaped/non-ASCII SSIDs; distinguish multiple APs advertising the same SSID; do not bind a roaming profile forever to an outdated BSSID unless explicitly requested.
- For existing saved connections, prefer activating the known profile by stable NetworkManager object/UUID rather than adding a duplicate network every attempt.
- Use compatible security settings for WPA2-Personal, WPA3-Personal/transition, open networks and enterprise only if implemented; do not misuse WPA/RSN flags or hard-code `key-mgmt=wpa-psk` against a genuinely SAE-only network.
- Handle supplicant secret requests through the intended credential flow, keep secrets in NetworkManager with proper permissions, and never put a password into a command-line argument/process listing.
- Ensure `autoconnect` and priority are persisted through NetworkManager; handle profile edits and password changes intentionally.
- Interpret connection activation as asynchronous and track it through activated/failed states with bounded timeouts and precise reason codes.
- Ensure only **one** subsystem manages a Wi-Fi device: inspect duplicate `wpa_supplicant`, `iwd`, ad-hoc `wpa_cli`, scripts, conflicting `systemd-networkd` management, and repeated bridge connection requests. Preserve the configured intended stack.
- Ensure NetworkManager is the single source of truth for connected SSID, BSSID, IP, gateway and connection status; avoid a second independent fake frontend store.

### Test the two control paths independently

**Control A:** From the live phone console, connect via the supported `nmcli` interactive secret-safe path (e.g. `nmcli --ask device wifi connect <SSID>` with the actual interface, confirming command availability locally). **Do not include Wi-Fi password in shell history or command line.**

**Control B:** Connect through Nuxel Settings with the on-screen keyboard.

If A fails, focus on NetworkManager, driver, firmware, security and AP. If A works but B fails, focus on bridge/profile/signals/UI. If A and B both work but internet fails, continue to network configuration diagnostics.

### WPA/driver investigations

Where evidence points there, inspect kernel messages for firmware resets, association rejects, scan instability, `cfg80211`/`nl80211` errors, auth timeouts, regulatory domain, WPA3-SAE/PMF compatibility, roaming, random MAC interactions, 2.4/5 GHz, channel restrictions and power saving.

As a **controlled differential test** only, compare the owner's regular AP and a known-compatible temporary WPA2-Personal 2.4 GHz hotspot if available, without weakening the owner's router or pretending a hotspot proves home-router compatibility. Do not hardcode a specific SSID/PSK, disable router security or impose unsafe permanent system settings.

If a firmware/kernel bug is actually demonstrated, write a separate reproducible driver-level blocker and safe backport plan; no unapproved kernel modifications/flashes in this mission.

---

# PHASE 3 — Finish IP assignment, DNS, HTTPS and reconnection persistence

**Association is not success.** Once the link is established:

1. Confirm NetworkManager reports fully activated.
2. Confirm IPv4 and/or IPv6 addresses and intended default route are real and sane; validate DHCP negotiation and lease renewals.
3. Confirm DNS resolution through the phone's actual resolver configuration. Separate a broken DNS resolver from absent routing.
4. Confirm system time is reasonably accurate for TLS checks; do not disable certificate verification to “fix” HTTPS.
5. Perform DNS and HTTPS reachability tests on the **phone**, not the Fedora laptop or MacBook. Test `https://www.google.nl` plus one independent HTTPS endpoint.
6. Record actual externally reachable state and failures without leaking account information.
7. Disconnect/reconnect, deliberately let the connection drop, disable/re-enable Wi-Fi once, and verify auto reconnect using the saved profile.
8. Reboot only with owner approval and stable recovery; verify profile survives and reconnects without re-entering the PSK.
9. Track max association, IP acquisition and UI update times from measured physical runs; set realistic bounded timeouts and a clear retry UI. Never keep a spinner spinning forever.
10. Handle networks with captive portals as `CONNECTED_NO_INTERNET` / `CAPTIVE_PORTAL` rather than `AUTH_FAILURE`.

Document result from the phone with redacted receipts (`nmcli`, `ip`, resolver status, TLS result). Tests should work on IPv4-only setups as well as dual-stack, and avoid requiring Google's site to respond to ICMP ping.

---

# PHASE 4 — Fix Settings Wi-Fi UX and backend contract permanently

Implement/repair a single shared typed Wi-Fi API and frontend state-machine (adapt to current architecture):

`OFFLINE → SCANNING → SELECTED → REQUESTING_SECRETS → ASSOCIATING → AUTHENTICATING → CONFIGURING_IP → CONNECTED → CHECKING_INTERNET → ONLINE`

Terminal/problem states: `AUTH_FAILED`, `AP_GONE`, `NO_DHCP`, `NO_DNS`, `NO_INTERNET`, `CAPTIVE_PORTAL`, `RADIO_BLOCKED`, `DRIVER_FAILED`, `CANCELLED`, `TIMED_OUT`.

The UI must:

- Debounce Connect and prevent concurrent activations; permit cancel/retry.
- Show which stage is occurring based on **real events**, not hard-coded sequencing.
- Never show a success checkmark until activation completes.
- Reconcile with NetworkManager after UI remount, bridge restart and screen wake.
- Keep keyboard input functional; hide keyboard on successful connect and allow dismissal independently on failure.
- Never log, echo unexpectedly or expose the Wi-Fi PSK through developer consoles or web pages.
- Save known-network preferences securely; provide a safe Forget network option and auto-connect toggle.
- Handle wrong-password correction without creating a pile of duplicate profiles.
- Work when Wi-Fi service becomes available after the UI starts; no `undefined`, stale `ap_path` or two-minute readiness race.
- Use proper notification/error messaging without overlapping top-bar icons.

Add regression tests for the old `/new` object-path error, stale APs, invalid credentials, duplicate profiles, lost state signals, restart, wrong SSID encoding, WPA2 and SAE conditional behavior, `nmcli works / UI fails`, and disconnect recovery.

---

# PHASE 5 — Make Nuxel Browser a REAL external web browser

Locate the current Nuxel Browser PWA/front-end and determine if it is merely a local page embedding remote sites via an iframe. If so, replace this approach with a **real WebKitGTK `WebKitWebView` native browser surface**, or the project's existing trusted GTK/WebKit browser host if already present. Modern HTTPS websites frequently prohibit being framed; changing user agents/CSP/X-Frame-Options or spoofing origin is NOT the solution.

Implement/repair a secure, touch-friendly browser with:

- A native top-level web view loading real `https://` URLs, including `https://www.google.nl`.
- URL/address bar with search behavior, Back, Forward, Reload/Stop, progress, page title, basic tab/window navigation where architecture supports it.
- Working TLS certificate verification; meaningful certificate error UI; no blanket insecure ignore-errors policy.
- DOM/JavaScript/CSS/resource loading, redirects, cookies, local storage and session persistence in the appropriate private application profile.
- Keyboard activation and dismissal through the **working existing** Nuxel OSK/native GTK input pathway (do not install duplicate keyboards).
- Zoom and touchscreen scrolling; app lifecycle, focus, rotation, URL bar and browser toolbar must coexist with Nuxel Home/Back/Recents.
- Cookie/session/site-data controls and Clear browsing data; support incognito/private browsing only if implemented correctly.
- Safe `http:` handling, `https:` default, common navigation, `mailto:` and unsupported schemes without unsafe shell command execution.
- `target=_blank`, downloads/file-picker integrations and permission prompts using the existing portal APIs where available; decline safely when unsupported.
- Safe WebKit content-process isolation/sandboxing, correct shared-memory and GPU fallback as applicable to the Samsung kernel. Do not blindly disable the browser sandbox to make the window appear.
- Recoverable WebKit content-process crash/reload, network failures, offline state, DNS/TLS errors and re-connect notifications.
- A proper Nuxel application registry entry with correct icon, menu visibility and launching path. One tap on Penguin Home must safely minimize/leave the browser without losing its running state.
- No synthetic screenshots, localhost-only “browser proof,” iframes that never navigate, or hardcoded successful network results.

### WebKitGTK/ARM64 preflight

Check installed WebKitGTK versions/APIs, GTK versions, `GDK_BACKEND`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR`, user session D-Bus, WebKit subprocesses, process sandbox availability, GPU/compositor constraints and memory footprint. Where target packages are missing, install compatible **phone-side AArch64** packages using the actual Fedora version; do not accidentally install onto the x86-64 Fedora laptop.

### Browser acceptance

On the actual S10+ over Wi-Fi:

- Open browser via Nuxel app drawer/icon.
- Navigate to `https://www.google.nl`; see actual live content.
- Enter a search using the on-screen keyboard and receive real results.
- Follow a result to a second real domain, Back, Forward, Reload and open a fresh URL.
- Close/return Home/reopen without becoming stuck; browser storage/cookies persist according to intended settings.
- Test after a network disconnect/reconnect, lock/unlock and reboot.

---

# PHASE 6 — Install and register real native browsers (only after primary browser works)

Discover available signed, ARM64-compatible Fedora packages and supported Flatpak runtimes on the **phone**. Install through documented verified repositories only, maintaining sandboxing and library integrity.

### Firefox — highest native-browser priority
- Check package availability and AArch64 build for current Fedora, install supported Firefox, verify binary and library dependencies, launch within Nuxel's actual Wayland/GTK session, and test real HTTPS, keyboard, scrolling, navigation and Home button.
- If graphical launch fails, report exact stderr/journal and missing portal/sandbox/driver dependency; no fake launcher status.

### Chromium — second priority
- Check Fedora `chromium` AArch64 or supported secure Flatpak path and installed browser sandbox requirements (especially kernel user namespaces).
- Install only a legitimate compatible build with sandbox enforced. Do not apply `--no-sandbox` as a permanent workaround.
- Verify actual browser functionality on the phone and register it with the application registry.

### Google Chrome — only if the official distribution supports this exact target
- Independently verify Google's current **Linux AArch64** package availability and hardware/runtime compatibility; never silently treat Chromium as Chrome or install an x86-64 RPM on ARM64.
- Install from official signed package sources if supported and safe; otherwise mark precise blocker and keep Firefox/Chromium functional.

### Ladybird — optional experiment, NOT a blocker for successful browsing
- Check official upstream Linux AArch64 support, Qt/toolchain versions, DRM/graphics requirements, memory footprint and packaging. Its developer-oriented state may make the build impractical on an S10+.
- Use native AArch64 building or correctly configured cross-compilation if feasible. Do not substitute a WebView wrapper and call it Ladybird.
- Set finite compute/time/build-resource constraints; if genuinely incompatible, document exact failing prerequisite and follow-up plan, without delaying Wi-Fi/Nuxel Browser acceptance.

### App visibility
Register actual executable paths, icons, `.desktop` and/or verified Flatpak IDs in the **current** Nuxel app registry. Avoid duplicate icons and stale entries. Installed-but-unlaunchable packages must be reported, not misrepresented as usable. Native apps must have proper Wayland environment and function via Back/Home/Recents or appropriate close/return routes.

---

# PHASE 7 — Reliable startup and state persistence

Address previous recurring Nuxel regressions:

- On device boot, service readiness is observable; UI can show an explicit short initializing state instead of permanently showing undefined.
- Wi-Fi and browser services have correctly ordered `systemd` dependencies without fragile sleeps or blind restart loops.
- NetworkManager connection profiles survive service restarts and cold boots.
- The browser works without rebuilding/cache-clearing manually after every deployment.
- Deployed browser code/bundles and registered app manifests actually match the latest source checkout. Record hashes of source versus installed files.
- Ensure only one authoritative bridge supplies Wi-Fi status, and only one browser launcher/host owns the active browser process. Remove obsolete stale script paths *only after* proving they're obsolete and preserving backups.
- Stabilize unit restarts without breaking the USB console or unexpectedly taking down Wayland/Phoc.

---

# PHASE 8 — Tests, live deployment, repeated real-world acceptance

### Automated tests (required)

Write unit/integration tests for NetworkManager profile generation and `a{sa{sv}}` D-Bus typing; selected AP lifetime and path, async state progression, timeout reason mapping, saved profiles, password corrections, authenticated versus IP-ready state, DNS and captive portal distinctions, UI lifecycle, native browser navigation and app registration.

Where mock D-Bus is used, label it `MOCK`. Also run actual NetworkManager D-Bus integration when a suitable test environment exists; don't mistake host NM tests for phone NM hardware results.

### Deployment (safe and reversible)

1. Verify stable phone console and a host-accessible rollback.
2. Build/test all patches in isolation; include precise file list and changeset.
3. Back up changed installed config and app files, record hashes.
4. Install required packages on **the phone**, not the host; confirm architecture and package signatures.
5. Deploy minimal bridge, browser and UI changes; verify installed hashes.
6. Restart only affected services with bounded timeouts and preserved recovery connectivity; get approval for disruptive steps.
7. Perform owner-guided hands-on verification. Do not force reboot until authorized.
8. Reboot when approved and repeat Wi-Fi/browser tests after cold boot.
9. Supply an exact idempotent rollback script/commands for every changed service and package where practical.

### Acceptance matrix — do not fake a PASS

| Gate | Physical proof |
|---|---|
| Scan | Real nearby networks appear |
| Choose network | Selecting AP uses a current NM object, not `/new` |
| Authenticate/associate | Actual state transitions to successful WPA link |
| IP | Valid address, gateway and route or valid IPv6 equivalent |
| DNS | Real public name resolution on phone |
| HTTPS | Real TLS-valid remote page response on phone |
| Saved profile | Reconnect after disconnect without retyping password |
| Reboot persistence | Automatic reconnect after owner-authorized reboot |
| Nuxel Browser | Actual `google.nl` renders, accepts typed search |
| Navigation | Back/Forward/Reload, links, Home, keyboard usable |
| Firefox | Real phone install, launch, page load or exact blocker |
| Chromium | Real phone install, launch, page load or exact blocker |
| Ladybird | Genuine upstream-compatible attempt or precise blocker |
| No regressions | Lock/unlock, keyboard, SnekByte, display and USB recovery still work |

Run a sequence of **at least three real connect/disconnect cycles and two independently verified browser launches**, plus a reboot-persistence check after authorization. Where the owner declines reboot, explicitly mark reboot tests `NOT_RUN` rather than `PASS`.

---

# PHASE 9 — Final deliverables and truthful report

Write under `docs/a62-wifi-browser/`:

- `00-baseline.md` — source/deployed provenance and diagnostics, sanitized.
- `01-root-cause.md` — precise first failure stage(s), actual NM reason codes and evidence.
- `02-networkmanager-and-bridge-fix.md` — implementation and D-Bus contract.
- `03-wifi-user-journey.md` — UI states, credential handling, known networks and reconnection behavior.
- `04-browser-architecture.md` — actual WebKitGTK host and app launch integration.
- `05-native-browser-compat.md` — installed package versions, Firefox/Chromium/Chrome/Ladybird compatibility.
- `06-test-results.md` — commands, unit and device observations, never exposing PSKs.
- `07-deployment-and-rollback.md` — hashes, service restarts, rollback steps.
- `08-acceptance.md` — separate `PASS`, `FAIL`, `BLOCKED`, `NOT_RUN`, and `MOCK_ONLY` verdicts for every gate.

In final response report root cause, changed files, exact commits, actual Wi-Fi state transitions, real phone IP/DNS/HTTPS tests, browser proof, installed app status, reboot persistence and remaining blockers.

## Definition of DONE

**DONE means the penguin is online:** Nuxel can actually authenticate/associate with the owner's Wi-Fi, get usable internet, remember the connection, and open a real external webpage in its own browser after reboot. Firefox/Chromium are added when supported and independently tested; Ladybird is explored without compromising the core milestones. No more endless “Authenticating and associating.”

**GO CONNECT THE PENGUIN TO THE OUTSIDE WORLD. 🐧🌐🔥**
