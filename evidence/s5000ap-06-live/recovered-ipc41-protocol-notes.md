# Recovered S5000AP/IpcProtocol41 protocol facts (source-backed, this round)

Source: vendor/lib64/libsec-ril.so (sda26, SM-G975F vendor, build ID 60889dd714394ae0db7c2ecc2bf2740f)
Method: on-device readelf/objdump/strings/nm (aarch64 binutils), read-only mount.

## FMT header (confirmed from IpcTxExchange disasm @0x342a80)
  7 bytes: u16 total_len, u8 msg_seq, u8 ack_seq, u8 main_cmd, u8 sub_cmd, u8 cmd_type
  Matches sipc_fmt_hdr (modem_prj.h). LIVE-correlated (AST_POWERON: main=0x13 sub=0x05 type=0x03).

## Dialect: IpcProtocol41 (confirmed)
  Class "IpcProtocol41" exported (IpcRx*/IpcTx* symbols). cmd_type enum has IPC_CMD_NOTI.

## main_cmd families (35, from *_SUB_CMD_UNDEFINED printf format strings)
  CALL, CDMA DATA, CFG, DISP, DOMESTIC, EMBMS, FACTORY, GEN, GPRS, GPS, IIL, IMEI, IMS,
  JPN, MCPTT, MISC, MMS, MODEMTEST, NET, OES, OMADM, PB, PROSE, PWR, QMIIMS, RFS, SAP, SAT,
  SEC, SMS, SND, SS, SVC, SYSTEM + MAIN_CMD_UNDEFINED

## RFS is handled by cbd, NOT libsec-ril
  IpcProtocol41::IpcRxRfs @0x340308 is a STUB (mov x0,xzr; ret).
  cbd binary (vendor/bin/cbd) handles NV/EFS + RFS via /dev/umts_rfs0.
  cbd references /mnt/vendor/efs/{nv_data.bin,fsm_data.bin,nv_5g_data.bin}, NV load.
  vendor.cbd.rfs_check_done / rfs_5g_check_done properties = RFS completion signals.

## Key exported functions (source offsets)
  IpcProtocol::ConvertToIpcCmd(int,int&,int&,int&,int&) @0x315190  (RIL req -> main/sub/type)
  IpcProtocol::ConvertIpcType(char*) @0x3155b8
  IpcProtocol41::IpcTxExchange(main,sub,type,seq,ack,len,buf) @0x342a80
  IpcProtocol41::IpcTxPsAttach @0x31fa98  (data/PS attach)
  IpcProtocol41::IpcTxGetAtr @0x342c28
  IpcProtocol41::IpcTxGetImsi @0x32b6d0
  IpcProtocol41::IpcRxSimInfo @0x344748
  IpcProtocol41::IpcRxPwrState @0x3400e8
  IpcProtocol41::IpcRxPwrUp @0x33ffa0
  IpcProtocol41::GetCmdTypeName(int) @0x323838
  IpcHijacker::GetIpcCmd(unsigned char*,int&,int&) @0x3164c8
  Nv::ProcessRfsPacket/ProcessRfsMessage/ProcessRfsMessageRecv @0x1d7f20/0x1d81d8
  Nv::SendRfsMessage @0x1dbfb8
  Modem::CreateRfsIoChannel/OpenRfsIoChannel @0x1dc6b0/0x1dc720
  ModemProxy::DefinePdpContext/SetAttachApn/SetDataProfile (data bearer)
  SimManager::* (SIM state), ImsManager::ReqImsDeregistration etc.

## cmd_type (IpcTxExchange stores type as a byte) and RFS opcode
  RFS request observed: [u32 len=25][0x0b][0x01][u16=15][u16=0]["DELETE_ALL_VIS\0"]
  RFS main_cmd family exists ("RFS_SUB_CMD_UNDEFINED"), handled by cbd.

## Note: NO command IDs are asserted as telephony semantics without further
   O4/O5 corroboration. These are O3 static candidates from the exact vendor RIL.
