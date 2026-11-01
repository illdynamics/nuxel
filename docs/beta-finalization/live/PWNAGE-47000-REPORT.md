# PWNAGE-47000 — Nuxel GUI Tri-Link / remote desktop final report

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)
**OS:** Nuxel v0.7.4-beta, Fedora 43 aarch64 userland, kernel `4.14.253-gf7194c1d15ed-dirty`
**Host:** MacBook, macOS 15.7.9 (24G830), arm64, Jump Desktop 9.1.21
**Date:** 2026-10-31
**Status:** boot hang repaired; VNC and XRDP live from Jump Desktop; scrcpy honestly not applicable to native Nuxel; existing Serial/WLAN/USB SSH Tri-Link preserved.

---

## 1. Boot hang — root cause and repair (owner priority)

The phone rebooted into the spinning Nuxel animation and never handed off. The
USB CDC-ACM console (`/dev/cu.usbmodem101`) was alive, but the framed command
helper could not run: every rootfs binary returned `Permission denied`.

Measured root cause:

- systemd PID 1 and the initramfs console run in SELinux domain `kernel_t`.
- The remote-desktop package transaction pulled in
  `selinux-policy-targeted-43.10-1.fc43.noarch` (via xrdp/tigervnc/greetd
  SELinux subpackages) and the image loaded it **enforcing**.
- PID 1 could not exec `systemd-journald`, `systemd-udevd` or its normal
  helpers, so the boot graph stalled with every job waiting. The initramfs
  animation player kept painting forever.

Live repair:

```text
/etc/selinux/config: SELINUX=permissive
getenforce -> Permissive (enforce=0)
```

A second, independent blocker appeared after the policy fix: the kernel is
built with `CONFIG_ANDROID_PARANOID_NETWORK=y`. A non-root process may only
create an AF_INET socket when its supplementary groups include gid 3003
(`inet`). The `nuxel` SSH account therefore could not open local port forwards
(`sshd: channel open failed: connect failed: open failed`) and the unprivileged
RDP account could not network. Both accounts were added to `inet`:

```text
inet:x:3003:nuxel,nuxel-remote
```

Durable image guards (in `images/s10plus/build-phone-rootfs-inside-fedora.sh`):

- after the package transaction, write `SELINUX=permissive` and remove
  `.autorelabel`; fail the build if the guard is not present;
- create gid 3003 and add `nuxel` + `nuxel-remote` to it;
- regression test asserts both guards.

Reboot verification: no `nuxel-anim-player`, handoff receipts present, Phoc and
`nuxel-wl-fb` active, launcher session started, `getenforce=Permissive`,
remote services inactive, no listeners. Evidence `01`, `13`, `11`.

---

## 2. Architecture delivered

### 2.1 Apps / registry

New canonical apps, registry revision 9:

| ID | Entry | Semantics |
|---|---|---|
| `org.nuxel.RemoteDesktopVNC` | `pwa/nuxel-apps/remote-vnc/` | mirrors the real Phoc/Wayland session |
| `org.nuxel.RemoteDesktopXRDP` | `pwa/nuxel-apps/remote-xrdp/` | separate authenticated X11 session |
| `org.nuxel.ScrcpyMirror` | `pwa/nuxel-apps/remote-scrcpy/` | Android ADB targets only |

The three existing console IDs (`LiveConsole`, `USBSSHConsole`,
`WiFiSSHConsole`) are unchanged. The native shell registry mirror and Home
service-worker cache were updated.

### 2.2 Bridge separation

`services/nuxel-bridge/src/tri_link_status.py` remains the read-only
serial/WLAN/USB SSH truth provider and was not made writable.

A separate provider `services/nuxel-bridge/src/remote_desktop.py` exposes
`system.remote-desktop` with a fixed allow-list:

- actions: `status`, `diagnose`, `connection-info`, `start`, `stop`,
  `stop-all`/`kill-switch`, `set-transport`, `scrcpy-targets`;
- services: `vnc`, `xrdp`, `scrcpy`;
- fixed ports: 5900, 3389; listeners bind `127.0.0.1` only;
- no arbitrary commands, paths, addresses or executable names;
- no secrets in status/connection-info.

`connection-info` was corrected to emit the verified `nuxel@` pinned tunnel and
the local Jump ports 15900/13389. `nuxel-remote-desktop-ctl status` was added as
a read-only quickstart helper.

### 2.3 Lifecycle cleanup

The first real `stop-all` exposed a 20 s `systemctl stop xrdp.service` timeout
that left Xorg `:10` and `xrdp-sesexec` alive. The helper now:

- catches `subprocess.TimeoutExpired` and returns a structured failure;
- stops `xrdp-sesman` first with `--no-block`;
- waits a bounded interval;
- terminates only `xorg-nuxel.conf` Xorg, `nuxel-xrdp-session` and remote
  Firefox owned by `nuxel-remote`;
- never targets Phoc or `nuxel-wl-fb`.

Verified after the fix: listener closed, no wayvnc/Xorg/sesexec, Phoc still
PID 5821, `nuxel-wl-fb` still the only `/dev/fb0` owner.

---

## 3. VNC — real Phoc screen sharing

- Server: `wayvnc 0.9.1-3.fc43.aarch64`, run as the session owner with
  `XDG_RUNTIME_DIR=/run/nuxel-wayland` and `WAYLAND_DISPLAY=wayland-0`.
- Phoc globals verified: `zwlr_screencopy_manager_v1` v3,
  `zwlr_virtual_pointer_manager_v1` v2,
  `zwp_virtual_keyboard_manager_v1` v1 (evidence `12`).
- Listener: `127.0.0.1:5900`; Mac local forward `127.0.0.1:15900`.
- Jump Desktop negotiated RFB 3.8, server `WayVNC`, 720×1520, one authenticated
  client. Security type 1 (None) exists **only inside** the pinned-key SSH
  tunnel; no DES-only auth is exposed on the network.
- The Mac window and phone screenshot show the same live Nuxel screen
  (`02`, `03`). A Jump pointer click opened the Applications drawer on the
  phone (`04`). Prior run keyboard marker `MANAGEDVNC` reached the Nuxel search
  field (`vnc-managed-input.png`).
- Stop removes wayvnc and closes 5900; Phoc and `/dev/fb0` are untouched.

## 4. XRDP — separate authenticated X11 session

- Packages: `xrdp 0.10.6.1-3.fc43.aarch64`,
  `xorgxrdp 0.10.5-1.fc43.aarch64`, Xorg, Openbox, Firefox.
- Listener `127.0.0.1:3389`, TLS 1.3; Mac local forward `127.0.0.1:13389`.
- PAM login as restricted `nuxel-remote` (uid 1001, no sudo, no root login).
  A new unique random credential was generated; it is stored only in
  `/etc/nuxel/remote-desktop/xrdp/credential` mode `0600 root:root`, and is not
  in the Jump profile, repo, logs or this report.
- Session: Xorg `:10`, `xrdp-sesexec`, Openbox, and the Firefox kiosk
  `file:///usr/share/nuxel/remote-desktop/launcher.html`.
- Jump Desktop showed the `SEPARATE X11 SESSION` desktop (`05`, `22`);
  keyboard marker `PWNAGERDPINPUT` reached the remote Firefox find bar (`06`).
- The physical Phoc screen remained the real phone screen during RDP (`07`);
  `nuxel-wl-fb` remained the only `/dev/fb0` writer.
- Stop cleans Xorg/sesexec and closes the listener (`10`).

This is **not** a physical-screen mirror and the UI says so.

## 5. scrcpy — Android only, honest native-Nuxel result

- Mac: official `scrcpy 5.0.1`, `adb 37.0.1`.
- Phone Bridge: `scrcpy=NOT_APPLICABLE_NATIVE_NUXEL`, `adb_available=true`,
  `scrcpy_available=false`, zero targets. No Waydroid installed or started.
- `scripts/nuxel-scrcpy.sh` supports `--list`, `--usb`, `--pair` (prompted
  pairing code), `--tcpip` (disconnects ADB on exit), and refuses to claim
  native Nuxel as an Android target.
- No fake server, no proprietary protocol, no native-Nuxel-as-Android claim.

## 6. Jump Desktop profiles

Saved through Jump Desktop's real Add Connection UI on the MacBook:

| Profile | Protocol | Address | Credential |
|---|---|---|---|
| `nux-vnc` | VNC (`ProtocolTypeCode=1`) | `127.0.0.1:15900` | none; pinned SSH tunnel is the security boundary |
| `nux-rdp` | RDP (`ProtocolTypeCode=0`) | `127.0.0.1:13389` | `nuxel-remote`, not saved in the profile |

Profile metadata is in evidence `15`; no passwords are present.

## 7. Transport, security and policy

- Wi-Fi is the default for VNC and XRDP; `wlan0` address is discovered live
  (`192.168.178.167` during this run), never hardcoded.
- SSH host pin matches `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`;
  tunnel uses `StrictHostKeyChecking=yes`.
- USB RDP/VNC remains `BLOCKED_KERNEL_PANIC`; the provider reports
  `mutated:false`, only `acm.usb0` present, no configfs/UDC mutation.
- OFF by default; no boot enablement; a reboot left both services inactive and
  no listeners.
- Indicator: Bridge `privacy.active=true`, `REMOTE DESKTOP ACTIVE`, kill switch
  `stop-all`.
- No wildcard/cellular/public bind, no router forwarding/UPnP/cloud relay.

## 8. Performance (measured on the S10+)

With one Jump VNC client connected (evidence `20`):

| Process | CPU % | RSS |
|---|---:|---:|
| `phoc` | 13.3 | 37.2 MiB |
| `nuxel-wl-fb` | 7.1 | 10.7 MiB |
| `wayvnc` | 3.7 | 43.7 MiB |
| `xrdp` | 0.2 | 8.5 MiB |
| `xrdp-sesman` | 0.0 | 2.3 MiB |

RDP active after reboot (`21`): Xorg `:10`, `xrdp-sesexec`, `xrdp-chansrv`,
Firefox, Openbox; Bridge `xrdp=CONNECTED(1)`. No claim of hardware encoding or
60 FPS is made; wayvnc runs at the configured 20 FPS cap with software capture.

## 9. Tests

Offline evidence `16`: **38 passed** across
`test_remote_desktop.py`, `test_tri_link_api.py`, `test_tri_link_status.py`.

New coverage includes:

- registry IDs, manifests, native consumer, no mock success;
- USB refusal before any helper call, no configfs mutation;
- scrcpy `NOT_APPLICABLE_NATIVE_NUXEL`;
- no secret fields in status; loopback-only connection info;
- `nuxel@` pinned tunnel and local ports;
- SELinux permissive boot guard;
- `inet` gid 3003 guard for both accounts;
- bounded stop timeout + no Phoc/wl-fb kill;
- read-only `status` verb.

## 10. Known limitations / owner steps

1. USB RDP/VNC is blocked by the recorded NCM teardown panic. No retry was
   made. A future safe non-NCM route plus macOS host testing is required.
2. VNC uses security type None inside the pinned SSH tunnel. Do not expose 5900
   directly; do not enable DES to satisfy a client prompt.
3. Jump may ask for the RDP password once per Mac session; the password is
   intentionally not stored in the profile. It can be read from the phone's
   root-only credential file.
4. A fresh rootfs rebuild is still required to carry the image guards into the
   shipped artifact; the live phone is already repaired.
5. `NetworkManager-wait-online.service` reports failed/degraded on this image;
   it does not block Phoc or remote access. This predates PWNAGE-47000.

## 11. Rollback

See `PWNAGE-47000-DEPLOYMENT.md`. Short form: `stop-all`, disable the two RDP
units and the VNC unit, restore the pre-47000 Bridge/registry/config backups,
restart only the Bridge. Never kill Phoc, `nuxel-wl-fb`, sshd or the serial
gadget to “fix” a remote-desktop service.

---

**Result:** boot hang fixed and durable; VNC mirrors the real phone and accepts
input from Jump Desktop; XRDP creates a real, usable separate X11 session with
TLS/PAM and accepts input from Jump Desktop; scrcpy reports the truth for native
Nuxel; the existing Serial/WLAN/USB SSH console paths are preserved.
