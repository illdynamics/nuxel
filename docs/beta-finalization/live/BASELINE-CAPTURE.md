# NUXEL S10+ — LIVE BASELINE CAPTURE (briq-10a)

**Device:** Samsung Galaxy S10+ (SM-G975F, `beyond2lte`, Exynos 9820) — Fedora 43 ARM64, kernel 4.14.253
**Host that captured it:** `dextronux` (Linux 6.17.1-300.fc43.x86_64), console node `/dev/ttyACM0`
**Captured:** 2026-10-16, this session (see bundle timestamps below)
**Method:** the live USB console, every read taken through a SHA-256-verified command frame
(`tools/beta/live/nuxel-live-baseline.py --dev /dev/ttyACM0`). Nothing is inferred.

## Why there are two bundles

The handset arrived booted in **LPM / charger mode** (`androidboot.mode=charger`,
`charging_mode=0x3030`). In that mode `sec_ts` refuses to initialise, so the touchscreen does not
exist at all. A single normal OS reboot (authorised by task.md §53, run through
`tools/beta/live/nuxel-live-reboot-verify.py --reboot`) cleared the condition. Both states were
captured, so the difference is evidence rather than opinion.

| bundle | boot mode | touchscreen | notes |
|---|---|---|---|
| `evidence/baseline-20261016T220528+0200` | `androidboot.mode=charger` | **absent** (`/sys/class/sec/tsp` missing) | pre-reboot; `nuxel-touch-arm.service` **failed** |
| `evidence/baseline-20261016T222451+0200` | *(empty)* — normal boot | **present** (`sec_touchscreen`, `INPUT_PROP_DIRECT`) | post-reboot; all units active, 0 failed |

## Post-reboot baseline (the one that matters)

Bundle: `docs/beta-finalization/live/evidence/baseline-20261016T222451+0200/`
(all 41 frames verified: `framed=True sha_ok=True`)

| fact | value |
|---|---|
| `/proc/cmdline` boot mode | *(no `androidboot.mode=*`)* — normal boot |
| uptime at capture | 255 s |
| kernel | `4.14.253` |
| `systemctl is-system-running` | `running` |
| failed units | **none** |
| `nuxel-wayland` / `nuxel-wl-fb` / `nuxel-button-manager` / `nuxel-touch-arm` / `seatd` | all **active** |
| framebuffer owner | `nuxel-wl-fb` (`/run/nuxel-wl-fb.state`: `FRAMES_OK total=5603 fps_1s=23 failures=0 blit_avg_ms=41 out=720x1520 panel=1440x3040 owner=nuxel-wl-fb display=on`) |
| animation stage | `ANIM_STAGE=ANIMATION_STOPPED` |
| touchscreen | `sec_touchscreen` → `event2` (`B: PROP=2`, i.e. `INPUT_PROP_DIRECT`) and `event3` (`PROP=1`) |
| `/sys/class/sec/tsp` | present (vendor TSP sysfs) |
| `sec_ts` interrupt | present, mapped (`431: ... Level sec_ts`), counter 11 |
| ALSA | card 0 `beyond-madera` present (CS47L93 + 2× CS35L40) |
| launcher HTTP | `200` at `http://127.0.0.1:8000/pwa/nuxel-home/index.html` |
| packages | 410 installed (`rpm -qa`) |

### Device layout (measured, and important)

The phone **serves its launcher tree from `/usr/share/nuxel`**, not `/home/nuxel/nuxel`:

```
/usr/share/nuxel/            docroot of `python3 -m http.server 8000` (cwd)
  nuxel-home/                the launcher (index.html, css/, js/, icons/, assets/)
  pwa/nuxel-home -> ../nuxel-home
  pwa/nuxel-apps/            the web apps (only settings+terminal shipped in the image)
  pwa/nuxel-common/          bridge.js, app-registry.json
  boot/                      animation container
/usr/lib/nuxel/              native runtime (nuxel-wl-fb, nuxel-pwa-host, nuxel-button-manager,
                             libnuxel-libinput-path.so, nuxel-session.sh, nuxel-postboot.sh …)
/etc/nuxel/                  config (device/, display/, input/, phoc-phone.ini, …)
/home/nuxel/nuxel            **does not exist** — it is only the VM/deploy-mirror fallback
```

This is why the previous, repository-only pass could not change the phone: the deploy plan wrote to
`/home/nuxel/nuxel/**`, which nothing on the device reads. The plan now remaps that root onto
`/usr/share/nuxel` (`target_root_map` in `tools/beta/live/deploy-manifest.json`).

## Launcher drift at baseline

Comparing the served bytes against the repository (device hash read through a verified frame):

| file | repo | device | state |
|---|---|---|---|
| `pwa/nuxel-home/index.html` | `a15be137…` | `f7eb859a…` | **differs** |
| `pwa/nuxel-home/js/apps.js` | `df08dfaf…` | `029c9331…` | **differs** |
| `pwa/nuxel-home/js/qs.js` | `2391b568…` | `413b3ec7…` | **differs** |
| `pwa/nuxel-home/js/safe-zones.js` | `0ef0c91a…` | `ca99df1a…` | **differs** |
| `pwa/nuxel-home/js/status-bar.js` | `7a2f02ea…` | `390393db…` | **differs** |
| `pwa/nuxel-home/manifest.json` | `bbb2edfa…` | `bae245b7…` | **differs** |
| `pwa/nuxel-home/sw.js` | `58461b89…` | `816bad13…` | **differs** |
| `pwa/nuxel-home/colour-test.html` | `1a1f1541…` | *(absent)* | **missing on device** |
| `pwa/nuxel-home/js/bootlog.js` | `d2f766a1…` | *(absent)* | **missing on device** |
| `pwa/nuxel-home/js/settings-store.js` | `383e0685…` | *(absent)* | **missing on device** |
| 11 further files (css, js) | — | — | identical |

So the device was running an **older launcher revision** and lacked three files — a real, visible
difference the deploy closes (see `DEPLOYMENTS.md`).

## How to reproduce

```bash
cd /x/nuxel
sudo python3 tools/beta/live/nuxel-live-baseline.py --dev /dev/ttyACM0 --json
# bundle: docs/beta-finalization/live/evidence/baseline-<timestamp>+0200/
```

## Honest limits

* A registered `sec_ts` driver and a mounted `INPUT_PROP_DIRECT` node are **not** proof that a finger
  works end-to-end; that remains `NEEDS_OWNER_TEST` (see the manual checklist).
* The framebuffer counters prove *this* capture's sliver of time, not sustained stability.
* Nothing here was written to the device by the baseline step — it is read-only.
