# 02 — THE S10+ LAUNCHER RUNTIME, BEFORE AND AFTER (measured live)

Console: `/dev/cu.usbmodem201`, framed SHA-verified round trips via
`scripts/s10plus-debug-pack/nuxel-live.sh`; files via
`tools/s10plus/a29/push-file.sh` (per-chunk acknowledged, 380-char chunks).

## BEFORE (first inspection of this cycle)

```
uname -r                       4.14.253 #15 SMP PREEMPT  (Fedora 43, systemd 258)
/proc/cmdline                  no androidboot.mode=charger  -> normal boot
systemctl list-units 'nuxel*'  nuxel-touch-arm active, nuxel-wayland active, nuxel-wl-fb active
ps --sort=-pcpu
  5436 nuxel-wl-fb         65.6%   /usr/lib/nuxel/nuxel-wl-fb
  3523 nuxel-anim-player   42.2%   /opt/nuxel/nuxel-anim-player … --stopfile=anim-stop
phoc fds                       0 x /dev/input/*          <-- compositor had NO input device
/run/nuxel-wl-fb.state         FRAMES_OK total=128627 fps_1s=128627 failures=0 … (no owner=)
/var/lib/nuxel/animation       ANIM_STAGE=MP4_PLAYER_ACTIVE
/var/lib/nuxel/anim-stop       ABSENT
curl …/pwa/nuxel-home/assets/nuxel-background.png -> 404 text/html 460
```

The **A30 handoff code was not what was running**: the installed bridge emitted
the A29 state format (`fps_1s=total`, no `owner=`), and nothing ever created
`/var/lib/nuxel/anim-stop`. Two processes therefore painted `/dev/fb0`
simultaneously for the whole session.

## AFTER (end state of this cycle, live)

```
systemctl list-units 'nuxel*'
  nuxel-touch-arm.service active running
  nuxel-wayland.service   active running
  nuxel-wl-fb.service     active running

phoc MainPID fd table       24 -> /dev/input/event2   (sec_touchscreen)
                            25 -> /dev/input/event4   (sec_touchproximity)

/run/nuxel-libinput-path.state
  PATH_ADD node=/dev/input/event2 name='sec_touchscreen' accepted=1
  UDEVDB_SEEDED /run/udev/data/c13:66 (initialized marker; systemd-udevd cannot run on this kernel)
  PATH_ADD node=/dev/input/event4 name='sec_touchproximity' accepted=1
  PATH_ASSIGN_SEAT seat='seat0' direct_devices_seen=2 added=2 db_seeded=2

/run/nuxel-wl-fb.state       FRAMES_OK total=5698 fps_1s=28 failures=0 blit_avg_ms=34
                             out=720x1520 src=720x1520 scale=2 panel=1440x3040 owner=nuxel-wl-fb
/var/lib/nuxel/animation     ANIM_STAGE=ANIMATION_STOPPED   ANIM_OWNER=nuxel-wl-fb
/run/nuxel-anim-stop.confirmed   PRESENT   (proof the painter terminated, not just a request)
pgrep -f nuxel-anim-player   none   |  pgrep -f nuxel-wl-fb | wc -l  -> 1  (single fb owner)
/run/nuxel-home.state        NUXEL_HOME_MEDIA enable_media=0 audio_sink=0
                             NUXEL_HOME_BOOT_OWNER os_animation=1 splash_removed_by_launcher=1
                             NUXEL_HOME_READY uri=http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os
                             NUXEL_INPUT_DIAG enabled=1
curl …/pwa/nuxel-home/assets/nuxel-background.png -> 200 image/png 1257938
```

`NUXEL_INPUT` lines in `/run/nuxel-home.state` are the injected observer's report
of events the *real launcher document* received (see doc 07).
