# Nuxel GUI Tri-Link — Quickstart

_Status: 2026-11-08 · Nuxel v0.8.1-beta · S10+ (beyond2lte, Exynos 9820)_
_PWNAGE-92000 live acceptance: direct LAN RFB and RDP TLS probes on macOS 15.7.9 (arm64). Jump Desktop VNC compatibility must be re-tested; the server stays secure either way._

The GUI Tri-Link is **separate** from the serial/WLAN/USB SSH Tri-Link.

| App | What it is | Default route | State |
|---|---|---|---|
| **VNC Screen Sharing** | `wayvnc` attached to the real Phoc/Wayland session | Direct Wi-Fi | works; no SSH tunnel; **PAM + VeNCrypt TLS/RSA-AES required** |
| **XRDP Remote Desktop** | `xrdp` + `xorgxrdp` **separate X11 session** (not a phone-screen mirror) | Direct Wi-Fi | works; TLS + PAM login as local `nuxel` |
| **scrcpy (Android)** | official scrcpy for real Android ADB targets only | USB ADB | no Android target on native Nuxel — honest `NOT_APPLICABLE_NATIVE_NUXEL` |
| Serial/Wi-Fi/USB SSH consoles | existing Tri-Link recovery tools | unchanged | preserved |

> **Direct owner-network access.** The privileged controller binds both listeners
> to the current **trusted WLAN IPv4 address**, not `0.0.0.0`. RDP is TLS 1.2/1.3
> + PAM. VNC is PAM + VeNCrypt TLS/RSA-AES; unauthenticated RFB is disabled. No
> SSH tunnel is required on the owner LAN. Do not port-forward 13389/15900 to
> the Internet.

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
#      nux-vnc  -> <PHONE_IP>:15900 (PAM + VeNCrypt TLS/RSA-AES)
#      nux-rdp  -> <PHONE_IP>:13389 (TLS + PAM, user: nuxel)
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
- A secure RDP viewer and a secure VNC viewer on the Mac. Jump Desktop 9.1.21
  previously failed to negotiate wayvnc 0.9.1's RSA-AES/VeNCrypt modes; re-test
  the current Jump version. If it still fails, use another client that supports
  VeNCrypt TLS or RSA-AES. Never disable VNC authentication to accommodate a
  client.
- No Jump Desktop Connect host agent is installed on Nuxel; Nuxel runs its own
  xrdp/wayvnc servers.

The SSH/RDP/VNC account is the local `nuxel` user (uid 1000). Use its local
account password in the client's secure credential store. The retired
`nuxel-remote` account is not created or accepted. Do not put the password in a
`.rdp` file, PWA storage, URL, QR code or log.

---

## 2. Start / stop from the phone apps

Open **Applications** and choose:

- **VNC Screen Sharing** — Start/Stop, current Wi-Fi address, port 15900,
  transport `Wi-Fi` (USB shows `NEEDS_VALIDATION`).
- **XRDP Remote Desktop** — Start/Stop, port 13389, transport `Wi-Fi`,
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
`authenticated_clients`, `session_mode`, `authentication_mode`, `encrypted`,
`security_verified`, `certificate_fingerprint`, `usb.status`,
`network.address`, and `privacy.indicator`.

---

## 3. Jump Desktop profiles (direct, no SSH tunnel)

Saved Jump Desktop connections:

| Jump profile | Protocol | Address | Notes |
|---|---|---|---|
| `nux-vnc` | VNC | `<PHONE_IP>:15900` | wayvnc mirrors the real Phoc screen; PAM + VeNCrypt TLS/RSA-AES |
| `nux-rdp` | RDP | `<PHONE_IP>:13389` | TLS 1.2/1.3, PAM user `nuxel`, separate X11 session |

- SSH is still used only for administration, with
  `~/.ssh/wicked_wqn_id_rsa`; it is not in either Jump connection.
- RDP's TLS certificate is self-signed. Accept it once in Jump and keep the
  saved certificate; verify the fingerprint on the phone if it changes.
- Use the phone's current IPv4 (discovered live from the app/status). Never
  hardcode a historical address.
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

## 5. Verified live acceptance (2026-11-08, PWNAGE-92000)

- **VNC:** direct LAN listener `192.168.178.167:15900`; RFB banner
  `RFB 003.008`; offered security types `129` (VeNCrypt) and `5` (RSA-AES);
  type `1` (None) was **not offered**. Effective config had `enable_auth=true`
  and `enable_pam=true`.
- **XRDP:** direct LAN listener `192.168.178.167:13389`; RDP negotiation
  completed and the socket upgraded to **TLS 1.3** with
  `TLS_AES_256_GCM_SHA384`; `security_layer=tls` and `autorun=Xorg`.
- **Stop/Stop All:** both listeners closed; `ss` showed no 13389/15900/3389/5900
  listener and the managed units were inactive.
- **Independence:** stopping remote access never targeted Phoc or `nuxel-wl-fb`.
- **scrcpy:** `NOT_APPLICABLE_NATIVE_NUXEL`; native Nuxel links to the VNC
  mirror. No fake ADB target.
- **USB:** NCM `BLOCKED_KNOWN_PANIC`, RNDIS `NEEDS_VALIDATION`; no configfs
  mutation. See `REPORT-USBNET.md`.

Evidence: `docs/beta-finalization/live/evidence/pwnage-92000/`.

---

## 6. Security rules

- Listeners bind to the current trusted WLAN IPv4 address on TCP 13389/15900.
- XRDP uses TLS + PAM as local `nuxel`. VNC uses PAM + VeNCrypt TLS/RSA-AES;
  unauthenticated RFB is disabled. Never expose either port to the Internet.
- No root desktop, no cellular/public exposure, no UPnP or router forwarding.
- VNC mirrors the real lockscreen; remote input goes through Phoc virtual-input
  protocols and cannot bypass the Nuxel lock.
- USB network stays mode-aware: NCM `BLOCKED_KNOWN_PANIC` on 4.14.253, RNDIS
  `NEEDS_VALIDATION`, ECM absent. Do not retry NCM, mutate configfs or rebind
  the UDC without the recovery plan in `REPORT-USBNET.md`.
- `System → Remote Access → Stop all` (Bridge `stop-all`) is the kill switch.

---

## 7. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Phone stuck on the spinning Nuxel animation after a package update | An enforcing SELinux policy was installed and PID 1 runs in `kernel_t`. `/etc/selinux/config` must say `SELINUX=permissive` (image guard included). Reboot and verify `getenforce` is `Permissive`. |
| SSH local forward opens but the remote end resets | The unprivileged account is missing group `inet` (gid 3003). This kernel is `CONFIG_ANDROID_PARANOID_NETWORK=y`; run `usermod -aG inet nuxel` and open a **new** SSH session. `nuxel-remote` needs it too. |
| VNC refused / no banner | Check `systemctl status nuxel-remote-vnc`, `wayvncctl client-list`, and that `/run/nuxel-wayland/wayland-0` exists. The server is root-owned on this image. |
| RDP login loops | Use the local `nuxel` account; verify `/etc/xrdp/xrdp.ini` binds the current WLAN IP on `:13389`; read `/var/log/xrdp-sesman.log`. |
| RDP shows a black screen | Check `pgrep -a Xorg` for `:10` and `/var/log/xrdp-sesman.log` for `X server :10 is working`. The launcher needs Firefox/Openbox. |
| VNC security error | Confirm the effective config has `enable_auth=true`, `enable_pam=true`, port `15900`, and that the client supports VeNCrypt TLS or RSA-AES. Do not disable authentication. If Jump cannot negotiate, use a compatible secure client. |
| USB toggle | Blocked pending mode-specific source review, host driver support and physical validation; see `REPORT-USBNET.md`. |
