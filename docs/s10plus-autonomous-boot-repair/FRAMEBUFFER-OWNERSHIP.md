# NUXEL — FRAMEBUFFER OWNERSHIP (A21)

## The rule

**Exactly one renderer may own `/dev/fb0` at any moment, and a renderer may not claim
ownership until it has committed a frame that the DECON will scan.** No renderer may
stop another by trusting `$!`, a stale pid file, or a timer.

## Every framebuffer writer that exists on the S10+

| # | Writer | Source | When it runs | Lifetime |
|---|---|---|---|---|
| 1 | `nuxel-fb-phone` (one-shot) | `tools/s10plus/nuxel-fb-phone.c` | `nuxel_first_light()`, ~t+2 s | one frame + 12 penguin frames, exits 0 |
| 2 | `nuxel-fb-phone hold` | same binary, `hold` arg | A16–A20: launched at first light. **A21: only as fallback** | infinite until stopped |
| 3 | `nuxel-anim-player` | `tools/s10plus/nuxel-anim-player.c` | after the Fedora rootfs mounts | until SIGUSR1/SIGTERM/SIGINT or the stop file |
| 4 | `show_boot_splash()` | `boot/initramfs/init.sh` | only when `/boot/nuxel-boot-splash.raw` exists | writes once |
| 5 | TWRP's own UI | recovery | recovery only | recovery only |
| 6 | a future phone UI | not implemented | — | — |

Writers 1–4 were audited; 1 and 4 are one-shot and mutually exclusive by argument, and
2/3 are the pair that fought on A20.

## Why A20 had two painters — and why nothing could stop the penguin

```
A20 init.sh
  nuxel_first_light()                  (t≈2 s)
      /opt/nuxel/nuxel-fb-phone            <- paints the static first-light frame
      /opt/nuxel/nuxel-fb-phone hold &     <- RESIDENT painter, every 250 ms
      NUXEL_HOLD_PID="unresolved-by-shell(player-publishes-it)"   <- toybox never sets $!
  ...
  nuxel_start_animation()              (t≈8.5 s)
      /opt/nuxel/nuxel-anim-player ... &   <- MP4 frames
      NUXEL_HOLD_PID was never resolvable, so the player had to find the painter itself
```

The player's only stop mechanism was a `/proc` walk, and it failed twice over:

1. **`O_DIRECTORY` is `040000` on this board, not `0x10000`.** `arch/arm64/include/uapi/asm/fcntl.h`
   defines `O_DIRECTORY 040000`, `O_NOFOLLOW 0100000`, `O_DIRECT 0200000`; glibc for
   aarch64 agrees (`__O_DIRECTORY 040000`). The player passed `0x10000`, which is
   `O_DIRECT`, and **procfs rejects `O_DIRECT` with `EINVAL`**:
   ```
   glibc O_DIRECTORY=040000 (16384)
   openat(/proc,O_DIRECTORY)=3 errno=0
   openat(/proc,0x10000)=-1 errno=22        <- A16..A20 did exactly this
   ```
2. **The scan ran after `switch_root`.** init.sh launched the player and immediately
   `exec switch_root`, which moves `/proc`/`/sys`/`/dev` into the new root and deletes
   the old root. Hardware log, A20 journal, t=8.521726:
   ```
   NUXEL_ANIM_TAKEOVER no /proc
   ```
   The same call also invalidated every absolute path, which is why A20's state files
   were never written (they were created relative to `AT_FDCWD` in the *old* root:
   `/fb-anim.pid`, `/fb-anim-ready`, `/animation` were found in the TWRP root, empty of
   value, while `<userdata>/var/lib/nuxel/fb-anim.pid` stayed absent).

Result: the penguin painter kept repainting its opaque sprite square over the MP4
frames 4×/second for the whole 894-second A20 boot (`nuxel-fb-phone: 3416` is in the
panic task dump next to `nuxel-anim-play: 3501` blocked in `decon_wait_for_vsync`).

## The A21 state machine (implemented, in this order)

```
EARLY_FIRST_LIGHT          init.sh nuxel_first_light()      one-shot paint, NO resident painter
   |  NUXEL_MARKER ANIMATION_HOLD_DEFERRED
FEDORA_MOUNTED             nuxel_start_animation()          ANIM_STAGE=MP4_PLAYER_STARTING
   |  player forked, BEFORE switch_root, /proc still valid
MP4_PLAYER_STARTING        player: opens fb, reads bitfields, builds DSTPIX
   |  player publishes fb-anim-starting, then:
FIRST_LIGHT_STOPPED        takeover: /proc scan (plain O_RDONLY), identity-checked SIGTERM,
   |                       bounded <=1.0 s acknowledgement re-reading /proc/<pid>/comm
MP4_FIRST_FRAME_READY      player commits frame 0, writes fb-anim-ready
   |  init.sh sees fb-anim-ready (bounded wait, <= NUXEL_ANIM_WAIT seconds, default 8)
MP4_PLAYER_ACTIVE          init.sh writes ANIM_STAGE=MP4_PLAYER_ACTIVE, does NOT start the painter
   |
switch_root                init execs systemd; the player keeps the fb fd + mmap (no path needed)

--- or, when the MP4 cannot own the panel ---
ANIMATION_PLAYER_MISSING / ANIMATION_CONTAINER_MISSING / MP4_PLAYER_FAILED /
MP4_PLAYER_ACTIVE_TIMEOUT  -> FIRST_LIGHT_FALLBACK -> nuxel_start_hold_painter()
                              the resident penguin painter runs, exactly as A16 did
```

### Stop mechanisms, in order of preference

1. **`fb-anim-ready` / `fb-hold-stop`** in the state directory. The resident painter
   polls both every 4 frames (1 s) and exits on sight — so the fallback *yields to the
   primary automatically* if the MP4 succeeds late.
2. **Identity-checked SIGTERM** from the player: it walks `/proc`, reads
   `/proc/<pid>/comm`, and only signals a process whose comm is exactly
   `nuxel-fb-phone` (a recycled pid can never be killed by mistake), then waits up to
   1.0 s re-verifying that the process is gone (`NUXEL_ANIM_TAKEOVER_STOPPED`).
3. **The painter publishes its own pid** to `<statedir>/fb-hold.pid` — the shell never
   guesses a pid, and `$!` is never used.

## Hardware proof (A21, TWRP, real DECON, real container)

```
resident painter started  (--statedir=…)      -> fb-hold.pid = 5229
MP4 player started with  --holdpid=fb-hold.pid
NUXEL_ANIM_STATEDIR_FD_OK=1                   state dir fd valid
NUXEL_ANIM_PROC_OPEN_RC_PLAIN=6               /proc opens with plain O_RDONLY
NUXEL_ANIM_PROC_OPEN_RC_DIRECTORY=EINVAL      the O_DIRECT O_DIRECTORY bug, reproduced
NUXEL_ANIM_TAKEOVER_PID=5229                  the painter was found by identity
NUXEL_ANIM_TAKEOVER_KILLED=1                  SIGTERM delivered
NUXEL_ANIM_TAKEOVER_STOPPED=1                 and verified gone, bounded
state dir afterwards: animation, fb-anim-ready, fb-anim-starting, fb-anim.pid, fb-hold.pid
   (all five created IN the state directory -- not in /)
```

## Invariants held

* The first-light renderer is **preserved** and still paints before anything else; it is
  never replaced by an untested player, so the panel is never left black.
* The first-light frame stays in framebuffer memory while the player starts, so the
  panel is not blank during the handoff either.
* A renderer that cannot produce a valid frame does not claim the panel: the player
  writes `fb-anim-failed` and exits, and init.sh starts the fallback painter.
* Bounded waits only (no unbounded blocking of PID 1): the rootfs handshake waits at
  most `NUXEL_ANIM_WAIT` seconds, the takeover retries at most 1.2 s, the stop
  acknowledgement at most 1.0 s.
