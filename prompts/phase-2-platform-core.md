# Phase 2 — NuXAI Platform Core (Gate G5 partial)

**Context:** Same API drives both backends (§4.1, §5.2). Build the common InferenceRuntime contract, the unprivileged control-plane daemon, adapters for both runtimes, the runtime selector, worker manager and systemd hardening.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 16 — Define common InferenceRuntime contract + schemas

- **Goal:** Stable versioned interface (§5.2).
- **Files / locations:** `InferenceRuntime` contract; request/route/action JSON schemas under `schemas/`.
- **Actions:** Author `InferenceRuntime` probe/load/generate/cancel/health/unload/info; `RuntimeProfile {engine, package_format, provider, threads, context_limit,...}`; request/route/action JSON schemas. Keep it a contract, adapted to Nuxel language/build.
- **Exit gate:** Contract + schema files land and are validated in CI.

[ ] Step 16 complete

---

## Step 17 — Implement NuXAI control-plane daemon (unprivileged)

- **Goal:** Mode controller + request queue (SQLite) + routing facade (§4.1, §8.1).
- **Files / locations:** `services/nuxel-penguru/daemon`; runs as unprivileged `nuxel-penguru` service; D-Bus name `org.nuxel.PenGuru1`.
- **Actions:** Create daemon as unprivileged `nuxel-penguru` service; implement mode state machine, SQLite request queue, D-Bus method skeletons (`org.nuxel.PenGuru1`).
- **Exit gate:** Daemon starts under the dedicated account; status endpoint responds.

[ ] Step 17 complete

---

## Step 18 — Implement llama.cpp adapter (GGUF) behind common API

- **Goal:** Wire pinned llama.cpp to `InferenceRuntime` (§5.3).
- **Files / locations:** llama.cpp worker process; Unix peer credentials + FS permissions IPC path.
- **Actions:** In-process or tightly sandboxed worker process via IPC over Unix peer credentials + FS permissions; no TCP listener; model-specific profiles per GGUF.
- **Exit gate:** Both GGUFs load through the common API in single mode.

[ ] Step 18 complete

---

## Step 19 — Implement ONNX Runtime GenAI adapter behind common API

- **Goal:** Versioned GenAI adapter (§5.4). Keep separate from standard ORT.
- **Files / locations:** Verified ONNX GenAI bundles.
- **Actions:** Adapter loads verified ONNX bundles; handles tokenizer/template, logits/sampling, KV-cache; fails closed on unsupported operator/provider/graph mismatch with specific status.
- **Exit gate:** Compatible ONNX package loads via common API; incompatible pairing is rejected (not silently converted).

[ ] Step 19 complete

---

## Step 20 — Implement runtime selector + compatibility resolver (§5.6)

- **Goal:** `resolve_backend()` returns explicit engine/provider/revision or `BACKEND_UNAVAILABLE`.
- **Files / locations:** Runtime selector / compatibility resolver logic.
- **Actions:** Enforce user preference as a constraint; AUTO picks highest-priority verified candidate allowed by policy; UI shows resolved engine+revision+provider before generation; no silent fallback mid-generation.
- **Exit gate:** Explicit selection requires a compatible verified artifact; mismatches report actionable status.

[ ] Step 20 complete

---

## Step 21 — Implement worker manager + one-heavy-model scheduler (§8)

- **Goal:** Demand-load workers, one resident by default (§8.3).
- **Files / locations:** Worker manager; memory budget model; battery/thermal states.
- **Actions:** Worker lifecycle state machine (DISABLED→IDLE→ROUTING→LOADING→ACTIVE→DRAINING→UNLOADING→ERROR); memory budget model; thread/context/batch limits honoring CPU topology; battery/thermal states.
- **Exit gate:** One worker resident by default; load/unload/cancel cycles do not leak significant memory.

[ ] Step 21 complete

---

## Step 22 — Systemd hardening profile for the daemon (§9.3)

- **Goal:** Start-line hardened unit (validate against actual systemd/kernel).
- **Files / locations:** systemd unit for `nuxel-penguru` daemon; downloader gets separate HTTPS access.
- **Actions:** Apply `User/Group=nuxel-penguru`, `NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome=read-only`, kernel protection directives, `ReadWritePaths=/var/lib/nuxel-penguru`, `RestrictAddressFamilies=AF_UNIX`; add MemoryMax/CPUQuota/TasksMax after measurements.
- **Exit gate:** Unit loads and runs hardened; build test asserts hardening directives present.

[ ] Step 22 complete

---

### Phase 2 completion checklist

- [ ] All 7 steps done and exit gates verified
- [ ] Common `InferenceRuntime` contract + schemas land, validated in CI
- [ ] Unprivileged control-plane daemon starts under `nuxel-penguru`; status responds
- [ ] llama.cpp (GGUF) + ONNX GenAI adapters load through common API
- [ ] Runtime selector returns explicit engine/revision or `BACKEND_UNAVAILABLE`
- [ ] One worker resident by default; no memory leaks
- [ ] Systemd unit hardened and build test asserts hardening directives

> Proceed to Phase 3 only when complete.

[ ] Phase 2 complete → proceed to `phase-3-model-store-and-single-modes.md`
