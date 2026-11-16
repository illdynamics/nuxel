# PenGuru Squad: ChatBird, CodeBird and SonarBird

**Goal:** A local AI subsystem for Nuxel with three roles:

- **ChatBird:** general chat and reasoning.
- **CodeBird:** code, scripts, debugging and extension building.
- **SonarBird:** the listener and decision maker. It classifies each request and starts the right model, or routes to a system tool.

**Modes:**
1. **Single ChatBird** (ad-hoc, only ChatBird runs)
2. **Single CodeBird** (ad-hoc, only CodeBird runs)
3. **Squad** (SonarBird decides per request)

---

## 1. Repository audit (what exists today)

Checked against `nuxel-main__2_.zip` (7,541 files).

| Area | Present | Relevance to PenGuru |
|---|---|---|
| `services/nuxel-bridge` | D-Bus capability mediator | **Reuse as the permission broker** for system actions |
| `services/nuxel-portal` | Portal policy service | **Reuse for scoped file/system access** |
| `services/nuxel-session`, `nuxel-notifications` | Session and notifications | Hooks for approvals and status |
| `services/nuxel-console`, `nuxel-web`, `nuxel-animation` | Console, web host, animation | Possible UI surfaces |
| PWA `terminal`, `rootcontrol`, `devmgmt`, `settings`, `authenticator`, `penguinterface` | User-facing apps | Tool targets for PenGuru; `rootcontrol` must stay behind the broker |
| LLM, GGUF, llama.cpp, PenGuru code | **None** | Everything for the Squad is new |
| Memory budget docs | Partial (`MP4-PLAYBACK-PERFORMANCE.md`, `yolo7.md`) | **Not yet read for this plan.** Read before Phase 0 |

**Conclusion:** the broker and portal patterns already exist, so PenGuru should be an additional client of the existing capability model. It should not get direct root access.

---

## 2. Model selection

### 2.1 ChatBird and CodeBird (chosen by you)

| Role | Model | Notes |
|---|---|---|
| ChatBird | `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated`, `Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf` | Llama 3.1 Community License. The model card describes it as abliterated, with reported refusals around 3%. See safety notes in section 6. |
| CodeBird | `empero-ai/Qwen3.8-4B-Distill-GGUF`, `Qwen3.8-4B-Q4_K_M.gguf` | Apache-2.0 per the repo tags. Third-party distillation of a larger Qwen model. Verify provenance and checksum before shipping. |

Both are about 4B parameters, which fits the 4B tier from the PenGuru concept doc. Only one should be resident at a time on an 8 GB phone (see section 4.3). Q4_K_M files of this size are typically around 2.5 GB. **Confirm the exact file sizes from the Hugging Face file listing** before writing download UI.

### 2.2 SonarBird (recommendation)

**Recommendation: do not use a generative LLM for SonarBird.** A router only needs to output a label, and it must cost almost nothing while idle.

**Recommended stack, in tiers:**

| Tier | Component | Size (approx.) | When it runs |
|---|---|---|---|
| 0 | Rule engine (regex, keywords, file paths, code fences, system verbs) | < 1 MB | Every request, always |
| 1 | **Sentence-embedding classifier: `all-MiniLM-L6-v2`** (22M parameters, 6 layers) with a small logistic head over embeddings | ~25–30 MB quantized | Every request that the rules did not decide |
| 2 | Optional tiny generative router (e.g. Qwen2.5-0.5B-Instruct Q4, grammar-constrained to one label) | ~0.4 GB | Only when Tier 1 confidence is low and the device has RAM to spare |

**Why MiniLM first:** 22M parameters, a few milliseconds per request on a phone CPU, negligible battery, and a small resident footprint. It is well understood and easy to fine-tune on your own routing examples.

**Alternative if MiniLM is not accurate enough:** `bge-small-en-v1.5` (about 33M parameters). It is slightly heavier but usually a little more accurate.

**Verify before use:** the exact GGUF or ONNX source for the embedding model. I have not confirmed a specific GGUF repo for this in this plan, so SonarBird's download button should point to a repo you have checked.

**Listening model:** SonarBird does not need to "listen" to audio or to the screen all the time. The always-on part should be a request queue plus the Tier 0 rules, which cost essentially nothing. If voice wake is added later, use a dedicated wake-word engine (a few MB), not an LLM.

---

## 3. Routing logic (SonarBird)

```
request
  ↓
Tier 0 rules
  ├─ system verb or file/settings target  → SYSTEM route (Broker, see section 5)
  ├─ code fence / file ext / "fix this" / stack trace → CODE
  └─ otherwise → Tier 1 classifier
                   ├─ confidence ≥ 0.80 → chosen label
                   ├─ 0.55 ≤ confidence < 0.80 → Tier 2 (if available) else ask user
                   └─ confidence < 0.55 → ask user "chat or code?"
```

Labels: `CHAT`, `CODE`, `SYSTEM`, `ASK`.

**Rules for SYSTEM:** SonarBird may route to SYSTEM, but it never executes anything itself. Execution happens only through the broker, with user approval (section 5).

**Thresholds** are starting points and must be tuned with real logs during Phase 2.

---

## 4. Runtime architecture

### 4.1 Processes

- **PenGuru supervisor** (a Nuxel service, D-Bus name `org.nuxel.PenGuru`): owns model lifecycle, routing, and the broker client.
- **llama.cpp server** instances on a Unix socket, one per loaded model, started on demand.
- **SonarBird classifier** loaded in-process (small enough to stay resident).

### 4.2 Lifecycle

- Models load on first use and unload after an idle timeout (default 120 s, configurable).
- The UI shows which model is active and whether it is loading.
- Nothing starts at boot unless the user has enabled PenGuru (PenGuru defaults to OFF, per the concept doc).

### 4.3 Memory and swapping

- **Never keep both 4B models loaded together by default.** Two Q4 models plus KV cache and the Nuxel desktop stack would leave little headroom on an 8 GB device.
- In Squad mode, switching model means unloading one and loading the other. Expect a noticeable delay (seconds, depending on storage speed). Show that in the UI.
- Optional "keep warm" setting for the last-used model, off by default because it costs memory and battery.

### 4.4 CPU and thermal limits

- Start with 4 threads on the Exynos 9820. Tune in Phase 0.
- Cap max generated tokens per request and per session.
- Pause generation when the battery is low or the device is thermally throttled. Show the reason.

---

## 5. Permission broker and actions

PenGuru must not have unrestricted root.

- All system actions go through `nuxel-bridge` / `nuxel-portal` with explicit scopes.
- Each action shows a preview (what changes, what it touches) and requires approval.
- Generated code is untrusted: it runs in an isolated environment first, with unit tests where possible, and is only installed after approval.
- Every action is logged to an audit file the user can read.
- One-tap rollback for anything PenGuru installs or changes.

The model's output can propose actions, but it cannot grant itself permissions or bypass the approval step. Enforcement lives in the broker.

---

## 6. Safety notes

1. **ChatBird is an abliterated model.** Its own card reports reduced refusals. Because PenGuru can propose system changes, safety must not depend on the model refusing things. The broker, scopes and approval prompts are the real controls.
2. **Recommended:** keep ChatBird out of the SYSTEM path entirely. SYSTEM requests go to the broker through the rules and the classifier, not through free-form chat output.
3. **Consider** offering a non-abliterated chat model as the default, with ChatBird as an explicit opt-in. This is your product decision.
4. **Provenance:** verify the CodeBird repo, its license and file hashes. Store SHA-256 for every model and check on download.
5. **Licenses:** show the Llama 3.1 Community License for ChatBird in the UI and keep the license text in the repo.
6. **Privacy:** no prompt, log or model output leaves the device by default. Network use is off unless the user enables it.

---

## 7. Download buttons (three models)

Each button:
- downloads from the Hugging Face `resolve/main` URL,
- supports resume,
- checks free disk space first,
- verifies SHA-256 after download (hash stored in the repo, not fetched at runtime),
- shows size, license and source repo before starting,
- can be deleted from the same screen.

| Button | Source | Status |
|---|---|---|
| ChatBird | `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated`, Q4_K_M | Repo and file confirmed to exist |
| CodeBird | `empero-ai/Qwen3.8-4B-Distill-GGUF`, Q4_K_M | Repo and file confirmed to exist. Verify hash and provenance |
| SonarBird | Embedding classifier (MiniLM class, GGUF or ONNX) | **Source to be confirmed** before the button is wired up |

---

## 8. Phased plan

### Phase 0: Hardware benchmark (gate for everything else)
- Run each model on the S10+ with llama.cpp (ARM64 build, CPU only).
- Measure: load time, tokens/s, resident memory, temperature, battery use per 100 short requests, behaviour under low memory.
- **Go/no-go:** if a 4B model cannot hold useful speed without swapping the desktop out, drop to a 1.5–2B model for ChatBird/CodeBird and report it honestly.

### Phase 1: Single-model modes
- Supervisor, model download buttons, load/unload, a chat UI with a model selector.
- Single ChatBird and single CodeBird modes working end-to-end.

### Phase 2: SonarBird classifier
- Tier 0 rules.
- Tier 1 MiniLM-class classifier. Collect labelled examples (aim for a few hundred per label to start).
- Log routing decisions and confidence for tuning. Keep logs local.

### Phase 3: Squad orchestration
- SonarBird routes CHAT/CODE/ASK. The supervisor loads and unloads models accordingly.
- Show the routing reason in the UI ("Routed to CodeBird: contains a stack trace").
- The user can override a route.

### Phase 4: Broker-backed actions
- SYSTEM route through `nuxel-bridge` / `nuxel-portal`.
- Approval UI, audit log, rollback.
- Start with the five operations from the PenGuru concept doc: system health, settings changes, file management, scheduled local actions, service failure diagnosis.

### Phase 5: Self-extension (later)
- Isolated feature builder, tests, sandboxing, supervised install.

---

## 9. Acceptance criteria

- Each mode works with the device offline.
- Idle PenGuru (SonarBird resident, no model loaded) adds negligible battery drain over a measured baseline over 24 hours. Measure, don't assume.
- No model output can execute a system action without an approval step.
- Every downloaded model passes hash verification.
- Routing decisions are visible to the user and can be overridden.
- Disabling PenGuru stops all its processes and frees its memory.

---

## 10. Open decisions for you

1. Default chat model: keep ChatBird (abliterated) as default, or make it opt-in?
2. Is 4B practical on your S10+? Phase 0 answers this. Fall back to 1.5–2B if not.
3. SonarBird source: confirm the embedding model repo before wiring its download.
4. Routing data: label your own examples, or start with synthetic examples and refine from real use?

---

## 11. Notes on the research brief

This document can be given to a deep-research assistant as a brief. Ask it to verify, on the actual Hugging Face pages: exact GGUF file sizes, licenses, and hashes for all three models, and current llama.cpp ARM64 performance notes for Exynos-class CPUs. Treat any figure here that is not confirmed on those pages as an estimate until the Phase 0 benchmark replaces it.
