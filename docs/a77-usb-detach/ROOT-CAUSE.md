# A77 — ghost PC + Live Console penguins after USB disconnect

**Device:** Samsung Galaxy S10+ (SM-G975F, beyond2lte), Linux 4.14.253, Fedora 43
**Release:** v0.6.6-beta
**Symptom:** after connecting the phone to a PC and then physically unplugging
the cable, the cyan "USB connected to PC" penguin and the amber "Live Console
active" penguin stayed lit. Charging behaved correctly.

## Why A73/A74 never cleared them

The A73/A74 physical-detach veto trusted the Type-C resolved data role:

```
/sys/class/typec/port0/data_role   ->  host [device]   # attached
                                      host [device]   # AFTER unplug (stale)
```

The owner's on-device detach logger (`/var/lib/nuxel/a74-usb-unplug.log`)
records both provider inputs across a real cable pull:

| signal | attached | after physical unplug |
|---|---|---|
| `typec/port0/data_role` | `host [device]` | **`host [device]` (unchanged, stale)** |
| `udc/10c00000.dwc3/state` | `configured` | **`configured` (unchanged, stale)** |
| `udc/10c00000.dwc3/current_speed` | `high-speed` | **`UNKNOWN`** |
| `power_supply/ac/online` | `1` | **`0`** |
| `power_supply/battery/external_power` | true | **false** |

So the only A73 veto condition (`typec == 0`, i.e. no `[device]` role) is never
true on this board after a real detach. The bridge and the native PWA host both
therefore kept `pc_connected: true`, and because the Live Console predicate is
gated by the USB data link, the console icon stayed lit too. The 3 s lockscreen
safety poll was working — it was fed a stale "true".

## Fix (A77)

The truth model now requires the positive enumeration proof **and** fails
closed on any independent detach signal:

1. **UDC speed veto** — a bound gadget whose UDC state is `configured` but whose
   `current_speed` is a readable non-connected value (`UNKNOWN`) is detached.
   A readable connected speed (`low-speed` … `super-speed-plus`) is neutral.
2. **Wired VBUS veto** — a bus-powered USB gadget cannot carry a data link
   without VBUS. If every readable wired supply (`usb`, `ac`, `mains`, …)
   reports `online=0`, the link is down. Wireless charging is deliberately
   excluded because it never carries data.
3. **Type-C role veto** — retained for kernels where the resolved role really
   does leave `[device]`.

Absent attributes remain neutral, so desktops/VMs and older kernels keep the
UDC proof authoritative. No `link_state` debugfs read was reintroduced (A74:
that read hard-locked the downstream 4.14 kernel after detach).

## Implementations

| Provider | File | Consumer |
|---|---|---|
| Python bridge | `services/nuxel-bridge/src/system_indicators.py` | HTTP `/api/v1/system/indicators` |
| Native phone host | `tools/s10plus/a45/nuxel-pwa-host.c` (and the `a33` source kept in lockstep) | `NuxelHost.statusRead('system-indicators')` |

`get_indicators()` now also reports `usb_data.vbus_present` and
`usb_data.udc_speeds` for field diagnosis. `live_console.active` remains gated
by `usb_data.pc_connected`, so clearing the data link clears **both** penguins
in the same read.

## Tests

| Suite | Result |
|---|---|
| `services/nuxel-bridge/test-system-indicators.py` | PASS (offline synthetic sysfs/proc; includes stale data_role + UNKNOWN speed + no-VBUS cases) |
| `tools/s10plus/a45/test-lockscreen-indicators.py` | PASS against **both** shipped C sources (`a33`, `a45`) |
| `tools/s10plus/a45/test-lockscreen-indicators.js` | PASS (DOM class truth, fail-closed reads, in-flight detach race) |

The synthetic detach fixtures encode the measured live values exactly, so the
regression is reproducible without unplugging the only recovery path.
