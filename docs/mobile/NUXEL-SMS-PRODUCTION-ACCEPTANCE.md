# Nuxel SMS production acceptance — 2026-11-25

## Physical gate update (Round03 result 0x0002) — 2026-11-25

Result 0x0002 root cause established (see `NUXEL-SMS-RESULT-0x0002-REPORT.md`).
The daemon was rebuilt, deployed, and verified; the truthfulness fix makes
`GetSmsStatus` report `registration="cs-denied"` instead of the former PS-or-CS
`"registered"`. LTE remains ACTIVE with native IPv6 (HTTPS 200 through rmnet0).

| Gate | Actual result |
|---|---|
| Result 0x0002 decoded | PASS: CS-domain submission rejection, no TP-FCS cause |
| Root cause | PASS: CS registration DENIED, no CS SMS bearer on LTE-only service |
| Native correction deployed | PASS: CS-only SMS gate + truthful `cs-denied` status |
| New authorized SMS transmitted | NOT PERFORMED: no evidence-supported bearer for a genuine submission |
| LTE preserved | PASS: phase ACTIVE, ip_configured true, IPv6 HTTPS 200 |
| Installed/running daemon | PASS: `e439005f...ddf169` |

**SMS production acceptance remains NOT complete.** Genuine outgoing SMS still
requires an actual CS/SGs or IMS bearer; IMS SMS is out of scope this round.


## Physical execution acceptance (Round02 correlated) — 2026-11-25

Corrected native daemon deployed and physically verified through the Radio1
`SendSms` path. This run supersedes the earlier un-deployed Round02 attempt in
`NUXEL-SMS-STATE.md`.

| Gate | Actual result |
|---|---|
| Corrected daemon deployed | PASS: installed/running `nuxel-radiod` hash matches the rebuilt verified source |
| SMS unit suites | PASS: vendor golden vectors, codec, durable store, service durability/correlation (0 failures) |
| Native `SendSms` queue | PASS: returned native message id 3, durable `queued` → `sending` |
| Generic modem acknowledgment | PASS: SIPC ack observed; only confirms command acceptance |
| Submission result observed | PASS: decoded and durably retained; `type=3, plen=5, ack=0, result=2, mr=158, correlated=false` |
| Correlation | PASS (correct refusal): type-3 unsequenced modem reference is not a valid correlation token; returned MR 158 differs from requested TP-MR, so no false attribution |
| Final local message state | PASS: transitioned to `unknown` (error -2); no false delivered/submitted claim |
| Actual modem result code | 2 (non-zero = submission rejected by modem/carrier) |
| Carrier submission confirmed | FAIL: modem rejected with raw result code 2 |
| Recipient delivery confirmed | FAIL: no delivery report; message rejected, never delivered |
| Incoming SMS | NOT TESTED: no real incoming exchange was available this pass |
| LTE baseline preserved | PASS: native IPv6 on rmnet0, data session active, NetworkManager/ZeroTier/SSH active |

The previously reported recipient non-reception is now explained: the modem
rejects the outbound submission with raw result code 2, before any carrier
delivery path is reached. The result code was decoded and retained this pass
instead of being lost; it is not a standardized 3GPP cause and was treated as
"not zero = not submitted", never as delivery evidence.

Safety: one authorized physical submission only. No retransmit, no automatic
resend, no protected-partition or boot-policy writes. Messages 1 and 2 remain
`unknown` (historical uncertainty preserved); message 3 is a fresh native ID
whose rejection is recorded without falsely marking the originals delivered or
failed. Audit rows record the owner-authorized `superseded` reconciliations.

**SMS production acceptance is NOT complete.** The demonstrated blocker is the
modem/carrier submission rejection (result code 2). Further work requires
decoding that vendor-specific cause against the recovered EFUJ2 RIL before any
additional chargeable attempt.
