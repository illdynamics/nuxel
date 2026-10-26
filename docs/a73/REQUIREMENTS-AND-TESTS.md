# NUXEL A73 — Requirements traceability

| req | description | implementation | test evidence |
|---|---|---|---|
| A73-01 | Ghost PC penguin off after unplug | physical detach veto in `system_indicators.usb_connection()` + native `ind_pc_connected_ex()` | test-system-indicators 11c + C harness veto cases; PENDING physical unplug |
| A73-02 | Ghost Live Console penguin off after unplug; ON only for real session | three-layer model (`service_armed`/`transport_connected`/`session_active`), display predicate requires all three | test-system-indicators 12 + C harness; PENDING physical unplug |
| A73-03 | Preserve charging penguin artwork/size/position/animation | `power_state()` untouched; lockscreen.css/index.html/PNG untouched; only `qs.js?v` + sw/manifest cache strings changed | a69 PWA invariants; attached screenshot; charging state verified live |
| A73-04 | BT tile real status+toggle | `BluetoothConnector` + D-Bus `BluetoothGetStatus/SetPowered` + RPC + qs.js | live readback `service_unavailable`; set-powered refuses fake ON |
| A73-05 | Location tile real global policy | `LocationConnector` + D-Bus `LocationGetStatus/SetEnabled` + RPC + qs.js; `GetLocation` policy-gated | live set-enabled round-trip; persisted policy; no fix fabrication |
| A73-06 | Deploy + physically prove | native host rebuilt+deployed, bridge/qs deployed, hashes matched, logger left running | REPO-VS-DEPLOYED.md; evidence/; PENDING owner unplug |
| Preflight | Audit git vs deployed first | repo↔deployed hash table captured before edits (drift found and resolved) | REPO-VS-DEPLOYED.md |
| Safety | backup, no flash, console untouched, rollback | `/var/lib/nuxel/a73-backup/`; console PIDs unchanged; ROLLBACK.sh | PREFLIGHT-AND-ROLLBACK.md |

## Release gate (final acceptance)
1. charging penguin works — **PASS_DEVICE_RUNTIME** (live readback true + screenshot).
2. ghost PC + Live off on disconnect — **PENDING owner unplug** (code + offline
   truth table complete; physical proof requires the owner to pull the cable).
3. PC returns on with genuine data — **PENDING** (same owner action).
4. console ON reflects live host session — **PASS_DEVICE_RUNTIME** (attached),
   detach side **PENDING**.
5. BT tile real path + truthful blocker — **PASS_DEVICE_RUNTIME** (blocker
   `BLOCKED_FIRMWARE`; no fake ON).
6. Location tile real global policy — **PASS_DEVICE_RUNTIME** (round-trip +
   persistence; honest no-fix).
7. source matches deployed — **PASS** (all sha256 match).
8. boot/Wi-Fi/browser/lockscreen/nav regression — Wi-Fi/browser/nav/lockscreen
   **PASS_DEVICE_RUNTIME**; cold-boot visual **NOT_TESTED**.
