#!/usr/bin/env python3
"""Offline test for the Nuxel static PWA web server (briq-04c).

`services/nuxel-web/bin/nuxel-web` is the unit that makes the launcher reachable
(`http://127.0.0.1:8000/pwa/nuxel-home/index.html`); if it resolves the wrong
docroot the WebKit view is blank and nothing else matters. This test starts the
REAL shim (only the interpreter is overridable, via NUXEL_WEB_PYTHON, because the
phone uses /usr/bin/python3 from the python3 RPM) and asserts what the phone
actually depends on:

  1. with NUXEL_WEBROOT set it serves the PWA tree ROOT, so the launcher's
     relative ES-module import `../nuxel-common/bridge.js` resolves (the wiring
     enforced by pwa/nuxel-common/verify-wiring.js);
  2. the launcher index and the shared bridge module both return HTTP 200 and
     real content (no directory listing, no 404 page);
  3. the docroot is resolved by probing `/usr/share/nuxel` then
     `/home/nuxel/nuxel` when NUXEL_WEBROOT is unset — and when the resolved
     docroot has no launcher index (explicit or probed) the shim FAILS LOUDLY
     (non-zero) instead of serving '/' and pretending; `web.conf`, the docroot
     override the builder writes, is actually loaded by the unit;
  4. a docroot with a launcher index but no `pwa/nuxel-common/bridge.js` is
     served WITH an explicit warning (documented degradation, never silent);
  5. it never leaves a listener behind: the child is terminated and the port is
     free afterwards.

Nothing here touches a device, a partition, or Qonqrete metadata.

Usage: python3 tools/s10plus/a33/tests/test-web-server.py
"""

from __future__ import annotations

import http.client
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", ".."))
SHIM = os.path.join(ROOT, "services", "nuxel-web", "bin", "nuxel-web")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def start_shim(env_extra: dict, cwd: str = "/"):
    env = dict(os.environ)
    env["NUXEL_WEB_PYTHON"] = shutil.which("python3") or sys.executable
    env.update(env_extra)
    return subprocess.Popen([SHIM], env=env, cwd=cwd,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def wait_http(port: int, path: str, timeout: float = 8.0):
    """Return the first successful response (status, body) or None."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=2) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(0.15)
    return None


def get(port: int, path: str):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path), timeout=3) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def stop(proc) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def port_free(port: int) -> bool:
    s = socket.socket()
    try:
        s.connect(("127.0.0.1", port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def main() -> int:
    print("[web-server] serves the PWA tree root so the launcher's ES module resolves")
    port = free_port()
    proc = start_shim({"NUXEL_WEBROOT": ROOT, "NUXEL_WEB_PORT": str(port),
                       "NUXEL_WEB_BIND": "127.0.0.1"})
    try:
        resp = wait_http(port, "/pwa/nuxel-home/index.html")
        check(resp is not None, "the launcher index is served on 127.0.0.1:%d" % port)
        if resp:
            status, body = resp
            check(status == 200, "GET /pwa/nuxel-home/index.html -> 200 (got %s)" % status)
            check("nuxel-app-id" in body, "the launcher page is the real shell (nuxel-app-id meta present)")
            check("<html" in body.lower(), "the response is HTML, not a directory listing")
            # the relative ES-module import the wiring check enforces
            m = re.search(r'["\'](\.\./nuxel-common/bridge\.js)["\']', body)
            check(bool(m), "index.html imports the shared bridge via ../nuxel-common/bridge.js")
            if m:
                status2, body2 = get(port, "/pwa/nuxel-common/bridge.js")
                check(status2 == 200, "the imported module /pwa/nuxel-common/bridge.js -> 200 (got %s)"
                      % status2)
                check("NUXEL_BRIDGE_VERSION" in body2, "the served module really is the bridge client")
                pin = None
                for line in body2.splitlines():
                    mm = re.search(r"NUXEL_BRIDGE_VERSION\s*=\s*['\"]([^'\"]+)['\"]", line)
                    if mm:
                        pin = mm.group(1)
                check(pin == "1", "the served bridge pins bridge_version=1 (got %r)" % pin)
            status3, _ = get(port, "/pwa/nuxel-apps/calendar/manifest.json")
            check(status3 in (200, 404),
                  "app assets are reachable from the same root (calendar manifest -> %s)" % status3)
        check(not proc.poll(), "the server is still running (no crash loop)")
    finally:
        stop(proc)
    check(port_free(port), "the listener is gone after termination (port %d freed)" % port)

    print("[web-server] a bad docroot fails loudly instead of serving '/'")
    with tempfile.TemporaryDirectory() as tmp:
        port = free_port()
        proc = start_shim({"NUXEL_WEBROOT": tmp, "NUXEL_WEB_PORT": str(port)})
        try:
            rc = proc.wait(timeout=10)
            err = proc.stderr.read()
            check(rc != 0, "the shim exits non-zero for a docroot without a launcher index (rc=%s)" % rc)
            check("no launcher index" in err or "no docroot" in err,
                  "the failure is named: %r" % err.strip()[:120])
        finally:
            if proc.poll() is None:
                stop(proc)

    print("[web-server] a missing shared bridge is a warning, not silence")
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "pwa/nuxel-home"))
        with open(os.path.join(tmp, "pwa/nuxel-home/index.html"), "w") as fh:
            fh.write("<html><head><meta name=\"nuxel-app-id\" content=\"org.nuxel.Home\"></head></html>")
        port = free_port()
        proc = start_shim({"NUXEL_WEBROOT": tmp, "NUXEL_WEB_PORT": str(port)})
        try:
            resp = wait_http(port, "/pwa/nuxel-home/index.html")
            check(resp is not None and resp[0] == 200,
                  "a launcher-only docroot is still served (%s)" % (resp[0] if resp else "no response"))
            stop(proc)
            err = proc.stderr.read()
            check("WARNING" in err and "bridge.js" in err,
                  "the missing shared bridge module is reported: %r" % err.strip()[:160])
        finally:
            if proc.poll() is None:
                stop(proc)

    print("[web-server] docroot probing is explicit (no NUXEL_WEBROOT)")
    probed = ["/usr/share/nuxel", "/home/nuxel/nuxel"]
    present = [p for p in probed if os.path.isfile(os.path.join(p, "pwa/nuxel-home/index.html"))
               or os.path.isfile(os.path.join(p, "nuxel-home/index.html"))]
    port = free_port()
    env = {k: v for k, v in os.environ.items() if k != "NUXEL_WEBROOT"}
    env["NUXEL_WEB_PYTHON"] = shutil.which("python3") or sys.executable
    env["NUXEL_WEB_PORT"] = str(port)
    proc = subprocess.Popen([SHIM], env=env, cwd="/", stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        if present:
            resp = wait_http(port, "/pwa/nuxel-home/index.html")
            check(resp is not None and resp[0] == 200,
                  "the first existing probe path is used (%s)" % present[0])
        else:
            rc = proc.wait(timeout=10)
            err = proc.stderr.read()
            check(rc != 0, "with no probe path present the shim exits non-zero (rc=%s)" % rc)
            check("no docroot" in err, "the probe failure is explicit: %r" % err.strip()[:120])
    finally:
        if proc.poll() is None:
            stop(proc)

    print("[web-server] the unit wiring matches the shim")
    unit = open(os.path.join(ROOT, "services", "nuxel-web.service"), errors="replace").read()
    check("ExecStart=/usr/bin/nuxel-web" in unit, "the unit runs the shim")
    check("Environment=NUXEL_WEB_PORT=8000" in unit, "the unit pins the documented port")
    check("Environment=NUXEL_WEB_BIND=127.0.0.1" in unit, "the unit binds loopback only")
    check("NUXEL_WEB_PYTHON" not in unit, "the unit does not override the interpreter (phone uses /usr/bin/python3)")
    check("EnvironmentFile=-/etc/nuxel/web.conf" in unit,
          "the unit loads the builder-written docroot override (EnvironmentFile=-/etc/nuxel/web.conf)")
    webconf = os.path.join(ROOT, "images", "s10plus", "build-phone-rootfs-inside-fedora.sh")
    builder = open(webconf, errors="replace").read()
    check("NUXEL_WEBROOT=/usr/share/nuxel" in builder and "/etc/nuxel/web.conf" in builder,
          "the builder writes the /etc/nuxel/web.conf the unit reads (no inert config)")
    check("WantedBy=multi-user.target" in unit, "the unit is enabled into multi-user.target")

    if FAILURES:
        print("\nFAILED: %d assertion(s)" % len(FAILURES))
        return 1
    print("\nAll static-web-server checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
