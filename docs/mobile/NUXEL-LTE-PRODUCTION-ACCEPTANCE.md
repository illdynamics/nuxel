# Nuxel LTE production acceptance — 2026-11-25

## Finisher acceptance — 2026-11-25

**BLOCKED at genuine PS registration; not LTE production accepted.**
Implementation commit **`c52726d3`**. Entry checkpoint `56b35c9d5b7a`, branch `cs/mob-round35-stage06`. Existing draft
implementation was completed/installed where independently achievable. Final
preference **ON**, CP ONLINE, SIM ready, RF ON, PS UNKNOWN/raw7, CS NOT_REGISTERED,
LTE RAT, reject0, no cellular IP. See [final state](evidence/finisher-20261125/final-state.json)
and [registration events](evidence/finisher-20261125/registration-events.json).

| Gate | Measured result |
|---|---|
| First enabled reboot | FAIL: missing /mnt/vendor/efs/nv_data.bin; loader never ran |
| Corrected enabled reboot | PASS startup/policy: read-only EFS, CP ONLINE, SIM ready, automatic native session; FAIL internet at PS_REGIST_VERIFY |
| Disabled reboot | PASS: preference disabled, CP ONLINE, IDLE, inactive CID1, no cellular addresses |
| QS OFF | PASS live WebKit widget click: durable OFF, correlated release/inactive readback, modem remains enabled; release of an already-active LTE bearer remains untested |
| QS ON | PASS request/policy: durable ON and real bounded connection attempt; FAIL carrier connection |
| Settings OFF/ON | PASS live rendered page clicks after exact legacy grant migration; OFF disabled, ON starts session |
| Settings/QS synchronization | PASS: actual QS DOM follows Settings OFF and ON without fabricated connected state |
| Top bar | PASS visible unknown/no-service indicator; no LTE registration claim; actual signal/serving operator decoding remains MISSING |
| NM | Temporary generic profile syntax accepted/deleted on NM 1.54.3; no bearer activation, DNS/route integration or live cleanup acceptance |
| Cellular-only HTTPS / DNS | BLOCKED: no carrier registration or usable cellular address |
| Reconnect with active service | Implemented/bounded; NOT physically verified without service |
| Wi-Fi | Preserved through reboot and UI tests; simultaneous live LTE coexistence NOT verified |
| USB / ZeroTier | PASS: both SSH paths available after controlled reboots; USB carrier1 |
| Speed test | NOT RUN; no LTE internet and allowance confirmation absent |
| Tests | Full host build.sh including ASan/UBSan and both 3000-case fuzz gates PASS; final AArch64 compile PASS; 31 focused Python tests PASS |

Live UI automation used the existing root-only host probe to click the real
rendered WebKit elements; it did not use a mock modem or replacement page.
[Settings screenshot](evidence/finisher-20261125/settings.png),
[QS screenshot](evidence/finisher-20261125/qs-connecting.png),
[disabled tile/top bar](evidence/finisher-20261125/topbar.png),
[UI probes](evidence/finisher-20261125/ui-probes.txt),
[Settings OFF](evidence/finisher-20261125/settings-off.json),
[Settings ON](evidence/finisher-20261125/settings-on.json).
The initial Settings attempt correctly failed capability checks after reboot;
only the exact shipped obsolete session grant was migrated, preserving owner
permissions/denials. This exposed a real integration defect before acceptance.

Reboot receipts retain distinct boot IDs:
[first failed](evidence/finisher-20261125/after-enabled-reboot.json),
[corrected enabled](evidence/finisher-20261125/after-corrected-enabled-reboot.json),
[disabled](evidence/finisher-20261125/after-disabled-reboot.json).
Final code's installed/running hashes match, with NRestarts=0 in the final boot:
[identity](evidence/finisher-20261125/identity.json). Enabled startup was tested
before the final bounded SIM-wait and IP-reporting refinements; the final binary
booted with OFF and then handled ON from QS/Settings. Automatic **internet**
after reboot is not accepted.

The older privacy-layout test `tests/pwnage52000/test_qs_privacy.py` still fails
its `privacy.hidden = !on` source assertion; that string is also absent at entry
HEAD. It was not changed as unrelated work. Host build tests include the owner's
preserved RFS policy/test edits. See [native log](evidence/finisher-20261125/native-tests.txt)
and [focused tests](evidence/finisher-20261125/focused-tests.txt).

The original verified production loader/guard and registration decoder were
preserved. Read-only EFS startup now has an actual bounded dependency, without
journal replay. No RF OFF/ON experiments, SMS/calls, firmware/NV/protected-content
writes, flashing, merge or push. Registration cause remains undiagnosed; do not
infer a carrier outage or bypass the gate. Existing SMS/telephony documentation
is retained below and in the handover.

---

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
