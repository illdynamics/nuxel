# `configs/nuxel/modem/` — SIM, cellular status and microSD (area 26 / manual 16 + 18)

| File | Install to | Purpose |
|---|---|---|
| `modem.json` | `/etc/nuxel/modem/modem.json` | Shannon LTE truth, host-transport candidates, ModemManager plugin paths, SIM sources, redaction rules, APN template, read-only AT allowlist, protected-partition denylist |
| `microsd.json` | `/etc/nuxel/modem/microsd.json` | microSD detection/mount policy: internal-vs-external denylist, supported filesystems, read-only default, auto-mount contract, never-format/never-partition invariants |
| `90-nuxel-microsd.rules` | `/etc/udev/rules.d/90-nuxel-microsd.rules` | udev: an EXTERNAL card appearing asks systemd for one read-only auto-mount; internal `mmcblk0` never matches |
| `nuxel-microsd-automount.service` | `/etc/systemd/system/nuxel-microsd-automount.service` | oneshot, non-looping service that runs `nuxel-microsd-diag.sh automount` |

Runtime state: `/var/lib/nuxel/modem/sim.json` (SIM detection), `/var/lib/nuxel/microsd/state.json`.

## Honest boundaries

* **The modem is a known Blocker, not a feature.** There is no upstream
  ModemManager plugin for the Samsung Shannon LTE modem, so the default verdict is
  `NOT_SUPPORTED_ON_DEVICE` / `BLOCKED_FIRMWARE`. **Calls, SMS and mobile data are
  not available and are never claimed.** See `docs/volte-carrier-strategy.md`.
* A CP node or a `rmnet*` netdev is a **transport**, never a working modem. The
  tool prints `signal_quality`, `operator` and `registration_state` **only** from a
  live ModemManager query; otherwise they are `null`, and
  `"cellular_available": false` / `"registration_verified": false` on every line.
* **Nothing about EFS/IMEI/calibration/modem firmware is ever read, written or
  flashed.** Heimdall/Odin/fastboot/Download Mode/TWRP are on the denylist.
* An AT channel is **off by default**: only an explicit `--yes-at` with a
  read-only allowlisted command is accepted, and radio-state/NV/EFS/APDU commands
  are refused outright. Nothing probes the modem at boot.
* IMSI/ICCID/IMEI/ESN/MEID/MSISDN/SPN/PIN/PUK are **redacted** on every modem line.
* microSD: the internal UFS storage (`/dev/mmcblk0*`) is **never** a card target;
  `/dev/block/*` is refused; media is **never formatted or partitioned**; the
  default mount is **read-only** and existing data is preserved.
* microSD **auto-mount is insert-only and boot-window aware**: the kernel replays
  the same "add" uevent for a card that was already seated, so `automount`
  refuses inside the first `automount.boot_grace_s` (120 s) of uptime and reports
  the skip, while `diagnostics.auto_mount_on_boot` stays `false`. It is
  read-only-only, idempotent, external-card-only, refuses an unknown filesystem,
  and the owner can silence it with `automount-off`.

## Commands

```sh
nuxel-modem-diag.sh status [--json]     # transport + plugin + SIM + verdict
nuxel-modem-diag.sh interfaces          # CP nodes and possible netdevs
nuxel-modem-diag.sh plugin              # ModemManager plugin / mmcli situation
nuxel-modem-diag.sh sim                 # SIM presence from a real source only
nuxel-modem-diag.sh redact              # mask IMSI/ICCID/IMEI/PIN on stdin
nuxel-modem-diag.sh at --yes-at <CMD>   # allowlisted read-only AT (owner action)
nuxel-modem-diag.sh selftest            # 4 offline fixtures

nuxel-microsd-diag.sh status [--json]   # controller + internal/external + mounts + verdict
nuxel-microsd-diag.sh cards             # hosts, internal (never a target), external, supported fs
nuxel-microsd-diag.sh mount <dev> [--rw --yes] [--fstype T]
nuxel-microsd-diag.sh unmount <dev>|--all
nuxel-microsd-diag.sh eject <dev>
nuxel-microsd-diag.sh automount         # what the udev rule/service calls (insert only, ro)
nuxel-microsd-diag.sh automount-on|off|status
nuxel-microsd-diag.sh selftest          # 6 offline fixtures
```

Owner procedures:
`docs/beta-finalization/manual-proof/16-sim-mobile-data.md`,
`docs/beta-finalization/manual-proof/18-microsd.md`.
