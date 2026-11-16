# PenGuru Kickstart — Full Implementation Mission for the Nuxel Agent

**Mission type:** repository-grounded, end-to-end implementation  
**Source specification:** `PenGuru_Squad_Dual_Runtime_Implementation_Guide_v1_1.md`  
**Product:** PenGuru Squad / NuXAI for native Nuxel  
**Priority:** deliver a real, integrated, testable product — not a mock-up, scaffold, demo, or collection of disconnected components.

---

## 0. Your assignment

You are the implementation agent responsible for turning the supplied PenGuru Dual-Runtime Implementation Guide into a complete, working PenGuru application and its required native Nuxel services.

Work directly in the existing Nuxel repository. First inspect the actual checkout, current branch, build system, device/kernel targets, app registry, bridge, permission authority, service conventions, UI conventions, tests and existing work. The guide contains a prior repository audit; treat it as important evidence, but verify every relevant finding against the current checkout before changing anything. Do not assume the repository is unchanged.

**Do not stop at planning, architecture documents, scaffolding, placeholder APIs, mocked inference, static UI, or a successful compile.** Implement, integrate, run tests, fix failures, and repeat. Continue through the acceptance gates in this prompt until every feasible required feature is implemented and verified on the actual supported target environment.

A task is not complete merely because:
- a file or service exists;
- a button is visible;
- a D-Bus method returns success without doing the real work;
- a model download completes without integrity and load verification;
- a runtime compiles but cannot load the exact model;
- a voice indicator animates without real microphone capture;
- a wake-word detector fires in a synthetic test only;
- a test is skipped, mocked, xfailed, or weakened;
- a feature is described as supported when it has not been tested on the relevant device.

Never fake test results, device support, model compatibility, permissions, hardware acceleration, wake-word recognition, or completion. If a dependency, hardware capability, model artifact, license decision, permission fix, or target device is genuinely unavailable, implement the strongest safe fallback, record the exact blocker and evidence, and keep all dependent functionality visibly unavailable rather than pretending it works. Continue implementing independent work.

### Definition of done

PenGuru is done only when:
1. The application is registered, packaged, launched and integrated through Nuxel's real app/service lifecycle.
2. Its three assistant modes work as specified.
3. The model store, signed manifests, downloads, integrity checks and model lifecycle work end-to-end.
4. The runtime abstraction and each claimed runtime/model combination work with real artifacts.
5. SonarBird routing works and cannot authorize actions.
6. The Supervisor, permission broker, approvals, audit and rollback paths enforce the actual Nuxel security model.
7. The opt-in voice/wake-word feature works with the real microphone and local speech stack, with the privacy controls below.
8. OFF really means OFF: no PenGuru daemons, wake-word capture, classifier or model workers remain running, and their memory/resources are released.
9. Automated tests, integration tests, adversarial tests and on-device acceptance tests pass.
10. Documentation, configuration, packaging, release evidence and known limitations match the tested implementation.

Maintain a living implementation checklist and evidence log in the repository. Mark an item complete only with a command, test output, trace, or reproducible manual verification that proves it.

---

## 1. Non-negotiable product principles

The product promise is:

> PenGuru may suggest anything, may prepare what it can verify, and may change only what its owner authorizes.

- Native Nuxel integration. Do not turn PenGuru into an Android app, Termux/proot product, generic web chatbot, or standalone model server.
- Local-first and offline after model installation. No cloud fallback, prompt telemetry, remote inference, or hidden network use.
- Feature disabled by default.
- Explicit owner control over enablement, mode, runtime, model packages, voice and wake-word operation.
- One heavyweight generative worker resident at a time by default.
- CPU inference is the baseline. GPU/NPU are optional only after exact target validation.
- Model output is untrusted data, never authority.
- No model gets root, broker credentials, arbitrary shell access, permission-grant authority, or approval authority.
- No action is executed because a classifier, model, wake word, speaker match, transcript or confidence score says it is safe.
- Preserve Nuxel's existing design language, app registration, shared bridge, permission portal, session services, notification system, build pipeline and conventions. Reuse canonical infrastructure; do not create parallel permission systems or duplicate bridge clients.

---

## 2. Start with a repository and target audit

Before implementation:

1. Record repository path, branch, commit, working-tree state and available build/test commands.
2. Inspect the complete relevant source areas, including at minimum:
   - `services/nuxel-bridge/`
   - `services/nuxel-portal/`
   - `shell/nuxel-shell/nuxel-permissions/`
   - `pwa/nuxel-common/bridge.js`
   - `pwa/nuxel-common/bridge-version.json`
   - `pwa/nuxel-common/app-registry.json`
   - `pwa/nuxel-apps/penguinterface/`
   - `services/nuxel-session/`
   - `services/nuxel-notifications/`
   - `Makefile`, build scripts and CI validation
   - existing audio, microphone, speech, power-management, D-Bus and systemd code.
3. Find all existing PenGuru/NuXAI/ChatBird/CodeBird/SonarBird work, including partially implemented or untracked components. Reuse sound work; do not overwrite it blindly.
4. Reproduce relevant baseline tests and record results before changes.
5. Identify the actual first target image, device SKU, kernel, systemd version, audio capture stack, available microphone devices and permissions. Do not infer support from a desktop development machine.
6. Produce a concise audit report listing observed facts, defects, files to modify, integration points and implementation order.

The prior guide identified critical security issues. Verify and fix these against current code:

### P0 — bridge identity and development-mode bypass
- Production images must not enable development loopback authentication bypass.
- Bind every token/session to a trusted launcher-authenticated application identity.
- Enforce token identity equals authenticated caller identity on every method.
- Derive caller identity from trusted launcher/session or authenticated D-Bus peer credentials, never JSON body fields, Origin or Referer.
- Do not make generic HTTP `/rpc` or owner-only service-control helpers the PenGuru privilege boundary.
- Add regression tests for forged app IDs, replay across apps, identity mutation, missing launcher secret, untrusted loopback and unauthorized service control.

### P1 — once/session grant semantics
- A `once` grant must be consumed by exactly one immutable action/request at the permission authority; it must not be reusable from an in-memory cache.
- A `session` grant must be bound to a real session ID, expiry and revocation lifecycle.
- Use monotonic time for in-process expiry.
- Add a bridge-level regression proving the first one-shot action succeeds and the second fails during the same daemon lifetime.

### P1 — canonical capability registry
- Use the canonical `nuxel-permd` registry.
- Do not create another independent capability definition.
- Generate or validate PenGuru mappings against the canonical registry.
- Unknown capability names must be denied.

### P1 — truthful sandbox reporting
- Probe the actual running kernel and systemd capabilities.
- Do not claim Landlock, AppArmor, SELinux, namespaces, BPF device filtering or any other isolation primitive unless it is actually effective.
- The guide notes Linux 4.14.253 limitations. Verify the target kernel rather than assuming modern features.
- If effective isolation cannot be proven, disable generated-code execution and provide patch review/export only.

**No privileged PenGuru feature may ship until these blockers are fixed and independently regression-tested.** Chat-only and read-only work may proceed with no privileged capabilities.

---

## 3. Required product modes

Implement all three user-selectable modes:

### A. Single ChatBird
- Every user request goes directly to ChatBird.
- SonarBird is bypassed completely.
- ChatBird handles conversation, explanations, brainstorming and summarization.
- It cannot execute commands, choose permissions, change the OS or approve actions.

### B. Single CodeBird
- Every user request goes directly to CodeBird.
- SonarBird is bypassed completely.
- CodeBird handles code explanation, debugging, patch proposals, scripts, tests and extension scaffolding.
- Generated code is staged only in a scoped workspace. It cannot install or execute itself.

### C. PenGuru Squad
- Every request passes through SonarBird.
- SonarBird returns exactly one constrained route: `CHAT`, `CODE`, `SYSTEM` or `ASK`.
- `CHAT` loads ChatBird; `CODE` loads CodeBird.
- `SYSTEM` resolves only through deterministic, allowlisted, typed Nuxel APIs and the Supervisor/broker.
- `ASK` asks the owner for clarification without loading a heavyweight model.
- Show the route, reason and confidence in the UI.
- User may temporarily override to CHAT, CODE or ASK. SYSTEM is available only through an explicit supported Nuxel action, never a free-form route override.

Single modes must not accidentally initialize SonarBird. Squad must use SonarBird or its safe deterministic fallback.

---

## 4. Independent runtime and provider selection

Do not conflate assistant mode, generative backend and hardware execution provider.

### Generative backend selector
Implement:
- `Auto`
- `llama.cpp`
- `ONNX Runtime GenAI`

Provide per-model override:
- `Inherit`
- `llama.cpp`
- `ORT GenAI`

Rules:
- GGUF goes to llama.cpp.
- ONNX GenAI packages go to ONNX Runtime GenAI.
- Standard ONNX Runtime is used for SonarBird embeddings/classification; it is not the LLM generation backend.
- GGUF does not become ONNX merely because ORT is installed.
- ONNX packages must be separately exported from the original Transformers checkpoints and separately manifested, hashed, licensed and validated.
- Explicit runtime selection is a hard constraint. If unavailable/incompatible, show a clear error and do not silently switch.
- Auto may select only a verified, installed, compatible package according to explicit preference and signed metadata.
- No cross-runtime fallback after generation starts. A failed load may offer a user-approved alternative before retry.
- UI must display the actual engine, model revision, package variant and provider used for every request.

### Runtime adapters
Create a stable, versioned `InferenceRuntime` contract with equivalents of:
- `probe(device_profile, runtime_profile)`
- `load(model_package, runtime_profile)`
- `generate(validated_prompt, generation_options)` as a cancellable event stream
- `cancel(request_id)`
- `health()`
- `unload(reason)`
- `info()`

Expose common events: loading, loaded, token, progress, cancelled, out-of-memory, error and unloaded.

### llama.cpp
- Pin an immutable upstream commit/tag and reproducible ARM64 build.
- Use the supplied GGUF artifacts as direct llama.cpp inputs, subject to current verification.
- Test exact model architecture, tokenizer, chat template, BOS/EOS, stop sequences and generation settings.
- CodeBird requires a build that actually supports its Qwen3.5/Gated DeltaNet architecture; prove it with the exact model.
- Prefer an in-process adapter or tightly sandboxed unprivileged worker over a general REST server.
- No production TCP listener is required. If a development server is used, bind privately, disable tools and prevent LAN exposure.
- Support bounded threads, context, batch, KV cache, affinity and cancellation.
- Verify memory release on unload.

### ONNX Runtime GenAI
- Pin ONNX Runtime core and GenAI as a tested compatibility set.
- Build ONNX packages from the exact original Transformers checkpoints, not GGUF files.
- Include graph(s), external tensor shards, `genai_config.json`, tokenizer assets, tokenizer configuration, generation configuration and metadata.
- Verify template/tokenizer parity and output behavior.
- Keep CPU execution available.
- Add XNNPACK/ACL/Arm NN or other providers only if compiled into the shipped build and proven on the exact target.
- Treat GenAI API/version maturity as an adapter concern; pin ABI and test it.

### Hardware providers
- CPU is mandatory baseline.
- GPU/Vulkan and NPU are not assumed available merely because graphics or neural hardware exists.
- Probe, run real model tests, record operator fallback, performance, energy and thermals.
- UI must label providers as supported, experimental or unavailable based on exact device profiles.

---

## 5. Model library and artifact integrity

There are exactly three logical model cards:

1. **ChatBird** — conversation model.
2. **CodeBird** — coding/extension model.
3. **SonarBird** — lightweight routing encoder + classifier.

Cards may expose multiple verified package variants. Do not create confusing duplicate logical model identities for GGUF and ONNX variants.

### Model source candidates from the guide
Verify these repositories, exact revisions, current files, model architecture and licenses before use:

- ChatBird GGUF: `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated_GGUF`
- ChatBird Transformers source candidate: `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated`
- CodeBird GGUF: `empero-ai/Qwen3.8-4B-Distill-GGUF`
- CodeBird Transformers source candidate: `empero-ai/Qwen3.8-4B-Distill`
- SonarBird: choose and document a complete, compatible encoder + tokenizer + pooling/normalization + classifier package. The guide does not approve an exact repository/hash; do not invent one.

The guide records a material ChatBird provenance/license inconsistency across GGUF, fine-tune and base model metadata. Do not redistribute until the complete license chain and redistribution rights are reviewed. Display an honest pending/legal-review state where necessary.

Do not claim CodeBird is a proven coding benchmark winner. Benchmark it on actual Nuxel tasks.

### Download flow
Implement the complete state machine:

`NOT_INSTALLED -> USER_CONFIRMED -> CHECK_SPACE -> DOWNLOADING -> VERIFY_SIGNATURE -> VERIFY_HASHES -> VERIFY_FORMAT -> VERIFY_LICENSE_ACK -> ATOMIC_INSTALL -> SELF_TEST -> READY`

Any failure must quarantine or clean partial artifacts and enter an explicit error state.

Requirements:
- Foreground owner action starts downloads.
- Show repository, immutable revision, exact files/sizes, format, backend compatibility, device requirements and license notice before download.
- HTTPS, resumable downloads where supported, progress, cancellation, retry/backoff and clear errors.
- Check storage for partial files, external tensors, staging/extraction overhead and safety reserve.
- Verify a trusted Nuxel-signed manifest; a hash served by the same untrusted model host is not a trust anchor.
- Verify SHA-256 for every file, signature, metadata, architecture, tokenizer/config completeness and expected sizes.
- Install atomically into an immutable revision/variant path.
- Keep last-known-good packages during updates.
- Owner can delete packages; partial/corrupt files are cleaned safely.
- License notices and accepted revisions remain visible.
- Never invent a commit, file size, hash, signature or license.

A package is READY only after its real runtime load/self-test passes on a compatible profile.

---

## 6. SonarBird routing

SonarBird is a small classifier/router, not a generative answer model and not a wake-word detector.

Implement:
1. Tier 0 deterministic rules for high-precision patterns.
2. Tier 1 sentence embeddings using standard ONNX Runtime and a Nuxel-trained classifier.
3. Calibrated route policy with explicit ASK/abstention.

Initial labels:
- `CHAT`
- `CODE`
- `SYSTEM`
- `ASK`

Safety:
- SonarBird never executes tools or grants permissions.
- No `requires_approval` output from SonarBird.
- SYSTEM requires a known typed API, deterministic action parsing and allowlist.
- Mixed code + device-action requests must be split into explicit owner-approved subrequests or sent to ASK.
- Uncertain, high-entropy or disagreeing results go to ASK.
- Route override is owner-only.
- A wrong CHAT/CODE route is a UX defect; a false SYSTEM dispatch is a security failure.
- Target zero false SYSTEM dispatches in a frozen adversarial security test set.

Build versioned training data with paraphrases, typos, expected languages, mixed intents, adversarial content and quoted commands. Split by intent family/source to prevent near-duplicate leakage. Measure macro-F1, per-class precision/recall, calibration error, confusion matrix, ASK rate and SYSTEM false-positive rate. Do not train from private prompts/logs without separate opt-in.

The guide suggests conservative initial CHAT/CODE confidence thresholds around 0.82 after calibration. Treat these as experimental starting points, not guarantees.

---

## 7. NuXAI service, scheduler and UI integration

Implement the service architecture described in the guide, adapting names/languages to repository conventions:

- `services/nuxel-penguru/` for the unprivileged control plane, Supervisor and runtime adapters.
- `pwa/nuxel-apps/penguru/` for the native Nuxel app surface.
- Existing shared PWA bridge and app registry for registration.
- Existing session, notification and canonical permission services.
- Persistent queue and state under `/var/lib/nuxel-penguru/` with safe ownership and permissions.

Proposed D-Bus identity: `org.nuxel.PenGuru` or versioned equivalent. Use authenticated D-Bus peer credentials and trusted launcher/session identity. UI must not receive broker secrets. Workers receive only the minimum model/prompt/workspace data needed for a job.

### Process/lifecycle policy
- `nuxel-penguru` control plane runs only while the feature is enabled and policy/session requires it.
- SonarBird loads only in Squad mode.
- One heavyweight ChatBird/CodeBird worker by default.
- Downloader is short-lived and gets network only for an owner-started download.
- Inference workers have no general network and no broker credentials.
- Supervisor/test runner is separate, scoped and bounded.

Implement the state machine:
`DISABLED -> IDLE -> ROUTING/LOADING -> ACTIVE -> DRAINING/CANCELLING -> UNLOADING -> IDLE`, with explicit `WAITING_USER` and `ERROR` states.

On disable:
- Reject new requests.
- Cancel/finish bounded work safely.
- Stop wake-word and speech capture immediately.
- Unload SonarBird and the generative worker.
- Stop PenGuru-specific daemons where possible.
- Close audio devices/streams and release memory.
- Clear ephemeral audio buffers.
- Report the final OFF state only after processes/resources are actually stopped.
- Do not silently restart because of a boot service, app relaunch or stale queue.

### Resource scheduler
- One heavy worker resident by default.
- Calculate usable memory after OS/compositor, foreground app, services, SonarBird and safety reserve.
- Model file size is not runtime RAM.
- Include weights/tensors, runtime buffers, KV cache, tokenizer/prompt/logits and provider allocations.
- Use measured RSS/PSS, conservative context defaults (e.g. 4K initially), bounded threads/batch and target-specific profiles.
- Respect battery saver, thermal state and memory pressure.
- Cancel/unload cleanly on pressure.
- Expose cold/warm load, TTFT, prompt/decode tokens/s, peak memory and provider fallback.

### PenGuru Control Center
Implement real working screens for:
- Overview: enabled state, mode, runtime, active model/provider, queue, offline status and device health.
- Model Library: exactly three logical model cards, package variants, provenance, hash, license, size, storage, download/delete.
- Runtime: backend toggles, versions, CPU/provider profile, threads, context and diagnostics.
- Squad routing: route, reason, confidence, ASK and temporary override.
- Approvals: exact proposal/diff, affected settings/files, capabilities, tests, risk, expiry and rollback.
- Privacy: local retention, clear conversation, delete model, network status, voice/wake-word state.
- Diagnostics: benchmark, memory/thermal state and redacted logs.

All controls must invoke real backend methods and reflect actual state; no decorative/inert toggles.

---

## 8. Supervisor, typed actions and permissions

Keep all model output and external content untrusted, including repository files, web pages, logs, model cards, notifications and transcripts.

### Action protocol
A model may propose a typed action object only. It must never return an executable shell string as an action.

The Supervisor must:
1. Validate a strict versioned schema.
2. Resolve operation against a compiled allowlist and canonical capability registry.
3. Deny unknown operations/capabilities.
4. Create an immutable preview with canonical payload, affected resources, capability, risk, tests and rollback plan.
5. Bind approval to a cryptographic hash of exact payload, target, capability, owner/session and expiry.
6. Re-check identity, session, action hash, current policy, grant, expiry and target immediately before execution.
7. Invalidate approval on any payload change.
8. Record result and rollback reference.

Risk tiers:
- Read-only: authenticated typed API, scoped and audited.
- Reversible: preview and explicit confirmation unless narrowly allowed by owner policy.
- Persistent write: staged test, exact diff, portal approval, audit and verified rollback.
- Destructive/boot-critical: unsupported in v1. Reject formatting, partition flashing, boot-chain/kernel/driver modification, root password and sudoers changes.

### Code/extension workflow
- CodeBird writes only to a disposable, scoped workspace.
- Fixed command catalogue; no arbitrary model-supplied shell.
- Separate runner process/service, dedicated UID, resource limits, no network by default and only isolation features proven on the actual kernel.
- Block symlink/path traversal outside workspace.
- Bound CPU, memory, process/file count, output and wall time.
- If isolation cannot be proven, do not execute generated code; provide patch/export for trusted review.
- Install only after owner sees diff, manifest, permissions, tests, risk and rollback.
- Promise rollback only where transaction/snapshot restore is actually tested.

---

## 9. Voice and the “Penguru” wake phrase — explicit additional requirement

The original guide deferred always-on wake-word detection for the first release. **The owner has now explicitly requested this feature as part of this implementation.** Implement it as a separate, opt-in voice subsystem. Do not quietly reinterpret the original deferral as permission to leave voice out. Preserve the guide's privacy principles and add the controls and tests below.

### 9.1 Two independent controls

Provide clearly separated controls:

1. **PenGuru enabled** — master feature switch. OFF stops the entire PenGuru subsystem and all its processes/resources.
2. **Wake-word listening** — optional sub-switch, OFF by default. It may be enabled only after PenGuru is enabled and microphone permission is granted.

Also provide:
- Push-to-talk/manual voice mode, which works without wake-word listening.
- A prominent microphone/listening status indicator.
- A one-action immediate stop/mute control accessible from the voice overlay and Control Center.
- Clear microphone permission and privacy explanation.
- A configurable setting for whether wake-word listening may continue with the screen locked or app backgrounded. Default conservatively; do not assume background microphone access is allowed by the platform.
- A visible status in the shell/status area whenever the microphone is actively open for wake-word detection.

If either master PenGuru is OFF or Wake-word listening is OFF, there must be no wake-word capture or background microphone stream. Do not start listening at boot by default. Persist owner preference only when explicitly enabled, and always honor OS permission/revocation and hardware privacy controls.

### 9.2 Expected user experience

The owner enables Wake-word listening and grants microphone permission. A small, local, low-power wake-word detector listens for the spoken phrase:

**“Penguru” — pronounced “peng-goo-roo”.**

When the detector recognizes the wake phrase:
1. Stop treating audio as ambient wake-word input and transition into command capture.
2. Immediately show a PenGuru voice overlay, even if the app was not already open, subject to Nuxel's allowed foreground/notification behavior.
3. Show a clear active-capture indicator and live/final local transcription.
4. Capture the words spoken after “Penguru” as the phone command. Do not send the wake phrase itself as the command text.
5. Detect end-of-speech using tested VAD/silence handling, with a visible timeout/cancel path.
6. Show the recognized command in the overlay and submit it through the same authenticated PenGuru request pipeline as typed input.
7. In Squad mode, route through SonarBird; in Single modes, go directly to the selected worker.
8. Display the route and response in the overlay and normal conversation history according to retention settings.
9. Return to wake-word detection only if the owner has left the wake-word toggle enabled and the voice session is complete.

Example:
- User says: “Penguru, what is my battery level?”
- Overlay appears and shows: “What is my battery level?”
- PenGuru routes/answers through the configured mode.
- No privileged action occurs without the normal Supervisor and approval flow.

Support natural pauses after the wake phrase. Do not require the command to be spoken in the same breath. If the user says only “Penguru” and then nothing, show a short prompt such as “I'm listening — what do you need?” and time out safely.

### 9.3 Local-only audio pipeline

Implement separate components for:
- Microphone capture service.
- Wake-word detector for the exact phrase/pronunciation.
- Voice activity detection/end-of-utterance.
- Local speech-to-text (STT).
- Overlay/UI state and transcript.
- Request handoff into PenGuru.

Wake-word detection and STT are not SonarBird and are not LLMs. Keep them separate in architecture and lifecycle.

Requirements:
- Wake-word detection runs locally on-device.
- STT runs locally on-device.
- No audio, transcript or wake-word event is sent to a cloud service.
- No ambient audio recording or persistent audio storage.
- Keep only the minimum short-lived in-memory audio needed for detection; clear it promptly after a wake event, timeout, cancellation or disable.
- Do not retain audio clips by default. Conversation text follows the separately visible retention policy.
- No network access for wake-word/STT workers.
- Use a small efficient detector; benchmark CPU, memory, false accepts, false rejects and battery drain on the actual phone.
- Make the phrase configurable only if the detector can reliably support it; “Penguru” must be the default and verified phrase.
- Handle microphone busy/unavailable, permission denied/revoked, audio route changes, suspend/resume, screen lock, service crash and low battery.
- If wake-word detection is unavailable, keep push-to-talk/manual text available and show the exact reason.

Do not use a general-purpose LLM to detect the wake phrase. Do not continuously transcribe all ambient audio. The wake-word model should only detect the phrase; full STT starts after activation.

### 9.4 Overlay behavior

Build a real native Nuxel overlay, not a browser alert or mock.

Required states:
- Disabled
- Wake-word armed/listening
- Wake phrase detected
- Capturing command
- Transcribing
- Reviewing recognized command
- Routing/processing
- Responding
- Error/permission denied
- Cancelled/timed out

Overlay contents:
- PenGuru identity/visual treatment consistent with Nuxel.
- Explicit mic state (listening vs capturing vs not using mic).
- Live transcript where feasible; otherwise clear recording/capture feedback.
- Final recognized command, editable before submission where practical.
- Submit/confirm, cancel and immediate mic-stop controls.
- Processing/routing state, response and error details.
- No misleading “listening” label when microphone capture is not active.

Do not auto-execute high-impact operations based on a transcript. For device changes, file writes, installs or other privileged actions, show the exact typed proposal and use the normal approval/permission workflow. Voice recognition is not authorization.

### 9.5 Wake-word quality and acceptance tests

Test with real microphone recordings and live speech on the target phone:
- Different speakers, distances, volume levels, accents and speaking rates.
- “Penguru” alone, “Penguru” followed by a pause, and “Penguru” followed by a command.
- Similar-sounding phrases and ordinary conversation that should not activate it.
- TV/music/background noise and quiet environments.
- False accept and false reject rates over a documented test set.
- End-of-speech timing, long pauses, interruption, cancellation and timeout.
- Microphone permission revoke while armed.
- Master OFF, wake-word OFF, OS mic privacy disabled and app/service stop.
- Screen lock/background behavior only if explicitly supported.
- Battery, CPU, memory and thermal impact over sustained realistic use.

Do not claim wake-word support is complete based only on unit tests or prerecorded fixtures. At least one real target-device live test is mandatory. Record device, kernel, audio route, detector version, test conditions and measured results.

**Privacy invariant:** the microphone may be open for local wake-word detection only when the owner explicitly enables the wake-word switch, grants permission and Nuxel policy allows it. Otherwise it must be closed. There is no hidden or implicit listening.

---

## 10. API and configuration contracts

Implement typed, versioned APIs equivalent to the guide's proposed methods:

- `GetStatus`
- `SetEnabled`
- `SetMode`
- `SetRuntimePreference`
- `SubmitRequest`
- `GetRequest`
- `CancelRequest`
- `OverrideRoute`
- `ListModels`
- `StartDownload`
- `CancelDownload`
- `DeleteModel`
- `ListApprovals`
- `DecideApproval`
- `RollbackAction`
- `GetDiagnostics`

Add appropriately scoped voice methods, such as:
- `GetVoiceStatus`
- `SetWakeWordEnabled`
- `StartPushToTalk`
- `StopVoiceCapture`
- `CancelVoiceSession`
- `SubmitVoiceTranscript` (internal authenticated handoff; not a permission bypass)

Exact names may follow repository conventions, but contracts must be typed, versioned, authenticated and tested. Resolve caller identity from trusted credentials, never client-supplied JSON identity.

Configuration should express, at minimum:
- master enabled (default false)
- mode (default Squad or documented product default)
- runtime preference (default Auto)
- per-model backend preference
- one heavy worker
- idle unload timeout
- SonarBird enabled only in Squad
- local-only worker network policy
- raw prompt routing logs disabled
- wake-word enabled false
- microphone permission/status separate from preference
- local STT/wake model package identity and version
- screen-lock/background listening preference default false

Configuration is preference, not authority. Capabilities and approvals live in the canonical permission subsystem.

---

## 11. Device support and resource discipline

Use the guide's target policy, but verify exact devices and SKUs:

- Pixel 10 Pro XL: full target candidate only after exact hardware/kernel/runtime tests.
- Galaxy S10+ Exynos: conditional CPU-first target; verify exact RAM/SKU and actual Nuxel kernel/sandbox. Do not promise 4B/5B inference until measurements pass.
- Moto G7 Power: UI and deterministic control first; do not promise the current models on 3/4 GB variants.

For every supported profile record:
- exact SKU/RAM/storage
- Nuxel image/build and kernel
- CPU topology
- systemd and audio stack
- runtime commits and provider
- model revision/variant
- memory reserve/context/thread defaults
- thermal/battery thresholds
- microphone/wake-word/STT package and measurements
- effective sandbox primitives.

CPU-first. Keep UI responsive. Benchmark cold/warm model load, TTFT, prompt/decode speed, RSS/PSS, thermal throttling, battery and audio wake-word power. Do not invent speed or battery claims.

---

## 12. Required testing and release gates

Create automated tests, integration tests and real-device evidence. Preserve existing tests and add regression coverage; do not weaken existing checks to get green.

### Gate G0 — privilege safety
- Bridge production bypass impossible.
- Authenticated app identity binding works.
- Once/session grant semantics correct.
- Canonical capabilities enforced.
- Sandbox accurately reports effective primitives.
- No privileged PenGuru operation before G0 passes.

### Gate G1 — llama.cpp
- Pinned ARM64 build.
- Exact ChatBird and CodeBird GGUF load and generate.
- Correct chat templates/tokenization.
- Cancellation and memory release.
- No production TCP listener.
- CodeBird architecture support proven.

### Gate G2 — ONNX
- Pinned ORT + ORT GenAI ARM64 compatibility set.
- Exact ONNX bundles load and generate, if published.
- SonarBird standard ONNX classifier passes accuracy tests.
- Unsupported variants remain disabled with reason.

### Gate G3 — device profile
- Exact SKU measurements: RSS/PSS, TTFT, prompt/decode speed, cold load, heat, battery, memory pressure and UI responsiveness.
- Voice capture and wake-word measurements on real hardware.

### Gate G4 — artifact provenance
- Signed immutable manifests.
- Exact revisions, hashes, file lists, tokenizer/config hashes, license notices and export provenance.
- No invented metadata.

### Gate G5 — product/security
- All modes, runtime selection, offline operation, hostile-input tests, approvals, rollback and visible routing pass.
- Voice toggles and privacy invariants pass.
- OFF releases all PenGuru processes/resources.

### Minimum test matrix
- Model signature, hashes, metadata, license, corrupt/partial download and wrong architecture.
- llama.cpp exact GGUF load, Qwen architecture, templates, cancellation, OOM and unload.
- ORT GenAI ABI, exact exports, provider compatibility, tokenizer parity, KV cache and cancellation.
- SonarBird route precision/recall/calibration, ASK and zero false SYSTEM dispatch in frozen adversarial set.
- Single modes bypass router; Squad routes all labels.
- Runtime mismatch rejected; Auto resolved visibly; no silent conversion/fallback.
- Malformed action schemas, path traversal, symlink attacks, oversized output, approval tampering/replay and denied capabilities.
- Forged app identity, token replay, expiry, one-shot reuse, session expiry, portal timeout, bridge down, unknown capability and revocation.
- Sandbox host access, network, device nodes, fork bomb, memory exhaustion, special files and out-of-workspace writes.
- Offline inference after install; no worker network/telemetry; deletion/retention/log redaction.
- Wake-word real-device tests listed in Section 9.5.
- Disable/enable cycles, suspend/resume, worker switches, memory leak and audio-device release.
- Rollback for each supported reversible action.

---

## 13. Implementation order

Work in dependency order. Do not start by polishing UI while the service/security foundations are missing.

1. **Audit and baseline:** inspect repo, establish target profile and reproduce tests.
2. **G0 security:** fix bridge identity, dev bypass, grant cache and capability drift.
3. **Contracts and core:** schemas, D-Bus service, authenticated identity, queue, state machine, model registry and scheduler.
4. **Runtime 1:** pinned llama.cpp ARM64 adapter; load and test both supplied GGUF models.
5. **SonarBird:** deterministic Tier 0, standard ORT Tier 1, dataset, calibration and ASK behavior.
6. **Model store:** signed manifests, downloader, integrity checks, atomic install, license UI and self-test.
7. **Single modes:** ChatBird and CodeBird full request lifecycle, cancellation, history and status.
8. **Squad mode:** routing, explanation, overrides and adversarial tests.
9. **ONNX GenAI:** export and validate CodeBird first, then ChatBird; enable only verified variants.
10. **Supervisor/read-only:** typed diagnostics and authenticated capability path.
11. **Safe code workflow:** scoped workspaces, fixed runner, previews, approval, install and rollback; disable execution if sandbox proof fails.
12. **Voice:** push-to-talk/local STT first, then opt-in Penguru wake-word detector, overlay and background/lock policy.
13. **Control Center:** finish all screens and real controls.
14. **Hardening:** offline, privacy, thermal/battery, accessibility, update/rollback and device profiles.
15. **Release proof:** run all gates, package app/service, document exact support and known limitations.

You may parallelize independent work, but preserve interface contracts and integrate/test each contribution.

---

## 14. Agent operating protocol — keep going until proven complete

At the start of each work cycle:
1. Read this prompt and the source implementation guide.
2. Read the current checklist and previous evidence.
3. Inspect the current working tree before editing.
4. Select the highest-priority incomplete task whose dependencies are satisfied.
5. Implement the real behavior, not a placeholder.
6. Run the narrowest relevant tests, then broader regression suites.
7. Fix failures and rerun.
8. Update checklist/evidence with exact commands, results and remaining limitations.
9. Commit only if the repository's workflow calls for it; never discard unrelated user changes.

Repeat this cycle. Do not stop after producing a plan or after one successful test suite.

### Completion discipline
- Never mark a gate complete without its evidence.
- Never replace failing tests with weaker tests.
- Never silently skip a feature because it is difficult.
- Never leave fake buttons, TODO-only implementations, stub responses or mock backends in production paths.
- Keep experimental/unavailable features explicitly labeled.
- If blocked, identify the precise blocker, attempt safe alternatives, complete independent tasks, and report what external action or hardware is required.
- Do not claim “100% complete” if any required gate is unverified.
- When all gates pass, run the full test suite from a clean/reproducible state and perform a final on-device walkthrough.
- Provide a final report with: implemented components, changed files, build/package commands, test commands/results, device evidence, model/runtime matrix, wake-word measurements, security findings closed, known limitations and exact remaining blockers (ideally none).

### Final end-to-end walkthrough

Demonstrate, on the actual target:
1. PenGuru starts OFF after install/reboot.
2. OFF means no PenGuru-specific process, model worker, classifier or microphone stream.
3. Owner enables PenGuru; service enters IDLE without loading a large model.
4. Owner selects Single ChatBird; a real request generates a response offline.
5. Owner selects Single CodeBird; a real code request uses CodeBird and bypasses SonarBird.
6. Owner selects Squad; SonarBird routes CHAT, CODE, SYSTEM and ASK test cases correctly.
7. Owner switches runtime preference; compatible packages work and incompatible combinations are rejected honestly.
8. Owner downloads a model; signature/hash/format/license/self-test gates all run.
9. Owner submits a read-only system query; it uses a typed API.
10. A proposed write shows an exact preview and requires the correct approval; denied/unapproved actions do not execute.
11. Code changes remain staged; safe tests run only if isolation is proven; rollback is verified.
12. Owner enables microphone permission and push-to-talk; local transcript enters the same request path.
13. Owner explicitly enables “Wake-word listening”; the microphone indicator becomes visible.
14. Owner says “Penguru” (peng-goo-roo), pauses, then speaks a command; the overlay opens, excludes the wake phrase from the command, displays the transcript and processes it.
15. Similar-sounding non-wake phrases do not routinely trigger; false accepts/rejects and battery cost are measured and reported.
16. Owner taps Stop listening or disables the wake-word switch; microphone closes immediately.
17. Owner disables PenGuru; all PenGuru processes/workers/audio streams stop and memory is released.
18. Reboot, suspend/resume, permission revocation and service restart do not violate OFF/privacy state.

**Start now with the repository audit. Then implement and verify the product in dependency order. Do not return a completion claim until the evidence supports it.**
