# Nuxel GUI Tri-Link — Quickstart

_Status: 2026-11-01 · Nuxel v0.7.6-beta · S10+ (beyond2lte, Exynos 9820)_
_PWNAGE-47000 live acceptance: Jump Desktop 9.1.21 on macOS 15.7.9 (arm64)._

The GUI Tri-Link is **separate** from the serial/WLAN/USB SSH Tri-Link.

| App | What it is | Default route | State |
|---|---|---|---|
| **VNC Screen Sharing** | `wayvnc` attached to the real Phoc/Wayland session | Direct Wi-Fi / ZeroTier | works; no SSH tunnel; unauthenticated RFB, trusted network only |
| **XRDP Remote Desktop** | `xrdp` + `xorgxrdp` **separate X11 session** (not a phone-screen mirror) | Direct Wi-Fi / ZeroTier | works; TLS + PAM login as local `nuxel` |
| **scrcpy (Android)** | official scrcpy for real Android ADB targets only | USB ADB | no Android target on native Nuxel — honest `NOT_APPLICABLE_NATIVE_NUXEL` |
| Serial/Wi-Fi/USB SSH consoles | existing Tri-Link recovery tools | unchanged | preserved |

> **Direct owner-network access.** Both listeners bind `0.0.0.0` and are meant
> only for the trusted LAN and, later, ZeroTier. RDP is protected by TLS + PAM.
> VNC is unauthenticated because Jump Desktop 9.1.21 cannot negotiate wayvnc
> 0.9.1's RSA-AES/VeNCrypt and this build has no VNC password auth. Do not
> port-forward 3389/5900 to the Internet.

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

# 3. No tunnel. In Jump Desktop use the saved profiles:
#      nux-vnc  -> <PHONE_IP>:5900
#      nux-rdp  -> <PHONE_IP>:3389  (user: nuxel)
```

Stop everything:

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa nuxel@<PHONE_IP> \
  'sudo -n /usr/local/libexec/nuxel/nuxel-remote-desktop-ctl stop-all'
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

The SSH and RDP account is the local `nuxel` user (uid 1000). It has password
`enf0rcer` for this lab session. The retired `nuxel-remote` account remains on
the image but is no longer used by the Jump profile. Do not put the password in
a `.rdp` file, PWA storage, URL, QR code or log.

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

## 3. Jump Desktop profiles (direct, no SSH tunnel)

Saved Jump Desktop connections:

| Jump profile | Protocol | Address | Notes |
|---|---|---|---|
| `nux-vnc` | VNC | `192.168.178.167:5900` | wayvnc mirrors the real Phoc screen; no VNC password |
| `nux-rdp` | RDP | `192.168.178.167:3389` | TLS, PAM user `nuxel`, password `enf0rcer` |

- SSH is still used only for administration, with
  `~/.ssh/wicked_wqn_id_rsa`; it is not in either Jump connection.
- RDP's TLS certificate is self-signed. Accept it once in Jump and keep the
  saved certificate; verify the fingerprint on the phone if it changes.
- Use the phone's current IPv4 (discovered live). `192.168.178.167` was the
  address during this run.
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

- Listeners bind directly for the trusted owner LAN / future ZeroTier network.
- XRDP uses TLS + PAM as local `nuxel`. VNC has no authentication; treat 5900
  as LAN/ZeroTier-only and never expose it to the Internet.
- No root desktop, no cellular/public exposure, no UPnP or router forwarding.
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
| RDP login loops | Use `nuxel` / `enf0rcer`; verify `/etc/xrdp/xrdp.ini` binds `:3389`; read `/var/log/xrdp-sesman.log`. |
| RDP shows a black screen | Check `pgrep -a Xorg` for `:10` and `/var/log/xrdp-sesman.log` for `X server :10 is working`. The launcher needs Firefox/Openbox. |
| Jump VNC security error | The direct listener is `enable_auth=false`; confirm the phone is serving `address=0.0.0.0`, port `5900`, and that Jump is connecting to `192.168.178.167:5900` (no tunnel). |
| USB toggle | Permanently blocked until a non-NCM USB network route is independently proven on the 4.14.253 kernel and macOS. |
