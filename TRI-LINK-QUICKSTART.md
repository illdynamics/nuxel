# Nuxel Tri-Link Quickstart

This is the canonical entry point for the three console transports.

- **GUI Tri-Link (XRDP/VNC/native mirror):** [GUI-TRI-LINK-QUICKSTART.md](GUI-TRI-LINK-QUICKSTART.md)
- **Serial / Wi-Fi SSH / USB SSH consoles (host CLI):** [TRI-LINK-CLI-QUICKSTART.md](TRI-LINK-CLI-QUICKSTART.md)
- **USB network blocker evidence:** [REPORT-USBNET.md](REPORT-USBNET.md)

Current direct-LAN contract:

```text
XRDP: PHONE_LAN_IP:13389  TCP, TLS 1.2/1.3 + PAM, separate X11 session
VNC:  PHONE_LAN_IP:15900  TCP, PAM + VeNCrypt TLS/RSA-AES, active Phoc session
Tunnel: not required on the trusted owner LAN
USB SSH: NOT READY (NCM blocked on 4.14.253; RNDIS needs validation)
```
