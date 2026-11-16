# PWNAGE 104xxx — component prompt index

Each kickstarter points to its full prompt. Start with the kickstarter.

| ID | Component | Kickstarter | Full prompt | Live status (2026-11-14) |
|---|---|---|---|---|
| 104100 | GNSS / GPS | `pwnage-104100.md` | `full-pwnage-104100.md` | LHD bridge exits; `handshake=False`, `gps=False` |
| 104200 | XRDP + VNC | `pwnage-104200.md` | `full-pwnage-104200.md` | **Fixed**: Apple-DH, loopback, PAM, credential sync |
| 104300 | Time / RTC / NTP | `pwnage-104300.md` | `full-pwnage-104300.md` | Wrong clock, bogus hostname |
| 104400 | TEE stall / load | `pwnage-104400.md` | `full-pwnage-104400.md` | 8 `tz_worker_threa` stuck in `D`, load ≈13 |
| 104500 | Camera | `pwnage-104500.md` | `full-pwnage-104500.md` | `BLOCKED_FIRMWARE`, no media graph, no frame |
| 104600 | Audio | `pwnage-104600.md` | `full-pwnage-104600.md` | PipeWire up (in nuxel-audio-session); hot-plug/capture/persistence unverified |
| 104700 | Display / rotation / HDMI | `pwnage-104700.md` | `full-pwnage-104700.md` | Displayd active; rotation blocked by SSP |
| 104800 | Wi-Fi / networking / DNS | `pwnage-104800.md` | `full-pwnage-104800.md` | Connected; secondary interfaces to audit |
| 104900 | Boot / lifecycle / watchdog | `pwnage-104900.md` | `full-pwnage-104900.md` | Compositor restarted twice; watchdog warnings |
| 104A00 | UI shell | `pwnage-104A00.md` | `full-pwnage-104A00.md` | Running; needs panel verification |
| 104B00 | Apps + mic/voice (ZapZap, Signal, Ferdium, Vesktop) | `pwnage-104B00.md` | `full-pwnage-104B00.md` | Installed apps untested; no startup/mic matrix |
| 104C00 | Permission manager + firewall | `pwnage-104C00.md` | `full-pwnage-104C00.md` | `nuxel-permd` up; enforcement unverified |
| 105000 | Performance / smoothness | `pwnage-105000.md` | `full-pwnage-105000.md` | Load ≈11.7, no `/dev/dri`, TEE stall |
| 105100 | Deploy live + reboot verify + release v0.8.5-beta | `pwnage-105100.md` | `full-pwnage-105100.md` | Deploy/PR/tag/release pending |

**Master prompt:** `pwnage-104000.md` → `full-pwnage-104000.md` (order, reboot
verification and v0.8.5-beta release procedure).

## Suggested order

1. `104200` — XRDP + VNC (auth + live screen), verify with Jump Desktop.
2. `104400` — TEE stall (affects everything's responsiveness).
3. `104300` — time (TLS, logs, auth).
4. `104100` — GPS (the original request).
5. `104700` — `/dev/dri`, graphics acceleration, HDMI video + audio, rotation.
6. `104600` — audio, mic, HDMI audio.
7. `104A00` — lockscreen, edge FX, notifications, `nuxel-pow.mp3`.
8. `104800` — Wi-Fi/BT, `104B00` apps + voice, `104C00` permissions/firewall.
9. `104900` — boot animation + preloading video audio.
10. `105000` — performance, then `105100` — deploy, reboot verify, v0.8.5-beta."

Related older missions: `full-pwnage-usbnet.md` (107000), `full-pwnage-nfc.md`,
`full-pwnage-ssp.md`, `full-pwnage-mobile.md`, `full-pwnage-gps.md`.
