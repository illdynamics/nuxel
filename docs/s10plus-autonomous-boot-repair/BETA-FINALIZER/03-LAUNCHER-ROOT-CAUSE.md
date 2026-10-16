# 03 — WHY THE FULL LAUNCHER DID NOT RELIABLY APPEAR (P1)

The A29b conclusion that the S10+ should render `pwa/nuxel-home/` through
WebKitGTK is **correct and was already implemented** — the PWA host, the static
server and the docroot layout were all live this cycle:

```
/run/nuxel-session.log  session start WAYLAND_DISPLAY=wayland-0 layout=/pwa/nuxel-home
                        bridge_ok=yes url=http://127.0.0.1:8000/pwa/nuxel-home/index.html
/run/nuxel-home.state   NUXEL_HOME_MEDIA / NUXEL_HOME_OPEN engine=WebKitGTK/2.52
                        NUXEL_HOME_COMMITTED / NUXEL_HOME_READY   (real page, no 404)
pgrep -c WebKitWebProcess -> 1 (WebKitWebProcess + WebKitNetworkProcess alive)
```

So "is it the A27 fallback?" — **no**:

```
nuxel-ui.service  inactive (ConditionResult=no via 10-launcher-primary.conf), disabled
nuxel-fallback.service  ExecCondition=/usr/lib/nuxel/nuxel-launcher-ready-wait 60
                        exits 1 (skip) while /run/nuxel-launcher-ready exists
```

The launcher *was* the real PWA. What made it "not reliably appear" was that the
panel was being repainted by a **second, unrelated writer** for the entire
session (doc 05/06): the initramfs MP4 player never stopped, so the glass
alternated between animation frames and launcher frames. Everything else
followed from that (and from the missing wallpaper, the missing input path and
the redundant PWA splash overlay).

Fixes applied for P1 in this cycle:

1. the A30 single-owner handoff is now actually **deployed** (doc 06), so the
   launcher owns the panel alone and its frames are not interleaved with the
   animation;
2. the PWA is told the OS owns the boot animation (`?boot=os`), so the redundant
   fullscreen `<video id="boot-splash-video">` is **removed from the DOM** instead
   of sitting above the launcher at `z-index:99999` for up to 12 s (doc 05);
3. the wallpaper the layout expects is really served (doc 04);
4. the compositor owns the real touchscreen, so the launcher is operable (doc 07).

Competing launchers are prevented by construction: `/usr/lib/nuxel/nuxel-wl-fb`
is the only framebuffer owner, `nuxel-ui.service` is condition-skipped while the
bridge exists, and `nuxel-fallback.service` can only run the A27 UI when
`/run/nuxel-launcher-ready` never appears.
