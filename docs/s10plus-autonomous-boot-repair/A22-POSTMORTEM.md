# A22 POSTMORTEM (2026-10-15)

```
BOOT_RESULT      = FAILED_USER_RETURNED_TO_TWRP      (operator hard-reset at t=129 s)
RECOVERY_ACCESS  = RESTORED (TWRP re-identified 17:54:24Z)
NEXT_ACTION      = determine the panel's TRUE channel order, then A23
```

## What A22 did on hardware — every measurable claim held

```
NUXEL_ANIM_MARKER FIRST_FRAME_COMMITTED                  t=7.60 s
NUXEL_ANIM_HEARTBEAT_FRAMES=2880 MS=119986 SKIPS=0 LOOPS=15   t=127.6 s
   -> 2880 / 119.99 s = 24.00 fps, zero dropped frames, animation looped 15x
decon_enable - (state:OFF -> ON)  at t=7.45 s  (the player's own bring-up)
no NUXEL_ANIM_PAN_FAILED / PAN_REASSERT lines  -> the panel was never released
                                                   during the run
persisted in the Fedora rootfs: ANIM_STAGE=MP4_PLAYER_ACTIVE,
                                fb-anim-ready=MP4_FIRST_FRAME_COMMITTED,
                                stale fb-hold.pid / fb-anim.pid cleared at boot
```

The end-of-run signature is again the operator's hard-reset hook
(`pc : hard_reset_hook_callback+0x144/0x150`, `Kernel panic … Fatal exception in
interrupt`, `sec_reboot (0, panic)`) — t=129 s. As with A21 this is an operator action,
not a fault of the candidate, and it must not be reported as a crash.

Note the improvement over A21: A21's run suffered 1279 failed pans after a diagnostic
`dd if=/dev/fb0` released the DECON. A22's run had **zero** — the console was used
read-only, and the self-heal path (which would have logged and recovered) was never
needed. The self-heal itself remains unexercised on hardware.

## The question A22 leaves open — and why it is now the only blocker

Everything on the *device side* of the colour path is proved:

* the container's palette maps to the source colours exactly (offline, max channel
  error 0 for both 8/8/8 layouts);
* the destination pixels are built from the runtime `fb_var` bitfields, and the
  on-device round trip `expected == readback` for red, green, blue, white and black;
* this kernel/Nuxel reports `red.off=16 green.off=8 blue.off=0`, and TWRP agrees.

What no host-side test can decide is **how the panel's DECON actually interprets memory
at bits 0..7 versus 16..23**. The A20 photograph is ambiguous between the two hypotheses:

| Hypothesis | What A20 would have shown | What A21/A22 should show |
|---|---|---|
| fb_var is honest (B,G,R,A memory order) | dark blue/cyan artwork, dead red channel, the painter's opaque sprite square, penguin with orange beak | the original artwork with correct colours |
| the panel swaps R and B relative to fb_var | the artwork's blue circuitry appears **red** | the artwork's blue circuitry would **still** appear red |

The operator reported "red" on A20, and reset A21 and A22 quickly. That is consistent
with either hypothesis, so the next step is not another flash — it is **one observation**.

## The one-glance test that settles it

`--colourtest=SECS` (A22 player, run in TWRP, currently on the panel) paints the same five
colours left to right — red, green, blue, white, black — **twice**:

* **TOP half**: packed with the driver-declared fields (`red=0x00FF0000`, `blue=0x000000FF`)
* **BOTTOM half**: red and blue fed to the opposite fields
  (`red=0x000000FF`, `blue=0x00FF0000`)

```
NUXEL_COLOURTEST_RED=16711680  NUXEL_COLOURTEST_BLUE=255
NUXEL_COLOURTEST_SWAP_RED=255  NUXEL_COLOURTEST_SWAP_BLUE=16711680
```

* if the **top** half reads red-green-blue-white-black → fb_var is honest → A21/A22 were
  already correct and the remaining problem is something else entirely;
* if the **bottom** half reads red-green-blue-white-black → the panel swaps R and B
  relative to `fb_var` → the conversion must be inverted (a one-line change feeding red
  to `blue.offset` and vice versa), and that single change explains the operator's
  "red" on A20 as well.

The same five-colour set is what the mission's section 8 requires to be tested
independently; this test is deterministic, bounded, opt-in and never used by the boot
path.

## Fix applied for A23 regardless of the answer

`NUXEL_INIT_REV` was still `A21-one-penguin-correct-colours` in the A22 initramfs — a
candidate-identification defect (a capture could not tell A21's `/init` from A22's). It is
now `A23-self-healing-panel`, and this must be bumped for every candidate: the mission's
requirement that "a capture can never again be ambiguous about which `/init` ran" applies
to the identifier itself.
