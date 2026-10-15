# Nuxel S10+ bootloop triage

**Result:** EVIDENCE_CAPTURED_NEEDS_REVIEW

Collected log files scanned: 37

A kernel panic cannot be ruled out by an empty pstore directory. The phone may reboot before pstore is initialized, or firmware may clear it.

## Evidence categories

- display (current_recovery_or_host): 42 occurrence(s)
- kernel_watchdog (current_recovery_or_host): 2 occurrence(s)

## Samples (review context in raw logs)

- `host-ioreg-usb.txt:11` [current_recovery_or_host; kernel_watchdog] |   "IOKitDiagnostics" = {"Instance allocation"=9999016,"Container allocation"=6525010,"Pageable allocation"=784400432,"Classes"={"AppleJPEGWrapperControlV8"=0,"KDISecondaryEncoding"=0,"RTBuddyFirmwareBundle"=0,"ApplePMPThermal"=0,"IOSkywalkPacketPoller"=0,"IO
- `kernel/cmdline.txt:1` [current_recovery_or_host; kernel_watchdog] console=ram loglevel=4 sec_debug.pcb_offset=7346944 sec_debug.smd_offset=7348992 sec_debug.lpddr4_size=8 sec_debug.dram_info=01,06,03,8G sec_debug.pwrsrc_rs=0x0000100140010000 sec_debug.reset_reason=9 sec_reset.reset_reason=9 sec_debug.reset_rwc=0 bootmode=2 s
- `recovery/current-recovery-dmesg.txt:149` [current_recovery_or_host; display] <3>[  116.449301]  [2:  kworker/u16:0:    5] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:157` [current_recovery_or_host; display] <3>[  118.455125]  [2:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:195` [current_recovery_or_host; display] <3>[  118.624852]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:196` [current_recovery_or_host; display] <3>[  118.624871]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:2446` [current_recovery_or_host; display] <3>[  576.269022]  [2:    kworker/2:2: 5026] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:2462` [current_recovery_or_host; display] <3>[  576.472740]  [3:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:2496` [current_recovery_or_host; display] <3>[  576.629331]  [0:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:2497` [current_recovery_or_host; display] <3>[  576.629343]  [0:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:2593` [current_recovery_or_host; display] <3>[  577.645477]  [2:    kworker/2:2: 5026] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:2640` [current_recovery_or_host; display] <3>[  577.838363]  [5:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:2676` [current_recovery_or_host; display] <3>[  577.996137]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:2677` [current_recovery_or_host; display] <3>[  577.996148]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:2746` [current_recovery_or_host; display] <3>[  578.058317]  [1:  kworker/u18:0: 1446] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:3247` [current_recovery_or_host; display] <3>[  641.495155]  [2:  kworker/u16:4:  765] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:3262` [current_recovery_or_host; display] <3>[  643.405582]  [2:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:3300` [current_recovery_or_host; display] <3>[  643.575562]  [0:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:3301` [current_recovery_or_host; display] <3>[  643.575576]  [0:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:4839` [current_recovery_or_host; display] <3>[  950.406170]  [2:  kworker/u16:1: 5060] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5218` [current_recovery_or_host; display] <3>[ 1013.108254]  [3:  kworker/u16:4:  765] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5226` [current_recovery_or_host; display] <3>[ 1015.114122]  [1:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:5264` [current_recovery_or_host; display] <3>[ 1015.283632]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:5265` [current_recovery_or_host; display] <3>[ 1015.283651]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:5829` [current_recovery_or_host; display] <3>[ 1175.078496]  [3:  kworker/u16:1: 5060] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6060` [current_recovery_or_host; display] <3>[ 1237.919741]  [0:    kworker/0:0: 5096] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6069` [current_recovery_or_host; display] <3>[ 1239.925438]  [3:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6107` [current_recovery_or_host; display] <3>[ 1240.094574]  [3:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:6108` [current_recovery_or_host; display] <3>[ 1240.094593]  [3:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:6635` [current_recovery_or_host; display] <3>[ 1561.332087]  [3:   decon0-fsync: 2856] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6792` [current_recovery_or_host; display] <3>[ 1621.738538]  [1:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6799` [current_recovery_or_host; display] <3>[ 1623.242850]  [1:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:6837` [current_recovery_or_host; display] <3>[ 1623.411951]  [0:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:6838` [current_recovery_or_host; display] <3>[ 1623.411970]  [0:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:7310` [current_recovery_or_host; display] <3>[ 1891.266724]  [2:   decon0-fsync: 2856] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:7508` [current_recovery_or_host; display] <3>[ 1953.302546]  [3:  kworker/u16:2: 5363] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:7516` [current_recovery_or_host; display] <3>[ 1955.307417]  [0:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:7554` [current_recovery_or_host; display] <3>[ 1955.474356]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:7555` [current_recovery_or_host; display] <3>[ 1955.474376]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)
- `recovery/current-recovery-dmesg.txt:7797` [current_recovery_or_host; display] <3>[ 2068.914538]  [0:   decon0-fsync: 2856] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8056` [current_recovery_or_host; display] <3>[ 2131.478181]  [3:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8068` [current_recovery_or_host; display] <3>[ 2133.489123]  [3:       recovery: 4877] [SSP] send_panel_information, failed to send panel information
- `recovery/current-recovery-dmesg.txt:8101` [current_recovery_or_host; display] <3>[ 2133.647286]  [1:       recovery: 4877] panel_bl_set_brightness, failed to write seqtbl
- `recovery/current-recovery-dmesg.txt:8102` [current_recovery_or_host; display] <3>[ 2133.647306]  [1:       recovery: 4877] panel_update_brightness, failed to set_brightness (ret -5)

## Decision tree

1. **Previous-boot pstore/last_kmsg contains panic or mount failure:** examine precise kernel stack, error code and failing path; inspect BOOT initramfs and Fedora rootfs together.
2. **Recovery logs exist but previous-boot logs do not:** don't attribute recovery dmesg to Nuxel. Investigate UART/earlycon and kernel pstore support as a *separate, reviewed firmware/kernel modification*.
3. **BOOT/DTB fails before kernel logging:** consider S-Boot handoff, DTB/DTBO overlay application, cmdline, vbmeta/recovery launch semantics.
4. **Kernel starts but display stays black:** assess kernel log for DECON/DSI/panel failures. Phosh cannot fix absent DRM/KMS.
5. **systemd starts but UI absent:** check greetd/Phosh/Phoc services, permissions, seatd/logind, input and display nodes after bringing up a debug console.

No device writes, resets, repartitioning or flashing were performed by this triage tool.
