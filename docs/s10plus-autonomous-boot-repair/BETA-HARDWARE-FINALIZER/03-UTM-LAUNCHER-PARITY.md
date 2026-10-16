# 03 — UTM LAUNCHER PARITY

**Status: implemented, deployed, verified by hash and by HTTP; one real difference
found and fixed (a stale service-worker cache), plus two missing registry entries.**

## What the comparison actually showed

The launcher on the handset was **already the same implementation** as the UTM one:

| File | VM (authority) | S10+ before | Verdict |
|---|---|---|---|
| `index.html` | `595d6ea7…` | `595d6ea7…` | identical |
| `css/*.css` (4 files) | — | — | identical |
| `icons/*` (9 files), `js/apps.js`, `js/launcher.js`, `js/search.js`, `js/qs.js`, `js/recents.js` | — | — | identical |
| `js/app.js` | `8754e9cc…` | `2612bdd0…` | handset/repo version adds the `?boot=os` splash-ownership rule (mission 15) — intended |
| `js/status-bar.js` | `068a0c49…` (v0.2.0) | `6627d8ff…` (**v0.3.2-alpha**) | handset file was stale and matched neither tree → replaced |
| `manifest.json` | `a85f382b…` | `bae245b7…` | stale → replaced |
| registry (`js/apps.js`) | as repo | as repo | identical, but **no Settings frontend and no Terminal at all existed** |

So “the launcher looks different” was **not** a different frontend.  The measured
causes were:

1. **A stale service-worker cache was serving the old page.**  After deploying new
   files the browser requested only `index.html` and `sw.js`
   (`/run/nuxel-web.log`), i.e. `js/*.js` never reached the server: the PWA’s
   cache-first rule for static assets kept the previous revision alive after the
   files on disk had already changed.  Fixed on both sides:
   * `sw.js`: cache namespace bumped (`v3-a32`), code assets (js/css/json/html and
     `/pwa/nuxel-apps/`) are now **network-first** (the launcher’s server is
     127.0.0.1 and always up; images/video stay cache-first);
   * `nuxel-pwa-host`: at startup it removes exactly three persisted subtrees
     (`serviceworkers`, `CacheStorage`, `WebKitCache`) and appends a version stamp
     derived from the served `index.html` (mtime+size) to the launcher URL, so a
     redeployed launcher can never be masked by cached state again.  `localStorage`
     (the settings fallback) is deliberately preserved.  `NUXEL_KEEP_CACHE=1` opts out.
2. **Two registry entries had no runnable frontend**: `nuxel-settings` pointed at the
   native GTK4 placeholder `nuxel-settings://` (which exists in neither tree) and
   there was no Terminal app at all.  Both are now real PWAs under the authoritative
   tree — `/pwa/nuxel-apps/settings/` and `/pwa/nuxel-apps/terminal/` — keeping the
   original registry ids (`nuxel-settings`, new `org.nuxel.Terminal`), names,
   categories and icons for everything else.  This is the same registry the VM
   serves, so both targets run one launcher, not two.

## Verification performed

```
$ grep -a -E "GET /(pwa|js|css)" /run/nuxel-web.log | tail -14
GET /pwa/nuxel-home/index.html            200
GET /pwa/nuxel-home/css/launcher.css      304
GET /pwa/nuxel-home/css/style.css         304
GET /pwa/nuxel-home/js/launcher.js        304
GET /pwa/nuxel-home/js/bridge.js          304
GET /pwa/nuxel-home/js/recents.js         304
GET /pwa/nuxel-home/js/qs.js              304
GET /pwa/nuxel-home/js/search.js          304
GET /pwa/nuxel-home/manifest.json         200
GET /pwa/nuxel-home/icons/icon-192.png    200
GET /pwa/nuxel-home/icons/icon-512.png    200
GET /pwa/nuxel-home/assets/nuxel-boot-animation.mp4 200
GET /pwa/nuxel-apps/settings/index.html   200 text/html
GET /pwa/nuxel-apps/terminal/index.html   200 text/html
```

The launcher page runs from the repo tree, its own app registry is loaded, and the
host reports `NUXEL_HOME_READY uri=…/index.html?boot=os&v=<stamp>` (WebKitGTK 2.52).

`tools/s10plus/a32/tests/launcher-registry-test.js` asserts (offline) that every
registry entry still exists, that all PWA URLs live under `/pwa/nuxel-apps/`, and that
Settings/Terminal are served PWAs rather than placeholders.
