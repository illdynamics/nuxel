# S5000AP Stage-06 — Data-path FMT TX serialization (recovered, source-backed)

SPDX-License-Identifier: CC-BY-SA-4.0
Status: research checkpoint — TX frame format + target function map recovered; payload decoding in progress.

## Authoritative vendor reference
`/tmp/vendor-ro/lib64/libsec-ril.so` (SM-G975F / EFUJ2, read-only mount on sda26)
  GNU Build ID  60889dd714394ae0db7c2ecc2bf2740f
  file SHA-256  b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3

## FMT TX wire format (CONFIRMED this round via IpcTxExchange disassembly @0x342a80)
The kernel strips/aliases the SIPC5 link header on RX and prepends it on TX.
Userspace writes to /dev/umts_ipc0 (and rfs0) a FMT message directly:

    [u16 total_len LE] [u8 msg_seq] [u8 ack_seq] [u8 main] [u8 sub] [u8 type] [payload...]

where total_len == 7 + payload_len.

Samsung packing idiom for main/sub (le/position): `strh (main | (sub<<8))` at FMT
header offset 4 => main at +4, sub at +5. Verified against GetPdpContext (main=13
GPRS, sub=4 PDP_CONTEXT => 0x040d) and PsAttach (main=13, sub=3 PS => 0x030d).

This matches the existing transport.h contract: `nuxel_dev_write` writes the
7-byte sipc_fmt_hdr + payload; kernel adds the link header. RFS responder already
works this way (14-byte raw record to /dev/umts_rfs0).

## Target data-path functions (exact dynamic symbol addresses)
| function | addr | main/sub | TX len |
|---|---|---|---|
| IpcTxExchange(char m,sub,type,ack,msg, payload*, int) | 0x342a80 | (generic) | 9+len |
| IpcTxPsAttach(u8,bool,bool,DataDetachReason) | 0x31fa98 | 13/3 (GPRS_PS) | 10 |
| IpcTxDefinePdpContext(apn*,u8,DataProtocol,bool,u8*,u8*) | 0x31f580 | 13/1 | 134 |
| IpcTxSetPdpContext(u8,int,apn*,user*,int,int) | 0x31f6e0 | 13/4 | var |
| IpcTxGetPdpContext(void) | 0x31f928 | 13/4 | 7 |
| IpcTxSetDataProfile(apn,user,pass,DataAuth,DataProtocol,DataProfile,bool,PcscfViaPco,int,int,int) | 0x31ff48 | 13/23 | 203 |
| IpcTxSetLteAttachProfile(...) | 0x320238 | 13/? | 201 |
| IpcTxSetDataCallEstablish(bool) | 0x320a10 | 13/25 | 8 (payload) |
| IpcTxSetMobileDataSetting(bool,bool) | 0x3214c8 | 13/25 | 9 |
| IpcTxSetAlwaysOnPdn(bool,DataProfile,int) | 0x321550 | 13/27 | 9 |

`IpcTxParseFmt`-style builders use the inline (stack) pattern, NOT Ipc41PacketBuilder
(which is only used by legacy CDMA/mobile-IP commands).

## Decoded TX payloads (this round)
### PsAttach (10-byte frame, main=13 sub=3 type=3 NOTI-class? see note)
    +0 u16 len=10
    +2 u8  msg_seq=0
    +3 u8  ack_seq=0
    +4 u8  main=13
    +5 u8  sub=3
    +6 u8  type=3
    +7 u8  attach flag (0/1)    ; w2 bit0 => 1
    +8 u8  flag (w3 bit0=>1)    ; "attached" indicator
    +9 u8  detach reason (w4, clamped 0..4)
### SetDataCallEstablish (8-byte payload frame, main=13 sub=25)
    payload[0]=0x0000020300000008 big; on LE: bytes = set flag at +7 (w1 bit0 => 0/1, eq=>inc)
### SetMobileDataSetting (9-byte frame, main=13 sub=25)
    +0 u16 len=9; +4 main/sub=0x190d... w8 (0/1) at +15-style -> data-enable byte
## Remaining
- Confirm exact payload offsets for DefinePdpContext (134-byte APN/profile blob) and
  SetDataProfile (203-byte) — disassembly captured in /tmp/analysis/IpcTx_data.txt.
- Recover APN string encoding + auth/protocol enum numeric values.
- Determine correct carrier APN (T-Mobile NL, MCC204/MNC16: default `internet`).

## Safety
No speculative TX yet. No DT/CP/protected-partition writes. All analysis read-only
against /tmp/vendor-ro. Disassembly cached in /tmp/analysis/*.txt on device.
