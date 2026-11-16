# Phase 6 — Safe Writes + Extension Builder (Gate G5 partial)

**Context:** Enable model-initiated *writes* only through typed proposals, owner approval and staged install with rollback — all sandboxed on the active kernel. If isolation cannot be proven, disable code execution and return patch/export only (§2.6).

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 36 — Isolated code workspace + fixed test runner (Gate G5 partial)

- **Goal:** CodeBird writes only into a disposable, isolated workspace.
- **Files / locations:** Isolated test process; dedicated UID; seccomp + namespace/systemd restrictions; source deps (read-only where practical).
- **Actions:** Separate test process with resource limits, read-only source deps where practical, no network by default, dedicated UID, seccomp + namespace/systemd restrictions proven on active kernel; block symlink/path traversal; run fixed command catalogue (lint/test/build targets), not arbitrary model shell.
- **Exit gate:** Isolation verified on target kernel; if isolation cannot be proven, disable code execution and return patch/export only (§2.6).

[ ] Step 36 complete

---

## Step 37 — Typed proposals, approval hash + preview (Gate G5 partial)

- **Goal:** Model emits typed action objects (no shell strings); Supervisor builds immutable preview + approval hash.
- **Files / locations:** Typed proposal schema (§10.2); compiled allowlist; approval store keyed on crypto hash of payload+target+capability+expiry.
- **Actions:** Validate against fixed schema; resolve against compiled allowlist; unknown → deny; create preview with canonical payload/affected resources/capability/risk tier/tests/rollback; store owner approval against crypto hash of exact payload+target+capability+expiry; re-verify before execution; any payload change invalidates approval.
- **Exit gate:** Tampered/replayed/denied-capability tests fail closed.

[ ] Step 37 complete

---

## Step 38 — Staged install + rollback for supported writes (Gate G5 partial)

- **Goal:** Only supported operations can write; rollback where a tested mechanism exists.
- **Files / locations:** Diff/manifest previews; staged install; transaction/snapshot rollback (§10.4, §15.1).
- **Actions:** Diff/manifest previews, declared permissions, test evidence; staged install after owner approval; rollback only where transaction/snapshot is verified; never imply every action is reversible.
- **Exit gate:** Extension rollback + each supported settings/system action restore correctly after simulated failure (§15.1).

[ ] Step 38 complete

---

### Phase 6 completion checklist

- [ ] All 3 steps done and exit gates verified
- [ ] Isolated code workspace proven on target kernel (or disabled → patch/export only)
- [ ] Typed proposals + approval hash tamper/replay-proof
- [ ] Staged install + rollback restores supported actions after simulated failure
- [ ] Never implies every action is reversible

> Proceed to Phase 7 only when complete.

[ ] Phase 6 complete → proceed to `phase-7-hardening-and-pilot.md`
