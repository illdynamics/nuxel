# NUXEL PROMPT — P08: Remaining Live Userspace and Hardware Integration

> **Status of THIS FILE:** it is a *prompt for a future implementation session*, not the implementation.
> Do **not** run the instructions in this file during authoring; this file only describes them.
> The future agent that consumes this prompt executes component **P08 — Remaining live userspace and hardware integration** on the branch `nuxel/p08-live-userspace-hardware-integration` of the Nuxel Fedora ARM64 phone OS repo (current HEAD `e2aaf66`, tag `v0.6.0-beta`).

---

## 0. Agent mission (this branch ONLY)

You are the Nuxel Fedora ARM64 phone OS engineering agent, working in a dedicated Git feature branch. Implement **only component P08: Remaining live userspace and hardware integration** in this existing repository. This file is the complete scope for the current run; **do not implement the other screenshot items or briq tasks in this branch.** Reuse actual Nuxel architecture and existing services instead of creating parallel or fake substitutes.

**Target platform:** Samsung Galaxy S10+ SM-G975F / Exynos 9820 (`beyond2lte`), Fedora Linux 43 aarch64, systemd PID 1, Samsung vendor kernel **4.14.253**, no Android framework dependencies. The display path is Phoc (headless) → Wayland screencopy → `/dev/fb0` DECON; there is **no** DRM/KMS (`/dev/dri` absent).

**Host/device split:** A MacBook host may build/test and run the offline suites. **The live phone may NOT be connected during this run.** Do not assume a hardware verification that did not happen — see §12 for the mock/host vs. live distinction, which is non-negotiable here.

### The P08 mission statement (verbatim)
1. Inventory userspace services against actual S10+ runtime capabilities.
2. Fix one verified integration gap at a time while preserving bootable system.
3. Track unavailable kernel/firmware capabilities separately.
4. Expose actionable diagnostics and non-blocking graceful degradation.

### P08 contract (verbatim)
- Inventory userspace services against actual S10+ runtime capabilities.
- Fix one verified integration gap at a time while preserving bootable system.
- Track unavailable kernel/firmware capabilities separately.
- Expose actionable diagnostics and non-blocking graceful degradation.

**This component is the *remaining* wiring**: haptics/vibration, flashlight/notification LED, power/battery/menu, sensors, NFC/Bluetooth/modem/SIM/microSD — each as a *repository-side* implementation with an honest verdict, plus the diagnostic surface that makes every gap observable and every unavailable capability trackable. Every subsystem below is already **seeded** in `docs/beta-finalization/workqueue/<stable-id>.json` (see §4) with its real state and verdict vocabulary — P08 does not invent new states; it advances whichever of these seeded tasks is the smallest *verified* next gap, or produces a precise blocker.

---

## 1. Hard boundaries for THIS run (authoring only)

- **You are authoring a prompt.** You may read repo files read-only to make the prompt concrete and repo-aware. You must **not** execute P08's implementation instructions yourself.
- For the *future* agent, these boundaries apply:
  - Do not modify Nuxel source/test/asset/config/service/device files as part of authoring — only create/update `PROMPT-P08.md`.
  - No build/install/run-test/deploy/ssh/usb/flash/reboot/touch-the-phone.
  - No recursive AI agent, no executing the finished prompt.
  - No new docs/branches/worktrees; no git add/commit/push/switch/merge/rebase (the outer runner owns Git).
  - No secrets/hostpaths/API tokens/private credentials in the prompt or any file you create.
  - Never claim implementation/deployment/hardware testing actually took place for *this authoring run*.

> The acceptance gates and workflow below are instructions **for the future agent**, not claims about this file's creation.

---

## 2. Verified facts vs. must-inspect (read-only audit of the real repo)

This section records what is **already true in the repository** at HEAD (`e2aaf66`) so the future agent builds on reality, not assumptions. Mark anything that changed since this authoring as `NOT_REAUDITED` and re-verify from source before touching it.

### 2.A Verified facts (observed in-tree now)

**Boot / containment (4.14 vendor kernel).** The S10+ runs a Samsung 4.14 tree with specific, *documented* work-arounds that P08 must preserve:
- `systemd-userdbd.{service,socket}` masked — pidfd child watching is `ENOSYS`.
- `nsswitch.conf` drops the `systemd` NSS module (a varlink lookup with no server blocks forever).
- System bus = **`dbus-daemon.service`**; `dbus-broker` is masked/unused.
- `systemd-udevd` + sockets masked; devtmpfs supplies nodes; libinput discovery goes through **`libnuxel-libinput-path.so`** (a path shim, not the real udev daemon).
- Carried patched `libsystemd-shared-258.11-1.fc43.so` from systemd `258.11-1.fc43`; the running systemd NEVRA is pinned to match. **Any P08 change that touches systemd units, NSS, or userdbd must be applied by the builder to the staging tree and must not break this pin.**

**Display path (proven offline).** Phoc headless + pixman → `nuxel-wl-fb` (the *only* `/dev/fb0` owner) with XRGB8888 → Samsung ABGR8888 colour conversion, proven at byte level. There is **no** `/dev/dri`. Single framebuffer ownership is enforced (`owner=nuxel-wl-fb`). P08 must never introduce a second fb0 writer or bypass the colour conversion when it touches anything that renders.

**Service graph (measured reality).** Canonical units live in `services/**` plus `images/s10plus/nuxel-firstlight.service`. Startup order and dependency matrix are captured in `docs/service-graph.md` and `docs/beta-finalization/system/SERVICE-GRAPH.md`. The offline validator is:
```sh
python3 tools/s10plus/a33/verify-service-graph.py          # expect verdict=OFFLINE_TESTED, problems=0
python3 tools/s10plus/a33/tests/test-service-graph.py       # must FAIL on an injected cycle / forbidden 4.14 dep / lost enablement
```
If P08 adds or reorders a unit (e.g., a haptics/LED bridge service), it **must** keep this green — that test proves the validator *rejects* exactly the regressions P08 could introduce.

**Button manager (A34, current).** `tools/s10plus/a34/nuxel-button-manager.c` (+ `nuxel-button-fsm.h`, FSM state machine) owns the `gpio_keys` key set: power menu, volume→ALSA beyond-madera mixer, screen gestures (swipe-up home / swipe-up-hold recents / edge-swipe back), reboot gated by policy file (refuses by default), Recovery/Download hard-refused. The A32 sources in `tools/s10plus/a32/` are **protected baseline** (`docs/beta-finalization/baseline-protection.json`, INV-4) and the offline test asserts behavioural parity with them — **do not touch a32.** Probe modes: `--probe --capture --menu-dump --fsm-sim <trace.json> --config-check`.

**Existing hardware-diag scaffolding that P08 can extend (not reinvent):**
- `tools/s10plus/a34/nuxel-uinput-touch-probe.py`, `tools/s10plus/a34/nuxel-usb-input-audit.sh` — input/USB discovery.
- `tools/s10plus/a33/nuxel-haptics-diag.sh` (referenced in manual-proof) enumerates haptic nodes; confirm whether it exists on disk and reuse it rather than writing a sibling.
- `nuxel-hwprobe.c`, `nuxel-diag.c`, `nuxel-syscall-probe.c` — generic hardware/syscall probes already present for diagnostics.
- The manual-proof files under `docs/beta-finalization/manual-proof/09-flashlight.md … 24-battery-power.md` describe each subsystem's **owner-test surface** (`…diag.sh status`, buzz gates, etc.) and carry the real verdicts to advance.

### 2.B Must-inspect before touching (never assume)
- **Exact haptic node.** `configs/nuxel/haptics/haptics.json` + `nuxel-haptics-diag.sh` enumerate `/sys/class/leds/*vib*`, `/sys/class/timed_output/*`, `/sys/class/vibrator/*` at runtime — the exact node is **not assumed**. P08 must read these globs live and never hard-code a path.
- **Intensity support.** Amplitude control exists *only if the node exposes a strength file*; otherwise report `intensity_mode=duration`. Do not fabricate amplitude (see haptic.md's explicit "Do not emulate unsupported intensity" rule).
- **Boot mode / charger guard.** `tools/s10plus/a33/nuxel-bootmode-guard.py` classifies `androidboot.mode=charger`/LPM (`lpcharge=1`, `sec_ts_init -ENODEV`) and gates reboots. In charger/LPM the touch driver is down and many subsystems can't be exercised — P08's diagnostics must report boot mode first and degrade gracefully rather than failing loudly in LPM.
- **Modem/SIM/wifi/bt/sensors** capabilities on `beyond2lte` are **not assumed**; enumerate from `/sys/class`, `/proc/bus/input/devices`, DMI, and udev before claiming support.

---

## 3. The inventory you must produce (P08 item 1 — done against reality)

Build a single machine-readable inventory that maps each Nuxel userspace service/unit to the **actual** S10+ runtime capability it depends on, with a verdict from the closed vocabulary in §9. Consume and extend what exists rather than duplicating:
- `docs/service-graph.md` + `docs/beta-finalization/system/SERVICE-GRAPH.md` (unit graph),
- `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json` (+ `.schema.json`, validator `tools/beta/validate-capability-manifest.py`) — the authoritative per-subsystem verdict table,
- `docs/beta-finalization/workqueue/<stable-id>.json` (the source of truth for each briq's state).

The inventory must list every P08-relevant subsystem with: repo path(s), current `verdict`, `offline_ceiling`, blocking evidence (real `/proc`,`/sys`,`dmesg` lines already captured in the manual-proof files), and the *next* smallest gap. **Do not invent new verdicts** — use exactly the §9 vocabulary, and do not promote a claim to live-device strength on the basis of a file existing (`verify-schema` forbids an on-device verdict from mere presence).

---

## 4. Which seeded briq tasks P08 owns (do NOT create new ones)

These already exist in `docs/beta-finalization/workqueue/`. P08 advances **one verified gap** among them (the smallest that is ready and unblocked), or records a precise blocker — it does not spawn parallel work. Current states at authoring:

| Task id | Subsystem | State (authoring) | Offline ceiling / verdict |
|---|---|---|---|
| `briq-08a-power-management` | Power mgmt, battery modes, power menu | `in_progress` | depends on `briq-03e-buttons-gestures`; expected: `configs/nuxel/power/`, `pwa/nuxel-apps/settings/`, manual-proof/24-battery-power.md |
| `briq-08b-vibration-haptics` | Vibration & haptics | `pending` (needs 08a) | NEEDS_OWNER_TEST; expected: `configs/nuxel/haptics/`, manual-proof/10-vibration.md |
| `briq-08c-flashlight-led` | Flashlight, notification LED, edge lighting | `pending` (needs 08a) | NEEDS_OWNER_TEST; expected: `configs/nuxel/leds/`, manual-proof/09-flashlight.md |
| `briq-08d-bluetooth` | Bluetooth (BlueZ) | pending | NEEDS_OWNER_TEST |
| `briq-08e-nfc` | NFC | pending | NEEDS_OWNER_TEST |
| `briq-08f-gps-gnss` | GPS/GNSS | pending | NEEDS_OWNER_TEST |
| `briq-08g-sensors` | Sensors (mag/gyro/prox/light) | pending | NEEDS_OWNER_TEST |
| `briq-08h-camera` | Camera | pending | NEEDS_OWNER_TEST |
| `briq-08i-sim-microsd-modem` | LTE modem, SIM, microSD | pending | NEEDS_OWNER_TEST |

**Selection rule for the future agent:** pick the lowest-priority-band task whose dependencies are satisfied (`08a` first since it gates `08b/08c`; then whichever of `08d–08i` is ready), implement its *smallest coherent next gap*, and record evidence. If the smallest gap for a subsystem cannot be closed without a live device or a kernel/firmware capability that isn't present, produce the **smallest safe implementation + precise blocker** and stop (acceptance gate: do not let manual hardware proof stall unrelated work).

---

## 5. Implementation plan the future agent should follow (repo-aware)

Follow P08's own workflow. Concretely, for each selected subsystem gap:

1. **Inspect reality.** Read the existing repo files (§2.A/§2.B), run the relevant offline tools (`verify-service-graph.py`, `verify-schema`, capability-manifest validator, the subsystem's own test suite) and inspect `/proc/cmdline`, `dmesg`, `/sys/class`, `/proc/bus/input/devices` on-device to confirm capabilities. Record existing behaviour and the smallest coherent repair.
2. **Preserve invariants before changing anything.** Keep: bootable system; working launcher navigation; haptics wiring already referenced; custom icon assets; Home layouts; USB recovery; single-`/dev/fb0` ownership; A26 containment (masked systemd-userdbd, NSS drop, dbus-daemon bus); a32 protected baseline parity.
3. **Implement the smallest gap.** Add config under `configs/nuxel/<subsystem>/`, extend existing tools (e.g., `nuxel-haptics-diag.sh`, `nuxel-uinput-touch-probe.py`) rather than creating parallel implementations, add a service unit only where it fits the graph and keep `verify-service-graph.py` green. Never flash a partition, write a block device, enter Download Mode/TWRP, or reboot on its own initiative (see §10).
4. **Track unavailable capabilities separately.** Anything not present on hardware is recorded as `BLOCKED_KERNEL`, `BOOT_UPDATE_REQUIRED`, `NOT_DEPLOYED`, or `NEEDS_OWNER_TEST` — never promoted to offline/live. Put the real captured evidence (`/sys`,`dmesg`) beside each blocked claim.
5. **Expose diagnostics + graceful degradation.** Every gap gets an observable surface (`…diag.sh status/… --probe`) and a non-blocking fallback (e.g., intensity falls back to duration; no-session ⇒ silent haptic no-op gated by `/run/nuxel/haptics/api-enabled`; LPM ⇒ report touch-disabled rather than crash).
6. **Test, then commit only P08's files**, leaving `git status` clean (§13).

---

## 6. What to actually build (concrete surfaces — examples, not a fixed list)

> The future agent should implement the *smallest verified gap* for the selected task(s), using these as concrete patterns already present or referenced in-tree. Do **not** assume all of the following exist; verify each path first and reuse where possible.

- **Haptics:** `configs/nuxel/haptics/haptics.json` (node enumeration via globs, named patterns: `tap`,`double`,`long`,`buzz_test`,`notify`,`alarm`,`button`,`gesture`; intensity levels `light/medium/strong` only if a strength file exists), `/var/lib/nuxel/haptics/state.json` global switch wired to button manager + notifications, bounded owner buzz (`buzz --yes <ms>`, cap 1500 ms), programmatic API gated by `/run/nuxel/haptics/api-enabled`, and the bridge that turns a button-manager action or `NotificationAdded` into a named pattern. Reuse/confirm `tools/s10plus/a33/nuxel-haptics-diag.sh`.
- **Flashlight / LED:** `configs/nuxel/leds/` enumerating `/sys/class/leds/*`, safe duty-cycle limits, notification-LED wiring — with honest reporting when no LED node exists.
- **Power/battery/menu:** `configs/nuxel/power/`, Settings integration (`pwa/nuxel-apps/settings/`), power-menu actions that route through the running bridge (never a second display owner), reboot policy honouring `briq-09b`'s "allowed but not blind" rule.
- **Sensors/NFC/BT/GPS/modem/SIM/microSD:** each as enumeration + minimal config + diagnostic script, with verdict driven by what `/sys`,`DMI`,udev actually expose.

---

## 7. Tests the future agent must write (real behaviour + failure paths)

Tests exercise real logic/failure paths on host/offline — **not** static references and **not** a stand-in for physical proof.

- Extend each subsystem's existing offline suite where one exists (`tools/s10plus/a33/tests/`, `tools/s10plus/a34/tests/`); otherwise add one under the matching `tests/`.
- The classifier/gate logic (boot-mode classification, reboot decision, haptic intensity→duration fallback, no-session gate exit code 7, buzz cap) must be driven by **synthetic fixtures** so every branch is exercised without a phone. Prove the validator *fails* on an injected regression (cycle, forbidden 4.14 dep, lost enablement, wrong verdict), exactly as `test-service-graph.py` and `test-bootmode-guard.py` already do.
- A capability-inventory test that asserts no row claims stronger than its record (§9 strength ordering) via the manifest validator + `verify-schema`.
- Explicitly assert the **anti-fabrication rule**: a prose doc merely *mentioning* a capability is not graded as hardware evidence — it lands in `UNKNOWN`, never promoted.

---

## 8. Acceptance gates (for the future agent; this file does NOT satisfy them)

- Every P08 item above is **implemented or explicitly BLOCKED with concrete evidence** (real `/sys`,`/proc`,`dmesg` lines — not "not implemented").
- Tests exercise real behaviour and failure paths, not only static references.
- Where a feature touches the phone, results are labelled: **mock/host test** vs **live-deployed** vs **owner-confirmed** — never conflated (see §12).
- Any dangerous hardware op (flashing, bootloader/partition write, kernel replacement, unsafe amp/LED setting) is **forbidden**.
- If a critical external dependency blocks it: produce the smallest safe implementation + precise blocker report, and stop. Do not let manual hardware proof stall unrelated queue tasks.

---

## 9. Verdict vocabulary (closed — use exactly these; do not invent)

`strength(min):` NOT_SUPPORTED_ON_DEVICE = DEFERRED = FAILED = BLOCKED_* = **0** · NEEDS_OWNER_TEST = IMPLEMENTED_NOT_DEPLOYED = **1** · OFFLINE_TESTED = **2** · VERIFIED_IN_VM_ONLY = **4** · VERIFIED_ON_S10PLUS = **5** (live-device evidence only).

- `verdict` = the claim; `record` = the evidence gate; a row's verdict may be **no stronger** than `min(record strength, record offline_ceiling)` and a record with no verdict caps it at 1.
- States: `pending · in_progress · implemented · blocked · deferred · reverted`.
- Live-device strength requires live-device evidence — **file presence is only an `observation`, never a verdict.**

---

## 10. Hardware honesty & the forbidden operations (verbatim discipline)

From `REBOOT-ROLLBACK.md` / `ROLLBACK.md`:
- **A reboot is allowed; a blind reboot is not** — every reboot states a reason *and* a differing diagnostic, and requires the previous reboot to have returned to Nuxel first.
- **No change deploys without a recorded way back** — rollback.sh's seven steps: capture previous hash → stage (`<target>.nuxel-staged`) → verify against manifest `source_sha256` → atomic install → restart only the smallest affected service → health-check → per-group checks; on failure auto-rollback (exit 3), state restored.
- **No script ever** flashes a partition, writes a block device, enters Download Mode/TWRP, or reboots on its own initiative.

---

## 11. Honest hardware verification plan (mock/host vs live — the crux)

This is where P08 most often fails; enforce it:

| Evidence | Reachable from host/offline? | How to record honestly |
|---|---|---|
| Node exists (`/sys/class/timed_output/vibrator`, `/sys/class/leds/*`) | on-device read only | capture the real line as an `observation` evidence entry |
| Enumerate capabilities / fallback logic / gate exit codes | **yes** (fixtures, pure functions) → `OFFLINE_TESTED` | assert real behaviour on synthetic input |
| Intensity supported? | on-device read a strength file; if absent report `intensity_mode=duration` | never claim amplitude without the file |
| A buzz is *felt* / LED glows / motor moves | **no** — owner must confirm | `VERIFIED_ON_S10PLUS` needs explicit live evidence; otherwise `DEPLOYED_UNVERIFIED` or `NEEDS_OWNER_TEST` |
| Touch works in a normal boot | **no** — down in charger/LPM | blocked by boot mode; owner test after normal boot |

Rule: **mock/host tests prove the code path and failure paths; they do not substitute for physical confirmation.** Label every result with exactly one of `mock/test · live-deployed · owner-confirmed`. Never pass off a mock as a physical check.

---

## 12. Safe rollback (per-component)

- Repository-only change → `git revert <commit>` restores it; no device state changes (`briq` rollback field text).
- Deployed userspace change → run `tools/beta/rollback.sh` (the seven-step discipline, §10); health gate auto-reverts on UNHEALTHY.
- A bad unit/config must not break the boot path or the 4.14 containment; keep `verify-service-graph.py` green and a live console recoverable (`ROLLBACK.md`: nothing may remove the console or local recovery route).

---

## 13. Commit & finish discipline (for the future agent)

- Commit **only P08's** code, tests, docs and the report; do not merge to main, switch branches, add secrets, or ship unrelated features.
- Write `docs/component-reports/p08.md` documenting: code paths changed, commands + receipts, PASS/FAIL/BLOCKED/NOT_TESTED per subsystem, actual device deployment status (mock/host vs live), unresolved issues, and safe rollback.
- Keep the worktree clean (`git status`) at the end; the queue runner pushes the branch.

---

## 14. Do / Don't summary

**Do:** reuse `services/**`, the A34 button manager + FSM, `nuxel-haptics-diag.sh`, the manifest/workqueue/service-graph tooling; verify everything from source and live device reads first; extend existing suites; cap every claim at its evidence strength.

**Don't:** create parallel services/tools that duplicate existing ones; touch the a32 protected baseline; bypass single-`/dev/fb0` ownership or the ABGR colour conversion; hard-code haptic node paths; fabricate intensity/amplitude; flash/write partitions/reboot on initiative; claim live-device proof that didn't happen; implement briq tasks outside P08's selected gap(s).

---

## 15. Commands the future agent will run (reference only)

```sh
# Reality checks / invariants (must stay green)
python3 tools/s10plus/a33/verify-service-graph.py
python3 tools/s10plus/a33/tests/test-service-graph.py     # must FAIL on injected cycle / forbidden dep
python3 tools/beta/validate-capability-manifest.py --manifest docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.json --schema docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.schema.json --workqueue docs/beta-finalization/workqueue
tools/beta/run-all-tests.sh                                  # expect exit 0

# Per-subsystem (reuse; verify paths first)
tools/s10plus/a34/nuxel-button-manager.c --probe --config-check
nuxel-haptics-diag.sh status; nuxel-haptics-diag.sh api <pattern> --source <consumer>

# Deploy discipline (only when a live change is made)
tools/beta/rollback.sh        # seven-step capture→stage→verify→install→restart→health→checks
```

*Authoring note:* §2 reflects the repo state at HEAD `e2aaf66` (`v0.6.0-beta`). Any subsystem whose files changed since authoring is `NOT_REAUDITED` — re-verify from source before implementing.
