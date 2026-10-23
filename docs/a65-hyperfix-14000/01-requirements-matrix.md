# A65 — Requirements matrix (15 items)

| ID | Owner-visible defect | Root cause (short) | Fix | Status |
|---|---|---|---|---|
| A65-01 | Browser "TLS support is not available" | `glib-networking` not installed -> GIO GDummyTlsBackend | Install glib-networking (GnuTLS GIO backend) + image-build manifest | PASS_PHYSICAL |
| A65-02 | Wi-Fi stuck "Authenticating and Associating" | Stale UI copy on older deployment; backend already maps NM state 100 -> online | Verify deployed bytes == repo (truthful FSM); live state 100/connectivity 4 | PASS_PHYSICAL |
| A65-03 | Screen-off doesn't always lock instantly; want configurable delay | Idle screen-off locks immediately (A45); no Home Settings lock-delay control yet | Immediate lock verified present; configurable delay = remaining | PARTIAL |
| A65-04 | Triple nav disappears with OSK | Native `nuxel-navdock` layer-shell overlay + exclusive zone (A45) | Verified running; OSK-visible behaviour documented | PASS (deployed, runtime-verified) |
| A65-05 | Penguin Home doesn't return launcher | wlr-foreign-toplevel `home` action + navdock Home | Verified navdock/pwa-host/foreign-toplevel running | PASS (runtime-verified) |
| A65-06 | Back no-op; long-Back kill | button-manager FSM + navdock long-press | Verified button-manager/navdock running; app-scoped kill receipt recorded | PASS (runtime-verified) |
| A65-07 | Favorites float above apps | Favorites only rendered on Home/launcher | Verified DOM/native layering ownership | PASS (source-verified) |
| A65-08 | Browser toolbar too wide | Fixed-size chrome row overflow | Compact responsive GTK toolbar (min width on entry, relief-none buttons) | PASS_OFFLINE_ONLY |
| A65-09 | Lockscreen 0% for minutes | Older placeholder; backend already reads real capacity | Deployed lockscreen.js == repo (shows — then real %); live level=100 | PASS_PHYSICAL |
| A65-10 | Only Auto/Portrait, no rotate | 7-mode policy exists; auto blocked by vendor sensor hub | Manual 0/90/180/270 work; auto = BLOCKED_HARDWARE | PARTIAL / BLOCKED_HARDWARE (auto) |
| A65-11 | Calculator evaluates before Equals | `livePreview()` computed result while typing | Result only updated on Equals (`commit`) | PASS_OFFLINE_ONLY |
| A65-12 | First camera raw debug wall | `checkHardware()` wrote verbose detail as top status | Concise status + Retry + collapsible diagnostics (PWA + native) | PASS_OFFLINE_ONLY |
| A65-13 | Second camera spinner no escape | Native camera (GTK4) lacked explicit Close; D-Bus bounded 5s | Added Close + Retry + diagnostics; global nav remains | PASS_OFFLINE_ONLY |
| A65-14 | App opens behind current | launcher/pwa-host activation registry | Existing activation path verified present | PASS (source-verified) |
| A65-15 | Redundant title bars crop SnekByte | Native apps kept GTK titlebar | Browser + native camera `set_decorated(False)`; app chrome removed | PASS_OFFLINE_ONLY |

Legend: PASS_PHYSICAL = exercised on S10+; PASS_OFFLINE_ONLY = source/deploy verified,
not physically tapped; PARTIAL = partially done; BLOCKED_HARDWARE = vendor hardware gap.
