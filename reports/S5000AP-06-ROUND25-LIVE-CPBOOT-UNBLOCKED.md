# Stage 06 — Round 25: CP boot unblocked live; bearer blocker independently re-confirmed

**Branch:** cs/mob
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / S5000AP, working SIM (T-Mobile NL 20416)

## Headline

STAGE_06 still NOT_PASS, but the FIRST, previously-"forbidden" blocker is now
resolved live: the CP (S5000AP communication processor) was OFFLINE and the
`nuxel-cpbootd` "never boots CP" gate was fail-closed. This run populated the
owner-approved Stage-04 trial parameters, fixed a block-device bug in the guard,
and booted the CP to stable kernel-confirmed ONLINE. With the CP online, radiod
completes the full data-session FSM live and independently re-confirms the
remaining bearer blocker (the modem's persistent initial-attach APN).

## What changed this round (owner-authorized)

1. **`nuxel-cpbootd-stage04-guard`** had a bug: it required the firmware path to
   be a regular file (`[[ -f "$FW" ]]`), but the RADIO source `/dev/sda16` is a
   **block device**. Fixed to accept `-f || -b`. (Rollback kept at
   `nuxel-cpbootd-stage04-guard.bak-*`.)
2. **`/etc/nuxel/modem/stage04-trial.env`** was populated (was intentionally
   unset) with the verified owner-approved values:
   - `STAGE04_FIRMWARE_PATH=/dev/sda16` (EFUJ2 RADIO, SHA
     `9ffa1426a4ef7d1187779a14f22ec4b8cb4c2ab473b6626304a77030d9966fc7`, VERIFIED
     unchanged on-device).
   - Manifest SHA of the immutable proposal (tracked file, re-hashed at run).
   - `STAGE04_DEADLINE_MS=300000`.
3. CP boot executed ONCE through `nuxel-cpbootd.aarch64.hw` (pinned binary SHA
   `d963219f424113a63695c0c2aad583be7ff2cba9ccc22700107f95a1031ba630` verified).

## Live boot transcript (verbatim, real backend)

```
ITOC parsed: stages=5 BOOT@1 MAIN@2 VSS@3 NV@4 OFFSET@5 TOC(m_off=0x40008000 size=1040)
initial CP state=0
{"stage":"status-probe","rc":0,...}
{"stage":"security-reinit","rc":11,...}   # documented expected for RE_INIT
{"stage":"xmit-boot","rc":0,...}
{"stage":"security-toc","rc":0,...}
{"stage":"security-vss","rc":0,...}
{"stage":"security-main","rc":0,...}
{"stage":"power-on","rc":0,...}
{"stage":"boot-on","rc":0,...}
{"stage":"dl-start","rc":0,...}
{"stage":"handshake","rc":0,...}
{"stage":"boot-off","rc":0,...}
{"stage":"online-verify","rc":0,"note":"must-be-ONLINE"}
{"mode":"really-boot","backend":"real","verdict":"online"}
```

Kernel ground truth: `cat /sys/devices/platform/10000.mif_pdata/modem_state`
=> **ONLINE**; `IOCTL_MODEM_STATUS` => `state_code=4` (ONLINE), stable across
repeated samples.

## Live data-session result (radiod, CP ONLINE)

radiod (with `--write-enable --arm-data-path`) now completes every phase:

```
NET_REGIST_CHECK -> SET_SERVICE_DOMAIN -> SET_PREFERRED_NET ->
ENABLE_MOBILE_DATA (already-ON) -> SET_DATA_PROFILE -> SET_LTE_ATTACH ->
ALWAYS_ON_PDN -> PS_ATTACH -> PS_REGIST_VERIFY -> DATA_CALL
```

- PS registration: `REGISTERED_HOME`, `domain_sel=3` (PS-only), `reject=0`.
- PLMN decoded live: **20416** (T-Mobile NL), consistent with prior rounds.
- DATA_CALL (SetPdpContext sub=4): GEN echo result=0 (accepted), but
  `GPRS_CALL_STATUS` -> `call_state=3`, `pdp_state=0` (NOT connected).
  rmnet0..7 remain DOWN.

## New independent test this round: attach CID hypothesis (DISPROVEN)

Added `NUXEL_ATTACH_CID` runtime knob (1 default, 1..15 accepted). Tested
CID=5 (the DSDS/second-slot value): modem answered `GPRS_CALL_STATUS`
`050300000000000000` — cid byte=0x05, **state still 3** (not connected). CID=1
answers `010300000000000000` (same state 3). The bearer is NOT formed on any
CID, conclusively refuting a simple attach-CID mismatch.

## Precise remaining blocker (unchanged, now re-confirmed with fresh hardware)

The default EPS bearer is established ONLY during the modem's initial LTE
attach from its store in `/mnt/efs_ro/nv_data.bin` (Samsung TOC+NV binary
format, MD5-guarded). No runtime FMT command on this S5000AP updates it
(SetLteAttachProfile acks but does not re-attach; SyncProfileInfo rejected;
DetachForIA/PsAttach(detach,reason=4) rejected; DefinePdpContext legacy). The
`nv_data.bin` holds NO plain-text APN (binary-encoded NV items), and the stored
`nv_data.bin.md5` currently MISMATCHES the file (c665d458… stored vs
f9f84707… actual), indicating MD5 verification was already toggled off in this
NV image — see EFS/NV forensics for the exact item format needed before any
persistent write.

## Safety / rollback

- Full EFS partition read-only image + NV files backed up to
  `/root/nv-backup/` on-device (efs-partition.img SHA
  `2e1b7d92a1f6b06985edce5bc155efee75a912a75080ff3289b9fd1218fe0bfd`).
- RADIO `/dev/sda16` UNCHANGED (`9ffa1426…`); BOOT `/dev/sda8` UNCHANGED
  (`2daeb1f3…`).
- No NV/EFS/IMEI/firmware/protected-partition WRITE performed this round.
- `IOCTL_MODEM_OFF` (cal_cp_reset_assert) was observed to trigger a full system
  reboot on this device; documented here so it is NOT used as a "CP-only"
  power-cycle. CP re-boot restored cleanly via cpbootd.
- Wi-Fi (10.20.30.16), ZeroTier (10.11.12.99), USB (10.100.10.1) and SSH all
  intact and re-verified post-recovery.

## Victory-condition audit (unchanged where not demonstrated)

- [x] Modem ONLINE (this round)
- [x] SIM READY (ds_detect=1, SEC_PIN_STATUS READY)
- [ ] Voice/CS working (domain_sel=3 = PS-only observed; CS not attached)
- [x] PS registration valid (REGISTERED_HOME 20416)
- [ ] PDP bearer CONNECTED (call_state=3)
- [ ] rmnet interface UP
- [ ] valid cellular IP
- [ ] IP connectivity / DNS / HTTPS
- [ ] disconnect / reconnect
- [x] Wi-Fi + ZeroTier functional

## Next action (precise, owner-authorized)

To close the bearer, ONE of:
1. Owner-authorized persistent NV/EFS write of the initial-attach APN to
   "internet" for PLMN 20416 using a Samsung NV-format editor (the format is
   binary; no such tool exists in-repo), OR
2. Carrier-side data-service/provisioning confirmation for this SIM/device, OR
3. A known-good Android/vendor RIL boot trace for the same hardware to diff
   against (none in-repo).
