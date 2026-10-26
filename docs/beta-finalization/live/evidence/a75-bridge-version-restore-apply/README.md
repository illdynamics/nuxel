# a75-bridge-version-restore-apply — notes

All 7 install frames show `INSTALL-OK` with the expected previous hashes, so the
files were atomically installed and hash-verified on-device. The deploy tool's
final `deployment.json` was not written because the CDC-ACM console
re-enumerated (`OSError: [Errno 6] Device not configured`) during the
post-install health-check phase — a documented S10+ behaviour under sustained
console load, not a failed step.

Post-crash verification (separate live console sessions) confirmed every target
hash equals the repo bytes and both services were then
`daemon-reload`ed/restarted and report `0.6.5-beta` / `bridge_version 1`.
Recorded in `docs/performance/A75/deployed-hashes.json`.
