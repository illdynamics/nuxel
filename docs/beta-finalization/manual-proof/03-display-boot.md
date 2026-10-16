# Area 3 — Display and boot animation

**Status: NEEDS_OWNER_TEST on the handset; `OFFLINE_TESTED` repository side.**
Owner action required? **Yes** — the handoff, the colour order and the boot log are things only
a human can *see*. No script run may promote any of this to `VERIFIED_ON_S10PLUS`.
The live/vm legs are owned by `bg-10-live-phone` (`docs/beta-finalization/live/REBOOT-AND-VERIFY.md`)
and `bg-11-vm-parity`.

Implementation: `tools/s10plus/a33/nuxel-wl-fb.c` (bridge), `tools/s10plus/a33/nuxel-anim-handoff.py`
(harness), `tools/s10plus/a33/nuxel-handoff-logic.h` (the shared decision table),
`tools/s10plus/a33/nuxel-verbose-boot.py` + `nuxel-verbose-boot.service` (early boot stage),
`configs/nuxel/boot/animation-handoff.json`, `configs/nuxel/boot/verbose-boot.json`.
Docs: `docs/beta-finalization/boot/ANIMATION-HANDOFF.md`, `…/VERBOSE-BOOT.md`,
`…/COLOUR-CONVERSION.md`, `docs/beta-finalization/launcher/SAFE-ZONES.md`.

---

## 1. Feature

Five owner-visible properties of the boot surface, in the order they happen on a normal boot:

| # | Claim | Prior defect it replaces |
|---|---|---|
| 3.1 | The boot animation plays **at least one complete cycle** (192 frames @ 24 fps = 8000 ms) before the panel changes hands | A32 stopped the player on a short time gap, cutting the second half of the MP4 |
| 3.2 | **Exactly one** process writes `/dev/fb0` at any moment, and the handoff is recorded as a receipt | A30 had two writers alternating frame by frame |
| 3.3 | The launcher takes over only **after** it is ready; if it is not ready, the animation **resumes** (never a blank or silently static frame) | a static wallpaper left on the glass |
| 3.4 | Colour order is correct: a pure **red** image is red on the glass, not blue (XRGB8888 shm → DECON `ABGR_8888`) | R/B swap on the glass (A29–A31) |
| 3.5 | The **verbose-boot** option exists in Settings, is durable, and puts the boot log on the glass early — and the one-time **Bixby hold** override is either honoured or honestly reported as requiring a BOOT update | a cosmetic switch that claims an effect it does not have |
| 3.6 | The status bar is inside the ten-zone safe areas (zones 9,10 excluded in S10+ portrait) throughout and after the handoff | items drawn under the hole-punch — see area 2 |

## 2. Why this matters

The boot surface is the first thing the owner sees and the one place where a defect is
unmistakable: a cut animation, a frozen wallpaper, a blue sky that should be red, or a boot log
that never appears. It is also the surface where two writers can corrupt each other’s frames, so
single ownership is a correctness property, not a style choice.

## 3. Preparation

1. Handset connected on the live USB console, root available, **not** in charger mode
   (`tr ' ' '\n' < /proc/cmdline | grep androidboot.mode` must print nothing).
2. Nothing is flashed, no partition is written, no bootloader interface is touched for this
   test. It is a **normal reboot** and a read-only audit.
3. Capture the pre-reboot state so the comparison is real:

   ```sh
   cat /run/nuxel-anim-handoff 2>/dev/null            # last handoff receipt (or absent)
   cat /var/lib/nuxel/fb-owner 2>/dev/null            # last ownership record
   tail -n 20 /var/lib/nuxel/anim-handoff.log 2>/dev/null
   ```
4. Confirm a rollback path exists before rebooting — the userspace rollback route in
   `docs/beta-finalization/release/ROLLBACK.md`; this group never modifies it.
5. Budget: one boot (~60–90 s) plus 5 minutes of reading receipts. **One** reboot, not a loop.

## 4. Exact action

1. Reboot normally (`systemctl reboot`) and watch the panel from the first frame.
2. Note what you see, then reconnect the console and audit the boot:

   ```sh
   nuxelctl handoff status          # owner lock + receipt + who owns the panel now
   nuxelctl handoff audit           # grades the real artefacts (receipt, log, min-cycle file)
   cat /run/nuxel-anim-handoff
   ```
3. Read the kernel markers of that boot:

   ```sh
   dmesg | grep -E 'NUXEL_ANIM|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY|NUXEL_FB_OWNER_BUSY'
   ```
4. **Colour order:** open the launcher, display a full-screen **pure red** image (the launcher
   can be driven from the console: `nuxelctl display test-pattern red`, or open any full-screen
   red page). The glass must be **red**.
5. **Verbose boot:** `nuxelctl verbose-boot status` → note the durable value, source and
   override capability. Then enable it (`nuxelctl verbose-boot on`) and reboot once more, and
   confirm the boot log appears on the glass early. Turn it back off afterwards
   (`nuxelctl verbose-boot off`) unless you want to keep it.
6. **Safe areas after handoff:** with the launcher up, confirm the status bar still excludes
   zones 9,10 in portrait (area 2, step 4).

## 5. Expected result

* The animation plays **all the way through** (a full golden/logo cycle, no truncated loop) and
  then, without a blank frame, the launcher appears.
* Receipts and markers:

  | Evidence | Expected content |
  |---|---|
  | `NUXEL_ANIM_LOOP=<n>` / `NUXEL_ANIM_HEARTBEAT_LOOPS=<n>` (from the initramfs player) | counts increase; at handoff `n >= min_cycles` (default 1) |
  | `ANIM_MIN_CYCLE … n/1 reached=1` then `ANIM_MIN_CYCLE_COMPLETED` in `/var/lib/nuxel/anim-min-cycle.completed` | the floor was actually reached, not assumed |
  | `ANIMATION_STOP_REQUESTED` → `ANIMATION_STOP_CONFIRMED` | the stop was requested and then **verified** (process identity re-checked and gone) |
  | `LAUNCHER_DISPLAY_OWNER` + `NUXEL_ANIM_HANDOFF receipt=<id> owner=ui stage=LAUNCHER_DISPLAY_OWNER terminal=1` | the panel changed hands to the launcher, with a receipt id |
  | `/run/nuxel-anim-handoff` | `owner=ui`, `stage`, `terminal=1`, `loops=n/m`, `boot_id`, `ts` |
  | `/var/lib/nuxel/fb-owner` | the single writer record (`owner=nuxel-wl-fb`, `stage`, `ui_writer`, `boot_id`) |
  | `NUXEL_FB_OWNER_BUSY` | must **not** appear in a healthy boot (it means a second writer was refused) |
  | `dmesg | grep -i colour` / the bridge state line | `colour=R@0,G@8,B@16_abgr8888_override=1` |

* Verbose boot: the boot log is visible on the glass before the launcher arrives, the setting
  survives the reboot and is still `verbose_boot=true` with `set_by=user`;
  `/run/nuxel/verbose-boot` reports `NUXEL_VERBOSE_BOOT=1 SOURCE=config`, and the handoff
  receipt says `reason=verbose_boot_requested terminal=0` (a deliberate waiver — it must never
  be reported as a completed animation cycle).

## 6. Failure symptoms → what they mean

| Symptom | Meaning |
|---|---|
| Animation stops halfway / logo freezes mid-loop | the minimum-cycle floor was not honoured (`ANIM_MIN_CYCLE_NOT_SEEN`, `_DEGRADED`, or a `terminal=0` receipt) |
| Animation plays but the panel then shows a **static wallpaper piece** or black | the launcher never took ownership and no resume happened — inspect `owner=` in the receipt and the `LAUNCHER_DISPLAY` marker |
| Frames from two sources alternate (jitter, tearing between two images) | two `/dev/fb0` writers; look for `NUXEL_FB_OWNER_BUSY` and both writers in `/run/nuxel-fb-owner.lock` / `/var/lib/nuxel/fb-owner` |
| Everything is blue that should be red (icons, wallpaper, green Wi-Fi tick) | the colour conversion was bypassed — area 3.4 |
| Verbose boot switched ON but no log on the glass | the early boot stage did not run/read `/etc/nuxel/boot/verbose-boot.json`; check `systemctl status nuxel-verbose-boot` and `/var/log/nuxel/boot-stage.log` |
| The Bixby hold override does nothing at boot | **expected today**: the installed early boot stage cannot read the Bixby key state — `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED`, deliberately not faked |
| Status items under the cutout after handoff | safe-zone layout — area 2 |

## 7. Diagnostic commands and log paths

```sh
nuxelctl handoff status | simulate | audit        # receipt, owner lock, replayable timeline
nuxelctl verbose-boot status | on | off | override
cat  /run/nuxel-anim-handoff                      # ownership receipt (K=V)
cat  /var/lib/nuxel/fb-owner                      # durable single-owner record
tail /var/lib/nuxel/anim-handoff.log              # append-only ownership audit log
cat  /var/lib/nuxel/anim-min-cycle.completed      # floor result of the last boot
cat  /run/nuxel/verbose-boot /run/nuxel/anim-skip.request /run/nuxel/boot-stage-capabilities
tail /var/log/nuxel/boot-stage.log                # early-stage verbose-boot consumer log
dmesg | grep -E 'NUXEL_ANIM|ANIM_MIN_CYCLE|ANIMATION_STOP|LAUNCHER_DISPLAY|NUXEL_FB_OWNER_BUSY'
python3 tools/s10plus/a33/nuxel-anim-handoff.py audit        # offline grading of the artefacts
python3 tools/s10plus/a33/nuxel-verbose-boot.py --selftest   # offline durability harness
```

## 8. Result

| Check | Result | Evidence |
|---|---|---|
| 3.1 complete animation cycle before handoff | ☐ PASS ☐ FAIL | `nuxel-anim-handoff.py selftest`: decision table over 22 cases + compiled C layer; `simulate` prints the legacy cut (negative control) next to the A33 behaviour (0 skipped frames) |
| 3.2 single framebuffer owner | ☐ PASS ☐ FAIL | bridge takes `/run/nuxel-fb-owner.lock`, identity-verifies the holder, refuses to be a second writer (`FB_OWNER_BUSY`); `audit` **rejects** a fixture with two different writers |
| 3.3 launcher-not-ready ⇒ animation resumes | ☐ PASS ☐ FAIL | `selftest`: “launcher never ready ⇒ animation keeps the panel”, “with no launcher the bridge never takes ownership” |
| 3.4 colour order (red stays red) | ☐ PASS ☐ FAIL | `test-colour-order.py`: golden bytes for R/G/B/white/black/mixed; LUT equals an independent reference over 74 words |
| 3.5 verbose-boot setting (durable, UI + console, boot consumer) | ☐ PASS ☐ FAIL | `nuxel-verbose-boot.py --selftest`: fresh install, upgrade-keep rule, legacy migration, unreadable document refused, override honoured/refused. On-glass effect needs the owner |
| 3.5b Bixby hold override | `BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED` | the installed early boot stage does not publish `bixby-hold-override=1`; the harness asserts the request is *refused, not faked* |
| 3.6 safe areas through the handoff | ☐ PASS ☐ FAIL | `tools/s10plus/a32/tests/safe-zones-test.js` (see area 2) |

**Current automatic evidence (build host, 2026-10-16):**
`nuxel-anim-handoff.py selftest` → *handoff harness selftest (0 failures)*, 29 checks including
the C layer compiled and executed against the shared 22-case corpus;
`nuxel-verbose-boot.py --selftest` → *verbose-boot offline harness passed (upgrade-safe, offline)*;
`test-colour-order.py` → *colour-order golden-bytes test (0 failures)*;
`bash tools/s10plus/a33/tests/run-boot-tests.sh` → all legs pass.
**No boot in this repository-only run has been observed by a human**, so the area verdict stays
`NEEDS_OWNER_TEST` (handset) with the VM leg owned by `bg-11-vm-parity`.
