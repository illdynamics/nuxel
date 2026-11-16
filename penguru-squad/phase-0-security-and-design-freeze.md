# Phase 0 — Security & Design Freeze (Gate G0)

**Context:** PenGuru must remain **chat-only** until the P0/P1 security fixes in this phase are closed and regression-tested. No privileged PenGuru action exists before this phase passes.

**How to use:** Execute exactly one numbered step, then verify its Exit gate before moving to the next. Do not proceed to Phase 1 until all of Phase 0 is complete.

---

## Step 1 — Confirm target image, kernel and service/app IDs

- **Goal:** Establish the exact Nuxel image/kernel baseline and canonical identities used everywhere else.
- **Files / locations:** Host device (`ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`); `/var/lib/nuxel-penguru/queue.db`.
- **Actions:**
  - On host: `uname -r`, record full build/boot-chain; snapshot available RAM, CPU topology (`lscpu`), storage.
  - Confirm the initial native target image and first supported phone SKU (decision item §17.1).
  - Assign canonical IDs: service account `nuxel-penguru` / `nuxel-ai-worker`, D-Bus name `org.nuxel.PenGuru1`, app id for PenGuru, queue DB path `/var/lib/nuxel-penguru/queue.db`.
- **Exit gate:** One line each recorded: target image, kernel, SKU(s), service account names, D-Bus name, app id.

[ ] Step 1 complete

---

## Step 2 — Fix P0: root-owned HTTP bridge dev-mode auth (Gate G0)

- **Goal:** Remove the loopback no-token bypass and bind tokens to authenticated app identity.
- **Files / locations:** `services/nuxel-bridge/systemd/nuxel-http-bridge.service`, `services/nuxel-bridge/src/api.py` (`_verify_auth()`).
- **Observed (guide §2.3):** bridge runs as root, binds `127.0.0.1:8080`, sets `NUXEL_HTTP_MODE=dev`; `_verify_auth()` accepts loopback without a token in dev mode; unauthenticated bootstrap route accepts an app id and does not bind body identity to token identity.
- **Actions:**
  - Remove/neutralize the dev-mode loopback bypass; make production units fail the build if any env can enable it.
  - Bind every session token to a launcher-authenticated app identity; enforce `token.app_id == request.app_id` for every method.
  - Derive caller identity from trusted launcher / authenticated D-Bus peer credentials, NOT JSON body, Origin or Referer.
  - Add typed PenGuru broker surface over the canonical permission service instead of generic HTTP `/rpc`.
- **Exit gate:** Build fails if dev bypass is enabled; no loopback path accepts a request without a token.

[ ] Step 2 complete

---

## Step 3 — Add P0 tests: forged app_id, token replay across apps, identity mutation, missing launcher secret, untrusted loopback, unauthorized service control

- **Goal:** Prove the Step 2 fixes hold under hostile inputs.
- **Files / locations:** Bridge API test suite (`services/nuxel-bridge`).
- **Actions:** Write and run unit/integration tests for each scenario: forged app_id, token replay across apps, identity mutation, missing launcher secret, untrusted loopback, unauthorized service control.
- **Exit gate:** All new tests pass; none silently accept a forged/replayed/mutated identity.

[ ] Step 3 complete

---

## Step 4 — Fix P1: once/session grant cache semantics (Gate G0)

- **Goal:** Never cache a `once` grant as reusable; bind session grants to real sessions with expiry/revocation.
- **Files / locations:** `services/nuxel-bridge/src/bridge.py` (`_check_capability()`).
- **Observed (§2.4):** `_check_capability()` can return true from an in-memory cache before consulting the portal.
- **Actions:**
  - Consume `once` at the permission authority, bound to one immutable action/request ID (no reuse).
  - Bind `session` grants to a real session id with explicit expiry and revocation events.
  - Persist `always` only where policy permits; use monotonic time for in-process expiry.
- **Exit gate:** Bridge regression proves first `once` action succeeds, second fails within same daemon lifetime.

[ ] Step 4 complete

---

## Step 5 — Canonicalize capability registry (Gate G0)

- **Goal:** Eliminate the fourth independent capability definition (§2.5).
- **Files / locations:** `shell/nuxel-shell/nuxel-permissions/` (`capabilities.json`, `nuxel-permd.py`) — authoritative registry.
- **Actions:** Treat this registry as authoritative; generate bridge adapter schemas from it; deny unknown capability names; add PenGuru scopes there; add CI validation.
- **Exit gate:** No bridge-side or module-level duplicate registry; unknown capabilities are rejected in tests.

[ ] Step 5 complete

---

## Step 6 — Kernel sandbox reality check + Supervisor probe (Gate G0)

- **Goal:** Make the Sandbox reflect real kernel facts (§2.6, Linux 4.14.253).
- **Files / locations:** Target device runtime probe.
- **Actions:** Probe for Landlock/AppArmor/SELinux; if a sufficiently isolated code runner is unavailable, disable code execution and permit only patch review/export. Record effective isolation primitives (DAC, Linux caps, seccomp, systemd sandbox settings).
- **Exit gate:** Supervisor runtime-probes real features and reports which are effective on this device.

[ ] Step 6 complete

---

## Step 7 — Decide v1 scope anchors (decision items §17.1)

- **Goal:** Lock the open architectural decisions before Phase 1 exits.
- **Files / locations:** Signed decisions record (release evidence).
- **Actions & recorded decisions:**
  - Which exact Nuxel image/kernel + first supported SKU.
  - ChatBird default vs explicitly chosen low-refusal personality model (Supervisor stays safety boundary).
  - Who signs manifests + which release-key trust root is embedded in Nuxel.
  - First published ONNX export precision/provider per model.
  - Definition of a "supported" profile: context + battery/thermal budget.
  - LAN provider reserved for v2 (recommendation: yes, keep v1 fully local).
- **Exit gate:** A signed decisions record with the answers above.

[ ] Step 7 complete

---

### Phase 0 completion checklist

- [ ] All 7 steps done and exit gates verified
- [ ] P0/P1 fixes closed and regression-tested
- [ ] Canonical IDs recorded (service account, D-Bus name, app id, queue DB path)
- [ ] Signed decisions record in place
- [ ] PenGuru still chat-only — no privileged actions taken

> **Gate G0 must pass before any privileged PenGuru action.** Proceed to Phase 1 only when complete.

[ ] Phase 0 complete → proceed to `phase-1-dual-runtime-spike.md`
