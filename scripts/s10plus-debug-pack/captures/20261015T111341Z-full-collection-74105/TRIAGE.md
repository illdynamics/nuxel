# Nuxel S10+ bootloop triage

**Result:** EVIDENCE_CAPTURED_NEEDS_REVIEW

Collected log files scanned: 34

A kernel panic cannot be ruled out by an empty pstore directory. The phone may reboot before pstore is initialized, or firmware may clear it.

## Evidence categories

- display (current_recovery_or_host): 13 occurrence(s)
- display (previous_boot): 9 occurrence(s)
- kernel_watchdog (previous_boot): 7 occurrence(s)
- kernel_watchdog (current_recovery_or_host): 4 occurrence(s)
- selinux (current_recovery_or_host): 3 occurrence(s)
- kernel_panic (previous_boot): 1 occurrence(s)
- filesystem (current_recovery_or_host): 1 occurrence(s)

## Samples (review context in raw logs)

- `host-ioreg-usb.txt:11` [current_recovery_or_host; kernel_watchdog] |   "IOKitDiagnostics" = {"Instance allocation"=11688920,"Container allocation"=6784106,"Pageable allocation"=1472397360,"Classes"={"AppleJPEGWrapperControlV8"=0,"KDISecondaryEncoding"=0,"RTBuddyFirmwareBundle"=0,"ApplePMPThermal"=0,"IOSkywalkPacketPoller"=0,"
- `kernel/cmdline.txt:1` [current_recovery_or_host; kernel_watchdog] console=ram loglevel=4 sec_debug.pcb_offset=7346944 sec_debug.smd_offset=7348992 sec_debug.lpddr4_size=8 sec_debug.dram_info=01,06,03,8G sec_debug.pwrsrc_rs=0x0000000840010000 sec_debug.reset_reason=5 sec_reset.reset_reason=5 sec_debug.reset_rwc=0 bootmode=2 s
- `previous-boot/last_kmsg.txt:2188` [previous_boot; display] <3>[    4.189315]  [0:    kworker/0:2: 1895] [SSP] send_panel_information, failed to send panel information
- `previous-boot/last_kmsg.txt:3518` [previous_boot; kernel_watchdog] <6>[    0.868318]  [0:      swapper/0:    1] s3c2410-wdt 10050000.watchdog_cl0: watchdog cluster 0, inactive, reset disabled, irq disabled
- `previous-boot/last_kmsg.txt:3525` [previous_boot; kernel_watchdog] <6>[    0.868627]  [0:      swapper/0:    1] s3c2410-wdt 10060000.watchdog_cl2: watchdog cluster 1, inactive, reset disabled, irq disabled
- `previous-boot/last_kmsg.txt:3987` [previous_boot; display] <3>[    1.229551]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s4_dsim0@0x19160000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:3990` [previous_boot; display] <3>[    1.229813]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s0_dsim0@0x19161000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:8697` [previous_boot; display] <3>[    4.271768]  [7:  kworker/u16:1:   67] [SSP] send_panel_information, failed to send panel information
- `previous-boot/last_kmsg.txt:9254` [previous_boot; kernel_panic] <0>[    9.396762] I[0:      swapper/0:    0] Kernel panic - not syncing: Fatal exception in interrupt
- `previous-boot/last_kmsg.txt:9257` [previous_boot; kernel_watchdog] <0>[    9.396776] I[0:      swapper/0:    0] watchdog reset is started to 30secs
- `previous-boot/last_kmsg.txt:11613` [previous_boot; kernel_watchdog] <6>[    0.852669]  [0:      swapper/0:    1] s3c2410-wdt 10050000.watchdog_cl0: watchdog cluster 0, inactive, reset disabled, irq disabled
- `previous-boot/last_kmsg.txt:11620` [previous_boot; kernel_watchdog] <6>[    0.853203]  [0:      swapper/0:    1] s3c2410-wdt 10060000.watchdog_cl2: watchdog cluster 1, inactive, reset disabled, irq disAblet
- `previous-boot/last_kmsg.txt:12085` [previous_boot; display] <3>[    1.232931]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s4_dsim0@0x19160000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:12088` [previous_boot; display] <3>[    1.233151]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s0_dsim0@0x19161000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:15638` [previous_boot; kernel_watchdog] <6>[    0.852598]  [0:      swapper/0:    1] s3c2410-wdt 10050000.watchdog_cl0: watchdog cluster 0, inactive, reset disabled, irq disabled
- `previous-boot/last_kmsg.txt:15645` [previous_boot; kernel_watchdog] <6>[    0.853127]  [0:      swapper/0:    1] s3c2410-wdt 10060000.watchdog_cl2: watchdog cluster 1, inactive, reset disabled, irq disabled
- `previous-boot/last_kmsg.txt:16107` [previous_boot; display] <3>[    1.218191]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s4_dsim0@0x19160000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:16110` [previous_boot; display] <3>[    1.218410]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s0_dsim0@0x19161000: failed to lookup PMU regmap, use PMU interface
- `previous-boot/last_kmsg.txt:20832` [previous_boot; display] <3>[    4.687950]  [7:  kworker/u16:0:    5] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:546` [current_recovery_or_host; kernel_watchdog] <6>[    0.838524]  [0:      swapper/0:    1] s3c2410-wdt 10050000.watchdog_cl0: watchdog cluster 0, inactive, reset disabled, irq disabled
- `recovery/current-recovery-dmesg.txt:553` [current_recovery_or_host; kernel_watchdog] <6>[    0.839176]  [0:      swapper/0:    1] s3c2410-wdt 10060000.watchdog_cl2: watchdog cluster 1, inactive, reset disabled, irq disabled
- `recovery/current-recovery-dmesg.txt:1019` [current_recovery_or_host; display] <3>[    6.507604]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s4_dsim0@0x19160000: failed to lookup PMU regmap, use PMU interface
- `recovery/current-recovery-dmesg.txt:1022` [current_recovery_or_host; display] <3>[    6.507828]  [0:      swapper/0:    1] exynos-mipi-phy dphy_m4s0_dsim0@0x19161000: failed to lookup PMU regmap, use PMU interface
- `recovery/current-recovery-dmesg.txt:5142` [current_recovery_or_host; selinux] <6>[    7.538310]  [7:           init:    1] SELinux: the above unknown classes and permissions will be denied
- `recovery/current-recovery-dmesg.txt:5324` [current_recovery_or_host; selinux] <11>[    7.743576]  [7:           init:    1] selinux: avc:  denied  { set } for property=twrp.crash_counter pid=4882 uid=0 gid=0 scontext=u:r:recovery:s0 tcontext=u:object_r:default_prop:s0 tclass=property_service permissive=1
- `recovery/current-recovery-dmesg.txt:5327` [current_recovery_or_host; display] <3>[    7.748058]  [4:       recovery: 4882] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5632` [current_recovery_or_host; display] <3>[    7.913278]  [7:  kworker/u16:2:   72] set_panel_poc, failed to read dim partition
- `recovery/current-recovery-dmesg.txt:5633` [current_recovery_or_host; display] <3>[    7.913281]  [7:  kworker/u16:2:   72] panel_update_dim_type, failed to read gamma flash(ret -11)
- `recovery/current-recovery-dmesg.txt:5635` [current_recovery_or_host; display] <3>[    7.913286]  [7:  kworker/u16:2:   72] PANEL:ERR:panel_update_dim_type failed to check dim_flash exist
- `recovery/current-recovery-dmesg.txt:5639` [current_recovery_or_host; display] <3>[    7.913294]  [7:  kworker/u16:2:   72] set_panel_poc, failed to read MTP partition
- `recovery/current-recovery-dmesg.txt:5640` [current_recovery_or_host; display] <3>[    7.913297]  [7:  kworker/u16:2:   72] panel_update_dim_type, failed to read mtp flash(ret -11)
- `recovery/current-recovery-dmesg.txt:5642` [current_recovery_or_host; display] <3>[    7.913302]  [7:  kworker/u16:2:   72] PANEL:ERR:__panel_seq_dim_flash_res_init, failed to seqtbl(PANEL_DIM_FLASH_RES_INIT_SEQ)
- `recovery/current-recovery-dmesg.txt:5643` [current_recovery_or_host; display] <3>[    7.913304]  [7:  kworker/u16:2:   72] panel_update_dim_type, failed to resource init
- `recovery/current-recovery-dmesg.txt:5645` [current_recovery_or_host; display] <3>[    7.913310]  [7:  kworker/u16:2:   72] panel_update_dim_type, failed to copy resource dim_flash_mtp_offset (ret -22)
- `recovery/current-recovery-dmesg.txt:5666` [current_recovery_or_host; display] <3>[    7.913368]  [7:  kworker/u16:2:   72] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:5667` [current_recovery_or_host; display] <3>[    7.913371]  [7:  kworker/u16:2:   72] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:6130` [current_recovery_or_host; selinux] <11>[    9.992274]  [7:           init:    1] selinux: avc:  denied  { set } for property=sys.usb.config pid=4882 uid=0 gid=0 scontext=u:r:recovery:s0 tcontext=u:object_r:system_radio_prop:s0 tclass=property_service permissive=1
- `recovery/current-recovery-dmesg.txt:6217` [current_recovery_or_host; filesystem] <3>[   12.971584]  [6:       recovery: 4882] EXT4-fs (sda31): errors=remount-ro for active namespaces on umount 0

## Decision tree

1. **Previous-boot pstore/last_kmsg contains panic or mount failure:** examine precise kernel stack, error code and failing path; inspect BOOT initramfs and Fedora rootfs together.
2. **Recovery logs exist but previous-boot logs do not:** don't attribute recovery dmesg to Nuxel. Investigate UART/earlycon and kernel pstore support as a *separate, reviewed firmware/kernel modification*.
3. **BOOT/DTB fails before kernel logging:** consider S-Boot handoff, DTB/DTBO overlay application, cmdline, vbmeta/recovery launch semantics.
4. **Kernel starts but display stays black:** assess kernel log for DECON/DSI/panel failures. Phosh cannot fix absent DRM/KMS.
5. **systemd starts but UI absent:** check greetd/Phosh/Phoc services, permissions, seatd/logind, input and display nodes after bringing up a debug console.

No device writes, resets, repartitioning or flashing were performed by this triage tool.
