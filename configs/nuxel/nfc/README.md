# `configs/nuxel/nfc/` — NFC controller + tag reading (area 24)

| File | Install to | Purpose |
|---|---|---|
| `nfc.json` | `/etc/nuxel/nfc/nfc.json` | Evidence sources, stage order, verdicts, owner tag procedure |

## Honest boundaries

* The controller is a **Samsung sec-nfc (S3FWRN5-family) @ I2C 0x27** with an
  embedded SE. Presence is **enumerated** (`/dev/nfc*`, `/sys/class/nfc`,
  `/sys/bus/i2c/devices`, `/proc/modules`), never assumed.
* **Configuration alone is never a working NFC.** The verdict names the FIRST
  failing stage (`controller → firmware → subsystem → stack → tag`) and the
  terminal state stays `NEEDS_OWNER_TEST` until a **physical tag** is read and
  its UID matches.
* If the vendor kernel provides no usable controller driver the verdict is
  `BLOCKED_KERNEL` / `NOT_SUPPORTED_ON_DEVICE`; no UID is ever fabricated.
* No flashing surface: no partition writes, no bootloader, no Odin/Heimdall.

## Commands

```sh
nuxel-nfc-diag.sh status [--json]   # per-stage evidence + first failing stage + verdict
nuxel-nfc-diag.sh firmware          # NFC firmware candidate inventory
nuxel-nfc-diag.sh read [secs]       # bounded read hint via the real client (owner action)
nuxel-nfc-diag.sh selftest
```

Owner procedure: `docs/beta-finalization/manual-proof/12-nfc.md`.
