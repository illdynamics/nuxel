# NUXEL A74 / 23000 — Test matrix

## Automated (host, offline)

| test | command | result |
|---|---|---|
| Bridge indicator state machine (Python) | `python3 services/nuxel-bridge/test-system-indicators.py` | **ALL PASS** |
| Native host indicator snippet a33 + a45 (`-Wall -Wextra -Werror`) | `python3 tools/s10plus/a45/test-lockscreen-indicators.py` | **ALL PASS** |

Both suites now include the A74 regression assertion: a synthetic DWC3 debugfs
`link_state=Off` node has **no effect** (proving the dangerous read was removed)
while the Type-C `data_role` still governs the detach veto.

## Physical acceptance matrix

| # | Action | Expected | status |
|---|---|---|---|
| P1 | Boot with no PC cable | boot; no stale PC/Live icons; no reboot loop | PENDING OWNER |
| P2 | Connect PC data cable | PC + Live Console ON, console works | PENDING OWNER |
| P3 | Disconnect PC cable while console active | icons OFF; **no hang/reboot**; boot ID unchanged; uptime continues | PENDING OWNER |
| P4 | Reconnect PC cable | transport/console recover, no manual reboot | PENDING OWNER |
| P5 | Repeat P2–P4 ≥ 5 cycles | no crash/restart-storm/zombie/leak | PENDING OWNER |
| P6 | Wall charger only | charging ON, PC OFF; healthy removal no reboot | PENDING OWNER |
| P7 | Detach while console idle | no system failure | PENDING OWNER |
| P8 | Detach mid-command/output | handled disconnect; shell/UI/OS alive | PENDING OWNER |
| P9 | Wi-Fi + HTTPS after detach | network/browser keep working | PENDING OWNER |
| P10 | Lock/unlock, nav, battery, all three penguins | no regression | PENDING OWNER |
| P11 | Normal reboot after all tests | clean boot, no stale session/loop | PENDING OWNER |

Continuity proof is recorded per cycle from `/var/lib/nuxel/a74-usb-unplug.log`
(boot_id + uptime each sample) plus `cat /proc/sys/kernel/random/boot_id` and
`/proc/uptime` over SSH after each re-plug.
