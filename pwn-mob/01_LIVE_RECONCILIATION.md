# 01 — DEEPSEEK PRO THINKING: Live Baseline, Source Reconciliation, First Blocker

**Read `00_MASTER_SAFETY_AND_TRUTH.md` first and obey it throughout. This round is strictly READ-ONLY on the physical device.**

## Mission

On owner's Mac host inspect real `/Users/wicked/x/nuxel` and `pwn/mobile*.md` (if now present), root `mobile.md`, `reports/S5000AP-RADIO-ENDGAME.md`, `reports/S5000AP-RADIO-FINAL-RECOVERY.md`, `packs/mobile`, Git branch/status and the full Exynos9820 kernel checkout. The supplied snapshot had none of `pwn/mobile*.md`, reports, packs/mobile or `.git`; inspect what currently exists, do not assume absence on owner's machine. Compare last recorded `22dd6b3ab46dece28abfe83607d7cc64add76843` to current HEAD but never reset history. Read existing memory/staged DT incidents so no repeating broken-DT failures.

The owner's previously used Nuxel access is `root@10.11.12.99` using an owner-controlled SSH key. Confirm reachability without blindly assuming IP/key still correct. Keep working Wi-Fi/USB connection. No RF state changes, no disabling Wi-Fi, no reboot, no partition reads or writes beyond bounded owner-approved BOOT metadata/backup process.

## Read-only evidence inventory

- Host side: `git status --short`, log, per-subtree diff, track `reports/` vs ignored files; enumerate newest `pwn/mobile*.md`, `mobile.md`, CP artifact paths, `cbd` source, loader executables, modem firmware host cache, RIL/SIPC headers and source. `sha256sum` candidate files; never copy proprietary blobs into Git or agent logs.
- Device side: timestamp, uname, `/proc/cmdline`, `/proc/version`, `/proc/config.gz` or `zcat /proc/config.gz`, `systemctl --failed`, Nuxel process/UI/network health, memory/thermal/battery snapshot, SSH/USB route, `ip -details link`, `ip route`, NetworkManager, ModemManager version and `mmcli -L`. Query `/dev/umts_*` presence/types/modes and driver/sysfs attribution, boot dmesg/pstore excerpts, permissions, owners of boot/IPC/RFS endpoints.
- **Actually read CP status via pinned `IOCTL_MODEM_STATUS` on verified `/dev/umts_boot0` using a built host-tested read-only tool**. Do not infer CP OFFLINE from a JSON fixture, a shell script's plugin check, or rmnet DOWN. Do not run mutating ioctls. Return exact `state` + errno and timestamp.
- Verify kernel built-in flags `SEC_SIPC_MODEM_IF`, `SEC_MODEM_S5000AP`, `LINK_DEVICE_SHMEM`, `UMTS_MODEM_S5000AP`, `CP_SECURE_BOOT`. Confirm in source *and* current running config.
- Record the hash of the **CURRENT BOOT image and embedded DT payload** where available via safe, bounded, authorized read; compare to host's last-known-good boot image and board hardware revision. Never write DTBO or repack BOOT for a diagnostic task.

## Fix diagnostic state-model defect before attempting firmware

In `tools/s10plus/a33/nuxel-modem-diag.sh`, `verdict()` currently checks missing Shannon plugin BEFORE verifying real CP power/boot state: it labels `modemmanager_plugin` first failing stage despite documented `CP OFFLINE`. Implement separate stage fields `host_present`, `cp_status`, `firmware_candidate_verified`, `cbd_available`, `cp_boot_completed`, `ipc_responsive`, `rfs_responsive`, `sim_ready`, `registered`, `bearer_connected`, `rmnet_verified`; express `UNKNOWN` rather than guess. Keep existing backward-compatible JSON fields and explicit `signal=null`/`registration=null`/`data=false` unless sourced from live carrier state. Don't assume `mmcli -L` showing one modem establishes SIM present: it must query actual modem/SIM readiness. A file in `/var/lib/nuxel/modem/sim.json` needs provenance, age and authenticated writer; stale/mock state cannot qualify.

Also inspect `firmware/s10plus/manifest.yml`: mislabeled `calliope_*` as Shannon/Calliope modem DSP even though the research document attributes `calliope_sram*` to Samsung ABOX audio; do NOT send it to S5000AP. Reconcile `configs/s10plus/modem/README.md` claiming a missing ModemManager plugin as sole blocker and modern root `mobile.md` identifying CP boot first.

## Flash review without flashing

Audit `boot/s10plus/flash.sh`, `scripts/nuxel-adb-flash-pack/scripts/03-flash.sh`, and history: probe dry-run behavior and denylist including `modem`, `radio`, `dtbo`, protected partitions, alias/symlink resolution and arbitrary `--rootfs-partition`. Flag unsafe or conflicting protections in a report; apply fixes only to source after tests. `configs/nuxel/modem/modem.json` forbids TWRP while owner expressly permits reviewed TWRP BOOT recovery; make a narrow scoped exception in mission-level documentation, NOT blanket weakening of the modem protected-partition denylist. Do not depend on unverified historic host backups; verify real files and hashes.

## Deliverables / STOP

`reports/S5000AP-01-LIVE-GATES.md`: per-layer observed source, capture time, first blocker, exact live software versions, redacted cp status, safety hashes, worktree findings, old/new drift. Add target fixtures (OFFLINE, absent, CP BOOTING, ONLINE-without-IPC, SIM-unknown, no-bearer) to verified diagnostic CI. Unit tests must fail on false-positive SIM, fake signal, and plugin-priority mistakes. Commit only these safe corrections and report precise changed files. **NO handset writes, BOOT flashes, CP boot, RF operations or DT modifications in this round.**

### Suggested Flash subjobs (each independent, no handset access)

1. Source & Git report inventory and discrepancy table.
2. Review and test modem-diag state machine using fixtures and synthetic negative states.
3. Verify flash script denylist and boot image packing assumptions in dry-run/host tests.

Thinking agent adjudicates all claims; Flash outputs are evidence only.
