# REPORT-PWNAGE-105000 — static boot penguin after the input round

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820)  
**Access:** `ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16`  
**Run:** 2026-11-09 21:10–21:25 CET  
**Status:** `FIXED_AND_VERIFIED_ON_REBOOT`

---

## A. Symptom

The boot sequence ended on a single, static penguin frame instead of the
spinning boot animation. The initramfs MP4 player itself was healthy: it logged
`NUXEL_ANIM_LOOP=1/2/3`, `NUXEL_ANIM_DRAWN_FRAMES=569/572/683`, and
`NUXEL_ANIM_PAN_FAILED_TOTAL=0`, and the DECON event log showed a window update
every ~41 ms (24 fps) throughout the animation window.

The static penguin was the **PWA pre-lockscreen poster**, not the MP4 player.

## B. Root cause

The PWA is served from `/usr/share/nuxel/pwa/nuxel-home` on this image
(layout A). The preload controller still wrote its same-origin status document
to the old layout-B path:

```
written:  /usr/share/nuxel/nuxel-home/preload-status.json
fetched:  /pwa/nuxel-home/preload-status.json
       -> /usr/share/nuxel/pwa/nuxel-home/preload-status.json   (404)
```

Measured on the handset before the fix:

| Boot | `preload-status.json` responses in `nuxel-web` |
|---|---|
| -2 (19:35) | **741 × 404** |
| -1 (20:53) | **378 × 404** |
| 0 (21:02) | **378 × 404** |

`pwa/nuxel-home/js/app.js::_holdPreloadCover()` therefore never received
`starting`/`covered`/`done`. It kept the opaque `#preload-cover` (the first
frame of `nuxel-preloading-screen.mp4`, a penguin poster) over the launcher
until its hard timeout. The code also had a 40 s timeout while its own comment
and the boot budget documented 15 s.

The initramfs animation is hidden behind that cover only while the MP4 player
owns `/dev/fb0`; as soon as `nuxel-wl-fb` takes the panel, the stale poster is
what the owner sees.

## C. Fix

1. `services/nuxel-preload-cinema/nuxel-preload-cinema`
   - `DEFAULT_STATUS` is resolved from the **actual launcher docroot**
     (`/usr/share/nuxel/pwa/nuxel-home` first, then the legacy
     `/usr/share/nuxel/nuxel-home`).
   - `NUXEL_PRELOAD_STATUS` still overrides it.
2. `tools/s10plus/a29/nuxel-session.sh`, `tools/s10plus/a45/nuxel-session.sh`,
   `release/s10plus/gpu/nuxel-session.sh`
   - export `NUXEL_PRELOAD_STATUS="$PRELOAD_STATUS_FILE"` when starting the
     early preload controller, so the controller and the session cannot drift.
3. `pwa/nuxel-home/js/app.js`
   - cover timeout restored to **15 s** (poll and hard stop);
   - a 404/missing status document now fails open after **4 s**, and a fetch
     failure after 6 s, instead of holding the poster for the full timeout.

The live device was patched in place; backups:

```
/root/nuxel-boot-anim-fix-backup-20261109T201638Z/
/root/nuxel-boot-anim-fix-backup-20261109T201653Z/
```

## D. Verification (after reboot, 21:23 CET)

The served document now exists and returns HTTP 200:

```
/usr/share/nuxel/pwa/nuxel-home/preload-status.json
curl http://127.0.0.1:8000/pwa/nuxel-home/preload-status.json -> 200
```

A 0.5 s compositor/poster sampler was run through the whole boot. It observed
the real state machine in the *served* file:

```
t=0.0s    state=starting  (initramfs MP4 owns the panel)
t=16.7s   wlfb FRAMES_OK display=on
t=17.3s   state=covered   (mpv first frame)
t=22.9s   state=done      (video EOF)
```

Frames captured at 0.5 s intervals were compared with the first preload frame,
the actual MP4 frames and the lockscreen:

| Captures | Best match | Meaning |
|---|---|---|
| `010`–`021` | video frame 0 (diff 1.03) | poster behind the initramfs animation |
| `022`–`029` | video frames 1.0–5.75 s (diff 10–25) | **video visible**, not a static poster |
| `030`+ | lockscreen (diff 2.37) | lockscreen after video EOF |

No `preload-status.json` 404 is logged in boot 0. `systemctl --failed` is
empty and the animation still reports 2–3 complete MP4 loops with zero pan
failures.

## E. Files changed on the handset

```
/usr/lib/nuxel/nuxel-preload-cinema
/usr/lib/nuxel/nuxel-session.sh
/usr/share/nuxel/pwa/nuxel-home/js/app.js
/usr/share/nuxel/nuxel-home/js/app.js     (legacy layout copy)
/etc/systemd/system/nuxel-preload-cinema.service
```

The static systemd fallback unit also gained
`/usr/share/nuxel/pwa/nuxel-home` in `ReadWritePaths`, so a systemd-only boot
cannot fail the same write under `ProtectSystem=full`.

The initramfs/boot image was not touched; the MP4 player, container
(`7d296871…`) and boot animation were not the fault.

## F. Repository changes

```
services/nuxel-preload-cinema/nuxel-preload-cinema   layout-aware status path
tools/s10plus/a29/nuxel-session.sh                  export NUXEL_PRELOAD_STATUS
tools/s10plus/a45/nuxel-session.sh                  export NUXEL_PRELOAD_STATUS
release/s10plus/gpu/nuxel-session.sh                export NUXEL_PRELOAD_STATUS
pwa/nuxel-home/js/app.js                            15 s bound + 4 s 404 fail-open
services/nuxel-preload-cinema/nuxel-preload-cinema.service  layout-A writable path
tests/pwnage31000/test_preload_cinema.py            served-docroot regression test
CHANGELOG.md                                        v0.8.2-beta fixed entry
```

Offline checks:

```
python3 -m py_compile services/nuxel-preload-cinema/nuxel-preload-cinema
node --check pwa/nuxel-home/js/app.js
python3 -m pytest -q \
  tests/pwnage31000/test_preload_cinema.py::test_default_status_path_follows_the_served_docroot
git diff --check
```

The remaining PWNAGE-31000 harness failures on this Mac are the documented
`ipc-unavailable` Unix-socket/path-length limitation, not a regression from this
change; the served-docroot test above passes.
