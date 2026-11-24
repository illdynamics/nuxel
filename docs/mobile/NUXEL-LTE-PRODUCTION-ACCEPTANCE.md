# Nuxel LTE production acceptance — 2026-11-25

**BLOCKED at genuine packet-service registration. Not production LTE accepted.**

Entry: `cs/mob-round35-stage06`, `4b95f377a0fe742a103ff7f2a8260e1b3fae8c47`.
Boot-layer implementation checkpoint: `f42c18ef`. Owner's unfinished policy/UI
changes were preserved; they were not deployed as accepted production code.

One bounded boot with the verified NV-capable loader returned ONLINE (exit 0),
including verified device-owned NV download. Native OES transfer completed and
SIM became ready. One subsequent session configured wire1 CS+PS and mode11,
but again failed at PS_REGIST_VERIFY. Raw PS state 7 remains UNKNOWN; decoding
was not changed. This demonstrates that the old production loader was **not
the sole cause**. It does not establish carrier outage, provisioning trouble,
or a different root cause. No subsequent reset loop was attempted.

[Physical receipt](evidence/finalizer-20261125/final-state.json),
[registration events](evidence/finalizer-20261125/registration-events.json),
[CP boot transcript](evidence/finalizer-20261125/cpboot.log).

| Requirement | Actual result |
|---|---|
| Native CP initialization | PASS — controlled physical NV-capable boot; normal reboot untested |
| SIM readiness | PASS — ready |
| Genuine LTE registration | FAIL — PS UNKNOWN/raw7, CS NOT_REGISTERED |
| Active cellular bearer | FAIL — no active bearer established |
| Cellular IP configuration | FAIL — no cellular IP |
| Cellular DNS | BLOCKED |
| Cellular-only HTTPS | BLOCKED |
| NetworkManager integration | FAIL — rmnet0 unmanaged; no MM modem |
| Automatic connection | NOT ACCEPTED |
| Automatic reconnection | NOT ACCEPTED |
| Mobile-data OFF | NOT PHYSICALLY TESTED |
| Mobile-data ON | NOT ACCEPTED — native start failed registration |
| Enabled preference survives reboot | NOT TESTED |
| Disabled preference survives reboot | NOT TESTED |
| Settings page integration | Draft owner changes retained; not deployed/accepted |
| Quick Settings integration | Draft owner changes retained; not deployed/accepted |
| Top bar integration | Draft owner changes retained; no rendered acceptance |
| Wi-Fi coexistence | Existing Wi-Fi preserved; transitions not tested |
| USB management | PASS — SSH over USB port 2022; carrier1 |
| SSH and ZeroTier | PASS — reachable and services active |
| Relevant regression tests | Host suites/ASan/UBSan PASS; phone sanitizer allocation FAIL; NM/UI/physical gates missing |
| Cellular-only speed test | NOT MEASURED |
| Implementation committed | PASS for scoped boot-layer correction; LTE mission incomplete |
| DeepSeek handover | Updated with blocker and exact continuation steps |

```text
NUXEL LTE PERFORMANCE

Carrier: registered serving carrier unavailable; home PLMN 20408
Technology: LTE reported, PS registration UNKNOWN
Interface: rmnet0
IP family: none currently usable
Ping: not measured
Download: not measured
Upload: not measured
Test server: not selected
Cellular-only routing verified: no
Reboot-to-internet time: not measured
```

No SMS submission, calls, IMS work, kernel/BOOT/DTB/DTBO/firmware changes or
EFS/NV/identity/calibration writes. EFS remained read-only. No normal reboot,
Wi-Fi disable, merge, push or completion marker. Production boot guard uses
persistent inputs and a separate loader; starting it while CP was ONLINE
correctly did no boot/reset. This is narrower than reboot persistence acceptance.
