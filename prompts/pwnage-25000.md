# 🐧 NUXEL 25000 — LIVER THAN LIVE CONSOLE++
## Quick Kickstart / Pwnage Launcher

Work in the existing Nuxel repository for the Samsung Galaxy S10+ Exynos 9820 (beyond2lte), using the currently bootable Samsung-derived Linux 4.14 baseline.

Read and follow `NUXEL-25000-LIVER-THAN-LIVE-CONSOLE-PLUSPLUS-UBERPROMPT.md` completely.

### CRITICAL INCIDENT
A previous deploy used `tools/beta/live/nuxel-live-deploy.py` with `tools/beta/live/a75-bridge-version-restore-manifest.json` and was reported still running after about 5.5 minutes. `services/nuxel-bridge/src/bridge.py` is about 92 KB and may transfer in hundreds of base64 parts. The tool may hold the serialized physical console lock for the full transaction.

**First determine whether that deployment is still active or completed. Do not launch another deploy, kill the process, delete its lock, or run another serial command while the transport may still be owned.** Inspect host-side process state, logs, journal, lock owner, hashes and device/service status without contending for the serial stream.

### MISSION
1. Fix `declared_reload` so identical actions across a multi-file group are coalesced and executed once per transaction, not once per file. Do not restart `nuxel-bridge` five times for five files.
2. Measure the actual transfer bottleneck. Improve it using bounded block writes, acknowledgements, integrity checks, bounded retries and safe resume only where supported. Never interleave raw serial writers.
3. Improve lock ownership/recovery, transaction journaling, cancellation semantics, reconnect and rollback.
4. Make the console operator-grade: explicit states, truthful progress based on acknowledged bytes, elapsed time, measured throughput, retries, logs and actionable errors.
5. Add deterministic tests for duplicate reloads, transfer corruption/disconnect, hashes, lock contention, cancellation, restart failures and rollback.
6. Preserve known-good recovery and the existing Linux 4.14 baseline. Do not wipe data or flash unrelated partitions.
7. Deploy only after resolving the prior transaction, reviewing the diff, passing preflight/dry-run and confirming recovery is available.
8. Verify hashes, bridge health, reconnect, boot ID, lock release and repeated safe no-op deploys.
9. Report exact tests, before/after measurements, changed files and which physical tests were actually performed.

Inspect the current code and call chains; do not guess paths or line numbers. Make reviewable code changes and tests, not just a plan. Follow the full uberprompt for design, safety boundaries and acceptance criteria.
