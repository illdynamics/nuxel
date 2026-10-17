# Report — everything else in this terminal, besides the live-console quickstart

**Scope.** This is the summary of the information sitting **above this command output in this tmux
pane** that is **not** about *how to connect to the S10+ live console*. The connection mechanics now
live in **`quickstart-live-console.md`** and are referenced here only where they explain something
else (for example: why a "console unreachable" line in a report is stale).

**Source.** Terminal scrollback of pane `main:1.2` (`%6`), session `main`, window `main:1`, host
`dextronux`, read back with `tmux capture-pane -p -S -` on 2026-10-17 ≈01:40 CEST (≈6 500 lines of
scrollback). Sessions visible there: `01a146f6`, `01a1470e`, `01a14716`. The scrollback in turn
quotes files from the working tree; those files are named inline where it matters.

---

## 1. What this workspace is

`/x/nuxel` is the **Nuxel Phone OS** repository — a from-scratch, Android-free Linux phone OS
(GrapheneOS-spirited security posture, Fedora/GNOME-Flatpak base, Phosh + GTK4 + Wayland shell,
Flatpak-sandboxed PWA-first + native GTK4 app model). Remote: `https://github.com/illdynamics/nuxel.git`.

| Field | Value |
|---|---|
| HEAD | `82ba43665e27e7d88120b5eac9d0b640c61abf51` — *"task2: land Nuxel userspace on S10+ and repair live service graph"*, 2026-10-17T00:55:28+02:00 |
| `VERSION` file | `v0.5.0-beta-rc1` |
| Test hardware named in `README.md` | Moto G7 Power, Samsung Galaxy S10+, Google Pixel 10 Pro XL (the stated target device) |
| Current live target | Samsung Galaxy S10+ `SM-G975F` / `beyond2lte` / Exynos 9820, Fedora 43 aarch64, Samsung kernel 4.14.253 |
| Host | `dextronux`, Linux 6.17.1-300.fc43.x86_64 |
| Uncommitted at time of writing | `ad.md` (untracked) |

The scrollback also shows the two other device trees being carried along: `docs/g7power-*` and
`docs/pixel10proxl-*` / `mustang-*`, plus the two recovery-mission records
(`s10plus-bootloop-repair/`, `s10plus-autonomous-boot-repair/`).

---

## 2. The other half of that same answer: boot animation → static wallpaper → never reaches the launcher

The question above the quickstart had two parts. The second part — *"it's all good on the boot
animation and then it shows the static wallpaper but it's not going through to the launcher"* — is a
**documented, known defect**, not an unexplained hang. The two files that describe it are
`docs/beta-finalization/boot/ANIMATION-HANDOFF.md` and `manual-proof/03-display-boot.md` §6.

Two distinct causes produce that same visual, and they are distinguishable:

1. **Handoff fires too early (the classic A31/A32 bug).** The old *time-based* handoff stopped the
   animation the moment the launcher committed its page (~6.05 s) and grabbed the panel — so
   **47 of the 192 frames (24.5 %) never reached the glass**, and the panel switched to the
   launcher's **static wallpaper piece** mid-animation. The fix is the *receipt-driven* handoff:
   `configs/nuxel/boot/animation-handoff.json` → `mode=receipt`, `min_cycles=1`, i.e. at least one
   full 8 s play-through before ownership changes. The manual-proof doc names the symptom literally:
   *"the launcher never took ownership and no resume happened."*
2. **The launcher itself never painted.** If `owner=ui` but the panel is static/blank, the panel did
   change hands and the launcher produced nothing — e.g. the A29b case where `nuxel-http-bridge`
   answered `/` with a directory listing and 404'd the launcher page. The launcher is served at
   `http://127.0.0.1:8000/pwa/nuxel-home/index.html` (expected HTTP 200).

How to tell which one you are looking at, over the console:

```sh
nuxelctl handoff status ; nuxelctl handoff audit
cat /run/nuxel-anim-handoff            # owner=anim|ui, stage, terminal, loops=n/m
cat /var/lib/nuxel/fb-owner            # single-writer record (owner=nuxel-wl-fb)
tail -n 20 /var/lib/nuxel/anim-handoff.log
dmesg | grep -E 'NUXEL_ANIM_HANDOFF|ANIMATION_STOP|LAUNCHER_DISPLAY|ANIM_MIN_CYCLE'
python3 tools/s10plus/a33/nuxel-anim-handoff.py audit --expect-ui
```

Reading it:

* `owner=anim` / `ANIMATION_RESUMED` → the handoff correctly refused; the animation should keep the
  panel, so a static frame here means the *resume* path failed.
* `owner=ui` + `terminal=1` + `loops>=1` but a static/blank wallpaper → the launcher / PWA host is
  the problem, not the animation.
* `NUXEL_FB_OWNER_BUSY` present → two `/dev/fb0` writers fighting; that is a separate defect.

**Honest status:** the on-glass verdict for this whole area is still `NEEDS_OWNER_TEST` in the tree.
It has been proven offline (simulation + compiled C + selftest, 30 checks PASS) but has never been
confirmed by eye on the handset — so the owner's observation is genuinely new evidence, not a stale
one.

---

## 3. The mission prompts sitting in the tree

These are the instruction documents that drove the work in this workspace — not documentation of the
product itself:

| File | What it is |
|---|---|
| `ad.md` | **QonQrete Fedora host override** (untracked). Declares the build now runs on a Fedora laptop with the S10+ physically attached, that the UTM VM is unavailable, and sets the standing rules: pick the authoritative launcher from the repo rather than by code volume; build/verify ARM64; **touchscreen end-to-end above all optional app work**; **only one agent may own the live USB console or deploy at a time**; work autonomously across cycles; persist progress/tests/failures/hashes/rollback after every subsystem; escalate architecture/root-cause to InstruQtor and security/release review to InspeQtor; **absolutely no device flashing**; never declare success from compilation/package/service status alone; mark physical tests as `NEEDS_OWNER_TEST`; produce the two mandatory final reports. |
| `task.md` (68 KB) | Task 1 — the beta finalization mission. Executed as a **repository-only** pass. |
| `task2.md` (43 KB) | Task 2 — *"land it on the phone"*. Explicitly the corrective pass: Task 1 shipped nothing to the device (`"apply": false`, verdict `IMPLEMENTED_NOT_DEPLOYED`), the owner reported *"no difference on my phone"*, and the deploy manifest covered only 7 groups / 37 steps, so the rest of the programme could not have reached the phone even in principle. |
| `35b.ms` | The earlier **CYBER-TIEL bootloop-repair** mission brief (TWRP-era: BOOT + USERDATA already flashed with SHA-256 readback, device bootlooping at the Samsung logo). Historical context for the flash guides. |
| `finish/`, `finish2/` | Earlier end-of-run artefacts (flash quickstart, build notes, stage-12 reports, blankflash/stock-recover helpers, boot-log monitors). |
| `prompts/`, `design/`, `ci/`, `vm/` | Prompt sets, design docs, CI wiring, VM tooling. |

**Standing constraints carried through all of it:** never flash
BOOT/USERDATA/SYSTEM/RECOVERY/DTB/DTBO/VBMETA/radio, never write a raw partition, never repartition
UFS, never run Heimdall/Odin, never enter Download Mode or TWRP, never touch EFS/calibration/IMEI/PIT,
never install a new kernel to the phone, never silently change hardware identity, never claim
untested hardware works.

---

## 4. The beta-finalization programme

Root: `docs/beta-finalization/` (engineering report, work queue, manual proof checklist, baseline
protection, plus `apps/ boot/ launcher/ live/ manual-proof/ preflight/ release/ system/ testing/
touch/ vm/ workqueue/`).

### 4.1 Work-queue state — measured in that session

`python3 tools/beta/workqueue.py verify-schema --json` → `"ok": true`, **55 tasks**:

| Dimension | Counts |
|---|---|
| By state | `implemented` 23 · `in_progress` 15 · `pending` 16 · `deferred` 1 |
| By verdict | none recorded 31 · `OFFLINE_TESTED` 20 · `VERIFIED_ON_S10PLUS` 2 · `DEPLOYED_UNVERIFIED` 1 · `DEFERRED` 1 |
| On-device verdicts | `briq-00a-repo-preflight`, `briq-10a-live-reachability-preflight` |

That is real movement against the earlier snapshot inside `BETA-FINALIZATION-ENGINEERING-REPORT.md`
(*54 tasks, 9 implemented / 24 in_progress / 21 pending, **zero** `VERIFIED_ON_S10PLUS`*). The
on-device verdict count is no longer zero.

### 4.2 The verdict vocabulary is the point of the programme

`OFFLINE_TESTED` is the ceiling for anything without the handset; `NEEDS_OWNER_TEST` for anything
needing a finger, ear, eye, SIM, tag, peer or credential; `BLOCKED_EXTERNAL_RESOURCE` when the
device/VM/archive is absent; `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED` for real kernel gaps. The schema
**refuses** an on-device verdict without on-device evidence — there is no override flag.

### 4.3 Evidence-backed offline state

* `tools/beta/regression-guard.sh` — a pinned-asset / invariant gate over the A32 baseline
  (protected asset pins, INV-2/INV-10/INV-11 assertions). Multiple runs are recorded with
  *different* totals (see §9).
* `tools/s10plus/a32/tests/run-tests.sh` → `0 failing suite(s)`, exit 0.
* Subsystem suites and diagnostics: touch, boot, P3, userspace (`pass=10 fail=0 skip=0`), firewall
  (49 passed / 0 failed), phone-app (`PASS=37 FAIL=0`).
* `docs/beta-finalization/BASELINE-PROTECTION.md` + `baseline-protection.json` — the frozen A32 floor
  (`0102b6009d5ac561fe15c85b25a58942404d081d`) that must not regress, with a `reverification_log`.

### 4.4 The two mandatory final reports

`docs/beta-finalization/BETA-FINALIZATION-ENGINEERING-REPORT.md` and
`docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` are the deliverables required by the mission
brief (`ad.md`). The engineering report now opens with a **LIVE DEVICE RESULTS — 2026-10-17** section
that supersedes its own earlier "repository-only" framing; the manual-proof checklist is the
owner-facing list of what a human still has to look at.

---

## 5. What the live work actually achieved (results, not connection mechanics)

Summarised from `docs/beta-finalization/live/BASELINE-CAPTURE.md`, `.../DEPLOYMENTS.md`,
`CHANGELOG.md` `[v0.5.0-beta-rc1]`, and the engineering report's live section:

| Item | Result |
|---|---|
| Userspace deploy | **624/624** manifest steps applied (16 newly installed, 0 failures, 0 rollbacks) |
| systemd | `is-system-running` = **`running`**, `systemctl --failed` = **0 units** (was `degraded` with the touch-arm unit failing in charger mode) |
| Boot mode | **non-charger normal boot**: touchscreen nodes registered (`sec_touchscreen` event2, `sec_touchpad` event3, `sec_touchproximity` event4), `sec_ts lpm:0` |
| Launcher | `http://127.0.0.1:8000/pwa/nuxel-home/index.html` → **200**; device PWA hashes match the repository |
| HTTP bridge | `http://127.0.0.1:8080/api/v1/ping` → **200** |
| Display | exactly one `/dev/fb0` owner (`nuxel-wl-fb`), `display=on`, ~24 fps, failures=0; handoff chain `BOOT_WAIT_LAUNCHER → … → LAUNCHER_DISPLAY_OWNER` complete |
| D-Bus | `org.nuxel.Bridge`, `org.nuxel.Portal`, `org.nuxel.Notifications` owned correctly |
| Time/RTC | repaired — the clock was ~1 month stale, now real time, `hwclock -w -u`, tz `Europe/Amsterdam` |
| Reboot | `systemctl reboot` **hung** on logind D-Bus activation; defect fixed (`--reboot-cmd "systemctl reboot --force"`); the 3-reboot budget was then exhausted → `briq-10c` **DEFERRED** |
| Soak | preliminary only: two samples 60 s apart, no reboot, 0 failed units, single fb owner, no unbounded CPU/RSS growth |

---

## 6. Service-graph defects that were real bugs, not environment noise

1. Hardened units depended on identities/dirs that had never been provisioned on the device → new
   idempotent `tools/s10plus/a33/nuxel-provision-services.sh`.
2. Missing Python D-Bus/GObject/Cairo aarch64 RPMs → installed on the phone.
3. `services/nuxel-bridge/src/bridge.py` used a non-existent `dbus.service.property` → replaced with
   a real `org.freedesktop.DBus.Properties` Get/GetAll.
4. `org.nuxel.Bridge.conf` carried an invalid `<limit name="log_level">` that made `dbus-daemon`
   **reject the whole file**; own-name policies added for `nuxel-bridge` / `nuxel-notifications`.
5. `nuxel-http-bridge.service` runs as root because the Samsung 4.14 vendor `ncm` module denies
   `AF_INET`/`AF_INET6` socket creation to non-root UIDs — a documented kernel limitation, not a
   relaxed security choice.

---

## 7. Repository changes that came out of the live work

* `tools/s10plus/a33/nuxel-provision-services.sh` (new).
* `tools/beta/live/nuxel-live-reboot-verify.py` — default reboot command corrected.
* `scripts/s10plus-debug-pack/nuxel-live.sh` — three host-tool defects fixed on Linux (missing
  heredoc terminator, macOS-only device discovery, port-lock crash under `sudo`), plus the glob-safe
  discovery rework. It is a **pinned protected asset**, so the change went through the guard's
  `--repin` path and the gate was re-run.
* `.gitignore` — narrowly scoped block so the supplied archives and a local `.venv/` could not be
  committed.
* `VERSION` pinned at `v0.5.0-beta-rc1`; `CHANGELOG.md` documents the pass.

---

## 8. What is still open, unproven, or blocked

| Item | State | Why |
|---|---|---|
| Real-finger touch behaviour, swipe, multi-contact, on-screen keyboard | `NEEDS_OWNER_TEST` | the `sec_ts → evdev → phoc/libinput` chain exists on a normal boot; a human finger has not been on the glass |
| Audible audio, headphones, Wi-Fi association, Bluetooth pairing, GPS fix, camera frame, NFC tag, microSD, SIM/calls/SMS, haptics, flashlight, sensors | `NEEDS_OWNER_TEST` or `NOT_SUPPORTED_ON_DEVICE` | needs a finger, an ear, credentials, a peer, a tag or a card |
| Charger-mode boot disabling `sec_ts` | `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED` | LPM boot makes `sec_ts` skip `sec_ts_init` (`lpm 1`); the fix is kernel/DTB-side and the no-flash rule forbids it |
| Reboot-into-Nuxel verification | `briq-10c` **DEFERRED** | 3-reboot budget exhausted this cycle; the reboot path was also defective and is now fixed |
| 8-hour device soak | not done | only the bounded two-sample smoke was run |
| `briq-10b-live-deploy-userspace` | carries `NEEDS_OWNER_TEST` in the ledger | deploy was applied; human-visible acceptance still pending |
| aarch64 execution channel on the host | absent | no cross-gcc, no `qemu-aarch64-static`, no binfmt, no UTM → two INV-2 binary legs report **WARN**; the handset is the only aarch64 execution channel |
| Supplied comparison archives (`docs.zip`, `scripts.zip`, `tools.zip`, A30–A32 archives) | absent on disk | dependent comparisons degraded to "compare against the live tree"; recorded as `BLOCKED_EXTERNAL_RESOURCE`, never assumed |
| VM parity run | not present at aggregation | belongs to `bg-11-vm-parity` |
| 31 work-queue tasks with no verdict at all | open | ordinary backlog: apps, power, radios, sensors, release deliverables |

---

## 9. Contradictions and stale numbers found (flagged, not silently fixed)

These are the places where the tree disagrees with itself. They are worth knowing before anyone cites
a number from it:

1. **Product version.** `README.md` still advertises **v0.4.0-alpha**, while `VERSION`, `CHANGELOG.md`
   and every 2026-10-17 document say **v0.5.0-beta-rc1**. The README badge is stale.
2. **Regression-guard totals.** Three different totals appear in the same session's append-only
   section of `preflight/ENVIRONMENT.md`: `PASS=41`, then `PASS=53` (INV-10), then `PASS=68`
   (INV-11), plus an earlier `44 pass / 0 fail` in the engineering report. Each is annotated as a
   correction, but a reader must follow the chain to find the current one.
3. **"Console unreachable" vs "console reachable".** `docs/beta-finalization/testing/evidence/
   soak-device-20261017T005131+0200/soak-report.md` reports `BLOCKED_EXTERNAL_RESOURCE` and cites
   `ENVIRONMENT.md` **§6** ("did not answer") — while the reboot-verify bundle at `00:49:29+0200` the
   same night records a **successful reconnect** with `sha_ok=yes`. The soak tool appears to be
   consulting the stale first-session conclusion rather than the live state. Do not read that soak
   result as evidence the console was down at 00:51.
4. **Engineering report self-contradiction.** Its header says *"the handset console did not answer"* /
   *"access tier: repository-only"*, and its very next section is a live-device results block
   produced **on the real S10+**. The live section is the newer truth; the header was never rewritten.
5. **Work-queue counts drift.** `WORK-QUEUE.md`'s summary table (31 without verdict, 18 owner-only)
   predates the current `verify-schema` output (55 tasks, 31 without verdict, 20 `OFFLINE_TESTED`,
   2 `ON_S10PLUS`, 1 `DEFERRED`, 1 `DEPLOYED_UNVERIFIED`). Use the tool, not the prose.
6. **`preflight/ENVIRONMENT.md` §1–§12 vs §13.** §1–§12 describe a **macOS** session at
   `/Users/wicked/x/nuxel` where the console never answered; §13 describes a **Fedora** session at
   `/x/nuxel` where it did. §13 explicitly supersedes §6/§10/§12, but the earlier sections remain
   readable as if current.

---

## 10. Repository hygiene notes (observed, not changed by this pass)

* `ad.md` is **untracked** and is the standing Fedora-host override — worth committing or consciously
  ignoring.
* Root-level clutter is substantial and partly legacy: `35b.ms`, `*.ms`, `yolo*.md` (14 files),
  `heim.md`, `heimd.md`, `fb.md`, `S10PLUS-*.md`, `task.md`/`task2.md`, three flash-guide pairs, and
  large dot-logs (`.kbuild.log` 924 KB, `.kbuild2.log` 339 KB, `.testsys.img` 4 MB,
  `.ocean.dtb/.dts`).
* `macbook-s10plus-flash-guide-final-full.md` and `…-final-full-updated.md` are **byte-identical**
  (same MD5) — one is a pure duplicate.
* `g7power-flash-guide.md` / `-current.md` and `s10plus-flash-guide.md` / `-current.md` are *different*
  files with the same base name; the `-current` variants are the newer ones.
* `.qqignore` and `.gitignore` both carry ignore rules; `.codeseeq/` (this agent's own runtime
  metadata: sqlite state, logs, shell snapshots) is pipeline metadata and must stay read-only.

---

## 11. Bottom line

* The **platform is real**: the S10+ boots Nuxel, the userspace is deployed (624/624 steps, 0
  failures/rollbacks), systemd is `running` with 0 failed units, the launcher answers 200, and exactly
  one process owns the framebuffer.
* The **verdict is still not an acceptance**: `BETA_CANDIDATE_PENDING_HARDWARE_PROOF`. Everything that
  needs a human sense, a credential, a peer device, a SIM/card/tag, or a kernel change is explicitly
  not claimed.
* The **biggest single technical gap** is charger-mode boot (LPM) disabling `sec_ts`, which is
  kernel/DTB-side and therefore out of bounds under the standing no-flash rule.
* The **biggest process gap** is documentation drift (§9): three live cycles' worth of documents are
  stacked append-only, so several headline numbers and one whole "console unreachable" conclusion are
  stale. The work-queue tool and the `live/` evidence bundles are the reliable sources; the prose
  summaries lag behind them.
* **Still unexplained from the owner's side** is §2 — animation plays, static wallpaper, no launcher.
  That is a real, documented defect class with a decision procedure, and its on-glass verdict is
  still `NEEDS_OWNER_TEST`.
