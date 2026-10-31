# Nuxel GUI Tri-Link — Quickstart

_Status: 2026-10-31 · Nuxel v0.7.4-beta · S10+ (beyond2lte, Exynos 9820)_
_PWNAGE-47000 live acceptance: Jump Desktop 9.1.21 on macOS 15.7.9 (arm64)._

The GUI Tri-Link is **separate** from the serial/WLAN/USB SSH Tri-Link.

| App | What it is | Default route | State |
|---|---|---|---|
| **VNC Screen Sharing** | `wayvnc` attached to the real Phoc/Wayland session | Wi-Fi via pinned SSH tunnel | works; remote display + pointer input verified |
| **XRDP Remote Desktop** | `xrdp` + `xorgxrdp` **separate X11 session** (not a phone-screen mirror) | Wi-Fi via pinned SSH tunnel | works; TLS + PAM login + keyboard input verified |
| **scrcpy (Android)** | official scrcpy for real Android ADB targets only | USB ADB | no Android target on native Nuxel — honest `NOT_APPLICABLE_NATIVE_NUXEL` |
| Serial/Wi-Fi/USB SSH consoles | existing Tri-Link recovery tools | unchanged | preserved |

> **Remote access is OFF by default and never starts at boot.**
> Both server listeners bind to `127.0.0.1` only. The Mac reaches them through a
> pinned-host-key SSH local forward. No wildcard bind, no cellular/public route,
> no router forwarding.

---

## 0. One-minute path (after Wi-Fi is up)

```sh
# From the repository root on the MacBook.
# 1. Read the live phone address from the app or the Bridge:
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@<PHONE_IP> \
  'curl -s http://127.0.0.1:8080/api/v1/system/remote-desktop | python3 -m json.tool | head'

# 2. Start the server you want (explicit owner action):
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@<PHONE_IP> \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl start vnc'
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@<PHONE_IP> \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl start xrdp'

# 3. Open the pinned tunnel (VNC 15900, RDP 13389):
./scripts/nuxel-gui-tunnel.sh --host <PHONE_IP> --background

# 4. In Jump Desktop use the saved profiles:
#      nux-vnc  -> 127.0.0.1:15900
#      nux-rdp  -> 127.0.0.1:13389  (user: nuxel-remote)
```

Stop everything:

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@<PHONE_IP> \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl stop-all'
./scripts/nuxel-gui-tunnel.sh --stop
```

---

## 1. What you need

- Nuxel S10+ booted into Phoc/Home (the boot animation must have handed off).
- Phone on the owner LAN; current IPv4 is discovered live, never hardcoded.
- The owner key `~/.ssh/wicked_wqn_id_rsa` and the pinned host key
  `configs/nuxel/security/ssh/known_hosts` (SHA256
  `LegjMkabj0ig6rTzMMiiekWQLzCJt0LsJUeTm3c7JGs`).
- Jump Desktop 9.1.21 (or another secure RDP/VNC viewer) on the Mac.
- No Jump Desktop Connect host agent is installed on Nuxel; Nuxel runs its own
  xrdp/wayvnc servers.

The SSH account is `nuxel`. The separate RDP account is `nuxel-remote`
(no sudo, no root login). Its password is stored only in
`/etc/nuxel/remote-desktop/xrdp/credential` on the phone, mode `0600`, and is
never put in a `.rdp` file, PWA storage, URL, QR code or log.

---

## 2. Start / stop from the phone apps

Open **Applications** and choose:

- **VNC Screen Sharing** — Start/Stop, current Wi-Fi address, port 5900,
  transport `Wi-Fi` (USB shows `BLOCKED_KERNEL_PANIC`).
- **XRDP Remote Desktop** — Start/Stop, port 3389, transport `Wi-Fi`,
  explicitly labelled **Separate remote X11 session**.
- **scrcpy (Android)** — target detection only; native Nuxel is not Android.

The apps call the typed Bridge namespace `system.remote-desktop`, not
`system.tri-link`. The old consoles remain the authority for serial/WLAN/USB SSH.

Read-only status from the phone:

```sh
curl -s http://127.0.0.1:8080/api/v1/system/remote-desktop | python3 -m json.tool
sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl status
```

Useful fields: `state`, `bind_address`, `port`, `listener_verified`,
`authenticated_clients`, `session_mode`, `tls_fingerprint`, `usb.status`,
`network.address`, and `privacy.indicator`.

---

## 3. Mac tunnel and Jump Desktop profiles

The tunnel helper copies the pinned key to a temporary host-specific
`known_hosts` and uses `StrictHostKeyChecking=yes`. It never disables host-key
verification.

```sh
./scripts/nuxel-gui-tunnel.sh --host 192.168.178.167 --background
# TUNNEL_READY vnc=127.0.0.1:15900 rdp=127.0.0.1:13389 host=...
```

Saved Jump Desktop connections:

| Jump profile | Protocol | Address | Notes |
|---|---|---|---|
| `nux-vnc` | VNC | `127.0.0.1:15900` | wayvnc, security type None **inside** the authenticated SSH tunnel |
| `nux-rdp` | RDP | `127.0.0.1:13389` | TLS, PAM user `nuxel-remote` |

- If Jump asks for a VNC password: there is none. The security boundary is the
  pinned-key SSH tunnel; do not enable legacy DES VNC to "fix" a prompt.
- For RDP, enter `nuxel-remote` and the credential from the phone's root-only
  file. Do not save it in the `.rdp` profile.
- The RDP profile creates a **separate X11 desktop** (Openbox + Nuxel launcher +
  Firefox). It does not mirror the physical Phoc screen and never owns
  `/dev/fb0`. Use `nux-vnc` to see the real phone screen.

---

## 4. scrcpy (Android-only)

Official scrcpy 5.0.1 and ADB 37.0.1 are on the Mac. Native Nuxel is not an
Android target.

```sh
./scripts/nuxel-scrcpy.sh --list          # NO_ANDROID_TARGET on this Mac today
./scripts/nuxel-scrcpy.sh --usb           # real Android device over USB ADB
./scripts/nuxel-scrcpy.sh --pair 192.168.1.50:37000   # prompts for pairing code
./scripts/nuxel-scrcpy.sh --tcpip 192.168.1.50:5555   # adb connect + scrcpy
```

The wireless pairing code is read from a prompt (or `ADB_PAIR_CODE` for
automation) and is never written to disk or logs. `--tcpip` disconnects the ADB
transport when scrcpy exits. No Waydroid is installed or started.

On the phone itself, `scripts/nuxel-scrcpy.sh --list` prints
`NOT_APPLICABLE_NATIVE_NUXEL` and points to VNC.

---

## 5. Verified live acceptance (2026-10-31)

- **VNC:** Jump Desktop handshake `RFB 003.008`, WayVNC 720×1520, one client;
  Mac window and phone screenshot show the same Nuxel screen; a Jump pointer
  click opened the Applications drawer on the phone; prior keyboard marker
  `MANAGEDVNC` was typed through Jump into the Nuxel search field.
- **XRDP:** Jump Desktop TLS 1.3, desktop 1512×916, PAM login as
  `nuxel-remote`, Xorg `:10` + `xrdp-sesexec` + Firefox kiosk launcher;
  keyboard marker `PWNAGERDPINPUT` reached the remote Firefox find bar.
- **Independence:** Phoc remained PID 5811 and `nuxel-wl-fb` remained the only
  `/dev/fb0` owner during the RDP session.
- **scrcpy:** `NOT_APPLICABLE_NATIVE_NUXEL`; ADB 37.0.1 available, zero Android
  targets; no fake READY state.
- **Bridge truth:** `vnc=CONNECTED(1)`, `xrdp=CONNECTED(1)`,
  `scrcpy=NOT_APPLICABLE_NATIVE_NUXEL`, `usb=BLOCKED_KERNEL_PANIC`.

Evidence: `docs/beta-finalization/live/evidence/pwnage-47000/`.

---

## 6. Security rules

- OFF by default; start requires an explicit owner action and is never enabled
  at boot.
- Listeners bind `127.0.0.1` only; access is through the pinned-key SSH tunnel.
- XRDP uses TLS; VNC never uses DES-only auth on a network interface.
- No root desktop, no wildcard bind, no cellular/public exposure, no UPnP or
  router forwarding.
- VNC mirrors the real lockscreen; remote input goes through Phoc virtual-input
  protocols and cannot bypass the Nuxel lock.
- USB network RDP/VNC stays `BLOCKED_KERNEL_PANIC` on 4.14.253. Do not retry
  NCM, mutate configfs or rebind the UDC.
- `System → Remote Access → Stop all` (Bridge `stop-all`) is the kill switch.

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Phone stuck on the spinning Nuxel animation after a package update | An enforcing SELinux policy was installed and PID 1 runs in `kernel_t`. `/etc/selinux/config` must say `SELINUX=permissive` (image guard included). Reboot and verify `getenforce` is `Permissive`. |
| SSH local forward opens but the remote end resets | The unprivileged account is missing group `inet` (gid 3003). This kernel is `CONFIG_ANDROID_PARANOID_NETWORK=y`; run `usermod -aG inet nuxel` and open a **new** SSH session. `nuxel-remote` needs it too. |
| VNC refused / no banner | Check `systemctl status nuxel-remote-vnc`, `wayvncctl client-list`, and that `/run/nuxel-wayland/wayland-0` exists. The server is root-owned on this image. |
| RDP login loops | Use `nuxel-remote`, not `nuxel`; verify `/etc/xrdp/xrdp.ini` binds `127.0.0.1:3389`; read `/var/log/xrdp-sesman.log`. |
| RDP shows a black screen | Check `pgrep -a Xorg` for `:10` and `/var/log/xrdp-sesman.log` for `X server :10 is working`. The launcher needs Firefox/Openbox. |
| Jump VNC connects then EOF | Start the tunnel with `ssh -f` (daemonized) or run the helper; a tunnel started as a shell child dies when that shell exits. |
| USB toggle | Permanently blocked until a non-NCM USB network route is independently proven on the 4.14.253 kernel and macOS. |
