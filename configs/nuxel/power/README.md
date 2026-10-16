# `configs/nuxel/power/` — power management, battery modes and power menu (area 17/18)

Everything in this directory is S10+ (beyond2lte) power policy. Install
locations, read by the tool at the time it runs:

| File | Install to | Purpose |
|---|---|---|
| `power.json` | `/etc/nuxel/power/power.json` | Single policy source: boot-mode detection, fuel-gauge field map, three battery profiles, charge-control policy, diagnostic field list |
| `power-menu.json` | `/etc/nuxel/power/power-menu.json` | Long-press POWER menu table (Lock / Restart / Power off / Recovery / Download Mode) with per-entry trigger gates |
| `nuxel-power-mode.service` | `/etc/systemd/system/nuxel-power-mode.service` | Applies the *persisted* profile once at boot; evidence-only, never changes the gate |

## What is deliberately NOT here

* **No charge-control writes.** `charger.allow_writes = false`. The tool reports
  charge state and whether a writable node exists; it does not poke charger
  voltage/current, because a bad write is a hardware risk that cannot be
  verified without the owner watching the handset.
* **No battery percentage claims from an assumed node.** The gauge device is
  enumerated from `/sys/class/power_supply/*` and the real name is reported. No
  gauge bound ⇒ `BLOCKED_KERNEL`, never an invented percentage.
* **No Recovery / Download Mode trigger.** Both entries exist and are
  offline-tested as *refusals*; they are hard-refused at execution time and
  require an in-person owner confirmation. The mission triggers no bootloader
  interface.
* **lpcharge / charger-mode** is treated as a *distinct boot mode*: Linux may
  start with `sec_ts` disabled before userspace runs. The remedy is an ordinary
  reboot — never a userspace kernel patch and never a flash.

## Commands (on the device)

```sh
nuxel-power-diag.sh status            # boot mode, gauge, charging, profile, governor
nuxel-power-diag.sh status --json     # machine-readable (Settings + bridge)
nuxel-power-diag.sh profiles          # the three profiles and what each changes
nuxel-power-diag.sh mode balanced     # apply + persist a profile (real governor/cgroup knobs)
nuxel-power-diag.sh menu              # the power-menu table with the refusal reason per entry
nuxel-power-diag.sh report            # status + append the evidence log
nuxel-power-diag.sh selftest          # offline fixtures (fake /sys + /proc)
```

Full design and the owner procedure:
`docs/beta-finalization/manual-proof/24-battery-power.md`.
