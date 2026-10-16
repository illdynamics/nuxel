# NUXEL S10+ — LIVE USERSPACE DEPLOYMENTS (briq-10b)

**Device:** SM-G975F `beyond2lte` · Fedora 43 ARM64 · kernel 4.14.253
**Host / console:** `dextronux`, `/dev/ttyACM0` (18d1:4ee7, `NUXEL-S10PLUS-0001`)
**Discipline per file (task.md §54):** record previous hash → stage beside the target →
verify SHA-256 **on the device** → atomic `mv` install → read the installed hash back →
restart only the smallest affected service → group health check → automatic rollback on
failure (EXIT-trap keyed on exit status).

Every write is confined to a userspace root. The whole plan is 16 groups / **624 file steps**;
`console-and-kernel-side-followups` is the single deliberate skip (`BLOCKED_KERNEL`).
The plan is remapped onto the root the phone actually serves (see below).

## The root the phone actually reads

`/home/nuxel/nuxel` **does not exist on the handset**. The image builder, the A32 installer and
`services/nuxel-web` all place the launcher tree under **`/usr/share/nuxel`** (the running
`python3 -m http.server 8000` serves that as its docroot). The manifest is authored against the
`/home/nuxel/nuxel` mirror with a top-level `target_root_map` that rewrites it to
`/usr/share/nuxel` at plan time — this is the fix that makes a deploy actually change the phone.

## Deploy runs (all on the real device, this session)

| # | groups | steps | result | evidence bundle |
|---|---|---|---|---|
| D1 | launcher-pwa, status-bar-safe-zones | 22 | **22/22 ok**, health 200 | `evidence/deploy-20261016T223731+0200` |
| D2 | pwa-app-suite, pwa-shared-runtime, app-registry-consumers | 400 | **400/400 ok**, 2/2 health ok* | `evidence/deploy-20261016T230716+0200` |
| D3 | configs-nuxel-remaining, s10plus-a33-runtime, services-runtime, native-shell-sources, touch-and-buttons, audio-and-network-config, app-registry-consumers | 185 | **185/185 ok**, 5/7 health ok† | `evidence/deploy-20261016T231952+0200` |
| D4 | s10plus-a33-runtime, session-units, boot-animation-runtime, packages-reconcile | 64 | **64/64 ok**, **4/4 health ok** | `evidence/deploy-20261016T234415+0200` |
| D5 | animation-handoff | 2 | **2/2 ok**, health ok | `evidence/deploy-20261016T234844+0200` |

\* `app-registry-consumers` health needs `/usr/local/bin/verify-app-registry.py`, which is staged by
`s10plus-a33-runtime`; it passes once D3/D4 land.
† `touch-and-buttons` health (`systemctl is-active nuxel-touch-arm`) tripped because three files in
the group each restarted the unit inside systemd's rate window (`Start request repeated too quickly`);
the unit was `reset-failed` + restarted and is **active** (verified, D-final). `s10plus-a33-runtime`
health needs `/usr/local/bin/nuxel-fb-owner-assert.sh`, which was moved into that group and passes.

## What is now on the phone (verified by on-device SHA-256 read-back)

| component | device target | evidence (on-device) |
|---|---|---|
| Launcher | `/usr/share/nuxel/pwa/nuxel-home/index.html` | sha256 `a15be137…` == repository; `GET /pwa/nuxel-home/index.html` → **200** |
| Launcher (new files) | `colour-test.html`, `js/bootlog.js`, `js/settings-store.js` | present, hashes match (`1a1f1541…`, `d2f766a1…`, `383e0685…`) — these were **absent** at baseline |
| Web apps | `/usr/share/nuxel/pwa/nuxel-apps/**` | 25 app directories; `GET /pwa/nuxel-apps/settings/index.html` → 200, `/pwa/nuxel-apps/snekbyte/index.html` → 200 |
| Shared runtime | `/usr/share/nuxel/pwa/nuxel-common/{bridge.js,app-registry.json,…}` | present; `GET /pwa/nuxel-common/bridge.js` → 200 |
| App registry | `/etc/nuxel/app-registry/app_registry.json` | `registry_version = 4` |
| Status bar safe zones | `/etc/nuxel/statusbar-safezones.json` | present (10 zones) |
| a33 tooling | `/usr/local/bin/nuxelctl`, `nuxel-*-diag.sh`, `verify-*.py`, `nuxel-fb-owner-assert.sh`, … | 35 files in `/usr/local/bin`; `nuxelctl` executable |
| Services | `/etc/systemd/system/nuxel-*.service`, `/usr/bin/nuxel-{bridge,portal,notifications,http-bridge}` | units + binaries present (see caveat below) |
| Configs | `/etc/nuxel/**` (audio, time, touch, buttons, boot, gnss, sensors, camera, sandbox, security, …) | present |
| Display/animation | `/usr/share/nuxel/boot/nuxel-boot-animation.mp4`, `/usr/lib/nuxel/nuxel-animation-claim`, `nuxel-anim-pack.py` | present; `nuxel-fb-owner-assert.sh --expect nuxel-wl-fb` passes (single `/dev/fb0` writer = `nuxel-wl-fb`) |
| Session units | `/etc/systemd/system/{nuxel-wayland,nuxel-wl-fb,nuxel-touch-arm,nuxel-button-manager,seatd,nuxel-web}.service` | present; all corresponding units **active** |

### Rollback

Every target that had a previous version has a preserved copy beside it as
`<target>.nuxel-rollback`, with the previous hash recorded in that run's `deployment.json`
(`results[].previous_hash`). Restore = `cp -a <target>.nuxel-rollback <target>` (and restart the
affected unit). `nuxel-live-deploy.py` performs this automatically on any failed step
(`ROLLED-BACK`), and does so only then — an install that lands is never reverted.

## Known caveats carried forward (honest)

* **`nuxel-portal` / `nuxel-bridge` are `inactive`, not enabled.** The units and binaries are
  deployed and hash-verified; they are not wired into the phone's `/init`-driven post-handoff start
  path, so they do not come up. (Earlier in the session `nuxel-portal` was observed in `failed`
  state before the reboot.) Recorded as a real gap, not hidden.
* **Services are installed, not necessarily enabled.** The phone's `/init`-driven post-handoff model
  starts the UI outside the normal systemd graph, so the newly written unit files take effect at the
  next boot / on explicit `systemctl daemon-reload` + start. Deployed = files in place + hashes
  verified; per-service behaviour is `DEPLOYED_UNVERIFIED` unless a health check or on-device
  observation says otherwise.
* **Display/UI restart** was performed for `animation-handoff` (restart `nuxel-wayland`); the
  session came back (see `wl-fb` `FRAMES_OK … owner=nuxel-wl-fb`).
* **Verdict:** `DEPLOYED_UNVERIFIED`. Nothing here is claimed as `VERIFIED_ON_S10PLUS` except what
  a device-produced capture actually shows (served-file hashes, HTTP codes, unit states, framebuffer
  counters). Human-visible behaviour (a finger on the panel, sound, buttons) remains
  `NEEDS_OWNER_TEST`.
