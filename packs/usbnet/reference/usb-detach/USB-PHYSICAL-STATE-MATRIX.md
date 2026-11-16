# NUXEL A73 — USB Physical State Matrix

## Root cause (why the ghosts existed)
The lockhead indicators derived "PC connected" solely from a configfs gadget
bound to a UDC whose `state == configured`, and "Live Console" from
`gadget_bound() && tty_registered` (native C) or a similar lease/tty check
(Python). On this Samsung 4.14 downstream kernel those signals **do not reliably
reflect a physical detach**:

- The gadget stays bound (`/sys/kernel/config/usb_gadget/nuxel/UDC` still reads
  `10c00000.dwc3`).
- The UDC `state` can remain `configured` (and the tty node / console daemon /
  lease survive), because the vendor controller does not always raise a clean
  gadget disconnect to the state machine on cable pull.

A wall charger / power-only cable also keeps the charger path active but must
never light PC or Live Console.

## Signals measured live (cable attached, host = macOS)
| signal | path | attached value |
|---|---|---|
| Type-C data role | `/sys/class/typec/port0/data_role` | `host [device]` |
| DWC3 link state | `/sys/kernel/debug/10c00000.dwc3/link_state` | `On` |
| UDC state | `/sys/class/udc/10c00000.dwc3/state` | `configured` |
| UDC speed | `/sys/class/udc/10c00000.dwc3/current_speed` | `high-speed` |
| Gadget UDC | `/sys/kernel/config/usb_gadget/nuxel/UDC` | `10c00000.dwc3` |
| MUIC attached dev | `/sys/devices/virtual/sec/switch/attached_dev` | `CDP` |
| VBUS | `/sys/devices/virtual/sec/switch/vbus_value` | `5` |
| android_usb state | `/sys/class/android_usb/android0/state` | `CONFIGURED` (diagnostic only) |
| power_supply ac | `/sys/class/power_supply/ac/online` | `1` (Mains) |
| power_supply usb | `/sys/class/power_supply/usb/online` | `0` |

## Algorithm truth table
`pc_connected` (both Python and native C) is now:

1. positive proof: bound gadget AND a bound UDC in exactly `configured`;
2. **physical detach veto**: if the Type-C class exists and reports no
   `[device]` role, OR the DWC3 `link_state` reads `Off`, the positive is
   vetoed (fail closed);
3. absent Type-C/debugfs (desktop/VM/no-typec kernels) leaves the UDC proof
   authoritative.

| Type-C data_role | dwc3 link_state | UDC | verdict |
|---|---|---|---|
| `[device]` | On | configured | **PC ON** |
| `[device]` | On | not attached / addressed | OFF (no UDC proof) |
| no `[device]` / none | * | configured | **OFF (veto)** |
| * | Off | configured | **OFF (veto)** |
| absent | absent | configured | ON (UDC authoritative) |
| absent | absent | not attached | OFF |

`live_console` is three layers, all required for `active`:
- `service_armed` — a `nuxel-console` process is alive (daemon state, NOT a
  display predicate);
- `transport_connected` — USB data link up (same vetoed predicate);
- `session_active` — daemon holds the console tty fd, or a validated lease
  names a live `nuxel-console` PID with matching `start_ticks`.

So: prestarted service without a host = OFF; open gadget tty without a host =
OFF; stale pid/lease after detach = OFF. The daemon is **never killed** to
extinguish its icon.

## Worst-case stale TTL
- Native host: uevent-driven refresh + 1 s signature fallback; on an explicit
  down signal (uevent/Type-C/link_state) the JS is pushed immediately.
- JS `lockscreen-indicators.js`: 3 s safety read while visible; a failed read
  fails PC/console closed (never charging).
- Bridge HTTP path: recomputed per request; no cached positive survives.

## Evidence collection (survives disconnect)
`/usr/lib/nuxel/a73-logger.sh` samples every 0.5 s (state-change + 15 s
heartbeat) to `/var/lib/nuxel/a73-usb-unplug.log`, capturing data_role,
link_state, UDC state/speed, ac/usb online, and the full `get_indicators()`
JSON. It runs `setsid`-detached so the unplug does not stop it.
