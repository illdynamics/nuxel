# A63 host and device identity

Observed 2026-10-23 from the Fedora host over the framed USB live console.

- Host: Fedora/Linux, x86_64, kernel `6.17.1-300.fc43.x86_64`.
- Repository baseline: branch `main`, commit `c69781e`; A63 implementation commits are `6899841` and `57f803c`.
- Device: Samsung Galaxy S10+ SM-G975F Nuxel Fedora 43, aarch64, vendor kernel `4.14.253`.
- Console: USB CDC ACM, VID:PID `18d1:4ee7`, serial `NUXEL-S10PLUS-0001`, `/dev/ttyACM0` during this run.
- Private recovery directory: `/home/wicked/nuxel-rescue/a63/20261023T120045+0200` (mode 0700; payloads mode 0600).
- Separate recovery route: USB live console plus host-side verified backups; no partition, kernel, DTB, bootloader, modem or EFS writes.

The current boot is not a known-good interaction baseline: `/proc/cmdline` reports `androidboot.mode=charger`, no `sec_touchscreen` input node exists, and `nuxel-touch-arm.service` therefore fails. Prior recorded normal boots returned to Nuxel with touch. The automated reboot guard reports its 3/3 budget exhausted, so recovery requires an owner-performed normal power-on with USB disconnected, followed by reconnecting USB.
