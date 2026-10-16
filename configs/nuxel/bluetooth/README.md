# `configs/nuxel/bluetooth/` — Bluetooth stack configuration (area 23)

| File | Install to | Purpose |
|---|---|---|
| `bluetooth.json` | `/etc/nuxel/bluetooth/bluetooth.json` | Evidence sources, stage order, verdicts, owner pairing procedure |
| `main.conf.d/60-nuxel.conf` | `/etc/bluetooth/main.conf.d/60-nuxel.conf` | BlueZ drop-in: **AutoEnable = false**, dual mode, device privacy |

## Honest boundaries

* Adapter presence, **rfkill** state, module binding, HCD firmware and the
  bluetoothd service are each reported per stage, and the **first failing stage**
  is named. A registered module is not proof the radio works.
* `AutoEnable = false`: nothing powers the adapter at boot, ever.
* No pairing, no scanning and no connect happens without an explicit owner
  command (`on`, `scan`, then `bluetoothctl`). Pairing is `NEEDS_OWNER_TEST`.
* If no adapter, no rfkill entry and no module exist, the verdict is
  `BLOCKED_HARDWARE`; if the module path exists but no HCD blob is present it is
  `BLOCKED_FIRMWARE`. Both are stated with the evidence that produced them.

## Commands

```sh
nuxel-bluetooth-diag.sh status [--json]   # per-stage evidence + first failing stage + verdict
nuxel-bluetooth-diag.sh firmware          # HCD candidate inventory
nuxel-bluetooth-diag.sh on | off          # explicit adapter power (rfkill/bluetoothctl)
nuxel-bluetooth-diag.sh scan [secs]       # bounded scan (default 10, max 60)
nuxel-bluetooth-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/11-bluetooth.md`.
