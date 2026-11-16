# Phase 3 — Model Store + Single Modes (Gate G5 partial)

**Context:** Build the signed model registry, download/integrity pipeline, model cards, PWA registration, then wire up offline single-mode ChatBird and CodeBird end-to-end (both bypass SonarBird).

**Hard rules:**
- Never invent hashes, commits or file sizes; keep them as placeholders until the release pipeline populates them (§11.3).
- Keep model weights and binaries out of source control.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 23 — Model registry + signed immutable manifests (Gate G5 partial)

- **Goal:** Registry identity per model with separately verified package variants.
- **Files / locations:** Manifest schema (§11.3); example manifests.
- **Actions:** Author manifest schema; record source_repo, immutable revision, file list/sha256, format, arch, quantization, runtime profile, license; keep placeholders for hashes/sigs (do NOT invent them).
- **Exit gate:** Manifest schema validated; example manifests pass schema check with placeholder values.

[ ] Step 23 complete

---

## Step 24 — Download helper: resumable transfer + integrity pipeline (Gate G5 partial)

- **Goal:** User-started, signed, atomic install (§11.1/§11.2).
- **Files / locations:** Downloader process; `/var/lib/nuxel-penguru/models/<model-id>/<revision>/<variant>/`; quarantine area for corrupt/partial files.
- **Actions:** State machine NOT_INSTALLED→USER_CONFIRMED→…→SELF_TEST→READY; HTTPS resume/range/cancel/retry; verify signed manifest (trusted channel), SHA-256 per file, GGUF/ONNX metadata, arch, tokenizer, size; atomic move into place; quarantine+clean partial on failure.
- **Exit gate:** Downloads verify signatures/hashes and install atomically; corrupt/partial files are quarantined and removed.

[ ] Step 24 complete

---

## Step 25 — Three model cards in NuXtore/PenGuru (Gate G5 partial)

- **Goal:** ChatBird, CodeBird, SonarBird download cards.
- **Files / locations:** Model card UI components.
- **Actions:** Each card shows role/author/repo/exact variant/size/context/quant/backend-compat/licence/provenance/verification; per-model GGUF/ONNX variant switch only when both signed+approved; keep exactly three logical cards.
- **Exit gate:** Cards render with real package details; disabled until verification passes.

[ ] Step 25 complete

---

## Step 26 — Register PenGuru in PWA pipeline (Gate G5 partial)

- **Goal:** Canonical app registration via existing build/asset pipeline.
- **Files / locations:** `pwa/nuxel-common/app-registry.json`; `bridge.js` + `bridge-version.json`.
- **Actions:** Add PenGuru entry to `pwa/nuxel-common/app-registry.json`; build manifest through the asset pipeline; reuse `bridge.js` + `bridge-version.json`; validate schema changes in CI.
- **Exit gate:** PenGuru app registered; build test proves it is packaged.

[ ] Step 26 complete

---

## Step 27 — Single ChatBird end-to-end (offline, bypasses SonarBird) (Gate G5 partial)

- **Goal:** Every prompt → ChatBird directly.
- **Files / locations:** Offline chat worker path; Supervisor validation; capability broker; audit log.
- **Actions:** Direct worker path still runs Supervisor validation, capability broker, schema checks, audit; tool-like strings in output stay inert without a typed UI action.
- **Exit gate:** Offline single-chat works; hashes verified; one-worker policy holds.

[ ] Step 27 complete

---

## Step 28 — Single CodeBird end-to-end (offline, bypasses SonarBird) (Gate G5 partial)

- **Goal:** Every prompt → CodeBird directly.
- **Files / locations:** Offline code worker path; Nuxel-specific code tasks (§6.1).
- **Actions:** Same as Step 27 for code worker; benchmark on Nuxel-specific code tasks.
- **Exit gate:** Offline single-code works; hashes verified.

[ ] Step 28 complete

---

### Phase 3 completion checklist

- [ ] All 6 steps done and exit gates verified
- [ ] Manifest schema validated; example manifests use placeholder hashes/sigs
- [ ] Download helper verifies signatures/hashes and installs atomically
- [ ] Three model cards render with real package details, disabled until verified
- [ ] PenGuru registered in PWA pipeline; build test proves packaging
- [ ] Offline single ChatBird + CodeBird work end-to-end; one-worker policy holds

> Proceed to Phase 4 only when complete.

[ ] Phase 3 complete → proceed to `phase-4-sonarbird-and-squad.md`
