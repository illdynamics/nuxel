# A26 — THE FEDORA SYSTEMD BOOT GRAPH IS REPAIRED (measured live, 2026-10-15)

**Result: `systemctl is-system-running` = `running`. Before this cycle it had never
been anything but `initializing`.**

All of the following was measured over the live CDC-ACM console on the running
handset (SM-G975F / beyond2lte / Exynos 9820 / Samsung Linux 4.14.253 / Fedora 43
aarch64 / systemd 258.11). No reboot was used to obtain any of it: every fix was
applied to the running system and verified in place.

---

## 1. Symptom

`NUXEL-BOOT-STALL.md` recorded it: minutes after `switch_root`,
`systemctl is-system-running` was still `initializing`, and *every* job was
`waiting` — 46 jobs listed, exactly one of them in state `running`:

```
JOB  UNIT                                       TYPE  STATE
43   systemd-tmpfiles-setup-dev-early.service   start running      <-- the head
3    sysinit.target                             start waiting
2    basic.target                               start waiting
26   local-fs.target                            start waiting
1    multi-user.target                          start waiting
50   nuxel-ui.service                           start waiting
...
46 jobs listed.
```

Nothing could start, so `nuxel-ui.service` (a normal unit) could never run and
`systemctl start nuxel-ui` blocked forever. That — not a renderer — is why the
phone stayed on the animation.

## 2. Root cause #1 — a varlink userdb lookup that can never be answered

`systemd-tmpfiles-setup-dev-early.service` is
`Type=oneshot`, `TimeoutStartUSec=infinity`, `Before=sysinit.target`. Its process
was parked in `epoll_wait` forever. `SYSTEMD_LOG_LEVEL=debug` on the exact
command it runs (`timeout 18 systemd-tmpfiles --prefix=/dev --create --boot
--graceful`) gave the last thing it ever did:

```
Reading config file "/usr/lib/tmpfiles.d/static-nodes-permissions.conf"…
Entry "/dev/snd/seq" matches include prefix "/dev".
varlink: Setting state idle-client
/run/systemd/userdb/io.systemd.DropIn: Sending message:
   {"method":"io.systemd.UserDatabase.GetGroupRecord",
    "parameters":{"groupName":"audio","service":"io.systemd.DropIn"}}
/run/systemd/userdb/io.systemd.DropIn: Changing state idle-client → awaiting-reply
   <-- and it never returns.  rc=124 after `timeout 18`.
```

The lookup is for the **`audio`** group, needed to apply
`z /dev/snd/seq 0660 - audio -`. The `io.systemd.DropIn` socket at
`/run/systemd/userdb/io.systemd.DropIn` is created and *symlinked* by
`systemd-userdbd.socket`, but `systemd-userdbd` itself cannot run:

```
systemd-userdbd[6181]: Failed to watch child 6182: Function not implemented
systemd-userdbd[6181]: Failed to start up daemon: Function not implemented
systemd[1]: systemd-userdbd.service: Main process exited, code=exited, status=1/FAILURE
```

`Function not implemented` = **ENOSYS**. systemd 258 dropped the legacy
`waitid()`-based child watcher and requires `pidfd` (`pidfd_open`, Linux 5.3) for
`sd_event_add_child()`. This kernel is 4.14. So the socket exists, nothing
listens on it, and **every** client blocks forever instead of failing.

## 3. Root cause #1b — nsswitch made *every* lookup hang

```
$ cat /etc/nsswitch.conf          # -> symlink to /etc/authselect/nsswitch.conf
passwd:     files systemd
shadow:     files systemd
group:      files [SUCCESS=merge] systemd
gshadow:    files systemd
```

`[SUCCESS=merge]` forces the `nss-systemd` module to be consulted on **every**
group lookup even when `files` already succeeded. `nss-systemd` speaks the same
userdb varlink API, so:

```
$ time timeout 10 getent group audio
  (hangs)                                    getent_rc=124
```

`/etc/group` *did* contain `audio:x:63:` — the local answer was present and
correct all along; the merge turned a 0.003 s lookup into an infinite one.

**Fix applied live and verified:**

```
$ sed -i -e 's/^passwd:.*/passwd:     files/' \
         -e 's/^shadow:.*/shadow:     files/' \
         -e 's/^group:.*/group:      files/' \
         -e 's/^gshadow:.*/gshadow:    files/' /etc/authselect/nsswitch.conf
$ time timeout 6 getent group audio
audio:x:63:
real    0m0.003s                                     getent_rc=0
```

On the target, `/etc/nsswitch.conf` is a symlink into authselect, so the edit is
made on the target file and the original is kept as `*.nuxel-orig`.

## 4. Root cause #2 — dbus-broker cannot start either

Once tmpfiles unblocked, the graph moved one step and stopped again:

```
JOB 112  polkit.service        start running   (activating, 37 s)
JOB 111  ModemManager.service  start waiting
JOB 1    multi-user.target     start waiting
```

`polkitd` had started (`Started polkitd version 126`) but is `Type=dbus`, so it
must acquire `org.freedesktop.PolicyKit1` on the **system bus** — and the system
bus was not there:

```
dbus-broker-launch[6417]: ERROR launcher_fork @ ../src/launch/launcher.c +400:
                                 Function not implemented
dbus-broker-launch[6417]:       launcher_run @ ../src/launch/launcher.c +1422
dbus-broker-launch[6417]: Exiting due to fatal error: -38
systemd[1]: dbus-broker.service: Main process exited, code=exited, status=1/FAILURE
```

**-38 = ENOSYS again** — dbus-broker-launch links `libsystemd.so.0` and uses the
same `sd_event_add_child()` path.

Fedora ships the reference implementation too, and it does not use sd-event:

```
$ rpm -q dbus-daemon dbus-broker
dbus-daemon-1.16.2-1.fc43.aarch64
dbus-broker-37-2.fc43.aarch64
$ ls /usr/lib/systemd/system/dbus*.service
dbus-broker.service  dbus-daemon.service       # same [Install] Alias=dbus.service
```

**Fix applied live:** disable the broker, enable the reference daemon (this is
the documented Fedora switch — the two units are aliases of `dbus.service`):

```
systemctl disable dbus-broker.service
systemctl enable  dbus-daemon.service
systemctl start   dbus-daemon.service
$ systemctl is-active dbus-daemon.service
active
$ busctl --system list | head -3
NAME                          PID PROCESS USER CONNECTION    UNIT
:1.0                            1 systemd root :1.0          init.scope
:1.1                        23415 busctl  root :1.1          init.scope
org.freedesktop.DBus            1 systemd root -             init.scope
```

## 5. Result

```
$ systemctl is-system-running
running
$ systemctl list-jobs --no-pager
No jobs running.
$ systemctl --failed --no-pager --no-legend
(empty)
$ for t in sysinit basic local-fs multi-user sockets; do ...; done
sysinit.target     active
basic.target       active
local-fs.target    active
multi-user.target  active
sockets.target     active
```

Only three jobs had ever been left, and clearing the bus cleared them:

```
JOB UNIT                 TYPE  STATE
111 ModemManager.service start waiting
112 polkit.service       start running
1   multi-user.target    start waiting
3 jobs listed.
```

**Side effect that matters:** `nuxel-ui.service` — a perfectly ordinary unit in
`multi-user.target.wants` — started on its own, and the boot animation stopped:

```
$ systemctl is-active nuxel-ui.service     -> active
$ cat /var/lib/nuxel/animation             -> ANIM_STAGE=ANIMATION_STOPPED
$ cat /var/lib/nuxel/boot-stage            -> STAGE=PHONE_UI_FRAME_COMMITTED ANIMATION_STOPPED=requested
$ cat /var/lib/nuxel/ui-fb-ready           -> PHONE_UI_FRAME_COMMITTED commit=fbio_pan_display fb=1440x3040x32 abgr8888
$ ls -l /run/nuxel-ui.cmd                  -> prw-r--r-- root root /run/nuxel-ui.cmd
```

The A24/A25 "start the UI behind the stalled graph" workarounds are no longer
load-bearing. They stay as belt-and-braces.

## 6. Root cause #3 (containment) — systemd-udevd forks unboundedly

With the graph finally moving, a *new* failure appeared within 50 s of boot, and
it very nearly took the phone with it:

```
$ ps -e --no-headers | wc -l
17537                    # 17318 of them are (udev-worker)
$ free -m | sed -n 2p
Mem:  7420  6944  432          # 0 swap
$ cat /proc/loadavg
16.14 13.67 9.65 ... 17524    # and the board watchdog-reset a minute later
```

`journalctl -u systemd-udevd` explains it in two lines, 17739 times each:

```
systemd-udevd[P]: Failed to create worker object: Function not implemented
systemd-udevd[P]: Received notify datagram of unknown process [N], ignoring.
```

**ENOSYS a third time.** udevd forks a worker, cannot create the worker *object*
for it, therefore never owns or reaps it, and its own `PROCESSED=` notify message
is discarded as "unknown process". Combined with an event storm on the device
tree (`asix: Device ready for processing (SEQNUM=…, ACTION=add, UUID=…)`, 3107
times, the same UUID every time) it forked ~350 processes/second.

**Containment applied live:** udevd and its three sockets are masked.
`CONFIG_DEVTMPFS=y` already gives every node Nuxel needs — verified after the
mask:

```
/dev/fb0 /dev/null /dev/ttyGS0 /dev/urandom /dev/zero
/dev/input/event0 … event10
```

and static `/dev` permissions are applied by `systemd-tmpfiles`, which is proven
to work (§2). After the mask:

```
$ ps -e --no-headers | wc -l     -> 292
$ free -m | sed -n 2p            -> Mem: 7420 518 6799
$ systemctl is-system-running    -> running
$ systemctl --failed             -> (empty)
```

**This is containment, not the finished article.** The correct durable fix is the
same class of source edit A17 already made twice in `systemd` — teach
`sd-event`'s child watcher to degrade to `waitid()` when `pidfd_open` is ENOSYS —
after which `systemd-userdbd`, `dbus-broker` and `systemd-udevd` can all be
un-masked. Tracked below.

## 7. The three fixes, and where they now live in the build

Nothing here may be a phone-only hotfix. All of it is now applied to the rootfs
**staging tree** by `tools/s10plus/a26/nuxel-rootfs-fixes.sh`, which
`images/s10plus/build-phone-rootfs-inside-fedora.sh` runs before packaging:

| # | Change | Why | Verified by |
|---|---|---|---|
| 1 | `authselect/nsswitch.conf`: `passwd/shadow/group/gshadow` → `files` | removes the infinite varlink lookup from every NSS call | `getent group audio` 124 → 0.003 s |
| 2 | mask `systemd-userdbd.{socket,service}` | userdbd cannot run (ENOSYS), so its socket must not exist | `/run/systemd/userdb/` keeps only PID1's own `io.systemd.DynamicUser` |
| 3 | system bus → `dbus-daemon.service` | `dbus-broker-launch` dies ENOSYS in `launcher_fork` | `busctl --system list` returns real names; polkit completes |
| 4 | mask `systemd-udevd.{service,+3 sockets}`, `udev_log=err` | udevd cannot register workers → unbounded fork | 17723 → 292 processes |

The script is idempotent, keeps `*.nuxel-orig` copies, and was self-tested
offline against a throw-away staging tree before being wired into the image
build.

## 8. What is still open on this track

1. **`sd-event` child-watch compat patch** (the real fix for 1–4). A third edit
   alongside `process-util.c` and `pidref.c` in the A17 change set. Until it
   exists, `nuxel-rootfs-fixes.sh` is the shipped configuration.
2. **The uevent storm** (`asix` re-added thousands of times, correlating with
   `wl_cfg80211_netdev_notifier_call: wdev null. Do nothing`). With udevd masked
   nothing consumes it, but it should be identified and stopped at the driver
   level.
3. **cpufreq/power**: `Failed to get CPU usage: No such file or directory` on
   every unit. cgroup v2 on 4.14 exposes only `memory` and `pids` controllers
   (`/sys/fs/cgroup/system.slice/<unit>/` has no `cpu.stat`), so systemd's CPU
   accounting is unavailable. Cosmetic/log-only so far; worth a
   `DefaultCPUAccounting=no` drop-in.
