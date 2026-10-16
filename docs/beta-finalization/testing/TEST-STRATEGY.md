# NUXEL BETA — TEST STRATEGY (L1–L6)

**briq:** `briq-09a-test-strategy-soak` · **component:** `bg-09-integration-release` (priority 8, the release gate)
**Device under test:** Samsung Galaxy S10+ / SM-G975F / beyond2lte / Exynos 9820
**Repository:** `/x/nuxel` · **Entry point:** `tools/beta/run-all-tests.sh`
**Terminal vocabulary:** `VERIFIED_ON_S10PLUS` · `VERIFIED_IN_VM_ONLY` · `OFFLINE_TESTED` · `DEPLOYED_UNVERIFIED` · `IMPLEMENTED_NOT_DEPLOYED` · `BLOCKED_KERNEL` · `BLOCKED_FIRMWARE` · `BLOCKED_HARDWARE` · `BLOCKED_EXTERNAL_RESOURCE` · `NEEDS_OWNER_TEST` · `FAILED` · `DEFERRED` · `NOT_SUPPORTED_ON_DEVICE`

---

## 1. Why this document exists

A green build is not a working phone. This strategy makes the *distance* between
"I ran something" and "it works on the handset" explicit and mechanical, so that
no reader — human or agent — can mistake one for the other.

Three rules are absolute:

1. **Files existing ≠ feature working.** A registered kernel driver is not
   hardware operation. A mixer write is not audible sound. A unit test is not a
   device verdict.
2. **A verdict may only be as strong as its evidence.** `VERIFIED_ON_S10PLUS`
   requires live-device evidence captured from the handset itself, with real
   timestamps, in this repository.
3. **Never fabricate.** A suite that cannot run is `SKIP` with a named reason, a
   suite that fails is `FAIL` with its log, and a suite that was never written is
   an orphan that `L1-test-coverage` reports. Nothing is ever upgraded to a pass
   it did not earn.

---

## 2. The hierarchy

| Tier | Name | Runs on | Verdict it can produce | Where it lives |
|---|---|---|---|---|
| **L1** | Static | build host | `OFFLINE_TESTED` | `run-all-tests.sh` registry, tier `static` |
| **L2** | Unit / offline | build host | `OFFLINE_TESTED` | tier `unit`, `cross` |
| **L3** | Integration (offline) | build host | `OFFLINE_TESTED` | tier `cross`, `legacy` |
| **L4** | UTM VM | the UTM Fedora 43 guest | `VERIFIED_IN_VM_ONLY` | tier `external` (`--external`), `vm/`, `tools/beta/vm/` |
| **L5** | Live phone | the S10+ over the USB CDC-ACM console | `VERIFIED_ON_S10PLUS` | tier `external`, `tools/beta/live/`, `tools/s10plus/a3x/` |
| **L6** | Owner physical | human hands + eyes + ears | `NEEDS_OWNER_TEST` → owner verdict | `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` |

### L1 — Static

Cheap, total, and it fails closed. Implemented as in-process programs inside
`run-all-tests.sh` so no file is written and nothing is imported from the tree:

| Suite | What it proves |
|---|---|
| `L1-python-syntax` | every repo-authored `.py` parses (`ast`, no bytecode written) |
| `L1-shell-syntax` | every `.sh` parses, dispatched by **shebang** (`boot/*/pack-boot-v1.sh` is Python with a `.sh` name) |
| `L1-js-syntax` | every PWA `.js` passes `node --check` |
| `L1-json-valid` | every manifest / registry / report JSON in the owned trees parses |
| `L1-no-flash-invariants` | no flash tool in command position, no `dd` to a block device, no write under `.qq/`, no receipt JSON in the workspace, and an allow-listed legacy flash doc is *unreachable* from the beta pipeline |
| `L1-test-coverage` | `tools/beta/suite-coverage.py` — no test file is orphaned: every discovered test is reachable from the registry. An orphan in a **release-owned** tree is a hard failure; an orphan in another group's tree is reported loudly and does not gate this group |

Missing prerequisites (interpreter, file, or a `probe:` predicate) are `SKIP`
with the missing piece named — **never** a silent pass and never a fake failure.
A *release-owned* suite whose own file is missing fails (`FAIL`), so this group's
gate can never be silently skipped.

### L2 — Unit / offline

Owned by the group that writes the component; the release group only runs them.
Representative coverage (the authoritative list is the registry —
`tools/beta/run-all-tests.sh --list`):

| Mission area | Suite | Owning group |
|---|---|---|
| work queue schema + tool | `U-workqueue-schema`, `U-workqueue-unit` | bg-00 |
| A32 baseline register (hash pins + behaviour) | `U-baseline-regression-guard`, `U-baseline-a32-suite` | bg-00 |
| boot image gates (container, initramfs, partition budget) | `U-boot-s10plus-gates` (probe-gated: needs the gitignored, hardware-proven A5 base + A4 initramfs), `U-boot-init-cmdline` | bg-00 |
| touch pipeline (trace tool, libinput shim, boot-mode guard, capture harness) | `U-touch-a33-suite` | bg-01 |
| boot/animation/launcher surface, colour order, safe zones | `U-boot-a33-suite`, `U-c-protocol-handoff` | bg-02 |
| Wi-Fi, time/RTC, audio, headphones, buttons | `U-p3-a33-suite` | bg-03 |
| services graph, packages, portal, notifications | `U-userspace-a33-suite`, `U-verify-service-graph`, `U-verify-packages` | bg-04 |
| firewall rule translation, VPN/Tor honest labels, permission policy | `U-security-*`, `U-verify-permissions`, `U-shell-permissions` | bg-05 |
| app registry, app inventory, phone data model | `U-verify-app-registry`, `U-verify-app-inventory`, `U-shell-phone-data`, `U-apps-js` | bg-06 |
| specialty apps (SnekByte parity + upstream pytest, NuxTore) | `U-snek-*`, `U-nuxtore-pwa` | bg-07 |
| soak harness, rollback/reboot policy, run-all-tests itself | `U-soak-harness`, `U-release-tools-selftest`, `U-rollback-reboot-scenarios`, `U-adb-pack-mock` | release |

**The checks column.** Each row reports `CHECKS`: the number of PASS-shaped
assertion lines the suite *printed*, counted by `count_checks()` as
`(^|\s)(PASS|ok|OK)(\s|:|.)|^\d+ passed`. It is a deliberate **floor**, not a
coverage claim: a suite that prints nothing measurable reports `-` and is never
credited with assertions it did not print. Read it together with the log path in
`build/reports/beta-tests/summary.json`.

### L3 — Integration (offline)

Cross-component behaviour that must hold without the phone:

* **A32 baseline regression guard** (`tools/beta/regression-guard.sh`) — the
  preserved A32 successes (single framebuffer owner, colour conversion, safe
  zones, wallpaper asset hash, launcher registry, button manager) still hold, as
  hash pins *and* as behavioural invariants. This is the "do not start over" gate.
* **Group runners** — each build group's `run-*-tests.sh` exercises its own
  integration surface (Phoc↔WebKit wiring, launcher↔bridge contract, service
  graph, Flatpak/NuxTore catalogue policy, console ownership, permission
  enforcement, app activation).
* **Release tooling** — `tools/beta/tests/test-release-tools.sh` and
  `tools/beta/tests/test-rollback-reboot.sh`: the rollback discipline under
  mocked failures, the reboot policy's refusals, the soak harness, the health
  gate, and `run-all-tests.sh`'s own registry and machine summary.

L3 is still `OFFLINE_TESTED`. A passing integration test on the build host says
nothing about the handset's panel, touch controller, codec or radios.

### L4 — UTM VM (`VERIFIED_IN_VM_ONLY`)

The UTM Fedora 43 guest is the **launcher reference**: it is what the phone's
launcher must match. Its suites are listed in the registry as `external` and run
only with `--external`:

```
tools/beta/run-all-tests.sh --external --only '^X-vm-'
```

* `X-vm-services` — the guest's service graph and unit health.
* `X-vm-launcher-parity` — launcher, status bar and safe-zone parity run.
* `tools/beta/vm/vm-launcher-dom-harness.py` — DOM-level harness for the launcher.

**A VM pass never implies a phone pass.** Hardware-specific behaviour (the
Wayland→framebuffer bridge, DECON colour order, the AMOLED panel, the touch
controller) cannot be validated in the VM and is not claimed from it.

### L5 — Live phone over the live console (`VERIFIED_ON_S10PLUS`)

The only tier that can produce a device verdict. Reached through the preserved
USB CDC-ACM console (`/dev/ttyACM0`, `scripts/s10plus-debug-pack/nuxel-live.sh`,
`tools/beta/live/nuxel_live.py`):

* `X-live-launcher-acceptance` — launcher acceptance on the handset.
* `X-live-soak` — the bounded soak (`tools/beta/soak.sh --device`).
* The touch capture harness, the boot-mode guard, the pipeline trace tool, and
  the deploy/rollback rehearsal (`docs/beta-finalization/release/REBOOT-ROLLBACK.md`).

Rules for L5:

* Read-only unless the task explicitly authorises a change; every change goes
  through the rollback discipline (`tools/beta/rollback.sh`) first.
* **No flashing.** No partition writes, no raw block writes, no bootloader
  tools, no Download Mode, no TWRP. `tools/beta/rollback.sh` and `soak.sh` refuse
  such paths and the L1 invariant suite enforces the refusal statically.
* Never run two clients against a dangerous device node at once.
* A lost console stops the work and is documented — it is not a reason to reboot.
* Evidence is captured with real timestamps into the evidence trees
  (`docs/beta-finalization/live/`, `docs/beta-finalization/touch/`,
  `docs/beta-finalization/release/evidence/`).

### L6 — Owner physical acceptance

Everything that needs a finger, an eye, an ear, headphones, a SIM, a microSD
card or credentials is prepared, documented and marked `NEEDS_OWNER_TEST` in
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`. It is **non-blocking**
and is **never auto-promoted**: no script may turn an owner step into
`VERIFIED_ON_S10PLUS`. The checklist records, per item, the exact preparation,
action, expected result, failure symptoms, diagnostic command, PASS and FAIL
criteria, and which items already have automatic evidence versus which need
human proof.

---

## 3. Running the gate

```bash
tools/beta/run-all-tests.sh                     # every offline suite + the regression guard
tools/beta/run-all-tests.sh --list              # the registry, run nothing
tools/beta/run-all-tests.sh --only '^L1-'       # a tier / id subset (grep -E)
tools/beta/run-all-tests.sh --strict            # the raw verdict: no cross-group allowances
tools/beta/run-all-tests.sh --external          # also attempt the live/VM tiers
tools/beta/run-all-tests.sh --json - > run.json # pure machine JSON on stdout
tools/beta/run-all-tests.sh --quiet             # less noise (the table still prints)
```

* Reports: `build/reports/beta-tests/summary.json` (machine) and one log per suite
  in `build/reports/beta-tests/logs/<suite-id>.log`. `build/` is gitignored;
  committed evidence is copied into `docs/beta-finalization/release/evidence/`.
* **Exit codes:** `0` every hard suite passed · `1` at least one hard suite
  failed (the gate is RED) · `2` usage/environment error.
* **stdout discipline:** with `--json -` the JSON document is the only thing on
  stdout; the human transcript goes to stderr, so stdout can be piped straight
  into a parser.
* The final table is printed on every run:

```
ID                             TIER     STATUS    OWNER                                    CHECKS   SECS
U-release-tools-selftest       unit     PASS      release                                      20      8
```

### Verdicts, allowances and honesty

The summary JSON always contains, side by side:

* `gate` / `verdict` — the run's verdict **with** any cross-group allowances applied;
* `raw_gate` / `raw_verdict` / `raw_fail_count` — what `--strict` would say, i.e.
  the release decision;
* `counts.warn_cross_group` — how many failures were downgraded, and only for
  *another* group's suite;
* `failures[]` — every failure, verbatim, with its owning group;
* `allowances_applied[]` — id, owning group, reason, evidence path and expiry.

The `INFLIGHT_ALLOWANCES` register in `run-all-tests.sh` may only hold suites that
belong to **another** build group while that group is actively writing into this
tree (eleven groups share it). It downgrades such a failure to a loud `WARN`,
prints it again in its own block, keeps it in the JSON, and carries an expiry
date. It can never turn a failure into a pass, and it can never hide a
release-owned failure. **The terminal integration pass — after every group has
landed — is `--strict`; that run is the release decision.**

Current run: see `docs/beta-finalization/release/evidence/` (transcript + summary
JSON). A red `raw_gate` in a mid-build run means another group's surface is
incomplete; the failures are attributed by group in `failures[]`.

---

## 4. What each tier may and may not claim

| Claim | L1 | L2 | L3 | L4 | L5 | L6 |
|---|---|---|---|---|---|---|
| "the file parses / the manifest is valid" | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| "the algorithm is correct on fixtures" | – | ✅ | ✅ | ✅ | ✅ | ✅ |
| "the components talk to each other" | – | – | ✅ | ✅ | ✅ | ✅ |
| "it runs in the Fedora 43 VM" | – | – | – | ✅ | ✅ | ✅ |
| "it works on this handset, right now" | – | – | – | – | ✅ | ✅ |
| "a human saw heard or felt it" | – | – | – | – | – | ✅ |

Hardware truth table (from the live preflight, cycle 003) that constrains every
verdict in this repository:

| Fact | Evidence | Consequence |
|---|---|---|
| `androidboot.mode=charger` (LPM) | `/proc/cmdline` | the touch controller is deliberately not initialised: `[sec_input] sec_ts_init: Do not load driver due to : lpm 1` |
| No `/sys/class/sec/tsp`, no touch evdev node | `ls /sys/class/sec/tsp`, `/proc/bus/input/devices` (event0–6 only) | touch cannot be tested in the current boot mode; it is `BLOCKED_KERNEL` on the boot mode, not on userspace |
| No `/dev/dri`; `/dev/fb0` 1440x6080x32 | `ls /dev/dri`, `fb0/virtual_size` | Phoc is headless; the display is the Wayland→framebuffer bridge, not DRM/KMS |
| `brcmfmac` wifi + `wlan0`/`wlan1` down, not blocked | `rfkill list`, `ip -br link` | Wi-Fi hardware enumerates; association is unproven |
| `rmnet0..7`, `umts_dm0`, `mcps0` present; `mmcli -L` → "No modems were found" | `ls /sys/class/net`, `mmcli -L` | Shannon transport is exposed to the kernel; no ModemManager-usable modem object yet |
| `beyond-madera`, `abox_vdma`, `abox_dump` cards; `aplay` absent | `/proc/asound/cards`, `aplay -l` | the codec is registered; audibility is unproven and `alsa-utils` is not installed |
| `timedatectl`: *RTC time: n/a*; device clock ≈ 2026-09-15 | `timedatectl`, live batches | there is **no exposed battery-backed RTC**; and the wrong clock already breaks RPM signature verification (`signature is not alive`) |
| `/sys/class/timed_output/vibrator`, `/sys/class/leds/{leds-sec1,torch-sec1}` | live batch 3 | haptics, the notification-LED class and the camera torch have real control paths |
| `pipewire`, `wireplumber`, `alsa-utils`, `flatpak` **not installed** (410 RPMs) | `rpm -q`, `flatpak --version` | the audio stack and the app store are not yet deployable on the handset |

---

## 5. Legacy per-cycle gates

The alpha cycles left their own gates (`tools/s10plus/a27`, `a28`,
`tools/app-registry-check.sh`). They are registered and still run, but two facts
make them conditional rather than unconditional:

* they gate on **artefacts of the alpha build chain** — the packed animation
  container and the first-light splash under `build/out/s10plus/a26/` — which are
  produced by the A26 tooling (`tools/s10plus/nuxel-anim-pack.py`,
  `tools/s10plus/a26/make-firstlight-asset.py`) and are **not** committed (and
  `nuxel-anim-pack.py` additionally needs `numpy`, which the beta build host does
  not carry);
* `a27/test-ui-layout.sh` needs **Pillow** and an **aarch64 cross-compiler**.

They are therefore precondition-gated with a `probe:` prerequisite. An unmet
probe is a **loud SKIP that names the missing piece** — never a silent pass and
never a fake failure:

```
SKIP L-a27-firstlight  host/artefact prerequisite unmet:
      test -s build/out/s10plus/a26/nuxel-firstlight.rawspl && python3 -c 'import numpy' (owner: legacy-per-cycle)
```

The same rule covers the **S10+ boot-image gates** (`U-boot-s10plus-gates`,
repaired by `briq-02-gate-failure-repair`). That gate is anchored on containers the
boot repair chain produced and that `build/` keeps out of git —
`build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img` (the one
container S-Boot is observed to deliver **and** unpack) and
`build/out/s10plus/debug-candidates/A4/initramfs.cpio` — and those images are
hardware-proven, so they can never be synthesised. It carries the same `probe:`
precondition, asserts the A5 base's documented sha256 so it can only speak about
the *proven* container, and exits `3` (`SKIP-PREREQ`, never `0`) with the exact
missing paths and this diagnostic when run by hand. Before that repair the suite
hard-failed (`exit 1: cannot unpack the hardware-proven A5 base`) on any host
without the artefacts, which is a missing prerequisite reported as a code
regression.

With the artefacts built (as the release workflow does), the probes are
satisfied, the suites run, and they gate **hard**. They can also be run by hand:

```bash
python3 tools/s10plus/nuxel-anim-pack.py --mp4 assets/nuxel-boot-animation.mp4 \
        --out build/out/s10plus/a26/nuxel-animation.nux
python3 tools/s10plus/a26/make-firstlight-asset.py \
        --anim build/out/s10plus/a26/nuxel-animation.nux \
        --out  build/out/s10plus/a26/nuxel-firstlight.rawspl \
        --raw-out build/out/s10plus/a26/nuxel-firstlight-raw.bin \
        --mp4 assets/nuxel-boot-animation.mp4
bash tools/s10plus/a27/test-firstlight.sh
```

`L-a28-launcher` and `L-app-registry-check` are `soft`: their subject matter was
superseded by the A32/A33 launcher registry and `verify-app-registry.py`, so a
failure there is reported as `WARN` and does not gate the beta.

---

## 6. Environment, reproduction and evidence

* **Host:** Fedora 43 x86_64, `python3` (3.11+), `bash`, `node`, `cc`, `git`.
  Optional: `jq`, coreutils `timeout`, `ffmpeg`, `numpy`, `Pillow`, an aarch64
  cross-compiler. Absence is a `SKIP` with a reason, not a failure.
* **Nothing in this tier touches the phone, the network, `/dev`, or `.qq/`.**
  Scripts are inert until invoked and may be reverted with `git revert`.
* **Evidence tree:** `docs/beta-finalization/release/evidence/`
  — `run-all-tests-transcript-<stamp>.txt` (full run, real timestamps),
  `run-all-tests-summary-<stamp>.json`, `soak-plan.txt`, `soak-selftest.txt`,
  `rollback-selftest.txt`, `reboot-policy-selftest.txt`,
  `capability-manifest-crosscheck.txt`, and `cross-group/<suite>.log` for every
  failure attributed to another group.
* **Rollback of this briQ:** `git revert` the commits touching
  `tools/beta/**` and `docs/beta-finalization/{testing,release}/**`. Tests change
  no device state, so no device rollback is required.

---

## 7. Related documents

| Document | Contents |
|---|---|
| [`SOAK-AND-PERFORMANCE.md`](SOAK-AND-PERFORMANCE.md) | the bounded soak, the resource/performance criteria, the harness |
| [`../release/REBOOT-ROLLBACK.md`](../release/REBOOT-ROLLBACK.md) | the autonomous reboot policy and the per-component rollback discipline |
| [`../release/DEVICE-CAPABILITY-MANIFEST.md`](../release/DEVICE-CAPABILITY-MANIFEST.md) | per-subsystem status and the hardware truth |
| [`../release/DEVICE-CAPABILITY-MANIFEST.json`](../release/DEVICE-CAPABILITY-MANIFEST.json) | the same, machine-readable, cross-checked against the work queue |
| [`../release/ROLLBACK.md`](../release/ROLLBACK.md) | how to undo a release-level change |
| [`../BETA-MANUAL-PROOF-CHECKLIST.md`](../BETA-MANUAL-PROOF-CHECKLIST.md) | L6 owner acceptance, 26 sections |
| [`../BETA-FINALIZATION-ENGINEERING-REPORT.md`](../BETA-FINALIZATION-ENGINEERING-REPORT.md) | the release report |

*Offline suites were validated on the beta build host; every device claim in this
strategy is traceable to a capture in the evidence trees and is dated. Where
evidence does not exist, the document says so.*
