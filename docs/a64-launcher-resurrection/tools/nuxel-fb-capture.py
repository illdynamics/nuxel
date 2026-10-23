#!/usr/bin/env python3
"""Read /dev/fb0 via mmap, downsample to a small PNG (stdlib only)."""
import os, zlib, struct, mmap

W, H, STRIDE = 1440, 6080, 5760
OUT_W, OUT_H = 360, 1520
OUT = "/var/tmp/nuxel-shot.png"

def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff)
    return c

def write_png(path, w, h, rgb):
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += rgb[y*w*3:(y+1)*w*3]
    idat = zlib.compress(bytes(raw), 6)
    data = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(data)

def mean_brightness(m, y0, y1):
    s = 0
    n = 0
    for y in range(y0, y1, 16):
        base = y * STRIDE
        for x in range(0, W, 16):
            o = base + x*4
            s += m[o] + m[o+1] + m[o+2]
            n += 3
    return (s / max(1, n)) if n else 0.0

def main():
    fd = os.open("/dev/fb0", os.O_RDONLY)
    m = mmap.mmap(fd, W*H*4, mmap.MAP_SHARED, mmap.PROT_READ)
    x_step = W // OUT_W
    y_step = H // OUT_H
    out = bytearray(OUT_W * OUT_H * 3)
    for oy in range(OUT_H):
        y = oy * y_step
        base = y * STRIDE
        for ox in range(OUT_W):
            off = base + (ox * x_step) * 4
            dst = (oy * OUT_W + ox) * 3
            out[dst] = m[off]
            out[dst+1] = m[off+1]
            out[dst+2] = m[off+2]
    print("BRIGHT top=%d bottom=%d" % (mean_brightness(m, 0, 3040), mean_brightness(m, 3040, 6080)))
    m.close()
    os.close(fd)
    write_png(OUT, OUT_W, OUT_H, bytes(out))
    print("WROTE %s %d" % (OUT, os.path.getsize(OUT)))

if __name__ == "__main__":
    main()
