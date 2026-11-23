# nuxel-modem — S5000AP CP bootstrap userspace deployment (Stage-04)

Reversible, FAIL-CLOSED userspace deployment for the Samsung Shannon S5000AP
(SM-G975F / beyond2lte) CP bootstrap. Two layers, strictly separated:

## Layer 1: read-only probe (always safe, always allowed)

- `systemd/nuxel-cp-status.service` — one-shot `nuxel-cp-status` (`s5000ap-status.aarch64`)
  that opens `/dev/umts_boot0` **O_RDONLY** and issues exactly one ioctl
  (`IOCTL_MODEM_STATUS = _IO('o',0x27)`). Never powers/resets/boots/transmits.

## Layer 2: physical CP boot (DISABLED by default; single owner-approved trial)

- `systemd/nuxel-cpbootd.service` — `Restart=no`, **never auto-enabled** (no
  `WantedBy`), no timer. Invokes `nuxel-cpbootd-stage04-guard`.
- `bin/nuxel-cpbootd-stage04-guard` — fail-closed gate. Never runs the HW binary
  unless the pinned binary hash matches (`d963219f…`) and a populated
  `/etc/nuxel/modem/stage04-trial.env` supplies the owner-approved manifest SHA.
- `bin/nuxel-modem-install.sh` — deploy/uninstall (see `--uninstall`).

## Physical trial invocation (only after owner approval of the exact manifest)

```
# 1. Owner approves reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md
# 2. Verify the manifest hash:
nuxel-cpbootd-manifest-check.sh reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md <sha>
# 3. Populate /etc/nuxel/modem/stage04-trial.env with STAGE04_MANIFEST_SHA256
#    and STAGE04_FIRMWARE_PATH (read-only RADIO ITOC), chmod 600.
# 4. systemctl start nuxel-cpbootd.service   # ONE shot, Restart=no
# 5. Confirm kernel CP state via nuxel-cp-status; require stable ONLINE(4),
#    repeated >=2x, NOT merely a successful process exit.
```

## Safety invariants

- No protected-partition write (BOOT/DTB/DTBO/RADIO/EFS/NV/calibration/IMEI/bootloader/TEE).
- No auto-retry/power-cycle loop. Any failure returns nonzero and disables the process.
- `--node` is pinned to `/dev/umts_boot0` exactly; the guard verifies binary identity.
- Mock/dry-run `online` is always tagged `"backend":"mock"` and never confused with physical ONLINE.
