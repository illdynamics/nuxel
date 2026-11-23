# 06 — DEEPSEEK PRO THINKING: SIM → Registration → Real LTE Data → ModemManager / NetworkManager

Read `00_MASTER_SAFETY_AND_TRUTH.md`. You may **not** mark this round PASS until the *physical CP* is online, *actual SIPC control exchanges* succeed, and the SIM/carrier session is real and consented. Do NOT modify DT or CP partition. Preserve independent USB connection when testing with Wi-Fi disabled.

## Protocol and SIM gate

With owner-approved inserted active SIM and plan, distinguish `ABSENT`, `PIN_REQUIRED`, `READY`, `ERROR`, `UNKNOWN` from protocol-backed SIM state. Never infer SIM present from `mmcli -L` or a stale `/var/lib/nuxel/modem/sim.json`, nor print PIN/PUK, IMSI, ICCID or IMEI. If PIN required, prompt in local privileged UI, zero temporary memory and enforce attempt limits; never brute-force. Read operator registration and RAT from real CP response; don't claim registration based on signal bars alone. No unapproved roaming or unexpected charges.

## Linux integration design

Only now compare a **real exact-version** ModemManager Shannon/SIPC custom plugin with a narrow service-backed MM-compatible transport or an isolated working vendor radio bridge. Document MM version/source ABI, plugin loadability, udev port identification, binding, D-Bus introspection and a successful real `mmcli -L` that identifies live hardware. No fake `org.freedesktop.ModemManager1` object masquerading as attached equipment. Implement only supported API gates: 3GPP registration, SIM, bearer connect/disconnect, signal. Call/SMS/IMS capability flags remain false until individually verified. Verify NetworkManager profiles, permissions, APN and IPv4/v6 method behavior; do not pull generic QMI/MBIM/PPP code unless transport is genuinely compatible.

## Data PASS must be unquestionably cellular

- Initial status: CP stable ONLINE; SIPC alive; SIM READY; registered with carrier/RAT known; NetworkManager profile owner-approved APN; mobile data authorization present.
- Establish actual PDP/data connection and identify which `rmnet` interface is used. Validate real interface UP, IP (including IPv6 where applicable), route table, DNS, connection ownership and counters.
- To rule out Wi-Fi/USB fallback, **preserve USB/serial as out-of-band management**, then conduct an explicitly safe isolated test where Wi-Fi is disabled only after recovery access is established. Observe selected network interface/routing via `ip route get`, per-interface byte counters, a new HTTPS request and public IP/traffic path where lawful; keep cellular data charges/data cap understood. Never simply disable Wi-Fi from sole SSH route.
- Test disconnect, reattach, link loss, no-SIM, radio-off/airplane, airplane release, carrier unavailability, DNS fail, daemon restart and cold boot. Preserve systemd device/host network service health, no repeated CP resets or carrier-registration storms.

## UI and truthful states

Network Settings, quick toggles, panel icon and status bar must render `no modem`, `CP offline`, `SIM missing`, `PIN required`, `searching`, `registered`, `attached`, `data active`, `failure`. Operator, bars, data icon and counters come only from authenticated live D-Bus state; no dummy carrier. An offline native modem may coexist with functional Wi-Fi. Keep capability boundaries separate; no SMS/voice PASS yet.

## Deliverables

`reports/S5000AP-06-LTE-REAL-LIVE.md`: exact device, current BOOT/DT hash, CP state, source/protocol version, SIM source, registration proof, interface/routing/DNS observations, HTTPS timestamps with route evidence, billing/cellular traffic proof as available, negative controls, airplane/reconnect/reboot evidence, log redaction. Record per-gate state and what still prevents data if blocked. Commit source/tests/docs, do not flash anything unless a distinct justified BOOT-only plan passes `09`.

### Flash subjobs

A. MM plugin compile/API/udev tests for pinned MM version. B. NetworkManager bearer/profile unit tests. C. Offline negative route/state machine fixtures. D. UI state machine/accessibility tests. Hardware/RF tests remain owner-reviewed and Thinking-coordinated.
