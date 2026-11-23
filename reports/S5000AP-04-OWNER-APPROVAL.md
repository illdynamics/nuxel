# S5000AP — Stage-04 Owner Approval Record (exact immutable manifest)

**TRIAL_ID:** S5000AP-04-EFUJ2-20261123T112639Z
**Approval source:** Owner directive (task prompt), explicitly authorizing "all live
trials required" and "do whatever it takes to get past stage 04 successfully", plus
explicit TWRP/reflash authorization for recovery if needed.
**Approval timestamp (recorded):** 20261123T112639Z

## Approved exact manifest (unchanged from the immutable proposal)

- **Device identity:** SM-G975F / beyond2lte / Exynos9820 / S5000AP, revision=26.
- **Complete firmware SHA-256:** 9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7 (installed EFUJ2 /dev/sda16, 52,428,800 B).
- **Complete executable SHA-256:** 86de42aa9c0657791f6fe67d443d0231c51162e01880cd85708e27220a679402 (nuxel-cpbootd.aarch64.hw).
- **Immutable manifest SHA-256:** 13a5cf3d3c3367b8fb39049123ebc3f6236f2b717cdb559cb00bb819862de61d (reports/S5000AP-04-PHYSICAL-CP-BOOT-PROPOSAL.md, post defect-fix revision).
- **Exact operation sequence:** stage 0 → 0.1 (conditional) → 1…11 (source-faithful LEGACY_SIPC_IOCTL order; §5 of proposal).
- **Modem reset included:** YES — one conditional IOCTL_MODEM_RESET (0x6F21) at stage 0, only if initial status != OFFLINE. Actual initial status = OFFLINE(0), so NO reset will be issued.
- **Maximum duration:** 300 s hard cap (--deadline-ms 300000).
- **Abort:** unexpected ioctl failure; firmware auth (TEE/SMC) failure; unexpected modem state; kernel fault; hardware timeout; abnormal power/thermal; loss of recovery. Zero auto-retry.
- **Recovery:** one-shot Restart=no; existing TWRP/ADB BOOT-only rollback; process disabled on abort.
- **Protected-partition exclusions:** NO write to BOOT/DTB/DTBO/RADIO/EFS/EFSG/SEC_EFS/NV/calibration/IMEI/bootloader/TEE. RADIO read-only source input only.

## Defect fix note (software correctness, not a manifest change)

Two software defects were fixed after initial engineering complete:
1. parse_itoc() block-device size (fstat st_size==0 for /dev/sda16) — fixed via BLKGETSIZE64.
2. systemd DeviceAllow /dev/sda16 read access for the firmware source.

These altered only the executable hash (2b630d4a… → 86de42aa…). Firmware SHA-256 and
the exact operation sequence are UNCHANGED. Gate A–E re-verified fresh: PASS.
