#!/usr/bin/env python3
"""nuxel bootcap — capture the real /dev/fb0 scanout during early boot.

The S10+ has no DRM device and no VT, so an in-compositor screenshot cannot
prove what the panel actually showed.  nuxel-wl-fb is the single /dev/fb0
owner; this diagnostic only *reads* the same mapping and writes downscaled
PPM frames plus a JSON index.  It never writes /dev/fb0.

Usage:
    bootcap.py --out /var/lib/nuxel/bootcap --duration 24 --interval 0.5

The index records the active yoffset (double-buffered DECON), per-frame mean
RGB and SHA-256, so a headless test can distinguish lockscreen / video /
black frames without image tooling on the phone.
"""
from __future__ import annotations

import argparse, fcntl, hashlib, json, mmap, os, struct, sys, time

FBIOGET_VSCREENINFO = 0x4600


def _var(fd):
    buf = bytearray(160)
    fcntl.ioctl(fd, FBIOGET_VSCREENINFO, buf, True)
    xres, yres, xres_v, yres_v, xoff, yoff = struct.unpack_from("6I", buf, 0)
    bpp = struct.unpack_from("I", buf, 24)[0]
    return xres, yres, xres_v, yres_v, xoff, yoff, bpp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/var/lib/nuxel/bootcap")
    ap.add_argument("--device", default="/dev/fb0")
    ap.add_argument("--duration", type=float, default=24.0)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--down", type=int, default=4)
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    fd = os.open(args.device, os.O_RDWR)
    xres, yres, xres_v, yres_v, _xoff, yoff, bpp = _var(fd)
    stride = xres_v * (bpp // 8)
    total = stride * yres_v
    mm = mmap.mmap(fd, total, prot=mmap.PROT_READ, flags=mmap.MAP_SHARED)
    down = max(1, args.down)
    sw, sh = xres // down, yres // down
    index = []
    t0 = time.monotonic()
    i = 0
    while time.monotonic() - t0 < args.duration:
        _x, _y, _xv, _yv, _xo, page, _bpp = _var(fd)
        base = page * stride
        rows = []
        sr = sg = sb = 0
        for y in range(0, yres, down):
            off = base + y * stride
            for x in range(0, xres, down):
                p = off + x * 4
                b, g, r = mm[p], mm[p + 1], mm[p + 2]
                rows.append(bytes((r, g, b)))
                sr += r; sg += g; sb += b
        payload = b"".join(rows)
        name = f"f{i:03d}.ppm"
        with open(os.path.join(args.out, name), "wb") as f:
            f.write(b"P6\n%d %d\n255\n" % (sw, sh))
            f.write(payload)
        n = sw * sh
        index.append({
            "file": name,
            "t": round(time.monotonic() - t0, 3),
            "wall": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "page": page,
            "mean": [round(sr / n / 255, 4), round(sg / n / 255, 4), round(sb / n / 255, 4)],
            "sha256": hashlib.sha256(payload).hexdigest(),
        })
        i += 1
        time.sleep(args.interval)
    mm.close()
    os.close(fd)
    with open(os.path.join(args.out, "index.json"), "w") as f:
        json.dump({"xres": xres, "yres": yres, "bpp": bpp, "frames": index}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
