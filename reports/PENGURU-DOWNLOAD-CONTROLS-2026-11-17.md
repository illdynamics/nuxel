# PenGuru model controls — 17 November 2026

Starting branch: `feat/png`, HEAD `7d11c8d9`. This is an incremental
implementation/deployment milestone, not acceptance of the full AI specification.
The requested kickstarter file is named `penguru-squad/penguru-kickstart.md`.

## Implemented

- App and Settings now share one model library rather than separate download code.
- Immutable Hugging Face revision links, license acknowledgements, signed-manifest
  gating, progress/cancel, deletion confirmation and per-model runtime selection.
- Active jobs lock the acknowledgement and download button; terminal READY remains
  disabled. Failed starts restore the acknowledgement-dependent button state.
- Cancellation is checked before networking, staging, hashing, installation and
  starting the runtime self-test. An already executing self-test remains bounded
  by the existing runtime; this change does not promise immediate interruption.

## Verification

- Existing registry, routing, installation (5 tests) and worker-protocol (4 tests)
  suites passed on host.
- Three new synthetic cancellation tests passed; no network/model use in fixtures.
- Chrome headless executed `tests/model-library.html`: PASS for OFF, trust gating,
  safe text, revision-bound download, active-job lock, READY and runtime controls.
  This is UI fixture evidence, not a real Hugging Face download.
- Python compilation, JavaScript syntax checks, seven-app bridge wiring and
  `git diff --check` passed.
- SSH to root@10.11.12.99 worked with the specified key. Existing static service
  units and model/runtime installation were preserved.
- Receipt installer deployed the update, restarting only the HTTP bridge.
  Receipt: `/var/backups/nuxel-penguru/20261117T220347/receipt.json`.
  Final Settings preference correction redeployed and rechecked successfully:
  `/var/backups/nuxel-penguru/20261117T220435/receipt.json` (latest receipt).
- Real launcher-authenticated device API test passed enable/status with three
  cards, battery SYSTEM query, cross-app HTTP 403, and OFF. No model weights
  downloaded; no test keys enabled; no modem/sensor/display/network changes.

## Remaining gates

Production manifests are unsigned or test-signed; the installed CodeBird model
is not production-authorized. A new owner-local release key/enrollment or an
existing approved release key is required. Approval was requested, not assumed.
Preserve current trust until that choice is made. Signing is artifact attestation,
not legal license clearance; ChatBird provenance remains unresolved.

ORT GenAI worker packages, a learned SonarBird bundle, local voice/wake-word,
privileged action approvals and full physical UI/performance acceptance remain
unimplemented or unverified as described in the service README. Deterministic
routing and read-only system requests work; this is not the full requested system.

## Reproduce

Run the four existing `services/nuxel-penguru/tests/test_*.py` scripts and the new
`test_downloader.py`. Serve the repository on loopback and open
`services/nuxel-penguru/tests/model-library.html` in a browser for the UI fixture.
Use `tools/install-device.py --source-root STAGED_REPOSITORY` on the handset,
then `tools/device-api-check.py`; the latter leaves PenGuru OFF.
Rollback uses `tools/rollback-device.py` with the receipt path (see its CLI).
Do not copy private signing keys, enable test trust, or download model weights as
part of installation. Next owner decision is release signing-key enrollment.
