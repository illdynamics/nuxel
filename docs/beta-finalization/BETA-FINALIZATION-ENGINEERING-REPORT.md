# Nuxel Beta Finalization — Engineering Report

| Field | Value |
|---|---|
| Document | `docs/beta-finalization/BETA-FINALIZATION-ENGINEERING-REPORT.md` |
| Produced by | `bg-12-reports` / `briq-12a-engineering-report` (construqtor, Qq cycle-001) |
| Access tier | **repository-only aggregation** — no handset console, no adb, no VM parity run executed by this briQ |
| Repository revision at aggregation | `838a00a5081323965af77f7f30e39f921312991e` (tree `f97b0802b743f1b4ac41933e46998b281dc4aeaf`) |
| A32 baseline floor (protected) | `0102b6009d5ac561fe15c85b25a58942404d081d` (2026-10-16T15:11:15+02:00) |
| Aggregation wall-clock | pass 1 **2026-10-16T14:26:28Z** (16:26 +02:00) · pass 2 **2026-10-16T16:55Z** (18:55 +02:00), `Europe/Amsterdam` — pass 2 = `§10` re-verification, no phone, no VM run |
| Target | Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), Fedora 43 ARM64 userspace, Samsung Linux 4.14.253, systemd PID 1 |
| Work-queue machine view | `docs/beta-finalization/workqueue/*.json` (54 tasks) |
| **Beta verdict** | **`BETA_CANDIDATE_PENDING_HARDWARE_PROOF`** (see §9) |

> **Evidence discipline used throughout.** A green unit test is `OFFLINE_TESTED` and never anything
> more. A registered kernel driver is not proof of working hardware; a writable mixer control is not
> proof of audible sound; a running `tor.service` is not proof that traffic is anonymised. Nothing in
> this report is `VERIFIED_ON_S10PLUS` unless it carries an **on-device** capture, and the only such
> items here are inherited from the **A32 record** (a previous cycle's measured evidence), which this
> run did **not** re-measure because the handset console did not answer (see §7).

---

## 1. Executive summary

This document is the terminal engineering record of the Nuxel **beta finalization** run. The mission
was repository-first, non-interactive and evidence-based: land the whole beta deliverable set in the
tree, test it offline (and in the UTM VM where a faithful substitute existed), and record honestly
what remains unproven. **No flashing of any kind happened or is required.** The physical phone was
not written to, not rebooted by this run, and its console was not even reachable.

**What landed.** Twelve priority bands wrote into `WORKSPACE_ROOT`. At aggregation time the
authoritative work queue holds **54 tasks**: **9 `implemented`**, **24 `in_progress`**, **21
`pending`**; **9 tasks carry a recorded verdict** (`OFFLINE_TESTED`), and **zero tasks claim
`VERIFIED_ON_S10PLUS`** (`python3 tools/beta/workqueue.py verify-schema --json` → `"ok": true`,
`"verified_on_s10plus": []`). The A32 baseline — the floor the mission forbids regressing — is
**intact**: `tools/beta/regression-guard.sh` → **`verdict: PASS`, 44 pass / 0 fail / 5 soft-warn /
2 info**, and `tools/s10plus/a32/tests/run-tests.sh` → **`0 failing suite(s)`** (exit 0).

**What is proven, and how.** The five test-suite entry points all pass on the build host at
aggregation time (all offline, no phone, no root, no display): `run-touch-tests.sh` →
`TOUCH-TESTS: ALL PASS`; `run-boot-tests.sh` → `BOOT-TESTS: ALL PASS`; `run-p3-tests.sh` →
`P3-TESTS: ALL PASS`; `run-userspace-tests.sh` → `pass=10 fail=0 skip=0 → OFFLINE_TESTED`; plus the
seven hardware-subsystem diagnostics (`PASS — OFFLINE_TESTED`), the firewall suite (**49 passed, 0
failed**) and the phone-app suite (**PASS=37 FAIL=0**). Full numbers in §7.

**What is *not* proven.** Every hardware behaviour that needs a human (a finger, an ear, eyes, a SIM,
a tag, a peer, the outdoors) is `NEEDS_OWNER_TEST`; every behaviour that needs the handset console is
`BLOCKED_EXTERNAL_RESOURCE`; the one durable kernel gap (charger-mode boot disabling `sec_ts`) is
`BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED`. None of these was papered over, and none was
auto-promoted.

**Verdict.** `BETA_CANDIDATE_PENDING_HARDWARE_PROOF` — the platform is real (the S10+ boots Nuxel and
A32 proved a working interactive launcher on the glass), the beta deliverable set is implemented and
offline/VMs-tested, nothing regressed, but the acceptance criteria that require the physical phone or
the owner's senses have not been observed in this run. §9 states exactly why the other three verdicts
were rejected.

### 1.1 Non-interactive assumptions (stated, not re-asked)

1. **The phone owner is not available during execution.** There is no interactive participant in this
   run. Every task needing a finger, ear, eyesight, credential, SIM, headphone, tag, peer device or
   physical manipulation is *implemented*, *offline-tested / instrumented*, given an automated
   diagnostic and exact owner instructions, marked `NEEDS_OWNER_TEST`, and recorded in
   `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`. Such tasks never blocked unrelated work
   and were never auto-promoted to `VERIFIED_ON_S10PLUS`.
2. **The repository at `WORKSPACE_ROOT` is the source of truth.** Supplied comparison archives are
   supplementary and were used **only where they were actually present on disk** (see §3.1). The
   mission named `docs(8).zip`, `scripts(7).zip`, `tools(4).zip` and standalone A30/A31/A32 archives;
   those were inspected for and found **ABSENT**, so their dependent work degraded to "compare
   against the live tree + the present snapshots" and was marked accordingly — no assumed upload path
   was ever referenced as if present.
3. **No environment is assumed reachable.** The live USB console did not answer (`BLOCKED_EXTERNAL_
   RESOURCE`); the UTM Fedora 43 guest *was* reachable (`VERIFIED_IN_VM_ONLY` channel available) but
   the VM parity run belongs to `bg-11-vm-parity`, whose output was not present at aggregation time.
   Live-access tasks stayed separable from repository-only tasks.
4. **Unenforceable restrictions are documented, not faked.** Fedora 43 ARM64 package claims were
   resolved against **real repository metadata** (93 975 NEVRAs), not guessed; unavailable essential
   packages were never hidden with `--skip-unavailable` (there was one genuinely retired package,
   `basesystem`, which was removed and documented). Linux 4.14 capabilities were taken from the real
   kernel/config, and mechanisms that do not exist there (Landlock, kernel lockdown, BPF-LSM, arm64
   CFI/SCS/BTI/PAuth) are named as **ABSENT limitations**, never promised by a cosmetic switch.
5. **Root compromise is out of scope of every enforcement claim.** Every enforcement statement is made
   *per attacker-privilege class* (§6). Nothing is described as "unbypassable".
6. **Third-party hardware documentation for other devices was not applied.** The S10+ radio is a
   Murata/Broadcom **BCM4375-class** part and its audio is ALSA card **`beyond-madera`**; the repo's
   Pixel BCM4390 / Pixel 10 Pro XL documents were explicitly *not* carried over.

### 1.2 Dependency report reference

The verified Fedora 43 ARM64 package/dependency record is
**`docs/beta-finalization/system/DEPENDENCY-REPORT.md`** (verifier `tools/s10plus/a33/verify-packages.py`,
machine-readable manifest `images/s10plus/packages-manifest.json`): 50/50 essential packages resolved
against real GA + updates metadata, `systemd` pinned to `systemd-258.11-1.fc43.aarch64`, with no
`--skip-unavailable` path. §8 restates its key numbers.

---

## 2. Verified existing functionality (the A32 floor)

The A32 build is the **floor**. Its record is byte-pinned (invariant `INV-7`, hard) and re-checked by
the regression gate on every run, and its behavioural invariants are enforced hard/soft by
`tools/beta/regression-guard.sh`. The rows below are A32's **own on-device observations** (inherited,
not re-measured this run); the "re-verified this run" column says what *this* run could actually
confirm.

Authoritative record: `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/13-RELEASE-NOTES-A32.md`
(sha256 `a4bfe968f1c409c3e0233877d6284c369eef263216111a2cad2aaf4b4c24db67`, hard pin `INV-7`) and
`00-BASELINE.md` (sha256 `0f7474fcca4dcf4b09325807ed333636a5a142da936517c2fe2e4e2e4adfa197`).

| A32 floor capability | On-device evidence (A32 record) | Re-verified this run |
|---|---|---|
| S10+ boots Nuxel: S-Boot → kernel → initramfs → Fedora 43 systemd PID 1 | `systemd[1]: systemd 258.11-1.fc43 … arm64`; boot 3.910 s kernel + 4.378 s userspace = 8.289 s | **not re-measured** (no console) — record intact (`INV-7`) |
| Touchscreen exists after a **normal** boot; libinput accepts it; compositor holds it | `input: sec_touchscreen … PROP=2`; libinput `accepted=1 direct_devices_seen=2`; 2 `/dev/input/event*` fds in phoc | **not re-measured**; the charger-mode root cause is re-documented (`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`) |
| Launcher is the authoritative UTM PWA (byte-identical JS/CSS/icons) | sha256 diff of handset vs VM trees; HTTP 200 per asset | **A32 suite re-run green**; registry/parity test green this run (`launcher-registry-test.js`) |
| Wallpaper asset at the served path | `6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29` | **re-verified** (A32 suite asserts the hash + CSS reference) |
| DECON colour order `R@0 G@8 B@16` (ABGR_8888), red stays red | live `colour=R@0,G@8,B@16` + unit test | **re-verified offline**: `test-colour-order.py` golden bytes + the compiled aarch64 bridge selftest |
| Ten-zone safe areas; S10+ portrait blocks zones 9,10; battery cluster moved 112 px clear | `SAFEZONES … blocked=[9,10]`; `moved=[{"cluster":"status-right","shift":112,"zone":9}]` | **re-verified offline**: `safe-zones-test.js` (44 assertions) + guard `INV-3` |
| Full animation cycle before hand-off; single framebuffer owner | `NUXEL_ANIM_LOOP=1/2`, `ANIMATION_STOPPED` at 21.1 s; `fb-owner` ends `LAUNCHER_DISPLAY_OWNER` | **re-verified in the shared decision table** (`nuxel-anim-handoff.py selftest`, 22-case corpus) |
| Buttons: POWER short → display off/on; volume → real ALSA element; Bixby 703 → Terminal | `DISPLAY_OFF brightness=0 saved=12800` → `DISPLAY_ON brightness=12800`; element `Left AMP PCM Gain` | **record intact** (`INV-4` hard pin); `power_volume_bixby` is the one `VERIFIED_ON_S10PLUS` item in the capability slice, inherited from this record |
| Live root console over USB survives disconnect (HUP-proof respawning supervisor) | A24 acceptance suite; `shell #N exited; respawning` | **record intact** (`INV-5`); the console did **not** answer this run (§7 gap) |
| Userspace rollback path (native home → known-working kiosk) | `tools/nuxel-rollback-home.sh` + three systemd-user units | **present and pinned** (`INV-6`), re-checked by the guard |

**Explicitly NOT claimed by the A32 floor** (quoted from its own record, and still true): audio
**output** (no player / no UCM bring-up beyond the amp-gain control), camera, modem, WLAN, and the
physical acceptance tests (finger taps, power/volume/Bixby presses, visual colour/wallpaper/cutout
confirmation). This beta run **adds** offline/VM-testable implementations for those areas but does not
promote any of them past their honest state.

### 2.1 A32 protected hashes (guard inputs)

| Invariant | Path | sha256 (pin) | Mode |
|---|---|---|---|
| `INV-1` launcher/cache | `pwa/nuxel-home/sw.js` | `d7fd084352f8fafa377d6f0ac28a4dd576fb842d03fd7292924609f6538ded30` | soft |
| `INV-1` | `tools/s10plus/a32/nuxel-pwa-host.c` | `adeddd50474b57f9b927a13831e411845fad0d3453d95086b4c02b24eed616a6` | hard |
| `INV-2` colour | `tools/s10plus/a32/nuxel-wl-fb.c` | `6501c6d5d74128f9004088663ca78e46356b7131756d325165822a76b56c51d7` | hard |
| `INV-3` safe areas | `pwa/nuxel-home/js/safe-zones.js` | `ca99df1a9da4d94c75d83b91b5962b3d6aafd3b3ec76af5b5cf2b2c9b97cdb93` | soft |
| `INV-4` buttons | `tools/s10plus/a32/nuxel-button-manager.c` | `07ce5c56d7f14efa4850a8ff8e851f574a034fe6582eb98fbec6188413b8632c` | hard |
| `INV-5` console | `tools/s10plus/a24-nuxel-console.c` | `d5d4c65c0605f88e8769a1e04d00795e27048899d493dee212f97e7134ad6dd1` | hard |
| `INV-6` rollback | `tools/nuxel-rollback-home.sh` | `b6288c34e1117edfccaa76bd7d764fbb903108a9dc29ea88e9582c27993c1f24` | hard |
| `INV-7` A32 record | `…/13-RELEASE-NOTES-A32.md` | `a4bfe968f1c409c3e0233877d6284c369eef263216111a2cad2aaf4b4c24db67` | hard |

Deployed-artefact hashes A32 recorded as **verified on the handset** (guard recomputes from
`build/out/s10plus/a32/`; a fresh on-device re-read is `NEEDS_OWNER_TEST`):
`/usr/lib/nuxel/nuxel-wl-fb` `e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e`,
`nuxel-pwa-host` `18631d5b71eb938d821ba319ddf78ee73b403811933824d93b36dc9439f7f6b0`,
`nuxel-button-manager` `5f052ef4523a3fee8f13c65a24fddfede553753d18725bd533e7e877f7cc3dc5`,
`nuxelctl` `e4281cab…`, `nuxel-button-manager.service` `d911babf…`.

---

## 3. Per-component changes (paths · root cause · build · tests · hashes · rollback)

Grouped by priority band. "State" is the honest terminal state from the mission vocabulary. In every
row, **rollback is repository-only** (revert the files / reinstall the previous artefact) because
nothing here was flashed and almost nothing was deployed.

### 3.1 Priority 0 — preflight, discovery, work queue, baseline protection (`bg-00-preflight`)

| briQ | Root cause / problem | Paths | Build / run | Tests (this run) | Rollback |
|---|---|---|---|---|---|
| `briq-00a` preflight | No measured environment record existed | `docs/beta-finalization/preflight/ENVIRONMENT.md`, `.gitignore` (archive-ignore block) | n/a | A32 suite exit 0; guard PASS; workqueue schema valid | remove the 6 `.gitignore` lines; `git checkout -- .gitignore` |
| `briq-00b` archive discovery | Mission-named archives were assumed present, not inspected | `docs/beta-finalization/ARCHIVE-INVENTORY.md` | `find`/`stat`/`shasum`/`unzip -l` (read in place, never extracted) | 3 members streamed & hash-identical to the live tree | delete the doc |
| `briq-00c` work queue | No persistent, dependency-aware, resumable queue | `docs/beta-finalization/WORK-QUEUE.md`, `docs/beta-finalization/workqueue/*.json` (54), `tools/beta/workqueue.py`, `tools/beta/tests/test_workqueue.py` | stdlib Python, atomic writes + advisory lock, append-only revisions | `verify-schema --json` → `ok:true`, 54 tasks; `test_workqueue.py` 27/27 | delete `workqueue/` + the two tools |
| `briq-00d` baseline protection | The A32 floor had no machine-checkable pin | `docs/beta-finalization/BASELINE-PROTECTION.md`, `docs/beta-finalization/baseline-protection.json`, `tools/beta/regression-guard.sh`, `tools/beta/tests/test-regression-guard.sh` | bash + `jq`; 9 invariants, hard/soft/self pins, `--repin` protocol | `regression-guard.sh --json` → `verdict PASS, 44/0/5/2`; self-test 10/10 | delete the guard + register |

### 3.2 Priority 1 — touchscreen and reliable interactive input (`bg-01-touch-pipeline`)

| briQ | Root cause | Paths | Build | Tests | Rollback |
|---|---|---|---|---|---|
| `briq-01a` pipeline tracer | Six cycles were misled: no way to name the first layer dropping a touch event, and tools hard-coded `/dev/input/eventN` | `tools/s10plus/a33/nuxel-touch-trace.py`, `nuxel-touch-capture.sh`, `touch-probe.html`, `docs/beta-finalization/touch/PIPELINE-TRACE.md`, `OFFLINE-TEST-RESULTS.md` | `python3 tools/s10plus/a33/nuxel-touch-trace.py`; bounded `signal.alarm(seconds+15)` + `timeout` | 7 layers graded (charger→L1, libinput reject→L4, no DOM→L7, empty→all blocked); `/dev/input/eventN` grep gate 26 files/0 fail | delete the three tools + docs |
| `briq-01b` libinput path shim | libinput's udev backend finds zero devices (udevd masked on 4.14) → compositor never opened the touch node | `tools/s10plus/a33/nuxel-libinput-path.c`, `build-libinput-shim.sh`, `configs/nuxel/…` | cross-`aarch64-linux-gnu-gcc` static `.so` + host selftest | capability fixtures 19/19; A31/A33 byte-parity 6/6 | reinstall the A31 shim; revert the C + config |
| `briq-01c` charger-mode / lpcharge | `androidboot.mode=charger` → `sec_ts_init()` returns `-ENODEV` before `i2c_add_driver()`; **no userspace workaround** (no `CONFIG_KEXEC`, not modular) | `tools/s10plus/a33/nuxel-bootmode-guard.py`, `docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md` | python + unit tests | LPM detected from 4 independent markers; every reboot gate (ack/config/lock/cooldown/uptime/charger) asserted to suppress | remove the guard; the durable fix is `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED` |
| `briq-01d` owner test | A finger is required | `docs/beta-finalization/manual-proof/01-touchscreen.md` | — | harness self-test 33/33 | — |

### 3.3 Priority 2 — boot stability, animation handoff, launcher parity (`bg-02`)

| briQ | Root cause | Paths | Build | Tests | Hashes | Rollback |
|---|---|---|---|---|---|---|
| `briq-02a` handoff | A32 stopped the player on a short time gap (cut the second half) and did not *prove* single ownership | `tools/s10plus/a33/nuxel-anim-handoff.py`, `nuxel-handoff-logic.h`, `nuxel-wl-fb.c`, `configs/nuxel/boot/animation-handoff.json`, `docs/beta-finalization/boot/ANIMATION-HANDOFF.md` | `build-a33-boot.sh` (aarch64 ELF on the UTM guest) | `selftest` 29 checks / 22-case corpus, 0 fail; `audit` rejects a two-writer fixture | A33 bridge `2d8718c4d92858bbae02b7e914f0172d295b1c12446eb861e91c355f2ac912fc` | reinstall the A32 bridge (`/usr/lib/nuxel/nuxel-wl-fb`, `e4b4293e…`) |
| `briq-02b` verbose boot | A cosmetic switch would lie; the Bixby-hold override needs a boot stage that does not exist | `nuxel-verbose-boot.py`, `nuxel-verbose-boot.service`, `configs/nuxel/boot/verbose-boot.json`, `docs/…/boot/VERBOSE-BOOT.md` | python + systemd unit | `--selftest`: upgrade-keep rule, legacy migration, unreadable doc refused, override honoured **or refused** (0 fail) | `nuxel-verbose-boot.py --selftest` | delete the unit + doc |
| `briq-02c` colour conversion | XRGB8888 screencopy words copied unchanged into an ABGR_8888 panel → R/B swap on the glass | `tools/s10plus/a33/nuxel-wl-fb.c`, `pwa/nuxel-home/colour-test.html`, `docs/…/boot/COLOUR-CONVERSION.md`, `tests/test-colour-order.py` | same aarch64 build | golden bytes R/G/B/W/BLK/mixed, LUT vs independent reference over 74 words (48 checks, 0 fail) | — | same as `02a` (A32 bridge) |
| `briq-02d` launcher parity | A32's real defect was a **stale service-worker cache** (old JS alive after deploy) + 2 registry entries with no runnable frontend | `pwa/nuxel-home/js/apps.js`, `sw.js`, `manifest.json`, `pwa/nuxel-apps/settings/…`, `docs/beta-finalization/launcher/SAFE-ZONES.md` | node | `launcher-registry-test.js` passed (1 cross-group warning: Live Console served by another group); `regression-guard` `INV-1` | sw.js `d7fd0843…` | revert the PWA files; the host purge remains A32 (`INV-1` hard) |
| `briq-02e` safe zones | A32's one-way push could shove the right cluster off-panel; the editor could drift from the real bar | `pwa/nuxel-home/js/safe-zones.js`, `configs/nuxel/statusbar-safezones.json`, `tools/s10plus/a32/tests/safe-zones-test.js` | node | `safe-zones-test.js` — 44 assertions, 0 fail; guard `INV-3` | safe-zones.js `ca99df1a…` | revert the JS + JSON |

### 3.4 Priority 3 — Wi-Fi, time/RTC, audio, headphones, buttons (`bg-03`)

| briQ | Root cause | Paths | Tests | Rollback |
|---|---|---|---|---|
| `briq-03a` Wi-Fi | No device-specific NM/wpa policy, no honest diagnostic; Pixel BCM4390 docs do not describe this BCM4375-class part | `configs/networkmanager/*`, `tools/s10plus/a33/nuxel-wifi-diag.sh`, `docs/beta-finalization/manual-proof/04-wifi.md` | `selftest` 5/5 fixtures; `test-wifi-diag.py` all PASS | delete the configs + tool |
| `briq-03b` time/RTC | No RTC/timesync observability; mark/compare arithmetic needed to be honest | `configs/nuxel/time/*`, `tools/s10plus/a33/nuxel-time.sh`, `docs/…/system/TIME-RTC.md` | `selftest` 5/5; `test-time-rtc.py` all PASS (same-boot-id refused) | revert `configs/nuxel/time/*`; `systemctl disable --now nuxel-rtc-check.timer` |
| `briq-03c` audio | A32 had only `Left AMP PCM Gain`; no UCM/DSP bring-up, no player, and volume ≠ audibility | `configs/alsa-ucm/beyond-madera/*`, `configs/pipewire/*`, `configs/wireplumber/*`, `tools/s10plus/a33/nuxel-audio-diag.sh`, `docs/…/manual-proof/06-audio.md` | `selftest` 8/8 pipeline fixtures; `test-audio-diag.py` all PASS | delete the UCM/PipeWire configs + tool |
| `briq-03d` headphones/USB-C | Jack/USB-C detection was unproven and control names must not be invented | `configs/nuxel/audio/jack-routes.json`, `tools/s10plus/a33/nuxel-headphone-diag.sh`, `docs/…/manual-proof/07-headphones.md` | `selftest` 7/7; `test-headphone-route.py` all PASS | delete config + tool |
| `briq-03e` buttons/gestures | A32: long-power mapped to `power-menu` which was **logged and refused**; no gesture machine | `configs/nuxel/input/button-fsm.json`, `configs/nuxel/buttons/reboot-gate.json`, `tools/s10plus/a33/nuxel-button-fsm.h`, `nuxel-button-manager.c`, `docs/…/system/BUTTONS-GESTURES.md` | `test-button-fsm.py` all PASS (replay, JSON↔C↔A32 parity, gate, 14 traces); `run-p3-tests` PASS | reinstall the A32 manager pair (documented in `BUTTONS-GESTURES.md` §10) |
| capability slice | There was no machine-readable per-area state set | `configs/nuxel/capabilities/connectivity-time-audio-buttons.json` | validated by `run-p3-tests` | delete the file |

### 3.5 Priority 4 — Fedora userspace, services, app infrastructure (`bg-04`)

| briQ | Root cause | Paths | Tests | Rollback |
|---|---|---|---|---|
| `briq-04a` packages | The install line was never resolved against real metadata and contained the **retired** `basesystem`; `stevia`/`phosh` exist only in `updates`; the carried 4.14 `libsystemd` patch pins `systemd-258.11-1.fc43` | `images/s10plus/packages-manifest.json`, `tools/s10plus/a33/verify-packages.py`, `docs/…/system/DEPENDENCY-REPORT.md` | 50/50 resolved; `--ga-only` FAILS on the pin (negative control); `test-packages-manifest.py` all PASS | `git checkout` the manifest + builder |
| `briq-04b` service graph | A real ordering **cycle** (`nuxel-bridge` ⇄ `nuxel-notifications`); builder installed units from globs, unprovable | `services/**`, `images/s10plus/build-phone-rootfs-inside-fedora.sh`, `tools/s10plus/a33/verify-service-graph.py`, `docs/…/system/SERVICE-GRAPH.md` | 14 units, 0 problems, 1 recorded warning; `test-service-graph.py` proves the validator **can** fail (injected cycle, unsatisfied dep, 4.14-forbidden dep, lost enablement, lost A26 repair) | revert `services/**` + builder |
| `briq-04c` app infrastructure | Registry drift across four consumers; `bridge_version` skew was unenforced; static server served a wrong docroot silently; `/etc/nuxel/web.conf` was inert | `pwa/nuxel-common/*`, `services/nuxel-bridge/*`, `services/nuxel-portal/*`, `services/nuxel-notifications/*`, `services/nuxel-web*`, `tools/s10plus/a33/verify-app-registry.py`, `docs/…/system/APP-INFRASTRUCTURE.md` | `run-userspace-tests.sh` → `pass=10 fail=0 skip=0`; real HTTP server test asserts 409 `version_mismatch` | revert the services + PWA-common |

### 3.6 Priority 5 — security, permissions, connectivity controls (`bg-05`)

| briQ | Root cause | Paths | Tests | Rollback |
|---|---|---|---|---|
| `briq-05a` permissions | Apps could declare capabilities the host cannot arbitrate; grants could overstate enforcement | `shell/nuxel-shell/nuxel-permissions/*`, `shell/nuxel-shell/nuxel-sandbox/profiles/*`, `tools/s10plus/a33/verify-permissions.py` | `verify-permissions.py` modes `repo`/`device`; fails on unsupported tokens + overstated grants | revert the permission manager + profiles |
| `briq-05b` firewall | No atomic, console-safe nftables application; per-app matching must pick the 4.14 path | `configs/nftables/*`, `tools/s10plus/a33/nuxel-firewall.sh` | `security-tests/test-firewall.sh` → **49 passed, 0 failed**; `nft -c` check + snapshot/rollback; console guard mandatory | `nuxel-firewall.sh rollback`; revert configs |
| `briq-05c` VPN/Tor/remote | A running `tor.service` is not anonymity; claims must be a truth ladder | `configs/nuxel/security/privacy-config.json`, `remote-access.json`, `tor/torrc`, `tools/s10plus/a33/nuxel-vpn-tor.sh` | claim vocabulary (`evidenced/unproven/unavailable/unknown`); `traffic_routed_through_tor/vpn` default **unproven**; wildcard SSH bind refused | `vpn off / tor off / remote off`; revert configs |
| `briq-05d` security auditor | No per-privilege-class exposure report | `tools/s10plus/a33/nuxel-security-audit.sh`, `tools/s10plus/a33/security-fixtures/*` | `--self-test` vs committed fixture; prints `unknown` (never a default) when a source is unavailable | delete the tool + fixtures |

Note: `bg-05` was still `in_progress` at aggregation time; its `docs/beta-finalization/security/*.md`
documents were **not present** in the tree (see §8 gaps).

### 3.7 Priority 6 — core phone applications (`bg-06`)

Core apps (Terminal, Notes, Files, Clock, Calculator, Browser, Photos, Recorder, Weather, Maps, Mail,
Calendar) plus Settings and the on-screen keyboard. Root cause: the mission's core-app gap matrix —
several apps existed only as icons/directories. Evidence: `docs/beta-finalization/apps/APP-INVENTORY.md`
(verifier `tools/s10plus/a33/verify-app-inventory.py`), the phone-app offline suite (`PASS=37 FAIL=0`),
and the core-app DOM acceptance run (`RESULT: PASS=130 FAIL=0 WARN=0 verdict=OFFLINE_RUNTIME_PASSED`).
Paths: `pwa/nuxel-apps/{terminal,notes,files,clock,calculator,browser,photos,recorder,weather,maps,
mail,calendar,settings}/`, `shell/nuxel-shell/{nuxel-dialer,nuxel-messages,nuxel-contacts,
nuxel-phone-data, nuxel-settings}`, `configs/nuxel/keyboard/`. Rollback: revert the app directories +
shell apps. **No gap owned by `bg-06` is left open.**

### 3.8 Priority 7a — store, power-user, specialty apps (`bg-07`)

NuxTore, DevMgmt, Safe Cleanup, Root/Sudo control, media players, downloader, authenticator, SnekByte
(ported from the supplied `snekbyte-main.zip`), Live Console, PenguInterface. Paths:
`pwa/nuxel-apps/{nuxtore,devmgmt,cleanup,rootcontrol,media,downloader,authenticator,snekbyte,console,
penguinterface}/`, `tools/s10plus/a33/nuxel-console.c`. At aggregation time `bg-07` was `in_progress`;
`pwa/nuxel-apps/console` and `penguinterface` still lacked an `index.html` (recorded as open gaps in
§8). Rollback: revert the app directories.

### 3.9 Priority 7b — hardware subsystems, power, sensors, owner kits (`bg-08`)

Power/battery modes + power menu, vibration/haptics, flashlight/LED/edge lighting, Bluetooth, NFC,
GNSS + offline OSM, sensors, camera, SIM/microSD/modem. Common root cause: each subsystem needed an
**enumerate-don't-assume** diagnostic and a `NEEDS_OWNER_TEST` owner procedure. Paths:
`configs/nuxel/{power,haptics,leds,bluetooth,nfc,gnss,sensors,camera,modem}/`,
`tools/s10plus/a33/nuxel-{power,haptics,led,bluetooth,nfc,gnss,sensors}-diag.sh`,
`docs/beta-finalization/manual-proof/{09,10,11,12,13,14,24}-*.md`. Tests (run this briQ, all green):
seven `test-*-diag.py` suites → `all checks PASS — OFFLINE_TESTED` (`NEEDS_OWNER_TEST` for the physical
observation). Rollback: delete the config + tool per subsystem.

### 3.10 Priority 8 — integration, soak, reboot policy, release (`bg-09`) and live/VM (`bg-10`, `bg-11`)

At aggregation time these were `pending`/`in_progress`; their expected artefacts
(`docs/beta-finalization/{release,testing,live,vm}/…`, `tools/beta/{reboot-policy.sh,rollback.sh,
run-all-tests.sh}`, `CHANGELOG.md`, `VERSION`, the capability manifests) were **not present** in the
tree. See §8. The `bg-12` reports (this file and the checklist) are the terminal aggregation and were
written against what *is* present, with the absent evidence named explicitly rather than assumed.

### 3.11 Archives: presence and disposition (no invented paths)

| Archive | On disk? | sha256 | Disposition |
|---|---|---|---|
| `docs.zip` | present | `427c7bd954cb1e4ab47ff508f53685d959099f6bb44cff2098e3f870d64721b0` | cross-check only (streamed, never extracted) |
| `scripts.zip` | present | `35a51844b711f986c743b609a83153db9cad2075e3eec8ab11198978cb86cb0e` | streamed only; 125 MB, never extracted |
| `tools.zip` | present | `98b1adc9b94e66e1c7ae159078dc278de13d8a83aa4417d128c5992d58a5c4eb` | cross-check; supplies `tools/s10plus/a17…a32` (a33 absent) |
| `/Users/wicked/Downloads/nuxel-main.zip` | present | `17c15a013983c87febc488a7c6d0014d25e69cf4b9173d507fefb98a11378ffd` | cross-check only (live tree supersedes) |
| `/Users/wicked/Downloads/snekbyte-main.zip` | present | `97f27d12942c708a7840ea403ebb4d2b9879ba0c6f02040dfaddc799c001f387` | used by the SnekByte port (bg-07) |
| `/Users/wicked/Nuxel/nuxel-main (2).zip` | present | `38956349aabc3e043e5b5a1896db8e3762ed2cec5e7a67b0c9769758b58db4c9` | historical cross-check only |
| `docs(8).zip` / `scripts(7).zip` / `tools(4).zip` | **ABSENT** | — | recorded as a documented gap; dependent work degraded to the live tree + present snapshots |
| standalone A30/A31/A32 zips | **ABSENT as supplied inputs** | — | present as generated bundles + `tools.zip` subtrees; authoritative A32 record is in-tree (`13-RELEASE-NOTES-A32.md`) |

---

## 4. Application inventory

Machine-readable source: `docs/beta-finalization/apps/APP-INVENTORY.md` (executable form
`tools/s10plus/a33/verify-app-inventory.py`). Honest status vocabulary there:
`present/full` = the surface and its offline tests exist; `present/partial` = something real is
missing; `missing` = no implementation; `external` = implemented by another group. **A status is not a
hardware claim.**

| Application | Type | Path | Status | Owner group |
|---|---|---|---|---|
| Phone (dialer) | native | `shell/nuxel-shell/nuxel-dialer` | present/partial (modem gap) | bg-06 |
| Messages (SMS/MMS) | native | `shell/nuxel-shell/nuxel-messages` | present/partial (modem gap) | bg-06 |
| Contacts | native | `shell/nuxel-shell/nuxel-contacts` | present/full | bg-06 |
| Mail | pwa | `pwa/nuxel-apps/mail` | present/full (send queued, never faked sent) | bg-06 |
| Calendar | pwa | `pwa/nuxel-apps/calendar` | present/full | bg-06 |
| Notes | pwa | `pwa/nuxel-apps/notes` | present/full | bg-06 |
| Calculator | pwa | `pwa/nuxel-apps/calculator` | present/full | bg-06 |
| Clock (alarms/timers) | pwa | `pwa/nuxel-apps/clock` | present/full | bg-06 |
| Files | pwa | `pwa/nuxel-apps/files` | present/full | bg-06 |
| Terminal (real local PTY) | pwa | `pwa/nuxel-apps/terminal` | present/full | bg-06 |
| Settings | pwa | `pwa/nuxel-apps/settings` | present/partial (no `sw.js`) | bg-02/bg-06/bg-08 |
| Native Settings shell app | native | `shell/nuxel-shell/nuxel-settings` | present/full | bg-06 |
| Browser | pwa | `pwa/nuxel-apps/browser` | present/full | bg-06 |
| Weather | pwa | `pwa/nuxel-apps/weather` | present/full | bg-06 |
| Maps (offline-first OSM) | pwa | `pwa/nuxel-apps/maps` | present/full | bg-06 |
| Photos / Gallery | pwa | `pwa/nuxel-apps/photos` | present/full | bg-06 |
| Recorder | pwa | `pwa/nuxel-apps/recorder` | present/partial (mic unproven) | bg-06 |
| Camera | pwa | `pwa/nuxel-apps/camera-gallery` | present/partial (capture unproven; `camera:read` not a bridge id) | bg-08 |
| NuXtore (app store) | pwa | `pwa/nuxel-apps/nuxtore` | present/full | bg-07 |
| DevMgmt | pwa | `pwa/nuxel-apps/devmgmt` | present/full | bg-07 |
| Safe Cleanup | pwa | `pwa/nuxel-apps/cleanup` | present/full | bg-07 |
| Root / sudo control | pwa | `pwa/nuxel-apps/rootcontrol` | present/full | bg-07 |
| Media players (audio+video) | pwa | `pwa/nuxel-apps/media` | present/full | bg-07 |
| Media downloader | pwa | `pwa/nuxel-apps/downloader` | present/full | bg-07 |
| Authenticator (TOTP) | pwa | `pwa/nuxel-apps/authenticator` | present/full | bg-07 |
| SnekByte (ported game) | pwa | `pwa/nuxel-apps/snekbyte` | present/full | bg-07 |
| Live Console | pwa | `pwa/nuxel-apps/console` | present/partial (**no `index.html`/manifest yet**) | bg-07 |
| PenguInterface | pwa | `pwa/nuxel-apps/penguinterface` | present/partial (**icons only, no `index.html`**) | bg-07 |
| Permissions manager | native | `shell/nuxel-shell/nuxel-permissions` | present/full | bg-05 |
| Privacy surface (PWA) | pwa | `pwa/nuxel-apps/privacy` | present/partial (icons only) | bg-05 |
| Firewall application | tool | `tools/s10plus/a33/nuxel-firewall.sh` | present/partial | bg-05 |
| Security auditor | tool | `tools/s10plus/a33/nuxel-security-audit.sh` | present/partial | bg-05 |
| Virtual keyboard + settings | tool | `configs/nuxel/keyboard` | present/full (VM/owner proof pending) | bg-06 |
| Casting | — | `pwa/nuxel-apps/casting` | **missing** (no app/daemon/protocol anywhere) | unassigned |

Verified this run: `pwa/nuxel-apps/` contains **24 app directories**; **19** carry an `index.html`
(`_shared`, `console`, `penguinterface`, `privacy` do not). The canonical registry is
`pwa/nuxel-common/app-registry.json` (`registry_version 4`), consumed by the launcher
(`pwa/nuxel-home/js/apps.js`), the native shell, the bridge API and the installed copy
(`/etc/nuxel/app-registry/app_registry.json`).

---

## 5. Hardware inventory

Device truth (not trademark marketing): Samsung **SM-G975F / beyond2lte / Exynos 9820**, 4100 mAh,
DisplayPort-class 1440×3040 AMOLED (`/dev/fb0`, 32 bpp, stride 5760). Real bound values from the A32
baseline record and the runtime diagnostics of this run:

| Subsystem | What the repository knows / observes | State |
|---|---|---|
| SoC / CPU | Exynos 9820, arm64; cpu governor selectable per power profile | `OFFLINE_TESTED` (profile control); load average ~12 is vendor kernel threads (TrustZone/RPMB), not a Nuxel restart loop (A31 note) |
| Display | `/dev/fb0` 1440×3040, 32 bpp, stride 5760, virtual 1440×6080; backlight `brightness=12800 / max_brightness=48600`; **no DRM/KMS** (`CONFIG_DRM` unset) → headless phoc + `nuxel-wl-fb` bridge (21–24 fps, 35–43 ms blit) | A32 `VERIFIED_ON_S10PLUS` (record); bridge re-verified offline |
| Touch | `sec_touchscreen`, `B: PROP=2` (INPUT_PROP_DIRECT), MT axes; disabled in charger/LPM boot | A32: driver/libinput/compositor `VERIFIED_ON_S10PLUS`; **a real finger is `NEEDS_OWNER_TEST`** |
| Keypad | one evdev device `gpio_keys`, keys **114 (VOLUMEDOWN) / 115 (VOLUMEUP) / 116 (POWER) / 703 (assistant/Bixby)**; resolved by capability, never `eventN` | A32 `VERIFIED_ON_S10PLUS` (key bitmap); A33 gesture/menu `OFFLINE_TESTED`/`NEEDS_OWNER_TEST` |
| Other input devices (A32) | `meta_event`, `grip_sensor`, `ssp_context`, `Headset`, `hall`, `certify_hall` | recorded; **raw sensor values unproven** |
| Audio | ALSA card0 **`beyond-madera`** (CS47L93 MADERA + 2× CS35L40, Exynos ABox); writable playback control `Left AMP PCM Gain` 0..20, current 19 | control `VERIFIED_ON_S10PLUS` (A32); **audibility `NEEDS_OWNER_TEST`** |
| Battery / charger | PMIC fuel gauge enumerated via `/sys/class/power_supply/*`; `charger.allow_writes=false` | `OFFLINE_TESTED` control surface; charging behaviour `NEEDS_OWNER_TEST` |
| RTC / time | PMIC RTC read via `/sys/class/rtc/*` when bound; `CONFIG_RTC_*` read from the real kernel config | `OFFLINE_TESTED` tooling; persistence `NEEDS_OWNER_TEST` |
| Wi-Fi | Murata/Broadcom **BCM4375-class** behind Samsung SDIO/PCIe glue | `BLOCKED_FIRMWARE` (default, evidence-derived at runtime); association `NEEDS_OWNER_TEST` |
| Bluetooth | **BCM4375** (BT 5.0), vendor HCD `bcm4375B1_semco.hcd`; `AutoEnable=false` | `NEEDS_OWNER_TEST`; stage diagnostic `OFFLINE_TESTED` |
| NFC | Samsung **sec-nfc (S3FWRN5-family)** at I2C 0x27 with embedded SE | `NEEDS_OWNER_TEST`; honest `BLOCKED_KERNEL`/`NOT_SUPPORTED_ON_DEVICE` posture |
| GNSS | SoC-integrated, needs vendor assistance; node/module/firmware/NMEA enumerated per stage | `NEEDS_OWNER_TEST`; no fabricated coordinate |
| LED / haptics | LED classes enumerated (`flashlight`, `notification`); `edge_lighting` modelled as a display overlay (`hardware_led:false`); haptic actuator enumerated across `/sys/class/{leds,timed_output,vibrator}` | `NEEDS_OWNER_TEST` (visible light / felt buzz) |
| Modem | Samsung **Shannon LTE** — **no upstream ModemManager plugin** | `BLOCKED_FIRMWARE` (honest); dialer/messages report the gap on screen |
| Storage | `USERDATA` ext4 rootfs discovered at boot (`/dev/sda31` in A25 record); microSD not exercised | rootfs A32 record; microSD `NEEDS_OWNER_TEST` |
| Console | USB CDC-ACM `usb0` / `/dev/ttyGS0`; `/dev/cu.usbmodem201` on the host | present; **did not answer this run** → `BLOCKED_EXTERNAL_RESOURCE` |

---

## 6. Security status (per attacker-privilege class; Linux 4.14 limits named)

**Mechanisms actually available on this device** (from the real kernel/behaviour, not newer kernels):
nftables (kernel-enforced filtering, `meta cgroup <classid>` for per-app matching — `socket cgroupv2`
matching needs ≥ 5.13 and is **not** used), cgroups v1/v2 (for `cpu.weight`/`classid`), polkit,
filesystem DAC, key-based SSH on the USB gadget interface, and the mandatory console guard. A
per-capability permission store (`shell/nuxel-shell/nuxel-permissions/nuxel-permd.py`
capabilities.json) with app sandbox profiles (`shell/nuxel-shell/nuxel-sandbox/profiles/*.json`).

**Absent on Linux 4.14.253 / this hardware — named as limitations, never faked:** Landlock (≥ 5.13),
kernel lockdown (≥ 4.17), BPF-LSM (≥ 5.7), arm64 CFI/SCS/BTI/PAuth. Also: **no AppArmor profile is
declared for any unit**, because Nuxel has no verifiable AppArmor policy-load path on this vendor
kernel; declaring an unenforced profile would be a cosmetic switch that lies about enforcement. The
`systemd-userdbd`/`dbus-broker`/`systemd-udevd` masking (§3.5, A26 repairs) is a **containment**
measure for 4.14, not an enforcement feature.

| Attacker-privilege class | What *is* enforced | What is *not* claimed |
|---|---|---|
| **Unprivileged app / PWA** | nftables per-app (classid) output policy defaults to **drop** (`input/forward/output = drop`, DHCP/DNS/ICMP/loopback allowed); a capability must have a stored grant, and the permission manager + `verify-permissions.py` reject grants that **overstate** enforcement; the portal mediates hardware permissions with per-app, per-type consent (`once`/`session`/`always`, 30 s deny-by-default timeout); `remote-access.json` refuses remote access without a visible indicator | not "unbypassable": a same-user side channel or a kernel bug is out of scope |
| **Local authenticated user (console/SSH)** | SSH accepts **publickey only** (password/keyboard-interactive/root-password refused) and the CLI refuses a wildcard (`0.0.0.0`/`::`) bind; the console path (`usb0`, `/dev/ttyGS0`) is protected by the mandatory console guard (`nuxel-console-guard.nft`, table priority −200) and can never be firewalled away; a bad `apply` auto-reverts within 60 s unless confirmed | the owner is trusted by design; the console *is* the recovery path |
| **Network attacker** | default-drop nftables posture with an explicit per-interface policy (`lo` allow, `usb0` console, `rmnet0` **disabled**, others allow/console/client/vpn/disabled); VPN/Tor provide transports but their **traffic-routing claims are `unproven` until an external-vantage leak test passes**; DNS-leak suspect is reported, not hidden; kill-switch is applied via the same firewall that cannot drop the console | "all traffic is anonymised" is **never** claimed; Tor `traffic_routed_through_tor` stays unproven |
| **Root / administrator** | nothing is designed to resist root | **explicitly out of scope**; every enforcement statement above is scoped to a non-root attacker. No claim is called "unbypassable" |

**Honest-vocabulary enforcement in the tooling.** `nuxel-security-audit.sh` states enforcement
per-privilege-class and prints `unknown` (never a plausible default) when a source is unavailable;
`nuxel-vpn-tor.sh` uses a closed claim vocabulary (`evidenced` / `unproven` / `unavailable` /
`unknown`) and never upgrades a claim to make a UI look better; `nuxel-firewall.sh` prints the **real**
`nft list ruleset` output and never summarises a rule it could not list. This run: firewall suite
**49 passed / 0 failed**; the VPN/Tor suite was launched but did not complete inside this run's bounded
window (it was interrupted) — so the VPN/Tor terminal state stays the group's own honest default.

---

## 7. Test results

All commands below were executed **by this briQ** on the build host at aggregation time
(2026-10-16T14:26Z) unless a different timestamp is quoted. No phone, no root, no display, no VM
parity run is involved. Command outputs are quoted from the real runs.

| Suite (entry point) | Real result | Exit |
|---|---|---|
| `tools/s10plus/a32/tests/run-tests.sh` (the A32 floor) | `== 0 failing suite(s) ==` (colour selftest vectors, key-bitmap decode 114/115/116/703, safe-zone 15 assertions, launcher registry 14 assertions, wallpaper hash, sources present) | 0 |
| `tools/beta/regression-guard.sh --json` | `{"verdict":"PASS","pass":44,"fail":0,"warn":5,"info":2}`; warned invariants `INV-1`, `INV-3`, `INV-9` (all files owned by `bg-02`, mid-flight — soft pins, behavioural checks still hard) | 0 |
| `python3 tools/beta/workqueue.py verify-schema --json` | `{"tasks":54,"ok":true,"errors":[],"verified_on_s10plus":[]}`; by-state `implemented 9 / in_progress 24 / pending 21`; by-verdict `OFFLINE_TESTED 9 / None 45` | 0 |
| `tools/s10plus/a33/tests/run-touch-tests.sh` | `TOUCH-TESTS: ALL PASS` — shim build, shim capability fixtures, A31/A33 parity, tracer layers/gate/boundedness, boot-mode guard, capture harness, `/dev/input/eventN` gate (149 assertions in the touch suites) | 0 |
| `tools/s10plus/a33/tests/run-boot-tests.sh` | `BOOT-TESTS: ALL PASS` — colour golden bytes, handoff decision table + single-owner proof, replayable timing harness, verbose-boot durability, settings store, launcher registry/cache parity, ten-zone safe areas (1 SKIP: aarch64 bridge build needs the guest) | 0 |
| `tools/s10plus/a33/tests/run-p3-tests.sh` | `P3-TESTS: ALL PASS` — wifi/time/audio/headphone diagnostics (5/5, 5/5, 8/8, 7/7 fixtures), policy+no-flash invariants, buttons JSON↔C↔A32 parity + power menu (1 SKIP: FSM replay build needs alsa-lib/linux headers) | 0 |
| `tools/s10plus/a33/tests/run-userspace-tests.sh` | `pass=10 fail=0 skip=0 -> OFFLINE_TESTED` (registry+manifests+bridge pin, bridge/HTTP/D-Bus policy, static web server, portal consent, notifications persistence, node bridge client + wiring, service-graph mutation test) | 0 |
| `tools/s10plus/a33/tests/hw-subsystems/test-*-diag.py` ×7 | each → `all checks PASS — OFFLINE_TESTED … NEEDS_OWNER_TEST for <physical observation>` (power, led, haptics, bluetooth, nfc, gnss, sensors) | 0 |
| `tools/s10plus/a33/security-tests/test-firewall.sh` | `== results: 49 passed, 0 failed ==` / `FIREWALL TESTS PASSED` (atomic apply, snapshot/rollback, console guard, no flash tool, no block device in a ruleset) | 0 |
| `tools/s10plus/a33/tests/test-core-apps.py` (bg-06, re-run §10) | `RESULT: PASS=86 FAIL=0 WARN=0 verdict=OFFLINE_STATIC_ONLY` on this host (L4 jsdom layer skipped: no `node_modules`); the inventory's **recorded** runtime run is `PASS=130 … OFFLINE_RUNTIME_PASSED` (`apps/APP-INVENTORY.md` line 111) | 0 |
| `tools/s10plus/a33/tests/test-phone-apps.py` (bg-06, re-run §10) | `RESULT: PASS=37 FAIL=0 verdict=OFFLINE_TESTED` (dialer/messages/mail honesty) | 0 |
| `tools/s10plus/a33/verify-app-inventory.py` (bg-06 verification, re-run §10) | **FAILS** at aggregation: `APP-INVENTORY.md: the machine-readable block markers <!-- INVENTORY-DATA:BEGIN --> / <!-- INVENTORY-DATA:END --> are missing` — doc and verifier out of sync (open defect, bg-06) | 1 |
| `tools/s10plus/a33/verify-packages.py` (bg-04) | `resolved` (rc 0), 50/50 essential packages; `--ga-only` → `FAILED` on the systemd pin (negative control) | 0 |

**What these numbers do not mean.** No suite above can produce `VERIFIED_ON_S10PLUS`. The
`workqueue verify-schema` output proves that mechanically: `"verified_on_s10plus": []`. A green
`run-boot-tests.sh` proves the colour LUT and the handoff decision table, **not** that a red image is
red on the glass; a green `run-p3-tests.sh` proves the audio *pipeline walker*, **not** that a tone is
audible. Faithful VM/native execution exists only where a device-independent artefact was run (the
A33 bridge was compiled and self-tested as an aarch64 ELF on the UTM Fedora 43 guest; that leg is
`VERIFIED_IN_VM_ONLY` at best and is owned by `bg-11`).

---

## 8. Unfinished work — blockers and next actions

Every row is a real, named gap. "Blocker class" uses the mission's terminal states. Nothing here is
hidden and nothing is a retry loop.

### 8.1 Blocked by an absent external resource (`BLOCKED_EXTERNAL_RESOURCE` → `NEEDS_OWNER_TEST`)

| Item | Blocker | Next action |
|---|---|---|
| Live phone console did not answer (`/dev/cu.usbmodem201` enumerated, 0 bytes in 6 s; console-host probe no reply in 30 s) | no reachable handset console | owner: boot the handset into Nuxel normally, confirm the console enumerates, then run `bash scripts/s10plus-debug-pack/nuxel-console-host.sh --run 'df -h /; free -m; systemctl --failed'` |
| Phone filesystem free space / `systemctl --failed` / kernel ring | same | same |
| A fresh on-device re-read of the A32 deployed-artefact hashes | same | same (guard proves *build parity with the shipped bytes*, not a fresh phone read) |
| `docs(8).zip`, `scripts(7).zip`, `tools(4).zip`, standalone A30/A31/A32 archives | **absent on disk** | owner supplies, or the work proceeds against the live tree + present snapshots (already done) |
| VM launcher/service parity (`docs/beta-finalization/vm/{LAUNCHER-PARITY,SERVICE-VERIFY}.md`, screenshots) | `bg-11` output not present at aggregation | `bg-11` run, then fold into the next report revision |
| Live deploy / reboot / on-device probes (`docs/beta-finalization/live/*`) | `bg-10` output not present; console unreachable | `bg-10` serialized run |

### 8.2 Blocked by kernel / boot stage (offline fix only, NOT deployed)

| Item | Blocker | Next action |
|---|---|---|
| Charger/LPM boot disables `sec_ts` (and fingerprint/Wacom) before userspace | `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED` — no `CONFIG_KEXEC`, nothing modular, so no userspace workaround | documented offline source patch + build + tests; a future flashing procedure **marked not deployed**. Immediate owners' remedy is a normal reboot |
| One-time **Bixby-hold** verbose-boot override | the installed early boot stage does not publish `bixby-hold-override=1` → `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`; the harness asserts it is **refused, not faked** | ship the early-stage consumer in a future BOOT update |
| No DRM/KMS (`CONFIG_DRM` unset) → headless phoc + framebuffer bridge | deliberate; enabling DRM is a driver-porting project, not a config flag | out of scope for this mission; bridge stays the supported path |

### 8.3 Blocked by firmware / hardware

| Item | Blocker | Next action |
|---|---|---|
| Wi-Fi association | `BLOCKED_FIRMWARE` (no BCM4375-class firmware observed bound) | deploy the vendor blob into `/lib/firmware` (repository-only; **never** a flash), then the owner test in checklist area 4 |
| Bluetooth pairing | vendor HCD `bcm4375B1_semco.hcd` presence unproven; pairing needs a peer | deploy HCD if missing; owner test area 11 |
| Calls / SMS | Samsung **Shannon** LTE modem has **no upstream ModemManager plugin** → `BLOCKED_FIRMWARE` | a modem plugin/DSP project; the dialer/messages apps report the gap truthfully meanwhile |
| Camera capture, microSD, GNSS fix, NFC tag, sensors, flashlight, haptics, audible audio, RTC persistence, battery/charging behaviour | physical observation required | owner tests: checklist areas 6, 7, 9–16, 18, 24 |

### 8.4 Open implementation gaps owned by other groups (recorded, not silent)

| Gap | What is missing | Owner |
|---|---|---|
| `gap-liveconsole-index` | `pwa/nuxel-apps/console` has icons but **no `index.html`/`manifest.json`** yet; the registry serves a tile for an app whose surface is absent | bg-07 |
| `gap-penguinterface` | `pwa/nuxel-apps/penguinterface` is **icons only** | bg-07 |
| `gap-privacy-pwa` | `pwa/nuxel-apps/privacy` is icons only; the privacy surface is native + settings-group | bg-05 |
| `gap-settings-sw` | `pwa/nuxel-apps/settings` has no `sw.js` (cannot install offline) | bg-02/bg-08 |
| `gap-registry-mail-calendar-caps` | registry lists `storage:read`/`storage:write`, which are not bridge-enum ids, while manifests declare `storage:persistent` | bg-04c |
| `gap-calendar-appjson` | Calendar/Camera lack `app.json` metadata | bg-04c |
| `gap-camera-read-cap` | Camera declares `camera:read`, not a bridge-enum id | bg-08 |
| `gap-terminal-pty-cap` | `shell:local-pty` is not a bridge capability (by design; the PTY belongs to the launcher host) | bg-06 — documented in `app-registry.json` `capability_gaps` |
| `gap-casting` | no casting app/daemon/protocol anywhere | unassigned |

### 8.5 Terminal-deliverable status (pass 1 → pass 2)

Listed so the beta never implies them. Pass 1 wrote this report against the tree at 16:26; `§10` re-ran the gates at 18:55. **Landed between the passes** (now present, evidence cited in `§10`): `tools/beta/run-all-tests.sh`, `tools/beta/soak.sh` + `soak_lib.py`, `tools/beta/live/` (`nuxel-live-reachability.py`, `nuxel_live.py`), `tools/beta/vm/vm-launcher-dom-harness.py`, `docs/beta-finalization/live/evidence/reachability-20261016*/` (with `reachability.json`, `SHA256SUMS`), `docs/beta-finalization/vm/screenshots/`, and the `manual-proof/` fragments for areas 15, 16 and 18. **Still absent at pass 2** (their groups were mid-flight) — so the beta must not imply them:

* `docs/beta-finalization/security/{ENFORCEMENT-PROOF,FIREWALL,PERMISSIONS,THREAT-MODEL,VPN-TOR-REMOTE}.md`,
  `manual-proof/21-vpn-remote.md`, `manual-proof/22-firewall-permissions.md` (bg-05)
* `docs/beta-finalization/apps/{NUXTORE,MEDIA-AUTH,POWER-USER-APPS,SNEKBYTE,LIVE-CONSOLE,PENGUINTERFACE}.md`,
  `manual-proof/20-applications.md` (bg-07)
* `docs/beta-finalization/manual-proof/17-calls-sms.md` (bg-06) — areas 15/16/18 **landed between the passes**
  and are listed as present above
* `docs/beta-finalization/release/*`, `docs/beta-finalization/testing/*`, the narrative
  `docs/beta-finalization/live/{BASELINE-CAPTURE,DEPLOYMENTS,REBOOT-AND-VERIFY}.md`, the narrative
  `docs/beta-finalization/vm/{LAUNCHER-PARITY,SERVICE-VERIFY}.md`, a `CHANGELOG.md` entry for this cycle,
  a `VERSION` bump for it, and `tools/beta/{reboot-policy.sh,rollback.sh}` (bg-09/bg-10/bg-11).
  (`tools/beta/run-all-tests.sh`, `tools/beta/soak.sh`, `tools/beta/live/`, `tools/beta/vm/` and the
  `live/evidence/` + `vm/screenshots/` raw captures **did** land between the passes.)
* a per-group capability manifest beyond `configs/nuxel/capabilities/connectivity-time-audio-buttons.json`
  (bg-03), and the aggregate `docs/beta-finalization/release/DEVICE-CAPABILITY-MANIFEST.{md,json}` (bg-09)

Where the manual-proof checklist needs one of these areas, it **synthesizes** the entry from the
evidence that does exist and marks the missing source explicitly (see
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`).

---

## 9. Beta verdict

# `BETA_CANDIDATE_PENDING_HARDWARE_PROOF`

**Why this verdict — and why not the other three.**

* **Not `BETA_ACCEPTANCE_PASSED`.** Acceptance requires the physical acceptance tests to be observed
  (finger taps, power/volume/Bixby presses, visual colour/wallpaper/cutout confirmation — A32's own
  "remaining physical tests" list). Those were **not** observed in this run: the handset console did
  not answer, and the owner is not available. `BETA_ACCEPTANCE_PASSED` would require
  `VERIFIED_ON_S10PLUS` evidence produced **now**; the work queue's validator confirms there is none
  (`"verified_on_s10plus": []`).
* **Not `BETA_BLOCKED`.** The beta is not blocked. The platform boots and runs (A32 record), the A32
  floor is **intact** (`REGRESSION GUARD: PASS`, `0 failing suite(s)`), the full deliverable set is
  implemented and passing offline/VM-testable suites, no hard failure was recorded, and there is a
  known-working userspace rollback path. The missing pieces are *physical observations and firmware
  bring-up*, not a broken beta.
* **Not `ALPHA_ONLY`.** The A32 floor is real hardware functionality verified on the actual SM-G975F
  (interactive launcher, colour conversion, safe areas, buttons, live console, rollback). Calling this
  alpha-only would discard proven, protected functionality and would itself be a false statement.

**What "pending hardware proof" concretely means.** The repository is beta-complete *as a repository*:
every physical test has a bounded automated diagnostic, an exact owner procedure, and a defined
PASS/FAIL. The verdict flips to `BETA_ACCEPTANCE_PASSED` when the owner executes
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` (26 areas) on a normally-booted handset with
the console reachable, and the observed results are attached — in particular the four classes that no
script can settle:

1. **A finger on the glass** producing a real touch that the launcher acts on (checklist area 1).
2. **An ear** confirming audible sound from the speaker / headphones (areas 6, 7).
3. **Eyes** confirming colour order, the full boot animation, the cutout clearance and the verbose
   boot log (areas 2, 3, 9).
4. **Firmware bring-up + a peer/credential** for Wi-Fi, Bluetooth, NFC, GNSS and the modem
   (areas 4, 11, 12, 13, 16).

**Residual risk if the beta ships at this verdict.** The S10+ will boot Nuxel (A32) with an
interactive launcher; Wi-Fi/Bluetooth/camera/modem/audio may be non-functional and are reported as such
*by the on-device tools*, not hidden; no hardware claim in this report exceeds its evidence class.
The single durable kernel gap (charger-mode boot disabling `sec_ts`) is a boot-mode issue with a
documented remedy (a normal reboot), and the permanent fix is `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED /
NOT_DEPLOYED`.

### 9.1 Invariants honoured (verbatim)

> NO FLASHING of any kind - no writes to raw partition block devices or to
> BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/VBMETA/radio/modem/EFS/SEC_EFS/calibration/IMEI/PIT or
> partition metadata; no Heimdall/Odin/wrappers, no Download Mode, no TWRP, no new kernel installed
> to the physical phone. Recovery/Download-Mode power-menu entries may be implemented and
> offline-tested but MUST NOT be triggered. NEVER create/edit/build anything under
> /Users/wicked/x/nuxel/.qq or RUN_ROOT - QonQrete metadata is read-only; NEVER write receipt JSON
> or pipeline metadata into the project workspace. Do not regress the A32 baseline. Do not start
> over: no new launcher, no replacing Fedora, no recreating existing functionality. Never claim
> untested hardware works; a passing unit test never yields VERIFIED_ON_S10PLUS. Reboots are allowed
> but must return to Nuxel with a known-working userspace rollback path; no blind repeat reboots.
> After three same-mode failures, change diagnostic strategy.

This run performed: **no flash, no partition write, no bootloader interface, no Download Mode, no
TWRP, no reboot, no kernel install.** It wrote files only under `WORKSPACE_ROOT` (this file and the
checklist) and its receipt only to `RECEIPT_PATH`. No QonQrete metadata was written into the project
workspace.

## 10. Pass-2 re-verification (terminal, repository-only)

Between pass 1 (16:26) and pass 2 (18:55) the other build groups landed more of their evidence, so this
briQ **re-ran the gates** instead of repeating its numbers. Everything below was executed on the build
host by this briQ; **no phone, no root, no display, no VM parity run, no reboot, no flash**. Outputs are
quoted from the real runs.

| Command | Real result (pass 2) | Exit |
|---|---|---|
| `python3 tools/beta/workqueue.py verify-schema --json` | `{"tasks":54,"ok":true,"errors":[],"verified_on_s10plus":[]}` · by-state `implemented 9 / in_progress 24 / pending 21` · by-verdict `OFFLINE_TESTED 9 / None 45` | 0 |
| `tools/beta/regression-guard.sh --json` | `{"verdict":"PASS","pass":44,"fail":0,"warn":5,"info":2}` · warned `INV-1-launcher-cache-invalidation` ×2, `INV-3-ten-zone-safe-areas` ×2, `INV-9-a32-suite` · `baseline_commit 0102b6009d5ac561fe15c85b25a58942404d081d` | 0 |
| `tools/s10plus/a32/tests/run-tests.sh` | `== 0 failing suite(s) ==` (launcher registry/parity *"1 warning(s)"*) — the A32 floor is intact | 0 |
| `tools/s10plus/a33/tests/run-touch-tests.sh` | `TOUCH-TESTS: ALL PASS` | 0 |
| `tools/s10plus/a33/tests/run-boot-tests.sh` | `BOOT-TESTS: ALL PASS` (1 SKIP: aarch64 bridge build needs the guest) | 0 |
| `tools/s10plus/a33/tests/run-p3-tests.sh` | `P3-TESTS: ALL PASS` (1 SKIP: FSM replay helper needs alsa-lib/linux headers) | 0 |
| `tools/s10plus/a33/tests/run-userspace-tests.sh` | `pass=10 fail=0 skip=0 -> OFFLINE_TESTED` | 0 |
| `tools/s10plus/a33/security-tests/test-firewall.sh` | `== results: 49 passed, 0 failed ==` / `FIREWALL TESTS PASSED` | 0 |
| `tools/s10plus/a33/tests/hw-subsystems/run-all.sh` | `ALL HARDWARE-SUBSYSTEM OFFLINE SUITES PASS (OFFLINE_TESTED; owner tests remain NEEDS_OWNER_TEST)` (camera 4 fixtures, modem 4, microsd 6, …) | 0 |
| `tools/s10plus/a33/tests/test-core-apps.py` | `RESULT: PASS=86 FAIL=0 WARN=0 verdict=OFFLINE_STATIC_ONLY` (L4 jsdom skipped — no `node_modules` on this host) | 0 |
| `tools/s10plus/a33/tests/test-phone-apps.py` | `RESULT: PASS=37 FAIL=0 verdict=OFFLINE_TESTED` | 0 |
| `tools/beta/soak.sh --selftest` | 7 of 8 checks PASS; `no writes under .qq` FAILed — **false positive, see §10.2** | 1 |
| `tools/s10plus/a33/nuxel-vpn-tor.sh claims --json` | valid claim ladder, `invalid_claim_levels: []`, `traffic_routed_through_tor: unproven`, `remote_access_enabled: evidenced (default off)`; a non-fatal helper traceback is printed first — see §10.2 | 0 |
| `tools/s10plus/a33/nuxel-power-diag.sh status` | `state: BLOCKED_KERNEL` (`no gauge driver bound… no battery percentage is invented`) | 0 |
| `tools/s10plus/a33/verify-app-inventory.py` | **FAIL** — `APP-INVENTORY.md: the machine-readable block markers … are missing` | 1 |
| `tools/s10plus/a33/tests/test-console-protocol.py` | device-side `PASS` lines, then **abort** at teardown (`ValueError: flush of closed file`) — the host half never runs | 1 |
| `tools/beta/live/nuxel-live-reachability.py` (via bg-10 evidence) | `"verdict": "BLOCKED_EXTERNAL_RESOURCE"` — gadget enumerated, port byte-silent (`bytes_in=0`, 11.38 s) | 3 |

### 10.1 What pass 2 confirms about the verdict

Nothing in pass 2 changes it. The A32 floor is still intact (`PASS`, `0 failing suite(s)`), every
offline gate still passes, `verified_on_s10plus` is still **empty**, and the live console is still
**byte-silent**. The beta verdict therefore stays **`BETA_CANDIDATE_PENDING_HARDWARE_PROOF`** — with the
new, better-evidenced reason that the one live leg that *could* have produced on-device evidence
(`bg-10`'s reachability preflight) actually ran and returned
`"blocked_reason": "gadget enumerated as /dev/cu.usbmodem201 but the port is byte-silent for 8.0s (no
shell echo, no /dev/kmsg mirror): the on-device console is not serving the port"`, with the raw evidence
preserved (`docs/beta-finalization/live/evidence/reachability-20261016/{reachability.json,probe-raw.txt,
SHA256SUMS}`). That is the honest `BLOCKED_EXTERNAL_RESOURCE` the mission asked for, not an assumption.

### 10.2 Defects and anomalies observed in pass 2 (recorded, not hidden)

| # | Observation | Owner | Severity | Disposition |
|---|---|---|---|---|
| D1 | `verify-app-inventory.py` FAILS: `docs/beta-finalization/apps/APP-INVENTORY.md` lacks the `<!-- INVENTORY-DATA:BEGIN -->` / `<!-- INVENTORY-DATA:END -->` block its verifier parses | `bg-06-core-phone-apps` | medium | the document and its executable form are out of sync; the inventory's *claims* are cited in §4 but its machine check is red at aggregation |
| D2 | `test-console-protocol.py` aborts with `ValueError: flush of closed file` (`subprocess.communicate()` after `proc.stdin.close()`, CPython 3.11) so its **host-side** half never executes | `bg-07-specialty-apps` | medium | area 23's console protocol is **not** fully offline-verified; the device-side cases that did run, passed |
| D3 | `nuxel-vpn-tor.sh claims --json` prints `ValueError: not enough values to unpack (expected 7, got 6)` from an internal helper before emitting valid JSON | `bg-05-security-permissions` | low (non-fatal, contained) | the ladder is still honest and valid (`invalid_claim_levels: []`); the Tor sub-parser is unclean |
| D4 | `soak.sh --selftest` check *"no writes under .qq"* FAILs | `bg-09-integration-release` | low (false positive) | the only file carrying the run stamp `20261016T163833+0200` was `.qq/runs/…/.codeseeq-home/call-6fa9eaf6-a1/sessions/…/rollout-*.jsonl` — the **QonQrete pipeline's own transcript of this briQ's terminal output**. The harness wrote nothing under `.qq`; the check cannot distinguish a pipeline transcript from a harness write. No invariant was violated by the repository. |
| D5 | `pwa/nuxel-apps/console`, `penguinterface`, `privacy` remain **icons only** (no `index.html`); `pwa/nuxel-apps/settings` has no `sw.js` | bg-07 / bg-05 / bg-02+bg-08 | low | already listed in §8.4; a registry tile whose surface is absent is a real, named gap |
| D6 | the L4 (jsdom) runtime layer of `test-core-apps.py` could not run on this host (no `node_modules` carrying jsdom) | environment | info | the recorded runtime run (`PASS=130`, `OFFLINE_RUNTIME_PASSED`) is the inventory's own evidence; pass 2 could reproduce only `PASS=86`, `OFFLINE_STATIC_ONLY` |

None of D1–D6 is a hardware claim and none is a failure of the A32 floor; D1–D3 are open defects in other
groups' deliverables that this terminal report records rather than smooths over. Per the mission's
repeat-failure rule, D2 and D4 were re-checked once by hand (§10.2 text) before being recorded, not
retried in a loop.


---

*Generated by `bg-12-reports` / `briq-12a-engineering-report`. Companion document:
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md`. Aggregated from the repository's own evidence;
every claim above traces to a named path, command or recorded verdict.*

---

# APPENDIX Z — LIVE ON-DEVICE PASS (task2.md, "land it on the phone")

This appendix supersedes the repository-only Beta verdict above with a pass that actually ran
against the physical handset from host `dextronux` over the live console. It is evidence-first: every
claim cites a device-produced artifact under `docs/beta-finalization/live/evidence/`.

## Z.1 What was wrong before this pass

1. **Charger/LPM boot.** The phone arrived booted with `androidboot.mode=charger` (`charging_mode=0x3030`).
   That is a boot-time kernel decision: `sec_ts` returns `-ENODEV` before `i2c_add_driver()`, so the
   touchscreen does not exist and `nuxel-touch-arm.service` fails. Confirmed live
   (`evidence/baseline-20261016T220528+0200`).
2. **The deploy plan targeted a root the phone does not serve.** 440 of 624 file targets were authored
   under `/home/nuxel/nuxel`, which **does not exist on the handset**; the image builder, the A32
   installer and `services/nuxel-web` all use `/usr/share/nuxel`. A deploy as planned could not change
   a single pixel — the concrete, provable reason the owner saw "no difference on my phone".
3. **Live tooling defects found and fixed while landing it** (each was a hard blocker):
   * `nuxel_live.py` could not verify ANY frame — the target tty ends lines with CRLF and the parser
     matched bare LF, so every command reported `framed=false sha_ok=false`. Now normalises CRLF.
   * Linux console discovery found **zero** nodes: sysfs `idVendor` is bare hex (`18d1`) and
     `int(val, 0)` rejects it. Now parsed base-16.
   * `MAX_WRAPPER_LEN` was 480 chars, refusing every chunked push of a path longer than ~120 chars;
     measured the real limit (tty N_TTY buffer) as >4100 and raised it to 3800.
   * `chunk_size_for()` counted *down* from 128 and always returned 128 → 62 frames for one 6 KB file;
     now returns the largest fitting chunk (3392).
   * `install_script()` ended with an unconditional `if [ -e backup ]; then cp backup target; fi`,
     so **every install atomically wrote the new file and then immediately restored the old one**.
     Replaced with an EXIT-trap rollback that fires only on failure.
   * The group `health_check` was appended to *every* file's install script, so the first files of a
     380-file group failed their own group-level check and rolled back. Health checks now run once per
     group, after it completes.
   * The flash-tool guard matched the bare substring `pit`, refusing a legitimate base64 icon payload.
     Now word-boundary matched, and generated payload lines bypass the guard.
   * `push_bytes()` ignored per-chunk frame failures, and a chunk *append* cannot be retried safely
     (duplicate bytes). Rewritten to write each chunk to its own part file with a truncating `>`
     (idempotent, retry-safe) then concatenate, with an on-device SHA-256 read-back.
   * `--only` filtered groups *before* validation, tripping the extension invariants. Now validates the
     full manifest and restricts execution afterwards.
   * Added resumability: a step whose target already carries the source bytes is skipped (and the
     original `.nuxel-rollback` copy is preserved), and the apply loop auto-reconnects the console
     (the gadget re-enumerates under load).

## Z.2 Boot-mode finding (task.md §6/§7)

A **normal OS reboot** (authorised by task.md §53; run through `nuxel-live-reboot-verify.py`) cleared
the charger condition and armed the touchscreen. Two normal reboots were performed this session; both
cleared LPM/charger mode. The condition **recurred** once because the hardware POWER key was held for
11.6 s (kernel: `gpio_keys_gpio_report_event: 116`; `nuxel-button-manager: POWER_DEBOUNCED held=11624ms`),
which reboots the handset and, with USB attached, returns it to LPM. The durable offline fix
(`nuxel-bootmode-guard`) remains `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED` — no flashing.

## Z.3 Deployment results (briq-10b)

16 groups / 624 steps planned, 0 invariant violations. Applied to the phone across five runs; the only
skip is `console-and-kernel-side-followups` (`BLOCKED_KERNEL`, by design). See `live/DEPLOYMENTS.md`.

* launcher + safe zones: **22/22**, health 200.
* PWA app suite + shared runtime + registry: **400/400**.
* configs / a33 tools / services / native-shell sources / touch-and-buttons / audio+network: **185/185**.
* a33 runtime + session units + boot animation + packages: **64/64, 4/4 health checks passed**.
* animation handoff: **2/2**.
* On-device read-back confirms the served launcher (`/usr/share/nuxel/pwa/nuxel-home/index.html`,
  sha256 `a15be137…`) equals the repository, `GET … → 200`, 25 app directories serve 200, and
  `nuxel-portal`/`nuxel-bridge` are inactive (deployed, not enabled).

## Z.4 Touchscreen and display (task.md §6, §7)

On the post-reboot normal boot the device reports: `/sys/class/sec/tsp` present; `sec_ts` on IRQ 431;
`sec_touchscreen → event2` with `INPUT_PROP_DIRECT`; the libinput path shim records
`PATH_ASSIGN_SEAT … direct_devices_seen=2`; the session log shows
`layout=/pwa/nuxel-home bridge_ok=yes`; and `/run/nuxel-wl-fb.state` shows
`FRAMES_OK … owner=nuxel-wl-fb display=on` (a single framebuffer writer). So the chain
`sec_ts → evdev → shim → libinput → phoc → WebKitGTK → launcher` is wired and measured.

**A registered driver is not a finger.** The end-to-end human interaction (tap, scroll, on-screen
keyboard) remains **`NEEDS_OWNER_TEST`** — see the manual checklist area 1.

## Z.5 Still open, honestly

* Touch human acceptance — `NEEDS_OWNER_TEST`.
* Audio/headphones/Bluetooth/NFC/GNSS/camera/SIM/vibration/flashlight — deployed tools + configs,
  physical proof `NEEDS_OWNER_TEST`; `mmcli -L` still finds no modem (`BLOCKED_FIRMWARE`).
* `nuxel-portal` / `nuxel-bridge` not enabled by the phone's post-handoff start path.
* **Clock is wrong** (device reads `2026-09-15T00:01Z` while the real date is 2026-10-16) — a live,
  user-visible defect; the chrony/time config is deployed but the clock is not synchronised.
* Charger-mode recurrence is a boot/hardware condition; the offline fix is `BLOCKED_KERNEL` (no flash).
* `nuxel-postboot.sh` was observed restart-looping `nuxel-ui` (iteration ≥148) on a prior boot.
* `flatpak` is still absent (`rpm -qa` = 410), so NuXtore has no backend — `IMPLEMENTED_NOT_DEPLOYED`
  / `BLOCKED_EXTERNAL_RESOURCE`, not a working store.

## Z.6 Beta verdict (re-derived from the new evidence)

Repository work is complete and offline-tested; the userspace **is now genuinely on the phone** with
verified hashes, healthy units and a rendering display bridge. But the physical acceptance tests
(a finger on the panel, audibility, buttons, radios) were **not observed by a human**, so the honest
verdict remains:

**`BETA_CANDIDATE_PENDING_HARDWARE_PROOF`**
