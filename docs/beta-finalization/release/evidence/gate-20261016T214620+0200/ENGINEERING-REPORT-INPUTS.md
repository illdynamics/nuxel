# Engineering-report inputs — pre-existing red gate (briq-02-gate-failure-repair)

**briQ:** `briq-02-gate-failure-repair` (bg-00-preflight, cycle 7) — device-free.
**Bundle:** `docs/beta-finalization/release/evidence/gate-20261016T214620+0200/`
**Machine-readable:** `RAW-VERDICTS.json` (pre/post state, per-failure root cause and
class, the sha256 of every file this pass touched, and the explicit statement that
nothing in this bundle is a device claim).

## 1. Why this bundle exists

`build/reports/beta-tests/summary.json` (2026-10-16T21:11:37+0200, `git_head`
`466551c`) reported `gate=red`, `verdict=OFFLINE_TESTED_FAIL`, `raw_fail_count=11`,
with **6 hard failures owned by bg-00-preflight** (`U-workqueue-schema`,
`U-workqueue-unit`, `U-regression-guard-selftest`, `U-baseline-regression-guard`,
`U-baseline-a32-suite`, `U-boot-s10plus-gates`), 5 cross-group allowances and 7
warnings.  `build/` is gitignored, so the raw summary and all six failing logs were
copied into `pre-repair/` **before any edit** — a gate that goes green may not also
erase what it looked like when it was red.

## 2. The six hard failures, raw verdict → what happened

| Suite | Raw verdict (verbatim, pre-repair) | Class | Outcome |
|---|---|---|---|
| `U-workqueue-schema` | `FAIL rc=1`, 37 schema errors | repository defect (tool + one record) | **fixed** — schema vocabulary/evidence-shape repaired; `briq-04c`'s invented verdict normalised by an appended revision |
| `U-workqueue-unit` | `FAIL rc=1`, 1 failing case ("real queue invalid") | same | **fixed** — 44 passing / 0 failing now, with 4 new cases |
| `U-regression-guard-selftest` | `FAIL rc=1`, 1 failing case ("real repository gate is not green") | consequence of the two below | **fixed**, and hardened with 2 new precedence cases (13 passing / 0 failing) |
| `U-baseline-regression-guard` | `FAIL rc=1`, 4 FAILs (`hard-pinned file changed` ×3 **for files whose own register entry says `hash_mode: soft`**, + `WORK-QUEUE.md … render --check`) | repository defect (guard) + stale ledger view | **fixed** — per-file `hash_mode` now wins; ledger re-rendered. **No pin moved, no assertion relaxed** |
| `U-baseline-a32-suite` | `FAIL rc=1`, 1 failing suite (`FAIL colour conversion (build the a32 binaries first)`) | host limitation reported as a code regression | **fixed** — colour leg now implements the two channels `BASELINE-PROTECTION.md` §9.3 / INV-2 already describe; the aarch64 channel reports a printed, counted **WARN**; the source-level golden-bytes test still gates hard |
| `U-boot-s10plus-gates` | `FAIL rc=1`, `cannot unpack the hardware-proven A5 base` (suite never reached an assertion) | repository defect (reporting) + missing gitignored artefact | **reporting fixed**; the gate itself **did NOT run** → now `SKIP` (exit 3 `SKIP-PREREQ` by hand, `probe:`-gated in the registry), **not a pass** |

Every fix is locked by a test or a gate: the guard's precedence rule by self-test
cases 2b/2c, the evidence shapes by four new `test_workqueue.py` cases, the A5
fixture identity by a sha256 assertion inside the boot suite, and the render
contract by INV-10's `render --check`.

## 3. What is explicitly NOT claimed (raw, not softened)

* **`U-boot-s10plus-gates` is SKIP — the boot-image gate has not been proven here.**
  The two containers it needs are hardware-proven and gitignored; a synthesised
  substitute would prove nothing, so none was made.  Rebuild them and the suite
  gates hard again.
* **The aarch64 colour selftest is unrun.**  This host has no aarch64 execution
  channel (§9.3: no cross-gcc, no `qemu-aarch64-static`, no binfmt handler, no
  reachable UTM guest), so INV-2's binary assertion stays a **WARN** and the A32
  suite's channel (a) stays a **WARN**.  The conversion is gated **only** by the
  source-level golden-bytes test.
* **The raw gate is still `red` under `--strict`**: `raw_fail_count=5`, the
  documented in-flight cross-group allowances for `bg-05-security-permissions`,
  `bg-06-core-phone-apps` and `bg-07-specialty-apps` (their queue records are still
  unfinished, so their failures are reported as WARN *and preserved verbatim* in
  `allowances_applied`).  They are **not** passes, they were **not** fixed here
  (other groups own those surfaces this run), and the terminal integration pass must
  re-run with `--strict`.
* **`SKIP` and `WARN` are never passes** in the committed summary: the 4 SKIPs
  (two legacy A27 gates, `U-nuxtore-pwa`, `U-boot-s10plus-gates`) and the 7 WARNs
  are listed by id in `RAW-VERDICTS.json`.
* **Nothing here is a hardware claim.**  No phone was touched, no on-device
  artefact was produced, and no verdict was promoted: the green gate is
  `OFFLINE_TESTED`, exactly the ceiling `BASELINE-PROTECTION.md` §11 recorded.

## 4. Ordering constraint (for the terminal integration pass)

The verdicts that need a real device land in other briQs (`briq-10a/10b/10c`, owned
by the live-phone group; this pass deliberately did not touch those records or
`tools/beta/live/**`).  The final raw gate state must therefore be produced **after**
those records land, with `tools/beta/run-all-tests.sh --strict`, in the integration
briQ — the pre-repair red and the post-repair raw red are both preserved here so the
comparison stays possible.
