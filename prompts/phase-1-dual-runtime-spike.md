# Phase 1 — Dual-Runtime Spike (Gate G1 & G2 signal)

**Context:** Build one runtime end-to-end before making two engines parallel (guide §16.1). This phase pins and builds the inference runtimes (llama.cpp GGUF + ONNX Runtime) on target, then captures device memory baselines.

**Hard rules:**
- Keep model weights / binaries OUT of source control — they come from the signed model store at runtime.
- Never invent hashes, commits or file sizes; keep them as placeholders until the release pipeline populates them (§11.3).
- Prefer building the llama.cpp GGUF path first (§16.1 order).

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 8 — Pin and build llama.cpp ARM64 from immutable commit (Gate G1)

- **Goal:** Reproducible pinned llama.cpp for the supplied GGUFs (§5.3).
- **Files / locations:** Build environment on target; artifact + SBOM outputs.
- **Actions:** Pick an immutable git commit; build ARM64 with CMake flags recorded; capture source commit, compiler, linked backends, SBOM, binary hash; NEON-capable CPU kernels baseline only.
- **Exit gate (G1):** Pinned commit + artifact hash recorded; `libllama` builds on the device.

[ ] Step 8 complete

---

## Step 9 — Load ChatBird GGUF in llama.cpp with correct template (Gate G1)

- **Goal:** Load `Impish_LLAMA_4B_Abliterated-Q4_K_M.gguf` (§6.1) end-to-end.
- **Files / locations:** ChatBird GGUF artifact.
- **Actions:** Use exact GGUF metadata/chat template, tokenizer BOS/EOS, stop sequences; run load-time self-tests (metadata parse, arch id, template presence, tokenizer sanity, short generation, clean cancellation).
- **Exit gate (G1):** ChatBird loads and generates a bounded response; templates correct for Llama family.

[ ] Step 9 complete

---

## Step 10 — Load CodeBird GGUF in llama.cpp with correct template (Gate G1)

- **Goal:** Load `Qwen3.8-4B-Q4_K_M.gguf` (§6.1); needs recent Qwen3.5/Gated DeltaNet-capable build.
- **Files / locations:** CodeBird GGUF artifact.
- **Actions:** Same self-test suite; verify Qwen3.5 template (do NOT use Llama template for Qwen).
- **Exit gate (G1):** CodeBird loads and generates; correct Qwen template applied.

[ ] Step 10 complete

---

## Step 11 — Cancellation, memory release and no external TCP listener (Gate G1)

- **Goal:** Safe worker lifecycle (§5.3, §8.7).
- **Files / locations:** Worker process under test.
- **Actions:** Implement cancel/finish bounded generation on unload; confirm worker RSS falls below baseline after unload; ensure no general REST/TCP listener in the application path.
- **Exit gate (G1):** Cancellation works; RSS reclaimed; no loopback TCP server used by app path.

[ ] Step 11 complete

---

## Step 12 — Build/pin standard ONNX Runtime for SonarBird (Gate G2 signal)

- **Goal:** Standard ORT session for the MiniLM encoder + classifier (NOT GenAI).
- **Files / locations:** Pinned ONNX Runtime core ARM64; encoder+tokenizer+pooling+classifier head bundle.
- **Actions:** Pin ONNX Runtime core ARM64; assemble encoder+tokenizer+pooling+classifier head package; run its own accuracy tests.
- **Exit gate (G2 signal):** SonarBird classifier loads and passes accuracy tests with a complete bundle.

[ ] Step 12 complete

---

## Step 13 — Export candidate ONNX for CodeBird from Transformers checkpoint (Gate G2 signal)

- **Goal:** Build ONNX GenAI package from `empero-ai/Qwen3.8-4B-Distill` (NOT the GGUF).
- **Files / locations:** Transformers checkpoint export; outputs `genai_config.json`, graphs, external tensor shards, tokenizer/generation configs.
- **Actions:** Pin ONNX Runtime + GenAI compatibility set; use pinned model-builder version; record every builder option; bundle config/graphs/shards/tokenizers; test template/tokenizer parity vs source checkpoint.
- **Exit gate (G2 signal):** Export either passes parity+load or is recorded as unavailable; never convert the GGUF.

[ ] Step 13 complete

---

## Step 14 — Export candidate ONNX for ChatBird from Transformers checkpoint (Gate G2 signal)

- **Goal:** Build ONNX GenAI package from `SicariusSicariiStuff/Impish_LLAMA_4B_Abliterated`.
- **Files / locations:** Transformers checkpoint export.
- **Actions:** Same process; verify parity and ARM64 load path.
- **Exit gate (G2 signal):** Passes or recorded unavailable; license/provenance conflict flagged for legal review (§6.1).

[ ] Step 14 complete

---

## Step 15 — Capture device memory baselines on target SKU (Gate G3 signal)

- **Goal:** Establish usable-RAM baseline before building scheduler logic (§8.4).
- **Files / locations:** Target SKU device; measurement outputs.
- **Actions:** Measure OS+compositor reserve, foreground app reserve, NuXAI overhead; record per-model cold load and peak RSS candidate.
- **Exit gate (G3 signal):** Baseline numbers captured for the target SKU.

[ ] Step 15 complete

---

### Phase 1 completion checklist

- [ ] All 8 steps done and exit gates verified
- [ ] llama.cpp pinned + both GGUFs load through self-tests (G1)
- [ ] SonarBird standard ORT passes accuracy tests (G2 signal)
- [ ] ONNX GenAI exports for CodeBird & ChatBird pass/recorded unavailable (G2 signal)
- [ ] Memory baselines captured for target SKU (G3 signal)
- [ ] No hashes/commits/sizes invented — placeholders used until release pipeline populates them

> Proceed to Phase 2 only when complete.

[ ] Phase 1 complete → proceed to `phase-2-platform-core.md`
