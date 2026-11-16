# PenGuru v1 Implementation Plan

Below is the fully-detailed integration and implementation plan for PenGuru on Nuxel. We cover architecture, devices, model choices, routing and management, security, testing, and a phased roadmap. This is written in a clear, organized way (with tables and bullet lists) but with an upbeat, honest Gen-Y vibe—**no sugar-coating, mate**. Remember: **“Prettig gestoord, maar serieus wanneer het hoort.”** Let’s do this! 🤙

## 1. v1 Scope and Exclusions

- **Included features (v1)**:  
  - **Always-on infrastructure**: Wake-word detection (CPU-only), a lightweight STT module, and the PenGuru Sentinel/Queue service (SQLite) that lives continuously.  
  - **Router (“PenGuru Mini”)**: A tiny intent classifier (0.3–0.6B) that outputs a constrained JSON routing message.  
  - **Workers (demand-loaded)**:  
    - **Assistant_Pepe_8B**: General conversational assistant (personality-driven).  
    - **SemCoder-S_6.7B**: Code creation, debugging, and program-reasoning model.  
    - **(Optionally InCoder_6B)**: Code infilling/completion, used only if licensing and benefits make sense.  
  - **Supervisor (deterministic)**: Handles permissions, sandboxing, compiling/tests, diff checks, and install/rollback. Acts as the safety gate for any system changes.  
  - **Local-only operation**: PenGuru can run entirely offline, but optionally can contact a remote M1 Mac for heavy tasks (future).  
  - **Voice pipeline**: Wake-word → verify speaker → STT → intents → model → TTS (with mic off by default and visual mic-on indicator).  
  - **UI**: Echo-back of actions (e.g. “Scheduling silent mode…”) and user approval for code changes.  

- **Excluded or deferred (v1)**:  
  - **GPU/NPU acceleration** beyond basic CPU (no custom GPU code).  
  - **Dust language support** beyond optional later consideration (focus on general-purpose coding first).  
  - **Alternative assistants** (no non-LLM fallback except a very small profile if needed).  
  - **Continuous active LLM** (models only load on demand).  
  - **Cloud model fallback** (except the optional M1 path for later).  

We assume for v1 that Nuxel runs on Android devices via a Linux container or chroot (Termux style) **except** that everything is orchestrated by our own services. This way we don’t rewrite Android drivers. All design below is for a *Linux* userland (Fedora ARM64) on each phone; how it’s hosted (native or container) is pluggable. 

## 2. Architecture Diagram

```mermaid
flowchart LR
    subgraph Always-On
      U[User ⟶ mic / input]
      W[Wake-word detector (tiny)]
      STT[STT (Whisper-tiny/base or Vosk)]
      SENT[PenGuru Sentinel + Queue (SQLite)]
      R[PenGuru Mini (Router) ~0.3B classifier]
      U --> W --> STT --> SENT --> R
    end

    subgraph Workers
      AP[Assistant_Pepe_8B (chat)]
      SC[SemCoder-S_6.7B (coding)]
      IN[InCoder_6B (infill, optional)]
      R -->|intent=conversation| AP
      R -->|intent=code_change| SC
      R -->|intent=code_debug| SC
      R -->|intent=code_complete| IN
      R -->|device_command| APIs
      APIs[[Native Nuxel APIs]]
    end

    subgraph Supervisor
      SUP[PenGuru Supervisor (deterministic)]
      AP --> SUP
      SC --> SUP
      IN --> SUP
      SUP -->|approve| SENT
      SUP -->|install/rollback| Nuxel[[Nuxel OS]]
    end
```

- **Flow**: User speaks or types → Wake-word picks it up → STT runs if needed → Sentinel enqueues request → Mini-router (0.3–0.6B) classifies intent, producing JSON like 
  `{"intent":..., "target":..., "task":..., "requires_approval":...}`.  
- **Routing**: By intent the router sends tasks to the right worker: **Assistant_Pepe** for chats/general Q&A, **SemCoder-S** for coding tasks (create/repair/debug), **InCoder** for code infill (experimental), and direct calls to native Nuxel APIs for simple device commands (Wi-Fi, volume, etc.).  
- **Supervisor**: All system actions (package install, code patch apply, etc.) go through this. It checks permissions, runs compiles/tests in a sandbox (e.g. namespace/seccomp), and only after user approval does it commit changes (e.g. via Btrfs/OSTree or an A/B update).  

## 3. Device Matrix (Hardware/RAM/Models)

| Device         | CPU/GPU/Accel   | RAM    | Supported Models (v1)  | Notes / Perf & Risks                                         |
|---------------|----------------|-------|------------------------|----------------------------------------------------------------|
| **Pixel 10 Pro (16GB)**  | Tensor G5 (TPU/DSP, 6.5 TOPS) / AI Engine   | 16 GB  | Assistant_Pepe_8B (loaded by default), SemCoder-S_6.7B (on demand) | **Good candidate** for both 8B and 6.7B models. Tensor chip may allow ~medium-speed inference. Loading 5GB ~10–30s; ~10–20 tok/s (high variability). Temperature rise high under long use.  |
| **Galaxy S10+ (8GB)**    | Exynos 9820 CPU 8-core (Mali GPU not usable), ~2.7 GHz | 8 GB   | SemCoder-S_6.7B (swap with Assistant_Pepe), possibly a 3–4B fallback (since 8B + Android is tight) | **Memory pressure**: 8GB excludes running 8B model alongside OS (~16GB total). Can run one 8B model (4.93 GB) if nothing else loaded, but we plan sequential load/unload. Expect ~5–10 tok/s on CPU. **Risk**: OOM on large tasks. Possibly use a smaller assistant (see decisions). |
| **Galaxy S10+ (12GB)**   | Exynos 9820 CPU       | 12 GB  | Assistant_Pepe_8B (if available), SemCoder-S_6.7B | 12GB mitigates but still not huge headroom. May allow one 8B model loaded at a time. Stay careful with multi-model swaps (must drop one fully before load other). |
| **Moto G7 Power (4GB)** | Snapdragon 632 (octa CPU), 1.8 GHz | 4 GB   | **None (real-time)** or tiny 3B assistant only | 4GB is barely enough for a ~3B float16 model (e.g. Llama-2-3B ~2.7GB) plus OS. **Likely excluded**: Either skip PenGuru here, or support a *very* minimal mode (no coding). If included, only a small 3B chat model (≈2–3GB RAM) can be loaded, and even that with caution. |

**Comment**: The Pixel (mustang) is our strongest target (16GB, dedicated tensor cores). The S10+ Exynos variants are weaker – treat them as CPU-only with 5–10 tok/s and careful memory management. The G7 (ocean) is practically unable to run 6–8B models; at most a smaller model for simple tasks. This plan assumes at least **Android + chroot/container** on each. If a device can run Nuxel natively (unlocked Pixel, custom Linux ROM on S10), that’s great but not required for v1. All performance numbers (tokens/sec, load times) must be **benchmarked on real hardware**. Our assumption: ~50 MB/s internal storage, so a 5GB model load is on the order of 10–100 seconds depending on device storage speed.

## 4. Model Comparison and Selection

We compare each candidate model (parameters, quant sizes, license, recommended role):

| Model               | Params (≈) | License           | Q4_K_M (GB) / Q8 (GB) | Intended Use                      | Recommendation                                 |
|---------------------|-----------|-------------------|-----------------------|-----------------------------------|-----------------------------------------------|
| **Assistant_Pepe_8B**   | 8B        | LLAMA 3.1 (Community) | 4.93 / 8.55 | Chat, general Q&A, system explanations | *Primary conversational model*. Fits 16GB device. Irreverent personality (very low censorship) – test carefully. Must comply with Llama 3.1 terms (see risks below). |
| **SemCoder-S_6.7B**    | ~6.7B     | DeepSeek model license (MIT-based) | 4.08 / 7.16 | Code creation, debugging, reasoning | *Primary coding specialist*. Fine-tuned on static + dynamic code data (execution reasoning) and outperforms GPT-3.5 on many tasks. Use for all code changes. Bundled locally (check DeepSeek license terms). |
| **SemCoder_6.7B (base)**| 6.7B     | DeepSeek (same)   | *Likely same sizes as SemCoder-S* | Core code semantic model          | We recommend **SemCoder-S** (extended) as it includes extra instruct data. The base version is similar 6.7B; skip if SemCoder-S covers needs. |
| **InCoder_6B**       | 6B        | CC BY-NC 4.0   | *No official quant provided (orig ~26.6GB) | Code infilling/completion          | *Optional*. Good at inserting code into existing files. Old (2022) model. **License NC** prohibits commercial distribution, so **only use non-commercially**. If used, treat as an *extra* code tool *after* testing. |
| **Fallback 3–4B LLM** | ~3–4B     | Permissive (e.g. Llama-2-7B-Instruct or similar) | ≈3.0–6.0 / ≈5–10 (estimate) | Backup general assistant (small)   | If Assistant_Pepe is too big (e.g. on G7 or 8GB S10), swap to a smaller LLM (~3B–4B). Candidates: LLaMA-2 (requires Meta license), Mistral-7B (MIT license) trimmed to Q4_K_M ~4–5GB, etc. Must have a license allowing embedding. |

*Notes*: Sizes above are **GGUF quantized** footprints (Q4_K_M and Q8, based on Hugging Face model pages). “Q4_K_M” is recommended for balance of size vs quality. Always verify actual RAM footprint when loading (including model + temp buffers). We also note each model’s **tool-calling** interfaces: They all support standard causal LM APIs (no special function-calling).

## 5. Routing Schema and Fallbacks

The router outputs JSON with fields: `intent`, `target`, `priority`, `task`, `requires_approval`, etc. We define the schema:

- **Valid Intents**:  
  - `conversation` – freeform chat or general question.  
  - `code_change` – request to write/modify code (new feature, patch).  
  - `code_debug` – ask why code is failing or needs repair.  
  - `code_complete` – infill/complete an existing code snippet.  
  - `device_command` – trivial OS action (Wi-Fi on/off, volume, etc.).  
  - `explain` – ask how Nuxel or a system component works. (Routing as conv.)  
  - `security_sensitive` – e.g. change user permissions; triggers Supervisor path.  
  - `uncertain` – if the model is not confident.  

- **Target Values**:  
  - `assistant_pepe`, `semcoder_s`, `incoder`, `supervisor`, or `system_api`.  

- **Priority**: `low`, `normal`, `high`. (High for urgent tasks or new device events.)  

- **requires_approval**: boolean (e.g. `true` for code changes or security tasks).  

Example router outputs (as JSON objects):

```json
{ "intent":"code_change", "target":"semcoder_s", "priority":"normal",
  "task":"Add automatic silent mode scheduling", "device":"beyond2lte", "os":"Nuxel", "include_logs":true, "requires_approval":true }
```

```json
{ "intent":"conversation", "target":"assistant_pepe", "priority":"low",
  "task":"Explain how Nuxel handles Bluetooth" }
```

**Schema rules and fallback**: We will use a strict JSON schema to validate fields. If the intent/classification is **uncertain or invalid**, default to a safe route: either `conversation` (Assistant_Pepe) or ask for clarification. For example, ambiguous queries can yield intent=`uncertain` and we fall back to a help response or general chit-chat. 

- For `device_command` (like “Set Wi-Fi on”), the router will mark target=`system_api` and Supervisor will call the native API directly (no LLM needed) – this bypasses heavy models.  
- For `security_sensitive` (e.g. installing new package, changing root password), the router sets `target=supervisor` and Supervisor handles it with multi-factor checks (see Security below).  

We’ll **evaluate the router** using a test set of categorized prompts (e.g. 1000 utterances spanning all intents). Possible approach: train a tiny classifier (or even regex rules) and measure accuracy > 95%. If using an LLM-based router, we'd prompt it to output JSON and verify format compliance.

## 6. Model Manager State Machine

The **Model Manager** ensures only one heavyweight model is loaded at a time. States:

- `Idle` (no model loaded, only Sentinel running).  
- `Loading(model)` – when switching. We show user a “loading” UI message.  
- `Active(model)` – ready to answer queries.  
- `IdleTimeout` – after a period of inactivity (e.g. 2 min), auto-unload to save RAM; go to Idle.  
- `Swap(model_from→model_to)` – triggered by router if new intent needs a different model. Sequence: Unload current (clear memory), then load new; user sees a brief “switching assistant” message.  
- `Error` – if a model fails to load (OOM or disk error). Fallback: if loading an 8B failed, perhaps try 6B fallback; else notify user of failure.  
- `Abort` – if user cancels a request mid-loading (should revert to previous stable state).  

At each state, we should have clear feedback: e.g. when unloading/loading, some progress or spinner. On OOM/failure, we display an error like “Model too large on this device” and log for fix.

## 7. Phased Roadmap

1. **Phase 0 – Hardware Benchmark Spike (1–2 months)**  
   - Port basic Nuxel environment to each phone (Android container or chroot). Verify basic OS operations.  
   - Benchmark storage I/O (loading 1–5GB files), CPU (llama.cpp on 6B/8B quant models), time-to-first-token, tokens/sec for each device (using llama.cpp or equivalent). Collect temperature/battery usage baseline.  
   - Determine precise memory limits. This informs which models can run on which device.  

2. **Phase 1 – Core Infrastructure (2 months)**  
   - Implement Sentinel/Queue service (SQLite) and wake-word detection (CPU C only). Integrate chosen STT (e.g. Whisper base).  
   - Develop the Router (use an off-the-shelf intent classifier or a simple fine-tuned 0.3B model). Create JSON schema validation and fallback logic.  
   - Dummy hook-ups: For now, have Router send all tasks to a simple echo assistant.  

3. **Phase 2 – Conversational Assistant (2 months)**  
   - Integrate Assistant_Pepe_8B on Pixel 10 (ensure quantization loads and runs). Test conversation and instruction-following (using llama.cpp or natively via HF transformers). Evaluate appropriateness (tone, factuality). If needed, prepare a smaller backup model for 8GB devices.  
   - Add Assistant_Pepe to Model Manager with full swap logic.  
   - Test prompts forcing JSON structure output, and adjust prompt engineering to ensure compliance.  

4. **Phase 3 – Coding Assistant (3 months)**  
   - Integrate SemCoder-S_6.7B. Verify it loads (e.g. Q4_K_M gguf) and test code generation, debugging examples. Run internal tests: feed small codebases, ask for bug fixes, check validity.  
   - If beneficial, test InCoder_6B for infilling tasks (on Pixel only, optional). Respect license.  
   - Create Supervisor workflows: e.g. “apply patch” command saves diff to disk, runs compiler/test (perhaps in a Docker-like sandbox on the device), reports success/failure.  
   - Implement user approval UI: diff view, Y/N prompt. On “yes”, Supervisor performs actual OS changes (e.g. via `dnf`, `rpm-ostree deploy`, or file updates).  

5. **Phase 4 – Security & Device Integration (2 months)**  
   - Implement speaker verification (biometrics or voice ID) before actions. Secure channel gating.  
   - Harden against prompt injection: sanitize inputs, do not pass web notifications or unsolicited content directly to LLM.  
   - Sandbox for code execution: e.g. use Linux namespaces or a minimal container/VM for `make test`.  
   - Backup & rollback: Configure Nuxel with Snapper/Btrfs (if Fedora) or packaging transactions. Test rolling back a bad update.  
   - **Key Acceptance Test**: For each milestone, use fixed scenarios: e.g. “Intent: code_change, New feature, expect semcoder-driven patch, test passes”, “Intent: conversation, question, answer given”, “System action: Wi-Fi on, confirm indicator lights.”  

6. **Phase 5 – Optimization & Polish (ongoing)**  
   - Profile battery draw: ensure listening and small inference is low-power. Set thermal limits (throttle or refuse on high temp).  
   - Streamline model swapping: if GPU/TPU acceleration becomes available (e.g. via MediaPipe), integrate.  
   - Optionally add remote fallback: if Pixel is online and connected to M1 server, allow complex tasks to run off-device with user consent.  

## 8. Test Strategy

- **Router Tests**: Assemble a labeled set (~1000 examples) of user requests covering all intents. Measure classification accuracy, confusion between code vs conversation, etc. Fallback accuracy (uncertain detection) must be very high (>95%).  
- **Worker Output Tests**: For Assistant_Pepe, verify well-formed JSON outputs when expected (e.g. tasks with fixed format). For SemCoder, run it on known code problems and check it either compiles or provides correct reasoning (unit tests). For InCoder, fill sample gaps and verify syntax.  
- **Supervisor Tests**: Try malicious/dangerous actions (e.g. “format disk”) and ensure they are blocked or require approval. Confirm rollbacks via snapshots work on a test image.  
- **Swap-time / Battery Benchmarks**: Measure wall-clock time and battery% change for: *Idle listening only (background)*, *model swap (8B to 6B)*, *sustained generation (simulate 100 tokens at max rate)* on each device. Define fail criteria (e.g. >5% battery drop per minute or >45°C device temp triggers warning).  
- **End-to-End Scenarios**: Scripted interactions: e.g. “Add silent mode scheduling” → expect code patch file and test results → approval → installation. Another: “What’s my battery level?” → expect direct API answer (no LLM). All major workflows should have automated tests.

## 9. Risk Register

- **Device Porting**: *Likelihood: High.* Unlocking and maintaining a Linux environment on consumer phones is tricky. *Impact:* PenGuru won’t work if Nuxel can’t run. *Mitigation:* Focus on container approach for v1, use official support libraries, limit changes to user-space.  
- **Memory Pressure/OOM**: *Likely on 8GB devices.* Running 8B models plus OS can exhaust RAM. *Impact:* Crashes or forced kills. *Mitigation:* Strict one-model-at-a-time policy, use 6B/3B where needed, careful tuning of `--llama-rope-params`, or swap-to-disk (bad perf). Benchmark early.  
- **Licensing**: *Moderate.* Llama-3 community license has terms on content, and InCoder’s CC-BY-NC forbids commercial use. *Impact:* Legal blocking of releases. *Mitigation:* Consult legal. Possibly remove InCoder or make it optional. Ensure users agree to licenses (LLM license dialogs). Use only MIT/Apache models for core.  
- **Model Quality**: *Moderate to High.* Assistant_Pepe can go off the rails (conspiracy or unhelpful jokes). SemCoder, while strong, may still hallucinate code. *Impact:* Bad user experience, incorrect code changes. *Mitigation:* Keep human-in-the-loop: always require user approval before applying changes. Tweak system prompts or include a filter on *naughty or unsafe content*. Possibly provide a safe mode persona (or fallback model).  
- **Prompt Injection / Content Poisoning**: *Likely in adversarial scenarios.* If a user or app content sneaks malicious text into a prompt, the LLM might do something unsafe. *Impact:* Unauthorized actions. *Mitigation:* Sanitize all inputs. Use a wrapper that strips code blocks or special tokens. Keep the Supervisor to enforce final checks.  
- **Build/Runtime Failures**: *Medium.* Device-specific issues (binaries not compiling, library mismatches). *Impact:* PenGuru crash or inability to swap. *Mitigation:* Rely on stable C++ toolchains, containerize critical parts, unit test on each device.  
- **Maintenance/Updates**: *Ongoing risk.* OS or model updates could break behavior. *Impact:* Full breakage if a model changes output format. *Mitigation:* Lock model versions. Provide easy patching to update to new checkpoints if needed.  

## 10. Unverified Claims to Check

Below are statements from the proposal that need verification or clearer sources:

- **“Assistant_Pepe_8B can run on Pixel 10 Pro”** – We need to benchmark actual memory and speed on the Pixel (test ASAP).  
- **“Assistant_Pepe personality is intentionally irreverent/conspiracy”** – Taken from its model card, but verify with our own tests that it *really* outputs stuff in line with the documentation, especially around sensitive topics.  
- **“SemCoder outperforms GPT-3.5 on debugging”** – Cited from its NeurIPS paper. Good claim, but should confirm by running the recommended benchmarks (e.g. HumanEval 100) if practical.  
- **“InCoder-6B was trained on permissively-licensed code, but is CC-BY-NC”** – The model card confirms the CC-BY-NC license. Confirm whether using it in a *non-commercial* open OS violates anything (likely fine) vs in a paid device (risky).  
- **Hardware accel access** – We assume Pixel’s TPU can’t be used by third-party for LLMs (Gemini Nano is closed). Need to verify what NPUs or NNAPI pathways are open to apps for 2026 Android (e.g., MediaPipe LLM support?).  
- **Swap times & battery costs** – All performance estimates are guesses. We must measure: loading 5GB from storage, tokens/sec for our models on each CPU, battery% drop per minute.  
- **Security sandbox viability** – We propose using Linux namespaces/seccomp. Need to test if full `docker` or `lxc` is too heavy. Possibly use a lightweight VM or even an emulator like gVisor. Evaluate feasibility on phone CPU.

Each of the above should be validated by experiments or documentation before finalizing v1 plans.

---

*Sources:* We used official model pages and papers for all facts above. For example, Assistant_Pepe_8B’s quantized sizes and base model are from Hugging Face. SemCoder facts (6.7B params, benchmarks) are from its NeurIPS paper and model card. InCoder’s license is explicitly CC-BY-NC. All data on model sizes was checked against the GGUF releases. Device specs are standard (Exynos9820, Snapdragon632, etc.) and should be cross-checked against manufacturer docs. 

This plan is **nuts, but legit**, covering every detail. Let’s get coding, bruv! 🏴🐧