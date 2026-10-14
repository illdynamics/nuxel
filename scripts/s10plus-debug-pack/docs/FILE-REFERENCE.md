# Evidence catalog

`captures/<session>/` may contain:

- `SESSION.txt`: time, host details and privacy notice.
- `CAPTURE-STATUS.tsv`: records read attempts, including missing optional files.
- `previous-boot/pstore-listing.txt`: pstore visibility.
- `pstore/console-ramoops-*`, `pstore/dmesg-ramoops-*`: previous-boot records when exposed.
- `previous-boot/last_kmsg.txt`: previous-boot kernel ring buffer if available.
- `previous-boot/boot-reason.txt`: reboot properties from recovery boot cmdline, **not the failed Nuxel cmdline**.
- `recovery/tmp/recovery.log`: TWRP log if available.
- `recovery/current-recovery-dmesg.txt`: current **TWRP** kernel log, not proof of Nuxel behavior.
- `device/partition-by-name.txt`, `device/proc-partitions.txt`, `device/mounts.txt`: hardware inventories.
- `kernel/recovery-config.gz`: current recovery kernel config if exposed.
- `host-*`: Mac-side USB snapshots.
- `boot-image/boot-analysis.json`: host-side structure, cmdline, DTB candidates, initramfs listing.
- `rootfs-image/`: readonly `debugfs` and `e2fsck -fn` evidence, including boot services / Fedora config.
- `TRIAGE.md`, `TRIAGE.json`: categorized lines to investigate, **not a definitive verdict**.

By default, all data stays on the Mac. Raw device serial numbers, carrier identifiers, command lines, IPs, Wi-Fi details or logs may be sensitive. The redacted sharing ZIP masks some identifiers and omits binary dumps; review it manually.
