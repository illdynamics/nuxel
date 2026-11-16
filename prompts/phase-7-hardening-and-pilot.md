# Phase 7 — Hardening & Pilot (Gate G5, G3)

**Context:** Execute the full test matrix, capture real device measurements, harden privacy/offline/power, then sign off acceptance criteria and ship. Finally run an opt-in pilot on the primary SKU before enabling secondary devices.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 39 — Full test matrix execution (Gate G5)

- **Goal:** Run every required test area.
- **Files / locations:** Entire codebase + test suites; model artifacts; sandbox; permissions; privacy/offline; device health; rollback.
- **Actions:** Cover: model artifacts; llama.cpp; ONNX GenAI; SonarBird; modes; runtime selector; Supervisor; permissions; sandbox; privacy/offline; device health; rollback. Fix failures with regression tests.
- **Exit gate:** Test matrix passes; coverage documented.

[ ] Step 39 complete

---

## Step 40 — Device measurement protocol (Gate G3)

- **Goal:** Real performance/power evidence on exact SKU.
- **Files / locations:** Target SKU device; raw logs/scripts (§15.3 format).
- **Actions:** ≥3 cold starts per model/runtime; TTFT; prompt/decode tokens/s; peak RSS/PSS; temperature/throttling; battery; UI responsiveness; suspend/resume; leak test; low-memory + foreground app conditions; cancellation/unload loops. Publish raw logs/scripts (no guessed TPS in notes).
- **Exit gate (G3):** Benchmark records follow §15.3 format with real values per device/SKU/build.

[ ] Step 40 complete

---

## Step 41 — Privacy, offline & power hardening (Gate G5)

- **Goal:** Offline-first, no telemetry, local retention controls.
- **Files / locations:** Runtime network policy; download process; conversation storage/metadata; microphone/wake-word config (§13, §13.1).
- **Actions:** Airplane-mode inference after install; worker network denied by default; downloads via separate user-started process; per-conversation deletion/clear-all/retention/redaction; microphone off by default, no wake-word at boot (§13.1).
- **Exit gate:** Offline operation verified for all three modes; telemetry absent; privacy controls functional.

[ ] Step 41 complete

---

## Step 42 — Acceptance criteria sign-off (Gate G5)

- **Goal:** Confirm every bullet in §15.2.
- **Files / locations:** §15.2 acceptance checklist; evidence per criterion.
- **Actions:** Walk each acceptance criterion with evidence: defaults OFF stops daemons and releases memory; all three modes offline; single modes bypass SonarBird; runtime selection works; one-worker resident; signed manifests; no model output executes system action without typed path; zero false SYSTEM; rollback tested; performance claims tied to named test record.
- **Exit gate:** All §15.2 criteria pass with recorded evidence.

[ ] Step 42 complete

---

## Step 43 — Packaging, signatures, update/rollback + release docs (Gate G4)

- **Goal:** Ship-ready artifacts and user docs.
- **Files / locations:** Signed manifests; release-key trust root; update/rollback pipeline; packaging for target image; user docs (§17.2).
- **Actions:** Sign manifests; embed release-key trust root; update/rollback pipeline; accessibility; packaging for target image; user doc states exact supported devices, runtimes and limitations.
- **Exit gate (G4):** Signed immutable manifests; docs state supported devices/runtimes/limitations.

[ ] Step 43 complete

---

## Step 44 — Opt-in pilot on primary device (Gate G5)

- **Goal:** Real-world pilot before secondary-device enablement.
- **Files / locations:** Primary SKU device; opt-in feature flag (§16).
- **Actions:** Enable feature opt-in on the primary SKU only; monitor thermal/battery; collect issues; secondary devices enabled only after exact profiles pass.
- **Exit gate:** Pilot passes on primary device; secondary enables only after profile validation.

[ ] Step 44 complete

---

### Phase 7 completion checklist

- [ ] All 6 steps done and exit gates verified
- [ ] Full test matrix passes with documented coverage
- [ ] Device measurements captured per §15.3 (real values, no guessed TPS)
- [ ] Offline operation verified for all three modes; telemetry absent
- [ ] All §15.2 acceptance criteria pass with recorded evidence
- [ ] Signed manifests + user docs state supported devices/runtimes/limitations (G4)
- [ ] Pilot passes on primary device before secondary enablement

> This is the final phase. Proceed to Appendix P conventions once complete.

[ ] Phase 7 complete → proceed to `appendix-agent-execution-conventions.md`
