# nuxel-browser-native

A genuine top-level WebKitGTK browser for the Nuxel S10+ (A55 mission area 7B).

- GTK4 + libadwaita + WebKitGTK 6.0 (`gi.repository.WebKit`), all already present
  on the device (verified live: `WebKit-6.0.typelib`, `Gtk-4.0.typelib`).
- One real `WebKitWebView` per window; navigation is top-level (NOT an iframe),
  so X-Frame-Options/CSP-denying sites such as google.nl load normally.
- TLS errors fail closed (WebKitGTK default); no certificate bypass, no sandbox
  disable.
- URL entry normalises `example.com` → `https://example.com`; non-URL terms fall
  back to a DuckDuckGo search (no tracking).
- Progress evidence written to `/run/nuxel-browser.state`
  (starting/loading/committed/finished/failed) for console-side verification.

## Launch (as the graphical session user)
```
XDG_RUNTIME_DIR=/run/nuxel-wayland WAYLAND_DISPLAY=wayland-0 \
GSK_RENDERER=cairo LIBGL_ALWAYS_SOFTWARE=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 \
NUXEL_BROWSER_URL=https://www.google.nl \
  /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py
```

## Honest limits
- Software rendering only (no /dev/dri on this kernel): expected slow-but-correct
  compositing, no GPU acceleration.
- The OSK integration is the existing Nuxel native keyboard (URL entry is a
  standard GTK Entry, which summons the same OSK focus path used by the launcher).
