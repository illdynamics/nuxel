#!/usr/bin/env python3
"""compare-wallpaper.py — prove the phone's PNG decoder draws the REAL asset.

nuxel-ui decodes assets/nuxel-background.png with its own freestanding
inflate + PNG unfilter + cover-fit bilinear scaler (it cannot link zlib).  This
script reproduces the SAME cover-fit arithmetic independently with numpy and
compares it against the PPM that the host build of the very same decoder wrote
(`nuxel-ui --selftest=DIR --wallpaper=<asset> --wallpaper-dump=<ppm>`).

Exit: 0 the decoder's output matches the reference, 1 mismatch, 2 usage error.
"""
import argparse
import sys


def read_ppm(path):
    import numpy as np
    with open(path, "rb") as f:
        data = f.read()
    if not data.startswith(b"P6"):
        sys.exit("not a P6 PPM: %s" % path)
    fields, i = [], 2
    while len(fields) < 3:
        while data[i:i + 1].isspace():
            i += 1
        j = i
        while not data[j:j + 1].isspace():
            j += 1
        fields.append(int(data[i:j]))
        i = j
    i += 1
    w, h, _ = fields
    a = np.frombuffer(data[i:i + w * h * 3], dtype=np.uint8)
    return a.reshape(h, w, 3).astype(np.int64)


def reference(asset, pw, ph):
    import numpy as np
    from PIL import Image
    src = np.asarray(Image.open(asset).convert("RGB"), dtype=np.int64)
    sh, sw, _ = src.shape
    sc = max((pw << 16) // sw, (ph << 16) // sh)
    used_w, used_h = (sw * sc) >> 16, (sh * sc) >> 16
    xoff = (used_w - pw) // 2 if used_w > pw else 0
    yoff = (used_h - ph) // 2 if used_h > ph else 0
    xs = ((np.arange(pw, dtype=np.int64) + xoff) << 16) + 32768
    ys = ((np.arange(ph, dtype=np.int64) + yoff) << 16) + 32768
    sx0 = np.minimum(xs >> 16, sw - 1)
    sy0 = np.minimum(ys >> 16, sh - 1)
    sx1 = np.minimum(sx0 + 1, sw - 1)
    sy1 = np.minimum(sy0 + 1, sh - 1)
    fx = ((xs >> 8) & 0xFF)[None, :, None]
    fy = ((ys >> 8) & 0xFF)[:, None, None]
    a = src[np.ix_(sy0, sx0)]
    b = src[np.ix_(sy0, sx1)]
    c = src[np.ix_(sy1, sx0)]
    d = src[np.ix_(sy1, sx1)]
    top = (a * (256 - fx) + b * fx) >> 8
    bot = (c * (256 - fx) + d * fx) >> 8
    return (top * (256 - fy) + bot * fy) >> 8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--dump", required=True)
    ap.add_argument("--max-diff", type=int, default=2)
    ap.add_argument("--max-mean", type=float, default=0.25)
    a = ap.parse_args()
    import numpy as np
    got = read_ppm(a.dump)
    ph, pw, _ = got.shape
    ref = reference(a.asset, pw, ph)
    diff = np.abs(got - ref)
    worst = int(diff.max())
    mean = float(diff.mean())
    print("   checked %dx%d pixels against the reference: worst=%d mean=%.4f"
          % (pw, ph, worst, mean))
    if worst > a.max_diff or mean > a.max_mean:
        print("WALLPAPER_DECODE_MISMATCH worst=%d mean=%.4f" % (worst, mean))
        return 1
    print("WALLPAPER_DECODE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
