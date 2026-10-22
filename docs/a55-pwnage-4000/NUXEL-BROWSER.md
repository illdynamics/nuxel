# A55 Nuxel Browser — genuine top-level WebKitGTK

## Why the old Browser PWA was insufficient
`pwa/nuxel-apps/browser/` renders pages in an `<iframe sandbox=…>`. Arbitrary
modern sites (google.nl among them) send `X-Frame-Options`/CSP that deny
framing, so a real browser must navigate a **top-level** `WebKitWebView`.

## New implementation (this cycle)
`shell/nuxel-browser-native/`:
- `nuxel_browser_native.py` — native browser with GTK3 + WebKit2GTK-4.1
  (the same stack the working `nuxel-pwa-host` launcher already uses).
- Address bar + Back/Forward/Reload/Go; `example.com` → `https://example.com`;
  non-URL input → DuckDuckGo search.
- TLS errors fail closed (WebKitGTK default; no certificate bypass, no sandbox
  disable).
- Progress evidence to `/run/nuxel-browser.state`.

## Why GTK3/WebKit2-4.1 (evidence, not assumption)
The first port used GTK4 + WebKit-6.0. On this vendor 4.14 kernel the
`WebKitWebProcess` for 6.0 **never spawned** (only its NetworkProcess), so the
load never committed. The device's proven launcher uses GTK3 + WebKit2GTK-4.1,
where both WebProcess and NetworkProcess spawn. The port was switched to that
stack and the load completed.

## Live evidence (device)
```
$ NUXEL_BROWSER_URL=https://example.org … nuxel_browser_native.py
  → /run/nuxel-browser.state = {"status":"finished","uri":"https://example.org/"}
  → WebKitWebProcess + WebKitNetworkProcess (webkit2gtk-4.1) both spawned

$ NUXEL_BROWSER_URL=https://www.google.nl … nuxel_browser_native.py
  → /run/nuxel-browser.state = {"status":"finished","uri":"https://www.google.nl/"}
```
On-device screenshot during the google.nl load: 720×1520 composited frame,
94.4% white pixel fraction + dark text content (Google page), frame FNV64
`a1bd0a4105fd9b8f` (differs from idle Home `8f294059366bb3bb`).

## Gate
- **NUXEL-BROWSER (integration):** PASS_INTEGRATION — real top-level WebKitGTK
  navigation to google.nl and example.org, verified on-device with a spawned
  WebProcess + composited render.
- **NUXEL-BROWSER (physical OSK typing / scroll / back-forward by hand):**
  NOT_TESTED — requires owner hands-on (root console cannot synthesize touch).
