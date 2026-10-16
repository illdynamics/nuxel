# Touch pipeline — offline test results (this build group)

**Verdict: OFFLINE_TESTED.** No phone, no root, no `/dev/input`, no libinput and no
reboot was used. Nothing here is a claim about the hardware; it is a claim about the
tooling being correct, and it says exactly what it measured.

Reproduce everything with:

```sh
./tools/s10plus/a33/tests/run-touch-tests.sh          # all of it
./tools/s10plus/a33/tests/run-touch-tests.sh --quick  # skip the shim build
```

## 1. Suite summary

| Suite | Command | Result |
|---|---|---|
| shim build (host selftest + aarch64 `.so`) | `build-libinput-shim.sh --selftest` | **PASS** — selftest built; aarch64 `.so` builds clean with the cross compiler |
| libinput shim: capability fixtures | `tests/test-libinput-path-fixture.py` | **19/19 PASS** |
| libinput shim: A31/A33 parity | `tests/test-libinput-parity.py` | **6/6 PASS** (deployed copy byte-identical) |
| touch tracer: layers, gate, boundedness | `tests/test-touch-trace.py` | **all PASS** |
| boot-mode guard: LPM detection + gates | `tests/test-bootmode-guard.py` | **all PASS** |
| capture harness: `--commands`, machine gate, no repo litter | `tests/test-capture-harness.py` | **33/33 PASS** |
| no `/dev/input/eventN` literal | `tests/test-no-eventn-literal.py` | **26 files checked, 0 failing** |
| A32 baseline regression guard (optional cross-check, other group's file) | `tools/beta/regression-guard.sh --no-tests` | **PASS — 42 pass / 0 fail / 4 soft warn** (`REGRESSION GUARD: PASS — the A32 baseline is intact`) |

Total assertions printed by `run-touch-tests.sh`: **149 PASS, 0 FAIL** from the touch
suites (198 PASS including the parallel group's 49 regression-guard assertions).
`run-touch-tests.sh` exits 0 (`TOUCH-TESTS: ALL PASS`).

## 2. What the tracer tests actually assert

| Assertion | Why it matters |
|---|---|
| a fully-synthetic delivered bundle → all 7 layers `ok`, `FIRST_FAIL_LAYER=none`, `GATE=pass` | the gate can be satisfied, so a pass is meaningful |
| a bundle whose libinput step rejected the node → layer 4 `drop`, `FIRST_FAIL_LAYER=4` | the "first failing layer" contract is graded, not assumed |
| a bundle with no DOM evidence → layer 7 `blocked`, `FIRST_FAIL_LAYER=7` | the top hop is required for a pass |
| a charger/LPM bundle → layer 1 `blocked`, `FIRST_FAIL_LAYER=1`, verdict names the cause | the boot-mode gate is surfaced where it belongs |
| an **empty** bundle → all 7 `blocked`, `GATE=fail`, exit 3 | absence of evidence is never a pass |
| a **checklist line** mentioning `accepted=1` → layer 4 `blocked` | a shell command listing is not device output (honesty) |
| a **real state-file line** → layer 4 `ok` | the same tokens *in state-file form* are evidence |
| `--seconds 2 --dry-run` returns in 2.1 s with all 7 layer lines | the live console can never hang on the tracer |
| `--seconds 0` is refused | out-of-range budgets cannot run unbounded |
| `--stage-probe` runs and stages nothing on a host | layer 7 staging is safe where there is no launcher docroot |

## 3. Grading real archived captures (the briq's acceptance)

The analyzer was run against the captures that exist in this repository, with the
same rules a fresh bundle is graded by. Full per-layer output: see §7 of
`PIPELINE-TRACE.md`.

| Capture | L1 | L2 | L3 | L4 | L5 | L6 | L7 | FIRST_FAIL | exit |
|---|---|---|---|---|---|---|---|---|---|
| `scripts/s10plus-debug-pack/captures/…A17-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 | 3 |
| `…A18-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 | 3 |
| `…A19-live-run` | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 | 3 |
| `…A20-live-run` | **ok** | blocked | **ok** | blocked | blocked | blocked | blocked | 2 | 3 |
| `…A21-live-run` | **ok** | blocked | **ok** | blocked | blocked | blocked | blocked | 2 | 3 |
| `.scratch/beta` (42 files) | blocked | blocked | blocked | blocked | blocked | blocked | blocked | 1 | 3 |

Reading this honestly:

* `A20` and `A21` contain the kernel's own `input: sec_touchscreen as …` registration
  line, so layers 1 and 3 are `ok` and the pipeline is reported as stopping at layer 2
  (no `/proc/interrupts` delta existed in those collections); layers 4–7 were never
  captured there and are reported `blocked`, never `ok`.
* `A17`–`A19` have no readable `sec_ts` evidence in this form and are honestly
  all-`blocked`.
* `.scratch/beta` is a set of *shell command listings* rather than device output; it
  is reported as having no usable evidence. Grading it is what exposed the two
  evidence-discipline bugs described in §6 of `PIPELINE-TRACE.md`.

These captures are historical and predate the arm-on-open fix and the DOM probe, so
they cannot demonstrate layers 2 and 4–7. They are **grading fixtures**, not proof of
touch.

## 4. Hashes of the artifacts tested

```
ce372fe27019794a1fee867a9dfbb94fb51e405af6f0e512c7d624a80322244d  tools/s10plus/a33/nuxel-touch-trace.py
bb95e9fe04551ca70d31ef1155d4cb708439ff0acf4a8c7a0c2807ef299bdcef  tools/s10plus/a33/nuxel-touch-capture.sh
2da705762cad42962b00a1bffbb2658b2b770ea8570e0c5c38af8b3eb185d88e  tools/s10plus/a33/nuxel-bootmode-guard.py
aea597a1b6cb77a5e7af497a63a4900b59000498a8ccedf6d5998ae8371aad21  tools/s10plus/a33/touch-probe.html
f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f  tools/s10plus/a33/nuxel-libinput-path.c
f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f  tools/s10plus/a31/nuxel-libinput-path.c
667f7fadb7ee475e130688d884e116fc2de12512b03941242fbcb1f6399e300c  tools/s10plus/a33/build-libinput-shim.sh
7b087146e6bb15d546d8c6bb7fa81a4c70eeee3e8fc5ba6a64e83b6f1e021ee7  build/out/s10plus/a33/libnuxel-libinput-path.so
e3e6cd86a058e63720f5e5dd8c3c8eb702bb94d5f47b6c94f90936f846a6a6bf  build/out/s10plus/a33/nuxel-libinput-path-selftest
```

`build/out/s10plus/a33/libnuxel-libinput-path.so` is
`ELF 64-bit LSB shared object, ARM aarch64, dynamically linked` — confirmed with
`file` — built by `build-libinput-shim.sh` from the byte-identical A33/A31 source.
A31 and A33 hashes being equal is itself asserted by `tests/test-libinput-parity.py`,
so the things the tests validated are the things that would be deployed.

## 4a. Harness defects the new test found and fixed

`tests/test-capture-harness.py` (33 assertions) was written because the owner-test
harness was the one deliverable in this group with no automated coverage. Writing it
found two real defects, both fixed and both now regression-gated:

* **The bundle could be written inside the repository.** When the on-device default
  `/var/lib/nuxel/touch-capture/<ts>` is not writable (any development host, or a
  read-only `/var`) the old fallback was `./touch-capture-<ts>` — i.e. it littered the
  Nuxel source tree with capture bundles, which is exactly what a repository-first,
  no-scratch-in-the-repo mission forbids. The fallback is now `${TMPDIR:-/tmp}` and the
  test asserts a default-path run creates nothing under the repo root or the CWD.
* **An explicit unwritable `--out` was silently ignored.** The operator's `--out` fell
  into the same fallback, so `BUNDLE=` would name one directory while the evidence was
  written to another. An explicit `--out` that cannot be created is now a hard
  `CAPTURE_GATE=BLOCKED reason=out-dir-unwritable` with exit 71.
* (Also corrected: the printed owner command set named the *checkout* tracer path
  `tools/s10plus/a33/nuxel-touch-trace.py`, which does not exist on the device. It now
  gives the installed `/usr/libexec/nuxel/nuxel-touch-trace.py`, with the checkout path
  only as a comment.)

The same test locks down the honesty rules that must not drift: `CAPTURE_GATE=PASS`
can only come from `gate.json` `pass:true`; an empty capture is `FAIL` and the verdict
is `NEEDS_OWNER_TEST`; `--commands` arms nothing and creates no bundle.

## 5. What was NOT tested, and must not be claimed from this document

* **No physical touch.** No finger touched the glass in this cycle. The end-to-end
  gate PASS path is exercised only with synthetic raw events and a synthetic DOM log.
* **No live capture.** `--live` was run in `--dry-run` on a workstation; layers 1–7
  are `blocked` there because there is no phone. That is the correct output, not a
  failure.
* **No reboot.** The boot-mode guard's reboot decision was exercised with
  `--print-only`, with fixture evidence, and through the pure decision function; no
  reboot command was executed anywhere.
* **No deploy.** The aarch64 `.so` was built but not installed on any device; the
  kernel patch was not applied.

## 6. Terminal verdicts

| Item | Verdict |
|---|---|
| tracer / harness / DOM probe / shim / guard / tests | **OFFLINE_TESTED** |
| A32 baseline | **not regressed** (regression guard PASS, 0 fail) |
| charger/LPM userspace mitigation | **OFFLINE_TESTED** (live effect needs a normal reboot) |
| permanent LPM fix (kernel) | **BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED** |
| touchscreen finger test | **NEEDS_OWNER_TEST** |
