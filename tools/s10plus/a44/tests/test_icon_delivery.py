#!/usr/bin/env python3
"""A44 icon delivery: generated manifest, real PNG decode, HTTP and cache tests.

This test is intentionally stricter than a regex check:
  * the manifest is regenerated from apps.js + index.html and must be current;
  * every URL is fetched over a real loopback HTTP server and must be a 200
    image/png whose bytes and SHA-256 equal the manifest and source file;
  * case mismatches and absent icons must return 404 (negative path);
  * the service worker must never cache 404/error responses and must delete only
    old Nuxel caches, never another app's cache or browser user storage.
"""
from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HOME = ROOT / "pwa/nuxel-home"
REGISTRY = HOME / "icon-registry.json"
GEN = ROOT / "tools/s10plus/a44/generate-icon-registry.js"
SW = HOME / "sw.js"
MANIFEST = HOME / "manifest.json"


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep test output declarative
        pass


def run(cmd, cwd=ROOT):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)


def serve(directory: Path):
    handler = lambda *a, **kw: Quiet(*a, directory=str(directory), **kw)  # noqa: E731
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return srv, "http://127.0.0.1:%d" % srv.server_address[1]


def http_get(url):
    req = urllib.request.Request(url, headers={"Cache-Control": "no-store"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", help="test an already-running phone web server")
    ap.add_argument("--deployed-root", help="also compare these files to the deployed webroot")
    args = ap.parse_args()

    ok = 0

    def check(cond, label, detail=""):
        nonlocal ok
        if not cond:
            print("FAIL", label, detail)
            raise SystemExit(1)
        ok += 1
        print("PASS", label)

    q = run(["node", str(GEN), "--check"])
    check(q.returncode == 0, "generated registry is current", (q.stdout + q.stderr).strip())

    reg = json.loads(REGISTRY.read_text())
    check(reg["schema"] == "nuxel.icon-registry/1", "registry schema")
    check(reg["counts"] == {"app": 12, "navigation": 3, "toggle": 8, "total": 23},
          "active icon counts", json.dumps(reg["counts"]))
    urls = [a["url"] for a in reg["assets"]]
    check(len(urls) == len(set(urls)), "every icon URL is registered exactly once")
    check(all(a["path"].startswith("/assets/") for a in reg["assets"]),
          "all custom artwork uses root /assets URLs")
    check(not any(a["path"].startswith("/pwa/") for a in reg["assets"]),
          "no icon URL is misclassified under /pwa")
    check(all(a["mime"] == "image/png" and a["width"] > 0 and a["height"] > 0
              and a["transparent_pixels"] > 0 and a["opaque_pixels"] > 0
              for a in reg["assets"]), "PNG metadata + real alpha/opaque pixels")

    # Manifest hashes must match the source bytes and the deployed root, when one
    # is supplied.  A source check alone is not a deployment check.
    for a in reg["assets"]:
        data = (ROOT / a["source"]).read_bytes()
        check(len(data) == a["bytes"] and hashlib.sha256(data).hexdigest() == a["sha256"],
              "source hash " + a["id"], a["source"])
        if args.deployed_root:
            dep = Path(args.deployed_root) / a["source"]
            check(dep.is_file(), "deployed file " + a["id"], str(dep))
            check(hashlib.sha256(dep.read_bytes()).hexdigest() == a["sha256"],
                  "deployed hash " + a["id"], str(dep))

    # A real HTTP response table, with MIME and exact bytes.
    if args.base_url:
        base = args.base_url.rstrip("/")
        close = None
    else:
        srv, base = serve(ROOT)
        close = srv.shutdown
    try:
        for a in reg["assets"]:
            status, ctype, body = http_get(base + a["url"])
            check(status == 200, "HTTP 200 " + a["id"], a["url"])
            check(ctype.split(";")[0].strip().lower() == "image/png",
                  "HTTP MIME " + a["id"], ctype)
            check(len(body) == a["bytes"] and hashlib.sha256(body).hexdigest() == a["sha256"],
                  "HTTP bytes/hash " + a["id"], a["url"])
        # Failure paths: a missing asset and the same path with changed case must
        # not be accepted.  The production filesystem is case-sensitive; serving
        # a 200 for the wrong case would hide a bad registry entry on the host.
        status, _, _ = http_get(base + "/assets/nuxel-applications-icon-pack/does-not-exist-a44.png")
        check(status == 404, "missing icon returns 404")
        a0 = reg["assets"][0]
        wrong_case = a0["path"].replace("/assets/", "/ASSETS/")
        status, _, _ = http_get(base + wrong_case)
        check(status == 404, "case-mismatched icon path returns 404", wrong_case)
    finally:
        if close:
            close()

    manifest = json.loads(MANIFEST.read_text())
    sw = SW.read_text()
    cache_version = manifest["nuxel"]["cache_version"]
    check(("const CACHE_VERSION = '" + cache_version + "'") in sw,
          "manifest and service-worker cache version agree", cache_version)
    app_ids = {a['app_id'] for a in reg['assets'] if a['kind'] == 'app'}
    check(set(manifest['nuxel']['apps_in_registry']) == app_ids,
          "manifest apps_in_registry covers every generated app icon")
    check(cache_version != "v27-a44-0.6.3-beta-launcher-fixes", "build cache namespace advanced")
    check("'./icon-registry.json'" in sw, "icon registry is precached")
    check("'./js/icon-health.js'" in sw and (HOME / "js/icon-health.js").is_file(),
          "in-engine WebKit health probe is shipped and precached")
    check('src="js/icon-health.js?v=a44"' in (HOME / "index.html").read_text(),
          "in-engine WebKit health probe is loaded by Home")
    trigger = json.loads((HOME / "icon-health-trigger.json").read_text())
    check(trigger.get("enabled") is False,
          "committed health trigger is disabled (no app launches on a normal boot)")
    health = (HOME / "js/icon-health.js").read_text()
    check("if (!gate) return;" in health and "localStorage.getItem(RUN_KEY) === runId" in health,
          "health probe is trigger-gated and runs once per run_id")
    check("cacheName.startsWith('nuxel-')" in sw,
          "activate only migrates Nuxel-owned caches")
    check(not re.search(r"\b(?:localStorage|sessionStorage|indexedDB|cookieStore)\s*\.", sw),
          "service worker never touches layout/credential stores")
    check("await cache.delete(request)" in sw and "response.status === 404" in sw,
          "404 responses evict the exact stale key")
    check("kind === 'image' && !type.startsWith('image/')" in sw,
          "custom artwork requires an image MIME before caching")
    check("new Response('Nuxel asset unavailable while offline'" in sw,
          "offline miss is an explicit 503, not another app's icon")
    check("networkFirst(event, request, ICON_CACHE, 'image', { cache: 'no-store' })" in sw,
          "custom artwork bypasses WebKit HTTP cache")

    # Duplicate renderers / clipped control invariants.
    apps = (HOME / "js/apps.js").read_text()
    css = (HOME / "css/launcher.css").read_text() + (HOME / "css/status-bar.css").read_text()
    check(apps.count("function nuxelAppIcon(") == 1, "one app-icon renderer")
    check("window.NuxelAppIcon" in apps and "NUXEL_APP_ICON_ASSETS" in apps,
          "launcher uses the shared icon renderer")
    check("nuxel-applications-icon-pack" not in css and "nuxel-quicksettings-icon-pack" not in css,
          "no CSS background duplicate of the raster icon packs")
    check(".qs-item img.qs-icon { object-fit: contain;" in (HOME / "css/status-bar.css").read_text(),
          "Quick Settings artwork is contained, not clipped")
    check(".system-navigation img { display: block; width: 100%; height: 100%; object-fit: contain; }"
          in (HOME / "css/style.css").read_text(), "navigation artwork is contained, not clipped")
    qs = (HOME / "js/qs.js").read_text()
    check(qs.count("_bindIconAssets()") >= 2 and "_iconAssetsBound" in qs,
          "Quick Settings image error binding is idempotent")

    # Negative engineering test: point one generated entry at the app tree and
    # prove the generator rejects it instead of blessing a 404-producing URL.
    with tempfile.TemporaryDirectory(prefix="nuxel-a44-neg-") as td:
        t = Path(td)
        (t / "pwa/nuxel-home/js").mkdir(parents=True)
        (t / "pwa/nuxel-common").mkdir(parents=True)
        shutil.copy2(HOME / "index.html", t / "pwa/nuxel-home/index.html")
        shutil.copy2(HOME / "js/qs.js", t / "pwa/nuxel-home/js/qs.js")
        shutil.copy2(ROOT / "pwa/nuxel-common/app-registry.json", t / "pwa/nuxel-common/app-registry.json")
        shutil.copytree(ROOT / "assets", t / "assets")
        bad = apps.replace("/assets/nuxel-applications-icon-pack/01-08_phone.png?v=a44",
                           "/pwa/assets/nuxel-applications-icon-pack/01-08_phone.png?v=a44")
        (t / "pwa/nuxel-home/js/apps.js").write_text(bad)
        r = run(["node", str(GEN), "--root", str(t), "--check"])
        msg = r.stdout + r.stderr
        check(r.returncode != 0 and "ICON-REGISTRY-FAIL" in msg
              and ("under /assets/" in msg or "icon URL drift for nuxel-dialer" in msg),
              "negative: wrong /pwa icon URL is rejected", msg.strip()[:200])

    print("PASS A44 icon delivery: %d checks" % ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())
