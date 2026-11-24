# Stage 06 — LTE Final Execution — Round 26 live root-cause (2026-11-24)

**Branch:** cs/mob
**Device:** SM-G975F / beyond2lte / Exynos 9820 / Shannon S5000AP (native Nuxel Linux)

## Verdict
STAGE_06 = NOT_YET_PASSED. This round re-derived the blocker from FIRST PRINCIPLES
on the live device and found a NEW, upstream blocker that supersedes the prior
"NV initial-attach APN" finding: the modem SIPC5 control-plane io-device nodes
are ABSENT, so the AP cannot reach the modem control plane at all.

## Live baseline (verified this session, 2026-11-24)
- Kernel: 4.14.253-gf7194c1d15ed-dirty aarch64 (boot 09:59:50 CET)
- DTB model: "Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820"
- CP state sysfs /sys/devices/platform/10000.mif_pdata/modem_state = ONLINE
- SIM ds_detect = 1
- Kernel mif link RX live (dmesg): `mif: LNK-RX(29): f8 eb ... 07 06 03 <rssi> ...`
  => the Shannon CP is genuinely alive and emitting DISP_RSSI_INFO on SIPC5 ch 0xeb.
- Management links intact: wlan0, usb0, ZeroTier 10.11.12.99, SSH.

## ROOT CAUSE (new, decisive, first-principles)

The modem control-plane device nodes DO NOT EXIST:

  /dev/umts_boot0   -> MISSING
  /dev/umts_ipc0    -> MISSING   (FMT, ch 0xeb)
  /dev/umts_ipc1    -> MISSING
  /dev/umts_rfs0    -> MISSING   (RFS, ch 0xf5)

Only /dev/multipdp and /dev/s5p-smem exist. `nuxel-radiod` hardcodes FMT_NODE
=/dev/umts_ipc0 and RFS_NODE=/dev/umts_rfs0 (tools/s10plus/s5000ap-05/src/radiod.c
lines 51-53). With the nodes absent, radiod opens only D-Bus/journal sockets and
can NEVER transmit the FMT data-session commands or answer the RFS handshake.
The data-session FSM (DS_* in data_session.c) is therefore unreachable, and the
EPS bearer can never be established regardless of NV/APN.

### Kernel-link proof the modem is alive
dmesg `mif: LNK-RX(29): f8 eb 1d 00 19 00 cX 00 07 06 03 <rssi> ff 63 00 ...`
decodes to SIPC5 link header (ch=0xeb FMT) carrying the same DISP_RSSI_INFO
payload radiod logs. The link layer works; only the io-device userspace surface
is missing.

### Why the io-devices are missing (DT evidence)
The modem io-devices are defined in the device tree overlay
`fragment@modemif/__overlay__/mif_pdata/iodevs` in
arch/arm64/boot/dts/samsung/exynos9820-beyond2lte_eur_open_26.dts (mif,num_iodevs
= 0x16, children io_device_0..21 defining umts_cass, umts_ipc0(0xeb),
umts_ipc1(0xec), umts_rfs0(0xf5), umts_csd, umts_router, umts_dm0,
ipc_loopback0, rmnet0..7, multipdp_hiprio, multipdp, umts_boot0(0xd7),
umts_ramdump0, smd4, umts_ciq0).

On the RUNNING kernel, the resolved DT node is present but STRIPPED:

  /sys/devices/platform/10000.mif_pdata/of_node/mif,name = "s5000ap"
  /sys/devices/platform/10000.mif_pdata/of_node/status   = "okay"
  /sys/devices/platform/10000.mif_pdata/of_node/iodevs    = ONLY a "name" property

The `iodevs` child has NO io_device_* children and no iod,name/iod,id attributes,
so modem_if_parse_dt_pdata()/parse_dt_iodevs_pdata() find zero io-devices and
create_io_device()->sipc5_init_io_device()->misc_register() is never invoked for
umts_ipc0/umts_rfs0/umts_boot0. confirm: `grep -rl umts_ipc /proc/device-tree/`
returns nothing.

The CP reports ONLINE because the modem_ctrl_s5000ap driver (modem_state sysfs)
probes independently of the io-device children. This is why CP==ONLINE but no
data-path control nodes exist.

## Conclusion
This is a DTB/BOOT-image regression, NOT a radiod serialization defect and NOT
(yet) an NV initial-attach APN problem. The correct DT source exists in-tree and
defines all 22 io-devices, but the DTB currently booted by the physical device
does not contain the iodevs children. The prior rounds' working data-session FSM
(rounds 17-25) implies an earlier boot carried a complete DTB; the current boot
does not.

## Required corrective action (owner-authorized)
Rebuild/redeploy a BOOT image whose embedded DTB carries the full
fragment@modemif mif_pdata/iodevs block (byte-verified against the in-tree
DT source), following 09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md, with two verified
known-good backups and a rollback receipt. This is the upstream blocker; the NV
initial-attach APN investigation remains downstream and cannot be exercised
until /dev/umts_ipc0 and /dev/umts_rfs0 are present.

## Safety (this session)
- No partition flashed. No NV/EFS write. No IMEI/identity/target modification.
- RADIO /dev/sda16 and BOOT partition untouched; no cpbootd --really-boot run.
- Wi-Fi, USB, ZeroTier, SSH all intact.

## Refinement: DTBO overlay application is the likely regression
The in-tree DT source `exynos9820-beyond2lte_eur_open_26.dts` is a DTBO overlay
(/dts-v1/ with fragment@modemif { target-path = "/"; __overlay__ { mif_pdata { ...
iodevs { io_device_0..21 } } } }). The running kernel's resolved DT has the
`mif_pdata` node (mif,name=s5000ap, status=okay) but its `iodevs` child is empty
(name property only). This is consistent with the DTBO overlay that populates
the 22 io-device children NOT being applied by the bootloader S-Boot on this
boot, while a base/stub mif_pdata node is. The DTBO application (or the BOOT
image's embedded combined DTB) must therefore be corrected — this is the exact
upstream blocker gate.

## What would make this PASS (not yet true)
Only after /dev/umts_ipc0 + /dev/umts_rfs0 (+ umts_boot0) are present can radiod
run the DS_* FSM (NET_REGIST -> ... -> SetPdpContext) and the CP's initial-attach
APN/EPS-bearer path be exercised. The NV initial-attach APN investigation
(rounds 19-25) is downstream of this DTBO/io-device gate and does not need to be
re-run first.
