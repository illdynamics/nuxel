# PenGuru Squad v0.9.1-beta — host patch status and remaining device gates

**Release status:** source patch candidate. **Not** a verified flash image, on-device voice release, or completed GitHub publication. Generated from user-supplied `nuxel-main(1).zip` and the `png.zip` specifications with `beak.json` defaults.

## Implemented in this source patch

- Reset stale `onnxruntime-genai` preference to `auto` for GGUF model generation. Do not conflate SonarBird's ordinary ONNX Runtime MiniLM session with generative ONNX GenAI; current ChatBird and CodeBird GGUF variants use llama.cpp.
- Shared Beak config under `/var/lib/nuxel-penguru/beak.json`, with one API used by standalone Squad and Settings; imported eight owner-provided defaults, added push-to-talk enabled, continuous listening **off** until explicitly opted in.
- Beak controls and download-to-**untrusted staging** buttons for Qwen 0.6B ASR GGUF, Needle3, Whistle, and Spark TTS; pinned immutable source revisions where established; Spark source explicitly not pinned; bound download progress, cancellation and disk budget; no model execution/promotions from staging.
- Foreground-only 5s recording and review-before-send transcription user interface, opt-in wake phrase via ASR, simple RMS silence gate, capture shutdown on hide/off/stop, and optional talkback invocation.
- Conditional Qwen ASR CLI and Piper WAV adapters with bounded input and timeout. **Neither CLI, model, licensed voice, native VAD nor RNNoise runtime is delivered here.** These adapters refuse absent dependencies.
- Device installer for new settings module and Beak defaults, non-destructive Wi-Fi SSH userspace `flash.md`, full release/validation handoff prompt.
- `VERSION` changed to v0.9.1-beta; changelog, release notes and exact-source-SHA guard added to the existing fail-closed workflow.

## Host checks completed (2026-11-18)

- `services/nuxel-penguru/tests/test_registry.py` PASS.
- `services/nuxel-penguru/tests/test_routing.py` PASS.
- `services/nuxel-penguru/tests/test_installation.py` 5 PASS.
- `services/nuxel-penguru/tests/test_worker_protocol.py` 4 PASS.
- `services/nuxel-penguru/tests/test_beak.py` PASS.
- Python compile checks PASS.
- Updated JavaScript `node --check` PASS.
- `pwa/nuxel-common/verify-wiring.js`: ALL 7 PWA surfaces PASS.
- Workflow YAML parse successful; prepare/build/release jobs present.

## Not verified / requires user agent on the physical S10+

- No SSH connection, userspace installation, recovery/boot flashing, live app test or actual battery measurements were made in this environment.
- Real MiniLM ONNX Runtime inference, installed 384-dimensional classification package and runtime parity must be tested on handset.
- Qwen GGUF ASR CLI ABI/format compatibility on Linux ARM64, waveform transcription, wake-word accuracy and voice isolation pending.
- True **Silero VAD**, **RNNoise DSP**, Cactus `.cact` adapter, low-power always-on background wake and Spark TTS decoder **not implemented**; browser noise suppression and RMS energy gate do not replace RNNoise or Silero.
- Piper ARM64 CLI and owner-approved compatible voice are missing; default talkback ON in configuration does not imply playback works.
- Model component downloads are staging, not signed Model Store READY packages; avoid treating returned SHA as authenticated provenance.
- No Git remote push, pull request, merge, GitHub workflow trigger or release/tag creation occurred. Agent prompt instructs exact next operations, with **trigger only and no workflow monitoring**.

## Safety/rollback

`flash.md` installs only PenGuru + Settings userspace via existing transactional installer. It does not touch the phone boot partition, recovery, modem, sensor firmware or hardware. Verify SSH host identity and existing backup before deploying. Retain rollback receipts; no boot-image provenance claims without physical verification.

## 2026-11-18 final handoff refinements

- Verified the newly supplied `nuxel-main(3).zip` matches `nuxel-main(1).zip` by ZIP membership, per-entry CRC and uncompressed file size (21,844 entries). Reused the independently tested v0.9.1 patch rather than silently replacing newer code.
- Hardened API power toggle: only JSON booleans are accepted; malformed strings like `"false"` can no longer enable PenGuru. Added `test_beak_api_security.py`.
- Hardened startup against malformed persisted engine-override data and microphone capture against revoked audio tracks.
- `beak(1).json` exactly matches the eight owner defaults; off-by-default opt-in fields for continuous capture remain independently documented.
- **Not performed:** live SSH, on-device inference/voice acceptance, PR merge, release trigger. These are delegated to the one-shot agent after preflight.

## 2026-11-18 verified Wi-Fi userspace install

- Strict-host-key SSH preflight to `root@10.11.12.99` succeeded. The host reported `aarch64` and 53 GiB available on `/var`; no boot, recovery, modem, kernel, firmware, trust-key, or model-file operation was performed.
- Host regression suite was rerun before staging: Python compile, every `services/nuxel-penguru/tests/test_*.py`, changed-JS `node --check`, `pwa/nuxel-common/verify-wiring.js` (7/7), and Python YAML parsing of `.github/workflows/release.yml` all passed.
- Installed the documented userspace archive (SHA-256 `30239df5fca862be5f4883913f4bf2aa44eb94ae019f21c937803385ecd450bd`) through the transactional installer. Receipt: `/var/backups/nuxel-penguru/20261118T182934/receipt.json`. The prior service snapshot is `/var/backups/nuxel-penguru/pre-v091-20261118T172921Z-services.txt`; the existing Beak configuration was preserved.
- Post-install `nuxel-penguru` and `nuxel-http-bridge` were `active`. The live API reported Auto plus `llama.cpp` per-model overrides, READY/self-tested ChatBird and CodeBird GGUF packages, and READY/self-tested signed SonarBird MiniLM. `onnxruntime` 1.32.0 with `CPUExecutionProvider` is installed; SonarBird loaded successfully using ordinary ONNX Runtime after a Squad request.
- The live Beak API returned the owner defaults and correctly reported Qwen ASR, Whisper ASR, Whistle/Cactus, RNNoise, Silero, Piper and Spark unavailable. No staged artifact was promoted or executed. A short generation probe was cancelled after its client was interrupted; the service returned to `IDLE`, queue depth zero and no llama worker. Therefore actual ChatBird/CodeBird response acceptance and UI microphone/Stop/talkback acceptance remain **NOT VERIFIED**, not PASS.

## 2026-11-18 v0.9.1 follow-up deployment

- Fixed the Beak download routing defect: `start_beak_download` now starts and uses the isolated download service, rather than attempting a socket that may not exist.
- Chromium rendered-UI test passed: mouse checkbox toggle called the shared Beak API, changed state, and rehydrated after reload. The control path is a native checkbox `change` listener, so keyboard and touch activation use the same persistence/error-revert handler.
- The catalog now presents all nine required components. Qwen uses the owner-mandated official endpoint; Needle3, Whistle and Spark use pinned permanent Hugging Face revisions. Piper, Silero, RNNoise, Cactus runtime and Qwen decoder remain `SOURCE UNVERIFIED` and automatic install is fail-closed until compatible pinned artifacts, licensing and checksums are accepted.
- Generated canonical transparent 192 and 512 PWA icons from `assets/nuxel-penguru-squad.png`; corrected the transactional installer to copy nested PWA assets. The live path contains both icon files.
- Host validation passed: compileall, all `test_*.py`, JS syntax, PWA wiring and workflow YAML. Wi-Fi deployment archive SHA-256: `79f92e37c4665f6d77c714afb2145749c808dcc597704ce90540529515d7f0ec`. Rollback receipt: `/var/backups/nuxel-penguru/20261118T184611/receipt.json`. Both `nuxel-penguru` and `nuxel-http-bridge` are active; live catalog reports nine cards and the mandated Qwen URL.
