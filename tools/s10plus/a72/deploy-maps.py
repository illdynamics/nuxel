#!/usr/bin/env python3
"""Deploy the 21000 Maps PWA update to the running phone via the verified console path."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "beta", "live"))
import nuxel_live as nl

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
files = [
    ("pwa/nuxel-apps/maps/index.html", "/usr/share/nuxel/pwa/nuxel-apps/maps/index.html", "0644"),
    ("pwa/nuxel-apps/maps/js/maps.js", "/usr/share/nuxel/pwa/nuxel-apps/maps/js/maps.js", "0644"),
    ("pwa/nuxel-apps/maps/sw.js", "/usr/share/nuxel/pwa/nuxel-apps/maps/sw.js", "0644"),
]
con, node, notes = nl.open_console(timeout=30.0)
con.open()
try:
    print("# console", node.get("callout"), notes)
    for rel, remote, mode in files:
        local = os.path.join(ROOT, rel)
        data = open(local, "rb").read()
        res = nl.push_bytes(con, data, remote, mode=mode)
        print("# pushed", rel, "->", remote, "sha256", res["decoded_sha256"][:16], "bytes", res["bytes"])
    print("# done")
finally:
    con.close()
