# 12 — REMAINING LIMITATIONS AND BLOCKERS (honest list, cycle A31)

## Blocked on hardware / kernel (documented, not attempted)

1. **No DRM/KMS** (`# CONFIG_DRM is not set`) → no hardware EGL/GBM, so WebKit
   renders in software (`WEBKIT_DISABLE_COMPOSITING_MODE=1`) and the bridge does a
   CPU blit to the AMOLED. A kernel with DRM + exynos/decon support would remove
   the bridge entirely; that is a BOOT-partition write and was **not** done here.
2. **No VT at all** (`/dev/tty0`, `/sys/class/vtconsole`, `/proc/consoles`
   absent) → seatd's VT-bound seat can never activate, and logind has no session
   source. Input therefore uses `LIBSEAT_BACKEND=noop` + the libinput path shim.
   If the kernel ever grows a VT (or fbcon binds), `seatd` + a session-based
   libinput would be the cleaner configuration; the shim becomes unnecessary.
3. **systemd-udevd cannot run** on Linux 4.14 here (`Failed to create worker
   object: Function not implemented`; measured unbounded forking). It stays masked.
   The consequence is that *no* udev rules run, so the shim writes one
   `/run/udev/data` entry per direct-pointer device from that device's own
   capability data. Any future subsystem that needs real udev rules (power
   management, USB hotplug policy) will need the sd-event child-watcher problem
   solved in systemd first — a library fix, i.e. a rootfs/initramfs change.
4. **No telephony / modem / audio / camera / sensors userspace.** Present in the
   image only as kernel drivers. Native-scheme apps therefore do nothing, and the
   launcher's `phone:status` / `notifications:receive` capability requests fail
   (caught, harmless).
5. **Charger-mode boots have no touchscreen at all** (`sec_ts_init` returns
   `-ENODEV` when `androidboot.mode=charger`). The launcher now still comes up
   (`WLR_LIBINPUT_NO_DEVICES=1`) and reports zero input devices in
   `/run/nuxel-libinput-path.state`, but touch cannot work in that mode. Recovery
   is a controlled normal reboot (a Linux `reboot` clears the mode).

## Blocked on scope (needed for VM parity, not done)

6. **`nuxel-http-bridge` + `nuxel-bridge`/`nuxel-portal`/`nuxel-notifications`
   are not installed.** Porting them needs `python3-dbus` plus the D-Bus policy
   and the portal/notification services. Until then the handset deliberately
   exposes **no** local HTTP API (nothing unauthenticated was added) and the
   launcher's capability calls degrade truthfully.
7. **Frame rate under software rendering is bounded at 30 fps by policy**, with
   measured `fps_1s≈27` and `blit_avg_ms≈36`. A higher target is possible
   (`NUXEL_TARGET_FPS`) but has no proven benefit on software pixman + CPU blit;
   smoothness on the glass is the user's judgement.
8. **The input shim is a workaround for two missing kernel/OS features** (no VT,
   no udev daemon). It is 70 KB, interposes four libinput/libseat entry points,
   only for `/dev/input` direct pointers, and fabricates nothing — but it is an
   `LD_PRELOAD` in the compositor's process, so it must be re-validated whenever
   wlroots or libinput is upgraded. `verify-launcher-live.sh` checks 2/3 cover it.
9. **Live-only vs image state.** Everything in doc 09 is now also expressed in
   `images/s10plus/build-phone-rootfs-inside-fedora.sh`, but the image has **not**
   been rebuilt and flashed in this cycle (that would be a BOOT/userdata write).
   The running handset is a live deployment; a fresh image would ship the same
   configuration but is unverified until built.
10. **`seatd.service` is installed but unused** (documented in doc 09 §deviations)
    and the `seat` group it wanted is unused too. Left in place as the record of a
    measured dead end; the unit is disabled and does not run.
11. **`nuxel-touch-arm` writes `fb0/blank` once at startup** to trigger the panel
    notifier that reaches `sec_ts_start_device()`. It is deliberately a one-shot
    (mission §11.4) and the state file records `ARMED_OK`. A driver-level fix to
    `sec_ts_start_device()`'s `already power on` early return would remove the need
    for it entirely — a kernel-maintenance item, not attempted here.

## Not yet verified (needs the user)

12. **Physical tap → app opens** on the glass (instrumented and waiting; see doc 10
    and the acceptance checklist).
13. **Visual confirmation** that the wallpaper is the one intended and that no
    flicker/black flash remains during the animation-to-launcher handoff.
14. **Reboot persistence of the *image* path** (the live configuration survived a
    reboot; a freshly built image was not flashed, see item 9).

## Appendix — the load average is NOT the launcher

`/proc/loadavg` sits around 12 on this handset, which looks alarming next to a
8-core SoC. Measured breakdown (same instant):

```
ps -eo pcpu,stat,comm --sort=-pcpu
  68.6 Rs  nuxel-wl-fb        <- the one framebuffer writer, CPU blit, ~28 fps
  27.6 Ssl phoc               <- pixman compositing of a 720x1520 output
   6.8 SLl WebKitWebProces
   1.7 Sl  nuxel-pwa-host
ps -eo stat,comm | awk '$1 ~ /^D/' | sort | uniq -c
   8 tz_worker_threa     1 tz_iwsock     1 scsi_srpmb_work     1 ree_time     1 sugov:4
```

The 11 tasks in `D` state are all Samsung vendor kernel threads (TrustZone
worker/interworld socket, RPMB secure-storage work, REE time) — they inflate the
load average on this port and are not part of the Nuxel userspace. Real CPU use of
the whole launcher stack is ~1 core of 8.

## Console hygiene

The kernel console loglevel was temporarily lowered (`printk 1`) so the
kmsg-to-USB mirror would not shred the file-transfer framing, and was **restored
to its original `4 4 1 7`** afterwards. The diagnostic directories created for
temporary phoc instances were removed. No persistent change was left behind
except the deployed artifacts listed in doc 09.
