# Native cell information, vendor build 60889dd7

The DTK9 firmware in `packs/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac`
contains the same RIL artifact previously compared with the device vendor
partition (sms12 checkpoint). This does not establish that every DTK9 artifact
matches EFUJ2. Pinned libsec-ril SHA256:
`b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3`.

`analysis/verify_cell_vendor.py <libsec-ril.so>` runs the actual RX instructions
in Unicorn with synthetic records, allocator/string-copy stubs and no network,
modem, Android runtime, or subscriber data. It asserts both record variants.

IpcTxNetCellInfoList @3378d0 emits 8/17 GET. IpcRxNetCellInfoList @33c3b0
receives the complete seven-byte IPC header followed by payload. Native
fmt_rx_net_cell_info receives just the payload; do not mix these APIs.

The length arithmetic @33c464–33c4bc accepts old length
`11 + GSM*20 + CDMA*20 + LTE*31 + WCDMA*19`, or new length
`12 + GSM*20 + CDMA*20 + LTE*31 + WCDMA*19 + NR*51`.
The first four counts are at full-frame offsets 7–10 (255 means absent).
Old records begin full-frame+11/payload+4. New records begin +12/payload+5,
with NR count at +11. Exact length selects the form; no guessed offsets.

LTE third group: @33c7f8 sets output type 3 (RIL LTE), @33c804–33c810
copies record[0] to registered. Registration is 0=neighbor, 1=registered;
unknown values and multiple registered LTE records are rejected conservatively.
ASCII MCC comes from record+1 (3 bytes); MNC record+4 (3 bytes with '#' third
byte converted to NUL by @33c834–33c844). Numeric fields are little endian:

| Wire offset | Width | Meaning | Vendor destination |
|---|---|---|---|
| 7 | 4 | ECI | cell+24, identity+8 |
| 11 | 4 | PCI | cell+28, identity+12 |
| 15 | 2 | TAC | cell+32, identity+16 |
| 17 | 4 | EARFCN | cell+36, identity+20 |

Loads/stores @33c89c–33c8f0; stride 31 @33c994. Fifth group is NR (type6),
not LTE. Independent downstream mapping: MbimRespBuilder::FillLteCellInfo
@2d7578 copies identity+8 to MBIM cell ID, +12 to physical cell ID, +16 to
TAC, +20 to EARFCN. Field order also agrees with RIL_CellIdentityLte_v12 in
[AOSP ril.h](https://android.googlesource.com/platform/hardware/ril/+/master/include/telephony/ril.h).
Samsung uses char[4] MCC/MNC; do not assume AOSP's integer representation.

Only one registered record with exact serving PLMN match is exposed. Invalid
high ECI bits are rejected, never masked. Full tuple expires after 30 seconds,
is cleared on loss/RAT/PLMN change, and is refreshed every 20 seconds. The
serving record supplies PLMN; there is no home-PLMN substitution. NET_REGIST
payload[4:6] is the legacy LAC, not a proven LTE TAC source.

[TS 24.229 v15.6.0](https://www.etsi.org/deliver/etsi_ts/124200_124299/124229/15.06.00_60/ts_124229v150600p.pdf)
7.2A.4.3 item12 defines LTE PANI as MCC+MNC+four hex TAC+seven hex ECI.
The previous separate `utran-tac` parameter and MCC+MNC+eight-digit ECI were
incorrect. Incomplete tuples are omitted, not filled with invented values.
This correction alone does not establish a cause for SIP 480.
