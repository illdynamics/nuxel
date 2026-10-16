# Service Dependency Graph (measured reality)

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820), Fedora 43
aarch64 userspace on Samsung Linux **4.14.253**, systemd PID 1.
**Canonical unit sources:** `services/**` (plus `images/s10plus/nuxel-firstlight.service`
and the VM-only `shell/nuxel-camera-portal/systemd/nuxel-camera-portal.service`).
**Offline proof:** `python3 tools/s10plus/a33/verify-service-graph.py`
**Full narrative + per-unit table:** `docs/beta-finalization/system/SERVICE-GRAPH.md`

> This page previously described a different device generation (mainline 6.12,
> elogind, iwd, BCM4390 Wi-Fi, OpenRC/pmOS). None of that is true for the S10+.
> It has been rewritten to what the repository and the handset actually run.

## 1. Boot graph as declared

```
                 ┌───────────────────────────┐
                 │ dbus.service (dbus-daemon) │   system bus = dbus-daemon, NOT dbus-broker
                 └──────┬───────────┬─────────┘
                        │           │
        ┌───────────────┘           └────────────────┐
        ▼                                            ▼
 nuxel-notifications.service                  nuxel-portal.service
 (org.nuxel.Notifications)                    (org.nuxel.Portal, user 'nuxel')
        │  producer                                  │ consent, via the SESSION bus
        ▼                                            ▼
 nuxel-bridge.service  ──────> nuxel-http-bridge.service ──────> nuxel-web.service (:8000)
 (org.nuxel.Bridge)             (REST front end, loopback)        (serves the PWA tree)

 systemd-udev-settle.service ─┬─> seatd.service ─────────────┐
                              └─> nuxel-touch-arm.service ───┤
                                                              ▼
                                              nuxel-wayland.service (phoc headless+pixman)
                                                              │
                                                              ▼
                                                    nuxel-wl-fb.service  ← the ONLY /dev/fb0 writer
                                                              │
                                          ┌───────────────────┴────────────────────┐
                                          ▼                                        ▼
                              nuxel-button-manager.service                nuxel-fallback.service
                                                                        (only if the launcher fails)

 nuxel-animation.service: Conflicts=nuxel-wl-fb.service
                          ConditionPathExists=!/usr/lib/nuxel/nuxel-wl-fb
                          ExecCondition=/usr/lib/nuxel/nuxel-animation-claim
 nuxel-firstlight.service: ConditionPathExists=/dev/fb0 (diagnostic; self-skipping)
```

## 2. Startup order (declared, cycle-free)

```
1.  dbus.service                  system bus (dbus-daemon on 4.14; dbus-broker is masked out)
2.  systemd-udev-settle.service   wait for devtmpfs nodes (the udev daemon itself is masked)
3.  seatd.service                 seat broker for the libinput backend
4.  nuxel-touch-arm.service       arms sec_ts and holds the panel open
5.  nuxel-notifications.service   notification hub (producer for the bridge)
6.  nuxel-portal.service          permission portal (system bus → session-bus consent dialog)
7.  nuxel-bridge.service          PWA ↔ native mediator (consumes 5 and 6)
8.  nuxel-http-bridge.service     loopback REST front end
9.  nuxel-web.service             static PWA server on 127.0.0.1:8000
10. nuxel-wayland.service         phoc (headless + pixman) with the libinput path shim
11. nuxel-wl-fb.service           Wayland screencopy → /dev/fb0 (single owner)
12. nuxel-button-manager.service  power / volume / assistant keys
13. nuxel-fallback.service        A27 fbdev UI, only if the launcher never signals ready
14. ModemManager, NetworkManager, pipewire, wireplumber, upower, geoclue2, bluez,
    polkit — external units, started by their own packages; Nuxel references only
    ModemManager.service from nuxel-bridge.service, and the reference is optional (Wants)
```

`nuxel-animation.service` is enabled but **skipped on every launcher image** by its
two guards; it is the animation owner only on `NUXEL_ENABLE_LAUNCHER=0` images.

## 3. Dependency matrix

| Service | Requires / Wants | Provides | Notes |
|---|---|---|---|
| `nuxel-notifications` | dbus | `org.nuxel.Notifications` on the system bus, history at `/var/lib/nuxel/notifications.json` | producer for the bridge |
| `nuxel-portal` | dbus, network.target | `org.nuxel.Portal`, per-app grants under `/var/lib/nuxel/permissions` | runs as user `nuxel` (it needs the session bus) |
| `nuxel-bridge` | dbus, ModemManager (optional), `nuxel-portal`, `nuxel-notifications` | `org.nuxel.Bridge`, capability model | refusal on `bridge_version` mismatch (409 / loud error) |
| `nuxel-http-bridge` | dbus, `nuxel-bridge` | `http://127.0.0.1:8080/api/v1/*` incl. `/apps/registry` | loopback only |
| `nuxel-web` | `nuxel-http-bridge` | the PWA tree on `127.0.0.1:8000` | serves the repository root, so `../nuxel-common/bridge.js` resolves |
| `seatd` | `systemd-udev-settle` | seat broker | `DevicePolicy=strict`, only `char-input`/`char-tty` |
| `nuxel-touch-arm` | `systemd-udev-settle` | open sec_ts device | `Before=nuxel-wayland` |
| `nuxel-wayland` | `nuxel-touch-arm`, `seatd` | Wayland socket in `/run/nuxel-wayland` | `WLR_BACKENDS=headless,libinput`, `LIBSEAT_BACKEND=noop`, LD_PRELOAD path shim |
| `nuxel-wl-fb` | `nuxel-wayland` | `/dev/fb0` | the single display owner |
| `nuxel-button-manager` | `nuxel-wayland`, `nuxel-wl-fb` | key handling for `gpio_keys` | power / volume / assistant |
| `nuxel-animation` | `systemd-udev-settle` | `/dev/fb0` **only** without the bridge | `Conflicts=nuxel-wl-fb` + condition + claim helper |
| `nuxel-firstlight` | — | diagnostic draw | condition-gated on `/dev/fb0` |

## 4. 4.14 containment (A26, applied by the builder to the staging tree)

* `systemd-userdbd.{service,socket}` masked — pidfd child watching is `ENOSYS`.
* `nsswitch.conf` drops the `systemd` NSS module — a varlink lookup with no server blocks forever.
* System bus = `dbus-daemon.service`; `dbus-broker` unused.
* `systemd-udevd` + its sockets masked; devtmpfs supplies the nodes; libinput
  discovery goes through `libnuxel-libinput-path.so`.
* Carried `libsystemd-shared-258.11-1.fc43.so` patch from `systemd-258.11-1.fc43`
  (updates) — the systemd NEVRA is pinned so the running binaries match the patch.

## 5. Verify

```sh
python3 tools/s10plus/a33/verify-service-graph.py
# units=14 problems=0 warnings=1 verdict=OFFLINE_TESTED
#   WARN nuxel-camera-portal.service: WantedBy=graphical-session.target is a
#        USER target in a SYSTEM unit - VM-only surface, never installed on the handset
python3 tools/s10plus/a33/tests/test-service-graph.py
#   proves the validator FAILS on an injected cycle / unsatisfied dep /
#   forbidden 4.14 dep / lost builder enablement / lost A26 repair
python3 tools/s10plus/a33/verify-service-graph.py --root /some/tree   # validate a copy
```

A green run means the repository can reproduce the graph, that no 4.14
forbidden dependency or ordering cycle exists in it, and (since the `[Install]`
`WantedBy=` assertions were repaired in this revision — they had been reading
`[Unit]` and could never fire) that every enabled unit is really enabled by the
builder. It is **not** a claim that `systemctl is-system-running` reaches
`running` on the handset — see
`docs/beta-finalization/system/SERVICE-GRAPH.md` §6.
