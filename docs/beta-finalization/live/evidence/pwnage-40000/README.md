# PWNAGE-40000 evidence index

Live evidence is stored on the handset under `/root/pwnage-40000/evidence/`.
This directory mirrors the durable summaries and the source/deployment hashes.

| File (host) | Purpose |
|-------------|---------|
| `01-baseline.txt` (device) | identity, services, bootstrap state |
| `02-mixer-baseline.txt` (device) | control namespace and initial OFF values |
| `03-pipewire-baseline.txt` (device) | sink/default/volume |
| `04-installed-config.txt` (device) | stale deployed route and unit paths |
| `05-notes-discovery.txt` (device) | Notes a11y/storage discovery |
| `06-notes-interface.txt` (device) | FIFO and pwa store discovery |
| `07-extended-controls.txt` (device) | amp/DSP/PCM control values |
| `09-a11y-tree.txt` (device) | live focused Title entry |
| `10-ready-after-route.txt` (device) | MUB0 + both DSPs booted/running |
| `11-three-pow-attempt1.txt` (device) | first 3× pw-play |
| `12-post-attempt1.txt` (device) | post-play mixer and volume |
| `13-journal-and-mixer.txt` (device) | kernel ABOX traces and state |
| `14-preflight-attempt2.txt` (device) | route check before second play |
| `15-dapm-during-playback.txt` (device) | DAPM samples during playback |
| `16-three-pow-attempt2.txt` (device) | second 3× pw-play |
| `notes-works-*.json*` (device) | detector baseline/poll/result |
| `SOURCE-RECONCILIATION.md` | repo ↔ deployed hashes and deliberate differences |
| `FINAL-REPORT.md` | honest result and remaining work |

## Confirmation rule

A PASS is recorded only from a **fresh** `works` entry in the live focused
Notes Title field. `pw-play` returning 0 is not evidence of audibility.
