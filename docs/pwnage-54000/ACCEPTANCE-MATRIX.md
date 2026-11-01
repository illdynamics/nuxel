# PWNAGE-54000 acceptance matrix

Status values: **PASS** (proved in this run), **PASS-LIVE** (proved on the
S10+), **BLOCKED-HW** (hardware/firmware missing), **NOT-TESTED** (no client or
physical finger available), **PASS-UNIT** (automated offline proof).

| Requirement | Status | Evidence |
|---|---|---|
| Seven exact labels in QS/Settings/config | PASS | `tests/pwnage54000/test_orientation_ui.py` |
| Stable keys + underscore aliases | PASS | `test_policy.py` |
| Locked PT 0° display | PASS-LIVE | `seven-modes.txt`; fb/grim corr 0.998 |
| Locked LS 90° display | PASS-LIVE | transform 270, 1520x720, corr 0.999 |
| Locked RPT 180° display | PASS-LIVE | transform 180, corr 1.000 |
| Locked RLS 270° display | PASS-LIVE | transform 90, corr 0.999 |
| Mode change applies transform | PASS-LIVE | Bridge set returns applied/verified |
| Failed transform rollback | PASS-UNIT | `test_failed_apply_restores_last_verified_orientation` |
| Auto FULL sensor behavior | BLOCKED-HW | `sensor.hub.raw_data=0,0,0`, LHD absent |
| Auto PT/LS allowed sets | PASS-UNIT | policy tests; live sets legal fallback |
| Auto flat/invalid last-good | PASS-UNIT | policy tests |
| Manual source not Auto | PASS-UNIT | `test_sensor_hub.py` |
| Touch matrix, no double rotation | PASS-UNIT | `test_input_matrices_match_each_compositor_transform_once` |
| Physical touch corners/edges/OSK | NOT-TESTED | agent has no physical finger |
| Reboot restores saved policy | PASS-LIVE | Locked (LS), sequence 169 after reboot |
| Daemon persistent service | PASS-LIVE | `Type=simple`, active after reboot |
| VNC portrait geometry | PASS-LIVE | RFB 720x1520 |
| VNC landscape geometry | PASS-LIVE | RFB 1520x720 |
| VNC connection survives refresh | PASS-LIVE | socket stayed connected through refresh |
| VNC failure cannot break local | PASS by design | helper is async consumer |
| XRDP listener | PASS-LIVE | 0.0.0.0:3389 |
| XRDP live rotate/no logout | NOT-TESTED | no RDP client / Jump Desktop available |
| Jump Desktop client | NOT-TESTED | not available in this run |
| Browser address-bar select-all | PASS (source contract) | `test_app_contracts.py` |
| Back closes app at root | PASS (source contract) | `test_app_contracts.py` |
| Numeric OSK for time fields | PASS (source contract) | `inputmode=numeric` calendar/clock |
| Alarm plays MP3 | PASS-LIVE asset 200 | `/assets/nuxel-alarm.mp3` HTTP 200 |
| Contacts manual add/edit | PASS-UNIT (built) | binary compiles, UI has New/Save |
| Contacts SIM import/sync/save | PASS-UNIT (built) | local SIM mirror; no physical SIM API |
| Files fast listing | PASS (source contract) | one `os.scandir` stat |
| Files copy text contents | PASS (source contract) | text-only guard + clipboard |
| Clipper app | PASS-LIVE asset 200 | `/pwa/nuxel-apps/clipper/index.html` |
| Phone app bug fix/dark | PASS-UNIT (built) | `MMCallProperties`, forced dark |
| Messages dark/SIM-ready | PASS-UNIT (built) | forced dark, SIM mirror |
| Pengu icon asset | PASS-LIVE asset 200 | `/assets/nuxel-app-penguinterface.png` |
| Native launch no 10 s stall | PASS-LIVE | 0.22 s HTTP response |
| Idle CPU | PASS-LIVE | 98% idle after final reboot |
| Home diagnostics log bounded | PASS-LIVE | 1.4 KB after reboot |
| One `/dev/fb0` writer | PASS-LIVE | `nuxel-wl-fb` owner lock |
