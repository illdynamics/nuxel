# `configs/nuxel/haptics/` — vibration / haptics (area 21)

| File | Install to | Purpose |
|---|---|---|
| `haptics.json` | `/etc/nuxel/haptics/haptics.json` | Node candidates, global switch, intensity levels, named patterns, consumers |
| `nuxel-haptics.state.json` | `/var/lib/nuxel/haptics/state.json` | Runtime state (enabled flag, default intensity) — created on first use |

## Honest boundaries

* The actuator node is **enumerated** from `/sys/class/leds/*vib*`,
  `/sys/class/timed_output/*` and `/sys/class/vibrator/*`. No path is assumed;
  the real path and the writable files are printed in `status`.
* A node existing is **not** proof that anything is *felt*. Felt haptics are
  `NEEDS_OWNER_TEST`; only the API/pattern expansion and the refuse-when-off
  behaviour are `OFFLINE_TESTED`.
* Nothing buzzes at boot. The one bounded test buzz runs only on an explicit
  `buzz --yes` from the owner and is capped at 1500 ms.
* If the node exposes no amplitude control, intensity is reported as
  `intensity_mode=duration` — the tool never claims a strength write it did not
  make.

## Commands

```sh
nuxel-haptics-diag.sh status           # node, writable files, switch, intensity mode
nuxel-haptics-diag.sh status --json
nuxel-haptics-diag.sh on | off         # global switch (persisted)
nuxel-haptics-diag.sh intensity 30     # 0..100
nuxel-haptics-diag.sh pattern notify   # expand a named pattern (dry run, no buzz)
nuxel-haptics-diag.sh buzz --yes 300   # ONE bounded test buzz; refuses without --yes
nuxel-haptics-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/10-vibration.md`.
