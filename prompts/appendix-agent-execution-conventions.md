# Appendix P — Agent Execution Conventions (for the operator)

**Context:** Operating rules for running this plan. These apply across every phase file in `prompts/`.

1. **One step at a time.** Hand exactly one numbered Step to an agent; wait for its Exit criteria before moving to the next.
2. **Build the llama.cpp GGUF path first (§16.1 order):** common API + registry → llama.cpp both GGUFs → SonarBird ONNX → ONNX GenAI CodeBird then ChatBird → UI/toggles/matrix.
3. **Never invent hashes, commits or file sizes** — keep them as placeholders until the release pipeline populates them (§11.3).
4. **Keep model weights and binaries out of source control** (Appendix A). They come from the signed model store at runtime.
5. **Any P0/P1 regression must be closed before privileged PenGuru actions exist.**
6. **Record every decision, build pin, hash reference and device measurement as you go** for the release evidence (§15.3 / §17.2).

---

## Global constraints (all phases)

- **PenGuru stays chat-only** until Phase 0 P0/P1 fixes are closed and regression-tested — no privileged PenGuru action before that.
- Gates referenced map to the guide's `G0–G5` and Phase `0–7`.
- Target: Nuxel native (Fedora ARM64 userland on the phone, kernel 4.14.253).
- Host access: `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167` (root).

---

## Phase index

| Phase | File | Gate | Steps |
|-------|------|------|-------|
| 0 — Security & design freeze | `phase-0-security-and-design-freeze.md` | G0 | 1–7 |
| 1 — Dual-runtime spike | `phase-1-dual-runtime-spike.md` | G1, G2 signal, G3 signal | 8–15 |
| 2 — NuXAI platform core | `phase-2-platform-core.md` | G5 partial | 16–22 |
| 3 — Model Store + single modes | `phase-3-model-store-and-single-modes.md` | G5 partial | 23–28 |
| 4 — SonarBird + Squad | `phase-4-sonarbird-and-squad.md` | G5 partial | 29–33 |
| 5 — Read-only broker tools | `phase-5-read-only-broker-tools.md` | G5 partial | 34–35 |
| 6 — Safe writes + extension builder | `phase-6-safe-writes-and-extension-builder.md` | G5 partial | 36–38 |
| 7 — Hardening & pilot | `phase-7-hardening-and-pilot.md` | G5, G3, G4 | 39–44 |

---

### How to run

1. Start with **Phase 0** — do not skip; it gates all privileged work.
2. Open the next phase file only after its predecessor's completion checklist is fully checked off and exit gates are verified.
3. Each step file ends with a "proceed to →" pointer to the next phase.
4. Keep release evidence (decisions, pins, hashes-as-placeholders, device measurements) as you go for §15.3 / §17.2.

[ ] Appendix conventions acknowledged
