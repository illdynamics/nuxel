# REGRESSION TESTS — A34

| Test | Command | Exit | Result |
|---|---|---|---|
| JS syntax | `node --check pwa/nuxel-home/js/status-bar.js` | 0 | PASS |
| Version triple | `grep` of status-bar/manifest/sw | 0 | `0.4.2-a34` / `v6-a34` consistent |
| Deployed hashes | `sha256sum` over console | 0 | all match host artifacts |
| Touch device present | `grep sec_touchscreen /proc/bus/input/devices` | 0 | PASS |
| IRQ alive | `grep sec_ts /proc/interrupts` | 0 | count 142 at 10:27:25Z |
| Frame progression | `nuxel-display-frame-trace.sh --seconds 3` | 0 | 71 frames / 3 s, failures 0 |
| Snapshot | `nuxel-wl-snapshot /tmp/...` | 0 | 720×1520, FNV recorded |
| Display off | FIFO `screen-off` | 0 | `bl_power=4`, brightness 0 |
| Display on | FIFO `screen-on` | 0 | `bl_power=0`, brightness 12800 |
| OSD without Power | FIFO `volume-up`, snapshot 2 s later | 0 | bright OSD region present |
| USB audit | `nuxel-usb-input-audit.sh` | 0 | device role, no xHCI bound |
| Home reload | `systemctl restart nuxel-wayland` | 0 | `NUXEL_HOME_READY`, statusbar 0.4.2-a34 |
| FSM: Power cancels Bixby | `tools/s10plus/a34/tests/test-fsm-power-bixby.sh` | 0 | PASS (A33 emitted open-terminal; A34 does not) |
| QS pull-down gesture | `node tools/s10plus/a34/tests/test-qs-gesture.js` | 0 | PASS (vertical pull fires once; short tap/diagonal rejected) |
| Button FSM/menu parity | `python3 tools/s10plus/a33/tests/test-button-fsm.py` | 0 | PASS, 0 failures (11-entry menu incl. Cancel) |
| Physical tap → WebKit | owner tap 10:13:01Z | — | PASS (T8 for Mail) |
| Physical tap → WebKit | owner tap 10:23:39Z | — | PASS (T8 for Calendar) |
| Host home closes app | FIFO `launch org.nuxel.Mail`, snapshot, `action home`, snapshot | 0 | PASS (295 → 23,547 unique colours; Mail frame → Home) |
| Owner normal use | Test B | — | **PENDING** |
| Power single/double | Test C | — | **PENDING** |
| Long-press menu | Test D | — | **PENDING** |
| USB mouse/keyboard | Test E | — | **NOT TESTED** |

No invented measurements. Tests that were not run are marked, not assumed.
