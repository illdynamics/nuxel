# Nuxel S10+ bootloop triage

**Result:** EVIDENCE_CAPTURED_NEEDS_REVIEW

Collected log files scanned: 37

A kernel panic cannot be ruled out by an empty pstore directory. The phone may reboot before pstore is initialized, or firmware may clear it.

## Evidence categories

- display (current_recovery_or_host): 34 occurrence(s)
- selinux (current_recovery_or_host): 3 occurrence(s)
- kernel_watchdog (current_recovery_or_host): 2 occurrence(s)
- filesystem (current_recovery_or_host): 1 occurrence(s)

## Samples (review context in raw logs)

- `host-ioreg-usb.txt:11` [current_recovery_or_host; kernel_watchdog] |   "IOKitDiagnostics" = {"Instance allocation"=10027736,"Container allocation"=6513171,"Pageable allocation"=796622896,"Classes"={"AppleJPEGWrapperControlV8"=0,"KDISecondaryEncoding"=0,"RTBuddyFirmwareBundle"=0,"ApplePMPThermal"=0,"IOSkywalkPacketPoller"=0,"I
- `kernel/cmdline.txt:1` [current_recovery_or_host; kernel_watchdog] console=ram loglevel=4 sec_debug.pcb_offset=7346944 sec_debug.smd_offset=7348992 sec_debug.lpddr4_size=8 sec_debug.dram_info=01,06,03,8G sec_debug.pwrsrc_rs=0x0000100140010000 sec_debug.reset_reason=9 sec_reset.reset_reason=9 sec_debug.reset_rwc=0 bootmode=2 s
- `recovery/current-recovery-dmesg.txt:726` [current_recovery_or_host; selinux] <6>[    7.470022]  [6:           init:    1] SELinux: the above unknown classes and permissions will be denied
- `recovery/current-recovery-dmesg.txt:906` [current_recovery_or_host; selinux] <11>[    7.675054]  [5:           init:    1] selinux: avc:  denied  { set } for property=twrp.crash_counter pid=4877 uid=0 gid=0 scontext=u:r:recovery:s0 tcontext=u:object_r:default_prop:s0 tclass=property_service permissive=1
- `recovery/current-recovery-dmesg.txt:913` [current_recovery_or_host; display] <3>[    7.679629]  [7:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:1167` [current_recovery_or_host; display] <3>[    7.843098]  [4:  kworker/u16:4:  765] set_panel_poc, failed to read dim partition
- `recovery/current-recovery-dmesg.txt:1168` [current_recovery_or_host; display] <3>[    7.843101]  [4:  kworker/u16:4:  765] panel_update_dim_type, failed to read gamma flash(ret -11)
- `recovery/current-recovery-dmesg.txt:1170` [current_recovery_or_host; display] <3>[    7.843107]  [4:  kworker/u16:4:  765] PANEL:ERR:panel_update_dim_type failed to check dim_flash exist
- `recovery/current-recovery-dmesg.txt:1174` [current_recovery_or_host; display] <3>[    7.843116]  [4:  kworker/u16:4:  765] set_panel_poc, failed to read MTP partition
- `recovery/current-recovery-dmesg.txt:1175` [current_recovery_or_host; display] <3>[    7.843119]  [4:  kworker/u16:4:  765] panel_update_dim_type, failed to read mtp flash(ret -11)
- `recovery/current-recovery-dmesg.txt:1177` [current_recovery_or_host; display] <3>[    7.843125]  [4:  kworker/u16:4:  765] PANEL:ERR:__panel_seq_dim_flash_res_init, failed to seqtbl(PANEL_DIM_FLASH_RES_INIT_SEQ)
- `recovery/current-recovery-dmesg.txt:1178` [current_recovery_or_host; display] <3>[    7.843127]  [4:  kworker/u16:4:  765] panel_update_dim_type, failed to resource init
- `recovery/current-recovery-dmesg.txt:1180` [current_recovery_or_host; display] <3>[    7.843134]  [4:  kworker/u16:4:  765] panel_update_dim_type, failed to copy resource dim_flash_mtp_offset (ret -22)
- `recovery/current-recovery-dmesg.txt:1201` [current_recovery_or_host; display] <3>[    7.843196]  [4:  kworker/u16:4:  765] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:1202` [current_recovery_or_host; display] <3>[    7.843199]  [4:  kworker/u16:4:  765] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:1710` [current_recovery_or_host; selinux] <11>[    9.818354]  [7:           init:    1] selinux: avc:  denied  { set } for property=sys.usb.config pid=4877 uid=0 gid=0 scontext=u:r:recovery:s0 tcontext=u:object_r:system_radio_prop:s0 tclass=property_service permissive=1
- `recovery/current-recovery-dmesg.txt:2400` [current_recovery_or_host; filesystem] <3>[   26.479785]  [7:       recovery: 4877] EXT4-fs (sda31): errors=remount-ro for active namespaces on umount 0
- `recovery/current-recovery-dmesg.txt:3084` [current_recovery_or_host; display] <3>[  116.449301]  [2:  kworker/u16:0:    5] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:3092` [current_recovery_or_host; display] <3>[  118.455125]  [2:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:3130` [current_recovery_or_host; display] <3>[  118.624852]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:3131` [current_recovery_or_host; display] <3>[  118.624871]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:5381` [current_recovery_or_host; display] <3>[  576.269022]  [2:    kworker/2:2: 5026] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5397` [current_recovery_or_host; display] <3>[  576.472740]  [3:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5431` [current_recovery_or_host; display] <3>[  576.629331]  [0:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:5432` [current_recovery_or_host; display] <3>[  576.629343]  [0:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:5528` [current_recovery_or_host; display] <3>[  577.645477]  [2:    kworker/2:2: 5026] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5575` [current_recovery_or_host; display] <3>[  577.838363]  [5:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5611` [current_recovery_or_host; display] <3>[  577.996137]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:5612` [current_recovery_or_host; display] <3>[  577.996148]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:5681` [current_recovery_or_host; display] <3>[  578.058317]  [1:  kworker/u18:0: 1446] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6182` [current_recovery_or_host; display] <3>[  641.495155]  [2:  kworker/u16:4:  765] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6197` [current_recovery_or_host; display] <3>[  643.405582]  [2:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6235` [current_recovery_or_host; display] <3>[  643.575562]  [0:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:6236` [current_recovery_or_host; display] <3>[  643.575576]  [0:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:7774` [current_recovery_or_host; display] <3>[  950.406170]  [2:  kworker/u16:1: 5060] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8153` [current_recovery_or_host; display] <3>[ 1013.108254]  [3:  kworker/u16:4:  765] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8161` [current_recovery_or_host; display] <3>[ 1015.114122]  [1:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8199` [current_recovery_or_host; display] <3>[ 1015.283632]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:8200` [current_recovery_or_host; display] <3>[ 1015.283651]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:8764` [current_recovery_or_host; display] <3>[ 1175.078496]  [3:  kworker/u16:1: 5060] [SSP] send_panel_information, failed to send panel information

## Decision tree

1. **Previous-boot pstore/last_kmsg contains panic or mount failure:** examine precise kernel stack, error code and failing path; inspect BOOT initramfs and Fedora rootfs together.
2. **Recovery logs exist but previous-boot logs do not:** don't attribute recovery dmesg to Nuxel. Investigate UART/earlycon and kernel pstore support as a *separate, reviewed firmware/kernel modification*.
3. **BOOT/DTB fails before kernel logging:** consider S-Boot handoff, DTB/DTBO overlay application, cmdline, vbmeta/recovery launch semantics.
4. **Kernel starts but display stays black:** assess kernel log for DECON/DSI/panel failures. Phosh cannot fix absent DRM/KMS.
5. **systemd starts but UI absent:** check greetd/Phosh/Phoc services, permissions, seatd/logind, input and display nodes after bringing up a debug console.

No device writes, resets, repartitioning or flashing were performed by this triage tool.
