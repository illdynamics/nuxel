# `configs/nuxel/leds/` — flashlight, notification LED and edge lighting (areas 9, 22)

| File | Install to | Purpose |
|---|---|---|
| `leds.json` | `/etc/nuxel/leds/leds.json` | LED-class candidates, safety limits, explicit-off/state file, truthful class expectations |
| `nuxel-led-state.json` | `/var/lib/nuxel/leds/state.json` | Runtime state (which class is on, bounded ON deadline) — created on first use |

## Honest boundaries

* Which LED classes the hardware exposes is **enumerated** and printed. A class
  that is absent is reported `NOT_SUPPORTED_ON_DEVICE` — never emulated.
* **Edge lighting on the S10+ is a display effect on the curved AMOLED, not a
  separate LED.** It is modelled as `display_overlay` (`hardware_led: false`)
  and depends on the display bridge; it is not claimed as working.
* The torch is a real emitter: the ON time is capped at 60 s, it requires an
  explicit `--yes`, and it is switched **off** on exit and never at boot.

## Commands

```sh
nuxel-led-diag.sh status            # classes found, real paths, current ON/OFF
nuxel-led-diag.sh status --json
nuxel-led-diag.sh flash --yes 3000  # torch on for 3 s, then forced OFF
nuxel-led-diag.sh off               # explicit OFF for every class found
nuxel-led-diag.sh notify red        # notification-LED colour/blink (if the class exists)
nuxel-led-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/09-flashlight.md`.
