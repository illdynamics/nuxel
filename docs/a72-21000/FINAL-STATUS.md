# NUXEL A72 / 21000 — FINAL STATUS (honest)

**Date:** 2026-10-25 (~16:00–16:30 CEST)
**Agent:** one writer, macOS host `infranux` (Darwin 24.6.0 arm64)
**Transport:** USB CDC-ACM Live Console `/dev/cu.usbmodem101` (18d1:4ee7, NUXEL-S10PLUS-0001)
**Target:** Samsung Galaxy S10+ SM-G975F (beyond2lte), Linux `4.14.253 #15 aarch64`, Fedora 43
**Repo HEAD:** `fe3ccd0` (working-tree A70/A71 WIP preserved, not reset)

## Headline
- Owner's internet baseline **CONFIRMED live** (Wi-Fi + DNS + TLS verified). T36 PASS_PHYSICAL.
- **Repo↔live delta found**: the deployed phone is AHEAD of repo HEAD in `status-bar.js`
  and `home-settings.js` (A66-02 empty-read guard / lock-after-off). Preserved + snapshotted.
- **dnf5 bootstrap designed**: exactly 13 signed Fedora 43 aarch64 RPMs (4.1 MiB, additive-only,
  no glibc/systemd/rpm/python upgrade). PENDING OWNER APPROVAL to install.
- **Maps online deployed + verified** (OSM tiles one-tap + Nominatim place search).
- Audio / rotation / GNSS / NFC / BT remain **firmware/dependency-blocked** with precise,
  re-measured evidence. Nothing faked.

## 13 objectives — current truth
| id | objective | status |
|---|---|---|
| A69-01 | lockscreen battery | PASS_DEVICE_RUNTIME (code+deploy verified; cold-boot visual pending owner reboot) |
| A69-02 | single nav bar | PASS_DEVICE_RUNTIME |
| A69-03 | speaker audio | BLOCKED_FIRMWARE (calliope_sram + cs47l93/cs35l40 DSP) |
| A69-04 | 7-mode rotation | BLOCKED_FIRMWARE (SSP down) |
| A69-05 | GPS + Maps | GNSS BLOCKED_FIRMWARE; Maps PASS_DEVICE_RUNTIME (this run) |
| A69-06 | NFC | BLOCKED_FIRMWARE/DRIVER |
| A69-07 | BT + A2DP | BLOCKED_DEPENDENCY (no BlueZ) + BLOCKED_FIRMWARE (HCD) |
| A69-08 | USB-C DAC/headset | NOT_TESTED (BLOCKED_EQUIPMENT) |
| A69-09 | VLC + music | BLOCKED_DEPENDENCY (dnf absent; dnf5 planned) |
| A69-10 | volume latency | PASS_DEVICE_RUNTIME (visual); audible BLOCKED_FIRMWARE |
| A69-11 | performance | PASS_OFFLINE_ONLY (baseline captured) |
| A69-12 | animations | PASS_OFFLINE_ONLY |
| A69-13 | app foregrounding | PASS_DEVICE_RUNTIME |

## Packages/firmware
- Installed this run: NONE (no rpm transaction without approval). Maps PWA deployed (3 files).
- Researched (not installed): dnf5+12 deps (approval-gated); BlueZ/pipewire/alsa-utils/vlc/mpv
  are available in Fedora 43 aarch64 but wait for dnf5.
- Firmware: calliope_sram.bin, vts.bin, cs47l93-dsp*, cs35l40-dsp*, BCM43xx HCD, SSP, NFC —
  all vendor/Cirrus-proprietary, not in linux-firmware, not fetched. Owner-supplied,
  licensed/provenanced files would unblock; details in 05/06/07/08.

## Evidence / measurements
- Internet: wlan0 connected, route via 192.168.178.1, TLS HTTP/2 302 (fedoraproject.org).
- Repo↔live hash table: 01-REPO-LIVE-DELTA.md (15 files match; 2 device-ahead).
- Audio: journal `calliope_sram.bin ... error -2`; `nuxelctl audio status` BLOCKED_FIRMWARE.
- Sensors: `ssp_down==true`, raw `0,0,0`. NFC: `sec-nfc@27` present, no bound device.
- Maps: OSM tile HTTP/2 200 + CORS, Nominatim JSON verified from phone; deployed hash-verified.
- Perf baseline: load 14.13, WebKitWebProcess 26.7% CPU, thermal BIG 62°C.

## Backups / rollback
- `/var/lib/nuxel/a72-backup-20261025T152149Z/` (symlink `a72-backup-latest`) + MANIFEST.sha256.
- `docs/a72-21000/ROLLBACK.sh` (reviewed; never reboots/flashes without approval).
- Recovery: USB Live Console reachable before/after every change.

## Next actions (in priority order)
1. **Owner approval** → run `docs/a72-21000/dnf5-bootstrap.sh` (13 RPMs) on the phone.
2. After dnf5: `alsa-utils` (diagnose real mixer), then `pipewire`/`wireplumber`, `bluez`,
   `vlc`, `mpv` — small signed transactions, each verified + rolled back independently.
3. Owner-supplied firmware (Cirrus/SSP/BCM HCD/NFC) for the hardware-blocked items, with
   licence/provenance + isolated reversible test.
4. Owner interactive session: Back/Home/Tabs, drawer launch, 10 wake cycles, 3 cold boots,
   physical touch animation check (T02–T06, T21, T25–T29, T31–T34).

## Hard completion contract
This run did NOT declare the phone "finished". It established a truthful baseline, protected
the device-ahead work, recovered a correct dnf5 path, shipped a real Maps improvement, and
documented exact firmware boundaries. Remaining items are gated on owner approval + owner
firmware/accessories + owner physical interaction — each called out precisely.
