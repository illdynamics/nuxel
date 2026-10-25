# NUXEL A72 / 21000 — 05-FIRMWARE-SOURCE-AND-ABI-AUDIT

Internet research was performed for each missing-firmware family. Conclusion:
all are Samsung/vendor/Cirrus-proprietary blobs that are NOT redistributable
from any upstream, kernel.org, or Fedora source. None is installed, none was
fetched from a third-party mirror.

## Missing firmware inventory (proven from boot journal + nuxelctl, this run)
| driver | requested file(s) | upstream? | verdict |
|---|---|---|---|
| samsung-abox / abox-core | `calliope_sram.bin`, `calliope_sram_2.bin` | no | BLOCKED_FIRMWARE |
| samsung-vts | `vts.bin` | no | BLOCKED_FIRMWARE (voice trigger only) |
| beyond-madera (CS47L93) | `cs47l93-dsp{,-1,-2}.wmfw/.bin` | no (linux-firmware has cs35l41 only) | BLOCKED_FIRMWARE |
| CS35L40 amps | `cs35l40-dsp1/2.wmfw/.bin` | no | BLOCKED_FIRMWARE |
| bcm43xx BT | BCM43xx `.hcd` (driver probed; HCI never registered) | no | BLOCKED_FIRMWARE/DEPENDENCY |
| SSP BCM47752 | sensor-hub firmware | no | BLOCKED_FIRMWARE (ssp_down) |
| sec-nfc@27 | NFC controller firmware | no | BLOCKED_FIRMWARE/DRIVER |

## Evidence
- boot journal: `samsung-abox 18c50000.abox: Direct firmware load for calliope_sram.bin failed with error -2` (also `calliope_sram_2.bin`, `samsung-abox-core`), `samsung-vts: vts.bin failed`.
- kernel cmdline sets `firmware_class.path=/vendor/firmware`; that path is empty on the Nuxel rootfs.
- `nuxelctl audio status` lists the Cirrus DSP set as ABSENT.
- linux-firmware `cirrus/` contains `cs35l41-*` DSP only — no `cs47l93`, no `cs35l40`, no `calliope_sram`.
- BT: `[BT] bcm43xx_bluetooth_probe.` / `probe End` in journal but no `hci0` registration; rfkill0 `bcm43xx Bluetooth` soft=1.

## ABI boundary (no kernel change allowed/needed in 21000)
- Audio: ABox calliope DSP + Cirrus codec DSP + UCM profile are all userspace/firmware
  layers; the 4.14 ASoC drivers are present and the ALSA card `beyond-madera` enumerates.
- Rotation/GNSS: SSP sensor-hub firmware + userspace protocol daemon, not a kernel swap.
- NFC: driver registered (`sec-nfc`) but no bound device — needs firmware/power/GPIO
  investigation, distinct from an app.

## Next action if owner can supply blobs
Owner-supplied, license/provenance-verified firmware staged under `/lib/firmware`
(or `/vendor/firmware`) with recorded sha256, then an isolated, reversible per-
service test. No blobs were fetched or installed this run.
