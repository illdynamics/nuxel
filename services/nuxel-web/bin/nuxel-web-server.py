#!/usr/bin/env python3
"""nuxel-web-server — the Nuxel static server for the PWA tree (briq-04c rev 2).

WHY THIS EXISTS
    The launcher, every Nuxel PWA and the shared bridge client are served from one
    docroot on 127.0.0.1:8000. Until this revision that docroot was served by
    `python3 -m http.server`, which is a *development* file server: it lists
    directories, sends no `Cache-Control` at all (so the browser invents its own
    policy per file), sends no `Service-Worker-Allowed` and no ETag, and serves a
    single request at a time.

    On a phone that costs real, measured defects:
      * a stale `sw.js` or `index.html` survives an update because nothing told
        the browser to revalidate — the launcher then runs old JavaScript against
        new assets (the "stale service worker" class the mission calls out);
      * a service worker that wants a wider scope than its own directory cannot
        get one without `Service-Worker-Allowed`;
      * WebKit opens several connections per page and a single-threaded server
        serialises them behind one slow request (the launcher waits);
      * directory listings expose the whole staged tree to any local process.

WHAT IT DOES (stdlib only - no new packages on the phone)
    1. one docroot, resolved by the shim and passed in NUXEL_WEBROOT; every path
       is resolved and must stay under the docroot (no `..`, no symlink escape);
    2. an explicit MIME table (including `.webmanifest`, `.mjs`, `.wasm`, `.mp4`,
       fonts) plus `X-Content-Type-Options: nosniff` so WebKit never guesses;
    3. `ETag` + `Last-Modified` on every 200, `304 Not Modified` for a matching
       `If-None-Match`/`If-Modified-Since` - the validator the CI smoke test
       looks for;
    4. the CACHE POLICY the PWA actually needs:
         * service workers  -> `Cache-Control: no-cache` + `Service-Worker-Allowed: /`
                               (an updated sw must be revalidated, and the sw may
                                claim the root scope it was registered for);
         * HTML + manifests -> `no-cache` (update checks must not be masked);
         * `?v=`/`?h=`/`?hash=`-suffixed assets -> immutable, one year
                               (content-addressed: the URL changes with content);
         * everything else  -> `max-age=3600` (bounded staleness);
         * NUXEL_WEB_NO_CACHE=1 -> `no-store` everywhere (the owner's
                               stale-asset troubleshooting switch);
    5. `X-Nuxel-Asset-Revision: <sha256-8>` on served files, so "which bytes did
       the launcher get" is answerable from one HTTP response;
    6. no directory listings (403), no traversal, threaded serving, and only
       non-200 responses logged (the journal must not become a request log).

NOT CLAIMED: this is a loopback static file server. It is not a sandbox, it does
not authenticate, and it must never be bound to a routable address (the unit
pins 127.0.0.1).
"""

from __future__ import annotations

import hashlib
import mimetypes
import os
import posixpath
import sys
import threading
from email.utils import formatdate, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit, parse_qs

VERSION = "nuxel-web-server/1 (briq-04c rev 2)"

# Explicit MIME policy. mimetypes.guess_type() already knows most of these on
# Fedora 43 / Python 3.11+ (checked: .webmanifest -> application/manifest+json),
# but the PWA tree depends on these exact types, so they are pinned here rather
# than inherited from a changing stdlib table.
MIME = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".ico": "image/vnd.microsoft.icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".otf": "font/otf",
    ".wasm": "application/wasm",
    ".mp4": "video/mp4",
    ".m4v": "video/mp4",
    ".webm": "video/webm",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".oga": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".pdf": "application/pdf",
    ".vtt": "text/vtt; charset=utf-8",
    ".map": "application/json; charset=utf-8",
}

# Query parameters that mean "this URL is content-addressed": the URL changes
# when the bytes change, so it may be cached hard. Anything else is revalidated.
IMMUTABLE_QUERY_KEYS = ("v", "h", "hash", "ver", "version", "rev")

MAX_AGE_DEFAULT = 3600
MAX_AGE_IMMUTABLE = 31536000

_etag_cache: dict = {}
_etag_lock = threading.Lock()


def log(msg: str) -> None:
    sys.stderr.write("[nuxel-web] %s\n" % msg)
    sys.stderr.flush()


def content_type(path: str) -> str:
    # A web app manifest is not "some JSON": WebKit/Chrome use the type to decide
    # whether to treat the document as an installable manifest, and every PWA in
    # this tree ships its manifest as `manifest.json`. Both the extension and the
    # name are checked so a manifest served from any directory is typed right.
    base = os.path.basename(path).lower()
    if base == "manifest.json" or base.endswith(".webmanifest"):
        return "application/manifest+json; charset=utf-8"
    ext = os.path.splitext(path)[1].lower()
    if ext in MIME:
        return MIME[ext]
    guessed, _encoding = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def is_service_worker(path: str) -> bool:
    """A service worker script is any *.js/*.mjs named sw/service-worker*."""
    base = os.path.basename(path).lower()
    return base in ("sw.js", "sw.mjs", "service-worker.js", "service-worker.mjs") \
        or base.startswith("sw-") and base.endswith(".js")


def asset_etag(path: str) -> str:
    """sha256[:16] of the file, memoised on (path, mtime_ns, size)."""
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size)
    with _etag_lock:
        cached = _etag_cache.get(path)
        if cached and cached[0] == key:
            return cached[1]
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(256 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()[:16]
    with _etag_lock:
        _etag_cache[path] = (key, digest)
    return digest


class NuxelWebHandler(BaseHTTPRequestHandler):
    server_version = VERSION
    protocol_version = "HTTP/1.1"
    docroot = "/"
    no_cache = False

    # -- helpers ------------------------------------------------------------
    def _resolve(self, raw_path: str):
        """Map a URL path to a real file under the docroot. None if invalid."""
        path = unquote(urlsplit(raw_path).path)
        path = posixpath.normpath(path)
        if path in ("/", ""):
            return None                      # never serve the docroot listing
        parts = [p for p in path.split("/") if p not in ("", ".")]
        if any(p == ".." for p in parts):
            return None
        fs_path = os.path.join(self.docroot, *parts)
        real = os.path.realpath(fs_path)
        root = os.path.realpath(self.docroot)
        if real != root and not real.startswith(root + os.sep):
            return None                      # symlink escape
        if not os.path.isfile(real):
            return None
        return real

    def _cache_control(self, real_path: str, query: str) -> str:
        if self.no_cache:
            return "no-store"
        if is_service_worker(real_path):
            # A service worker update MUST be seen: no-cache = store but always
            # revalidate, so an unchanged sw costs one 304 and a changed one is
            # picked up on the next navigation (this is the stale-sw fix).
            return "no-cache"
        ext = os.path.splitext(real_path)[1].lower()
        if ext in (".html", ".htm", ".webmanifest") or os.path.basename(real_path) == "manifest.json":
            return "no-cache"
        params = parse_qs(query)
        if any(k in params for k in IMMUTABLE_QUERY_KEYS):
            return "public, max-age=%d, immutable" % MAX_AGE_IMMUTABLE
        return "public, max-age=%d" % MAX_AGE_DEFAULT

    def _send_common_headers(self, real_path: str, etag: str, last_modified: float,
                             cache_control: str, status: int = 200) -> None:
        self.send_header("Content-Type", content_type(real_path))
        self.send_header("Cache-Control", cache_control)
        self.send_header("ETag", '"%s"' % etag)
        self.send_header("Last-Modified", formatdate(last_modified, usegmt=True))
        self.send_header("X-Nuxel-Asset-Revision", etag)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if is_service_worker(real_path):
            # The launcher registers /pwa/nuxel-home/sw.js; allowing the root
            # scope is what lets a service worker control the whole tree. The
            # header is harmless when the registration scope is narrower.
            self.send_header("Service-Worker-Allowed", "/")
            self.send_header("X-Nuxel-Service-Worker", "1")
        if status == 200:
            self.send_header("Content-Length", str(os.path.getsize(real_path)))

    def _not_modified(self, etag: str, last_modified: float) -> bool:
        inm = self.headers.get("If-None-Match")
        if inm:
            tags = [t.strip().lstrip("W/") for t in inm.split(",")]
            if ('"%s"' % etag) in tags or "*" in tags:
                return True
        ims = self.headers.get("If-Modified-Since")
        if ims:
            try:
                since = parsedate_to_datetime(ims).timestamp()
                if int(last_modified) <= int(since):
                    return True
            except (TypeError, ValueError):
                pass
        return False

    def _serve(self, head_only: bool = False) -> None:
        query = urlsplit(self.path).query
        real = self._resolve(self.path)
        if real is None:
            # Distinguish "no listing" from "no such file" in the status, but
            # never reveal the filesystem layout.
            self.send_response(403 if urlsplit(self.path).path.endswith("/") else 404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            body = b"nuxel-web: not served (no directory listings)\n" \
                if urlsplit(self.path).path.endswith("/") else b"nuxel-web: not found\n"
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if not head_only:
                self.wfile.write(body)
            log("%s %s -> %d" % (self.command, self.path, 403 if urlsplit(self.path).path.endswith("/") else 404))
            return

        try:
            etag = asset_etag(real)
            st = os.stat(real)
        except OSError as exc:
            log("%s %s -> 500 (%s)" % (self.command, self.path, exc))
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        cache_control = self._cache_control(real, query)
        if self._not_modified(etag, st.st_mtime):
            self.send_response(304)
            self._send_common_headers(real, etag, st.st_mtime, cache_control, status=304)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Accept-Ranges", "none")
        self._send_common_headers(real, etag, st.st_mtime, cache_control)
        self.end_headers()
        if head_only:
            return
        try:
            with open(real, "rb") as fh:
                while True:
                    chunk = fh.read(256 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            # A WebKit subresource abort is normal (navigation away); it is not
            # an error worth a journal line.
            pass

    # -- HTTP verbs ---------------------------------------------------------
    def do_GET(self):  # noqa: N802 (BaseHTTPRequestHandler API)
        self._serve(head_only=False)

    def do_HEAD(self):  # noqa: N802
        self._serve(head_only=True)

    def log_message(self, fmt, *args):  # noqa: A003
        # Suppress the default per-request stderr line: the shim's unit does not
        # want a journal entry per asset. Non-200 responses are logged by _serve.
        return


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    docroot = os.environ.get("NUXEL_WEBROOT") or ""
    port = int(os.environ.get("NUXEL_WEB_PORT", "8000"))
    bind = os.environ.get("NUXEL_WEB_BIND", "127.0.0.1")
    no_cache = os.environ.get("NUXEL_WEB_NO_CACHE", "") not in ("", "0", "no", "false")
    i = 0
    while i < len(argv):
        if argv[i] == "--root" and i + 1 < len(argv):
            docroot = argv[i + 1]
        elif argv[i] == "--port" and i + 1 < len(argv):
            port = int(argv[i + 1])
        elif argv[i] == "--bind" and i + 1 < len(argv):
            bind = argv[i + 1]
        elif argv[i] == "--no-cache":
            no_cache = True
        i += 1
    if not docroot or not os.path.isdir(docroot):
        log("ERROR: docroot %r is not a directory (set NUXEL_WEBROOT)" % docroot)
        return 2
    if not os.path.isfile(os.path.join(docroot, "pwa", "nuxel-home", "index.html")) and \
       not os.path.isfile(os.path.join(docroot, "nuxel-home", "index.html")):
        log("ERROR: %s contains no launcher index.html (expected pwa/nuxel-home/index.html)" % docroot)
        return 2
    NuxelWebHandler.docroot = docroot
    NuxelWebHandler.no_cache = no_cache
    httpd = ThreadingHTTPServer((bind, port), NuxelWebHandler)
    httpd.daemon_threads = True
    log("%s serving %s on %s:%d (cache=%s, threaded, ETag+Last-Modified, "
        "Service-Worker-Allowed for sw scripts)"
        % (VERSION, docroot, bind, port, "no-store (NUXEL_WEB_NO_CACHE)" if no_cache else "policy"))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
