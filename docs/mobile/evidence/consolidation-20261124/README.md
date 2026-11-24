# Consolidation evidence receipts

2026-11-24; source commit `24e617639a9e91236b1d75d72c9bfaf26703e2f1`.
`live-state.json` is a redacted extraction of read-only device commands and one
bounded native session-start request. Raw busctl/SSH/journal observations stay
in `/tmp/nuxel-lte-consolidation/`; private configuration/binaries are also
backed up on-device in `/var/lib/nuxel/lte-consolidation-20261124/`.
No private database, EFS image, credentials or raw modem payload is included.

Each `.exit` records the actual corresponding command exit status. The host
radio build passed including both 3000-input fuzz gates and 12 sanitizer suites.
CP pytest passed 34 tests; the CP sanitizer runner passed 13 mock cases.
Native full build/test stopped on existing `rfs_policy.c` GCC warnings (exit 1).
Separate native core compilation and 12 suites completed; that wrapper then
failed at the absent `file` utility (exit 127). The follow-up `readelf` and hash
identification succeeded (exit 0); this does not turn the full native suite into
a pass. The phone-data runner failed to compile on macOS (`mkdtemp`, exit 1).

Reproduction commands and detailed boundaries are in the handover. Native
helper scripts stage builds only; they do not install or start any executable.
The CP hardware-enabled binary was compiled but never executed.
