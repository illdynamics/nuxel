# Phase 5 — Read-Only Broker Tools (Gate G5 partial)

**Context:** Expose read-only diagnostics and the full D-Bus control-plane method surface over authenticated, typed capabilities. No free-form shell; P0/P1 paths stay closed.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving on.

---

## Step 34 — Typed read-only diagnostics via Supervisor/broker (Gate G5 partial)

- **Goal:** Battery level, device identity, service status, documented diagnostics over authenticated typed capabilities.
- **Files / locations:** Read-only action definitions; compiled allowlist + canonical registry (§10, §9.5).
- **Actions:** Implement read-only actions validated against compiled allowlist + canonical registry; no free-form shell; redact tokens/paths/secrets from diagnostics by default.
- **Exit gate:** Read-only device status is reliable; P0/P1 paths remain closed.

[ ] Step 34 complete

---

## Step 35 — D-Bus method surface for control plane (Gate G5 partial)

- **Goal:** Expose the full control-plane D-Bus interface (§14.3).
- **Files / locations:** `org.nuxel.PenGuru1` D-Bus methods.
- **Actions:** Implement these methods with signatures and rules from §14.3:
  - `GetStatus`, `SetEnabled`, `SetMode`, `SetRuntimePreference`, `SubmitRequest`, `GetRequest`, `CancelRequest`, `OverrideRoute`, `ListModels`, `StartDownload`, `CancelDownload`, `DeleteModel`, `ListApprovals`, `DecideApproval`, `RollbackAction`, `GetDiagnostics`.
  - Reject incompatible runtime prefs with reason (no silent fallback); approvals bound to payload hash/target/capability/session/expiry.
- **Exit gate:** Methods behave per contract; tests cover forged/replayed/expired identities.

[ ] Step 35 complete

---

### Phase 5 completion checklist

- [ ] All 2 steps done and exit gates verified
- [ ] Read-only diagnostics work over typed capabilities; secrets redacted by default
- [ ] P0/P1 paths remain closed after adding tools
- [ ] Full D-Bus control-plane surface implemented per §14.3
- [ ] Tests cover forged/replayed/expired identities for the methods

> Proceed to Phase 6 only when complete.

[ ] Phase 5 complete → proceed to `phase-6-safe-writes-and-extension-builder.md`
