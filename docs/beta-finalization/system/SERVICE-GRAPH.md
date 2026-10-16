# SERVICE-GRAPH — the Nuxel S10+ boot graph as actually installed

**Component:** Priority 4 — Full Fedora userspace, services & application infrastructure
**BriQ:** `briq-04b-service-definitions`
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) — Fedora 43
aarch64 userspace, Samsung Linux **4.14.253**, **systemd PID 1**
**Verifier:** `tools/s10plus/a33/verify-service-graph.py` → **`OFFLINE_TESTED`**
(15 system units + 3 user-manager units, 0 problems, 4 recorded warnings, 1
recorded INFO; machine-readable report written to
`build/pkgmeta/service-graph.json`). Revision 2 of
`briq-04b-service-definitions` adds the one service that had NO unit anywhere in
the repository — the **live console** — plus the assertions that keep it
single-owner (`services/nuxel-console/`).
**Console ownership test:** `python3 services/nuxel-console/test-console-ownership.py`
— proves the console's single-owner guard with the real `flock(2)` mechanism.
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

## 2. The installed unit set (15 units)

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
| `nuxel-console.service` | `services/nuxel-console/systemd/nuxel-console.service` | `/usr/bin/nuxel-console /` | **installed, deliberately NOT enabled** (§2.1) |
| `nuxel-camera-portal.service` | `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service` | `/usr/bin/python3 …/nuxel_camera_portal.py` | VM-only surface, installed by the VM bootstrap |

The builder also installs a drop-in,
`nuxel-ui.service.d/10-launcher-primary.conf`
(`ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb`), so the initramfs'
unconditional `systemctl start nuxel-ui` cannot become a second `/dev/fb0`
owner behind the launcher. `nuxel-ui.service` itself is installed by the
initramfs `/init`, not by the rootfs builder, which is why it appears in the
validator's known-unit set but not in the installed table above.

### 2.1 The live console: installed, and deliberately **not** enabled

briq-04b requires every Nuxel service — the live console included — to be a
declared unit with ordering, dependencies, restart policy and jail scoping. The
console was the one exception: its ownership rules lived only in a comment in
`boot/initramfs/init.sh` and in `tools/s10plus/a33/nuxel-console.c`.
`services/nuxel-console/systemd/nuxel-console.service` is that declaration, and
it is **installed without an enablement symlink**, because the console's owner on
this image is not systemd at all:

| Question | Answer | Where it is enforced |
|---|---|---|
| Who owns the console today? | the **initramfs** instance of `/opt/nuxel/nuxel-console`, started before systemd exists (`boot/initramfs/init.sh`), which binds the CDC-ACM gadget, `mknod`s `/dev/ttyGS0`, mirrors `/dev/kmsg` and `chroot`s into the Fedora root | `boot/initramfs/init.sh`; asserted by `services/nuxel-console/test-console-ownership.py` |
| What stops a second owner? | `ConditionPathExists=/usr/bin/nuxel-console` (the rootfs binary is absent on the shipped image ⇒ `ConditionResult=no`), `ExecCondition=/usr/lib/nuxel/nuxel-console-free` (takes the **same** `flock(LOCK_EX\|LOCK_NB)` on `/run/nuxel-console.lock` the console takes; non-zero ⇒ the unit is skipped), and `Restart=no` | the unit file; asserted by both the verifier (§3c) and the test |
| Why not simply enable it? | enabling it would put a second console on the same tty the moment the rootfs binary is added, desynchronising the framed protocol. `verify-service-graph.py` now **fails the build** if a `multi-user.target.wants/nuxel-console.service` line appears in the builder | `PROVISIONED_NOT_ENABLED` in `tools/s10plus/a33/verify-service-graph.py` |
| What is the jail scoping? | `NoNewPrivileges=yes`, `ReadWritePaths=/run`, `ReadOnlyPaths=/usr/bin/nuxel-console /opt/nuxel /usr/lib/nuxel`. `ProtectSystem`/`ProtectKernelTunables`/`PrivateDevices`/`ProtectHome`/`PrivateTmp` are **not** set, and the unit file says why: the console writes configfs (`/sys/kernel/config`) to bind the gadget and needs `/dev/ttyGS0` + `/dev/kmsg` | the unit file (documented, not silently omitted) |
| Ordering | `After=systemd-tmpfiles-setup.service` (the lock lives in `/run`), `Before=nuxel-wayland.service nuxel-wl-fb.service nuxel-fallback.service` — the console is the only channel that can report a compositor failure | asserted by the verifier |

The verifier also cross-checks the **lock protocol across three files**
(`nuxel-console.c` default, the guard's default, the unit's
`NUXEL_CONSOLE_LOCK`) and fails if the C implementation stops using
`/run/nuxel-console.lock`, because a guard that probes a lock nobody takes is a
rubber stamp.

### 2.2 Who owns what: every Priority-4 service → its unit (or its owner)

briq-04b names the services that must exist as units. This is the honest mapping,
including the two entries that are **not** systemd units and say so:

| Service (briq-04b) | Declared as | State |
|---|---|---|
| live console | `nuxel-console.service` + the initramfs instance of `/opt/nuxel/nuxel-console` | unit installed, **not enabled** (§2.1); the initramfs instance is the live owner |
| wl-fb bridge | `nuxel-wl-fb.service` | enabled, single `/dev/fb0` owner |
| animation handoff | `nuxel-animation.service` (+ the initramfs player `/opt/nuxel/nuxel-anim-player`) | enabled and *self-skipping* while the bridge exists; the handoff is receipt-driven in the initramfs/host pair (bg-02) |
| launcher host | `nuxel-web.service` (PWA tree on `127.0.0.1:8000`), `nuxel-wayland.service` (phoc), `nuxel-home-native.service` / `nuxel-home-kiosk.service` (`shell/config/systemd-user/`, user manager), plus the initramfs `nuxel-ui.service` fallback | enabled (launcher images) |
| button manager | `nuxel-button-manager.service` | enabled, owns the physical keys |
| bridge / portal / notifications | `nuxel-bridge.service`, `nuxel-http-bridge.service` (in-process HTTP front end of the same bridge), `nuxel-portal.service`, `nuxel-notifications.service` | enabled, ordered hub-before-consumer (§3) |
| settings daemon pieces | **no settings daemon exists, deliberately** — see §2.3 | — |

### 2.3 There is no settings daemon, and that is a design decision

The mission warns explicitly against "daemon-per-setting sprawl", and the
settings surface is where that sprawl usually starts. Nuxel therefore has **no
`nuxel-settingsd`**, and nothing in the boot graph waits on one:

* the durable store is a **file contract**, not a service: one JSON document per
  setting under `/etc/nuxel/boot/<name>.json`, written atomically (same-directory
  rename) by the launcher host (`pwa/nuxel-home/js/settings-store.js` through
  `NuxelHost.configSet`), with `localStorage` as the documented fallback on
  VM/desktop/plain-browser hosts and merge-on-write so an upgrade cannot clobber
  a key this revision does not know;
* the console path writes the **same** file (`nuxelctl`), so a setting cannot
  have a UI value and a console value that disagree;
* anything privileged — notifications, files, location, camera permission, PTY —
  is mediated by the already-declared narrow services (`nuxel-bridge`,
  `nuxel-portal`, `nuxel-notifications`) that are subject to the capability
  model, never by a settings daemon running as root;
* consequence, stated plainly: a setting the *system* must act on (e.g. verbose
  boot) is consumed by the component that owns the behaviour
  (`pwa/nuxel-home/js/qs.js`, the launcher host, `nuxelctl`), each reading the one
  document. If a future feature genuinely needs a supervisor it gets a named unit
  here with its own ordering and restart policy — not a new daemon per setting.

### 2.4 The user-manager units, and the cross-manager defect they carried

`shell/config/systemd-user/` ships three USER units for the **UTM VM / desktop**
surface (`[vm]` in `configs/init/archived/README.md`): `nuxel-home-kiosk.service`,
`nuxel-home-native.service` (both launcher surfaces) and `nuxel-phosh-agent.service`
(the `org.nuxel.PhoshAgent` session-bus consent agent). The handset rootfs
builder installs **none** of them, because no systemd user session is proven on
this kernel (§6) — and the validator now asserts that:

| Rule | Checked by |
|---|---|
| a USER unit may not reference a SYSTEM unit | validator section 3d (`names a SYSTEM unit from a USER unit`) |
| a USER unit may not be enabled into a SYSTEM target | validator section 3d (`is a SYSTEM target in a USER unit`) |
| the handset builder never installs a user unit | validator section 5 (builder text scan) |
| a VM/desktop development path in `ExecStart` is reported, never assumed | validator warning (`/home/…`, `/usr/local/…`) |

**A real defect was fixed here.** Both launcher units declared
`Wants=nuxel-web.service`. In the *user* manager that name is a user unit that
does not exist, so the dependency was unsatisfiable noise that also implied an
ordering which never happened (and it read as if the user unit could start the
system web service). It is gone from both units in revision 2, replaced by a
documented statement of who actually owns readiness: the kiosk launcher polls
`http://127.0.0.1:8000/pwa/nuxel-home/index.html` before it execs a browser, and
the native launcher's `ExecStartPre=/bin/sleep 8` is explicitly labelled a
**timing** wait (the handset's receipt-driven equivalent belongs to the
Priority 2 handoff work). The mutation test proves the validator now fails if the
dependency ever returns, or if a user unit is enabled into a system target.

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
(initramfs, pre-systemd) /opt/nuxel/nuxel-console ─> nuxel-console.service (skipped: port owned)
                                                   └─ Before=nuxel-wayland.service
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

### 3.1 Native DRM is **not** what runs here (do not read this graph as Phosh)

The graphical path this graph starts is **headless Phoc + a Wayland→framebuffer
bridge**, and it is *not equivalent* to native DRM/KMS-accelerated Phosh:

| | This device (4.14 vendor kernel) | A DRM-capable Fedora phone |
|---|---|---|
| Kernel interfaces | **no `CONFIG_DRM`** in the running kernel: no KMS device, no atomic modesetting, no GBM/EGL-on-DRM | `card0` + `renderD128`, atomic modesetting |
| Compositor backend | `phoc` with `WLR_BACKENDS=headless,libinput` and `WLR_RENDERER=pixman` (software) | `WLR_BACKENDS=drm` with GPU rendering |
| Presentation | `nuxel-wl-fb` copies the composited buffer into the DECON framebuffer (`/dev/fb0`) with the XRGB8888→Samsung ABGR8888 translation | the compositor scans out directly |
| Session/seat | `LIBSEAT_BACKEND=noop` + the libinput path shim (no VT on this device: `/dev/tty0`, `/sys/class/vtconsole` and `/proc/consoles` are absent) | logind/seatd on a real VT |
| Cost | a full-frame copy per presented frame, no vsync fencing, no per-plane composition | zero-copy, tear-free |

`phoc`, `phosh`, `mesa-*` and `libinput` are installed because that is what
Fedora ships and what the shared PWA/Phosh-agent code expects — **not** as a
claim that hardware acceleration, KMS or `phosh.service` as a system session work
on this phone. Native DRM/KMS support is future kernel work (a 4.14 tree with
`CONFIG_DRM` plus the S10+ display driver); until then the framebuffer bridge is
the supported path, it has exactly one owner, and the fallback framebuffer UI
stays as the non-competing recovery surface. Nothing in this document is evidence
of hardware-accelerated rendering on the S10+.

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
dependency, missing enablement, user-target enablement, lost A26 repair, and the
four live-console cases plus the two user-manager cases added in revision 2) and
a green verdict for the unmutated copy — so a green run means the checks ran, not
that they were unreachable.

Installed-but-not-enabled is itself asserted (revision 2): for every unit in
`PROVISIONED_NOT_ENABLED` the validator requires that the builder installs it,
that the builder does **not** create a `multi-user.target.wants` symlink, and
that the unit file states why. The report carries the reason
(`provisioned_not_enabled`) and prints it as an `INFO` line on every run, so the
exception cannot silently become a forgotten enablement (or, worse, a second
console). The one entry today is `nuxel-console.service` (§2.1).

The validator checks, in order: reference resolution, forbidden 4.14
dependencies, the console's single-owner guard (3c), ordering cycles,
system-unit-into-user-target enablement, the A26
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
* Four warnings are recorded on every run rather than suppressed, because each
  one is information the next reader needs: the VM-only camera portal's no-op
  enablement (see §1), and the three user-manager units whose `ExecStart` is a
  VM/desktop development path (`/home/…/nuxel-home-kiosk`,
  `/usr/local/bin/nuxel-home`, `/usr/local/bin/nuxel-phosh-agent` — §2.4). None
  of them is a handset boot-graph failure; all of them would be if the
  corresponding unit were ever installed on the phone.
* The console unit is **`IMPLEMENTED_NOT_DEPLOYED`** as a systemd service: the
  unit, the guard and the builder line are in the repository and offline-tested,
  but the running console is still the initramfs instance. Enabling it on the
  handset would require the console binary in the rootfs *and* stopping the
  initramfs instance first — a live change that has not been made and is not
  claimed here. What IS verified offline is the ownership rule (the guard refuses
  to start beside an existing owner; the builder cannot enable it).
* **`systemctl is-system-running` is not measured on the handset here.** Per-unit
  live state (`systemctl --failed`, `is-active` for each unit in §2) is the
  live-deployment group's capture (bg-10). A unit that is `enabled` in this
  document is *declared*, and may be self-skipping by condition (`nuxel-animation`,
  `nuxel-fallback`, `nuxel-console`).
* **Deferred 4.14 compatibility work, named rather than hidden.** Three
  components remain contained (`masked` / `unused`) instead of fixed:
  `systemd-userdbd` (service+socket), `systemd-udevd` (4 units) and
  `dbus-broker` as the system bus. Unmasking any of them on this kernel requires
  the sd-event child-watch compatibility patch (pidfd-free child watching) to be
  carried the same way the `libsystemd-shared` patch is; until that patch exists
  and is tested, they stay masked and the graph is built not to need them. The
  A26 script is the single place that encodes this, and the validator fails if
  any of its four repairs disappears.
* **No systemd user session is claimed** (§2.4). `shell/config/systemd-user/*`
  units are VM/desktop surfaces with development paths; they are validated under
  user-manager rules and the builder is forbidden from installing them. Direct
  consequence, stated plainly: the portal's **consent dialog depends on
  `org.nuxel.PhoshAgent` on the session bus**, so on the handset in this
  revision a first-time permission request has no dialog surface — the bridge's
  portal call then resolves by the portal's own timeout/deny rule (§
  `APP-INFRASTRUCTURE.md` §4), never by a fabricated grant. That is an open gap
  for the permission-manager work (Priority 5), not a hidden pass.
