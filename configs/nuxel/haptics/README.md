# `configs/nuxel/haptics/` — vibration / haptics (area 21)

| File | Install to | Purpose |
|---|---|---|
| `haptics.json` | `/etc/nuxel/haptics/haptics.json` | Node candidates, global switch, intensity levels, named patterns, the gated programmatic API, consumers |
| `bridge.json` | `/etc/nuxel/haptics/bridge.json` | Event → pattern wiring for the button manager and the notification daemon (pure data) |
| `nuxel-haptics-bridge.service` | `/usr/lib/systemd/user/nuxel-haptics-bridge.service` | Session unit that owns the API gate and runs the bridge |
| `nuxel-haptics.state.json` | `/var/lib/nuxel/haptics/state.json` | Runtime state (enabled flag, default intensity) — created on first use |

## Honest boundaries

* The actuator node is **enumerated** from `/sys/class/leds/*vib*`,
  `/sys/class/timed_output/*` and `/sys/class/vibrator/*`. No path is assumed;
  the real path and the writable files are printed in `status`.
* A node existing is **not** proof that anything is *felt*. Felt haptics are
  `NEEDS_OWNER_TEST`; only the API/pattern expansion, the gate, the rate limit
  and the refuse-when-off behaviour are `OFFLINE_TESTED`.
* Nothing buzzes at boot. The one bounded test buzz runs only on an explicit
  `buzz --yes` from the owner and is capped at 1500 ms.
* If the node exposes no amplitude control, intensity is reported as
  `intensity_mode=duration` — the tool never claims a strength write it did not
  make.

## Two surfaces, one switch

| Surface | Who uses it | Gate |
|---|---|---|
| **Owner** `buzz --yes <ms>` | a human at the console | none (it *is* the human action) |
| **Programmatic** `api <pattern> --source <who>` | button manager, notifier — always through `nuxel-haptics-bridge` | refuses unless `/run/nuxel/haptics/api-enabled` exists (armed by the session unit only) |

Both surfaces consult the **same** persisted global switch
(`/var/lib/nuxel/haptics/state.json`). `off` silences everything at once; the
bridge only ever *reads* that file, so nothing re-enables haptics behind the
owner's back.

Why the gate exists: a system daemon (the button manager, the notifier) must not
be able to buzz while no user session is up, and nothing may buzz during boot.
The gate makes both properties **structural**:

```
session starts  -> nuxel-haptics-bridge arms  /run/nuxel/haptics/api-enabled
session exits   -> bridge disarms it           (and systemd clears the dir)
no session      -> api refuses, exit 7        "gate closed"
```

## Wiring (what is actually connected)

```
button manager (system)                 notification daemon (system)
  /var/log/nuxel/buttons.log              /var/lib/nuxel/notifications.json
  "FSM_ACTION source=… action=…"          org.freedesktop.Notifications.NotificationAdded
             │                                       │
             └──────────────┬────────────────────────┘
                            ▼
             nuxel-haptics-bridge (user session unit)
               bridge.json: action/urgency → pattern
               quiet hours, per-consumer rate limit, skip list
                            │  api <pattern> --source <consumer>
                            ▼
             nuxel-haptics-diag.sh  ── gated by the global switch ──► /sys/class/leds/*vib*
```

`/run/nuxel-haptics.cmd` is the optional request FIFO for exact press-time
haptics and for the clock app's alarm:

```sh
printf 'button volume-up\n' > /run/nuxel-haptics.cmd
printf 'pattern double\n'   > /run/nuxel-haptics.cmd
printf 'off\n'              > /run/nuxel-haptics.cmd   # 30 s panic silence
```

The FIFO only exists while the bridge runs, so a writer with no session is a
silent no-op — never an error storm and never a buzz.

## Commands

```sh
nuxel-haptics-diag.sh status           # node, writable files, switch, intensity, API gate
nuxel-haptics-diag.sh status --json
nuxel-haptics-diag.sh on | off         # global switch (persisted)
nuxel-haptics-diag.sh intensity 30     # 0..100
nuxel-haptics-diag.sh pattern notify   # expand a named pattern (dry run, no buzz)
nuxel-haptics-diag.sh buzz --yes 300   # ONE bounded test buzz; refuses without --yes
nuxel-haptics-diag.sh api notify --source test   # programmatic (refuses when not armed)
nuxel-haptics-diag.sh arm | disarm     # what the session unit does
nuxel-haptics-diag.sh selftest

nuxel-haptics-bridge.py --status
nuxel-haptics-bridge.py --selftest                 # offline wiring proof
nuxel-haptics-bridge.py --once-event volume-up     # one event, honouring every gate
nuxel-haptics-bridge.py --follow                   # the session service runs this
```

## Integration status (truthful)

* **Button manager (bg-03, `tools/s10plus/a33/nuxel-button-manager.c`)** — its
  action stream is already wired: the daemon writes `FSM_ACTION source=… action=…`
  to `/var/log/nuxel/buttons.log` and the bridge maps those action names to
  patterns, so **no change to the daemon is required for action haptics**.
  Press-time (key-down) haptics need one line in that daemon. The daemon file is
  owned by another in-flight build group, so the change is **not applied here**;
  the exact one-line addition is:

  ```c
  /* in the EV_KEY branch, right after nuxel_fsm_feed(...) produced an action */
  fifo_send("/run/nuxel-haptics.cmd", "button volume-up\n");   /* or the action id */
  ```

  Until that line lands, button haptics fire on the *action* (which is logged)
  rather than on the raw press.
* **Notifications (bg-04, `services/nuxel-notifications/`)** — the notifier's
  persisted state file and its `NotificationAdded` signal are both consumed by
  the bridge; again no change to that service is required.
* **Global off switch** — fully wired: `nuxel-haptics-diag.sh off` refuses both
  surfaces and the bridge's `switch_on()` check fails closed for every consumer.

Owner procedure: `docs/beta-finalization/manual-proof/10-vibration.md`.
