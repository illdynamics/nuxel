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
| Verbose boot may waive the floor — **only** as a recorded operator choice | Decision 5 of the shared table: if `/run/nuxel/anim-skip.request` says `ANIM_SKIP_REQUESTED` (published by `nuxel-verbose-boot` when the durable verbose-boot setting is ON), the floor is waived for that boot only. The receipt/state records `ANIM_MIN_CYCLE_SKIPPED` / `reason=verbose_boot_requested` with `terminal=0`, so a waiver can never be mistaken for a completed cycle. With no request file this branch is inert |
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
```

Latest run — 23 checks, 0 failures:

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
