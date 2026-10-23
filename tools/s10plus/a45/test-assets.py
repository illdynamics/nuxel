#!/usr/bin/env python3
"""A45 asset integrity test: the two exact owner-supplied lockscreen assets.
Checks presence, format, dimensions and PNG alpha.  The lockhead must remain the
actual PNG (never a substitute)."""
import os, sys, hashlib
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
WALLPAPER = os.path.join(ROOT, "assets", "nuxel-lockscreen.jpg")
LOCKHEAD = os.path.join(ROOT, "assets", "nuxel-lockhead.png")

fails = 0
def check(name, cond):
    global fails
    print(("PASS " if cond else "FAIL ") + name)
    if not cond: fails += 1

check("wallpaper exists", os.path.isfile(WALLPAPER))
check("lockhead exists", os.path.isfile(LOCKHEAD))

if os.path.isfile(WALLPAPER):
    im = Image.open(WALLPAPER)
    check("wallpaper is JPEG", im.format == "JPEG")
    check("wallpaper is portrait 768x1376", im.size == (768, 1376))

if os.path.isfile(LOCKHEAD):
    im = Image.open(LOCKHEAD)
    check("lockhead is PNG", im.format == "PNG")
    check("lockhead has an alpha channel", im.mode in ("RGBA", "LA"))
    if im.mode in ("RGBA", "LA"):
        a = im.convert("RGBA").getchannel("A")
        lo, hi = a.getextrema()
        check("lockhead has real transparency (alpha min < 255)", lo < 255)
        check("lockhead has opaque artwork (alpha max > 0)", hi > 0)
    check("lockhead is a square canvas", im.size[0] == im.size[1])

# Hash pinning: these are the exact deployed bytes (recorded in the report).
wh = hashlib.sha256(open(WALLPAPER, "rb").read()).hexdigest()
lh = hashlib.sha256(open(LOCKHEAD, "rb").read()).hexdigest()
print("wallpaper sha256:", wh)
print("lockhead  sha256:", lh)
check("wallpaper hash matches deployed", wh == "8939eed2d689500a187e827868363162e27524155f01a6d5d2e2a54cf95604bb")
check("lockhead hash matches deployed", lh == "379266ffe06e881e00b57cb5448662781b8d5ce6a6edd43dda95dff938b0b318")

print(fails == 0 and "ALL PASS" or ("%d FAILURES" % fails))
sys.exit(0 if fails == 0 else 1)
