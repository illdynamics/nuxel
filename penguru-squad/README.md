# PenGuru / NuXAI — Phase Prompts

This directory splits [`../penguru-plan.md`](../penguru-plan.md) into **one prompt file per phase**, so each step can be handed to an agent individually.

**Guide reference:** DUAL-RUNTIME IMPLEMENTATION GUIDE v1.1 (9 Nov 2026). Gates G0–G5; Phases 0–7.

## Files

| File | Phase | Steps |
|------|-------|-------|
| `README.md` | index (this file) | — |
| `phase-0-security-and-design-freeze.md` | 0 — Security & design freeze | 1–7 |
| `phase-1-dual-runtime-spike.md` | 1 — Dual-runtime spike | 8–15 |
| `phase-2-platform-core.md` | 2 — NuXAI platform core | 16–22 |
| `phase-3-model-store-and-single-modes.md` | 3 — Model Store + single modes | 23–28 |
| `phase-4-sonarbird-and-squad.md` | 4 — SonarBird + Squad | 29–33 |
| `phase-5-read-only-broker-tools.md` | 5 — Read-only broker tools | 34–35 |
| `phase-6-safe-writes-and-extension-builder.md` | 6 — Safe writes + extension builder | 36–38 |
| `phase-7-hardening-and-pilot.md` | 7 — Hardening & pilot | 39–44 |
| `appendix-agent-execution-conventions.md` | Appendix P — conventions | (global) |

## How to use each file

- Each numbered step is formatted as an **agent prompt**: Goal / Files·locations / Actions / Exit gate.
- Execute exactly one step, verify its **Exit gate**, then tick `[ ] Step N complete`.
- Each phase ends with a **completion checklist** and a pointer to the next phase.
- **Hard rule:** PenGuru stays chat-only until Phase 0 (P0/P1) is closed and regression-tested — no privileged action before then.

Run in order: Phase 0 → 1 → … → 7, following `appendix-agent-execution-conventions.md`.
