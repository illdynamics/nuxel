# GNSS / GPS report — PWNAGE 64000

## Final status: `IMPLEMENTED — HARDWARE VERIFICATION REQUIRED` / **`BLOCKED_FIRMWARE`**

The repository-side completion work is implemented, deployed and verified on
the S10+. No satellite fix is claimed.

## Live inventory (after deployment)

```
state: BLOCKED_FIRMWARE
first_failing_stage: firmware
device_node: node:/dev/ttyBCM
module: bound:/sys/bus/spi/drivers/brcm gps spi/spi17.0
firmware: loader-only:/dev/bbd_patch
vendor_runtime: missing:lhd,gpsd,android_linker,lhd_config,gps_config,gnss_hidl_impl
userspace: no-consumer
stream: readable:/dev/ttyBCM
protocol: broadcom-bbd-lhd-rpc
nmea_stream: false
fix_verified: false
GPS_PWR_EN: 0
```

Canonical bridge inventory (`gnss_inventory.bridge_inventory("/")`):

```
present=true driver_bound=true spi_bindings=["spi17.0"]
firmware_present=false firmware_loaded=false fix_supported=false
vendor_runtime.complete=false
blocker="no compatible BCM4773 BBD sensor-hub patch firmware (vendor lhd expects /dev/bbd_patch)"
```

`/dev/bbd_patch` is classified as a **loader**, never as firmware. Generic
`gps.bin`/`gnss.bin`/`ssp*` and BCM47752/47755 images are rejected. Network
GeoClue remains a separate `network_*` source and is not reported as GNSS.

## Work completed this run

- Fixed `gnss_inventory.bridge_inventory()`: unbound `blocker` on a fully
  populated path, fake-root `spi_bindings()` path join, duplicate `bbd_nodes`,
  and vendor-runtime `complete` key leakage.
- Refactored `bridge.LocationConnector._gnss_hardware()` to consume the single
  canonical inventory instead of a duplicate candidate list.
- Fixed the diagnostic self-test: fixture discovery, bounded subprocess per
  fixture, and an honest `SKIP` on installed hosts without the host-only corpus.
- Corrected the JSON protocol label to `broadcom-bbd-lhd-rpc` and
  `nmea_stream=false` when no stream exists.
- Added `tests/pwnage64000` (10 tests) and userspace-only
  `tools/s10plus/a64/{deploy,rollback}-pwnage64000.sh`.
- Deployed policy/diagnostic/bridge module to the phone; bridge health 200;
  no GPS rail write and no BBD node open.

## Blocker

The exact BCM4773 BBD/LHD sensor-hub patch (`bcm_sensorhub_a1.patch` family) is
absent from every Nuxel path and there is no native BBD/LHD decoder. The vendor
`lhd`/`gpsd` path is Android/Bionic + HIDL. A fix requires the owner-provided
matching patch (provenance/hash/ABI) plus a native protocol provider, followed
by the outdoor cold/warm/no-sky tests in `full-pwnage-64000.md`.

## Tests

- `tests/pwnage64000`: **10 passed**
- `tests/pwnage42000` GNSS provider: **13 passed**
- `tools/s10plus/a33/tests/hw-subsystems/test-gnss-diag.py`: **all checks PASS**
- diagnostic selftest: 5 fixtures PASS on the host; installed host reports an
  explicit SKIP (no fixtures), not a hang or a false PASS.
