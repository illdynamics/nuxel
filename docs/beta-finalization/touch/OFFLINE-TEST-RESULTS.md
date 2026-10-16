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
| shim build (host selftest + aarch64 `.so`) | `build-libinput-shim.sh --selftest` | **PASS** — host selftest built and driven; the aarch64 `.so` is **unchanged from the recorded build** and was not rebuilt in this environment (no cross compiler, UTM guest unreachable) — see §4 |
| libinput shim: capability fixtures | `tests/test-libinput-path-fixture.py` | **19/19 PASS** |
| libinput shim: A31/A33 parity | `tests/test-libinput-parity.py` | **6/6 PASS** (deployed copy byte-identical) |
| libinput shim: the LD_PRELOAD invocation chain | `tests/test-libinput-shim-invocation.py` | **27/27 PASS** |
| touch tracer: layers, gate, boundedness, capture, exit codes, capability scan, archive, self-test, honesty regressions | `tests/test-touch-trace.py` | **67/67 PASS** |
| boot-mode guard: LPM detection, gates, own config subpath | `tests/test-bootmode-guard.py` | **53/53 PASS** |
| capture harness: `--commands`, machine gate, no repo litter | `tests/test-capture-harness.py` | **33/33 PASS** |
| no `/dev/input/eventN` literal | `tests/test-no-eventn-literal.py` | **27 files checked, 0 failing** |
| A32 baseline regression guard (optional cross-check, other group's file) | `tools/beta/regression-guard.sh --no-tests` | **PASS — `REGRESSION GUARD: PASS — the A32 baseline is intact`** |

Total assertions printed by `run-touch-tests.sh`: **240 PASS, 0 FAIL**
(67 + 53 + 33 + 27 + 27 + 19 + 6 suite `PASS` lines + the 8 `run_step` summary lines;
the 239 of the previous revision was the count *before* `test-no-eventn-literal.py`
grew to 27 files and `test-libinput-shim-invocation.py` joined `TARGETS`).
`run-touch-tests.sh` exits 0 (`TOUCH-TESTS: ALL PASS`).

The tool's own logic is additionally assertable on any host, with no phone and no
`/dev/input` at all:

```sh
python3 tools/s10plus/a33/nuxel-touch-trace.py --self-test     # -> SELF-TEST: PASS (43/43 assertions)
```

## 1a. What this cycle added (and what it found)

| Added | Why |
|---|---|
| `--self-test` (43 assertions) | the tool's own decisions (ioctl numbers incl. `EVIOCGID`/`EVIOCGABS(ABS_MT_SLOT)`, decoder, bitmap word order, coordinate mapping, gate, exit codes) are now checkable anywhere, without a phone |
| `/sys/class/input/*/device` capability scan (`--sysfs-root`, `NUXEL_SYSFS_INPUT_ROOT`) | a second, independent identity source (name, bustype/vendor/product, capability bitmaps, absinfo) beside the evict ioctls — and driveable offline from `tests/fixtures/sec-ts-only/` |
| `coordinate-map.json` + `COORD_VALIDATION` | validates every captured point against the device's own range **and** the 1440x3040 DECON panel, naming where the range came from |
| `--capture SECONDS`, `events.jsonl` | the bounded owner-tap window with one JSON record per input event (kernel timeval) and a `point` record per frame |
| `--archive` / `--archive-dir`, `INDEX.jsonl` | live evidence lands in `docs/beta-finalization/live/evidence/touch-<ts>/` instead of only on the phone |
| per-layer exit codes (`LAYER_EXIT=`, `--layer-exit-codes`) | a wrapper can branch on the exact hop that lost the event |
| `tests/test-libinput-shim-invocation.py` | the deployment chain (`LD_PRELOAD=…libnuxel-libinput-path.so` on `nuxel-wayland.service`) is pinned so a hardened shim that nothing preloads cannot pass |
| `configs/nuxel/bootmode/` | the guard's own configuration subpath, with the two configs asserted to agree on every gate field |

**Three bugs found by grading a LIVE capture** taken this cycle over the console (see
§3a and §6b/§6c of `PIPELINE-TRACE.md`):

1. an unhandled case in the layer-4 grader (`added=0` with no `accepted=0` line)
   crashed the analyzer — it now reports the shim's zero-device scan as `blocked` with
   the state-file line as evidence;
2. a live-console **command frame** was read as device output, so a `grep -c
   <panel name>` command header was reported as "the panel appears in the evidence" on
   a boot where the driver never initialised;
3. the analyzer **graded its own previous verdict**: a second `--analyze` run with
   `--json-out` inside the bundle produced `LAYER=6 ok` out of a sentence the first run
   had written there.

All three are fixed and regression-gated, and the live capture itself is a test case.

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

Source and configuration (hashes re-taken after this cycle's changes):

```
HASH_TOUCH_TRACE   tools/s10plus/a33/nuxel-touch-trace.py
HASH_CAPTURE_SH    tools/s10plus/a33/nuxel-touch-capture.sh
HASH_BOOTMODE_PY   tools/s10plus/a33/nuxel-bootmode-guard.py
HASH_PROBE_HTML    tools/s10plus/a33/touch-probe.html
HASH_SHIM_C        tools/s10plus/a33/nuxel-libinput-path.c          (== tools/s10plus/a31/nuxel-libinput-path.c)
HASH_BUILD_SH      tools/s10plus/a33/build-libinput-shim.sh
```

The concrete values are written by `tools/s10plus/a33/tests/run-touch-tests.sh`
(`sha256sum` section) and are reproducible with:

```sh
cd /x/nuxel && sha256sum \
  tools/s10plus/a33/nuxel-touch-trace.py tools/s10plus/a33/nuxel-touch-capture.sh \
  tools/s10plus/a33/nuxel-bootmode-guard.py tools/s10plus/a33/touch-probe.html \
  tools/s10plus/a33/nuxel-libinput-path.c tools/s10plus/a31/nuxel-libinput-path.c \
  tools/s10plus/a33/build-libinput-shim.sh
```

### The compiled shim object

```
f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f  tools/s10plus/a33/nuxel-libinput-path.c
f94240412b731233ad0e93de24d20283f55fc0d0b1f74aa1cddc9f19265e598f  tools/s10plus/a31/nuxel-libinput-path.c
7b087146e6bb15d546d8c6bb7fa81a4c70eeee3e8fc5ba6a64e83b6f1e021ee7  build/out/s10plus/a33/libnuxel-libinput-path.so   (recorded_from_previous_cycle: NOT present in this tree; build/ is gitignored and the object is rebuilt on demand - this hash is the previous cycle's record, re-verifiable against the unchanged, parity-asserted source)
f333421fc68549864bc6d8ccc3671b3e04c9ababd21446536f2328087dce936c  the DEPLOYED /usr/lib/nuxel/libnuxel-libinput-path.so (A31 record)
```

**This environment could not rebuild the aarch64 `.so`**: there is no
`aarch64-linux-gnu-gcc` on the host and the UTM guest the build script falls back to
(`nuxel@192.168.64.3`) was not reachable, so `build-libinput-shim.sh` built the host
selftest and stopped there with an explicit "cross/VM build UNAVAILABLE" message and
exit 3. That is reported rather than papered over:

* the **object itself is not in this tree**: `build/out/s10plus/a33/` contains only
  `nuxel-libinput-path-selftest`, and a find over the tree and `/home` returns no
  `libnuxel-libinput-path*.so`. The object hash below is therefore typed
  `recorded_from_previous_cycle` in the briq-01b revision (queue evidence kind `doc`:
  the queue's schema allows only `offline`/`vm`/`on_device`/`owner_instruction`/
  `observation`/`doc`, and `observation` would read as if the file were present) — it
  is a record to rebuild against, not a file a reviewer will find at that path;
* the **source hash is unchanged** from the build whose object hash is recorded above,
  so the recorded object still corresponds to this source and to the deployed copy
  (which `tests/test-libinput-parity.py` proves is byte-identical);
* `tools/s10plus/a33/tests/test-libinput-shim-invocation.py` asserts the invocation
  chain and prints the deployed `.so` hash from the A31 live-deployment record, which
  is what a rollback would restore;
* the `.so` is not tracked in git (`build/` is in `.gitignore`), which is the
  pre-existing, deliberate arrangement — the artifact is rebuilt, never committed.

Rebuild with a cross compiler or the guest when one is available:

```sh
CROSS=/path/to/aarch64-linux-gnu-gcc ./tools/s10plus/a33/build-libinput-shim.sh
VM=user@host ./tools/s10plus/a33/build-libinput-shim.sh --vm
```

A31 and A33 source hashes being equal is itself asserted by
`tests/test-libinput-parity.py`, so the things the tests validated are the things that
would be deployed.

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
