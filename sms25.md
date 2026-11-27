# Round 25 — resumable engineering checkpoint

Mission NOT achieved. No physical submission or carrier acceptance. Message 4
queued, part queued, error/result 0, no audit events; messages 1–3 unknown and
untouched. No changes deployed yet. Budget telemetry unavailable; bounded
execution, no purchases. Starting checkpoint sms24.md read; claims challenged.

## Baseline (2026-11-27 16:19 UTC)
Running/installed MD5 0a09e67b82009ef09e528920a32aa387. PS LTE home, CID1/CID2
IPv6 addresses, P-CSCF host route on rmnet1, USB and ZeroTier present.
subscriber.conf and SMS DB mode 0600 root:root. Prior rollback binary verified:
/var/lib/nuxel/rollback-sms24r12-20261127T154133/nuxel-radiod
MD5 0cf607d4d5b1fbdcd1c38cc54b22fff3.
Latest observed REGISTER response SIP 480 before challenge. Eight bounded retry
cycles appear exhausted; no new registration attempt issued by this round.

## Vendor evidence in progress
./packs contains DTK9 AP/CP/CSC/BL firmware, extracted vendor.img.lz4, and
Lineage device configuration. Do NOT relabel the whole pack EFUJ2.
.vendor-ro/libsec-ril.so GNU build ID 60889dd714394ae0db7c2ecc2bf2740f,
SHA256 b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3;
prior sms12 comparison established same vendor library as device. MD5 f2c26fb8.
/tmp/full.dis is a disassembly of that binary.

Demonstrated local decoder defect: IpcRxNetCellInfoList @33c3b0 counts are
GSM, CDMA, LTE, WCDMA, optional NR. Sizes 20,20,31,19,51, not previous claims.
@33c464..33c4bc checks complete-frame length: 11 + first four blocks (old),
or 12 + first four blocks + NR*51 (new). Payload API excludes 7-byte IPC header.
Old records begin complete-frame+11 = payload+4; new at frame+12 = payload+5.
Live response plen=128 fits old four-count layout with four LTE records.
LTE @33c7f8 writes type=3; @33c804 copies record[0] into output+4.
@33c814..33c88c copies ASCII MCC[1:4], MNC[4:7], converts third MNC '#' to NUL.
@33c89c reads u32le +7 -> output+24; +11 -> output+28;
@33c8a0 u16le +15 -> output+32; +17 u32le -> output+36;
@33c994 stride=31. Trace output semantics independently before wiring.

No external-dependency conclusion justified: local decoder reconstruction is
making progress. NET_REGIST payload[4:6] is not yet validated as LTE TAC.
SIP PANI currently omits TAC from cell identifier and uses eight ECI digits;
check TS24.229 7.2A.4.3 (expected MCC+MNC+4 TAC+7 ECI).

## Next actions
Finish vendor semantic cross-check/emulation; replace wrong decoder, tests,
wire fresh full serving-cell tuple; validate PANI; test/build/deploy with rollback.
Audit SMS SIP acknowledgment semantics before releasing message 4: SIP 2xx
must not be treated as RP/carrier acceptance. Verify AP SIP incoming path.
Preserve owner-modified test binaries and untracked round18..25.md files.

## Implemented, pending deployment
Vendor offline emulator passes both layouts; downstream MBIM LTE conversion
and AOSP member semantics independently corroborate CI/PCI/TAC/EARFCN.
Replaced invented decoder/fixtures; complete PLMN match, neighbor filtering,
contradiction rejection, bounded lengths, 30s freshness and 20s read-only refresh.
Removed NET_REGIST legacy LAC from PANI. Correct complete LTE PANI syntax.
Added operator hold file /var/lib/nuxel/sms-submit.hold (present on device);
queued jobs will remain held when the new binary runs, incoming stays enabled.
Baseline binary + SQLite backup saved in /var/lib/nuxel/rollback-sms25-baseline.

Additional demonstrated defects: initial AKA Authorization missing (24.229
5.1.1.2.2a); authenticated Authorization concatenated onto previous header
because insertion preceded its CRLF; digest uri used IMPU rather than actual
Request-URI. Fixed all three. Reopen passed prev==t then zeroed its Retry-After
state; now snapshot hold before clearing. Tests exercise production alias.

## Pre-deploy validation
Focused fmt_rx / ims_sip / ims_sip_tr tests pass under ASan+UBSan.
Full host unit suites pass; 3000-input normal fuzzer passes (no crash/timeout).
Full sanitizer fuzz gate still running. AArch64 native build passes at interim
fe076d6d; final build underway after identity/Contact corrections.
Message 4 verified privately: exact authorized body match, recipient valid and
not subscriber, queued part/result0/status-1, zero audit events. No PII copied.
Persistent UUID instance provisioned mode0600, replacing fabricated zero IMEI.
Contact advertises SMS-over-IP and 600-second expiry, not unimplemented MMTEL.
Network refusal will persist an engineering registration hold containing the
minimum retry epoch. This deliberately prevents unchanged repeated attempts
across restarts; remove only after a meaningful correction and expiry.
