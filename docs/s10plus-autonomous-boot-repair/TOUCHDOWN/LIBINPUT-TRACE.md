# LIBINPUT TRACE — A34

## Registration

`/run/nuxel-libinput-path.state` on the current boot:

```
PATH_CONTEXT_CREATED ... udev=... (udev daemon not required)
UDEVDB_SEEDED /run/udev/data/c13:66
DEVICE_OPEN_LIBSEAT path=/dev/input/event2 rc=24 fd=-1
PATH_ADD node=/dev/input/event2 name='sec_touchscreen' accepted=1
UDEVDB_SEEDED /run/udev/data/c13:68
DEVICE_OPEN_LIBSEAT path=/dev/input/event4 rc=25 fd=-1
PATH_ADD node=/dev/input/event4 name='sec_touchproximity' accepted=1
PATH_ASSIGN_SEAT seat='seat0' direct_devices_seen=2 added=2 db_seeded=2
```

The libinput path shim is preloaded into phoc (`LD_PRELOAD=/usr/lib/nuxel/libnuxel-libinput-path.so`).
It redirects only libinput's discovery step to the real `/dev/input/event2`
node; parsing remains real libinput. `systemd-udevd` is masked on this 4.14
kernel, so the usual udev database is seeded by the shim. This is the minimum
workaround, not a blanket udev change.

## Delivery

Phoc holds the actual node:

```
lrwx------ 24 -> /dev/input/event2
lrwx------ 25 -> /dev/input/event4
```

A physical contact that appears in evdev also appears in WebKit (see
`WEBKIT-INPUT-TRACE.md`), so for that contact libinput → phoc delivery worked.
There is no libinput debug log for a long continuous trace; that would require
restarting phoc with `LIBINPUT_LOG_PRIORITY=debug`. The end-to-end physical
correlation is stronger evidence than a debug log.

## Verdict

T4 **PASS** (device accepted into seat0). No libinput-side loss demonstrated.
