#!/usr/bin/env python3
"""ref-firstlight.py — INDEPENDENT reference for the A27 first-light frame.

Renders the NUXSPL01 first-light asset with a from-scratch implementation of the
maths in tools/s10plus/nuxel-anim-player.c (the binary that actually owns the
panel during the boot animation):

  * palette: RGB565 -> 8-bit channels -> DECON ABGR_8888 word (R@0 G@8 B@16),
    the hardware order A23 measured, not the driver's declared bitfields;
  * spans:  DW=PW; DH=AH*PW/AW; if DH>PH then DH=PH, DW=AW*PH/AH;
            OX=(PW-DW)/2; OY=(PH-DH)/2; integer nearest-neighbour per source
            pixel, with the player's own clamping;
  * letterbox: the artwork's most frequent palette index;
  * every virtual buffer (yres_virtual/yres) is painted.

Usage:
  ref-firstlight.py <asset.rawspl> <out.raw> [W H] [--ppm out.ppm]

The byte-for-byte comparison against the C renderer (built for the host by
tools/s10plus/a27/test-firstlight.c) is what makes "the first light IS the
player's first frame" a measurement instead of a claim.
"""
import hashlib
import struct
import sys


def parse(blob):
    if len(blob) < 32:
        raise SystemExit("short header")
    if blob[:8] != b"NUXSPL01":
        raise SystemExit("bad magic")
    w, h, paln, flags, blobsz, resv = struct.unpack_from("<IIIIII", blob, 8)
    if resv or flags:
        raise SystemExit("flags/reserved")
    need = 32 + paln * 2 + w * h
    if len(blob) != need:
        raise SystemExit("size")
    pal = struct.unpack_from("<%dH" % paln, blob, 32)
    return w, h, paln, pal, blob[32 + paln * 2:]


def render(asset, PW, PH, bufs):
    w, h, paln, pal, idx = parse(asset)
    rlen = glen = blen = 8
    roff, goff, boff = 0, 8, 16                    # ABGR_8888 (A23)
    def pack(r, g, b):
        R = (r * ((1 << rlen) - 1) + 127) // 255
        G = (g * ((1 << glen) - 1) + 127) // 255
        B = (b * ((1 << blen) - 1) + 127) // 255
        return (R << roff) | (G << goff) | (B << boff)
    dst = []
    for c in pal:
        r = ((c >> 11) & 31) * 255 // 31
        g = ((c >> 5) & 63) * 255 // 63
        b = (c & 31) * 255 // 31
        dst.append(pack(r, g, b))
    DW, DH = PW, (h * PW) // w
    if DH > PH:
        DH = PH
        DW = (w * PH) // h
    OX, OY = (PW - DW) // 2, (PH - DH) // 2
    DX0 = []; DX1 = []; DY0 = []; DY1 = []
    for x in range(w):
        a = OX + (x * DW) // w
        b = OX + ((x + 1) * DW) // w
        if b <= a:
            b = a + 1
        if b > PW:
            b = PW
        if a >= PW:
            a = PW - 1
        DX0.append(a); DX1.append(b)
    for y in range(h):
        a = OY + (y * DH) // h
        b = OY + ((y + 1) * DH) // h
        if b <= a:
            b = a + 1
        if b > PH:
            b = PH
        if a >= PH:
            a = PH - 1
        DY0.append(a); DY1.append(b)
    hist = [0] * 256
    for v in idx:
        hist[v] += 1
    best = 0
    for i in range(1, paln):
        if hist[i] > hist[best]:
            best = i
    bg = dst[best]
    out = bytearray()
    for _ in range(bufs):
        buf = [bg] * (PW * PH)
        for sy in range(h):
            row = idx[sy * w:(sy + 1) * w]
            for y in range(DY0[sy], DY1[sy]):
                base = y * PW
                for sx in range(w):
                    c = dst[row[sx]]
                    for x in range(DX0[sx], DX1[sx]):
                        buf[base + x] = c
        out += struct.pack("<%dI" % (PW * PH), *buf)
    return DW, DH, OX, OY, best, bg, bytes(out)


def main(argv):
    asset_path, out_path = argv[1], argv[2]
    PW, PH = 1440, 3040
    ppm = None
    if len(argv) >= 5 and not argv[3].startswith("--"):
        PW, PH = int(argv[3]), int(argv[4])
    if "--ppm" in argv:
        ppm = argv[argv.index("--ppm") + 1]
    asset = open(asset_path, "rb").read()
    bufs = max(1, min(4, 2))
    DW, DH, OX, OY, best, bg, data = render(asset, PW, PH, bufs)
    open(out_path, "wb").write(data)
    print("REF_DST_W=%d\nREF_DST_H=%d\nREF_DST_X=%d\nREF_DST_Y=%d" % (DW, DH, OX, OY))
    print("REF_BG_INDEX=%d\nREF_BG_DST=0x%08x" % (best, bg))
    print("REF_BYTES=%d\nREF_SHA256=%s" % (len(data), hashlib.sha256(data).hexdigest()))
    if ppm:
        words = struct.unpack("<%dI" % (PW * PH * bufs), data)
        with open(ppm, "wb") as f:
            f.write(b"P6\n%d %d\n255\n" % (PW, PH * bufs))
            for wd in words:
                r, g, b = wd & 255, (wd >> 8) & 255, (wd >> 16) & 255
                f.write(bytes((r, g, b)))
        print("REF_PPM=%s" % ppm)


if __name__ == "__main__":
    main(sys.argv)
