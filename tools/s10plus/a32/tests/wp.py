#!/usr/bin/env python3
"""Wallpaper/asset assertions (mission 8/17): the ONE authoritative asset, at the
path the launcher's CSS actually loads, byte-identical everywhere it is staged."""
import hashlib, os, re, sys
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../../.."))
EXPECT = "6e337ef2d506a16778fd3c79159f0cf053eb07ace40cf43387a33486da76cb29"
paths = ["assets/nuxel-background.png", "pwa/nuxel-home/assets/nuxel-background.png"]
fail = 0
for rel in paths:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print("FAIL missing %s" % rel); fail += 1; continue
    h = hashlib.sha256(open(p, "rb").read()).hexdigest()
    ok = h == EXPECT
    print("%s %s sha256=%s" % ("PASS" if ok else "FAIL", rel, h))
    if not ok: fail += 1
css = open(os.path.join(ROOT, "pwa/nuxel-home/css/style.css")).read()
m = re.search(r"background-image:\s*url\((['\"]?)([^)'\"]+)\1\)", css)
print("%s style.css background-image = %s (resolves under the served pwa tree)"
      % ("PASS" if m and "nuxel-background.png" in m.group(2) else "FAIL", m.group(2) if m else "(none)"))
if not (m and "nuxel-background.png" in m.group(2)): fail += 1
sys.exit(1 if fail else 0)
