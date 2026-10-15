# NUXEL — WHY THE PENGUIN NEVER BECOMES A PHONE UI (A23/A24, PROVEN ON HARDWARE)

```
FINDING      = the Fedora userspace on this image NEVER finishes booting
MEASURED ON  = A23 boot, 2026-10-15, ~6 minutes of uptime
EVIDENCE     = every systemd job in state "waiting", nothing running, is-system-running=initializing
CONSEQUENCE  = any unit that depends on a target (i.e. every normally-enabled service) never starts
```

## 1. The measurement

On the A23 boot, over the live CDC-ACM console, with the MP4 animation running at
24.00 fps:

```
$ systemctl is-system-running
initializing                       # ~150 s and again at ~360 s after switch_root
$ systemctl is-active multi-user.target graphical.target sysinit.target basic.target
inactive  inactive  inactive  inactive
$ systemctl list-jobs
 JOB UNIT                              TYPE  STATE
  40 systemd-udevd.service             start waiting
  23 systemd-firstboot.service         start waiting
   3 sysinit.target                    start waiting
  33 systemd-tmpfiles-setup.service    start waiting
   2 basic.target                      start waiting
  79 sockets.target                    start waiting
 109 getty@tty1.service                start waiting
 106 ModemManager.service              start waiting
  17 local-fs-pre.target               start waiting
  13 local-fs.target                   start waiting
   1 multi-user.target                 start waiting
 116 dbus-broker.service               start waiting
 ... (and no job in state "running" at all)
```

There is **no `/etc/fstab`** in this rootfs, so it is not a missing mount entry.
Whatever the first unsatisfiable ordering dependency is, the whole graph waits behind
it and *nothing* downstream can run.

## 2. Why this looked like "the animation never exits"

Nothing was ever wrong with the renderer. The boot-animation player is started by the
initramfs `/init` (not by systemd), so it runs regardless -- and it correctly keeps the
panel while it waits for a UI that can commit a frame. The UI, however, was enabled into
`multi-user.target.wants`, and that target never arrives. A21/A22 never noticed because
every test until now was performed either in the initramfs or by hand from the console.

Two further traps were measured on the same boot:

* `systemctl start nuxel-ui` **blocks forever** (the start job inherits the stalled
  ordering), and the host-side console session dies if the Mac closes the port, which
  *looked* like a frozen phone. It was a blocked `systemctl`, not a blocked phone.
* `systemctl show -p ConditionResult nuxel-ui` reported `no` even though `/dev/fb0`
  exists (`crw------- 1 root root 29, 0`) -- i.e. do not trust `ConditionPathExists`
  as a boot gate on this system; the UI now carries no conditions at all and checks
  the framebuffer itself.

## 3. The fixes (A24)

| Fix | Where |
|---|---|
| The UI unit carries **no ordering and no conditions** (`Restart=always`); it opens `/dev/fb0` itself and retries | `tools/s10plus/a24/nuxel-ui.service` |
| Enabled in **`sysinit.target.wants` as well as `multi-user.target.wants`** (sysinit is reached before local-fs) | `boot/initramfs/init.sh` (`nuxel_install_ui`) |
| **`nuxel-postboot.sh`**, started by `/init` before `switch_root` so it survives it (exactly like `nuxel-console`): writes `/var/lib/nuxel/bootreport.txt` (is-system-running, jobs, failed units, procs, panel, input, journal warnings) and starts the UI directly, then keeps re-starting it | `tools/s10plus/a24/nuxel-postboot.sh` |
| The **live console respawns its shell** after any exit, including the SIGHUP the ACM tty raises when the host closes the port | `tools/s10plus/a24-nuxel-console.c` |

The three independently-proven regression baselines (A16 display, A18 service execution,
A21/A22 MP4 at 24 fps) are untouched by any of this.

## 4. Still open

The **root** unsatisfiable dependency in the Fedora unit graph has not yet been named:
`nuxel-postboot.sh` now dumps `list-jobs`, `--failed`, `journalctl -b -p warning` and the
process table into `/var/lib/nuxel/bootreport.txt` on every boot, and that report is
readable from TWRP with a single `mount /data`, so the next boot names it.
`systemd-firstboot.service` and `rpmdb-rebuild.service` are the first candidates
(both are Fedora first-boot machinery that this read-only-configured image does not
need); neither is masked yet, because masking without the report would be a guess.
