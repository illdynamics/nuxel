# nuxel-gnss - native Broadcom BBD/LHD GNSS service (beyond2lte BCM4773)

Nuxel-native implementation of the Broadcom Bridge Driver (BBD) / LHD protocol
for the S10+ SM-G975F GNSS receiver, ported from the GPL-2.0 kernel source in
drivers/sensorhub/brcm/bbdpl/ on the device (/root/kbuild/).

## Components
- src/nuxel_bbd_tl.py - transport-layer framing, CRC-8, RPC framing/parse.
- src/nuxel_control.py - control strings, power/patch constants, patch parser.
- src/nuxel_lhd.py - native daemon (power lease, firmware provenance, transport
  open/wakeup, control exchange, bounded handshake, guaranteed cleanup).
- systemd/nuxel-gnss-lhd.service - systemd unit (least-privilege, bounded).
- tests/ - host-only unit tests (incl. the kernel sample1 framing vector).

## Honest boundary
The firmware (bcm_sensorhub_a1, AsicVersion=0x004775B0, BCM4773) is embedded in
the running kernel and served read-only via /dev/bbd_patch (SHA-256:
0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72).

This service implements everything up to the BBD communication boundary. The
GNSS position solution decode requires the proprietary Samsung
lhd/gpsd/libwrappergps application RPC map, which is not open-sourced and not
present here; the daemon therefore reports POSITION_DECODER_UNAVAILABLE instead
of fabricating a fix.

See docs/hardware/gps/ for the full architecture, blockers, reflash manifest,
and test report.
