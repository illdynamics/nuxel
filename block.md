All three deployed to `/usr/share/nuxel/pwa/nuxel-home/` (hash-verified, pre-patch backups in `/var/lib/nuxel/a69-backup/`). 5 new offline invariant tests + 40 orientation tests pass.

## ⛔ Exact hardware blockers (not faked)
- **A69-03 speaker → BLOCKED_FIRMWARE**: `beyond-madera` = Cirrus **CS47L93** + **CS35L40×2**; `nuxelctl audio status` reports codec/amp DSP firmware absent (`cs47l93-dsp*.wmfw/.bin`, `cs35l40-dsp*.bin`), UCM `HiFi.conf` absent, no PipeWire/alsautils. No audio server, no `dnf`, no network.
- **A69-04 rotation → BLOCKED_HARDWARE**: sensor hub **BCM47752** is down (`ssp_down==true`, `ssp_send_cmd failed`, accel `raw_data=0,0,0`); no SSP sensor-hub firmware, no Samsung libsensorhub. All 7 rotation policies intact offline.
- **A69-05 GNSS/Maps → BLOCKED_HARDWARE / BLOCKED_DEPENDENCY**: no GNSS node (`SSP GPS:false`); Maps needs HTTPS tiles and Wi-Fi is **currently disconnected**.
- **A69-06 NFC → BLOCKED_HARDWARE**: `sec-nfc` driver registered, no bound device/firmware.
- **A69-07 Bluetooth → BLOCKED_DEPENDENCY**: no BlueZ, no hci, `bcm43xx` soft-blocked, no BT firmware.
- **A69-09 VLC/MP3 → BLOCKED_DEPENDENCY**: `dnf` is **absent** on the phone and there is no network.

## ⚠️  Two things you must know
1. **Wi-Fi is disconnected right now** (`wlan0`/`wlan1` disconnected, no route/DNS) — baseline **T30 is FAILED** and blocks all package installs and Maps tiles. Your saved profiles are untouched; please reconnect one.
2. The phone **rebooted at 19:49:14** — this was **not initiated by me**. The journal shows it came from the button-manager power menu (`MENU_SELECT id=restart`, `source=key`), i.e. a physical power-menu action. The A69 fixes survived the reboot.

## 📁 Deliverables
`docs/a69/` → `FINAL-STATUS.md` (184 lines, full A69-01…13 root-cause/fix/status), `PREFLIGHT.md`, `LIVE-VS-REPO.md`, `RISK-AND-ROLLBACK.md`, `ROTATION-HARDWARE-BOUNDARY.md`, `requirements.csv`, `test-matrix.csv` (all 35 gates), `logs/boot-state-home.log`. Benchmarks folder intentionally empty — I did not fabricate before/after FPS.

**What would unblock the rest:** owner-supplied Cirrus CS47L93/CS35L40 DSP firmware + a Fedora ARM64 audio server; BCM4775x SSP sensor-hub firmware + lawful userspace; BlueZ + BCM43xx HCD; a `dnf`/network path for VLC/mpv; and Wi-Fi reconnection. I can continue on any of those the moment the corresponding firmware/network is available.
tokens used
24,202,619
[codeseeq] stopping owned bridge process (pid=1993)

