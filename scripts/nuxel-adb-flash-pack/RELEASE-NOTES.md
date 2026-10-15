# Nuxel ADB Flash Pack — release notes

Built 2026-10-14. Hosts: macOS / Linux with Python >=3.9 + Android platform-tools.

## What was tested

- BOOT/USERDATA simulated end-to-end ADB flash: host backup, optional recovery backup, rootfs write, full rootfs SHA-256 readback, boot write, full boot SHA-256 readback, receipt state verified.
- Simulator refused missing `--execute`, incorrect interactive confirmation, mismatching readback SHA, mounted `/data`, and incorrect S10+ device identity.
- Offline unit tests covered G7 Power A/B slot selection, forbidden partitions, format guard, partition size guard, and required explicit targets.
- All shell scripts syntax-checked (`bash -n`), and Python script compiled.
- **No real phone was flashed or tested with this pack.** The G7 profile remains dependent on verified hardware partition/slot layout and boot chain.

## Design notes

- The S10+ profile matches the verified `beyond2lte` recovery configuration from this conversation: `/dev/block/by-name/boot` + `/dev/block/by-name/userdata`.
- The G7 Power `ocean` profile is deliberately not wired to S10+ USERDATA by default; pass explicit device-specific partitions. Only active A/B boot slot accepted.
- All device partition writes are gated by `--action flash --execute` and a typed exact confirmation phrase; to overwrite USERDATA a second confirmation is required.
- Full readbacks stream without buffering all of the 4 GiB rootfs in memory, but USB reads can be slow.
- No USB reset, flashing protocol switch, reboot, wipe, partition table edits, root provisioning, or filesystem mounts.
