# Boot animation → launcher handoff, and the single framebuffer owner (area 2, briq-02a)

Scope: Samsung Galaxy S10+ **SM-G975F / beyond2lte / Exynos 9820**, Fedora 43 ARM64
userspace, Linux 4.14.253 (Samsung), systemd PID 1. The panel is a DECON
framebuffer (`/dev/fb0`, 1440x3040, no DRM in this kernel).

Access tier: **repository-only implementation + offline review**. The effect can
only be *observed* on a live boot; the live group (bg-10) owns that observation.

**Terminal states for this area**

| Item | State |
|---|---|
| Receipt-driven handoff decision logic (shared C/Python table) | `OFFLINE_TESTED` |
| Single framebuffer owner (lock + durable owner record) | `OFFLINE_TESTED` |
| Minimum completed-cycle floor (configurable, default 1) | `OFFLINE_TESTED` |
| Audit tooling (simulate / audit / selftest) | `OFFLINE_TESTED` |
| Handoff as seen on the handset glass | `NEEDS_OWNER_TEST` (bg-10 live run) |

No claim in this document is `VERIFIED_ON_S10PLUS`.

### Revision 3 (bg-02 verification pass) — what was re-verified

| Check | Command | Result |
|---|---|---|
| The A32 conversion baseline pin is intact | `bash tools/beta/regression-guard.sh` | `INV-2-colour-conversion` **MATCH** (hard pin, `tools/s10plus/a32/nuxel-wl-fb.c` = `6501c6d5…`); guard `PASS`, exit 0 |
| The bridge under test is byte-identified | `sha256sum tools/s10plus/a33/nuxel-wl-fb.c` | `052bfdbf673ef658c93b8c07925f2c9249af3c755a011ccbe90011c616f7b768` (unchanged this revision — no conversion or handoff semantics were touched) |
| Handoff state machine (decision table + single-owner proof) | `python3 tools/s10plus/a33/nuxel-anim-handoff.py selftest` | **PASS, 30 checks / 0 failures** |
| Replayable timeline | `python3 tools/s10plus/a33/nuxel-anim-handoff.py simulate` | 195 presented, 0 dropped, 8150 ms whole cycle (A32 row shown as the negative control) |
| Wiring contract across the boot surface | `python3 tools/s10plus/a33/tests/test-boot-surface-contract.py` | **PASS, 295 checks / 0 failures** |
| Whole offline gate | `bash tools/s10plus/a33/tests/run-boot-tests.sh` | `BOOT-TESTS: ALL PASS` (8 legs; the aarch64 build leg reported `SKIP` — the UTM guest was not reachable, and a skip is never a pass) |

The only behaviour added in this revision is the recorded *reason* for a waived
minimum-cycle floor plus its documentation (§2, §6d); the conversion, the lock, the
receipt and the presentation path are untouched.

---

## 1. The defect this fixes (A31/A32 evidence)

The A31/A32 bridge stopped the boot animation as soon as the launcher committed
its page and only then took the panel:

* measured timeline: animation starts at uptime **2.9 s**, launcher page
  committed at **≈5.9 s**;
* A32 therefore handed over at **≈6.05 s** → **145 of the 192 frames** of the
  shipping MP4 had been shown (`ffprobe`: 192 frames @ 24 fps, 8.0 s);
* the remaining **47 frames (24.5 %)** never reached the glass, and the panel
  switched to the launcher's **static wallpaper** mid-animation.

The A21/A22 animation work shipped a 0-skipped-frames player
(`tools/s10plus/a20/nuxel-anim-player.c`, `tools/s10plus/a31/test-anim-player.sh`);
A32's handoff silently undid that by stopping the player early.

## 2. Required behaviour and how it is implemented

| Requirement | Implementation |
|---|---|
| Animation keeps `/dev/fb0` until a **real terminal condition** | The bridge requests the stop only after the player's own loop markers reach the configured floor (`ANIM_MIN_CYCLE`), or the player reports a terminal marker |
| Handoff driven by a **receipt**, not a timeout | `/run/nuxel-anim-handoff` (JSON, schema_version 1) is written before any scanout byte changes owner; the launcher/UI stage is only recorded as owner once the painter is confirmed gone |
| Exactly **one framebuffer owner** at any time | `/run/nuxel-fb-owner.lock` (O_CREAT\|O_EXCL, identity-verified via `/proc/<pid>/comm`, stale files reclaimed) + durable `/var/lib/nuxel/fb-owner` record. A live foreign writer ⇒ this process exits `FB_OWNER_BUSY` (`NUXEL_FB_OWNER_BUSY`) instead of becoming a second writer |
| **Minimum full cycle count** before handoff | `min_cycles`, default 1 = one complete play-through of the shipping 192-frame 24 fps MP4 = **8000 ms**; configurable in `configs/nuxel/boot/animation-handoff.json` |
| Handoff is **auditable after the fact** | Kernel marker `NUXEL_ANIM_HANDOFF receipt=<id> owner=<anim\|ui> stage=… terminal=… loops=n/m reason=…` plus an append-only `/var/lib/nuxel/anim-handoff.log` |
| **Launcher-not-ready ⇒ the animation resumes** | No scanout write at all, stale stop file unlinked, receipt `owner=anim stage=ANIMATION_RESUMED`, ownership lock released so the first-light fallback can legally take the panel — never a blank or silently static frame |
| Verbose boot may waive the floor — **only** as a recorded operator choice | Decision 5 of the shared table: if `/run/nuxel/anim-skip.request` says `ANIM_SKIP_REQUESTED` (published by `nuxel-verbose-boot`), the floor is waived for that boot only. The receipt/state records `ANIM_MIN_CYCLE_SKIPPED` / `reason=…` with `terminal=0`, so a waiver can never be mistaken for a completed cycle. With no request file this branch is inert |
| The waiver must say **WHY** | `nuxel-verbose-boot` writes `ANIM_SKIP_REQUESTED reason=<animation_mode_off\|animation_mode_short\|verbose_boot_requested> animation_mode=<standard\|short\|off>`, and the state file carries `ANIMATION_MODE`, `ANIMATION_MODE_SOURCE`, `EFFECTIVE_ANIMATION`, `ANIMATION_REASON`, `VERBOSITY`. The precedence is `off > short > verbose_boot > standard`, so the bridge has exactly one reason to record — never a guess. `animation_mode=off` means the animation never starts at all rather than being cut short |
| A stalled player must not freeze the boot | Bounded wait (`max_wait_s`, default 24 s) ⇒ `ANIMATION_DEGRADED_STOP` with an explicit `reason` (`anim_min_cycle_timeout` / `anim_clock_unavailable`); the receipt records `terminal=0` and **never** claims a completed cycle |

### Ownership contract (single writer)

```
/run/nuxel-fb-owner.lock      ASCII PID of the current /dev/fb0 owner (identity-verified)
/var/lib/nuxel/fb-owner       durable K=V record: owner, pid, stage, ui_writer, reason,
                              receipt=<id>, lock, boot_id, ts
/run/nuxel-anim-handoff       last ownership receipt (JSON)
/var/lib/nuxel/anim-handoff.log  append-only: "<ts> NUXEL_ANIM_HANDOFF receipt=… owner=… stage=… …"
```

Receipt stages in boot order (as printed by `nuxel-anim-handoff.py simulate`):

```
owner=anim  stage=BRIDGE_WAITING_FOR_LAUNCHER
owner=anim  stage=ANIMATION_RUNNING
owner=anim  stage=ANIM_MIN_CYCLE 1/1
owner=anim  stage=ANIM_TERMINAL_CONDITION
owner=anim  stage=ANIMATION_STOP_REQUESTED
owner=anim  stage=ANIMATION_STOP_CONFIRMED
owner=ui    stage=LAUNCHER_DISPLAY_OWNER
```

### Evidence markers the live group greps

`ANIM_MIN_CYCLE` (with `_WAIT` / `_RESULT` / `_DEGRADED` / `_SKIPPED` variants —
`ANIM_MIN_CYCLE_SKIPPED` is the *recorded* verbose-boot waiver, `_DEGRADED` is an
unexpected fault, and they are never conflated),
`ANIMATION_STOP` (`ANIMATION_STOP_REQUESTED`, `ANIMATION_STOP_CONFIRMED`),
`LAUNCHER_DISPLAY` (`LAUNCHER_DISPLAY_OWNER`), `NUXEL_ANIM_HANDOFF`, plus the
player's own `NUXEL_ANIM_LOOP=<n>` and `NUXEL_ANIM_HEARTBEAT_LOOPS=<n>`.

The animation *policy* of the boot is published by the early stage as
`NUXEL_BOOT_ANIMATION=<standard|short|off> reason=<reason> verbosity=<0..3>`
(the same values are in `/run/nuxel/verbose-boot` and, when a waiver happened, in
`/run/nuxel/anim-skip.request`), so a live run can be graded without guessing which
of the three boot-diagnostics controls produced what was seen.

## 3. Files

| File | Role |
|---|---|
| `tools/s10plus/a33/nuxel-handoff-logic.h` | The pure decision table, shared **verbatim** by the bridge and the offline tests (no divergent copies) |
| `tools/s10plus/a33/nuxel-wl-fb.c` | The bridge: ownership lock, receipt writer, minimum-cycle wait, colour conversion, screen on/off, paced presentation |
| `tools/s10plus/a33/nuxel-anim-handoff.py` | `simulate` (replayable timeline), `audit` (verdict on real artefacts, `--root` for a fixture), `selftest` (the full offline proof) |
| `tools/s10plus/a33/tests/handoff-cases.json` | The shared decision corpus, **22 cases** (both implementations are executed against it; it includes the five verbose-skip rows) |
| `tools/s10plus/a33/tests/test-handoff-logic.c` | Compiles the header against the corpus and asserts the invariants |
| `configs/nuxel/boot/animation-handoff.json` | Installs to `/etc/nuxel/boot/animation-handoff.json`; read by the bridge at boot |
| `tools/s10plus/a33/nuxelctl` | `nuxelctl handoff status\|simulate\|audit` |
| `tools/s10plus/a33/build-a33-boot.sh` | Builds **this** bridge as an aarch64 ELF (UTM guest, or `CROSS_COMPILE`), then runs the bridge's own `--colour-selftest`, `--colour-dump` and `--handoff-selftest` natively on the build channel. A build that cannot run is reported as skipped — never as a pass. Output: `build/out/s10plus/a33-boot/` (never the A32 artifact directory) |
| `tools/s10plus/a33/tests/run-boot-tests.sh` | The whole bg-02 offline set (headless, rootless) as one command |
| `tools/s10plus/a33/tests/test-boot-surface-contract.py` | Wiring contract: the markers, the lock/receipt paths, the config the bridge reads, the console/UI wiring, the ten-zone contract and the documents all agreeing |
| `configs/nuxel/README.md` | Install/upgrade rules for the `/etc/nuxel` documents |

Geometry is **measured, not assumed**: `mp4_frames=192`, `mp4_fps=24`,
`cycle_ms=8000` in `configs/nuxel/boot/animation-handoff.json`, and the same
constants are compiled into the header (`NUXEL_MP4_FRAMES_DEFAULT`,
`NUXEL_MP4_FPS_DEFAULT`, `NUXEL_ANIM_MIN_CYCLES_DEFAULT`,
`NUXEL_ANIM_MAX_WAIT_S_DEFAULT`). The selftest fails if the header and the config
ever disagree.

## 4. Tests (offline, no phone, no display, no root)

```sh
python3 tools/s10plus/a33/nuxel-anim-handoff.py selftest   # exit 0 == all pass
python3 tools/s10plus/a33/nuxel-anim-handoff.py simulate   # the A32-vs-A33 timeline
python3 tools/s10plus/a33/nuxel-anim-handoff.py audit --root <fixture>   # auditor
python3 tools/s10plus/a33/nuxelctl handoff status|simulate|audit

bash tools/s10plus/a33/tests/run-boot-tests.sh          # every bg-02 leg, one command
bash tools/s10plus/a33/build-a33-boot.sh                # build + self-test the aarch64 bridge
bash tools/beta/regression-guard.sh                     # the A32 floor (INV-1..INV-9)
```

Measured 2026-10-16, `build-a33-boot.sh`: `BUILD_A33_BOOT=OK channel=vm` — the A33
bridge built as an aarch64 ELF on the UTM Fedora 43 guest (sha256
`2d8718c4d92858bbae02b7e914f0172d295b1c12446eb861e91c355f2ac912fc`), and on that guest
`--colour-selftest` printed all six PASS lines, `--handoff-selftest` printed
`PASS handoff_logic invariants cases=22` and `--colour-dump` reported
`hw=R@0,G@8,B@16 hw_order_override=1`. The artifact is **not deployed to the phone** by
that script (deployment is the serialized live group's job).

Latest run — **30 checks, 0 failures**:

* header/config agreement (mp4 geometry, floor, schema version);
* the shipping asset's play-through is 8000 ms;
* the Python model reproduces **every** corpus case, and the compiled C table
  (built here with `cc`) reproduces the same decisions plus its invariants;
* legacy (A31/A32) reproduces the reported defect; A33 shows **at least one
  complete play-through** and **0 cut frames**;
* floor honoured exactly for 1, 2 and 3 cycles; the fail-safe stays bounded for
  floors 0/1/2;
* launcher never ready ⇒ the animation keeps the panel (`resume_animation()` = 1)
  and the bridge never takes ownership;
* auditor accepts a correct single-owner handoff and **rejects** (a) a handoff
  with no completed cycle on the glass and (b) a fixture with two different
  writers (negative control); it reports `floor_honoured_exactly` separately from
  the tolerated `verbose_boot_requested` waiver;
* the verbose-boot waiver never fires without the request file, without a painter,
  before the launcher is ready, or when the floor was reached anyway (invariant 6,
  checked exhaustively over 2×2×2×5×4×2 input combinations in the compiled C layer);
* the consumer that publishes the request file is the same file the bridge reads
  (the harness greps `nuxel-verbose-boot.py` for `anim-skip.request`).

Simulated timeline (this is the fix as a number):

```
scenario                             frames    loops  1st-cut    cut%   handoff verdict
A31/A32 time-based (no floor)           145     0.76       47    24.5   6050 ms CUT - static wallpaper
A33 receipt-driven (floor=1)            195     1.02        0     0.0   8150 ms whole cycle shown
A33, launcher never ready               720     3.75        0     0.0         - whole cycle shown
```

## 5. What the live group must observe (owner/live run, not claimed here)

```sh
dmesg | grep -E 'NUXEL_ANIM_HANDOFF|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY'
cat /run/nuxel-anim-handoff; cat /var/lib/nuxel/fb-owner; cat /run/nuxel-fb-owner.lock
cat /var/lib/nuxel/anim-handoff.log | tail -20
python3 /usr/lib/nuxel/nuxel-anim-handoff.py audit      # verdict on the real boot
```

Expected: the last receipt is `owner=ui stage=LAUNCHER_DISPLAY_OWNER terminal=1
loops>=1`; the animation is visibly shown for at least one whole cycle before the
launcher appears; `FB_OWNER_BUSY` never appears; with the launcher stopped on
purpose, `ANIMATION_RESUMED` appears and the panel keeps animating.

Failure symptoms: the wallpaper appears mid-animation (floor not honoured);
`FB_OWNER_BUSY` (a second writer exists — find it with the lock's PID);
`ANIM_MIN_CYCLE_DEGRADED` (the player stopped emitting `NUXEL_ANIM_LOOP`) — then
follow §6.

## 6. Honest limitations

* The player's loop markers are read from `/dev/kmsg`; if the kernel log is not
  readable the bridge records `anim_clock_unavailable` and degrades **explicitly**
  rather than pretending the floor was met.
* The bridge can only stop the painter (SIGTERM→SIGKILL after identity
  re-verification). If the painter survives, **nothing** is written to the panel:
  the animation keeps sole ownership and the bridge exits non-zero.
* If the operator enables verbose boot, the bridge deliberately waives the floor
  and the receipt says `reason=verbose_boot_requested terminal=0`. That is a
  documented user choice, not evidence that the animation completed — the audit
  tool keeps the two separate.
* `mode` in the config is `receipt`. The A31/A32 time-based rule is kept in the
  model for comparison only (it is what `simulate` prints in its first row); it is
  never selected by the shipped configuration, and the shipped config is what the
  bridge reads.
* `animation_mode=short` is an *earlier* handoff, not a shorter clip: the bridge
  still confirms the stop before it writes a scanout byte, and the receipt still
  records `terminal=0` because the minimum-cycle floor was deliberately waived. It
  is not evidence that a full cycle was seen, and the audit tool does not treat it
  as such.

## 6b. Owner-visible proof (manual proof area 3)

The on-glass half of this briQ is
`docs/beta-finalization/manual-proof/03-display-boot.md` (area 3 — display and boot
animation): watch one normal boot, then read the receipts and markers with
`nuxelctl handoff status|audit`, `cat /run/nuxel-anim-handoff`,
`dmesg | grep -E 'NUXEL_ANIM|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY'` and
`tail /var/lib/nuxel/anim-handoff.log`. The verdict stays **NEEDS_OWNER_TEST** until a
human has watched that boot: the evidence above is a decision table, a compiled binary
and a harness — none of which can see the panel.

## 6c. Flash-free deployment hand-off (`bg-10-live-phone`)

This revision is **repository-only**: nothing here has been copied to the handset
and nothing may be flashed. The deploy step is owned by `bg-10-live-phone`; this is
the exact list it needs, with the install path, the pre-check and the rollback for
each artefact. All of it is userspace under `/usr/lib/nuxel`, `/usr/libexec/nuxel`
and `/etc/nuxel` — **no BOOT, USERDATA, SYSTEM, DTB/DTBO, VBMETA or recovery write,
and no partition is touched at any point.**

| Artefact (repository) | Installs to | Pre-deploy check | Rollback |
|---|---|---|---|
| `tools/s10plus/a33/nuxel-wl-fb.c` → built with `tools/s10plus/a33/build-a33-boot.sh` | `/usr/lib/nuxel/nuxel-wl-fb` (`build/out/s10plus/a33-boot/`) | record the current binary's `sha256sum`; the A32 fallback hash is `e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e` | keep the previous binary next to it and `systemctl restart nuxel-wl-fb` (or restore the A32 binary) — no partition write |
| `tools/s10plus/a33/nuxel-handoff-logic.h` | compiled into the bridge | header compiled from the same tree as the bridge | rebuilt with the bridge |
| `tools/s10plus/a33/nuxel-anim-handoff.py` | `/usr/lib/nuxel/nuxel-anim-handoff` (used by `nuxelctl handoff …`) | `python3 … audit` must run on the device | keep the previous copy; it is read-only tooling |
| `tools/s10plus/a33/nuxel-verbose-boot.py` + `.service` | `/usr/libexec/nuxel/nuxel-verbose-boot` + systemd unit | `systemctl status nuxel-verbose-boot` before; `--status` after | `systemctl disable --now nuxel-verbose-boot.service` restores the pre-A33 behaviour immediately |
| `configs/nuxel/boot/animation-handoff.json` | `/etc/nuxel/boot/animation-handoff.json` | **must be installed with the `keep` rule**; `python3 -c "import json;json.load(open(...))"` | restore the previous file (git has it); no reboot needed |
| `configs/nuxel/boot/verbose-boot.json` | `/etc/nuxel/boot/verbose-boot.json` | **`keep` rule** (an existing user document wins); additive keys only, so an older consumer keeps working | restore the previous file; keys are additive so a downgrade is safe |
| `pwa/nuxel-home/{index.html,css/,js/,manifest.json,sw.js,icons/,assets/}` | the launcher docroot | compare `sha256sum` per file; the SW `CACHE_VERSION` must be `v5-a33` (see §6d) | restore the previous bundle; the cache namespace bump makes the old bundle reclaim itself |
| `pwa/nuxel-apps/settings/*` | the Settings app docroot | `node --check settings.js` locally, then re-check on the device | restore the previous files |
| `tools/s10plus/a33/nuxelctl` | `/usr/bin/nuxelctl` | `nuxelctl verbose-boot status` must not error | restore the previous file |

Deploy order that keeps the single-owner rule intact: (1) files on disk, (2) the
`/etc/nuxel` documents with the `keep` rule, (3) `systemctl restart
nuxel-verbose-boot`/`nuxel-wl-fb`/`nuxel-pwa-host` (smallest affected unit first),
(4) observe one normal boot. **Never** start a second framebuffer writer to "check"
the bridge: `FB_OWNER_BUSY` is the correct answer, and a second writer on `/dev/fb0`
is exactly the failure this briQ exists to prevent.

Verdict after a successful copy but before an observed boot:
`DEPLOYED_UNVERIFIED`. `VERIFIED_ON_S10PLUS` is never reached without the ownership
receipts from §5 captured on the handset — ownership is evidence, a binary on disk
is not.

## 6d. Cache invalidation for the deployed launcher bundle

The launcher bundle changed in this revision (`js/qs.js` gained the boot-diagnostics
long-press, `js/settings-store.js` gained the two controls), so the service-worker
namespace was bumped `v4-a33` → **`v5-a33`** in both `pwa/nuxel-home/sw.js`
(`CACHE_VERSION`) and `pwa/nuxel-home/manifest.json`
(`nuxel.cache_version`). Without the bump a launcher restored from the v4 cache
would keep serving the old tile with no way to tell. `launcher-registry-test.js`
asserts `sw.js CACHE_VERSION == manifest.cache_version` and that it has advanced
past the A32 baseline `v3-a32`; `sw.js`'s `activate` handler deletes every other
namespace, and the host purges WebKit's caches and version-stamps the launcher URL
(`tools/s10plus/a32/nuxel-pwa-host.c`, guarded by `INV-1`).

## 7. Rollback

Repository-only change. `git revert` the commit(s) touching
`tools/s10plus/a33/nuxel-wl-fb.c`, `tools/s10plus/a33/nuxel-anim-*.py`,
`tools/s10plus/a33/nuxel-handoff-logic.h`,
`configs/nuxel/boot/animation-handoff.json`. On the device, roll the userspace
bridge back to the A32 binary (`/usr/lib/nuxel/nuxel-wl-fb`, sha256
`e4b4293e8d3d7d5e1c168e58c80ef23e4cb64db30313f0658498362ccaca7b9e`, per
`docs/beta-finalization/baseline-protection.json`) and restart
`nuxel-wl-fb.service`. No boot/USERDATA/DTB write is involved at any point —
**no flashing of any kind**.
