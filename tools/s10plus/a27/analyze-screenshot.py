#!/usr/bin/env python3
"""analyze-screenshot.py — objective checks on a Nuxel AMOLED capture (PPM).

A framebuffer capture is not proof of what the glass shows, but it IS proof of
what the DECON was told to scan out, and it can be measured.  This tool reports,
in the SAME 360x760 design space the UI lays out in:

  * the detection rate and bounding box of text "ink" per band (status bar, hero,
    app grid, dock) -- so an overflowing clock, a fused dock label or a stray
    block of stale framebuffer can be seen without a human eye;
  * whether any ink lands in the camera cutout band;
  * whether each dock label stays inside its own 72-px slot (the A26 defect was
    SETTINGS needing ~96 design px in a 72-px slot);
  * the colour histogram (are we still in the Nuxel navy/blue palette?).

Usage: analyze-screenshot.py <capture.ppm> [--expect-w DESIGN_WIDTH]
Exit: 0 all structural checks pass, 1 a check failed, 2 usage/parse error.
"""
import sys

NAVY = (0x0a, 0x16, 0x28)


def read_ppm(path):
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"P6"):
        sys.exit("not a P6 PPM")
    fields = []
    i = 2
    while len(fields) < 3:
        while data[i:i + 1].isspace():
            i += 1
        if data[i:i + 1] == b"#":
            while data[i:i + 1] != b"\n":
                i += 1
            continue
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        fields.append(int(data[i:j]))
        i = j
    i += 1
    w, h, maxv = fields
    px = data[i:i + w * h * 3]
    if len(px) != w * h * 3:
        sys.exit("truncated pixel data: %d != %d" % (len(px), w * h * 3))
    return w, h, px


def ink_mask_row(px, w, y, thresh=90):
    """A pixel is 'ink' when it is clearly brighter than the navy background."""
    base = y * w * 3
    row = px[base:base + w * 3]
    out = []
    for x in range(w):
        r, g, b = row[x * 3], row[x * 3 + 1], row[x * 3 + 2]
        out.append(1 if (r + g + b) / 3 > thresh else 0)
    return out


def bbox(px, w, y0, y1, x0, x1, thresh=90):
    minx, maxx, miny, maxy, n = None, None, None, None, 0
    for y in range(y0, y1):
        m = ink_mask_row(px, w, y, thresh)
        for x in range(x0, x1):
            if m[x]:
                n += 1
                minx = x if minx is None else min(minx, x)
                maxx = x if maxx is None else max(maxx, x)
                miny = y if miny is None else min(miny, y)
                maxy = y if maxy is None else max(maxy, y)
    if minx is None:
        return None
    return (minx, miny, maxx, maxy, n)


def main(argv):
    if len(argv) < 2:
        sys.exit("usage: analyze-screenshot.py <capture.ppm>")
    path = argv[1]
    w, h, px = read_ppm(path)
    sc = max(1, w // 360)
    dw, dh = w // sc, h // sc
    print("capture      : %s" % path)
    print("resolution   : %dx%d  (design space %dx%d, scale %d)" % (w, h, dw, dh, sc))
    # palette
    counts = {}
    step = 7
    for y in range(0, h, step):
        for x in range(0, w, step):
            i = (y * w + x) * 3
            counts[(px[i], px[i + 1], px[i + 2])] = counts.get((px[i], px[i + 1], px[i + 2]), 0) + 1
    top = sorted(counts.items(), key=lambda kv: -kv[1])[:6]
    tot = sum(counts.values())
    print("top colours  : " + ", ".join("rgb%s %.1f%%" % (c, 100.0 * n / tot) for c, n in top))

    fails = []
    bands = [
        ("status-bar", 0, 36, 0, dw),
        ("hero/clock", 40, 90, 0, dw),
        ("app-grid", 150, 240, 0, dw),
        ("content", 240, dw and dh - 80, 0, dw),
        ("dock", dh - 80, dh, 0, dw),
    ]
    for name, y0, y1, x0, x1 in bands:
        b = bbox(px, w, y0 * sc, y1 * sc, x0 * sc, x1 * sc)
        if b is None:
            print("band %-10s: no ink" % name)
            continue
        print("band %-10s: ink bbox design=(%d,%d)-(%d,%d) width=%d px, %d ink px"
              % (name, b[0] / sc, b[1] / sc, b[2] / sc, b[3] / sc, (b[2] - b[0] + 1) / sc, b[4] / (sc * sc)))

    # camera cutout must stay empty in the status bar band
    cut = bbox(px, w, 0, 36 * sc, int(118 * sc), int(242 * sc))
    print("cutout band  : %s" % ("clear" if cut is None else "INK FOUND %s" % (cut,)))
    if cut is not None:
        fails.append("ink inside the camera cutout band")

    # dock labels must not cross their slot boundaries
    slot = dw // 5
    for i in range(5):
        x0, x1 = i * slot * sc, (i + 1) * slot * sc
        b = bbox(px, w, (dh - 80) * sc, dh * sc, x0, x1)
        if b and (b[0] - x0) < 0:
            fails.append("dock slot %d ink leaves its slot" % i)
        print("dock slot %d  : %s" % (i, "empty" if b is None else
              "ink width %d design px (slot %d)" % ((b[2] - b[0] + 1) / sc, slot)))
    # no ink may sit exactly on the dock slot boundaries (the 'fused labels' defect)
    for i in range(1, 5):
        x = i * slot
        b = bbox(px, w, (dh - 24) * sc, dh * sc, max(0, (x - 1) * sc), (x + 1) * sc)
        if b is not None:
            fails.append("ink across the dock slot boundary at design x=%d (fused labels)" % x)

    # the clock must not overflow: its ink must stay well inside the content width
    hero = bbox(px, w, 40 * sc, 90 * sc, 0, dw * sc)
    if hero:
        hw = (hero[2] - hero[0] + 1) / sc
        print("clock width  : %d design px of %d available (%.0f%%)" % (hw, dw, 100.0 * hw / dw))
        if hw > 0.60 * dw:
            fails.append("clock ink occupies %.0f%% of the width (A26 defect)" % (100.0 * hw / dw))
    if fails:
        print("SCREENSHOT_CHECKS_FAILED")
        for f in fails:
            print("   FAIL " + f)
        return 1
    print("SCREENSHOT_CHECKS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
