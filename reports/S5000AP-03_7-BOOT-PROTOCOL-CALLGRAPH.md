# S5000AP — Prompt 03.7: Boot Protocol Call Graph (canonical, source-pinned)

**Branch/HEAD:** `cs/mob` @ `ae26b271c144780abb748ce2fb172919abb1131d`
**Sources:**
- kernel `android_kernel_samsung_exynos9820` @ `f7194c1d15eded1c2a1a4dc63825b26103435cc0`
  (`drivers/misc/modem_v1/{modem_prj.h,modem_io_device.c,modem_ctrl_s5000ap.c,link_device_shmem.c,include/sipc5.h}`)
- cbd `android_hardware_samsung_slsi-linaro_exynos` `cpboot_v3` @ `234b138716426c36ed801a71052bc144f7d8d806`
  (`{BootDumpModap.cpp,BootDump.cpp,ProtocolSipc.cpp,Type.h,Protocol.h}`)

**Build configuration (exynos9820-common `BoardConfigCommon.mk`):**
`protocol=sipc` → `-DCONFIG_SEC_CP_VERIFYING_ALL`; `use_legacy_sipc_ioctl=true` →
`-DLEGACY_SIPC_IOCTL`; plus `-DCONFIG_TYPE_MODAP -DCONFIG_TYPE_EXT`; `-t ss310`
→ `SEC_SS310` (SIPC/SHMEM/5-stage path). `use_legacy_ioctl` is NOT set (`LEGACY_IOCTL` undefined).

This document supersedes the older 03.5 proposal's abbreviated (and partially
wrong) ordering. It is derived by direct source reading of `BootDumpModap::boot()`
under the above macros — not invented.

## 0. ioctl numeric contract (verified `_IO('o',N)` == `0x6F00|N`)

| Samsung userspace name (cpboot_v3 Type.h) | Kernel name (modem_prj.h) | numeric |
|---|---|---|
| `IOCTL_POWER_ON` | `IOCTL_MODEM_ON` | 0x6F19 |
| `IOCTL_POWER_RESET` (LEGACY_SIPC_IOCTL: `_IO`) | `IOCTL_MODEM_RESET` | 0x6F21 |
| `IOCTL_MODEM_BOOT_ON` / `IOCTL_START_CP_BOOTLOADER` | `IOCTL_MODEM_BOOT_ON` | 0x6F22 |
| `IOCTL_COMPLETE_NORMAL_BOOTUP` | `IOCTL_MODEM_BOOT_OFF` | 0x6F23 |
| `IOCTL_GET_CP_STATUS` | `IOCTL_MODEM_STATUS` | 0x6F27 |
| `IOCTL_MODEM_DL_START` | `IOCTL_MODEM_DL_START` | 0x6F28 |
| `IOCTL_LOAD_CP_IMAGE` (LEGACY_SIPC_IOCTL `_IO`) | `IOCTL_MODEM_XMIT_BOOT` | 0x6F40 |
| `IOCTL_CLR_CP_BOOTLOG` | `IOCTL_MODEM_CLR_CP_BOOTLOG` | 0x6F48 |
| `IOCTL_REQ_SECURITY` (LEGACY_SIPC_IOCTL `_IO`) | `IOCTL_SECURITY_REQ` | 0x6F53 |

`IOCTL_MODEM_XMIT_BOOT`/`IOCTL_SECURITY_REQ` are `_IO` (raw `arg` pointer, NOT
`_IOW`): the kernel does `copy_from_user(&mf, arg, sizeof(mf))`. `struct
modem_firmware` = 28 B (packed, field order `binary,size,m_offset,b_offset,mode,len`);
`struct modem_sec_req` = 16 B (`mode,param2,param3,param4`).

## 1. Canonical call graph (LEGACY_SIPC_IOCTL, exact)

`BootDumpModap::boot()` executes, in order:

1. `prepare_boot_args(CP_BOOT_MODE_NORMAL)` → `std_boot_prepare_args` (open
   `/dev/umts_boot0` O_RDWR) + `std_boot_parse_toc_img` (open RADIO O_RDONLY,
   read TOC, locate BOOT/MAIN/VSS/NV/OFFSET).
2. `get_modem_state()` → `IOCTL_GET_CP_STATUS` (0x27). If != `STATE_OFFLINE`:
   `std_boot_power_reset` → `IOCTL_POWER_RESET` (0x21).
3. `std_security_req(CP_BOOT_RE_INIT=2, 0, 0)` → `IOCTL_REQ_SECURITY` (0x53).
4. `load_cp_images(NORMAL)` → loop `load_cp_image_by_stage` → `IOCTL_LOAD_CP_IMAGE`
   (0x40) for BOOT, MAIN, VSS, NV parts. The `struct cp_image` under non-LEGACY_IOCTL
   layout is `{binary,size,m_offset,b_offset,mode,len}` — byte-identical field
   *semantics* to the kernel `modem_firmware` (mode=0 BOOT window). Payload chunks
   of `EXYNOS_PAYLOAD_LEN` (62 KiB).
5. `std_security_req(CP_BOOT_MODE_MANUAL=7, TOC.m_offset, TOC.size)` → 0x53.
6. (if VSS present) `std_security_req(VSS mode, VSS.m_offset, VSS.size)` → 0x53.
7. `std_security_req(CP_BOOT_MODE_NORMAL=0, BOOT.size, MAIN.size)` → 0x53.
8. `std_boot_power_on()` → `IOCTL_POWER_ON` (0x19).
9. `std_boot_start_cp_bootloader(NORMAL)` → `IOCTL_MODEM_BOOT_ON` (0x22).
10. `IOCTL_MODEM_DL_START` (0x28).
11. `ProtocolSipc::std_boot_finish_handshake()` → SIPC UDL:
    - `std_udl_stage_done(OPER_BOOT, STD_UDL_STAGE_START=0)` → write 0x9000|0|0xD, expect 0xA000|0|0xD;
    - `std_udl_stage_start(OPER_BOOT, STD_UDL_FIN_STAGE=0xF)` → write 0x9000|F|0x0, expect 0xA000|F|0x0.
12. `std_boot_complete_normal_bootup()` → `IOCTL_COMPLETE_NORMAL_BOOTUP` (0x23,
    kernel `modem_boot_off` waits `init_cmpl` with `MIF_INIT_TIMEOUT` 15 s), then
    `IOCTL_CLR_CP_BOOTLOG` (0x48).

Kernel handler mapping:
- 0x19 → `modem_ctrl_s5000ap.c:s5000ap_on` (cal_cp_init + AP2CP_CFG).
- 0x40 → `link_device_shmem.c:shmem_xmit_boot` (bounds-checked `copy_from_user`).
- 0x53 → `link_device_shmem.c:shmem_security_request` → `exynos_smc` (TEE; `SMC_ID`,
  `SSS_CLK_ENABLE/DISABLE`, `MODE_CP_CHECK_CONTINUE` retry loop).
- 0x22 → `s5000ap_boot_on` (polls `mbox cp_status` ≤ ~2 s).
- 0x28 → `dload_start` + `modem_boot_confirm`.
- 0x23 → `s5000ap_boot_off` (`wait_for_completion_timeout(init_cmpl, 15*HZ)`).

## 2. State transitions

`OFFLINE(0) → BOOTING(3) [BOOT_ON] → LOADER_DONE(6) [optional] → ONLINE(4)`
`NV_REBUILDING(5)` possible. `SIM_ATTACH/DETACH(7/8)` only after online+SIM.

## 3. Timeouts / abort conditions

| Stage | Deadline | Abort on |
|---|---|---|
| SIPC UDL poll | 30 s (`WAIT_POLL_TIME`) | poll timeout / POLLHUP / bad resp |
| boot_off init_cmpl | 15 s (`MIF_INIT_TIMEOUT`) | `-EAGAIN` on timeout |
| boot_on cp_status | ~2 s (100 × 10–20 ms) | `-EACCES` on timeout |
| SECURITY_REQ SMC | up to `MAX_TRY_CNT` (0x1000) | signature not-finished |

No blind retry of other offsets/binaries/stages; no power-cycle loop.

## 4. Where this differs from the stale 03.5 proposal

The 03.5 proposal ordered `STATUS → POWER_ON → XMIT_BOOT → BOOT_ON → DL_START →
MAIN(SIPC) → SECURITY → BOOT_OFF → BOOT_DONE → ONLINE`, and cited **DTK9** BOOT/MAIN
sizes. Both are superseded: (a) the correct order under LEGACY_SIPC_IOCTL performs
SECURITY/XMIT **before** POWER_ON (see above); (b) section sizes now come from the
**EFUJ2** ITOC parsed at runtime, never DTK9 constants.
