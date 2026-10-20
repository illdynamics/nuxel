# NUXEL REPAIR 04 — icon delivery and WebKit/cache consistency

**Date:** 2026-10-20  
**Phone:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Fedora 43 aarch64, kernel `4.14.253`, live `/dev/ttyACM0` console  
**Branch:** `nuxel/repair04-icon-cache`  
**Source baseline:** `d851713` (v0.6.3-beta)  
**Verdict:** `SOURCE VERIFIED`, `DEPLOYMENT VERIFIED`, `HARDWARE VERIFIED` (instrumented device evidence).
**Owner physical confirmation:** `PENDING` — not claimed.

---

## 1. What was wrong

- App, navigation and toggle icon URLs existed in three different places with no
  generated inventory, so a missing/renamed PNG could not be detected as one set.
- Custom artwork was network-first only for a narrow regex; other PNGs were
  cache-first and could survive a redeploy indefinitely.
- HTML responses were cached without checking `response.ok`, allowing a 404 page
  to become a permanent fallback. A generic offline fallback substituted
  `/icons/icon-192.png` for any missing custom icon, masking the real failure.
- Cache cleanup deleted every cache not in the current list, including caches
  owned by other apps.
- The canonical app registry had no `icon_asset` field, and the Home manifest
  omitted `org.nuxel.Browser` from `apps_in_registry`.
- There was no in-engine, manifest-driven test that opened every icon URL and
  checked Quick Settings reopen, Home reload, app switching and user-data
  preservation.

## 2. Implementation

- Added `pwa/nuxel-home/icon-registry.json`, generated from `apps.js` and
  `index.html` by `tools/s10plus/a44/generate-icon-registry.js`.
  - 12 app icons, 3 navigation icons, 8 raster Quick Settings icons = 23.
  - Every asset is checked for real PNG decode, dimensions, RGBA alpha,
    transparent and near-opaque pixels, bytes and SHA-256.
  - Canonical `app-registry.json` now carries matching `icon_asset` URLs.
- Bumped all active icon URLs and the build cache namespace to `a44` /
  `v28-a44-0.6.3-beta-icon-delivery`.
- Replaced the service-worker fetch policy:
  - code/HTML/artwork: network-first with exact cache fallback;
  - only verified `200` responses of the expected MIME are cached;
  - a real `404` evicts the exact stale key and is not stored;
  - no substitute icon is returned on an offline miss (explicit 503);
  - activation deletes only old `nuxel-*` caches, never unrelated caches;
  - `localStorage`, IndexedDB and credentials are never touched.
- Added idempotent image error binding to Quick Settings and fail-honest labels.
- Added `js/icon-health.js`, a trigger-gated in-engine WebKit probe. It:
  - opens every registered image URL and compares decode dimensions, HTTP
    status, MIME, bytes and SHA-256;
  - checks Home reload, Quick Settings open/close twice, Settings/Browser app
    switching, visible-vs-retained frames, cache keys and localStorage;
  - posts a compact result to the host's existing `nuxelDiag` channel.
- The committed trigger is disabled, so normal boots launch no diagnostics and
  no apps. A unique one-shot trigger was used for the live run.

## 3. Tests

| Test | Result |
|---|---|
| `node tools/s10plus/a44/generate-icon-registry.js --check` | **PASS** — 23 assets |
| `python3 tools/s10plus/a44/tests/test_icon_delivery.py` | **PASS** — 121 checks (real loopback HTTP, MIME, hashes, case/missing negatives) |
| `node tools/s10plus/a44/tests/test_sw_cache.js` | **PASS** — 20 behavioural cache checks |
| `python3 tools/s10plus/a34/tests/test-icon-assets.py` | **PASS** |
| `python3 tools/s10plus/a39/tests/test_a39_assets.py` | **PASS** |
| `python3 tools/s10plus/a33/verify-app-registry.py --quiet` | **PASS** |
| `node --check` on `apps.js`, `qs.js`, `sw.js`, `icon-health.js` | **PASS** |
| `git diff --check` | **PASS** |

Pre-existing test noise, not introduced by A44:

- `tools/s10plus/a33/tests/launcher-registry-test.js` still reports six
  assertions that predate this mission (the current controller deliberately
  retains background app surfaces; the test expects removal). The baseline
  checkout reported these same six plus two additional failures now fixed here
  (`apps_in_registry`, precached wallpaper in a clean worktree).
- `tools/verify-pwa-assets.sh` stops before checking because
  `tools/dedupe-assets.sh` is not executable in this checkout.

## 4. Deployment

Live webroot: `/usr/share/nuxel` (HTTP server PID cwd), physical launcher tree
`/usr/share/nuxel/nuxel-home`.

Deployed revision files and SHA-256:

| Source | Deployed path | SHA-256 |
|---|---|---|
| `pwa/nuxel-home/index.html` | `/usr/share/nuxel/nuxel-home/index.html` | `0ce30b6980f620e67562316b9f4e365373d687992fc344e7897eb79e8bed8fd5` |
| `pwa/nuxel-home/manifest.json` | `/usr/share/nuxel/nuxel-home/manifest.json` | `71b8441b003cf67ee5211ac18df4c4235014c4a7e33fa0a312f0a2ca07b71812` |
| `pwa/nuxel-home/sw.js` | `/usr/share/nuxel/nuxel-home/sw.js` | `aac1ee86e1dc60b10452f15ef0a2a68853abb66422b6eb6083bf3134610833c6` |
| `pwa/nuxel-home/icon-registry.json` | `/usr/share/nuxel/nuxel-home/icon-registry.json` | `90e524174d1d0b9baab9ad9309d9242f7c8ff14bda26c438141b69f8201082a3` |
| `pwa/nuxel-home/js/apps.js` | `/usr/share/nuxel/nuxel-home/js/apps.js` | `de57357e8630b5b962612c61d8fdd2b4d81fe3728d1c222782f97711c5196531` |
| `pwa/nuxel-home/js/qs.js` | `/usr/share/nuxel/nuxel-home/js/qs.js` | `35538b976a038c6ea92c89351b3a5b3ef68796a3ad217955a6dd59b8910655b1` |
| `pwa/nuxel-home/js/icon-health.js` | `/usr/share/nuxel/nuxel-home/js/icon-health.js` | `e5d927084a7fb0f6838f50873fe5303a8ef0d99215c4ff6e351d626988c9985b` |
| `pwa/nuxel-home/icon-health-trigger.json` | `/usr/share/nuxel/nuxel-home/icon-health-trigger.json` | `ca68bd90f1f76e52b651374bc4c79d2294212d112c567c7f68ec69a31b2b0adc` |
| `pwa/nuxel-common/app-registry.json` | `/usr/share/nuxel/pwa/nuxel-common/app-registry.json` | `707fcdb8a52836e8f66c27056e932c1289b6c13d9796fb43c2fdbd8bec3a1581` |

All nine deployed hashes equal the repository sources. Deployment used
same-directory rename, per-file staged SHA verification and per-file readback.
No partition, kernel, bootloader, modem, firmware or reboot operation was
performed. `nuxel-wayland` was restarted once after the old host exhausted its
bounded web-process reload budget; the USB console and userspace remained live.

## 5. URL / MIME / hash evidence

`http-icons-final.json` and `url-status-mime.tsv` contain all 23 rows.

| Kind | Count | HTTP | MIME | Source == deployed == HTTP hash |
|---|---:|---:|---|---|
| app | 12 | 200 | `image/png` | PASS |
| navigation | 3 | 200 | `image/png` | PASS |
| toggle | 8 | 200 | `image/png` | PASS |
| missing probe | 1 | 404 | — | PASS (not served) |
| wrong-case probe | 1 | 404 | — | PASS (not served) |

## 6. In-engine WebKit and cache evidence

Final probe: `in-engine-health-a44-3.json`, version `a44-3`, `ok: true`.

| Check | Result |
|---|---|
| 23 manifest URLs opened in WebKit | PASS — all decoded at expected dimensions |
| HTTP status/MIME/bytes/SHA | PASS — all 200 `image/png`, hashes equal manifest |
| Home DOM after reload | PASS — 23 images, 23 unique URLs, zero duplicates |
| Navigation images | PASS — 3/3 loaded and `has-image` set |
| App grid images | PASS — 12/12 loaded |
| Quick Settings reopen | PASS — two cycles, 8/8 loaded, 8 unique URLs, no failures, one verbose tile |
| App switching | PASS — one visible frame/bar at a time; Home steps have zero visible frames; retained background surfaces are hidden, not duplicate paint |
| Cache names | `nuxel-static-v28-a44-0.6.3-beta-icon-delivery`, `nuxel-dynamic-v28-…`, `nuxel-icons-v28-…`; no old v≤27 namespace |
| Service worker | active/activated at `/pwa/nuxel-home/sw.js` |
| User storage | temporary probe survived; all pre-existing localStorage keys remained; layout/appearance values were not read or logged |

Screenshot spot check: `home.png` / `home.ppm.gz`, 720×1520, captured from the
compositor after the probe returned Home. SHA-256 of the PNG is recorded by the
file itself and compressed source is verified against the device hash. This is
machine evidence only; the owner must still confirm the visible result.

## 7. Rollback

Fresh final backup (created from the known-good pre-deploy baseline):

```sh
sh /var/backups/nuxel/a44-icon-delivery-20261020T145655Z/rollback.sh
```

The rollback restores the six pre-existing files and removes the three new files
(`icon-registry.json`, `icon-health.js`, `icon-health-trigger.json`). A rollback
to the same baseline was executed and verified before the final clean deploy:
restored hashes matched baseline, new files were absent, Home returned HTTP 200
and the new registry returned 404. The UI was then redeployed and verified again.

`nuxel-wayland` may be restarted only if the old host's bounded web-process
reload budget is exhausted:

```sh
systemctl restart nuxel-wayland
```

## 8. Open acceptance item

**OWNER CONFIRMED — PENDING.** The owner must visually confirm Home/dock,
Quick Settings reopen and Settings/Browser icon rendering on the glass. A source
pass, HTTP 200, image decode or synthetic touch is not a physical PASS.
