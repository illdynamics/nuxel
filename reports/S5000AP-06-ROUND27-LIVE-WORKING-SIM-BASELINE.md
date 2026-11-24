# Stage 06 — Round 27: Working SIM live baseline (KPN PLMN proven)

**Date:** 2026-11-24 CET
**Branch:** cs/mob @ bec66ee5
**Device:** Samsung SM-G975F (beyond2lte), native Nuxel Linux

## State established this session
- SSH root@10.11.12.99 works (ZeroTier); WiFi/ZeroTier/USB all preserved.
- CP: ONLINE. SIM seated (ds_detect=1). All umts_* nodes present.
- radiod running: `/usr/libexec/nuxel/nuxel-radiod --write-enable --arm-data-path`
  SHA256 6a3b77b186386bf254faf75db805ea54b4ade7dd9ae4e521abb1d98a6aa9b906
- **NEW (working SIM):** NET_SERVING_NETWORK = ASCII "20408" (KPN), vs prior
  empty PLMN "00000000". SIM is now gennuinely registered on KPN.

## Live FSM run (full, correct byte-exact sequence)
SET_SERVICE_DOMAIN -> SET_PREFERRED_NET -> ENABLE_MOBILE_DATA (GEN=3 idempotent)
-> SET_DATA_PROFILE -> SET_LTE_ATTACH -> ALWAYS_ON_PDN -> PS_ATTACH
-> PS_REGIST_VERIFY (REGISTERED_HOME, ps=1) -> DATA_CALL.

## THE REMAINING BLOCKER (unchanged symptom, now on a working SIM)
At DATA_CALL: fmt_tx SetPdpContext main=13 sub=4 len=112 -> GEN echo 0d04030080 OK
-> GPRS_CALL_STATUS payload `010300000000000000` => payload[1]=3 (NOT connected).
No GPRS_IP_CONFIGURATION. No ESM cause. rmnet0..7 DOWN. No cellular IP.

## Notes
- SEC_SIM_ICC_TYPE=02 (USIM). SEC_PIN_STATUS alternates 0000/8200/8300.
- SMS family frames observed: main=4 sub=7, main=4 sub=12 (UNKNOWN names).
- NET_REGIST decode net_regist_state also momentarily ps=4 (UNKNOWN) before
  settling to ps=1 (REGISTERED_HOME), domain PS_ONLY.

## Next-investigation leads
1. call_state=3 decode: verify against vendor IpcRxGprsCallStatus once more;
   state 3 may be "connecting" not "failed" (needs a follow-up status poll
   rather than immediate REJECTED).
2. SetPdpContext APN path: confirm g.dsc.apn == "internet" (KPN). pdp_type_wire
   =1 (full APN path) by default; may need to try pdp_type_wire=4 (EUTRAN-only)
   for KPN.
3. Persistent initial-attach APN: vendor SetAttachApn is userspace-only (answer
   A, already proven); real attach is via SetLteAttachProfile flag=1 (define).
