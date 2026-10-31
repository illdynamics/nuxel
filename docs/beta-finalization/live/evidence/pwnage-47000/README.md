# PWNAGE-47000 evidence index

All captures are from the actual S10+ and the actual MacBook (macOS 15.7.9,
arm64, Jump Desktop 9.1.21), 2026-10-31.

| # | File | What it proves |
|---|---|---|
| 01 | `01-postboot-phoc.png` | After the reboot the physical Phoc screen is the Nuxel Applications drawer, not the spinning animation. |
| 02 | `02-phone-vnc-live.png` | Phone-side grim capture of the live Phoc screen while VNC is connected. |
| 03 | `03-mac-jump-vnc-live.png` | Mac Jump Desktop `nux-vnc` window showing the same Nuxel screen (WayVNC 720×1520). |
| 04 | `04-phone-vnc-pointer-input.png` | Phone screen after a Jump pointer click: Applications drawer open (VNC input reached Phoc). |
| 05 | `05-mac-jump-rdp-session.png` | Mac Jump `nux-rdp` window showing the separate authenticated X11 desktop (Openbox + Nuxel launcher). |
| 06 | `06-mac-jump-rdp-keyboard-input.png` | Remote Firefox find bar containing the typed marker `PWNAGERDPINPUT` (RDP keyboard input). |
| 07 | `07-phone-phoc-during-rdp.png` | Physical phone screen unchanged while the RDP X11 session is active. |
| 08 | `08-mac-jump-rdp-login.png` | Real Jump RDP TLS/PAM login dialog before authentication. |
| 09 | `09-start-after-reboot.txt` | Fresh post-reboot start of VNC + XRDP: loopback listeners and `WAITING_FOR_CLIENT`. |
| 10 | `10-stop-cleanup.txt` | `stop-all`: listeners closed, wayvnc/Xorg/sesexec gone, Phoc alive, `nuxel-wl-fb` still owns `/dev/fb0`. |
| 11 | `11-phone-packages.txt` | Kernel, package NEVRAs/aarch64, `Permissive`, `inet` group, credential mode. |
| 12 | `12-wayland-protocols.txt` | Phoc advertises screencopy + virtual pointer + virtual keyboard. |
| 13 | `13-post-reboot-boot.txt` | Post-reboot systemd state, wlan0 address, handoff files, Phoc/wl-fb PIDs, no anim. |
| 14 | `14-mac-host.txt` | macOS/Jump Desktop/scrcpy/ADB versions. |
| 15 | `15-jump-profiles.json` | Saved `nux-vnc` and `nux-rdp` profiles (host/port/protocol only; no secrets). |
| 16 | `16-tests.txt` | Offline tests (28 passed). |
| 17 | `17-bridge-status.json` | Full `system.remote-desktop` status: VNC/XRDP WAITING, scrcpy NOT_APPLICABLE, USB blocked. |
| 18 | `18-final-off.txt` | Final state after stop: no listeners, no Xorg, no wayvnc. |
| 19 | `19-sha256.txt` | SHA-256 of every evidence file. |
| 20 | `20-performance.txt` | Idle and one-Jump-client CPU/RSS for Phoc, wl-fb, wayvnc, xrdp; final listener close. |
| 21 | `21-rdp-after-reboot.txt` | Post-reboot RDP reconnect: Xorg/sesexec/Firefox active, Bridge `CONNECTED(1)`. |
| 22 | `22-mac-jump-rdp-after-reboot.png` | Post-reboot Jump RDP window showing the separate X11 desktop. |
| 24 | `24-apps-deployed.txt` | Live registry revision 9: three new apps + three consoles, all entry files present and HTTP 200. |
| raw/ | `raw/*.png` | Intermediate/duplicate captures kept for audit (first login attempt, repeated click frames, VNC keyboard-focus attempt that did not focus a text field). |

No credentials, Wi-Fi PSK, ADB private key or RDP password appear in this
directory. The RDP password is only in the phone's root-owned `0600` file.
