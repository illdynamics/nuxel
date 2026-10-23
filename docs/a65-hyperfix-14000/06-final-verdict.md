# A65 — Final acceptance verdict

| ID | Status | Evidence |
|---|---|---|
| A65-01 | PASS_PHYSICAL | GTlsBackendGnutls True; WebKitGTK loads google.nl/example.org, rejects badssl |
| A65-02 | PASS_PHYSICAL | NM state 100 + connectivity 4; bridge wifi_stage=online; deployed bytes == repo |
| A65-03 | PARTIAL | Immediate screen-off lock present; configurable lock-delay enum not yet in Home Settings |
| A65-04 | PASS (runtime-verified) | nuxel-navdock layer-shell running; OSK above dock |
| A65-05 | PASS (runtime-verified) | navdock + wlr-foreign-toplevel home action running |
| A65-06 | PASS (runtime-verified) | button-manager FSM + navdock long-press; scoped kill receipt |
| A65-07 | PASS (source-verified) | favorites rendered only on Home |
| A65-08 | PASS_OFFLINE_ONLY | browser toolbar compact/undecorated (py_compile + hash match) |
| A65-09 | PASS_PHYSICAL | live battery level=100; lockscreen.js == repo; never synthetic 0% |
| A65-10 | PARTIAL + BLOCKED_HARDWARE (auto) | 7 modes selectable; manual 0/90/180/270 work; BCM4773 exposes no IIO accel channels |
| A65-11 | PASS_OFFLINE_ONLY | livePreview no longer evaluates; Equals-gated |
| A65-12 | PASS_OFFLINE_ONLY | concise status + Retry + diagnostics (PWA + native) |
| A65-13 | PASS_OFFLINE_ONLY | native camera explicit Close + bounded retry; global nav escape |
| A65-14 | PASS (source-verified) | launcher/pwa-host activation registry present |
| A65-15 | PASS_OFFLINE_ONLY | browser + native camera undecorated |

Camera capture (real frames) and accelerometer auto-rotation are BLOCKED_HARDWARE by
the vendor FIMC-IS camera stack and the BCM4773 sensor hub's lack of IIO accel channels,
respectively — reported separately, not faked.
