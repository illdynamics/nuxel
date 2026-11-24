# Nuxel LTE speed test — 2026-11-25

## Finisher measurement status — 2026-11-25

**Not run: download, upload and latency are unmeasured.** The corrected normal
boot reaches CP ONLINE and starts the native session automatically, but PS
registration still fails with UNKNOWN/raw7. No cellular address, carrier DNS
or cellular-only HTTPS was established. Data-allowance confirmation also remains
absent. No speedtest-cli benchmark was invoked. See
[finisher acceptance](NUXEL-LTE-PRODUCTION-ACCEPTANCE.md).

**NOT RUN. No measured LTE throughput or latency is available from this pass.**

The physical handset remains unregistered for packet service after one bounded
NV-capable CP initialization and one registration-gated native session attempt.
CP is ONLINE, SIM ready, radio ON, reported RAT LTE, but PS registration is
UNKNOWN (raw 7), bearer inactive and rmnet0 has no IP configuration. See
[evidence](evidence/finalizer-20261125/final-state.json).

The owner's sufficient-data-allowance confirmation was requested and has not
been received. A speed test requires both that confirmation and verified
cellular-only DNS/HTTPS with an independent management path. No speed-test
package was installed, no benchmark was invoked, and Wi-Fi was not disabled.
The verified independent management path is USB SSH, port 2022.

| Measurement | Result |
|---|---|
| Carrier | Home PLMN 20408; registered serving carrier not established |
| Technology | CP reports LTE; registration absent |
| Interface | rmnet0 |
| IPv4 / IPv6 transport | Neither usable in this pass |
| Server, ping, download, upload, bytes | Not measured |
| Process exit status | Not applicable: no benchmark process |
| Cellular counters at final receipt | See linked JSON; zero RX/TX bytes and packets |
| Cellular-only routing verified | No |
| Reboot-to-internet time | Not measured |

Historical IPv6-only success remains documented in NUXEL-LTE-STATE.md. It is
not a measurement from this pass and does not establish present dual-stack
service. Once registration is restored, use the installed distribution's
`speedtest-cli` if present, inspect its supported options, and run one controlled
machine-readable test only after verifying traffic routing and data allowance.
