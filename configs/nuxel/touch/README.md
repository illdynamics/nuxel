# configs/nuxel/touch/ — boot-mode guard for the S10+ touchscreen

> **Canonical location:** the guard configuration now has its own subpath,
> `configs/nuxel/bootmode/` (`bootmode-guard.json` + `README.md`), and
> `nuxel-bootmode-guard.py` searches it **first**. The copy here is kept unchanged
> because an already-generated deploy plan names this path as the source for
> `/etc/nuxel/touch/bootmode-guard.json`;
> `tools/s10plus/a33/tests/test-bootmode-guard.py` asserts the two files agree on
> every gate field, so the duplication is enforced rather than trusted. The systemd
> units stay here (they are not configuration).

Files
-----
| File | Installed to | Purpose |
|---|---|---|
| `bootmode-guard.json` | `/etc/nuxel/touch/bootmode-guard.json` | gate configuration (reboot off by default) |
| `nuxel-bootmode-guard.service` | `/usr/lib/systemd/system/` | classify the boot, publish state, never act |
| `nuxel-bootmode-reboot.service` | `/usr/lib/systemd/system/` | optional guarded normal reboot (shipped disabled) |

What it is for
--------------
When S-Boot powers the board up from off with a charger attached it passes
`androidboot.mode=charger`; `sec_bat_is_lpm_check()` turns that into `lpcharge=1`;
`sec_ts_init()` then returns `-ENODEV` before `i2c_add_driver()`, so **no
touchscreen device exists at all on that boot**. The panel is also not driven in
that mode, so there is nothing to interact with. The full analysis, the evidence
and the not-deployed kernel patch are in
`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`.

Published interface (no launcher code is changed here)
-----------------------------------------------------
`/run/nuxel-bootmode.json` is the contract for whoever renders the message:

```json
{
  "mode": "charger-lpm | normal | unknown",
  "touch_available": false,
  "headline": "touch disabled (charging-mode boot)",
  "message": "charging-mode boot: touch is disabled on this boot. Unplug the charger and reboot normally (or wait for the guarded automatic normal reboot) to get an interactive screen.",
  "action": "unplug-and-normal-reboot",
  "permanent_fix": "BLOCKED_KERNEL BOOT_UPDATE_REQUIRED NOT_DEPLOYED",
  "graded": true,
  "evidence": [{"why": "...", "origin": "/proc/cmdline", "line": "..."}]
}
```

The Nuxel Home status bar / notification surface is owned by the launcher work;
this config only guarantees the file exists with those keys, and that
`mode == "unknown"` is never presented as a pass.

Verify offline (no phone)
-------------------------
```
python3 tools/s10plus/a33/nuxel-bootmode-guard.py \
  --offline-fixture tools/s10plus/a33/tests/fixtures/bootmode/lpm-boot --no-write
python3 tools/s10plus/a33/tests/test-bootmode-guard.py
```
