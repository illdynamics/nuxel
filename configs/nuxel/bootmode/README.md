# configs/nuxel/bootmode/ — charger/LPM boot-mode guard (its own subpath)

The guard that classifies a **charger/LPM** boot — the boot on which the S10+
touchscreen driver deliberately does not initialise — has its own configuration
home here. It is not part of the touch-pipeline configuration directory.

| File | Installed to | Purpose |
|---|---|---|
| `bootmode-guard.json` | `/etc/nuxel/bootmode/bootmode-guard.json` | gate configuration; reboot disabled by default |

The systemd units and the tool stay where they are (they are not configuration):
`configs/nuxel/touch/nuxel-bootmode-guard.service`,
`configs/nuxel/touch/nuxel-bootmode-reboot.service` (shipped **disabled**) and
`tools/s10plus/a33/nuxel-bootmode-guard.py`.

## Why the guard exists

When S-Boot powers the board up **from off with a charger attached**, it passes
`androidboot.mode=charger`; `sec_bat_is_lpm_check()` turns that into
`lpcharge = 1`; `sec_ts_init()` then returns `-ENODEV` **before**
`i2c_add_driver()`, so no touchscreen device exists at all on that boot and the
panel is not driven either. Full analysis, the source-level path, the live
evidence and the not-deployed kernel patch:
`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`.

The permanent fix is therefore a kernel/early-boot change; it is written up in
`tools/s10plus/a33/kernel-patches/sec_ts-lpm-initcall-deferred-bind.patch` and is
marked **BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED**. It is not applied,
not compiled, not loaded and not flashed.

No userspace step can create that device: the driver is built in
(`=y`), there is no `/lib/modules` to reload it from, `CONFIG_KEXEC` is unset, and
the decision is taken before the driver ever owns an i2c client or an IRQ. Any
claim to the contrary would be fabricated. What userspace **can** do, and what this
configuration gates, is come up in normal mode: unplug and reboot normally, or let
the guard do exactly that once, behind every gate below.

## Search order (this subpath wins)

`nuxel-bootmode-guard.py` looks for the configuration in this order and uses the
first file that exists:

1. `--config FILE` (explicit, wins over everything)
2. `/etc/nuxel/bootmode/bootmode-guard.json`  ← this subpath
3. `configs/nuxel/bootmode/bootmode-guard.json` (running from the repository)
4. `/etc/nuxel/touch/bootmode-guard.json` (legacy deployed path)
5. `configs/nuxel/touch/bootmode-guard.json` (legacy repository path)

`configs/nuxel/touch/bootmode-guard.json` is retained unchanged because an
already-generated deploy plan names it as the source for
`/etc/nuxel/touch/bootmode-guard.json`. `tests/test-bootmode-guard.py` asserts the
two files **agree on every gate field**, so the duplication is enforced rather than
trusted.

## The gates, and what each one refuses

| Gate | Default | What it refuses |
|---|---|---|
| explicit request | `--status` | nothing happens without `--reboot` |
| acknowledgement | absent | `--reboot` alone never reboots; `--i-understand-this-reboots-the-phone` is required |
| `allow_reboot` | `false` | a config edit alone is not enough |
| owner-test locks | any present | a reboot during a capture/manual-proof session |
| `min_uptime_seconds` | 120 | a boot that becomes a reboot loop |
| `cooldown_seconds` | 900 | repeated reboots |
| `require_charger` | `true` | a reboot with no charger/charging (unreadable power state = refuse) |

`reboot_command` is `systemctl reboot` — userspace, systemd as PID 1. There is no
code path in the guard that writes a partition, a bootloader, a DTB, a modem, EFS
or a partition table, and there is no recovery/Download-Mode entry anywhere in it.

## Verify offline (no phone, no reboot)

```sh
python3 tools/s10plus/a33/nuxel-bootmode-guard.py \
  --offline-fixture tools/s10plus/a33/tests/fixtures/bootmode/lpm-boot --no-write
python3 tools/s10plus/a33/tests/test-bootmode-guard.py
```

The guard publishes state for both consumers (Settings and the live console):

| File | Contents |
|---|---|
| `/run/nuxel-bootmode.state` | `BOOTMODE=…`, `TOUCH_AVAILABLE=…`, `PERMANENT_FIX=…`, one `EVIDENCE_n=` per marker |
| `/run/nuxel-bootmode.json` | launcher/Settings-facing `headline`, `message`, `action`, `permanent_fix`, `graded` |
