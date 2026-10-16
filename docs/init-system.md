# Nuxel Init System on the S10+ (systemd, Linux 4.14)

**Scope:** this document describes the init/service-manager reality of the
supported phone target — **Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos
9820), Fedora 43 aarch64 userspace on Samsung Linux 4.14.253, systemd PID 1**.
**Related:** `docs/service-graph.md` (graph + dependency matrix),
`docs/beta-finalization/system/SERVICE-GRAPH.md` (per-unit evidence and 4.14
constraints), `docs/s10plus-autonomous-boot-repair/` (how this kernel was made
to boot systemd at all).

## 1. One init system, no split

The S10+ runs **systemd only**. There is no OpenRC path, no elogind, no
`systemd-shim`: `/sbin/init` is the Fedora systemd binary and
`default.target → multi-user.target`.

Earlier revisions of this document described an `NUXEL_INIT` switch between
"systemd (VM)" and "OpenRC (mustang/pmOS)". That split applied to a *different*
device generation that is not a supported target, and it never described the
S10+. It is recorded here only so the stale claim is not silently reused:
**no OpenRC script, and no Alpine/pmOS rootfs, is part of the S10+ boot.**

`shell/config/openrc/*` still exists in the tree as non-applicable history for
that other device. It is not installed by
`images/s10plus/build-phone-rootfs-inside-fedora.sh`, and no S10+ document may
cite it as live.

## 2. What actually starts the phone

```
Samsung bootloader (NO FLASHING is performed by this project)
  └─ BOOT container: Samsung kernel + initramfs (carried 4.14 systemd compatibility patch)
       └─ initramfs /init
            ├─ installs the patched libsystemd-shared-258.11-1.fc43.so over /usr/lib64/systemd/
            ├─ plays the boot animation (nuxel-anim-player) while it owns /dev/fb0
            ├─ enables nuxel-ui.service into sysinit + multi-user targets (initramfs revision)
            ├─ starts the post-boot supervisor (periodic health checks, no blind reboots)
            └─ switch_root → Fedora 43 userspace, systemd PID 1
                 └─ multi-user.target → the Nuxel service set (docs/service-graph.md)
```

The initramfs stage is **not** rebuilt or modified by the rootfs builder; it is
referenced read-only and its compatibility patch is pinned by NEVRA (see
`docs/beta-finalization/system/DEPENDENCY-REPORT.md` §3.1).

## 3. Unit sources and installation

| Class | Repository path | Installed to |
|---|---|---|
| Session / display / input | `services/nuxel-session/systemd/*.service` | `/etc/systemd/system/` |
| Animation phase | `services/nuxel-animation/systemd/nuxel-animation.service` | `/etc/systemd/system/` |
| Bridge / portal / notifications | `services/nuxel-{bridge,portal,notifications}/systemd/*.service` | `/etc/systemd/system/` |
| Static web server | `services/nuxel-web.service` | `/etc/systemd/system/` |
| Diagnostic | `images/s10plus/nuxel-firstlight.service` | `/etc/systemd/system/` |
| VM-only | `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | VM bootstrap only |

Enablement is explicit symlinks into `/etc/systemd/system/multi-user.target.wants/`
created by the builder (never `systemctl enable`), because the initramfs
re-enables `nuxel-ui.service` on every boot and the shipped enablement must be
readable and diffable. See `docs/beta-finalization/system/SERVICE-GRAPH.md` §5.

D-Bus policies are installed from the single canonical directory `configs/dbus/`
into `/etc/dbus-1/system.d/`. The per-service copies under `services/*/dbus/`
are legacy sources; new installs prefer `configs/dbus/`.

## 4. 4.14 compatibility (why the units look unusual)

Linux 4.14 has no `pidfd_open(2)` (5.3) and no `waitid(P_PIDFD)` (5.4). Fedora 43's
systemd 258 uses pidfd child watching for unit execution, so three components can
never run on this kernel:

* `systemd-userdbd.{service,socket}` → masked; the `systemd` NSS module is removed
  from `nsswitch.conf` (a varlink lookup without a server blocks forever);
* `dbus-broker` → `dbus-broker-launch` dies `ENOSYS` in `launcher_fork`; the
  system bus is `dbus-daemon.service`;
* `systemd-udevd` (+ its sockets) → cannot register worker objects and forks
  unboundedly; masked, devtmpfs supplies the nodes, and libinput's device
  discovery is redirected by `libnuxel-libinput-path.so`.

The carried `libsystemd-shared-258.11-1.fc43.so` patch (posix_spawn fallback in
`process-util.c`, PID-only `PidRef` degraded in `pidref.c`) is what lets the
remaining units execute at all. It is bound to the exact `systemd-258.11-1.fc43`
NEVRA from the Fedora `updates` repository — the pin is enforced by
`tools/s10plus/a33/verify-packages.py` and by the builder.

`tools/s10plus/a26/nuxel-rootfs-fixes.sh` applies all four repairs to the staging
tree inside the image build (never on a phone), idempotently, and
`tools/s10plus/a33/verify-service-graph.py` fails if any of them disappears.

## 5. Verification and honest limits

```sh
python3 tools/s10plus/a33/verify-service-graph.py     # OFFLINE_TESTED (repository evidence)
python3 tools/s10plus/a33/verify-packages.py          # package/NEVRA pin evidence
```

* Offline: the graph is cycle-free, every reference resolves, no forbidden 4.14
  dependency exists, and the builder installs + enables exactly the canonical set.
* On-device: `systemctl is-system-running`, `systemctl --failed`,
  `journalctl -b -p err` are **not** claimed here. They are measured by the live
  deployment group and recorded in `docs/beta-finalization/live/` and the manual
  proof checklist.
* Reboots are permitted but must return to Nuxel; a known-working userspace
  rollback path is kept at all times. No blind repeat reboots (three same-mode
  failures ⇒ change the diagnostic strategy).
* No unit declares an AppArmor profile: Nuxel has no verified policy-load path on
  this kernel, and an unenforced profile would be a claim it cannot support.
