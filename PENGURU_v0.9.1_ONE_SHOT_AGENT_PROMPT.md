
# NUXEL v0.9.1-beta — PENGURU SQUAD VOICE DOWNLOADS, UI FIXES, APP DRAWER ICON & LIVE DEPLOYMENT

You are continuing work on the existing Nuxel Linux repository for the Samsung Galaxy S10+ Exynos 9820.

**IMPLEMENT THE CHANGES. DO NOT STOP AT PLANNING.**

This is an additional task following the previous PenGuru Squad implementation and deployment.

Preserve all working functionality, especially ChatBird, CodeBird, SonarBird MiniLM, ONNX Runtime 1.32.0 CPU, and existing model files.

## P0 — Fix the PenGuru Squad download list immediately

**CURRENT BUG:** The PenGuru Squad application only shows a Whisper download option, despite the owner explicitly requesting Qwen ASR, Needle3, Whistle and Spark TTS.

This is unacceptable. Fix the actual source of the model catalog, frontend filtering, registry entries and API responses.

The following four entries are **MANDATORY** and must always be visible in the PenGuru Squad application under **Beak → Voice Models & Components**:

| Display name | Exact filename | Type |
|---|---|---|
| Qwen3 ASR 0.6B INT4 | `qwen3-asr-0.6b-q4_k_m.gguf` | Speech-to-text |
| Needle3 | `needle3.cact` | Cactus voice model |
| Whistle | `whistle.cact` | Cactus voice model |
| Spark TTS | `spark-tts-tunartts-v1.Q4_K_M.gguf` | Text-to-speech |

**Qwen download URL — use this exact permanent Hugging Face endpoint:**

https://huggingface.co/OpenVoiceOS/qwen3-asr-0.6b-q4-k-m/resolve/main/qwen3-asr-0.6b-q4_k_m.gguf?download=true

**Needle3 source:** The owner supplied an `us.aws.cdn.hf.co/xet-bridge-us/...` download URL with the filename `needle3.cact`.

**Whistle source:** The owner supplied an `us.aws.cdn.hf.co/xet-bridge-us/...` download URL with the filename `whistle.cact`.

**Spark TTS source:** The owner supplied an `us.aws.cdn.hf.co/xet-bridge-us/...` download URL with the filename `spark-tts-tunartts-v1.Q4_K_M.gguf`.

The three Xet URLs are signed temporary CDN links, not permanent source URLs. Locate their canonical Hugging Face repository IDs, exact filenames and revisions. Generate stable `/resolve/<revision>/<filename>` download URLs and verify them before enabling the download action.

**Do not fabricate repository IDs or use expired CDN URLs.** If source resolution fails, retain a visible component card with `SOURCE UNVERIFIED` and explain the blocker.

Whisper may remain as an optional legacy component, but it must never replace, hide, or take priority over the four requested entries.

### Additional required components

Also show downloadable/installable cards for:

- Silero VAD ONNX model.
- RNNoise native ARM64 library.
- Piper TTS ARM64 runtime.
- Piper compatible ONNX voice and voice configuration.
- Cactus ARM64 runtime.
- Qwen ASR compatible ARM64 runtime.

For components that require a build rather than a model download, provide an **Install Runtime** or **Build Runtime** action with an accurate status instead of a misleading download button.

Every component must have its own registry entry and UI card.

## P1 — Make every download button functional

Each downloadable model must have:

- A working **Download** button.
- Verified source URL.
- Download size where available.
- Real progress bar.
- Downloaded bytes and percentage.
- Cancel, retry and resume when supported.
- SHA-256 verification.
- Persistent installed state.
- Atomic model-store installation.
- Runtime compatibility validation.
- Test button.
- Safe removal.
- Clear errors.

A download button must initiate a real backend-managed download to the Nuxel phone, **not merely open the Hugging Face webpage**.

Use the existing downloader and model registry where possible. Avoid creating a second independent download system.

Do not execute unverified downloaded binaries or promote partially downloaded files.

Use these states:

`NOT INSTALLED → DOWNLOADING → VERIFYING → INSTALLED → READY`

Also support `PAUSED`, `FAILED`, `INCOMPATIBLE`, `SOURCE UNVERIFIED`, and `RUNTIME MISSING`.

**Acceptance requirement:** All four owner-specified model cards must appear simultaneously in the actual running PenGuru Squad application, regardless of whether their runtimes are installed.

## P2 — Fix all unclickable voice settings

**CURRENT BUG:** Voice control checkboxes and toggles cannot be clicked.

Reproduce and fix the root cause.

Inspect:

- Disabled input attributes.
- CSS `pointer-events`.
- Overlays and stacking contexts.
- Broken labels or input IDs.
- JavaScript initialization errors.
- Missing event handlers.
- Failed API calls.
- State hydration.
- Browser/PWA caching.
- Mobile touchscreen handling.

Ensure all voice settings are interactive and persistent:

- Push-to-talk.
- Continuous listening.
- Wake-word listening.
- Wake phrase `Penguru`.
- Talkback on/off, default ON.
- Qwen ASR selection.
- Piper/Spark TTS selection.
- Silero VAD.
- RNNoise.
- Interrupt on speech.
- Microphone permission and device selection where supported.

Each setting must respond to clicks, save to the shared Beak backend configuration, survive reload, and remain synchronized between PenGuru Squad and PenGuru AI Settings.

If a dependency is unavailable, show an explanatory status. Do not silently ignore clicks.

Continuous listening must remain explicitly opt-in, with a visible microphone indicator and Stop control.

## P3 — FIX THE APPLICATION ICON IN THE NUXEL APPS DRAWER

**CURRENT REQUIREMENT:** The PenGuru Squad icon displayed in the Nuxel application drawer must come from:

`./assets/nuxel-penguru-squad.png`

This is mandatory.

Inspect the actual Nuxel apps drawer implementation and determine how it resolves application icons.

Update the **PenGuru Squad application registration/manifest** to reference the correct deployed icon.

Do not assume that updating a PWA manifest alone will change the Nuxel apps drawer icon.

Specifically:

1. Locate the PenGuru Squad entry in the Nuxel apps drawer registry.
2. Locate the current icon reference and identify why it is wrong or missing.
3. Use `./assets/nuxel-penguru-squad.png` as the canonical source asset.
4. Ensure the image is copied into the correct deployed assets directory.
5. Update the apps drawer entry to reference the deployed icon URL/path.
6. Update desktop launcher and `.desktop` metadata if applicable.
7. Generate appropriate PWA icon sizes from the same source image.
8. Invalidate stale icon caches or update asset versions where needed.
9. Verify the correct icon is displayed in the **actual running apps drawer on the phone**.

Preserve image transparency, proportions and artwork.

Do not replace unrelated Nuxel application icons.

**Acceptance requirement:** Opening the Nuxel apps drawer must show the official PenGuru Squad PNG as the PenGuru Squad application icon, not a generic placeholder, emoji, old icon or broken image.

## P4 — Connect installed components to Beak

Target pipeline:

`Microphone → RNNoise → Silero VAD → Qwen ASR → SonarBird → ChatBird/CodeBird → Piper/Spark TTS`

Requirements:

- Push-to-talk works without wake-word listening.
- Continuous listening remains opt-in.
- Wake-word activation only claims to work after a compatible detector passes a real test.
- Talkback can be disabled independently of request processing.
- Stop/cancel interrupts capture, transcription, generation and playback.
- Missing runtimes are reported accurately.
- Preserve existing SYSTEM permission boundaries.
- Minimize idle CPU, battery use and simultaneous heavy inference workers.

Do not claim Needle3 or Whistle implements the `Penguru` wake phrase without verifying the runtime and detection capability.

## P5 — Test and deploy LIVE to the S10+

Run existing Python, JavaScript, model registry, download manager, PWA wiring and workflow YAML tests.

Add tests for:

- All four mandatory model cards.
- Correct model-to-URL mapping.
- Download state transitions.
- Invalid checksums and interrupted downloads.
- Cancellation and retry.
- Voice checkbox interaction and persistence.
- Shared Beak settings synchronization.
- Apps drawer icon asset resolution.

**Do not rely exclusively on unit tests.** Use browser automation or the actual rendered UI to verify that checkboxes are clickable, buttons initiate downloads, and the app drawer displays the correct icon.

Then deploy validated userspace changes to:

`root@10.11.12.99`

Use the existing transactional installer in `./scripts`.

Verify SSH host identity, ARM64 architecture, disk space and service health before deployment.

Back up active services and Beak configuration, preserve all working models, and record the rollback receipt.

Never touch boot, recovery, modem, kernel, firmware or trust keys.

Restart only affected services and invalidate stale frontend caches.

After deployment, verify the **live running phone**, not just the source tree:

1. PenGuru Squad shows Qwen ASR, Needle3, Whistle and Spark TTS download cards.
2. Every verified-source download button initiates a real backend request.
3. Voice checkboxes are clickable and persist after reload.
4. The Nuxel apps drawer displays `nuxel-penguru-squad.png`.
5. PenGuru and HTTP bridge services are active.
6. SonarBird MiniLM still loads with ONNX Runtime.
7. ChatBird and CodeBird remain available.
8. No existing models or user settings were lost.

If a deployment test fails, investigate and repair it or roll back safely. Do not report PASS without verification.

## P6 — GitHub work, only after successful deployment

Review existing Git changes carefully. Do not stage unrelated modifications.

If feasible, create a dedicated feature branch, commit intended changes, push, open and merge a PR after checks pass, and trigger the release workflow from the correct merged commit.

Do not overwrite existing releases or tags.

## Execution priorities

This is intended for one limited coding-agent run.

**Priority order:**

1. Four mandatory download cards and correct URLs.
2. Functional backend download actions.
3. Clickable, persistent voice settings.
4. Correct PenGuru Squad icon in the Nuxel apps drawer.
5. Live deployment and verification.
6. Voice runtime integration.
7. GitHub/release work.

If time is limited, drop GitHub work and optional voice runtime integration first. Do not sacrifice the four mandatory cards, settings fixes, apps drawer icon or validated deployment.

## Final report

Provide concise PASS/FAIL/NOT VERIFIED results for:

- Qwen ASR download button.
- Needle3 download button.
- Whistle download button.
- Spark TTS download button.
- Silero VAD, RNNoise, Piper, Cactus and Qwen runtime entries.
- Voice checkbox interaction and persistence.
- Apps drawer icon.
- Live service status.
- Deployment and rollback receipt.

Include exact resolved canonical download URLs, model storage paths, changed files, and remaining blockers.

**BEGIN NOW. Inspect the actual PenGuru Squad model catalog, fix the missing four download cards, repair the unclickable controls, set the apps drawer icon to `./assets/nuxel-penguru-squad.png`, and deploy the tested changes live.**

# PENGURU SQUAD v0.9.1-beta — BEAK DOWNLOADS, VOICE UI FIXES & LIVE DEPLOYMENT

You are working in the existing Nuxel repository for the Samsung Galaxy S10+ (SM-G975F), running native Linux without Android dependencies.

**Execute this task immediately. Do not stop at planning.**

This is a focused continuation of the existing PenGuru Squad work. Preserve the working ChatBird, CodeBird, SonarBird MiniLM and ordinary ONNX Runtime 1.32.0 CPU integration.

**Primary goals:**
1. Fix every nonfunctional voice checkbox, toggle, selector and button.
2. Add real download buttons for all Beak voice models and dependencies.
3. Connect downloaded components to the existing Beak registry and runtime.
4. Install the official PenGuru Squad application icons.
5. Test and deploy validated userspace changes over Wi-Fi SSH.
6. Perform Git/release work only after the above succeeds.

## P0 — Fix all Beak settings and controls

The owner reports that **voice-control checkboxes cannot be clicked**.

Treat this as a critical bug, not a cosmetic issue.

Inspect the actual PenGuru Squad application and Settings implementation, including:

- HTML inputs, labels, IDs and event listeners.
- CSS `pointer-events`, overlays, stacking contexts and disabled states.
- JavaScript initialization errors.
- State hydration and settings persistence.
- API routes, request validation and authorization.
- Browser/PWA caching and stale JavaScript.
- Conflicts between the PenGuru Squad UI and PenGuru AI Settings.
- Mobile touch events and accessibility behavior.

Repair the underlying cause rather than adding duplicate controls.

Every checkbox must:

- Respond to mouse, touchscreen and keyboard input.
- Visibly change state.
- Call the correct backend API.
- Persist the setting.
- Restore the saved value after page reload.
- Stay synchronized between both interfaces.
- Display a useful error if saving fails.
- Revert optimistic UI changes when persistence fails.

Verify at least these settings:

- Push-to-talk enabled.
- Continuous listening enabled/disabled.
- Wake-word listening enabled/disabled.
- Wake phrase: `Penguru`.
- Talkback enabled/disabled, default enabled.
- ASR engine selection.
- TTS engine selection.
- Silero VAD enabled/disabled.
- RNNoise enabled/disabled.
- Speech interruption/barge-in enabled/disabled.
- Microphone selection and permission state, where supported.

**Continuous listening must remain explicitly opt-in**, with a visible recording indicator and an immediate Stop control. Do not silently activate the microphone merely because talkback defaults to enabled.

If a component is unavailable, its settings must still be understandable and interactive where appropriate, but the UI must clearly explain why activation cannot succeed.

## P1 — Real Beak model download buttons

Add a dedicated **Beak → Voice Models & Components** section inside the PenGuru Squad application.

Also expose the same components in PenGuru AI → Settings → Beak.

Both interfaces must share one backend model registry, downloader, configuration source and status API.

### Required downloadable components

| Component | Required artifact | Function |
|---|---|---|
| Qwen ASR | `qwen3-asr-0.6b-q4_k_m.gguf` | Offline speech recognition |
| Needle3 | `needle3.cact` | Cactus-compatible voice component |
| Whistle | `whistle.cact` | Cactus-compatible voice component |
| Spark TTS | `spark-tts-tunartts-v1.Q4_K_M.gguf` | Optional speech output |
| Piper TTS | ARM64 runtime + compatible ONNX voice and JSON | Default speech output |
| Silero VAD | Compatible ONNX model | Voice activity detection |
| RNNoise | Native ARM64 runtime/library | Noise suppression |
| Cactus | Compatible ARM64 runtime | `.cact` execution |
| Qwen ASR runtime | Compatible ARM64 decoder | GGUF ASR execution |

### Download source requirements

**Qwen ASR — use this exact official download endpoint:**

https://huggingface.co/OpenVoiceOS/qwen3-asr-0.6b-q4-k-m/resolve/main/qwen3-asr-0.6b-q4_k_m.gguf?download=true

**Needle3:** The owner supplied a signed Hugging Face Xet URL identifying `needle3.cact`.

**Whistle:** The owner supplied a signed Hugging Face Xet URL identifying `whistle.cact`.

**Spark TTS:** The owner supplied a signed Hugging Face Xet URL identifying `spark-tts-tunartts-v1.Q4_K_M.gguf`.

For these three, locate and verify the canonical Hugging Face repository, revision and filename. Replace the temporary Xet links with permanent `/resolve/<revision>/<filename>` URLs.

Do not guess repository names or fabricate download endpoints. If the canonical source cannot be verified, show `SOURCE UNVERIFIED` and do not enable automatic installation.

For Piper, Silero, RNNoise, Cactus and the Qwen decoder, locate official compatible release artifacts or build sources, check licensing, and record exact versions.

**All nine components must appear in the UI**, even when a source or runtime is unavailable.

### Each component card must provide

- Download button linked to its verified source.
- Download progress, transferred bytes and total size when available.
- Pause/resume where supported.
- Cancel and retry.
- SHA-256 integrity verification.
- Install/activate button.
- Runtime compatibility status.
- Test component button.
- Remove/uninstall button.
- Clear error and recovery messages.

Use a backend-managed download operation, not merely `window.open()`.

The backend must stream to temporary storage, check disk space, validate source and checksum, and atomically promote verified files.

Persist download state and avoid duplicate simultaneous downloads.

Never mark a model READY just because the file exists.

## P2 — Connect Beak to actual voice processing

Implement and validate:

`Microphone → optional RNNoise → Silero VAD → Qwen ASR → SonarBird → ChatBird/CodeBird → optional Piper/Spark TTS`

Push-to-talk must work without continuous listening.

Wake-word mode must only claim to recognize `Penguru` after an actual compatible wake detector passes tests. Do not assume Needle3 or Whistle supports that phrase.

Talkback defaults to enabled but must be independently switchable off. Turning talkback off must never stop text processing.

Stop/cancel must terminate recording, transcription, inference and audio playback promptly.

Maintain the existing SYSTEM permission boundary and prevent automatic execution of generated commands.

When a runtime is missing, display `RUNTIME MISSING` rather than silently falling back to a fake success.

## P3 — Official PenGuru Squad icons

Use the existing file:

`./assets/nuxel-penguru-squad.png`

as the **canonical PenGuru Squad application icon**.

Update the relevant:

- Application launcher and menu entries.
- Desktop `.desktop` file.
- Window/task-switcher icon where supported.
- PWA manifest icons (192×192 and 512×512).
- Browser favicon and touch icon.
- PenGuru Squad application header.
- Installer asset paths.

Generate necessary sizes without distortion and preserve transparency.

Do not replace unrelated Nuxel branding.

Verify that icon files are installed to permanent paths and remain correct after reboot.

## P4 — Tests and live Wi-Fi SSH deployment

Run all relevant tests, including:

- Python compilation and PenGuru unit tests.
- JavaScript syntax checks.
- PWA wiring verification.
- Download-manager state tests.
- Checkbox interaction and persistence tests.
- Settings synchronization tests.
- API permission and error-path tests.
- Icon and desktop-entry validation.
- Release workflow YAML validation.

**Browser interaction tests are essential:** automated source checks alone cannot establish that a checkbox is actually clickable. Test the real rendered interface using mouse/touch or browser automation if available.

After host tests pass, deploy userspace changes to:

`root@10.11.12.99`

Use the existing transactional deployment scripts in `./scripts`.

Before deployment, verify the SSH host key, target architecture and free disk space. Back up the active services and Beak configuration, preserve existing ChatBird/CodeBird/SonarBird models, and record the rollback receipt.

Deploy only validated userspace components. Do not modify boot, recovery, modem, kernel, firmware or trust keys.

Restart only affected services and verify:

1. `nuxel-penguru` and `nuxel-http-bridge` are active.
2. SonarBird still loads with ONNX Runtime CPU.
3. ChatBird and CodeBird remain available.
4. Every voice checkbox can be clicked and persists.
5. Every model download button calls the correct backend endpoint.
6. A small model download completes, verifies and installs.
7. Push-to-talk and talkback are tested where dependencies permit.
8. The new Squad application icon appears correctly.

If a deployment test fails, use the transactional rollback procedure.

## P5 — GitHub actions (lowest priority)

Only after the implementation and deployment are stable:

- Review `git status` and isolate unrelated pre-existing changes.
- Create a dedicated feature branch.
- Stage and commit only intended changes.
- Push the feature branch.
- Create a PR and merge after checks pass.
- Reconcile repository version metadata to `v0.9.1-beta`.
- Update CHANGELOG and implementation documentation.
- Create the release tag from the exact merged commit.
- Trigger the GitHub release workflow.
- Do not monitor the workflow after successful triggering.

Never force-push or discard unrelated work.

## Execution budget

This task is intended for **one GPT-5.6 Terra Medium run**.

Priority order:

**P0 clickable settings → P1 real downloads → P2 voice runtime integration → P3 icons → P4 live deployment → P5 GitHub.**

Avoid unrelated refactoring and lengthy commentary. Implement and test continuously.

If time runs short, drop GitHub actions first. Preserve a tested, deployable source state and concise manual deployment instructions if live deployment cannot be completed.

## Final report

Return a compact table for all nine Beak components showing:

`SOURCE VERIFIED | DOWNLOADED | INSTALLED | RUNTIME READY | LIVE TEST`

Also report checkbox interaction results, deployed service status, icon installation, rollback receipt, changed files, and remaining blockers.

**Start by reproducing the unclickable voice settings bug. Fix it, then implement the actual download controls and deploy the tested changes. Do not stop at a plan.**

# ONE-SHOT GPT-5.6 Terra (Medium): PenGuru v0.9.1-beta

## Delivery assembly (first, zero interpretation)

The source is a **complete 454 MiB ZIP** split into five numbered download parts ONLY because the chat file-export limit rejects a single 454 MiB attachment. **This is not a partial patch kit.** Download all five `NUXEL_v091_FULL.part01` … `part05` files into one directory and reconstruct EXACTLY in numerical order. On macOS/Linux:

```bash
cat NUXEL_v091_FULL.part01 NUXEL_v091_FULL.part02 NUXEL_v091_FULL.part03 NUXEL_v091_FULL.part04 NUXEL_v091_FULL.part05 > NUXEL_v0.9.1-beta_FULL_DROPIN.zip
shasum -a 256 NUXEL_v0.9.1-beta_FULL_DROPIN.zip
# EXPECT: f3ebbd4d2b51b46d1ac4a6f6aee53116a79d412d3e9867b42812b9d52a683da6
unzip -q NUXEL_v0.9.1-beta_FULL_DROPIN.zip
cd nuxel-main
```

If the SHA-256 does not match **stop**, re-download the affected part, and do not deploy. Do not commit the assembled ZIP or the parts. The reconstructed archive contains 21,857 entries, 47 preserved symlinks, all original repo files and the patched source, Beak config, root `flash.md`, status report, tests and workflow. If already supplied with the complete reconstructed ZIP or extracted repository, skip assembly.


**Mission:** Finish the most important PenGuru/Beak integration gaps in THIS supplied full Nuxel repository; run tests; deploy the resulting **userspace** update to the existing Galaxy S10+ over verified Wi-Fi SSH; ONLY THEN attempt feature branch/PR/release trigger if time allows. **No unnecessary explanations, wholesale refactors, or repeat research.** Use commands, edit source and show evidence. Do as much as possible in one run. Priorities: **P0 source correctness > P1 physical SSH deployment > P2 Git and release.** If you must drop work: drop P2 first, then P1. Preserve a tested P0 and repo-root `flash.md`.

## Starting facts and paths

- Repository root contains `flash.md`, `beak.json`, `PENGURU_V091_PATCH_STATUS.md`, `VERSION` (`v0.9.1-beta`), and this prompt; also consult `penguru-squad/` specs only where implementing a specific missing piece. This is a fully patched **source** archive, not a flashed image.
- S10+ Exynos9820 ARM64 Linux, host: `root@10.11.12.99`, SSH key: `$HOME/.ssh/wicked_wqn_id_rsa`; do NOT disable StrictHostKeyChecking or replace SSH credentials. `./scripts/nuxel-deploy-live.py` exists; inspect its applicability. For PenGuru/Settings use `services/nuxel-penguru/tools/install-device.py` transactional installer and `rollback-device.py` as described in `flash.md`. **No boot/recovery/modem/kernel partition flashing** in this mission.
- Owner has demonstrated ChatBird + CodeBird generation; protect the working GGUF files, keys, workers, memory management, and existing live preferences. Screenshot error `backend_unavailable ... 'onnxruntime-genai'`: GGUF ChatBird/CodeBird need **Auto/llama.cpp**; MiniLM SonarBird uses separate ordinary ONNX Runtime. Do not install GenAI as a GGUF workaround.
- Owner's actual `beak.json` defaults: `asr_backend=qwen`, `vad_enabled=true`, `interrupt_on_speech=true`, `noise_suppression=rnnoise`, `talkback_enabled=true`, `tts_backend=piper`, `config_owner=penguru-beak`. Already incorporated. Extra safety defaults: push-to-talk ON, continuous microphone capture OFF until user opts in, visible mic indicator and Stop. Both apps use `/var/lib/nuxel-penguru/beak.json`. Talkback preference ON does not imply Piper is provisioned.
- Source patch currently includes 4 HTTPS **staging** download buttons (Qwen ASR GGUF, Needle3 `.cact`, Whistle `.cact`, Spark TTS GGUF), shared Beak settings in Squad+Nuxel Settings, a bounded foreground microphone UI, a Qwen ASR CLI adapter, conditional Piper adapter, ONNX runtime selection fixes, and host regression tests. **Do not misrepresent staged weights as installed signed models.** The temporary browser-provided Xet URLs expire; use pinned Hugging Face `resolve/<revision>/filename` URLs from `beak/catalog.py`.

## P0 — Verify and finish SOURCE first (mandatory)

1. `git status --short; cat VERSION; cat PENGURU_V091_PATCH_STATUS.md`; inspect only relevant files: `services/nuxel-penguru/{service.py,beak/,voice/,sonarbird/,scheduler/,model_store/,tests/,tools/install-device.py}`, `services/nuxel-bridge/src/penguru_api.py`, `pwa/nuxel-apps/{penguru/,settings/penguru*.js}`, `.github/workflows/release.yml`, and root `flash.md`. Preserve unrelated changes; do not rewrite historical hardware reports.
2. **Backend/routing:** verify Auto and per-model inherit select llama.cpp for GGUF, stale ONNX GenAI preference migrates correctly, ChatBird/CodeBird generation remains intact, failure reports are actionable, no silent execute. SonarBird must load signed and self-tested `all-MiniLM-L6-v2` (ONNX encoder, exact WordPiece, attention-mask mean pooling, 384-dimensional L2 embeddings, trained classification head) via regular `onnxruntime` CPU on device. If no signed package/runtime exists, report NOT READY with Tier-0/ASK fallback, NOT fictitious MiniLM inference. Zero unauthorized SYSTEM dispatch, explicit owner override CHAT/CODE/ASK only.
3. **Beak:** all UI settings and download/cancel/progress/diagnostic controls functional. Both UIs share the live Beak API/config and persist changes. Qwen ASR file -> real compatible ARM64 ASR executable; test with WAV, not llama.cpp text inference. Staged Cactus `.cact` files require compatible Linux ARM64 runtime. Spark GGUF requires working audio tokenizer/codec and decoder. Piper requires executable, voice `.onnx` + `.onnx.json` and audio playback. For each missing native dependency, implement only if supported by real ABI and tests; otherwise surface honest install instructions and remain functional without it. No Android dependencies.
4. **Voice:** make push-to-talk acquire permission and 16k PCM WAV, VAD/silence gate, transcribe locally when decoder available, put transcript in input for **review before Send**; never grant SYSTEM actions via audio. Optional *foreground-only* “Penguru” listening must be opt-in, visibly indicate recording, stop on Stop/disable/hide/lock/permission revoke, cancel pending results, and never turn on at boot. A full Qwen ASR pass every 5 seconds is not a low-power wake engine; measure and replace only if a verified lightweight wake model is available. `vad_enabled`/`noise_suppression=rnnoise` config fields are not proof of installed Silero VAD/native RNNoise. Talkback enabled by default must speak only if Piper is actually installed and validated, otherwise text works with a clear warning; turning it OFF stops subsequent speech while retaining processing.
5. Run: `python3 -m compileall -q services/nuxel-penguru`; `for t in services/nuxel-penguru/tests/test_*.py; do python3 "$t" || exit 1; done`; `node --check` for modified JS; `node pwa/nuxel-common/verify-wiring.js`; check Python YAML parsing of release workflow. Fix regressions. Update root `PENGURU_V091_PATCH_STATUS.md` with test outputs, exact remaining phone-native dependencies, and no unsupported claims.

## P1 — Wi-Fi SSH userspace deployment (preferably complete)

6. **Read root `flash.md`** and installer before running. Identify device and SSH host key against owner's known_hosts; if mismatch or uncertain STOP. Preflight: `ssh -i "$HOME/.ssh/wicked_wqn_id_rsa" -o StrictHostKeyChecking=yes root@10.11.12.99 'uname -m; cat /etc/os-release | head -5; df -h /var; systemctl is-active nuxel-penguru nuxel-http-bridge || true'`. Require aarch64, enough disk, working SSH, no active model generation/download, current service snapshots and backed-up `/var/lib/nuxel-penguru/beak.json` and rollback strategy. Preserve existing installed GGUF files and trust material.
7. From checkout root, stage only the userspace tree **exactly as root `flash.md` documents**. Reference command:

```bash
KEY="$HOME/.ssh/wicked_wqn_id_rsa"; HOST=root@10.11.12.99
tar -czf /tmp/nuxel-penguru-v091-userspace.tgz services/nuxel-penguru services/nuxel-bridge/src/penguru_api.py pwa/nuxel-apps/penguru pwa/nuxel-apps/settings/index.html pwa/nuxel-apps/settings/penguru-settings.js pwa/nuxel-apps/settings/penguru-models.js pwa/nuxel-apps/settings/penguru-beak.js pwa/nuxel-common/app-registry.json assets/nuxel-penguru-squad.png
shasum -a 256 /tmp/nuxel-penguru-v091-userspace.tgz
scp -i "$KEY" -o StrictHostKeyChecking=yes /tmp/nuxel-penguru-v091-userspace.tgz "$HOST:/tmp/"
ssh -i "$KEY" -o StrictHostKeyChecking=yes "$HOST" 'set -eu; mkdir -p /tmp/nuxel-penguru-v091; cd /tmp/nuxel-penguru-v091; tar -xzf /tmp/nuxel-penguru-v091-userspace.tgz; python3 -m compileall -q services/nuxel-penguru; systemctl stop nuxel-penguru-download nuxel-penguru || true; python3 services/nuxel-penguru/tools/install-device.py --source-root /tmp/nuxel-penguru-v091; systemctl start nuxel-penguru; systemctl is-active nuxel-penguru'
```

8. Capture the installer's rollback receipt and `systemctl`/journal evidence. Verify actual ChatBird and CodeBird generation, Auto routing, signed SonarBird if installed, Beak settings from both UIs, model staging, permission and stop behavior, real audio capture/transcription/talkback where runtime exists. On failure use `rollback-device.py` per `flash.md`; do not reboot/flash recovery to hide an error. Record PASS / FAIL / NOT VERIFIED; phone measurements only, no guessed thermal, latency or battery numbers. If SSH/preflight blocked: preserve source, document exact next commands, and stop P1 safely.

## P2 — Git and GitHub (only after P0+P1)

9. `VERSION` must be `v0.9.1-beta`; keep docs/CHANGELOG/README consistent; release workflow must build merged `main` SHA rather than historical assets, and must **retain fail-closed installed-image provenance checks**. No model weights, secrets, caches or ZIPs committed. Create `feat/penguru-beak-v0.9.1-beta` from the correct base, stage reviewed files, commit, push, open PR via `gh pr create`, merge **after required checks/approval**. Let `push main` trigger `.github/workflows/release.yml`; if needed invoke `gh workflow run release.yml --ref main` with appropriate inputs. **Trigger only: do not monitor the build, and do not claim release passed.** Let the workflow create the tag/release after its gates, rather than pretagging a broken build. Show actual branch, PR URL, merged SHA and trigger ID if available.
10. **If constrained, skip P2 entirely; do not waste time on workflows instead of working voice/routing or phone deployment.** If P1 cannot finish, leave a working host patch and root `flash.md`. No invented successful flash, tag or release.

## Final agent output (short)

Report `P0 source tests`, `P1 device install + rollback receipt`, `ChatBird / CodeBird / MiniLM / ASR / VAD / RNNoise / wake word / talkback` as PASS/FAIL/NOT VERIFIED, `P2 Git/PR/workflow trigger or SKIPPED`, exact remaining blockers and files changed. Prefer stable usable PenGuru over unverified optional model integrations. **Do not monitor release.**
