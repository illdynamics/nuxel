# Nuxel Samsung Galaxy S10+ — bootloop observability & debugging pack

**Target:** Samsung Galaxy S10+ Exynos SM-G975F (`beyond2lte`), reported board revision 26 / EUR OPEN, running TWRP 3.7.0_9-2. **Situation:** BOOT and USERDATA were flashed with ADB and matched byte-for-byte on readback, but the phone loops on the Samsung logo. Full Fedora 43 aarch64 rootfs contains Python, systemd, Phosh and Phoc. Hardware boot/display is **not yet verified**.

**Safety:** This is a standalone, **read-only** toolkit. No `adb push`, `dd of=`, `flash`, `reboot`, `remount`, `mount`, `umount`, `wipe`, `setprop`, `pstore` clearing, DTBO writes, or other phone changes. ADB recovery must be working. Local reports are stored under `captures/`. `13-verify-partition-readback.sh` optionally reads up to 4 GiB from USERDATA but never writes. Homebrew installation is explicit opt-in (`--apply`) on the Mac **only**.

## Quickest path after a Samsung-logo bootloop

1. Enter working TWRP recovery as soon as the failed boot is reproducible. Avoid reflashing or wiping anything; repeated reboots may overwrite recoverable evidence.
2. On the Mac, extract this ZIP, and from its top-level folder:

```bash
bash tools/doctor.sh
bash tools/install-mac-deps.sh               # preview only
# Only if needed and you approve Mac software installation:
bash tools/install-mac-deps.sh --apply
adb devices                                # should say recovery
bash nuxel-debug.sh collect
```

The launcher runs `scripts/12-full-diagnostics.sh` and prints its capture directory, e.g. `captures/20261014T194100Z-full-collection-12345/`. Start with `TRIAGE.md`, `pstore/`, `previous-boot/`, and `recovery/`.

If there are **no pstore or last_kmsg files**, that does **not** prove Nuxel never reached its kernel; a device reset can happen before durable logging, or its firmware/recovery can fail to preserve logs.

## What is included

| Script | Purpose | Prerequisites |
|---|---|---|
| `scripts/01-previous-boot-overview.sh` | Look for pstore/last_kmsg, reset reasons, recovery board properties | ADB TWRP |
| `scripts/02-pstore-capture.sh` | Copy all readable `/sys/fs/pstore/*` files to Mac | ADB TWRP |
| `scripts/03-last-kmsg-capture.sh` | Read `/proc/last_kmsg` exactly, if available | ADB TWRP |
| `scripts/04-twrp-recovery-logs.sh` | Recovery logs and current recovery dmesg | ADB TWRP |
| `scripts/05-partitions-mounts.sh` | Read-only block names, capacities, fstab, mounts | ADB TWRP |
| `scripts/06-recovery-kernel-info.sh` | `CONFIG_PSTORE`, recovery kernel config, reset information | ADB TWRP |
| `scripts/07-mac-usb-snapshot.sh` | macOS USB enumeration and ADB snapshot | Mac only |
| `scripts/08-adb-usb-watch.sh` | Passive ADB state changes over 3 min (default) | Mac + adb |
| `scripts/09-inspect-boot-image.sh` | Android BOOT header, DTBs and gzip/newc entries | Local image + Python |
| `scripts/10-inspect-fedora-rootfs.sh` | Offline ext4 fsck (read-only) and Fedora systemd/Phosh file review | Local image + e2fsprogs |
| `scripts/11-triage-collected-logs.sh` | Build evidence-based `TRIAGE.md`/`.json` | Capture directory |
| `scripts/12-full-diagnostics.sh` | Runs the non-destructive collectors and triage | ADB TWRP |
| `scripts/13-verify-partition-readback.sh` | Optional streaming SHA256 of BOOT, optionally USERDATA (4 GiB) | ADB TWRP + local images |
| `scripts/14-create-share-bundle.sh` | ZIP text logs with best-effort private-data redaction | Capture directory |
| `scripts/15-nuxel-boot-health-check.sh` | If Linux itself later exposes ADB, inspect systemd, graphics and mounts | Working ADB shell |
| `tools/install-mac-deps.sh` | Opt-in Homebrew tool installer | macOS, Homebrew |
| `tools/doctor.sh` | Check Mac tools and ADB presence | Mac |
| `tools/check-script-syntax.sh` | Syntax sanity checks | Bash/Python |
| `tools/inspect_android_boot.py` | Image header, DTB and initramfs parser | Python stdlib |
| `tools/triage.py` | Error-pattern classification with source context | Python stdlib |

## Inspect the images you actually flashed

Specify **your Mac local paths**, not the small diagnostic rootfs:

```bash
bash scripts/09-inspect-boot-image.sh \
  ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img

bash scripts/10-inspect-fedora-rootfs.sh \
  ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img
```

Both use local files; they don't touch the phone. The boot inspector extracts candidate DTBs into the capture folder on the **Mac** and checks for missing initramfs entries. In your previous reports, `BEYOND2LTE EUR OPEN 26` matches the handset's revision/region identifiers, **but that does not guarantee S-Boot's DTBO handoff is correct** (`androidboot.dtbo_idx=9`).

You can run full diagnostics plus offline checks together:

```bash
NUXEL_BOOT_IMAGE="$HOME/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img" \
NUXEL_ROOTFS_IMAGE="$HOME/x/nuxel/build/out/s10plus/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img" \
  bash scripts/12-full-diagnostics.sh
```

## Optional: verify byte-for-byte storage again (reads only)

```bash
bash scripts/13-verify-partition-readback.sh --boot \
  ~/x/nuxel/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img
# Add --rootfs /path/to/4GiB/rootfs.img only when needed; takes longer.
```

This step was already completed successfully on your handset; **there is no reason to repeat the 4 GiB readback while investigating the bootloop** unless storage corruption is newly suspected.

## Passive observation through the next manual reboot

Start this *before* manually triggering a boot attempt, in a second terminal:

```bash
NUXEL_WATCH_SECONDS=240 NUXEL_WATCH_INTERVAL=2 bash scripts/08-adb-usb-watch.sh
```

This monitors only `adb devices` (no automatic reboot). A missing ADB device during normal Fedora boot is **not** evidence that the kernel failed: the Fedora image may not have an ADB daemon or USB gadget configured.

## Share evidence safely

```bash
bash scripts/14-create-share-bundle.sh captures/<your-session-folder>
```

This generates a `-REDACTED.zip` with only text logs. Redaction is best-effort; inspect the ZIP before sharing. Raw files and serials can contain sensitive information. No reports are automatically uploaded anywhere.

## Interpreting symptoms

- Samsung logo repeatedly restarts: likely an early boot-chain/kernel/init problem, but logo alone cannot distinguish S-Boot rejection from a kernel panic.
- pstore shows `Kernel panic` / `unknown-block` / `/init` problems: focus on BOOT initramfs and the UFS root mount / systemd handoff.
- Kernel reaches `systemd` but display remains black: probe `/dev/dri`, Samsung DECON/DSI/DRM, panel driver, and Phoc session after restoring a debug channel.
- No persistent logs at all: investigate kernel pstore/ramoops availability, or a **hardware serial/UART console** (only with proper pinout, electrical safety and review; not implemented in this kit). No guessing a console port.

See `docs/BOOTLOOP-DECISION-TREE.md` for an ordered workflow. Build-manifest and PIT information should be kept with diagnostic evidence, not used as proof of a successful boot.

## Quality gates

- Built-in scripts are tested with shell syntax checks and simulated ADB (no phone writes).
- `TRIAGE.md` distinguishes source of log evidence; it does not assert a root cause from mere pattern matches.
- The offline e2fsck check uses `-fn` and **will not repair your image**. Do not edit your boot/rootfs images during log collection.
- **Not covered:** physical UART, display driver repair, DTBO flashing, OS installation, USB gadget setup, recovery restoration, autonomous rebooting, or firmware-level telemetry.

The pack is designed for observability and root-cause isolation, **not a promise that the next reboot will work**.

### Additional offline diagnostics

- `scripts/16-kernel-config-audit.sh /path/to/kernel/.config` (or `.config.gz`) summarizes storage, initramfs, persistent logging, Samsung display and USB gadget options. Missing Kconfig names may be renamed by vendor patches; this is not a compile-time proof of hardware support.
- `scripts/17-pstore-decode-offline.sh /path/to/captured/pstore/console-ramoops-0` tries common compression formats **on the Mac copy** and preserves the raw evidence.

## 20-triage-nuxel-boot.py — segment and triage a ram-console record

`/proc/last_kmsg` is a ring buffer holding several boots concatenated; reading it
as one boot is the easiest way to reach a wrong conclusion (it is what made an
earlier cycle call an intentional animation loop a bootloop). This tool segments
it by S-Boot records, finds the Nuxel session(s) by their own markers, and prints
the A16/A17 decision points with counts and line numbers:

```sh
python3 scripts/s10plus-debug-pack/scripts/20-triage-nuxel-boot.py \
        captures/<stamp>-A16-postfail/previous-boot/last_kmsg.clean.txt
```

It reports, among others: fbdev geometry, first-light markers, the animation hold
PID marker, `SYSTEMD_LIB_*` verification results, `CGROUP2_VERIFIED`,
`LIVE_CONSOLE_*`, **the count of `Failed to spawn executor`** (must be 0 after
A17), the count of `Failed at step CGROUP`, service/target counts, the reset
cause, and the touchscreen (`sec_ts`) status. `--grep PATTERN` prints matching
lines with line numbers.
