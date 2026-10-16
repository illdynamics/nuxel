# Area 2 — Launcher: the Nuxel Home PWA, its registry, its apps and its safe areas

**Status: NEEDS_OWNER_TEST on the handset; `OFFLINE_TESTED` repository side**
(VM parity run is owned by `bg-11-vm-parity`, results in
`docs/beta-finalization/vm/LAUNCHER-PARITY.md`).
Owner action required? **Yes** — only a human can confirm that the launcher *looks* right on
the glass. Nothing here may be auto-promoted to `VERIFIED_ON_S10PLUS` from a script run.

Authoritative launcher: `pwa/nuxel-home/` (index.html, css/, js/, manifest.json, sw.js).
Related briQs: `briq-02d-launcher-parity` (registry, stale assets, cache invalidation),
`briq-02e-safe-zones-statusbar` (ten-zone safe areas, editor polish).
Related docs: `docs/beta-finalization/launcher/SAFE-ZONES.md`.

---

## 1. Feature

The launcher is the existing Nuxel Home PWA — **not** a new launcher — served by
`nuxel-pwa-host` (WebKitGTK on headless Phoc/Wayland, presented through the framebuffer
bridge). The owner-visible claim: the handset shows the **same** launcher as the UTM VM, with
the same app registry, the same status bar and the same ten-zone safe areas.

Four concrete things are being checked:

| # | Claim | Why it matters |
|---|---|---|
| 2.1 | The served launcher bundle is the current one (status bar `0.4.1-a33`, cache namespace `v5-a33`) | The phone’s copy had drifted (`status-bar.js` v0.3.2, stale `manifest.json`): the launcher on the glass was *not* the launcher in the repository |
| 2.2 | The registry contains **Terminal** (`org.nuxel.Terminal`) and a runnable **Settings** app (`nuxel-settings`) | Both existed as metadata/placeholder before; Terminal was missing from the phone’s registry and Settings had no runnable frontend |
| 2.3 | Tapping a tile really opens the app (frame, real content, working Back/close) | “A tile exists” is not “an app launches” |
| 2.4 | The status bar lays every item out **outside** the ten-zone blocked intervals (S10+ portrait: zones 9,10 = the hole-punch cutout) | Items under the cutout are invisible in normal use; the shipped preset must exclude them |

## 2. Why this matters

The launcher is the only UI the phone has: it is the home screen, the app switcher and the
entry point to Settings, Terminal and every application. Parity with the VM matters because
the VM is the reference truth for the launcher and the only place where the PWA can be
exercised without the handset. Cache and version drift matter because a stale service-worker
bundle silently serves an old UI *that looks fine* — the defect only shows up as missing
features (exactly how Terminal went missing on the device copy).

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger mode
   (`tr ' ' '\n' < /proc/cmdline | grep androidboot.mode` must print nothing — see area 1).
2. Root access on the live console (or the on-device Terminal app).
3. The launcher must be the foreground surface. If the boot animation is still on the glass,
   wait for the handoff (area 3) or read the receipt:
   `cat /run/nuxel-anim-handoff` — it must contain `owner=ui`.
4. Record the current bundle before judging it (30 seconds):

   ```sh
   curl -s http://127.0.0.1:8000/pwa/nuxel-home/js/status-bar.js | grep -m1 VERSION
   curl -s http://127.0.0.1:8000/pwa/nuxel-home/manifest.json | python3 -c \
     'import json,sys; print(json.load(sys.stdin)["nuxel"])'
   ```

   Expect `VERSION = "0.4.1-a33"` and `pwa_version 0.4.1-a33`, `cache_version v5-a33`,
   `registry_version 4`.
5. Nothing needs to be installed, flashed or rebooted for this test.

## 4. Exact action

1. **Registry**: on the home screen, confirm the app grid contains **Terminal**, **Settings**,
   Phone, Messages, Contacts, Mail, Calendar, Notes, Files, Camera and Live Console.
2. **Launch:** tap **Terminal**; a real PTY must open inside the launcher frame (a prompt,
   and `id` typed by hand must answer). Tap **Back/close**, the launcher must return to the
   home grid without a reload flash.
3. **Launch:** tap **Settings**; the real Settings UI must render (tabs Display/Sound/Buttons/
   Developer/…), not a blank frame or a placeholder message.
4. **Safe areas:** with the phone in **portrait**, look at the top-right corner of the status
   bar — the region around the hole-punch cutout. The clock, battery, signal and Wi-Fi items
   must all be **clear of the cutout**; no item may be drawn under it, and there must be no
   painted “blocked zone” marker.
5. **Editor:** open **Settings → Display → Safe zones**. The preview strip must move the same
   way the real bar does; block zone **9** and **10** in portrait and press
   *Apply to real status bar (preview)* — the real status bar’s right cluster must move **left**
   (it must not be pushed off the right edge of the panel). Press *Cancel* to restore.
6. **Stale-bundle check (cache invalidation):** reboot normally once (see area 25), and after
   the launcher is up confirm step 1..4 still hold — a stale cached bundle is the failure this
   step is designed to catch.

## 5. Expected result

* App grid identical to the UTM VM, Terminal and Settings both present and both opening real
  content.
* Status-bar items all readable, none under the cutout; the row does not visually shift when a
  notification arrives (the layout pass is idempotent).
* The safe-zone editor’s preview and the real bar agree, including for the shipped S10+
  portrait preset (zones 9,10) and for zones 1,2 (left camera) and 5,6 (centre camera).
* No console/service crash, no double launcher, one status bar.

## 6. Failure symptoms → what they mean

| Symptom | Meaning |
|---|---|
| Terminal tile missing / Settings shows a blank frame | the served bundle is stale or the registry shipped is not `REGISTRY_VERSION 4` |
| App icons and wallpaper have red and blue exchanged | the framebuffer colour conversion was bypassed — **area 3.3**, not a launcher defect |
| Status-bar items sit under the hole-punch or vanish | safe-zone layout did not run (engine absent) or the blocked intervals were ignored |
| The right status cluster is pushed **off the panel** when zones 9,10 are blocked | the A32 one-way push returned (A33 solves against the free intervals) |
| The row drifts right/left a little on every notification | the layout pass measured before resetting the previous transform (non-idempotent) |
| Launcher never appears: static wallpaper or black panel after the animation | the animation→launcher handoff did not complete — **area 3.1/3.2** |

## 7. Diagnostic commands and log paths

```sh
# what the launcher reports about itself (status-bar version, safe-zone engine presence)
grep -i 'status-bar\|safezones' /run/nuxel-home.state            # host diagnostic channel
grep -i SAFEZONES /var/log/nuxel/*.log 2>/dev/null

# the served bundle vs the repository (source of truth)
sha256sum /usr/share/nuxel/pwa/nuxel-home/js/status-bar.js \
          /usr/share/nuxel/pwa/nuxel-home/manifest.json
python3 -c "print(open('pwa/nuxel-home/js/status-bar.js').read().split('VERSION')[1][:40])"

# registry + parity (offline, on the build host)
node tools/s10plus/a33/tests/launcher-registry-test.js
node tools/s10plus/a32/tests/safe-zones-test.js
bash tools/beta/regression-guard.sh          # INV-1 cache invalidation, INV-3 safe zones
```

Logs: `/var/log/nuxel/pwa-host.log` (page load + diagnostics),
`/run/nuxel-home.state` (host state and the `SAFEZONES …` placement line).

## 8. Result

| Check | Result | Evidence |
|---|---|---|
| 2.1 bundle is current (`0.4.1-a33`, `v5-a33`) | ☐ PASS ☐ FAIL | `launcher-registry-test.js`: status-bar `VERSION == manifest.pwa_version`, `CACHE_VERSION == manifest.cache_version` and advanced past `v3-a32` |
| 2.2 registry has Terminal + Settings | ☐ PASS ☐ FAIL | `apps.js` `REGISTRY_VERSION 4` contains `org.nuxel.Terminal` and `nuxel-settings`; test asserts both, plus a runnable Settings frontend (`index.html` + `settings.js`) |
| 2.3 apps launch | ☐ PASS ☐ FAIL | owner observation (no automated substitute for “a human tapped a tile”) |
| 2.4 safe areas on the glass | ☐ PASS ☐ FAIL | `safe-zones-test.js`: 44 assertions, 0 failures (`OFFLINE_TESTED`); on-glass verdict needs the owner |

**Current automatic evidence (build host, 2026-10-16):**
`node tools/s10plus/a33/tests/launcher-registry-test.js` → *launcher registry/parity tests
passed* (1 warning: the Live Console entry is being served by another build group);
`node tools/s10plus/a32/tests/safe-zones-test.js` → *all safe-zone tests passed* (44/44);
`bash tools/beta/regression-guard.sh` → A32 baseline intact (INV-1, INV-3 green).
No on-device evidence exists for this area yet, so the area verdict stays **NEEDS_OWNER_TEST**.
