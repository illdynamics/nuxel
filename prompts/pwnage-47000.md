# PWNAGE-47000 — NUXEL GUI TRI-LINK / REMOTE DESKTOP KICKSTARTER

**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel, custom Fedora-based ARM64 Linux  
**Primary UI:** Nuxel Home Applications drawer + three dedicated PWAs  
**Existing management path:** `services/nuxel-bridge` + `system.tri-link` status API  
**Remote viewer:** Jump Desktop for macOS on the user's MacBook (preferred); Windows App / another RDP client only as fallback  
**Mission:** implement three truthful remote-access apps and prove real connections from the MacBook.

## MISSION

Repair and extend Nuxel's graphical remote-access experience without breaking the existing Serial/WLAN/USB SSH Tri-Link. Add three distinct Applications entries:

1. **XRDP Remote Desktop** — RDP server, Wi-Fi preferred by default, USB network optional only when safely supported.
2. **VNC Screen Sharing** — VNC server that should share the actual running Nuxel Wayland/Phoc session, Wi-Fi preferred by default, USB network optional only when safely supported.
3. **scrcpy (Android)** — official scrcpy integration for real Android ADB targets, USB preferred by default and TCP/IP optional. Do not misrepresent scrcpy as a native Linux screen-sharing protocol.

Create proper app UIs, Bridge APIs, service/config/package integration, registry entries, security controls, live status, start/stop, address/port display, optional USB selection, and real host-side tests. Use the MacBook's existing **Jump Desktop** viewer to connect to the phone and verify XRDP and VNC live. Do not claim a connection based only on an open TCP port or a successful local service start: a remote display must actually appear and accept input.

**Important:** the existing Tri-Link is a host-side serial/SSH management and recovery system. It is not a graphical remote-desktop service. Preserve it. Add a separate graphical remote-access group and a shared status/control layer rather than pretending the old SSH status represents RDP/VNC/scrcpy.

## REQUIRED TRANSPORT DEFAULTS

| App | Default preference | Optional alternative | Meaning |
|---|---|---|---|
| XRDP | Wi-Fi | USB network, only if verified | RDP server on Nuxel, tested from Jump Desktop Mac |
| VNC | Wi-Fi | USB network, only if verified | VNC server attached to the real Nuxel Wayland session, tested from Jump Desktop Mac |
| scrcpy | USB | Wi-Fi / TCP-IP | scrcpy operates on Android ADB targets only; it does not mirror native Nuxel Linux |

“Default” means the preferred transport selected in the app. It does **not** mean remote access starts automatically at boot. All remote-access services remain OFF until the owner explicitly enables them.

## CRITICAL REPOSITORY FINDINGS — DO NOT IGNORE

The supplied repository snapshot already contains a mature Tri-Link console implementation, but it does not contain XRDP, VNC or scrcpy server implementations:

- `tools/beta/live/nuxel_tri_link.py` is a host-side transport manager for `serial`, `wlan`, `usb` and `auto` SSH/recovery transport.
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh` and `tools/beta/live/nuxel-live-ssh.py` are the host-side SSH/serial entry points.
- `services/nuxel-bridge/src/tri_link_status.py` is explicitly **read-only** phone-side transport truth. It does not start or stop services.
- `services/nuxel-bridge/src/api.py` exposes `/api/v1/system/tri-link` and `system.tri-link`.
- `pwa/nuxel-apps/console/console.js` is the shared UI used by three existing status panels.
- Current registry entries already include `org.nuxel.LiveConsole`, `org.nuxel.USBSSHConsole` and `org.nuxel.WiFiSSHConsole`. Keep all three.
- The current UI report is `docs/beta-finalization/live/NUXEL-28000-TRI-LINK-UI-REPORT.md`; the physical transport report is `docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md`.

**USB warning:** the existing USB-network SSH experiment on the live Samsung-derived 4.14.253 kernel caused a physical kernel panic in NCM teardown (`ncm_free_inst -> misc_deregister`), followed by watchdog reboot. The recorded current gadget was CDC-ACM serial only. ECM/ECM_SUBSET were not compiled; NCM is known unsafe on this kernel; RNDIS was compiled but was not physically proven. The existing status correctly reports USB SSH as `BLOCKED_KERNEL_PANIC`. Do not retry NCM, do not delete/recreate configfs functions, and do not rebind the UDC as a shortcut. Optional RDP/VNC-over-USB must stay blocked until an independently safe USB network route and Mac host compatibility are proven.

**Remote-access policy warning:** `configs/nuxel/security/remote-access.json` currently has `enabled:false` and says remote access is OFF by default. Its security model forbids wildcard/public exposure. Keep remote access opt-in, LAN-scoped, authenticated and visibly indicated. The existing SSH key, pinned host key and `AllowUsers` CIDR policy should be reused where appropriate, but do not assume its current IP/CIDRs are permanent.

**Wayland / VNC finding:** the S10+ uses Phoc/wlroots with a headless Wayland output and `nuxel-wl-fb` as the single `/dev/fb0` presentation owner. `wayvnc` is a strong candidate because it attaches to a running wlroots compositor, captures the Wayland session and injects virtual input. Verify that the actual Phoc build exposes the required screencopy and virtual input protocols; do not assume compatibility merely from the compositor name.

**XRDP finding:** `xrdp` plus `xorgxrdp` is an Xorg-based RDP backend, not a native Wayland screen-shadowing service. It normally creates a separate Xorg/Xvnc remote login session. Implement it as a clearly labelled separate remote session unless a real, supported shadow backend for the active Phoc session is independently proven. Never claim that it mirrors the phone's physical screen if it does not.

**scrcpy finding:** official scrcpy is an Android screen-mirroring/control system. It requires an Android target (Android API 21+ and USB debugging for normal USB/TCP-IP use). It has a host client and an Android-side server launched through ADB. Native Fedora/Wayland Nuxel is not an Android target and does not expose Android's ADB/MediaProjection/SurfaceControl APIs. The scrcpy app must report this distinction honestly. Do not invent a “scrcpy server” for native Nuxel or install Waydroid automatically.

## IMPLEMENTATION PLAN

### 1. Add three separate GUI apps

Create dedicated apps and valid manifests/assets under sensible paths such as:

- `pwa/nuxel-apps/remote-xrdp/`
- `pwa/nuxel-apps/remote-vnc/`
- `pwa/nuxel-apps/remote-scrcpy/`

Use canonical IDs after checking for collisions; recommended IDs:

- `org.nuxel.RemoteDesktopXRDP`
- `org.nuxel.RemoteDesktopVNC`
- `org.nuxel.ScrcpyMirror`

Register all three in `pwa/nuxel-common/app-registry.json`, update the registry revision, generate/update any native shell registry consumer, add each app to the normal Home Applications drawer and update PWA service-worker/cache metadata. Preserve the three existing console apps and their registry IDs.

Each app must provide:

- Real provider status (`OFF`, `STARTING`, `READY`, `WAITING_FOR_CLIENT`, `CONNECTED`, `STOPPING`, `BLOCKED`, `UNSUPPORTED`, `ERROR`).
- Start/Stop controls with explicit confirmation and real Bridge acknowledgement.
- Preferred transport selector with the requested default.
- Optional USB selector only when a real safe USB network capability is available.
- Current phone address/interface/port and the exact client connection details.
- Authentication/encryption state and certificate/host-key fingerprint where applicable.
- Last connection, active client/session count, CPU/memory/frame or traffic statistics where available.
- Recheck/diagnostics, useful error details and Copy connection details.
- A privacy banner while any remote server is active.

Use accessible touch-sized controls, a clear OFF-by-default state, no fake green indicators and no high-frequency polling while the app is hidden.

### 2. Create a separate remote-desktop Bridge/provider

Do not make `tri_link_status.py` writable. Keep `system.tri-link` as the existing serial/SSH status contract. Add a distinct `system.remote-desktop` status/control namespace (or equivalent typed Bridge API) with narrowly scoped operations:

- `status`: read-only per-service and per-transport facts.
- `start`: start one named service using a fixed, validated profile.
- `stop`: stop one named service and close its listener/firewall allowance.
- `set-transport`: select Wi-Fi or a verified USB network interface.
- `diagnose`: bounded, read-only probes.
- `get-connection-info`: produce host/port/tunnel/Jump import details without exposing passwords or private keys.

The Bridge must validate app/service IDs, allowed transports, config paths, port ranges and caller permissions. Never accept arbitrary command strings, service names, bind addresses or executable paths from JavaScript. Use fixed privileged helpers/systemd units and argument arrays. Return structured status and real failures.

Recommended status facts include:

- selected/preferred transport;
- active transport;
- bind interface and actual bind address;
- local Wi-Fi IPv4 address discovered live (never a hardcoded historical address);
- USB capability verdict and exact blocker;
- configured and listening port;
- service state and PID/process health;
- session count / client state where supported;
- authentication mode and TLS status;
- last error, start time and expiry/idle-stop deadline.

Keep a single owner for each service lifecycle. Avoid a duplicate status poller per UI; share Bridge cached facts with bounded expiry.

### 3. XRDP Remote Desktop — Wi-Fi default, USB optional

Investigate the actual Fedora release, configured repositories and ARM64 package availability for `xrdp`, `xorgxrdp`, Xorg and any Xvnc/TigerVNC backend required. Fedora package existence on x86_64 is not proof of aarch64 availability. Verify dependency closure on the clean S10+ image builder and on the live device before integration.

Implement an RDP server with the safest supported backend:

- Prefer `xrdp` + `xorgxrdp` when the ARM64 packages and Xorg session work.
- If not, evaluate `xrdp` + a compatible TigerVNC `Xvnc` backend as a separate virtual X11 remote session.
- Do not start a second Phoc compositor or a second `/dev/fb0` writer.
- Do not imply this is a mirror of the physical Nuxel screen. Label it **Separate remote desktop session** unless physical-session shadowing is proven.
- Build a lightweight Nuxel remote X session that can actually display a usable Nuxel launcher/web UI or a documented lightweight desktop. Do not ship an empty X screen or a bare terminal and call it a completed desktop.
- Keep remote X session isolated from the active physical Wayland session's runtime socket and D-Bus session. Do not reuse `/run/user/<uid>` session state unsafely.
- Run as a normal non-root user. No remote root login or sudo by default. Use a dedicated restricted remote account or a properly isolated `nuxel` session after a security review.
- Configure PAM/credentials safely, lockout/backoff, session limits and clean logout.
- Configure TLS certificate/key and strict protocol policy. Do not claim NLA if the chosen xrdp version/backend does not support it. Prefer an SSH tunnel for Jump testing if direct RDP security/client compatibility is uncertain.
- Default transport preference is Wi-Fi. Provide USB only after a safe USB network is physically verified.
- Default service state is OFF. Do not auto-enable RDP at boot.

Use the standard RDP port 3389 unless port conflict or security architecture requires a documented configurable port. Bind to loopback for SSH-tunnel use or to the exact active trusted Wi-Fi interface/address for direct-LAN use. Do not bind `0.0.0.0` or `::` unrestricted.

### 4. VNC Screen Sharing — Wi-Fi default, USB optional

Investigate `wayvnc` first. Fedora provides a `wayvnc` package for wlroots Wayland compositors; the official upstream says it attaches to the running Wayland session, exposes one display over RFB, and creates virtual input devices. On the S10+ verify the current Phoc runtime actually advertises the protocols it needs, including the appropriate screencopy and virtual pointer/keyboard protocols.

If supported:

- Build/package a compatible ARM64 `wayvnc` and dependencies in the S10+ rootfs.
- Run it as the logged-in Nuxel session user with the correct `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and seat permissions.
- Capture the actual Phoc/Nuxel screen; remote viewer must see the same visible lockscreen/Home/Apps screen the physical user sees.
- Remote mouse/keyboard input must travel through supported virtual-input protocols and obey the active Nuxel lockscreen/security state.
- Never use a second framebuffer writer or direct `/dev/fb0` access.
- Respect lock/unlock and screen-off policy. A locked phone must not leak protected app content through VNC; remote input must not bypass authentication.
- Default port 5900 unless configured otherwise; do not expose without explicit user action.
- Use secure TLS/VeNCrypt or a verified SSH tunnel. Do not enable legacy DES-only VNC authentication or 8-character-truncated password handling on a network interface. Verify Jump Desktop's VNC security compatibility in a live test; if necessary keep wayvnc bound to `127.0.0.1` and use a pinned-host-key SSH local forward from the Mac.
- Default transport preference is Wi-Fi. USB optional only when a real verified USB network path exists.

If the Phoc build lacks required protocols, do not claim wayvnc works. Investigate whether the current Phoc/wlroots build can safely expose them in userspace without breaking the phone UI; otherwise report the exact protocol blocker and use an alternative VNC server only if it can share the current Wayland session securely. TigerVNC `Xvnc` creates a virtual X desktop and is not an automatic substitute for sharing the active Phoc screen.

### 5. scrcpy — Android-only integration, USB default, Wi-Fi optional

Use official upstream scrcpy only. It mirrors and controls Android devices over USB or TCP/IP; it requires a real Android endpoint and ADB debugging. It is not a generic VNC/RDP/Wayland server.

Implement a truthful Scrcpy app that:

- Detects whether an Android ADB target is present (USB preferred by default).
- Shows USB Android target, device ID/model/API level where available, ADB authorization state and scrcpy version compatibility.
- Starts the official scrcpy host client/server pair only for a detected compatible Android target.
- Provides optional Wi-Fi/TCP-IP pairing/connect for a real Android target, with explicit owner authorization and a time-bounded ADB wireless-debugging session.
- Avoids keeping ADB TCP debugging open after use; stop/revert it on disconnect where supported.
- Does not store ADB private keys/secrets in PWA localStorage or logs.
- Does not install Waydroid automatically.
- If no Android ADB target exists because this handset is running native Nuxel Linux, show `NOT_APPLICABLE_NATIVE_NUXEL` with a clear explanation: “scrcpy supports Android targets; use VNC Screen Sharing to mirror and control native Nuxel.”
- If Waydroid already exists, do not assume it is usable; check its runtime, Android image, binder requirements and ADB endpoint. Only offer it if already installed and explicitly enabled by the owner. Do not install or modify Waydroid as part of this mission.

Do not invent a fake scrcpy server, do not reimplement the internal scrcpy protocol as a proprietary Nuxel protocol, and do not advertise native Nuxel as an Android device. If a future native high-speed mirror is desired, it must be a separately named **Nuxel Mirror** product with its own documented protocol and Mac client, not scrcpy.

### 6. Transport design and USB safety

#### Wi-Fi

- Wi-Fi is the default preferred transport for XRDP and VNC.
- Detect the actual current `wlan0` IPv4 address dynamically using the Bridge's verified network provider. Do not hardcode `10.20.30.16`; it is historical evidence only.
- Limit access to the active trusted LAN subnet and/or an authenticated SSH tunnel. Do not expose ports to cellular, public Internet or arbitrary interfaces.
- Do not add router port-forwarding, UPnP, public DNS or cloud relay.
- Display a persistent `REMOTE DESKTOP ACTIVE` privacy indicator while a server is listening or a remote client is connected.

#### USB for XRDP/VNC

- The USB alternate is a network route, not the CDC-ACM serial recovery console.
- The known NCM teardown panic on kernel 4.14.253 is a hard stop. Do not retry NCM or alter its safety guard.
- ECM/ECM_SUBSET were not compiled in the recorded kernel. RNDIS was compiled but not physically proven and macOS compatibility must be separately verified.
- Begin with read-only checks of current UDC, configfs, function descriptors, host driver support and kernel config. Do not mutate configfs or rebind UDC during a read-only audit.
- Only implement an alternate USB network function if it has a safe creation/teardown path, a proven rollback, preserves CDC-ACM, does not trigger the recorded panic and works from the MacBook's actual macOS version/USB host stack.
- Never repurpose or disable the only serial recovery interface.
- Until the above proof exists, show USB as `BLOCKED_KERNEL` / `NOT_SUPPORTED_ON_DEVICE` and keep Wi-Fi working. No false “USB ready” state.

#### USB for scrcpy

USB scrcpy is ADB over the Android device's USB-debugging interface. It is not the Nuxel USB SSH/NCM gadget. Enable it only for a real Android target and explicit ADB authorization.

### 7. MacBook + Jump Desktop live acceptance

The user specifically wants the agent to use the existing MacBook **Jump Desktop** application as the client, preferably for both RDP and VNC.

Before testing, identify the actual host environment and Mac:

- Verify whether the agent is running on the MacBook or another workstation. The repository's historical Tri-Link report describes Fedora 43 `dextronux` as a previous host; do not assume it is the current Mac.
- On the Mac, read `sw_vers`, `uname -m`, current network interfaces/routes and Jump Desktop app presence/version.
- Check for `/Applications/Jump Desktop.app` or the actual installed app path and verify its code signature/version. Check whether the app is running.
- The **Jump Desktop client/viewer** belongs on the Mac. Do not install Jump Desktop Connect onto Nuxel; Connect is a host agent for supported Jump/Fluid access and is not required for a manually configured RDP/VNC server connection.
- Do not download/install Jump Desktop, grant macOS Accessibility/Screen Recording permissions or sign into a Jump account without the owner's explicit authorization. If it is not installed or GUI control is unavailable, prepare exact manual steps and connection files without pretending a test was run.
- If GUI/computer-use automation is available and authorized, open Jump Desktop and configure connections through the real UI. Do not use screenshots or logs from a different machine as MacBook evidence.

#### RDP test

1. Start the Nuxel XRDP service over Wi-Fi.
2. Obtain live address/port and secure connection details from the Bridge.
3. Prefer an SSH local forward from the Mac using the existing pinned host key and authorized key when available, for example a local port mapped to Nuxel `127.0.0.1:3389`. Do not invent or bypass host keys/credentials.
4. In Jump Desktop for Mac, add/connect to the RDP server using the current Jump UI. If Jump's Mac client requires an imported `.rdp` connection file, generate a private non-secret `.rdp` file, import it and connect. Do not save credentials in the file.
5. Confirm a live remote X session appears, sign in as the restricted remote user, open the Nuxel remote desktop/launcher and verify keyboard and mouse input.
6. Verify that this is a separate X session and that the physical Phoc/Nuxel Home session remains alive and unchanged.
7. Disconnect, reconnect and stop XRDP. Verify session cleanup and listener closure.

If Jump Desktop Mac does not offer a supported direct RDP path in the installed version, use Microsoft's Windows App for macOS or another standard RDP client only as a fallback and document why. Still test Jump first and do not claim Jump RDP success from a TCP probe.

#### VNC test

1. Start VNC Screen Sharing over Wi-Fi.
2. Confirm the VNC server attaches to the actual Phoc session.
3. Use Jump Desktop for Mac's manual VNC connection path with the phone's current IP/port, or a secure SSH local forward to loopback if that is the only secure interoperability path.
4. Confirm the live physical phone lockscreen/Home/Apps screen is visible.
5. Use Mac mouse/keyboard input to interact with Nuxel. Open Notes or a disposable test view, type a unique harmless marker, and verify the action appears on the phone. Do not edit/delete real user content.
6. Rotate the phone (if rotation works), lock/unlock using the normal policy and verify remote view follows the same visible Nuxel state without bypassing lock.
7. Disconnect, reconnect, stop VNC and verify the service/listener and virtual input devices are cleaned up.

Jump Desktop's official support says it can connect to Linux remote-desktop services using manual VNC configuration. Verify the actual Mac client version/security-type compatibility instead of assuming all VNC authentication methods work.

#### USB test

Only after the USB network path is independently proven safe on the target kernel and macOS host. Then repeat the RDP and/or VNC client test through the actual USB interface, verify the interface/route and ensure the CDC-ACM serial recovery interface remains accessible. If unavailable, record a real blocked result and do not experiment with NCM teardown.

#### scrcpy test

Use official scrcpy from a real Android ADB target only. Test USB first, then optional Wi-Fi pairing if the Android target supports it. If the Nuxel phone has no Android endpoint, physically verify the UI reports `NOT_APPLICABLE_NATIVE_NUXEL` and clearly directs the owner to VNC for native screen control. That is an honest capability result, not a scrcpy success.

### 8. Security and policy

- Remote access remains off by default and never starts silently at boot.
- Starting a service requires an explicit user action and a visible explanation of the listening interface, remote-control power and current transport.
- Only the owner-approved local account may connect. No root desktop login, no shared default password and no account-wide default credential.
- Use strong, separate, randomly generated service credentials or a secure SSH tunnel. Never reuse the Nuxel lock PIN, Microsoft password, Wi-Fi password or SSH private key as the VNC/RDP password.
- Store password hashes/credentials only in the provider's secure storage or service-owned files with strict permissions. Never store passwords in browser localStorage, manifest, catalog, command arguments, generated QR codes or logs.
- Use TLS for RDP. Use TLS/VeNCrypt or a pinned-host-key SSH tunnel for VNC. Never enable legacy DES-only VNC auth on a network interface.
- Bind only to the explicitly selected Wi-Fi IP or localhost for SSH-tunnel mode. Never wildcard-bind `0.0.0.0`/`::` without explicit policy approval and a proven firewall interface restriction.
- Do not open cellular/rmnet interfaces, public routes, UPnP, router forwarding or cloud relay.
- Add a separate policy section in `configs/nuxel/security/remote-access.json` for GUI remote desktop. Preserve existing SSH/serial policy and `enabled:false` default. A user action may enable one selected service temporarily; stopping it must close its listener and firewall allowance.
- Add rate limiting, authentication failure lockout/backoff, bounded concurrent sessions and idle timeout.
- When device is locked, VNC may show only the lockscreen. It must not bypass local lock authentication or expose protected app contents. RDP's separate session must still require its own authenticated login.
- Display a persistent remote-access indicator in the phone UI and a kill switch that stops all GUI remote services.
- Do not expose remote desktop inside the public Internet or outside the owner LAN/VPN as part of this mission.

### 9. Rootfs, systemd and packaging

- Verify ARM64/aarch64 availability for xrdp, xorgxrdp, Xorg, TigerVNC/Xvnc, wayvnc and all runtime dependencies from the currently configured Fedora repositories.
- Verify actual package architecture and kernel/userspace compatibility; do not assume a Fedora package listing for x86 is present for ARM64.
- Add selected packages to `images/s10plus` manifests/build script.
- Add narrow systemd user/system units and polkit/policy authorization for service start/stop.
- Do not enable remote services at boot; units should be activation-driven and stop cleanly.
- Preserve Wayland user session environment for wayvnc. Do not run the active-session VNC server as root if avoidable.
- Add XRDP session startup/cleanup and account policy.
- Add configs, certificates/keys and state directories with strict ownership/modes.
- Ensure package installation does not add a display manager or replace Phoc/Wayland as the physical phone session.
- Add clean-rootfs assertions that each supported server binary, unit and config is present at its expected path.

### 10. Required tests and delivery

Run focused unit/API/UI tests plus build/install checks. Add tests for:

- Canonical app registry IDs and the three existing console entries preserved.
- Remote-desktop status API and all service state transitions.
- Start/stop/idempotency, service failure, stale process, timeout and interface loss.
- Wi-Fi address discovery; no hardcoded IP.
- USB unavailable/known-bad NCM refusal; no configfs mutation on the blocker path.
- Binding/listener checks and firewall/interface restrictions.
- XRDP package/backend/session creation, authentication failure, logout and no root session.
- wayvnc protocol availability, current Wayland capture, virtual input and lockscreen gating.
- TLS/SSH tunnel authentication and no DES-only VNC fallback.
- scrcpy Android target detection, USB authorization, Wi-Fi pairing, target absent and native Nuxel unsupported status.
- PWA service-worker/cache versions and no mock/success fallback.

Create `docs/beta-finalization/live/PWNAGE-47000-TODO.md`, a numbered evidence directory, deployment/rollback manifest and final report. Record exact command outputs, package versions/architectures, live Mac Jump Desktop version, client screenshots, connect/disconnect tests, input tests, performance measurements and unsupported blockers.

## EXECUTION ORDER

1. Audit the repo and live phone, especially NUXEL-26000/28000 reports, Tri-Link code, current remote-access policy, Phoc protocols, kernel USB facts and build package paths.
2. Establish the actual MacBook host, Jump Desktop installation/version and authorized way to control its UI.
3. Design the independent GUI remote-access API and the three PWA apps; preserve existing Serial/Wi-Fi/USB SSH entries.
4. Implement VNC against the active Phoc/Wayland session first if wayvnc protocols are supported, then test it live with Jump Desktop on Mac.
5. Implement XRDP as a separate remote X session, verify ARM64 packages/backend, add a real usable Nuxel remote desktop shell and test it live with Jump Desktop on Mac.
6. Implement the scrcpy Android-target app with explicit USB-first/Wi-Fi-second logic and honest native-Nuxel incompatibility. Do not install Waydroid.
7. Add optional USB networking only if a safe non-NCM implementation is independently proven. Otherwise preserve `BLOCKED_KERNEL_PANIC` and keep Wi-Fi operational.
8. Complete app registry, cache, package, systemd, Bridge, security indicators and test integration.
9. Run full regression and ARM64 rootfs/package checks. Deploy safely through the existing configured Tri-Link WLAN SSH route where available; never interrupt serial recovery.
10. Connect from Jump Desktop on the actual MacBook. Record visual and input proof for RDP/VNC; report scrcpy target availability separately.

## DEFINITION OF DONE

- Three new separate Applications entries exist and open their real screens.
- Existing Serial Live Console, Wi-Fi SSH Console and USB SSH Console remain intact.
- XRDP works over Wi-Fi from Jump Desktop Mac, creates a usable remote X session, and cleans up safely.
- VNC works over Wi-Fi from Jump Desktop Mac, mirrors the actual physical Nuxel Wayland session and supports remote input without breaking local touch/lock policy.
- USB alternatives are enabled only if physically proven safe; otherwise the apps state the exact blocker and keep Wi-Fi working.
- scrcpy correctly works for real Android ADB targets over USB/Wi-Fi, or reports that native Nuxel is not an Android target and recommends VNC for native Nuxel. It never falsely claims to mirror Nuxel through scrcpy.
- Remote access is OFF by default, opt-in, authenticated, encrypted and restricted to the owner-approved local network/tunnel.
- No NCM panic retry, no second framebuffer owner, no root remote desktop, no credentials in PWA storage/logs and no public Internet exposure.
- The MacBook Jump Desktop test is backed by actual remote screen display and input evidence, not just port probes.

**Do the implementation. Preserve the existing Tri-Link recovery path. Make the graphical remote access real, secure and testable from the owner's MacBook.**
