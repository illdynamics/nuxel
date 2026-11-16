# Phase 4 — SonarBird + Squad (Gate G5 partial)

**Context:** Build the two-tier Squad routing: Tier 0 deterministic rules, then Tier 1 MiniLM embeddings + Nuxel classifier. The headline security goal is **ZERO false SYSTEM dispatches**.

**Hard rule:** Zero false SYSTEM dispatch on the frozen adversarial set; wrong CHAT/CODE is a UX issue only.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 29 — Tier 0 deterministic rules engine (Gate G5 partial)

- **Goal:** Every Squad request runs deterministic rules first.
- **Files / locations:** Detection module (§7.3, §7.4).
- **Actions:** Implement detection for SYSTEM candidate (supported setting+verb+id), CODE candidate (fence/trace/source/compiler error), CHAT candidate (knowledge/chat cues); low specificity → ASK; no `requires_approval` field emitted.
- **Exit gate:** Rules produce constrained route labels + reason codes only.

[ ] Step 29 complete

---

## Step 30 — Tier 1 MiniLM embeddings + Nuxel classifier (Gate G5 partial)

- **Goal:** Standard ORT session after Tier 0; calibrated confidence.
- **Files / locations:** Completed SonarBird ONNX package (encoder+tokenizer+pooling+classifier).
- **Actions:** Complete SonarBird ONNX package; produce route reason + version; confidence buckets per §7.5 starting thresholds.
- **Exit gate:** Classifier runs and returns label+confidence+reason for Squad requests.

[ ] Step 30 complete

---

## Step 31 — Routing decision policy + ASK/override (Gate G5 partial)

- **Goal:** Clear CHAT/CODE → worker; SYSTEM only via known typed API; uncertain/high entropy → ASK.
- **Files / locations:** Routing policy + audit log.
- **Actions:** Implement confidence thresholds (experimental starts); override is user-only and visible (CHAT/CODE/ASK; no free-form SYSTEM); log label/scores/confidence/rule-id/version/override/outcome without retaining raw prompts by default.
- **Exit gate:** Squad routing works end-to-end with visible reason and ASK fallback.

[ ] Step 31 complete

---

## Step 32 — Build/freeze adversarial route test set (Gate G5 partial)

- **Goal:** Target ZERO false SYSTEM dispatches.
- **Files / locations:** Versioned labeled dataset; disjoint splits by intent family.
- **Actions:** Hundreds of labeled examples per class; measure macro-F1/precision/recall/calibration/confusion matrix/ASK rate/SYSTEM false-positive rate; freeze security test set.
- **Exit gate:** Zero false SYSTEM dispatch on the frozen set; wrong CHAT/CODE is a UX issue only.

[ ] Step 32 complete

---

## Step 33 — Squad mode end-to-end (Gate G5 partial)

- **Goal:** Request → SonarBird → route → worker/Supervisor/ASK.
- **Files / locations:** Full Squad lifecycle; runtime manager; memory/thermal budget checks.
- **Actions:** Wire full lifecycle: authenticate caller, session ownership, payload/queue/rate limits, store request record; SYSTEM via allowlisted typed capability through Supervisor; runtime manager picks installed variant and verifies memory/thermal budget before load.
- **Exit gate:** All four labels (CHAT/CODE/SYSTEM/ASK) work offline in Squad mode with visible route decisions.

[ ] Step 33 complete

---

### Phase 4 completion checklist

- [ ] All 5 steps done and exit gates verified
- [ ] Tier 0 deterministic rules produce constrained labels + reason codes only
- [ ] Tier 1 classifier returns label+confidence+reason
- [ ] Routing policy works with visible ASK fallback; no free-form SYSTEM override
- [ ] Adversarial test set frozen; ZERO false SYSTEM dispatch confirmed
- [ ] Squad mode end-to-end works offline for all four labels

> Proceed to Phase 5 only when complete.

[ ] Phase 4 complete → proceed to `phase-5-read-only-broker-tools.md`
