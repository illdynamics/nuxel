# NUXEL S10+ Camera — Live Physical Acceptance Matrix

**Date:** 2026-11-20
**Device:** SM-G975F beyond2lte, kernel 4.14.253-gf7194c1d15ed-dirty (live via SSH root@10.11.12.99)
**Method:** physical sensor init + ION DMABUF capture on `/dev/video131` (exynos-fimc-is-i0c)

## Result table

| Test | Required result | Observed | Status |
|---|---|---|---|
| Firmware selection | PASS | `rom id[0] 1`, `rta=fimc_is_rta.bin`, SAK2L4 rev 0xA102 | ✅ PASS |
| Rear sensor initialization | PASS | `[MOD:SAK2L4] sensor_module_init(0)`, OIS, actuator 0xE | ✅ PASS |
| Rear physical frame capture | PASS | **no DQBUF yet** | ❌ NOT PASS |
| Front physical frame capture | PASS | not attempted (blocked by #1) | ❌ NOT PASS |
| Rear live preview | PASS | not reached | ❌ NOT PASS |
| Front live preview | PASS | not reached | ❌ NOT PASS |
| Rear JPEG/photo saved | PASS | not reached | ❌ NOT PASS |
| Front JPEG/photo saved | PASS | not reached | ❌ NOT PASS |
| Rear video recording | PASS | not reached | ❌ NOT PASS |
| Front video recording | PASS | not reached | ❌ NOT PASS |
| Recorded microphone audio | n/a (mic verified separately) | — | — |
| Audio/video sync | PASS | not reached | ❌ NOT PASS |
| Gallery photo/video playback | PASS | not reached | ❌ NOT PASS |
| Flash/torch | PASS | not reached | ❌ NOT PASS |
| Native Nuxel Camera | PASS | not reached | ❌ NOT PASS |
| Native GTK camera | PASS | not reached | ❌ NOT PASS |
| Flatpak camera | PASS | not reached | ❌ NOT PASS |
| Camera permissions | PASS | not reached | ❌ NOT PASS |
| Repeated switching | PASS | not reached | ❌ NOT PASS |
| Camera cleanup on exit | PASS | observed clean deinit | ✅ PASS (partial) |
| Kernel stability after capture | PASS | no panic; clean deinit | ✅ PASS (partial) |

## Live trace evidence (2026-11-20 run)

`nuxel-fimc-leader-capture2` (corrected packed S_INPUT):

```
[sensor S_INPUT] 0x00000001 => scenario=0 stream=0 position=0 vindex=0 intype=0 leader=1  ret=0
[sensor S_FMT]      ret=-1 errno=22   <- Problem C: leader S_FMT needs S_INPUT|S_BUFS state
[sensor REQBUFS]    ret=-1 errno=22   <- REQBUFS needs S_FORMAT|STOP|S_BUFS state
[cap S_FMT]         ret=0             <- capture node accepts format (new)
[cap REQBUFS]       ret=0 count=4     <- 4 buffers (new)
[cap QBUF 0..3]     ret=0             <- 4 buffers queued (new)
[cap STREAMON]      ret=-1 errno=22   <- Problem D: needs 3AA/ISP group leader started
[DQBUF]             timeout
```

## Precise remaining blocker (source-backed)

The sensor leader (`ss0`, `/dev/video101`) state machine in `fimc-is-video.c`:

- `S_FMT` (LEADER) requires `BIT(S_INPUT) | BIT(S_BUFS)`
- `REQBUFS` requires `BIT(S_FORMAT) | BIT(STOP) | BIT(S_BUFS)`
- `STREAMON` requires `BIT(S_BUFS) | BIT(STOP)`

This is resolvable but the exact Samsung-HAL ordering (which uses the
`V4L2_CID_IS_S_STREAM` private control + the OUTPUT-queue `.start_streaming` ->
`fimc_is_sensor_back_start` path) must be reproduced. The capture node's `S_FMT`
returns success but `G_FMT` is a stub (`return 0`), so the ISP output format is
established only through the leader's internally-driven sensor mode, not G_FMT.

## Honest conclusion

`FIRST_FRAME_VERIFIED` = **NOT PASS**. Real, incremental progress was made this
session (correct S_INPUT encoding discovered; capture node now reaches 4 queued
buffers). No synthetic/test-pattern frame has been accepted. The next concrete
action is to reproduce the exact leader S_BUFS/S_FMT ordering (or enable the
vendor HAL debug log to capture the authoritative sequence), then start the 3AA
group leader before the ISP capture node STREAMON.
