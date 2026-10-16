# SERVICE-GRAPH — the Nuxel S10+ boot graph as actually installed

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04b-service-definitions`
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) — Fedora 43
aarch64 userspace, Samsung Linux **4.14.253**, **systemd PID 1**
**Verifier:** `tools/s10plus/a33/verify-service-graph.py` → **`OFFLINE_TESTED`**
(14 units, 0 problems, 1 recorded warning; machine-readable report written to
`build/pkgmeta/service-graph.json`)
**Regression test:** `python3 tools/s10plus/a33/tests/test-service-graph.py` —
proves the validator actually *fails* on an injected cycle, an unsatisfied
dependency, a 4.14-forbidden dependency, a lost builder enablement and a lost
A26 repair (a validator that has only ever run against the fixed tree has never
been shown to work).
**Builder:** `images/s10plus/build-phone-rootfs-inside-fedora.sh`
**Verdict scope:** this document is *repository evidence*. `systemctl
is-system-running` on the handset is **not** claimed here — that verdict belongs
to the live-deployment group (bg-10) and is `VERIFIED_IN_VM_ONLY` /
`NEEDS_OWNER_TEST` until it is measured on the device.

---

## 1. Why this document exists

Before A33 the boot graph existed in three places at once: the A29/A31/A32 tool
directories (where each unit was *measured*), the rootfs builder (which installed
some of them through shell globs), and the initramfs `/init` (which re-enabled
`nuxel-ui.service` into two targets on every boot). Nothing proved that the
repository could reproduce the running system, and two real defects were hiding
in it:

1. **an ordering cycle** — `nuxel-bridge.service` declared
   `Before=nuxel-notifications.service` while `nuxel-notifications.service`
   declared `Before=nuxel-bridge.service`. systemd resolves a cycle by dropping a
   dependency at random, so the notification hub could be started *after* the
   bridge that calls it (`SendNotification` → `org.nuxel.Notifications`).
2. **units that the builder never installed** — the builder installed the
   session units from a `for` loop and the bridge/portal/notification units from a
   glob, so nothing could mechanically prove that the canonical `services/**`
   revisions were the ones that landed in the image.

Both are fixed here. The units now live in exactly one canonical place
(`services/**`), the builder installs and enables them with explicit per-unit
lines, and a validator parses the real unit files *and* the real builder text.

A **third** defect was found in the validator itself while writing the
regression test for it: every `WantedBy=` assertion read the **`[Unit]`**
section, but `WantedBy=` lives in **`[Install]`**. The enablement checks had
therefore never been able to fail (dead code) — a green run proved nothing about
enablement. Fixed (`install_refs()`), and the mutation test now proves the check
fires (`builder installs but does not enable nuxel-web.service`,
`WantedBy=graphical-session.target is a USER target in a SYSTEM unit`). Turning
the check back on immediately surfaced one real, previously invisible finding,
recorded as a **warning** rather than silently passing:

* `nuxel-camera-portal.service` (`shell/nuxel-camera-portal/systemd/`) declares
  `WantedBy=graphical-session.target`, a **user** target, so enabling it in the
  system manager is a no-op. It is a VM-only surface that the handset rootfs
  builder never installs, so it is a recorded `WARN` (with the reason and the
  file's own corrected install instructions) and never a handset boot failure.
  Its unit header now documents the user-manager install it actually needs.

## 2. The installed unit set (14 units)

| Unit | Repository path | ExecStart | Enabled |
|---|---|---|---|
| `seatd.service` | `services/nuxel-session/systemd/seatd.service` | `/usr/bin/seatd -g seat` | yes (launcher images) |
| `nuxel-touch-arm.service` | `services/nuxel-session/systemd/nuxel-touch-arm.service` | `/usr/lib/nuxel/nuxel-touch-arm` | yes |
| `nuxel-wayland.service` | `services/nuxel-session/systemd/nuxel-wayland.service` | `/usr/sbin/phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh` | yes (launcher images) |
| `nuxel-wl-fb.service` | `services/nuxel-session/systemd/nuxel-wl-fb.service` | `/usr/lib/nuxel/nuxel-wl-fb` | yes (launcher images) |
| `nuxel-fallback.service` | `services/nuxel-session/systemd/nuxel-fallback.service` | `/usr/bin/nuxel-ui` (only if the launcher never becomes ready) | yes (launcher images) |
| `nuxel-button-manager.service` | `services/nuxel-session/systemd/nuxel-button-manager.service` | `/usr/lib/nuxel/nuxel-button-manager` | yes (launcher images) |
| `nuxel-animation.service` | `services/nuxel-animation/systemd/nuxel-animation.service` | `/usr/bin/nuxel-anim-player` | yes (always skipped while the bridge exists) |
| `nuxel-notifications.service` | `services/nuxel-notifications/systemd/nuxel-notifications.service` | `/usr/bin/nuxel-notifications` | yes |
| `nuxel-portal.service` | `services/nuxel-portal/systemd/nuxel-portal.service` | `/usr/bin/nuxel-portal` | yes |
| `nuxel-bridge.service` | `services/nuxel-bridge/systemd/nuxel-bridge.service` | `/usr/bin/nuxel-bridge` | yes |
| `nuxel-http-bridge.service` | `services/nuxel-bridge/systemd/nuxel-http-bridge.service` | `/usr/bin/nuxel-http-bridge` | yes |
| `nuxel-web.service` | `services/nuxel-web.service` | `/usr/bin/nuxel-web` | yes |
| `nuxel-firstlight.service` | `images/s10plus/nuxel-firstlight.service` | `/usr/bin/nuxel-fb-phone` | yes (self-skipping diagnostic) |
| `nuxel-camera-portal.service` | `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | `/usr/bin/python3 …/nuxel_camera_portal.py` | VM-only surface, installed by the VM bootstrap |

The builder also installs a drop-in,
`nuxel-ui.service.d/10-launcher-primary.conf`
(`ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb`), so the initramfs'
unconditional `systemctl start nuxel-ui` cannot become a second `/dev/fb0`
owner behind the launcher. `nuxel-ui.service` itself is installed by the
initramfs `/init`, not by the rootfs builder, which is why it appears in the
validator's known-unit set but not in the installed table above.

## 3. Ordering (as declared, and why)

```
systemd-udev-settle.service ─┐
                             ├─> seatd.service ─┐
                             │                  ├─> nuxel-wayland.service ─> nuxel-wl-fb.service ─┐
                             └─> nuxel-touch-arm.service ─┘                     │                  │
                                                                               │                  ├─> nuxel-fallback.service
                                                                               │                  └─> nuxel-button-manager.service
dbus.service ─> nuxel-notifications.service ─> nuxel-bridge.service ─> nuxel-http-bridge.service ─> nuxel-web.service
                          (producer)            (consumer)                 (in-process HTTP front end)
dbus.service ─> nuxel-portal.service ─(session bus)→ org.nuxel.PhoshAgent
nuxel-animation.service: Conflicts=nuxel-wl-fb.service; ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb
```

Three properties are load-bearing:

* **`nuxel-notifications` → `nuxel-bridge`** (fixed in A33). The bridge *calls*
  the hub, so the hub starts first. The cycle is gone; the validator's
  cycle detector now returns nothing.
* **Single framebuffer owner.** `nuxel-wl-fb` is the only writer of `/dev/fb0`
  on a launcher image. `nuxel-animation.service` carries
  `ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb` *and* an `ExecCondition`
  (`services/nuxel-animation/bin/nuxel-animation-claim`) that inspects real
  process state (`nuxel-anim-player` / `nuxel-wl-fb` / `nuxel-ui` /
  `nuxel-fb-phone`) and refuses to run if any of them already owns the panel.
  `nuxel-fallback.service` is the only path that starts the A27 fbdev UI, and it
  does so only when the launcher fails to signal readiness
  (`ExecCondition=/usr/lib/nuxel/nuxel-launcher-ready-wait 60`).
* **Touch before compositor.** `nuxel-touch-arm` must hold the panel open before
  libinput (inside phoc) opens it, so it is `Before=nuxel-wayland.service`.

Restart policy is bounded everywhere (`StartLimitIntervalSec` /
`StartLimitBurst`), so a failing unit cannot become a process storm — a measured
A31 concern (the vendor kernel's `loadavg ~12` is TrustZone/RPMB threads, not a
Nuxel restart loop).

## 4. Linux 4.14 constraints that shape the graph

These are *containment*, not preference. They come from
`tools/s10plus/a26/nuxel-rootfs-fixes.sh`, which the builder runs against the
staging tree so the shipped image needs no live fix. The validator re-checks all
four on every run:

| Constraint | Why | Treatment |
|---|---|---|
| `systemd-userdbd.{service,socket}` | needs pidfd child watching (`pidfd_open(2)` is 5.3; `waitid(P_PIDFD)` is 5.4) → `ENOSYS` on 4.14 | masked; `nsswitch.conf` drops the `systemd` NSS module for passwd/shadow/group/gshadow (otherwise every lookup blocks forever on a varlink call that has no server) |
| `dbus-broker` | `dbus-broker-launch` dies `ENOSYS` in `launcher_fork` | the system bus is `dbus-daemon.service`; `dbus-broker` stays installed but unused (one `systemctl` away) |
| `systemd-udevd` (+3 sockets) | cannot register worker objects → forks unboundedly | masked; `udev_log=err`; devtmpfs supplies every node Nuxel needs. This is *why* `nuxel-wayland.service` preloads the libinput path shim: libinput's udev backend would find zero devices, so the shim redirects only its discovery step to the real `eventN` node carrying `INPUT_PROP_DIRECT` |
| carried `libsystemd-shared` patch | 4.14 has no pidfd spawn path | `boot/s10plus/payload/libsystemd-shared-258.11-1.fc43.so` installs over `/usr/lib64/systemd/`; it is built from `systemd-258.11-1.fc43` (updates), which is why that NEVRA is pinned in `images/s10plus/packages-manifest.json` (see `docs/beta-finalization/system/DEPENDENCY-REPORT.md`) |

The validator **fails** if any unit gains an `After=`/`Wants=`/`Requires=` on
`systemd-userdbd.service`, `systemd-userdbd.socket` or `dbus-broker.service`, and
if the A26 script loses any of its four repairs.

## 5. Enablement: the graph is reproducible from the repository

`systemctl enable` is not used in the image build. The builder creates the
`multi-user.target.wants` symlinks itself, one explicit line per unit, and
`default.target → multi-user.target`. That is deliberate: `/init` on this device
re-enables `nuxel-ui.service` on every boot, and the initramfs post-boot
supervisor restarts it every 30 s, so the shipped enablement must be readable and
diffable rather than emergent.

Re-run the proof:

```sh
python3 tools/s10plus/a33/verify-service-graph.py                       # text verdict
python3 tools/s10plus/a33/verify-service-graph.py --json build/pkgmeta/service-graph.json
python3 tools/s10plus/a33/tests/test-service-graph.py                   # prove the validator can FAIL
bash tools/s10plus/a33/tests/run-userspace-tests.sh                     # all of Priority 4
```

`--root <dir>` validates a copy of the tree instead of the repository. The
regression test uses it to mutate a verbatim fixture and require a `FAILED`
verdict for each defect class (cycle, unsatisfied dependency, forbidden 4.14
dependency, missing enablement, user-target enablement, lost A26 repair) and a
green verdict for the unmutated copy — so a green run means the checks ran, not
that they were unreachable.

The validator checks, in order: reference resolution, forbidden 4.14
dependencies, ordering cycles, system-unit-into-user-target enablement, the A26
repairs, builder install+enable for every canonical unit, and *provenance* — a
canonical unit may not silently lose an `Environment=`/`ExecStart=` line that the
shipped A29/A31/A32 revision carried (the check reports `problems` for a lost
`ExecStart` and `warnings` for a lost `Environment=`).

## 6. Honest limits

* A green validator is `OFFLINE_TESTED`. It proves the *repository* can
  reproduce the graph; it does not prove the handset reaches
  `systemctl is-system-running` → `running`. That is bg-10's measurement.
* `nuxel-firstlight.service` and `nuxel-fallback.service` are enabled but
  self-skipping by condition; "enabled" here means "declared", never "ran".
* `nuxel-wayland`/`nuxel-wl-fb`/`nuxel-button-manager` are enabled only for
  `NUXEL_ENABLE_LAUNCHER=1` images. `NUXEL_ENABLE_LAUNCHER=0` produces the older
  A27 fbdev-UI image, where `nuxel-animation.service` becomes the real animation
  owner — the guards above are what make both images safe.
* No AppArmor profile is declared for any unit: Nuxel has no verified AppArmor
  policy-load path on this vendor kernel, and declaring an unenforced profile
  would be a cosmetic switch that lies about enforcement.
* The single warning is real but out of scope for the handset:
  `nuxel-camera-portal.service` is a VM-only, user-manager surface (see §1). It
  is reported on every run rather than suppressed, because "the VM unit is a
  no-op in the system manager" is information the next reader needs.
