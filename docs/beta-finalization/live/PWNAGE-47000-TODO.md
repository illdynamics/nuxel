# PWNAGE-47000 — GUI Tri-Link TODO / evidence ledger

_Updated 2026-10-31 14:10 CET · Nuxel v0.7.4-beta · S10+ beyond2lte_

## 0. Boot-blocker first (owner-reported)

- [x] Reproduce: phone looping on the spinning Nuxel animation after reboot.
- [x] Reach the phone: USB CDC-ACM console (`/dev/cu.usbmodem101`) and the live WLAN address `192.168.178.167`.
- [x] Root cause: the remote-desktop package transaction pulled in `selinux-policy-targeted`; the image was enforcing while systemd PID 1 and the initramfs console run in `kernel_t`. Every helper exec (`journald`, `udevd`, rootfs binaries) was denied, so systemd stalled before the UI handoff.
- [x] Live repair: `/etc/selinux/config` set to permissive; `getenforce` now returns `Permissive` after reboot.
- [x] Durable repair: image builder pins `SELINUX=permissive` after `dnf install` and removes `.autorelabel`; regression test added.
- [x] Second boot blocker found: `CONFIG_ANDROID_PARANOID_NETWORK=y`; non-root AF_INET sockets require gid 3003 (`inet`). Without it sshd local forwards fail (`connect failed: open failed`) and the unprivileged RDP session cannot network.
- [x] Live repair: `usermod -aG inet nuxel`, `usermod -aG inet nuxel-remote`.
- [x] Durable repair: image builder creates gid 3003 and adds both accounts; regression test added.
- [x] Rebooted after the fixes: no `nuxel-anim-player`, handoff files present, Phoc + `nuxel-wl-fb` active, launcher logging, remote services OFF, no listeners.
- [x] Evidence: `01-postboot-phoc.png`, `13-post-reboot-boot.txt`, `11-phone-packages.txt`.

## 1. Applications / registry

- [x] `org.nuxel.RemoteDesktopXRDP` → `pwa/nuxel-apps/remote-xrdp/`
- [x] `org.nuxel.RemoteDesktopVNC` → `pwa/nuxel-apps/remote-vnc/`
- [x] `org.nuxel.ScrcpyMirror` → `pwa/nuxel-apps/remote-scrcpy/`
- [x] Existing `org.nuxel.LiveConsole`, `org.nuxel.USBSSHConsole`, `org.nuxel.WiFiSSHConsole` preserved.
- [x] Canonical registry revision 9, native consumer updated, Home service-worker cache bumped.
- [x] Apps show real state, Wi-Fi default for VNC/XRDP, USB `BLOCKED_KERNEL_PANIC`, scrcpy native-Nuxel limitation.

## 2. Bridge / provider separation

- [x] `tri_link_status.py` left read-only and unchanged in contract.
- [x] New `services/nuxel-bridge/src/remote_desktop.py` with `system.remote-desktop` namespace.
- [x] Typed actions: `status`, `diagnose`, `connection-info`, `start`, `stop`, `stop-all`/`kill-switch`, `set-transport`, `scrcpy-targets`.
- [x] Fixed service allow-list (`vnc`, `xrdp`, `scrcpy`), fixed ports (5900/3389), loopback-only listeners, no arbitrary commands/paths.
- [x] `connection-info` now emits the verified `nuxel@` pinned tunnel and local ports 15900/13389 (was `root@`).
- [x] `nuxel-remote-desktop-ctl status` read-only verb added for the quickstart.
- [x] Cleanup hardened after a real timeout: bounded subprocess handling, session-manager-first stop, bounded SIGTERM/SIGKILL of only `xorg-nuxel.conf` / `nuxel-xrdp-session` / remote-Firefox, never Phoc or `nuxel-wl-fb`.

## 3. VNC (real Phoc session)

- [x] wayvnc 0.9.1-3.fc43.aarch64 on ARM64.
- [x] Phoc advertises `zwlr_screencopy_manager_v1` v3, `zwlr_virtual_pointer_manager_v1` v2, `zwp_virtual_keyboard_manager_v1` v1.
- [x] wayvnc runs as the session owner with `XDG_RUNTIME_DIR=/run/nuxel-wayland`, `WAYLAND_DISPLAY=wayland-0`.
- [x] Loopback listener 127.0.0.1:5900; pinned-key SSH forward; no DES auth on the network.
- [x] Jump Desktop 9.1.21: RFB 3.8, WayVNC 720×1520, one authenticated client, live screen.
- [x] Pointer input from Jump opened the Applications drawer on the phone (`02`, `03`, `04`).
- [x] Prior keyboard marker `MANAGEDVNC` typed through Jump into the Nuxel search field (prior evidence `vnc-managed-input.png`).
- [x] Stop removes the listener and wayvnc; Phoc and `/dev/fb0` untouched (`10-stop-cleanup.txt`).

## 4. XRDP (separate X11 session)

- [x] xrdp 0.10.6.1-3.fc43.aarch64 + xorgxrdp 0.10.5-1.fc43.aarch64 + Xorg ARM64.
- [x] Loopback TLS listener 127.0.0.1:3389; TLS 1.3 negotiated by Jump.
- [x] PAM login as restricted `nuxel-remote` (no sudo, no root login). New unique random credential stored only in `/etc/nuxel/remote-desktop/xrdp/credential`, mode 0600.
- [x] Xorg `:10`, `xrdp-sesexec`, Openbox and the Firefox kiosk Nuxel launcher are live (`05`).
- [x] Keyboard input from Jump reached the remote Firefox find bar (`06`), marker `PWNAGERDPINPUT`.
- [x] Physical Phoc screen remained the real phone screen during RDP (`07`); `nuxel-wl-fb` stayed the only `/dev/fb0` owner.
- [x] Disconnect/stop cleans Xorg and sesexec; listener closed (`10-stop-cleanup.txt`).
- [x] UI labels this **Separate remote X11 session**, not a physical-screen mirror.

## 5. scrcpy

- [x] Official scrcpy/ADB only; host has scrcpy 5.0.1 and ADB 37.0.1.
- [x] Phone reports `NOT_APPLICABLE_NATIVE_NUXEL` with a VNC recommendation; no fake READY/CONNECTED.
- [x] No Android target was present; no Waydroid installed or started.
- [x] `scripts/nuxel-scrcpy.sh` supports `--list`, `--usb`, `--pair` (prompted code), `--tcpip` with disconnect on exit.
- [x] Pairing code never written to disk/logs; no ADB private key access.

## 6. Transport / security

- [x] Wi-Fi default for VNC/XRDP; live address discovered from `wlan0`, never hardcoded.
- [x] USB remains `BLOCKED_KERNEL_PANIC`; no configfs mutation, no NCM retry, no UDC rebind.
- [x] SSH pinned Ed25519 host key `SHA256:LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`, `StrictHostKeyChecking=yes`.
- [x] Off by default; remote services have no boot enablement; kill switch verified.
- [x] Remote-desktop indicator active while listening; `REMOTE DESKTOP ACTIVE` from the Bridge.
- [x] No wildcard/cellular/public bind; no router forwarding/UPnP/cloud relay.

## 7. Mac / Jump Desktop

- [x] Mac: macOS 15.7.9 (24G830), arm64, Jump Desktop 9.1.21.
- [x] Saved Jump profiles:
  - `nux-vnc` → VNC 127.0.0.1:15900 (`ProtocolTypeCode=1`)
  - `nux-rdp` → RDP 127.0.0.1:13389 (`ProtocolTypeCode=0`)
- [x] No credentials are stored in the `.jump` profiles or the repo.
- [x] Real remote display + input evidence captured; no port-probe-only claim.

## 8. Tests / packaging

- [x] `tests/a80/test_remote_desktop.py`: 18 tests (registry, manifests, Bridge safety, USB refusal, scrcpy truth, SELinux boot guard, `inet` group guard, cleanup safety, status verb).
- [x] Existing Tri-Link tests: 38 passed in the combined run (`16-tests.txt`).
- [x] Image builder includes wayvnc/xrdp/xorgxrdp/Xorg/openbox/firefox/android-tools/openssl and clean-rootfs assertions.
- [x] Boot and `inet` guards are in the build after the package transaction.

## 9. Remaining owner-only steps

- [ ] Re-enter the RDP credential once in Jump if macOS Keychain was not asked to save it (the password is intentionally not in the profile).
- [ ] USB network RDP/VNC remains blocked until a safe non-NCM route and macOS host test exist.
- [ ] Rebuild and flash a fresh ARM64 rootfs to carry the two image guards (the live phone is already repaired).

## 10. Rollback

See `PWNAGE-47000-DEPLOYMENT.md`. The short form:

```sh
sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl stop-all
sudo -n systemctl disable --now xrdp.service xrdp-sesman.service 2>/dev/null || true
# restore /etc/nuxel/remote-desktop, /etc/xrdp, /etc/systemd/system/nuxel-remote-vnc.service,
# /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl and the Bridge module from the
# pre-47000 backups; keep sshd/serial untouched.
```
