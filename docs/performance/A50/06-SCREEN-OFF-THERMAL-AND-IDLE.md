# A50 — 06: Screen-off, thermal and idle

## Screen-off state (verified live)
- `/run/nuxel-wl-fb.state`: `DISPLAY_SLEEP total=… failures=0 owner=nuxel-wl-fb
  display=off capture=stopped` — the bridge **stops requesting/copying frames**,
  not merely skipping presentation.
- Panel: `bl_power=4` (FB_BLANK_POWERDOWN), `brightness=0`,
  `19030000.decon_f/power/runtime_status=suspended`.
- Bridge CPU while asleep: **0.1 %** of a core; phoc/WebKit idle (`do_sys_poll`).
- The bridge blocks in `poll()` on its control FIFO (1000 ms timeout), not a
  busy loop.

## Thermal
- Screen-off: SoC zones report 25.0 °C (these zones appear clamped at a 25 °C
  floor on this vendor kernel — treated as "not above 25 °C", not as exact),
  battery 19.7–21.2 °C (plausible live readings).
- Screen-on (locked/idle, ~1 min): BIG zone 30.0 °C, battery 21.2 °C — warm but
  safe, consistent with the measured ~86 %-of-one-core graphics load.
- No throttling observed; `schedutil` governor left untouched.

## "Warm when locked" historical issue
The current build appears to have **already fixed** the old "very warm at
lockscreen / screen-off" regression: with the display off the bridge stops
capturing (capture=stopped) and the whole stack idles at <1 % CPU. Load average
reads ~12, but this is D-state kernel threads (8× `tz_worker_thread`,
`scsi_srpmb_work`, `tz_iwsock`, `dhd_rpm_state_t`), not CPU work — `/proc/stat`
shows <1 % total CPU.

## Wake validation
Wake via the supported `action screen-on` control path succeeds: `DISPLAY_ON`,
`actual_brightness=183`, FRAMES_OK resumes with `display=on`, first frame
healthy (no black/stale frame, `decon_pan_failed=0`). Direct writes to the
bridge FIFO alone are defeated by the button-manager's 60 s idle timer (stale
`last_activity_ms`), which is why the button-manager path must be used.

## Confounder for A50 measurements
The console cable is simultaneously the charging path (battery 93 %, "Charging",
USB PDIC). This makes the battery/charger/Wi-Fi drivers extremely chatty on
`/dev/kmsg`, intermittently shredding long framed console output. Short
single-shot reads are reliable; long continuous samplers are not while charging.
