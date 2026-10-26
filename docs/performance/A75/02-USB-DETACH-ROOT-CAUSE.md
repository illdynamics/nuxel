# A75 — USB Detach Root Cause and State Model

## Historical root cause (A74, already fixed and still deployed)
The prior owner-reported hang/reboot on unplug was traced to the DWC3 debugfs
`link_state` read. On the S10+ downstream 4.14 kernel, reading that debugfs
attribute after a physical detach dereferences DWC3 controller registers while
the controller can be runtime-suspended (FSYS0 powered off), producing a bus
`SLVERR` that escalates to a hard lockup on the reading CPU and a watchdog
reset. Commit `909a9db` removed that read.

## Current state model (verified live, A73+A74 code)
Three independent truths are computed in-process by
`services/nuxel-bridge/src/system_indicators.py` (deployed sha matches repo):

1. **Charging** — from `power_supply` `status == "Charging"` only; "Full",
   "Not charging" and "Discharging" never light the charge animation. A host
   OTG/USB-host supply is excluded.
2. **PC-connected** — a configfs gadget bound to the SAME UDC whose state is
   exactly `configured`, **vetoed** by the Type-C `data_role` physical signal:
   after a real detach the resolved role leaves `[device]`, so a stale
   `configured` UDC cannot keep the icon lit.
3. **Live Console** — requires ALL of: `nuxel-console` daemon running, USB data
   link up, console tty registered, AND an open tty fd (or a validated
   start_ticks-bound lease). A bare `ttyGS0`, a bound gadget, or root access is
   never sufficient.

Live readback while the host is connected (correct):
```
charging.external_power: true, charging.charging: false (battery full)
usb_data.pc_connected: true, source "sysfs:udc:10c00000.dwc3:configured"
physical: ["typec:device-role"]
live_console.active: true, source "proc:nuxel-console:tty"
```

## Physical detach acceptance
`NOT_TESTED` — the USB CDC-ACM Live Console is the **only** recovery channel
and was not disconnected during this mission (mission rule 3). The code path is
covered by offline tests (see `test-system-indicators.py`: A74 DWC3 link_state
removal, Type-C veto, stale-UDC rejection, PID/lease staleness, and the six
reachable indicator combinations), but a physical unplug/replug must be run by
the owner with a prepared alternative recovery path before
`PASS_PHYSICAL` can be claimed.

## Required owner-supervised test (before physical claim)
Same boot_id before/after unplug (`/proc/sys/kernel/random/boot_id`), uptime
continues, PC + Live Console icons clear promptly, no hang/reboot, reconnect
restores both states, repeat ≥5×. Boot_id recorded throughout this mission:
`9ff44f39-69e4-4444-bb47-24ca923a0d69`.
