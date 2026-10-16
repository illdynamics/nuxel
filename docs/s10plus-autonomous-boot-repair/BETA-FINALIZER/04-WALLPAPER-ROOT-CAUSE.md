# 04 — WALLPAPER ROOT CAUSE AND FIX (P2)

## The bug, exactly

`pwa/nuxel-home/css/style.css:60`

```css
html, body { … background-image: url('../assets/nuxel-background.png'); … }
```

relative to `css/` that resolves to

```
pwa/nuxel-home/assets/nuxel-background.png
```

On the handset that path returned **404**:

```
$ curl -o /dev/null -w '%{http_code} %{content_type}' \
    http://127.0.0.1:8000/pwa/nuxel-home/assets/nuxel-background.png
404 text/html;charset=utf-8
$ find /usr/share/nuxel/pwa/nuxel-home/assets
…/nuxel-boot-animation.mp4        <-- the PNG was simply not there
```

Why it was missing on the device while it exists in the repository:
`.gitignore:119` ignores `pwa/**/assets/nuxel-background.png` (the wallpaper is
single-sourced in `assets/` and copied into each PWA **at build time** by
`tools/dedupe-assets.sh`, which the phone-rootfs builder never ran), and
`images/s10plus/build-phone-rootfs-inside-fedora.sh:47` installs it only to
`/usr/share/nuxel/nuxel-background.png` — never to the PWA's own `assets/`.

## The fix chosen (maintainable, no artwork altered)

Stage the authoritative asset at the path the stylesheet actually uses, using the
deployment asset that is **already on the device** — the authoritative wallpaper
was present all along at `/usr/share/nuxel/nuxel-background.png`:

```
sha256sum /usr/share/nuxel/nuxel-background.png
  6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
install -m 0644 /usr/share/nuxel/nuxel-background.png \
                 /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
sha256sum /usr/share/nuxel/pwa/nuxel-home/assets/nuxel-background.png
  6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29
curl -o /dev/null -w '%{http_code} %{content_type} %{size_download}' \
     http://127.0.0.1:8000/pwa/nuxel-home/assets/nuxel-background.png
  200 image/png 1257938
```

No second background was created, the artwork was not modified (byte-identical
hash), and no CSS design change was made.

## Cache / version migration (mission §7)

`pwa/nuxel-home/sw.js` serves static assets **cache-first**, so a redeployed
launcher could be served stale. That was fixed with a controlled migration rather
than by deleting browser state:

* `CACHE_VERSION` (`v2`) → `CACHE_NAME`/`STATIC_CACHE`/`DYNAMIC_CACHE` namespaced;
  `activate` already deletes non-current caches, so one page load swaps them;
* `./assets/nuxel-background.png` added to `PRECACHE_ASSETS` so the wallpaper is
  part of the installed app shell;
* launch mode `?boot=os` (doc 05) means the *new* document always re-evaluates the
  splash policy.

## Browser-level verification (no screenshots)

The A31 PWA host injects a read-only observer into the real launcher document
(doc 07). It reports the **computed** `background-image` and whether the browser
actually decoded the bytes:

```
NUXEL_INPUT EVT diag-ready x=-1 y=-1 tag=- id= w=360 h=760 dpr=2 splash=absent
NUXEL_INPUT EVT wallpaper url=http://127.0.0.1:8000/pwa/nuxel-home/assets/nuxel-background.png decoded=1 natural=941x1672 x=-1 y=-1 tag=BODY id= w=360 h=760 dpr=2 splash=absent
NUXEL_INPUT EVT splash-t1s absent pointer-events=n/a z-index=n/a … splash=absent
NUXEL_INPUT EVT splash-t4s absent … splash=absent
NUXEL_INPUT EVT splash-t9s absent … splash=absent
```

`decoded=1 natural=941x1672` is libweb's own decode result for exactly the URL
the *computed* CSS resolves to; the viewport is 360x760 CSS px at dpr 2, i.e. the
720x1520 output at scale 2, and the overlay is absent at load and at +1/+4/+9 s.

That covers the mission's acceptance list items 1–8: source hash, deployed hash,
HTTP 200, correct MIME type, correct dimensions, successful browser decode, the
computed CSS background-image referencing the intended URL, and the splash
overlay absent from the document so the wallpaper really is what the UI sits on.
The probe resolves the *computed* `background-image` of `document.body`, creates
an `Image` for that exact URL and reports `naturalWidth`/`naturalHeight` (or the
error) — i.e. it is libweb's own decode result, not an inference from a file
being present.

## Repository fix (so a fresh image ships it)

`images/s10plus/build-phone-rootfs-inside-fedora.sh` now installs the canonical
wallpaper into the PWA's own `assets/` directory as part of the PWA staging step
(and still keeps `/usr/share/nuxel/nuxel-background.png` for legacy consumers).
The staging step also runs `tools/dedupe-assets.sh` semantics explicitly instead
of relying on the git-ignored per-app copies being present in the build context.
