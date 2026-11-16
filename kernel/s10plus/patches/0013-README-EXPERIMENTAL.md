# 0013 — sensor-hub native bring-up: EXPERIMENTAL, not in the build series

The BCM47752 sensor-hub bring-up work exists as
`0013-nuxel-sensorhub-bringup-native-bbd.patch.experimental` and is **not
applied** by `build-kernel.sh` (only `*.patch` files are).

Why it was pulled from the series for v0.8.6-beta:

1. It superseded and duplicated every hunk of the required, proven
   `0020-nuxel-ssp-hub-power-and-pm.patch` (hub rail reference, keep the hub out
   of shutdown, probe registration) plus untested extras (BBD peers, GPS SPI
   IRQ depth, `ssp_i2c` zero-length forwarding, sysfs diagnostics). It can
   therefore not be applied after 0020 and the required 0020 must stay.
2. The extra behaviour has never produced a streaming hub on the live handset:
   `/run/nuxel-orientation/status.json` still reports `raw_data="0,0,0"`,
   `enable_bits=0`, `lhd_present=false`.

The patch is kept verbatim so the bring-up work is not lost. To resume it,
rebase it onto the current 0020 series, make it a single non-overlapping patch,
build it with `GNSS`/sensor-hub diagnostics enabled, and only re-add the
`.required` sidecar once a live boot proves `raw_live=true` on the device.
See `final-summary.md` §9 (auto-rotate sensors) for the current state.
