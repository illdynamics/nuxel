# FULL-PWNAGE-92000 — NUXEL DIRECT LAN REMOTE DESKTOP + GUI TRI-LINK + USB NETWORK RECOVERY

**Mission ID:** PWNAGE-92000  
**Target:** Nuxel Mobile Linux — Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820)  
**Repository baseline supplied for this mission:** Nuxel `v0.7.7-beta` archive, dated documentation through 2026-11-01.  
**Primary objective:** make XRDP and VNC directly reachable from the owner's LAN on the requested non-default ports, repair the GUI Tri-Link screen-mirroring/scrcpy experience without lying about protocol compatibility, and bring the third Serial/Wi-Fi/USB SSH Tri-Link option to a safe, genuinely usable USB-network implementation where the current kernel and host support permit it.  
**Required blocker report:** `./REPORT-USBNET.md`  
**Priority:** correctness, safe recovery and existing functionality preservation before feature claims or cosmetic polish.

---

## 0. EXECUTIVE DIRECTIVE — READ BEFORE TOUCHING CODE

You are the senior Linux platform, kernel, networking, remote-desktop, Wayland, security and Nuxel integration engineer. Do not begin by changing ports in one configuration file, adding another PWA, or running a USB gadget experiment. First reconstruct the complete current implementation and prove how all components work together.

The supplied source tree already contains substantial Tri-Link and remote-desktop infrastructure. Your job is to finish, correct and unify it. Do not create a second competing remote-access daemon, another unrelated USB gadget manager, duplicate status provider, duplicate console application, or an alternate configuration store.

### User-visible result required

1. From a computer on the same trusted LAN, the owner can connect directly to Nuxel using:
   - **RDP:** `PHONE_LAN_IP:13389` over TCP.
   - **VNC:** `PHONE_LAN_IP:15900` over TCP.
   - No SSH tunnel, local port-forward, proxy tunnel, or Jump Desktop Connect host agent is required for either direct LAN route.
2. XRDP creates the explicitly labelled separate remote X11 desktop. VNC captures the actual active Phoc/Wayland phone session. These are different session types and must never be mislabelled as equivalent.
3. Both services remain OFF by default and are started only by the owner's explicit action. Stop/Stop All reliably closes the actual listener and removes any temporary firewall allowance.
4. RDP and VNC both use working authentication and encryption. VNC must not silently fall back to unauthenticated RFB. The current repository has a serious mismatch between VNC runtime configuration and the Bridge's advertised security state; fix it.
5. The third GUI Tri-Link option must give the owner an honest, working screen-mirroring path. Official `scrcpy` is Android/ADB-specific. Native Nuxel is Linux/Wayland, not Android. Do not invent a fake ADB device or claim official scrcpy can mirror native Phoc. Keep legitimate Android scrcpy support, and provide a clear native Nuxel mirror route through the native screen-sharing backend (VNC) or a separately named native mirror implementation if the audit proves the existing experience is insufficient.
6. The third console option, **USB SSH Console**, must use a real USB network interface and the Tri-Link host CLI must connect over it using the existing pinned-key SSH path. Do not claim READY because a kernel option is compiled or a configfs function directory exists. READY requires a live host interface, correct IP route, SSH listener, successful key-authenticated connection and verified command execution.
7. The known USB NCM teardown panic on the recorded 4.14.253 device must never be casually retried. Investigate other compiled function modes, especially RNDIS, and inspect exact kernel sources/teardown paths before any physical gadget modification. Preserve the CDC-ACM serial recovery console.
8. Any remaining USB-network blocker, failed compatibility path, or unverified host requirement must be captured in `./REPORT-USBNET.md` with exact evidence and a best next step.

### Hard rule

**No regression, no fake READY state, no removal of serial recovery, no unsafe USB gadget experiment, no weak/unauthenticated LAN listener, and no breaking of the working WLAN SSH path.**

---

## 1. REPOSITORY BASELINE AND KNOWN FINDINGS TO VERIFY

The supplied archive was inspected at `v0.7.7-beta`. These findings are a starting point, not permission to assume the active checkout is identical. Begin by comparing the current working tree, version, git branch, commit, modified files and installed-image state. The active checkout wins over this snapshot, but every difference must be understood.

### 1.1 GUI Tri-Link architecture already present

Relevant current files include:

- `configs/nuxel/security/remote-access.json`
- `services/nuxel-bridge/src/remote_desktop.py`
- `services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl`
- `services/nuxel-remote-desktop/config/xrdp.ini`
- `services/nuxel-remote-desktop/config/sesman.ini`
- `services/nuxel-remote-desktop/config/xorg.conf`
- `services/nuxel-remote-desktop/config/xrdp-sesman.pam`
- `services/nuxel-remote-desktop/config/wayvnc.conf.example`
- `services/nuxel-remote-desktop/systemd/nuxel-remote-vnc.service`
- `services/nuxel-remote-desktop/bin/nuxel-xrdp-session`
- `pwa/nuxel-common/remote-desktop.js`
- `pwa/nuxel-common/remote-desktop.css`
- `pwa/nuxel-apps/remote-xrdp/`
- `pwa/nuxel-apps/remote-vnc/`
- `pwa/nuxel-apps/remote-scrcpy/`
- `pwa/nuxel-common/app-registry.json`
- `GUI-TRI-LINK-QUICKSTART.md`
- `docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md`
- `docs/beta-finalization/live/NUXEL-28000-TRI-LINK-UI-REPORT.md`

The GUI remote-desktop provider is intentionally separate from the Serial/WLAN/USB SSH console provider. Preserve that separation at the ownership/API boundary. It is correct to keep `system.remote-desktop` separate from `system.tri-link`; it is not correct to let their USB capability claims contradict each other.

### 1.2 Current requested port values are not implemented in the archive

The supplied version uses:

- XRDP TCP `3389`
- VNC TCP `5900`

The requested ports are:

- XRDP TCP `13389`
- VNC TCP `15900`

The old values are duplicated in multiple places, including the Bridge's `FIXED_PORTS`, the privileged controller's listener/status checks and generated VNC config, `xrdp.ini`, security policy JSON, tests, app connection details and docs. Update the complete contract atomically. Do not change only `xrdp.ini` and call it done.

### 1.3 Current VNC authentication mismatch — security-critical

The supplied controller `services/nuxel-remote-desktop/bin/nuxel-remote-desktop-ctl` generates a wayvnc config containing:

```ini
address=0.0.0.0
port=5900
enable_auth=false
```

But the Bridge currently describes VNC as authenticated/encrypted (`PAM_RSA_AES`, `encrypted: true`) and the example config/docs imply a secured VNC path. That is false status reporting. The owner must never be told VNC is protected by TLS/PAM while the live service has `enable_auth=false`.

Fix the live config, effective state inspection, Bridge payload, app UI, policy and tests together. A service is not READY for owner LAN use unless the effective daemon configuration and a real client handshake prove the negotiated authentication/encryption mode.

The current wayvnc upstream configuration documents `enable_auth`, certificate and private key paths, password authentication, optional PAM integration and an explicit `allow_broken_crypto` compatibility option. Do not enable weak DES/legacy crypto merely to make an old VNC client connect. If Jump Desktop cannot negotiate the modern security mode, document that client limitation and use an actually compatible secure client or supported mode. Do not disable authentication.

### 1.4 Existing XRDP configuration

The supplied `xrdp.ini` currently listens on `tcp://:3389`, enforces `security_layer=tls`, uses TLS 1.2/1.3, and references a device certificate/key. `sesman.ini` has an Xorg backend and session limits. The remote session launcher is a separate X11 session, not a physical Phoc mirror. The bridge currently checks service state and a port constant.

Audit current runtime config generation and the actual session identity before changes. Historical docs contain inconsistent references to `nuxel` and the retired `nuxel-remote` account. The current source tests assert a local `nuxel` identity in the PAM/session path. Verify the installed image rather than using old plaintext example credentials. Do not expose, copy, or log an old password that appears in historical docs.

### 1.5 Existing USB Tri-Link architecture

Relevant files include:

- `tools/beta/live/nuxel-usb-net.py`
- `tools/beta/live/nuxel_tri_link.py`
- `tools/beta/live/nuxel-live-ssh.py`
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh`
- `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh`
- `services/nuxel-bridge/src/tri_link_status.py`
- `services/nuxel-bridge/src/remote_desktop.py`
- `pwa/nuxel-apps/console-usb/`
- `pwa/nuxel-apps/console/console.js`
- `configs/nuxel/live-ssh.json`
- `configs/nuxel/security/remote-access.json`
- `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`
- `docs/beta-finalization/live/NUXEL-26000-TRI-LINK-REPORT.md`
- `docs/beta-finalization/live/NUXEL-28000-TRI-LINK-UI-REPORT.md`

The USB network helper currently implements CDC-NCM only. It snapshots configfs, adds NCM alongside ACM, rebinds the UDC, assigns `10.15.19.82/24`, starts/checks SSH and supports a confirmation timer/rollback. The host helper is Linux-specific and currently refuses to guess on macOS. The USB SSH app reports endpoint truth; the interactive terminal and file transfers are host-side Tri-Link CLI operations.

### 1.6 Existing NCM panic — do not repeat it

The real evidence is preserved under `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`. On kernel `4.14.253`, an NCM configfs function creation/cleanup sequence ended in a kernel panic during NCM function-instance teardown. The recorded stack includes:

```text
__list_del_entry_valid
misc_deregister
ncm_free_inst
usb_put_function_instance
ncm_attr_release
```

The watchdog rebooted the phone. The saved evidence says the post-reboot gadget was returned to ACM-only and WLAN SSH/serial came back. The helper therefore refuses NCM by default on this kernel.

**Do not run `nuxel-usb-net.py --apply`, do not use `--allow-unsafe-kernel`, do not manually create/remove `functions/ncm.*`, and do not use a test command that triggers NCM teardown on the user's only physical phone.** Remove or disable any user-facing unsafe override in production packaging. If needed, reproduce the bug on a separate test kernel/device or fix the kernel source and validate before the physical phone is touched.

The saved kernel config also indicates RNDIS gadget support is compiled (`CONFIG_USB_F_RNDIS=y`, `CONFIG_USB_CONFIGFS_RNDIS=y`). The supplied code's blanket `KNOWN_BAD_USB_KERNELS` policy and NCM-first preferred-mode selection do not distinguish the NCM-specific evidence from a potentially independent RNDIS path. Audit RNDIS carefully; do not assume it is safe just because it is compiled.

### 1.7 Current USB detection and host gaps

The supplied `nuxel_tri_link.usb_capability()` prefers NCM when NCM and RNDIS are both compiled. The USB helper creates only an NCM function. `tri_link_status.usb_status()` returns the known-kernel NCM panic status before distinguishing other possible gadget modes. `remote_desktop.usb_network_status()` also uses broad kernel-version blocking and reports network remote-desktop USB unavailable. The host helper `nuxel-usb-net-host.sh` handles Linux sysfs/IP commands but intentionally exits on Darwin; it is not a finished MacBook implementation.

The owner has historically used a MacBook Pro on Apple Silicon / macOS 15.7.x and Fedora 43 as a secondary development host. Verify the actual host at execution time; do not assume only Linux. For a Mac, investigate native CDC-NCM support and available reputable userspace RNDIS drivers (for example ReRNDIS/TetherKit) using their current official repositories and licenses. Do not silently install host drivers, weaken macOS security, disable SIP, or require unexplained third-party kernel extensions.

---

## 2. PHASE 0 — FULL-CODEBASE FORENSIC AUDIT (MANDATORY)

Do not edit files until this phase is complete and you have a dependency map.

### 2.1 Establish the actual checkout

Record:

- repository root, `VERSION`, branch, commit hash and dirty status;
- whether the source archive's version and tree are current;
- exact build target/device and kernel release/commit/config if available;
- current host OS/architecture and connected physical target availability;
- existing live SSH/serial access and the known-good recovery routes;
- whether the deployed phone image matches source config/build outputs.

Never overwrite unrelated uncommitted work. Preserve existing changes. If the checkout differs from v0.7.7-beta, map the newer implementation before editing.

### 2.2 Trace every remote-desktop code path

Create a dependency graph covering:

- PWA entry pages, manifests, app registry and Settings/Applications launch metadata;
- common `remote-desktop.js` UI and service-specific wrappers;
- Bridge namespace/API route, action dispatch, status schema and preferences;
- privileged fixed-argv controller, helper installation path and sudo policy;
- generated/static wayvnc, XRDP, PAM, sesman, Xorg and systemd files;
- image build/package dependencies, certificate/credential generation and account setup;
- firewall policy, allowed interface/CIDR logic and privacy indicator;
- tests, quickstart docs, release manifests and deployment manifest entries.

For every exposed UI button, identify exact RPC, validation, privileged command, expected state transition and proof of resulting daemon/listener state. Find dead branches, stale names, misleading comments and hard-coded defaults. Do not treat a static unit file or an installed binary as proof the live behavior works.

### 2.3 Trace the USB Tri-Link end to end

Map all of:

- kernel Kconfig options for ACM/NCM/RNDIS/ECM/ECM-subset/EEM and DWC3;
- current configfs gadget, UDC, current ACM function and its config symlink;
- USB VID/PID, descriptors, endpoint availability, interface names and host enumeration;
- phone-side `nuxel-usb-net.py` and its backup/rollback/timer paths;
- `nuxel_tri_link.py` capability selection and transport discovery;
- Bridge's `tri_link_status.usb_status()` and remote-desktop USB status;
- USB SSH console PWA and status schema;
- host-side USB network setup scripts and host address/routing logic;
- `nuxel-live-ssh.py`, `nuxel-live-ssh.sh`, transport config, pinned host-key, retries and file transfer;
- SSH daemon binding, user/group privileges, `AllowUsers`, `authorized_keys` and `CONFIG_ANDROID_PARANOID_NETWORK`/`inet` group requirements;
- deployment and rollback support, physical evidence and tests.

Find every occurrence of `3389`, `5900`, `usb0`, `ncm0`, `rndis0`, `NCM`, `RNDIS`, `USB SSH Console`, `NOT_APPLICABLE_NATIVE_NUXEL`, `scrcpy`, `remote-desktop`, and `tri-link`. Keep results grouped by component. Search rootfs builders, manifests, scripts, docs, tests, release workflows, examples and generated bundles.

### 2.4 Audit current runtime truth if the phone is reachable

Use read-only commands first. Collect:

- `uname -a`, kernel build ID, boot ID;
- `/proc/config.gz` or exact matching kernel config;
- `/sys/kernel/config/usb_gadget/nuxel/UDC`;
- current gadget function directories and config symlinks;
- `/sys/class/udc`, `/sys/class/tty/ttyGS0`, `/sys/class/net`;
- `ip -br link`, `ip -4 addr`, `ip route`, `ip rule`;
- `ss -ltnp` and `/proc/net/tcp` listener data;
- actual xrdp/wayvnc processes, units and effective configs;
- `systemctl cat/status` for remote-desktop and network units;
- Wayland runtime socket and advertised protocol list;
- wayvnc version and `wayvnc --help`/matching man page;
- xrdp/xorgxrdp versions and config validation;
- bridge JSON status and full sanitized logs;
- firewall status/rules on the device.

Do not print credentials, private keys, password hashes, tokens or full `authorized_keys` content into reports. Redact public host identity where not needed.

### 2.5 Baseline proof before change

Create a short baseline report or section in the execution notes containing:

- current direct RDP port/listener result;
- current VNC port/listener result and actual negotiated security type if a client is available;
- current Bridge status versus live daemon configuration;
- current GUI Tri-Link app labels/actions;
- current USB kernel modes compiled and currently instantiated;
- current USB phone/host interfaces and actual route;
- baseline serial console and WLAN SSH success;
- tests that pass/fail before modification.

No changes to USB configfs during the baseline audit.

---

## 3. SINGLE SOURCE OF TRUTH FOR REMOTE ACCESS CONFIGURATION

Consolidate remote-access settings so ports, interfaces, mode, security and enable state cannot silently diverge.

### 3.1 Canonical configuration

Use the existing canonical policy file `configs/nuxel/security/remote-access.json` unless the current tree already has a newer authoritative schema. Extend it in a versioned, backward-compatible way. Avoid storing the same port as a manually editable literal in a dozen files.

Required values:

```json
{
  "gui_remote_desktop": {
    "enabled": false,
    "services": {
      "xrdp": {
        "port": 13389,
        "protocol": "tcp",
        "bind_mode": "trusted-lan",
        "session": "separate-x11-session",
        "tls_required": true,
        "authentication": "pam"
      },
      "vnc": {
        "port": 15900,
        "protocol": "tcp",
        "bind_mode": "trusted-lan",
        "session": "current-wayland-session",
        "tls_required": true,
        "authentication": "pam-or-strong-server-password"
      }
    }
  }
}
```

This is an illustrative shape; follow the current schema conventions and avoid adding a duplicate root key if a current equivalent exists. The important immutable values are the requested ports and security defaults.

### 3.2 Configuration validation

At build/install/start time:

- validate port is an integer in the non-privileged range and not used by another service;
- reject duplicate RDP/VNC ports;
- validate protocol is TCP for the requested RDP and RFB listeners;
- validate exact bind mode and trusted interface policy;
- verify certificate/key ownership and permissions;
- fail closed on missing authentication material;
- reject unsupported authentication modes instead of silently downgrading;
- validate firewall allowance corresponds to the same port, service, interface and trusted source CIDRs;
- persist owner preferences separately from generated runtime state;
- write generated daemon configs atomically and preserve rollback copies.

### 3.3 No public Internet exposure

Direct LAN means the owner's local network, not the public Internet. Do not create router port forwarding, UPnP, NAT-PMP, public relay, cellular listener or cloud rendezvous.

Prefer binding explicitly to the current trusted WLAN IPv4 address if supported reliably, with safe reconfiguration on DHCP address changes. If wildcard binding is required, enforce source/interface firewall restrictions before service start and prove the listener is not reachable from `rmnet*`, arbitrary public interfaces, or untrusted LANs. If the device cannot enforce the required ingress boundary, fail closed rather than leaving a wildcard, remotely authenticated listener exposed to all interfaces.

Do not expose RDP/VNC by writing `0.0.0.0` and assuming this means “LAN only”. It means all IPv4 interfaces. The policy/firewall must enforce the intended reachability.

### 3.4 Service lifecycle

Keep all GUI remote access OFF by default and not enabled at boot. Explicit user action starts only the selected server. `stop-all` must stop both servers, terminate managed session children, close all relevant listeners and remove any on-demand firewall allowances. Do not kill Phoc or the framebuffer bridge.

Privacy indicator must reflect the actual live listener/client state, not stored preference. If the indicator cannot be shown, follow the current fail-closed rule and refuse to start remote access.

---

## 4. XRDP — DIRECT RDP ON TCP 13389

### 4.1 Server configuration

Update the complete XRDP path to use **TCP 13389**:

- `services/nuxel-remote-desktop/config/xrdp.ini`;
- rootfs installed `/etc/xrdp/xrdp.ini` generation/templating;
- any generated/default `xrdp.ini` snippets;
- privileged controller's expected listener port and return payload;
- Bridge fixed-port/status/connection-info data;
- firewall rule generator and remote-access policy;
- PWA UI, copy-connection details and QR/URI generation if present;
- tests, docs, sample connection profiles and deployment manifest.

Effective XRDP configuration must contain the correct bind/port form supported by the installed xrdp version. The upstream xrdp configuration documents `port` as the listening TCP port and `security_layer=tls` as TLS-only enhanced security. Retain TLS-only; do not use `security_layer=rdp` and do not silently use `negotiate` if TLS can be required.

Keep TLS 1.2/1.3 only where verified supported by the installed xrdp/OpenSSL build. Do not enable obsolete SSL/TLS versions or write TLS pre-master secrets.

### 4.2 Correct direct connection instructions

The UI and quickstart must show:

```text
RDP host: PHONE_LAN_IP
RDP port: 13389
Protocol: RDP over TCP
Tunnel: not required on the trusted LAN
Session: separate remote X11 desktop
```

Support standard clients by entering host and port separately or `PHONE_LAN_IP:13389`. If a URL scheme is displayed, label it convenience-only; don't rely on proprietary URI handler semantics. The Jump Desktop profile must use direct RDP to the phone IP and port 13389, not localhost, a tunnel, or a Connect host agent.

### 4.3 Session integrity

Retain the existing dedicated Xorg/XRDP session design, session limits, idle cleanup and restricted account policy. Confirm which account is canonical in current code and image. The account must not be root. Do not reintroduce the retired `nuxel-remote` user by mistake. Do not expose passwords in app registry, settings, clipboard URLs, QR codes, logs or reports.

Audit and correct any current mismatch among:

- `xrdp.ini` `autorun` target;
- `sesman.ini` Xorg session definition;
- installed xorgxrdp module/config;
- `nuxel-xrdp-session` launcher;
- PAM auth/account policy;
- generated unique password/certificate provisioning;
- `nuxel-remote-desktop-ctl` start/stop cleanup;
- app's label and remote session description.

Do not run the XRDP session as root. Keep it separate from the physical Phoc session. It must not own `/dev/fb0`, the physical Wayland socket, display bridge or compositor process.

### 4.4 Start and health verification

A successful start requires all of:

1. required XRDP/Xorg dependencies installed;
2. effective config validates;
3. required certificate/key exists, matches, has correct owner/mode and is readable by xrdp;
4. sesman starts before xrdp where required;
5. both expected systemd units active;
6. exactly the expected TCP 13389 listener is open on the intended bind address;
7. TLS handshake is successful and uses approved protocol/cipher;
8. a client reaches the login prompt directly over Wi-Fi LAN;
9. PAM login succeeds with the canonical owner account;
10. Xorg session starts and displays the Nuxel remote desktop launcher;
11. keyboard/mouse and disconnect/reconnect work;
12. stop closes listener and cleans only XRDP child/session processes.

A listening socket alone is not an end-to-end PASS.

### 4.5 Error handling

Expose exact states such as `OFF`, `STARTING`, `WAITING_FOR_CLIENT`, `CONNECTED`, `STOPPING`, `ERROR`, `UNSUPPORTED`, with `last_error` sanitized. Distinguish package missing, certificate error, sesman startup failure, listener bind failure, TLS handshake failure, PAM rejection, Xorg backend failure and session launcher failure.

Never return READY when xrdp.service is active but sesman is not; never check 3389 after migrating to 13389.

---

## 5. VNC — DIRECT WAYLAND SCREEN SHARING ON TCP 15900

### 5.1 Correct listener port

Use **TCP 15900** across:

- canonical security policy;
- wayvnc generated configuration and shipped example;
- systemd command/config arguments;
- controller port checks and start timeout errors;
- Bridge `FIXED_PORTS`, status, listener inspection and connection-info;
- firewall policy;
- GUI PWA status/connection detail and copy buttons;
- docs, tests and host profiles.

There must not be a hidden fallback to 5900. The app must show the actual listener port from authoritative runtime status.

### 5.2 Secure authentication is mandatory

The current generated config `enable_auth=false` is not acceptable on a direct LAN listener. Implement a supported secure wayvnc authentication mode for the installed wayvnc release. Prefer PAM-backed account authentication if verified in that exact release; otherwise use a strong individually provisioned VNC password protected from disclosure and stored only in a root-owned secret file/config mechanism supported by wayvnc.

Enable TLS using generated certificate and private key paths with restricted permissions. If the installed wayvnc requires `certificate_file`, `private_key_file`, `username` and `password` when auth is enabled, obey the actual version's syntax. If using `enable_pam=true`, verify its exact interaction with configured username/password and PAM module. Do not assume `enable_pam` works the same in all releases.

Do not enable `allow_broken_crypto`, DES, legacy unauthenticated security type, empty password or “relax encryption” merely to accommodate an older client. Do not keep a plaintext/no-auth escape hatch on `0.0.0.0`.

### 5.3 Jump Desktop and client compatibility

The archived quickstart states Jump Desktop 9.1.21 on macOS 15.7.9 and reports that the tested version could not negotiate the then-configured wayvnc 0.9.1 RSA-AES/VeNCrypt mode. Re-test with the actual current Jump Desktop version and actual installed wayvnc version; do not assume the old limitation still applies.

Test the complete RFB negotiation including security-type list, TLS certificate validation, PAM/password authentication and input channels. If Jump Desktop still cannot negotiate the secure server mode:

- keep the VNC service secure;
- document the incompatible client version and exact server security type;
- verify a different secure Mac VNC client that supports the implemented security type;
- give the owner direct `PHONE_LAN_IP:15900` instructions for that client;
- do not turn off VNC authentication/encryption to preserve Jump compatibility.

Do not require an SSH tunnel for the desired LAN path. A tunnel may remain documented as an optional fallback for administration, but it is not the primary direct-LAN method.

### 5.4 Preserve real Phoc session capture

The wayvnc service must attach to the existing active Phoc/Wayland session. Verify:

- `XDG_RUNTIME_DIR` and `WAYLAND_DISPLAY` point to the actual Nuxel Wayland socket;
- server process has the minimum required access to the socket;
- the socket is alive and belongs to the active compositor;
- Phoc advertises all required screencopy, virtual pointer and virtual keyboard protocols for the installed wayvnc build;
- remote client sees the real physical Nuxel desktop, not a separate blank compositor/X session;
- remote input is delivered only through supported virtual-input protocols;
- locked phone exposes only the lockscreen and remote input cannot bypass local unlock;
- screen-off/lock state follows Nuxel privacy policy;
- multiple clients are limited according to policy;
- disconnect releases client state/input devices.

The existing service uses `wayvnc -f 20 -r`; verify every flag against the installed version rather than changing flags by assumption. `-r` is render-cursor on current upstream wayvnc; `--disable-input` is the separate input-disable flag. Preserve pointer/keyboard input if the owner requests remote control, but don't accidentally launch with input disabled or assume `-r` means read-only.

### 5.5 Performance and resolution

Measure actual capture latency, frame rate, CPU/GPU load and resolution on the S10+. Set a sensible default frame rate and quality for a phone display and Wi-Fi LAN. Do not claim GPU acceleration simply because the wayvnc binary accepts `-g`; verify the buffer and capture path. Avoid damaging compositor smoothness. If GPU capture is not supported by this vendor Phoc/wlroots build, report it and use the stable supported capture path.

### 5.6 Status must mirror effective security

Bridge fields must be derived from active process/config/handshake facts. E.g. do not hardcode `authentication=PAM_RSA_AES` if effective config has `enable_auth=false`. Add explicit fields:

- `authentication_mode`;
- `encrypted` and `encryption_mode`;
- `certificate_fingerprint`;
- `listener_address`, `port`, `protocol`;
- `listener_verified`;
- `authenticated_clients` and client-query availability;
- `input_enabled`;
- `wayland_protocols_ok`;
- `privacy_gate_ok`;
- `security_verified`.

If you cannot inspect a fact, report `unknown`/`unverified`; never infer secure from package presence or desired config.

---

## 6. DIRECT LAN FIREWALL / INTERFACE POLICY

Direct LAN exposure must be explicitly narrow and testable.

1. Add TCP 13389 and TCP 15900 to the Nuxel firewall's canonical application/remote-access policy only when the owner starts the corresponding service.
2. Scope ingress to the current trusted WLAN interface and trusted LAN source CIDR(s). Support DHCP changes through dynamic discovery/config update. Do not hardcode historical `192.168.178.167` or `192.168.44.77` addresses.
3. Do not permit `rmnet*`, mobile/cellular, WAN/public ingress, tethered guests, arbitrary VPN routes or other interfaces by default. ZeroTier support must be explicitly configured and distinct from LAN.
4. If a firewall daemon/engine is not installed or not active, use a proven interface-specific bind strategy if possible. Otherwise refuse wildcard exposure and clearly report the blocker. Never rely only on an undocumented host/router assumption.
5. `stop` removes the exact dynamic firewall rule associated with that service; it must not flush the user's firewall, clear unrelated rules, or change the default policy.
6. `stop-all` stops both, confirms listeners closed and verifies temporary rule removal.
7. Test connection allowed from the owner LAN and rejected from an untrusted interface/source when a test fixture or physical second network is available.
8. Never expose RDP/VNC via public router forwarding, UPnP or NAT-PMP.

Keep GUI remote access OFF by default and never start it on boot.

---

## 7. GUI TRI-LINK — FIX THE SCRCPY / NATIVE MIRROR EXPERIENCE HONESTLY

### 7.1 Protocol reality

Official scrcpy mirrors and controls Android devices through ADB. Its server implementation is Android-specific; the official project description explicitly defines Android as the target. Native Nuxel is Fedora/Linux with Phoc/Wayland and is not an Android device. It does not provide Android `app_process`, SurfaceFlinger or Android's scrcpy server runtime merely because ADB tools are installed.

Therefore:

- Do not generate a fake ADB device record for Nuxel.
- Do not make an `adb devices` output line claim the running Nuxel handset is Android.
- Do not implement a “scrcpy server” by copying private protocol fragments and labelling the result official scrcpy.
- Do not report `READY` for scrcpy when there is no Android ADB target or no official host binary.

### 7.2 The third GUI option must still be useful

Audit what the owner expects from the third GUI Tri-Link option. Preserve genuine Android-device scrcpy functionality (USB ADB or Android TCP/IP) where a real Android target exists. But make the native Nuxel route first-class and useful:

**Recommended user-facing contract:** the third app becomes a combined **Screen Mirror** surface with two clearly separated modes:

- **Native Nuxel screen:** opens/controls the current Phoc session through the secure native screen-sharing backend (wayvnc on TCP 15900), with actual phone IP, port, client compatibility, authentication status and copyable connection details. It must not show `NOT_APPLICABLE_NATIVE_NUXEL` as the only outcome while offering no useful native mirror route.
- **Android device (scrcpy):** shows real ADB targets and starts official scrcpy only when an actual Android target is attached/authorized and a compatible scrcpy binary exists on the host where it is supposed to run.

You may either:
1. rename the current scrcpy app and identity to a less confusing Screen Mirror application while preserving an Android scrcpy sub-mode; or
2. retain the scrcpy-branded application but make its native Nuxel section clearly launch the secure native mirror path and label Android-only scrcpy separately.

Choose the cleanest registry-compatible route after inspecting installed app IDs and external links. Do not leave duplicate app entries or break saved launcher state.

### 7.3 Optional low-latency Nuxel Mirror (only if VNC does not meet the user's requirement)

If the existing VNC viewer experience does not meet the desired latency/quality/control requirements, evaluate a separately named **Nuxel Mirror** protocol/client. Do not claim compatibility with official scrcpy. Investigate the current Phoc/wlroots capture path, PipeWire/DMABUF support, hardware H.264 encoder/decoder availability, libavcodec/gstreamer/VA-API alternatives on Exynos 9820/Mali and a practical macOS client.

Implement only if there is a complete, supportable client-server path. It must include authenticated encrypted transport, pairing/trust, user confirmation, lockscreen privacy, input event routing, disconnect cleanup, performance measurements and a Mac client install/launch experience. Prefer mature protocol components over a large bespoke transport. If no viable hardware encode path exists, provide a measured software fallback and state the cost. Do not spend this mission inventing a proprietary scrcpy clone without proving it is technically achievable.

### 7.4 Android scrcpy integration requirements

For Android targets:

- detect ADB targets and their states (`device`, `unauthorized`, `offline`, absent);
- show model/device/serial safely, without exposing private debugging secrets;
- support USB ADB and TCP/IP pairing/connection as official scrcpy supports;
- keep pairing codes ephemeral and never log/store them;
- check official scrcpy binary/version on the actual host OS/architecture;
- invoke with argv (never shell string from PWA data);
- stop the exact child process on stop/close;
- distinguish host-side scrcpy client requirement from phone-side Nuxel provider;
- report target absent/unauthorized/client missing distinctly;
- do not auto-install ADB/scrcpy or grant Android debugging authorization.

If native Nuxel is the only target, guide the owner to the Native Nuxel Screen Mirror option and show its direct host:port connection details.

---

## 8. USB NETWORKING — THIRD CONSOLE / TRI-LINK CLI

This is a first-class implementation target. The goal is a reliable **USB network interface between the Nuxel handset and a connected development host**, allowing the existing SSH Tri-Link CLI (`--transport usb`) and optionally file transfer/deploy operations to work. This task is not the same as general USB Internet tethering; keep those feature boundaries clear.

### 8.1 Preserve the three console semantics

The three console entries remain separate:

1. **Serial Live Console:** USB CDC-ACM recovery console, independent, preserved.
2. **Wi-Fi SSH Console:** key-only WLAN SSH, unchanged and working.
3. **USB SSH Console:** SSH over a real USB Ethernet gadget interface, not serial-over-TCP and not a simulated interface.

Phone PWA cards remain phone-side status/control information; interactive CLI/file-transfer sessions run on the development host using the existing Tri-Link host tool. Do not move private SSH keys onto the phone.

### 8.2 Per-mode capability analysis

Add mode-specific capability evaluation rather than a single global kernel block:

- NCM;
- RNDIS;
- ECM;
- ECM-subset;
- EEM if there is a real host driver and reason to support it.

Read exact kernel config and inspect current device-tree/UDC/DWC3 driver, configfs function implementation and teardown code for the exact 4.14.253-derived kernel. Read the full vendor source for NCM and RNDIS functions (`f_ncm.c`, `f_rndis.c`, configfs integration, `u_ether.c`, `composite.c`, DWC3 glue). Investigate the exact observed `misc_deregister` lifecycle and whether a similar teardown bug exists in RNDIS. Confirm the function release/cleanup path is safe in the vendor kernel, not just upstream current mainline.

The saved kernel evidence indicates:

- NCM gadget function compiled and configfs NCM enabled;
- RNDIS gadget function and configfs RNDIS enabled;
- ECM was not compiled in the historical evidence;
- the gadget currently exposes only ACM serial;
- the exact NCM teardown path previously panicked the phone.

Re-read live config and don't assume these options remain the same. `CONFIG_* = y` proves compile-time availability only; it does not prove runtime creation, safe teardown, host driver support, or a working SSH transport.

### 8.3 Select the best practical mode

Evaluate modes against these priorities:

1. keep CDC-ACM serial available during normal use and after disconnect/failure;
2. do not trigger the recorded NCM panic;
3. support the owner's actual MacBook Pro M1/macOS 15.7.x host, preferably without SIP reduction or unsafe third-party kernel extension;
4. also support Fedora/Linux development hosts where available;
5. stable enumeration/reconnection on cable reconnect;
6. low friction for existing Tri-Link CLI;
7. no default-route or Wi-Fi changes on either side.

Potential paths to investigate:

- **RNDIS composite gadget + Mac host userspace driver:** RNDIS is compiled in the historical kernel. Current macOS may not ship a built-in RNDIS network driver. Evaluate maintained userspace implementations such as ReRNDIS/TetherKit for macOS Apple Silicon and their exact release/license/system requirements. Do not install without owner approval and a documented uninstall path. Do not require SIP disabled.
- **NCM fixed in the kernel:** Linux/macOS have native NCM support, but Nuxel's NCM teardown bug must be fixed and validated in the exact kernel before deployment. Treat this as a possible long-term preferred mode only after safe test proof.
- **ECM:** compile/configure only if the exact kernel and DWC3 platform support it and host compatibility is proven. Historical config indicated it was absent; don't assume it can be enabled by changing a JSON flag.

No blind fallback from NCM to RNDIS at runtime. Choose a proven mode explicitly and report its identity. If RNDIS teardown is not proven safe, keep USB networking blocked and generate `REPORT-USBNET.md` with the specific required kernel work.

### 8.4 Never repeat the NCM panic on the only physical phone

Remove the production `--allow-unsafe-kernel` escape hatch or ensure it cannot be used through app/normal host CLI. The helper must refuse NCM on every build known to contain the bug. Version matching must be robust to suffixes such as `4.14.253-gf7194c1d15ed-dirty`.

Only use physical phone testing when all conditions are true:

- source audit of selected function create/bind/unbind/release paths is complete;
- dedicated test plan and recovery path exist;
- current serial and WLAN SSH are verified immediately before test;
- a remote rollback watchdog is armed and independently tested;
- ACM function and its config symlink are snapshotted;
- only the selected network function is changed;
- exact UDC transition/re-enumeration sequence is reviewed;
- a known-good boot/recovery image is available;
- owner-facing confirmation step is required;
- rollback can restore ACM and UDC state even when host USB interface disappears.

The rollback watchdog must not be the only recovery mechanism if the kernel panics and never schedules the timer. Keep WLAN SSH alive and preserve pstore/ramoops evidence. Prefer a separate test phone or lab board for first physical RNDIS/NCM function tests.

### 8.5 Refactor the device-side USB networking helper

Refactor `tools/beta/live/nuxel-usb-net.py` from NCM-only logic into a mode-aware, testable backend. Requirements:

- `--status --json`: strictly read-only; enumerate exact compiled modes, active functions, configfs links, UDC, interface names, IP/route state, kernel release, last transaction and health.
- `--preflight [--mode auto|rndis|ncm|ecm]`: read-only and shows the exact plan, expected re-enumeration, address plan, host requirement and risk.
- `--apply --mode <mode>`: only allowed after capability and safety gates; never accepts arbitrary configfs paths, function names, IPs, or executable strings from an untrusted caller.
- `--confirm`: only after host has a working network interface and a successful authenticated SSH command has completed.
- `--rollback`: restore exact original configfs state, ACM symlinks, UDC binding, device-side IP and routes; only remove function instances created by this transaction.
- `--timer`: bounded rollback service/process with durable status and ownership.
- `--diagnose`: gather read-only logs, USB identities, network interface, route, SSH listener and host compatibility hints.

Transaction record must store:

- selected mode;
- original UDC state;
- pre-existing function list and symlink targets;
- new function name and whether it was created by this transaction;
- original and assigned network addresses/routes;
- start time, rollback deadline, timer owner and confirmation state;
- current boot ID and transaction ID;
- all changed files and rollback checksums.

Before cleanup, verify no other process uses the network interface/function and never remove ACM. Do not remove a pre-existing RNDIS/NCM function that was not created by this transaction. Do not unbind/rebind UDC unless required and explicitly approved by the safe plan.

### 8.6 IP addressing and routing

Retain the current private USB point-to-point subnet only if the audit confirms it does not collide with the owner's LAN/VPN. Current repository values include device `10.15.19.82/24` and host `10.15.19.1/24`; these must be configurable through a validated canonical config and checked for conflicts.

Requirements:

- do not add a default route on the phone or host;
- add only the USB-link subnet route;
- no NAT, Internet forwarding, DHCP server or DNS proxy unless separately requested;
- no changes to `wlan0` or cellular modem route;
- detect overlap with current route table, WireGuard/ZeroTier/VPN and LAN CIDRs;
- refuse and report conflict rather than changing the user's network;
- confirm ARP/neighbor reachability and route selection.

### 8.7 Host-side support: macOS and Linux

The existing `scripts/s10plus-debug-pack/nuxel-usb-net-host.sh` is Linux-specific and refuses Darwin. Replace or extend it with tested host adapters.

**Linux adapter:** use system discovery by USB VID/PID and associated interface; verify driver/module, add only the USB interface IP, bring only that interface up, never change default route; support idempotent apply/remove/status; ensure the host interface matches Nuxel's connected USB gadget.

**macOS adapter:** use supported system tools and documented host driver integration. Detect the connected USB device and network interface via `system_profiler`, `ioreg`, `ifconfig`/network interface state and driver-specific APIs where available. If RNDIS requires a third-party userspace driver, detect its presence/version and give exact install/check/uninstall instructions, but do not silently install it. If using NCM, verify the actual macOS release recognises the device natively. Don't pretend `networksetup -listallhardwareports` or a sysfs lookup alone proves the RNDIS/NCM data plane is available.

The host CLI must:

- support `--status`, `--discover`, `--preflight`, `--apply`, `--remove`, `--diagnose`, `--json`;
- print the detected interface and mode;
- configure a point-to-point or isolated USB subnet without touching the default route;
- be repeatable/idempotent;
- remove only the state it created;
- fail clearly on missing drivers, permissions, missing USB gadget, wrong VID/PID or unsupported OS;
- not change Wi-Fi, VPN, DNS or default gateway;
- avoid relying on root except for the specific interface configuration step;
- ship with a dry-run/preflight that makes no changes.

Keep host platform-specific code modular; don't duplicate a whole second Tri-Link CLI. The existing common CLI should invoke the appropriate host adapter.

### 8.8 Fix the USB SSH Tri-Link CLI end to end

Review and improve:

- `tools/beta/live/nuxel_tri_link.py`;
- `tools/beta/live/nuxel-live-ssh.py`;
- `scripts/s10plus-debug-pack/nuxel-live-ssh.sh`;
- host USB helper;
- `configs/nuxel/live-ssh.json`;
- USB app's Bridge status.

Expected usage remains explicit and predictable, e.g.:

```bash
# Read-only discovery/status
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport auto --discover
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport usb --status

# Once USB network is physically available and host route is ready
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport usb --host 10.15.19.82 --status
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport usb --host 10.15.19.82 --shell
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh --transport usb --host 10.15.19.82 --exec 'uname -a'
```

Actual CLI flags must follow current existing interface. Keep key-only SSH and pinned host-key verification. Do not accept changed host keys automatically. Preserve existing exit-code semantics and deployment lock. `--transport auto` may select only a fully preflighted available transport and must never silently fall back after an explicit USB transport was selected.

The CLI must verify the selected host interface/route is actually associated with the phone's USB device. Do not connect to a different machine that happens to have `10.15.19.82`. Preserve the stable host-key alias and never weaken `StrictHostKeyChecking` to get a connection.

### 8.9 USB remote desktop transport

Only after USB SSH has independently passed the full physical test may the GUI VNC/RDP provider list USB as an available transport. Bind the servers to the USB interface/address or exact trusted interface as appropriate; update firewall rules; ensure VNC's 15900 and XRDP's 13389 are reachable over the USB link. Do not let GUI Tri-Link offer a USB button merely because the network helper reports kernel support.

---

## 9. BRIDGE/API STATUS CONTRACT — ONE TRUTHFUL MODEL

### 9.1 Remote desktop status schema

Keep `system.remote-desktop` as the single GUI remote-access API unless the current code has already migrated. Version the schema when adding fields. All UI fields must derive from the same provider and authoritative canonical policy.

Every service status must distinguish:

- installed / version;
- supported / unavailable / blocked / off;
- desired transport vs active transport;
- configured bind address vs actual listener address;
- configured port vs actual listener port;
- listener process owner/PID and unit state;
- actual TLS/encryption and auth mode;
- session mode;
- client count/connection state;
- security verification status;
- privacy indicator state;
- exact sanitized reason/error;
- USB mode-specific status if relevant.

Do not report authenticated clients as `0` when `wayvncctl` is unavailable; distinguish `0` from `unknown`/unavailable.

### 9.2 USB status schema

USB status must include a per-mode table, e.g.:

```json
{
  "status": "SUPPORTED_NOT_ENABLED",
  "kernel_release": "...",
  "selected_mode": null,
  "modes": {
    "ncm": {"compiled": true, "safe_on_current_kernel": false, "status": "BLOCKED_KNOWN_PANIC"},
    "rndis": {"compiled": true, "safe_on_current_kernel": "UNVERIFIED", "host_driver": "...", "status": "NEEDS_VALIDATION"},
    "ecm": {"compiled": false, "status": "BLOCKED_KERNEL"}
  },
  "acm_preserved": true,
  "gadget_network_function": null,
  "device_interface": null,
  "host_interface": null,
  "device_ip": null,
  "host_ip": null,
  "ssh_listener": false,
  "ssh_authenticated_probe": false,
  "mutated": false
}
```

This is an example, not a mandate to use identical property names. The key is distinguishing mode-specific known bug vs general kernel inability. RNDIS may not be marked READY while unverified. NCM's historic panic should not be silently relabelled as safe simply because RNDIS exists.

### 9.3 Keep the providers consistent

`system.tri-link`, `system.remote-desktop`, the USB console PWA, GUI remote desktop apps, status bar, host CLI and docs must all agree about:

- kernel release;
- current USB mode;
- host/device interface readiness;
- direct LAN port numbers;
- whether USB transport is currently unavailable/available;
- authentication and encryption.

Avoid duplicated code that has its own hardcoded status policy. Factor common read-only capability and USB status where reasonable, but preserve clean module ownership. Use a tested shared contract rather than circular imports.

---

## 10. PRIVILEGED CONTROLLER / SYSTEMD / DEPLOYMENT

### 10.1 Fixed argv and narrow privilege

Retain the existing allow-listed privileged helper pattern. Never accept shell command, executable path, config path, port or arbitrary interface from PWA caller input. Validate actions, service and transport against a strict enum. Invoke child processes with argument arrays, bounded timeouts and no `shell=True`.

The helper may load canonical configuration itself and derive fixed listener/port settings. PWA callers may request only safe actions such as status/start/stop/stop-all/set-preferred-transport/connection-info. They may not upload executable config or certificates.

### 10.2 Start order and readiness

For VNC:

- require active Nuxel Wayland session and correct socket;
- verify required protocols;
- generate/validate secure config and secret/certificate permissions;
- install precise LAN firewall allowance;
- start service and verify actual listener on TCP 15900;
- verify effective auth/security settings;
- then publish READY and privacy indicator.

For XRDP:

- validate packages, PAM, Xorg backend and certificate;
- add precise LAN firewall allowance;
- start sesman then xrdp in the sequence appropriate to the image;
- verify actual listener on TCP 13389 and TLS;
- publish WAITING_FOR_CLIENT/READY only after effective checks.

If any step fails, stop only that service and remove the temporary rule. Preserve other remote-access and console services.

### 10.3 Stop order

Stop accepting new clients, stop daemon, terminate managed XRDP sessions and helper children, close listener, remove temporary firewall allowance, remove generated transient state, update privacy state and report final status. Do not indiscriminately `pkill` shared Xorg or desktop processes. Never kill Phoc, the physical X/Wayland session, `nuxel-wl-fb`, SSHD or serial console supervisor.

### 10.4 Boot behavior

No remote desktop listener starts automatically after reboot unless a distinct user-approved future policy exists. Reboot should always return to OFF. USB gadget should default to the current safe ACM-only recovery composition unless a separately accepted/persisted USB networking mode has a safe and tested setup path. Do not enable a mode just because the user selected it in the past if the current kernel release is known unsafe.

### 10.5 Packaging and image build

Audit and update rootfs builder/package definitions, systemd file installation, `sudoers` allowlist, SELinux policy/workarounds, user/group creation, certificates, firewall package dependencies, Bridge installation and deployment manifest. Ensure all resources exist at the paths referenced at runtime.

Do not weaken system policy to make remote desktop run. Keep existing Nuxel boot hardening. If a new package changes SELinux state or boot service dependencies, test full boot, not only the feature in an already-running session.

---

## 11. UI/UX REQUIREMENTS

### 11.1 XRDP app

Show:

- title `XRDP Remote Desktop`;
- clear label `Separate remote X11 session`;
- state and exact reason;
- detected current LAN IPv4 and interface;
- `RDP port 13389/TCP`;
- direct connection string `PHONE_LAN_IP:13389`;
- TLS status/fingerprint;
- auth method and login account label (never password);
- Start / Stop / Recheck / Stop All;
- copy host:port / copy full instructions;
- selected/active transport and USB state only when meaningful.

If the service is OFF, the port number is a configuration value, not an open listener. Visually distinguish `configured` from `listening`. Do not show a live green dot when no socket exists.

### 11.2 VNC app

Show:

- title `VNC Screen Sharing`;
- clear label `Mirrors the actual Phoc/Wayland screen`;
- exact current LAN IPv4 and interface;
- `VNC port 15900/TCP`;
- direct connection string `PHONE_LAN_IP:15900`;
- actual negotiated security/auth mode and certificate fingerprint;
- whether remote keyboard/mouse control is enabled;
- required Wayland protocols and privacy lock state;
- client count when available;
- Start / Stop / Recheck / Stop All;
- secure-client compatibility note only when needed.

### 11.3 Native mirror / scrcpy surface

Clearly distinguish Android scrcpy from native Nuxel screen sharing. If native Nuxel is the current device, provide a direct actionable entry to VNC/Native Screen Mirror and display the correct 15900 LAN endpoint. Do not show “scrcpy ready” unless an actual Android ADB target and host binary are verified.

### 11.4 USB SSH Console

Display:

- kernel version;
- selected USB networking mode;
- per-mode compile/safety status;
- whether ACM serial remains present;
- gadget function list;
- device-side interface/IP;
- host-side interface/IP when reported by host CLI;
- SSH listener and authenticated probe status;
- exact safe next command;
- blocker link to `REPORT-USBNET.md` when blocked.

No Start/Apply button should be available on known-unsafe NCM. If RNDIS is only source-reviewed but not yet physically proven, display `NEEDS VALIDATION`, not `READY`.

### 11.5 Registry and installed app identity

If changing the scrcpy app name or converting it into a Screen Mirror app:

- update app registry, native registry, PWA app.json, manifest, app icon metadata, app service IDs, routes, launcher's cache/version key and tests consistently;
- preserve backward compatibility with existing user app state/favourites/desktop positions;
- avoid duplicate registry IDs;
- update uninstall/upgrade migration and app registry version only according to current schema policy;
- keep all three serial/Wi-Fi/USB console IDs intact.

---

## 12. TESTING — OFFLINE, INTEGRATION, LIVE AND PHYSICAL

Do not mark the mission complete based only on static grep assertions. Add real tests and report exact commands/results.

### 12.1 Remote-desktop unit tests

Test at minimum:

- canonical ports are exactly XRDP 13389 and VNC 15900;
- no active status/connection-info returns old 3389/5900;
- controller listener probes use the canonical values;
- xrdp.ini and generated config use 13389;
- generated wayvnc config uses 15900 and has auth/encryption enabled;
- missing VNC TLS cert/key/auth secret refuses service start;
- no `enable_auth=false` production config;
- no `allow_broken_crypto=true`;
- Bridge reports effective auth/encryption rather than hardcoded claims;
- no password/private key/secret in status/API payloads/logs;
- connection info is direct LAN and does not produce tunnel commands;
- dynamic address is discovered, not hardcoded;
- rmnet/untrusted-interface exposure blocked;
- service start/stop/stop-all state and rollback paths;
- listener false-positive tests (`ss` unavailable, IPv6 listener, wrong port, stale PID);
- XRDP session cleanup never targets Phoc/framebuffer processes;
- VNC Wayland socket/protocol missing => UNSUPPORTED/ERROR, not READY;
- lockscreen privacy enforcement;
- start button only available in valid states.

### 12.2 Real RDP integration tests

On device or an equivalent integration image:

- `ss -ltnp` shows TCP 13389 on intended interface;
- TCP 3389 is not listening due to this service;
- host reaches TCP 13389 directly over LAN without SSH process/tunnel;
- TLS handshake negotiated approved protocol;
- RDP client completes login to expected account;
- Xorg session exists with expected UID/session metadata;
- remote keyboard/mouse works;
- remote desktop content is shown;
- disconnect/reconnect and stop works;
- unauthorized account/root is rejected;
- 13389 closes on stop and firewall allowance removed.

### 12.3 Real VNC integration tests

- actual active Phoc display is captured;
- listener is TCP 15900;
- TCP 5900 is not the active service listener;
- direct LAN RFB handshake reaches secure authentication;
- certificate validation/identity is correct;
- unauthenticated connection fails;
- failed login fails;
- authenticated allowed client sees live phone screen, not a stale screenshot;
- remote pointer and keyboard work only if policy says enabled;
- remote lockscreen cannot bypass the phone lock;
- stop closes listener and client sessions;
- capture load/frame pacing is measured.

### 12.4 Client compatibility testing

For Jump Desktop on the owner's Mac, record exact macOS version, Jump version, protocol settings, security type and error details. Use direct address/port (not localhost). Prove whether it supports the configured RDP TLS and wayvnc VNC security mechanism.

If Jump's VNC security is incompatible, perform a test with a compatible secure VNC client, record the result and update docs accordingly. Do not drop server security to make the old client happy.

### 12.5 USB networking unit tests

Add a mode matrix and fake configfs tests. Include:

- NCM known-bad release always blocked by mode-specific safety gate;
- robust version parsing for `4.14.253-g...-dirty`;
- RNDIS compile options detected independently of NCM;
- ECM/ECM-subset detection correct;
- NCM panic does not incorrectly prove RNDIS safe;
- RNDIS unverified does not report READY;
- only active, tested mode may be selected;
- ACM function directory and symlink remain untouched across apply/rollback;
- no mutation in `status` or `preflight`;
- transaction snapshot and rollback restore exact UDC, function list, symlink targets and IP state;
- rollback never removes pre-existing function not owned by transaction;
- no default route changes;
- subnet overlap refusal;
- host interface must match VID/PID or verified Mac USB device;
- host missing driver reports BLOCKED_HOST_DRIVER;
- host IP idempotence and cleanup;
- device interface without SSH listener is not AVAILABLE;
- SSH listener without actual host interface is not AVAILABLE;
- network route without successful key-authenticated SSH probe is at most `LINK_UP_UNVERIFIED`;
- explicit USB CLI never silently falls back to WLAN/serial;
- auto mode selects only fully AVAILABLE path;
- host key mismatch, auth failure, wrong host, route conflict and cable removal have correct error categories;
- serial recovery checks pass before and after test fixture apply/rollback.

### 12.6 USB physical acceptance criteria

A physical USB-network PASS requires all of:

1. Nuxel phone USB gadget enumerates the expected network interface on the owner's actual host.
2. CDC-ACM serial is still present after enumeration and accessible after disconnect/reconnect.
3. Host and device interface IPs/routes are correct, with no default route changed.
4. Phone can be discovered by correct USB VID/PID/mode.
5. `ping`/ARP or equivalent local link test works.
6. SSH TCP 22 is reachable over USB IP.
7. strict pinned host-key authentication works.
8. `--transport usb --exec 'uname -a'` executes and returns the expected kernel string/exit code.
9. upload/download with SHA-256 verification works over USB.
10. file deployment lock/reconnect behavior remains intact.
11. cable disconnect/reconnect restores correct status without manual cleanup.
12. rollback and serial recovery succeed.
13. phone reboots and returns to safe default gadget state without stale or half-created network functions.

If physical host access is not available, do not claim physical PASS. Report offline tests separately and create the blocker report.

### 12.7 Existing regression suite

Run relevant tests before and after. Discover current Makefile gates, Python unit suites and static checks. At minimum inspect/run:

- `tests/a80/test_remote_desktop.py`;
- `tests/a80/test_tri_link_status.py`;
- `tests/a80/test_tri_link_api.py`;
- `tests/a80/test_tri_link_console.py`;
- `tools/beta/live/tests/test_tri_link.py`;
- bridge tests for remote desktop and API routes;
- rootfs image builder/manifest coverage;
- JavaScript/registry tests;
- full relevant `make` quality gate if feasible.

Do not delete or weaken a failing test to manufacture a pass. If baseline failures exist, identify them separately with before/after comparison.

---

## 13. DOCUMENTATION AND REQUIRED REPORT

### 13.1 Update existing user documentation

Update at least:

- `GUI-TRI-LINK-QUICKSTART.md`;
- `TRI-LINK-QUICKSTART.md`;
- remote-desktop service README/package docs if present;
- release notes/changelog;
- app UI inline help and error copy;
- security policy docs;
- any host setup instructions for Mac and Fedora.

Remove obsolete connection examples for port 3389/5900 and stale IP addresses. Clearly document:

```text
XRDP: PHONE_LAN_IP:13389 (TCP, direct LAN, TLS + PAM)
VNC:  PHONE_LAN_IP:15900 (TCP, direct LAN, TLS + authenticated access)
```

State VNC mirrors active Phoc; XRDP is a separate X11 session. Neither requires an SSH tunnel on the trusted LAN. Do not imply either may be safely exposed to the public Internet.

### 13.2 `./REPORT-USBNET.md` is mandatory

Create or replace `./REPORT-USBNET.md` in the repository root. It must be an evidence-based engineering report, not a generic plan. Include:

1. **Executive verdict:** WORKING / PARTIAL / BLOCKED / NOT TESTED.
2. **Exact target:** device, kernel release/commit, host OS/version/architecture, USB controller/UDC and test date.
3. **Current architecture:** serial ACM, USB network gadget mode, host driver, IP path and SSH CLI.
4. **Kernel capability matrix:** ACM/NCM/RNDIS/ECM/ECM-subset/EEM compile status and relevant runtime function support.
5. **NCM panic evidence:** precise source references, saved pstore trace, why current behavior is blocked and explicit statement that the unsafe NCM experiment was not repeated.
6. **RNDIS analysis:** exact vendor kernel code path, instance lifecycle, teardown audit, configfs options and whether a safe physical test is justified.
7. **ECM analysis:** why available/unavailable and whether it is worth enabling.
8. **Host compatibility:** Linux and macOS detection/driver requirements; actual host interface evidence; third-party userspace driver version/license/security if applicable.
9. **ACM preservation:** before/after function list, symlink state, serial port enumeration and tested access.
10. **IP and routing:** actual USB subnet, interface names, addresses, route table deltas and proof no default route changed.
11. **Tri-Link CLI:** exact commands tested and output summary, host key behavior, file transfer and exit codes.
12. **UI/Bridge truth:** exact status and error codes presented by USB SSH Console.
13. **Tests:** offline/unit/integration/physical separated, commands, totals, logs/evidence paths.
14. **Current blocker(s):** each with evidence and the lowest-risk remediation.
15. **Recommended route to fully working USB networking:** ordered steps, source files, kernel changes if needed, host requirements, risks and acceptance criteria.
16. **Rollback/recovery:** serial, WLAN SSH, known-good image, current gadget state and exact safe rollback command.
17. **Honest residual gaps:** no assumption that a mode works because it compiles.

If no blocker remains, still create the report and say `WORKING`, with physical proof and all evidence. If blocked, make the report sufficient for another engineer to continue without repeating unsafe experiments.

### 13.3 Evidence files

Store logs, test output, before/after JSON, network route snapshots and sanitized physical test results under a uniquely named directory such as:

`docs/beta-finalization/live/evidence/pwnage-92000/`

Do not commit secrets, private keys, user passwords, full public key material or personally sensitive network details. Add checksums for immutable evidence where the repository uses that pattern.

---

## 14. SECURITY, PRIVACY AND RECOVERY RULES

1. RDP and VNC listeners remain off until explicitly started.
2. RDP requires TLS and PAM; no root login.
3. VNC requires modern authentication and encryption; no unauthenticated LAN exposure.
4. No weak DES/legacy VNC authentication or `allow_broken_crypto` compatibility mode.
5. No passwords in source, configs committed to git, PWA local storage, URLs, QR codes or logs.
6. No private keys on the handset for host-side SSH; host pinned key behavior remains intact.
7. No public Internet exposure, router port forwarding, UPnP, cellular listening or default route changes.
8. Keep privacy indicator synchronized with actual listener and active remote session.
9. The lockscreen continues to protect content and input.
10. Never kill physical Phoc or framebuffer services when stopping XRDP/VNC.
11. Preserve serial CDC-ACM and WLAN SSH as separate recovery paths.
12. Never retry NCM create/unbind/teardown on the known bad 4.14.253 kernel.
13. Do not physically test a different gadget mode until exact source lifecycle, rollback and recovery have been reviewed.
14. If system lacks required firewall/auth/certificate support, refuse the unsafe action and report the blocker.
15. Any live test that may affect the USB UDC must have a tested rollback and confirmed WLAN SSH session; a paper rollback is not enough.

---

## 15. IMPLEMENTATION ORDER — DO NOT RANDOMLY PARALLELIZE

Use this sequence and keep each stage reviewable.

### Stage A — Audit and plan

- Complete Section 2.
- Record baseline ports, VNC security mismatch and USB mode status.
- Identify authoritative config and all references.
- Build test plan and rollback plan.
- No runtime changes.

### Stage B — Port and server configuration unification

- Introduce/verify canonical port values 13389/15900.
- Update generated XRDP/wayvnc configs, controller, Bridge, firewall, status schema, tests and docs.
- Add config validation and no secret leakage.
- Do not enable services yet.

### Stage C — Secure direct RDP

- Validate TLS/PAM and session identity.
- Add trusted-LAN firewall/bind rules.
- Test start/stop/listener/TLS/session.
- Verify direct Mac RDP client connection with no tunnel.

### Stage D — Secure direct VNC

- Fix generated config to use port 15900 and modern auth/TLS.
- Verify actual Wayland capture/input and privacy gating.
- Test Jump compatibility; if it fails, keep security and document a compatible secure client.
- Verify direct connection with no tunnel.

### Stage E — GUI Tri-Link / scrcpy correction

- Make third GUI path useful for native Nuxel using the secure native mirror route.
- Preserve genuine Android scrcpy functionality only for real ADB devices.
- Update registry/app metadata/status and tests.

### Stage F — USB network source and mode audit

- Re-read current kernel config and vendor kernel source.
- Analyse NCM panic and RNDIS/ECM create/cleanup independently.
- Update capability model and report candidate modes.
- No physical gadget mutation until explicit safe test plan.

### Stage G — Host and device USB CLI implementation

- Generalize device helper safely.
- Implement host platform adapters and mode-aware CLI.
- Preserve serial ACM and existing host-key SSH CLI behavior.
- Run offline test fixtures before any physical test.

### Stage H — Physical USB validation (conditional)

Proceed only when the exact selected mode is source-reviewed and the recovery criteria in 8.4 are satisfied. Start with the least risky supported mode, maintain WLAN SSH, verify serial after re-enumeration, and stop immediately on unexpected kernel warnings or connectivity loss. Do not move to another mode in the same un-recovered test transaction.

### Stage I — Full acceptance and docs

- Run regression suites.
- Run live RDP/VNC and (if safe) USB tests.
- Capture actual evidence.
- Update quickstarts and `REPORT-USBNET.md`.
- Review source diff for unrelated changes, secret exposure, stale old ports and duplicate implementations.

---

## 16. DEFINITION OF DONE

### Direct XRDP

- [ ] XRDP configuration, Bridge, helper, firewall, UI, docs and tests agree on TCP 13389.
- [ ] Listener is actually open on the intended trusted LAN interface only while explicitly started.
- [ ] Direct LAN connection works with no SSH tunnel.
- [ ] TLS-only and PAM login are verified; root denied.
- [ ] Separate Xorg desktop and input work.
- [ ] Stop/Stop All closes listener, kills only managed child sessions and removes temporary firewall allowance.
- [ ] OFF-by-default and reboot-safe.

### Direct VNC

- [ ] WayVNC configuration, Bridge, helper, firewall, UI, docs and tests agree on TCP 15900.
- [ ] VNC is authenticated and encrypted in the effective running daemon config.
- [ ] Bridge/UI never advertise security that is not present.
- [ ] Direct LAN connection works with no SSH tunnel using a verified compatible secure client.
- [ ] It shows the real active Phoc screen, remote input works as intended, lock privacy holds.
- [ ] Stop closes listener and removes temporary firewall allowance.
- [ ] OFF-by-default and reboot-safe.

### GUI Tri-Link / scrcpy

- [ ] Native Nuxel has a useful native mirror route; it is not misrepresented as Android scrcpy.
- [ ] Android scrcpy works only with real ADB targets and a valid official client/server path.
- [ ] Native and Android states/errors are distinct and truthful.
- [ ] No duplicate/unstable app registry IDs or broken launcher entries.

### USB network / CLI

- [ ] No unsafe NCM retry on the known panic kernel.
- [ ] Mode-aware capability evaluation distinguishes NCM/RNDIS/ECM.
- [ ] A safe mode is source-reviewed, host-compatible and physically verified before it reports READY.
- [ ] Serial ACM recovery remains intact.
- [ ] The MacBook host workflow is genuinely supported or the exact host driver limitation is documented.
- [ ] USB SSH CLI performs real key-authenticated commands and verified file transfer.
- [ ] No default route/Wi-Fi/VPN changes.
- [ ] Status UI and host CLI show truthful state.
- [ ] `REPORT-USBNET.md` exists and contains evidence-backed result plus best next step for any blocker.

### Regression

- [ ] All relevant pre-existing tests remain enabled.
- [ ] New tests cover every new security and lifecycle requirement.
- [ ] `git diff --check` and code linters pass.
- [ ] No unrelated system behavior is broken.
- [ ] Deployment/rollback plan is documented and tested.

---

## 17. REQUIRED FINAL RESPONSE FROM THE CODING AGENT

At completion, report:

1. Files changed, grouped by XRDP, VNC, GUI Tri-Link, USB device/host CLI, Bridge/API, packaging/tests/docs.
2. Exact final ports and bind/firewall behavior.
3. Actual direct LAN test results for RDP and VNC, including client version, security mode and whether an SSH tunnel was absent.
4. Exact VNC authentication/encryption mode now enforced.
5. How native Nuxel mirror and Android scrcpy are separated.
6. USB mode selected or blocked, why, and whether RNDIS/NCM/ECM was physically verified.
7. Confirmation that serial CDC-ACM and WLAN SSH remain available.
8. Tests run with exact pass/fail totals and any baseline failures.
9. Evidence directory path.
10. Link/path to `./REPORT-USBNET.md` and concise executive verdict.
11. Any remaining blockers, exact cause and recommended next step.

Do not say “fully working” if only code, package or unit tests exist. Separate **implemented**, **unit-tested**, **device-tested**, **host-tested** and **physically verified end-to-end**. Be explicit about every unverified boundary.

---

## 18. UPSTREAM TECHNICAL REFERENCES

Use current upstream documentation and source for the exact versions packaged by Nuxel. These references provide starting points; verify exact behavior for installed releases and vendor kernel source.

- **scrcpy official project:** <https://github.com/Genymobile/scrcpy> — Android screen mirroring/control over ADB; official sources only.
- **Linux USB gadget configfs documentation:** <https://docs.kernel.org/usb/gadget_configfs.html> — function instances, config symlinks, UDC bind/unbind and cleanup behavior.
- **Linux USB gadget Kconfig:** <https://github.com/torvalds/linux/blob/master/drivers/usb/gadget/Kconfig> — function compile-time options; compare with Nuxel's exact vendor kernel.
- **wayvnc upstream manual:** <https://github.com/any1/wayvnc/blob/master/wayvnc.scd> — bind address/port, authentication, PAM, TLS certificate/private key and crypto compatibility settings.
- **wayvnc current CLI options:** <https://man.archlinux.org/man/wayvnc.1> — rendering cursor, frame rate, GPU option, input-disable flag and control socket.
- **xrdp upstream `xrdp.ini` manual:** <https://github.com/neutrinolabs/xrdp/blob/devel/docs/man/xrdp.ini.5.in> — port, bind semantics, TLS security layer, certificates and TLS versions.
- **ReRNDIS for macOS:** <https://github.com/JellyBrick/ReRNDIS> — evaluate as a userspace RNDIS path for modern macOS/Apple Silicon; check current releases, permissions and exact compatibility before recommending.
- **RNDIS tether host userspace alternative:** <https://github.com/stlk0/rndis-tether> — evaluate current architecture/compatibility and compare with ReRNDIS; verify current maintenance and license.

Do not cite a current-mainline kernel Kconfig option as proof that the Nuxel vendor 4.14.253 tree behaves the same. Do not assume a macOS driver works because its README says macOS 15; test the owner's actual Mac environment and document the exact driver release.

---

## 19. FINAL COMMANDMENT

**Make the direct LAN remote desktop paths genuinely work on TCP 13389 and 15900, make their security status truthful, give the native Nuxel screen-mirror path a useful and technically honest implementation, and solve USB networking through a source-reviewed, mode-aware and physically proven gadget path. Preserve the serial recovery console and WLAN SSH at every stage. Never trade security or the only recovery path for a green READY badge.**
