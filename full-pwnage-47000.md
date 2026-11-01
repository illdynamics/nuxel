# FULL-PWNAGE-47000
# NUXEL GUI TRI-LINK — XRDP, WAYLAND VNC, SCRCPY/ANDROID BRIDGE, SECURE WI-FI/USB TRANSPORTS AND LIVE JUMP DESKTOP ACCEPTANCE FROM THE MACBOOK

## Complete source audit, app implementation, Bridge/service integration, secure transport design, active ARM64 image packaging, Mac client automation and physical acceptance mission

**Mission ID:** PWNAGE-47000  
**Target device:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820  
**OS:** Nuxel — custom Fedora-based ARM64 Linux mobile OS  
**Compositor:** Phoc / Wayland, headless output where applicable  
**Physical display pipeline:** Wayland screencopy → `nuxel-wl-fb` → single `/dev/fb0` owner → Samsung DECON/panel  
**Existing management transport:** Nuxel Tri-Link Serial / WLAN SSH / USB SSH (USB SSH is documented blocked on the current kernel)  
**New GUI access apps:** XRDP, VNC, scrcpy (Android-only)  
**Preferred client/host for live test:** user's MacBook running Jump Desktop for macOS  
**Fallback client:** Microsoft's Windows App for macOS or another verified RDP/VNC client only when Jump Desktop cannot perform a specific protocol path  
**Mission type:** full implementation, package/build integration, remote access security hardening, live Mac client testing and measured physical acceptance.

---

# 0. EXECUTIVE MISSION — WHAT MUST BE DELIVERED

The existing Nuxel Tri-Link system is a transport/recovery/SSH management feature. It currently provides three distinct Applications entries:

- Serial Live Console (USB CDC-ACM recovery console);
- Wi-Fi SSH Console (key-only SSH over the phone's current WLAN address);
- USB SSH Console (USB network SSH, presently blocked by a documented kernel panic).

These are not remote graphical desktop servers. The objective of PWNAGE-47000 is to preserve them and add three new graphical-access applications:

1. **XRDP Remote Desktop** — RDP server on Nuxel, with Wi-Fi as the preferred/default transport and USB networking as an optional route only when safely proven. This should create a real remote login/session. Unless a true physical-session shadow backend is proven, it is a separate X11 session and must say so.
2. **VNC Screen Sharing** — VNC server using the actual running Nuxel/Phoc Wayland session. Wi-Fi preferred/default; USB network optional only if safe and tested. This should let the Mac see/control the real phone screen, subject to the Nuxel lock/security policy.
3. **scrcpy (Android)** — official scrcpy integration for Android ADB targets, USB preferred/default and Wi-Fi/TCP-IP optional. This is not a native Linux/Wayland screen-sharing protocol. Native Nuxel itself is not an Android device, so the app must show this truthfully when no Android runtime or external Android target exists.

Implement three proper apps, add them to the real Applications registry, connect them to a secure backend through typed Bridge APIs, add systemd/package/rootfs integration, and test from the user's actual MacBook using its Jump Desktop application. Do not report success from a listening port alone: the Mac must display the remote screen/session, accept keyboard/mouse input and disconnect/reconnect cleanly.

The required defaults are transport **preferences**, not automatic service activation:

| App | Preferred transport | Optional transport | Server/target semantics |
|---|---|---|---|
| XRDP | Wi-Fi | USB network only if proven | RDP server; separate X11 remote login session by default |
| VNC | Wi-Fi | USB network only if proven | RFB/VNC server mirroring the current Phoc session |
| scrcpy | USB | Wi-Fi/TCP-IP | Official scrcpy client/server flow for real Android ADB target(s) only |

All servers remain OFF at boot and OFF unless the owner explicitly starts them. Starting a service must show what interface it binds to and that remote users may control the phone/session.

---

# 1. REPOSITORY SOURCE AUDIT — EXISTING TRI-LINK IS NOT GUI REMOTE DESKTOP

The supplied archive `nuxel-main (10)(1).zip` / `(10)(1)` was inspected. Verify the active worktree and live device still match before modifying anything. The archive establishes the following architecture and blockers.

## 1.1 Existing Tri-Link implementation

Important sources:

```text
NUXEL-26000-TRI-LINK-CONSOLE-REVOLUTION-UBERPROMPT.md
NUXEL-28000-TRI-LINK-UBERFIXER-UBERPROMPT.md
TRI-LINK-QUICKSTART.md

docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md
docs/beta-finalization/live/NUXEL-28000-TRI-LINK-UI-REPORT.md

tools/beta/live/nuxel_tri_link.py
tools/beta/live/nuxel-live-ssh.py
scripts/s10plus-debug-pack/nuxel-live-ssh.sh
scripts/s10plus-debug-pack/nuxel-live.sh

tools/beta/live/nuxel-usb-net.py
scripts/s10plus-debug-pack/nuxel-usb-net-host.sh

services/nuxel-bridge/src/tri_link_status.py
services/nuxel-bridge/src/api.py
services/nuxel-bridge/src/bridge.py

pwa/nuxel-common/app-registry.json
pwa/nuxel-home/js/apps.js
pwa/nuxel-apps/console/
pwa/nuxel-apps/console-usb/
pwa/nuxel-apps/console-wifi/

tests/a80/test_tri_link_api.py
tests/a80/test_tri_link_console.py
tests/a80/test_tri_link_status.py
tools/beta/live/tests/test_tri_link.py
```

`tools/beta/live/nuxel_tri_link.py` and `nuxel-live-ssh.py` are host-side. They provide explicit serial/WLAN/USB/auto SSH selection, pinned host keys, key-only SSH, transfer/deploy locks, SHA-256 verified put/get and structured error codes. The serial path delegates to the existing serial recovery console. Keep this transport manager independent of the GUI server lifecycles.

`services/nuxel-bridge/src/tri_link_status.py` is deliberately read-only. It checks phone-side serial gadget, Wi-Fi address/sshd policy and USB network capability. It never enables gadgets, starts/stops sshd, opens serial, changes routes or reads private keys. Keep that read-only boundary; do not stuff privileged start/stop controls into it.

`services/nuxel-bridge/src/api.py` exposes the existing `/api/v1/system/tri-link` route and the `system.tri-link` Bridge RPC. `system_indicators.py` also imports cached Tri-Link facts. Do not make these SSH status results pretend that XRDP/VNC/scrcpy is active.

## 1.2 Existing Applications registry entries

The current canonical registry `pwa/nuxel-common/app-registry.json` already contains:

| ID | Name | Entry path | Purpose |
|---|---|---|---|
| `org.nuxel.LiveConsole` | Serial Live Console | `/pwa/nuxel-apps/console/index.html` | CDC-ACM serial recovery |
| `org.nuxel.USBSSHConsole` | USB SSH Console | `/pwa/nuxel-apps/console-usb/index.html` | USB network SSH; currently blocked |
| `org.nuxel.WiFiSSHConsole` | Wi-Fi SSH Console | `/pwa/nuxel-apps/console-wifi/index.html` | key-only WLAN SSH |

`pwa/nuxel-apps/console/console.js` is shared by the three existing documents. It displays phone-side status, target, auth, diagnostics and a copyable host command. It does **not** run the authenticated remote shell in the phone browser; that is a host-side developer tool. The UI report says the three entries are registered once, and the current registry revision is 6.

Keep those three entries and their app IDs unchanged. Add three graphical remote-access entries as additional applications. Do not rename the original apps to XRDP/VNC/scrcpy.

## 1.3 Existing USB-network blocker — hard safety constraint

`docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md` documents a physical USB NCM experiment on the Samsung-derived Linux 4.14.253 kernel:

- Before experiment the only configfs function was `acm.usb0`, UDC `10c00000.dwc3`.
- `CONFIG_USB_CONFIGFS=y`, `CONFIG_USB_F_NCM=y` and `CONFIG_USB_CONFIGFS_NCM=y` were present; ECM and ECM_SUBSET were not set. RNDIS was compiled, but no physical RNDIS path was verified.
- Experimental NCM setup/rebind led to host `error -71`; cleanup of the NCM configfs function then caused a kernel panic whose trace included `ncm_free_inst -> misc_deregister -> __list_del_entry_valid`.
- The watchdog rebooted the phone. pstore evidence is kept under `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`.
- The updated helper refuses 4.14.253 with `BLOCKED_KERNEL_PANIC`; do not pass an unsafe override or retry NCM.
- After recovery the only gadget function was again `acm.usb0`; serial recovery and WLAN SSH were verified. USB SSH was not proven.

This means USB RDP/VNC cannot be promised right now. Their optional USB path needs a genuine USB IP interface (or another explicitly proven TCP transport) and compatible Mac host driver. Do not repurpose CDC-ACM serial or damage the only recovery path to make a USB checkbox appear green.

## 1.4 Existing remote access policy

`configs/nuxel/security/remote-access.json` has `enabled:false` and states remote access is off by default. It describes an owner-controlled console route and forbids wildcard binds. It records serial recovery as always available, historical WLAN SSH interface/host key policy, and USB SSH as blocked by the NCM panic.

The current WLAN SSH record from 2026-10-27 contains a historical phone address `10.20.30.16`, host `10.20.30.22`, `/24` network and host key fingerprint. Those are evidence, **not permanent addresses**. Discover the live network values dynamically. Existing SSH uses public-key authentication, a pinned Ed25519 host key and CIDR restrictions. Reuse this security approach where possible; never assume the repo private key is present on the Mac or copy it to the phone.

Create a distinct GUI remote-access policy section in `remote-access.json` or its schema, preserving the default OFF state and existing SSH/serial rules. Do not silently broaden the legacy SSH AllowUsers rule.

## 1.5 Existing physical display/compositor architecture

Nuxel's physical S10+ stack uses Phoc/Wayland and the `nuxel-wl-fb` screenshot/presentation bridge. The current image builder compiles `tools/s10plus/a34/nuxel-wl-fb.c`; other newer source directories are not active unless the build script is changed. `nuxel-wl-fb` is the single owner of `/dev/fb0`, captures Wayland frames through `zwlr_screencopy_manager_v1` and presents them to the Samsung DECON panel.

A VNC server that uses Wayland screencopy and virtual-input protocols is compatible with this architecture in principle; it must not open `/dev/fb0` directly. XRDP/Xorg remote sessions must be separate from the phone's single Phoc presentation owner. Do not add a second compositor that competes for the physical panel.

---

# 2. PRODUCT MODEL — THREE DISTINCT APPS, THREE DISTINCT SESSION SEMANTICS

Create these app surfaces and keep their responsibilities unambiguous.

## 2.1 XRDP Remote Desktop

- Purpose: allow Mac/Windows RDP client to log into a separate Nuxel X11 remote session.
- Preferred transport: Wi-Fi.
- Optional transport: USB network only when independently proven safe.
- Default service state: off.
- Expected port: TCP 3389, configurable only through a validated schema.
- Session semantics: new virtual remote X session, **not** a mirror of the physical Phoc screen unless a separate supported shadow implementation is actually proven.
- Remote UI must be useful: a lightweight Nuxel remote desktop/launcher web UI or a documented lightweight desktop must open, not a blank X root or only an `xterm` unless the UI explicitly identifies a diagnostic shell.
- Do not touch the physical panel/framebuffer or create another physical seat.

## 2.2 VNC Screen Sharing

- Purpose: view and control the actual running Nuxel/Phoc screen on the phone.
- Preferred transport: Wi-Fi.
- Optional transport: USB network only when independently proven safe.
- Default service state: off.
- Expected port: TCP 5900, configurable only through a validated schema.
- Session semantics: screen sharing/shadowing of the current Phoc Wayland session, not a separate Xvnc virtual desktop.
- Preferred server candidate: `wayvnc`, a VNC server for wlroots-based Wayland compositors. The Fedora package page currently lists a Fedora 43 build, but verify the target ARM64 package and runtime dependencies.
- Requires actual compositor protocols. Verify them from the live Phoc session.

## 2.3 scrcpy (Android)

- Purpose: display/control real Android device(s) through ADB using official scrcpy.
- Preferred transport: USB ADB.
- Optional transport: Wi-Fi/TCP-IP pairing.
- Default state: no ADB device assumed; do not enable debugging automatically.
- Android target requirement: Android API 21+ and USB debugging for normal ADB operation. Official scrcpy uses a host client and device-side server; it supports Android over USB or TCP/IP.
- Native Nuxel is Fedora/Linux, not Android. It cannot be a native scrcpy target merely by changing a device name or user-agent.
- If the user intends to view/control the Nuxel phone from the Mac, direct them to **VNC Screen Sharing**. That is the correct native Nuxel path.

The app is still required in Applications as a real, honest scrcpy capability surface. It must discover a real Android target and run scrcpy if one exists; otherwise show `NOT_APPLICABLE_NATIVE_NUXEL` or `NO_ANDROID_TARGET`, with a helpful explanation and VNC link. Do not claim that a blocked scrcpy target is a successful third native desktop protocol.

---

# 3. APPLICATIONS, APP REGISTRY AND GUI TRI-LINK INTEGRATION

## 3.1 New app IDs and paths

Use unique stable app IDs after checking every current catalog/registry. Recommended IDs:

- `org.nuxel.RemoteDesktopXRDP`
- `org.nuxel.RemoteDesktopVNC`
- `org.nuxel.ScrcpyMirror`

Suggested source paths:

```text
pwa/nuxel-apps/remote-xrdp/
  index.html
  app.json
  manifest.json
  js/remote-xrdp.js
  css/remote-xrdp.css
  icons/

pwa/nuxel-apps/remote-vnc/
  index.html
  app.json
  manifest.json
  js/remote-vnc.js
  css/remote-vnc.css
  icons/

pwa/nuxel-apps/remote-scrcpy/
  index.html
  app.json
  manifest.json
  js/remote-scrcpy.js
  css/remote-scrcpy.css
  icons/

pwa/nuxel-common/remote-desktop.js    # optional shared UI/controller module
```

Exact filenames may follow repository conventions, but each app needs its own entrypoint and stable registry record.

Update:

- `pwa/nuxel-common/app-registry.json`;
- `pwa/nuxel-home/js/apps.js` only if the canonical-registry architecture requires a generated mirror or fallback;
- `shell/nuxel-home-native/nuxel_home/app_registry.json` and its generation script;
- app icons/manifest paths;
- Home service worker/cache version and any per-app caches;
- `README.md`, app/remote-access docs and device capability manifest.

Preserve the existing registry entries for Serial Live Console, USB SSH Console and Wi-Fi SSH Console. Do not duplicate the new app entries in multiple handwritten catalogs without a validation test.

## 3.2 Applications drawer design

The drawer should display six distinct entries in appropriate groups:

**Developer / Console**
- Serial Live Console
- Wi-Fi SSH Console
- USB SSH Console

**Remote Desktop**
- XRDP Remote Desktop
- VNC Screen Sharing
- scrcpy (Android)

The existing console apps remain visibly available even while one transport is blocked. The three new apps also remain discoverable even when a backend is unsupported; they must show their true state and reason, not disappear. Use consistent icon sizes and card styles with the Nuxel UI.

## 3.3 Shared remote service presentation

Build a common UI state model to avoid three slightly different status implementations. Each app may have its own view, but status facts and state names must be shared.

Required states include:

- `OFF`: explicitly stopped;
- `STARTING`: activation requested;
- `READY`: server listening and service health verified;
- `WAITING_FOR_CLIENT`: ready with no remote client connected;
- `CONNECTED`: authenticated client/session genuinely connected;
- `STOPPING`: shutdown in progress;
- `BLOCKED_KERNEL`: required kernel interface/driver missing;
- `BLOCKED_KERNEL_PANIC`: transport prohibited by known panic evidence;
- `UNSUPPORTED`: protocol/backend unavailable on current platform;
- `NO_ANDROID_TARGET`: scrcpy has no real ADB target;
- `NOT_APPLICABLE_NATIVE_NUXEL`: scrcpy is not a native Nuxel screen-share path;
- `ERROR`: actual service/provider failure.

Never infer `CONNECTED` from the listening port. For VNC query wayvnc status/control socket or authenticated client state. For XRDP inspect actual xrdp-sesman session state. For scrcpy inspect real ADB target, process/transport and client/server session.

## 3.4 GUI Tri-Link overview

Provide an optional common `Remote Access`/`GUI Tri-Link` overview (either a fourth small dashboard or section in the existing three pages) that displays the three methods side-by-side:

- XRDP: service state, selected route, host/port and session status;
- VNC: service state, current Phoc session status, selected route and remote client count;
- scrcpy: ADB target count and Android target status;
- existing SSH Tri-Link: read-only summary showing serial/WLAN/USB console status separately.

Do not make the three new services synonyms for the old SSH transports. Make the distinction obvious: **Console Tri-Link** is serial/SSH; **GUI Tri-Link** is XRDP/VNC/scrcpy capability.

---

# 4. BRIDGE AND BACKEND ARCHITECTURE

## 4.1 Keep the current read-only Tri-Link endpoint read-only

`services/nuxel-bridge/src/tri_link_status.py` explicitly documents that it never starts/stops services, changes network routes or opens serial. Preserve that contract. It remains the authority for existing serial/Wi-Fi/USB SSH status.

Add a separate module, such as:

`services/nuxel-bridge/src/remote_desktop.py`

or a narrow service manager/provider with the equivalent separation. Add it to the current Bridge server/service installation and test environment.

## 4.2 New typed Bridge contract

Create a dedicated namespace, preferably `system.remote-desktop` or `remote-desktop` with verbs such as:

- `status`: read-only status of all named methods;
- `status-one`: read-only status of one named method;
- `start`: start one approved service profile;
- `stop`: stop one service;
- `set-transport`: update its preferred/active transport choice;
- `diagnose`: bounded read-only diagnostic;
- `connection-info`: generate safe connection details/tunnel instructions;
- `scrcpy-targets`: list ADB target metadata without secrets;
- `scrcpy-start` / `scrcpy-stop`: start/stop official scrcpy for a validated Android target if the execution context supports it.

Use exact enums for service and transport. Example service keys: `xrdp`, `vnc`, `scrcpy`. Example transports: `wlan`, `usb`, `android-adb-usb`, `android-adb-tcpip`. Do not conflate `usb` network with Android ADB USB or CDC-ACM serial.

Every operation must validate:

- caller authentication/session and capabilities;
- service key is allowlisted;
- transport is allowed for this service and currently available;
- port is in the service's fixed allowed range;
- bind address is a currently verified interface IP or loopback;
- start/stop action is explicitly user initiated;
- config file schema and path are known;
- the remote-access policy allows this action.

No generic `exec`, arbitrary `systemctl` action, shell command or client-supplied executable path is permitted.

## 4.3 Status contract

Expose only the metadata needed for display and tests. Suggested fields:

```json
{
  "service": "vnc",
  "state": "WAITING_FOR_CLIENT",
  "enabled_by_policy": true,
  "preferred_transport": "wlan",
  "active_transport": "wlan",
  "interface": "wlan0",
  "bind_address": "actual-current-wlan-address",
  "port": 5900,
  "listener_verified": true,
  "authenticated_clients": 0,
  "session_mode": "current-wayland-session",
  "authentication": "TLS_OR_SSH_TUNNEL",
  "encrypted": true,
  "started_at": "timestamp",
  "last_error": null
}
```

This is an illustrative schema. Never hardcode the example IP, claim `encrypted:true` without verifying the actual selected protocol/tunnel, or report a session mode not proven by the backend.

Scrcpy should additionally expose Android target metadata such as serial/device ID, transport type, ADB authorization state and Android API level when available. Do not expose ADB private keys, pairing secrets or Android account material.

## 4.4 Privilege boundary

Use a small privileged service/helper or carefully scoped systemd D-Bus/polkit integration. PWA JavaScript must not:

- write configfs or sysfs;
- call raw `systemctl` directly;
- edit firewall rules;
- read service passwords/private keys;
- kill arbitrary processes;
- create arbitrary user sessions;
- launch arbitrary host executables.

Service helpers use fixed executable paths, safe argument arrays, no shell interpolation, timeouts and bounded output. Persist config/state atomically with correct ownership/modes. Log only service IDs, request IDs and outcome/error codes, not credentials or note/app content.

---

# 5. XRDP IMPLEMENTATION — A REAL, USEFUL RDP SESSION

## 5.1 Package/build investigation

The current S10+ rootfs is Fedora-based ARM64 but uses an older vendor Linux kernel 4.14.253. Verify actual repository metadata and the target architecture for:

- `xrdp`;
- `xorgxrdp`;
- Xorg server and the required Xorg drivers/modules;
- TigerVNC `Xvnc` or alternative backend if needed;
- lightweight desktop/launcher session dependencies;
- PAM and TLS dependencies.

Fedora's xrdp and xorgxrdp package pages document these projects and recent Fedora packages, but a package's existence on x86_64 or Fedora 43 does not automatically establish ARM64 build availability. Query the actual repo metadata for `aarch64`, download package metadata without installing, inspect dependency closure and perform a clean rootfs package-resolve test.

## 5.2 Session semantics — do not fake physical-screen shadowing

XRDP with `xorgxrdp` provides an Xorg backend. It normally creates a separate remote desktop session. It is not automatically able to shadow an active Phoc/Wayland display. Do not call this “the same phone screen” unless it has been physically demonstrated.

Implement a separate session with clear UI text:

`Separate remote desktop session — does not mirror the physical Nuxel display.`

The physical Nuxel session must continue running on Phoc/Wayland. The XRDP X server must not take over `/dev/fb0`, stop Phoc, alter the physical panel mode or steal the physical touchscreen seat.

## 5.3 Backend selection

Preferred order:

1. `xrdp` + `xorgxrdp` if ARM64 packages and Xorg virtual session run on this image.
2. `xrdp` with a supported Xvnc/TigerVNC backend if Xorgxrdp is unavailable or incompatible.
3. Otherwise report XRDP blocked with exact package/backend/architecture issue and do not ship an empty service.

Do not use GNOME Remote Desktop as a drop-in on Phoc: its implementation is built around Mutter remote desktop APIs and GNOME session modes. Do not start GNOME/Mutter over the Nuxel physical compositor merely to get RDP.

## 5.4 Useful Nuxel remote session

Build a small remote session startup script/unit that provides a meaningful Nuxel workspace:

- a lightweight, touch-independent X11 desktop/window manager suitable for a small remote canvas;
- a Nuxel Home/Apps web application view hosted from the existing local PWA server, if it can run under X11 and communicate with the Bridge safely;
- a small set of safe remote diagnostics/settings shortcuts;
- no privileged terminal or root desktop by default.

The session must not blank or change the physical phone UI. It must use a separate X11 `DISPLAY`, separate session D-Bus/runtime state and a clean session shutdown. Do not reuse or overwrite the active Wayland session environment.

Test the actual session as a normal user; a successful xrdp listener with a blank black screen is not completion.

## 5.5 Authentication and network binding

- No root login.
- Use PAM with a dedicated restricted remote user or a carefully reviewed `nuxel` account session. Prefer a dedicated account without sudo and only the required app/data permissions.
- Do not use the screen-unlock PIN as the RDP password.
- Set strong unique credentials via a secure Settings flow; service secrets must not be passed as command-line arguments or displayed in plaintext after setup.
- Configure `xrdp.ini` and `sesman.ini` with a supported secure TLS configuration, a generated certificate/key with correct permissions, bounded session count and login delay/lockout.
- Do not claim NLA/CredSSP support if the selected xrdp build/backend does not actually support it.
- Prefer binding RDP to `127.0.0.1` and accessing it over an SSH local-forward from the Mac. If direct LAN binding is enabled, bind only to the current approved WLAN IP and enforce interface/subnet policy.
- Default port 3389 unless a fixed alternate is required; port must be validated by config schema.
- Keep service OFF at boot.

## 5.6 XRDP app functions

- current state;
- preferred transport `Wi-Fi`;
- USB disabled unless verified;
- start/stop;
- remote session status and active users;
- current WLAN address/port;
- “Copy SSH tunnel command” using the current pinned host key/key path, when the owner host key is available;
- “Create/import Jump Desktop RDP profile” or export a private `.rdp` file without credentials;
- service logs/diagnostics, sanitized;
- explicit note that this is a separate X11 session.

---

# 6. VNC IMPLEMENTATION — MIRROR THE REAL NUXEL PHOC SESSION

## 6.1 Why wayvnc is the first candidate

`wayvnc` is a VNC/RFB server designed for wlroots-based Wayland compositors. Its upstream describes attaching to an existing Wayland session, exporting one display over RFB and creating virtual input devices. Fedora's package catalog lists a Fedora 43 package. This aligns much better with Nuxel's Phoc/wlroots architecture than Xvnc, which creates a separate virtual X server.

Sources:

- Fedora package: `https://packages.fedoraproject.org/pkgs/wayvnc/wayvnc/`
- Official upstream: `https://github.com/any1/wayvnc`

## 6.2 Protocol preflight

Before installing/enabling, inspect the running Phoc session using `wayland-info`, compositor logs or other installed protocol introspection. Verify exactly which interfaces are advertised and supported, including the matching versions required by the selected wayvnc release:

- `zwlr_screencopy_manager_v1` or required supported screencopy protocol;
- `zwlr_virtual_pointer_manager_v1` or compatible virtual pointer interface;
- `zwlr_virtual_keyboard_manager_v1` or other supported keyboard injection path where required;
- any required output-management or ext protocols.

Do not infer support from “Phoc uses wlroots”. Test wayvnc's startup against the real socket and inspect errors. Confirm ARM64 package build and dependencies.

## 6.3 Attach to the actual active session

- Run wayvnc as the logged-in Nuxel session user, not root unless an exceptional reviewed permission model requires it.
- Use the actual `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY` owned by the active Phoc session.
- Make service start dependent on the Nuxel Wayland session being ready.
- Keep VNC in a separate service lifecycle but attached as an ordinary Wayland client.
- Ensure the frame captured remotely corresponds to the actual visible lockscreen/Home/app window on the physical panel.
- Ensure remote keyboard/pointer events reach the active Nuxel session through compositor virtual-input APIs and respect the existing lock policy.
- Do not bypass device lock or expose protected screen contents while locked. Remote client should see the actual lockscreen and must not get a backdoor unlock.
- Do not touch `/dev/fb0`, do not create a second physical display owner, do not change the `nuxel-wl-fb` service, and do not run a second compositor.

## 6.4 Security details

Wayvnc supports TLS/VeNCrypt and RSA-AES options in recent versions; it also documents legacy DES authentication as weak and unencrypted. Never enable the legacy DES-only mode on a network interface.

Preferred access model:

1. VNC listener bound to `127.0.0.1` by default.
2. Mac creates a local SSH forward over the existing verified WLAN SSH route using the pinned host key and authorized key.
3. Jump Desktop on Mac connects to local forwarded port (e.g. `127.0.0.1:5900` or `5901`) using a supported secure VNC authentication mode.
4. If Jump supports wayvnc TLS/VeNCrypt/RSA-AES in the installed Mac client, direct LAN VNC may be offered with strong authentication and certificate fingerprint validation. If not, keep the server loopback-bound and use SSH tunnel; never weaken to DES for compatibility.

Test the actual Jump Desktop client security negotiation. Do not put VNC password/private certificate in a PWA URL, clipboard command or QR code. Use secure credential setup and store files under the user's config directory with restrictive modes.

## 6.5 Performance and resolution

The S10+ is CPU constrained and the physical screen is high resolution. Configure a conservative remote-stream profile:

- sensible initial max dimensions (e.g. 1280px long edge, configurable);
- bounded update rate and encoding quality;
- no full-resolution 1440×3040 at maximum refresh by default;
- avoid expensive full-frame retransmission where server supports damage updates;
- keep physical phone display smooth while remote client connected;
- report actual fps/bitrate/latency if the server exposes them;
- allow user to select quality presets and observe real applied values.

Do not falsely report hardware-accelerated encoding. The display/encoding path may be software/Pixman.

## 6.6 VNC app functions

- current state and actual Phoc connection;
- preferred transport Wi-Fi;
- active listener/interface/port;
- whether remote control input is enabled or view-only;
- Start/Stop (explicit consent);
- current connected-client count;
- copy secure SSH tunnel command or show approved direct LAN details;
- show current host key/TLS fingerprint for first-use verification;
- `Recheck` with actual Wayland protocol/support output;
- USB route only when independently verified;
- persistent privacy indicator and kill switch.

A VNC app is complete only when the Mac sees and controls the actual physical Nuxel screen. An Xvnc virtual desktop is not an acceptable replacement for this specific app.

---

# 7. SCRCPY — OFFICIAL ANDROID ENDPOINTS ONLY

## 7.1 Product reality

Official scrcpy (`https://github.com/Genymobile/scrcpy`) mirrors and controls **Android** devices over USB or TCP/IP. The official project requires Android API 21 or newer and USB debugging for normal operation. The scrcpy host client deploys/starts a matching `scrcpy-server` on the Android target through ADB; its internal client/server protocol is version-coupled and intended for scrcpy, not as a generic Linux display protocol.

Native Nuxel is Fedora ARM64/Wayland. It does not provide Android `MediaProjection`, `SurfaceControl`, `INJECT_EVENTS`, Android framework or ADB daemon behavior. Installing the `scrcpy` package on Nuxel does not make Nuxel a scrcpy target.

## 7.2 App implementation

Create a proper `Scrcpy (Android)` app that is useful when an actual Android target exists:

- Detect `adb` executable availability and version.
- Enumerate attached USB Android ADB devices and distinguish `device`, `unauthorized`, `offline`, `no permissions`, unsupported target and no-device states.
- Show USB ADB as default/preferred transport.
- Allow Wi-Fi/TCP-IP pairing only after explicit user action on an actual target that supports Android wireless debugging; use pairing code/port flow with bounded lifetime.
- Do not keep ADB TCP debugging open indefinitely; restore/disable it on stop where device supports it.
- Use official scrcpy client and matching server version. Never mix client/server versions or download binaries from unofficial mirror sites.
- Use safe arguments, bounded process lifecycle and clear logs.
- Show resolution, fps/audio capability and real session state where available.
- Start/stop/clean up only the scrcpy process and adb connection owned by this app.
- Do not auto-authorize or trust an Android device without the user confirming the ADB key/authorization prompt.

## 7.3 Native Nuxel state

When no real Android ADB target exists:

- Set state `NOT_APPLICABLE_NATIVE_NUXEL` or `NO_ANDROID_TARGET`.
- Explain that scrcpy is Android-only and does not mirror Nuxel's native Linux desktop.
- Provide a direct launch/open link to `VNC Screen Sharing` for native Nuxel remote view/control.
- Do not display `READY`, `CONNECTED` or a fake screen-preview.
- Do not install Waydroid or Android images. If Waydroid already exists, inspect it read-only and only offer an Android target if the owner explicitly enables it and ADB is actually reachable.
- Do not try to alter build properties/device identity to fake an Android target.

If a native Nuxel low-latency mirror is desired in a future mission, give it a different name (`Nuxel Mirror`) and a separately documented protocol/client. Do not claim that a custom Wayland stream is scrcpy or that Jump Desktop understands a proprietary stream.

## 7.4 USB and Wi-Fi semantics

Scrcpy USB is Android ADB USB, not Nuxel's USB network interface and not CDC-ACM. Scrcpy Wi-Fi is ADB over TCP/IP or Android wireless debugging, not XRDP/VNC's WLAN route. Keep those states and controls separate.

---

# 8. NETWORKING — WI-FI DEFAULT AND SAFE USB ALTERNATIVE

## 8.1 Wi-Fi connection discovery

Use current network facts from the Bridge or a dedicated provider; do not hardcode a past `10.20.30.x` address. Distinguish:

- current WLAN interface and address;
- subnet/mask;
- default route;
- whether the address is global, private, loopback or link-local;
- whether it is a trusted/approved LAN for remote desktop;
- whether SSH key-only service is actually listening;
- whether the client Mac can reach it locally.

If the phone changes Wi-Fi network/address, update status and connection details. Never silently keep advertising a stale IP.

## 8.2 Preferred secure delivery: SSH tunnel

The repository already has a key-only Tri-Link SSH path and pinned host key. Where the Mac has the authorized private key and matching pinned host key, prefer local SSH forwards:

- RDP local Mac port → Nuxel loopback RDP port;
- VNC local Mac port → Nuxel loopback VNC port.

Use the exact approved `known_hosts` pin and `StrictHostKeyChecking=yes`. Do not disable host key verification to “make Jump work”. Do not copy the SSH private key to Nuxel. Do not embed any private key/credential in a generated `.rdp` file. Do not launch a wildcard SSH reverse tunnel or public listener.

The remote desktop UI can produce a host-side helper command for the Mac, but it must be an explicit, safe, bounded command, not executable text passed back to the phone.

## 8.3 Direct Wi-Fi listener option

If direct WLAN remote desktop is needed and supported, bind only to the actual current approved Wi-Fi IP. Use strong TLS/authentication and enforce the local subnet policy. Remote-access is still OFF by default and activation requires explicit owner confirmation. Never bind to all interfaces, cellular interface or public WAN.

## 8.4 USB networking audit and hard guard

The current historical `remote-access.json` has a reserved USB SSH address and a prior report of USB NCM panic. The live gadget must be probed read-only first:

- UDC name/state;
- currently configured functions and symlinks;
- host-visible interfaces on the Mac;
- kernel config for NCM/ECM/RNDIS/FunctionFS/CDC functions;
- active CDC-ACM serial path;
- physical host driver support on current macOS;
- any known teardown/pstore failures.

Do not mutate configfs or rebind UDC as part of diagnosis. Do not try the known unsafe NCM path on 4.14.253. ECM/ECM_SUBSET were absent in the recorded kernel. RNDIS was compiled but not physically validated and may lack a native macOS host driver; test real macOS support before choosing it.

USB RDP/VNC may be made available only if a non-NCM transport is proven safe and stable, does not remove serial recovery, and the Mac can obtain an IP route. It must have an independent rollback plan. Until then the optional USB toggle is disabled with exact `BLOCKED_KERNEL_PANIC` / `UNVERIFIED_HOST_DRIVER` reason. Do not set USB status to ready just because a configfs function name exists.

---

# 9. MACBOOK + JUMP DESKTOP — MANDATORY LIVE CLIENT TEST

The user explicitly requests the agent to use the MacBook's Jump Desktop app to connect to the phone and test it live. This is a mission acceptance requirement, not an optional documentation task.

## 9.1 Identify the actual Mac host

Historical project documentation identifies Fedora 43 `dextronux` as a previous development host. The current agent may run on the MacBook, on Fedora, or somewhere else. Determine the real environment instead of assuming.

On the MacBook, use read-only checks such as:

```sh
sw_vers
uname -a
uname -m
scutil --get ComputerName
networksetup -listallhardwareports
```

Find Jump Desktop, for example by inspecting `/Applications`, LaunchServices/Spotlight metadata or `mdfind`. Verify app version and code signature. Check whether Jump Desktop is open/running. Do not install or update it automatically, do not sign in to an account, and do not grant macOS accessibility/screen-recording permissions without the owner's approval.

The MacBook must be on a network where it can reach the phone's Wi-Fi address, or use the existing approved VPN/SSH route. Do not scan unrelated networks. Use the phone's current Bridge-discovered WLAN address and independently verify that the Mac is on the same reachable LAN.

## 9.2 Distinguish Jump Desktop Viewer and Jump Desktop Connect

- **Jump Desktop for Mac** is the client/viewer on the MacBook.
- **Jump Desktop Connect** is a host agent used when a computer is made available through Jump's Fluid/cloud workflow.
- Nuxel is implementing its own RDP/VNC server. Do not install Jump Desktop Connect on Nuxel as if it were the RDP/VNC server.
- For manual Linux VNC, Jump's support says to configure the Linux host address and select VNC. Verify the actual Mac client UI/version.
- Jump's documentation supports importing `.rdp` remote-resource files on Mac. Verify the current app can import the generated local RDP profile, or add the server through its current UI if direct RDP is supported.

Official references to check against the installed client:

- Jump Desktop client/viewer: `https://docs.jumpdesktop.com/viewer/`
- Install Jump Desktop client for Mac: `https://docs.jumpdesktop.com/viewer/install/`
- Jump's Linux/VNC compatibility note: `https://support.jumpdesktop.com/hc/en-us/articles/216426043-General-Is-Jump-Desktop-compatible-with-Linux`
- Jump's VNC guidance: `https://support.jumpdesktop.com/hc/en-us/articles/218327683-VNC-How-to-use-VNC-with-Jump-Desktop-Connect`
- Jump RDP `.rdp` import: `https://support.jumpdesktop.com/hc/en-us/articles/215106626-General-Connecting-to-RDP-Remote-Resources-or-Remote-Apps`

If the Mac Jump app can be controlled by an approved GUI automation/Computer Use capability, use that real UI. If it cannot, do not claim live client validation; prepare the profile and give the owner the exact remaining click/permission step. Never claim that a Jump test occurred based only on `nc`, curl or protocol banners.

## 9.3 VNC live test via Jump Desktop

1. Ensure Nuxel is unlocked and its physical Phoc/Home screen is visible.
2. Start VNC Screen Sharing using Wi-Fi preferred transport.
3. Verify service state, real listener and current interface. If server is loopback-bound, create an SSH local forward from Mac using the repo's pinned host key and authorized key. Confirm SSH reports the expected pinned key; no `StrictHostKeyChecking=no`.
4. Open Jump Desktop for Mac.
5. Create a manual VNC connection to the phone's live WLAN IP/port or to the local forwarded port.
6. Accept/trust TLS/host fingerprint only after showing it to the owner or matching the expected generated fingerprint.
7. Confirm that the actual phone screen is visible: lockscreen, Home, app drawer or a known harmless test screen.
8. Test pointer and keyboard input. Use a disposable test note with unique marker such as `PWNAGE-47000-VNC-<timestamp>` or an on-screen test panel. Do not edit actual user notes or credentials.
9. Confirm that the remote click lands on the visible control, text input enters correctly, scrolling works, orientation changes are reflected and remote input does not bypass local lock policy.
10. Disconnect from Jump, reconnect and confirm a second session works or is refused according to configured session policy.
11. Stop VNC from Nuxel and verify listener, service, virtual input devices and remote indicator clear.
12. Record screenshots from the Mac Jump viewer and Nuxel state/logs. Do not include credentials or secret note contents.

If Jump Desktop cannot negotiate the chosen wayvnc TLS/RFB authentication mode, keep security intact. Try the supported SSH-tunnel approach or use a compatible VNC viewer for protocol diagnosis. Do not enable DES-only VNC just to satisfy Jump.

## 9.4 XRDP live test via Jump Desktop

1. Start XRDP using Wi-Fi preferred transport.
2. Verify the separate Xorg/Xvnc session backend and PAM auth are ready.
3. Prefer SSH local forwarding to phone loopback port 3389; otherwise use only an explicitly secure direct WLAN bind.
4. Generate a local private `.rdp` connection file for Jump Desktop, with host/port and safe display settings but **no username/password secret**. Use a private temporary directory and restrictive permissions.
5. Import into Jump Desktop for Mac using the current supported menu/flow or create a direct RDP host if supported by the installed client.
6. Connect and log in using the separate restricted remote session credential.
7. Confirm a usable Nuxel remote desktop/session appears (not a blank X server), keyboard/mouse input works and the chosen resolution is reasonable.
8. Verify physical phone Phoc/Home still runs and the local touch display is unaffected.
9. Disconnect/log out; confirm `xrdp-sesman` terminates the session and cleanup runs.
10. Reconnect and repeat.

If Jump Desktop's current Mac client cannot connect directly to a manually configured xrdp host, try importing `.rdp` as the documented path. If still unsupported, test with Microsoft's Windows App for macOS or another genuine RDP viewer as a protocol fallback, but report Jump RDP as not supported by that client version rather than claiming a successful Jump connection.

## 9.5 USB live test

Only after an independently safe USB network route is built and physically verified on this exact kernel/host. Repeat the RDP/VNC connection using the USB interface IP. Confirm CDC-ACM serial remains present and usable before, during and after the test. If the known NCM blocker remains, do not run any USB mutation; record the optional USB path as blocked and leave Wi-Fi as default.

## 9.6 scrcpy live test

Use official scrcpy on a real Android target. If an external Android device is available and explicitly authorized, connect USB ADB, accept its device authorization on the Android device and start scrcpy. Test Wi-Fi pairing only after USB succeeds. If there is no Android target or no authorized Waydroid endpoint, confirm Scrcpy app's truthful unavailable state and use the VNC app for Nuxel-native screen access.

---

# 10. REMOTE-ACCESS SECURITY AND PRIVACY MODEL

Remote desktop is high-impact control of a mobile device. Apply a stronger default posture than an ordinary local app.

## 10.1 OFF by default

- `remote-access.json` remains `enabled:false` after clean install.
- No XRDP/VNC service is listening at boot.
- App preference (`wlan` or `usb`) is stored independently from service enabled state.
- User must explicitly tap Start and approve the interface/address/port shown.
- Stop All Remote Access is always accessible from the remote apps and Quick Settings/settings privacy area.

## 10.2 Allowed interfaces

- WLAN only by default; bind to the exact current WLAN address or loopback for tunnel mode.
- USB only after verified USB network capability and separate owner consent.
- Never bind to `rmnet0`/cellular, public WAN, all interfaces or all IPv6 addresses by default.
- No router port forwarding, UPnP or remote cloud relay in this mission.
- Respect existing firewall and `AllowUsers` restrictions; do not weaken the SSH policy.

## 10.3 Authentication

XRDP:

- PAM/local account auth, unique non-root user, lockout/backoff and bounded sessions.
- TLS cert/key with correct permissions.
- no anonymous/guest login and no root desktop login.

VNC:

- strong auth and TLS/VeNCrypt/RSA-AES or SSH tunnel;
- no DES-only mode;
- no password in PWA localStorage, URLs, QR codes, clipboard commands or logs;
- display certificate fingerprint for first trust.

SSH tunnel:

- pinned host key and `StrictHostKeyChecking=yes`;
- authorized public key only;
- no private key copied to phone;
- no forwarding beyond the exact local ports needed;
- tunnel stops when remote app disconnects or owner presses stop.

scrcpy:

- require explicit ADB device authorization;
- short-lived Wi-Fi debugging session;
- do not store Android secrets or ADB private keys in app UI storage;
- clean target connection on stop.

## 10.4 Lock policy

- VNC mirrors the current screen exactly. When Nuxel is locked, the remote viewer must see only the lockscreen and cannot unlock by bypassing the real session authentication.
- If remote-control input is enabled, it must pass through the same compositor/session lock gates as local input.
- XRDP is a separate authenticated session; do not grant root or automatic access to the physical session's secrets.
- Closing the VNC app UI must not silently leave an invisible active remote server; display a persistent indicator and provide a central stop control.

## 10.5 Connection lifetime

Implement configurable session timeout/idle-stop, max remote sessions and failed-auth backoff. On Wi-Fi detach, IP change, sleep, service failure or policy disable, update state immediately and close/rebind only using safe controlled logic. Never leave a service listening on a stale or newly public interface.

---

# 11. SYSTEMD, PACKAGES AND ROOTFS BUILD INTEGRATION

The current image is a lean custom Fedora-based phone image. Do not install packages only on the development host or rely on an untracked manual package install.

## 11.1 Verify aarch64 packages and dependency closure

Before selecting dependencies, query actual repository metadata for the target release/architecture. Candidates include:

- `wayvnc` and its runtime stack;
- `xrdp` and `xorgxrdp`;
- Xorg/Xvnc/TigerVNC and a minimal session/WM if needed;
- `adb`/Android platform tools and `scrcpy` only if a compatible ARM64 package exists and the host-side use case justifies it;
- TLS, PAM and D-Bus/polkit dependencies.

Check aarch64 architecture, package repo trust/signatures, size, old-kernel compatibility, hard dependencies, service files and runtime operation. Do not assume Fedora 43 x86_64 package metadata establishes ARM64 availability.

## 11.2 Build integration

Update the authoritative `images/s10plus/build-phone-rootfs-inside-fedora.sh` and package manifest. Add:

- binaries and libraries;
- app files/assets;
- systemd units;
- service configs/schema;
- credentials/state directories with strict ownership;
- firewall/polkit policy as applicable;
- app registry and PWA cache version changes;
- clean-image assertions for all expected files and architecture.

Do not replace the active Wayland session, remove Phoc, alter the framebuffer owner or enable a new display manager to satisfy XRDP.

## 11.3 Systemd services

Use narrow units with correct ordering and hardening, with activation-driven start/stop. Services should not start at boot by default. `wayvnc` should be associated with the actual user Wayland session. XRDP should start the remote X session only when authenticated. Add a dedicated service manager or Bridge-controlled unit activation path. Do not allow PWA code to call raw systemctl.

Ensure all services:

- fail closed on missing config or credential;
- stop child processes and remove runtime sockets on shutdown;
- remove temporary USB/forward/listener state;
- log bounded diagnostic reasons;
- do not run as root unless strictly needed by a restricted unit capability;
- cannot access SSH private keys or authenticator secrets;
- enforce per-user session isolation.

---

# 12. PERFORMANCE AND QUALITY

S10+ has an old 4.14.253 kernel and software-heavy Phoc/Pixman/framebuffer output. Remote desktop streaming must not make the physical UI unusable.

Before and after testing, measure:

- idle CPU/RAM with services off;
- VNC connected idle and active scrolling/input;
- XRDP remote session idle and active;
- frame rate/latency and dropped update behavior;
- battery and thermal changes where available;
- physical UI responsiveness with remote client connected;
- Wi-Fi bandwidth and connection stability.

Apply caps:

- reasonable remote resolution and frame rate;
- configurable quality/bitrate/encoding;
- bounded remote sessions;
- no unnecessary background polling;
- no permanent high-rate screenshot capture when VNC is off;
- stop audio/capture workers when disconnected;
- adapt quality if CPU or temperature exceeds safe limits.

Do not claim hardware encoding or 60 FPS without measurement. `nuxel-wl-fb` remains the only physical framebuffer writer. VNC can access Wayland capture APIs; it must not start another framebuffer capture/presentation loop of its own.

---

# 13. AUTOMATED TEST PLAN

Add focused tests for new functionality and preserve all existing console tests.

## 13.1 Registry and UI tests

- all three app IDs unique and registered once;
- existing Serial/WLAN/USB SSH entries unchanged;
- app manifest/entry paths all exist;
- apps appear in Applications drawer;
- each app reports distinct protocol/transport semantics;
- no mock Bridge success makes any service appear active;
- app status refreshes when visible, pauses when hidden and cancels stale requests;
- no service auto-start on Home open/boot;
- cache/version update serves new code.

## 13.2 Bridge/service tests

- valid and invalid service names/transports;
- unauthorized start/stop rejected;
- OFF → STARTING → READY → CONNECTED → STOPPING → OFF transitions;
- provider crash, stale PID, port unavailable, bind failure, interface loss and timeout;
- status truth from real service/control socket;
- no secret fields in API output;
- service start idempotent;
- stop closes listener and firewall allowance;
- current Wi-Fi IP is dynamically discovered;
- USB route blocked on known-bad kernel without configfs mutation.

## 13.3 XRDP tests

- package architecture and dependency resolve;
- xrdp-sesman starts only on explicit enable;
- Xorg/xorgxrdp or Xvnc backend starts a working session;
- login success and auth failure;
- no root login;
- TLS config present;
- separate session isolation; no Phoc or `/dev/fb0` ownership changes;
- session logout cleans up X server and processes;
- Jump-import `.rdp` profile contains no credentials.

## 13.4 VNC tests

- wayvnc binary and protocol compatibility against actual Phoc;
- no screencopy/virtual-pointer protocol means explicit unsupported state;
- service runs as correct user/session;
- real screen capture frame changes when physical screen changes;
- remote input maps correctly to compositor controls;
- locked state is respected;
- authenticated client count accurate;
- no DES-only fallback;
- certificate/SSH tunnel works;
- stop removes virtual devices/sockets/listener cleanly.

## 13.5 scrcpy tests

- adb absent, scrcpy absent, no targets;
- USB authorized/unauthorized/offline target;
- Wi-Fi pairing success/failure/timeout;
- Android API below supported minimum;
- official client/server version mismatch;
- stop cleans target-side process/ADB transport;
- native Nuxel reports not applicable/no Android target honestly;
- no Waydroid auto-install or spoofing.

## 13.6 Security tests

- no listener on wildcard/cellular/public address;
- no service active after boot by default;
- weak/empty credentials rejected;
- no passwords or private keys in logs/configs exposed to PWA;
- host-key mismatch refuses SSH tunnel;
- VNC DES-only mode prohibited;
- repeated auth failure locks/backoffs;
- remote access indicator visible while active;
- lockscreen not bypassed by VNC or XRDP;
- no port-forwarding/UPnP/cellular route created.

## 13.7 Physical acceptance tests

Must be completed from the actual MacBook using Jump Desktop for RDP and VNC. Unit tests cannot replace this requirement.

---

# 14. ON-DEVICE DEPLOYMENT AND LIVE TEST SEQUENCE

## Phase A — safe baseline

- Record source branch/commit/dirty state.
- Record current Nuxel version, kernel, build ID and active services.
- Verify Tri-Link WLAN SSH and Serial Live Console currently work.
- Verify USB SSH state and NCM blocker without attempting a gadget mutation.
- Record current configfs UDC/functions and `/dev/fb0` owner.
- Check Phoc protocol globals and output.
- Check current package/architecture availability.
- Check MacBook/Jump Desktop presence and version.
- Back up remote-access config, app registry, services/configs and existing known-hosts/SSH state.

## Phase B — VNC first

1. Verify wayvnc package and Phoc protocol support.
2. Install/stage wayvnc and a secure configuration; keep OFF.
3. Add Bridge status/control and VNC app.
4. Start over Wi-Fi explicitly.
5. Establish secure SSH local forward or verified TLS path from the Mac.
6. Open Jump Desktop for Mac and connect as VNC.
7. Verify physical screen is visible and remote clicks/keyboard are functional.
8. Confirm local phone touch still works and remote disconnect leaves the phone UI unaffected.
9. Stop service and prove listener/virtual input cleanup.

## Phase C — XRDP

1. Verify ARM64 xrdp/xorgxrdp/Xorg or Xvnc dependencies.
2. Build a separate lightweight remote X session.
3. Add Bridge status/control and XRDP app.
4. Start over Wi-Fi explicitly.
5. Create a safe temporary `.rdp` file or direct Jump connection; no credentials in the file.
6. Connect with Jump Desktop Mac, authenticate, verify usable session and input.
7. Confirm no effect on physical Phoc screen or `/dev/fb0` owner.
8. Disconnect/log out, stop service and prove session cleanup.

## Phase D — scrcpy

1. Verify official scrcpy and ADB capability.
2. Detect real Android target(s), if any.
3. Test USB ADB first; verify user-authorized prompt.
4. Test Wi-Fi pairing only if the real target supports it.
5. If no Android target exists, verify correct unavailable/not-applicable UI and direct user to VNC for native Nuxel. Do not install Waydroid.

## Phase E — optional USB network

Only if a safe non-NCM USB networking function is established and the owner explicitly permits mutation. Verify it from the Mac's actual macOS kernel/driver stack and prove CDC-ACM recovery stays active. Then repeat VNC or RDP through USB. Otherwise mark blocked and stop.

## Phase F — regression and delivery

Run all existing Tri-Link tests plus new tests. Verify app cache/revision and clean ARM64 image. Save evidence and rollback. Do not reboot unless required and safely approved.

---

# 15. ROLLBACK AND RECOVERY

- Preserve Serial Live Console and the existing WLAN SSH route throughout.
- Do not stop SSH or change its AllowUsers/host-key policy as part of remote desktop feature work unless separately approved and proven safe.
- Before deployment, back up every modified file, unit, config, registry, package manifest and remote access policy.
- Use staged/atomic installation and per-service restart.
- If VNC start crashes Phoc or destabilizes input, stop only the VNC service and restore its config; do not kill the compositor or framebuffer bridge.
- If XRDP start harms the physical session, stop xrdp/xrdp-sesman and clean its remote X session; never reset physical Phoc to “fix” it.
- If USB experimentation produces any gadget descriptor or host error, do not continue cleanup experiments on NCM; preserve serial/UDC, record evidence and use the established recovery procedure.
- Do not flash kernel, bootloader, recovery, partitions or device firmware.
- Maintain known-good Wi-Fi remote shell and serial recovery.

---

# 16. DELIVERABLES

Create/update:

1. `docs/beta-finalization/live/PWNAGE-47000-TODO.md` with every implementation, test, dependency, result and blocker.
2. `docs/beta-finalization/live/evidence/pwnage-47000/` containing baseline, build/package checks, service logs, Mac Jump screenshots, VNC frame/input proof, XRDP session proof, security checks, USB blocker/optional USB evidence and deployment hashes.
3. Three new PWAs with manifests/assets/styles/JS and unique canonical registry entries.
4. Shared Bridge provider/control contract and narrow privileged helper/service(s).
5. XRDP server/backend/session scripts and configs if supported by ARM64 target.
6. VNC server/package/config using wayvnc if the actual Phoc protocols allow it.
7. Scrcpy app with real Android ADB detection, USB-first/Wi-Fi optional control and honest native Nuxel incompatibility.
8. Updated `configs/nuxel/security/remote-access.json` schema/defaults, preserving OFF-by-default and legacy Tri-Link restrictions.
9. Updated rootfs/package/systemd build integration and validation tests.
10. Final report: what actually works on S10+, what was tested using Jump Desktop on Mac, exact package/build versions, active addresses/ports (no secrets), connection screenshots, input proof, performance data, USB result and rollback commands.

---

# 17. FINAL ACCEPTANCE MATRIX

| Item | Pass condition |
|---|---|
| Existing Tri-Link consoles | Serial, WLAN SSH and blocked USB SSH states remain correct; no regression |
| XRDP app | Visible app, real xrdp backend/session, separate useful remote desktop, secure Wi-Fi connection from Jump Desktop Mac, keyboard/mouse works |
| VNC app | Visible app, wayvnc-compatible real Phoc session, secure Wi-Fi connection from Jump Desktop Mac, remote display and input works |
| scrcpy app | Real ADB Android target is detected and official scrcpy works, or native Nuxel limitation is honestly shown; no fake READY state |
| Wi-Fi defaults | XRDP/VNC prefer Wi-Fi; scrcpy prefers USB ADB; all route states dynamically discovered |
| USB optional RDP/VNC | Enabled only with a physically safe and Mac-compatible USB network route; otherwise exact blocker and no mutation |
| Security | OFF by default, explicit enable, authenticated, encrypted, interface-restricted, no secrets in PWA/logs, lockscreen respected |
| Jump Desktop | Actual Mac Jump client shows the live remote session and accepts input for VNC and XRDP where supported; fallback client documented only if Jump lacks a protocol feature |
| Performance | Phone remains responsive; measured CPU/RAM/FPS/latency; no second framebuffer owner |
| Build | Clean ARM64 rootfs includes selected servers, units, configs, apps and registry entries |
| Rollback | Services stop cleanly; existing WLAN SSH and CDC-ACM serial recovery remain intact |

## FINAL RULE

**Do not confuse three separate concepts:**

- SSH Tri-Link is the current development/recovery console system.
- XRDP is a separate remote X11 desktop session.
- VNC is the native Nuxel/Phoc screen-sharing path.
- scrcpy is for Android targets only; it cannot mirror native Nuxel by pretending Nuxel is Android.

The user specifically wants a real MacBook Jump Desktop connection test. A port probe is not proof. Only a visible remote desktop plus verified keyboard/mouse interaction from the Mac client counts as live acceptance.

**Implement the apps, connect them to the real system services, test them from Jump Desktop on the MacBook, retain the current recovery transports and report every unsupported capability honestly.**

🐧 **NUXEL — ONE PHONE, THREE GRAPHICAL ACCESS PATHS, REAL CONNECTIONS.**

---

# 18. PRIMARY UPSTREAM / VENDOR REFERENCES TO RECHECK DURING IMPLEMENTATION

These are the starting points, not a substitute for checking the exact installed versions and protocols:

- Jump Desktop viewer documentation: https://docs.jumpdesktop.com/viewer/
- Jump Desktop Mac viewer installation: https://docs.jumpdesktop.com/viewer/install/
- Jump Desktop Linux/VNC compatibility: https://support.jumpdesktop.com/hc/en-us/articles/216426043-General-Is-Jump-Desktop-compatible-with-Linux
- Jump Desktop VNC guidance: https://support.jumpdesktop.com/hc/en-us/articles/218327683-VNC-How-to-use-VNC-with-Jump-Desktop-Connect
- Jump Desktop RDP resource import: https://support.jumpdesktop.com/hc/en-us/articles/215106626-General-Connecting-to-RDP-Remote-Resources-or-Remote-Apps
- Fedora xrdp package: https://packages.fedoraproject.org/pkgs/xrdp/xrdp/
- Fedora xorgxrdp package: https://packages.fedoraproject.org/pkgs/xorgxrdp/xorgxrdp/
- Fedora wayvnc package: https://packages.fedoraproject.org/pkgs/wayvnc/wayvnc/
- Official wayvnc upstream: https://github.com/any1/wayvnc
- TigerVNC/Xvnc documentation: https://tigervnc.org/doc/Xvnc.html
- Official scrcpy upstream: https://github.com/Genymobile/scrcpy
- scrcpy architecture/protocol notes: https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md

Recheck current supported versions, ARM64 builds and client security compatibility on the implementation date. Never download scrcpy binaries from unofficial sources.
