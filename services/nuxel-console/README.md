# services/nuxel-console — the live console as a declared, single-owner service

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04b-service-definitions` (revision 2, cycle 6)
**Verdict:** `OFFLINE_TESTED` (repository evidence) / `IMPLEMENTED_NOT_DEPLOYED`
as a systemd service — the running console on the handset is still the
**initramfs** instance.

## What is here

| File | What it is |
|---|---|
| `systemd/nuxel-console.service` | the canonical unit for the console: ordering, dependencies, restart policy, jail scoping and the single-owner guard, each with its reason |
| `bin/nuxel-console-free` | the `ExecCondition` guard: takes the SAME `flock(LOCK_EX\|LOCK_NB)` on `/run/nuxel-console.lock` the console takes and exits non-zero if anyone holds it (fail closed) |
| `test-console-ownership.py` | offline test: the unit's semantics, the builder's install-but-not-enable rule, the lock protocol across the three files, and the guard's real `flock(2)` behaviour |

The device-side implementation stays where it is:
`tools/s10plus/a33/nuxel-console.c` (owned by the Live Console app work), and the
initramfs starts it — see `boot/initramfs/init.sh`.

## Why this unit is INSTALLED but NOT ENABLED

The console has exactly ONE owner. A second console on the same tty does not
degrade the protocol, it breaks it (the framed responder and the interactive
shell interleave; the C implementation takes an flock precisely because a second
instance is destructive).

On this image the owner is the **initramfs**: `/init` starts
`/opt/nuxel/nuxel-console` before systemd exists, and it holds
`/run/nuxel-console.lock` for the rest of the boot. Therefore:

* `ConditionPathExists=/usr/bin/nuxel-console` — the rootfs binary. The shipped
  image carries the console in the initramfs, so this condition is false and
  systemd skips the unit (`ConditionResult=no`): an honest "not deployed" rather
  than a failed unit;
* `ExecCondition=/usr/lib/nuxel/nuxel-console-free` — proves the port is free at
  the moment of start, so the unit can never race an owner that appeared in
  between;
* `Restart=no` — a restart loop would fight for the tty; a bounded, visible
  failure is strictly better than two owners;
* the rootfs builder installs the unit and the guard but creates **no**
  `multi-user.target.wants` symlink, and `verify-service-graph.py` fails the
  build if such a line ever appears.

## Single-owner protocol (one lock, three files)

| File | Reference |
|---|---|
| `tools/s10plus/a33/nuxel-console.c` | `lockpath = "/run/nuxel-console.lock"`, `flock(fd, LOCK_EX \| LOCK_NB)` |
| `bin/nuxel-console-free` | `NUXEL_CONSOLE_LOCK` (default the same path), `flock -n <lock> -c true` |
| `systemd/nuxel-console.service` | `Environment=NUXEL_CONSOLE_LOCK=/run/nuxel-console.lock` |

`verify-service-graph.py` cross-checks all three and fails if the C
implementation stops using that path — a guard that probes a lock nobody takes is
a rubber stamp.

## Jail scoping: applied, and deliberately not applied

Applied: `NoNewPrivileges=yes`, `ReadWritePaths=/run`,
`ReadOnlyPaths=/usr/bin/nuxel-console /opt/nuxel /usr/lib/nuxel`.

Not applied, with the reason recorded in the unit: `ProtectSystem=strict` and
`ProtectKernelTunables=yes` (the console writes `/sys/kernel/config` to bind the
CDC-ACM gadget — `CONFIG_USB_CONFIGFS_ACM=y` is the only peripheral-console path
this kernel provides), `PrivateDevices=yes` (it needs `/dev/ttyGS0`, mknod'd from
`/sys/class/tty/ttyGS0/dev`, and `/dev/kmsg`), `ProtectHome`/`PrivateTmp` (the
chroot target and the journal hand-off live in the real hierarchy). The residual
risk is stated rather than hidden: whoever controls this process controls a root
shell on the phone. The Live Console app (Priority 7e) is where the owner-facing
disable and the remote/local arbitration live.

## Reproduce the evidence

```sh
python3 services/nuxel-console/test-console-ownership.py     # unit + guard + builder
python3 tools/s10plus/a33/verify-service-graph.py            # the whole boot graph (15 units)
python3 tools/s10plus/a33/tests/test-service-graph.py        # prove the validator can FAIL
bash tools/s10plus/a33/tests/run-userspace-tests.sh          # all of Priority 4
```

## Rollback

Repository-only until someone enables the unit: `git revert` the commit that
added `services/nuxel-console/` and the two builder lines. Nothing here changes
the running console, the initramfs, any partition or any device state; if the
unit is ever enabled on the handset, the rollback is
`systemctl disable --now nuxel-console.service` followed by the initramfs
instance (already running) taking the port back.
