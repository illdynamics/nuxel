# PenGuru / NuXAI — Step-by-Step Implementation Plan

**Target:** Nuxel native (Fedora ARM64 userland on the phone, kernel 4.14.253)
**Host access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.11.12.99` (root)
**Source repo local path:** `/Users/wicked/x/nuxel`
**Guide version:** DUAL-RUNTIME IMPLEMENTATION GUIDE v1.1 (9 Nov 2026)

## Current implementation status (v0.8.9-beta)

This document is the implementation target, not a completion claim. Current
verified scope, outstanding work and release evidence live in
[`../docs/releases/v0.8.9-beta.md`](../docs/releases/v0.8.9-beta.md).
Owner signing trust is enrolled; the full dual-runtime and voice gates are open.

## How to use this plan
- Steps are **globally numbered** (`Step 1 … Step N`). Ask an agent to execute exactly one step, then verify its exit criteria before moving on.
- Each step lists: **Goal**, **Files / locations**, **Actions**, and **Exit gate / verification**.
- Gates referenced here map to the guide's `G0–G5` and Phase `0–7`.
- **Hard rule:** PenGuru stays chat-only until the Phase 0 security fixes (P0/P1) are closed and regression-tested. No privileged PenGuru action before that.
- Keep model weights / binaries OUT of source control; they come from the signed model store at runtime.

---

## PHASE 0 — Security & design freeze (Gate G0)
*PenGuru must remain chat-only until these pass.*

### Step 1 — Confirm target image, kernel and service/app IDs
- **Goal:** Establish the exact Nuxel image/kernel baseline and canonical identities used everywhere else.
- **Actions:**
  - On host: `uname -r`, record full build/boot-chain; snapshot available RAM, CPU topology (`lscpu`), storage.
  - Confirm the initial native target image and first supported phone SKU (decision item §17.1).
  - Assign canonical IDs: service account `nuxel-penguru`/`nuxel-ai-worker`, D-Bus name `org.nuxel.PenGuru1`, app id for PenGuru, queue DB path `/var/lib/nuxel-penguru/queue.db`.
- **Exit:** One line each: target image, kernel, SKU(s), service account names, D-Bus name, app id.

### Step 2 — Fix P0: root-owned HTTP bridge dev-mode auth (Gate G0)
- **Goal:** Remove the loopback no-token bypass and bind tokens to authenticated app identity.
- **Observed (guide §2.3):** `services/nuxel-bridge/systemd/nuxel-http-bridge.service` runs as root, binds `127.0.0.1:8080`, sets `NUXEL_HTTP_MODE=dev`; `services/nuxel-bridge/src/api.py` `_verify_auth()` accepts loopback without a token in dev mode; unauthenticated bootstrap route accepts an app id and does not bind body identity to token identity.
- **Actions:**
  - Remove/neutralize the dev-mode loopback bypass; make production units fail the build if any env can enable it.
  - Bind every session token to a launcher-authenticated app identity; enforce `token.app_id == request.app_id` for every method.
  - Derive caller identity from trusted launcher / authenticated D-Bus peer credentials, NOT JSON body, Origin or Referer.
  - Add typed PenGuru broker surface over the canonical permission service instead of generic HTTP `/rpc`.
- **Exit:** Build fails if dev bypass is enabled; no loopback path accepts a request without a token.

### Step 3 — Add P0 tests: forged app_id, token replay across apps, identity mutation, missing launcher secret, untrusted loopback, unauthorized service control
- **Goal:** Prove the Step 2 fixes hold under hostile inputs.
- **Actions:** Write and run unit/integration tests for each scenario above against the bridge API.
- **Exit:** All new tests pass; none silently accept a forged/replayed/mutated identity.

### Step 4 — Fix P1: once/session grant cache semantics (Gate G0)
- **Goal:** Never cache a `once` grant as reusable; bind session grants to real sessions with expiry/revocation.
- **Observed (§2.4):** `services/nuxel-bridge/src/bridge.py` `_check_capability()` can return true from an in-memory cache before consulting the portal.
- **Actions:**
  - Consume `once` at the permission authority, bound to one immutable action/request ID (no reuse).
  - Bind `session` grants to a real session id with explicit expiry and revocation events.
  - Persist `always` only where policy permits; use monotonic time for in-process expiry.
- **Exit:** Bridge regression proves first `once` action succeeds, second fails within same daemon lifetime.

### Step 5 — Canonicalize capability registry (Gate G0)
- **Goal:** Eliminate the fourth independent capability definition (§2.5).
- **Actions:** Treat `shell/nuxel-shell/nuxel-permissions/` canonical registry (`capabilities.json`, `nuxel-permd.py`) as authoritative; generate bridge adapter schemas from it; deny unknown capability names; add PenGuru scopes there and CI validation.
- **Exit:** No bridge-side or module-level duplicate registry; unknown capabilities are rejected in tests.

### Step 6 — Kernel sandbox reality check + Supervisor probe (Gate G0)
- **Goal:** Make the Sandbox reflect real kernel facts (§2.6, Linux 4.14.253).
- **Actions:** Probe for Landlock/AppArmor/SELinux; if a sufficiently isolated code runner is unavailable, disable code execution and permit only patch review/export. Record effective isolation primitives (DAC, Linux caps, seccomp, systemd sandbox settings).
- **Exit:** Supervisor runtime-probes real features and reports which are effective on this device.

### Step 7 — Decide v1 scope anchors (decision items §17.1)
- **Goal:** Lock the open architectural decisions before Phase 1 exits.
- **Actions & recorded decisions:**
  - Which exact Nuxel image/kernel + first supported SKU.
  - ChatBird default vs explicitly chosen low-refusal personality model (Supervisor stays safety boundary).
  - Who signs manifests + which release-key trust root is embedded in Nuxel.
  - First published ONNX export precision/provider per model.
  - Definition of a "supported" profile: context + battery/thermal budget.
  - LAN provider reserved for v2 (recommendation: yes, keep v1 fully local).
- **Exit:** A signed decisions record with the answers above.

---

## PHASE 1 — Dual-runtime spike (Gate G1 & G2 signal)
*Build one runtime end-to-end before making two engines parallel (guide §16.1).*

### Step 8 — Pin and build llama.cpp ARM64 from immutable commit
- **Goal:** Reproducible pinned llama.cpp for the supplied GGUFs (§5.3).
- **Actions:** Pick an immutable git commit; build ARM64 with CMake flags recorded; capture source commit, compiler, linked backends, SBOM, binary hash; NEON-capable CPU kernels baseline only.
- **Exit (G1):** Pinned commit + artifact hash recorded; `libllama` builds on the device.

### Step 9 — Load ChatBird GGUF in llama.cpp with correct template
- **Goal:** Load `Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf` (§6.1) end-to-end.
- **Actions:** Use exact GGUF metadata/chat template, tokenizer BOS/EOS, stop sequences; run load-time self-tests (metadata parse, arch id, template presence, tokenizer sanity, short generation, clean cancellation).
- **Exit (G1):** ChatBird loads and generates a bounded response; templates correct for Llama family.

### Step 10 — Load CodeBird GGUF in llama.cpp with correct template
- **Goal:** Load `Qwen3.8-4B-Q4_K_M.gguf` (§6.1); needs recent Qwen3.5/Gated DeltaNet-capable build.
- **Actions:** Same self-test suite; verify Qwen3.5 template (do NOT use Llama template for Qwen).
- **Exit (G1):** CodeBird loads and generates; correct Qwen template applied.

### Step 11 — Cancellation, memory release and no external TCP listener
- **Goal:** Safe worker lifecycle (§5.3, §8.7).
- **Actions:** Implement cancel/finish bounded generation on unload; confirm worker RSS falls below baseline after unload; ensure no general REST/TCP listener in the application path.
- **Exit (G1):** Cancellation works; RSS reclaimed; no loopback TCP server used by app path.

### Step 12 — Build/pin standard ONNX Runtime for SonarBird (§5.4, §7.6)
- **Goal:** Standard ORT session for the MiniLM encoder + classifier (NOT GenAI).
- **Actions:** Pin ONNX Runtime core ARM64; assemble encoder+tokenizer+pooling+classifier head package; run its own accuracy tests.
- **Exit (G2 signal):** SonarBird classifier loads and passes accuracy tests with a complete bundle.

### Step 13 — Export candidate ONNX for CodeBird from Transformers checkpoint (§5.4, §6.1)
- **Goal:** Build ONNX GenAI package from `empero-ai/Qwen3.8-4B-Distill` (NOT the GGUF).
- **Actions:** Pin ONNX Runtime + GenAI compatibility set; use pinned model-builder version; record every builder option; bundle `genai_config.json`, graphs, external tensor shards, tokenizer/generation configs; test template/tokenizer parity vs source checkpoint.
- **Exit (G2 signal):** Export either passes parity+load or is recorded as unavailable; never convert the GGUF.

### Step 14 — Export candidate ONNX for ChatBird from Transformers checkpoint (§5.4, §6.1)
- **Goal:** Build ONNX GenAI package from `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated`.
- **Actions:** Same process; verify parity and ARM64 load path.
- **Exit (G2 signal):** Passes or recorded unavailable; license/provenance conflict flagged for legal review (§6.1).

### Step 15 — Capture device memory baselines on target SKU
- **Goal:** Establish usable-RAM baseline before building scheduler logic (§8.4).
- **Actions:** Measure OS+compositor reserve, foreground app reserve, NuXAI overhead; record per-model cold load and peak RSS candidate.
- **Exit (G3 signal):** Baseline numbers captured for the target SKU.

---

## PHASE 2 — NuXAI platform core (Gate G5 partial)
*Same API drives both backends (§4.1, §5.2).*

### Step 16 — Define common InferenceRuntime contract + schemas
- **Goal:** Stable versioned interface (§5.2).
- **Actions:** Author `InferenceRuntime` probe/load/generate/cancel/health/unload/info; `RuntimeProfile {engine, package_format, provider, threads, context_limit,...}`; request/route/action JSON schemas under `schemas/`. Keep it a contract, adapted to Nuxel language/build.
- **Exit:** Contract + schema files land and are validated in CI.

### Step 17 — Implement NuXAI control-plane daemon (unprivileged)
- **Goal:** Mode controller + request queue (SQLite) + routing facade (§4.1, §8.1).
- **Actions:** Create `services/nuxel-penguru/daemon` as unprivileged `nuxel-penguru` service; implement mode state machine, SQLite request queue, D-Bus method skeletons (`org.nuxel.PenGuru1`).
- **Exit:** Daemon starts under the dedicated account; status endpoint responds.

### Step 18 — Implement llama.cpp adapter (GGUF) behind common API
- **Goal:** Wire pinned llama.cpp to `InferenceRuntime` (§5.3).
- **Actions:** In-process or tightly sandboxed worker process via IPC over Unix peer credentials + FS permissions; no TCP listener; model-specific profiles per GGUF.
- **Exit:** Both GGUFs load through the common API in single mode.

### Step 19 — Implement ONNX Runtime GenAI adapter behind common API
- **Goal:** Versioned GenAI adapter (§5.4). Keep separate from standard ORT.
- **Actions:** Adapter loads verified ONNX bundles; handles tokenizer/template, logits/sampling, KV-cache; fails closed on unsupported operator/provider/graph mismatch with specific status.
- **Exit:** Compatible ONNX package loads via common API; incompatible pairing is rejected (not silently converted).

### Step 20 — Implement runtime selector + compatibility resolver (§5.6)
- **Goal:** `resolve_backend()` returns explicit engine/provider/revision or `BACKEND_UNAVAILABLE`.
- **Actions:** Enforce user preference as a constraint; AUTO picks highest-priority verified candidate allowed by policy; UI shows resolved engine+revision+provider before generation; no silent fallback mid-generation.
- **Exit:** Explicit selection requires a compatible verified artifact; mismatches report actionable status.

### Step 21 — Implement worker manager + one-heavy-model scheduler (§8)
- **Goal:** Demand-load workers, one resident by default (§8.3).
- **Actions:** Worker lifecycle state machine (DISABLED→IDLE→ROUTING→LOADING→ACTIVE→DRAINING→UNLOADING→ERROR); memory budget model; thread/context/batch limits honoring CPU topology; battery/thermal states.
- **Exit:** One worker resident by default; load/unload/cancel cycles do not leak significant memory.

### Step 22 — Systemd hardening profile for the daemon (§9.3)
- **Goal:** Start-line hardened unit (validate against actual systemd/kernel).
- **Actions:** Apply `User/Group=nuxel-penguru`, `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=read-only`, kernel protection directives, `ReadWritePaths=/var/lib/nuxel-penguru`, `RestrictAddressFamilies=AF_UNIX`; add MemoryMax/CPUQuota/TasksMax after measurements; downloader gets separate HTTPS access.
- **Exit:** Unit loads and runs hardened; build test asserts hardening directives present.

---

## PHASE 3 — Model Store + single modes (Gate G5 partial)

### Step 23 — Model registry + signed immutable manifests (§6.2, §11)
- **Goal:** Registry identity per model with separately verified package variants.
- **Actions:** Author manifest schema (§11.3); record source_repo, immutable revision, file list/sha256, format, arch, quantization, runtime profile, license; keep placeholders for hashes/sigs (do NOT invent them).
- **Exit:** Manifest schema validated; example manifests pass schema check with placeholder values.

### Step 24 — Download helper: resumable transfer + integrity pipeline (§11)
- **Goal:** User-started, signed, atomic install (§11.1/§11.2).
- **Actions:** State machine NOT_INSTALLED→USER_CONFIRMED→…→SELF_TEST→READY; HTTPS resume/range/cancel/retry; verify signed manifest (trusted channel), SHA-256 per file, GGUF/ONNX metadata, arch, tokenizer, size; atomic move into `/var/lib/nuxel-penguru/models/<model-id>/<revision>/<variant>/`; quarantine+clean partial on failure.
- **Exit:** Downloads verify signatures/hashes and install atomically; corrupt/partial files are quarantined and removed.

### Step 25 — Three model cards in NuXtore/PenGuru (§6.4)
- **Goal:** ChatBird, CodeBird, SonarBird download cards.
- **Actions:** Each card shows role/author/repo/exact variant/size/context/quant/backend-compat/licence/provenance/verification; per-model GGUF/ONNX variant switch only when both signed+approved; keep exactly three logical cards.
- **Exit:** Cards render with real package details; disabled until verification passes.

### Step 26 — Register PenGuru in PWA pipeline (§9.4)
- **Goal:** Canonical app registration via existing build/asset pipeline.
- **Actions:** Add PenGuru entry to `pwa/nuxel-common/app-registry.json`; build manifest through the asset pipeline; reuse `bridge.js` + `bridge-version.json`; validate schema changes in CI.
- **Exit:** PenGuru app registered; build test proves it is packaged.

### Step 27 — Single ChatBird end-to-end (offline, bypasses SonarBird) (§4.3)
- **Goal:** Every prompt → ChatBird directly.
- **Actions:** Direct worker path still runs Supervisor validation, capability broker, schema checks, audit; tool-like strings in output stay inert without a typed UI action.
- **Exit:** Offline single-chat works; hashes verified; one-worker policy holds.

### Step 28 — Single CodeBird end-to-end (offline, bypasses SonarBird) (§4.3)
- **Goal:** Every prompt → CodeBird directly.
- **Actions:** Same as above for code worker; benchmark on Nuxel-specific code tasks (§6.1).
- **Exit:** Offline single-code works; hashes verified.

---

## PHASE 4 — SonarBird + Squad (Gate G5 partial)

### Step 29 — Tier 0 deterministic rules engine (§7.3, §7.4)
- **Goal:** Every Squad request runs deterministic rules first.
- **Actions:** Implement detection for SYSTEM candidate (supported setting+verb+id), CODE candidate (fence/trace/source/compiler error), CHAT candidate (knowledge/chat cues); low specificity → ASK; no `requires_approval` field emitted.
- **Exit:** Rules produce constrained route labels + reason codes only.

### Step 30 — Tier 1 MiniLM embeddings + Nuxel classifier (§7.3, §7.6)
- **Goal:** Standard ORT session after Tier 0; calibrated confidence.
- **Actions:** Complete SonarBird ONNX package (encoder+tokenizer+pooling+classifier); produce route reason + version; confidence buckets per §7.5 starting thresholds.
- **Exit:** Classifier runs and returns label+confidence+reason for Squad requests.

### Step 31 — Routing decision policy + ASK/override (§7.3, §7.4)
- **Goal:** Clear CHAT/CODE → worker; SYSTEM only via known typed API; uncertain/high entropy → ASK.
- **Actions:** Implement confidence thresholds (experimental starts), override is user-only and visible (CHAT/CODE/ASK; no free-form SYSTEM); log label/scores/confidence/rule-id/version/override/outcome without retaining raw prompts by default.
- **Exit:** Squad routing works end-to-end with visible reason and ASK fallback.

### Step 32 — Build/freeze adversarial route test set (§7.5)
- **Goal:** Target ZERO false SYSTEM dispatches.
- **Actions:** Versioned dataset, hundreds of labeled examples per class; disjoint splits by intent family; measure macro-F1/precision/recall/calibration/confusion matrix/ASK rate/SYSTEM false-positive rate; freeze security test set.
- **Exit:** Zero false SYSTEM dispatch on the frozen set; wrong CHAT/CODE is a UX issue only.

### Step 33 — Squad mode end-to-end (§4.2)
- **Goal:** Request → SonarBird → route → worker/Supervisor/ASK.
- **Actions:** Wire full lifecycle: authenticate caller, session ownership, payload/queue/rate limits, store request record; SYSTEM via allowlisted typed capability through Supervisor; runtime manager picks installed variant and verifies memory/thermal budget before load.
- **Exit:** All four labels (CHAT/CODE/SYSTEM/ASK) work offline in Squad mode with visible route decisions.

---

## PHASE 5 — Read-only broker tools (Gate G5 partial)

### Step 34 — Typed read-only diagnostics via Supervisor/broker (§10, §9.5)
- **Goal:** Battery level, device identity, service status, documented diagnostics over authenticated typed capabilities.
- **Actions:** Implement read-only actions validated against compiled allowlist + canonical registry; no free-form shell; redact tokens/paths/secrets from diagnostics by default.
- **Exit:** Read-only device status is reliable; P0/P1 paths remain closed.

### Step 35 — D-Bus method surface for control plane (§14.3)
- **Goal:** Expose `GetStatus/SetEnabled/SetMode/SetRuntimePreference/SubmitRequest/GetRequest/CancelRequest/OverrideRoute/ListModels/StartDownload/CancelDownload/DeleteModel/ListApprovals/DecideApproval/RollbackAction GetDiagnostics`.
- **Actions:** Implement signatures and rules from §14.3; reject incompatible runtime prefs with reason (no silent fallback); approvals bound to payload hash/target/capability/session/expiry.
- **Exit:** Methods behave per contract; tests cover forged/replayed/expired identities.

---

## PHASE 6 — Safe writes + extension builder (Gate G5 partial)

### Step 36 — Isolated code workspace + fixed test runner (§10.4, §2.6)
- **Goal:** CodeBird writes only into a disposable, isolated workspace.
- **Actions:** Separate test process with resource limits, read-only source deps where practical, no network by default, dedicated UID, seccomp + namespace/systemd restrictions proven on active kernel; block symlink/path traversal; run fixed command catalogue (lint/test/build targets), not arbitrary model shell.
- **Exit:** Isolation verified on target kernel; if isolation cannot be proven, disable code execution and return patch/export only (§2.6).

### Step 37 — Typed proposals, approval hash + preview (§10.2)
- **Goal:** Model emits typed action objects (no shell strings); Supervisor builds immutable preview + approval hash.
- **Actions:** Validate against fixed schema; resolve against compiled allowlist; unknown → deny; create preview with canonical payload/affected resources/capability/risk tier/tests/rollback; store owner approval against crypto hash of exact payload+target+capability+expiry; re-verify before execution; any payload change invalidates approval.
- **Exit:** Tampered/replayed/denied-capability tests fail closed.

### Step 38 — Staged install + rollback for supported writes (§10.4)
- **Goal:** Only supported operations can write; rollback where a tested mechanism exists.
- **Actions:** Diff/manifest previews, declared permissions, test evidence; staged install after owner approval; rollback only where transaction/snapshot is verified; never imply every action is reversible.
- **Exit:** Extension rollback + each supported settings/system action restore correctly after simulated failure (§15.1).

---

## PHASE 7 — Hardening & pilot (Gate G5, G3)

### Step 39 — Full test matrix execution (§15.1)
- **Goal:** Run every required test area.
- **Actions:** Model artifacts; llama.cpp; ONNX GenAI; SonarBird; modes; runtime selector; Supervisor; permissions; sandbox; privacy/offline; device health; rollback. Fix failures with regression tests.
- **Exit:** Test matrix passes; coverage documented.

### Step 40 — Device measurement protocol (§12.5)
- **Goal:** Real performance/power evidence on exact SKU.
- **Actions:** ≥3 cold starts per model/runtime; TTFT; prompt/decode tokens/s; peak RSS/PSS; temperature/throttling; battery; UI responsiveness; suspend/resume; leak test; low-memory + foreground app conditions; cancellation/unload loops. Publish raw logs/scripts (no guessed TPS in notes).
- **Exit (G3):** Benchmark records follow §15.3 format with real values per device/SKU/build.

### Step 41 — Privacy, offline & power hardening (§13)
- **Goal:** Offline-first, no telemetry, local retention controls.
- **Actions:** Airplane-mode inference after install; worker network denied by default; downloads via separate user-started process; per-conversation deletion/clear-all/retention/redaction; microphone off by default, no wake-word at boot (§13.1).
- **Exit:** Offline operation verified for all three modes; telemetry absent; privacy controls functional.

### Step 42 — Acceptance criteria sign-off (§15.2)
- **Goal:** Confirm every bullet in §15.2.
- **Actions:** Walk each acceptance criterion with evidence (defaults OFF stops daemons and releases memory; all three modes offline; single modes bypass SonarBird; runtime selection works; one-worker resident; signed manifests; no model output executes system action without typed path; zero false SYSTEM; rollback tested; performance claims tied to named test record).
- **Exit:** All §15.2 criteria pass with recorded evidence.

### Step 43 — Packaging, signatures, update/rollback + release docs (§17.2)
- **Goal:** Ship-ready artifacts and user docs.
- **Actions:** Sign manifests; embed release-key trust root; update/rollback pipeline; accessibility; packaging for target image; user doc states exact supported devices, runtimes and limitations.
- **Exit (G4):** Signed immutable manifests; docs state supported devices/runtimes/limitations.

### Step 44 — Opt-in pilot on primary device (§16)
- **Goal:** Real-world pilot before secondary-device enablement.
- **Actions:** Enable feature opt-in on the primary SKU only; monitor thermal/battery; collect issues; secondary devices enabled only after exact profiles pass.
- **Exit:** Pilot passes on primary device; secondary enables only after profile validation.

---

## Appendix P — Agent execution conventions (for the operator)
1. Hand one numbered Step at a time; wait for its Exit criteria before the next.
2. Prefer building the llama.cpp GGUF path first (§16.1 order): common API+registry → llama.cpp both GGUFs → SonarBird ONNX → ONNX GenAI CodeBird then ChatBird → UI/toggles/matrix.
3. Never invent hashes, commits or file sizes; keep them as placeholders until the release pipeline populates them (§11.3).
4. Keep model weights and binaries out of source control (Appendix A).
5. Any P0/P1 regression must be closed before privileged PenGuru actions exist.
6. Record every decision, build pin, hash reference and device measurement as you go for the release evidence (§15.3 / §17.2).

---
*Plan generated from DUAL-RUNTIME IMPLEMENTATION GUIDE v1.1 (9 Nov 2026). Gates G0–G5; Phases 0–7.*
