# S10+ bootloop: evidence-first decision tree

## Known facts from the actual phone

- Exynos Galaxy S10+ SM-G975F, `beyond2lte`, recovery TWRP 3.7.0_9-2, ADB root available.
- `androidboot.revision=26`, `region1=EUR`, `region2=OPEN`, `androidboot.dtbo_idx=9`, `androidboot.verifiedbootstate=orange` in the **recovery** cmdline.
- `/dev/block/by-name/boot -> /dev/block/sda14` (55 MiB), `/dev/block/by-name/userdata -> /dev/block/sda31` (~110.9 GiB).
- Merged boot image and full Fedora 43 ARM64 phone rootfs reported byte-identical SHA-256 readback from the phone.
- It subsequently bootloops at the Samsung logo. Verified bytes on storage do **not** prove kernel or firmware acceptance.

## Capture order

1. Keep the recovery accessible. Avoid reflashing, formatting, repeated restarts, or trying random DTBOs.
2. Immediately collect `02-pstore-capture.sh`, `03-last-kmsg-capture.sh`, and `04-twrp-recovery-logs.sh` — or run `12-full-diagnostics.sh`.
3. Read `TRIAGE.md`, but inspect the **exact surrounding raw lines**, timestamps and prior-boot source.
4. Inspect actual flashed images with `09-inspect-boot-image.sh` and `10-inspect-fedora-rootfs.sh`.
5. If a fix is justified, patch Nuxel source separately and preserve old image hashes and raw logs to compare before/after.

## Distinguish error stages

| Evidence | Hypothesis, not conclusion | Safe follow-up |
|---|---|---|
| pstore/last_kmsg contains early panic | kernel reached panic handler | review call stack, device tree, UFS probes, init path |
| `VFS: Unable to mount root fs` or missing `/newroot` | root resolver or ext4/storage driver | inspect initramfs root selection, partition discovery and ext4 support |
| PID 1 exec failure | wrong init path / missing ELF interpreter / incompatible binary | inspect `/init` then `/sbin/init`, linked libraries, and kernel CONFIG_BINFMT_ELF |
| `systemd[1]` errors after switch_root | userspace handoff succeeds; service/startup defect | inspect Fedora target units and early journal capture plan |
| DRM/DECON/DSI panel error | display pipeline failed | inspect exact kernel logs/DTB panel nodes/driver config; phosh alone won't help |
| no pstore and repeated Samsung logo | unknown early stage | inspect bootloader/reboot reason; plan UART/ramoops only after verified hardware approach |
| TWRP dmesg shows clean boot | **only TWRP** is healthy | do not conflate current recovery with failed Nuxel boot |

## Very early boot without logs

A phone can reboot before USB gadget or persistent kernel logging starts. For this stage, consider **source-side** changes to the kernel/initramfs in a separate controlled development workflow:

- Verify kernel command line isn't using an incompatible root path or `init=`; confirm early initramfs uses a working shell/interpreter.
- Confirm the initramfs includes UFS controller, SCSI block support, ext4 and devtmpfs needed to mount USERDATA; avoid assuming Android by-name symlinks before udev exists.
- Verify merged board DTB selection matches the device, and determine whether S-Boot still applies the DTBO overlay from a separate partition.
- Determine whether existing Samsung kernel supports persistent logging (`CONFIG_PSTORE`, `CONFIG_PSTORE_RAM`, ramoops reserved memory). The TWRP kernel's CONFIG values are not definitive for the Nuxel kernel.
- A UART/serial debug cable requires documented pins, correct voltage and safe physical interface. Never connect a generic RS-232 serial adapter to phone logic pins.
- UART/earlycon setup or changes to kernel reserved memory are **not automatic safe patches**: require independent hardware review and recoverability.

## No part of this kit modifies the installed BOOT/USERDATA images

If a later kernel patch requires another flash, continue using the separately audited recovery flash procedure, with backups, image verification and readback. Never repurpose diagnostic tools to execute unreviewed partition writes.
