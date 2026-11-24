# Stage 06 — Round 44 Initial Reconciliation

Date: 2026-11-24 CET. Branch `cs/mob-round35-stage06`. Device SM-G975F/S5000AP.

## Recovered state (verified, not assumed)

- HEAD = `2c377487` "Implement native SMS transactions and record cellular-only
  HTTPS evidence" (SMS wire/codec/store/service committed).
- 12 files modified-but-uncommitted (radiod.c +173, fmt_rx/fmt_tx, build/install
  scripts, mobile.md, recover_vendor_vectors.py, tests).
- 10 untracked files: call_service.{c,h}, fmt_call.{c,h}, cellular_link.{c,h},
  scripts/cellular_link.py, tests/test_{call_service,fmt_call}.c,
  tests/vendor_call_vectors.h.
- Physical device reachable over ZeroTier 10.11.12.99 (root), kernel
  4.14.253 aarch64. Modem ONLINE. nuxel-radiod/zerotier/NetworkManager/sshd active.

## Live cellular milestone (preserved, active)

- rmnet0 UP with KPN global IPv6 `2a02:a420:265c:b063:8f9e:9c76:37:948c/64`.
- Policy routes table106 + rules 30600/30601 + metric2100 default route intact.
- wlan0 restored (10.20.30.16/24, Wi-Fi default metric600 preferred).
- usb0 DOWN (cellular-only test posture). ZeroTier alive.
- rmnet0 counters: RX 627700B/5030pkts, TX 1315609B/8221pkts, 0 err/drop.

## Deployed binary identity

- Running + installed = build-15 hash
  `c0c1af0ef9dd194ea527d828ea0a5c5175a64e7b32f79579c864ab588b105095`.
- build-15 compiled radiod+fmt_call+call_service but NOT cellular_link.c.
- installed bash `grep` shows no cellular_link.c in install.sh (gap).

## Astra's uncommitted telephony + auto-config work (recovered)

- fmt_call.c: dial/answer/release/get_list/voice_registration serializers,
  fail-closed CS-voice parsing, no emergency/supp service.
- call_service.c: call FSM (dial/answer/hangup, list/status tracking).
- cellular_link.c: forks /usr/libexec/nuxel/nuxel-cellular-link helper to apply
  CP-decoded addresses via scripts/cellular_link.py (iproute2 + resolvectl,
  undo journal, table106/rule30600/30601/metric2100).
- D-Bus: Dial/AnswerCall/HangupCall/GetCalls/GetVoiceStatus/GetPdpProfiles
  methods + IncomingCall/CallStateChanged signals wired in radiod vtable.

## Gaps identified (must fix before deploy)

1. install.sh omitted `src/cellular_link.c` (link error) — FIXED.
2. install.sh did not install `scripts/cellular_link.py` as the helper — FIXED.
3. dbus/nl.nuxel.Radio1.xml missing the 5 call methods + 2 signals — FIXED.
4. build.sh `${libs[@]}` empty-array under macOS bash3.2 `set -u` — FIXED
   (portable `${libs[@]:+...}`); pre-existing host artifact, not Astra logic.

## Remaining physical acceptance (not yet verified)

- SMS outbound/inbound physical delivery (needs owner-authorized test number).
- Voice outbound/inbound + two-way audio + data recovery after call.
- Automatic interface configuration (helper deploy + WAIT_IP closure).
- Reconnection, Wi-Fi/cellular transition, reboot persistence.

## Strategy

Preserve running cellular state. Build full native binary (with cellular_link.c)
on device, install helper, verify WAIT_IP closes without breaking the active
bearer. Then SMS, then telephony, then lifecycle/reconnection/reboot. Commit
only after physical acceptance; never overwrite owner changes.
